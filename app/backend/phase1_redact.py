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

from contracts import Box, DetectResult
import gemma


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


REGEX_RULES: list[tuple[str, str, str]] = [
    # (category, label, pattern)
    ("gov_id", "SSN", r"\b\d{3}-\d{2}-\d{4}\b"),
    ("contact", "email", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ("contact", "phone", r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    ("date", "date", r"\b(?:0?[1-9]|1[0-2])[/\-.](?:0?[1-9]|[12]\d|3[01])[/\-.](?:19|20)\d{2}\b"),
    ("financial", "credit card", r"\b(?:\d[ -]?){13,16}\b"),
    ("contact", "ZIP", r"\b\d{5}(?:-\d{4})?\b"),
]


def regex_hits(text: str) -> list[dict]:
    hits = []
    for cat, label, pat in REGEX_RULES:
        for m in re.finditer(pat, text):
            s = m.group(0)
            if label == "credit card" and not _luhn(s):
                continue
            hits.append({"category": cat, "label": label, "text": s.strip()})
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


def ground_text_boxes(hits: list[dict], words: list[dict], pad_frac=0.06) -> list[Box]:
    """Map each regex/string hit to exact OCR word boxes (the minimal consecutive
    same-line span whose concatenation contains the hit). Returns pixel boxes —
    no model-grid drift, and no cross-line mega-boxes."""
    boxes: list[Box] = []
    claimed: set[tuple[str, int]] = set()  # (text, start_word_idx) — dedupe
    for hit in hits:
        target = re.sub(r"\s+", "", hit["text"]).lower()
        if not target:
            continue
        for i in range(len(words)):
            acc, matched = "", []
            for j in range(i, min(i + 8, len(words))):
                if matched and not _same_line(matched[-1], words[j]):
                    break  # never span lines
                acc += re.sub(r"\s+", "", words[j]["text"]).lower()
                matched.append(words[j])
                if target in acc:
                    if (hit["text"], i) in claimed:
                        break
                    claimed.add((hit["text"], i))
                    x1 = min(w["x1"] for w in matched)
                    y1 = min(w["y1"] for w in matched)
                    x2 = max(w["x2"] for w in matched)
                    y2 = max(w["y2"] for w in matched)
                    padx = int((x2 - x1) * pad_frac) + 2
                    pady = int((y2 - y1) * pad_frac) + 2
                    boxes.append(Box(
                        x1=x1 - padx, y1=y1 - pady, x2=x2 + padx, y2=y2 + pady,
                        category=hit["category"], label=hit["label"],
                        text=hit["text"], confidence=0.99, source="ocr_grounded",
                        reason="Structured identifier matched by deterministic rule.",
                    ))
                    break
                if len(acc) > len(target) + 4:
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

TEXT_ENTITY_PROMPT = (
    "You are a document privacy reviewer. Read the document text below and list "
    "every sensitive personal item that a records officer must redact but that a "
    "simple regex would MISS: full personal names, home/street addresses, employer "
    "or organization names tied to a person, medical conditions, and any phrase "
    "that could re-identify a specific individual.\n"
    "Return ONLY JSON: {\"items\":[{\"text\":\"exact substring copied verbatim from "
    "the document\",\"category\":\"person|address|medical|other\",\"reason\":\"short\"}]}\n"
    "Copy each 'text' value EXACTLY as it appears so it can be found in the page. "
    "If none, return {\"items\":[]}.\n\nDOCUMENT:\n"
)


def gemma_text_entities(full_text: str, words: list[dict], model: str) -> list[Box]:
    """Ask Gemma for sensitive STRINGS (names/addresses/context regex misses),
    then OCR-ground each to exact pixel boxes. No coordinate drift."""
    if not full_text.strip():
        return []
    try:
        data = gemma.generate_json(TEXT_ENTITY_PROMPT + full_text[:6000],
                                   model=model, num_predict=800, timeout=240)
    except gemma.GemmaError:
        return []
    items = data.get("items", []) if isinstance(data, dict) else []
    hits = []
    for it in items:
        t = (it.get("text") or "").strip()
        if 2 <= len(t) <= 80:
            hits.append({"category": it.get("category", "person"),
                         "label": it.get("category", "sensitive"),
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
            category=it.get("category", "other"),
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


def merge(boxes: list[Box], thresh=0.5) -> list[Box]:
    # prefer higher-confidence (ocr_grounded=0.99) boxes on overlap
    boxes = sorted(boxes, key=lambda b: -b.confidence)
    kept: list[Box] = []
    for b in boxes:
        if all(_iou(b, k) < thresh for k in kept):
            kept.append(b)
    return kept


# ---------------------------------------------------------------------------
# Full detect for one page
# ---------------------------------------------------------------------------

def detect_page(img: Image.Image, model: str, use_vision=True,
                use_gemma_text=True) -> DetectResult:
    W, H = img.size
    full_text, words = ocr_words(img)
    hits = regex_hits(full_text)
    boxes = ground_text_boxes(hits, words)          # deterministic PII, exact
    if use_gemma_text:                              # names/addresses/context, OCR-grounded
        boxes += gemma_text_entities(full_text, words, model)
    if use_vision:                                  # signatures/faces only — visual
        boxes += [b for b in gemma_vision_boxes(img, model)
                  if b.category in VISUAL_CATS]
    boxes = merge(boxes)
    # clamp to page
    for b in boxes:
        b.x1, b.y1 = max(0, b.x1), max(0, b.y1)
        b.x2, b.y2 = min(W, b.x2), min(H, b.y2)
    return DetectResult(
        page_width=W, page_height=H, boxes=boxes, full_text=full_text,
        stats={"regex_hits": len(hits), "words": len(words), "boxes": len(boxes)},
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
    """Open the exported PDF, confirm (a) no selectable text layer, and
    (b) OCR of the rendered pages contains none of the redacted strings."""
    doc = fitz.open(out_path)
    selectable = "".join(page.get_text() for page in doc).strip()
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
    doc.close()
    return {
        "has_text_layer": bool(selectable),
        "selectable_chars": len(selectable),
        "residual_hits": residual,
        "passed": (not selectable) and (not residual),
    }
