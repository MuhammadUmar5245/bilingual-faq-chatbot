# Screenshots index (Chapter 5.1.2)

All screenshots were captured automatically with Playwright
(`python screenshots/capture_screenshots.py`) from the Docker deployment
(`docker compose up`, PostgreSQL 14, SBERT enabled) on a freshly seeded database.
Before capturing, the script sent a short demonstration session of 27 queries through the
public API so that the dashboard has data to display; the statistics shown therefore come from
this demonstration and the screenshot run itself, **not from real students**. Function IDs
(F01–F33) refer to [`functions_list.md`](functions_list.md).

## Student chatbot widget

| File | Function(s) | Caption |
|---|---|---|
| `01_college_site_with_chat_bubble.png` | F01, F16 | A college website (fictional "Al Sahil College", `docs/demo-college-site.html`) with the chatbot embedded through a single `<script>` tag. The floating chat bubble appears in the bottom-right corner. |
| `02_chat_welcome_popular_questions.png` | F01, F07, F08 | The chat panel after opening: greeting, popular questions ranked by real usage, and the six category chips above the input box. |
| `03_chat_english_answer.png` | F02, F09, F12 | An English question answered with the verified FAQ. The card shows the matched question, the category tag, the confidence score, the detected language and the thumbs up/down feedback buttons. |
| `04_chat_typing_indicator.png` | F06 | The animated typing indicator shown while the answer is retrieved (the API response was artificially delayed for this capture so the indicator is visible). |
| `05_chat_arabic_auto_detected_rtl.png` | F03, F04, F05 | An Arabic question: the language is detected automatically, the whole interface switches to Arabic with a right-to-left layout, and the answer is given in Arabic. |
| `06_category_chip_questions.png` | F07 | Clicking the "Student Services" chip lists the questions of that category; each question can be asked with one click. |
| `07_fallback_contact_card.png` | F10, F11 | An out-of-scope question ("what is the capital of france") gets the fallback message with the escalation contact card (office, phone, email, hours) and "Did you mean" suggestions (FR-05). |
| `08_feedback_thumbs_up_thanks.png` | F12 | After the student rates an answer as helpful, the buttons are replaced by a thank-you message; the rating is stored with the conversation log. |
| `09_history_last_five_questions.png` | F13 | The history view (clock icon) shows the last five question–answer pairs of the session, newest first; a question can be asked again with one click (FR-10). |
| `10_arabic_interface_toggle.png` | F05, F14 | The chat cleared and switched to Arabic with the EN/عربي toggle: greeting, popular questions, chips and input placeholder are all in Arabic, right-to-left. |
| `11_mobile_college_site.png` | F15 | The demo college site on a phone-size screen (390 × 844) with the chat bubble. |
| `12_mobile_chat_english.png` | F15, F02 | On a phone the chat opens full-screen; an English answer is shown. |
| `13_mobile_chat_arabic.png` | F15, F03 | An Arabic question on the phone. The query "هل يوجد سكن للطلاب؟" (is there student housing?) was matched to the related FAQ about separate male/female hostels rather than the general hostel FAQ — a realistic example of a near-miss retrieval. |

## Admin dashboard

| File | Function(s) | Caption |
|---|---|---|
| `14_admin_login.png` | F17 | Staff sign-in page of the admin dashboard. |
| `15_admin_login_failed.png` | F17 | A wrong password is rejected with a generic error message (NF-05). |
| `16_admin_overview_dashboard.png` | F18, F19 | Overview: total queries, resolution rate, average confidence, average response time, helpful-feedback rate and active FAQs; queries per day, by category, by answer method and by language; most-asked FAQs. |
| `17_admin_faq_table.png` | F20 | The FAQ table (210 bilingual entries) with search, category and status filters, pagination and per-row actions. |
| `18_admin_faq_search_filter_preview.png` | F20 | Searching "hostel" within the Student Services category; clicking a question expands its English and Arabic answers and keywords. |
| `19_admin_add_faq_form.png` | F21 | The Add FAQ form: English and Arabic question and answer, category and keywords — no programming needed (FR-06, NF-06). |
| `20_admin_faq_saved_index_rebuilt.png` | F21, F25 | After saving, a notification confirms that the FAQ was added and the chatbot's index rebuilt. |
| `21_chatbot_uses_new_faq_immediately.png` | F25 | Immediately afterwards, a student asking "can I go swimming at the college?" receives the new FAQ — no restart required. |
| `22_admin_edit_faq.png` | F22 | Editing an existing FAQ in the same form. |
| `23_admin_faq_disabled.png` | F23 | The FAQ disabled with one click: it stays in the table (greyed out, "Disabled") but is no longer used by the chatbot. |
| `24_admin_delete_confirmation.png` | F24 | Deleting an FAQ asks for confirmation and suggests disabling instead. |
| `25_admin_csv_import_result.png` | F26 | Bulk import from CSV: one valid row imported, one invalid row skipped with the reason reported. |
| `26_admin_conversation_logs.png` | F28 | Conversation logs: time, query, matched FAQ, language, method (TF-IDF/SBERT/fallback), confidence, response time, rating and session (FR-07). |
| `27_admin_logs_filtered_arabic.png` | F28 | The same log filtered to Arabic queries. |
| `28_admin_unanswered_queries.png` | F29 | Unanswered queries: fallback answers and answers rated "not helpful", with the predicted category and best score. |
| `29_admin_create_faq_from_unanswered.png` | F30 | "Create FAQ from this" opens the Add FAQ form pre-filled with the student's question ("do you have a gym"). |
| `30_admin_settings_thresholds_contacts.png` | F31, F32 | Settings: TF-IDF threshold (0.75), SBERT-stage threshold (0.35) and fusion weight (0.6) sliders, and the fallback contact details shown to students. |
| `31_admin_change_password_validation.png` | F33 | Changing the password: a weak new password is rejected by the strength rules (NF-05). |
| `32_admin_chart_tooltip.png` | F19 | Hovering a bar in the queries-per-day chart shows a tooltip with the date and count. |
| `33_admin_mobile_view.png` | F18 | The admin dashboard on a phone: KPI cards reflow to two columns and the menu collapses behind the ☰ button. |

Note: the "Export CSV" function (F27) downloads a file and has no separate screen; it is verified
by test case TC19 in [`test_cases.md`](test_cases.md).
