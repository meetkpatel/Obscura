# Obscura — Kaggle Writeup (FINAL — paste into Kaggle "New Writeup")

> Track: **GenAI for Good** (the only track listed on the live competition page). Attach under Project Links: the public GitHub repo + live demo / recording. Body word count: ~1,380 (limit 1,500).

---

**Title:** Obscura — Redaction That Never Leaves the Room

**Subtitle:** An on-device privacy engine built on Gemma 4: find every sensitive detail in a document, on your own machine, and destroy it — provably. Healthcare and civic records finally get a fast tool that is also the legal tool.

**Track:** GenAI for Good

---

## The problem

Redacting a sensitive document is slow, manual, and catastrophically error-prone — and the one tool that could make it fast, a cloud AI, is the exact tool the largest redactors are legally forbidden to use. Federal agencies received **1.5 million FOIA requests in FY2024** (+25%), carry a **267,056-request backlog** (+33% in one year), and spend **$723 million** processing them largely by hand (DOJ OIP FY2024 report). Hospitals face the same wall under HIPAA. And when redaction is rushed it fails the same way every time — the DOJ Epstein files and the Meta v. FTC filing were both "redacted" with black boxes over live text that reporters simply copied out.

The obvious fix — point an AI at the document — is the one thing you cannot do here. For protected health information, government CUI, or attorney-client material, **uploading the document to a cloud model is itself the disclosure**. The classification step is precisely the step that cannot leave the building.

Gemma 4 dissolves that paradox. It is good enough, small enough, and open enough (Apache 2.0) to run frontier reasoning **entirely on a laptop**. For the first time the fast tool and the legal tool are the same tool.

## What we built

Obscura is one on-device engine pointed at the three surfaces of a laptop's privacy, each a plugin on the same loop — **Scan (deterministic) → Understand (Gemma 4) → Propose → Human approves → Apply → Verify → Undo:**

- **REDACT** — the document is the secret. Find every sensitive item (including the full HIPAA Safe Harbor identifier set), destroy it — flattened raster, no recoverable text layer, metadata stripped — and self-verify.
- **SECURE** — the machine is the vault. A read-only scan for plaintext secrets, weak configuration, and risky ports — plus a performance pass (a 10-point cleanup analysis that finds reclaimable disk space and scores the machine 0–100), all in a plain-English report with a Safety Score.
- **ORGANIZE** — the filesystem is the archive. Gemma reads each file, proposes a clean structure and names, flags sensitive files for redaction and audio files for transcription, and applies it all with a crash-safe journal and one-click Undo.

A fourth surface — **TRANSCRIBE**, a Gemma clinical scribe that turns a visit recording into a transcript-grounded SOAP draft (MedGemma 4B GGUF as the local-model path; drafts labeled unverified, clinician review required) — is an MVP in review as PR #9.

The phases feed each other: SECURE finds a plaintext credential on disk → one click **"Send to Redactor"** → REDACT destroys it → ORGANIZE files the result. Everything runs behind an always-visible on-device badge and a live **egress panel** listing the process's own network connections — external count: 0. The UI ships zero external assets and runs with Wi-Fi off.

## Architecture

```
app/backend/
  contracts.py       # frozen Pydantic vocabulary shared by all phases
  gemma.py           # single Ollama gateway: queue + structured JSON + retries
  hardware.py        # VRAM-aware model chooser (E4B default, 12B quality mode)
  presidio_detect.py # deterministic Scan layer: Presidio + spaCy NER, on-device
  phase1_redact.py   # ingest → hybrid detect → OCR-grounded boxes → burn/flatten/scrub → verify
  phase2_secure.py   # deterministic collectors → Gemma explainer → Safety Score
  phase3_organize.py # inventory → Gemma classify → propose → crash-safe journal → undo
  main.py            # FastAPI: one server, three phases, egress-proof endpoint
app/frontend/index.html  # single page, zero external assets
app/demo-data/           # SYNTHETIC sample doc + planted secret + messy folder
```

One spine, three plugins: every phase emits the same contract objects, calls Gemma through the same serialized gateway (an 8 GB GPU is never thrashed), and ends in a human-approval gate before anything is changed.

## How we specifically used Gemma 4

Gemma 4 is not a garnish on a rules engine; it is the reasoner doing the work regex cannot.

**1. Reading comprehension for detection (REDACT).** Structured PII (SSN, credit card via Luhn, MRN, email, phone, dates) is caught deterministically by Presidio — perfect precision, instant. But names, home addresses, and *re-identifying context* require reading. Our key move: we do **not** trust the model's pixel coordinates for text. We ask **Gemma 4 for the sensitive strings** ("copy the exact substrings a records officer must redact that a regex would miss"), then locate each returned string with Tesseract OCR word boxes, with fuzzy matching to survive OCR noise. **The model finds the meaning; OCR fixes the pixels.** Gemma's **native multimodal vision** (`box_2d` on a 1000×1000 grid) is reserved for genuinely visual items — signatures, faces — where a slightly loose box is safe.

**2. Local reasoning as an explainer (SECURE).** Deterministic collectors produce raw findings; Gemma 4 turns each into a one-sentence, plain-English *what-this-means-and-why-it-matters*, prioritizes them, and writes a short prioritized cleanup plan for the performance findings. The model never scans and never executes — remediations come from a hardcoded registry.

**3. Multimodal classification (ORGANIZE).** For each file Gemma 4 reads a cheap signature (first page of a PDF, first rows of a sheet, or — for scans and images — the picture itself via vision) and returns structured JSON: doc-type, category, entity, date, suggested descriptor. Code enforces the naming template; Gemma supplies only the understanding.

All calls go through one Ollama gateway with structured JSON output and a json-repair + validation retry loop. Multimodal input and local reasoning are both load-bearing.

## Why our technical choices were right

- **Hybrid over pure-LLM.** Open-source LLM PII detection averages ~0.54 F1 alone. Deterministic Presidio for structured data + Gemma for the reasoning-dependent rest + human review is the only configuration that reaches defensible recall.
- **OCR-grounded model output.** Asking the model for *strings* and grounding them in OCR gives both the model's comprehension and pixel-exact boxes — and it degrades gracefully on the smaller model.
- **Destroy, don't cover.** Output is re-encoded through raw pixels to a flattened image-only PDF with metadata cleared. **Verify** re-opens the result, asserts no selectable text layer exists, and re-OCRs the rendered pages to confirm none of the redacted strings survive — the tool checks its own work, then a HIPAA Safe Harbor coverage self-check runs on top.
- **Human-in-the-loop and reversible by architecture.** Nothing is redacted, moved, or changed without a click; ORGANIZE writes an intent journal (fsync before the move, commit flag after, startup reconciliation) and Undo replays it in reverse.

## Challenges we overcame in the sprint

- **Model reality vs. the spec.** Benchmarked on the actual demo laptop (RTX 4070, 8 GB): the 12B-QAT model fits in VRAM but generates ~14 tok/s, so we made **E4B-QAT (~38 tok/s) the interactive default** with 12B as a "quality mode" toggle — a decision only measurement could make. A hardware-aware chooser now picks per machine.
- **The smaller model's boxes drift.** E4B returned one imprecise mega-box over dense text. That failure *drove* the OCR-grounding architecture — it turned a weakness into the design.
- **OCR is noisy.** Exact substring grounding missed hits when Tesseract misread characters; we added normalized fuzzy matching with a similarity floor, and any Gemma finding that still can't be grounded is *reported to the human* instead of silently dropped — fail loud, never silent.
- **Over-redaction.** Early runs boxed field labels and non-PII terms; a denylist plus value-only boxing (redact "John Smith", keep "Patient Name:") fixed precision without losing recall.

## Proof of work

One-day sprint, all in the open: **12 pull requests (8 merged), ~26 commits to main, ~4,800 lines** of Python + HTML across 13 modules — every feature landed by PR with a written description (Presidio scan layer #5, fuzzy OCR grounding #6, precision fixes #8, HIPAA Safe Harbor + verification battery #2–3). The repo README documents setup, install, and run end-to-end.

## Status

All three phases work end-to-end on synthetic data: REDACT catches names, addresses, and every structured identifier and passes self-verification (zero selectable characters, zero residual after re-OCR); SECURE finds planted credentials and scores the machine; ORGANIZE classifies, applies, and fully undoes a folder move. A prototype — but the engineering (hybrid detector, verification gate, crash-safe journal) is real and documented in the repo.

---

**Attachments (Project Links):**
- Public code repository: `https://github.com/meetkpatel/Obscura`
- Live demo: hosted locally (Wi-Fi off) for the 3-min live demo + screen recording fallback.
