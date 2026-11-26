"""Sentence-BERT semantic retriever - fallback when TF-IDF confidence is low (FR-03).

Uses the multilingual paraphrase-multilingual-MiniLM-L12-v2 model, which maps English
and Arabic sentences into the same vector space, so an Arabic query can match an English
question and vice-versa. FAQ embeddings are cached on disk (keyed by a hash of the model
name and FAQ texts) so the API starts quickly and only re-encodes when FAQs change.
"""
import hashlib
import os
import threading
from pathlib import Path

import numpy as np

from nlp.tfidf_retriever import FaqDoc, faq_documents

CACHE_DIR = Path(os.getenv("NLP_CACHE_DIR", Path(__file__).resolve().parent / "cache"))

_model_lock = threading.Lock()
_models: dict = {}


def load_model(name: str):
    """Load (once per process) and return the SentenceTransformer model."""
    with _model_lock:
        if name not in _models:
            import torch
            from sentence_transformers import SentenceTransformer
            # One small model per worker: limit intra-op threads so several gunicorn workers
            # do not oversubscribe the CPU under concurrent load (NF-01).
            torch.set_num_threads(int(os.getenv("TORCH_THREADS", "2")))
            _models[name] = SentenceTransformer(name, device="cpu")
        return _models[name]


class SbertRetriever:
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2", use_cache: bool = True,
                 answer_weight: float = 0.0):
        self.answer_weight = answer_weight
        self.model_name = model_name
        self.use_cache = use_cache
        self.model = load_model(model_name)
        self.faqs: list[FaqDoc] = []
        self.owners = np.array([], dtype=int)
        self.weights = np.array([])
        self.embeddings = None

    def _cache_path(self, texts: list[str]) -> Path:
        h = hashlib.sha256((self.model_name + "\n" + "\n".join(texts)).encode("utf-8")).hexdigest()[:16]
        return CACHE_DIR / f"sbert_{h}.npy"

    def encode(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, batch_size=64, normalize_embeddings=True,
                                 convert_to_numpy=True, show_progress_bar=False)

    def fit(self, faqs: list[FaqDoc]) -> "SbertRetriever":
        self.faqs = list(faqs)
        texts, owners, weights = faq_documents(self.faqs, self.answer_weight)
        self.owners = np.array(owners, dtype=int)
        self.weights = np.array(weights)
        if not texts:
            self.embeddings = None
            return self
        path = self._cache_path(texts)
        if self.use_cache and path.exists():
            self.embeddings = np.load(path)
        else:
            self.embeddings = self.encode(texts)
            if self.use_cache:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                np.save(path, self.embeddings)
        return self

    def scores(self, query: str) -> np.ndarray:
        out = np.full(len(self.faqs), -1.0)
        if self.embeddings is None or not query.strip():
            return out
        sims = (self.embeddings @ self.encode([query])[0]) * self.weights
        np.maximum.at(out, self.owners, sims)
        return out

    def search(self, query: str, top_k: int = 3) -> list[tuple[FaqDoc, float]]:
        s = self.scores(query)
        idx = np.argsort(-s)[:top_k]
        return [(self.faqs[i], float(s[i])) for i in idx if len(self.faqs)]
