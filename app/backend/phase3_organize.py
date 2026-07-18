"""Phase 3 — ORGANIZE.

inventory -> understand (Gemma, cached) -> propose names/tree -> apply
(crash-safe intent journal) -> UNDO.

Safety design:
  * Nothing moves until the user clicks Apply.
  * Every op writes a journal entry (fsync'd) BEFORE the move, flips to
    committed AFTER. On restart, incomplete ops are reconciled.
  * Same-volume os.replace only (atomic). Cross-volume = out of MVP scope.
  * UNDO replays the journal in reverse.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import time
from pathlib import Path

import fitz  # PyMuPDF

from contracts import FileProposal, OrganizePlan, JournalEntry
import gemma


SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "AppData",
             "$RECYCLE.BIN", "System Volume Information"}
TEXT_EXTS = {".pdf", ".docx", ".txt", ".md", ".rtf"}
SHEET_EXTS = {".xlsx", ".csv"}
IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


# ---------------------------------------------------------------------------
# 1. Inventory
# ---------------------------------------------------------------------------

def quick_hash(fp: Path) -> str:
    """size + first/last 64KB — cheap near-unique id without full read."""
    try:
        size = fp.stat().st_size
        h = hashlib.sha1(str(size).encode())
        with open(fp, "rb") as f:
            h.update(f.read(65536))
            if size > 65536:
                f.seek(-65536, os.SEEK_END)
                h.update(f.read(65536))
        return h.hexdigest()[:16]
    except Exception:
        return ""


def inventory(root: str, limit=500) -> list[Path]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.startswith("."):
                continue
            files.append(Path(dirpath) / fn)
            if len(files) >= limit:
                return files
    return files


# ---------------------------------------------------------------------------
# 2. Cheap signature -> Gemma classification (cached by quick-hash)
# ---------------------------------------------------------------------------

def signature(fp: Path) -> tuple[str, list[bytes]]:
    """Return (text_snippet, [image_bytes]) — the minimum for the model to
    classify without loading the whole file."""
    ext = fp.suffix.lower()
    try:
        if ext == ".pdf":
            doc = fitz.open(fp)
            txt = doc[0].get_text()[:1500] if len(doc) else ""
            imgs = []
            if len(txt.strip()) < 40 and len(doc):  # scanned -> give the model a picture
                pix = doc[0].get_pixmap(dpi=110)
                imgs = [pix.tobytes("png")]
            doc.close()
            return f"[PDF] {fp.name}\n{txt}", imgs
        if ext in {".txt", ".md", ".csv"}:
            return f"[{ext}] {fp.name}\n" + fp.read_text(encoding="utf-8", errors="ignore")[:1500], []
        if ext == ".docx":
            return f"[DOCX] {fp.name}\n" + _docx_text(fp)[:1500], []
        if ext in IMG_EXTS:
            from PIL import Image
            im = Image.open(fp).convert("RGB")
            im.thumbnail((640, 640))
            buf = io.BytesIO(); im.save(buf, "PNG")
            return f"[IMAGE] {fp.name}", [buf.getvalue()]
    except Exception:
        pass
    return f"[{ext}] {fp.name}", []


def _docx_text(fp: Path) -> str:
    try:
        import zipfile, xml.etree.ElementTree as ET
        with zipfile.ZipFile(fp) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
        return re.sub(r"<[^>]+>", " ", xml)
    except Exception:
        return ""


CLASSIFY_PROMPT = (
    "You are a file-organization assistant. Given a file's name and a snippet of "
    "its content, classify it. Return ONLY JSON:\n"
    '{"doc_type":"invoice|contract|report|resume|receipt|letter|photo|statement|'
    'presentation|spreadsheet|note|other","category":"Finance|Legal|Work|Personal|'
    'Medical|Media|Other","topic":"2-4 word subject","entity":"company or person '
    'or empty","doc_date":"YYYY-MM-DD or empty","descriptor":"short-kebab-name",'
    '"confidence":0.0}'
)


def classify(fp: Path, model: str, cache: dict) -> dict:
    qh = quick_hash(fp)
    if qh and qh in cache:
        return cache[qh]
    snip, imgs = signature(fp)
    prompt = CLASSIFY_PROMPT + f"\n\nFILE:\n{snip}"
    try:
        data = gemma.generate_json(prompt, model=model, images=imgs or None,
                                   num_predict=300, timeout=180)
    except gemma.GemmaError:
        data = {"doc_type": "other", "category": "Other", "topic": "",
                "entity": "", "doc_date": "", "descriptor": fp.stem[:30],
                "confidence": 0.0}
    data["_qh"] = qh
    if qh:
        cache[qh] = data
    return data


# ---------------------------------------------------------------------------
# 3. Propose — code-enforced naming template (Gemma supplies descriptor only)
# ---------------------------------------------------------------------------

def sanitize(s: str, maxlen=40) -> str:
    s = re.sub(r"[^\w\s-]", "", s).strip().lower()
    s = re.sub(r"[\s_]+", "-", s)
    return s[:maxlen].strip("-") or "untitled"


def build_plan(root: str, model: str, limit=200) -> OrganizePlan:
    files = inventory(root, limit)
    cache: dict = {}
    proposals: list[FileProposal] = []
    used: set[str] = set()
    tree: dict = {}
    for fp in files:
        meta = classify(fp, model, cache)
        cat = meta.get("category", "Other") or "Other"
        date = meta.get("doc_date", "") or ""
        dtype = meta.get("doc_type", "other") or "other"
        desc = sanitize(meta.get("descriptor") or fp.stem)
        prefix = (date + "_") if re.match(r"\d{4}-\d{2}-\d{2}", date) else ""
        new_name = f"{prefix}{sanitize(dtype,16)}_{desc}{fp.suffix.lower()}"
        # de-dupe within the target category
        base, i = new_name, 1
        while (cat + "/" + new_name) in used:
            stem = base.rsplit(".", 1)[0]
            new_name = f"{stem}-{i}{fp.suffix.lower()}"
            i += 1
        used.add(cat + "/" + new_name)
        dst = str(Path(root) / "_Organized" / cat / new_name)
        tree.setdefault(cat, 0)
        tree[cat] += 1
        proposals.append(FileProposal(
            src=str(fp), dst=dst, old_name=fp.name, new_name=new_name,
            category=cat, doc_type=dtype, topic=meta.get("topic", ""),
            reason=f"{dtype} · {meta.get('topic','')}".strip(" ·"),
            confidence=float(meta.get("confidence", 0.5) or 0.5),
            quick_hash=meta.get("_qh", ""),
        ))
    proposals.sort(key=lambda p: p.confidence)  # low-confidence first for review
    return OrganizePlan(root=root, proposals=proposals, tree_preview=tree)


# ---------------------------------------------------------------------------
# 4. Apply — crash-safe intent journal
# ---------------------------------------------------------------------------

def _fsync_write(path: Path, obj) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)
        f.flush()
        os.fsync(f.fileno())


def apply_plan(plan: OrganizePlan, journal_path: str) -> dict:
    entries = []
    moved = 0
    skipped = []
    for p in plan.proposals:
        if p.excluded:
            continue
        src, dst = Path(p.src), Path(p.dst)
        if not src.exists():
            skipped.append({"src": p.src, "why": "source gone"})
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        # collision suffix
        if dst.exists():
            k = 1
            while dst.with_stem(f"{dst.stem}-{k}").exists():
                k += 1
            dst = dst.with_stem(f"{dst.stem}-{k}")
        # same-volume only (MVP)
        if src.drive.lower() != dst.drive.lower():
            skipped.append({"src": p.src, "why": "cross-volume (out of MVP scope)"})
            continue
        entry = {"op": "move", "src": str(src), "dst": str(dst),
                 "hash": p.quick_hash, "ts": _now(), "committed": False}
        entries.append(entry)
        _fsync_write(Path(journal_path), entries)   # intent BEFORE the move
        try:
            os.replace(src, dst)                     # atomic on same volume
            entry["committed"] = True
            _fsync_write(Path(journal_path), entries)
            moved += 1
        except PermissionError:
            skipped.append({"src": p.src, "why": "file locked/open"})
            entries.pop()
            _fsync_write(Path(journal_path), entries)
        except Exception as e:
            skipped.append({"src": p.src, "why": str(e)})
            entries.pop()
            _fsync_write(Path(journal_path), entries)
    return {"moved": moved, "skipped": skipped, "journal": journal_path,
            "map": [{"from": e["src"], "to": e["dst"]} for e in entries if e["committed"]]}


def undo(journal_path: str) -> dict:
    """Replay committed moves in reverse."""
    p = Path(journal_path)
    if not p.exists():
        return {"restored": 0, "error": "no journal"}
    entries = json.loads(p.read_text())
    restored, failed = 0, []
    for e in reversed(entries):
        if not e.get("committed"):
            continue
        src, dst = Path(e["dst"]), Path(e["src"])   # reverse
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.exists():
                os.replace(src, dst)
                restored += 1
        except Exception as ex:
            failed.append({"file": str(src), "why": str(ex)})
    return {"restored": restored, "failed": failed}


def reconcile(journal_path: str) -> dict:
    """On startup: roll back any move that was journaled but not committed."""
    p = Path(journal_path)
    if not p.exists():
        return {"rolled_back": 0}
    try:
        entries = json.loads(p.read_text())
    except Exception:
        return {"rolled_back": 0}
    rb = 0
    for e in entries:
        if e.get("committed"):
            continue
        src, dst = Path(e["src"]), Path(e["dst"])
        if dst.exists() and not src.exists():   # move happened, flag didn't flip
            try:
                os.replace(dst, src)
                rb += 1
            except Exception:
                pass
    return {"rolled_back": rb}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")
