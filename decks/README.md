# Obscura Decks — how to edit & rebuild

Every deck here is **generated from code** — edit the `.js`, re-run, done. No hand-editing pptx needed (but you can: the pptx files are normal PowerPoint).

## The three decks

| File | Purpose | Generator |
|---|---|---|
| `20260718_Obscura_Pitch_90s` | 10-slide **stage deck** (2-min pitch + 1-min live demo fits the 3-min window) | `assets/gen_deck_v2.js` |
| `20260718_Obscura_4-Prong_Healthcare_Deck` | 14-slide **detail / leave-behind** (HIPAA Safe Harbor, competitive 2×2, workflow, cost ledger) | `assets/gen_deck.js` |
| `20260718_Obscura_Overview_PalantirGrade` | 17-slide **overview** — Palantir-AIP structural baseline + healthcare humanity; market slide grounded in Abridge's public customer roster | `assets/gen_deck_v3.js` |

## Rebuild

```bash
npm install -g pptxgenjs
cd decks/assets
NODE_PATH=$(npm root -g) node gen_deck_v3.js MyDeck.pptx     # or gen_deck.js / gen_deck_v2.js
# optional PDF:
soffice --headless --convert-to pdf MyDeck.pptx
```

Run from `decks/assets/` — image paths in the scripts are relative.

## Gotchas (learned the hard way)

- **Never use pptxgenjs `sizing:{type:"cover"}`.** LibreOffice crops it correctly; **PowerPoint stretches** (squeezed people). All images here are pre-cropped with PIL to the exact placement aspect ratio and embedded plain. If you add an image, crop it to the target aspect first.
- Fonts: stage/detail decks use Georgia + Calibri; overview uses Segoe UI Light / Semibold + Consolas (Windows-installed).
- The images are Nano Banana Pro (`gemini-3-pro-image`) generations — synthetic, no real people/PHI. Keep numbers OUT of generated images (models hallucinate digits); charts/figures stay native text.

## Stage-deck speaker split (120s, 4 speakers)

1. Slides 1–4 (~35s): hook + "the upload is the breach" (pause after)
2. Slides 5–6 (~20s): open models + four prongs — narrate as a DAY, not features
3. Slides 7–8 (~35s): walk the trust-boundary diagram left→right, then proof (0 / 18 / 4)
4. Slides 9–10 (~30s): free-forever contrast + close

QA prep: `QA_CHEAT_SHEET.md`. Submission text: `KAGGLE_WRITEUP_GenAIforGood.md`.

## Fact sources (verify before external use — list prices move)

- Scribe pricing: Freed pricing page; Suki via healos/lemonfox 2026 guides; Nuance DAX via Microsoft Marketplace + reseller breakdowns
- Redaction: CaseGuard + Redactable published pricing
- Managed IT/HIPAA: MSP pricing surveys (Atlantic Computer Systems, ACT, AccountableHQ)
- Market size: Dataintelo, Astute Analytica, SNS Insider, Grand View (2025–26 reports)
- Clinician stats: Sinsky et al. (Annals of Internal Medicine) 2-for-1 desk-time; Mayo Clinic Proceedings intent-to-leave; IBM Cost of a Data Breach 2024; HRSA 2023
- Client roster on the market slide: abridge.com/customers (public page, July 2026) — labeled as Abridge's customers (market proof), NOT ours
- Reference decks studied (Ambience Series C, Suki Series D, Palantir AIP): kept OFF this public repo (their copyright) — ask the team for the shared-drive `reference-decks` folder
