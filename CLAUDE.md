# CLAUDE.md — Oman College FAQ Chatbot (GIS6001 Dissertation)

## What this is
Bilingual (English + Arabic) FAQ chatbot for colleges in Oman. Students ask
questions in natural language; the system retrieves the best matching answer
from a verified FAQ knowledge base. Staff manage FAQs through an admin
dashboard without coding. This is a dissertation prototype — code, results,
diagrams and screenshots all feed into the written report.

## Source of truth
- docs/dissertation_ch1-3.txt — objectives, scope, SRS (Chapters 1–3)
- docs/requirements.md — FR/NF requirement IDs (must stay traceable)
- docs/report_template_structure.txt — what Chapters 4–6 and Appendices need
- BUILD_PROMPT.md — the phased build plan

## Fixed stack (do not change — it is written into the report)
- Python 3.10+, Flask 3, Flask-SQLAlchemy, Flask-Login, bcrypt
- NLP: TF-IDF (scikit-learn) primary + sentence-BERT
  (paraphrase-multilingual-MiniLM-L12-v2) fallback, langdetect, NLTK,
  Arabic normalisation (CAMeL Tools or custom)
- React 18 (Vite) + Axios — chat widget + admin dashboard
- PostgreSQL 14 (Docker) / SQLite (dev + tests)
- Docker Compose: api, web (Nginx), db
- Retrieval only — the chatbot never generates answers (no hallucination)

## Conventions
- Reference requirement IDs (FR-xx / NF-xx) in docstrings, tests and test cases.
- Default TF-IDF confidence threshold 0.75 (stored in settings table, editable).
- Six categories: Admissions, Registration, Fees, Academic Programmes,
  Examinations, Student Services.
- Never hard-code or fabricate evaluation numbers or survey responses.
  Results must come from actually running the scripts.
- FAQ data in data/faqs_seed.csv is SAMPLE data until replaced with real
  college FAQs. Keep the CSV format stable so it can be swapped later.
- Commit after every phase; keep PROGRESS.md updated with what is done,
  what is next, and current metrics.

## Resuming after /clear
Read CLAUDE.md and PROGRESS.md, then continue from the next unfinished phase
in BUILD_PROMPT.md.
