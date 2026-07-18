# Obscura — Kaggle Writeup (draft, ≤1,500 words)

> Paste into the Kaggle "New Writeup". **Track: Edge On-Device** (recommended — see note at bottom for the GenAI-for-Good reframe). Attach: GitHub repo (public) + live demo / recording. Word count of the body below: ~1,180.

---

**Title:** Obscura — Redaction That Never Leaves the Room

**Subtitle:** An on-device privacy engine built entirely on Gemma 4: find every sensitive detail in a document, on your own machine, and destroy it — provably.

**Track:** Edge On-Device

---

## The problem

Redacting a sensitive document is slow, manual, and catastrophically error-prone — and the one tool that could make it fast, a cloud AI, is the exact tool the largest redactors are legally forbidden to use. Federal agencies received **1.5 million FOIA requests in FY2024** (+25%), carry a **267,056-request backlog** (+33% in one year), and spend **$723 million** processing them, largely by hand (DOJ OIP FY2024 report). When redaction is rushed it fails the same way every time — the DOJ Epstein files and the Meta v. FTC filing were both "redacted" with black boxes over live text that reporters simply copied out.

The obvious fix — point an AI at the document — is the one thing you cannot do here. For government CUI, attorney-client privilege, or ITAR-controlled data, **uploading the document to a cloud model is itself the disclosure** (for export-controlled data, a potential felony). The classification step is precisely the step that cannot leave the building.

Gemma 4 dissolves that paradox. It is good enough, small enough, and open enough (Apache 2.0) to run frontier reasoning **entirely on a laptop**. For the first time the fast tool and the legal tool are the same tool.

## What we built

Obscura is one on-device engine pointed at the three surfaces of a laptop's privacy, each a plugin on the same loop — **Scan (deterministic) → Understand (Gemma 4) → Propose → Human approves → Apply → Verify → Undo:**

- **REDACT** — the document is the secret. Find every sensitive item, destroy it (flattened raster, no recoverable text layer, metadata stripped), and self-verify.
- **SECURE** — the machine is the vault. A read-only scan for plaintext secrets, weak configuration, and risky ports, with a plain-English report and a Safety Score.
- **ORGANIZE** — the filesystem is the archive. Gemma reads each file, proposes a clean structure and names, and applies it with a crash-safe journal and one-click Undo.

The phases feed each other: SECURE finds a plaintext API key on disk → one click **"Send to Redactor"** → REDACT destroys it → ORGANIZE files the result. Everything runs behind an always-visible on-device badge and a live **egress panel** that lists the process's network connections — external count: 0.

## How Gemma 4 is core to the solution

Gemma 4 is not a garnish on a rules engine; it is the reasoner that does the work regex cannot.

**1. The detection insight (REDACT).** Structured PII (SSN, credit card via Luhn, email, phone, dates) is caught by deterministic rules — perfect precision, instant. But names, home addresses, and *re-identifying context* require reading comprehension. Our key move: we do **not** trust the model's pixel coordinates for text. We ask **Gemma 4 for the sensitive strings** ("copy the exact substrings a records officer must redact that a regex would miss"), then locate each returned string with Tesseract OCR word boxes. **The model finds the meaning; OCR fixes the pixels.** This eliminates the "characters peeking out from under the box" failure mode that coordinate-only tools suffer, while still using Gemma for the hard part — understanding what is sensitive. Gemma's **native multimodal vision** (`box_2d` on a 1000×1000 grid) is reserved for genuinely visual items like signatures and faces, where a slightly loose box is safe.

**2. Local reasoning as an explainer (SECURE).** Deterministic collectors produce raw findings; Gemma 4 turns each into a one-sentence, plain-English *what-this-means-and-why-it-matters* for a non-technical user, and prioritizes them. The model never scans and never executes — remediations come from a hardcoded registry.

**3. Multimodal classification (ORGANIZE).** For each file Gemma 4 reads a cheap signature (first page of a PDF, first rows of a sheet, or — for scans and images — the picture itself via vision) and returns structured JSON: doc-type, category, topic, entity, date, and a suggested descriptor. Code enforces the final naming template; Gemma supplies only the understanding.

Across all three phases Gemma 4 runs through a single Ollama gateway with structured JSON output, a json-repair + validation retry loop, and a serialized queue so one 8 GB GPU is never thrashed. Multimodal input (text + image) and reasoning are both load-bearing.

## Why our technical choices were right

- **Hybrid over pure-LLM.** Open-source LLM PII detection averages ~0.54 F1 alone. Deterministic rules for structured data + Gemma for the reasoning-dependent rest + human review is the only configuration that gets to a defensible recall.
- **OCR-grounded model output.** Asking the model for *strings* and grounding them in OCR gives us both the model's comprehension and pixel-exact boxes — the best of both, and it degraded gracefully when we tested the smaller model.
- **Destroy, don't cover.** Output is re-encoded through raw pixels to a flattened image-only PDF with its metadata dictionary cleared. **Verify** re-opens the result, asserts there is no selectable text layer, and OCRs the rendered pages to confirm none of the redacted strings survive — the tool checks its own work.
- **Human-in-the-loop and reversible by architecture.** Nothing is redacted, moved, or changed without a click; ORGANIZE writes an intent journal (fsync before the move, commit flag after, startup reconciliation) and Undo replays it in reverse.
- **Truly local.** The UI ships zero external assets, so it runs with Wi-Fi off. No API keys, no network path in the code.

## Challenges we overcame in the sprint

- **Model reality vs. the spec.** We benchmarked on the actual demo laptop (RTX 4070, 8 GB): the 12B-QAT model fits in VRAM but generates ~14 tok/s, so we made **E4B-QAT (~38 tok/s) the interactive default** and 12B a "quality mode" toggle — a decision only measurement, not the datasheet, could make.
- **The smaller model's boxes drift.** E4B returned one imprecise mega-box over dense text. That failure is exactly what drove the OCR-grounding architecture above; it turned a weakness into the design.
- **De-duplication and line-spanning.** Our first OCR grounding produced cross-line boxes; constraining spans to a single text line (vertical-overlap test) fixed it.

## Status

All three phases work end-to-end and were tested on synthetic data: REDACT catches names, addresses, and every structured identifier and passes self-verification (zero selectable characters, zero residual after re-OCR); SECURE finds planted credentials and scores the machine; ORGANIZE classifies, applies, and fully undoes a folder move. This is a prototype built in a one-day sprint — the engineering (the hybrid detector, the verification gate, the crash-safe journal) is real and documented in the repo.

---

**Attachments (required):**
- Public code repository: `https://github.com/meetkpatel/Obscura`
- Live demo: hosted at `http://localhost:8000` on the demo machine (Wi-Fi off) + a 40-second fallback screen recording.

---

### Track note (decision for the team)
Drafted for **Edge On-Device** — the purest fit for "nothing leaves the room." To switch to **GenAI for Good** ($2,000, civic track): change the Track line, retitle the subtitle around *civic transparency / FOIA backlog*, and lead the problem section with the public-records-access angle (already the opening). Same build, ~2-minute reframe. Avoid the **Autonomous Agent** track — Obscura is deliberately human-in-the-loop, which contradicts that track's thesis.
