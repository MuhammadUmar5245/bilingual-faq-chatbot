# Progress

## Phase 1 — Project setup + database ✅
- git repo, `.gitignore`, `.env.example`
- Flask app factory (`backend/app/`), config from env, SQLAlchemy models (`backend/models/`)
- Tables: categories, faqs, conversation_logs, feedback, admin_users (bcrypt), settings
- Auto-seed on start: 6 categories, default settings (threshold 0.75), default admin from env
- Python 3.10 virtualenv at `.venv` (Python 3.14 is not supported by torch/sentence-transformers)

## Phase 2 — FAQ dataset ✅
- `data/faqs_seed.csv`: 210 bilingual FAQs (35 × 6 categories), EN + MSA Arabic questions and answers — SAMPLE DATA
- `data/test_queries.csv`: 361 held-out queries (244 EN, 117 AR, 32 out-of-scope), all 210 FAQs covered
- Added optional `answer_ar` column so Arabic users get Arabic answers (CSV import still works without it)

## Phase 3 — NLP pipeline ✅
- `backend/nlp/`: preprocess (custom Arabic normaliser + light stemmer; CAMeL Tools rejected because it
  downgrades transformers/tokenizers needed by sentence-transformers), language (script rule + langdetect),
  tfidf_retriever (word + char n-grams), sbert_retriever (cached embeddings), classifier (category SVM, FR-02),
  hybrid (TF-IDF ≥ 0.75 → SBERT stage with score fusion → fallback)
- `python -m nlp.evaluate` (from backend/) → docs/results/: results.md/csv, per-language, per-category,
  per-variation, confusion matrix, threshold sweep, method comparison. Tuning split = odd ids, held-out = even ids.
- **Hybrid accuracy: 85.6 % held-out / 87.3 % full set** (held-out: TF-IDF 81.1 %, SBERT 78.3 %,
  spec hybrid 78.9 %, keyword 63.9 %). Language detection 100 %, category classifier 85.4 %.
- What changed to reach 85 %: docs/results/tuning_log.md (score fusion, Arabic stemmer fixes, Arabic keywords)

## Phase 4 — Flask REST API ✅
- Public: POST /api/chat (validation, rate limit, logging FR-07, Arabic answers for Arabic queries, fallback with
  contact details FR-05, "did you mean" suggestions), GET /api/categories, GET /api/faqs/popular
  (?category_id), POST /api/feedback, GET /api/health, GET /api/contact
- Admin (Flask-Login session): login/logout/me, FAQ CRUD + toggle + CSV import/export, logs (filters +
  pagination), unanswered (fallback + thumbs-down), stats, settings (thresholds + contact), change password
- Index auto-rebuild: `faq_version` setting bumped on every FAQ change; each worker rebuilds when stale
- Added `conversation_logs.category` (FR-02 category of each query, used for per-category stats)
- Known limitation: some out-of-scope queries score just above the tuned 0.35 SBERT-stage threshold
  (e.g. "what is the weather today" → cyclone/exam FAQ); OOS rejection on the test set is 87.5 %

## Phase 5 — React frontend ✅
- `frontend/widget`: React 18 + Axios chat widget built as one self-contained `widget.js` (IIFE, Shadow DOM
  style isolation). EN/AR toggle with RTL, auto language switch, typing indicator, category chips, popular
  questions, answer card (category + confidence), fallback contact card + "did you mean", thumbs feedback,
  last-5 history (FR-10), clear chat, full-screen mobile layout
- `docs/demo-college-site.html`: fictional college site embedding the widget with one `<script>` tag (FR-08)
- `frontend/admin`: dashboard (login, overview KPIs + SVG charts, FAQ CRUD/toggle/search/filter/pagination,
  CSV import/export, logs, unanswered + "create FAQ from this", thresholds, contact details, password)
- Local run without Docker: Flask serves `/` (demo site), `/widget.js`, `/admin/` when `frontend/*/dist` exist
- `docs/functions_list.md`: 33 functions mapped to FR/NF IDs

## Deployment (NF-04) ✅
- `docker-compose.yml` (db: postgres:14-alpine, api: python:3.10-slim + gunicorn, web: nginx:1.27-alpine)
- `docker compose up --build` → http://localhost:8088 (demo college site + widget), /admin/ (dashboard)
- Web port is 8088 (8080 was taken by another local project); override with `WEB_PORT`
- SBERT model and NLTK stop-words are baked into the API image (runs offline)

## Phase 6 — Testing ✅
- pytest: 138 unit + integration tests, all passing; coverage 96 % of app/nlp/models/routes
  (`docs/results/coverage.txt`; evaluate.py excluded as an experiment script)
- Black-box: 39 test cases run automatically against the Docker deployment (API + Playwright UI) →
  `docs/test_cases.md` / `.xlsx`: **39/39 pass**. Earlier runs had 2 failures caused by the test script
  itself (TC18 unquoted comma in CSV test data; TC27 race with the typing indicator) — both fixed.
- Performance (NF-01): 50 concurrent users, no think time: **p95 802 ms, 0 errors** (PASS) after fixing CPU
  oversubscription (first run p95 3743 ms FAIL) — see `docs/results/performance_tuning.md`
- Security (NF-05): `docs/security_review.md`; traceability: `docs/traceability_matrix.md`

## Phase 7 — Dissertation assets ✅
- `diagrams/`: 13 diagrams — Mermaid sources (`src/*.mmd`, `diagram_sources.py`) + PNGs rendered locally
  (`render.py`): architecture, package, deployment, network, use case, activity, 2 sequence, DFD 0 and 1,
  ERD, class, NLP pipeline
- `screenshots/`: 33 PNGs captured by Playwright from the Docker deployment (EN + AR chat, mobile, every admin
  screen); captions in `docs/screenshots_index.md`. Dashboard numbers come from a 27-query demonstration
  session + the capture run itself — stated in the index, not presented as real student usage
- `docs/important_code.md` (5 snippets, generated from the real source) and `docs/code_listing/` (22 files)
- `docs/user_manual.md` (student guide, admin guide, installation) with screenshots
- `docs/questionnaire.md` (15 Likert items + staff items + NF-03 item + demographics + 2 open questions),
  `docs/survey/survey_responses_template.csv` (empty) and `docs/survey/survey_analysis.py`
  (descriptives, % agree, NF-03 check, Cronbach's α, by-group means, charts). No responses were invented.
- `README.md`: setup, default admin login, how to rerun evaluation/tests/load test/screenshots

## Revision 2026-11-20 — changes requested in Chapters_4-6_FAQ_Chatbot_revised.docx ✅
Revised chapters: `docs/Chapters_4-6_FAQ_Chatbot_revised.docx` (placeholders filled from real runs; survey and
staff-task tables 28/29 remain to be filled with real data).
- NF-02 is now judged on the **linear SVM intent (category) accuracy on held-out in-scope queries: 145/164 =
  88.4 %** (met); per category/language, precision/recall and `confusion_matrix_svm.png` from `nlp.evaluate`.
  TC37 now tests this. Retrieval accuracy (85.6 %) unchanged and reproduced exactly.
- `nlp.evaluate` also writes tuning-split sensitivity (`tuning_sensitivity.csv`), the margin-rule analysis
  (`margin_rule.csv`) and language-detection counts (en 244/244, ar 117/117).
- `nlp.check_keyword_leakage`: 0 keywords equal a held-out query; 4 English keywords equal tuning queries.
- Near-miss black-box cases TC40–TC43 added: **all four fail** (confident related-but-wrong answers). A margin
  rule was measured (m = 0.02 → held-out 83.9 %; m = 0.10 fixes TC40 → 76.1 %) and NOT adopted (user decision:
  report honestly). Black-box: **39/43 pass**.
- Query-log privacy: `app/privacy.py` masks e-mails and ≥ 7-digit numbers before logging; `flask purge-logs`
  removes query_text older than `LOG_RETENTION_DAYS` (365); widget welcome screen privacy notice (EN/AR).
  Retention purge is not scheduled automatically. pytest **151 passed**, coverage 96 %.
- Index rebuild: 2,636 ms mean for 210 FAQs (`nlp.rebuild_timing`, in container, `rebuild_timing.json`).
- Load tests: the 802 ms run lasted 4.7 s; a 60 s run gave p95 2006 ms (fail) due to uneven load between
  gunicorn workers → `--worker-connections` = threads added to `backend/Dockerfile`. **LT-2 (60 s): p95 535 ms**;
  **LT-3 (FAQ edit at 30 s): whole-run p95 529 ms**, but all workers rebuild together and requests in the
  ~8 s after the edit wait up to 8.3 s. All runs in `docs/results/performance_tuning.md`, `lt_runs/`.
- Still open: Chapter 3 FR-01 wording must state the ≥ 95 % language-detection target; questionnaire mode
  (online/paper); survey + staff tasks (Tables 28, 29); recapture Figure 12 if the privacy notice should show.

---

# Final summary

## What was built
A bilingual (English/Arabic) retrieval-only FAQ chatbot: Flask REST API with a hybrid NLP engine
(TF-IDF → sentence-BERT fallback with score fusion → fallback with contact details), an embeddable
React chat widget (`widget.js`, one script tag), a React admin dashboard for staff, PostgreSQL storage,
and a three-container Docker Compose deployment. 33 demonstrable functions (`docs/functions_list.md`).

## Metrics achieved (all produced by running the scripts)
| Measure | Result | Target |
|---|---|---|
| Hybrid retrieval accuracy — held-out split (180 queries) | **85.6 %** | NF-02 ≥ 85 % ✅ |
| Hybrid accuracy — all 361 test queries | 87.3 % | – |
| Baselines (held-out): keyword / TF-IDF / SBERT / spec hybrid | 63.9 / 81.1 / 78.3 / 78.9 % | – |
| Out-of-scope rejection (32 queries) | 87.5 % | – |
| Language detection (FR-01) / category classifier (FR-02) | 100 % / 85.4 % | – |
| p95 latency, 50 concurrent users, no think time | **802 ms**, 0 errors | NF-01 < 2 s ✅ |
| Single-query round trip (TC09) | 65–73 ms | FR-04 < 2 s ✅ |
| pytest | 138 passed, 96 % coverage | – |
| Black-box test cases (Docker deployment) | **39 / 39 passed** | ≥ 30 ✅ |
| Knowledge base | 210 FAQs (35 per category) | FR-09 ≥ 200 ✅ |

## Requirements not fully met / limitations (and why)
- **NF-03 (≥ 80 % rate the interface easy)** — not measured. It needs the 30-respondent survey with real
  students, applicants and staff; the questionnaire, empty template and analysis script are ready, but no
  responses were (or should be) fabricated.
- **FAQ data is SAMPLE data.** The 210 FAQs are realistic but illustrative (fees, dates, policies). FR-09 is met
  by count, but the knowledge base must be verified with or replaced by the participating colleges' FAQs;
  then regenerate `test_queries.csv` and rerun `nlp.evaluate`.
- **Accuracy validity:** the test queries and the Arabic keywords were written by the same author, so some
  vocabulary overlap is unavoidable (exact keyword/test duplicates were removed automatically). Accuracy on
  real student queries may be lower — re-measure with queries from the conversation logs.
- **Hybrid design changed from the Chapter 3 description:** the 0.75 TF-IDF threshold is kept, but very few
  queries reach it, so the SBERT stage fuses SBERT with the TF-IDF score (w = 0.6, threshold 0.35). Pure
  "TF-IDF then SBERT" reached only 78.9 %. Documented in `docs/results/tuning_log.md`.
- **Some out-of-scope queries are answered** (12.5 % of out-of-scope test queries got an FAQ, e.g. "what is the
  weather today" → the cyclone/exam FAQ); raising the SBERT-stage threshold trades this against more fallbacks.
- **Load test** ran on the development PC (28 CPUs) with 6 workers (~4 GB RAM); a smaller server needs fewer
  workers and a re-run. All simulated users shared one IP, so the chat rate limit was raised for that run.
- **Schema additions** beyond the specification: `faqs.answer_ar` (Arabic answers) and
  `conversation_logs.category` (FR-02 statistics). CSV format stays backward-compatible.
- **Prototype security gaps** (see `docs/security_review.md`): HTTP only (no TLS), single admin role, no CSRF
  token, in-memory per-worker rate limits.
- Web port is **8088**, not 8080, because 8080 was already used by another project on this PC (`WEB_PORT`).

## Notes for the report (from `START_HERE.md`)
- Update Table 11 FR-01 wording (see `docs/requirements.md`).
- Chapter 3 names "UTAS Muscat" in 3.2.2 but "Middle East College" in 1.5 — keep the college names consistent.
- Remove the stray line in Chapter 2 and verify the references listed in `START_HERE.md`.
