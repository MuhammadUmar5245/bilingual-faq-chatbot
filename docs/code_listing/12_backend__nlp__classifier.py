"""Category classifier (FR-02).

Classifies every query into one of the six FAQ categories. When the retriever finds an
FAQ, the category of that FAQ is used; the classifier is still applied to unanswered
(fallback) queries so administrators can see which area they belong to.
Model: TF-IDF (same preprocessing as retrieval) + linear SVM trained on FAQ questions
in both languages plus their keywords.
"""
from collections import Counter

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC

from nlp.preprocess import normalize_text, preprocess
from nlp.tfidf_retriever import FaqDoc


class CategoryClassifier:
    def __init__(self):
        self.vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True)
        self.word_vec = TfidfVectorizer(analyzer=str.split, sublinear_tf=True)
        self.model = LinearSVC(C=1.0)
        self.labels: list[str] = []
        self.fitted = False

    def _features(self, texts, fit=False):
        from scipy.sparse import hstack
        chars = [normalize_text(t) for t in texts]
        words = [preprocess(t) for t in texts]
        if fit:
            return hstack([self.vec.fit_transform(chars), self.word_vec.fit_transform(words)]).tocsr()
        return hstack([self.vec.transform(chars), self.word_vec.transform(words)]).tocsr()

    def fit(self, faqs: list[FaqDoc]) -> "CategoryClassifier":
        texts, y = [], []
        for f in faqs:
            for t in (f.question_en, f.question_ar, f.keywords, f"{f.question_en} {f.keywords}"):
                if t:
                    texts.append(t)
                    y.append(f.category)
        self.labels = sorted(set(y))
        if len(self.labels) >= 2:
            self.model.fit(self._features(texts, fit=True), y)
            self.fitted = True
        else:
            self.fitted = False
            self._only = Counter(y).most_common(1)[0][0] if y else None
        return self

    def predict(self, query: str) -> str | None:
        if not self.fitted:
            return getattr(self, "_only", None)
        return str(self.model.predict(self._features([query]))[0])

    def decision(self, query: str) -> dict[str, float]:
        if not self.fitted:
            return {}
        d = self.model.decision_function(self._features([query]))[0]
        return {lbl: float(v) for lbl, v in zip(self.model.classes_, np.atleast_1d(d))}
