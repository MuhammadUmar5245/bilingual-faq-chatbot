// Chapter 5 - condensed version (target ~15 pages)
const fs = require("fs");
const path = require("path");
const { H1, H2, H3, H4, P, B, figure, table, code, note, fig, tab, ROOT } = require("./lib");

const tc = JSON.parse(fs.readFileSync(path.join(__dirname, "testcases.json"), "utf8"));
const imp = fs.readFileSync(path.join(ROOT, "docs/important_code.md"), "utf8").split(String.fromCharCode(13)).join("");
const blocks = [...imp.matchAll(/```(?:python|jsx|html)\n([\s\S]*?)```/g)].map((m) => m[1].trimEnd());

// Cut excerpts from the real source: each range runs from the line containing `from` to the next line containing `to`.
function excerpt(src, ranges) {
  const lines = src.split("\n");
  const parts = ranges.map(([from, to]) => {
    const a = lines.findIndex((l) => l.includes(from));
    const b = lines.findIndex((l, i) => i >= a && l.includes(to));
    if (a < 0 || b < 0) throw new Error(`excerpt marker not found: ${from} / ${to}`);
    return lines.slice(a, b + 1).join("\n");
  });
  return parts.join("\n    ...\n");
}

const IMG = (f) => `docs/report_builder/img/${f}.png`;

module.exports = () => [
  H1("Chapter 5. Project Implementation, Testing & Evaluation"),
  P("This chapter describes the implementation and deployment of the system (Section 5.1), its testing at unit, integration, system, performance and security level together with the quasi-experiment on retrieval accuracy (Section 5.2), and its evaluation against the objectives (Section 5.3). All results were produced by running the project's scripts; none were entered by hand."),

  H2("5.1 Project Implementation"),
  H3("5.1.1 Software Deployment"),
  P(`The system was built in seven Agile increments matching the plan in Section 1.5. ${tab("env")} lists the main technologies; versions are pinned so that the build is reproducible.`),
  ...table("env", "Implementation environment", ["Layer", "Technologies"], [
    ["Back end", "Python 3.10, Flask 3, Flask-SQLAlchemy, Flask-Login, Flask-Limiter, bcrypt, gunicorn"],
    ["NLP", "scikit-learn 1.5, sentence-transformers 3.2 (PyTorch 2.4, CPU), NLTK 3.9, langdetect"],
    ["Front end", "React 18, Vite 5, Axios"],
    ["Database", "PostgreSQL 14 (Docker); SQLite for development and tests"],
    ["Deployment", "Docker Compose with three containers (Nginx, API, PostgreSQL)"],
    ["Testing", "pytest, pytest-cov, Playwright, a Python load-test script"],
  ], [20, 80], { size: 18 }),
  P("The whole system starts with one command, `docker compose up --build`. On first start the API creates the tables and loads the six categories, default settings, the administrator account and the 210 FAQs. The chatbot is then available at `http://localhost:8088` and the dashboard at `/admin/`. A college website embeds the chatbot with a single line (FR-08):"),
  ...code('<script src="https://chatbot.college.edu.om/widget.js" data-title="College Assistant" defer></script>'),

  H3("5.1.2 Screenshots and Discussion of the Implemented Functions"),
  P(`The system implements 33 functions (minimum 20), listed in ${tab("funcs")}. The screenshots were captured automatically from the Docker deployment; the dashboard figures come from a short demonstration session, not from real students.`),
  ...table("funcs", "Implemented functions", ["Student chat widget", "Req.", "Admin dashboard", "Req."], [
    ["F01 Floating chat button on any page", "FR-08", "F17 Secure login / logout", "NF-05"],
    ["F02 Question in English, verified answer", "FR-01, FR-03", "F18 Statistics: queries, resolution rate, confidence, response time", "FR-04, FR-07"],
    ["F03 Question in Arabic, Arabic answer", "FR-01", "F19 Charts by day, category, method and language", "FR-02, FR-07"],
    ["F04 Automatic language detection", "FR-01", "F20 FAQ table with search, filters, pages", "FR-06"],
    ["F05 EN/عربي toggle with RTL layout", "FR-01", "F21 Add FAQ (bilingual form)", "FR-06"],
    ["F06 Typing indicator", "NF-03", "F22 Edit FAQ", "FR-06"],
    ["F07 Category quick-reply buttons", "FR-02", "F23 Disable / enable FAQ", "FR-06"],
    ["F08 Popular questions", "FR-03", "F24 Delete FAQ with confirmation", "FR-06"],
    ["F09 Answer card with category and confidence", "FR-02", "F25 Automatic index rebuild", "NF-06"],
    ["F10 Fallback with contact details", "FR-05", "F26 CSV import with error report", "FR-06"],
    ["F11 'Did you mean' suggestions", "FR-05", "F27 CSV export", "FR-06"],
    ["F12 Thumbs up / down feedback", "FR-07", "F28 Conversation logs with filters", "FR-07"],
    ["F13 History of last five Q&A pairs", "FR-10", "F29 Unanswered queries list", "FR-07"],
    ["F14 Clear chat", "NF-03", "F30 Create FAQ from unanswered query", "FR-06"],
    ["F15 Full-screen mobile layout", "NF-03", "F31 Threshold settings", "FR-03"],
    ["F16 Embeddable widget.js", "FR-08", "F32 Fallback contact settings", "FR-05"],
    ["", "", "F33 Change password", "NF-05"],
  ], [33, 14, 39, 14], { size: 16 }),
  P(`${fig("w1")} shows the student chat. The chatbot appears as a floating button on the college page (a); on opening, it offers popular questions and the six category buttons (b). An English question is answered with the matched FAQ, its category, the confidence and feedback buttons (c). When the student writes in Arabic, the language is detected, the answer is given in Arabic and the whole widget switches to right-to-left (d).`),
  ...figure("w1", IMG("w1_chat"), "Chat widget: (a) college page with chat button, (b) welcome screen, (c) English answer, (d) Arabic answer with RTL layout", 6.0, 3.8),
  P(`${fig("w2")} shows the supporting functions: browsing a category (a); the fallback for an out-of-scope question with the contact card and suggestions (b, FR-05); feedback (c); and the history of the last five questions and answers (d, FR-10). ${fig("w3")} shows the full-screen phone layout in English and Arabic (a, b) and the typing indicator (c). Panel (b) also shows a near miss: a general Arabic question about student housing was matched to the related FAQ about separate male and female hostels.`),
  ...figure("w2", IMG("w2_features"), "(a) Category questions, (b) fallback with contact details, (c) feedback, (d) last-five history", 6.0, 3.8),
  ...figure("w3", IMG("w3_mobile"), "(a) Mobile view in English, (b) mobile view in Arabic, (c) typing indicator", 5.2, 3.8),
  P(`${fig("a1")} shows the admin dashboard: a rejected login (a, NF-05), the overview statistics and charts (b), the FAQ table (c) and the bilingual Add FAQ form (d), which requires no programming (FR-06, NF-06). ${fig("a2")} demonstrates maintenance: immediately after an FAQ about a swimming pool was saved, the chatbot answered a question about it (a, no restart needed); a disabled FAQ (b); a CSV import that reports the invalid row it skipped (c); and the conversation log (d, FR-07). ${fig("a3")} shows the unanswered-queries list (a), the button that turns such a query into a pre-filled new FAQ (b), and the settings for thresholds, contact details and password (c, d).`),
  ...figure("a1", IMG("a1_admin"), "(a) Rejected login, (b) overview dashboard, (c) FAQ table, (d) Add FAQ form", 6.0, 4.4),
  ...figure("a2", IMG("a2_manage"), "(a) New FAQ used immediately by the chatbot, (b) disabled FAQ, (c) CSV import result, (d) conversation logs", 6.0, 3.9),
  ...figure("a3", IMG("a3_improve"), "(a) Unanswered queries, (b) create FAQ from a query, (c) settings, (d) password validation", 6.0, 3.9),

  H3("5.1.3 Discussion of Important Codes"),
  P("The five most important parts of the code are shown as short excerpts taken directly from the source files (… marks omitted lines)."),
  H4("Code 1 — Hybrid retrieval (nlp/hybrid.py)"),
  ...code(excerpt(blocks[0], [["t_scores = tfidf.scores(query)", '"fallback", t_scores'], ["category = faq.category if faq", "category = faq.category if faq"]])),
  P("If the best TF-IDF score reaches the threshold, that FAQ is returned. Otherwise the sentence-BERT scores are fused with the TF-IDF scores and the best FAQ is accepted only above the second threshold; if not, the result is a fallback, still classified into a category (FR-02, FR-03, FR-05). Only the identifier of a stored FAQ is returned, so the chatbot cannot produce an unverified answer."),
  H4("Code 2 — Arabic preprocessing (nlp/preprocess.py)"),
  ...code(excerpt(blocks[1], [["def normalize_arabic", "return text.translate"], ["def stem_arabic", "return token"]])),
  P("Diacritics and tatweel are removed and letter variants unified, then one common prefix (such as the article ال) and one suffix are stripped while keeping at least three letters, so الدراسة, الدراسه and دراسي share one stem. This made Arabic retrieval as accurate as English (Section 5.2.3)."),
  H4("Code 3 — Chat endpoint (routes/public.py)"),
  ...code(excerpt(blocks[2], [['@public_bp.post("/chat")', "def chat"], ["result = get_engine().retrieve(message)", "faq = db.session.get"], ["log = ConversationLog(", "db.session.commit()"]])),
  P("The endpoint is rate-limited (NF-05), validates its input, calls the retrieval engine and returns the answer in the student's language or the fallback with contact details. Every query, answered or not, is logged with its session, language, FAQ, confidence, method and response time (FR-07)."),
  H4("Code 4 — FAQ management with automatic index rebuild (routes/admin.py, app/nlp_service.py)"),
  ...code(excerpt(blocks[3], [['@admin_bp.post("/faqs")', "return jsonify(faq.to_dict()), 201"], ["def bump_faq_version", "db.session.commit()"], ["def get_engine", "if engine is None or"]])),
  P("Admin endpoints require login. After an FAQ is saved, the FAQ version in the database is incremented; on the next chat request each worker sees the new version and rebuilds its index, so staff changes take effect immediately without restarting the service (FR-06, NF-06)."),
  H4("Code 5 — Embeddable widget (frontend/widget/src/embed.jsx)"),
  ...code(excerpt(blocks[4], [["function mount", "createRoot(container)"]])),
  P("The widget reads its settings from its own `<script>` tag and renders inside a Shadow DOM, so the college's styles and the widget's styles cannot affect each other. One script tag is the whole integration (FR-08)."),

  H2("5.2 Project Testing"),
  H3("5.2.1 Types of Testing"),
  P(`${tab("types")} summarises the testing. Unit and integration tests were written alongside each increment; the system tests, the accuracy experiment and the load test were run against the complete Docker deployment.`),
  ...table("types", "Types of testing applied", ["Type", "Method and tool", "Result"], [
    ["Unit testing", "pytest: preprocessing, language detection, retrievers, classifier, models", "55 tests passed"],
    ["Integration testing", "pytest + Flask test client: every API endpoint, validation, security", "83 tests passed; 96 % code coverage"],
    ["System (black-box) testing", "39 requirement-based test cases via the API and a real browser (Playwright)", "39 / 39 passed"],
    ["Accuracy (quasi-experiment)", "evaluate.py on 361 held-out queries", "85.6 % (NF-02 met)"],
    ["Performance testing", "50 concurrent users, load_test.py", "p95 802 ms (NF-01 met)"],
    ["Security testing", "Negative tests: unauthorised access, SQL injection, brute force", "All passed (NF-05 met)"],
    ["Acceptance / usability", "Questionnaire with 30 respondents", "Pending data collection"],
  ], [24, 52, 24], { size: 18 }),

  H3("5.2.2 Test Cases and Results"),
  P(`${tab("tcs")} lists the 39 black-box test cases (minimum 25), executed automatically against the running system. Full steps, test data and the recorded actual results are in the test-case spreadsheet in the appendix. All test cases passed; two failures in early runs were caused by mistakes in the test script itself (CSV test data in TC18, timing in TC27) and were corrected before the final run.`),
  ...table("tcs", "Black-box test cases and results", ["TC", "Req.", "Description", "Expected result", "Status"],
    tc.cases.map((r) => [r[0], r[1], r[2], r[6], r[8]]), [7, 11, 44, 30, 8],
    { size: 15, fill: (r, ri, i) => (i === 4 ? (r[4] === "Pass" ? "D9F2E3" : "F9D6D2") : ri % 2 ? "F3F6F9" : undefined) }),

  H3("5.2.3 Quasi-Experiment: Retrieval Accuracy (NF-02)"),
  P("As planned in Section 3.2.1, five retrieval methods were compared on 361 test queries written separately from the 210 FAQs (244 English, 117 Arabic, including paraphrases, synonyms, misspellings, abbreviations, colloquial Arabic and 32 out-of-scope questions). To avoid tuning on the reported numbers, thresholds were chosen only on the odd-numbered queries (tuning split); results are reported on the even-numbered queries (held-out split, 180 queries)."),
  ...table("methods", "Retrieval accuracy by method", ["Method", "Held-out (n = 180)", "All (n = 361)", "Arabic", "Out-of-scope rejected"], [
    ["Keyword match (baseline)", "63.9 %", "64.3 %", "59.8 %", "62.5 %"],
    ["TF-IDF only", "81.1 %", "81.2 %", "82.1 %", "53.1 %"],
    ["SBERT only", "78.3 %", "77.3 %", "75.2 %", "93.8 %"],
    ["Hybrid as specified (TF-IDF → SBERT)", "78.9 %", "77.6 %", "76.1 %", "93.8 %"],
    ["**Hybrid final (with score fusion)**", "**85.6 %**", "**87.3 %**", "**88.9 %**", "87.5 %"],
  ], [36, 16, 16, 14, 18], { size: 18 }),
  P(`The final hybrid reached **85.6 %** on the held-out queries, meeting NF-02, and outperformed TF-IDF alone and the keyword baseline (${fig("methods")}), which supports the hypothesis of the experiment. The hybrid as first specified did not reach the target: correct TF-IDF matches rarely exceed 0.75, so most queries were decided by sentence-BERT alone, which is weaker on this data. Fusing the two scores solved this. Three further changes, judged only on the tuning split, were kept: improved Arabic stemming, Arabic keywords added to the FAQs (phrases identical to a test query were removed automatically) and tuned thresholds. Arabic accuracy (88.9 %) was slightly higher than English (86.5 %), and language detection was correct for all 361 queries. Paraphrases remained the hardest type (77.3 %), and 12.5 % of out-of-scope questions still received an answer. Because the same author wrote the test queries and the keywords, accuracy on real student questions may be lower.`),
  ...figure("methods", "docs/results/method_comparison.png", "Accuracy by method on the held-out queries", 5.4, 2.8),

  H3("5.2.4 Performance and Security Testing"),
  P("**Performance (NF-01).** Fifty simulated users each sent ten queries at the same time with no pause between them, a stricter condition than real use. The first run failed (p95 = 3.7 s): every worker process created as many processor threads as the server has cores, so threads competed for the CPU. After increasing the worker processes and limiting each to one numerical-library thread, the 95th-percentile response time was **802 ms with no errors** at 106 requests per second, so NF-01 is met. A single question under normal load took 65–74 ms end to end (FR-04)."),
  P("**Security (NF-05).** All administration endpoints returned HTTP 401 without login; passwords are stored as bcrypt hashes with random salts; SQL-injection payloads in the login, search and chat fields were rejected or treated as text with the database intact; login and chat are rate-limited; and weak new passwords are refused (TC32–TC35, TC39)."),

  H3("5.2.5 Requirements Traceability"),
  ...table("rtm", "Requirements traceability", ["Req.", "Implemented in", "Test cases", "Result"], [
    ["FR-01", "nlp/language.py, nlp/preprocess.py, widget", "TC01–TC03, TC28", "Met"],
    ["FR-02", "nlp/classifier.py, nlp/hybrid.py", "TC04, TC05, TC30", "Met"],
    ["FR-03", "nlp/tfidf_retriever.py, sbert_retriever.py, hybrid.py", "TC06–TC08, TC36", "Met"],
    ["FR-04", "routes/public.py", "TC09", "Met"],
    ["FR-05", "routes/public.py, widget fallback card", "TC10, TC11, TC31", "Met"],
    ["FR-06", "routes/admin.py, admin dashboard", "TC12–TC19", "Met"],
    ["FR-07", "conversation logs, feedback, statistics", "TC20–TC23", "Met"],
    ["FR-08", "widget embed.jsx, Nginx", "TC24, TC25", "Met"],
    ["FR-09", "data/faqs_seed.csv (210 FAQs)", "TC26", "Met (sample data)"],
    ["FR-10", "widget history", "TC27", "Met"],
    ["NF-01", "gunicorn workers, thread limits", "Load test", "Met"],
    ["NF-02", "nlp package, evaluate.py", "TC37", "Met"],
    ["NF-03", "widget and dashboard design", "TC28–TC30; survey", "Pending survey"],
    ["NF-04", "Docker Compose", "TC38", "Met"],
    ["NF-05", "Flask-Login, bcrypt, rate limits", "TC32–TC35, TC39", "Met"],
    ["NF-06", "dashboard, automatic index rebuild", "TC12, TC18, TC36", "Met"],
  ], [10, 50, 22, 18], { size: 16 }),

  H2("5.3 System Evaluation"),
  P("**a. How the solution is realised.** Students receive a verified answer in a fraction of a second at any time, in the language they write in, through a chat window on the college website; the chatbot understands paraphrased, misspelled and colloquial questions that a keyword search misses (85.6 % against 63.9 %), and when it cannot answer it directs the student to a person. Staff turn repetitive enquiries into a managed knowledge base and can see which questions students actually ask."),
  P("**b. Implementation method.** The stack of Section 3.5 was used. A retrieval-only design was preferred to a generative model so that official information is always the college's own; pre-trained models were used without fine-tuning because 210 FAQs are too few for reliable training; and all evaluation artefacts are scripts, so the results can be regenerated when the sample FAQs are replaced with real data."),
  P(`**c. Types of testing.** Unit, integration, black-box system, accuracy, performance, security and acceptance testing were applicable (${tab("types")}).`),
  P("**d. Evaluation against objectives and success criteria.** A requirements-based strategy gave every success criterion an objective, repeatable test, planned from the traceability matrix and run against the final deployment. All functional requirements and NF-01, NF-02, NF-04, NF-05 and NF-06 were met. Testing led to three modifications — score fusion, better Arabic processing and the worker configuration. NF-03 and user satisfaction are evaluated with the questionnaire below."),
  H3("Usability Questionnaire"),
  P("The questionnaire (Appendix) is given to 30 respondents (18 students, 6 applicants, 6 staff; Table 10) after ten minutes of use. It contains demographic questions, 15 five-point Likert items on ease of use, perceived accuracy, speed, Arabic support, interface, satisfaction and intention to reuse, two staff items on maintaining FAQs, an overall ease-of-use rating for NF-03 and two open questions. Responses are analysed with `survey_analysis.py` (means, percentage agreeing, Cronbach's alpha (Cronbach, 1951) and results by group)."),
  note("[TO BE COMPLETED AFTER DATA COLLECTION] Insert the survey results from survey_analysis.py: respondent profile, NF-03 percentage (target ≥ 80 % Easy or Very easy), item means and the Likert chart. Do not use estimated values."),
];
