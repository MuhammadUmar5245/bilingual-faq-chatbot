# Data

> **SAMPLE DATA — TO BE VERIFIED WITH COLLEGES.**
> The FAQ entries are realistic examples modelled on the kind of information published by
> private colleges in Oman (Gulf College, Middle East College, Muscat College style).
> Fees, dates, scores and policies are illustrative and must be replaced or verified with the
> participating colleges before the system is used with real students.

## `faqs_seed.csv` — knowledge base (FR-09)
210 bilingual FAQ entries, 35 per category. Loaded automatically into the `faqs` table the first
time the API starts with an empty database. The `id` of each FAQ equals its row number (1–210).

| Column | Description |
|---|---|
| `question_en` | Canonical question in English |
| `question_ar` | Same question in Modern Standard Arabic |
| `answer` | Verified answer in English |
| `answer_ar` | Verified answer in Arabic (optional column — shown to Arabic users) |
| `answer_lang` | Languages the answer is available in (`en`, `ar`, `en+ar`) |
| `category` | One of: Admissions, Registration, Fees, Academic Programmes, Examinations, Student Services |
| `keywords` | Comma-separated keywords/synonyms in English and Arabic (Arabic ones are matched against Arabic queries) |

Only `question_en`, `answer` and `category` are required, so a college can supply a simpler
file. The same format is used by the admin dashboard CSV import/export.

## `test_queries.csv` — held-out evaluation set (NF-02)
361 queries written independently of the seed questions (none is a copy of a seed question):
paraphrases, synonyms, misspellings, abbreviations, word re-ordering, short keyword queries,
colloquial Gulf Arabic, and 32 out-of-scope queries (expected answer `NONE` → fallback).

| Column | Description |
|---|---|
| `query_id` | Sequential id |
| `query` | Test query text |
| `lang` | `en` or `ar` |
| `expected_faq_id` | FAQ id (row number in `faqs_seed.csv`) or `NONE` |
| `expected_category` | Category of the expected FAQ, or `NONE` |
| `variation` | paraphrase / synonym / keyword / misspelling / abbreviation / reorder / colloquial / out_of_scope |

Composition: 244 English, 117 Arabic; every one of the 210 FAQs is targeted at least once.

## Replacing the sample data
Keep the same columns, replace `faqs_seed.csv`, delete the database (or use the admin CSV
import), regenerate `test_queries.csv` for the new FAQs and rerun `backend/nlp/evaluate.py`.
