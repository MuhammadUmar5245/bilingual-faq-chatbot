# Code listing (Appendix)

Key source files of the system, copied from the repository.

| # | File | Lines | Purpose |
|---|---|---|---|
| 1 | [`backend/app/__init__.py`](01_backend__app____init__.py) | 59 | Flask application factory. |
| 2 | [`backend/app/config.py`](02_backend__app__config.py) | 65 | Application configuration loaded from environment variables (.env). |
| 3 | [`backend/app/nlp_service.py`](03_backend__app__nlp_service.py) | 83 | Bridge between the database and the NLP engine. |
| 4 | [`backend/app/seed.py`](04_backend__app__seed.py) | 106 | Database seeding: categories, default settings, default admin, FAQ CSV (FR-09). |
| 5 | [`backend/models/__init__.py`](05_backend__models____init__.py) | 160 | SQLAlchemy data model (Chapter 3.5.2 / Chapter 4.4 Data Model). |
| 6 | [`backend/routes/public.py`](06_backend__routes__public.py) | 180 | Public chatbot API used by the chat widget (FR-01..FR-05, FR-07, FR-10). |
| 7 | [`backend/routes/admin.py`](07_backend__routes__admin.py) | 402 | Admin dashboard API - login required (FR-06, FR-07, NF-05, NF-06). |
| 8 | [`backend/nlp/language.py`](08_backend__nlp__language.py) | 32 | Query language detection (FR-01). |
| 9 | [`backend/nlp/preprocess.py`](09_backend__nlp__preprocess.py) | 144 | Bilingual text preprocessing for retrieval (FR-01, FR-03, NF-02). |
| 10 | [`backend/nlp/tfidf_retriever.py`](10_backend__nlp__tfidf_retriever.py) | 115 | TF-IDF cosine-similarity retriever - the primary matcher (FR-03). |
| 11 | [`backend/nlp/sbert_retriever.py`](11_backend__nlp__sbert_retriever.py) | 85 | Sentence-BERT semantic retriever - fallback when TF-IDF confidence is low (FR-03). |
| 12 | [`backend/nlp/classifier.py`](12_backend__nlp__classifier.py) | 60 | Category classifier (FR-02). |
| 13 | [`backend/nlp/hybrid.py`](13_backend__nlp__hybrid.py) | 107 | Hybrid retrieval pipeline (FR-01, FR-02, FR-03, FR-05, NF-02). |
| 14 | [`backend/nlp/evaluate.py`](14_backend__nlp__evaluate.py) | 418 | Quasi-experiment (Chapter 3.2.1): keyword match vs TF-IDF vs SBERT vs Hybrid (NF-02). |
| 15 | [`frontend/widget/src/embed.jsx`](15_frontend__widget__src__embed.jsx) | 47 | Embeddable entry point (FR-08). A college website adds the chatbot with one tag: |
| 16 | [`frontend/widget/src/Widget.jsx`](16_frontend__widget__src__Widget.jsx) | 423 | import { useEffect, useMemo, useRef, useState } from "react"; |
| 17 | [`frontend/admin/src/App.jsx`](17_frontend__admin__src__App.jsx) | 119 | import { useCallback, useEffect, useState } from "react"; |
| 18 | [`frontend/admin/src/pages/Faqs.jsx`](18_frontend__admin__src__pages__Faqs.jsx) | 352 | import { useCallback, useEffect, useState } from "react"; |
| 19 | [`docker-compose.yml`](19_docker-compose.yml) | 55 | One command: docker compose up --build   ->  http://localhost:8088  (admin: /admin/) |
| 20 | [`backend/Dockerfile`](20_backend__Dockerfile) | 38 | Flask API + NLP engine (build context: project root) |
| 21 | [`frontend/Dockerfile`](21_frontend__Dockerfile) | 19 | Build both React apps, then serve them with Nginx (build context: project root) |
| 22 | [`frontend/nginx.conf`](22_frontend__nginx.conf) | 36 | server { |
