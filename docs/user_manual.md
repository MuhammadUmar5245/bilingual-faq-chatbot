# User manual — College FAQ Chatbot

This manual has two parts: a **student guide** for anyone asking questions through the chat
widget, and an **admin guide** for college staff who maintain the FAQ knowledge base.

---

# Part A — Student guide

## A1. Opening the chatbot
On the college website, click the round chat button in the bottom-right corner. The chat panel
opens with a greeting, the most popular questions and six topic buttons.

![College website with the chat button](../screenshots/01_college_site_with_chat_bubble.png)
![Welcome screen](../screenshots/02_chat_welcome_popular_questions.png)

## A2. Asking a question
Type your question in your own words — in **English or Arabic** — and press Enter or the send
button. You do not need to use exact words; spelling mistakes and short questions such as
"hostel fees" are fine. While the chatbot is looking for the answer you will see a typing indicator.

![Typing indicator](../screenshots/04_chat_typing_indicator.png)

The answer card shows:
- the FAQ question that was matched (check it is what you meant),
- the verified answer from the college,
- the topic (category), how confident the chatbot is, and the language it detected.

![English answer](../screenshots/03_chat_english_answer.png)

## A3. Arabic
If you write in Arabic, the chatbot detects it automatically, answers in Arabic and switches the
whole chat to right-to-left. You can also switch language at any time with the **عربي / English**
button in the header.

![Arabic answer](../screenshots/05_chat_arabic_auto_detected_rtl.png)
![Arabic interface](../screenshots/10_arabic_interface_toggle.png)

## A4. Browsing by topic
Click a topic button (Admissions, Registration, Fees, Academic Programmes, Examinations, Student
Services) to see the questions in that topic, then click any question to get its answer.

![Topic questions](../screenshots/06_category_chip_questions.png)

## A5. When the chatbot cannot answer
The chatbot only gives answers that the college has verified. If it cannot find a matching
answer, it shows the contact details of the student services office (phone, email and opening
hours) and may suggest similar questions ("Did you mean…?").

![Fallback with contact details](../screenshots/07_fallback_contact_card.png)

## A6. Rating an answer
Under each answer, click 👍 if it helped or 👎 if it did not. Your rating helps the college
improve the answers.

![Feedback](../screenshots/08_feedback_thumbs_up_thanks.png)

## A7. Your recent questions
Click the clock icon in the header to see your last five questions and answers in this session.
Click a question to ask it again. Click the bin icon to clear the conversation.

![History](../screenshots/09_history_last_five_questions.png)

## A8. On a mobile phone
On a phone the chat opens full-screen and works the same way.

![Mobile](../screenshots/12_mobile_chat_english.png)

---

# Part B — Admin guide (college staff)

## B1. Signing in
Open `/admin/` on the chatbot server (for example `http://localhost:8088/admin/`) and sign in
with your staff account. The default account created at installation is **admin / Admin@12345** —
change this password immediately (section B9).

![Login](../screenshots/14_admin_login.png)

## B2. Overview dashboard
The overview shows how the chatbot is used: total queries, the share answered without staff
(resolution rate), average confidence, average response time, the share of helpful ratings,
queries per day (choose 7, 14 or 30 days), queries per topic, how queries were answered
(keyword match, semantic match or fallback), the query language, and the most-asked FAQs.
Hover over a bar to see its exact value.

![Overview](../screenshots/16_admin_overview_dashboard.png)

## B3. Finding FAQs
Open **FAQ Management**. Type in the search box to search questions, answers and keywords in both
languages, and filter by category or status. Click a question to preview its answers.

![FAQ table](../screenshots/17_admin_faq_table.png)
![Search and preview](../screenshots/18_admin_faq_search_filter_preview.png)

## B4. Adding an FAQ
Click **+ Add FAQ** and fill in:
- **Question (English)** and **Answer (English)** — required;
- **Question (Arabic)** and **Answer (Arabic)** — recommended, used for Arabic-speaking students;
- **Category** — one of the six topics;
- **Keywords / synonyms** — other words students might use, in English or Arabic, separated by commas
  (for example `fees, tuition, cost, الرسوم, التكلفة`). Good keywords noticeably improve matching.

Click **Save FAQ**. The chatbot updates itself automatically — the new answer is available to
students straight away; no restart or technical help is needed.

![Add FAQ](../screenshots/19_admin_add_faq_form.png)
![Saved](../screenshots/20_admin_faq_saved_index_rebuilt.png)
![Chatbot uses the new FAQ](../screenshots/21_chatbot_uses_new_faq_immediately.png)

## B5. Editing, disabling and deleting
- **Edit** opens the same form to correct a question or answer.
- **Disable** hides an FAQ from the chatbot without deleting it (for example a fee that is being
  reviewed); click **Enable** to bring it back.
- **Delete** removes it permanently after confirmation. Disabling is usually safer.

![Disabled FAQ](../screenshots/23_admin_faq_disabled.png)
![Delete confirmation](../screenshots/24_admin_delete_confirmation.png)

## B6. Importing and exporting FAQs (CSV)
**Export CSV** downloads all FAQs as a spreadsheet file that opens in Excel. **Import CSV**
adds many FAQs at once from a UTF-8 CSV file with the columns `question_en, question_ar, answer,
answer_ar, category, keywords` (only `question_en`, `answer` and `category` are required).
Choose **Add to existing FAQs** or **Replace** (disables all current FAQs first). Rows with
problems are skipped and listed with the reason.

![CSV import](../screenshots/25_admin_csv_import_result.png)

## B7. Conversation logs
**Conversation Logs** lists every question students asked, the FAQ that was returned, the
language, how it was answered, the confidence, the response time and any rating. Filter by text,
method, language or date.

![Logs](../screenshots/26_admin_conversation_logs.png)

## B8. Improving the chatbot with unanswered queries
**Unanswered Queries** lists questions that received the fallback message or were rated "not
helpful". These show what students need that the knowledge base is missing. Click **Create FAQ
from this** to open the Add FAQ form with the student's question already filled in.

![Unanswered](../screenshots/28_admin_unanswered_queries.png)
![Create FAQ from query](../screenshots/29_admin_create_faq_from_unanswered.png)

## B9. Settings and password
- **TF-IDF confidence threshold** (default 0.75) — keyword matches at or above this score are
  answered directly.
- **SBERT-stage threshold** (default 0.35) — for other questions, the semantic score must reach
  this value or the student gets the fallback. Raise it to reduce wrong answers (more fallbacks);
  lower it to answer more questions (more risk of a wrong match).
- **TF-IDF weight in the SBERT stage** (default 0.6) — normally leave unchanged.
- **Fallback contact details** — the office name, phone, email and hours shown to students.
- **Change password** — at least 8 characters with letters and digits.

Changes apply to the chatbot immediately.

![Settings](../screenshots/30_admin_settings_thresholds_contacts.png)

---

# Part C — Installation (IT staff)

Requirements: Docker Engine 20.10+ with Docker Compose (Table 13).

```
docker compose up --build
```

Then open `http://localhost:8088` (demo college page with the chatbot) and
`http://localhost:8088/admin/` (dashboard). To embed the chatbot in the real college website, add:

```html
<script src="https://YOUR-CHATBOT-SERVER/widget.js" data-title="College Assistant" defer></script>
```

Configuration (admin password, database password, thresholds, contact details, port) is set in a
`.env` file — copy `.env.example` and edit it. See the project `README.md` for details.
