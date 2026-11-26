# Requirements traceability matrix

Every functional (FR) and non-functional (NF) requirement from Chapter 3 (Tables 11–12) is traced to
the code that implements it, the automated tests (pytest, `backend/tests/`), the black-box test
cases ([`test_cases.md`](test_cases.md)) and the functions shown in the screenshots
([`functions_list.md`](functions_list.md)).

| Req. | Requirement (short) | Implementing modules | Automated tests (pytest) | Black-box test cases | Functions |
|---|---|---|---|---|---|
| FR-01 | Accept EN/AR queries, detect language | `nlp/language.py`, `nlp/preprocess.py`, `routes/public.py::chat`, widget `Widget.jsx` (auto switch, toggle) | `test_preprocess.py` (TestLanguageDetection, TestArabicNormalisation, TestTokenize), `test_chat_arabic_returns_arabic_answer` | TC01, TC02, TC03, TC28 | F02–F05 |
| FR-02 | Classify each query into 6 categories | `nlp/classifier.py`, `nlp/hybrid.py`, `conversation_logs.category` | `TestClassifier`, `test_low_score_goes_to_fallback`, `test_chat_fallback_includes_contact` | TC04, TC05, TC30 | F07, F09, F19 |
| FR-03 | TF-IDF retrieval with SBERT fallback | `nlp/tfidf_retriever.py`, `nlp/sbert_retriever.py`, `nlp/hybrid.py`, `app/nlp_service.py` | `TestTfidf`, `TestHybridTfidfOnly`, `TestSbert`, `test_chat_english_exact_question` | TC06, TC07, TC08, TC36, TC40–TC43 (fail) | F02, F03, F09, F25, F31 |
| FR-04 | Answer displayed within 2 s | `routes/public.py::chat` (response_ms), cached indexes/embeddings | `test_chat_english_exact_question` (response_ms < 2000) | TC09 (+ load test NF-01) | F02, F18 |
| FR-05 | Fallback with escalation contacts | `routes/public.py` (`FALLBACK_TEXT`, `contact_details`), widget `ContactCard` | `test_chat_fallback_includes_contact`, `test_chat_fallback_arabic_text`, `test_settings_update_applies_to_chat` | TC10, TC11, TC31, TC40, TC41, TC43 (fail) | F10, F11, F32 |
| FR-06 | Staff add/edit/disable FAQs without code | `routes/admin.py` (FAQ CRUD, toggle, import/export), admin `Faqs.jsx`, `Unanswered.jsx` | `test_create_faq_and_chatbot_uses_it_immediately`, `test_update_faq`, `test_toggle_disables_faq_in_chatbot`, `test_delete_faq_keeps_logs`, `test_import_csv`, `test_export_csv` | TC12–TC19 | F20–F27, F30 |
| FR-07 | Log every query (FAQ, confidence, method, session) | `models.ConversationLog`, `models.Feedback`, `routes/public.py::chat`, `routes/admin.py` (logs, unanswered, stats) | `test_every_query_is_logged`, `test_privacy.py` (masking, retention), `test_feedback`, `test_logs_filters`, `test_unanswered_includes_fallback_and_thumbs_down`, `test_stats` | TC20–TC23 | F12, F18, F19, F28, F29 |
| FR-08 | Widget embeddable via JS snippet | `frontend/widget/src/embed.jsx` (Shadow DOM, `widget.js`), `docs/demo-college-site.html`, `frontend/nginx.conf` | `test_site.py` | TC24, TC25 | F01, F16 |
| FR-09 | ≥ 200 FAQ entries | `data/faqs_seed.csv` (210), `app/seed.py` | `test_seed_loads_at_least_200_faqs`, `test_categories_with_counts` | TC26 | F20 |
| FR-10 | Show last 5 Q–A pairs of the session | widget `Widget.jsx` (`HISTORY_SIZE = 5`, history view) | – (UI) | TC27 | F13 |
| NF-01 | p95 < 2 s with 50 concurrent users | gunicorn workers/threads/connection limit, cached indexes | `tests/perf/load_test.py` | LT-2 ([`results/performance.md`](results/performance.md)), LT-3 during an index rebuild ([`results/performance_rebuild.md`](results/performance_rebuild.md)) | – |
| NF-02 | Intent classification accuracy ≥ 85 % on held-out set (linear SVM: 88.4 %) | `nlp/classifier.py`, `nlp/evaluate.py` | `nlp/evaluate.py` ([`results/results.md`](results/results.md)) | TC37 | – |
| NF-03 | Usability (≥ 80 % rate easy) | widget RTL, typing indicator, chips, mobile layout; admin forms | – | TC28, TC29, TC30; survey ([`questionnaire.md`](questionnaire.md)) | F05, F06, F14, F15 |
| NF-04 | Containerised, Docker Engine 20.10+ | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile`, `/api/health` | `test_health` | TC38 | – |
| NF-05 | Login required; bcrypt passwords | `routes/admin.py` (`@login_required`), `models.AdminUser`, Flask-Limiter | `test_admin_routes_require_login`, `test_password_is_bcrypt_hashed`, SQL-injection tests, rate-limit tests | TC32–TC35, TC39; [`security_review.md`](security_review.md) | F17, F33 |
| NF-06 | FAQs maintainable by staff without code | admin dashboard, automatic index rebuild (`faq_version`), live settings | `test_create_faq_and_chatbot_uses_it_immediately`, `test_settings_update_applies_to_chat` | TC12, TC18, TC36 | F21–F26, F30, F31 |
