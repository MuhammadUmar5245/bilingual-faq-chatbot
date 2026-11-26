"""Bilingual text preprocessing for retrieval (FR-01, FR-03, NF-02).

English: lower-casing, domain abbreviation expansion, NLTK stop-word removal
(question words are kept because they carry intent), Snowball stemming.

Arabic: custom normaliser (CAMeL Tools was evaluated but rejected because it pins
older transformers/tokenizers versions that conflict with sentence-transformers):
  * remove diacritics (tashkeel) and tatweel
  * unify alef forms (أ إ آ ٱ -> ا), alef maqsura (ى -> ي), taa marbuta (ة -> ه),
    hamza carriers (ؤ -> و, ئ -> ي)
  * remove Arabic stop words (MSA + common Gulf colloquial fillers)
  * light stemming: strip common prefixes (ال، وال، بال، لل ...) and suffixes (ات، ون، ين، ها، ه ...)

Each token is routed by script, so mixed Arabic/English queries are handled.
"""
import re

from nltk.stem.snowball import SnowballStemmer

ARABIC_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭ]")
TATWEEL = "ـ"
ARABIC_CHAR = re.compile(r"[ء-ي]")
TOKEN_RE = re.compile(r"[ء-ي]+|[a-z0-9]+")

_ALEF_MAP = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"})
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

# Question words are deliberately NOT stop words: "when" vs "how much" changes the intent.
_KEEP = {"what", "when", "where", "how", "who", "which", "why", "can", "not", "no"}
_EN_FALLBACK_STOP = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being", "am", "do", "does", "did",
    "i", "me", "my", "we", "our", "you", "your", "he", "she", "it", "its", "they", "them", "their",
    "this", "that", "these", "those", "of", "to", "in", "on", "at", "for", "with", "by", "from",
    "and", "or", "if", "so", "as", "about", "into", "there", "here", "any", "some", "will", "would",
    "should", "could", "have", "has", "had", "get", "please", "tell", "want", "need", "know",
}
try:
    from nltk.corpus import stopwords as _sw
    EN_STOP = (set(_sw.words("english")) | {"please", "tell", "want", "need", "know", "get"}) - _KEEP
except LookupError:  # NLTK corpus not downloaded - use the built-in list
    EN_STOP = _EN_FALLBACK_STOP - _KEEP

# Arabic stop words, written in normalised form (after _ALEF_MAP).
AR_STOP = {
    "في", "من", "الي", "علي", "عن", "مع", "هذا", "هذه", "ذلك", "تلك", "التي", "الذي", "الذين",
    "هل", "ما", "ماذا", "و", "او", "ثم", "ان", "انا", "انت", "هو", "هي", "نحن", "هم", "كان",
    "يكون", "لا", "لم", "لن", "قد", "كل", "اي", "لي", "لك", "به", "بها", "فيه", "فيها", "عليه",
    "منه", "يا", "عند", "اذا", "لكن", "حتي", "بعض", "غير", "اريد", "ابغي", "ابي", "ايش", "شو",
    "وش", "يوجد", "توجد", "هناك", "ممكن", "يمكن", "يمكنني", "استطيع", "اود", "لو", "الرجاء",
}
_AR_PREFIXES = ("وال", "بال", "كال", "فال", "لل", "ال")
_AR_SUFFIXES = ("ات", "ون", "ان", "ها", "هم", "يه", "ه", "ي")

# Domain glossary: abbreviations, spelling variants and colloquial terms -> canonical words.
EN_SYNONYMS = {
    "gfp": "general foundation programme",
    "heac": "higher education admission centre",
    "moheri": "ministry higher education scholarship",
    "cgpa": "cumulative gpa",
    "ojt": "on job training internship",
    "noc": "no objection letter",
    "mba": "master business administration",
    "bba": "bachelor business administration",
    "fyp": "final year project",
    "uni": "university",
    "id": "id card",
    "wifi": "wi fi wireless internet",
    "program": "programme",
    "programs": "programmes",
    "center": "centre",
    "counseling": "counselling",
    "enroll": "enrol",
    "enrollment": "enrolment",
    "installments": "instalments",
    "installment": "instalment",
    "finals": "final exams",
    "majors": "programmes",
    "major": "specialisation",
}
AR_SYNONYMS = {  # normalised Arabic -> canonical normalised Arabic
    "باص": "حافله", "باصات": "حافلات", "جوال": "هاتف", "موبايل": "هاتف",
    "باسورد": "كلمه مرور", "ايميل": "بريد الكتروني", "ايلتس": "اختبار ايلتس",
    "المواد": "المقررات", "ماده": "مقرر",
}

_stemmer = SnowballStemmer("english")


def normalize_arabic(text: str) -> str:
    """Orthographic normalisation of Arabic text."""
    text = ARABIC_DIACRITICS.sub("", text).replace(TATWEEL, "")
    return text.translate(_ALEF_MAP).translate(_ARABIC_DIGITS)


def _strip_ar_prefix(token: str) -> str:
    for p in _AR_PREFIXES:
        if token.startswith(p) and len(token) - len(p) >= 3:
            return token[len(p):]
    if token[:1] in ("و", "ب") and len(token) > 4:
        return token[1:]
    return token


def stem_arabic(token: str) -> str:
    """Light stemmer: strip one common prefix and one common suffix, keeping >= 3 letters."""
    token = _strip_ar_prefix(token)
    for s in _AR_SUFFIXES:
        if token.endswith(s) and len(token) - len(s) >= 3:
            token = token[: -len(s)]
            break
    return token


def normalize_text(text: str) -> str:
    """Lower-case, normalise Arabic, unify punctuation - no token removal."""
    text = normalize_arabic(text or "").lower()
    text = re.sub(r"\bre[\s-]+(sit|mark|take)", r"re\1", text)  # re-sit -> resit
    text = re.sub(r"[-_/]", " ", text)
    return " ".join(TOKEN_RE.findall(text))


def tokenize(text: str, stem: bool = True, remove_stop: bool = True) -> list[str]:
    """Normalise and tokenise text into retrieval tokens (script-aware)."""
    out = []
    for tok in normalize_text(text).split():
        is_ar = bool(ARABIC_CHAR.match(tok))
        if is_ar:
            base = _strip_ar_prefix(tok)
            expanded = AR_SYNONYMS.get(tok, AR_SYNONYMS.get(base, tok)).split()
        else:
            expanded = EN_SYNONYMS.get(tok, tok).split()
        for t in expanded:
            if remove_stop and t in (AR_STOP if is_ar else EN_STOP):
                continue
            if stem:
                t = stem_arabic(t) if is_ar else _stemmer.stem(t)
            if t:
                out.append(t)
    return out


def preprocess(text: str) -> str:
    """Full pipeline used by the retrievers: returns a space-joined token string."""
    return " ".join(tokenize(text))
