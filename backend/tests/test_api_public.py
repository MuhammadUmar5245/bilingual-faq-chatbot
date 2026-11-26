"""Integration tests - public chatbot API (FR-01, FR-03, FR-04, FR-05, FR-07, FR-10)."""
import pytest

from app.extensions import db
from models import FAQ, ConversationLog, Feedback
from tests.conftest import make_app


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json["status"] == "ok" and r.json["active_faqs"] >= 200


def test_chat_english_exact_question(client, app):
    with app.app_context():
        faq = db.session.get(FAQ, 72)
    r = client.post("/api/chat", json={"message": faq.question_en, "session_id": "t1"})
    j = r.json
    assert r.status_code == 200
    assert j["faq_id"] == 72 and j["method"] == "tfidf" and not j["fallback"]
    assert j["answer"] == faq.answer and j["lang"] == "en" and j["answer_lang"] == "en"
    assert j["category"] == "Fees" and j["log_id"] and j["response_ms"] < 2000  # FR-04


def test_chat_arabic_returns_arabic_answer(client, app):
    with app.app_context():
        faq = db.session.get(FAQ, 150)
    j = client.post("/api/chat", json={"message": faq.question_ar}).json
    assert j["lang"] == "ar" and j["answer"] == faq.answer_ar and j["answer_lang"] == "ar"
    assert j["answer_alt"] == faq.answer and j["category_ar"]


def test_chat_fallback_includes_contact(client):  # FR-05
    j = client.post("/api/chat", json={"message": "who won the football match yesterday"}).json
    assert j["fallback"] is True and j["faq_id"] is None and j["method"] == "fallback"
    assert {"phone", "email", "office", "hours"} <= set(j["contact"])
    assert j["category"]  # FR-02: classified even when unanswered


def test_chat_fallback_arabic_text(client):
    j = client.post("/api/chat", json={"message": "من فاز في مباراة كرة القدم"}).json
    assert j["fallback"] and "عذراً" in j["answer"]


def test_chat_generates_session_id_when_missing(client):
    assert len(client.post("/api/chat", json={"message": "fees"}).json["session_id"]) >= 16


@pytest.mark.parametrize("body,status", [
    ({}, 400),
    ({"message": ""}, 400),
    ({"message": "   "}, 400),
    ({"message": 123}, 400),
    ({"message": "x" * 501}, 400),
])
def test_chat_validation(client, body, status):
    r = client.post("/api/chat", json=body)
    assert r.status_code == status and "error" in r.json


def test_chat_rejects_non_json(client):
    r = client.post("/api/chat", data="message=hi", content_type="application/x-www-form-urlencoded")
    assert r.status_code == 400


def test_every_query_is_logged(client, app):  # FR-07
    client.post("/api/chat", json={"message": "What is the General Foundation Programme?", "session_id": "log-test"})
    client.post("/api/chat", json={"message": "tell me a joke", "session_id": "log-test"})
    with app.app_context():
        logs = ConversationLog.query.filter_by(session_id="log-test").order_by(ConversationLog.id).all()
        assert len(logs) == 2
        assert logs[0].matched_faq_id == 6 and logs[0].method == "tfidf" and logs[0].confidence > 0.75
        assert logs[0].detected_lang == "en" and logs[0].response_ms > 0 and logs[0].category == "Admissions"
        assert logs[1].method == "fallback" and logs[1].matched_faq_id is None


def test_feedback(client, app):
    log_id = client.post("/api/chat", json={"message": "hostel fees"}).json["log_id"]
    r = client.post("/api/feedback", json={"log_id": log_id, "helpful": True})
    assert r.status_code == 201
    with app.app_context():
        assert Feedback.query.filter_by(log_id=log_id).one().helpful is True


@pytest.mark.parametrize("body,status", [
    ({"log_id": 999999, "helpful": True}, 404),
    ({"log_id": "1", "helpful": True}, 400),
    ({"log_id": 1, "helpful": "yes"}, 400),
    ({}, 400),
])
def test_feedback_validation(client, body, status):
    assert client.post("/api/feedback", json=body).status_code == status


def test_categories_with_counts(client):
    cats = client.get("/api/categories").json
    assert len(cats) == 6 and all(c["faq_count"] == 35 for c in cats)


def test_popular_defaults_to_one_per_category(client):
    items = client.get("/api/faqs/popular?limit=6").json
    assert len({i["category"] for i in items}) == 6


def test_popular_ranks_by_usage(client):
    for _ in range(3):
        client.post("/api/chat", json={"message": "What is the General Foundation Programme?"})
    assert client.get("/api/faqs/popular").json[0]["id"] == 6


def test_popular_by_category_in_arabic(client):
    items = client.get("/api/faqs/popular?category_id=3&lang=ar&limit=50").json
    assert len(items) == 35 and all(i["category"] == "Fees" for i in items)
    assert items[0]["question"] == items[0]["question_ar"]


def test_contact_endpoint(client):
    assert client.get("/api/contact").json["email"]


def test_unknown_route_returns_json_404(client):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404 and "error" in r.json


def test_rate_limit_on_chat():  # NF-05 abuse protection
    app = make_app(CHAT_RATE_LIMIT="3 per minute")
    c = app.test_client()
    codes = [c.post("/api/chat", json={"message": "fees"}).status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200] and codes[3:] == [429, 429]
