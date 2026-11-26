"""Check that no FAQ keyword phrase copies a test query (NF-02 evaluation validity, Section 5.2.3).

Usage (from backend/):  python -m nlp.check_keyword_leakage

A keyword phrase "leaks" if, after normalisation, it is identical to a test query. The check reads
the query text of BOTH splits, because a copied held-out query would inflate held-out accuracy;
it can only remove keywords, never add them, so it cannot make held-out results look better.
Exit code 1 if a keyword copies a HELD-OUT query (overlap with tuning queries only affects
tuning-split figures and is reported as a warning).
"""
import sys

from nlp.evaluate import load_faqs, load_queries
from nlp.preprocess import normalize_text


def norm(s: str) -> str:
    return " ".join(normalize_text(s).replace("?", " ").replace("؟", " ").split())


def main() -> int:
    faqs, queries = load_faqs(), load_queries()
    by_text = {}
    for q in queries:
        by_text.setdefault(norm(q["query"]), []).append(q)
    leaks = []
    for f in faqs:
        for phrase in (p.strip() for p in f.keywords.split(",")):
            for q in by_text.get(norm(phrase), []) if phrase else []:
                split = "tuning" if int(q["query_id"]) % 2 else "held-out"
                leaks.append((f.id, phrase, q["query_id"], split))
    n_phrases = sum(len([p for p in f.keywords.split(",") if p.strip()]) for f in faqs)
    print(f"{n_phrases} keyword phrases in {len(faqs)} FAQs checked against {len(queries)} test queries")
    for faq_id, phrase, qid, split in leaks:
        print(f"  LEAK FAQ #{faq_id} keyword '{phrase}' == query {qid} ({split})")
    held = sum(1 for leak in leaks if leak[3] == "held-out")
    print(f"Matches: {len(leaks)} ({len(leaks) - held} tuning, {held} held-out)")
    return 1 if held else 0


if __name__ == "__main__":
    sys.exit(main())
