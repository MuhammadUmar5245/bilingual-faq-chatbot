"""Application configuration loaded from environment variables (.env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent
load_dotenv(PROJECT_DIR / ".env")

DATA_DIR = Path(os.getenv("DATA_DIR", PROJECT_DIR / "data"))


def _sqlite_default() -> str:
    instance = BACKEND_DIR / "instance"
    instance.mkdir(exist_ok=True)
    return f"sqlite:///{(instance / 'faq.db').as_posix()}"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL") or _sqlite_default()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False

    # Session cookie hardening (NF-05)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True

    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@12345")

    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))
    SBERT_THRESHOLD = float(os.getenv("SBERT_THRESHOLD", "0.35"))
    SBERT_MODEL = os.getenv("SBERT_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
    FUSION_WEIGHT = float(os.getenv("FUSION_WEIGHT", "0.6"))
    ENABLE_SBERT = os.getenv("ENABLE_SBERT", "1") == "1"

    CHAT_RATE_LIMIT = os.getenv("CHAT_RATE_LIMIT", "60 per minute")
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_HEADERS_ENABLED = True

    SERVE_FRONTEND = os.getenv("SERVE_FRONTEND", "1") == "1"  # local runs only; Nginx serves it in Docker

    FAQ_SEED_CSV = DATA_DIR / "faqs_seed.csv"
    AUTO_SEED = os.getenv("AUTO_SEED", "1") == "1"

    CONTACT = {
        "office": os.getenv("COLLEGE_NAME", "Student Services Office"),
        "phone": os.getenv("CONTACT_PHONE", "+968 2400 0000"),
        "email": os.getenv("CONTACT_EMAIL", "info@college.edu.om"),
        "hours": os.getenv("CONTACT_HOURS", "Sun-Thu, 8:00-15:00"),
    }


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    ENABLE_SBERT = False
    WARMUP_NLP = False
    SERVE_FRONTEND = False
    CHAT_RATE_LIMIT = "1000 per minute"
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "Admin@12345"
