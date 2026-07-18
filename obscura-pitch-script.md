---
type: working-doc
project: Obscura (working name)
doc: 3-minute pitch script + speaker notes
tags: [life, business, hackathon, gemma, redaction, pitch]
created: 2026-07-16
event: GDG Newport Beach "Build & Hack with Gemma 4.0" — Fri Jul 17 2026 · 3-min demo + 2-min QA
related:
  - [[obscura-prd]]
  - [[obscura-problem-statement]]
---

# Obscura — 3-Minute Pitch Script

*Rehearse this out loud 3×. Time it. The demo is the middle; the numbers open it; the
"why us / why now" closes it. Pair with `Obscura-Pitch-Deck.pptx` (8 slides).*

> **Delivery notes:** slow down on the numbers. Let the black boxes appear in silence.
> The copy-paste test is your mic-drop — pause after it. Do NOT sell "offline" as the
> headline (everyone's demo is offline tomorrow) — sell "cloud is *forbidden* here."

---

## [0:00–0:30] The hook — the number + the fear · (Slide 1–2)

> "Last year, federal agencies received **1.5 million** public-records requests. Two
> hundred sixty-seven thousand are stuck in a backlog that grew a third in one year, and
> it costs **$723 million** to process. Every one of those documents has to be redacted
> by hand before it's released.
>
> And when it's rushed, this happens —" *(Slide 2: the Epstein/Meta headline)* "— the
> Epstein files, the Meta antitrust filing. Someone drew a black box over the text… and
> reporters just **copied the text out from under it.** The data was never actually
> removed. It was just hidden."

## [0:30–1:00] The trap — why AI hasn't fixed this · (Slide 3)

> "So why not point AI at it? Because the document *is* the secret. Sending a classified
> or privileged file to a cloud AI to ask 'what's sensitive in here?' — **that upload is
> the leak.** For government records, court files, defense data, it's not just risky,
> it's illegal — sending export-controlled data to a cloud model can be a felony.
>
> So agencies are stuck: the fast tool is the forbidden tool. Until now."

## [1:00–2:00] The demo — Obscura · (Slide 4, then live)

> "This is **Obscura**. It runs Gemma 4 **entirely on this laptop.** Watch." *(Log in.)*
>
> "I drop in a records document." *(Upload the sample.)* "Gemma reads it like a person —
> and instead of just describing it, it returns the **coordinates** of every sensitive
> item: the name, the social security number, the address, the signature." *(Boxes
> appear — say nothing for a beat.)*
>
> "I click **Redact**." *(Filled black boxes burn in.)* "And here's the part that matters
> —" *(Slide: copy-paste test / do it live)* "— I try to select the text under the box.
> **There's nothing there.** We didn't cover the data. We rendered the page to an image
> and **destroyed** it. This document is physically incapable of the Epstein mistake.
>
> And the whole time —" *(hold up Wi-Fi-off / airplane icon)* "— **nothing left this
> machine.**"

## [2:00–2:30] Why it's right — trust + the model · (Slide 5)

> "Two things make this real. **One: it's triage, not judgment.** A human officer clears
> every page — we bias the AI to *over*-redact, because a false positive wastes a click
> and a false negative is a breach. **Two: it's Gemma 4, open-weight, Apache 2.0** — so it
> can run inside the agency's own firewall, on their own box. No closed cloud API can
> legally be in this loop. That's not our preference. That's the law."

## [2:30–3:00] The close — market + ask · (Slide 6–7)

> "The buyer is every organization that must release documents without releasing the
> people in them: FOIA offices, hospitals under HIPAA, law firms, defense contractors.
> They have the budget, the legal mandate, and **no cloud option.**
>
> Redaction should be as fast as AI and as final as a shredder. The only way to be both
> is to never let the document leave the room. **That's Obscura.** Thank you."

---

## Q&A prep (the 2 minutes after — rehearse these)

- **"What's your accuracy / what if it misses one?"** → *"It's first-pass triage — a
  human clears every page. We deliberately tune for over-redaction: the model's job is to
  make sure a reviewer never has to hunt for a miss, only reject the occasional extra box.
  A false negative is a breach; a false positive is one click."*
- **"Why not just use Gemini / a cloud API?"** → *"For these documents the upload itself
  is the disclosure — CUI, privilege, ITAR. A cloud API is disqualified by statute, not by
  price. Open weights running locally is the only legal configuration."*
- **"Isn't running offline nothing special — everyone here is on Ollama?"** → *"Offline is
  table stakes today, agreed. The point isn't that we *can* run offline — it's that for
  this use you *must*, and we built the whole product, including true pixel-level
  redaction and the audit trail, around that constraint."*
- **"How is this different from Redactable / Adobe redaction?"** → *"Two things: they're
  cloud SaaS — a non-starter for our buyer — and most tools still leave a recoverable
  layer or rely on the user knowing to flatten. We destroy the pixels by default and prove
  it with the copy-paste test."*
- **"Does the small model really detect well on real documents?"** → *"We run a hybrid:
  deterministic rules nail structured data like SSNs and card numbers perfectly, and Gemma
  handles names, faces, and context. Neither alone is enough; together they're strong, and
  the human review closes the gap."*
- **"What did you build today vs. what's the vision?"** → *"Today: the full detect →
  redact → prove → export loop on a single document, on-device. Next: multipage batch, an
  audit report, and video — bodycam redaction is the same idea with a bigger backlog."*

## The 8 slides (see `Obscura-Pitch-Deck.pptx`)

1. **Title** — Obscura · "Redaction that never leaves the room."
2. **The problem** — the FOIA numbers + the Epstein/Meta failure.
3. **The trap** — you can't send the secret to the cloud to hide the secret.
4. **The product** — Obscura, Gemma 4 on-device, the pipeline.
5. **The proof** — before/after + copy-paste test + on-device badge.
6. **Why us / why now** — hybrid + human-in-the-loop + Apache 2.0 + the legal moat.
7. **The market** — FOIA, HIPAA, legal, defense — budget + mandate + no cloud.
8. **Close** — "as fast as AI, as final as a shredder." Thank you.
