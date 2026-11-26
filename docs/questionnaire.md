# Usability and satisfaction questionnaire (Chapter 5.3 / Appendix)

**Project:** Chatbot for Frequently Asked Questions in Colleges in Oman (GIS6001)
**Target respondents:** 30 — 18 current students, 6 prospective students/applicants, 6 administration staff (Table 10)
**Evaluates:** NF-03 (≥ 80 % rate the interface easy / very easy), perceived accuracy, speed, Arabic support, intention to reuse

> **Instructions for the respondent.** Please use the chatbot for about 10 minutes: ask at least
> five questions about admissions, fees, registration, exams or student services — some in English
> and some in Arabic. Staff respondents should also add or edit one FAQ in the admin dashboard.
> Then answer the questions below. Participation is voluntary and anonymous; you may stop at any time.
>
> **تعليمات للمشارك:** يرجى استخدام روبوت المحادثة لمدة 10 دقائق تقريباً وطرح خمسة أسئلة على الأقل
> بالعربية والإنجليزية، ثم الإجابة عن الأسئلة التالية. المشاركة طوعية ومجهولة الهوية.

---

## Section A — About you

| ID | Question | Options |
|---|---|---|
| D1 | Which group are you in? | ☐ Current student ☐ Prospective student / applicant ☐ Administration staff |
| D2 | Gender | ☐ Male ☐ Female ☐ Prefer not to say |
| D3 | Age group | ☐ 17–20 ☐ 21–24 ☐ 25–34 ☐ 35+ |
| D4 | Your college | ☐ College A ☐ College B ☐ College C ☐ Other |
| D5 | Year of study (students only) | ☐ Foundation ☐ Year 1 ☐ Year 2 ☐ Year 3 ☐ Year 4 ☐ Not a student |
| D6 | Which language did you mainly use with the chatbot? | ☐ English ☐ Arabic ☐ Both |
| D7 | How often do you use chatbots or virtual assistants? | ☐ Never ☐ Rarely ☐ Sometimes ☐ Often |

## Section B — Your experience (5-point Likert scale)

1 = Strongly disagree · 2 = Disagree · 3 = Neutral · 4 = Agree · 5 = Strongly agree

| ID | Construct | Statement | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|---|
| Q1 | Ease of use | The chatbot was easy to use. | ☐ | ☐ | ☐ | ☐ | ☐ |
| Q2 | Ease of use | I could find the chat button and start a conversation without help. | ☐ | ☐ | ☐ | ☐ | ☐ |
| Q3 | Ease of use | The topic buttons and popular questions helped me find information. | ☐ | ☐ | ☐ | ☐ | ☐ |
| Q4 | Perceived accuracy | The answers matched the questions I asked. | ☐ | ☐ | ☐ | ☐ | ☐ |
| Q5 | Perceived accuracy | The answers were clear and complete. | ☐ | ☐ | ☐ | ☐ | ☐ |
| Q6 | Perceived accuracy | When the chatbot could not answer, the contact details shown were useful. | ☐ | ☐ | ☐ | ☐ | ☐ |
| Q7 | Speed | The chatbot answered quickly. | ☐ | ☐ | ☐ | ☐ | ☐ |
| Q8 | Speed | Using the chatbot was faster than searching the college website or emailing staff. | ☐ | ☐ | ☐ | ☐ | ☐ |
| Q9 | Arabic support | The chatbot understood my questions in Arabic. | ☐ | ☐ | ☐ | ☐ | ☐ |
| Q10 | Arabic support | The Arabic interface (right-to-left layout) was displayed correctly. | ☐ | ☐ | ☐ | ☐ | ☐ |
| Q11 | Interface | The chatbot worked well on my mobile phone. | ☐ | ☐ | ☐ | ☐ | ☐ |
| Q12 | Interface | The design of the chatbot is clear and professional. | ☐ | ☐ | ☐ | ☐ | ☐ |
| Q13 | Satisfaction | Overall, I am satisfied with the chatbot. | ☐ | ☐ | ☐ | ☐ | ☐ |
| Q14 | Intent to reuse | I would use this chatbot again for college questions. | ☐ | ☐ | ☐ | ☐ | ☐ |
| Q15 | Intent to reuse | I would recommend the chatbot to other students. | ☐ | ☐ | ☐ | ☐ | ☐ |

**Staff only (administration staff respondents):**

| ID | Construct | Statement | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|---|---|
| S1 | Maintainability (NF-06) | I could add or edit an FAQ in the admin dashboard without technical help. | ☐ | ☐ | ☐ | ☐ | ☐ |
| S2 | Usefulness | The statistics and unanswered-queries list would help my office. | ☐ | ☐ | ☐ | ☐ | ☐ |

## Section C — Overall rating (NF-03)

| ID | Question | Options |
|---|---|---|
| E1 | How easy was the chatbot interface to use overall? | ☐ Very difficult ☐ Difficult ☐ Neutral ☐ Easy ☐ Very easy |

## Section D — Open questions

| ID | Question |
|---|---|
| O1 | What did you like most about the chatbot? |
| O2 | What should be improved, or which questions could the chatbot not answer? |

---

## Coding sheet for analysis
Enter each respondent as one row in [`survey/survey_responses_template.csv`](survey/survey_responses_template.csv)
(copy it to `survey_responses.csv`). Likert items are coded 1–5; E1 is coded 1 (very difficult) to
5 (very easy); leave a cell empty when not answered; S1–S2 are empty for non-staff respondents.
Then run:

```
python docs/survey/survey_analysis.py docs/survey/survey_responses.csv
```

The script produces descriptive statistics (n, mean, median, standard deviation, % agree), the
NF-03 result (% of respondents rating E1 as Easy or Very easy), results by respondent group,
Cronbach's alpha for the multi-item constructs, and charts in `docs/survey/results/`.

**No survey responses are included in this repository — the 30 responses must be collected from real participants.**
