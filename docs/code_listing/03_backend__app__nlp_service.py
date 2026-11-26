"""Bridge between the database and the NLP engine.

Keeps one HybridRetriever per process. Every change to the knowledge base made through the
admin API increments the `faq_version` setting; before answering, each worker compares its
own version with the database and rebuilds its indexes if they are stale. This keeps several
gunicorn workers consistent without restarting the API (FR-06, NF-06).
"""
import threading

from flask import current_app

from app.extensions import db
from models import FAQ, Setting
from nlp.hybrid import HybridRetriever
from nlp.tfidf_retriever import FaqDoc

_lock = threading.Lock()
_state = {"engine": None, "version": None, "settings": None}


_ENGINE_KEYS = ("faq_version", "confidence_threshold", "sbert_threshold", "fusion_weight")


def _engine_settings() -> tuple[str, dict]:
    """Read the FAQ version and thresholds in a single query (called on every chat request)."""
    cfg = current_app.config
    rows = dict(db.session.query(Setting.key, Setting.value).filter(Setting.key.in_(_ENGINE_KEYS)).all())

    def num(key, default):
        try:
            return float(rows.get(key, default))
        except (TypeError, ValueError):
            return default

    return rows.get("faq_version", "0"), {
        "confidence_threshold": num("confidence_threshold", cfg["CONFIDENCE_THRESHOLD"]),
        "sbert_threshold": num("sbert_threshold", cfg["SBERT_THRESHOLD"]),
        "fusion_weight": num("fusion_weight", cfg["FUSION_WEIGHT"]),
    }


def current_settings() -> dict:
    return _engine_settings()[1]


def bump_faq_version() -> None:
    """Mark the knowledge base as changed; every worker rebuilds on its next query."""
    Setting.set("faq_version", int(Setting.get("faq_version", 0) or 0) + 1)
    db.session.commit()


def _faq_docs() -> list[FaqDoc]:
    rows = FAQ.query.filter_by(is_active=True).order_by(FAQ.id).all()
    return [FaqDoc(f.id, f.question_en, f.question_ar or "", f.keywords or "", f.category.name_en,
                   f.answer, f.answer_ar or "") for f in rows]


def get_engine() -> HybridRetriever:
    """Return an up-to-date retriever, rebuilding it when FAQs or thresholds changed."""
    version, settings = _engine_settings()
    with _lock:
        engine = _state["engine"]
        if engine is None or _state["version"] != version:
            cfg = current_app.config
            engine = HybridRetriever(
                tfidf_threshold=settings["confidence_threshold"],
                sbert_threshold=settings["sbert_threshold"],
                fusion_weight=settings["fusion_weight"],
                use_sbert=cfg["ENABLE_SBERT"],
                sbert_model=cfg["SBERT_MODEL"],
            ).fit(_faq_docs())
            _state.update(engine=engine, version=version, settings=settings)
        elif _state["settings"] != settings:  # thresholds edited in admin - no rebuild needed
            engine.tfidf_threshold = settings["confidence_threshold"]
            engine.sbert_threshold = settings["sbert_threshold"]
            engine.fusion_weight = settings["fusion_weight"]
            _state["settings"] = settings
        return engine


def reset_engine() -> None:
    with _lock:
        _state.update(engine=None, version=None, settings=None)
