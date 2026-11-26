"""Query-log privacy (FR-07; Chapter 4.4, Table 19): masking of personal details and retention."""
from datetime import timedelta

import pytest

from app.extensions import db
from app.privacy import EMAIL_MASK, NUMBER_MASK, REDACTED, mask_personal_details, purge_old_query_text
from models import ConversationLog, Feedback, utcnow


@pytest.mark.parametrize("text, expected", [
    ("my email is ali.said@student.edu.om please reply", f"my email is {EMAIL_MASK} please reply"),
    ("call me on +968 9123 4567", f"call me on {NUMBER_MASK}"),
    ("call 91234567 after 3", f"call {NUMBER_MASK} after 3"),
    ("my student number is 20231234", f"my student number is {NUMBER_MASK}"),
    ("رقمي ٩١٢٣٤٥٦٧", f"رقمي {NUMBER_MASK}"),
    ("phone 9123-4567", f"phone {NUMBER_MASK}"),
])
def test_personal_details_are_masked(text, expected):
    assert mask_personal_details(text) == expected


@pytest.mark.parametrize("text", [
    "When does the 2025 semester start?",
    "Is MATH101 a prerequisite?",
    "Hostel costs 450 OMR per semester",
    "كم رسوم السكن؟",
])
def test_ordinary_questions_are_unchanged(text):
    assert mask_personal_details(text) == text


def test_chat_log_stores_masked_text_but_answers_normally(client, app):  # FR-07, Table 19
    msg = "How do I pay the tuition fees? my number is 91234567, email a.b@x.om"
    r = client.post("/api/chat", json={"message": msg, "session_id": "privacy"})
    assert r.status_code == 200 and r.json["query"] == msg
    with app.app_context():
        log = db.session.get(ConversationLog, r.json["log_id"])
        assert "91234567" not in log.query_text and "a.b@x.om" not in log.query_text
        assert NUMBER_MASK in log.query_text and EMAIL_MASK in log.query_text


def test_purge_removes_only_old_free_text(app):  # Table 19 retention
    with app.app_context():
        old = ConversationLog(session_id="s", query_text="old question", detected_lang="en", method="tfidf",
                              matched_faq_id=1, confidence=0.9, category="Fees",
                              created_at=utcnow() - timedelta(days=400))
        new = ConversationLog(session_id="s", query_text="new question", detected_lang="en", method="fallback",
                              created_at=utcnow() - timedelta(days=10))
        db.session.add_all([old, new])
        db.session.flush()
        db.session.add(Feedback(log_id=old.id, helpful=True))
        db.session.commit()
        assert purge_old_query_text(365) == 1
        assert purge_old_query_text(365) == 0  # idempotent
        db.session.refresh(old)
        db.session.refresh(new)
        assert old.query_text == REDACTED and new.query_text == "new question"
        # metadata and feedback are kept
        assert old.matched_faq_id == 1 and old.method == "tfidf" and old.category == "Fees" and old.feedback


def test_purge_cli_command(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["purge-logs", "--days", "30"])
    assert result.exit_code == 0 and "older than 30 days" in result.output
