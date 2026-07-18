// Obscura — 90-second keynote-style pitch deck (big text, one idea per slide)
const pptxgen = require("pptxgenjs");
const p = new pptxgen();
p.defineLayout({ name: "WIDE", width: 13.33, height: 7.5 });
p.layout = "WIDE";

const NAVY = "0A1420";
const PANEL = "142438";
const ICE = "C9DCF0";
const DIM = "7C92A8";
const MINT = "2FC49E";
const P1 = "4FA0DC", P2 = "E05A55", P3 = "E0AC4A", P4 = "2FC49E";
const HEAD = "Georgia";
const BODYF = "Calibri";
const W = 13.33, H = 7.5;

function base() {
  const s = p.addSlide();
  s.background = { color: NAVY };
  return s;
}

let pageNo = 1;
function mark(s) {
  pageNo += 1;
  s.addText("OBSCURA", { x: 11.55, y: 7.02, w: 1.35, h: 0.32, align: "right",
    fontFace: HEAD, fontSize: 9, bold: true, color: "44586E", charSpacing: 3 });
  s.addText(String(pageNo), { x: 0.45, y: 7.02, w: 0.5, h: 0.32,
    fontFace: BODYF, fontSize: 9, color: "44586E" });
}

// big statement slide: huge centered line + small support line
function statement(big, bigSize, support, opts = {}) {
  const s = base();
  s.addText(big, {
    x: 0.7, y: opts.bigY ?? 2.3, w: 11.93, h: opts.bigH ?? 2.2, align: "center",
    fontFace: HEAD, fontSize: bigSize, bold: true,
    color: opts.bigColor ?? "FFFFFF", valign: "middle",
  });
  if (support) s.addText(support, {
    x: 1.6, y: opts.supY ?? 4.9, w: 10.13, h: 0.9, align: "center",
    fontFace: BODYF, fontSize: opts.supSize ?? 18, color: opts.supColor ?? DIM, valign: "top",
  });
  mark(s);
  return s;
}

// ---------------------------------------------------------------- 1 TITLE
let s = base();
s.addImage({ path: "img_hero_dark.png", x: 0, y: 0, w: W, h: H, sizing: { type: "cover", w: W, h: H } });
s.addShape("rect", { x: 0, y: 0, w: W, h: H, fill: { color: NAVY, transparency: 45 } });
s.addText("OBSCURA", { x: 0.7, y: 2.35, w: 11.93, h: 1.5, align: "center",
  fontFace: HEAD, fontSize: 80, bold: true, color: "FFFFFF", charSpacing: 10 });
s.addText("Four tools. One laptop. Zero cloud.", { x: 0.7, y: 4.05, w: 11.93, h: 0.7,
  align: "center", fontFace: BODYF, fontSize: 26, bold: true, color: MINT });
s.addText("Open-source AI for the clinics America runs on", { x: 0.7, y: 4.8, w: 11.93, h: 0.5,
  align: "center", fontFace: HEAD, fontSize: 18, italic: true, color: DIM });

// ---------------------------------------------------------------- 2 STAT
s = base();
s.addImage({ path: "img_burnout_crop.png", x: 0, y: 0, w: 6.6, h: H });
s.addText([
  { text: "2 hours", options: { color: MINT } },
  { text: " at a desk\nfor every ", options: {} },
  { text: "1 hour", options: { color: MINT } },
  { text: " with a patient.", options: {} },
], { x: 7.0, y: 2.1, w: 5.8, h: 2.6, align: "left", fontFace: HEAD, fontSize: 44,
  bold: true, color: "FFFFFF", valign: "middle" });
s.addText("That’s a doctor’s day now — and one in five say they intend to leave medicine within two years.", {
  x: 7.0, y: 4.85, w: 5.6, h: 0.85, fontFace: BODYF, fontSize: 18, color: ICE });
s.addText("AMA time-motion study, Annals of Internal Medicine  ·  intent-to-leave: Mayo Clinic Proceedings physician survey", {
  x: 7.0, y: 5.75, w: 5.6, h: 0.6, fontFace: BODYF, fontSize: 12, italic: true, color: DIM });
mark(s);

// ---------------------------------------------------------------- 3 PARADOX
statement("The clinics that need AI most\nare the ones that can’t use it.", 44,
  "Cloud AI costs hundreds per doctor per month  ·  won’t sign a HIPAA agreement  ·  assumes an IT department",
  { bigH: 2.4 });

// ---------------------------------------------------------------- 4 THE LINE
statement("The upload is the breach.", 60,
  "Sending a patient record to a cloud AI to ask “what’s sensitive?” is itself the disclosure.",
  { bigColor: P2, supSize: 20, supColor: ICE });

// ---------------------------------------------------------------- 5 TURN
statement("Open models changed everything.", 48,
  "Gemma 4  ·  Apache-2.0  ·  frontier reasoning on a stock laptop — no account, no fee, no network",
  { supSize: 18 });

// ---------------------------------------------------------------- 6 FOUR PRONGS
s = base();
s.addText("One engine. Four prongs.", { x: 0.7, y: 0.75, w: 11.93, h: 0.9, align: "center",
  fontFace: HEAD, fontSize: 44, bold: true, color: "FFFFFF" });
const prongs = [
  ["01", "Transcribe", "The visit writes itself."],
  ["02", "Redact", "Share the record, not the patient."],
  ["03", "Secure", "A $0 IT department."],
  ["04", "Organize", "Files that name themselves."],
];
prongs.forEach((pr, i) => {
  const y = 1.95 + i * 1.02;
  s.addText(pr[0], { x: 1.5, y: y + 0.18, w: 0.85, h: 0.5, fontFace: BODYF,
    fontSize: 15, bold: true, color: MINT });
  s.addText(pr[1], { x: 2.5, y, w: 4.6, h: 0.8, fontFace: HEAD,
    fontSize: 34, bold: true, color: "FFFFFF", valign: "middle" });
  s.addText(pr[2], { x: 7.2, y, w: 4.6, h: 0.8, align: "right", fontFace: BODYF,
    fontSize: 17, color: DIM, valign: "middle" });
  if (i < 3) s.addShape("rect", { x: 1.5, y: y + 0.93, w: 10.3, h: 0.012, fill: { color: "263646" } });
});
s.addText("AI proposes.  A human approves.  It verifies itself.", {
  x: 0.7, y: 6.25, w: 11.93, h: 0.55, align: "center", fontFace: BODYF, fontSize: 16, color: DIM });
mark(s);

// ---------------------------------------------------------------- 7 ARCHITECTURE
s = base();
s.addText("Everything happens inside the laptop.", { x: 0.7, y: 0.6, w: 11.93, h: 0.85,
  align: "center", fontFace: HEAD, fontSize: 38, bold: true, color: "FFFFFF" });
// trust boundary
s.addShape("roundRect", { x: 2.95, y: 1.85, w: 7.55, h: 3.15, rectRadius: 0.12,
  fill: { color: PANEL }, line: { color: MINT, width: 1.5, dashType: "dash" } });
s.addText("THE CLINIC'S LAPTOP  —  THE TRUST BOUNDARY", { x: 3.25, y: 2.05, w: 7.0, h: 0.35,
  fontFace: BODYF, fontSize: 11.5, bold: true, color: MINT, charSpacing: 2 });
// inputs
s.addText("Visit audio\n\nDocuments\n\nMessy files", { x: 0.55, y: 2.6, w: 1.75, h: 2.4,
  align: "right", fontFace: BODYF, fontSize: 14, color: ICE, lineSpacing: 22 });
s.addText("→", { x: 2.35, y: 3.35, w: 0.55, h: 0.6, align: "center", fontFace: BODYF,
  fontSize: 24, bold: true, color: DIM });
// four stages
const stages = [
  ["SCAN", "deterministic rules\nregex · Luhn · collectors", false],
  ["GEMMA 4", "one local model\nreads · reasons · classifies", true],
  ["APPROVE", "a human clicks\n— always", false],
  ["VERIFY", "attacks its own output\nre-OCR · journal · undo", false],
];
stages.forEach((st, i) => {
  const x = 3.25 + i * 1.78;
  s.addShape("roundRect", { x, y: 2.75, w: 1.6, h: 1.85, rectRadius: 0.08,
    fill: { color: st[2] ? "0E2A22" : NAVY }, line: { color: st[2] ? MINT : "31465C", width: st[2] ? 2 : 1 } });
  s.addText(st[0], { x, y: 2.95, w: 1.6, h: 0.4, align: "center", fontFace: BODYF,
    fontSize: 13.5, bold: true, color: st[2] ? MINT : "FFFFFF", charSpacing: 1 });
  s.addText(st[1], { x: x + 0.06, y: 3.42, w: 1.48, h: 1.1, align: "center", fontFace: BODYF,
    fontSize: 10, color: st[2] ? "CFEFE4" : DIM });
  if (i < 3) s.addText("→", { x: x + 1.58, y: 3.35, w: 0.22, h: 0.6, align: "center",
    fontFace: BODYF, fontSize: 16, bold: true, color: DIM });
});
// outputs
s.addText("→", { x: 10.55, y: 3.35, w: 0.55, h: 0.6, align: "center", fontFace: BODYF,
  fontSize: 24, bold: true, color: DIM });
s.addText("Signed note\n\nRedacted PDF\n\nSafety Score\n\nClean files", { x: 11.15, y: 2.35, w: 1.9, h: 3.0,
  fontFace: BODYF, fontSize: 14, color: ICE, lineSpacing: 22 });
// egress caption
s.addShape("ellipse", { x: 4.05, y: 6.22, w: 0.16, h: 0.16, fill: { color: MINT } });
s.addText("Network egress: 0  —  pull the Wi-Fi and everything still works.", {
  x: 4.35, y: 6.05, w: 6.5, h: 0.5, fontFace: BODYF, fontSize: 16, color: ICE });
mark(s);

// ---------------------------------------------------------------- 8 PROOF
s = base();
s.addText("It destroys data — and proves it.", { x: 0.7, y: 1.0, w: 11.93, h: 1.0,
  align: "center", fontFace: HEAD, fontSize: 46, bold: true, color: "FFFFFF" });
s.addImage({ path: "img_redact_crop.png", x: 0.75, y: 2.1, w: 5.95, h: 3.6 });
const proofs = [["0", "recoverable characters after redaction"], ["18", "HIPAA Safe Harbor identifiers in the coverage panel"], ["4", "self-run verification checks on every export"]];
proofs.forEach((pr, i) => {
  const y = 2.05 + i * 1.25;
  s.addText(pr[0], { x: 7.1, y, w: 1.5, h: 1.1, align: "center", fontFace: HEAD,
    fontSize: 54, bold: true, color: MINT, valign: "middle" });
  s.addText(pr[1], { x: 8.75, y: y + 0.05, w: 3.85, h: 1.0, fontFace: BODYF,
    fontSize: 16, color: ICE, valign: "middle" });
});
s.addText("Select-all  ·  text-search  ·  re-OCR  ·  metadata audit — the tool attacks its own output before you trust it", {
  x: 0.7, y: 6.0, w: 11.93, h: 0.55, align: "center", fontFace: BODYF, fontSize: 15, color: DIM });
mark(s);

// ---------------------------------------------------------------- 9 FREE
s = base();
s.addText("Free. Forever. For everyone.", { x: 0.7, y: 2.1, w: 11.93, h: 1.4, align: "center",
  fontFace: HEAD, fontSize: 56, bold: true, color: "FFFFFF", valign: "middle" });
s.addText("Apache-2.0  ·  runs on the laptop the clinic already owns", {
  x: 1.6, y: 3.8, w: 10.13, h: 0.6, align: "center", fontFace: BODYF, fontSize: 20, color: ICE });
s.addText("Cloud AI scribes run $299–$1,512 per doctor, per month. Redaction suites, $279+/user. IT support, $150/user.\nObscura replaces that stack at $0 — for the clinics the $300M cloud-scribe market doesn’t serve.", {
  x: 1.2, y: 4.7, w: 10.93, h: 1.0, align: "center", fontFace: BODYF, fontSize: 16, color: DIM });
mark(s);

// ---------------------------------------------------------------- 10 CLOSE
s = base();
s.addImage({ path: "img_human_crop.png", x: 0, y: 0, w: 6.6, h: H });
s.addShape("rect", { x: 6.6, y: 0, w: 0.07, h: H, fill: { color: MINT } });
s.addText("This is what the\ntime is for.", { x: 7.1, y: 1.35, w: 5.6, h: 1.7,
  fontFace: HEAD, fontSize: 40, bold: true, color: "FFFFFF" });
s.addText("As fast as AI.\nAs private as a locked filing cabinet.", {
  x: 7.1, y: 3.25, w: 5.6, h: 1.05, fontFace: HEAD, fontSize: 22, italic: true, color: ICE });
s.addText("Open models made this inevitable. We just built it first.", {
  x: 7.1, y: 4.45, w: 5.6, h: 0.45, fontFace: BODYF, fontSize: 15, bold: true, color: "FFFFFF" });
s.addText("OBSCURA", { x: 7.1, y: 5.05, w: 5.6, h: 0.6, fontFace: HEAD,
  fontSize: 28, bold: true, color: MINT, charSpacing: 7 });
s.addText("github.com/meetkpatel/Obscura\nbuilt on Gemma 4  ·  Apache-2.0", {
  x: 7.1, y: 5.75, w: 5.6, h: 0.8, fontFace: BODYF, fontSize: 14, color: DIM });

p.writeFile({ fileName: process.argv[2] || "20260718_Obscura_Pitch_90s.pptx" })
  .then(f => console.log("WROTE " + f));
