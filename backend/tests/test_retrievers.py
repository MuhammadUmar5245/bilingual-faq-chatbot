"""Unit tests - TF-IDF / SBERT retrievers, category classifier and hybrid pipeline (FR-02, FR-03, FR-05)."""
import csv

import numpy as np
import pytest

from app.config import DATA_DIR
from nlp.classifier import CategoryClassifier
from nlp.hybrid import HybridRetriever
from nlp.tfidf_retriever import FaqDoc, TfidfRetriever, split_keywords


@pytest.fixture(scope="module")
def faqs():
    with open(DATA_DIR / "faqs_seed.csv", encoding="utf-8") as f:
        return [FaqDoc(i, r["question_en"], r["question_ar"], r["keywords"], r["category"], r["answer"], r["answer_ar"])
                for i, r in enumerate(csv.DictReader(f), start=1)]


@pytest.fixture(scope="module")
def tfidf(faqs):
    return TfidfRetriever().fit(faqs)


class TestTfidf:
    def test_exact_english_question_scores_highest(self, tfidf, faqs):
        top, score = tfidf.search(faqs[10].question_en, top_k=1)[0]
        assert top.id == faqs[10].id and score >= 0.75  # above the default threshold

    def test_exact_arabic_question_scores_highest(self, tfidf, faqs):
        top, score = tfidf.search(faqs[70].question_ar, top_k=1)[0]
        assert top.id == faqs[70].id and score >= 0.75

    def test_scores_are_cosine_similarities(self, tfidf):
        s = tfidf.scores("hostel fees")
        assert s.shape == (210,) and s.min() >= 0 and s.max() <= 1.0 + 1e-9

    def test_misspelling_still_matches(self, tfidf):
        top, _ = tfidf.search("tution fess for bachelor", top_k=1)[0]
        assert top.category == "Fees"

    def test_empty_query_returns_zeros(self, tfidf):
        assert not tfidf.scores("   ").any()

    def test_empty_knowledge_base(self):
        r = TfidfRetriever().fit([])
        assert r.scores("anything").size == 0

    def test_split_keywords_by_script(self):
        en, ar = split_keywords("fees, tuition, الرسوم، التكلفة")
        assert en == "fees, tuition" and "الرسوم" in ar and "التكلفة" in ar


class TestClassifier:
    def test_predicts_all_six_categories(self, faqs):
        clf = CategoryClassifier().fit(faqs)
        assert set(clf.labels) == {"Admissions", "Registration", "Fees", "Academic Programmes",
                                   "Examinations", "Student Services"}

    @pytest.mark.parametrize("query,expected", [
        ("how much is the tuition", "Fees"),
        ("when are the final exams", "Examinations"),
        ("is there a hostel", "Student Services"),
        ("ما هي شروط القبول", "Admissions"),
    ])
    def test_predictions(self, faqs, query, expected):
        assert CategoryClassifier().fit(faqs).predict(query) == expected

    def test_single_category_fallback(self, faqs):
        clf = CategoryClassifier().fit([faqs[0]])
        assert clf.predict("anything") == "Admissions"


class TestHybridTfidfOnly:
    """Hybrid pipeline with SBERT disabled - exercises the TF-IDF stage and the fallback."""

    def test_exact_question_answered_by_tfidf(self, faqs):
        h = HybridRetriever(use_sbert=False).fit(faqs)
        r = h.retrieve(faqs[5].question_en)
        assert r.method == "tfidf" and r.faq_id == faqs[5].id and r.confidence >= 0.75

    def test_low_score_goes_to_fallback(self, faqs):
        h = HybridRetriever(use_sbert=False).fit(faqs)
        r = h.retrieve("who won the football match yesterday")
        assert r.method == "fallback" and r.faq_id is None
        assert r.category in {"Admissions", "Registration", "Fees", "Academic Programmes", "Examinations",
                              "Student Services"}  # FR-02: still classified

    def test_language_and_timing_reported(self, faqs):
        r = HybridRetriever(use_sbert=False).fit(faqs).retrieve(faqs[0].question_ar)
        assert r.lang == "ar" and r.elapsed_ms > 0

    def test_empty_knowledge_base_falls_back(self):
        r = HybridRetriever(use_sbert=False).fit([]).retrieve("fees")
        assert r.method == "fallback"


@pytest.mark.sbert
class TestSbert:
    @pytest.fixture(scope="class")
    def hybrid(self, faqs):
        return HybridRetriever(use_sbert=True).fit(faqs)

    def test_cross_lingual_semantic_match(self, faqs):
        from nlp.sbert_retriever import SbertRetriever
        s = SbertRetriever().fit(faqs)
        # Arabic wording with no word in common with the English question "Is there a dress code?"
        top, score = s.search("هل يوجد زي رسمي للطلاب", top_k=1)[0]
        assert top.question_en == "Is there a dress code?" and 0 < score <= 1
        top, _ = s.search("Can I live on campus?", top_k=1)[0]
        assert top.question_en == "Does the college provide hostel accommodation?"

    def test_paraphrase_uses_sbert_stage(self, hybrid):
        r = hybrid.retrieve("i was ill and missed the final")
        assert r.method == "sbert" and r.category == "Examinations"

    def test_out_of_scope_fallback(self, hybrid):
        r = hybrid.retrieve("write python code to sort a list")
        assert r.method == "fallback"

    def test_embeddings_cached_on_disk(self, faqs):
        from nlp.sbert_retriever import SbertRetriever
        s1 = SbertRetriever().fit(faqs)
        texts = [d for d in __import__("nlp.tfidf_retriever", fromlist=["faq_documents"]).faq_documents(faqs)[0]]
        assert s1._cache_path(texts).exists()
        s2 = SbertRetriever().fit(faqs)
        assert np.allclose(s1.embeddings, s2.embeddings)
