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
    presidio_detect.py # deterministic Scan layer: Presidio analyzer + spaCy NER (on-device)
    phase1_redact.py   # ingest → hybrid detect → OCR-grounded boxes → burn/flatten/scrub → verify
    phase2_secure.py   # deterministic collectors → FixRegistry → Gemma explainer → Safety Score
    phase3_organize.py # inventory → Gemma classify → propose → crash-safe journal → undo
    main.py            # FastAPI: one server, three phases, egress-proof endpoint
  frontend/
    index.html         # single-page UI, zero external assets (works with Wi-Fi off)
  demo-data/           # SYNTHETIC sample doc + planted secret + messy folder
  make_demo_data.py
```

**Detection design (the important bit):** this is the **Scan (deterministic) → Understand (Gemma)** spine. The Scan layer is **Microsoft Presidio** running fully on-device — validated recognizers (SSN, credit card + Luhn, IBAN, passport, MRN, …) plus **spaCy NER** for names / locations / organizations — augmented by Obscura's own regex floor for healthcare identifiers. Gemma then does the one job an LLM wins at: **quasi-identifier / re-identification** reasoning over the text. Every detected string is **located with Tesseract OCR word boxes** — the *engine finds the string*, *OCR fixes the pixels*, and only the value is boxed (field labels like `Phone:` stay visible). Model bounding-box coordinates are used only for genuinely visual items (signatures, faces). This kills the "characters peeking out from under the box" failure mode that coordinate-only tools suffer. If Presidio isn't installed, detection falls back to regex + Gemma automatically.

**True redaction:** boxes are drawn onto the rasterized page, the page is re-encoded through raw pixels (no layers), exported as an image-only PDF, and its metadata dictionary is cleared. **Verify** re-opens the output, asserts there is no selectable text layer, and OCRs the rendered pages to confirm none of the redacted strings survive.

## Setup

### Prerequisites

| Tool | Why | Install |
|---|---|---|
| **Python 3.11+** | backend runtime | [python.org](https://www.python.org/downloads/) |
| **Tesseract OCR** | pixel-exact coordinate grounding for REDACT | macOS: `brew install tesseract` · Ubuntu: `sudo apt install tesseract-ocr` · Windows: [UB-Mannheim build](https://github.com/UB-Mannheim/tesseract/wiki) |
| **Ollama ≥ 0.22** | runs Gemma 4 locally | [ollama.com/download](https://ollama.com/download) |

### 1. Clone

```bash
git clone https://github.com/meetkpatel/Obscura.git
cd Obscura
```

### 2. Python environment + dependencies

Use a virtual environment so the install is isolated:

```bash
python3 -m venv app/.venv
source app/.venv/bin/activate          # Windows: app\.venv\Scripts\activate
pip install -r app/requirements.txt
```

### 3. Download the spaCy NER model (one-time, ~590 MB)

Presidio's named-entity recognition needs this model. It caches locally, so it
works offline afterward:

```bash
python -m spacy download en_core_web_lg
```

> If you skip Presidio/spaCy entirely, the app still runs — REDACT falls back to
> its regex + Gemma passes automatically.

### 4. Pull a Gemma 4 model in Ollama

```bash
ollama pull gemma4:e4b-it-qat     # interactive default (~38 tok/s on an 8 GB GPU)
ollama pull gemma4:12b-it-qat     # quality mode for dense docs (~14 tok/s)
```

The app expects these exact tags. If the header shows **`MODEL MISSING`**, the
pulled tag name doesn't match — either pull the tags above, or edit
`FAST_MODEL` / `QUALITY_MODEL` in [`app/backend/gemma.py`](app/backend/gemma.py)
to a Gemma model you already have (`ollama list` shows them). REDACT still detects
via Presidio + regex without Gemma; Gemma adds the quasi-identifier and vision passes.

> Benchmarked on an RTX 4070 laptop (8 GB VRAM): the 12B QAT model fits in VRAM
> but generates ~14 tok/s; **E4B is the interactive default**. Both models + the
> Ollama installer belong on a USB stick for the venue — don't trust conference Wi-Fi.

## Run

```bash
source app/.venv/bin/activate          # if not already active
python app/make_demo_data.py           # generate synthetic demo assets (first run only)

cd app/backend
python -m uvicorn main:app --port 8000
```

Then open **http://localhost:8000** (sign in — mock auth, any credentials).

Turn Wi-Fi off first. Everything still works — click the on-device badge to see the
egress proof (external connections: 0).

### Companion mode — monitor + dispatch from your phone

Obscura runs long jobs (deep scans, big reorgs). Companion mode lets you walk
away and keep working in parallel from your phone — watch live progress, get an
activity feed, dispatch a security scan or an organize plan, and approve the
plan when it's ready. Same zero-cloud rules apply.

```bash
# start the server reachable on your network (still token-gated):
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Click **📱 Companion** in the desktop header and scan the QR with your phone
(same Wi-Fi). That's it.

**Away from home / on cellular:** join both devices to your own
[Tailscale](https://tailscale.com) (or any WireGuard) network and open the same
address. The tunnel is end-to-end encrypted, device-to-device — no cloud relay
ever sees your data, so the confidentiality story is unchanged.

How it stays confidential:

- **No third-party service.** The phone talks directly to your machine. Obscura
  adds zero egress — verify it live on the Privacy tab (`/api/egress` labels
  your phone as *inbound, paired* and still counts outbound connections only).
- **Metadata-first.** The companion API serves job states, counts, scores and
  file names — never document pages, extracted text, or file contents.
  Box-by-box redaction review deliberately stays on the desktop.
- **Paired, not open.** Every non-localhost request must carry the pairing
  token from the QR; anything else is rejected before any route runs. The token
  is random, memory-only, and rotates every restart — restarting Obscura
  unpairs every phone.
- If port 8000 is taken and you run on another port, also set `OBSCURA_PORT`
  (e.g. `OBSCURA_PORT=8010`) so the pairing QR encodes the right port.

### Troubleshooting

- **`MODEL MISSING` badge** — the pulled Ollama tag doesn't match what the app asks
  for (see step 4).
- **No boxes / "deterministic only"** — Ollama isn't running (`ollama serve`) or the
  model isn't pulled; detection falls back to Presidio + regex.
- **Nothing detected on a scan/photo** — check `tesseract --version` resolves on PATH.
- **Port 8000 in use** — run with `--port 8010` (or any free port) and open that.

## Safety & scope

- Human-in-the-loop by default: nothing is redacted, no file is moved, and no machine setting is changed without an explicit click.
- SECURE is **read-only and defensive** — it scans your own machine and *describes* fixes from a hardcoded registry; Gemma never executes anything.
- ORGANIZE never deletes: it moves within the same volume via an atomic, journaled operation that **Undo** fully reverses.
- All demo data is synthetic. Never load real PII on stage.

## License

Apache-2.0 — mirroring Gemma 4's own open-weight license. See [LICENSE](LICENSE).
