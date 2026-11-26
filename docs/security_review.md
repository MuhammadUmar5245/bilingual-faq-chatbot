# Security review (NF-05)

NF-05: *The admin dashboard shall require authenticated login; all passwords shall be stored
using bcrypt hashing.* This review lists each control, where it is implemented, and the test
that checks it. All listed tests pass (see `backend/tests/` and [`test_cases.md`](test_cases.md)).

| # | Control | Implementation | Evidence (test) | Result |
|---|---|---|---|---|
| S1 | Passwords stored as bcrypt hashes (cost 12, random salt) — never plain text | `models.AdminUser.set_password` (`bcrypt.hashpw`, `gensalt(rounds=12)`) | `test_models.py::test_password_is_bcrypt_hashed`, `test_same_password_gives_different_hashes` | Pass |
| S2 | Every admin endpoint requires an authenticated session | `@login_required` on all routes in `routes/admin.py`; JSON 401 handler in `app/__init__.py` | `test_api_admin.py::test_admin_routes_require_login` (17 endpoints), TC32 | Pass |
| S3 | Wrong credentials rejected with a generic message (no user enumeration) | `routes/admin.py::login` returns the same 401 for unknown user and wrong password | `test_login_wrong_password`, `test_login_unknown_user`, TC33 | Pass |
| S4 | Brute-force protection on login | Flask-Limiter `10 per minute` on `POST /api/admin/login` | `test_login_rate_limited` | Pass |
| S5 | Flooding protection on the public chat endpoint | Flask-Limiter on `POST /api/chat` (`CHAT_RATE_LIMIT`, default 60/min per IP) | `test_rate_limit_on_chat`, TC39 | Pass |
| S6 | SQL injection prevented | All queries use the SQLAlchemy ORM with bound parameters; no string-built SQL anywhere | `test_sql_injection_on_login_fails` (4 payloads), `test_sql_injection_in_search_is_harmless`, `test_sql_injection_in_chat_is_treated_as_text`, TC34 | Pass |
| S7 | Session cookie hardening | `SESSION_COOKIE_HTTPONLY`, `SameSite=Lax`, signed with `SECRET_KEY` from the environment | `test_session_cookie_is_httponly` | Pass |
| S8 | Password strength rule and re-authentication on change | `PUT /api/admin/password` requires the current password; new one ≥ 8 chars with letters and digits | `test_change_password`, TC35 | Pass |
| S9 | Logout invalidates the session | `logout_user()` | `test_logout_ends_session` | Pass |
| S10 | Input validation and size limits | Chat message ≤ 500 chars; FAQ fields ≤ 4000 chars; type checks; CSV import: `.csv` only, UTF-8, ≤ 5 MB | `test_chat_validation`, `test_create_faq_requires_fields`, `test_import_rejects_invalid_files` | Pass |
| S11 | No internal errors leaked | Global error handlers return JSON `{"error": ...}` without stack traces | `test_unknown_route_returns_json_404` | Pass |
| S12 | XSS-safe rendering | React escapes all text; answers are rendered as text (no `dangerouslySetInnerHTML`); widget isolated in a Shadow DOM | Code review (`frontend/widget/src/Widget.jsx`) | Pass |
| S13 | Secrets from environment, not source code | `SECRET_KEY`, DB password and default admin password read from env / `.env` (`.env` is git-ignored) | Code review (`app/config.py`, `docker-compose.yml`) | Pass |
| S14 | Containers run as non-root; security headers | API image runs as `appuser`; Nginx adds `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` | `backend/Dockerfile`, `frontend/nginx.conf` | Pass |
| S15 | Retrieval-only answers (no generated / hallucinated content) | The chatbot only returns stored FAQ answers or the fixed fallback text | Design (`nlp/hybrid.py`) | Pass |

## Residual risks and recommendations
- **HTTPS**: the prototype serves HTTP. In production, terminate TLS at Nginx (or a load balancer)
  and set `SESSION_COOKIE_SECURE=True`.
- **Default admin password**: `Admin@12345` is for demonstration only; change it on first login
  (Settings → Change password) or set `ADMIN_PASSWORD` before the first start.
- **CSRF**: admin requests are JSON with a `SameSite=Lax` cookie and same-origin hosting, which blocks
  classic cross-site form posts; a CSRF token would add defence in depth.
- **Rate limits are per IP** and stored in memory per worker; a shared store (e.g. Redis) would be
  needed for exact limits across several API containers.
- **Single admin role**: there is no role separation or audit trail of which staff member changed an FAQ.
