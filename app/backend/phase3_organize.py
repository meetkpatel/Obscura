"""Phase 3 — ORGANIZE.

Browse -> inventory (with duplicate detection) -> understand (Gemma, first page)
-> propose a healthcare-optimized taxonomy + naming -> apply (crash-safe journal)
-> UNDO.

Safety design:
  * Nothing moves until the user clicks Apply.
  * NEVER deletes. Duplicates are MOVED to a _Duplicates_ForReview folder, so a
    mistake is undoable.
  * Every op writes a journal entry (fsync'd) BEFORE the move, flips to committed
    AFTER. On restart, incomplete ops are reconciled. UNDO replays in reverse.
  * Same-volume os.replace only (atomic).
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import string
import sys
import time
from pathlib import Path

import fitz  # PyMuPDF

from contracts import (FileProposal, OrganizePlan, DuplicateGroup, DirEntry,
                       DirListing)
import gemma
import throttle

IS_WIN = sys.platform.startswith("win")

SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "AppData",
             "$RECYCLE.BIN", "System Volume Information", "Windows",
             "Program Files", "Program Files (x86)", "ProgramData", ".cache",
             "_Organized", "_Duplicates_ForReview"}
IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}


# ---------------------------------------------------------------------------
# 0. Directory browsing (in-app file explorer — no fragile native dialog)
# ---------------------------------------------------------------------------

def list_drives() -> list[str]:
    if not IS_WIN:
        return ["/"]
    drives = []
    try:
        from ctypes import windll
        bits = windll.kernel32.GetLogicalDrives()
        for i, letter in enumerate(string.ascii_uppercase):
            if bits & (1 << i):
                drives.append(f"{letter}:\\")
    except Exception:
        drives = ["C:\\"]
    return drives


def _shortcuts() -> list[DirEntry]:
    home = Path.home()
    out = []
    for name, p in [("Desktop", home / "Desktop"), ("Documents", home / "Documents"),
                    ("Downloads", home / "Downloads"), ("Home", home)]:
        if p.exists():
            out.append(DirEntry(name=name, path=str(p)))
    return out


def browse(path: str | None) -> DirListing:
    """List subfolders (+ file count) of a path so the UI can navigate. If no
    path, return drives + shortcuts (the 'This PC' view)."""
    if not path:
        return DirListing(path="", drives=list_drives(), shortcuts=_shortcuts())
    p = Path(path)
    if not p.exists() or not p.is_dir():
        return DirListing(path=path, parent=None, drives=list_drives(),
                          shortcuts=_shortcuts())
    dirs, fcount = [], 0
    try:
        for entry in os.scandir(p):
            try:
                if entry.is_dir(follow_symlinks=False):
                    if entry.name in SKIP_DIRS or entry.name.startswith("."):
                        continue
                    dirs.append(DirEntry(name=entry.name, path=entry.path))
                elif entry.is_file(follow_symlinks=False):
                    fcount += 1
            except OSError:
                continue
    except PermissionError:
        pass
    dirs.sort(key=lambda d: d.name.lower())
    parent = str(p.parent) if p.parent != p else None
    return DirListing(path=str(p), parent=parent, dirs=dirs, file_count=fcount,
                      drives=list_drives(), shortcuts=_shortcuts())


# ---------------------------------------------------------------------------
# 0b. Taxonomy map — understand the EXISTING structure first (fast, free)
# ---------------------------------------------------------------------------

def map_taxonomy(root: str, max_dirs=400) -> dict:
    """Deterministic scan of the existing folder tree: per top-level area, count
    files and the dominant extensions. Free (no model). This is step 1 — know the
    lay of the land before proposing changes."""
    rootp = Path(root)
    areas: dict[str, dict] = {}
    total_files, total_dirs, dirs_seen = 0, 0, 0
    for dirpath, dirnames, filenames in os.walk(rootp):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        dirs_seen += 1
        if dirs_seen > max_dirs:
            break
        rel = Path(dirpath).relative_to(rootp)
        area = rel.parts[0] if rel.parts else "(root)"
        a = areas.setdefault(area, {"files": 0, "exts": {}})
        for fn in filenames:
            if fn.startswith("."):
                continue
            total_files += 1
            a["files"] += 1
            ext = Path(fn).suffix.lower() or "(none)"
            a["exts"][ext] = a["exts"].get(ext, 0) + 1
        total_dirs += len(dirnames)
    # top exts per area
    out_areas = []
    for name, a in sorted(areas.items(), key=lambda kv: -kv[1]["files"]):
        top = sorted(a["exts"].items(), key=lambda kv: -kv[1])[:5]
        out_areas.append({"area": name, "files": a["files"],
                          "top_types": [f"{e} ({c})" for e, c in top]})
    return {"root": str(rootp), "total_files": total_files,
            "total_areas": len(areas), "areas": out_areas[:40],
            "truncated": dirs_seen > max_dirs}


# ---------------------------------------------------------------------------
# 1. Inventory + duplicate detection
# ---------------------------------------------------------------------------

def quick_hash(fp: Path) -> str:
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


def full_sha(fp: Path) -> str:
    try:
        h = hashlib.sha256()
        with open(fp, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return ""


def inventory(root: str, limit=500) -> list[Path]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            if fn.startswith("."):
                continue
            files.append(Path(dirpath) / fn)
            if len(files) >= limit:
                return files
    return files


def find_duplicates(files: list[Path]) -> tuple[list[DuplicateGroup], set[str]]:
    """Exact-duplicate detection: group by size, then full SHA-256 on same-size
    groups (so we only hash real candidates). Returns (groups, set-of-dup-paths).
    Keeps the file with the shortest path / earliest mtime as the original."""
    by_size: dict[int, list[Path]] = {}
    for fp in files:
        try:
            by_size.setdefault(fp.stat().st_size, []).append(fp)
        except OSError:
            continue
    groups, dup_paths = [], set()
    for size, group in by_size.items():
        if len(group) < 2 or size == 0:
            continue
        by_hash: dict[str, list[Path]] = {}
        for fp in group:
            s = full_sha(fp)
            if s:
                by_hash.setdefault(s, []).append(fp)
        for sha, fps in by_hash.items():
            if len(fps) < 2:
                continue
            fps.sort(key=lambda p: (len(str(p)), str(p)))  # keep shortest path
            keep = fps[0]
            dups = fps[1:]
            for d in dups:
                dup_paths.add(str(d))
            groups.append(DuplicateGroup(sha=sha[:16], size=size, keep=str(keep),
                                         duplicates=[str(d) for d in dups]))
    return groups, dup_paths


# ---------------------------------------------------------------------------
# 2. Understand — first page -> Gemma classification (cached)
# ---------------------------------------------------------------------------

def signature(fp: Path) -> tuple[str, list[bytes]]:
    ext = fp.suffix.lower()
    try:
        if ext == ".pdf":
            doc = fitz.open(fp)
            txt = doc[0].get_text()[:1800] if len(doc) else ""
            imgs = []
            if len(txt.strip()) < 40 and len(doc):  # scanned -> vision
                pix = doc[0].get_pixmap(dpi=110)
                imgs = [pix.tobytes("png")]
            doc.close()
            return f"[PDF] {fp.name}\n{txt}", imgs
        if ext in {".txt", ".md", ".csv", ".rtf"}:
            return f"[{ext}] {fp.name}\n" + fp.read_text(encoding="utf-8", errors="ignore")[:1800], []
        if ext == ".docx":
            return f"[DOCX] {fp.name}\n" + _docx_text(fp)[:1800], []
        if ext in IMG_EXTS:
            from PIL import Image
            im = Image.open(fp).convert("RGB"); im.thumbnail((720, 720))
            buf = io.BytesIO(); im.save(buf, "PNG")
            return f"[IMAGE] {fp.name}", [buf.getvalue()]
    except Exception:
        pass
    return f"[{ext}] {fp.name}", []


def _docx_text(fp: Path) -> str:
    try:
        import zipfile
        with zipfile.ZipFile(fp) as z:
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
        return re.sub(r"<[^>]+>", " ", xml)
    except Exception:
        return ""


# Healthcare document taxonomy -> (category, subcategory)
HC_DOCTYPES = {
    "visit-note": ("Clinical", "Visit Notes"),
    "progress-note": ("Clinical", "Visit Notes"),
    "lab-result": ("Clinical", "Lab Results"),
    "imaging-report": ("Clinical", "Imaging & Radiology"),
    "pathology-report": ("Clinical", "Lab Results"),
    "medication-list": ("Clinical", "Medications"),
    "prescription": ("Clinical", "Medications"),
    "referral": ("Clinical", "Referrals & Consults"),
    "consult-note": ("Clinical", "Referrals & Consults"),
    "discharge-summary": ("Clinical", "Discharge & Summaries"),
    "immunization": ("Clinical", "Immunizations"),
    "insurance-card": ("Administrative", "Insurance"),
    "eob": ("Administrative", "Insurance"),
    "billing-statement": ("Administrative", "Billing & Claims"),
    "claim": ("Administrative", "Billing & Claims"),
    "consent-form": ("Administrative", "Consents & Forms"),
    "intake-form": ("Administrative", "Consents & Forms"),
    "correspondence": ("Administrative", "Correspondence"),
    "other": ("Administrative", "Other"),
}

HC_PROMPT = (
    "You are a medical records organizer. From the file name and its first-page "
    "text, classify the document for a clinic's filing system. Return ONLY JSON:\n"
    '{"doc_type":"visit-note|progress-note|lab-result|imaging-report|pathology-report|'
    'medication-list|prescription|referral|consult-note|discharge-summary|immunization|'
    'insurance-card|eob|billing-statement|claim|consent-form|intake-form|correspondence|'
    'other","patient":"Last-First or empty if none","provider":"name or empty",'
    '"doc_date":"YYYY-MM-DD or empty","descriptor":"3-5 word kebab summary",'
    '"confidence":0.0}'
)

GEN_PROMPT = (
    "You are a file-organization assistant. From the file name and a content "
    "snippet, classify it. Return ONLY JSON:\n"
    '{"doc_type":"invoice|contract|report|resume|receipt|letter|photo|statement|'
    'presentation|spreadsheet|note|other","category":"Finance|Legal|Work|Personal|'
    'Medical|Media|Other","patient":"","doc_date":"YYYY-MM-DD or empty",'
    '"descriptor":"short-kebab-name","confidence":0.0}'
)


def classify(fp: Path, model: str, cache: dict, profile: str) -> dict:
    qh = quick_hash(fp)
    if qh and qh in cache:
        return cache[qh]
    snip, imgs = signature(fp)
    prompt = (HC_PROMPT if profile == "healthcare" else GEN_PROMPT) + f"\n\nFILE:\n{snip}"
    try:
        data = gemma.generate_json(prompt, model=model, images=imgs or None,
                                   num_predict=300, timeout=180)
    except gemma.GemmaError:
        data = {"doc_type": "other", "descriptor": fp.stem[:30], "confidence": 0.0}
    data["_qh"] = qh
    if qh:
        cache[qh] = data
    return data


# ---------------------------------------------------------------------------
# 3. Propose — healthcare-optimized folders + searchable naming
# ---------------------------------------------------------------------------

def sanitize(s: str, maxlen=40) -> str:
    s = re.sub(r"[^\w\s-]", "", (s or "")).strip()
    s = re.sub(r"[\s_]+", "-", s)
    return s[:maxlen].strip("-")


def _clean_date(date: str) -> str:
    """Extract just a YYYY-MM-DD from a possibly-messy model date field."""
    m = re.search(r"(\d{4}-\d{2}-\d{2})", date or "")
    return m.group(1) if m else ""


def _place(meta: dict, profile: str) -> tuple[str, str, str]:
    """Return (category, subcategory, new_name) from classified metadata.
    Every component is sanitized so filenames are always clean + searchable."""
    dtype = sanitize((meta.get("doc_type") or "other").lower(), 20) or "other"
    date = _clean_date(meta.get("doc_date"))
    desc = sanitize(meta.get("descriptor"), 40) or "document"
    if profile == "healthcare":
        cat, sub = HC_DOCTYPES.get((meta.get("doc_type") or "other").lower(),
                                   ("Administrative", "Other"))
        patient = sanitize(meta.get("patient"), 30)
        parts = [p for p in [date, patient, dtype, desc] if p]   # DATE_Patient_Type_desc
        return cat, sub, "_".join(parts)
    cat = meta.get("category", "Other") or "Other"
    parts = [p for p in [date, dtype, desc] if p]
    return cat, "", "_".join(parts)


def build_plan(root: str, model: str, profile="healthcare", limit=200,
               gate: "throttle.Gate | None" = None) -> OrganizePlan:
    files = inventory(root, limit)
    dup_groups, dup_paths = find_duplicates(files)
    cache: dict = {}
    proposals: list[FileProposal] = []
    used: set[str] = set()
    tree: dict = {}
    for fp in files:
        if gate and not gate.wait():   # stay polite during a big scan
            break
        is_dup = str(fp) in dup_paths
        meta = classify(fp, model, cache, profile) if not is_dup else {"doc_type": "duplicate", "confidence": 1.0}
        if is_dup:
            dst = str(Path(root) / "_Duplicates_ForReview" / fp.name)
            proposals.append(FileProposal(
                src=str(fp), dst=dst, old_name=fp.name, new_name=fp.name,
                category="_Duplicates_ForReview", doc_type="duplicate",
                reason="Exact copy of another file (same SHA-256). Quarantined, not deleted.",
                confidence=1.0, quick_hash=quick_hash(fp), is_duplicate=True))
            continue
        cat, sub, base_name = _place(meta, profile)
        new_name = base_name + fp.suffix.lower()
        folder = f"{cat}/{sub}".rstrip("/")
        key = folder + "/" + new_name.lower()
        n = 1
        while key in used:
            new_name = base_name + f"-{n}" + fp.suffix.lower()
            key = folder + "/" + new_name.lower()
            n += 1
        used.add(key)
        dst = str(Path(root) / "_Organized" / cat / sub / new_name) if sub \
            else str(Path(root) / "_Organized" / cat / new_name)
        tree.setdefault(folder, 0)
        tree[folder] += 1
        reason_bits = [meta.get("doc_type", ""), meta.get("patient", ""),
                       meta.get("doc_date", "")]
        proposals.append(FileProposal(
            src=str(fp), dst=dst, old_name=fp.name, new_name=new_name,
            category=cat, subcategory=sub, doc_type=meta.get("doc_type", ""),
            patient=meta.get("patient", ""), topic=meta.get("descriptor", ""),
            reason=" · ".join([b for b in reason_bits if b]) or "classified from first page",
            confidence=float(meta.get("confidence", 0.5) or 0.5),
            quick_hash=meta.get("_qh", ""), is_duplicate=False))
    proposals.sort(key=lambda p: (p.is_duplicate, p.confidence))
    conv = ("YYYY-MM-DD_Patient_DocType_description.ext — sorts by date, groups by "
            "patient, and is self-describing so search finds it fast."
            if profile == "healthcare"
            else "YYYY-MM-DD_type_description.ext")
    reason = (_taxonomy_reason(tree, profile, len(dup_groups)))
    return OrganizePlan(root=root, profile=profile, proposals=proposals,
                        tree_preview=tree, duplicates=dup_groups,
                        naming_convention=conv, taxonomy_reason=reason,
                        scanned=len(files), capped=len(files) >= limit, cap=limit)


def _taxonomy_reason(tree: dict, profile: str, n_dupes: int) -> str:
    if profile == "healthcare":
        base = ("Clinical vs. Administrative at the top level mirrors how a chart "
                "is used at the point of care: clinicians reach for Visit Notes, "
                "Labs, Imaging, Medications; front-office staff reach for Insurance, "
                "Billing, Consents. Every file name starts with the date and patient "
                "so chronological browsing and name search both work.")
    else:
        base = ("Grouped by document category so related files live together; "
                "names start with the date for chronological browsing.")
    if n_dupes:
        base += f" Found {n_dupes} set(s) of exact duplicates — quarantined for review, never deleted."
    return base


# ---------------------------------------------------------------------------
# 4. Apply — crash-safe intent journal (moves only; never deletes)
# ---------------------------------------------------------------------------

def _fsync_write(path: Path, obj) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)
        f.flush()
        os.fsync(f.fileno())


def _move_one(p: FileProposal, entries: list, journal_path: str) -> tuple[bool, dict | None]:
    """Move a single proposal, journaled. Returns (moved, skip_info)."""
    src, dst = Path(p.src), Path(p.dst)
    if not src.exists():
        return False, {"src": p.src, "why": "source gone"}
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        k = 1
        while dst.with_stem(f"{dst.stem}-{k}").exists():
            k += 1
        dst = dst.with_stem(f"{dst.stem}-{k}")
    if src.drive.lower() != dst.drive.lower():
        return False, {"src": p.src, "why": "cross-volume (out of scope)"}
    entry = {"op": "move", "src": str(src), "dst": str(dst),
             "hash": p.quick_hash, "ts": _now(), "committed": False}
    entries.append(entry)
    _fsync_write(Path(journal_path), entries)      # intent BEFORE the move
    try:
        os.replace(src, dst)
        entry["committed"] = True
        _fsync_write(Path(journal_path), entries)
        return True, None
    except PermissionError:
        entries.pop(); _fsync_write(Path(journal_path), entries)
        return False, {"src": p.src, "why": "file locked/open"}
    except Exception as e:
        entries.pop(); _fsync_write(Path(journal_path), entries)
        return False, {"src": p.src, "why": str(e)}


def apply_plan(plan: OrganizePlan, journal_path: str) -> dict:
    """Synchronous apply (small folders / 'now' mode)."""
    entries, moved, skipped = [], 0, []
    for p in plan.proposals:
        if p.excluded:
            continue
        ok, skip = _move_one(p, entries, journal_path)
        if ok:
            moved += 1
        elif skip:
            skipped.append(skip)
    return {"moved": moved, "skipped": skipped, "journal": journal_path,
            "map": [{"from": e["src"], "to": e["dst"]} for e in entries if e["committed"]]}


# --- Background, throttled, idle-aware apply job -------------------------------
import threading

_JOB: dict = {"thread": None, "gate": None, "total": 0, "done": 0, "moved": 0,
              "skipped": [], "state": "idle", "journal": ""}


def _apply_worker(plan: OrganizePlan, journal_path: str, mode: str):
    gate = throttle.Gate(mode)
    _JOB.update(gate=gate, total=len([p for p in plan.proposals if not p.excluded]),
                done=0, moved=0, skipped=[], state="running", journal=journal_path)
    throttle.set_low_priority()
    entries = []
    try:
        for p in plan.proposals:
            if p.excluded:
                continue
            if not gate.wait():          # cancelled
                _JOB["state"] = "cancelled"
                break
            ok, skip = _move_one(p, entries, journal_path)
            _JOB["done"] += 1
            if ok:
                _JOB["moved"] += 1
            elif skip:
                _JOB["skipped"].append(skip)
        else:
            _JOB["state"] = "done"
    finally:
        throttle.restore_priority()
        if _JOB["state"] not in ("cancelled", "done"):
            _JOB["state"] = "done"


def start_apply(plan: OrganizePlan, journal_path: str, mode="eco") -> dict:
    if _JOB["thread"] and _JOB["thread"].is_alive():
        return {"error": "a reorg is already running"}
    t = threading.Thread(target=_apply_worker, args=(plan, journal_path, mode), daemon=True)
    _JOB["thread"] = t
    t.start()
    return {"started": True, "mode": mode,
            "total": len([p for p in plan.proposals if not p.excluded])}


def apply_job_status() -> dict:
    g = _JOB.get("gate")
    snap = g.snapshot() if g else {}
    return {"state": _JOB["state"], "done": _JOB["done"], "total": _JOB["total"],
            "moved": _JOB["moved"], "skipped": len(_JOB["skipped"]), "gate": snap}


def pause_job():
    if _JOB.get("gate"): _JOB["gate"].paused = True
    return apply_job_status()


def resume_job():
    if _JOB.get("gate"): _JOB["gate"].paused = False
    return apply_job_status()


def cancel_job():
    if _JOB.get("gate"): _JOB["gate"].cancelled = True
    return apply_job_status()


def undo(journal_path: str) -> dict:
    p = Path(journal_path)
    if not p.exists():
        return {"restored": 0, "error": "no journal"}
    entries = json.loads(p.read_text())
    restored, failed = 0, []
    for e in reversed(entries):
        if not e.get("committed"):
            continue
        src, dst = Path(e["dst"]), Path(e["src"])
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.exists():
                os.replace(src, dst)
                restored += 1
        except Exception as ex:
            failed.append({"file": str(src), "why": str(ex)})
    return {"restored": restored, "failed": failed}


def reconcile(journal_path: str) -> dict:
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
        if dst.exists() and not src.exists():
            try:
                os.replace(dst, src); rb += 1
            except Exception:
                pass
    return {"rolled_back": rb}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")
