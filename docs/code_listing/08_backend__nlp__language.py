"""Query language detection (FR-01).

langdetect is unreliable on very short texts (2-3 words), so a script-ratio rule is
applied first: if Arabic letters dominate the query it is Arabic. Otherwise langdetect
decides; any non-Arabic result is mapped to English, the other supported language.
"""
import re

from langdetect import DetectorFactory, LangDetectException, detect

DetectorFactory.seed = 0  # deterministic results

_AR = re.compile(r"[؀-ۿ]")
_LATIN = re.compile(r"[A-Za-z]")

SUPPORTED = ("en", "ar")


def detect_language(text: str) -> str:
    """Return 'ar' or 'en' for a user query."""
    ar = len(_AR.findall(text or ""))
    lat = len(_LATIN.findall(text or ""))
    if ar == 0 and lat == 0:
        return "en"
    if ar >= lat:
        return "ar"
    if ar == 0 and lat < 12:
        return "en"  # too short for langdetect; only Latin script -> English
    try:
        return "ar" if detect(text) == "ar" else "en"
    except LangDetectException:
        return "en"
