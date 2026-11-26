"""Unit tests - data model, seeding and password hashing (FR-09, NF-05)."""
from app.extensions import db
from models import FAQ, AdminUser, Category, ConversationLog, Feedback, Setting


def test_seed_creates_six_categories(app):
    with app.app_context():
        names = {c.name_en for c in Category.query.all()}
    assert names == {"Admissions", "Registration", "Fees", "Academic Programmes", "Examinations", "Student Services"}


def test_seed_loads_at_least_200_faqs(app):  # FR-09
    with app.app_context():
        assert FAQ.query.count() >= 200
        assert FAQ.query.filter(FAQ.question_ar != "").count() == FAQ.query.count()


def test_default_settings_seeded(app):
    with app.app_context():
        assert float(Setting.get("confidence_threshold")) == 0.75
        assert Setting.get("contact_email")


def test_password_is_bcrypt_hashed(app):  # NF-05
    with app.app_context():
        user = AdminUser.query.first()
        assert user.password_hash.startswith("$2b$12$")
        assert "Admin@12345" not in user.password_hash
        assert user.check_password("Admin@12345")
        assert not user.check_password("admin@12345")


def test_same_password_gives_different_hashes(app):
    with app.app_context():
        a, b = AdminUser(username="a"), AdminUser(username="b")
        a.set_password("Secret123")
        b.set_password("Secret123")
        assert a.password_hash != b.password_hash  # random salt


def test_check_password_with_corrupt_hash(app):
    with app.app_context():
        u = AdminUser(username="x", password_hash="not-a-hash")
        assert not u.check_password("anything")


def test_setting_get_set(app):
    with app.app_context():
        Setting.set("demo_key", 0.5)
        db.session.commit()
        assert Setting.get("demo_key") == "0.5"
        Setting.set("demo_key", "x")
        db.session.commit()
        assert Setting.get("demo_key") == "x"
        assert Setting.get("missing", "default") == "default"


def test_faq_to_dict_contains_category(app):
    with app.app_context():
        d = FAQ.query.first().to_dict()
        assert d["category"] == "Admissions" and d["category_ar"] == "القبول" and d["is_active"] is True


def test_log_and_feedback_relationship(app):
    with app.app_context():
        log = ConversationLog(session_id="s", query_text="q", detected_lang="en", matched_faq_id=1,
                              confidence=0.8, method="tfidf", response_ms=12.3)
        db.session.add(log)
        db.session.commit()
        db.session.add(Feedback(log_id=log.id, helpful=False))
        db.session.commit()
        d = log.to_dict()
        assert d["helpful"] is False and d["matched_question"] and d["method"] == "tfidf"
