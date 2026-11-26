// Chapter 4 - condensed version (target ~8 pages)
const { H1, H2, H3, P, B, figure, table, fig, tab } = require("./lib");

module.exports = () => [
  H1("Chapter 4. Project Design"),
  P("This chapter presents the design of the bilingual FAQ chatbot, following the viewpoints of IEEE Std 1016-2009 (IEEE, 2009): a system overview with design constraints, the architecture, the process model and the data model. Every design element is traced to the requirement identifiers of Chapter 3 (FR-01 to FR-10, NF-01 to NF-06)."),

  H2("4.1 System Overview and Design Constraints"),
  P("The system is a **retrieval-based** question-answering service in English and Arabic. A student types a question in the chat widget on the college website; the system detects the language, compares the question with a knowledge base of verified FAQs and returns the best answer with its category and a confidence score. When no FAQ matches confidently, it shows the contact details of the student services office instead of guessing (FR-05). Staff maintain the FAQs through a web dashboard without programming (FR-06, NF-06). The chatbot never generates text, so every answer a student sees is one that the college has approved — an important property for official information such as fees and examination rules."),
  P(`The system consists of an embeddable **chat widget** (React, delivered as one \`widget.js\` file, FR-08), an **admin dashboard** (React), a **REST API** (Flask) and an **NLP engine** that combines TF-IDF with a multilingual sentence-BERT model (FR-01 to FR-03). ${tab("dc")} lists the main design constraints.`),
  ...table("dc", "Main design constraints", ["Constraint", "Source", "Effect on the design"], [
    ["Answers only from verified FAQs", "Ch. 2; FR-05", "Retrieval architecture with an explicit fallback"],
    ["English and Arabic, including right-to-left display", "FR-01", "Language detection, Arabic normalisation, multilingual model, RTL interface"],
    ["Fixed stack: Python 3.10, Flask, React 18, PostgreSQL 14, Docker", "Section 3.5", "Three-tier architecture in three containers"],
    ["Modest hardware (4 GB RAM minimum)", "Table 13", "Small CPU-only MiniLM model; cached embeddings"],
    ["Staff have no programming knowledge", "FR-06, NF-06", "Form-based maintenance; automatic index rebuild"],
    ["Widget must not affect the college website", "FR-08", "Widget isolated in a Shadow DOM"],
  ], [34, 18, 48], { size: 18 }),

  H2("4.2 System Architecture"),
  P(`The system follows a **three-tier client–server architecture** with a RESTful interface (Fielding, 2000), shown in ${fig("arch")}. The presentation tier (widget, dashboard and host college page) is served by Nginx; the application tier is a stateless Flask API that contains the NLP engine; the data tier is PostgreSQL with the two schemas of Section 3.5.2 — the FAQ knowledge base and the interaction data. Separating the tiers lets the same API serve the widget and the dashboard, allows the API to scale by adding worker processes (needed later for NF-01) and maps each tier to one container (NF-04).`),
  P("Two mechanisms are central. **Index synchronisation:** each API worker keeps its TF-IDF index and sentence embeddings in memory; when staff change an FAQ, a `faq_version` value in the database is incremented and every worker rebuilds its index before its next answer, so changes apply without a restart (NF-06). **Logging by design:** every query is stored with its result, which feeds the statistics, the unanswered-queries list and the evaluation (FR-07)."),
  ...figure("arch", "diagrams/01_system_architecture.png", "System architecture", 6.0, 4.4),
  P(`The **package diagram** (${fig("pkg")}) shows the code structure. The back end is divided into \`app\` (configuration, seeding, link to the NLP engine), \`routes\` (public and admin API), \`models\` (database entities) and \`nlp\` (language detection, preprocessing, retrievers, classifier, hybrid pipeline and evaluation). The \`nlp\` package does not depend on the web framework, so it can be tested and evaluated on its own. The \`widget\` and \`admin\` front-end packages communicate with the back end only through the REST API.`),
  ...figure("pkg", "diagrams/02_package_diagram.png", "Package diagram", 6.0, 4.6),
  P(`The **deployment diagram** (${fig("deploy")}) shows the three Docker containers started by \`docker compose up --build\`: **web** (Nginx, the only container with a published port), **api** (gunicorn running Flask, with the sentence-BERT model built into the image so it runs offline) and **db** (PostgreSQL with a persistent volume). Health checks make each container wait until the one it depends on is ready. The **network diagram** (${fig("net")}) places the system in a college network: students and staff reach only the web container through the firewall, while the API and database stay on a private Docker network.`),
  ...figure("deploy", "diagrams/03_deployment_diagram.png", "Deployment diagram", 4.0, 4.2),
  ...figure("net", "diagrams/04_network_diagram.png", "Network diagram", 4.0, 3.6),

  H2("4.3 Process Model"),
  P("The use cases of the two actors — the student, who asks questions, browses categories, views the session history and rates answers, and the administrator, who manages FAQs, reviews logs and statistics and configures the system — are shown in Figure 3 (Chapter 3) and implemented without change."),
  P(`The **activity diagram** (${fig("act")}) refines Figure 4 of Chapter 3. After validation, the language is detected and the text pre-processed. If the TF-IDF similarity of the best FAQ reaches the threshold (0.75, editable by staff) that FAQ is returned. Otherwise the sentence-BERT stage combines the semantic similarity with the TF-IDF evidence (fused = 0.6 × TF-IDF + 0.4 × SBERT) and accepts the best FAQ if the fused score reaches 0.35. If neither stage is confident, the fallback with contact details is returned and a classifier still assigns one of the six categories (FR-02). Every query is logged before the answer is displayed. The score-fusion step was added after the quasi-experiment (Section 5.2.3) showed that using sentence-BERT alone in the fallback stage reached only 78.9 % accuracy.`),
  ...figure("act", "diagrams/06_activity_diagram.png", "Activity diagram — processing of a student query", 2.6, 7.2),
  P(`The **sequence diagram** (${fig("seq")}) shows the interaction for a student question: the widget sends \`POST /api/chat\` through Nginx; the API validates the request, applies the rate limit, checks that its index is current, calls the hybrid retriever, loads the answer in the query language, writes the log record and returns JSON, which the widget renders as an answer or fallback card.`),
  ...figure("seq", "diagrams/07_sequence_chat_query.png", "Sequence diagram — student asks a question", 6.0, 5.6),
  P(`${tab("nlp")} summarises the design of the NLP pipeline. CAMeL Tools (Obeid et al., 2020), named in Section 3.5.3, was evaluated but not used: it requires older versions of libraries that sentence-transformers depends on. A custom normaliser and light stemmer provide the orthographic normalisation the project needs.`),
  ...table("nlp", "Design of the NLP pipeline", ["Step", "Design and rationale"], [
    ["Language detection", "Ratio of Arabic to Latin letters, langdetect for longer text (short queries defeat langdetect)"],
    ["Normalisation", "Remove diacritics and tatweel; unify alef, yaa, taa marbuta and hamza forms, so different spellings of a word become identical"],
    ["Tokens and stemming", "NLTK English stop words (question words kept) and Snowball stemmer (Bird, Klein and Loper, 2009); Arabic stop words and light prefix/suffix stemming (Larkey, Ballesteros and Connell, 2007); glossary for abbreviations and Gulf colloquial words"],
    ["TF-IDF", "English and Arabic document per FAQ; stemmed word 1–2-grams plus character 3–5-grams (tolerates misspellings); cosine similarity (Salton and Buckley, 1988)"],
    ["Sentence-BERT", "paraphrase-multilingual-MiniLM-L12-v2: English and Arabic paraphrases in one vector space (Reimers and Gurevych, 2019; 2020); embeddings cached"],
    ["Decision", "TF-IDF ≥ 0.75, else fused score ≥ 0.35, else fallback; category classifier (linear SVM) for every query"],
  ], [22, 78], { size: 18 }),

  H2("4.4 Data Model"),
  P(`${fig("erd")} shows the entity–relationship diagram. **CATEGORIES** holds the six categories in English and Arabic. **FAQS** holds each question and answer in both languages, keywords and an \`is_active\` flag that implements "disable" (FR-06). **CONVERSATION_LOGS** stores every query with the detected language, matched FAQ (empty for a fallback), confidence, method, category and response time (FR-07); the link is set to empty if an FAQ is deleted so the history is kept. **FEEDBACK** stores thumbs-up/down ratings, **ADMIN_USERS** stores staff accounts with bcrypt hashes (NF-05) and **SETTINGS** holds the thresholds, contact details and FAQ version. SQLAlchemy is used as the object-relational mapper, so the same model runs on PostgreSQL and on SQLite for testing, and all queries use bound parameters, which prevents SQL injection.`),
  ...figure("erd", "diagrams/11_erd.png", "Entity–relationship diagram", 3.6, 5.2),

  H2("4.5 Choice of Design Method and Experience of its Application"),
  P("An object-oriented, model-driven approach with UML diagrams was used within the Agile process of Section 3.3, because the implementation (Python and React) is component- and object-oriented (Sommerville, 2016). All diagrams were written as text (Mermaid) and rendered automatically, so they were kept in the repository and regenerated when the design changed. The architecture and data model stayed stable, with only two added attributes (the Arabic answer and the query category). The process model changed after testing: the measured accuracy of the first fallback design was below target, which led to score fusion, and the first load test showed that the deployment had to limit processor threads (Section 5.2.4). Keeping the NLP engine independent of the web framework made these experiments quick to repeat."),
];
