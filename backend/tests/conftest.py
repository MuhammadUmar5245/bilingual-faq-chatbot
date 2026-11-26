"""Shared fixtures: an isolated app with an in-memory SQLite database seeded from data/faqs_seed.csv."""
import pytest

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.nlp_service import reset_engine


def make_app(**overrides):
    cfg = type("Cfg", (TestConfig,), overrides)
    reset_engine()
    app = create_app(cfg)
    return app


@pytest.fixture()
def app():
    app = make_app()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()
    reset_engine()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def admin(client):
    """A test client already logged in as the default admin."""
    r = client.post("/api/admin/login", json={"username": "admin", "password": "Admin@12345"})
    assert r.status_code == 200
    return client
