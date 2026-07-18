---
type: working-doc
project: Obscura (working name) — on-device document redaction
doc: Problem Statement & Rationale
tags: [life, business, hackathon, gemma, redaction, foia]
created: 2026-07-16
event: GDG Newport Beach "Build & Hack with Gemma 4.0" — Fri Jul 17 2026
related:
  - [[obscura-prd]]
  - [[hackathon-gemma4-top10-TOMORROW]]
---

# Obscura — Problem Statement

*Why this exists, what's broken today, and why it has to be solved on-device.*

---

## The one-sentence problem

**Redacting a sensitive document safely is slow, manual, and error-prone — and the one
tool that could make it fast, a cloud AI, is the exact tool you're legally forbidden to
use, because sending the document away to ask "what's sensitive here?" is itself the
disclosure.**

---

## 1. Redaction is a massive, growing, hand-done bottleneck

Government agencies are the largest redactors on earth, and they are drowning. From the
DOJ's own FY2024 Annual FOIA Report **[GOV — checkable]**:

- **1.5 million** FOIA requests in FY2024 — up **25%** from 1.2M the year before.
- A backlog of **267,056** requests — up **33%** in a single year.
- **$723 million** spent processing requests (up 22%), plus **$54 million** defending
  FOIA lawsuits.
- **5,638** full-time FOIA staff doing this largely by hand.
- Simple-request wait times rose from **39 to 44 days** — and *Federal News Network*
  (Mar 2026) reported staff cuts are pushing backlogs **higher**.

Every one of those requests may contain names, SSNs, medical details, or law-enforcement
information that a human must find and black out, page by page, before release. This is
the definition of a task that is expensive, repetitive, high-stakes, and done by people
who don't have time — the exact profile of work that should be compressed by AI.

## 2. When redaction is done fast, it's done wrong — catastrophically

The failure mode isn't hypothetical. It's the most repeated mistake in modern document
handling: someone draws a **black box over text**, but the text is still *there*,
selectable underneath. **[LAW/NEWS — documented]**

- **DOJ Epstein files (Dec 2025):** improper redaction; readers simply **copied the text
  from under the black boxes**. Reported by Forbes and others.
- **Meta v. FTC (2025):** within *hours* of filing, journalists selected the blacked-out
  text, copied it, and pasted competitor secrets in plain text.
- **Manafort case (2019):** copy-paste revealed a Madrid meeting, shared campaign polling
  data, and a Ukraine peace-plan discussion — all "redacted."
- **NYT / Snowden documents (2014):** highlight, copy, paste. Gone.

The root causes are always the same three: **(a) cosmetic-only redaction** (a box over a
live text layer), **(b) OCR misalignment** (the box lands on the wrong coordinates), and
**(c) metadata leakage** (sensitive content hiding in a document layer nobody flattened).

**The lesson:** a redaction tool's job is not to *cover* data. It is to *destroy* it, and
prove it's gone.

## 3. The cloud paradox — why you can't just use ChatGPT

The obvious fix is "point a powerful AI at the document." But the document is, by
definition, the sensitive thing. For the biggest redactors, sending it to a commercial
cloud API is not merely risky — it's prohibited:

- **Government CUI / law-enforcement records** cannot be processed on commercial cloud
  environments that can't guarantee US-person handling and no data egress.
- **Attorney-client privileged** material risks **waiver** if exposed to a third party.
- **ITAR / export-controlled** technical data: transmission to a cloud LLM can itself be
  an **unauthorized export** — civil penalty **$1,271,078 or 2× the transaction value**,
  criminal up to **$1M and 20 years** (eCFR 22 CFR Part 127) **[GOV]**.

So the classification step — "what in here is sensitive?" — is precisely the step that
cannot leave the building. **This is not a preference for on-device AI. It is a legal
requirement, and it disqualifies every closed API by statute.**

## 4. Why now — the capability just arrived

Two things became true at the same time:

- **Open-weight models got good enough and small enough.** Gemma 4 (Apache 2.0) runs
  entirely on a laptop via Ollama, does **native document/PDF parsing, OCR, handwriting
  recognition, and object detection that returns bounding-box coordinates** — the exact
  primitive redaction needs — with **no network**.
- **The detection primitive is native.** Gemma 4 returns `[y1, x1, y2, x2]` boxes for
  requested objects out of the box. You no longer need a trained, single-purpose vision
  model per document type; you can ask, in plain language, "find every SSN, name, and
  signature," and get coordinates back — locally.

For the first time, the fast tool and the legal tool are the same tool.

## 5. The honest challenges (what makes this hard, and how we answer)

A serious problem statement names its own hard parts. **[research-grounded]**

| Challenge | Reality | Our answer |
|---|---|---|
| **Recall is life-or-death** | Open-source LLM PII detection averages only ~**0.54 F1** alone; a single missed SSN is a breach. | **Hybrid detection** (deterministic regex for structured PII + Gemma for names/faces/context) + **human-in-the-loop** review + a **recall bias** (when unsure, redact). |
| **No single method is both precise and complete** | Regex nails SSNs but is blind to names; NER catches names but over-flags. | Run **both** and merge. Regex/checksums for SSN, credit-card (Luhn), email, phone; Gemma for the unstructured, reasoning-dependent rest. |
| **Cosmetic redaction leaks** | A box over text is not redaction. | **Rasterize → burn filled boxes into the pixels → flatten → export image-only PDF.** There is no text layer left to copy. Strip metadata. This is a structural guarantee, not a promise. |
| **Small model, hard documents** | E4B may miss small text on dense forms. | Use **12B** if RAM allows; raise the **vision token budget** (up to 1120) for OCR-grade detail; one-field-at-a-time prompts. |
| **Accountability** | FOIA demands a defensible, auditable process. | Every redaction logged (page, box, category, reviewer, timestamp) → exportable **audit trail**. |

## 6. Who feels this pain (and would pay)

- **Government FOIA / public-records offices** — the anchor. Statutory duty, growing
  backlog, existing budget, and a hard cloud prohibition.
- **Hospitals & health systems** — HIPAA Safe Harbor requires stripping **18 identifier
  types** before data sharing.
- **Law firms** — privilege review, where a leak means waiver.
- **Defense / aerospace subcontractors** — ITAR/CUI, where the cloud is a felony.
- **Insurers, courts, journalists' FOIA shops** — anyone who must release documents
  without releasing the people in them.

## 7. The thesis in one line

**Redaction should be as fast as AI and as safe as a shredder — and the only way to be
both is to never let the document leave the room.** Obscura is that tool.

---

## Sources

- FOIA scale **[GOV]** — [DOJ OIP FY2024 Annual FOIA Report](https://www.justice.gov/oip/media/1398111/dl?inline=) · [Brechner Center summary](https://brechner.org/2025/04/30/foia-requests-denials-surge-fy-2024/) · [GAO on FOIA backlogs](https://www.gao.gov/blog/foia-backlogs-hinder-government-transparency-and-accountability) · [Federal News Network, Mar 2026](https://federalnewsnetwork.com/agency-oversight/2026/03/significant-staff-cuts-drive-rising-foia-backlogs/)
- Redaction failures — [ABA: Embarrassing Redaction Failures](https://www.americanbar.org/groups/judicial/resources/judges-journal/archive/embarrassing-redaction-failures/) · [Redactable: failures in history](https://www.redactable.com/blog/most-embarrassing-redaction-failures-in-history-and-how-they-can-be-avoided) · [Meta/FTC leak](https://saferedact.app/insights/meta-ftc-redaction-failure) · [Forbes: Epstein files un-redacted](https://www.forbes.com/sites/daveywinder/2025/12/26/epstein-files-hacked---all-you-need-to-know/) · [Tech-Savvy Lawyer: how to redact properly](https://www.thetechsavvylawyer.page/blog/2025/12/25/how-to-redact-pdf-documents-properly-and-recover-data-from-failed-redactions-a-guide-for-lawyers-after-the-doj-epstein-files-release-leak)
- PII detection accuracy — [PRvL: LLMs for PII redaction (arXiv 2508.05545)](https://arxiv.org/html/2508.05545v1) · [Benchmarking open-source PII detection](https://albertsikkema.com/python/security/privacy/2026/06/01/benchmarking-open-source-pii-detection.html) · [Protecto: best NER models for PII](https://www.protecto.ai/blog/best-ner-models-for-pii-identification/)
- Redaction workflow / human-in-the-loop — [CIO: using AI to redact PII at scale](https://www.cio.com/article/4185269/how-to-use-ai-to-redact-pii-in-large-document-sets.html) · [Redactable: complete guide to PII redaction](https://www.redactable.com/blog/the-complete-guide-to-pii-redaction) · [Docuflair: what is redaction software](https://www.docuflair.com/en/pages/resources/blog/what-is-redaction-software.html)
- HIPAA identifiers — [Accountable: the 18 HIPAA identifiers](https://www.accountablehq.com/post/complete-list-of-the-18-hipaa-identifiers-for-de-identification-safe-harbor)
- ITAR **[GOV]** — [eCFR 22 CFR Part 127](https://www.ecfr.gov/current/title-22/chapter-I/subchapter-M/part-127)
- Gemma 4 capability — [image understanding docs](https://ai.google.dev/gemma/docs/capabilities/vision/image) · [model card](https://ai.google.dev/gemma/docs/core/model_card_4)
