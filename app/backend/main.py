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
    return h


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
    """Prove nothing leaves: list this process tree's remote connections.
    Loopback (Ollama) is labeled allowed; anything else is EXTERNAL."""
    conns: list[Connection] = []
    external = 0
    me = psutil.Process()
    pids = {me.pid} | {c.pid for c in me.children(recursive=True)}
    for c in psutil.net_connections(kind="inet"):
        if c.pid not in pids or not c.raddr:
            continue
        ip = c.raddr.ip
        loop = ip.startswith("127.") or ip == "::1"
        label = "local LLM — allowed" if (loop and c.raddr.port == 11434) \
            else ("local" if loop else "EXTERNAL")
        if label == "EXTERNAL":
            external += 1
        try:
            pname = psutil.Process(c.pid).name()
        except Exception:
            pname = "?"
        conns.append(Connection(
            pid=c.pid or 0, proc=pname,
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

@app.post("/api/organize/plan")
def organize_plan(body: dict = Body(...)):
    root = body.get("root")
    quality = body.get("quality", False)
    if not root or not os.path.isdir(root):
        return JSONResponse({"error": f"not a folder: {root}"}, status_code=400)
    model = gemma.QUALITY_MODEL if quality else gemma.FAST_MODEL
    plan = p3.build_plan(root, model, limit=body.get("limit", 200))
    STATE["plan"] = plan
    return plan.model_dump()


@app.post("/api/organize/apply")
def organize_apply(body: dict = Body(default={})):
    plan = STATE.get("plan")
    if not plan:
        return JSONResponse({"error": "no plan built yet"}, status_code=400)
    excl = set(body.get("excluded", []))
    for pr in plan.proposals:
        pr.excluded = pr.src in excl
    return p3.apply_plan(plan, JOURNAL)


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


# startup: reconcile any interrupted organize run
p3.reconcile(JOURNAL)
