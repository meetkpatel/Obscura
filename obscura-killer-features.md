---
type: working-doc
project: Obscura — on-device document redaction
doc: Competitive landscape + killer-feature research
tags: [business, hackathon, gemma, redaction, competitive, strategy]
created: 2026-07-16
related:
  - obscura-prd.md
  - obscura-problem-statement.md
---

# Obscura — Competitive Landscape & Killer Features

*Deep research on how everyone else does redaction, where they all stop, and the
features that would make Obscura a category of one. Source tiers labeled:
**[GOV]** statutory/government, **[ACAD]** academic/paper, **[VENDOR]** a company
selling the thing (marketing — directional).*

---

## The one big finding

**Every serious redaction tool on the market is a detector. None of them is a
reasoner.** They find and hide known patterns. Not one of them looks at the *finished*
document and asks the question a human expert asks: *"even with the names gone, can I
still tell who this is? And did we miss anything a pattern-matcher can't see?"*

That gap is not a minor feature. It is the difference between a tool that draws boxes
and a tool that thinks — and it is **exactly** what a local reasoning model like Gemma 4
can do that regex, NER, and cloud-detection APIs structurally cannot. **This is
Obscura's whole opening.**

---

## 1. The competitive landscape — who does what, and where they stop

| Tool | What it is | How it detects | Where it STOPS |
|---|---|---|---|
| **Microsoft Presidio** [VENDOR/open-source] | The open-source standard. On-prem, free, MIT. Analyzer + Anonymizer + Image Redactor. | NLP (spaCy) + regex + checksums (Luhn) + context scoring. 180+ entity types. | Detection only. Their own docs: *"no guarantee Presidio will find all sensitive information."* No reasoning about residual risk. A community thread is literally titled *"Redaction kills context, what do you use instead?"* |
| **Relativity / RelativityOne** [VENDOR] | eDiscovery giant, cloud. Native "Relativity Redact." | AI/ML + pattern recognition, integrated into review. | Cloud-only (disqualified for CUI/ITAR). Detection + workflow, not residual-identity reasoning. |
| **Everlaw** [VENDOR] | Cloud eDiscovery, strong UX. | ML + regex + custom patterns. 15 languages. | Cloud. Same ceiling. |
| **Nuix** [VENDOR] | High-speed investigations platform. | ML clustering, entity recognition, analytics. | Heavy/enterprise, cloud/server. Detection-centric. |
| **CaseGuard** [VENDOR] | The multimedia leader — video, audio, image, docs. 30+ PII/PHI types, 750+ formats, face/plate/screen redaction. | AI detection across media + auto-transcription. | The broadest *coverage*, but still detect-and-hide. No mosaic-effect reasoning. |
| **Redactable / Docuflair / ReadyRedact / RedactifyAI** [VENDOR] | SaaS document redactors. ~5s/doc, ~60× manual. | AI detection + human-in-the-loop review modes. | Cloud SaaS (upload required — the non-starter for our buyer). Detection + workflow. |
| **FOIA suites (GovQA, FOIAXpress, VIDIZMO)** [VENDOR] | Government records-request platforms. | Workflow + some auto-redaction + exemption tracking. | Records-management first; AI reasoning is bolted on, and it's cloud/hosted. |

**The pattern:** the market splits into **(a) cloud detectors** (fast, but you must
upload — illegal for Obscura's buyer) and **(b) on-prem detectors** (Presidio — free but
"no guarantee it finds all," and zero reasoning). **Nobody occupies "on-prem AND
reasoning."** That empty quadrant is the product.

---

## 2. The three things every tool gets wrong (your opening)

1. **They detect patterns, not *identity*.** They'll catch "SSN 431-88-2190" and miss
   that "the only left-handed pitcher on the 1998 team who now lives in Powell, WY" names
   exactly one person. Pattern-matchers are blind to the **mosaic effect**.
2. **They don't tell you what they missed.** A black box is silent about the boxes it
   *didn't* draw. There is no "second opinion." **[ACAD]** A Dec 2025 arXiv study of AI
   redaction in UK public authorities names this the "human oversight imperative" — AI
   surfaces items but cannot self-certify completeness.
3. **They produce boxes, not justification.** **[GOV]** FOIA law requires every redaction
   be *coded to a specific exemption* (Exemption 6, 7(C), 4…). *"A black bar with no
   label does not satisfy the statute."* Courts demand a **Vaughn index** — a
   portion-by-portion justification (Vaughn v. Rosen, 1973). Detectors give you the bar;
   the officer still writes the justification by hand.

Each of these is a reasoning task. Each is a killer feature. Here they are, ranked.

---

## 3. 🔑 Killer features, ranked

### ⭐ #1 — The Re-Identification Radar (the mosaic-effect engine)

**What it is:** After the direct identifiers are redacted, Gemma re-reads the document
and flags **quasi-identifiers** — facts that don't name anyone alone but, *combined*,
re-identify the person. Rare diagnosis + small county + a date. Job title + employer +
gender. It gives the officer a **residual re-identification risk score** and highlights
the specific combination.

**Why it's a game-changer:** this is the single hardest, most valuable problem in
de-identification, and **no pattern-based tool can do it** — it requires *reasoning about
what a document reveals as a whole.* **[GOV/ACAD]** It's the formal basis of HIPAA's
**Expert Determination** pathway (45 CFR 164.514) and the reason "de-identified" data
still leaks. Frameworks like k-anonymity exist precisely because removing names isn't
enough. **Obscura would be the first tool that hands a records officer an expert-style
residual-risk read on their own laptop.**

**Why only Gemma / on-device:** it's pure reasoning over the full document (256K context),
and the document can't go to the cloud. This is the perfect marriage of the constraint
and the capability.

**Demoability:** ⭐⭐⭐ — redact a document the "normal" way, then show Obscura's panel:
*"⚠️ Even with names removed, this is likely re-identifiable: 'rare autoimmune condition'
+ 'Inyo County' (pop. 18k) + 'diagnosed March 2026' points to a very small set of people."*
Judges will not have seen another tool do that.

**Effort:** medium — it's a second Gemma prompt over the redacted text, not new infra.
**Feasible as tomorrow's differentiator.**

---

### ⭐ #2 — Auto-Vaughn / Exemption Justification (the FOIA killer)

**What it is:** For every redaction, Gemma proposes the **specific FOIA exemption** and
writes a one-line **justification** — then compiles them into a **Vaughn index** as the
document is processed, not after a lawsuit.

**Why it's a game-changer:** **[GOV]** this is a *statutory requirement* that every
detector ignores — they give the officer a bar and leave the legal coding as manual work.
DOJ even publishes standard redaction-code explanations. Building the Vaughn index during
processing is what makes a production court-defensible. **This converts Obscura from "a
faster marker" into "the officer's legal co-author."**

**Why only Gemma:** matching a passage to an exemption and articulating *why* is
reasoning + drafting — the model's core strength — over data that can't leave the room.

**Demoability:** ⭐⭐⭐ — each box shows a chip: **b(6) · personal privacy** with a
hover-rationale, and a "Generate Vaughn index" button produces the table. Very visual,
very obviously valuable to a FOIA judge.

**Effort:** low-medium — a structured Gemma prompt per detected item. **Also feasible
tomorrow** (even as a lightweight version).

---

### ⭐ #3 — The Second-Opinion / Missed-PII Sweep (what you specifically asked about)

**What it is:** A dedicated verification pass. After detection (and even after the human
review), Gemma does an adversarial re-read: *"You are an auditor. Find anything sensitive
that was NOT redacted."* It surfaces a **"possible misses"** list the reviewer must clear
— the safety net that catches the un-boxed.

**Why it's a game-changer:** **[ACAD/VENDOR]** the entire industry consensus is "AI isn't
enough, you need human verification" — but nobody gives the human an *AI second reviewer*.
This directly attacks the failure mode behind every redaction scandal (the missed item).
It reframes the pitch from "we redact" to "**we make sure nothing slips through.**"

**Why only Gemma:** a second, differently-prompted reasoning pass over the whole
document, locally. Cheap because it's your own model — no per-call cost to run detection
twice.

**Demoability:** ⭐⭐ — a "🔍 Audit sweep" that lights up a missed handwritten initial or a
name buried in a sentence. Pairs beautifully with #1.

**Effort:** low — it's a second prompt. **Trivial to add tomorrow.**

---

### #4 — Insight & Summary Layer (the "understand the document" feature)

**What it is:** Beyond redaction, Gemma gives the officer a plain-language **summary** of
the document, a list of **who and what appears**, and a **sensitivity briefing**: *"This
is a use-of-force incident report involving 2 officers and 1 juvenile; it contains
medical info (Exemption 6) and an ongoing-investigation reference (Exemption 7(A))."*

**Why it's a game-changer:** it turns a redaction tool into a **triage tool.** A FOIA
officer facing 400 pages doesn't just need boxes — they need to *understand and
prioritize* the pile. This is the "insightful details" you asked for, and it's a natural
by-product of a model that already read the whole document to redact it.

**Why only Gemma:** summarization + entity extraction over the full doc, locally. The
model is already loaded and has already parsed the page — the summary is nearly free.

**Demoability:** ⭐⭐ — a clean right-rail "Document brief" panel.

**Effort:** low. A strong, easy add.

---

### #5 — Consistent Pseudonymization Mode (redaction that keeps the document readable)

**What it is:** Instead of black bars, optionally replace each entity with a **consistent
surrogate** — "John Smith" → **"Person A"** everywhere, "22 Ivy Ln" → **"[Address 1]"** —
so the released document is still *readable and analyzable* while identities are gone.

**Why it's a game-changer:** **[VENDOR]** the loudest complaint about redaction is
*"redaction kills context."* Black bars destroy the narrative; a journalist or researcher
can't follow "Person A did X, then Person A did Y." Consistent pseudonyms preserve the
*relationships* while protecting the people — and keeping it **consistent across the whole
document** (every "John Smith" → the same "Person A") is itself a reasoning/entity-linking
task most tools botch.

**Why only Gemma:** entity resolution ("these three mentions are the same person") is
reasoning, and it must stay local.

**Demoability:** ⭐⭐ — a toggle: **Redact ▸ Black bars / Pseudonyms.** Flipping it live is
a great "oh, nice" moment.

**Effort:** medium.

---

### #6 — Entity Consistency / "Redact everywhere" (table stakes, but do it well)

**What it is:** Redact *the person*, not the string — every mention, every alias, every
page, consistently. **[VENDOR]** "Redact all matching instances" exists in incumbents, but
they match *strings*; Gemma can match *people* (John / Mr. Smith / he / the plaintiff).

**Effort:** medium. More a correctness requirement than a headline feature — but the
entity-resolution version (not just string match) is genuinely better than incumbents.

---

## 4. The positioning this unlocks

Detectors say: *"We find and hide sensitive data."*

**Obscura says: *"We're the only tool that reads the finished document back and tells you
if the person is still identifiable — and writes the legal justification for every
redaction. On your hardware, because it has to be."***

That's not a faster marker. That's **an on-device de-identification expert.** The boxes
are the commodity; the reasoning around them is the moat — and the reasoning is the one
thing the cloud incumbents can't move on-prem and the on-prem incumbents (Presidio)
can't reason with.

---

## 5. What to actually do — tomorrow vs. roadmap

**For the hackathon (add ONE reasoning feature — it's what beats a room full of
detectors):**
- **Core loop** (detect → redact → true-flatten → export) as specced in the PRD, **plus**
- **#3 the Missed-PII sweep** (trivial, second prompt) as the safety-net line, **and**
- **#1 the Re-ID Radar** as the *wow* — even a lightweight version ("here's why this is
  still re-identifiable") is a moment no detector can match.
- If time is tight, **#2 exemption chips** is the easiest visible "this is FOIA-real"
  touch.

> ⚠️ Scope discipline: the core redaction loop must work first (PRD §7 build order). Add
> the reasoning panel only once detect→redact→export is solid. One killer reasoning
> feature > three half-built ones. The Re-ID Radar is one extra Gemma call over text you
> already have.

**For the product roadmap (V2+):** all six, plus batch/multi-doc entity consistency,
the full Vaughn-index export, and video (bodycam).

---

## 6. Honest caveats

- **[ACAD]** LLM PII detection alone is imperfect (open-source ≈ 0.54 F1). Every reasoning
  feature here is **decision-support for a human**, never an autonomous authority. That
  framing is not a weakness to hide — it's the compliant, court-defensible posture, and
  it's what the whole industry says is required.
- The Re-ID Radar gives a *risk read*, not a guarantee — position it as "expert second
  opinion," matching how HIPAA Expert Determination actually works.
- Don't over-claim accuracy numbers on stage; claim the *capability that's unique*
  (reasoning about residual identity + auto-justification), which is true and checkable.

---

## Sources

- Competitors [VENDOR] — [Presidio (GitHub / Microsoft)](https://github.com/microsoft/presidio) · [Presidio: "redaction kills context" discussion](https://github.com/data-privacy-stack/presidio/discussions/2043) · [ZipDo: auto-redaction tools 2026](https://zipdo.co/best/auto-redaction-software/) · [CaseGuard / Relativity / Everlaw / Nuix comparison](https://www.redactifyai.com/blog/best-redaction-software-comparison/)
- Re-identification / mosaic effect [GOV/ACAD] — [HIPAA Expert Determination & re-ID risk](https://www.accountablehq.com/post/expert-determination-method-under-hipaa-best-practices-to-minimize-re-identification-risk) · [Direct vs indirect identifiers](https://www.accountablehq.com/post/hipaa-individual-identifiers-direct-vs-indirect-and-how-to-de-identify-data) · [Censinet: assessing re-ID risk in PHI](https://censinet.com/perspectives/assess-re-identification-risks-phi) · [JHU: disclosure risk & quasi-identifiers](https://guides.library.jhu.edu/protecting_identifiers/definitions)
- Court-defensibility / Vaughn / exemption coding [GOV] — [DOJ OIP redaction code explanations](https://www.justice.gov/oip/page/file/1176466/dl) · [DigitalWarRoom: why redaction logs matter](https://www.digitalwarroom.com/blog/why-redaction-logs-matter) · [AI-Redact: FOIA exemptions & best practices](https://ai-redact.com/blog/foia-redaction-guide) · [ComplyLoft: defensible audit trails](https://www.complyloft.com/redaction/audit-trail)
- Verification / human oversight [ACAD/VENDOR] — [arXiv 2512.02774: AI redaction in UK public authorities](https://arxiv.org/pdf/2512.02774) · [CivicPlus: why AI isn't enough](https://www.civicplus.com/blog/rr/avoiding-redaction-mistakes-with-ai/) · [Reveal: eDiscovery redactions at scale 2026](https://www.revealdata.com/blog/ediscovery-redactions-at-scale-ais-role-in-2026) · [SecureRedact: court-defensible standards](https://www.secureredact.ai/articles/ai-redaction-court-defensible-standards)
- Pseudonymization [VENDOR] — [Re-Doc: redaction vs anonymization vs pseudonymization](https://re-doc.com/blog/redaction-vs-anonymization-vs-pseudonymization-2026-guide) · [IRI: reversible/irreversible tokenization](https://www.iri.com/solutions/data-masking/static-data-masking/pseudonymize)
