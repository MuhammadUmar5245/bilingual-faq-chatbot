"""Hybrid retrieval pipeline (FR-01, FR-02, FR-03, FR-05, NF-02).

Flow (Chapter 3, Figure 4 - Activity Diagram):
    detect language -> preprocess -> TF-IDF cosine
      -> score >= tfidf_threshold            : answer (method = "tfidf")
      -> else SBERT semantic similarity, fused with the TF-IDF evidence:
             fused = w * tfidf + (1 - w) * sbert   (w = fusion_weight; w = 0 -> pure SBERT)
           -> fused >= sbert_threshold       : answer (method = "sbert")
           -> else                           : fallback message (method = "fallback", FR-05)

The chatbot is retrieval-only: it always returns a verified FAQ answer or the fallback,
never generated text.
"""
import threading
import time
from dataclasses import dataclass, field

from nlp.classifier import CategoryClassifier
from nlp.language import detect_language
from nlp.tfidf_retriever import FaqDoc, TfidfRetriever


@dataclass
class RetrievalResult:
    faq_id: int | None
    confidence: float
    method: str              # tfidf | sbert | fallback
    lang: str                # en | ar
    category: str | None
    tfidf_score: float = 0.0
    sbert_score: float | None = None
    elapsed_ms: float = 0.0
    alternatives: list = field(default_factory=list)  # [(faq_id, score)] near misses


class HybridRetriever:
    def __init__(self, tfidf_threshold: float = 0.75, sbert_threshold: float = 0.35,
                 use_sbert: bool = True, sbert_model: str = "paraphrase-multilingual-MiniLM-L12-v2",
                 sbert_cache: bool = True, fusion_weight: float = 0.6):
        self.fusion_weight = fusion_weight
        self.tfidf_threshold = tfidf_threshold
        self.sbert_threshold = sbert_threshold
        self.use_sbert = use_sbert
        self.sbert_model = sbert_model
        self.sbert_cache = sbert_cache
        self.tfidf = TfidfRetriever()
        self.sbert = None
        self.classifier = CategoryClassifier()
        self.faqs: list[FaqDoc] = []
        self._lock = threading.RLock()

    def fit(self, faqs: list[FaqDoc]) -> "HybridRetriever":
        """(Re)build all indexes. Called at start-up and whenever an admin changes FAQs."""
        faqs = list(faqs)
        tfidf = TfidfRetriever().fit(faqs)
        clf = CategoryClassifier().fit(faqs)
        sbert = None
        if self.use_sbert:
            from nlp.sbert_retriever import SbertRetriever
            sbert = SbertRetriever(self.sbert_model, use_cache=self.sbert_cache).fit(faqs)
        with self._lock:  # swap atomically so concurrent requests never see a half-built index
            self.faqs, self.tfidf, self.classifier, self.sbert = faqs, tfidf, clf, sbert
        return self

    def retrieve(self, query: str) -> RetrievalResult:
        start = time.perf_counter()
        with self._lock:
            faqs, tfidf, sbert, clf = self.faqs, self.tfidf, self.sbert, self.classifier
        lang = detect_language(query)
        if not faqs:
            return RetrievalResult(None, 0.0, "fallback", lang, None,
                                   elapsed_ms=(time.perf_counter() - start) * 1000)

        t_scores = tfidf.scores(query)
        t_best = int(t_scores.argmax())
        t_score = float(t_scores[t_best])
        s_score = None

        if t_score >= self.tfidf_threshold:
            faq, conf, method, scores = faqs[t_best], t_score, "tfidf", t_scores
        elif sbert is not None:
            w = self.fusion_weight
            s_scores = (1 - w) * sbert.scores(query) + w * t_scores
            s_best = int(s_scores.argmax())
            s_score = float(s_scores[s_best])
            if s_score >= self.sbert_threshold:
                faq, conf, method, scores = faqs[s_best], s_score, "sbert", s_scores
            else:
                faq, conf, method, scores = None, s_score, "fallback", s_scores
        else:
            faq, conf, method, scores = None, t_score, "fallback", t_scores

        top = scores.argsort()[::-1][:4]
        alternatives = [(faqs[i].id, round(float(scores[i]), 4)) for i in top
                        if faq is None or faqs[i].id != faq.id][:3]
        category = faq.category if faq else clf.predict(query)
        return RetrievalResult(
            faq_id=faq.id if faq else None,
            confidence=round(conf, 4),
            method=method,
            lang=lang,
            category=category,
            tfidf_score=round(t_score, 4),
            sbert_score=round(s_score, 4) if s_score is not None else None,
            elapsed_ms=(time.perf_counter() - start) * 1000,
            alternatives=alternatives,
        )
