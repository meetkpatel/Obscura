"""Phase 1 — REDACT.

Pipeline: ingest -> hybrid detect (regex + Gemma vision, OCR-grounded) ->
review -> burn+flatten -> metadata scrub -> verify -> audit.

Design guarantees (from the PRD):
  * Recall bias — proposed boxes are accepted by default.
  * Destroy, don't cover — the output is a flattened raster, image-only PDF,
    with no text layer to copy and no metadata.
  * Coordinates for *text* items come from OCR word boxes (exact pixels), not
    from the model's normalized grid — this kills the "character peeking out of
    the box" failure mode. Model boxes (padded) are used only for visual items
    (signatures, faces, handwriting).
"""
from __future__ import annotations

import io
import re
import json
import subprocess
import tempfile
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

from contracts import Box, DetectResult, coerce_category
import gemma
import presidio_detect


# ---------------------------------------------------------------------------
# Ingest — anything -> a list of page PIL images at a known resolution
# ---------------------------------------------------------------------------

RENDER_DPI = 150


def load_pages(path: str) -> list[Image.Image]:
    p = Path(path)
    ext = p.suffix.lower()
    if ext == ".pdf":
        doc = fitz.open(path)
        pages = []
        for page in doc:
            pix = page.get_pixmap(dpi=RENDER_DPI)
            pages.append(Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB"))
        doc.close()
        return pages
    if ext in (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"):
        return [Image.open(path).convert("RGB")]
    raise ValueError(f"Unsupported input type: {ext}")


def _png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Detect — Pass A: deterministic regex/checksum (high precision, instant)
# ---------------------------------------------------------------------------

def _luhn(num: str) -> bool:
    digits = [int(c) for c in num if c.isdigit()]
    if len(digits) < 13:
        return False
    checksum, parity = 0, len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


# Deterministic, HIGH-PRECISION rules. Names/addresses/orgs are left to the
# Gemma pass (context-dependent). These catch the structured identifiers exactly.
REGEX_RULES: list[tuple[str, str, str]] = [
    # (category, label, pattern)
    ("gov_id", "SSN", r"\b\d{3}-\d{2}-\d{4}\b"),
    ("gov_id", "EIN/Tax ID", r"\b\d{2}-\d{7}\b"),
    ("gov_id", "bar/license no.", r"\b(?:VSB|Bar|License|Lic)\s*#?\s*(\d{3,7})\b"),
    ("contact", "email", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ("contact", "phone", r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    ("address", "P.O. Box", r"\bP\.?\s*O\.?\s*Box\s+\d+\b"),
    ("date", "date", r"\b(?:0?[1-9]|1[0-2])[/\-.](?:0?[1-9]|[12]\d|3[01])[/\-.](?:19|20)\d{2}\b"),
    ("date", "written date", r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+(?:19|20)\d{2}\b"),
    ("financial", "credit card", r"\b(?:\d[ -]?){13,16}\b"),
    ("financial", "account no.", r"\b(?:Account|Acct|Loan|Policy|Deed|Instrument|PRN)\s*#?\.?\s*(\d{4,})\b"),
    # --- HIPAA Safe Harbor healthcare identifiers (45 CFR 164.514(b)(2)) ---
    # NOTE: the label anchors the match but is captured in group(1) so only the
    # VALUE is boxed — the "MRN"/"Member ID" label stays visible.
    ("medical", "medical record no.", r"\b(?:MRN|Medical\s*Record(?:\s*(?:No|Number|#))?)\s*[:#]?\s*([A-Z0-9-]{4,})\b"),
    ("medical", "health plan/member ID", r"\b(?:Member|Beneficiary|Subscriber|Policy|Group|Plan|Insurance)\s*(?:ID|No|Number|#)\.?\s*[:#]?\s*([A-Z0-9-]{4,})\b"),
    ("other", "URL", r"\bhttps?://[^\s]+|\bwww\.[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ("other", "VIN", r"\b[A-HJ-NPR-Z0-9]{17}\b"),
    ("other", "IP address", r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    ("contact", "ZIP", r"\b\d{5}(?:-\d{4})?\b"),
]

# Grounded PII taxonomy — the HIPAA Safe Harbor 18 identifiers
# (45 CFR 164.514(b)(2)(i)(A)-(R)) + NIST SP 800-122 + FOIA b(6)/b(7)(C).
# Drives the Gemma prompt below. Enumerates the healthcare identifiers explicitly
# so a patient record is fully de-identified.
PII_TAXONOMY = (
    "full personal names (patients, providers, relatives, employers, guarantors, "
    "attorneys, notaries, witnesses); complete street addresses INCLUDING number, "
    "street, suite/unit, city, county, and ZIP as ONE span; P.O. boxes; "
    "organization / company / clinic / employer names tied to a person; telephone "
    "and fax numbers; email addresses; Social Security numbers; MEDICAL RECORD "
    "NUMBERS (MRN); HEALTH PLAN / insurance beneficiary, member, subscriber, or "
    "group numbers; financial account, loan, policy, or instrument numbers; "
    "certificate, license, NPI, or DEA numbers; vehicle identifiers (VIN, plate); "
    "device identifiers and serial numbers; web URLs; IP addresses; biometric "
    "identifiers (finger/voice prints); full-face or identifying patient photos; "
    "ALL dates tied to a person (birth, admission, discharge, death, service, "
    "signing); ages over 89; handwritten signatures; and any other unique code or "
    "quasi-identifier combination that could re-identify a specific individual"
)

# The 18 Safe Harbor identifiers (45 CFR 164.514(b)(2)(i)) and how Obscura targets
# each — used for the coverage self-check (technical, not a compliance opinion).
HIPAA_SAFE_HARBOR = [
    ("A", "Names", "Gemma text pass (person/organization)"),
    ("B", "Geographic subdivisions < state (address, city, county, ZIP)", "Gemma addresses + ZIP regex"),
    ("C", "All date elements (except year) + ages > 89", "date regex + Gemma dates (removed in full)"),
    ("D", "Telephone numbers", "phone regex"),
    ("E", "Fax numbers", "phone/fax regex"),
    ("F", "Email addresses", "email regex"),
    ("G", "Social Security numbers", "SSN regex"),
    ("H", "Medical record numbers", "MRN regex + Gemma"),
    ("I", "Health plan beneficiary numbers", "health-plan/member regex + Gemma"),
    ("J", "Account numbers", "account regex + Gemma"),
    ("K", "Certificate / license numbers", "license/bar regex + Gemma"),
    ("L", "Vehicle identifiers & serial numbers", "VIN regex + Gemma"),
    ("M", "Device identifiers & serial numbers", "Gemma text pass"),
    ("N", "Web URLs", "URL regex"),
    ("O", "IP addresses", "IP regex"),
    ("P", "Biometric identifiers", "Gemma text pass"),
    ("Q", "Full-face photos & comparable images", "Gemma vision (faces)"),
    ("R", "Any other unique identifying number/characteristic/code", "Gemma quasi-identifier reasoning"),
]


def regex_hits(text: str) -> list[dict]:
    hits = []
    for cat, label, pat in REGEX_RULES:
        for m in re.finditer(pat, text):
            full = m.group(0)
            if label == "credit card" and not _luhn(full):
                continue
            # If the rule captured a value group, box ONLY that (the label stays
            # visible); otherwise box the whole match.
            value = (m.group(1) if m.groups() else full) or full
            hits.append({"category": cat, "label": label, "text": value.strip()})
    return hits


# ---------------------------------------------------------------------------
# OCR — Tesseract TSV -> word boxes (for grounding text coordinates)
# ---------------------------------------------------------------------------

def ocr_words(img: Image.Image) -> tuple[str, list[dict]]:
    """Return (full_text, [{text,x1,y1,x2,y2}]) via Tesseract TSV."""
    with tempfile.TemporaryDirectory() as td:
        ip = Path(td) / "page.png"
        img.save(ip)
        out = Path(td) / "out"
        try:
            subprocess.run(
                ["tesseract", str(ip), str(out), "--dpi", str(RENDER_DPI),
                 "--psm", "6", "tsv"],
                check=True, capture_output=True, timeout=60,
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return "", []
        tsv = (out.with_suffix(".tsv")).read_text(encoding="utf-8", errors="ignore")

    words, lines = [], []
    for row in tsv.splitlines()[1:]:
        c = row.split("\t")
        if len(c) < 12:
            continue
        txt = c[11].strip()
        if not txt:
            continue
        x, y, w, h = int(c[6]), int(c[7]), int(c[8]), int(c[9])
        words.append({"text": txt, "x1": x, "y1": y, "x2": x + w, "y2": y + h})
        lines.append(txt)
    return " ".join(lines), words


def _same_line(a: dict, b: dict) -> bool:
    """True if two OCR words sit on the same text line (vertical overlap)."""
    ov = min(a["y2"], b["y2"]) - max(a["y1"], b["y1"])
    h = min(a["y2"] - a["y1"], b["y2"] - b["y1"])
    return h > 0 and ov / h > 0.4


def _emit_line_boxes(matched: list[dict], hit: dict, pad_frac: float) -> list[Box]:
    """Split a matched word-run into per-line groups and box each line segment
    (so a wrapped address becomes one box per line, not a mega-box)."""
    out: list[Box] = []
    group: list[dict] = []
    for w in matched:
        if group and not _same_line(group[-1], w):
            out.append(_box_from_words(group, hit, pad_frac))
            group = []
        group.append(w)
    if group:
        out.append(_box_from_words(group, hit, pad_frac))
    return out


def _box_from_words(ws: list[dict], hit: dict, pad_frac: float) -> Box:
    x1 = min(w["x1"] for w in ws); y1 = min(w["y1"] for w in ws)
    x2 = max(w["x2"] for w in ws); y2 = max(w["y2"] for w in ws)
    # Pad to fully cover the glyphs, but CAP it — a proportional pad on a wide
    # value (long URL) would otherwise bleed onto the neighbouring label.
    padx = min(int((x2 - x1) * pad_frac) + 2, 10)
    pady = min(int((y2 - y1) * pad_frac) + 2, 10)
    return Box(x1=x1 - padx, y1=y1 - pady, x2=x2 + padx, y2=y2 + pady,
              category=hit["category"], label=hit["label"], text=hit["text"],
              confidence=0.98, source="ocr_grounded",
              reason=hit.get("reason") or "Matched by deterministic rule.")


def _trim_to_target(matched: list[dict], target: str) -> list[dict]:
    """Drop leading/trailing OCR words that fall OUTSIDE the matched target span.

    Grounding accumulates words from the start of a line, so the value box would
    otherwise swallow a preceding field label ("Phone: (559)…" -> box over
    "Phone:" too). Keep only the words whose characters overlap the target span.
    """
    norm = [re.sub(r"\s+", "", w["text"]).lower() for w in matched]
    pos = "".join(norm).find(target)
    if pos < 0:
        return matched
    start, end = pos, pos + len(target)
    out, cursor = [], 0
    for w, n in zip(matched, norm):
        w0, w1 = cursor, cursor + len(n)
        cursor = w1
        if w1 > start and w0 < end:            # word overlaps [start, end)
            out.append(w)
    return out or matched


def ground_text_boxes(hits: list[dict], words: list[dict], pad_frac=0.06) -> list[Box]:
    """Map each hit string to exact OCR word boxes. Handles multi-line spans
    (wrapped addresses) by emitting one box per line segment. No grid drift.
    Leading/trailing label words are trimmed so only the value is boxed."""
    boxes: list[Box] = []
    claimed: set[tuple[str, int]] = set()
    for hit in hits:
        target = re.sub(r"\s+", "", hit["text"]).lower()
        if len(target) < 2:
            continue
        for i in range(len(words)):
            acc, matched = "", []
            for j in range(i, min(i + 16, len(words))):   # allow long spans (addresses)
                acc += re.sub(r"\s+", "", words[j]["text"]).lower()
                matched.append(words[j])
                if target in acc:
                    if (hit["text"], i) not in claimed:
                        claimed.add((hit["text"], i))
                        tight = _trim_to_target(matched, target)
                        boxes.extend(_emit_line_boxes(tight, hit, pad_frac))
                    break
                if len(acc) > len(target) + 6:
                    break
    return boxes


# ---------------------------------------------------------------------------
# Detect — Pass B: Gemma 4 vision (unstructured / visual items)
# ---------------------------------------------------------------------------

VISION_PROMPT = (
    "You are a document privacy scanner. Look at this document image and detect "
    "every sensitive item a records officer must redact: full personal names, "
    "home/street addresses, handwritten signatures, faces/photos of people, "
    "dates of birth, and account or ID numbers.\n"
    "Return ONLY JSON of the form:\n"
    '{"items":[{"box_2d":[y1,x1,y2,x2],"label":"...","category":"person|address|'
    'signature|face|gov_id|financial|medical|date|other","reason":"short reason"}]}\n'
    "Coordinates are on a 1000x1000 grid relative to the image. If none, return "
    '{"items":[]}.'
)

# Categories we trust the *model* to localize by coordinate (genuinely visual,
# no text to OCR-ground). For everything textual we ask the model for the STRING
# and locate it with OCR — model coordinates on text drift; strings don't.
VISUAL_CATS = {"signature", "face"}

# Broad prompt — used ONLY when Presidio is unavailable, so Gemma still catches
# structured PII + names/addresses on its own (deterministic fallback path).
TEXT_ENTITY_PROMPT = (
    "You are a meticulous records/FOIA redaction officer. Read the document text "
    "below and list EVERY sensitive item that should be redacted. Bias toward "
    "OVER-inclusion — a reviewer removes a false positive with one click, but a "
    "missed item is a breach. Redact these categories:\n"
    f"{PII_TAXONOMY}.\n\n"
    "Rules:\n"
    "- For an address, return the ENTIRE address as one span (e.g. '1100 Confroy "
    "Drive, Suite 1, South Boston, Virginia 24592'), not just the ZIP.\n"
    "- Catch EVERY person name and EVERY company/firm/organization name.\n"
    "- Copy each 'text' value EXACTLY (verbatim substring) so it can be located.\n"
    "- List each distinct occurrence you see.\n"
    "Return ONLY JSON: {\"items\":[{\"text\":\"verbatim substring\",\"category\":"
    "\"person|address|contact|financial|gov_id|date|medical|other\",\"reason\":"
    "\"short\"}]}. If none, {\"items\":[]}.\n\nDOCUMENT:\n"
)

# Narrowed prompt — used when Presidio has ALREADY found the structured PII and
# named entities. Here Gemma does the one job an LLM wins at: spotting the
# re-identifying CONTEXT that a rule/NER engine can't reason about. Names,
# emails, SSNs, phones, addresses, orgs are handled upstream — don't re-list them
# unless they're part of a re-identifying phrase Presidio would miss.
QUASI_ID_PROMPT = (
    "You are a records/FOIA redaction officer doing a SECOND pass. A deterministic "
    "engine has already flagged the obvious identifiers (names, addresses, emails, "
    "phones, SSNs, account and ID numbers, dates). Your job is the subtle layer it "
    "cannot reason about: QUASI-IDENTIFIERS and re-identifying context — phrases "
    "that, in combination, could single out a specific person even with the obvious "
    "identifiers removed.\n"
    "Examples: a unique job title tied to a place ('the only female fire captain in "
    "Dubuque'); a distinctive medical condition or diagnosis; a rare event, case, or "
    "docket description; a relationship that pins an identity ('the plaintiff's "
    "twin brother'); an unusual physical description; a non-standard internal ID, "
    "badge, or reference number the rules missed.\n"
    "Do NOT re-list plain names, addresses, emails, phones, or standard ID numbers — "
    "those are already handled. Only return spans that add re-identification risk.\n"
    "Copy each 'text' value EXACTLY (verbatim substring) so it can be located.\n"
    "Return ONLY JSON: {\"items\":[{\"text\":\"verbatim substring\",\"category\":"
    "\"person|medical|gov_id|financial|other\",\"reason\":\"why it re-identifies\"}]}."
    " If none, {\"items\":[]}.\n\nDOCUMENT:\n"
)


def gemma_text_entities(full_text: str, words: list[dict], model: str,
                        presidio_on: bool = False) -> list[Box]:
    """Ask Gemma for sensitive STRINGS, then OCR-ground each to exact pixel boxes.
    When Presidio ran (`presidio_on`), Gemma is narrowed to quasi-identifier /
    re-identification context; otherwise it does the full broad sweep so nothing
    is missed on the deterministic-fallback path."""
    if not full_text.strip():
        return []
    prompt = QUASI_ID_PROMPT if presidio_on else TEXT_ENTITY_PROMPT
    try:
        data = gemma.generate_json(prompt + full_text[:6000],
                                   model=model, num_predict=800, timeout=240)
    except gemma.GemmaError:
        return []
    items = data.get("items", []) if isinstance(data, dict) else []
    hits = []
    for it in items:
        t = (it.get("text") or "").strip()
        if 2 <= len(t) <= 90:
            cat = coerce_category(it.get("category", "other"))
            hits.append({"category": cat, "label": cat,
                         "text": t, "reason": it.get("reason", "")})
    grounded = ground_text_boxes(hits, words)
    # carry the model's reason onto the grounded box + mark provenance
    for b in grounded:
        b.source = "ocr_grounded"
        b.confidence = 0.85
        for h in hits:
            if h["text"] == b.text and h.get("reason"):
                b.reason = h["reason"]
    return grounded


def gemma_vision_boxes(img: Image.Image, model: str, pad_frac=0.02) -> list[Box]:
    W, H = img.size
    try:
        data = gemma.generate_json(
            VISION_PROMPT, model=model, images=[_png_bytes(img)],
            num_predict=1024, timeout=300,
        )
    except gemma.GemmaError:
        return []
    items = data.get("items", []) if isinstance(data, dict) else []
    boxes: list[Box] = []
    for it in items:
        bb = it.get("box_2d") or it.get("box") or []
        if len(bb) != 4:
            continue
        y1, x1, y2, x2 = bb
        # descale 1000-grid -> pixels
        px1, px2 = sorted([int(x1 / 1000 * W), int(x2 / 1000 * W)])
        py1, py2 = sorted([int(y1 / 1000 * H), int(y2 / 1000 * H)])
        padx = int((px2 - px1) * pad_frac) + 3
        pady = int((py2 - py1) * pad_frac) + 3
        boxes.append(Box(
            x1=px1 - padx, y1=py1 - pady, x2=px2 + padx, y2=py2 + pady,
            category=coerce_category(it.get("category", "other")),
            label=it.get("label", "sensitive"),
            reason=it.get("reason", ""), confidence=0.75, source="gemma_vision",
        ))
    return boxes


# ---------------------------------------------------------------------------
# Merge + dedupe
# ---------------------------------------------------------------------------

def _iou(a: Box, b: Box) -> float:
    ix1, iy1 = max(a.x1, b.x1), max(a.y1, b.y1)
    ix2, iy2 = min(a.x2, b.x2), min(a.y2, b.y2)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    ua = (a.x2 - a.x1) * (a.y2 - a.y1) + (b.x2 - b.x1) * (b.y2 - b.y1) - inter
    return inter / ua if ua else 0.0


def _contained(b: Box, k: Box, frac=0.6) -> bool:
    """True if >frac of b's area lies inside k (b is a near-duplicate/subset)."""
    ix1, iy1 = max(b.x1, k.x1), max(b.y1, k.y1)
    ix2, iy2 = min(b.x2, k.x2), min(b.y2, k.y2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    ab = (b.x2 - b.x1) * (b.y2 - b.y1)
    return ab > 0 and inter / ab > frac


def merge(boxes: list[Box], thresh=0.5) -> list[Box]:
    # keep bigger, higher-confidence boxes first; drop overlaps and near-duplicates
    boxes = sorted(boxes, key=lambda b: (-b.confidence,
                                         -((b.x2 - b.x1) * (b.y2 - b.y1))))
    kept: list[Box] = []
    for b in boxes:
        if any(_iou(b, k) >= thresh or _contained(b, k) for k in kept):
            continue
        kept.append(b)
    return kept


# ---------------------------------------------------------------------------
# Full detect for one page
# ---------------------------------------------------------------------------

def detect_page(img: Image.Image, model: str, use_vision=True,
                use_gemma_text=True, vision_model: str | None = None) -> DetectResult:
    """`model` runs the text-entity reasoning (respects the user's Fast/Quality
    choice). Vision (signatures/faces only) runs on the SAME model by default —
    on an 8GB card, using a different model for vision would force Ollama to
    evict/reload between calls (thrash). Warmup covers the cold-load cost."""
    W, H = img.size
    vision_model = vision_model or model
    full_text, words = ocr_words(img)
    regex = regex_hits(full_text)                   # deterministic floor (works w/o presidio)
    presidio_on = presidio_detect.available()
    presidio = presidio_detect.presidio_hits(full_text) if presidio_on else []
    hits = regex + presidio                         # structured PII + named entities
    boxes = ground_text_boxes(hits, words)          # OCR-ground every hit to pixels
    if use_gemma_text:                              # quasi-identifier / re-id context
        boxes += gemma_text_entities(full_text, words, model, presidio_on=presidio_on)
    # Vision is for signatures/faces. Skip it on text-dense pages (signatures are
    # rare there and it's the slow part) — keeps the 12B path responsive.
    if use_vision and len(full_text) < 800:
        boxes += [b for b in gemma_vision_boxes(img, vision_model)
                  if b.category in VISUAL_CATS]
    boxes = merge(boxes)
    # clamp to page
    for b in boxes:
        b.x1, b.y1 = max(0, b.x1), max(0, b.y1)
        b.x2, b.y2 = min(W, b.x2), min(H, b.y2)
    return DetectResult(
        page_width=W, page_height=H, boxes=boxes, full_text=full_text,
        stats={"regex_hits": len(regex), "presidio_hits": len(presidio),
               "presidio": presidio_on, "words": len(words), "boxes": len(boxes)},
    )


def _text_grounded(vbox: Box, text_boxes: list[Box]) -> bool:
    return any(_iou(vbox, t) > 0.4 for t in text_boxes)


# ---------------------------------------------------------------------------
# Redact — burn filled boxes, flatten, strip metadata, export image-only PDF
# ---------------------------------------------------------------------------

def apply_redactions(img: Image.Image, boxes: list[Box]) -> Image.Image:
    """Return a NEW flattened image with opaque boxes burned into the pixels.
    No layers, no annotations — the data under each box is gone."""
    from PIL import ImageDraw
    out = img.convert("RGB").copy()
    draw = ImageDraw.Draw(out)
    for b in boxes:
        if b.accepted:
            draw.rectangle([b.x1, b.y1, b.x2, b.y2], fill=(0, 0, 0))
    # re-encode through raw pixels -> guarantees a single flat raster, no metadata
    flat = Image.frombytes("RGB", out.size, out.tobytes())
    return flat


def export_pdf(pages: list[Image.Image], out_path: str) -> str:
    """Image-only PDF with metadata scrubbed. Copy-paste yields nothing."""
    clean = [Image.frombytes("RGB", p.size, p.convert("RGB").tobytes()) for p in pages]
    clean[0].save(out_path, save_all=True, append_images=clean[1:], format="PDF")
    # scrub any PDF metadata dictionary
    doc = fitz.open(out_path)
    doc.set_metadata({})
    doc.del_xml_metadata()
    doc.saveIncr()
    doc.close()
    return out_path


# ---------------------------------------------------------------------------
# Verify — re-extract the OUTPUT and assert zero residual sensitive text
# ---------------------------------------------------------------------------

def verify_pdf(out_path: str, expect_gone: list[str]) -> dict:
    """Run the industry-standard redaction validation battery on the OUTPUT file
    (technical QA — not legal advice). Named after the checks documented in
    redaction QA guidance: select-all/copy-paste, interactive text search, OCR
    re-exposure, and metadata/XMP audit.
    """
    doc = fitz.open(out_path)
    checks = []

    # 1. Select-all / copy-paste test — the output must carry no text layer.
    selectable = "".join(page.get_text() for page in doc).strip()
    checks.append({
        "name": "Select-all / copy-paste test",
        "passed": not selectable,
        "detail": ("No selectable text layer — copy-paste yields nothing."
                   if not selectable else f"{len(selectable)} selectable characters remain!"),
    })

    # 2. Interactive text-search test — each redacted string must not be findable.
    search_hits = []
    for page in doc:
        for s in expect_gone:
            if s and len(s) > 2 and page.search_for(s):
                search_hits.append(s)
    search_hits = sorted(set(search_hits))
    checks.append({
        "name": "Interactive text-search test",
        "passed": not search_hits,
        "detail": ("No redacted term is findable by search."
                   if not search_hits else f"{len(search_hits)} redacted term(s) still searchable!"),
    })

    # 3. OCR re-exposure check — re-OCR the rendered pixels; nothing should return.
    residual = []
    for page in doc:
        pix = page.get_pixmap(dpi=RENDER_DPI)
        pimg = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        txt, _ = ocr_words(pimg)
        low = re.sub(r"\s+", "", txt).lower()
        for s in expect_gone:
            t = re.sub(r"\s+", "", s).lower()
            if t and t in low and s not in residual:
                residual.append(s)
    checks.append({
        "name": "OCR re-exposure check",
        "passed": not residual,
        "detail": ("Re-OCR of the redacted pixels recovers none of the redacted text."
                   if not residual else f"{len(residual)} item(s) recovered by OCR!"),
    })

    # 4. Metadata & XMP audit — no author/title/history or XMP stream survives.
    md = doc.metadata or {}
    leftover_md = {k: v for k, v in md.items() if v and k not in ("format", "encryption")}
    try:
        xmp = doc.get_xml_metadata()   # XMP string; "" after scrub
    except Exception:
        xmp = ""
    md_clean = (not leftover_md) and (not xmp)
    checks.append({
        "name": "Metadata & XMP audit",
        "passed": md_clean,
        "detail": ("Document metadata and XMP stream are scrubbed."
                   if md_clean else f"Residual metadata: {list(leftover_md)}"),
    })
    doc.close()

    passed = all(c["passed"] for c in checks)
    return {
        "passed": passed,
        "checks": checks,
        "redacted_count": len(expect_gone),
        # legacy fields kept for the existing UI
        "has_text_layer": bool(selectable),
        "selectable_chars": len(selectable),
        "residual_hits": residual + search_hits,
    }
