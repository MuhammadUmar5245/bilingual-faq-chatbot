"""Privacy of the query log (FR-07; Chapter 4.4, Table 19 - query logs specification).

1. Masking: before a student question is written to CONVERSATION_LOGS, e-mail addresses,
   telephone numbers and long digit sequences (e.g. student or civil ID numbers) are replaced
   by a placeholder. Only the stored copy is masked; retrieval uses the original question.
2. Retention: `flask --app wsgi purge-logs` empties query_text in log rows older than
   LOG_RETENTION_DAYS (default 365). All other fields are kept, so statistics, the
   unanswered-queries list and evaluation data based on metadata are not affected.
"""
import re
from datetime import timedelta

EMAIL_MASK = "[email]"
NUMBER_MASK = "[number]"
REDACTED = "[removed after retention period]"

# Arabic-Indic (٠-٩) and Eastern Arabic-Indic (۰-۹) digits count as digits too.
_DIGIT = r"[0-9٠-٩۰-۹]"
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+", re.UNICODE)
# 7 or more digits, optionally with a leading + and single spaces/dashes/dots between groups:
# catches Omani phone numbers (+968 9123 4567, 91234567) and student/civil ID numbers, but not
# years, course codes or amounts such as "2025", "MATH101" or "450 OMR".
_LONG_NUMBER = re.compile(rf"\+?{_DIGIT}(?:[\s\-.]?{_DIGIT}){{6,}}")


def mask_personal_details(text: str) -> str:
    """Replace e-mail addresses and long digit sequences with placeholders (Table 19)."""
    text = _EMAIL.sub(EMAIL_MASK, text)
    return _LONG_NUMBER.sub(NUMBER_MASK, text)


def purge_old_query_text(days: int) -> int:
    """Empty query_text of log rows older than `days` days; return the number of rows changed."""
    from app.extensions import db
    from models import ConversationLog, utcnow

    cutoff = utcnow() - timedelta(days=days)
    n = (ConversationLog.query
         .filter(ConversationLog.created_at < cutoff, ConversationLog.query_text != REDACTED)
         .update({ConversationLog.query_text: REDACTED}, synchronize_session=False))
    db.session.commit()
    return n
