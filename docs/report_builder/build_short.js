const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, AlignmentType, LevelFormat, Footer, PageNumber, TableOfContents,
  HeadingLevel, Header,
} = require("docx");
const { H1, H2, P, B, runs, FONT, ROOT, tab } = require("./lib");

const ch4 = require("./c4")();
const ch5 = require("./c5")();
const ch6 = require("./c6")();

// Resolve the placeholder used in ch6 for the traceability table number
function fixRefs(children) { return children; }

const refs = [
  "Bird, S., Klein, E. and Loper, E. (2009) *Natural Language Processing with Python*. Sebastopol, CA: O'Reilly Media.",
  "Cronbach, L.J. (1951) 'Coefficient alpha and the internal structure of tests', *Psychometrika*, 16(3), pp. 297–334.",
  "Fielding, R.T. (2000) *Architectural Styles and the Design of Network-based Software Architectures*. PhD thesis. University of California, Irvine.",
  "IEEE (2009) *IEEE Std 1016-2009: IEEE Standard for Information Technology — Systems Design — Software Design Descriptions*. New York: IEEE.",
  "Larkey, L.S., Ballesteros, L. and Connell, M.E. (2007) 'Light stemming for Arabic information retrieval', in Soudi, A., van den Bosch, A. and Neumann, G. (eds) *Arabic Computational Morphology*. Dordrecht: Springer, pp. 221–243.",
  "Obeid, O., Zalmout, N., Khalifa, S., Taji, D., Oudah, M., Alhafni, B., Inoue, G., Eryani, F., Erdmann, A. and Habash, N. (2020) 'CAMeL Tools: An open source Python toolkit for Arabic natural language processing', *Proceedings of the 12th Language Resources and Evaluation Conference (LREC 2020)*, pp. 7022–7032.",
  "Reimers, N. and Gurevych, I. (2019) 'Sentence-BERT: Sentence embeddings using Siamese BERT-networks', *Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing (EMNLP-IJCNLP)*, pp. 3982–3992.",
  "Reimers, N. and Gurevych, I. (2020) 'Making monolingual sentence embeddings multilingual using knowledge distillation', *Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing (EMNLP)*, pp. 4512–4525.",
  "Salton, G. and Buckley, C. (1988) 'Term-weighting approaches in automatic text retrieval', *Information Processing & Management*, 24(5), pp. 513–523.",
  "Sommerville, I. (2016) *Software Engineering*. 10th edn. Harlow: Pearson.",
];

const refSection = [
  H1("References (additions for Chapters 4–6)"),
  P("The following sources are cited in Chapters 4–6 in addition to those already listed in Chapters 1–3. Merge them into the main reference list in alphabetical order (Harvard style)."),
  ...refs.map((r) => new Paragraph({ spacing: { after: 120, line: 300 }, indent: { left: 567, hanging: 567 }, children: runs(r) })),
];

const appendix = [
  H1("Appendices (material provided with the project)"),
  P("The following appendix material is available in the project repository and can be inserted into the appendices of the report:"),
  B("**User's Manual** — `docs/user_manual.md` (student guide, admin guide and installation, with screenshots)."),
  B("**Code Listing** — `docs/code_listing/` (22 key source files) and `docs/important_code.md`."),
  B("**Sample Research Questionnaire** — `docs/questionnaire.md`, with the response template `docs/survey/survey_responses_template.csv` and analysis script `docs/survey/survey_analysis.py`."),
  B("**Test cases** — `docs/test_cases.xlsx` and `docs/test_cases.md` (39 test cases with actual results)."),
  B("**Evaluation results** — `docs/results/` (result tables, tuning log, performance and security reports, coverage report)."),
  B("**Diagrams and screenshots** — `diagrams/` (13 diagrams with their sources) and `screenshots/` (33 screenshots, captions in `docs/screenshots_index.md`)."),
];

const cover = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 2400, after: 240 }, children: [new TextRun({ text: "GIS6001 – Computer Science Dissertation Project", font: FONT, size: 28 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 480 }, children: [new TextRun({ text: "CHATBOT FOR FREQUENTLY ASKED QUESTIONS IN COLLEGES IN OMAN", font: FONT, size: 36, bold: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [new TextRun({ text: "Chapter 4 – Project Design", font: FONT, size: 28 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [new TextRun({ text: "Chapter 5 – Project Implementation, Testing & Evaluation", font: FONT, size: 28 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 960 }, children: [new TextRun({ text: "Chapter 6 – Conclusion, Critical Evaluation and Future Work", font: FONT, size: 28 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Figures continue from Figure 5 and tables from Table 14 (Chapter 3 ends at Figure 4 / Table 13).", font: FONT, size: 20, italics: true, color: "555555" })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Right-click the table of contents and choose Update Field after pasting into the full report.", font: FONT, size: 20, italics: true, color: "555555" })] }),
  new Paragraph({ pageBreakBefore: true, children: [new TextRun({ text: "Contents", font: FONT, size: 32, bold: true })] }),
  new TableOfContents("Contents", { hyperlink: true, headingStyleRange: "1-3" }),
];

const doc = new Document({
  creator: "GIS6001 student",
  title: "Chatbot for FAQ in Colleges in Oman — Chapters 4–6",
  styles: {
    default: { document: { run: { font: FONT, size: 24 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: FONT, color: "0B3B66" }, paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: FONT, color: "0B3B66" }, paragraph: { spacing: { before: 300, after: 160 }, outlineLevel: 1, keepNext: true } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: FONT, color: "1F4E79" }, paragraph: { spacing: { before: 220, after: 120 }, outlineLevel: 2, keepNext: true } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 567, hanging: 283 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1134, hanging: 283 } } } },
      ] },
      { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 567, hanging: 283 } } } }] },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "GIS6001 – Chatbot for FAQ in Colleges in Oman", font: FONT, size: 18, color: "777777" })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 20 })] })] }) },
    children: [...ch4, ...ch5, ...ch6, ...refSection],
  }],
});

const out = path.join(ROOT, "docs", "Chapters_4-6_FAQ_Chatbot_short.docx");
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(out, buf); console.log("wrote", out, (buf.length / 1e6).toFixed(1), "MB"); });
