"""Database seeding: categories, default settings, default admin, FAQ CSV (FR-09)."""
import csv
import io
from pathlib import Path

from flask import current_app

from app.extensions import db
from models import AdminUser, Category, FAQ, Setting

CATEGORIES = [
    ("Admissions", "القبول"),
    ("Registration", "التسجيل"),
    ("Fees", "الرسوم"),
    ("Academic Programmes", "البرامج الأكاديمية"),
    ("Examinations", "الامتحانات"),
    ("Student Services", "خدمات الطلبة"),
]

CSV_COLUMNS = ["question_en", "question_ar", "answer", "answer_ar", "answer_lang", "category", "keywords"]
REQUIRED_COLUMNS = {"question_en", "answer", "category"}


def seed_categories() -> None:
    for name_en, name_ar in CATEGORIES:
        if not Category.query.filter_by(name_en=name_en).first():
            db.session.add(Category(name_en=name_en, name_ar=name_ar))
    db.session.commit()


def seed_settings() -> None:
    cfg = current_app.config
    defaults = {
        "confidence_threshold": cfg["CONFIDENCE_THRESHOLD"],
        "sbert_threshold": cfg["SBERT_THRESHOLD"],
        "fusion_weight": cfg["FUSION_WEIGHT"],
        "contact_office": cfg["CONTACT"]["office"],
        "contact_phone": cfg["CONTACT"]["phone"],
        "contact_email": cfg["CONTACT"]["email"],
        "contact_hours": cfg["CONTACT"]["hours"],
    }
    for key, value in defaults.items():
        if Setting.get(key) is None:
            Setting.set(key, value)
    db.session.commit()


def seed_admin() -> None:
    """Create the default admin from env vars if no admin exists (NF-05)."""
    if AdminUser.query.count() == 0:
        user = AdminUser(username=current_app.config["ADMIN_USERNAME"])
        user.set_password(current_app.config["ADMIN_PASSWORD"])
        db.session.add(user)
        db.session.commit()


def parse_faq_rows(text: str):
    """Parse CSV text into FAQ dicts. Returns (rows, errors). Used by seeding and admin import."""
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    if not reader.fieldnames or not REQUIRED_COLUMNS.issubset({f.strip() for f in reader.fieldnames}):
        return [], [f"CSV must contain columns: {', '.join(sorted(REQUIRED_COLUMNS))}"]
    categories = {c.name_en.lower(): c for c in Category.query.all()}
    rows, errors = [], []
    for line_no, raw in enumerate(reader, start=2):
        row = {k.strip(): (v or "").strip() for k, v in raw.items() if k}
        cat = categories.get(row.get("category", "").lower())
        if not row.get("question_en") or not row.get("answer"):
            errors.append(f"Line {line_no}: question_en and answer are required")
            continue
        if not cat:
            errors.append(f"Line {line_no}: unknown category '{row.get('category')}'")
            continue
        rows.append({
            "question_en": row["question_en"],
            "question_ar": row.get("question_ar", ""),
            "answer": row["answer"],
            "answer_ar": row.get("answer_ar", ""),
            "answer_lang": row.get("answer_lang") or "en",
            "category_id": cat.id,
            "keywords": row.get("keywords", ""),
        })
    return rows, errors


def seed_faqs(csv_path: Path | None = None) -> int:
    """Load FAQs from data/faqs_seed.csv when the faqs table is empty."""
    if FAQ.query.count() > 0:
        return 0
    path = Path(csv_path or current_app.config["FAQ_SEED_CSV"])
    if not path.exists():
        current_app.logger.warning("FAQ seed file not found: %s", path)
        return 0
    rows, errors = parse_faq_rows(path.read_text(encoding="utf-8"))
    for err in errors:
        current_app.logger.warning("Seed: %s", err)
    db.session.add_all(FAQ(**r) for r in rows)
    db.session.commit()
    return len(rows)


def seed_all() -> None:
    seed_categories()
    seed_settings()
    seed_admin()
    if current_app.config.get("AUTO_SEED", True):
        seed_faqs()
