// Chapter 6 - condensed version (target ~4 pages)
const { H1, H2, H3, P, B, table, note, tab } = require("./lib");

module.exports = () => [
  H1("Chapter 6. Conclusion, Critical Evaluation and Future Work"),

  H2("6.1 Conclusion"),
  P("The project set out to build and test a chatbot that answers students' questions about Omani colleges in English and Arabic. A working prototype was delivered: a bilingual knowledge base of 210 FAQs in six categories, a hybrid NLP pipeline combining TF-IDF with a multilingual sentence-BERT model, an embeddable chat widget, an administration dashboard and a one-command Docker deployment."),
  P("The quasi-experiment supports the hypothesis that a hybrid method is more accurate than TF-IDF alone — 85.6 % against 81.1 % on held-out queries — but only when the two scores are combined. Using sentence-BERT alone as a fallback, as first specified, gave 78.9 %. TF-IDF contributes precise word matching and tolerance of spelling variants; sentence-BERT contributes paraphrase understanding and the rejection of unrelated questions. The retrieval-only design, together with a dashboard in which staff can correct an answer and see it used immediately, keeps the college in control of the information given to students."),

  H2("6.2 Evaluation against the Objectives"),
  ...table("obj", "Evaluation against the specific objectives (Section 1.3.2)", ["Objective", "Result", "Status"], [
    ["≥ 200 FAQs from three colleges in six areas", "210 bilingual FAQs; sample data not yet confirmed by the colleges", "Partly met"],
    ["Bilingual NLP pipeline with ≥ 85 % accuracy", "85.6 % held-out (87.3 % on all queries); Arabic 88.9 %", "Met"],
    ["Web chatbot for desktop and mobile, embeddable", "widget.js with one script tag; mobile layout", "Met"],
    ["Admin interface to add, edit and disable FAQs without coding", "Dashboard with forms, CSV import/export, live update", "Met"],
    ["Survey with ≥ 30 respondents", "Questionnaire and analysis ready; responses not yet collected", "Pending"],
    ["Black-box testing with ≥ 25 test cases; IEEE SRS", "39 test cases, all passed; full traceability", "Met"],
    ["NF-01 performance / NF-03 usability", "p95 802 ms with 50 users / survey pending", "Met / Pending"],
  ], [38, 46, 16], { size: 18 }),

  H2("6.3 Critical Evaluation"),
  H3("6.3.1 Strengths"),
  B("Reproducible results: every figure in Chapter 5 is produced by a script, and accuracy was reported on queries never used for tuning."),
  B("Genuine bilingual support, with Arabic accuracy as high as English and a fully right-to-left interface."),
  B("Safe answers: retrieval only, with an explicit fallback; most errors are refusals rather than wrong answers."),
  B("Easy maintenance and deployment: staff need no programming, the system starts with one command and embeds with one tag."),
  H3("6.3.2 Limitations"),
  B("The FAQs are realistic sample data that the colleges have not yet verified; they must be checked before use with students."),
  B("The test queries and the Arabic keywords were written by the same author, and 361 queries is a small test set (roughly ±5 percentage points), so accuracy on real questions may be lower."),
  B("Paraphrases (77.3 %) and closely related FAQs are still confused, and 12.5 % of out-of-scope questions receive an answer."),
  B("Usability (NF-03) has not yet been measured."),
  B("Prototype security: HTTP instead of HTTPS, a single administrator role and no audit trail; six worker processes need about 4 GB of memory."),
  H3("6.3.3 Problems Encountered"),
  P("The specified hybrid design missed the accuracy target; this was found in the quasi-experiment and solved by score fusion and better Arabic processing. CAMeL Tools conflicted with the sentence-BERT libraries and was replaced by a custom Arabic normaliser. The first load test failed NF-01 because of processor-thread contention, which was fixed in the deployment configuration. Python 3.14 on the development PC was not supported by PyTorch, so a Python 3.10 environment matching Table 13 was used."),

  H2("6.4 Testing Strategy and Conclusions"),
  P("A requirements-based strategy was used: black-box tests for the functional requirements, white-box unit tests for the NLP components, a quasi-experiment for accuracy, and load and security tests for the non-functional requirements, with a survey for usability. The tests were automated, planned from the traceability matrix and run against the final Docker deployment. They show that all functional requirements and the measurable non-functional requirements are met, and they led to three design improvements. A further recommendation is to raise the fallback threshold slightly if the college prefers fewer answers to off-topic questions."),

  H2("6.5 Future Work"),
  B("Verify or replace the FAQs with the colleges, rebuild the test set partly from real student questions in the logs, and re-run the evaluation."),
  B("Complete the 30-respondent survey and use its feedback to refine the interface."),
  B("Fine-tune the multilingual model on question pairs from the logs and add a re-ranking step and an out-of-scope detector."),
  B("Add HTTPS, role-based staff accounts with an audit trail and an approval step for FAQ changes."),
  B("Integrate with the student information system for personal answers, add escalation to live staff (for example WhatsApp) and voice input."),
  note("[TO BE COMPLETED] After the survey, update the survey and NF-03 rows in the table above and add the main survey findings to Sections 6.1 and 6.3."),
];
