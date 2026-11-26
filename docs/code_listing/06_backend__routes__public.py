"""Public chatbot API used by the chat widget (FR-01..FR-05, FR-07, FR-10)."""
import time
import uuid

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import func

from app.extensions import db, limiter
from app.nlp_service import get_engine
from models import FAQ, Category, ConversationLog, Feedback, Setting

public_bp = Blueprint("public", __name__)

MAX_QUERY_LEN = 500

FALLBACK_TEXT = {
    "en": "Sorry, I couldn't find a verified answer to your question. Please contact the {office} "
          "and a member of staff will help you.",
    "ar": "عذراً، لم أجد إجابة موثقة لسؤالك. يرجى التواصل مع {office} وسيقوم أحد الموظفين بمساعدتك.",
}


def contact_details() -> dict:
    cfg = current_app.config["CONTACT"]
    return {
        "office": Setting.get("contact_office", cfg["office"]),
        "phone": Setting.get("contact_phone", cfg["phone"]),
        "email": Setting.get("contact_email", cfg["email"]),
        "hours": Setting.get("contact_hours", cfg["hours"]),
    }


def _bad_request(msg):
    return jsonify(error=msg), 400


def _faq_brief(faq: FAQ, lang: str) -> dict:
    return {
        "id": faq.id,
        "question": faq.question_ar if lang == "ar" and faq.question_ar else faq.question_en,
        "question_en": faq.question_en,
        "question_ar": faq.question_ar,
        "category": faq.category.name_en,
        "category_ar": faq.category.name_ar,
    }


@public_bp.get("/health")
def health():
    """Liveness/readiness probe for Docker (NF-04)."""
    try:
        faqs = db.session.query(func.count(FAQ.id)).filter(FAQ.is_active.is_(True)).scalar()
        db_ok = True
    except Exception:  # pragma: no cover - only when the database is down
        faqs, db_ok = 0, False
    return jsonify(status="ok" if db_ok else "degraded", database=db_ok, active_faqs=faqs,
                   sbert_enabled=current_app.config["ENABLE_SBERT"]), (200 if db_ok else 503)


@public_bp.post("/chat")
@limiter.limit(lambda: current_app.config["CHAT_RATE_LIMIT"])
def chat():
    """Answer a student query with a verified FAQ or the fallback message; log it (FR-07)."""
    start = time.perf_counter()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _bad_request("request body must be JSON")
    message = data.get("message")
    if not isinstance(message, str) or not message.strip():
        return _bad_request("'message' is required")
    message = message.strip()
    if len(message) > MAX_QUERY_LEN:
        return _bad_request(f"'message' must be at most {MAX_QUERY_LEN} characters")
    session_id = str(data.get("session_id") or uuid.uuid4().hex)[:64]

    result = get_engine().retrieve(message)
    lang = result.lang
    faq = db.session.get(FAQ, result.faq_id) if result.faq_id else None

    body = {
        "session_id": session_id,
        "query": message,
        "lang": lang,
        "method": result.method,
        "confidence": result.confidence,
        "category": result.category,
        "fallback": faq is None,
    }
    if faq:
        use_ar = lang == "ar" and bool(faq.answer_ar)
        body.update(
            faq_id=faq.id,
            question=faq.question_ar if lang == "ar" and faq.question_ar else faq.question_en,
            answer=faq.answer_ar if use_ar else faq.answer,
            answer_lang="ar" if use_ar else "en",
            answer_alt=faq.answer if use_ar else (faq.answer_ar or None),
            category=faq.category.name_en,
            category_ar=faq.category.name_ar,
        )
    else:
        contact = contact_details()
        body.update(
            faq_id=None,
            answer=FALLBACK_TEXT[lang].format(office=contact["office"]),
            answer_lang=lang,
            contact=contact,
        )
        cat = Category.query.filter_by(name_en=result.category).first() if result.category else None
        body["category_ar"] = cat.name_ar if cat else None
    # Near misses are offered as "Did you mean...?" suggestions
    alt_ids = [faq_id for faq_id, _score in result.alternatives]
    alts = {f.id: f for f in FAQ.query.filter(FAQ.id.in_(alt_ids), FAQ.is_active.is_(True)).all()} if alt_ids else {}
    body["suggestions"] = [_faq_brief(alts[i], lang) for i in alt_ids if i in alts][:3]

    elapsed = (time.perf_counter() - start) * 1000
    log = ConversationLog(session_id=session_id, query_text=message, detected_lang=lang,
                          matched_faq_id=result.faq_id, confidence=result.confidence, method=result.method,
                          category=body.get("category"), response_ms=elapsed)
    db.session.add(log)
    db.session.commit()
    body.update(log_id=log.id, response_ms=round(elapsed, 1))
    return jsonify(body)


@public_bp.get("/categories")
def categories():
    counts = dict(db.session.query(FAQ.category_id, func.count(FAQ.id))
                  .filter(FAQ.is_active.is_(True)).group_by(FAQ.category_id).all())
    return jsonify([{**c.to_dict(), "faq_count": counts.get(c.id, 0)}
                    for c in Category.query.order_by(Category.id).all()])


@public_bp.get("/faqs/popular")
def popular():
    """Most frequently matched FAQs; optional ?category_id= returns that category's questions."""
    lang = request.args.get("lang", "en")
    limit = min(max(request.args.get("limit", 6, type=int), 1), 50)
    category_id = request.args.get("category_id", type=int)

    q = FAQ.query.filter(FAQ.is_active.is_(True))
    if category_id:
        q = q.filter(FAQ.category_id == category_id)
    hits = dict(db.session.query(ConversationLog.matched_faq_id, func.count(ConversationLog.id))
                .filter(ConversationLog.matched_faq_id.isnot(None))
                .group_by(ConversationLog.matched_faq_id).all())
    faqs = q.order_by(FAQ.id).all()
    if hits:
        faqs.sort(key=lambda f: (-hits.get(f.id, 0), f.id))
    elif not category_id:
        # No usage data yet: show the first question of every category
        seen, firsts = set(), []
        for f in faqs:
            if f.category_id not in seen:
                seen.add(f.category_id)
                firsts.append(f)
        faqs = firsts + [f for f in faqs if f not in firsts]
    return jsonify([{**_faq_brief(f, lang), "hits": hits.get(f.id, 0)} for f in faqs[:limit]])


@public_bp.post("/feedback")
def feedback():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _bad_request("request body must be JSON")
    log_id, helpful = data.get("log_id"), data.get("helpful")
    if not isinstance(log_id, int) or not isinstance(helpful, bool):
        return _bad_request("'log_id' (integer) and 'helpful' (boolean) are required")
    log = db.session.get(ConversationLog, log_id)
    if not log:
        return jsonify(error="conversation log not found"), 404
    fb = Feedback(log_id=log.id, helpful=helpful)
    db.session.add(fb)
    db.session.commit()
    return jsonify(ok=True, feedback_id=fb.id), 201


@public_bp.get("/contact")
def contact():
    """Escalation contact details shown on the fallback card (FR-05)."""
    return jsonify(contact_details())
