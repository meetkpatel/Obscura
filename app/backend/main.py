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

@app.post("/api/redact/detect")
async def redact_detect(file: UploadFile = File(...),
                        quality: bool = False):
    """Always returns JSON. A slow/failed page keeps its deterministic (regex+OCR)
    boxes and just skips the Gemma passes — never an HTML 500."""
    import base64
    try:
        raw = await file.read()
        src = WORK / f"in_{Path(file.filename).name}"
        src.write_bytes(raw)
        pages = p1.load_pages(str(src))
    except Exception as e:
        return JSONResponse(
            {"error": f"Could not open '{file.filename}': {type(e).__name__}: {e}. "
                      f"Encrypted or unsupported PDFs may need to be re-saved/printed to PDF first."},
            status_code=200)

    model = gemma.QUALITY_MODEL if quality else gemma.FAST_MODEL
    results, out, skipped = [], [], []
    for i, pg in enumerate(pages):
        try:
            res = p1.detect_page(pg, model)
        except Exception as e:  # last-resort: deterministic-only for this page
            try:
                res = p1.detect_page(pg, model, use_vision=False, use_gemma_text=False)
                skipped.append(i + 1)
            except Exception:
                res = p1.DetectResult(page_width=pg.size[0], page_height=pg.size[1],
                                      boxes=[], full_text="", stats={"error": str(e)[:120]})
                skipped.append(i + 1)
        results.append(res)
        buf = io.BytesIO(); pg.save(buf, "PNG")
        out.append({
            "image": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(),
            "width": res.page_width, "height": res.page_height,
            "boxes": [b.model_dump() for b in res.boxes],
            "stats": res.stats,
        })
    STATE["pages"] = pages
    STATE["detect"] = results
    return {"pages": out, "page_count": len(pages),
            "gemma_skipped_pages": skipped,
            "note": (f"{len(skipped)} page(s) used deterministic detection only "
                     f"(Gemma slow/unavailable on those pages)." if skipped else "")}


@app.post("/api/redact/apply")
def redact_apply(decisions: dict = Body(...)):
    """decisions = {page_index: [accepted_bool,...]}. Burn, flatten, scrub, verify."""
    pages = STATE["pages"]
    results = STATE["detect"]
    if not pages:
        return JSONResponse({"error": "no document detected yet"}, status_code=400)
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
            "redacted_count": len(gone)}


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
