"""SQLAlchemy data model (Chapter 3.5.2 / Chapter 4.4 Data Model).

Schema 1 - FAQ knowledge base: categories, faqs, settings, admin_users.
Schema 2 - Interaction data: conversation_logs, feedback (FR-07).
"""
from datetime import datetime, timezone

import bcrypt
from flask_login import UserMixin

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Category(db.Model):
    """One of the six FAQ categories (FR-02)."""
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name_en = db.Column(db.String(64), unique=True, nullable=False)
    name_ar = db.Column(db.String(64), nullable=False)

    faqs = db.relationship("FAQ", back_populates="category")

    def to_dict(self):
        return {"id": self.id, "name_en": self.name_en, "name_ar": self.name_ar}


class FAQ(db.Model):
    """A verified question/answer pair in the knowledge base (FR-06, FR-09)."""
    __tablename__ = "faqs"

    id = db.Column(db.Integer, primary_key=True)
    question_en = db.Column(db.Text, nullable=False)
    question_ar = db.Column(db.Text, nullable=False, default="")
    answer = db.Column(db.Text, nullable=False)
    answer_ar = db.Column(db.Text, nullable=False, default="")
    answer_lang = db.Column(db.String(8), nullable=False, default="en")
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    keywords = db.Column(db.Text, nullable=False, default="")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    category = db.relationship("Category", back_populates="faqs")

    def to_dict(self):
        return {
            "id": self.id,
            "question_en": self.question_en,
            "question_ar": self.question_ar,
            "answer": self.answer,
            "answer_ar": self.answer_ar,
            "answer_lang": self.answer_lang,
            "category_id": self.category_id,
            "category": self.category.name_en if self.category else None,
            "category_ar": self.category.name_ar if self.category else None,
            "keywords": self.keywords,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ConversationLog(db.Model):
    """Every chatbot query with its match, confidence and method (FR-07)."""
    __tablename__ = "conversation_logs"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(64), nullable=False, index=True)
    query_text = db.Column(db.Text, nullable=False)
    detected_lang = db.Column(db.String(8), nullable=False)
    matched_faq_id = db.Column(db.Integer, db.ForeignKey("faqs.id", ondelete="SET NULL"), nullable=True)
    confidence = db.Column(db.Float, nullable=False, default=0.0)
    method = db.Column(db.String(16), nullable=False)  # tfidf | sbert | fallback
    category = db.Column(db.String(64), nullable=True)  # FR-02 category of the query
    response_ms = db.Column(db.Float, nullable=False, default=0.0)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    matched_faq = db.relationship("FAQ")
    feedback = db.relationship("Feedback", back_populates="log", cascade="all, delete-orphan")

    def to_dict(self):
        fb = self.feedback[-1].helpful if self.feedback else None
        return {
            "id": self.id,
            "session_id": self.session_id,
            "query_text": self.query_text,
            "detected_lang": self.detected_lang,
            "matched_faq_id": self.matched_faq_id,
            "matched_question": self.matched_faq.question_en if self.matched_faq else None,
            "confidence": round(self.confidence, 4),
            "method": self.method,
            "category": self.category,
            "response_ms": round(self.response_ms, 1),
            "helpful": fb,
            "created_at": self.created_at.isoformat(),
        }


class Feedback(db.Model):
    """Thumbs up/down rating on a chatbot answer."""
    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)
    log_id = db.Column(db.Integer, db.ForeignKey("conversation_logs.id"), nullable=False)
    helpful = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)

    log = db.relationship("ConversationLog", back_populates="feedback")


class AdminUser(UserMixin, db.Model):
    """Staff account for the admin dashboard; bcrypt-hashed password (NF-05)."""
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)

    def set_password(self, password: str) -> None:
        self.password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

    def check_password(self, password: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), self.password_hash.encode("utf-8"))
        except ValueError:
            return False

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }


class Setting(db.Model):
    """Key/value runtime settings, e.g. confidence_threshold (editable by admin)."""
    __tablename__ = "settings"

    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.String(255), nullable=False)

    @staticmethod
    def get(key: str, default=None):
        row = db.session.get(Setting, key)
        return row.value if row else default

    @staticmethod
    def set(key: str, value) -> None:
        row = db.session.get(Setting, key)
        if row:
            row.value = str(value)
        else:
            db.session.add(Setting(key=key, value=str(value)))
