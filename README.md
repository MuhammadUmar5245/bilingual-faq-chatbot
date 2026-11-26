# College FAQ Chatbot for Oman (GIS6001)

Bilingual (English + Arabic) retrieval-based FAQ chatbot for colleges in Oman. Students ask
questions in natural language through an embeddable chat widget; the system returns the best
matching **verified** answer from the college FAQ knowledge base (it never generates answers).
Staff maintain the FAQs through an admin dashboard without programming.

| | |
|---|---|
| Backend | Python 3.10, Flask 3, Flask-SQLAlchemy, Flask-Login, Flask-Limiter, bcrypt |
| NLP | TF-IDF (scikit-learn) → sentence-BERT `paraphrase-multilingual-MiniLM-L12-v2` fallback with score fusion; langdetect; NLTK; custom Arabic normaliser |
| Frontend | React 18 (Vite) + Axios — chat widget (`widget.js`) and admin dashboard |
| Database | PostgreSQL 14 (Docker) / SQLite (local development and tests) |
| Deployment | Docker Compose: `db`, `api` (gunicorn), `web` (Nginx) |

> **Sample data.** `data/faqs_seed.csv` contains 210 realistic but **illustrative** FAQs —
> they must be verified with or replaced by real college FAQs (see `data/README.md`).

## Quick start (Docker)

```bash
cp .env.example .env          # optional — defaults work for a local demo
docker compose up --build
```

| URL | What |
|---|---|
| http://localhost:8088 | Demo college website with the embedded chatbot |
| http://localhost:8088/admin/ | Admin dashboard |
| http://localhost:8088/api/health | API health check |

**Default admin login:** `admin` / `Admin@12345` (set `ADMIN_USERNAME` / `ADMIN_PASSWORD` in
`.env` before the first start, or change the password in Settings).

The first build downloads PyTorch (CPU) and the SBERT model (~3 GB API image); later starts are
quick. The web port can be changed with `WEB_PORT` (default 8088). The database is stored in the
`pgdata` volume; `docker compose down -v` resets it to the seed data.

Embed the chatbot in any website with one tag:

```html
<script src="http://localhost:8088/widget.js" data-title="College Assistant" data-lang="en" defer></script>
```

## Local development (without Docker)

```bash
py -3.10 -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements-dev.txt     # Linux/macOS: .venv/bin/python
cd frontend/widget && npm install && npm run build && cd ../admin && npm install && npm run build && cd ../..
cd backend && ../.venv/Scripts/python wsgi.py
```

Flask then serves everything on http://localhost:5000 (`/`, `/widget.js`, `/admin/`, `/api/*`)
with a SQLite database in `backend/instance/`. For frontend hot-reload run `npm run dev` in
`frontend/widget` (port 5173) or `frontend/admin` (port 5174); both proxy `/api` to port 5000.

## Re-running the evaluation and tests

All commands from `backend/` using the project virtualenv (`../.venv/Scripts/python`):

| Command | Output |
|---|---|
| `python -m nlp.evaluate` | Keyword vs TF-IDF vs SBERT vs Hybrid on `data/test_queries.csv` → `docs/results/` (tables, confusion matrix, threshold sweep) |
| `python -m pytest --cov=app --cov=nlp --cov=models --cov=routes` | 138 unit + integration tests with coverage |
| `python -m tests.blackbox.run_test_cases --base http://localhost:8088` | 39 black-box test cases against the running system → `docs/test_cases.md` / `.xlsx` |
| `python -m tests.perf.load_test --base http://localhost:8088` | 50-concurrent-user load test (NF-01) → `docs/results/performance.md` (start the API with `CHAT_RATE_LIMIT="100000 per minute"` first; add `--duration 60` for a timed run and `--edit-at 30 --tag rebuild` for LT-3) |

From the project root:

| Command | Output |
|---|---|
| `python diagrams/render.py` | Renders the 13 Mermaid diagrams to PNG (needs `cd diagrams/.tools && npm install` once) |
| `python screenshots/capture_screenshots.py` | Captures the 33 screenshots (fresh Docker database recommended) |
| `python docs/build_code_docs.py` | Regenerates `docs/important_code.md` and `docs/code_listing/` |
| `python docs/survey/survey_analysis.py <responses.csv>` | Survey statistics and charts (real responses only) |

## Results (from the latest runs)

| Measure | Result | Requirement |
|---|---|---|
| Hybrid FAQ-retrieval accuracy, held-out split (180 queries) | 85.6 % | objective ≥ 85 % |
| Linear SVM intent (category) accuracy, held-out in-scope queries (164) | 88.4 % | NF-02 ≥ 85 % |
| Hybrid accuracy, all 361 test queries | 87.3 % | – |
| p95 response time, 50 concurrent users, 60 s | 535 ms (529 ms with an FAQ edit mid-run) | NF-01 < 2 s |
| pytest | 151 passed, 96 % coverage | – |
| Black-box test cases | 39 / 43 passed (near-miss cases TC40–TC43 fail) | ≥ 30 |

Details: `docs/results/results.md`, `docs/results/tuning_log.md`, `docs/results/performance.md`,
`docs/test_cases.md`, `PROGRESS.md`.

## Repository layout

```
backend/    Flask API (app/, routes/, models/), NLP (nlp/), tests (tests/), Dockerfile
frontend/   widget/ (embeddable chat), admin/ (dashboard), nginx.conf, Dockerfile
data/       faqs_seed.csv (210 FAQs), test_queries.csv (361 held-out queries)
docs/       requirements, results, test cases, manuals, questionnaire, code listing, demo site
diagrams/   Mermaid sources (src/) and rendered PNGs for Chapters 3–4
screenshots/  33 screenshots of every function + capture script
```
