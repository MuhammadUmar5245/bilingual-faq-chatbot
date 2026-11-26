"""Generate docs/important_code.md and docs/code_listing/ from the real source files.

Usage (from the project root):  .venv/Scripts/python docs/build_code_docs.py
Code snippets are extracted with `inspect`, so the document always matches the code.
"""
import inspect
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app import nlp_service  # noqa: E402
from nlp import hybrid, preprocess  # noqa: E402
from routes import admin, public  # noqa: E402


def src(obj) -> str:
    return inspect.getsource(obj).rstrip()


def block(code: str, lang="python") -> str:
    return f"```{lang}\n{code}\n```"


def file_excerpt(path: Path, start: str, end: str | None = None) -> str:
    text = path.read_text(encoding="utf-8")
    i = text.index(start)
    j = text.index(end, i) if end else len(text)
    return text[i:j].rstrip()


SECTIONS = [
    (
        "1. Hybrid retriever — TF-IDF first, SBERT fallback with score fusion",
        "backend/nlp/hybrid.py — `HybridRetriever.retrieve`",
        lambda: block(src(hybrid.HybridRetriever.retrieve)),
        """This method is the core of the NLP pipeline (FR-01, FR-02, FR-03, FR-05). It detects the
query language, computes TF-IDF cosine similarity against every active FAQ and accepts the best
match directly when the score reaches the configurable threshold (0.75 by default). Otherwise the
sentence-BERT model is used as the fallback stage: its semantic similarity is fused with the TF-IDF
evidence (`fused = w·TF-IDF + (1−w)·SBERT`, w = 0.6) and the best FAQ is accepted if the fused
score reaches the SBERT-stage threshold (0.35). If neither stage is confident the result is a
fallback, and the category classifier still assigns one of the six categories so the query can be
analysed by staff. The indexes are read under a lock and swapped atomically when they are rebuilt,
so concurrent requests never see a half-built index. The method never generates text — it only
returns the id of a verified FAQ, which is what keeps the chatbot free of hallucinations.""",
    ),
    (
        "2. Arabic preprocessing — normalisation and light stemming",
        "backend/nlp/preprocess.py — `normalize_arabic`, `stem_arabic`, `tokenize`",
        lambda: block("\n\n\n".join([src(preprocess.normalize_arabic), src(preprocess._strip_ar_prefix),
                                     src(preprocess.stem_arabic), src(preprocess.tokenize)])),
        """Arabic words appear in many written forms: with or without diacritics, with different
alef/hamza shapes, taa marbuta (ة) or haa (ه), and with attached prefixes such as the article
"ال" or the conjunction "و". `normalize_arabic` removes diacritics and tatweel and unifies these
letter variants; `stem_arabic` strips one common prefix and one common suffix while keeping at least
three letters, so "الدراسة", "الدراسه" and "دراسي" all become the same stem. `tokenize` routes each
token by script, so English tokens go through NLTK stop-word removal and Snowball stemming while
Arabic tokens use the custom pipeline, and mixed queries ("رسوم IELTS") work. A small domain
glossary maps abbreviations (GFP, HEAC, MoHERI) and Gulf colloquial words (جوال → هاتف) to the
vocabulary of the knowledge base. CAMeL Tools was evaluated but not used because it requires
older versions of libraries that sentence-transformers depends on (see the tuning log).""",
    ),
    (
        "3. Chat endpoint — validation, retrieval, bilingual answer, logging",
        "backend/routes/public.py — `POST /api/chat`",
        lambda: block(src(public.chat)),
        """The public endpoint used by the widget. It is rate-limited per IP (NF-05), validates the
JSON body (non-empty text, at most 500 characters) and calls the retrieval engine. When an FAQ is
found the answer is returned in the language the student wrote in (the Arabic answer for Arabic
queries, FR-01) together with the category and confidence; otherwise the fallback message is
returned with the escalation contact details stored in the settings table (FR-05). Near misses are
returned as "Did you mean…?" suggestions. Every query — answered or not — is written to
`conversation_logs` with the session id, detected language, matched FAQ, confidence, method,
category and measured response time (FR-07), which feeds the admin statistics and the
unanswered-queries list.""",
    ),
    (
        "4. FAQ management with automatic index rebuild",
        "backend/routes/admin.py — `create_faq`, `toggle_faq`; backend/app/nlp_service.py — `bump_faq_version`, `get_engine`",
        lambda: block("\n\n\n".join([src(admin.create_faq), src(admin.toggle_faq),
                                     src(nlp_service.bump_faq_version), src(nlp_service.get_engine)])),
        """Staff manage FAQs through the dashboard without code (FR-06, NF-06). Every change —
create, update, enable/disable, delete or CSV import — is protected by `@login_required` (NF-05),
validated, saved, and then `bump_faq_version()` increments a version number stored in the
database. Each API worker process keeps its own retrieval engine; on every chat request
`get_engine()` compares its version with the database and rebuilds the TF-IDF index, the category
classifier and the SBERT embeddings (cached on disk by content hash) when they differ. This keeps
several gunicorn workers consistent without restarting the service, so a new FAQ is answerable on
the very next question (screenshot 21). Threshold changes made in Settings are applied without a
rebuild.""",
    ),
    (
        "5. Embeddable widget — one script tag, isolated with Shadow DOM",
        "frontend/widget/src/embed.jsx",
        lambda: block((ROOT / "frontend/widget/src/embed.jsx").read_text(encoding="utf-8").rstrip(), "jsx")
        + "\n\nEmbedding on any college page (FR-08):\n\n"
        + block('<script src="https://chatbot.college.edu.om/widget.js"\n        data-title="Gulf College Assistant" data-lang="en" defer></script>', "html"),
        """The widget is built by Vite in library mode into one self-contained `widget.js` file
(React, Axios and CSS included). When a college website loads it, the script reads optional
`data-*` attributes from its own `<script>` tag (API address, default language, title), creates a
host element, attaches a Shadow DOM and renders the React chat widget inside it with its
stylesheet. The Shadow DOM isolates the widget completely: the college's CSS cannot break the
chat, and the chat's CSS cannot change the college page. By default the API address is the
origin the script was loaded from, so the only integration needed is the single `<script>` tag —
demonstrated by `docs/demo-college-site.html` (screenshot 01) and test cases TC24–TC25.""",
    ),
]

LISTING = [
    "backend/app/__init__.py", "backend/app/config.py", "backend/app/nlp_service.py", "backend/app/seed.py",
    "backend/models/__init__.py", "backend/routes/public.py", "backend/routes/admin.py",
    "backend/nlp/language.py", "backend/nlp/preprocess.py", "backend/nlp/tfidf_retriever.py",
    "backend/nlp/sbert_retriever.py", "backend/nlp/classifier.py", "backend/nlp/hybrid.py", "backend/nlp/evaluate.py",
    "frontend/widget/src/embed.jsx", "frontend/widget/src/Widget.jsx", "frontend/admin/src/App.jsx",
    "frontend/admin/src/pages/Faqs.jsx", "docker-compose.yml", "backend/Dockerfile", "frontend/Dockerfile",
    "frontend/nginx.conf",
]


def main():
    out = ["# Discussion of important code (Chapter 5.1.3)", "",
           "Generated by `docs/build_code_docs.py` from the actual source files.", ""]
    for title, where, code, text in SECTIONS:
        out += [f"## {title}", "", f"*Source: {where}*", "", code(), "", "**Explanation.** " + re.sub(r"\s*\n\s*", " ", text), ""]
    (ROOT / "docs" / "important_code.md").write_text("\n".join(out), encoding="utf-8")

    dest = ROOT / "docs" / "code_listing"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir()
    index = ["# Code listing (Appendix)", "", "Key source files of the system, copied from the repository.", "",
             "| # | File | Lines | Purpose |", "|---|---|---|---|"]
    for n, rel in enumerate(LISTING, 1):
        p = ROOT / rel
        text = p.read_text(encoding="utf-8")
        name = f"{n:02d}_" + rel.replace("/", "__")
        (dest / name).write_text(text, encoding="utf-8")
        first = next((l.strip(' "#/*') for l in text.splitlines() if l.strip(' "#/*')), "")
        index.append(f"| {n} | [`{rel}`]({name}) | {len(text.splitlines())} | {first[:90]} |")
    (dest / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    print("wrote docs/important_code.md and", len(LISTING), "files to docs/code_listing/")


if __name__ == "__main__":
    main()
