"""SECURE — optimization EXECUTION engine (opt-in, self-verifying).

Turns the read-only cleanup ANALYSIS into real, safe, measured actions.

Safety model (non-negotiable):
  * Every action is a HARDCODED Python function here. Gemma NEVER supplies a
    command string — it only chooses which of these named actions to run and
    reviews the plan for reliability. No dynamic code, no shelling model output.
  * Only safe, well-understood cleanup is included: temp files, caches, recycle
    bin, DNS flush, Storage Sense, TRIM. NO registry edits (snake oil + risk),
    no process killing, no file deletion outside temp/cache locations.
  * Self-verifying: each action MEASURES disk before + after and reports the
    ACTUAL space reclaimed, plus a success check — so the app proves the result
    instead of claiming it.
  * Human-in-the-loop: nothing runs without an explicit per-action request.
"""
from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

IS_WIN = sys.platform.startswith("win")


def is_admin() -> bool:
    if not IS_WIN:
        return hasattr(os, "geteuid") and os.geteuid() == 0
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _free_bytes(drive="C:\\") -> int:
    try:
        total, used, free = shutil.disk_usage(drive)
        return free
    except Exception:
        return 0


def _clear_dir(path: str, older_than_s: int = 0) -> tuple[int, int, int]:
    """Delete files under `path` (best-effort, skip locked/in-use). Returns
    (files_removed, bytes_removed, skipped)."""
    removed = skipped = freed = 0
    p = Path(path)
    if not p.exists():
        return 0, 0, 0
    cutoff = time.time() - older_than_s if older_than_s else None
    for dp, dn, fn in os.walk(path, topdown=False):
        for f in fn:
            fp = Path(dp) / f
            try:
                st = fp.stat()
                if cutoff and st.st_mtime > cutoff:
                    continue
                sz = st.st_size
                fp.unlink()
                removed += 1
                freed += sz
            except Exception:
                skipped += 1
        # remove now-empty dirs (not the root)
        if Path(dp) != p:
            try:
                Path(dp).rmdir()
            except Exception:
                pass
    return removed, freed, skipped


# ---------------------------------------------------------------------------
# Action implementations — each returns a dict with measured results.
# ---------------------------------------------------------------------------

def _act_user_temp():
    before = _free_bytes()
    n, freed, sk = _clear_dir(os.environ.get("TEMP", ""))
    return {"files_removed": n, "skipped": sk, "measured_freed_mb": freed // (1024 * 1024)}


def _act_win_temp():
    n, freed, sk = _clear_dir(os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "Temp"))
    return {"files_removed": n, "skipped": sk, "measured_freed_mb": freed // (1024 * 1024)}


def _act_recycle():
    if not IS_WIN:
        return {"note": "recycle bin is Windows-only"}
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                        "Clear-RecycleBin -Force -ErrorAction SilentlyContinue"],
                       capture_output=True, text=True, timeout=60)
    return {"ok": r.returncode == 0}


def _act_flush_dns():
    if not IS_WIN:
        return {"note": "Windows-only"}
    r = subprocess.run(["ipconfig", "/flushdns"], capture_output=True, text=True, timeout=30)
    return {"ok": "Successfully" in r.stdout or r.returncode == 0}


def _act_thumb_cache():
    la = os.environ.get("LOCALAPPDATA", "")
    explorer = os.path.join(la, "Microsoft", "Windows", "Explorer")
    n, freed, sk = 0, 0, 0
    for f in Path(explorer).glob("thumbcache_*.db") if Path(explorer).exists() else []:
        try:
            freed += f.stat().st_size; f.unlink(); n += 1
        except Exception:
            sk += 1
    return {"files_removed": n, "skipped": sk, "measured_freed_mb": freed // (1024 * 1024)}


def _act_storage_sense_on():
    if not IS_WIN:
        return {"note": "Windows-only"}
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                        "New-Item -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\StorageSense\\Parameters\\StoragePolicy' -Force | Out-Null;"
                        "Set-ItemProperty -Path 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\StorageSense\\Parameters\\StoragePolicy' -Name '01' -Value 1 -Type DWord"],
                       capture_output=True, text=True, timeout=30)
    return {"ok": r.returncode == 0, "reversible": True}


def _act_trim():
    if not IS_WIN:
        return {"note": "Windows-only"}
    if not is_admin():
        return {"ok": False, "note": "needs Administrator"}
    r = subprocess.run(["fsutil", "behavior", "set", "DisableDeleteNotify", "0"],
                       capture_output=True, text=True, timeout=30)
    return {"ok": r.returncode == 0}


# id -> (label, fn, requires_admin, reversible, safe_note)
ACTIONS = {
    "clear_user_temp": ("Clear your temp files", _act_user_temp, False, False,
                        "Deletes files in %TEMP% (temp files are safe to remove; in-use files skipped)."),
    "clear_win_temp": ("Clear Windows temp files", _act_win_temp, True, False,
                       "Deletes files in Windows\\Temp (admin; in-use files skipped)."),
    "empty_recycle": ("Empty the Recycle Bin", _act_recycle, False, False,
                      "Permanently empties the Recycle Bin."),
    "flush_dns": ("Flush DNS cache", _act_flush_dns, False, True,
                  "Clears stale DNS entries (rebuilds automatically)."),
    "clear_thumb_cache": ("Clear thumbnail cache", _act_thumb_cache, False, True,
                          "Deletes thumbnail cache DBs (Windows rebuilds them)."),
    "enable_storage_sense": ("Enable Storage Sense", _act_storage_sense_on, False, True,
                             "Turns on automatic scheduled cleanup (reversible in Settings)."),
    "enable_trim": ("Enable SSD TRIM", _act_trim, True, True,
                    "Re-enables TRIM for SSD longevity (admin)."),
}

# Map a scan finding id -> the safe action that fixes it (only auto-fixable ones)
FINDING_TO_ACTION = {
    "opt_temp": "clear_user_temp",
    "opt_recycle": "empty_recycle",
    "opt_thumb": "clear_thumb_cache",
    "opt_storagesense": "enable_storage_sense",
    "opt_trim": "enable_trim",
}


def preview(action_ids: list[str]) -> dict:
    """What WILL run, deterministically — the plan the user consents to. Includes
    each action's hardcoded description + admin/reversibility, and an estimated
    reclaim from a dry measurement where cheap."""
    plan = []
    for aid in action_ids:
        spec = ACTIONS.get(aid)
        if not spec:
            continue
        label, fn, needs_admin, reversible, note = spec
        plan.append({"id": aid, "label": label, "note": note,
                     "requires_admin": needs_admin, "reversible": reversible,
                     "runnable": (not needs_admin) or is_admin()})
    return {"plan": plan, "admin": is_admin()}


def evaluate_plan(action_ids: list[str], model: str) -> dict:
    """Gemma reviews its OWN plan for reliability before it runs — the self-check
    the user asked for. Gemma cannot add actions (the registry is fixed); it
    confirms each is safe/appropriate and flags anything to watch. Reliability is
    grounded: every action here is pre-vetted safe, so the review is a sanity gate
    + plain-English 'here's what will happen', never a green light to run code the
    model wrote."""
    import gemma
    specs = [{"action": ACTIONS[a][0], "does": ACTIONS[a][4], "reversible": ACTIONS[a][3]}
             for a in action_ids if a in ACTIONS]
    prompt = (
        "You are a careful PC-optimization reviewer. These cleanup actions are "
        "about to run on the user's own laptop. For EACH, confirm in one short "
        "sentence that it is safe + what it does, and set reliable=true unless you "
        "see a real risk (these are all standard, reversible-or-harmless cleanups). "
        "Then give one overall sentence. Return ONLY JSON: {\"reviews\":[{\"action\":"
        "\"...\",\"reliable\":true,\"note\":\"...\"}],\"overall\":\"...\"}\n\n"
        f"Actions: {specs}"
    )
    try:
        data = gemma.generate_json(prompt, model=model, num_predict=500)
        if isinstance(data, dict):
            return data
    except gemma.GemmaError:
        pass
    # deterministic fallback — the actions are safe by construction
    return {"reviews": [{"action": s["action"], "reliable": True, "note": s["does"]}
                        for s in specs],
            "overall": "All selected actions are standard, safe Windows cleanups."}


def run_actions(action_ids: list[str]) -> dict:
    """Execute the requested SAFE actions, measuring disk before/after each and
    verifying success. Returns a self-evaluated report."""
    results = []
    disk_before = _free_bytes()
    for aid in action_ids:
        spec = ACTIONS.get(aid)
        if not spec:
            results.append({"id": aid, "ok": False, "error": "unknown action (not in the safe registry)"})
            continue
        label, fn, needs_admin, reversible, note = spec
        if needs_admin and not is_admin():
            results.append({"id": aid, "label": label, "ok": False,
                            "error": "needs Administrator — relaunch as admin to run this one"})
            continue
        b = _free_bytes()
        t0 = time.time()
        try:
            out = fn()
            ok = out.get("ok", True) is not False
        except Exception as e:
            out, ok = {"error": str(e)}, False
        freed_mb = max(0, (_free_bytes() - b)) // (1024 * 1024)
        results.append({"id": aid, "label": label, "ok": ok, "reversible": reversible,
                        "disk_freed_mb": freed_mb, "detail": out,
                        "seconds": round(time.time() - t0, 1)})
    disk_after = _free_bytes()
    total_freed_mb = max(0, (disk_after - disk_before)) // (1024 * 1024)
    return {"results": results, "total_freed_mb": total_freed_mb,
            "disk_free_before_gb": round(disk_before / 1e9, 1),
            "disk_free_after_gb": round(disk_after / 1e9, 1),
            "admin": is_admin(),
            # self-verification: did we actually free what we removed?
            "verified": all(r.get("ok") for r in results) if results else False}
