# Implemented functions (Chapter 5.1.2)

33 distinct, demonstrable functions (minimum required: 20). Screenshot file names refer to
`screenshots/` — see [`screenshots_index.md`](screenshots_index.md) for captions.

## A. Student chatbot widget

| # | Function | Requirement | Screen / where to see it |
|---|---|---|---|
| F01 | Floating chat bubble that opens/closes the chat panel on any page | FR-08, NF-03 | Demo college site — bottom-right launcher |
| F02 | Ask a question in English and receive the verified FAQ answer | FR-01, FR-03, FR-04 | Chat panel |
| F03 | Ask a question in Arabic and receive the answer in Arabic | FR-01, FR-03 | Chat panel (Arabic) |
| F04 | Automatic language detection — the interface follows the language the student types in | FR-01 | Chat panel ("Detected language" label) |
| F05 | Manual EN / عربي toggle with full right-to-left (RTL) layout | FR-01, NF-03 | Chat header toggle |
| F06 | Typing indicator while the answer is retrieved | NF-03 | Chat panel |
| F07 | Category quick-reply chips (six FAQ categories) listing each category's questions | FR-02 | Chips bar above the input |
| F08 | Popular questions on the welcome screen (ranked by real usage) | FR-03 | Welcome screen |
| F09 | Answer card showing matched question, category tag and confidence score | FR-02, FR-03 | Chat answer bubble |
| F10 | Fallback message with escalation contact card (phone, email, hours) when no FAQ matches | FR-05 | Fallback bubble |
| F11 | "Did you mean…?" suggestions offered with the fallback | FR-05 | Fallback bubble |
| F12 | Thumbs up / thumbs down feedback on every answer | FR-07 | Answer bubble |
| F13 | Session history — last five question–answer pairs, re-askable with one click | FR-10 | History view (clock icon) |
| F14 | Clear chat | NF-03 | Header trash icon |
| F15 | Mobile-responsive full-screen chat on phones | NF-03 | Mobile view |
| F16 | Embeddable `widget.js` — any college website adds the chatbot with one `<script>` tag | FR-08 | `docs/demo-college-site.html` |

## B. Admin dashboard (staff)

| # | Function | Requirement | Screen / where to see it |
|---|---|---|---|
| F17 | Secure staff login / logout (bcrypt password hashes, session cookie) | NF-05 | Login page |
| F18 | Overview statistics: total queries, resolution rate, average confidence, average response time, helpful-feedback rate, active FAQs | FR-04, FR-07 | Overview |
| F19 | Charts: queries per day (7/14/30 days), queries by category, answer method and query language shares, most-asked FAQs | FR-02, FR-07 | Overview |
| F20 | FAQ table with search, category/status filters and pagination | FR-06, FR-09 | FAQ Management |
| F21 | Add a new FAQ (English + Arabic question/answer, category, keywords) without code | FR-06, NF-06 | Add FAQ form |
| F22 | Edit an existing FAQ | FR-06, NF-06 | Edit FAQ form |
| F23 | Disable / re-enable an FAQ (hidden from the chatbot but kept) | FR-06 | FAQ Management |
| F24 | Delete an FAQ (with confirmation) | FR-06 | Delete dialog |
| F25 | Automatic rebuild of the TF-IDF / SBERT indexes after any FAQ change — no restart | FR-03, FR-06, NF-06 | Toast "chatbot index rebuilt"; answer changes immediately |
| F26 | Bulk import of FAQs from CSV (append or replace) with row-level error report | FR-06, FR-09, NF-06 | Import CSV dialog |
| F27 | Export all FAQs to CSV (UTF-8, Excel-friendly) | FR-06 | Export CSV button |
| F28 | Conversation log viewer with text search, method, language and date filters, pagination | FR-07 | Conversation Logs |
| F29 | Unanswered queries list (fallback answers and thumbs-down ratings) | FR-05, FR-07 | Unanswered Queries |
| F30 | "Create FAQ from this" — turns an unanswered query into a pre-filled new FAQ form | FR-06, NF-06 | Unanswered Queries → Add FAQ |
| F31 | Edit matching thresholds (TF-IDF threshold, SBERT-stage threshold, fusion weight) — applied live | FR-03, FR-05 | Settings |
| F32 | Edit fallback contact details shown to students | FR-05 | Settings |
| F33 | Change admin password (strength rules, bcrypt) | NF-05 | Settings |

## C. Supporting (non-visual) functions
- Input validation and JSON error responses on every endpoint; rate limiting on `POST /api/chat` and login (NF-05).
- Every query logged with session id, detected language, matched FAQ, confidence, method, category and response time (FR-07).
- `GET /api/health` used by Docker health checks (NF-04).
- Category classifier assigns one of six categories to every query, including unanswered ones (FR-02).
