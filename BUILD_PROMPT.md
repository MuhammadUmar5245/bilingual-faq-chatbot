# BUILD PROMPT — paste this whole file's content into Claude Code

You are building my final-year Computer Science dissertation project (GIS6001):
"CHATBOT FOR FREQUENTLY ASKED QUESTIONS IN COLLEGES IN OMAN".

Read these first and treat them as the spec:
- CLAUDE.md (project rules)
- docs/dissertation_ch1-3.txt (my Chapters 1–3: objectives, scope, SRS)
- docs/requirements.md (FR-01…FR-10, NF-01…NF-06 — every one must be implemented and traceable)
- docs/report_template_structure.txt (what Chapters 4, 5 and the Appendices need)

Work in phases. After each phase: run it, fix errors, git commit, and update
PROGRESS.md. Ask me only if truly blocked.

=====================================================================
STACK (fixed — matches my SRS, do not change)
=====================================================================
- Backend: Python 3.10+, Flask 3, Flask-SQLAlchemy, Flask-Login, Flask-CORS, bcrypt
- NLP: scikit-learn (TF-IDF + cosine), sentence-transformers
  (paraphrase-multilingual-MiniLM-L12-v2 for EN+AR fallback), langdetect, NLTK.
  Arabic normalisation: remove diacritics/tatweel, unify alef/yaa/taa-marbuta forms,
  Arabic stopwords. Use CAMeL Tools if it installs cleanly, otherwise a custom
  normaliser — document whichever is used.
- Frontend: React 18 (Vite) + Axios. Two apps: chatbot widget + admin dashboard.
- DB: PostgreSQL 14 (Docker), SQLite for local dev/tests.
- Deployment: Docker Compose with 3 services: api (Flask+gunicorn),
  web (Nginx serving React), db (Postgres). One command: docker compose up --build

=====================================================================
PHASE 1 — Project setup + database
=====================================================================
Folders already exist (backend/, frontend/, data/, docs/, diagrams/, screenshots/).
git init, add .gitignore, .env.example.
Tables:
- categories (id, name_en, name_ar) — seed 6: Admissions, Registration, Fees,
  Academic Programmes, Examinations, Student Services
- faqs (id, question_en, question_ar, answer, answer_lang, category_id,
  keywords, is_active, created_at, updated_at)
- conversation_logs (id, session_id, query_text, detected_lang, matched_faq_id,
  confidence, method [tfidf|sbert|fallback], response_ms, created_at)
- feedback (id, log_id, helpful bool, created_at)
- admin_users (id, username, password_hash [bcrypt], last_login)
- settings (key, value) — e.g. confidence_threshold = 0.75

=====================================================================
PHASE 2 — FAQ dataset (FR-09)
=====================================================================
Create data/faqs_seed.csv with at least 210 bilingual FAQ entries (~35 per
category) realistic for Omani colleges (Gulf College, Middle East College,
Muscat College style): admission requirements, General Foundation Programme,
MoHERI scholarships, registration deadlines, fee payment, add/drop,
attendance, exam rules, resits, transcripts, hostel, transport, etc.
Columns: question_en, question_ar (proper Modern Standard Arabic), answer,
answer_lang, category, keywords.
Add a comment/README note: SAMPLE DATA — TO BE VERIFIED WITH COLLEGES.
Also create data/test_queries.csv with 300+ held-out test queries (paraphrases,
synonyms, misspellings, abbreviations, word reordering, Arabic + English,
plus ~30 out-of-scope queries) labelled with the expected faq_id or "NONE".
Test queries must NOT be copies of the seed questions.

=====================================================================
PHASE 3 — NLP pipeline (FR-01, FR-02, FR-03, FR-05, NF-02)
=====================================================================
backend/nlp/: preprocess.py, language.py, tfidf_retriever.py,
sbert_retriever.py, hybrid.py, classifier.py.
Flow: detect language → preprocess → TF-IDF cosine against question_en/ar →
if score >= threshold return it → else SBERT similarity → if still below
SBERT threshold return fallback message with college contact details (FR-05).
Return category, answer, confidence, method.
Cache embeddings; rebuild index automatically when FAQs change via admin.

Experiment script backend/nlp/evaluate.py (quasi-experiment from Ch.3):
compare keyword match vs TF-IDF vs SBERT vs Hybrid on test_queries.csv.
Output accuracy, precision, recall, F1, per-language accuracy, per-category
accuracy, confusion matrix PNG, threshold sweep chart (0.5–0.9) PNG, and a
results table as CSV + Markdown into docs/results/. Hybrid must reach >= 85%;
if not, tune preprocessing/thresholds and record what changed. Report the
real numbers honestly — never hard-code results.

=====================================================================
PHASE 4 — Flask REST API
=====================================================================
Public: POST /api/chat, GET /api/categories, GET /api/faqs/popular,
POST /api/feedback, GET /api/health
Admin (login required): POST /api/admin/login, POST /api/admin/logout,
GET/POST/PUT/DELETE /api/admin/faqs, PATCH /api/admin/faqs/<id>/toggle,
POST /api/admin/faqs/import (CSV), GET /api/admin/faqs/export,
GET /api/admin/logs (filter/paginate), GET /api/admin/unanswered,
GET /api/admin/stats, GET/PUT /api/admin/settings, PUT /api/admin/password
Log every query (FR-07). Input validation, rate limiting on /api/chat,
proper error JSON. Seed default admin from env vars.

=====================================================================
PHASE 5 — React frontend (FR-04, FR-06, FR-08, FR-10, NF-03)
=====================================================================
Chat widget: floating bubble, EN/AR toggle with full RTL layout, auto language
detection, typing indicator, category quick-reply chips, popular questions,
last 5 Q&A history in session (FR-10), thumbs up/down feedback, clear chat,
fallback card with contact info, mobile responsive. Build an embeddable
widget.js so any college site can add it with one <script> tag (FR-08) —
include docs/demo-college-site.html showing it embedded.
Admin dashboard: login, overview stats (total queries, resolution rate,
avg confidence, avg response time, queries per day/category charts),
FAQ table with search/filter/pagination, add/edit/disable/delete forms
(no code needed — FR-06), CSV import/export, conversation logs viewer,
unanswered queries list with "create FAQ from this" button, threshold
setting, change password. Clean professional design, college blue/teal theme.

The final system must have AT LEAST 20 distinct demonstrable functions.
Write docs/functions_list.md listing each function, its FR ID, and screen.

=====================================================================
PHASE 6 — Testing (Chapter 5.2)
=====================================================================
- pytest unit tests (preprocessing, retrievers, models), integration tests
  (API endpoints), coverage report.
- docs/test_cases.md + docs/test_cases.xlsx: MINIMUM 30 black-box test cases:
  TC ID, FR/NF ID, Description, Preconditions, Steps, Test Data,
  Expected Result, Actual Result, Status. Run them and fill actual results.
- Performance test (locust or a script): 50 concurrent users, report p95
  response time vs NF-01 (< 2s), save chart.
- Security check for NF-05 (bcrypt, protected routes, SQL injection attempts).
- Requirements traceability matrix: FR/NF → code module → test case IDs.

=====================================================================
PHASE 7 — Dissertation assets (Chapters 4, 5, Appendices)
=====================================================================
diagrams/ — write Mermaid or PlantUML source AND render PNGs for:
system architecture, package diagram, deployment diagram (Docker),
network diagram, use case diagram, activity diagram (query flow),
sequence diagrams (chat query, admin add FAQ), DFD level 0 and 1,
ERD / data model, class diagram, NLP pipeline diagram.
screenshots/ — use Playwright to auto-capture every function (both EN and AR
chat, mobile view, every admin screen), named 01_xxx.png … and listed in
docs/screenshots_index.md with a 2–3 line caption each.
docs/important_code.md — 5 most important code snippets (hybrid retriever,
Arabic preprocessing, chat endpoint, FAQ CRUD with index rebuild, widget
embed) each with explanation.
docs/user_manual.md — student guide + admin guide with screenshots.
docs/questionnaire.md — 5-point Likert usability questionnaire (~15 items:
ease of use, perceived accuracy, speed, Arabic support, intent to reuse,
plus demographics and 2 open questions) for 30 respondents (18 students,
6 applicants, 6 staff), and survey_analysis.py that reads a responses CSV
and produces descriptive stats + charts (include an empty template CSV —
do NOT invent survey responses).
docs/code_listing/ — key source files for the appendix.

=====================================================================
DONE CRITERIA
=====================================================================
- docker compose up --build runs everything with seeded data, no errors
- Hybrid accuracy >= 85% on held-out set, real results saved
- All tests pass; 30+ test cases documented with results
- 20+ functions working and screenshotted
- README with setup, default admin login, and how to rerun evaluation
Finish with a summary in PROGRESS.md: what was built, metrics achieved, and
any requirement that could not be fully met and why.
