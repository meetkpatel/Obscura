# Obscura — Kaggle Writeup (final, paste-ready)

> **Track:** GenAI for Good. Body word count: ~1,320 (limit 1,500). Attach the two required assets under **Project Links** (see *Attachments* at the bottom). Submit, then edit freely until the deadline.

---

**Title:** Obscura — Four Tools. One Laptop. Zero Cloud.

**Subtitle:** A private AI suite for the clinics America runs on — built entirely on Gemma 4, it redacts patient records *provably*, hardens the front-desk laptop, and organizes the files, all on hardware the clinic already owns. Nothing ever leaves the machine.

**Track:** GenAI for Good

---

## The problem

Small and safety-net medical practices are drowning in unpaid computer work. Clinicians spend nearly two hours on desk and EHR work for every hour of direct patient care (AMA-funded time-motion study, *Annals of Internal Medicine*). Healthcare has been the costliest breach industry on earth — roughly $10M per incident — fourteen years running (IBM). And 31 million patients depend on community health centers that run on thin margins with no IT department, no compliance officer, and no enterprise software budget.

The AI industry's answer is cloud tooling priced for large health systems: ambient scribes at $299–$1,512 per clinician per month, redaction suites at $279+ per user per month, plus $100–250/user/month for HIPAA-ready managed IT. Worse, for a small clinic the cloud is not just expensive — **it is the risk itself.** Consumer AI tools won't sign a HIPAA Business Associate Agreement, and pasting a patient note into a chatbot to ask *"what's sensitive here?"* is not a shortcut — it *is* the disclosure. **The upload is the breach.** The clinics that need AI most are the ones that legally can't use it.

Gemma 4 dissolves that paradox: open weights (Apache-2.0), small enough for a stock laptop, capable enough to do the reasoning. For the first time, the fast tool and the compliant tool are the same tool.

## What we built

Obscura is **one on-device engine** pointed at a clinic's privacy surfaces — each tool a plugin on the same loop:

> **Scan (deterministic) → Understand (Gemma 4) → Propose → Human approves → Apply → Verify → Undo**

- **REDACT** — *share the record, not the patient.* Detection maps to the 18 HIPAA Safe Harbor identifier categories (45 CFR 164.514(b)(2)(i)) — names, MRNs, member IDs, dates, geography — with a per-document coverage panel. Output **destroys** data rather than covering it: pages rasterized, boxes burned into pixels, metadata dictionary cleared, exported as an image-only PDF.
- **SECURE** — *a $0 IT department.* A read-only scan for plaintext credentials, weak OS configuration, and risky open ports, rolled into a plain-English Safety Score. Gemma explains; it never executes.
- **ORGANIZE** — *files that name themselves.* Gemma reads each file's first page (or the image itself, via vision) and returns doc-type, entity, and date; code enforces the naming template; a crash-safe journal makes every move fully undoable.
- **TRANSCRIBE** *(roadmap, in design)* — on-device visit-to-note, eliminating the BAA entirely because there is no third party.

The prongs feed each other: SECURE finds a plaintext key → one click **"Send to Redactor"** → REDACT destroys it → ORGANIZE files the result. An always-visible **egress panel** enumerates this process tree's live network connections — external count: **0**. Pull the Wi-Fi; everything still works.

## How Gemma 4 is core to the solution

Gemma 4 is the reasoner doing the work rules cannot — one local model behind every tool, reached through a single Ollama gateway (`gemma.py`).

**1. The detection insight (REDACT).** Structured PII (SSN, Luhn-validated cards, MRN, phone, email) comes from deterministic rules — perfect precision, instant. But names, addresses, and *re-identifying context* require reading comprehension. Our key move: **we do not trust the model's pixel coordinates for text.** We ask Gemma 4 for the sensitive *strings*, then locate each with Tesseract OCR word boxes. **The model finds the meaning; OCR fixes the pixels.** Only the value is boxed — the label `Phone:` stays readable. Gemma's native vision (`box_2d` on a 1000×1000 grid) is reserved for genuinely *visual* items — signatures, faces — where a slightly loose box is safe. This kills the "characters peeking out from under the box" failure mode that coordinate-only tools suffer.

**2. Local reasoning as an explainer (SECURE).** Deterministic collectors produce raw findings; Gemma turns each into one sentence of *what-this-means-and-why-it-matters* for a non-technical front desk, and prioritizes them. Remediations come from a hardcoded registry — the model never runs anything.

**3. Multimodal classification (ORGANIZE).** Gemma reads a cheap signature per file — first PDF page, first sheet rows, or the picture itself — and returns structured JSON (doc-type, category, entity, date, descriptor). Code owns the final filename.

All calls route through one gateway with **structured `format: json` decoding, a json-repair + validation retry loop, a serialized lock** so one 8 GB GPU is never thrashed, and a `repeat_penalty` + output sanitizer that defends against the small model's degenerate-repetition failure. No network path exists anywhere in the model layer — every call points at `localhost:11434`.

## Technical verification — the proof of work

The claims above are not aspirational; they are enforced in code:

- **Redaction is destroyed, not hidden.** On every export, `verify_pdf()` re-opens Obscura's *own* output and runs a verification battery: a select-all/copy test (zero selectable characters), a text search (no redacted string findable), and a **re-OCR of the rendered pixels** (nothing sensitive readable in the raster), plus a metadata audit. If any redacted string survives, the export is flagged.
- **Egress is measured, not asserted.** `/api/egress` iterates *this* process and its children via `psutil`, reads each one's remote connections, and returns the external count with a verdict — a live number a judge can watch stay at 0.
- **Coverage is honest.** `/api/redact/hipaa` reports which of the 18 Safe Harbor categories the detector actually targets, explicitly labeled a technical self-check, **not** a legal compliance opinion.
- **Moves are reversible by architecture.** ORGANIZE writes an intent journal (fsync before the move, commit flag after, startup reconciliation) and Undo replays it in reverse.

## Challenges we overcame in the one-day sprint

- **Model reality vs. the datasheet.** On the demo laptop (RTX 4070, 8 GB VRAM) the 12B-QAT model *fits* but generates ~14 tok/s and triggered client-side fetch timeouts. We made **E4B-QAT (~38 tok/s) the interactive default** and shipped a **hardware-probe endpoint** (`hardware.py`) that detects VRAM/RAM and auto-recommends the right Gemma 4 variant per machine — a decision only measurement, not the spec sheet, could make.
- **The smaller model's boxes drift.** E4B returned one imprecise mega-box over dense text. That failure *drove* the OCR-grounding architecture above — it turned a weakness into the design.
- **Line-spanning and OCR misreads.** First-pass grounding produced cross-line boxes (fixed with a single-line vertical-overlap constraint), and OCR misreads like "Srnith" for "Smith" evaded verbatim matching — so we added a fuzzy fallback (`difflib`) that still places the box and any string it *can't* ground is surfaced as an "ungrounded hit," never silently dropped.

## Why our technical choices were right

Pure-LLM PII detection averages ~0.54 F1 in open benchmarks — not good enough alone when a single missed MRN is a breach. **Hybrid detection** (deterministic rules for structured data + Gemma reasoning for the rest + human review, biased to over-redact) is the only configuration that reaches defensible recall. **Destroy-don't-cover** is a structural guarantee, not a promise — the DOJ Epstein files and the Meta v. FTC filing were both "redacted" with black boxes over live text that reporters simply copied out; Obscura's flattened image-only output is physically incapable of that mistake, and the verification battery proves it per document. **Human-in-the-loop and full reversibility** are architecture, not policy: nothing is redacted, moved, or changed without a click.

## Impact

Everything here is Apache-2.0 and runs on hardware a clinic already owns. A two-provider practice conservatively replaces $15,000+/year of cloud subscriptions — in a market that is almost entirely cloud and priced for large health systems. The same three-plus-one prongs generalize to legal aid, social work, and schools — anywhere sensitive records meet thin budgets.

## Status

Three of four prongs work end-to-end on **synthetic** data: REDACT passes the full verification battery (zero recoverable characters, zero residual after re-OCR); SECURE finds planted credentials and scores the machine; ORGANIZE classifies, applies, and fully undoes a folder move. All demo data is synthetic — no real PHI, ever. Built in a one-day sprint; the engineering — the hybrid detector, the verification gate, the crash-safe journal — is real and documented in the repo.

---

## Attachments (required — add under *Project Links*)

- **Public code repository:** `https://github.com/meetkpatel/Obscura`
- **Live demo:** in-person on the demo laptop with Wi-Fi off (`http://localhost:8000`), plus a fallback screen recording. The demo is fully local — no login, no paywall, no network.
