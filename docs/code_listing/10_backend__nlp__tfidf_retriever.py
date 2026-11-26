"""TF-IDF cosine-similarity retriever - the primary matcher (FR-03).

Every FAQ is indexed as two documents (English question + keywords, Arabic question),
and a query's score for an FAQ is the maximum cosine similarity over its documents.
The vector space concatenates word n-grams (stemmed tokens, 1-2 grams) with character
n-grams (3-5, word-bounded), which makes matching tolerant of misspellings and of
Arabic morphological variation that the light stemmer misses.
"""
import re
from dataclasses import dataclass

import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from nlp.preprocess import normalize_text, preprocess


@dataclass
class FaqDoc:
    """Minimal FAQ view used by the NLP layer (decoupled from the database model)."""
    id: int
    question_en: str
    question_ar: str
    keywords: str
    category: str
    answer_en: str = ""
    answer_ar: str = ""


_ARABIC = re.compile(r"[؀-ۿ]")


def split_keywords(keywords: str) -> tuple[str, str]:
    """Split the comma-separated keyword list into English and Arabic keywords."""
    parts = [k.strip() for k in re.split(r"[,،]", keywords or "") if k.strip()]
    return (", ".join(k for k in parts if not _ARABIC.search(k)),
            "، ".join(k for k in parts if _ARABIC.search(k)))


def faq_documents(faqs: list[FaqDoc], answer_weight: float = 0.0):
    """Expand FAQs into documents.

    Returns (texts, owner index, weight). Each FAQ gives an English document (question +
    keywords) and an Arabic document (question) with weight 1.0; when answer_weight > 0 the
    answers are added as extra documents whose similarity is down-weighted, so a query that
    only matches answer vocabulary can still find the FAQ but never outranks a question match.
    """
    texts, owners, weights = [], [], []

    def add(text, i, w):
        if text and w > 0:
            texts.append(text.strip())
            owners.append(i)
            weights.append(w)

    for i, f in enumerate(faqs):
        kw_en, kw_ar = split_keywords(f.keywords)
        add(f"{f.question_en} {kw_en}", i, 1.0)
        add(f"{f.question_ar} {kw_ar}", i, 1.0)
        add(f.answer_en, i, answer_weight)
        add(f.answer_ar, i, answer_weight)
    return texts, owners, weights


class TfidfRetriever:
    def __init__(self, word_weight: float = 0.6, char_weight: float = 0.4, answer_weight: float = 0.0):
        self.answer_weight = answer_weight
        self.word_weight = word_weight
        self.char_weight = char_weight
        self.word_vec = TfidfVectorizer(analyzer=str.split, sublinear_tf=True)
        self.char_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True, min_df=1)
        self.faqs: list[FaqDoc] = []
        self.owners = np.array([], dtype=int)
        self.weights = np.array([])
        self.matrix = None

    @staticmethod
    def _word_tokens(text: str) -> list[str]:
        toks = preprocess(text).split()
        return toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]

    def _vectorize(self, texts: list[str], fit: bool = False):
        words = [" ".join(self._word_tokens(t)) for t in texts]
        chars = [normalize_text(t) for t in texts]
        if fit:
            w = self.word_vec.fit_transform(words)
            c = self.char_vec.fit_transform(chars)
        else:
            w = self.word_vec.transform(words)
            c = self.char_vec.transform(chars)
        return normalize(hstack([w * np.sqrt(self.word_weight), c * np.sqrt(self.char_weight)]).tocsr())

    def fit(self, faqs: list[FaqDoc]) -> "TfidfRetriever":
        self.faqs = list(faqs)
        texts, owners, weights = faq_documents(self.faqs, self.answer_weight)
        self.owners = np.array(owners, dtype=int)
        self.weights = np.array(weights)
        self.matrix = self._vectorize(texts, fit=True) if texts else None
        return self

    def scores(self, query: str) -> np.ndarray:
        """Cosine similarity of the query to every FAQ (max over its documents)."""
        out = np.zeros(len(self.faqs))
        if self.matrix is None or not query.strip():
            return out
        sims = (self._vectorize([query]) @ self.matrix.T).toarray().ravel() * self.weights
        np.maximum.at(out, self.owners, sims)
        return out

    def search(self, query: str, top_k: int = 3) -> list[tuple[FaqDoc, float]]:
        s = self.scores(query)
        idx = np.argsort(-s)[:top_k]
        return [(self.faqs[i], float(s[i])) for i in idx if len(self.faqs)]
