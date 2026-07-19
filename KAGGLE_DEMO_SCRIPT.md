# Obscura — 3-Minute Live Demo + 2-Minute QA (Kaggle submission asset)

> Companion to **`KAGGLE_SUBMISSION.md`** (GenAI for Good). Same framing, same honesty rules.
> Rehearse out loud 3× and **time it** — the demo is the middle; the fear opens it; "why us / why now" closes it.
> **Delivery:** slow down on the numbers. Let the black boxes appear in silence. The copy-paste test is the mic-drop — *pause* after it. Do **not** sell "offline" as the headline; sell "for this buyer, cloud is *forbidden*."

## Pre-flight (before you hit record)
- [ ] `ollama serve` running; `gemma4:e4b-it-qat` pulled. Header badge should **not** say `MODEL MISSING`.
- [ ] `python app/make_demo_data.py` has run once (synthetic patient record + planted secret + messy folder exist).
- [ ] Server up: `cd app/backend && python -m uvicorn main:app --port 8000`. Open `http://localhost:8000`.
- [ ] **Wi-Fi OFF.** Log in with any credentials (mock auth — no real login, no paywall).
- [ ] Have the `/api/egress` panel and the Safe Harbor coverage panel one click away.

---

## THE DEMO — 3:00

### [0:00–0:30] The trap — why AI hasn't fixed this
> "Small clinics do two hours of paperwork for every hour with a patient, and healthcare is the costliest breach industry on earth — about **ten million dollars** an incident. The obvious fix is AI. But for a clinic, the obvious fix is illegal: pasting a patient note into a cloud chatbot to ask *'what's sensitive here?'* — **that upload is the disclosure.** No consumer AI will sign a HIPAA agreement. So the clinics that need AI most are the ones that legally can't use it. Until this."

### [0:30–0:50] One engine, on this laptop — and prove it
> "This is **Obscura**. One Gemma 4 model, running **entirely on this laptop**, behind four tools. First — the receipt."
- **Click the on-device badge → egress panel.** Point, wordless, at **external connections: 0.**
> "Wi-Fi's off. Nothing here can leave the machine — that's not a setting, it's the architecture."

### [0:50–1:50] REDACT — the core, and the mic-drop
> "A clinic needs to send a referral without sending the patient. I drop in a synthetic patient record."
- **Upload the demo record.** Boxes appear on names, MRN, SSN, address, signature.
> "Structured IDs — SSN, MRN — come from deterministic rules, perfect precision. Names, addresses, context — that needs *reading*, so Gemma reads it. But here's our key move: we **don't trust the model's coordinates.** Gemma hands us the sensitive *strings*; **OCR pins the exact pixels.** The label `Phone:` stays readable — only the number dies."
- **Click Redact.** Black boxes burn in.
> "And the part that matters —" *(do it live: select/drag under a box, Ctrl+C, paste into the address bar)* "— I try to copy the text out from under the box. **There's nothing there.** We didn't cover the data; we rendered the page to an image and **destroyed** it. This file is physically incapable of the Epstein / Meta copy-paste failure."
- **Flash the Safe Harbor coverage panel + downloadable verification report.**
> "It grades itself against the 18 HIPAA Safe Harbor categories, and a verification battery attacks our own output — select-all, text-search, re-OCR the pixels, metadata audit — per document."

### [1:50–2:30] SECURE + ORGANIZE — the same loop, twice more
> "Same engine, two more surfaces."
- **Run SECURE scan.** Show the Safety Score + a plain-English finding.
> "A **$0 IT department** — read-only scan for plaintext credentials, weak config, risky ports. Gemma *explains* each finding in one sentence for a non-technical front desk; it never executes anything. See a plaintext key? One click — **Send to Redactor** — and REDACT destroys it."
- **Run ORGANIZE plan → apply → Undo.**
> "And the messy folder names itself: Gemma reads each file, code enforces the naming, and every move is journaled — so **Undo** fully reverses it. Nothing is moved, redacted, or changed without a click."

### [2:30–3:00] Why it's right — the close
> "Two things make this real. **One: it's triage, not judgment** — a human clears every page, and we bias Gemma to *over*-redact, because a false positive costs one click and a false negative is a breach. **Two: it's Gemma 4 — open weights, Apache 2.0** — the first model good *and* small enough to do text, vision, and classification for all four tools on an 8 GB laptop. No cloud API can legally be in this loop. That's not our preference — that's the constraint, and we built the whole product around it. **Four tools. One laptop. Zero cloud.** Thank you."

---

## THE QA — 2:00 (rehearse these; one breath each, never overclaim)

**"How do you know the redaction didn't miss something?"**
> "Three layers plus a human. Deterministic rules catch structured PII with perfect precision. Gemma reads for meaning — and we don't trust its pixel coordinates: it gives us strings, OCR pins the pixels. Then a verification battery attacks our own output — select-all, text-search, re-OCR, metadata audit — per document. And a human signs off, exactly as HIPAA Safe Harbor requires."

**"Model accuracy? Hallucinations?"**
> "Pure-LLM PII detection benchmarks around 0.54 F1 — that's *why* we don't run pure-LLM. Rules + Gemma + human review, biased to over-redact: a false positive is one click, a false negative is a breach."

**"Why Gemma and not a bigger cloud model?"**
> "For this buyer the cloud is disqualified, not dispreferred — no BAA, and the upload itself is the disclosure. Gemma 4 is the first open model good *and* small enough: one local model does text, vision, and classification for every tool on an 8 GB laptop."

**"Is a local model fast enough?"**
> "E4B runs ~38 tok/s on the demo laptop — interactive. A hardware probe detects VRAM and picks the right Gemma variant per machine; 12B is the quality mode at ~14 tok/s. And there's no network round-trip."

**"Isn't running offline table stakes at this hackathon?"**
> "Running offline is easy. Being *architecturally incapable* of leaking is the product: zero external assets, egress panel pinned at 0, output that physically can't do the copy-paste mistake. The constraint is the feature."

**"What actually works today?"** *(be exact)*
> "Three of four prongs, end-to-end on **synthetic** data. REDACT passes the full verification battery — zero recoverable characters. SECURE finds planted credentials and scores the machine. ORGANIZE classifies, renames, and fully undoes. TRANSCRIBE — on-device visit-to-note — is the next prong, in design."

**"Business model? Who pays?"**
> "Apache-2.0, free forever — open source *is* the model for this segment. The funded players charge $299–$1,512 per clinician per month and sell to CFOs of big systems. Our pitch to a two-provider clinic: $0, BAA-free, self-verifying. Path: pilots → community → paid support / EHR integration later, never a license fee."

## Never say
- ❌ "HIPAA compliant" → ✅ "supports Safe Harbor de-identification — compliance is organizational; we do the technical piece."
- ❌ "All four tools work" → ✅ "three shipped, one in design."
- ❌ "It catches everything" → ✅ "recall-biased, with human sign-off."

## If the live demo breaks (fallback)
- `MODEL MISSING` badge → wrong Ollama tag; pull `gemma4:e4b-it-qat` or edit `FAST_MODEL` in `app/backend/gemma.py`.
- No boxes / "deterministic only" → Ollama isn't running; detection still falls back to rules — say so and keep going.
- Nothing detected on a scan → `tesseract --version` must resolve on PATH.
- Port busy → `--port 8010`.
- Worst case → cut to the pre-recorded screen capture (attach it alongside the repo link).
