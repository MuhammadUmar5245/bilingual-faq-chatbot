"""Unit tests - text preprocessing and language detection (FR-01, NF-02)."""
from nlp.language import detect_language
from nlp.preprocess import normalize_arabic, normalize_text, preprocess, stem_arabic, tokenize


class TestArabicNormalisation:
    def test_removes_diacritics(self):
        assert normalize_arabic("الدِّرَاسَةُ") == "الدراسه"

    def test_removes_tatweel(self):
        assert normalize_arabic("الـــرسوم") == "الرسوم"

    def test_unifies_alef_forms(self):
        assert normalize_arabic("أإآا") == "اااا"

    def test_unifies_yaa_and_taa_marbuta(self):
        assert normalize_arabic("على") == "علي"
        assert normalize_arabic("مدرسة") == "مدرسه"

    def test_hamza_carriers(self):
        assert normalize_arabic("مؤسسة") == "موسسه"
        assert normalize_arabic("رئيس") == "رييس"

    def test_arabic_digits_converted(self):
        assert normalize_arabic("٢٠٢٤") == "2024"


class TestArabicStemming:
    def test_strips_definite_article(self):
        assert stem_arabic("الرسوم") == "رسوم"

    def test_strips_prefix_and_suffix(self):
        assert stem_arabic("والمقررات") == "مقرر"

    def test_keeps_short_words(self):
        assert stem_arabic("الى") == "الى"  # stripping would leave fewer than 3 letters

    def test_spelling_variants_share_a_stem(self):
        assert preprocess("الدراسة") == preprocess("الدراسه") == preprocess("دراسي")


class TestTokenize:
    def test_english_stopwords_removed_but_question_words_kept(self):
        toks = tokenize("When is the final exam?", stem=False)
        assert "when" in toks and "the" not in toks and "is" not in toks

    def test_english_stemming(self):
        assert tokenize("registering registration", remove_stop=False) == ["regist", "registr"]

    def test_arabic_stopwords_removed(self):
        assert "في" not in tokenize("ما هي الرسوم في الكلية", stem=False)

    def test_abbreviation_expansion(self):
        assert "foundat" in tokenize("GFP")

    def test_resit_variants_unified(self):
        assert preprocess("re-sit") == preprocess("resit") == preprocess("re sit")

    def test_colloquial_arabic_synonym_after_prefix(self):
        assert "هاتف" in tokenize("بالجوال", stem=False)

    def test_mixed_language_query(self):
        toks = tokenize("رسوم IELTS")
        assert "رسوم" in toks and "ielt" in toks

    def test_empty_and_punctuation_only(self):
        assert tokenize("") == [] and tokenize("?!...") == []

    def test_normalize_text_lowercases_and_strips_punctuation(self):
        assert normalize_text("Hello, WORLD!") == "hello world"


class TestLanguageDetection:
    def test_english(self):
        assert detect_language("How much are the tuition fees?") == "en"

    def test_arabic(self):
        assert detect_language("كم تبلغ الرسوم الدراسية؟") == "ar"

    def test_short_arabic(self):
        assert detect_language("الرسوم") == "ar"

    def test_short_english(self):
        assert detect_language("fees") == "en"

    def test_mixed_mostly_arabic(self):
        assert detect_language("ما هي درجة IELTS المطلوبة") == "ar"

    def test_empty_defaults_to_english(self):
        assert detect_language("") == "en" and detect_language("123") == "en"
