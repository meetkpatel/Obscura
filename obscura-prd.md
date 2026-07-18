---
type: working-doc
project: Obscura (working name) — on-device document redaction
doc: Product Requirements Document (PRD) + MVP spec
tags: [life, business, hackathon, gemma, redaction, foia, prd]
created: 2026-07-16
event: GDG Newport Beach "Build & Hack with Gemma 4.0" — Fri Jul 17 2026
related:
  - [[obscura-problem-statement]]
  - [[hackathon-gemma4-top10-TOMORROW]]
---

# Obscura — PRD & MVP Spec

**On-device AI redaction. Find every sensitive detail in a document and destroy it —
permanently, provably, and without the file ever touching a network.**

> Working name: **Obscura**. Tagline: *"Redaction that never leaves the room."*
> Anchor vertical: **Government / FOIA.** Stack: **Gemma 4 (12B via Ollama)** +
> a modern web UI with login. Everything below is scoped so the **hackathon slice (§7)
> is genuinely buildable in 3.5 hours**, with V2/V3 marked as future.

---

## 1. Vision & positioning

**Vision:** every organization that must release documents without releasing the people
in them gets a redaction tool that is as fast as AI and as final as a shredder — running
entirely on their own hardware.

**Positioning (one line):** *Cloud redaction tools ask you to upload your most sensitive
document to a stranger's server. Obscura never does — because the AI runs on your
laptop.*

**Category:** on-device / air-gapped document privacy. **Not** another cloud SaaS
redactor (Redactable, Docuflair) — the whole point is that nothing leaves.

## 2. Target users & the job-to-be-done

| User | Job-to-be-done | Why Obscura |
|---|---|---|
| **FOIA / public-records officer** (anchor) | Release requested records with every exempt detail removed, defensibly, at scale. | Statutory duty + 267k backlog + cloud prohibited. |
| Compliance / privacy officer (health, legal) | De-identify before sharing (HIPAA 18 identifiers; privilege). | On-prem = no waiver, no breach surface. |
| Paralegal / records clerk | Stop black-box-over-text mistakes. | True redaction is structural, not manual. |

**Primary persona for the demo — "Dana, FOIA officer":** 400 pages due this week, a
marker-and-manual process, and a personal fear of being the next Epstein-files headline.

## 3. Goals & non-goals

**Goals**
- Detect the widest possible set of sensitive items with a **recall bias** (miss nothing).
- Make redaction **irreversible and leak-proof** (no recoverable text layer, no metadata).
- Keep a **defensible audit trail** of every action.
- Run **100% locally**. No network call, ever.
- Feel like a **polished product** — login, clean modern UI — not a script.

**Non-goals (say these out loud; they build trust)**
- **Not** a fully autonomous redactor. A human approves. It is *triage + tooling*, not a
  decision-maker.
- **Not** a medical/legal judgment engine — it finds identifiers, it doesn't practice law.
- **Not** trying to beat a fine-tuned YOLO on speed; open-vocabulary flexibility is the point.

## 4. The core design principles (these are the product)

1. **Destroy, don't cover.** Every redaction is burned into a flattened raster and
   exported as an image-only PDF. There is no text under the box to copy. *This is the
   anti-Epstein guarantee and it is the single most important design decision.*
2. **Recall over precision.** A false positive wastes a reviewer's click. A false
   negative is a breach. When the model is unsure, it redacts. The human *un*-redacts if
   needed — the safe default is hidden.
3. **Hybrid detection.** Deterministic rules catch structured PII perfectly; the model
   catches the rest. Neither alone is enough (open-source LLM PII ≈ 0.54 F1).
4. **Human-in-the-loop by default.** The compliance-preferred mode. The tool proposes;
   the officer disposes; the log records.
5. **Local or it doesn't ship.** The network being off is not a feature toggle. It's the
   architecture.

## 5. Functional requirements — the redaction pipeline

```
 ┌─────────┐   ┌──────────────┐   ┌─────────────────────┐   ┌───────────┐   ┌──────────┐
 │ INGEST  │──▶│  DETECT      │──▶│  REVIEW (human)     │──▶│ REDACT    │──▶│ AUDIT    │
 │ pdf/img │   │  hybrid      │   │  accept/reject/add  │   │ burn+flat │   │ log+export│
 └─────────┘   └──────────────┘   └─────────────────────┘   └───────────┘   └──────────┘
        all on-device · Ollama @ localhost:11434 · no network
```

### 5.1 Ingest
- Accept **PNG/JPG** (MVP) and **PDF** (render each page to an image via `pdf2image` /
  `pypdfium2`). Single page for the hackathon; multipage in V2.
- Normalize to a known resolution; keep the scale factor for coordinate descaling.

### 5.2 Detect (hybrid)
- **Pass A — deterministic (regex + checksums):** SSN (`\d{3}-\d{2}-\d{4}` + context),
  credit card (Luhn), email, phone, dates, ZIP. High precision, instant, catches what
  models miss. *(This is where your QA brain shines — you're writing the test oracle.)*
- **Pass B — Gemma 4 vision (12B via Ollama):** prompt for the unstructured/visual items
  the regex can't see — **names, addresses, signatures, faces, handwriting, and
  contextually sensitive passages.** Returns `[y1, x1, y2, x2]` boxes on a 1000×1000 grid.
  - Prompt shape: *"Detect and return JSON only: social security numbers, full names,
    home addresses, signatures, faces, dates of birth. Format: `[{box_2d:[y1,x1,y2,x2],
    label, reason}]`."*
  - Vision **token budget 1120** for dense documents (small text needs the resolution).
- **Merge:** descale both passes to pixel coordinates, dedupe overlapping boxes, union.

### 5.3 Review (human-in-the-loop)
- Render the document with every proposed box overlaid, color-coded by category, each
  showing **label + confidence + reason**.
- Reviewer can **accept / reject / resize / add** a box, and **filter by category**
  (e.g., FOIA exemption **b(6)** personal privacy, **b(7)(C)** law-enforcement personal
  privacy — let the officer redact by exemption).
- Default state = all proposed boxes **accepted** (recall bias); the officer removes the
  few false positives rather than hunting for misses.

### 5.4 Redact (true redaction)
- Draw **filled, opaque** rectangles onto the rasterized page (`PIL`,
  `ImageDraw.rectangle(fill="black")`).
- **Flatten** the page to a new image. **Export as an image-only PDF.** No text layer
  survives; copy-paste yields nothing.
- **Strip metadata** on export.

### 5.5 Audit
- Log every action: page, box coordinates, category, confidence, **accepted/added/rejected
  by whom, timestamp**.
- Export a **redaction certificate / audit report** (PDF or JSON) — the defensibility
  artifact FOIA and courts require.

## 6. UX & screens (modern, beautiful, with login — per your ask)

**Design language:** clean, dark, government-serious-but-modern. Think Linear/Vercel
polish, not enterprise-gray. One accent color (deep blue or teal). Generous whitespace.
An always-visible **"🔒 On-device · No network" status badge** — it's both reassurance
and the pitch.

1. **Login screen.** Beautiful, minimal. Product name + tagline, one card, email +
   password, a subtle "SSO (coming soon)" ghost button. **For the hackathon this is mock
   auth** (hard-coded / any credentials pass, or a demo user) — it *looks* like a real
   product without burning build time on real identity. Sets the "this is a product, not
   a script" tone the instant judges see it.
2. **Dashboard / upload.** Drag-and-drop zone, recent documents list, the on-device
   badge, a big "New redaction" button.
3. **Review workspace (the hero screen).** Document on the left with colored boxes
   overlaid; a right-hand panel listing detected items (icon, label, confidence, reason,
   accept/reject). Category filter chips across the top. A prominent **"Redact & Export"**
   button.
4. **Before/After + proof.** Split view. A **"Copy-paste test"** widget: try to select
   text on the output → nothing selectable. *(This is the money shot — it visually proves
   you didn't make the Epstein mistake.)*
5. **Audit panel.** The log, and a "Download audit report" button.

## 7. ⭐ Hackathon MVP slice (build 1:30–5:00 — ONE happy path)

**Cut everything except this loop:**

> Login (mock) → drag in a sample FOIA document (image) → auto-detect PII → boxes appear
> with labels → click **Redact & Export** → filled black boxes burned into a flattened
> image → before/after with the copy-paste-test proof → download.

**Build order (do in this sequence so you always have something demoable):**

1. **[H+0:00] Prove detection on YOUR sample doc via Ollama.** (You'll have tested this
   tonight.) Hard-code the model call. This is the risk — de-risk it first.
2. **[H+0:30] The redaction core, headless.** Python: image in → Gemma boxes → PIL draws
   filled rects → flattened PNG out. **If you stop here, you still have a demo.**
3. **[H+1:15] Wrap in the web UI.** Recommended: **a single modern page** (e.g. React/Vite
   + Tailwind, or plain HTML/JS + Tailwind) that calls a tiny local Python/Flask endpoint
   which calls Ollama. Upload → shows boxes → Redact button → before/after.
4. **[H+2:15] The login screen + polish.** Mock auth, the on-device badge, the accent
   color, the copy-paste-test widget. This is what makes judges believe it's a product.
5. **[H+3:00] Rehearse + record a 40-sec fallback video.** Freeze the build. Practice the
   3-min run 3×.

**Explicit cut list for today:** multipage PDF, real auth, batch, category-by-exemption
filtering, resize/add boxes, audit export, metadata scrub. All V2. **A working one-page
demo beats a broken product.**

## 8. Technical architecture

- **Model:** `gemma4:12b` via Ollama (`gemma4:e4b` fallback if <16GB RAM). Vision via
  Ollama's image input. Everything on `localhost:11434`.
- **Detection:** Python. `re` for structured PII; Ollama HTTP call for the vision pass;
  merge/descale util.
- **Redaction:** `pdf2image`/`pypdfium2` (PDF→image), `Pillow` (draw + flatten), image-only
  PDF export.
- **Backend:** thin Flask/FastAPI localhost server (upload, detect, redact, serve results).
- **Frontend:** React+Vite+Tailwind **or** single HTML+Tailwind page — whichever your team
  is faster in. Prioritize *looks polished* over *feature-complete*.
- **No external calls. No API keys. Airplane mode works.** (Demo it.)

## 9. Success metrics

**Product (the real ones):**
- **Recall / miss rate** — % of true sensitive items caught. *The number that matters.*
  Target: ≈100% caught *before* human review via over-redaction.
- **Precision / over-redaction rate** — secondary; measures reviewer clicks wasted.
- **Time per page** vs manual (target: seconds vs minutes; industry AI tools ≈5s/page,
  ~60× manual).
- **% pages needing human correction.**

**Hackathon (tomorrow):**
- Detects the planted PII on the sample doc live.
- Output has **zero selectable text** (copy-paste test passes on stage).
- The demo runs start-to-finish with the **Wi-Fi off**.

## 10. Risks & mitigations

| Risk | Mitigation |
|---|---|
| E4B misses small text on dense forms | Use 12B; token budget 1120; test tonight; use a clean, legible sample doc for the demo. |
| Model hallucinates a box in the wrong spot | Human-in-the-loop; recall bias means over-redaction, not exposure; demo doc is controlled. |
| Login/real auth eats build time | **Mock auth** — looks real, costs 20 min, not 2 hrs. |
| Full web app too ambitious in 3.5 hrs | Build order §7 keeps a headless demo working at H+0:30 as the floor. |
| "Why not cloud?" challenge | The legal-necessity answer (CUI/ITAR/privilege) — rehearsed, §3 of the problem doc. |
| "What's your accuracy?" challenge | "It's triage; a human clears every page; we tune for over-redaction because a false negative is a breach." |

## 11. Roadmap beyond the hackathon

- **V2:** multipage PDF + batch, per-exemption category filtering, accept/reject/resize,
  metadata scrub, exportable audit report, real auth + roles.
- **V3:** **video redaction (bodycam)** — face detection + tracking + re-encode; on-prem
  appliance; fine-tuned detector per document family; SSO; secure reversible unredact for
  authorized roles.
- **Business:** sell as an on-prem appliance / per-seat license to FOIA offices, health
  systems, and defense subs — the buyers for whom cloud is prohibited. Distribution:
  GovTech channels, records-management resellers.

---

## Sources
See [[obscura-problem-statement]] for the full, categorized source list
(**[GOV]** FOIA stats, redaction-failure cases, PII-detection accuracy research, HIPAA
identifiers, Gemma 4 capability docs).
