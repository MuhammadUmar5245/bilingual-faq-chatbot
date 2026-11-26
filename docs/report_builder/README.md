# Report builder (Chapters 4–6)

Generates `docs/Chapters_4-6_FAQ_Chatbot.docx` from the chapter text (`ch4.js`, `ch5.js`, `ch6.js`)
and the project's real results (diagrams, screenshots, `docs/results/*`, test cases).

```
cd docs/report_builder
npm install
# refresh the test-case data from docs/test_cases.xlsx (optional):
../../.venv/Scripts/python -c "import json,openpyxl; wb=openpyxl.load_workbook('../test_cases.xlsx'); ws=wb['Test cases']; json.dump({'cases':[[c or '' for c in r] for r in ws.iter_rows(min_row=2, values_only=True)],'env':wb['Summary']['B1'].value}, open('testcases.json','w',encoding='utf-8'), ensure_ascii=False)"
node build.js
```

After the survey: add the results to the "Survey Results" section in `ch5.js` and the notes in
`ch6.js`, then rebuild. `ROOT` in `lib.js` points to the project folder.
