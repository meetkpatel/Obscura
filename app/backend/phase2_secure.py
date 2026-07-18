"""Phase 2 — SECURE.

Own-machine, read-only, defensive scan. Deterministic collectors produce
Findings; Gemma explains + prioritizes (never scans, never executes). Fixes
come from a hardcoded FixRegistry — no dynamic code generation, ever.

Windows-first (PowerShell collectors), with graceful non-admin degradation and
a cross-platform secrets sweep that is the bridge to Phase 1 (REDACT).
"""
from __future__ import annotations

import ctypes
import os
import re
import subprocess
import sys
from pathlib import Path

import psutil

from contracts import Finding, ScanResult, SEVERITY_WEIGHT
import gemma


IS_WIN = sys.platform.startswith("win")


def is_admin() -> bool:
    if not IS_WIN:
        return os.geteuid() == 0 if hasattr(os, "geteuid") else False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _ps(cmd: str, timeout=30) -> str:
    """Run a PowerShell one-liner, return stdout ('' on any failure)."""
    if not IS_WIN:
        return ""
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
            capture_output=True, text=True, timeout=timeout,
        )
        return r.stdout.strip()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# FixRegistry — every remediation is hardcoded, consented, and labeled.
# Gemma never writes to this. (script left descriptive for the demo — we do not
# auto-execute system changes on stage.)
# ---------------------------------------------------------------------------

FIX_REGISTRY = {
    "firewall_off": dict(remediation="Enable Windows Firewall for all profiles "
                         "(Set-NetFirewallProfile -All -Enabled True).",
                         requires_admin=True, reversible=True),
    "rdp_enabled": dict(remediation="Disable Remote Desktop if unused "
                        "(Set-ItemProperty ...\\Terminal Server fDenyTSConnections 1).",
                        requires_admin=True, reversible=True),
    "bitlocker_off": dict(remediation="Enable BitLocker on the system drive.",
                          requires_admin=True, reversible=False),
    "uac_low": dict(remediation="Raise UAC to 'Always notify'.",
                    requires_admin=True, reversible=True),
    "secret_on_disk": dict(remediation="Move the secret into a vault / env var, "
                           "rotate the exposed key, and redact the file.",
                           requires_admin=False, reversible=False),
}


# ---------------------------------------------------------------------------
# Collector: secrets-on-disk (the star — bridges to REDACT). Pure Python,
# cross-platform, no admin needed for the user's own directories.
# ---------------------------------------------------------------------------

SECRET_PATTERNS = [
    ("AWS access key", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("AWS secret key", re.compile(r"(?i)aws_secret_access_key\s*=\s*[A-Za-z0-9/+=]{30,}")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("Google API key", re.compile(r"AIza[0-9A-Za-z\-_]{35}")),
    ("Slack token", re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}")),
    ("Generic password assignment", re.compile(r"(?i)\bpassword\s*[:=]\s*['\"][^'\"]{6,}['\"]")),
    ("Bearer/JWT token", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}")),
]

SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", "env",
             "dist", "build", ".cache", "site-packages", ".mypy_cache",
             ".pytest_cache", "AppData"}
SCAN_EXTS = {".env", ".txt", ".json", ".yaml", ".yml", ".ini", ".cfg", ".config",
             ".py", ".js", ".ts", ".sh", ".ps1", ".pem", ".key", ".csv", ".md", ""}
MAX_FILE = 1_000_000  # 1 MB — secrets live in small config files


def scan_secrets(roots: list[str], limit=2000) -> list[Finding]:
    findings, seen, checked = [], set(), 0
    for root in roots:
        rp = Path(root).expanduser()
        if not rp.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(rp):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            for fn in filenames:
                if checked >= limit:
                    break
                fp = Path(dirpath) / fn
                if fp.suffix.lower() not in SCAN_EXTS:
                    continue
                try:
                    if fp.stat().st_size > MAX_FILE:
                        continue
                    text = fp.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                checked += 1
                for name, pat in SECRET_PATTERNS:
                    if pat.search(text):
                        key = (str(fp), name)
                        if key in seen:
                            continue
                        seen.add(key)
                        reg = FIX_REGISTRY["secret_on_disk"]
                        findings.append(Finding(
                            id=f"secret_{len(findings)}",
                            collector="secrets_on_disk",
                            title=f"{name} found in {fp.name}",
                            severity="critical" if "key" in name.lower()
                                     or "private" in name.lower() else "high",
                            detail=f"Pattern '{name}' matched in {fp}",
                            remediation=reg["remediation"],
                            requires_admin=False, reversible=False,
                            path=str(fp), can_redact=True,
                        ))
    return findings


# ---------------------------------------------------------------------------
# Collector: config hygiene (Windows) — degrades gracefully without admin
# ---------------------------------------------------------------------------

def scan_config() -> list[Finding]:
    if not IS_WIN:
        return []
    f: list[Finding] = []

    fw = _ps("(Get-NetFirewallProfile | Where-Object {$_.Enabled -eq 'False'}).Name -join ','")
    if fw:
        r = FIX_REGISTRY["firewall_off"]
        f.append(Finding(id="fw", collector="config", title=f"Firewall disabled: {fw}",
                         severity="high", detail=f"Profiles off: {fw}", **_reg(r)))

    rdp = _ps("(Get-ItemProperty 'HKLM:\\System\\CurrentControlSet\\Control\\Terminal Server'"
              " -Name fDenyTSConnections).fDenyTSConnections")
    if rdp == "0":
        r = FIX_REGISTRY["rdp_enabled"]
        f.append(Finding(id="rdp", collector="config", title="Remote Desktop is enabled",
                         severity="medium", detail="fDenyTSConnections=0", **_reg(r)))

    bl = _ps("(Get-BitLockerVolume -MountPoint $env:SystemDrive"
             " -ErrorAction SilentlyContinue).ProtectionStatus")
    if bl and bl != "On" and bl != "1":
        r = FIX_REGISTRY["bitlocker_off"]
        f.append(Finding(id="bl", collector="config",
                         title="System drive is not encrypted (BitLocker off)",
                         severity="high", detail=f"ProtectionStatus={bl}", **_reg(r)))

    defx = _ps("(Get-MpPreference -ErrorAction SilentlyContinue)."
               "ExclusionPath -join ','")
    if defx:
        f.append(Finding(id="defx", collector="config",
                         title="Windows Defender has folder exclusions",
                         severity="medium",
                         detail=f"Excluded: {defx}",
                         remediation="Review exclusions; attackers add them to hide payloads.",
                         requires_admin=True, reversible=True))
    return f


def _reg(r: dict) -> dict:
    return dict(remediation=r["remediation"], requires_admin=r["requires_admin"],
                reversible=r["reversible"])


# ---------------------------------------------------------------------------
# Collector: network — listening ports + owning process (psutil, no admin)
# ---------------------------------------------------------------------------

RISKY_PORTS = {23: "Telnet", 3389: "RDP", 445: "SMB", 5900: "VNC", 21: "FTP"}


def scan_network() -> list[Finding]:
    f: list[Finding] = []
    try:
        conns = psutil.net_connections(kind="inet")
    except Exception:
        return f
    listening = {}
    for c in conns:
        if c.status == psutil.CONN_LISTEN and c.laddr:
            port = c.laddr.port
            try:
                pname = psutil.Process(c.pid).name() if c.pid else "?"
            except Exception:
                pname = "?"
            listening.setdefault(port, pname)
    for port, pname in sorted(listening.items()):
        if port in RISKY_PORTS:
            f.append(Finding(
                id=f"port_{port}", collector="network",
                title=f"{RISKY_PORTS[port]} port {port} is listening ({pname})",
                severity="high" if port in (23, 3389, 21) else "medium",
                detail=f"Process {pname} listening on 0.0.0.0:{port}",
                remediation=f"Close {RISKY_PORTS[port]} if not required.",
                requires_admin=True, reversible=True,
            ))
    return f


# ---------------------------------------------------------------------------
# Gemma explainer pass — plain-English what/why/fix, batched into one call
# ---------------------------------------------------------------------------

def explain(findings: list[Finding], model: str) -> None:
    if not findings:
        return
    payload = [{"id": f.id, "title": f.title, "severity": f.severity,
                "detail": f.detail} for f in findings]
    prompt = (
        "You are a friendly security advisor for a non-technical laptop user. "
        "For each finding below, write a one-sentence plain-English explanation of "
        "what it means and why it matters. Return ONLY JSON: "
        '{"explanations":[{"id":"...","explanation":"..."}]}\n\n'
        f"Findings: {payload}"
    )
    try:
        data = gemma.generate_json(prompt, model=model, num_predict=1024)
        by_id = {e["id"]: e.get("explanation", "")
                 for e in data.get("explanations", [])}
        for f in findings:
            f.explanation = by_id.get(f.id, "")
    except gemma.GemmaError:
        pass  # explanations are enrichment, not load-bearing


# ---------------------------------------------------------------------------
# Score + orchestrate
# ---------------------------------------------------------------------------

def safety_score(findings: list[Finding]) -> tuple[int, dict]:
    breakdown = {}
    total = 0
    for f in findings:
        w = SEVERITY_WEIGHT.get(f.severity, 0)
        total += w
        breakdown[f.severity] = breakdown.get(f.severity, 0) + w
    return max(0, 100 - total), breakdown


def run_scan(roots: list[str] | None, model: str, use_gemma=True) -> ScanResult:
    roots = roots or [str(Path.home() / "Downloads"), str(Path.home() / "Documents"),
                      str(Path.home() / "Desktop")]
    findings = scan_secrets(roots) + scan_config() + scan_network()
    if use_gemma:
        explain(findings, model)
    score, breakdown = safety_score(findings)
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    findings.sort(key=lambda f: order.get(f.severity, 9))
    return ScanResult(findings=findings, safety_score=score,
                      score_breakdown=breakdown, admin=is_admin(),
                      generated_offline=True)
