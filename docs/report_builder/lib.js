// Helpers for building the dissertation chapters with docx-js.
const fs = require("fs");
const path = require("path");
const sizeOf = require("image-size");
const {
  Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell, WidthType,
  ShadingType, BorderStyle, ImageRun, PageBreak, VerticalAlign,
} = require("docx");

const ROOT = "C:/Users/PC/Downloads/oman-faq-chatbot/oman-faq-chatbot";
const FONT = "Times New Roman";
const CONTENT_WIDTH = 9026; // A4 width 11906 - 2 x 1440 margins (DXA)

let figNo = 4;   // Chapter 3 ended at Figure 4
let tabNo = 13;  // Chapter 3 ended at Table 13
const figRefs = {};
const tabRefs = {};

// Pre-assign numbers so text can refer to figures/tables before they appear.
function fig(key) { if (!figRefs[key]) figRefs[key] = ++figNo; return `Figure ${figRefs[key]}`; }
function tab(key) { if (!tabRefs[key]) tabRefs[key] = ++tabNo; return `Table ${tabRefs[key]}`; }

// Inline markup: **bold**, *italic*, `code`
function runs(text, base = {}) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), font: FONT, ...base }));
    const t = m[0];
    if (t.startsWith("**")) out.push(new TextRun({ text: t.slice(2, -2), bold: true, font: FONT, ...base }));
    else if (t.startsWith("`")) out.push(new TextRun({ text: t.slice(1, -1), font: "Consolas", size: (base.size || 24) - 2 }));
    else out.push(new TextRun({ text: t.slice(1, -1), italics: true, font: FONT, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), font: FONT, ...base }));
  return out;
}

const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, children: [new TextRun({ text: t, font: FONT })] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text: t, font: FONT })] });
const H3 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun({ text: t, font: FONT })] });
const H4 = (t) => new Paragraph({ keepNext: true, spacing: { before: 200, after: 100 }, children: runs(`**${t}**`) });
const P = (t) => new Paragraph({ alignment: AlignmentType.JUSTIFIED, spacing: { after: 160, line: 360 }, children: runs(t) });
const B = (t, level = 0) => new Paragraph({ numbering: { reference: "bullets", level }, spacing: { after: 80, line: 336 }, alignment: AlignmentType.JUSTIFIED, children: runs(t) });
const N = (t, ref = "numbers") => new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 80, line: 336 }, children: runs(t) });
const pageBreak = () => new Paragraph({ children: [new PageBreak()] });

function caption(text) {
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 80, after: 240 }, keepLines: true,
    children: runs(text, { size: 22, italics: false }).map((r) => r) });
}

function figure(key, file, title, maxWidthIn = 6.2, maxHeightIn = 7.6) {
  const p = path.isAbsolute(file) ? file : path.join(ROOT, file);
  const buf = fs.readFileSync(p);
  const dim = sizeOf(buf);
  let w = maxWidthIn * 96, h = (dim.height / dim.width) * w;
  if (h > maxHeightIn * 96) { h = maxHeightIn * 96; w = (dim.width / dim.height) * h; }
  const label = fig(key);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120 },
      children: [new ImageRun({ type: "png", data: buf, transformation: { width: Math.round(w), height: Math.round(h) },
        altText: { title: title, description: title, name: key } })] }),
    caption(`**${label}:** ${title}`),
  ];
}

const border = { style: BorderStyle.SINGLE, size: 4, color: "8A9AA9" };
const borders = { top: border, bottom: border, left: border, right: border };

// widths: relative numbers; converted to DXA summing to CONTENT_WIDTH
function table(key, title, header, rows, widths, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const tw = opts.width || CONTENT_WIDTH;
  const cols = widths.map((w) => Math.floor((w / total) * tw));
  cols[cols.length - 1] += tw - cols.reduce((a, b) => a + b, 0);
  const size = opts.size || 20;
  const cell = (text, i, isHead, fill) => new TableCell({
    width: { size: cols[i], type: WidthType.DXA }, borders, verticalAlign: VerticalAlign.TOP,
    shading: isHead ? { fill: "0B4F8A", type: ShadingType.CLEAR, color: "auto" } : fill ? { fill, type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 50, bottom: 50, left: 90, right: 90 },
    children: String(text).split("\n").map((line) => new Paragraph({ spacing: { after: 0, line: 252 },
      children: runs(line, { size, color: isHead ? "FFFFFF" : undefined, bold: isHead || undefined }) })),
  });
  const label = tab(key);
  const out = [new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 200, after: 100 },
    children: runs(`**${label}:** ${title}`, { size: 22 }) })];
  out.push(new Table({
    width: { size: tw, type: WidthType.DXA }, columnWidths: cols,
    rows: [new TableRow({ tableHeader: true, children: header.map((h, i) => cell(h, i, true)) }),
      ...rows.map((r, ri) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, i, false, opts.fill ? opts.fill(r, ri, i) : (ri % 2 ? "F3F6F9" : undefined))) }))],
  }));
  out.push(new Paragraph({ spacing: { after: 160 }, children: [] }));
  return out;
}

function code(text, title) {
  const lines = text.replace(/\r/g, "").split("\n");
  const out = [];
  if (title) out.push(new Paragraph({ keepNext: true, spacing: { before: 120, after: 60 }, children: runs(`*${title}*`, { size: 20 }) }));
  lines.forEach((line, i) => out.push(new Paragraph({
    spacing: { after: 0, line: 240 }, keepLines: true,
    shading: { fill: "F4F6F8", type: ShadingType.CLEAR, color: "auto" },
    border: i === 0 ? { top: { style: BorderStyle.SINGLE, size: 4, color: "C9D3DC", space: 2 } } : i === lines.length - 1 ? { bottom: { style: BorderStyle.SINGLE, size: 4, color: "C9D3DC", space: 2 } } : undefined,
    children: [new TextRun({ text: line.length ? line : " ", font: "Consolas", size: 16 })],
  })));
  out.push(new Paragraph({ spacing: { after: 160 }, children: [] }));
  return out;
}

const note = (t) => new Paragraph({ spacing: { before: 80, after: 160 }, shading: { fill: "FFF4D6", type: ShadingType.CLEAR, color: "auto" },
  border: { left: { style: BorderStyle.SINGLE, size: 18, color: "E0A100", space: 6 } }, children: runs(t, { size: 22 }) });

module.exports = { H1, H2, H3, H4, P, B, N, pageBreak, figure, table, code, note, fig, tab, runs, FONT, ROOT, CONTENT_WIDTH };
