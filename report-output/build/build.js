"use strict";
/* Report builder. Reads ../source/*.md (light markup, see parse()) and writes the Word document.
   Formatting follows "Project Report Format.pdf": Times New Roman, body 12 pt / 1.5 spacing / justified,
   chapter titles 16 pt bold centred, headings 14 pt bold, sub-headings 12 pt bold, captions 10 pt bold,
   figure captions below figures, table captions above tables, roman numerals for the front matter. */
const fs = require("fs");
const path = require("path");
const D = require("docx");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, AlignmentType, Footer,
  PageNumber, TabStopType, LeaderType, SectionType, BorderStyle, ShadingType, LevelFormat, NumberFormat,
  TableLayoutType, VerticalAlign, SimpleField, LineRuleType,
} = D;

const ROOT = path.resolve(__dirname, "..");
const SRC = path.join(ROOT, "source");
const ASSETS = path.join(ROOT, "assets");
const OUT = process.argv[2] || path.join(ROOT, "output", "Cybersecurity_Project_Report_Naytik_Goyal.docx");
const CFG = JSON.parse(fs.readFileSync(path.join(SRC, "config.json"), "utf8"));
const REFS = JSON.parse(fs.readFileSync(path.join(__dirname, "refs.json"), "utf8"));
const REF = Object.fromEntries(REFS.map((r) => [r.key, r]));
let PAGEMAP = {};
try { PAGEMAP = JSON.parse(fs.readFileSync(path.join(__dirname, "pagemap.json"), "utf8")); } catch (e) { /* first pass */ }

const FONT = "Times New Roman";
const CW = 9026; // content width in DXA (A4, 2.54 cm margins)
const cited = new Set();
const warnings = [];

// ---------------------------------------------------------------- parsing
function parseFile(file) {
  const lines = fs.readFileSync(path.join(SRC, file), "utf8").split(/\r?\n/);
  const blocks = [];
  let i = 0;
  const isBlank = (l) => l.trim() === "";
  while (i < lines.length) {
    let l = lines[i];
    if (isBlank(l) || l.startsWith("<!--")) { i++; continue; }
    let m;
    if ((m = l.match(/^@chapter\s+(\d+)\s*\|\s*(.+)$/))) { blocks.push({ t: "chapter", num: +m[1], title: m[2].trim() }); i++; continue; }
    if ((m = l.match(/^@pa\s+(.+)$/))) { blocks.push({ t: "pa", text: m[1].trim() }); i++; continue; }
    if ((m = l.match(/^@uh\s+(.+)$/))) { blocks.push({ t: "uh", title: m[1].trim() }); i++; continue; }
    if ((m = l.match(/^@appendix\s+(\d+)\s*\|\s*(.+)$/))) { blocks.push({ t: "appendix", num: +m[1], title: m[2].trim() }); i++; continue; }
    if (l.startsWith("@pagebreak")) { blocks.push({ t: "pb" }); i++; continue; }
    if ((m = l.match(/^@space(?:\s+(\d+))?/))) { blocks.push({ t: "space", n: +(m[1] || 1) }); i++; continue; }
    if ((m = l.match(/^###\s+(\S+)\s+(.+)$/))) { blocks.push({ t: "h3", num: m[1], title: m[2].trim() }); i++; continue; }
    if ((m = l.match(/^##\s+(\S+)\s+(.+)$/))) { blocks.push({ t: "h2", num: m[1], title: m[2].trim() }); i++; continue; }
    if ((m = l.match(/^@figure\s+(\S+)\s*\|\s*([^|]+)\|\s*([\d.]+)\s*\|\s*(.+)$/))) {
      blocks.push({ t: "fig", id: m[1], file: m[2].trim(), w: +m[3], caption: m[4].trim() }); i++; continue;
    }
    if ((m = l.match(/^@table\s+(\S+)\s*\|\s*([^|]*)(?:\|\s*(.*))?$/))) {
      const b = { t: "table", id: m[1], caption: (m[2] || "").trim(), weights: (m[3] || "").split(",").map((x) => parseFloat(x)).filter((x) => x > 0), rows: [] };
      i++;
      while (i < lines.length && lines[i].trim().startsWith("|")) {
        const cells = lines[i].trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
        if (!cells.every((c) => /^:?-{2,}:?$/.test(c))) b.rows.push(cells);
        i++;
      }
      blocks.push(b); continue;
    }
    if ((m = l.match(/^@codefile\s+(\S+)\s*\|\s*([^|]+)\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(.+)$/))) {
      const REPO = "/Users/naytikgoyal/Downloads/repo";
      const all = fs.readFileSync(path.join(REPO, m[2].trim()), "utf8").split(/\r?\n/);
      const a = +m[3], z = +m[4];
      blocks.push({ t: "codefig", id: m[1], file: m[2].trim(), a, z, caption: m[5].trim(), lines: all.slice(a - 1, z) }); i++; continue;
    }
    if (l.startsWith("@code")) {
      const code = []; i++;
      while (i < lines.length && !lines[i].startsWith("@endcode")) { code.push(lines[i]); i++; }
      i++; blocks.push({ t: "code", lines: code }); continue;
    }
    if (/^-\s+/.test(l)) {
      const items = [];
      while (i < lines.length && (/^-\s+/.test(lines[i]) || /^\s{2,}\S/.test(lines[i]))) {
        if (/^-\s+/.test(lines[i])) items.push(lines[i].replace(/^-\s+/, "")); else items[items.length - 1] += " " + lines[i].trim();
        i++;
      }
      blocks.push({ t: "ul", items }); continue;
    }
    if (/^\d+\.\s+/.test(l)) {
      const items = [];
      while (i < lines.length && (/^\d+\.\s+/.test(lines[i]) || /^\s{2,}\S/.test(lines[i]))) {
        if (/^\d+\.\s+/.test(lines[i])) items.push(lines[i].replace(/^\d+\.\s+/, "")); else items[items.length - 1] += " " + lines[i].trim();
        i++;
      }
      blocks.push({ t: "ol", items }); continue;
    }
    const para = [];
    while (i < lines.length && !isBlank(lines[i]) && !/^(@|##|-\s|\d+\.\s)/.test(lines[i])) { para.push(lines[i].trim()); i++; }
    if (para.length) blocks.push({ t: "p", text: para.join(" ") });
    else { warnings.push(`unparsed line in ${file}: ${l}`); i++; }
  }
  return blocks;
}

// ---------------------------------------------------------------- numbering and references
const figNo = {}, tabNo = {};
function assignNumbers(blocks) {
  let f = 0, t = 0;
  const seen = new Set();
  for (const b of blocks) {
    if ((b.t === "fig" || b.t === "codefig" || (b.t === "table" && b.id !== "-"))) {
      const key = (b.t === "table" ? "tab:" : "fig:") + b.id;
      if (seen.has(key)) throw new Error("duplicate id " + key);
      seen.add(key);
    }
    if (b.t === "fig" || b.t === "codefig") { figNo[b.id] = ++f; b.no = f; }
    if (b.t === "table" && b.id !== "-") { tabNo[b.id] = ++t; b.no = t; }
  }
}

function resolveText(s) {
  s = s.replace(/\[@([^\]]+)\]/g, (_, body) => {
    const parts = body.split(";").map((x) => x.trim().replace(/^@/, ""));
    if (parts.length === 1 && /:n$/.test(parts[0])) {
      const k = parts[0].replace(/:n$/, "");
      if (!REF[k]) throw new Error("unknown citation " + k);
      cited.add(k); return REF[k].nar;
    }
    const sh = parts.map((p) => { if (!REF[p]) throw new Error("unknown citation " + p); cited.add(p); return REF[p].short; });
    return "(" + sh.join("; ") + ")";
  });
  s = s.replace(/\{fig:([^}]+)\}/g, (_, id) => { if (!figNo[id]) throw new Error("unknown figure " + id); return "Figure " + figNo[id]; });
  s = s.replace(/\{tab:([^}]+)\}/g, (_, id) => { if (!tabNo[id]) throw new Error("unknown table " + id); return "Table " + tabNo[id]; });
  return s;
}

function runs(text, base = {}) {
  text = resolveText(text);
  const out = [];
  const re = /(\*\*[^*]+\*\*|\*[^*\s][^*]*[^*\s]\*|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(new TextRun({ text: text.slice(last, m.index), font: FONT, ...base }));
    const tok = m[0];
    if (tok.startsWith("**")) out.push(new TextRun({ text: tok.slice(2, -2), bold: true, font: FONT, ...base }));
    else if (tok.startsWith("`")) out.push(new TextRun({ text: tok.slice(1, -1), font: "Courier New", size: (base.size || 24) - 3 }));
    else out.push(new TextRun({ text: tok.slice(1, -1), italics: true, font: FONT, ...base }));
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(new TextRun({ text: text.slice(last), font: FONT, ...base }));
  return out;
}

// ---------------------------------------------------------------- block rendering
function pngSize(file) {
  const b = fs.readFileSync(file);
  return { w: b.readUInt32BE(16), h: b.readUInt32BE(20) };
}
const tocEntries = []; // for pagemap
let olInstance = 0;

function renderBlock(b, ctx) {
  const out = [];
  switch (b.t) {
    case "chapter": {
      const txt = `CHAPTER ${b.num}`;
      out.push(new Paragraph({ style: "Heading1", pageBreakBefore: !ctx.firstInSection,
        children: [new TextRun({ text: txt, font: FONT }), new TextRun({ text: b.title.toUpperCase(), break: 1, font: FONT })] }));
      tocEntries.push({ id: "H:" + txt + " " + b.title.toUpperCase(), kind: "h1", text: `CHAPTER ${b.num}. ${b.title.toUpperCase()}`, match: `${txt} ${b.title.toUpperCase()}` });
      break;
    }
    case "appendix": {
      const txt = `APPENDIX-${b.num}`;
      out.push(new Paragraph({ style: "Heading1", pageBreakBefore: true,
        children: [new TextRun({ text: txt, font: FONT }), new TextRun({ text: b.title.toUpperCase(), break: 1, font: FONT })] }));
      tocEntries.push({ id: "H:" + txt + " " + b.title.toUpperCase(), kind: "h1", text: `${txt}: ${b.title.toUpperCase()}`, match: `${txt} ${b.title.toUpperCase()}` });
      break;
    }
    case "uh": {
      out.push(new Paragraph({ style: "FrontHeading", pageBreakBefore: !ctx.firstInSection, children: [new TextRun({ text: b.title.toUpperCase(), font: FONT })] }));
      if (b.title.toUpperCase() !== "TABLE OF CONTENTS" && !b.noToc) tocEntries.push({ id: "H:" + b.title.toUpperCase(), kind: "h1", text: b.title.toUpperCase(), match: b.title.toUpperCase() });
      break;
    }
    case "h2": {
      const text = `${b.num}. ${b.title}`;
      out.push(new Paragraph({ style: "Heading2", children: [new TextRun({ text, font: FONT })] }));
      if (!/^A\d/.test(b.num)) tocEntries.push({ id: "H:" + text, kind: "h2", text, match: text });
      break;
    }
    case "h3": {
      const text = `${b.num}. ${b.title}`;
      out.push(new Paragraph({ style: "Heading3", children: [new TextRun({ text, font: FONT })] }));
      break;
    }
    case "p": out.push(new Paragraph({ style: "BodyText", children: runs(b.text) })); break;
    case "pa": out.push(new Paragraph({ style: "AbstractText", children: runs(b.text, { size: 28 }) })); break;
    case "ul": for (const it of b.items) out.push(new Paragraph({ style: "ListText", numbering: { reference: "bullets", level: 0 }, children: runs(it) })); break;
    case "ol": { olInstance++; for (const it of b.items) out.push(new Paragraph({ style: "ListText", numbering: { reference: "numbers", level: 0, instance: olInstance }, children: runs(it) })); break; }
    case "space": for (let k = 0; k < b.n; k++) out.push(new Paragraph({ style: "Plain", children: [new TextRun({ text: "", font: FONT })] })); break;
    case "pb": out.push(new Paragraph({ style: "Plain", pageBreakBefore: true, children: [] })); break;
    case "code": {
      b.lines.forEach((ln, idx) => out.push(new Paragraph({ style: "Code", keepLines: true, keepNext: b.lines.length <= 45 ? idx < b.lines.length - 1 : idx < 2,
        children: [new TextRun({ text: ln.length ? ln : " ", font: "Courier New", size: 17 })] })));
      out.push(new Paragraph({ style: "Plain", children: [] }));
      break;
    }
    case "codefig": {
      const cap = `${resolveText(b.caption)} (${b.file}, lines ${b.a}-${b.z})`;
      b.lines.forEach((ln, idx) => out.push(new Paragraph({ style: "Code", keepLines: true, keepNext: b.lines.length <= 45 ? true : (idx >= b.lines.length - 3 || idx < 1),
        children: [new TextRun({ text: ln.length ? ln : " ", font: "Courier New", size: 15 })] })));
      out.push(new Paragraph({ style: "Caption", children: [new TextRun({ text: "Figure ", font: FONT, bold: true, size: 20 }),
        new SimpleField("SEQ Figure \\* ARABIC", String(b.no)), new TextRun({ text: `: ${cap}`, font: FONT, bold: true, size: 20 })] }));
      tocEntries.push({ id: "F:" + b.no, kind: "fig", text: `Figure ${b.no}: ${cap}`, match: `Figure ${b.no}: ${cap}` });
      break;
    }
    case "fig": {
      const file = path.join(ASSETS, b.file);
      const { w, h } = pngSize(file);
      let wcm = b.w, hcm = (wcm * h) / w;
      const maxh = 19.0;
      if (hcm > maxh) { wcm = (wcm * maxh) / hcm; hcm = maxh; }
      const px = (cm) => Math.round(cm * 37.795);
      out.push(new Paragraph({ style: "Figure", keepNext: true, children: [new ImageRun({ type: "png", data: fs.readFileSync(file),
        transformation: { width: px(wcm), height: px(hcm) }, altText: { title: `Figure ${b.no}`, description: b.caption, name: b.id } })] }));
      out.push(new Paragraph({ style: "Caption", children: [new TextRun({ text: "Figure ", font: FONT, bold: true, size: 20 }),
        new SimpleField("SEQ Figure \\* ARABIC", String(b.no)), new TextRun({ text: `: ${resolveText(b.caption)}`, font: FONT, bold: true, size: 20 })] }));
      tocEntries.push({ id: "F:" + b.no, kind: "fig", text: `Figure ${b.no}: ${resolveText(b.caption)}`, match: `Figure ${b.no}: ${resolveText(b.caption)}` });
      break;
    }
    case "table": {
      if (b.id !== "-") {
        out.push(new Paragraph({ style: "Caption", keepNext: true, children: [new TextRun({ text: "Table ", font: FONT, bold: true, size: 20 }),
          new SimpleField("SEQ Table \\* ARABIC", String(b.no)), new TextRun({ text: `: ${resolveText(b.caption)}`, font: FONT, bold: true, size: 20 })] }));
        tocEntries.push({ id: "T:" + b.no, kind: "tab", text: `Table ${b.no}: ${resolveText(b.caption)}`, match: `Table ${b.no}: ${resolveText(b.caption)}` });
      }
      const ncol = b.rows[0].length;
      const wts = b.weights.length === ncol ? b.weights : Array(ncol).fill(1);
      const tot = wts.reduce((a, c) => a + c, 0);
      const strip = (t) => (t || "").replace(/\*\*|`|\*/g, "");
      const longest = (ci) => Math.max(...b.rows.map((r) => Math.max(...strip(r[ci]).split(/[\s/]+/).map((w) => w.length))));
      const minw = b.rows[0].map((_, ci) => Math.min(longest(ci), 13) * 112 + 260);
      let cols = wts.map((w) => (CW * w) / tot);
      for (let it = 0; it < 8; it++) {
        let deficit = 0, free = 0;
        cols.forEach((c, i) => { if (c < minw[i]) deficit += minw[i] - c; else free += c - minw[i]; });
        if (deficit <= 0.5 || free <= 0) break;
        const k = Math.min(1, deficit / free);
        cols = cols.map((c, i) => (c < minw[i] ? minw[i] : c - (c - minw[i]) * k));
      }
      cols = cols.map((c) => Math.floor(c));
      cols[cols.length - 1] += CW - cols.reduce((a, c) => a + c, 0);
      const border = { style: BorderStyle.SINGLE, size: 4, color: "7F7F7F" };
      const borders = { top: border, bottom: border, left: border, right: border };
      const rows = b.rows.map((r, ri) => new TableRow({ tableHeader: ri === 0, cantSplit: true,
        children: r.map((c, ci) => new TableCell({ width: { size: cols[ci], type: WidthType.DXA }, borders,
          shading: ri === 0 ? { fill: "D9D9D9", type: ShadingType.CLEAR, color: "auto" } : undefined,
          margins: { top: b.id === "-" ? 25 : 50, bottom: b.id === "-" ? 25 : 50, left: 90, right: 90 }, verticalAlign: VerticalAlign.TOP,
          children: c.split(" // ").map((part) => new Paragraph({ style: "TableText", children: runs(part, ri === 0 ? { bold: true, size: 20 } : { size: 20 }) })) })) }));
      out.push(new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: cols, layout: TableLayoutType.FIXED, rows }));
      out.push(new Paragraph({ style: "Plain", children: [] }));
      break;
    }
    default: throw new Error("unknown block " + b.t);
  }
  return out;
}

// ---------------------------------------------------------------- special pages
function logoImage(wcm) {
  const file = path.join(ASSETS, "logo-cu.png");
  const { w, h } = pngSize(file);
  return new ImageRun({ type: "png", data: fs.readFileSync(file), transformation: { width: Math.round(wcm * 37.795), height: Math.round((wcm * 37.795 * h) / w) },
    altText: { title: "Chandigarh University logo", description: "Chandigarh University logo", name: "logo" } });
}
const C = (text, o = {}) => new Paragraph({ style: "Plain", alignment: AlignmentType.CENTER, spacing: { before: o.before || 0, after: o.after || 0, line: 276 },
  children: [new TextRun({ text, font: FONT, bold: o.bold, italics: o.italics, size: o.size || 28 })] });

function titlePage() {
  return [
    C(CFG.title.toUpperCase(), { bold: true, size: 34, before: 1000, after: 480 }),
    C("A PROJECT REPORT", { bold: true, size: 28, after: 360 }),
    C("Submitted by", { bold: true, italics: true, size: 28, after: 240 }),
    C(`${CFG.student.toUpperCase()} : ${CFG.uid}`, { bold: true, size: 30, after: 480 }),
    C("in partial fulfillment for the award of the degree of", { bold: true, italics: true, size: 26, after: 360 }),
    C("BACHELOR OF ENGINEERING", { bold: true, size: 30, after: 60 }),
    C("IN", { bold: true, size: 24, after: 60 }),
    C("COMPUTER SCIENCE ENGINEERING", { size: 28, after: 2000 }),
    new Paragraph({ style: "Plain", alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [logoImage(6.2)] }),
    C("Chandigarh University", { bold: true, size: 26, after: 60 }),
    C(CFG.month_year.toUpperCase(), { size: 26 }),
  ];
}

function certificatePage() {
  const noB = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
  const nb = { top: noB, bottom: noB, left: noB, right: noB };
  const L = (t, o = {}) => new Paragraph({ style: "Plain", spacing: { line: 300, after: o.after || 0 }, children: [new TextRun({ text: t, font: FONT, bold: o.bold, size: o.size || 24 })] });
  const cell = (ps) => new TableCell({ width: { size: CW / 2, type: WidthType.DXA }, borders: nb, children: ps, margins: { left: 0, right: 140 } });
  const sig = new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: [CW / 2, CW / 2], layout: TableLayoutType.FIXED, rows: [new TableRow({ children: [
    cell([L("SIGNATURE", { bold: true, after: 700 }), L(CFG.hod, { bold: true }), L("HEAD OF THE DEPARTMENT", { bold: true }), L("Department of Computer Science & Engineering"), L("Chandigarh University")]),
    cell([L("SIGNATURE", { bold: true, after: 700 }), L(CFG.supervisor, { bold: true }), L("SUPERVISOR", { bold: true }), L(CFG.supervisor_designation), L("Department of Computer Science & Engineering"), L(CFG.address)]),
  ] })] });
  return [
    new Paragraph({ style: "Plain", pageBreakBefore: true, alignment: AlignmentType.CENTER, spacing: { after: 160 }, children: [logoImage(5.6)] }),
    C("BONAFIDE CERTIFICATE", { bold: true, size: 30, after: 240 }),
    new Paragraph({ style: "Plain", alignment: AlignmentType.JUSTIFIED, spacing: { line: 480, after: 360 }, children: [
      new TextRun({ text: "Certified that this project report ", font: FONT, size: 28 }),
      new TextRun({ text: `“${CFG.title.toUpperCase()}”`, font: FONT, size: 28, bold: true }),
      new TextRun({ text: " is the bonafide work of ", font: FONT, size: 28 }),
      new TextRun({ text: `“${CFG.student.toUpperCase()}”`, font: FONT, size: 28, bold: true }),
      new TextRun({ text: " who carried out the project work under my supervision.", font: FONT, size: 28 }) ] }),
    sig,
    new Paragraph({ style: "Plain", spacing: { before: 360, after: 360, line: 300 }, children: [new TextRun({ text: `Submitted for the project viva-voce examination held on ____________ ${CFG.viva_month_year}`, font: FONT, size: 24 })] }),
    new Table({ width: { size: CW, type: WidthType.DXA }, columnWidths: [CW / 2, CW / 2], layout: TableLayoutType.FIXED, rows: [new TableRow({ children: [
      cell([L("INTERNAL EXAMINER", { bold: true })]), cell([L("EXTERNAL EXAMINER", { bold: true })]) ] })] }),
  ];
}

function toc(entries, title, kinds, opts = {}) {
  const out = [new Paragraph({ style: "FrontHeading", pageBreakBefore: true, spacing: { before: 0, after: 120 }, children: [new TextRun({ text: title, font: FONT })] })];
  for (const e of entries.filter((x) => kinds.includes(x.kind))) {
    const pg = PAGEMAP[e.id] || "";
    const lvl2 = e.kind === "h2";
    out.push(new Paragraph({ style: "TocText", indent: { left: lvl2 ? 360 : 0, right: 400, hanging: 0 },
      tabStops: [{ type: TabStopType.RIGHT, position: CW, leader: LeaderType.DOT }],
      children: [new TextRun({ text: e.text, font: FONT, bold: e.kind === "h1" && opts.boldH1 }), new TextRun({ text: "\t" + pg, font: FONT })] }));
  }
  return out;
}

// ---------------------------------------------------------------- assemble
function main() {
  const order = {
    front: [["ack.md"]],
    abstractBlock: [["abstract.md"], ["graphical.md"], ["abbrev.md"]],
    body: ["ch1.md", "ch2.md", "ch3.md", "ch4.md", "ch4b.md", "ch5.md"],
    back: ["references.md", "app1.md", "app2.md", "app3.md", "achievements.md"],
  };
  const cache = {};
  const parse = (f) => (cache[f] = cache[f] || parseFile(f));  // parse each file once so figure/table numbers stick
  const ack = parse("ack.md"), abs = parse("abstract.md"), gra = parse("graphical.md"), abb = parse("abbrev.md");
  const body = order.body.flatMap(parse);
  const back = order.back.flatMap((f) => (f === "references.md" ? [] : parse(f)));
  // figure/table numbers follow document order (front matter first, so the graphical abstract is Figure 1)
  assignNumbers([...ack, ...abs, ...gra, ...abb, ...body, ...back]);

  // render main content first to collect TOC data
  const render = (blocks, first) => blocks.flatMap((b, i) => renderBlock(b, { firstInSection: first && i === 0 }));
  const ackP = render(ack, false);
  const absP = render(abs, false), graP = render(gra, false), abbP = render(abb, false);
  const bodyP = render(body, true);
  // references
  const refP = [new Paragraph({ style: "Heading1", pageBreakBefore: true, children: [new TextRun({ text: "REFERENCES", font: FONT })] })];
  tocEntries.push({ id: "H:REFERENCES", kind: "h1", text: "REFERENCES", match: "REFERENCES" });
  REFS.forEach((r, i) => refP.push(new Paragraph({ style: "RefText", children: [new TextRun({ text: `${i + 1}.\t`, font: FONT }), new TextRun({ text: r.full, font: FONT })] })));
  const backBlocks = order.back.filter((f) => f !== "references.md");
  const backP = [];
  // order: references first, then appendices, then achievements
  const backParsed = backBlocks.map((f) => ({ f, blocks: parse(f) }));
  const backRendered = backParsed.map(({ f, blocks }) => blocks.flatMap((b) => renderBlock(b, { firstInSection: false })));
  const unused = REFS.filter((r) => !cited.has(r.key)).map((r) => r.key);
  if (unused.length) warnings.push("uncited references: " + unused.join(", "));

  // contents pages need the entries collected above
  const mainEntries = tocEntries.filter((e) => e.kind === "h1" || e.kind === "h2");
  const lofEntries = tocEntries.filter((e) => e.kind === "fig");
  const lotEntries = tocEntries.filter((e) => e.kind === "tab");
  // document order: ACKNOWLEDGEMENT, (TOC), LIST OF FIGURES, LIST OF TABLES, ABSTRACT, GRAPHICAL ABSTRACT, ABBREVIATIONS, chapters ...
  const ackE = mainEntries.filter((e) => e.id === "H:ACKNOWLEDGEMENT");
  const restE = mainEntries.filter((e) => e.id !== "H:ACKNOWLEDGEMENT");
  const contentsList = [
    ...ackE,
    { id: "H:LIST OF FIGURES", kind: "h1", text: "LIST OF FIGURES", match: "LIST OF FIGURES" },
    { id: "H:LIST OF TABLES", kind: "h1", text: "LIST OF TABLES", match: "LIST OF TABLES" },
    ...restE,
  ];
  const tocP = toc(contentsList, "TABLE OF CONTENTS", ["h1", "h2"], { boldH1: true });
  const lofP = toc(lofEntries, "LIST OF FIGURES", ["fig"]);
  const lotP = toc(lotEntries, "LIST OF TABLES", ["tab"]);
  fs.writeFileSync(path.join(__dirname, "toc.json"), JSON.stringify({ headings: contentsList, figures: lofEntries, tables: lotEntries }, null, 1));

  const footer = new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 22 })] })] });
  const emptyFooter = new Footer({ children: [new Paragraph({ children: [] })] });
  const page = (fmt) => ({ size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440, footer: 700 }, pageNumbers: { start: 1, formatType: fmt } });

  const front = [...titlePage(), ...certificatePage(), ...ackP, ...tocP, ...lofP, ...lotP, ...absP, ...graP, ...abbP];
  const doc = new Document({
    creator: CFG.student, title: CFG.title, description: "Project report", lastModifiedBy: CFG.student,
    styles: {
      default: { document: { run: { font: FONT, size: 24 } } },
      paragraphStyles: [
        { id: "BodyText", name: "Body Text", basedOn: "Normal", quickFormat: true, run: { font: FONT, size: 24 }, paragraph: { alignment: AlignmentType.JUSTIFIED, spacing: { line: 360, lineRule: LineRuleType.AUTO, after: 120 } } },
        { id: "AbstractText", name: "Abstract Text", basedOn: "Normal", run: { font: FONT, size: 28 }, paragraph: { alignment: AlignmentType.JUSTIFIED, spacing: { line: 480, after: 0 } } },
        { id: "ListText", name: "List Text", basedOn: "Normal", run: { font: FONT, size: 24 }, paragraph: { alignment: AlignmentType.JUSTIFIED, spacing: { line: 360, after: 60 } } },
        { id: "Plain", name: "Plain", basedOn: "Normal", run: { font: FONT, size: 24 }, paragraph: { spacing: { line: 276, after: 0 } } },
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "BodyText", quickFormat: true, run: { font: FONT, size: 32, bold: true }, paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 240, after: 360, line: 360 }, keepNext: true, outlineLevel: 0 } },
        { id: "FrontHeading", name: "Front Heading", basedOn: "Normal", next: "BodyText", run: { font: FONT, size: 32, bold: true }, paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 240, after: 360, line: 360 }, keepNext: true, outlineLevel: 0 } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "BodyText", quickFormat: true, run: { font: FONT, size: 28, bold: true }, paragraph: { alignment: AlignmentType.LEFT, spacing: { before: 280, after: 120, line: 360 }, keepNext: true, outlineLevel: 1 } },
        { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "BodyText", quickFormat: true, run: { font: FONT, size: 24, bold: true }, paragraph: { alignment: AlignmentType.LEFT, spacing: { before: 200, after: 80, line: 360 }, keepNext: true, outlineLevel: 2 } },
        { id: "Caption", name: "Caption", basedOn: "Normal", run: { font: FONT, size: 20, bold: true }, paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 80, after: 200, line: 276 } } },
        { id: "Figure", name: "Figure", basedOn: "Normal", paragraph: { alignment: AlignmentType.CENTER, spacing: { before: 160, after: 0, line: 240 } } },
        { id: "TableText", name: "Table Text", basedOn: "Normal", run: { font: FONT, size: 20 }, paragraph: { alignment: AlignmentType.LEFT, spacing: { line: 252, after: 0 } } },
        { id: "TocText", name: "TOC Text", basedOn: "Normal", run: { font: FONT, size: 24 }, paragraph: { spacing: { line: 360, after: 0 } } },
        { id: "RefText", name: "Reference Text", basedOn: "Normal", run: { font: FONT, size: 24 }, paragraph: { alignment: AlignmentType.LEFT, spacing: { line: 252, after: 120 }, indent: { left: 540, hanging: 540 }, tabStops: [{ type: TabStopType.LEFT, position: 540 }] } },
        { id: "Code", name: "Code", basedOn: "Normal", run: { font: "Courier New", size: 17 }, paragraph: { alignment: AlignmentType.LEFT, spacing: { line: 228, after: 0 }, shading: { type: ShadingType.CLEAR, fill: "F2F2F2", color: "auto" }, indent: { left: 120, right: 120 } } },
      ],
    },
    numbering: { config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ] },
    sections: [
      { properties: { page: page(NumberFormat.LOWER_ROMAN), titlePage: true }, footers: { default: footer, first: emptyFooter }, children: front },
      { properties: { type: SectionType.NEXT_PAGE, page: page(NumberFormat.DECIMAL) }, footers: { default: footer }, children: [...bodyP, ...refP, ...backRendered.flat()] },
    ],
  });
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  return Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(OUT, buf); console.log("wrote", OUT, (buf.length / 1024).toFixed(0) + " KB"); });
}
main().then(() => { if (warnings.length) console.log("WARNINGS:\n - " + warnings.join("\n - ")); }).catch((e) => { console.error("BUILD FAILED:", e.message); process.exit(1); });
