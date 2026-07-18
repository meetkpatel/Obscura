"""Obscura backend — one FastAPI app, three phases, zero network egress.

Run:  python -m uvicorn main:app --port 8000   (from app/backend)
Then open http://localhost:8000
"""
from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path

import psutil
from fastapi import FastAPI, UploadFile, File, Body
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import gemma
import hardware
import phase1_redact as p1
import phase2_secure as p2
import phase3_organize as p3
from contracts import Connection, EgressReport, OrganizePlan

app = FastAPI(title="Obscura", docs_url=None, redoc_url=None)

FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
WORK = Path(tempfile.gettempdir()) / "obscura_work"
WORK.mkdir(exist_ok=True)
JOURNAL = str(WORK / "organize_journal.json")

# in-memory demo state (single-user hackathon app)
STATE: dict = {"pages": [], "detect": [], "plan": None, "redacted_pdf": None}


# --------------------------------------------------------------------------
# Health + egress proof (shared spine)
# --------------------------------------------------------------------------

@app.get("/api/health")
def health():
    h = gemma.health()
    h["admin"] = p2.is_admin()
    h["presidio"] = p1.presidio_detect.available()  # deterministic Scan layer on?
    return h


@app.post("/api/warmup")
def warmup(body: dict = Body(default={})):
    """Pre-load a model into VRAM so the FIRST real request isn't slowed by a
    cold load (evicting the other model + loading 12B can take ~15-20s on an
    8GB card). Called when the user picks a model in the UI."""
    model = gemma.QUALITY_MODEL if body.get("quality") else gemma.FAST_MODEL
    try:
        gemma.generate("ok", model=model, num_predict=1, timeout=120)
        return {"ready": True, "model": model}
    except gemma.GemmaError as e:
        return {"ready": False, "model": model, "error": str(e)}


@app.get("/api/hardware")
def hardware_probe():
    """Detect this machine and recommend a Gemma 4 model (offer 12B if capable)."""
    hw = hardware.probe()
    tags = gemma.health()
    # only offer 12B if the hardware can take it AND the model is actually pulled
    hw["twelve_b_present"] = tags.get("quality_present", False)
    hw["e4b_present"] = tags.get("fast_present", False)
    if hw["recommended_model"] == gemma.QUALITY_MODEL and not hw["twelve_b_present"]:
        hw["recommended_model"] = gemma.FAST_MODEL
        hw["reason"] += " (12B not pulled yet — run `ollama pull gemma4:12b-it-qat` to enable.)"
    return hw


@app.get("/api/egress")
def egress() -> EgressReport:
    """Prove nothing leaves: list THIS process tree's remote connections.

    Iterate our OWN processes (me + children) and read each one's connections —
    a process may always inspect itself, so this needs no privileges. The old
    approach enumerated every process on the machine via psutil.net_connections(),
    which requires root on macOS and raised AccessDenied. We only ever cared about
    our own tree anyway. Loopback (Ollama :11434) is allowed; anything else EXTERNAL.
    """
    conns: list[Connection] = []
    external = 0
    me = psutil.Process()
    for p in [me] + me.children(recursive=True):
        try:
            # psutil >=6 renamed Process.connections() -> net_connections()
            reader = getattr(p, "net_connections", None) or p.connections
            pconns = reader(kind="inet")
            pname = p.name()
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            continue
        for c in pconns:
            if not c.raddr:
                continue
            ip = c.raddr.ip
            loop = ip.startswith("127.") or ip == "::1"
            label = "local LLM — allowed" if (loop and c.raddr.port == 11434) \
                else ("local" if loop else "EXTERNAL")
            if label == "EXTERNAL":
                external += 1
            conns.append(Connection(
                pid=p.pid or 0, proc=pname,
                laddr=f"{c.laddr.ip}:{c.laddr.port}" if c.laddr else "",
                raddr=f"{ip}:{c.raddr.port}", is_loopback=loop, label=label))
    return EgressReport(
        external_count=external, connections=conns,
        verdict="0 external connections — the document never left this machine."
        if external == 0 else f"{external} EXTERNAL connection(s) detected!")


# --------------------------------------------------------------------------
# Phase 1 — REDACT
# --------------------------------------------------------------------------

def _img_data_url(pg) -> str:
    import base64
    buf = io.BytesIO(); pg.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _detect_one(i: int, model: str):
    """Detect a single page (i, 0-based) into STATE['detect'][i]. One page at a
    time keeps the small model focused. Falls back to deterministic-only rather
    than failing. Returns (DetectResult, gemma_skipped_bool)."""
    pg = STATE["pages"][i]
    try:
        res = p1.detect_page(pg, model)
        return res, False
    except Exception as e:
        try:
            res = p1.detect_page(pg, model, use_vision=False, use_gemma_text=False)
            return res, True
        except Exception:
            return p1.DetectResult(page_width=pg.size[0], page_height=pg.size[1],
                                   boxes=[], full_text="", stats={"error": str(e)[:120]}), True


@app.post("/api/redact/load")
async def redact_load(file: UploadFile = File(...)):
    """Upload + render pages ONLY (no detection yet). Detection runs per-page,
    on demand, so a small model handles one page at a time."""
    try:
        raw = await file.read()
        src = WORK / f"in_{Path(file.filename).name}"
        src.write_bytes(raw)
        pages = p1.load_pages(str(src))
    except Exception as e:
        return JSONResponse(
            {"error": f"Could not open '{file.filename}': {type(e).__name__}: {e}. "
                      f"Encrypted/unsupported PDFs may need to be re-saved or printed to PDF first."},
            status_code=200)
    STATE["pages"] = pages
    STATE["detect"] = [None] * len(pages)
    return {"page_count": len(pages),
            "pages": [{"image": _img_data_url(pg), "width": pg.size[0], "height": pg.size[1]}
                      for pg in pages]}


@app.post("/api/redact/detect_page")
def redact_detect_page(body: dict = Body(...)):
    """Detect ONE page. body = {index, quality}. Cached in STATE."""
    pages = STATE.get("pages") or []
    i = int(body.get("index", 0))
    if not (0 <= i < len(pages)):
        return JSONResponse({"error": "page index out of range"}, status_code=200)
    model = gemma.QUALITY_MODEL if body.get("quality") else gemma.FAST_MODEL
    res, skipped = _detect_one(i, model)
    STATE["detect"][i] = res
    return {"index": i, "boxes": [b.model_dump() for b in res.boxes],
            "stats": res.stats, "gemma_skipped": skipped,
            "note": ("This page used deterministic detection only (Gemma slow/unavailable)."
                     if skipped else "")}


@app.post("/api/redact/apply")
def redact_apply(body: dict = Body(...)):
    """body = {decisions:{page_index:[bool,...]}, quality:bool}. Any page not yet
    detected is detected now (so nothing ships unredacted). Burn, flatten, scrub, verify."""
    pages = STATE.get("pages") or []
    if not pages:
        return JSONResponse({"error": "no document loaded yet"}, status_code=400)
    decisions = body.get("decisions", {}) if isinstance(body, dict) else {}
    model = gemma.QUALITY_MODEL if body.get("quality") else gemma.FAST_MODEL
    # auto-detect any page the reviewer never opened — recall safety
    auto = []
    for i in range(len(pages)):
        if STATE["detect"][i] is None:
            STATE["detect"][i], _ = _detect_one(i, model)
            auto.append(i + 1)
    results = STATE["detect"]
    redacted, gone = [], []
    for i, (pg, res) in enumerate(zip(pages, results)):
        acc = decisions.get(str(i)) or decisions.get(i) or [b.accepted for b in res.boxes]
        for b, a in zip(res.boxes, acc):
            b.accepted = bool(a)
            if b.accepted and b.text:
                gone.append(b.text)
        redacted.append(p1.apply_redactions(pg, res.boxes))
    out_pdf = str(WORK / "redacted.pdf")
    p1.export_pdf(redacted, out_pdf)
    verify = p1.verify_pdf(out_pdf, gone)
    STATE["redacted_pdf"] = out_pdf
    STATE["verify"] = verify
    STATE["redacted_count"] = len(gone)
    import base64
    previews = []
    for r in redacted:
        buf = io.BytesIO(); r.save(buf, "PNG")
        previews.append("data:image/png;base64," + base64.b64encode(buf.getvalue()).decode())
    return {"verify": verify, "previews": previews,
            "download": "/api/redact/download",
            "redacted_count": len(gone),
            "auto_detected_pages": auto,
            "note": (f"Auto-detected {len(auto)} page(s) you hadn't opened, so nothing "
                     f"ships unredacted." if auto else "")}


@app.get("/api/redact/hipaa")
def hipaa_coverage():
    """HIPAA Safe Harbor (45 CFR 164.514(b)(2)) identifier-coverage self-check.
    TECHNICAL coverage of the app's detection — NOT a legal compliance opinion or
    certification. HIPAA compliance also requires administrative, physical, and
    technical safeguards, workforce training, and (for any cloud vendor) a BAA —
    none of which a redaction tool provides. Obscura's advantage here: it runs
    fully on-device, so PHI never leaves the machine and no cloud-AI BAA is needed.
    If a redacted item was detected on the current document, it is marked found."""
    detected = set()
    for res in (STATE.get("detect") or []):
        if res:
            for b in res.boxes:
                detected.add(b.category)
    # map detected categories -> Safe Harbor items (coarse)
    cat_map = {"A": {"person", "organization"}, "B": {"address", "contact"},
               "C": {"date"}, "D": {"contact"}, "E": {"contact"}, "F": {"contact"},
               "G": {"gov_id"}, "H": {"medical"}, "I": {"medical"}, "J": {"financial"},
               "K": {"gov_id"}, "L": {"other"}, "M": {"other"}, "N": {"other"},
               "O": {"other"}, "P": {"other"}, "Q": {"face", "signature"}, "R": {"other"}}
    items = []
    for code, name, method in p1.HIPAA_SAFE_HARBOR:
        items.append({"code": code, "identifier": name, "detection": method,
                      "found_on_document": bool(cat_map.get(code, set()) & detected)})
    return {
        "standard": "HIPAA Safe Harbor — 45 CFR 164.514(b)(2)(i)",
        "disclaimer": ("Technical detection-coverage self-check, NOT a legal "
                       "compliance certification. De-identification success under "
                       "Safe Harbor also requires no actual knowledge that residual "
                       "data could re-identify an individual; have a qualified "
                       "reviewer / compliance officer confirm. On-device: no PHI "
                       "leaves this machine."),
        "identifiers": items,
        "note_on_dates_zip": ("Obscura REMOVES dates and ZIPs entirely — more "
                              "conservative than Safe Harbor's keep-year / 3-digit-ZIP "
                              "allowances, which is acceptable (removing more is fine)."),
    }


@app.get("/api/redact/report")
def redact_report():
    """Downloadable verification report — the defensibility artifact. Records the
    validation battery result. Technical QA record, not legal advice."""
    v = STATE.get("verify")
    if not v:
        return JSONResponse({"error": "nothing redacted yet"}, status_code=404)
    lines = [
        "OBSCURA — REDACTION VERIFICATION REPORT",
        "(on-device technical QA record — not legal advice)",
        "=" * 52,
        f"Items redacted:        {STATE.get('redacted_count', 0)}",
        f"Overall verification:  {'PASSED' if v['passed'] else 'FAILED'}",
        "",
        "Validation battery:",
    ]
    for c in v.get("checks", []):
        lines.append(f"  [{'PASS' if c['passed'] else 'FAIL'}] {c['name']}")
        lines.append(f"         {c['detail']}")
    lines += ["", "Method: text destroyed at the pixel level (image-only PDF, no",
              "text layer), metadata + XMP scrubbed, output independently re-scanned.",
              "Generated on-device. No document data left this machine."]
    report = "\n".join(lines)
    path = WORK / "verification_report.txt"
    path.write_text(report, encoding="utf-8")
    return FileResponse(str(path), media_type="text/plain",
                        filename="obscura_verification_report.txt")


@app.get("/api/redact/download")
def redact_download():
    p = STATE.get("redacted_pdf")
    if not p or not os.path.exists(p):
        return JSONResponse({"error": "nothing redacted yet"}, status_code=404)
    return FileResponse(p, media_type="application/pdf", filename="redacted.pdf")


# --------------------------------------------------------------------------
# Phase 2 — SECURE
# --------------------------------------------------------------------------

@app.post("/api/secure/scan")
def secure_scan(body: dict = Body(default={})):
    roots = body.get("roots")
    quality = body.get("quality", False)
    model = gemma.QUALITY_MODEL if quality else gemma.FAST_MODEL
    res = p2.run_scan(roots, model, use_gemma=body.get("use_gemma", True))
    return res.model_dump()


# --------------------------------------------------------------------------
# Phase 3 — ORGANIZE
# --------------------------------------------------------------------------

def _resolve_scope(scope: str, path: str | None) -> str | None:
    """scope: folder(uses path) | downloads | home."""
    home = Path.home()
    if scope == "downloads":
        return str(home / "Downloads")
    if scope in ("home", "computer"):
        return str(home)
    return path


@app.post("/api/organize/browse")
def organize_browse(body: dict = Body(default={})):
    """In-app directory browser. body={path} or empty for the 'This PC' view."""
    return p3.browse(body.get("path")).model_dump()


@app.post("/api/organize/taxonomy")
def organize_taxonomy(body: dict = Body(default={})):
    """Step 1 — map the EXISTING folder/file structure (free, no model)."""
    root = _resolve_scope(body.get("scope", "folder"), body.get("path"))
    if not root or not os.path.isdir(root):
        return JSONResponse({"error": f"not a folder: {root}"}, status_code=400)
    return p3.map_taxonomy(root)


@app.post("/api/organize/plan")
def organize_plan(body: dict = Body(...)):
    root = _resolve_scope(body.get("scope", "folder"), body.get("root") or body.get("path"))
    quality = body.get("quality", False)
    profile = body.get("profile", "healthcare")
    if not root or not os.path.isdir(root):
        return JSONResponse({"error": f"not a folder: {root}"}, status_code=400)
    model = gemma.QUALITY_MODEL if quality else gemma.FAST_MODEL
    gate = p3.throttle.Gate(body.get("run_mode", "eco"))   # gentle during a big scan
    plan = p3.build_plan(root, model, profile=profile, limit=body.get("limit", 200), gate=gate)
    STATE["plan"] = plan
    return plan.model_dump()


@app.post("/api/organize/apply")
def organize_apply(body: dict = Body(default={})):
    """Start the reorg as a throttled, idle-aware BACKGROUND job so it never
    fights the user for the machine. Poll /api/organize/apply_status."""
    plan = STATE.get("plan")
    if not plan:
        return JSONResponse({"error": "no plan built yet"}, status_code=400)
    excl = set(body.get("excluded", []))
    for pr in plan.proposals:
        pr.excluded = pr.src in excl
    mode = body.get("run_mode", "eco")   # idle | eco | now
    return p3.start_apply(plan, JOURNAL, mode)


@app.get("/api/organize/apply_status")
def organize_apply_status():
    return p3.apply_job_status()


@app.post("/api/organize/pause")
def organize_pause():
    return p3.pause_job()


@app.post("/api/organize/resume")
def organize_resume():
    return p3.resume_job()


@app.post("/api/organize/cancel")
def organize_cancel():
    return p3.cancel_job()


@app.post("/api/organize/undo")
def organize_undo():
    return p3.undo(JOURNAL)


# --------------------------------------------------------------------------
# Frontend
# --------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index():
    return (FRONTEND / "index.html").read_text(encoding="utf-8")

if FRONTEND.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND)), name="static")

DEMO = Path(__file__).resolve().parent.parent / "demo-data"
if DEMO.exists():
    app.mount("/demo-data", StaticFiles(directory=str(DEMO)), name="demo")


# startup: reconcile any interrupted organize run
p3.reconcile(JOURNAL)
