// Obscura — 4-Prong Healthcare Deck (pptxgenjs)
const pptxgen = require("pptxgenjs");
const p = new pptxgen();
p.defineLayout({ name: "WIDE", width: 13.33, height: 7.5 });
p.layout = "WIDE";

// ---------- palette ----------
const NAVY = "0B1826";      // dark bg
const PANEL_D = "142438";   // dark panel
const LIGHT = "F6F9FC";     // light bg
const CARD = "FFFFFF";
const LINE = "DCE6F0";
const INK = "13293F";       // headings on light
const BODY = "3A4E62";      // body on light
const MUTED = "71869B";
const ICE = "C9DCF0";       // body on dark
const MINT = "2FB48C";
const P1 = "3E8FD0", P2 = "D95550", P3 = "D9A441", P4 = "2FB48C";

const HEAD = "Georgia";
const BODYF = "Calibri";
const MONO = "Consolas";

const W = 13.33, H = 7.5, M = 0.6;

function footer(s, n, dark) {
  s.addText("Obscura  ·  open-source (Apache-2.0)  ·  built on Gemma 4", {
    x: M, y: 7.08, w: 6.5, h: 0.3, fontFace: BODYF, fontSize: 9,
    color: dark ? "5E7288" : "9AACBE", align: "left",
  });
  s.addText(String(n), {
    x: W - 1.1, y: 7.08, w: 0.5, h: 0.3, fontFace: BODYF, fontSize: 9,
    color: dark ? "5E7288" : "9AACBE", align: "right",
  });
}

function chip(s, x, y, color, num, d = 0.52) {
  s.addShape("ellipse", { x, y, w: d, h: d, fill: { color } });
  s.addText(num, { x, y: y - 0.02, w: d, h: d, align: "center", valign: "middle",
    fontFace: HEAD, fontSize: 16, bold: true, color: "FFFFFF" });
}

function tag(s, x, y, text, color) {
  s.addShape("roundRect", { x, y, w: 1.7, h: 0.34, rectRadius: 0.17, fill: { color } });
  s.addText(text, { x, y: y - 0.02, w: 1.7, h: 0.34, align: "center", valign: "middle",
    fontFace: BODYF, fontSize: 11, bold: true, color: "FFFFFF", charSpacing: 1 });
}

// ============================================================ S1 — TITLE (dark)
let s = p.addSlide();
s.background = { color: NAVY };
s.addImage({ path: "img_human_crop_title.png", x: 7.13, y: 0, w: 6.2, h: H });
s.addShape("rect", { x: 7.13, y: 0, w: 0.06, h: H, fill: { color: MINT } });
// subtle side band
s.addShape("rect", { x: 0, y: 0, w: 0.18, h: H, fill: { color: MINT } });
s.addText("OBSCURA", { x: 0.85, y: 1.55, w: 6.1, h: 1.0, fontFace: HEAD, fontSize: 46,
  bold: true, color: "FFFFFF", charSpacing: 5 });
s.addText("Open-source AI for the clinics America runs on.", {
  x: 0.88, y: 2.6, w: 5.9, h: 0.95, fontFace: HEAD, fontSize: 21, italic: true, color: ICE });
s.addText("Four tools. One laptop. Zero cloud.", {
  x: 0.88, y: 3.6, w: 5.9, h: 0.5, fontFace: BODYF, fontSize: 17, color: MINT, bold: true });
// four prong chips, 2x2
const prongTitle = [["1", "TRANSCRIBE", P1], ["2", "REDACT", P2], ["3", "SECURE", P3], ["4", "ORGANIZE", P4]];
prongTitle.forEach((pr, i) => {
  const x = 0.88 + (i % 2) * 2.95, y = 4.45 + Math.floor(i / 2) * 0.75;
  chip(s, x, y, pr[2], pr[0], 0.42);
  s.addText(pr[1], { x: x + 0.54, y: y - 0.02, w: 2.3, h: 0.46, fontFace: BODYF, fontSize: 13,
    bold: true, color: "FFFFFF", valign: "middle", charSpacing: 1.5 });
});
s.addText("GDG “Build & Hack with Gemma 4.0”  ·  July 2026\ngithub.com/meetkpatel/Obscura", {
  x: 0.88, y: 6.3, w: 5.9, h: 0.75, fontFace: BODYF, fontSize: 11.5, color: "8FA6BC" });

// ============================================================ S2 — PROBLEM (light)
s = p.addSlide();
s.background = { color: LIGHT };
s.addText("Independent medicine is drowning in unpaid computer work", {
  x: M, y: 0.45, w: 12.1, h: 0.85, fontFace: HEAD, fontSize: 32, bold: true, color: INK });
// three stat cards
const stats = [
  { big: "2 hrs", sub: "of desk + EHR work for every 1 hour of direct patient care",
    src: "Sinsky et al., Annals of Internal Medicine (AMA time-motion study)" },
  { big: "$9.8M", sub: "average cost of a healthcare data breach — the costliest industry 14 years running",
    src: "IBM Cost of a Data Breach Report, 2024" },
  { big: "31M+", sub: "patients depend on community health centers that run on thin margins",
    src: "HRSA Health Center Program data, 2023" },
];
stats.forEach((st, i) => {
  const x = M + i * 4.13;
  s.addShape("roundRect", { x, y: 1.6, w: 3.85, h: 2.9, rectRadius: 0.1, fill: { color: CARD },
    line: { color: LINE, width: 1 } });
  s.addText(st.big, { x: x + 0.25, y: 1.85, w: 3.35, h: 1.0, fontFace: HEAD, fontSize: 48,
    bold: true, color: INK });
  s.addText(st.sub, { x: x + 0.25, y: 2.95, w: 3.35, h: 1.0, fontFace: BODYF, fontSize: 13.5,
    color: BODY });
  s.addText(st.src, { x: x + 0.25, y: 4.0, w: 3.35, h: 0.45, fontFace: BODYF, fontSize: 9.5,
    italic: true, color: MUTED });
});
s.addShape("roundRect", { x: M, y: 4.85, w: 12.13, h: 1.75, rectRadius: 0.1, fill: { color: "EAF1F8" } });
s.addText([
  { text: "Behind every stat is the same clinic:  ", options: { bold: true, color: INK } },
  { text: "no IT department, no compliance officer, no enterprise software budget — and a front-desk laptop holding thousands of patient records. The paperwork burden falls on the clinicians who can least afford the time, at the practices that can least afford the tools.",
    options: { color: BODY } },
], { x: M + 0.35, y: 5.05, w: 11.45, h: 1.4, fontFace: BODYF, fontSize: 15, valign: "top" });
footer(s, 2, false);

// ============================================================ S3 — PARADOX (light)
s = p.addSlide();
s.background = { color: LIGHT };
s.addText("The clinics that need AI most are the ones that can’t use it", {
  x: M, y: 0.45, w: 12.1, h: 0.85, fontFace: HEAD, fontSize: 32, bold: true, color: INK });
const traps = [
  { h: "COST", c: P3, t: "Cloud AI scribes and document tools list at roughly $99–$600 per clinician per month. A safety-net clinic with five providers is looking at up to $36k a year — for one tool." },
  { h: "COMPLIANCE", c: P2, t: "Consumer AI tools won’t sign a Business Associate Agreement. Pasting a patient note into a chatbot isn’t a shortcut — it’s a HIPAA disclosure. The upload is the breach." },
  { h: "CAPACITY", c: P1, t: "Enterprise AI assumes an IT department to vet vendors, manage deployments, and harden machines. Most small practices have nobody whose job that is." },
];
traps.forEach((tr, i) => {
  const x = M + i * 4.13;
  s.addShape("roundRect", { x, y: 1.6, w: 3.85, h: 3.0, rectRadius: 0.1, fill: { color: CARD },
    line: { color: LINE, width: 1 } });
  s.addShape("rect", { x, y: 1.6, w: 0.14, h: 3.0, fill: { color: tr.c } });
  s.addText(tr.h, { x: x + 0.35, y: 1.85, w: 3.2, h: 0.45, fontFace: BODYF, fontSize: 16,
    bold: true, color: tr.c, charSpacing: 2 });
  s.addText(tr.t, { x: x + 0.35, y: 2.35, w: 3.25, h: 2.1, fontFace: BODYF, fontSize: 13,
    color: BODY });
});
s.addShape("roundRect", { x: M, y: 4.95, w: 12.13, h: 1.7, rectRadius: 0.1, fill: { color: NAVY } });
s.addText([
  { text: "Open weights changed the math.  ", options: { bold: true, color: MINT } },
  { text: "Gemma 4 (Apache-2.0) now runs frontier-grade reasoning on a stock laptop — no account, no per-seat fee, no data leaving the building. For the first time, the fast tool and the compliant tool are the same tool.",
    options: { color: "E8F0F8" } },
], { x: M + 0.35, y: 5.15, w: 11.45, h: 1.35, fontFace: BODYF, fontSize: 15.5, valign: "top" });
footer(s, 3, false);

// ============================================================ S4 — PLATFORM (light)
s = p.addSlide();
s.background = { color: LIGHT };
s.addText("One engine. Four prongs. Every byte stays in the building.", {
  x: M, y: 0.45, w: 12.1, h: 0.85, fontFace: HEAD, fontSize: 32, bold: true, color: INK });
const prongs = [
  { n: "1", c: P1, h: "TRANSCRIBE", t: "The visit writes itself. On-device speech-to-note — audio never touches a server." },
  { n: "2", c: P2, h: "REDACT", t: "Share the record, not the patient. HIPAA Safe Harbor redaction that destroys data and proves it." },
  { n: "3", c: P3, h: "SECURE", t: "A $0 IT department. Read-only scan for exposed secrets, weak config, and slow hardware." },
  { n: "4", c: P4, h: "ORGANIZE", t: "Files that name themselves. Gemma reads page one, proposes clean names — with one-click Undo." },
];
prongs.forEach((pr, i) => {
  const x = M + i * 3.09;
  s.addShape("roundRect", { x, y: 1.55, w: 2.85, h: 3.15, rectRadius: 0.1, fill: { color: CARD },
    line: { color: LINE, width: 1 } });
  chip(s, x + 0.28, 1.85, pr.c, pr.n, 0.5);
  s.addText(pr.h, { x: x + 0.92, y: 1.86, w: 1.85, h: 0.5, fontFace: BODYF, fontSize: 14.5,
    bold: true, color: pr.c, valign: "middle", charSpacing: 1 });
  s.addText(pr.t, { x: x + 0.28, y: 2.6, w: 2.32, h: 1.95, fontFace: BODYF, fontSize: 12.5,
    color: BODY });
});
// spine
s.addText("Every prong runs the same trust loop:", { x: M, y: 5.0, w: 6.0, h: 0.4,
  fontFace: BODYF, fontSize: 14, bold: true, color: INK });
const steps = ["SCAN", "UNDERSTAND", "PROPOSE", "APPROVE", "APPLY", "VERIFY", "UNDO"];
const stepNote = ["deterministic", "Gemma 4", "nothing silent", "a human clicks", "atomic", "checks itself", "always reversible"];
const sw = 1.62, gap = 0.13;
steps.forEach((st, i) => {
  const x = M + i * (sw + gap);
  s.addShape("roundRect", { x, y: 5.45, w: sw, h: 0.85, rectRadius: 0.08,
    fill: { color: i === 3 ? NAVY : "EAF1F8" } });
  s.addText(st, { x, y: 5.5, w: sw, h: 0.4, align: "center", fontFace: BODYF, fontSize: 11.5,
    bold: true, color: i === 3 ? "FFFFFF" : INK });
  s.addText(stepNote[i], { x, y: 5.88, w: sw, h: 0.35, align: "center", fontFace: BODYF,
    fontSize: 9, italic: true, color: i === 3 ? ICE : MUTED });
});
footer(s, 4, false);

// ---------- prong slide factory ----------
function prongSlide(num, color, name, title, tagText, tagColor, bullets, panelTitle, panelLines, note, pageNo, mono = false) {
  const sl = p.addSlide();
  sl.background = { color: LIGHT };
  chip(sl, M, 0.52, color, num, 0.56);
  sl.addText(name, { x: M + 0.7, y: 0.5, w: 3.4, h: 0.6, fontFace: BODYF, fontSize: 17,
    bold: true, color, valign: "middle", charSpacing: 2 });
  tag(sl, W - M - 1.7, 0.62, tagText, tagColor);
  sl.addText(title, { x: M, y: 1.18, w: 12.1, h: 0.8, fontFace: HEAD, fontSize: 30, bold: true, color: INK });
  // left bullets
  let y = 2.25;
  bullets.forEach(b => {
    sl.addShape("ellipse", { x: M + 0.02, y: y + 0.09, w: 0.12, h: 0.12, fill: { color } });
    sl.addText([
      { text: b[0] + "  ", options: { bold: true, color: INK } },
      { text: b[1], options: { color: BODY } },
    ], { x: M + 0.3, y, w: 6.6, h: b[2], fontFace: BODYF, fontSize: 13.5, valign: "top" });
    y += b[2] + 0.12;
  });
  // right panel
  sl.addShape("roundRect", { x: 7.75, y: 2.25, w: 4.98, h: 3.6, rectRadius: 0.1,
    fill: { color: NAVY } });
  sl.addText(panelTitle, { x: 8.05, y: 2.45, w: 4.4, h: 0.4, fontFace: BODYF, fontSize: 13,
    bold: true, color: MINT, charSpacing: 1 });
  sl.addText(panelLines, { x: 8.05, y: 2.95, w: 4.45, h: 2.75, fontFace: mono ? MONO : BODYF,
    fontSize: mono ? 11 : 12.5, color: "E8F0F8", valign: "top", lineSpacing: mono ? 16 : 18 });
  // bottom note
  sl.addShape("roundRect", { x: M, y: 6.1, w: 12.13, h: 0.72, rectRadius: 0.08, fill: { color: "EAF1F8" } });
  sl.addText(note, { x: M + 0.3, y: 6.12, w: 11.6, h: 0.68, fontFace: BODYF, fontSize: 12.5,
    italic: true, color: INK, valign: "middle" });
  footer(sl, pageNo, false);
  return sl;
}

// ============================================================ S5 — TRANSCRIBE
prongSlide("1", P1, "TRANSCRIBE", "The visit writes itself — and never leaves the room",
  "NEXT UP", "8A9BB0",
  [
    ["Capture the encounter on-device.", "Local speech-to-text runs on the clinic’s own laptop — the audio file never touches a server, so there is no third party and no BAA to sign.", 0.85],
    ["Gemma drafts the note.", "The transcript is structured into a SOAP-style draft — subjective, objective, assessment, plan — ready for the clinician to edit and sign.", 0.85],
    ["The clinician stays the author.", "Nothing enters the chart without review and an explicit click. The AI drafts; the doctor decides.", 0.6],
    ["A proven market — priced for the big systems.", "Investors put $300M+ into cloud ambient scribes in 2024 alone: Abridge ($150M at an $850M valuation), Suki ($70M), Ambience, Nabla — all sold to large health systems. Obscura brings the capability to everyone else, free. (Business Insider, Oct 2024)", 1.15],
  ],
  "WHY ON-DEVICE WINS HERE",
  [
    { text: "Visit audio is the most sensitive PHI a clinic creates.\n", options: {} },
    { text: "\nCloud scribe: audio → vendor server → BAA, subprocessors, retention policies to audit.\n", options: {} },
    { text: "\nObscura: audio → this laptop → note. The privacy review is one sentence long.", options: { color: "FFFFFF", bold: true } },
  ],
  "Status: in design — the newest prong of the four. REDACT, SECURE and ORGANIZE are working today.",
  5);

// ============================================================ S6 — REDACT
prongSlide("2", P2, "REDACT", "Share the record, not the patient",
  "SHIPPED", MINT,
  [
    ["Built on the HIPAA Safe Harbor standard.", "Detection is mapped to all 18 identifier categories of 45 CFR 164.514(b)(2)(i) — names, MRNs, member IDs, dates, geography and the rest — with a live coverage panel per document.", 1.0],
    ["Hybrid detection, on purpose.", "Pure-LLM PII detection averages ~0.54 F1. Obscura runs deterministic rules (SSN, Luhn, MRN, phone) for perfect precision, and Gemma 4 for names, addresses and context — grounded to exact pixels by OCR.", 1.0],
    ["Destroys, never covers.", "Pages are rasterized, boxes burned into pixels, metadata stripped — an image-only PDF with no text layer to copy out.", 0.75],
  ],
  "IT CHECKS ITS OWN WORK",
  [
    { text: "4-part verification battery on every export:\n\n", options: { bold: true } },
    { text: "①  Select-all test — zero selectable characters\n②  Text-search — no redacted string findable\n③  Re-OCR — nothing readable survives in pixels\n④  Metadata audit — document dictionary empty\n\n", options: {} },
    { text: "Downloadable compliance report, per document.", options: { color: "FFFFFF", bold: true } },
  ],
  "Coverage audit is technical QA, not legal advice — a human reviewer still signs off, exactly as Safe Harbor requires.",
  6);

// ============================================================ S7 — SECURE
prongSlide("3", P3, "SECURE", "A $0 IT department for the front-desk laptop",
  "SHIPPED", MINT,
  [
    ["Finds what an auditor would.", "Read-only scan for plaintext passwords and keys on disk, weak OS configuration, and risky open ports — the everyday exposures behind real clinic breaches.", 0.85],
    ["Grounded in CIS hardening checks.", "Findings map to CIS Level 1 benchmark checks, rolled into a single plain-English Safety Score anyone at the front desk can read.", 0.75],
    ["Explains, never executes.", "Gemma turns each finding into one sentence of “what this means and why it matters.” Fixes come from a hardcoded registry — the model never runs anything.", 0.85],
    ["Performance, too.", "The same scan flags what slows aging hardware — startup bloat, low disk, pending updates — so the one clinic laptop stays usable.", 0.75],
  ],
  "WHAT A SCAN RETURNS",
  [
    { text: "Safety Score: 62 → 91 after fixes\n\n", options: { bold: true, color: "FFFFFF" } },
    { text: "•  API key in plaintext on Desktop → “Send to Redactor”\n•  Disk encryption off on PHI volume\n•  Remote-desktop port open to network\n•  14 startup apps slowing boot\n\n", options: {} },
    { text: "Every fix described in plain English. You click; it never acts alone.", options: {} },
  ],
  "Defensive by design: it scans only your own machine, read-only, and describes fixes — it does not attack, probe networks, or auto-remediate.",
  7);

// ============================================================ S8 — ORGANIZE
prongSlide("4", P4, "ORGANIZE", "Files that name themselves",
  "SHIPPED", MINT,
  [
    ["Gemma reads page one.", "For each file it reads a cheap signature — first page of a PDF, first rows of a sheet, or the image itself — and returns doc-type, entity, date and a descriptor.", 0.85],
    ["Code enforces the template.", "The model supplies understanding only; a deterministic naming template builds the final name, so results are consistent every time.", 0.75],
    ["Crash-safe and reversible.", "Moves run through a journaled, atomic operation — never a delete — and one-click Undo replays the whole reorganization in reverse.", 0.75],
    ["Approve before anything moves.", "The full folder proposal is shown first; nothing happens until the human says yes.", 0.6],
  ],
  "BEFORE  →  AFTER",
  [
    { text: "scan0007.pdf\nNew Text Document.txt\ncopy of copy final.txt\nIMG_20260312 final FINAL v2.pdf\n\n", options: { color: "8FA6BC" } },
    { text: "2026-03-12_Lab-Result_Alvarez.pdf\n2026-04-02_Referral_Nguyen.pdf\n2026-05-19_Intake-Form_Okafor.pdf\n2026-06-30_Insurance-EOB_Reyes.pdf", options: { color: "FFFFFF", bold: true } },
  ],
  "A findable record is a safer record — files you can locate are files you can protect, redact, and produce on request.",
  8, true);

// ============================================================ S9 — CLINICAL WORKFLOW (light)
s = p.addSlide();
s.background = { color: LIGHT };
s.addText("A Tuesday at a two-provider clinic", {
  x: M, y: 0.45, w: 12.1, h: 0.8, fontFace: HEAD, fontSize: 32, bold: true, color: INK });
const day = [
  ["9:05 AM", P1, "TRANSCRIBE", "Walk-in visit. The note drafts itself while the door is still closed; the doctor edits and signs."],
  ["11:30 AM", P2, "REDACT", "Specialist referral goes out — the record travels, the patient's identity stays home. Coverage panel: green."],
  ["12:40 PM", P3, "SECURE", "Lunchtime scan finds one plaintext password on the front-desk laptop. Fixed in two clicks."],
  ["4:55 PM", P4, "ORGANIZE", "The day's scans and faxes are named, filed, and fully undo-able before anyone goes home."],
];
// timeline spine
s.addShape("rect", { x: M + 0.9, y: 1.75, w: 0.035, h: 4.15, fill: { color: LINE } });
day.forEach((dv, i) => {
  const y = 1.65 + i * 1.08;
  s.addShape("ellipse", { x: M + 0.78, y: y + 0.12, w: 0.28, h: 0.28, fill: { color: dv[1] } });
  s.addText(dv[0], { x: M - 0.15, y: y + 0.06, w: 0.85, h: 0.4, align: "right",
    fontFace: BODYF, fontSize: 12, bold: true, color: MUTED });
  s.addShape("roundRect", { x: M + 1.35, y, w: 10.15, h: 0.92, rectRadius: 0.08,
    fill: { color: CARD }, line: { color: LINE, width: 1 } });
  s.addText([
    { text: dv[2] + "   ", options: { bold: true, color: dv[1] } },
    { text: dv[3], options: { color: BODY } },
  ], { x: M + 1.65, y: y + 0.06, w: 9.6, h: 0.8, fontFace: BODYF, fontSize: 13.5, valign: "middle" });
});
s.addShape("roundRect", { x: M, y: 6.1, w: 12.13, h: 0.72, rectRadius: 0.08, fill: { color: "EAF1F8" } });
s.addText("Notes and redacted records export as standard PDFs today; EHR integration is the roadmap's next mile — the moat the cloud vendors built closed, we build open.", {
  x: M + 0.3, y: 6.12, w: 11.6, h: 0.68, fontFace: BODYF, fontSize: 12.5, italic: true,
  color: INK, valign: "middle" });
footer(s, 9, false);

// ============================================================ S10 — COMPETITIVE 2x2 (light)
s = p.addSlide();
s.background = { color: LIGHT };
s.addText("Everyone else is in the cloud — and priced for the big systems", {
  x: M, y: 0.45, w: 12.1, h: 0.8, fontFace: HEAD, fontSize: 30, bold: true, color: INK });
// plot area
const PX = 3.3, PY = 1.7, PW = 6.75, PH = 4.35;
s.addShape("roundRect", { x: PX, y: PY, w: PW, h: PH, rectRadius: 0.08, fill: { color: CARD },
  line: { color: LINE, width: 1 } });
// axes
s.addShape("rect", { x: PX + PW / 2 - 0.01, y: PY + 0.15, w: 0.02, h: PH - 0.3, fill: { color: LINE } });
s.addShape("rect", { x: PX + 0.15, y: PY + PH / 2 - 0.01, w: PW - 0.3, h: 0.02, fill: { color: LINE } });
// axis labels
s.addText("CLOUD", { x: PX + 0.22, y: PY + PH / 2 - 0.45, w: 1.5, h: 0.35, align: "left",
  fontFace: BODYF, fontSize: 12, bold: true, color: MUTED, charSpacing: 2 });
s.addText("ON-DEVICE", { x: PX + PW - 1.95, y: PY + PH / 2 - 0.45, w: 1.73, h: 0.35,
  align: "right", fontFace: BODYF, fontSize: 12, bold: true, color: MUTED, charSpacing: 2 });
s.addText("BUILT FOR EVERYONE", { x: PX, y: PY - 0.42, w: PW, h: 0.35, align: "center",
  fontFace: BODYF, fontSize: 12, bold: true, color: MUTED, charSpacing: 2 });
s.addText("BUILT FOR BIG HEALTH SYSTEMS", { x: PX, y: PY + PH + 0.08, w: PW, h: 0.35,
  align: "center", fontFace: BODYF, fontSize: 12, bold: true, color: MUTED, charSpacing: 2 });
// competitor dots (cloud side)
function dot(x, y, label, sub, color, big) {
  const d = big ? 0.42 : 0.24;
  s.addShape("ellipse", { x, y, w: d, h: d, fill: { color } });
  s.addText(label, { x: x - 0.9 + d / 2, y: y + d + 0.02, w: 1.8, h: 0.3, align: "center",
    fontFace: BODYF, fontSize: big ? 14 : 11, bold: true, color: big ? color : BODY });
  if (sub) s.addText(sub, { x: x - 1.15 + d / 2, y: y + d + 0.3, w: 2.3, h: 0.3, align: "center",
    fontFace: BODYF, fontSize: 9.5, italic: true, color: MUTED });
}
dot(PX + 0.85, PY + 2.75, "Abridge", "$850M valuation", "8A9BB0");
dot(PX + 2.15, PY + 3.3, "Suki", "$165M raised", "8A9BB0");
dot(PX + 0.75, PY + 3.55, "Ambience · DAX", null, "8A9BB0");
dot(PX + 1.0, PY + 0.75, "Freed", null, "8A9BB0");
dot(PX + 2.3, PY + 0.5, "Nabla · DeepScribe", null, "8A9BB0");
dot(PX + PW - 1.7, PY + 0.62, "OBSCURA", "free · open-source", MINT, true);
// takeaway band
s.addShape("roundRect", { x: 10.45, y: 1.7, w: 2.28, h: 4.35, rectRadius: 0.08, fill: { color: NAVY } });
s.addText("THE OPEN\nQUADRANT", { x: 10.6, y: 1.95, w: 2.0, h: 0.8, fontFace: BODYF,
  fontSize: 13, bold: true, color: MINT, charSpacing: 1 });
s.addText("Every funded player sells cloud AI to institutions.\n\nOn-device + built-for-everyone is empty — because there was no business model for it.\n\nOpen source is the business model.", {
  x: 10.6, y: 2.8, w: 2.0, h: 3.1, fontFace: BODYF, fontSize: 11.5, color: "E8F0F8" });
s.addText("Positioning per Business Insider funding coverage, Oct 2024; company placements approximate.", {
  x: M, y: 6.55, w: 12.1, h: 0.35, fontFace: BODYF, fontSize: 9.5, italic: true, color: MUTED });
footer(s, 10, false);

// ============================================================ S11 — WHAT THIS REPLACES (light)
s = p.addSlide();
s.background = { color: LIGHT };
s.addText("What a small clinic pays for this today", {
  x: M, y: 0.45, w: 12.1, h: 0.75, fontFace: HEAD, fontSize: 32, bold: true, color: INK });
const costs = [
  ["AI scribe", P1, "$299–$1,512", "per clinician / month", "Suki $299–399 · DAX Copilot list $1,512 (typ. $369–830 + $5k–50k setup) · budget tier: Freed $79–119"],
  ["Redaction software", P2, "$279–$379", "per user / month", "CaseGuard Doc/Ultimate suites · budget tier: Redactable from $278/yr"],
  ["Managed IT + HIPAA", P3, "$100–$250", "per user / month", "small-practice HIPAA-ready managed IT; HIPAA compliance support adds $15–30/user"],
  ["File & records admin", P4, "staff hours", "every single day", "manual naming, filing, and hunting for documents — unpriced but paid in time"],
];
costs.forEach((c, i) => {
  const y = 1.45 + i * 1.08;
  s.addShape("roundRect", { x: M, y, w: 8.35, h: 0.95, rectRadius: 0.08,
    fill: { color: CARD }, line: { color: LINE, width: 1 } });
  s.addShape("rect", { x: M, y, w: 0.12, h: 0.95, fill: { color: c[1] } });
  s.addText(c[0], { x: M + 0.3, y: y + 0.08, w: 2.15, h: 0.4, fontFace: BODYF, fontSize: 14,
    bold: true, color: INK });
  s.addText([
    { text: c[2] + "  ", options: { bold: true, color: c[1], fontSize: 16 } },
    { text: c[3], options: { color: MUTED, fontSize: 11 } },
  ], { x: M + 0.3, y: y + 0.44, w: 2.9, h: 0.45, fontFace: BODYF });
  s.addText(c[4], { x: M + 3.35, y: y + 0.06, w: 4.85, h: 0.85, fontFace: BODYF, fontSize: 10.5,
    color: BODY, valign: "middle" });
});
// obscura column
s.addShape("roundRect", { x: 9.2, y: 1.45, w: 3.53, h: 4.19, rectRadius: 0.1, fill: { color: NAVY } });
s.addText("OBSCURA", { x: 9.45, y: 1.75, w: 3.0, h: 0.45, fontFace: HEAD, fontSize: 18,
  bold: true, color: "FFFFFF", charSpacing: 3 });
s.addText("$0", { x: 9.45, y: 2.25, w: 3.0, h: 1.2, fontFace: HEAD, fontSize: 64, bold: true, color: MINT });
s.addText("per clinician · per month · forever\n\nApache-2.0, on hardware the clinic already owns. A 2-provider clinic replaces $15,000+ a year of the stack at left.", {
  x: 9.45, y: 3.5, w: 3.05, h: 1.95, fontFace: BODYF, fontSize: 12, color: "E8F0F8" });
s.addShape("roundRect", { x: M, y: 5.85, w: 12.13, h: 0.85, rectRadius: 0.08, fill: { color: "EAF1F8" } });
s.addText([
  { text: "The market says the pain is real:  ", options: { bold: true, color: INK } },
  { text: "AI clinical documentation is a $1.2–2.8B market today, forecast to reach ~$15B by 2034–35 (19–29% CAGR across analyst houses). All of it cloud. None of it priced for small practices.",
    options: { color: BODY } },
], { x: M + 0.3, y: 5.95, w: 11.6, h: 0.7, fontFace: BODYF, fontSize: 12.5, valign: "middle" });
s.addText("Pricing: vendor list/published reseller pages + 2026 pricing guides (Freed, Suki, Microsoft/Nuance, CaseGuard, Redactable, MSP surveys); market size: Dataintelo, Astute Analytica, SNS Insider, Grand View 2025–26 reports. Ranges are list prices, verify per quote.", {
  x: M, y: 6.78, w: 12.1, h: 0.3, fontFace: BODYF, fontSize: 8.5, italic: true, color: MUTED });
footer(s, 11, false);

// ============================================================ S12 — TRUST (light)
s = p.addSlide();
s.background = { color: LIGHT };
s.addText("Privacy you can watch. Safety by architecture.", {
  x: M, y: 0.45, w: 12.1, h: 0.8, fontFace: HEAD, fontSize: 32, bold: true, color: INK });
const trust = [
  { h: "External connections: 0", t: "A live egress panel lists every network connection the app holds. Run it with Wi-Fi off — everything still works. That’s the proof, not a promise." },
  { h: "Human-in-the-loop, everywhere", t: "No redaction, no file move, no machine change without an explicit click. The AI proposes; a person disposes." },
  { h: "Verification is a feature", t: "REDACT re-opens its own output and attacks it. ORGANIZE journals every move for Undo. The tool assumes it made a mistake and checks." },
];
trust.forEach((tr, i) => {
  const x = M + i * 4.13;
  s.addShape("roundRect", { x, y: 1.55, w: 3.85, h: 2.5, rectRadius: 0.1, fill: { color: CARD },
    line: { color: LINE, width: 1 } });
  s.addText(tr.h, { x: x + 0.28, y: 1.78, w: 3.3, h: 0.65, fontFace: BODYF, fontSize: 16,
    bold: true, color: INK });
  s.addText(tr.t, { x: x + 0.28, y: 2.5, w: 3.3, h: 1.45, fontFace: BODYF, fontSize: 12.5, color: BODY });
});
// prongs feed each other band
s.addShape("roundRect", { x: M, y: 4.4, w: 12.13, h: 2.15, rectRadius: 0.1, fill: { color: NAVY } });
s.addText("THE PRONGS FEED EACH OTHER", { x: M + 0.35, y: 4.6, w: 6, h: 0.4,
  fontFace: BODYF, fontSize: 13, bold: true, color: MINT, charSpacing: 1.5 });
const flow = [["SECURE", P3, "finds a plaintext\nkey on disk"], ["REDACT", P2, "destroys it —\nprovably"], ["ORGANIZE", P4, "files the clean\nresult"], ["TRANSCRIBE", P1, "feeds notes into\nthe same loop"]];
flow.forEach((f, i) => {
  const x = M + 0.5 + i * 3.0;
  s.addShape("roundRect", { x, y: 5.1, w: 2.35, h: 1.15, rectRadius: 0.08, fill: { color: PANEL_D },
    line: { color: f[1], width: 1.5 } });
  s.addText(f[0], { x, y: 5.2, w: 2.35, h: 0.35, align: "center", fontFace: BODYF, fontSize: 12,
    bold: true, color: f[1] });
  s.addText(f[2], { x, y: 5.55, w: 2.35, h: 0.65, align: "center", fontFace: BODYF, fontSize: 10.5,
    color: "D5E2EF" });
  if (i < 3) s.addText("→", { x: x + 2.38, y: 5.35, w: 0.6, h: 0.5, align: "center",
    fontFace: BODYF, fontSize: 22, bold: true, color: MINT });
});
footer(s, 12, false);

// ============================================================ S12 — PROOF (light)
s = p.addSlide();
s.background = { color: LIGHT };
s.addText("Built, demoed, and self-verified — in a one-day sprint", {
  x: M, y: 0.45, w: 12.1, h: 0.7, fontFace: HEAD, fontSize: 28, bold: true, color: INK });
s.addText("GDG “Build & Hack with Gemma 4.0” — Newport Beach, July 2026", {
  x: M, y: 1.18, w: 12.1, h: 0.45, fontFace: BODYF, fontSize: 15, italic: true, color: MUTED });
const proofs = [
  { big: "3 / 4", sub: "prongs working end-to-end today — REDACT, SECURE, ORGANIZE — on synthetic demo data" },
  { big: "0", sub: "recoverable characters after redaction: select-all, text-search, re-OCR and metadata checks all pass" },
  { big: "16/18", sub: "HIPAA Safe Harbor identifier categories flagged on a synthetic patient record, shown in the coverage panel" },
  { big: "8 GB", sub: "of laptop GPU is enough — hardware probe auto-selects the right Gemma 4 variant per machine" },
];
proofs.forEach((pr, i) => {
  const x = M + (i % 2) * 6.15, y = 1.95 + Math.floor(i / 2) * 2.15;
  s.addShape("roundRect", { x, y, w: 5.95, h: 1.95, rectRadius: 0.1, fill: { color: CARD },
    line: { color: LINE, width: 1 } });
  s.addText(pr.big, { x: x + 0.3, y: y + 0.25, w: 1.85, h: 1.45, fontFace: HEAD, fontSize: 40,
    bold: true, color: MINT, valign: "middle" });
  s.addText(pr.sub, { x: x + 2.25, y: y + 0.22, w: 3.5, h: 1.55, fontFace: BODYF, fontSize: 12.5,
    color: BODY, valign: "middle" });
});
s.addText([
  { text: "Open code, open license:  ", options: { bold: true, color: INK } },
  { text: "github.com/meetkpatel/Obscura  ·  Apache-2.0, mirroring Gemma 4’s own license  ·  all demo data synthetic — no real PHI, ever",
    options: { color: BODY } },
], { x: M, y: 6.3, w: 12.1, h: 0.5, fontFace: BODYF, fontSize: 13.5 });
footer(s, 13, false);

// ============================================================ S14 — CLOSE (dark)
s = p.addSlide();
s.background = { color: NAVY };
s.addShape("rect", { x: 0, y: 0, w: 0.18, h: H, fill: { color: MINT } });
s.addText("Frontier AI shouldn’t be a luxury good.", {
  x: 1.0, y: 1.0, w: 11.3, h: 0.9, fontFace: HEAD, fontSize: 38, bold: true, color: "FFFFFF" });
s.addText("The practices serving the most vulnerable patients deserve the same AI leverage as the biggest health systems — without the subscription, the BAA, or the data leaving the building. Open-source models finally make that possible. Obscura is the wrapper that makes it usable.", {
  x: 1.03, y: 2.05, w: 11.0, h: 1.2, fontFace: BODYF, fontSize: 16.5, color: ICE });
const road = [
  ["NOW", "Ship the TRANSCRIBE prong — on-device visit notes"],
  ["NEXT", "One-click installer + pilots with community clinics"],
  ["THEN", "The same four prongs for legal aid, social work, schools"],
];
road.forEach((r, i) => {
  const x = 1.03 + i * 3.95;
  s.addShape("roundRect", { x, y: 3.6, w: 3.7, h: 1.5, rectRadius: 0.1, fill: { color: PANEL_D } });
  s.addText(r[0], { x: x + 0.25, y: 3.78, w: 3.2, h: 0.4, fontFace: BODYF, fontSize: 13,
    bold: true, color: MINT, charSpacing: 2 });
  s.addText(r[1], { x: x + 0.25, y: 4.2, w: 3.25, h: 0.8, fontFace: BODYF, fontSize: 13, color: "E8F0F8" });
});
s.addText([
  { text: "The ask:  ", options: { bold: true, color: "FFFFFF" } },
  { text: "pilot clinics to shape TRANSCRIBE  ·  open-source contributors  ·  EHR-integration partners",
    options: { color: ICE } },
], { x: 1.03, y: 5.3, w: 11.3, h: 0.45, fontFace: BODYF, fontSize: 15 });
s.addText("As fast as AI. As private as a locked filing cabinet.", {
  x: 1.03, y: 5.9, w: 11.3, h: 0.55, fontFace: HEAD, fontSize: 24, italic: true, color: MINT });
s.addText("github.com/meetkpatel/Obscura   ·   Apache-2.0   ·   built on Gemma 4", {
  x: 1.03, y: 6.55, w: 11.3, h: 0.4, fontFace: BODYF, fontSize: 13, color: "8FA6BC" });

// ---------- write ----------
p.writeFile({ fileName: process.argv[2] || "20260718_Obscura_4-Prong_Healthcare_Deck.pptx" })
  .then(f => console.log("WROTE " + f));
