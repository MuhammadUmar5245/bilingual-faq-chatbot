"""Admin dashboard API - login required (FR-06, FR-07, NF-05, NF-06).

All database access goes through SQLAlchemy with bound parameters, so user input is never
concatenated into SQL (SQL-injection protection, NF-05).
"""
import csv
import io
import re
from datetime import datetime, timedelta

from flask import Blueprint, Response, jsonify, request
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func, or_

from app.extensions import db, limiter
from app.nlp_service import bump_faq_version, current_settings
from app.seed import CSV_COLUMNS, parse_faq_rows
from models import FAQ, AdminUser, Category, ConversationLog, Feedback, Setting, utcnow

admin_bp = Blueprint("admin", __name__)

FAQ_TEXT_FIELDS = ("question_en", "question_ar", "answer", "answer_ar", "keywords")
MAX_FIELD_LEN = 4000
SETTING_KEYS = {
    "confidence_threshold": float, "sbert_threshold": float, "fusion_weight": float,
    "contact_office": str, "contact_phone": str, "contact_email": str, "contact_hours": str,
}


def error(msg, code=400):
    return jsonify(error=msg), code


def json_body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def paginate(query, default_per_page=20):
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", default_per_page, type=int), 1), 200)
    total = query.order_by(None).count()
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    return items, {"page": page, "per_page": per_page, "total": total,
                   "pages": max((total + per_page - 1) // per_page, 1)}


def parse_date(value, end=False):
    if not value:
        return None
    try:
        d = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None
    return d + timedelta(days=1) if end else d


# --------------------------------------------------------------------------- auth
@admin_bp.post("/login")
@limiter.limit("10 per minute")
def login():
    data = json_body()
    if not data:
        return error("request body must be JSON")
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    user = AdminUser.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return error("invalid username or password", 401)
    login_user(user)
    user.last_login = utcnow()
    db.session.commit()
    return jsonify(user=user.to_dict())


@admin_bp.post("/logout")
@login_required
def logout():
    logout_user()
    return jsonify(ok=True)


@admin_bp.get("/me")
@login_required
def me():
    return jsonify(user=current_user.to_dict())


@admin_bp.put("/password")
@login_required
def change_password():
    data = json_body() or {}
    current, new = str(data.get("current_password", "")), str(data.get("new_password", ""))
    if not current_user.check_password(current):
        return error("current password is incorrect", 403)
    if len(new) < 8 or not re.search(r"[A-Za-z]", new) or not re.search(r"\d", new):
        return error("new password must be at least 8 characters and contain letters and digits")
    current_user.set_password(new)
    db.session.commit()
    return jsonify(ok=True)


# --------------------------------------------------------------------------- FAQs (FR-06)
def validate_faq(data: dict, partial=False):
    """Return (clean_values, error_message)."""
    clean = {}
    for f in FAQ_TEXT_FIELDS:
        if f in data:
            v = data[f]
            if v is None:
                v = ""
            if not isinstance(v, str):
                return None, f"'{f}' must be text"
            if len(v) > MAX_FIELD_LEN:
                return None, f"'{f}' is too long"
            clean[f] = v.strip()
    if "category_id" in data:
        if not isinstance(data["category_id"], int) or not db.session.get(Category, data["category_id"]):
            return None, "'category_id' must be a valid category"
        clean["category_id"] = data["category_id"]
    if "is_active" in data:
        if not isinstance(data["is_active"], bool):
            return None, "'is_active' must be true or false"
        clean["is_active"] = data["is_active"]
    if not partial:
        for req in ("question_en", "answer", "category_id"):
            if not clean.get(req):
                return None, f"'{req}' is required"
    else:
        for req in ("question_en", "answer"):
            if req in clean and not clean[req]:
                return None, f"'{req}' cannot be empty"
    if "answer" in clean or "answer_ar" in clean:
        has_ar = bool(clean.get("answer_ar"))
        clean["answer_lang"] = "en+ar" if has_ar else "en"
    return clean, None


@admin_bp.get("/faqs")
@login_required
def list_faqs():
    q = FAQ.query
    search = request.args.get("q", "").strip()
    if search:
        like = f"%{search}%"
        q = q.filter(or_(FAQ.question_en.ilike(like), FAQ.question_ar.ilike(like),
                         FAQ.answer.ilike(like), FAQ.keywords.ilike(like)))
    if cat := request.args.get("category_id", type=int):
        q = q.filter(FAQ.category_id == cat)
    status = request.args.get("status")
    if status in ("active", "inactive"):
        q = q.filter(FAQ.is_active.is_(status == "active"))
    sort = request.args.get("sort", "id")
    order = {"id": FAQ.id, "updated": FAQ.updated_at.desc(), "question": FAQ.question_en}.get(sort, FAQ.id)
    items, meta = paginate(q.order_by(order))
    return jsonify(items=[f.to_dict() for f in items], **meta)


@admin_bp.get("/faqs/<int:faq_id>")
@login_required
def get_faq(faq_id):
    faq = db.session.get(FAQ, faq_id)
    return jsonify(faq.to_dict()) if faq else error("FAQ not found", 404)


@admin_bp.post("/faqs")
@login_required
def create_faq():
    data = json_body()
    if data is None:
        return error("request body must be JSON")
    clean, err = validate_faq(data)
    if err:
        return error(err)
    faq = FAQ(**clean)
    db.session.add(faq)
    db.session.commit()
    bump_faq_version()  # rebuild the retrieval index
    return jsonify(faq.to_dict()), 201


@admin_bp.put("/faqs/<int:faq_id>")
@login_required
def update_faq(faq_id):
    faq = db.session.get(FAQ, faq_id)
    if not faq:
        return error("FAQ not found", 404)
    data = json_body()
    if data is None:
        return error("request body must be JSON")
    clean, err = validate_faq(data, partial=True)
    if err:
        return error(err)
    for k, v in clean.items():
        setattr(faq, k, v)
    faq.updated_at = utcnow()
    db.session.commit()
    bump_faq_version()
    return jsonify(faq.to_dict())


@admin_bp.patch("/faqs/<int:faq_id>/toggle")
@login_required
def toggle_faq(faq_id):
    faq = db.session.get(FAQ, faq_id)
    if not faq:
        return error("FAQ not found", 404)
    faq.is_active = not faq.is_active
    faq.updated_at = utcnow()
    db.session.commit()
    bump_faq_version()
    return jsonify(faq.to_dict())


@admin_bp.delete("/faqs/<int:faq_id>")
@login_required
def delete_faq(faq_id):
    faq = db.session.get(FAQ, faq_id)
    if not faq:
        return error("FAQ not found", 404)
    ConversationLog.query.filter_by(matched_faq_id=faq.id).update({"matched_faq_id": None})
    db.session.delete(faq)
    db.session.commit()
    bump_faq_version()
    return jsonify(ok=True, deleted_id=faq_id)


@admin_bp.post("/faqs/import")
@login_required
def import_faqs():
    """Import FAQs from a CSV file (same columns as data/faqs_seed.csv). mode=append|replace."""
    upload = request.files.get("file")
    if not upload or not upload.filename:
        return error("upload a CSV file in the 'file' field")
    if not upload.filename.lower().endswith(".csv"):
        return error("only .csv files are accepted")
    raw = upload.read(5 * 1024 * 1024 + 1)
    if len(raw) > 5 * 1024 * 1024:
        return error("file is larger than 5 MB")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return error("file must be UTF-8 encoded")
    rows, errors = parse_faq_rows(text)
    if not rows:
        return error("; ".join(errors[:5]) or "no valid rows found")
    mode = request.form.get("mode", "append")
    if mode == "replace":
        FAQ.query.update({"is_active": False})
    db.session.add_all(FAQ(**r) for r in rows)
    db.session.commit()
    bump_faq_version()
    return jsonify(imported=len(rows), skipped=len(errors), errors=errors[:20], mode=mode), 201


@admin_bp.get("/faqs/export")
@login_required
def export_faqs():
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["id"] + CSV_COLUMNS + ["is_active"])
    writer.writeheader()
    for f in FAQ.query.order_by(FAQ.id).all():
        writer.writerow({"id": f.id, "question_en": f.question_en, "question_ar": f.question_ar,
                         "answer": f.answer, "answer_ar": f.answer_ar, "answer_lang": f.answer_lang,
                         "category": f.category.name_en, "keywords": f.keywords, "is_active": f.is_active})
    return Response("﻿" + buf.getvalue(), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=faqs_export.csv"})


@admin_bp.get("/categories")
@login_required
def admin_categories():
    return jsonify([c.to_dict() for c in Category.query.order_by(Category.id).all()])


# --------------------------------------------------------------------------- logs (FR-07)
def filtered_logs():
    q = ConversationLog.query
    if search := request.args.get("q", "").strip():
        q = q.filter(ConversationLog.query_text.ilike(f"%{search}%"))
    if (method := request.args.get("method")) in ("tfidf", "sbert", "fallback"):
        q = q.filter(ConversationLog.method == method)
    if (lang := request.args.get("lang")) in ("en", "ar"):
        q = q.filter(ConversationLog.detected_lang == lang)
    if session_id := request.args.get("session_id"):
        q = q.filter(ConversationLog.session_id == session_id)
    if d := parse_date(request.args.get("date_from")):
        q = q.filter(ConversationLog.created_at >= d)
    if d := parse_date(request.args.get("date_to"), end=True):
        q = q.filter(ConversationLog.created_at < d)
    return q


@admin_bp.get("/logs")
@login_required
def logs():
    items, meta = paginate(filtered_logs().order_by(ConversationLog.id.desc()))
    return jsonify(items=[l.to_dict() for l in items], **meta)


@admin_bp.get("/unanswered")
@login_required
def unanswered():
    """Queries that got the fallback or were rated unhelpful - candidates for new FAQs."""
    kind = request.args.get("type", "all")
    negative = db.session.query(Feedback.log_id).filter(Feedback.helpful.is_(False))
    if kind == "fallback":
        cond = ConversationLog.method == "fallback"
    elif kind == "unhelpful":
        cond = ConversationLog.id.in_(negative)
    else:
        cond = or_(ConversationLog.method == "fallback", ConversationLog.id.in_(negative))
    items, meta = paginate(ConversationLog.query.filter(cond).order_by(ConversationLog.id.desc()))
    out = []
    for l in items:
        d = l.to_dict()
        d["reason"] = "fallback" if l.method == "fallback" else "unhelpful"
        out.append(d)
    return jsonify(items=out, **meta)


# --------------------------------------------------------------------------- stats
@admin_bp.get("/stats")
@login_required
def stats():
    days = min(max(request.args.get("days", 14, type=int), 1), 90)
    total = db.session.query(func.count(ConversationLog.id)).scalar() or 0
    answered = db.session.query(func.count(ConversationLog.id)).filter(ConversationLog.method != "fallback").scalar() or 0
    avg_conf = db.session.query(func.avg(ConversationLog.confidence)).filter(ConversationLog.method != "fallback").scalar()
    avg_ms = db.session.query(func.avg(ConversationLog.response_ms)).scalar()
    fb_total = db.session.query(func.count(Feedback.id)).scalar() or 0
    fb_up = db.session.query(func.count(Feedback.id)).filter(Feedback.helpful.is_(True)).scalar() or 0

    since = (utcnow() - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    per_day = {(since + timedelta(days=i)).strftime("%Y-%m-%d"): 0 for i in range(days)}
    for (created,) in db.session.query(ConversationLog.created_at).filter(ConversationLog.created_at >= since):
        key = created.strftime("%Y-%m-%d")
        if key in per_day:
            per_day[key] += 1

    def group(col):
        return {k or "Unknown": v for k, v in
                db.session.query(col, func.count(ConversationLog.id)).group_by(col).all()}

    top = (db.session.query(FAQ, func.count(ConversationLog.id).label("n"))
           .join(ConversationLog, ConversationLog.matched_faq_id == FAQ.id)
           .group_by(FAQ.id).order_by(func.count(ConversationLog.id).desc()).limit(5).all())
    return jsonify(
        total_queries=total,
        answered=answered,
        fallback=total - answered,
        resolution_rate=round(answered / total, 4) if total else 0.0,
        avg_confidence=round(float(avg_conf), 4) if avg_conf is not None else 0.0,
        avg_response_ms=round(float(avg_ms), 1) if avg_ms is not None else 0.0,
        feedback_total=fb_total,
        helpful_rate=round(fb_up / fb_total, 4) if fb_total else None,
        sessions=db.session.query(func.count(func.distinct(ConversationLog.session_id))).scalar() or 0,
        faqs_active=FAQ.query.filter_by(is_active=True).count(),
        faqs_inactive=FAQ.query.filter_by(is_active=False).count(),
        per_day=[{"date": k, "count": v} for k, v in per_day.items()],
        per_category=group(ConversationLog.category),
        per_method=group(ConversationLog.method),
        per_language=group(ConversationLog.detected_lang),
        top_faqs=[{"id": f.id, "question": f.question_en, "count": n} for f, n in top],
    )


# --------------------------------------------------------------------------- settings
@admin_bp.get("/settings")
@login_required
def get_settings():
    out = current_settings()
    for k in SETTING_KEYS:
        if k not in out:
            out[k] = Setting.get(k, "")
    return jsonify(out)


@admin_bp.put("/settings")
@login_required
def put_settings():
    data = json_body()
    if not data:
        return error("request body must be JSON")
    updates = {}
    for key, value in data.items():
        if key not in SETTING_KEYS:
            return error(f"unknown setting '{key}'")
        if SETTING_KEYS[key] is float:
            try:
                value = float(value)
            except (TypeError, ValueError):
                return error(f"'{key}' must be a number")
            if not 0.0 <= value <= 1.0:
                return error(f"'{key}' must be between 0 and 1")
        else:
            value = str(value).strip()[:255]
        updates[key] = value
    for k, v in updates.items():
        Setting.set(k, v)
    db.session.commit()
    return get_settings()
