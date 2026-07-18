# Obscura

**Redaction that never leaves the room.** One on-device AI engine, three surfaces of your privacy — built on **Gemma 4**, running entirely on your laptop. No network, ever.

> GDG "Build & Hack with Gemma 4.0" — Newport Beach / Irvine, July 2026.

| Surface | What it does |
|---|---|
| **REDACT** | Find every sensitive item in a document and *destroy* it — burned into a flattened raster, no recoverable text layer, metadata stripped, self-verified. |
| **SECURE** | Read-only scan of your own machine — secrets in plaintext, weak config, risky ports — with a plain-English report and a Safety Score. |
| **ORGANIZE** | Gemma reads each file, proposes a clean folder structure and names, and applies it with a crash-safe journal and one-click **Undo**. |

The same loop everywhere: **Scan (deterministic) → Understand (Gemma) → Propose → Human approves → Apply → Verify → Undo.** One spine, three plugins.

Connective tissue: SECURE finds a plaintext key → **"Send to Redactor"** → REDACT destroys it. The phases feed each other.

## Why on-device

For the buyers who need this most — FOIA offices, hospitals under HIPAA, law firms, defense subcontractors — sending the document to a cloud AI to ask *"what's sensitive here?"* **is itself the disclosure**, and for CUI/ITAR it's illegal. Gemma 4 (Apache 2.0) is good enough to run the whole pipeline locally. The fast tool and the legal tool are finally the same tool.

## Architecture

```
app/
  backend/
    contracts.py       # frozen Pydantic vocabulary shared by all phases
    gemma.py           # single Ollama gateway: queue + structured JSON + retries
    phase1_redact.py   # ingest → hybrid detect → OCR-grounded boxes → burn/flatten/scrub → verify
    phase2_secure.py   # deterministic collectors → FixRegistry → Gemma explainer → Safety Score
    phase3_organize.py # inventory → Gemma classify → propose → crash-safe journal → undo
    main.py            # FastAPI: one server, three phases, egress-proof endpoint
  frontend/
    index.html         # single-page UI, zero external assets (works with Wi-Fi off)
  demo-data/           # SYNTHETIC sample doc + planted secret + messy folder
  make_demo_data.py
```

**Detection design (the important bit):** structured PII (SSN, card, email, phone) comes from **deterministic regex + Luhn** — perfect precision, instant. Names, addresses, and re-identifying context come from a **Gemma text pass** whose output strings are then **located with Tesseract OCR word boxes** — so the *model finds the string* but *OCR fixes the pixels*. Model bounding-box coordinates are used only for genuinely visual items (signatures, faces), where a slightly loose box is fine. This kills the "characters peeking out from under the box" failure mode that coordinate-only tools suffer.

**True redaction:** boxes are drawn onto the rasterized page, the page is re-encoded through raw pixels (no layers), exported as an image-only PDF, and its metadata dictionary is cleared. **Verify** re-opens the output, asserts there is no selectable text layer, and OCRs the rendered pages to confirm none of the redacted strings survive.

## Requirements

- **Ollama ≥ 0.22** with two models pulled:
  ```
  ollama pull gemma4:e4b-it-qat     # interactive default (~38 tok/s on an 8GB GPU)
  ollama pull gemma4:12b-it-qat     # quality mode for dense docs (~14 tok/s)
  ```
- **Tesseract OCR** on PATH (coordinate grounding for REDACT).
- Python 3.11+ and `pip install -r app/requirements.txt`.

> Benchmarked on an RTX 4070 laptop (8 GB VRAM): the 12B QAT model fits in VRAM but generates ~14 tok/s; **E4B is the interactive default**. Both models + the Ollama installer belong on a USB stick for the venue — don't trust conference Wi-Fi.

## Run

```
python app/make_demo_data.py                      # synthetic demo assets
cd app/backend
python -m uvicorn main:app --port 8000
# open http://localhost:8000  (sign in — mock auth, any credentials)
```

Turn Wi-Fi off first. Everything still works — click the on-device badge to see the egress proof (external connections: 0).

## Safety & scope

- Human-in-the-loop by default: nothing is redacted, no file is moved, and no machine setting is changed without an explicit click.
- SECURE is **read-only and defensive** — it scans your own machine and *describes* fixes from a hardcoded registry; Gemma never executes anything.
- ORGANIZE never deletes: it moves within the same volume via an atomic, journaled operation that **Undo** fully reverses.
- All demo data is synthetic. Never load real PII on stage.

## License

Apache-2.0 — mirroring Gemma 4's own open-weight license. See [LICENSE](LICENSE).
