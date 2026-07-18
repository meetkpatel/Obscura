# Obscura — Kaggle Writeup (GenAI for Good track) — paste-ready, ~1,240 words

> Track: **GenAI for Good** (the only track in this competition). Attach under Project Links: public repo `https://github.com/meetkpatel/Obscura` + demo (in-person live demo on the laptop; attach the fallback screen recording if you have it). Submit, then edit/re-submit freely until the deadline.

---

**Title:** Obscura — Four Tools. One Laptop. Zero Cloud.

**Subtitle:** A private AI suite for the clinics America runs on — built entirely on Gemma 4, it transcribes nothing to the cloud, redacts patient records provably, hardens the front-desk laptop, and organizes the files — all on hardware the clinic already owns.

**Track:** GenAI for Good

---

## The problem

Small and safety-net medical practices are drowning in unpaid computer work. Clinicians spend nearly two hours on desk and EHR work for every hour of direct patient care (AMA-funded time-motion study, Annals of Internal Medicine). Healthcare is the costliest breach industry on earth — roughly $10M per incident, fourteen years running (IBM). And 31 million patients depend on community health centers that run on thin margins with no IT department, no compliance officer, and no enterprise software budget.

The AI industry's answer is cloud tools priced for big health systems: ambient scribes at $299–$1,512 per clinician per month (Suki, Nuance DAX Copilot), redaction suites at $279+ per user per month, plus $100–250/user/month for HIPAA-ready managed IT. Worse, for a small clinic the cloud is not just expensive — it is the risk itself. Consumer AI tools won't sign a HIPAA Business Associate Agreement. Pasting a patient note into a chatbot is not a shortcut; it is a disclosure. **The upload is the breach.** The clinics that need AI most are the ones that can't use it.

Gemma 4 dissolves that paradox: open weights (Apache-2.0), small enough for a stock laptop, capable enough to do the reasoning. For the first time, the fast tool and the compliant tool are the same tool.

## What we built

Obscura is one on-device engine pointed at a clinic's privacy surfaces — each tool a plugin on the same loop: **Scan (deterministic) → Understand (Gemma 4) → Propose → Human approves → Apply → Verify → Undo.**

- **REDACT** — share the record, not the patient. Detection is mapped to all 18 HIPAA Safe Harbor identifier categories (45 CFR 164.514(b)(2)(i)) — names, MRNs, member IDs, dates, geography — with a live per-document coverage panel. Output destroys data rather than covering it: pages rasterized, boxes burned into pixels, metadata stripped, exported as an image-only PDF.
- **SECURE** — a $0 IT department. A read-only scan for plaintext credentials, weak OS configuration, and risky open ports, grounded in CIS Level 1 hardening checks, rolled into a plain-English Safety Score. Gemma explains; it never executes.
- **ORGANIZE** — files that name themselves. Gemma reads each file's first page (or the image itself, via vision) and returns doc-type, entity, date; code enforces the naming template; a crash-safe journal makes every move fully undoable.
- **TRANSCRIBE** (roadmap, in design) — the fourth prong: on-device visit-to-note, eliminating the BAA entirely because there is no third party.

The prongs feed each other: SECURE finds a plaintext key → one click "Send to Redactor" → REDACT destroys it → ORGANIZE files the result. An always-visible egress panel lists the process's live network connections — external count: 0. Pull the Wi-Fi; everything still works.

## How Gemma 4 is core to the solution

Gemma 4 is the reasoner doing the work rules cannot — one local model behind every tool.

1. **The detection insight (REDACT).** Structured PII (SSN, Luhn-validated cards, MRN, phone, email) comes from deterministic rules — perfect precision, instant. But names, addresses, and re-identifying context require reading comprehension. Our key move: we do **not** trust the model's pixel coordinates for text. We ask Gemma 4 for the sensitive *strings*, then locate each with Tesseract OCR word boxes. **The model finds the meaning; OCR fixes the pixels.** Gemma's native vision (`box_2d`) is reserved for genuinely visual items — signatures, faces — where a loose box is safe.
2. **Local reasoning as an explainer (SECURE).** Deterministic collectors produce raw findings; Gemma turns each into one sentence of what-this-means-and-why-it-matters for a non-technical front desk, and prioritizes them. Remediations come from a hardcoded registry — the model never runs anything.
3. **Multimodal classification (ORGANIZE).** Gemma reads a cheap signature per file — first PDF page, first sheet rows, or the picture itself — and returns structured JSON (doc-type, category, entity, date, descriptor). Code owns the final name.

All calls run through a single Ollama gateway with structured-JSON output, a json-repair + validation retry loop, and a serialized queue so one 8 GB GPU is never thrashed.

## Challenges we overcame in the sprint

- **Model reality vs. the datasheet.** On the demo laptop (RTX 4070, 8 GB VRAM) the 12B-QAT model fits but generates ~14 tok/s and triggered client-side fetch timeouts. We made E4B-QAT (~38 tok/s) the interactive default and shipped a **hardware-probe endpoint** that auto-recommends the right Gemma 4 variant per machine — a decision only measurement could make.
- **The smaller model's boxes drift.** E4B returned one imprecise mega-box over dense text. That failure drove the OCR-grounding architecture — it turned a weakness into the design.
- **Line-spanning and repetition.** First OCR grounding produced cross-line boxes (fixed with a vertical-overlap constraint); Gemma occasionally looped on repetitive documents (fixed with generation guards).
- **Proving the redaction.** We built a 4-part verification battery that attacks our own output on every export: select-all test (zero selectable characters), text-search (no redacted string findable), re-OCR (nothing readable survives in pixels), metadata audit (document dictionary empty) — with a downloadable per-document report.

## Why our technical choices were right

Pure-LLM PII detection averages ~0.54 F1 in open benchmarks — not good enough alone when a single missed MRN is a breach. Hybrid detection (deterministic rules + Gemma reasoning + human review, biased to over-redact) is the only configuration that reaches defensible recall. Destroy-don't-cover is a structural guarantee, not a promise — the DOJ Epstein files and Meta v. FTC leaks were both "redacted" black boxes over live text that reporters simply copied out; our output is physically incapable of that mistake, and the verification battery proves it per document. Human-in-the-loop and full reversibility are architecture, not policy: nothing is redacted, moved, or changed without a click, and ORGANIZE's journaled moves undo completely.

## Impact — GenAI for Good

Everything here is Apache-2.0 and runs on hardware a clinic already owns. A two-provider practice conservatively replaces $15,000+/year of cloud subscriptions — in a market ($1.2–2.8B today, ~$15B by 2034–35) that is entirely cloud and entirely priced for large health systems. The same four prongs generalize to legal aid, social work, and schools — anywhere sensitive records meet thin budgets. De-identification coverage is labeled technical QA, not legal advice: a human reviewer signs off, exactly as Safe Harbor requires.

## Status

Three of four prongs work end-to-end on synthetic data: REDACT passes the full verification battery (16/18 Safe Harbor categories flagged on a synthetic patient record; zero recoverable characters); SECURE finds planted credentials and scores the machine; ORGANIZE classifies, applies, and fully undoes. All demo data is synthetic — no real PHI, ever. Built in a one-day sprint; the engineering is real and documented in the repo.

---

**Attachments (Project Links):**
- Public code repository: `https://github.com/meetkpatel/Obscura`
- Live demo: in-person on the demo laptop, Wi-Fi off (http://localhost:8000) + fallback screen recording.
