"""Integration tests - admin API (FR-06, FR-07, NF-05, NF-06) including security checks."""
import io

import pytest

from app.extensions import db
from models import FAQ, AdminUser, ConversationLog

PROTECTED = [
    ("get", "/api/admin/me"), ("post", "/api/admin/logout"), ("get", "/api/admin/faqs"),
    ("post", "/api/admin/faqs"), ("get", "/api/admin/faqs/1"), ("put", "/api/admin/faqs/1"),
    ("delete", "/api/admin/faqs/1"), ("patch", "/api/admin/faqs/1/toggle"), ("post", "/api/admin/faqs/import"),
    ("get", "/api/admin/faqs/export"), ("get", "/api/admin/logs"), ("get", "/api/admin/unanswered"),
    ("get", "/api/admin/stats"), ("get", "/api/admin/settings"), ("put", "/api/admin/settings"),
    ("put", "/api/admin/password"), ("get", "/api/admin/categories"),
]

NEW_FAQ = {
    "question_en": "Is there a swimming pool on campus?",
    "question_ar": "هل يوجد مسبح في الحرم الجامعي؟",
    "answer": "Yes, the indoor pool is open from 6 am to 9 pm.",
    "answer_ar": "نعم، المسبح الداخلي مفتوح من 6 صباحاً حتى 9 مساءً.",
    "category_id": 6,
    "keywords": "pool, swimming, مسبح",
}


# ------------------------------------------------------------------ authentication (NF-05)
@pytest.mark.parametrize("method,url", PROTECTED)
def test_admin_routes_require_login(client, method, url):
    r = getattr(client, method)(url, json={})
    assert r.status_code == 401 and r.json["error"] == "authentication required"


def test_login_wrong_password(client):
    r = client.post("/api/admin/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_login_unknown_user(client):
    assert client.post("/api/admin/login", json={"username": "ghost", "password": "x"}).status_code == 401


def test_login_success_sets_last_login(client, app):
    r = client.post("/api/admin/login", json={"username": "admin", "password": "Admin@12345"})
    assert r.status_code == 200 and r.json["user"]["last_login"]
    assert client.get("/api/admin/me").json["user"]["username"] == "admin"


def test_session_cookie_is_httponly(client):
    r = client.post("/api/admin/login", json={"username": "admin", "password": "Admin@12345"})
    cookie = r.headers.get("Set-Cookie", "")
    assert "HttpOnly" in cookie and "SameSite=Lax" in cookie


def test_logout_ends_session(admin):
    assert admin.post("/api/admin/logout").status_code == 200
    assert admin.get("/api/admin/faqs").status_code == 401


def test_login_rate_limited(client):
    codes = [client.post("/api/admin/login", json={"username": "admin", "password": "bad"}).status_code
             for _ in range(12)]
    assert 429 in codes


@pytest.mark.parametrize("payload", [
    "' OR '1'='1", "admin'--", "admin\" OR \"\"=\"", "'; DROP TABLE admin_users; --",
])
def test_sql_injection_on_login_fails(client, app, payload):
    r = client.post("/api/admin/login", json={"username": payload, "password": payload})
    assert r.status_code == 401
    with app.app_context():
        assert AdminUser.query.count() == 1  # table intact


def test_sql_injection_in_search_is_harmless(admin, app):
    r = admin.get("/api/admin/faqs", query_string={"q": "x' OR 1=1; DROP TABLE faqs; --"})
    assert r.status_code == 200 and r.json["total"] == 0
    with app.app_context():
        assert FAQ.query.count() == 210


def test_sql_injection_in_chat_is_treated_as_text(client, app):
    r = client.post("/api/chat", json={"message": "'; DELETE FROM faqs; --"})
    assert r.status_code == 200
    with app.app_context():
        assert FAQ.query.count() == 210


# ------------------------------------------------------------------ FAQ management (FR-06)
def test_list_faqs_paginated(admin):
    j = admin.get("/api/admin/faqs?per_page=15&page=2").json
    assert j["total"] == 210 and j["page"] == 2 and len(j["items"]) == 15 and j["pages"] == 14


def test_search_and_filter(admin):
    j = admin.get("/api/admin/faqs", query_string={"q": "hostel", "category_id": 6}).json
    assert j["total"] >= 3 and all(i["category"] == "Student Services" for i in j["items"])
    j = admin.get("/api/admin/faqs", query_string={"q": "السكن"}).json
    assert j["total"] >= 1


def test_create_faq_and_chatbot_uses_it_immediately(admin, client):  # FR-06 + index rebuild
    r = admin.post("/api/admin/faqs", json=NEW_FAQ)
    assert r.status_code == 201 and r.json["answer_lang"] == "en+ar"
    j = client.post("/api/chat", json={"message": NEW_FAQ["question_en"]}).json
    assert j["faq_id"] == r.json["id"]


@pytest.mark.parametrize("missing", ["question_en", "answer", "category_id"])
def test_create_faq_requires_fields(admin, missing):
    body = {k: v for k, v in NEW_FAQ.items() if k != missing}
    assert admin.post("/api/admin/faqs", json=body).status_code == 400


def test_create_faq_rejects_bad_category(admin):
    assert admin.post("/api/admin/faqs", json={**NEW_FAQ, "category_id": 99}).status_code == 400


def test_update_faq(admin, client):
    r = admin.put("/api/admin/faqs/11", json={"answer": "Updated answer about placement tests."})
    assert r.status_code == 200 and r.json["answer"].startswith("Updated")
    j = client.post("/api/chat", json={"message": "Is there an entrance or placement test?"}).json
    assert j["answer"] == "Updated answer about placement tests."


def test_update_cannot_blank_question(admin):
    assert admin.put("/api/admin/faqs/12", json={"question_en": ""}).status_code == 400


def test_toggle_disables_faq_in_chatbot(admin, client):
    q = "Can I rent a locker on campus?"
    assert client.post("/api/chat", json={"message": q}).json["faq_id"] == 210
    assert admin.patch("/api/admin/faqs/210/toggle").json["is_active"] is False
    assert client.post("/api/chat", json={"message": q}).json["faq_id"] != 210
    assert admin.patch("/api/admin/faqs/210/toggle").json["is_active"] is True


def test_delete_faq_keeps_logs(admin, client, app):
    client.post("/api/chat", json={"message": "Can I rent a locker on campus?"})
    assert admin.delete("/api/admin/faqs/210").status_code == 200
    assert admin.get("/api/admin/faqs/210").status_code == 404
    with app.app_context():
        log = ConversationLog.query.order_by(ConversationLog.id.desc()).first()
        assert log.matched_faq_id is None


def test_missing_faq_returns_404(admin):
    assert admin.put("/api/admin/faqs/9999", json={"answer": "x"}).status_code == 404
    assert admin.patch("/api/admin/faqs/9999/toggle").status_code == 404
    assert admin.delete("/api/admin/faqs/9999").status_code == 404


def test_import_csv(admin, app):
    csv_text = ("question_en,question_ar,answer,category,keywords\n"
                "Is parking free?,هل المواقف مجانية؟,Yes it is free.,Student Services,parking\n"
                "Bad row,,,Fees,\n"
                "Unknown cat,,Answer,Sports,\n")
    r = admin.post("/api/admin/faqs/import", data={"file": (io.BytesIO(csv_text.encode()), "faqs.csv")},
                   content_type="multipart/form-data")
    assert r.status_code == 201 and r.json["imported"] == 1 and r.json["skipped"] == 2
    with app.app_context():
        assert FAQ.query.count() == 211


def test_import_replace_mode(admin, app):
    csv_text = "question_en,answer,category\nOnly question?,Only answer,Fees\n"
    admin.post("/api/admin/faqs/import", data={"file": (io.BytesIO(csv_text.encode()), "f.csv"), "mode": "replace"},
               content_type="multipart/form-data")
    with app.app_context():
        assert FAQ.query.filter_by(is_active=True).count() == 1


@pytest.mark.parametrize("filename,content", [
    ("faqs.txt", b"question_en,answer,category\n"),
    ("faqs.csv", b"wrong,columns\n1,2\n"),
    ("faqs.csv", "question_en,answer,category\nق,ج,Fees\n".encode("utf-16")),
])
def test_import_rejects_invalid_files(admin, filename, content):
    r = admin.post("/api/admin/faqs/import", data={"file": (io.BytesIO(content), filename)},
                   content_type="multipart/form-data")
    assert r.status_code == 400


def test_export_csv(admin):
    r = admin.get("/api/admin/faqs/export")
    text = r.data.decode("utf-8-sig")
    assert r.status_code == 200 and "attachment" in r.headers["Content-Disposition"]
    assert text.splitlines()[0].startswith("id,question_en,question_ar,answer")
    assert len(text.strip().splitlines()) >= 211


# ------------------------------------------------------------------ logs, unanswered, stats (FR-07)
def test_logs_filters(admin, client):
    client.post("/api/chat", json={"message": "What is the General Foundation Programme?"})
    client.post("/api/chat", json={"message": "ما هي عاصمة فرنسا"})
    assert admin.get("/api/admin/logs").json["total"] == 2
    assert admin.get("/api/admin/logs?lang=ar").json["total"] == 1
    assert admin.get("/api/admin/logs?method=tfidf").json["total"] == 1
    assert admin.get("/api/admin/logs?q=Foundation").json["total"] == 1
    assert admin.get("/api/admin/logs?date_from=2000-01-01&date_to=2999-01-01").json["total"] == 2
    assert admin.get("/api/admin/logs?date_from=2999-01-01").json["total"] == 0


def test_unanswered_includes_fallback_and_thumbs_down(admin, client):
    client.post("/api/chat", json={"message": "tell me a joke"})
    log_id = client.post("/api/chat", json={"message": "What is the General Foundation Programme?"}).json["log_id"]
    client.post("/api/feedback", json={"log_id": log_id, "helpful": False})
    j = admin.get("/api/admin/unanswered").json
    assert j["total"] == 2 and {i["reason"] for i in j["items"]} == {"fallback", "unhelpful"}
    assert admin.get("/api/admin/unanswered?type=fallback").json["total"] == 1
    assert admin.get("/api/admin/unanswered?type=unhelpful").json["total"] == 1


def test_stats(admin, client):
    client.post("/api/chat", json={"message": "What is the General Foundation Programme?", "session_id": "a"})
    client.post("/api/chat", json={"message": "tell me a joke", "session_id": "b"})
    s = admin.get("/api/admin/stats?days=7").json
    assert s["total_queries"] == 2 and s["resolution_rate"] == 0.5 and s["sessions"] == 2
    assert len(s["per_day"]) == 7 and s["per_day"][-1]["count"] == 2
    assert s["per_method"] == {"tfidf": 1, "fallback": 1} and s["faqs_active"] == 210
    assert s["top_faqs"][0]["id"] == 6


# ------------------------------------------------------------------ settings & password
def test_settings_update_applies_to_chat(admin, client):
    q = "What is the General Foundation Programme?"
    assert client.post("/api/chat", json={"message": q}).json["method"] == "tfidf"
    s = admin.put("/api/admin/settings", json={"confidence_threshold": 1.0, "contact_phone": "+968 9999 0000"}).json
    assert s["confidence_threshold"] == 1.0 and s["contact_phone"] == "+968 9999 0000"
    j = client.post("/api/chat", json={"message": q}).json  # TF-IDF can no longer reach 1.0 -> fallback (no SBERT)
    assert j["method"] == "fallback" and j["contact"]["phone"] == "+968 9999 0000"


@pytest.mark.parametrize("body", [{"confidence_threshold": 1.5}, {"confidence_threshold": "abc"}, {"unknown": 1}])
def test_settings_validation(admin, body):
    assert admin.put("/api/admin/settings", json=body).status_code == 400


def test_change_password(admin, client):
    assert admin.put("/api/admin/password", json={"current_password": "wrong", "new_password": "NewPass123"}).status_code == 403
    assert admin.put("/api/admin/password", json={"current_password": "Admin@12345", "new_password": "short"}).status_code == 400
    assert admin.put("/api/admin/password", json={"current_password": "Admin@12345", "new_password": "NewPass123"}).status_code == 200
    admin.post("/api/admin/logout")
    assert client.post("/api/admin/login", json={"username": "admin", "password": "Admin@12345"}).status_code == 401
    assert client.post("/api/admin/login", json={"username": "admin", "password": "NewPass123"}).status_code == 200
