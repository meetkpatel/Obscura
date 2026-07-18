# Obscura — 2-Minute QA Cheat Sheet (4 speakers, print or keep on a phone)

_Grounded in the ambient-scribe pitch-deck teardown (Ambience/Suki/Abridge/DeepScribe) + our build. One breath per answer. Whoever owns the topic answers; nobody talks twice in a row._

## The kill-shot questions

**"What if Epic / the EHR vendors just ship this natively?"**
→ "Epic's native AI serves the top health systems — the analyst take is that standalone cloud scribes die there. Our users are the clinics running paper and bare-bones EHRs that Epic never reaches. And you can't commoditize open-source on-device software — it already IS the commodity. We're the floor, not a feature."

**"How do you know the redaction didn't miss something?"**
→ "Three layers. Deterministic rules catch structured PII with perfect precision. Gemma 4 reads for meaning — and we don't trust its pixel coordinates: it gives us strings, OCR pins the pixels. Then a verification battery attacks our own output — select-all, text-search, re-OCR, metadata audit — per document. And a human signs off, exactly as HIPAA Safe Harbor requires."

**"Accuracy of the model? Hallucinations?"**
→ "Pure-LLM PII detection benchmarks around 0.54 F1 — that's why we don't run pure-LLM. Rules + Gemma + human review, biased to over-redact: a false positive costs one click, a false negative is a breach. Same trust pattern the funded players use — Abridge and Suki do 'evidence linking' from note to transcript; our analog is the coverage panel plus the verification report."

**"Why Gemma and not a bigger cloud model?"**
→ "For this buyer the cloud is disqualified, not dispreferred — no BAA, and the upload itself is the disclosure. Gemma 4 is the first open model good enough AND small enough: one local model does text, vision, and classification for all our tools on an 8GB laptop."

**"Business model? Who pays?"**
→ "Apache-2.0, free forever — open source is the business model for this segment. The funded players charge $299–$1,512 per clinician per month and sell to CFOs of big systems. In a two-provider clinic the CMO, CFO, and compliance officer are the same person — and she's seeing patients. Our pitch to all three of her: $0, BAA-free, self-verifying. Sustainability path: pilots → community → paid support/EHR integration later, never a license fee."

**"What actually works today?"** (be exact — never overclaim)
→ "Three of four prongs end-to-end on synthetic data: REDACT passes the full battery — 16 of 18 Safe Harbor categories flagged on our sample, zero recoverable characters. SECURE finds planted credentials and scores the machine. ORGANIZE classifies, renames, and fully undoes. TRANSCRIBE is the next prong — in design."

**"Latency? Is a local model fast enough?"**
→ "E4B runs ~38 tok/s on the demo laptop — interactive. A hardware probe picks the right Gemma variant per machine; 12B is the quality mode. And there's no network round-trip: cloud human-in-the-loop scribes historically took hours; local inference is seconds."

**"Isn't offline table stakes at this hackathon?"**
→ "Running offline is easy. Being *architecturally incapable* of leaking is the product: zero external assets, egress panel at zero, output that physically can't do the Epstein copy-paste mistake. The constraint is the feature."

## Demo beats (inside the 3 min)
1. Wi-Fi off, egress panel: 0 (5s, wordless point)
2. Drop synthetic patient record → boxes appear → Redact
3. The copy-paste test — select under the box, nothing there (the mic-drop; pause)
4. Safe Harbor coverage panel + verification report download (flash it)

## Never say
- "HIPAA compliant" (say: "supports Safe Harbor de-identification — compliance is organizational; we do the technical piece")
- "All four tools work" (three shipped, one in design)
- "It catches everything" (recall-biased + human sign-off)

## Slide 6 (Four Prongs) — narrate it as a WORKFLOW, not a feature list
(Per the deck-research report: best decks show the clinician's day — before/during/after — never a floating capability box.)
Speaker 2 says, pointing down the list:
"Nine a.m. — the visit writes itself while the door is still closed. Eleven-thirty — a referral
goes out redacted, the patient's identity stays home. Lunch — the laptop gets a safety check.
Five o'clock — the day's files name and file themselves. That's one Tuesday, one laptop, zero cloud."

## Sequencing note (why the deck is ordered this way — if a judge asks about structure)
Architecture (slide 7) sits AFTER the product creates desire and BEFORE trust questions arise —
the same sequencing Ambience/Abridge/Palantir use. Don't reorder on the fly.
