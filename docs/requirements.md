# Requirements (from Chapter 3 SRS, cleaned up)

## Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | The system shall accept natural-language queries in English and Arabic and automatically detect the query language. | High |
| FR-02 | The system shall classify every query into one of six FAQ categories: Admissions, Registration, Fees, Academic Programmes, Examinations, Student Services. | High |
| FR-03 | The system shall retrieve the best matching FAQ using TF-IDF cosine similarity, and use sentence-BERT as a fallback when TF-IDF confidence is below the threshold. | High |
| FR-04 | The chatbot shall display the retrieved answer within two seconds of query submission under normal load. | High |
| FR-05 | When no FAQ matches above the confidence threshold, the system shall show a fallback message with college escalation contact details. | High |
| FR-06 | Authorised staff shall be able to add, edit and disable FAQ entries through a web admin dashboard without programming knowledge. | High |
| FR-07 | The system shall log every query with matched FAQ, confidence score, method and session ID for administrator review. | Medium |
| FR-08 | The chatbot widget shall be embeddable in an external college website via a JavaScript snippet. | Medium |
| FR-09 | The knowledge base shall support at least 200 FAQ entries at the time of usability testing. | Medium |
| FR-10 | The chatbot shall display the last five query–response pairs of the current session. | Low |

## Non-Functional Requirements

| ID | Category | Requirement | Metric |
|---|---|---|---|
| NF-01 | Performance | p95 API response < 2 s with 50 concurrent users | Load test |
| NF-02 | Accuracy | Intent classification accuracy ≥ 85% on held-out test set | Evaluation script |
| NF-03 | Usability | ≥ 80% of survey respondents rate interface easy / very easy | Survey (Likert) |
| NF-04 | Availability | Containerised with Docker; runs on Docker Engine 20.10+ | Deployment check |
| NF-05 | Security | Admin login required; passwords stored with bcrypt | Security review |
| NF-06 | Maintainability | FAQs updatable by staff via dashboard without code | Staff task test |

> Note: FR-01 in the original Chapter 3 table contained a copy-paste error
> (it repeated the elicitation sentence). The wording above is the intended
> requirement — update Table 11 in the report to match.
