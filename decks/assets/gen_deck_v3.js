// Obscura Overview — Palantir-AIP-baseline deck (grammar: Palantir; voice: Obscura; humanity: medical decks)
const pptxgen = require("pptxgenjs");
const p = new pptxgen();
p.defineLayout({ name: "WIDE", width: 13.33, height: 7.5 });
p.layout = "WIDE";

const BLACK = "101014";      // near-black
const PANEL = "17171C";      // dark panel
const LIGHT = "F2F2EF";      // warm paper white
const INK = "141414";
const GRAY = "8C8C8C";
const LGRAY = "B9B9B4";
const DGRAY = "55555A";
const MINT = "2FC49E";
const RED = "E05A55";
const WHITE = "FFFFFF";

const SANS = "Arial";
const HEADF = "Segoe UI Light";
const SEMI = "Segoe UI Semibold";
const MONO = "Consolas";
const W = 13.33, H = 7.5;

const CHAPTERS = ["Who This Is For", "Private Clinical AI", "One Engine, Four Surfaces", "Obscura in Action", "Getting Started"];

// ---------- chrome helpers ----------
function cropMarks(s, color) {
  const c = color || DGRAY;
  s.addText("┌", { x: 0.25, y: 0.2, w: 0.4, h: 0.4, fontFace: MONO, fontSize: 14, color: c });
  s.addText("└", { x: 0.25, y: 6.9, w: 0.4, h: 0.4, fontFace: MONO, fontSize: 14, color: c });
}
function glyphs(s, dark) {
  s.addText("-+++++-+-++++", { x: 10.4, y: 7.0, w: 2.6, h: 0.3, align: "right",
    fontFace: MONO, fontSize: 10, color: dark ? DGRAY : LGRAY, charSpacing: 2 });
}
function header(s, chapterIdx, dark) {
  s.addText("OBSCURA", { x: 0.55, y: 0.38, w: 1.6, h: 0.35, fontFace: SANS, fontSize: 13,
    bold: true, color: dark ? WHITE : INK, charSpacing: 2 });
  // dot progress
  CHAPTERS.forEach((c, i) => {
    s.addShape("ellipse", { x: 2.9 + i * 0.28, y: 0.48, w: 0.13, h: 0.13,
      fill: i === chapterIdx ? { color: dark ? WHITE : INK } : { type: "none" },
      line: { color: dark ? GRAY : GRAY, width: 0.75 } });
  });
  s.addText(CHAPTERS[chapterIdx], { x: 4.45, y: 0.38, w: 4.0, h: 0.35, fontFace: SANS,
    fontSize: 10.5, color: dark ? LGRAY : GRAY });
}
function microFooter(s, dark) {
  s.addText("The content herein describes a working prototype built at the GDG “Build & Hack with Gemma 4.0” sprint. All demo data synthetic — no real PHI. © Obscura contributors, Apache-2.0.", {
    x: 0.55, y: 7.12, w: 9.0, h: 0.28, fontFace: SANS, fontSize: 7.5, color: dark ? DGRAY : LGRAY });
}

// Editable PowerPoint pictograms. Native shapes keep the workflow slide crisp
// in PowerPoint, Keynote, and PDF export without relying on SVG support.
function featureIcon(slide, kind, x, y, size, color = WHITE) {
  const line = { color, width: 1.75, beginArrowType: "none", endArrowType: "none" };
  const clear = { color: BLACK, transparency: 100 };
  const sx = (n) => x + n * size;
  const sy = (n) => y + n * size;
  const ss = (n) => n * size;

  if (kind === "capture") {
    slide.addShape("roundRect", { x: sx(0.34), y: sy(0.06), w: ss(0.32), h: ss(0.52), rectRadius: 0.04,
      fill: clear, line });
    slide.addShape("line", { x: sx(0.18), y: sy(0.39), w: 0, h: ss(0.15), line });
    slide.addShape("line", { x: sx(0.82), y: sy(0.39), w: 0, h: ss(0.15), line });
    slide.addShape("line", { x: sx(0.18), y: sy(0.54), w: ss(0.64), h: 0, line });
    slide.addShape("line", { x: sx(0.5), y: sy(0.54), w: 0, h: ss(0.25), line });
    slide.addShape("line", { x: sx(0.28), y: sy(0.82), w: ss(0.44), h: 0, line });
  } else if (kind === "upload") {
    slide.addShape("line", { x: sx(0.5), y: sy(0.12), w: 0, h: ss(0.48), line });
    slide.addShape("line", { x: sx(0.5), y: sy(0.12), w: ss(-0.2), h: ss(0.2), line });
    slide.addShape("line", { x: sx(0.5), y: sy(0.12), w: ss(0.2), h: ss(0.2), line });
    slide.addShape("line", { x: sx(0.18), y: sy(0.66), w: ss(0.64), h: 0, line });
    slide.addShape("line", { x: sx(0.18), y: sy(0.66), w: 0, h: ss(0.18), line });
    slide.addShape("line", { x: sx(0.82), y: sy(0.66), w: 0, h: ss(0.18), line });
    slide.addShape("line", { x: sx(0.18), y: sy(0.84), w: ss(0.64), h: 0, line });
  } else if (kind === "transcribe") {
    const bars = [0.28, 0.5, 0.76, 0.42, 0.84, 0.56, 0.32];
    bars.forEach((height, i) => {
      const bx = 0.14 + i * 0.12;
      slide.addShape("line", { x: sx(bx), y: sy(0.5 - height / 2), w: 0, h: ss(height), line });
    });
  } else if (kind === "structure") {
    slide.addShape("rect", { x: sx(0.2), y: sy(0.08), w: ss(0.6), h: ss(0.82), fill: clear, line });
    slide.addText("SOAP", { x: sx(0.22), y: sy(0.19), w: ss(0.56), h: ss(0.2), align: "center",
      fontFace: SANS, fontSize: 7.2, bold: true, color, margin: 0, charSpacing: 0.4 });
    [0.48, 0.61, 0.74].forEach((yy, i) => {
      slide.addShape("line", { x: sx(0.31), y: sy(yy), w: ss(i === 2 ? 0.28 : 0.38), h: 0,
        line: { color, width: 1.1 } });
    });
  } else if (kind === "review") {
    slide.addShape("ellipse", { x: sx(0.1), y: sy(0.27), w: ss(0.8), h: ss(0.46), fill: clear, line });
    slide.addShape("ellipse", { x: sx(0.39), y: sy(0.39), w: ss(0.22), h: ss(0.22),
      fill: { color }, line: { color, transparency: 100 } });
  } else if (kind === "control") {
    slide.addShape("ellipse", { x: sx(0.08), y: sy(0.08), w: ss(0.84), h: ss(0.84), fill: clear, line });
    slide.addText("✓", { x: sx(0.16), y: sy(0.18), w: ss(0.68), h: ss(0.58), align: "center",
      valign: "mid", fontFace: SANS, fontSize: size * 38, bold: true, color, margin: 0 });
  }
}

// ============================================================ 1 — TITLE (Palantir grammar: light grotesk, full-bleed object, ledger footer)
let s = p.addSlide();
s.background = { color: BLACK };
// full-bleed monolith: the redacted document, right column edge-to-edge
s.addImage({ path: "img_redact_cover.png", x: 8.0, y: 0, w: 5.33, h: H });
s.addShape("rect", { x: 8.0, y: 0, w: 0.02, h: H, fill: { color: "2A2A32" } });
s.addImage({ path: "../../public/brand-lockup.png", x: 0.48, y: 0.08, w: 2.55, h: 1.7 });
s.addText("Obscura\nOverview", { x: 0.5, y: 1.28, w: 7.2, h: 2.35, fontFace: HEADF,
  fontSize: 62, color: WHITE, lineSpacing: 72, charSpacing: 0 });
s.addText("Private clinical AI on the clinic’s own laptop", {
  x: 0.55, y: 3.92, w: 7.2, h: 0.5, fontFace: SANS, fontSize: 18, color: LGRAY });
// Primary brand mark from the application repo; it sits on the cover's dark
// field without introducing a second rectangular panel over the hero image.
// WHO IT SERVES — the client ledger (Kevin directive: audience on the cover)
s.addShape("rect", { x: 0.55, y: 4.6, w: 7.0, h: 0.012, fill: { color: DGRAY } });
s.addText([
  { text: "BUILT FOR /  ", options: { color: MINT, bold: true } },
  { text: "COMMUNITY CLINICS · SMALL & RURAL PRACTICES · FQHCs — AND EVERY HEALTH SYSTEM ALREADY PAYING FOR CLOUD TRANSCRIPTION", options: { color: LGRAY } },
], { x: 0.55, y: 4.72, w: 7.0, h: 0.65, fontFace: MONO, fontSize: 9, lineSpacing: 13 });
s.addText([
  { text: "MARKET PROOF /  ", options: { color: MINT, bold: true } },
  { text: "EMORY · YALE NEW HAVEN · UNC HEALTH · CHRISTUS · COREWELL · U. KANSAS HEALTH SYSTEM +8 MORE ALREADY BUY CLOUD SCRIBES (ABRIDGE PUBLIC ROSTER) — SUKI COUNTS 300 SYSTEM & CLINIC CLIENTS", options: { color: LGRAY } },
], { x: 0.55, y: 5.32, w: 7.0, h: 0.8, fontFace: MONO, fontSize: 9, lineSpacing: 13 });
// footer ledger — three ruled columns, shared baseline
const colX = [0.55, 3.35, 6.15], colW = [2.6, 2.6, 1.65];
s.addShape("rect", { x: colX[0], y: 6.35, w: colW[0], h: 0.012, fill: { color: DGRAY } });
s.addShape("rect", { x: colX[1], y: 6.35, w: colW[1], h: 0.012, fill: { color: DGRAY } });
s.addShape("rect", { x: colX[2], y: 6.35, w: colW[2], h: 0.012, fill: { color: DGRAY } });
s.addText("OBSCURA / SOFTWARE\nFOUR TOOLS. ONE LAPTOP.\nZERO CLOUD.", { x: colX[0], y: 6.45, w: colW[0], h: 0.9,
  fontFace: MONO, fontSize: 8.5, color: LGRAY, lineSpacing: 12, valign: "top" });
s.addText("LICENSE /  APACHE-2.0\nMODEL /  GEMMA 4, LOCAL\nDATA PATH /  STAYS HOME", { x: colX[1], y: 6.45, w: colW[1], h: 0.9,
  fontFace: MONO, fontSize: 8.5, color: LGRAY, lineSpacing: 12, valign: "top" });
s.addText("BUILT /  JULY 2026\n→  GITHUB.COM/\n    MEETKPATEL/OBSCURA", { x: colX[2], y: 6.45, w: colW[2] + 0.15, h: 0.9,
  fontFace: MONO, fontSize: 8.5, color: LGRAY, lineSpacing: 12, valign: "top" });

// ---------- divider factory ----------
function divider(chapterTitle) {
  const d = p.addSlide();
  d.background = { color: BLACK };
  cropMarks(d);
  d.addText("Obscura →", { x: 0.55, y: 3.35, w: 4.5, h: 0.7, fontFace: SANS,
    fontSize: 26, color: DGRAY });
  d.addText(chapterTitle, { x: 6.3, y: 3.35, w: 6.4, h: 0.9, fontFace: SANS,
    fontSize: 26, color: WHITE });
  glyphs(d, true);
  d.addText("OBSCURA", { x: 12.0, y: 0.35, w: 0.95, h: 0.35, align: "right", fontFace: SANS,
    fontSize: 11, bold: true, color: WHITE, charSpacing: 2 });
  return d;
}

// ============================================================ 2 — DIVIDER: WHO THIS IS FOR
divider("Who This Is For");

// ============================================================ 3 — WHO (light, ledger + human photo)
s = p.addSlide();
s.background = { color: LIGHT };
header(s, 0, false);
s.addText([
  { text: "Obscura builds private AI for ", options: { color: INK } },
  { text: "the clinics America runs on", options: { color: INK, underline: true } },
  { text: ".", options: { color: INK } },
], { x: 0.55, y: 1.0, w: 6.6, h: 1.5, fontFace: SANS, fontSize: 28, bold: true });
const facts = [
  ["THE DESK TAX", "2 hours of desk + EHR work per 1 hour of direct patient care.", "Sinsky et al., Annals of Internal Medicine"],
  ["THE EXODUS", "1 in 5 physicians intend to leave medicine within two years.", "Mayo Clinic Proceedings survey"],
  ["THE EXPOSURE", "$9.8M average healthcare breach — costliest industry, 14 years running.", "IBM Cost of a Data Breach, 2024"],
  ["THE PEOPLE", "31M+ patients depend on community health centers on thin margins.", "HRSA Health Center Program, 2023"],
];
let fy = 2.75;
facts.forEach(f => {
  s.addShape("rect", { x: 0.55, y: fy, w: 6.3, h: 0.012, fill: { color: LGRAY } });
  s.addText(f[0], { x: 0.55, y: fy + 0.07, w: 1.75, h: 0.75, fontFace: MONO, fontSize: 9.5,
    bold: true, color: GRAY });
  s.addText([
    { text: f[1] + "  ", options: { color: INK, fontSize: 11.5 } },
    { text: f[2], options: { color: GRAY, fontSize: 8.5, italic: true } },
  ], { x: 2.4, y: fy + 0.07, w: 4.45, h: 0.92, fontFace: SANS, valign: "top" });
  fy += 1.02;
});
s.addImage({ path: "img_human_crop_title.png", x: 7.4, y: 1.0, w: 5.35, h: 5.9,
  sizing: { type: "crop", x: 0, y: 0, w: 5.35, h: 5.9 } });
microFooter(s, false);

// ============================================================ 3b — THE MARKET IS ALREADY PAYING (light, name-wall)
s = p.addSlide();
s.background = { color: LIGHT };
header(s, 0, false);
s.addText([
  { text: "The market is already paying — ", options: { color: INK } },
  { text: "just not for everyone", options: { color: INK, underline: true } },
  { text: ".", options: { color: INK } },
], { x: 0.55, y: 0.95, w: 7.4, h: 1.0, fontFace: SEMI, fontSize: 26 });
// left: market ledger
const mkt2 = [
  ["CATEGORY TODAY", "$1.2–2.8B AI clinical documentation market, forecast ~$15B by 2034–35 (19–29% CAGR across analyst houses)."],
  ["THE INCUMBENTS", "Abridge $5.3B valuation · Suki $165M raised, 300 system & clinic clients · Nuance DAX list price $1,512/clinician/mo."],
  ["THE CEILING", "All of it cloud. All of it priced for enterprise health systems with IT departments and BAA counsel."],
  ["THE OPENING", "Most U.S. physicians work in practices of 10 or fewer (AMA benchmark) — the segment no cloud vendor prices for. That segment is ours, at $0."],
];
let m2y = 2.15;
mkt2.forEach(r => {
  s.addShape("rect", { x: 0.55, y: m2y, w: 6.55, h: 0.012, fill: { color: LGRAY } });
  s.addText(r[0], { x: 0.55, y: m2y + 0.08, w: 1.9, h: 0.8, fontFace: MONO, fontSize: 9,
    bold: true, color: GRAY });
  s.addText(r[1], { x: 2.55, y: m2y + 0.08, w: 4.55, h: 1.0, fontFace: SANS, fontSize: 10.5, color: INK });
  m2y += 1.12;
});
// right: typeset client name wall (Palantir logo-wall grammar, honestly attributed)
s.addText("WHO ALREADY BUYS CLOUD TRANSCRIPTION — ABRIDGE'S PUBLIC CUSTOMER ROSTER", {
  x: 7.55, y: 2.15, w: 5.25, h: 0.45, fontFace: MONO, fontSize: 8.5, bold: true, color: GRAY, charSpacing: 1 });
const roster = ["Emory Healthcare", "Yale New Haven Health", "UNC Health", "CHRISTUS Health",
  "Corewell Health", "U. Kansas Health System", "Rochester Regional", "Cambridge Health Alliance",
  "Akron Children’s", "Lee Health", "Riverside Health", "Reid Health", "Tanner Health", "U. Vermont Health"];
roster.forEach((n, i) => {
  const cx = 7.55 + (i % 2) * 2.68, cy = 2.75 + Math.floor(i / 2) * 0.52;
  s.addText(n, { x: cx, y: cy, w: 2.6, h: 0.42, fontFace: SEMI, fontSize: 10.5, color: "3A3A3A", valign: "middle" });
  s.addShape("rect", { x: cx, y: cy + 0.44, w: 2.5, h: 0.01, fill: { color: "D8D8D2" } });
});
s.addText("Every name above signed with a cloud vendor. Every clinic below their size threshold could not — until the tooling became free and local.", {
  x: 7.55, y: 6.5, w: 5.25, h: 0.6, fontFace: SANS, fontSize: 9, italic: true, color: GRAY });
microFooter(s, false);

// ============================================================ 3c — THE DOCUMENTATION PAIN (light ledger, same grammar as Who)
s = p.addSlide();
s.background = { color: LIGHT };
header(s, 0, false);
s.addText("The visit ends.\nDocumentation starts.", { x: 0.55, y: 1.0, w: 6.35, h: 1.38,
  fontFace: SANS, fontSize: 31, bold: true, color: INK, margin: 0 });
s.addText("The care happens in the room. The burden follows clinicians out of it.", {
  x: 0.55, y: 2.62, w: 6.1, h: 0.6, fontFace: SANS, fontSize: 14.5, italic: true, color: GRAY, margin: 0 });
const painFacts = [
  ["THE DESK TAX", "2 hours of desk + EHR work for every 1 hour of direct patient care.", "Sinsky et al., Annals of Internal Medicine"],
  ["THE EXODUS", "1 in 5 physicians intend to leave medicine within two years.", "Mayo Clinic Proceedings physician survey"],
  ["THE PEOPLE", "31M+ patients depend on community health centers running on thin margins.", "HRSA Health Center Program, 2023"],
];
let pfy = 3.55;
painFacts.forEach(f => {
  s.addShape("rect", { x: 0.55, y: pfy, w: 6.45, h: 0.012, fill: { color: LGRAY } });
  s.addText(f[0], { x: 0.55, y: pfy + 0.08, w: 1.65, h: 0.55, fontFace: MONO, fontSize: 9,
    bold: true, color: GRAY });
  s.addText([{ text: f[1] + "  ", options: { color: INK, fontSize: 10.8 } },
    { text: f[2], options: { color: GRAY, fontSize: 8.3, italic: true } }], {
    x: 2.25, y: pfy + 0.08, w: 4.7, h: 0.7, fontFace: SANS, valign: "top", margin: 0 });
  pfy += 0.98;
});
s.addImage({ path: "img_burnout_crop.png", x: 7.55, y: 1.0, w: 5.2, h: 5.9,
  sizing: { type: "crop", x: 0, y: 0, w: 5.2, h: 5.9 } });
s.addShape("rect", { x: 7.55, y: 5.63, w: 5.2, h: 1.27,
  fill: { color: BLACK, transparency: 28 }, line: { color: BLACK, transparency: 100 } });
s.addText("THE GAP IS NOT A LACK OF AI.\nIT IS A LACK OF ACCESS.", { x: 7.95, y: 5.9, w: 4.25, h: 0.65,
  fontFace: MONO, fontSize: 10, bold: true, color: WHITE, charSpacing: 0.8, margin: 0 });
microFooter(s, false);

// ============================================================ 4 — DIVIDER: WHAT IS NEEDED
divider("What is needed for\nprivate clinical AI?");

// ---------- progressive diagram factory ----------
function beatSlide(chapterIdx, titleParts, sideNote, middle) {
  const b = p.addSlide();
  b.background = { color: LIGHT };
  header(b, chapterIdx, false);
  b.addText(titleParts, { x: 0.55, y: 0.95, w: 7.6, h: 1.05, fontFace: SANS, fontSize: 26, bold: true });
  if (sideNote) b.addText(sideNote, { x: 8.5, y: 0.95, w: 4.3, h: 1.15, fontFace: SANS,
    fontSize: 12, color: GRAY });
  // dark canvas
  b.addShape("roundRect", { x: 0.55, y: 2.2, w: 12.23, h: 4.55, rectRadius: 0.12, fill: { color: BLACK } });
  // left column
  b.addText("The clinic’s\nreality", { x: 1.15, y: 2.6, w: 2.3, h: 0.85, align: "center",
    fontFace: SANS, fontSize: 13.5, color: WHITE });
  b.addText("Visit audio\n\nPatient documents\n\nA messy file system\n\nOne aging laptop", {
    x: 1.15, y: 3.6, w: 2.3, h: 2.6, align: "center", fontFace: SANS, fontSize: 11.5,
    color: LGRAY, lineSpacing: 17 });
  // right column
  b.addText("The clinician’s\nneed", { x: 9.9, y: 2.6, w: 2.3, h: 0.85, align: "center",
    fontFace: SANS, fontSize: 13.5, color: WHITE });
  b.addText("Signed notes\n\nShareable, safe records\n\nA protected machine\n\nFindable files", {
    x: 9.9, y: 3.6, w: 2.3, h: 2.6, align: "center", fontFace: SANS, fontSize: 11.5,
    color: LGRAY, lineSpacing: 17 });
  // arrows
  b.addText("→", { x: 3.55, y: 4.2, w: 0.6, h: 0.6, align: "center", fontFace: SANS,
    fontSize: 22, color: GRAY });
  b.addText("→", { x: 9.2, y: 4.2, w: 0.6, h: 0.6, align: "center", fontFace: SANS,
    fontSize: 22, color: GRAY });
  middle(b);
  microFooter(b, false);
  return b;
}

// ============================================================ 5 — BEAT 1: "?"
beatSlide(1,
  [{ text: "How does AI reach the exam room ", options: { color: INK } },
   { text: "safely", options: { color: INK, underline: true } },
   { text: "?", options: { color: INK } }],
  null,
  (b) => {
    b.addShape("rect", { x: 6.05, y: 4.05, w: 1.2, h: 0.9, fill: { type: "none" },
      line: { color: WHITE, width: 1.25 } });
    b.addText("?", { x: 6.05, y: 4.05, w: 1.2, h: 0.9, align: "center", valign: "middle",
      fontFace: SANS, fontSize: 26, color: WHITE });
  });

// ============================================================ 6 — BEAT 2: CLOUD ✗
beatSlide(1,
  [{ text: "Not through the cloud.", options: { color: INK } }],
  "Consumer AI tools won’t sign a HIPAA Business Associate Agreement. For a patient record, the upload is the disclosure.",
  (b) => {
    b.addText("Cloud AI scribes · chatbots · SaaS redaction", { x: 4.45, y: 3.15, w: 4.4, h: 0.4,
      align: "center", fontFace: SANS, fontSize: 11.5, color: LGRAY });
    b.addShape("roundRect", { x: 4.95, y: 3.7, w: 3.4, h: 1.35, rectRadius: 0.08,
      fill: { color: PANEL }, line: { color: "32323A", width: 1 } });
    b.addText("$299–$1,512 / clinician / mo\nBAA + subprocessors to audit\nPHI leaves the building", {
      x: 4.95, y: 3.8, w: 3.4, h: 1.15, align: "center", fontFace: SANS, fontSize: 10.5,
      color: LGRAY, lineSpacing: 15 });
    b.addShape("ellipse", { x: 6.32, y: 5.35, w: 0.66, h: 0.66, fill: { color: RED } });
    b.addText("✕", { x: 6.32, y: 5.33, w: 0.66, h: 0.66, align: "center", valign: "middle",
      fontFace: SANS, fontSize: 20, bold: true, color: WHITE });
  });

// ============================================================ 7 — BEAT 3: OBSCURA ✓
beatSlide(1,
  [{ text: "Through one engine that ", options: { color: INK } },
   { text: "never leaves the room", options: { color: INK, underline: true } },
   { text: ".", options: { color: INK } }],
  "Gemma 4 — open weights, Apache-2.0 — runs frontier reasoning on the laptop the clinic already owns.",
  (b) => {
    b.addShape("roundRect", { x: 4.35, y: 2.95, w: 4.6, h: 3.35, rectRadius: 0.1,
      fill: { color: PANEL }, line: { color: MINT, width: 1.5, dashType: "dash" } });
    b.addText("THE OBSCURA ENGINE  ·  ON-DEVICE", { x: 4.35, y: 3.12, w: 4.6, h: 0.3,
      align: "center", fontFace: MONO, fontSize: 9.5, bold: true, color: MINT, charSpacing: 1 });
    const mods = [["SCAN", "deterministic rules"], ["GEMMA 4", "reads · reasons · classifies"],
      ["APPROVE", "a human clicks — always"], ["VERIFY", "attacks its own output"]];
    mods.forEach((m, i) => {
      const mx = 4.7 + (i % 2) * 2.0, my = 3.6 + Math.floor(i / 2) * 1.28;
      b.addShape("roundRect", { x: mx, y: my, w: 1.9, h: 1.12, rectRadius: 0.06,
        fill: { color: m[0] === "GEMMA 4" ? "0E2A22" : BLACK },
        line: { color: m[0] === "GEMMA 4" ? MINT : "32323A", width: m[0] === "GEMMA 4" ? 1.5 : 1 } });
      b.addText(m[0], { x: mx, y: my + 0.12, w: 1.9, h: 0.35, align: "center", fontFace: SANS,
        fontSize: 11.5, bold: true, color: m[0] === "GEMMA 4" ? MINT : WHITE });
      b.addText(m[1], { x: mx + 0.05, y: my + 0.5, w: 1.8, h: 0.55, align: "center",
        fontFace: SANS, fontSize: 8.5, color: LGRAY });
    });
    b.addText("Network egress: 0", { x: 4.35, y: 6.32, w: 4.6, h: 0.3, align: "center",
      fontFace: MONO, fontSize: 10, bold: true, color: MINT });
  });

// ============================================================ 8 — DIVIDER: ONE ENGINE FOUR SURFACES
divider("One engine.\nFour surfaces.");

// ============================================================ 9 — FOUR SURFACES (dark editorial + capability ledger)
s = p.addSlide();
s.background = { color: BLACK };
header(s, 2, true);
const surf = [
  ["01", "Transcribe", "The visit writes itself.", "on-device speech → SOAP draft → clinician signs · no BAA because no third party", "IN DESIGN"],
  ["02", "Redact", "Share the record, not the patient.", "all 18 HIPAA Safe Harbor identifier categories · destroys pixels, never covers text", "SHIPPED"],
  ["03", "Secure", "A $0 IT department.", "CIS Level 1 checks · plaintext-secret scan · Safety Score · read-only, never executes", "SHIPPED"],
  ["04", "Organize", "Files that name themselves.", "Gemma reads page one · template-enforced names · crash-safe journal · one-click Undo", "SHIPPED"],
];
let sy = 1.35;
surf.forEach(r => {
  s.addText(r[0], { x: 0.75, y: sy + 0.18, w: 0.7, h: 0.45, fontFace: MONO, fontSize: 13,
    bold: true, color: MINT });
  s.addText(r[1], { x: 1.55, y: sy, w: 3.1, h: 0.8, fontFace: SANS, fontSize: 27, bold: true,
    color: WHITE, valign: "middle" });
  s.addText(r[2], { x: 4.8, y: sy + 0.05, w: 3.3, h: 0.42, fontFace: SANS, fontSize: 13.5,
    color: WHITE, valign: "middle" });
  s.addText(r[3], { x: 4.8, y: sy + 0.44, w: 6.0, h: 0.4, fontFace: SANS, fontSize: 10,
    color: GRAY, valign: "top" });
  s.addText(r[4], { x: 11.35, y: sy + 0.18, w: 1.4, h: 0.4, align: "right", fontFace: MONO,
    fontSize: 9.5, bold: true, color: r[4] === "SHIPPED" ? MINT : GRAY, charSpacing: 1 });
  s.addShape("rect", { x: 0.75, y: sy + 1.02, w: 12.0, h: 0.012, fill: { color: "2A2A32" } });
  sy += 1.17;
});
s.addText("The surfaces feed each other: SECURE finds a plaintext key → REDACT destroys it → ORGANIZE files the result.", {
  x: 0.75, y: 6.25, w: 12.0, h: 0.4, fontFace: SANS, fontSize: 12, italic: true, color: LGRAY });
microFooter(s, true);

// ============================================================ 9b — GEMMA ACROSS THE FOUR PILLARS (pal_06 grammar)
s = p.addSlide();
s.background = { color: BLACK };
header(s, 2, true);
// gradient-style claim banner (Palantir p6: full-width title with highlighted phrases)
s.addText([
  { text: "One local ", options: { color: WHITE } },
  { text: "Gemma 4", options: { color: MINT } },
  { text: " model powers every surface — ", options: { color: WHITE } },
  { text: "before, during, and after", options: { color: MINT } },
  { text: " each patient touchpoint", options: { color: WHITE } },
], { x: 0.55, y: 0.95, w: 12.2, h: 0.95, fontFace: SEMI, fontSize: 22 });
s.addShape("rect", { x: 0.55, y: 1.95, w: 12.23, h: 0.014, fill: { color: "2A2A32" } });
// center core
s.addShape("roundRect", { x: 5.29, y: 3.55, w: 2.75, h: 1.5, rectRadius: 0.08,
  fill: { color: "0E2A22" }, line: { color: MINT, width: 2 } });
s.addText("GEMMA 4", { x: 5.29, y: 3.72, w: 2.75, h: 0.45, align: "center", fontFace: SEMI,
  fontSize: 17, color: MINT, charSpacing: 2 });
s.addText("text · vision · reasoning\none Ollama gateway", { x: 5.29, y: 4.2, w: 2.75, h: 0.7,
  align: "center", fontFace: SANS, fontSize: 9.5, color: LGRAY, lineSpacing: 13 });
// four pillar blocks (2 left, 2 right), connectors to core
const pillars = [
  ["01  TRANSCRIBE", "visit audio → structured SOAP draft", "no third party — no BAA", 0.85, 2.5],
  ["03  SECURE", "explains findings in plain English", "CIS L1 checks · Safety Score", 0.85, 4.72],
  ["02  REDACT", "finds meaning; OCR pins the pixels", "18 Safe Harbor identifier types", 9.28, 2.5],
  ["04  ORGANIZE", "reads page one → doc-type · entity · date", "code enforces names · Undo journal", 9.28, 4.72],
];
pillars.forEach(pl => {
  s.addShape("roundRect", { x: pl[3], y: pl[4], w: 3.2, h: 1.42, rectRadius: 0.08,
    fill: { color: PANEL }, line: { color: "32323A", width: 1 } });
  s.addText(pl[0], { x: pl[3] + 0.2, y: pl[4] + 0.12, w: 2.85, h: 0.35, fontFace: MONO,
    fontSize: 11, bold: true, color: WHITE, charSpacing: 1 });
  s.addText(pl[1], { x: pl[3] + 0.2, y: pl[4] + 0.5, w: 2.85, h: 0.45, fontFace: SANS,
    fontSize: 10, color: LGRAY });
  s.addText(pl[2], { x: pl[3] + 0.2, y: pl[4] + 0.95, w: 2.85, h: 0.4, fontFace: SANS,
    fontSize: 9, color: MINT });
});
// connectors (thin lines core ↔ pillars)
s.addShape("line", { x: 4.05, y: 3.35, w: 1.24, h: 0.85, line: { color: "3A5A50", width: 1.25 } });
s.addShape("line", { x: 4.05, y: 5.55, w: 1.24, h: -0.6, line: { color: "3A5A50", width: 1.25 } });
s.addShape("line", { x: 8.04, y: 4.2, w: 1.24, h: -0.85, line: { color: "3A5A50", width: 1.25 } });
s.addShape("line", { x: 8.04, y: 4.55, w: 1.24, h: 1.0, line: { color: "3A5A50", width: 1.25 } });
// shared substrate strip
s.addShape("roundRect", { x: 2.4, y: 6.38, w: 8.5, h: 0.58, rectRadius: 0.29,
  fill: { color: PANEL }, line: { color: "32323A", width: 1 } });
s.addText("SHARED SPINE /  structured-JSON output · retry + repair loop · serialized GPU queue · hardware probe picks E4B or 12B · runs on an 8 GB laptop, Wi-Fi off", {
  x: 2.7, y: 6.42, w: 8.0, h: 0.5, align: "center", fontFace: MONO, fontSize: 8.5,
  color: LGRAY, valign: "middle" });
microFooter(s, true);

// ============================================================ 9c — FOCUSED SCRIBE WORKFLOW (dark capability flow)
s = p.addSlide();
s.background = { color: BLACK };
header(s, 2, true);
s.addText([
  { text: "From conversation to ", options: { color: WHITE } },
  { text: "clinician control", options: { color: MINT } },
  { text: ".", options: { color: WHITE } },
], { x: 0.55, y: 0.96, w: 12.2, h: 0.7, fontFace: SEMI, fontSize: 27, margin: 0 });
s.addText("The focused MVP is one complete, transcript-grounded scribe workflow — not a disconnected feature list.", {
  x: 0.55, y: 1.76, w: 10.5, h: 0.42, fontFace: SANS, fontSize: 12.5, color: LGRAY, margin: 0 });

const focusedFeatures = [
  ["01", "capture", "Capture", "Ambient · dictate · pause"],
  ["02", "upload", "Upload", "Audio · PDF · document"],
  ["03", "transcribe", "Transcribe", "Whisper + timestamps"],
  ["04", "structure", "Structure", "Gemma → SOAP / template"],
  ["05", "review", "Review", "Draft + transcript evidence"],
  ["06", "control", "Control", "Edit · reprocess · save"],
];
const featureStartX = 0.82, featureGapX = 2.12, featureNodeY = 2.73;
s.addShape("line", { x: 1.22, y: featureNodeY + 0.42, w: 10.88, h: 0,
  line: { color: "32323A", width: 1.5 } });
focusedFeatures.forEach((feature, index) => {
  const [number, kind, title, detail] = feature;
  const x = featureStartX + index * featureGapX;
  if (index < focusedFeatures.length - 1) {
    s.addText("→", { x: x + 1.35, y: featureNodeY + 0.18, w: 0.62, h: 0.46, align: "center",
      fontFace: SANS, fontSize: 16, bold: true, color: DGRAY, margin: 0 });
  }
  s.addText(number, { x: x + 0.02, y: 2.3, w: 0.8, h: 0.24, align: "center",
    fontFace: MONO, fontSize: 9, bold: true, color: MINT, charSpacing: 1.2, margin: 0 });
  s.addShape("ellipse", { x, y: featureNodeY, w: 0.84, h: 0.84,
    fill: { color: PANEL }, line: { color: MINT, width: 1.5 } });
  featureIcon(s, kind, x + 0.2, featureNodeY + 0.2, 0.44);
  s.addText(title, { x: x - 0.42, y: 3.77, w: 1.68, h: 0.38, align: "center",
    fontFace: SEMI, fontSize: 15.5, color: WHITE, margin: 0 });
  s.addText(detail, { x: x - 0.48, y: 4.24, w: 1.8, h: 0.5, align: "center",
    fontFace: SANS, fontSize: 9.7, color: GRAY, margin: 0 });
});

s.addShape("roundRect", { x: 1.7, y: 5.3, w: 9.93, h: 1.02, rectRadius: 0.08,
  fill: { color: PANEL }, line: { color: "32323A", width: 1 } });
featureIcon(s, "control", 2.08, 5.54, 0.5, MINT);
s.addText("Human review is the final step, not a footnote.", { x: 2.85, y: 5.45, w: 5.25, h: 0.34,
  fontFace: SEMI, fontSize: 15.5, color: WHITE, margin: 0 });
s.addText("Every SOAP note is labeled an unverified draft until a clinician reviews and edits it.", {
  x: 2.85, y: 5.82, w: 7.95, h: 0.3, fontFace: SANS, fontSize: 10.8, color: LGRAY, margin: 0 });
microFooter(s, true);

// ============================================================ 10 — DIVIDER: OBSCURA IN ACTION
divider("Obscura in Action");

// ============================================================ 11 — PROOF CATALOG (light)
s = p.addSlide();
s.background = { color: LIGHT };
header(s, 3, false);
s.addText([
  { text: "Built in one day. ", options: { color: INK } },
  { text: "Verified before it was demoed", options: { color: INK, underline: true } },
  { text: ".", options: { color: INK } },
], { x: 0.55, y: 0.95, w: 8.5, h: 0.7, fontFace: SANS, fontSize: 26, bold: true });
// results ledger left
const res = [
  ["0", "recoverable characters after redaction — select-all, text-search, re-OCR, metadata audit all pass"],
  ["16/18", "HIPAA Safe Harbor identifier categories flagged on a synthetic patient record, live coverage panel"],
  ["4", "verification checks the tool runs against its own output on every single export"],
  ["8 GB", "of laptop GPU is enough — a hardware probe picks the right Gemma 4 variant per machine"],
];
let ry = 1.95;
res.forEach(r => {
  s.addShape("rect", { x: 0.55, y: ry, w: 6.9, h: 0.012, fill: { color: LGRAY } });
  s.addText(r[0], { x: 0.55, y: ry + 0.1, w: 1.45, h: 0.9, fontFace: SANS, fontSize: 30,
    bold: true, color: MINT });
  s.addText(r[1], { x: 2.15, y: ry + 0.14, w: 5.3, h: 0.95, fontFace: SANS, fontSize: 10.5, color: INK });
  ry += 1.13;
});
// use-case index right (Palantir catalog grammar)
s.addText("VERIFICATION INDEX", { x: 7.95, y: 1.95, w: 4.8, h: 0.3, fontFace: MONO, fontSize: 10,
  bold: true, color: GRAY, charSpacing: 1 });
const idx = [
  ["01/", "SELECT-ALL TEST", "zero selectable characters", "PASS"],
  ["02/", "TEXT-SEARCH", "no redacted string findable", "PASS"],
  ["03/", "RE-OCR", "nothing readable survives in pixels", "PASS"],
  ["04/", "METADATA AUDIT", "document dictionary empty", "PASS"],
  ["05/", "EGRESS PANEL", "external connections: zero, live", "PASS"],
  ["06/", "UNDO REPLAY", "full reorganization reversed", "PASS"],
];
let iy = 2.35;
idx.forEach(r => {
  s.addShape("rect", { x: 7.95, y: iy, w: 4.8, h: 0.012, fill: { color: LGRAY } });
  s.addText(r[0], { x: 7.95, y: iy + 0.06, w: 0.5, h: 0.35, fontFace: MONO, fontSize: 9, color: GRAY });
  s.addText(r[1], { x: 8.45, y: iy + 0.06, w: 1.9, h: 0.35, fontFace: SANS, fontSize: 9.5, bold: true, color: INK });
  s.addText(r[2], { x: 10.35, y: iy + 0.06, w: 1.8, h: 0.42, fontFace: SANS, fontSize: 8, color: GRAY });
  s.addShape("roundRect", { x: 12.2, y: iy + 0.08, w: 0.55, h: 0.26, rectRadius: 0.13, fill: { color: "DDEDE6" } });
  s.addText(r[3], { x: 12.2, y: iy + 0.06, w: 0.55, h: 0.3, align: "center", fontFace: MONO,
    fontSize: 7.5, bold: true, color: "1E7A5F" });
  iy += 0.72;
});
microFooter(s, false);

// ============================================================ 12 — WHAT IT REPLACES (light ledger)
s = p.addSlide();
s.background = { color: LIGHT };
header(s, 3, false);
s.addText([
  { text: "The market charges ", options: { color: INK } },
  { text: "$15,000+ a year", options: { color: INK, underline: true } },
  { text: " for what a two-provider clinic gets here at $0.", options: { color: INK } },
], { x: 0.55, y: 0.95, w: 12.2, h: 1.0, fontFace: SANS, fontSize: 25, bold: true });
const mkt = [
  ["AI SCRIBE", "$299–$1,512 / clinician / mo", "Suki · Nuance DAX Copilot (list $1,512; typical $369–830 + $5k–50k setup) · budget tier Freed $79–119"],
  ["REDACTION SUITE", "$279–$379 / user / mo", "CaseGuard Doc & Ultimate suites · budget tier Redactable from $278/yr"],
  ["MANAGED IT + HIPAA", "$100–$250 / user / mo", "small-practice HIPAA-ready MSP plans · HIPAA support adds $15–30/user"],
  ["OBSCURA", "$0 · forever", "Apache-2.0, on hardware the clinic already owns — in a $1.2–2.8B market headed to ~$15B by 2034–35, all cloud, none priced for small practices"],
];
let my = 2.35;
mkt.forEach((r, i) => {
  const last = i === 3;
  s.addShape("rect", { x: 0.55, y: my, w: 12.23, h: 0.012, fill: { color: last ? MINT : LGRAY } });
  s.addText(r[0], { x: 0.55, y: my + 0.12, w: 2.6, h: 0.5, fontFace: MONO, fontSize: 10.5,
    bold: true, color: last ? "1E7A5F" : GRAY, charSpacing: 1 });
  s.addText(r[1], { x: 3.3, y: my + 0.06, w: 3.1, h: 0.6, fontFace: SANS, fontSize: 16,
    bold: true, color: last ? "1E7A5F" : INK });
  s.addText(r[2], { x: 6.6, y: my + 0.1, w: 6.1, h: 0.85, fontFace: SANS, fontSize: 9.5, color: last ? INK : GRAY });
  my += 1.0;
});
s.addText("Pricing: vendor list / published reseller pages + 2026 pricing guides; market size: Dataintelo, Astute Analytica, SNS Insider, Grand View 2025–26. List prices — verify per quote.", {
  x: 0.55, y: 6.55, w: 12.2, h: 0.3, fontFace: SANS, fontSize: 8, italic: true, color: GRAY });
microFooter(s, false);

// ============================================================ 13 — DIVIDER: GETTING STARTED
divider("Getting Started");

// ============================================================ 14 — GETTING STARTED (split, bootcamp grammar)
s = p.addSlide();
s.background = { color: LIGHT };
header(s, 4, false);
s.addText("From zero to private AI\nin one afternoon.", { x: 0.55, y: 1.05, w: 6.6, h: 1.5,
  fontFace: SANS, fontSize: 30, bold: true, color: INK });
const steps = [
  "Install Ollama · pull Gemma 4 (two commands)",
  "Clone the repo · pip install · run one server",
  "Turn the Wi-Fi off — everything still works",
  "Redact, scan, and organize with a human click on every action",
];
let gy = 2.85;
steps.forEach((st, i) => {
  s.addShape("rect", { x: 0.55, y: gy, w: 6.3, h: 0.012, fill: { color: LGRAY } });
  s.addText(String(i + 1).padStart(2, "0"), { x: 0.55, y: gy + 0.09, w: 0.6, h: 0.4,
    fontFace: MONO, fontSize: 10.5, bold: true, color: MINT });
  s.addText(st, { x: 1.25, y: gy + 0.07, w: 5.6, h: 0.5, fontFace: SANS, fontSize: 11.5, color: INK });
  gy += 0.72;
});
s.addText("The ask:  pilot clinics to shape TRANSCRIBE  ·  open-source contributors  ·  EHR-integration partners", {
  x: 0.55, y: 6.0, w: 6.6, h: 0.65, fontFace: SANS, fontSize: 11.5, bold: true, color: INK });
// right menu panel
s.addShape("rect", { x: 7.6, y: 0, w: 5.73, h: H, fill: { color: "E9E9E4" } });
s.addText("The same four surfaces generalize —", { x: 8.0, y: 1.05, w: 4.9, h: 0.4,
  fontFace: SANS, fontSize: 12, italic: true, color: GRAY });
const verts = ["OBSCURA FOR CLINICS", "OBSCURA FOR LEGAL AID", "OBSCURA FOR SOCIAL WORK", "OBSCURA FOR SCHOOLS", "OBSCURA FOR FOIA OFFICES", "OBSCURA FOR COURTS", "OBSCURA FOR SHELTERS", "OBSCURA FOR EVERYONE"];
let vy = 1.7;
verts.forEach((v, i) => {
  const fade = [INK, INK, "3A3A3A", "5A5A5A", "7A7A7A", "979792", "AFAFAA", "C4C4BF"][i];
  s.addText(v, { x: 8.0, y: vy, w: 4.9, h: 0.5, fontFace: SANS, fontSize: 15, bold: true, color: fade });
  s.addShape("rect", { x: 8.0, y: vy + 0.5, w: 4.75, h: 0.012, fill: { color: "CFCFC9" } });
  vy += 0.62;
});
microFooter(s, false);

// ============================================================ 15 — CLOSE
s = p.addSlide();
s.background = { color: BLACK };
cropMarks(s);
s.addImage({ path: "../../public/brand-lockup.png", x: 4.35, y: 0.02, w: 4.65, h: 2.65,
  transparency: 0 });
s.addText("As fast as AI.\nAs private as a locked filing cabinet.", {
  x: 0.55, y: 2.82, w: 12.23, h: 1.7, align: "center", fontFace: SANS, fontSize: 34,
  bold: true, color: WHITE });
s.addText("Open models made this inevitable. We just built it first.", {
  x: 0.55, y: 4.65, w: 12.23, h: 0.5, align: "center", fontFace: SANS, fontSize: 15, color: MINT });
s.addText("OBSCURA   ·   GITHUB.COM/MEETKPATEL/OBSCURA   ·   BUILT ON GEMMA 4   ·   APACHE-2.0", {
  x: 0.55, y: 5.3, w: 12.23, h: 0.4, align: "center", fontFace: MONO, fontSize: 10.5,
  color: LGRAY, charSpacing: 1 });
glyphs(s, true);

p.writeFile({ fileName: process.argv[2] || "20260718_Obscura_Overview_PalantirGrade_FocusedMVP.pptx" })
  .then(f => console.log("WROTE " + f));
