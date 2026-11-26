"""Mermaid sources for all report diagrams (Chapters 3-4). Run render.py to write .mmd + .png files."""

DIAGRAMS = {}

DIAGRAMS["01_system_architecture"] = """flowchart TB
  subgraph Users
    S["Student / applicant<br/>(browser or phone)"]
    A["College staff<br/>(administrator)"]
  end
  subgraph Web["Web tier - Nginx container"]
    H["College website<br/>(embeds widget)"]
    W["Chat widget<br/>widget.js (React)"]
    D["Admin dashboard<br/>(React SPA)"]
  end
  subgraph API["Application tier - Flask API container (gunicorn)"]
    P["Public API<br/>/api/chat, /categories,<br/>/faqs/popular, /feedback"]
    AD["Admin API<br/>/api/admin/* (Flask-Login)"]
    N["NLP engine<br/>language detection, preprocessing,<br/>TF-IDF, SBERT fusion, fallback"]
    C["Category classifier<br/>(6 categories)"]
  end
  subgraph Data["Data tier - PostgreSQL 14 container"]
    KB[("FAQ knowledge base<br/>categories, faqs, settings,<br/>admin_users")]
    LG[("Interaction data<br/>conversation_logs, feedback")]
  end
  S --> H --> W
  A --> D
  W -- "HTTP / JSON" --> P
  D -- "HTTP / JSON + session cookie" --> AD
  P --> N --> C
  N -- "reads active FAQs" --> KB
  P -- "logs every query" --> LG
  AD -- "CRUD, import/export,<br/>settings" --> KB
  AD -- "reads logs and stats" --> LG
  AD -. "faq_version bump:<br/>index rebuild" .-> N
"""

DIAGRAMS["02_package_diagram"] = """flowchart TB
  subgraph backend["package: backend (Python / Flask)"]
    direction TB
    subgraph app["package: app"]
      app1["__init__ (create_app)"]
      app2["config"]
      app3["extensions"]
      app4["seed"]
      app5["nlp_service"]
    end
    subgraph routes["package: routes"]
      r1["public"]
      r2["admin"]
      r3["site"]
    end
    subgraph models["package: models"]
      m1["Category, FAQ, ConversationLog,<br/>Feedback, AdminUser, Setting"]
    end
    subgraph nlp["package: nlp"]
      n1["language"]
      n2["preprocess"]
      n3["tfidf_retriever"]
      n4["sbert_retriever"]
      n5["classifier"]
      n6["hybrid"]
      n7["evaluate"]
    end
    subgraph tests["package: tests"]
      t1["unit + integration (pytest)"]
      t2["blackbox"]
      t3["perf"]
    end
  end
  subgraph frontend["package: frontend (React 18 + Vite)"]
    subgraph widget["package: widget"]
      w1["embed.jsx"]
      w2["Widget.jsx"]
      w3["api.js / i18n.js"]
    end
    subgraph admin["package: admin"]
      a1["App.jsx"]
      a2["pages/*"]
      a3["components/*"]
    end
  end
  data["package: data<br/>faqs_seed.csv, test_queries.csv"]
  routes --> app
  routes --> models
  app --> nlp
  app --> models
  widget -. "REST /api" .-> routes
  admin -. "REST /api/admin" .-> routes
  app --> data
  nlp --> data
  tests --> routes
  tests --> nlp
"""

DIAGRAMS["03_deployment_diagram"] = """flowchart TB
  subgraph client["device: Client (PC / phone)"]
    B["Web browser<br/>college site + widget.js<br/>admin dashboard"]
  end
  subgraph host["device: Server running Docker Engine 20.10+ (docker compose)"]
    subgraph web["container: web (nginx:1.27-alpine)"]
      NG["Nginx - published port 8088<br/>/ demo site, /widget.js,<br/>/admin/ SPA, /api/ proxy"]
    end
    subgraph api["container: api (python:3.10-slim)"]
      GU["gunicorn: 6 workers x 4 threads<br/>Flask app + NLP engine"]
      MD[("SBERT model<br/>baked into image")]
    end
    subgraph db["container: db (postgres:14-alpine)"]
      PG[("PostgreSQL 14<br/>database faqbot")]
    end
    VOL[("volume: pgdata")]
  end
  B -- "HTTP :8088" --> NG
  NG -- "HTTP :5000 (internal network)" --> GU
  GU -- "TCP :5432 (psycopg2)" --> PG
  GU --- MD
  PG --- VOL
"""

DIAGRAMS["04_network_diagram"] = """flowchart TB
  subgraph internet["Internet / campus network"]
    ST["Students' phones and laptops"]
    CS["College website<br/>(any host)"]
  end
  subgraph lan["College staff LAN"]
    AD["Staff PCs<br/>(admin dashboard)"]
  end
  FW{{"Firewall / router<br/>only web port open"}}
  subgraph dmz["Server (Docker host)"]
    subgraph net["Docker bridge network (private)"]
      WEB["web (Nginx)<br/>published :8088"]
      API["api (Flask)<br/>:5000 not published"]
      DB[("db (PostgreSQL)<br/>:5432 not published")]
    end
  end
  ST -- "HTTP(S)" --> FW
  CS -. "loads /widget.js" .-> FW
  AD -- "HTTP(S)" --> FW
  FW --> WEB
  WEB -- "/api/*" --> API
  API --> DB
"""

DIAGRAMS["05_use_case_diagram"] = """flowchart LR
  STU(("Student /<br/>applicant"))
  ADM(("Admin<br/>staff"))
  subgraph sys["FAQ Chatbot System"]
    direction TB
    U1(["Ask question (EN/AR)"])
    U2(["Receive verified answer"])
    U3(["Receive fallback + contact details"])
    U4(["Browse categories / popular questions"])
    U5(["View last 5 Q and A (history)"])
    U6(["Rate answer (helpful / not)"])
    U7(["Switch language EN / AR"])
    U8(["Log in / log out"])
    U9(["Manage FAQs (add, edit, disable, delete)"])
    U10(["Import / export FAQs (CSV)"])
    U11(["View conversation logs"])
    U12(["Review unanswered queries"])
    U13(["View usage statistics"])
    U14(["Configure thresholds and contacts"])
    U15(["Change password"])
  end
  STU --- U1
  STU --- U4
  STU --- U5
  STU --- U6
  STU --- U7
  U1 -. "include" .-> U2
  U1 -. "extend: low confidence" .-> U3
  ADM --- U8
  ADM --- U9
  ADM --- U10
  ADM --- U11
  ADM --- U12
  ADM --- U13
  ADM --- U14
  ADM --- U15
  U12 -. "extend: create FAQ from query" .-> U9
"""

DIAGRAMS["06_activity_diagram"] = """flowchart TD
  start(("start")) --> A["Student types a question"]
  A --> V{"Valid?<br/>1-500 characters"}
  V -- No --> E["Show validation message"] --> stop1(("end"))
  V -- Yes --> L["Detect language (EN / AR)"]
  L --> P["Preprocess<br/>normalise, stop-words, stemming"]
  P --> T["TF-IDF cosine similarity<br/>against all active FAQs"]
  T --> D1{"TF-IDF score >= 0.75?"}
  D1 -- Yes --> R1["Best TF-IDF match<br/>method = tfidf"]
  D1 -- No --> S["SBERT similarity<br/>fused = 0.6 TF-IDF + 0.4 SBERT"]
  S --> D2{"fused score >= 0.35?"}
  D2 -- Yes --> R2["Best fused match<br/>method = sbert"]
  D2 -- No --> F["Fallback message + contact details<br/>+ 'Did you mean' suggestions<br/>method = fallback"]
  R1 --> ANS["Answer in query language<br/>+ category + confidence"]
  R2 --> ANS
  F --> CL["Classify category (SVM)"]
  CL --> LOG
  ANS --> LOG["Log query: session, language, FAQ,<br/>confidence, method, response time"]
  LOG --> SH["Display in widget,<br/>update last-5 history"]
  SH --> FB{"Student rates<br/>the answer?"}
  FB -- Yes --> SF["Store feedback"] --> stop2(("end"))
  FB -- No --> stop2
"""

DIAGRAMS["07_sequence_chat_query"] = """sequenceDiagram
  autonumber
  actor S as Student
  participant W as Chat widget (React)
  participant N as Nginx
  participant API as Flask /api/chat
  participant E as HybridRetriever
  participant DB as PostgreSQL
  S->>W: Type question and press Send
  W->>W: Show typing indicator
  W->>N: POST /api/chat {message, session_id}
  N->>API: proxy request
  API->>API: Validate input, rate-limit check
  API->>DB: SELECT faq_version (index up to date?)
  API->>E: retrieve(message)
  E->>E: detect_language, preprocess
  E->>E: TF-IDF cosine similarity
  alt TF-IDF score >= 0.75
    E-->>API: FAQ id, confidence, method = tfidf
  else below threshold
    E->>E: SBERT embedding + score fusion
    alt fused >= 0.35
      E-->>API: FAQ id, confidence, method = sbert
    else no match
      E-->>API: category, method = fallback
    end
  end
  API->>DB: SELECT faq (answer in query language)
  API->>DB: INSERT conversation_logs
  API-->>N: 200 JSON {answer, category, confidence, method, log_id}
  N-->>W: response
  W->>W: Render answer or fallback card, add to history
  W-->>S: Display answer
  opt Student rates the answer
    S->>W: Thumbs up / down
    W->>API: POST /api/feedback {log_id, helpful}
    API->>DB: INSERT feedback
  end
"""

DIAGRAMS["08_sequence_admin_add_faq"] = """sequenceDiagram
  autonumber
  actor A as Admin staff
  participant D as Admin dashboard (React)
  participant API as Flask /api/admin
  participant DB as PostgreSQL
  participant E as HybridRetriever (each worker)
  A->>D: Log in (username, password)
  D->>API: POST /api/admin/login
  API->>DB: SELECT admin_users
  API->>API: bcrypt.checkpw
  API-->>D: 200 + session cookie
  A->>D: Click Add FAQ, fill EN/AR question and answer, category, keywords
  D->>API: POST /api/admin/faqs (JSON)
  API->>API: login_required, validate fields
  alt invalid
    API-->>D: 400 {error}
    D-->>A: Show error message
  else valid
    API->>DB: INSERT faqs
    API->>DB: UPDATE settings faq_version + 1
    API-->>D: 201 {faq}
    D-->>A: Toast - FAQ added, chatbot index rebuilt
  end
  Note over E,DB: On the next student query
  E->>DB: faq_version changed?
  E->>DB: SELECT active faqs
  E->>E: Rebuild TF-IDF index, classifier, SBERT embeddings (cached)
"""

DIAGRAMS["09_dfd_level0"] = """flowchart LR
  STU["Student /<br/>applicant"]
  ADM["Admin staff"]
  P0(("0<br/>FAQ Chatbot<br/>System"))
  STU -- "question (EN/AR),<br/>feedback" --> P0
  P0 -- "verified answer / fallback +<br/>contacts, suggestions, history" --> STU
  ADM -- "credentials, FAQ changes,<br/>CSV files, settings" --> P0
  P0 -- "statistics, logs, unanswered<br/>queries, CSV export" --> ADM
"""

DIAGRAMS["10_dfd_level1"] = """flowchart TB
  STU["Student"]
  ADM["Admin staff"]
  P1(("1.0<br/>Receive and<br/>validate query"))
  P2(("2.0<br/>Detect language<br/>and preprocess"))
  P3(("3.0<br/>Retrieve answer<br/>TF-IDF, SBERT"))
  P4(("4.0<br/>Compose response<br/>or fallback"))
  P5(("5.0<br/>Log query<br/>and feedback"))
  P6(("6.0<br/>Authenticate<br/>staff"))
  P7(("7.0<br/>Manage FAQs<br/>and settings"))
  P8(("8.0<br/>Report statistics<br/>and logs"))
  D1[("D1 FAQs and categories")]
  D2[("D2 Settings")]
  D3[("D3 Conversation logs")]
  D4[("D4 Feedback")]
  D5[("D5 Admin users")]
  STU -- question --> P1
  P1 -- valid query --> P2
  P2 -- "tokens, language" --> P3
  D1 -- active FAQs --> P3
  D2 -- thresholds --> P3
  P3 -- "FAQ id, confidence, method" --> P4
  D1 -- answer text --> P4
  D2 -- contact details --> P4
  P4 -- answer --> STU
  P4 -- log record --> P5
  STU -- feedback --> P5
  P5 --> D3
  P5 --> D4
  ADM -- credentials --> P6
  D5 -- password hash --> P6
  P6 -- session --> P7
  ADM -- "FAQ edits, CSV, settings" --> P7
  P7 --> D1
  P7 --> D2
  D3 --> P8
  D4 --> P8
  P8 -- "stats, logs, unanswered" --> ADM
"""

DIAGRAMS["11_erd"] = """erDiagram
  CATEGORIES ||--o{ FAQS : "groups"
  FAQS |o--o{ CONVERSATION_LOGS : "matched by"
  CONVERSATION_LOGS ||--o{ FEEDBACK : "rated by"
  CATEGORIES {
    int id PK
    varchar name_en UK
    varchar name_ar
  }
  FAQS {
    int id PK
    text question_en
    text question_ar
    text answer
    text answer_ar
    varchar answer_lang
    int category_id FK
    text keywords
    boolean is_active
    timestamp created_at
    timestamp updated_at
  }
  CONVERSATION_LOGS {
    int id PK
    varchar session_id
    text query_text
    varchar detected_lang
    int matched_faq_id FK "nullable"
    float confidence
    varchar method "tfidf, sbert or fallback"
    varchar category
    float response_ms
    timestamp created_at
  }
  FEEDBACK {
    int id PK
    int log_id FK
    boolean helpful
    timestamp created_at
  }
  ADMIN_USERS {
    int id PK
    varchar username UK
    varchar password_hash "bcrypt"
    timestamp last_login
  }
  SETTINGS {
    varchar key PK
    varchar value
  }
"""

DIAGRAMS["12_class_diagram"] = """classDiagram
  direction LR
  class HybridRetriever {
    +float tfidf_threshold
    +float sbert_threshold
    +float fusion_weight
    +bool use_sbert
    +fit(faqs) HybridRetriever
    +retrieve(query) RetrievalResult
  }
  class TfidfRetriever {
    +float word_weight
    +float char_weight
    +fit(faqs) TfidfRetriever
    +scores(query) ndarray
    +search(query, top_k) list
  }
  class SbertRetriever {
    +str model_name
    +ndarray embeddings
    +fit(faqs) SbertRetriever
    +encode(texts) ndarray
    +scores(query) ndarray
  }
  class CategoryClassifier {
    +list labels
    +fit(faqs) CategoryClassifier
    +predict(query) str
  }
  class RetrievalResult {
    +int faq_id
    +float confidence
    +str method
    +str lang
    +str category
    +float elapsed_ms
    +list alternatives
  }
  class FaqDoc {
    +int id
    +str question_en
    +str question_ar
    +str keywords
    +str category
  }
  class Category {
    +int id
    +str name_en
    +str name_ar
  }
  class FAQ {
    +int id
    +str question_en
    +str question_ar
    +str answer
    +str answer_ar
    +bool is_active
    +to_dict() dict
  }
  class ConversationLog {
    +str session_id
    +str query_text
    +str detected_lang
    +float confidence
    +str method
    +float response_ms
    +to_dict() dict
  }
  class Feedback {
    +int log_id
    +bool helpful
  }
  class AdminUser {
    +str username
    -str password_hash
    +set_password(pw)
    +check_password(pw) bool
  }
  class Setting {
    +str key
    +str value
    +get(key)$
    +set(key, value)$
  }
  HybridRetriever *-- TfidfRetriever
  HybridRetriever *-- SbertRetriever
  HybridRetriever *-- CategoryClassifier
  HybridRetriever ..> RetrievalResult : creates
  HybridRetriever o-- FaqDoc
  FAQ ..> FaqDoc : mapped to
  Category "1" -- "*" FAQ
  FAQ "0..1" -- "*" ConversationLog
  ConversationLog "1" -- "*" Feedback
"""

DIAGRAMS["13_nlp_pipeline"] = """flowchart TB
  Q["User query<br/>كيف أدفع الرسوم؟"] --> LD["1 Language detection<br/>script ratio + langdetect"]
  LD --> N["2 Normalisation<br/>remove diacritics, tatweel<br/>unify alef, yaa, taa marbuta"]
  N --> TK["3 Tokenisation + stop-words<br/>NLTK English / Arabic list<br/>synonym glossary"]
  TK --> ST["4 Stemming<br/>Snowball (EN)<br/>light prefix/suffix (AR)"]
  ST --> TF["5 TF-IDF vector<br/>word 1-2-grams (0.6)<br/>+ char 3-5-grams (0.4)"]
  TF --> CS1{"cosine >= 0.75?"}
  CS1 -- yes --> OUT1["Answer (tfidf)"]
  CS1 -- no --> SB["6 SBERT embedding<br/>paraphrase-multilingual-<br/>MiniLM-L12-v2 (384-d)"]
  SB --> FU["7 Score fusion<br/>0.6 TF-IDF + 0.4 SBERT"]
  FU --> CS2{"fused >= 0.35?"}
  CS2 -- yes --> OUT2["Answer (sbert)"]
  CS2 -- no --> OUT3["Fallback + contacts (FR-05)"]
  OUT3 --> CLS["Category classifier<br/>TF-IDF + linear SVM"]
  KB[("FAQ index<br/>EN + AR document per FAQ<br/>cached embeddings")] -.-> TF
  KB -.-> SB
"""
