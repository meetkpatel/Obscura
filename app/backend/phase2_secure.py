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
# Collector: OPTIMIZATION / cleanup — the read-only analysis a paid "PC cleaner"
# does, using only Microsoft-supported methods. Grounded in Windows 11 cleanup
# guidance (temp/cache/WinSxS/update cleanup, startup, TRIM, power, updates).
# We ANALYZE + estimate reclaimable space; the FixRegistry describes the safe,
# consented command. We deliberately DO NOT touch the registry (registry
# "cleaners" are snake oil — near-zero benefit, real risk).
# ---------------------------------------------------------------------------

def _dir_size_mb(path: str, cap_files=60000) -> int:
    """Sum a directory's file sizes in MB (best-effort, bounded)."""
    total, n = 0, 0
    try:
        for dp, dn, fn in os.walk(path):
            for f in fn:
                try:
                    total += os.path.getsize(os.path.join(dp, f))
                except OSError:
                    pass
                n += 1
                if n >= cap_files:
                    return total // (1024 * 1024)
    except Exception:
        pass
    return total // (1024 * 1024)


def scan_optimization(deep=True) -> tuple[list[Finding], int]:
    """Return (optimization findings, total reclaimable MB)."""
    if not IS_WIN:
        return [], 0
    f: list[Finding] = []
    reclaim_total = 0
    win = os.environ.get("SystemRoot", r"C:\Windows")

    def add_space(id_, title, mb, remediation, sev_hint=None):
        nonlocal reclaim_total
        if mb < 50:      # ignore trivial
            return
        reclaim_total += mb
        sev = sev_hint or ("medium" if mb > 2000 else "low")
        f.append(Finding(id=id_, collector="optimization", kind="optimization",
                         title=f"{title} — ~{mb/1024:.1f} GB reclaimable" if mb >= 1024
                               else f"{title} — ~{mb} MB reclaimable",
                         severity=sev, detail=f"{mb} MB in {title.lower()}",
                         remediation=remediation, reclaimable_mb=mb,
                         requires_admin=False, reversible=False))

    # 1. Temp files (user + system)
    temp_mb = _dir_size_mb(os.environ.get("TEMP", "")) + _dir_size_mb(os.path.join(win, "Temp"))
    add_space("opt_temp", "Temporary files", temp_mb,
              "Disk Cleanup or Storage Sense clears %TEMP% and Windows\\Temp safely.")

    # 2. Windows Update download cache
    add_space("opt_update", "Windows Update cache",
              _dir_size_mb(os.path.join(win, "SoftwareDistribution", "Download")),
              "Clear via Disk Cleanup 'Windows Update Cleanup' (needs the update service stopped).")

    # 3. Delivery Optimization cache
    add_space("opt_do", "Delivery Optimization cache",
              _dir_size_mb(os.path.join(win, "SoftwareDistribution", "DeliveryOptimization")),
              "Disk Cleanup 'Delivery Optimization Files'.")

    # 4. Recycle Bin
    rb = _ps("(Get-ChildItem 'C:\\$Recycle.Bin' -Recurse -Force -ErrorAction SilentlyContinue "
             "| Measure-Object Length -Sum).Sum")
    try:
        add_space("opt_recycle", "Recycle Bin", int(int(rb) / 1024 / 1024) if rb.strip().isdigit() else 0,
                  "Empty the Recycle Bin (Clear-RecycleBin).")
    except Exception:
        pass

    # 5. WinSxS component store (DISM analyze — Microsoft-supported, slower)
    if deep:
        out = _ps("dism.exe /online /cleanup-image /AnalyzeComponentStore", timeout=70)
        m = re.search(r"Actual Size of Component Store\s*:\s*([\d.]+)\s*(MB|GB)", out)
        rec = re.search(r"(?:Reclaimable|can be cleaned)\s*:?\s*(Yes|No)", out, re.I)
        recommend = re.search(r"Component Store Cleanup Recommended\s*:\s*(Yes|No)", out, re.I)
        if recommend and recommend.group(1).lower() == "yes":
            f.append(Finding(id="opt_winsxs", collector="optimization", kind="optimization",
                             title="Windows component store (WinSxS) cleanup recommended",
                             severity="low", detail=out.strip()[-300:] or "DISM recommends cleanup",
                             remediation="dism.exe /online /cleanup-image /StartComponentCleanup "
                                         "(Microsoft-supported; removes superseded update components).",
                             reclaimable_mb=0, requires_admin=True, reversible=False))

    # 6. Startup impact — the #1 boot-time slowdown
    startups = _ps("(Get-CimInstance Win32_StartupCommand -ErrorAction SilentlyContinue).Name -join '|'")
    n_start = len([s for s in startups.split("|") if s.strip()]) if startups else 0
    if n_start >= 8:
        f.append(Finding(id="opt_startup", collector="optimization", kind="optimization",
                         title=f"{n_start} apps launch at startup",
                         severity="medium" if n_start >= 15 else "low",
                         detail=f"{n_start} startup entries: {startups[:200]}",
                         remediation="Disable non-essential startup apps in Task Manager > Startup "
                                     "(keep security software). The top boot-time win.",
                         requires_admin=False, reversible=True))

    # 7. Storage Sense enabled?
    ss = _ps("(Get-ItemProperty 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\StorageSense\\Parameters\\StoragePolicy' "
             "-Name '01' -ErrorAction SilentlyContinue).'01'")
    if ss != "1":
        f.append(Finding(id="opt_storagesense", collector="optimization", kind="optimization",
                         title="Storage Sense is off (automatic cleanup disabled)",
                         severity="low", detail="StorageSense policy not enabled",
                         remediation="Enable Storage Sense (Settings > System > Storage) to auto-clear "
                                     "temp files and empty the Recycle Bin on a schedule.",
                         requires_admin=False, reversible=True))

    # 8. Power plan
    plan = _ps("powercfg /getactivescheme")
    if plan and "power saver" in plan.lower():
        f.append(Finding(id="opt_power", collector="optimization", kind="optimization",
                         title="On the Power Saver plan (throttles performance)",
                         severity="low", detail=plan.strip(),
                         remediation="Switch to Balanced or High performance (powercfg /setactive SCHEME_BALANCED).",
                         requires_admin=False, reversible=True))

    # 9. SSD TRIM enabled?
    trim = _ps("fsutil behavior query DisableDeleteNotify")
    if "= 1" in trim.replace(" ", " "):
        f.append(Finding(id="opt_trim", collector="optimization", kind="optimization",
                         title="SSD TRIM is disabled (slows an SSD over time)",
                         severity="low", detail=trim.strip(),
                         remediation="Enable TRIM: fsutil behavior set DisableDeleteNotify 0.",
                         requires_admin=True, reversible=True))

    # 10. Pending Windows Update / reboot / build freshness
    build = _ps("(Get-ItemProperty 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion' "
                "-Name DisplayVersion -ErrorAction SilentlyContinue).DisplayVersion")
    pend = _ps("Test-Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsUpdate\\Auto Update\\RebootRequired'")
    if pend == "True":
        f.append(Finding(id="opt_wu_reboot", collector="optimization", kind="optimization",
                         title="Windows updates installed but not applied (reboot pending)",
                         severity="medium", detail=f"Windows build {build}; reboot required",
                         remediation="Restart to finish applying security + feature updates.",
                         requires_admin=False, reversible=False))
    return f, reclaim_total


# ---------------------------------------------------------------------------
# Collector: CIS Level 1 baseline (Windows). Grounded in the CIS Microsoft
# Windows 11 Benchmark / NIST hardening guidance. High-value, laptop-relevant
# controls; each check degrades gracefully and never breaks the scan.
# ---------------------------------------------------------------------------

def scan_cis() -> list[Finding]:
    if not IS_WIN:
        return []
    f: list[Finding] = []

    # 1. SMBv1 — legacy protocol behind EternalBlue / WannaCry / NotPetya.
    smb1 = _ps("$s=(Get-SmbServerConfiguration -ErrorAction SilentlyContinue).EnableSMB1Protocol;"
               "$o=(Get-WindowsOptionalFeature -Online -FeatureName SMB1Protocol -ErrorAction SilentlyContinue).State;"
               "\"$s|$o\"")
    if "True" in smb1 or "Enabled" in smb1:
        f.append(Finding(id="smb1", collector="cis", title="SMBv1 legacy protocol is enabled",
                         severity="critical",
                         detail="SMBv1 is the vector for EternalBlue/WannaCry/NotPetya.",
                         remediation="Disable SMBv1: Disable-WindowsOptionalFeature -Online "
                                     "-FeatureName SMB1Protocol. Breaks only legacy NAS/printers.",
                         requires_admin=True, reversible=True))

    # 2. PowerShell v2 — bypasses AMSI + ScriptBlock logging; malware favorite.
    psv2 = _ps("(Get-WindowsOptionalFeature -Online -FeatureName MicrosoftWindowsPowerShellV2 "
               "-ErrorAction SilentlyContinue).State")
    if psv2 == "Enabled":
        f.append(Finding(id="psv2", collector="cis",
                         title="Legacy PowerShell v2 is installed",
                         severity="high",
                         detail="PS v2 evades AMSI and ScriptBlock logging.",
                         remediation="Remove it: Disable-WindowsOptionalFeature -Online "
                                     "-FeatureName MicrosoftWindowsPowerShellV2Root. No modern impact.",
                         requires_admin=True, reversible=True))

    # 3. Guest account enabled.
    guest = _ps("(Get-LocalUser -Name 'Guest' -ErrorAction SilentlyContinue).Enabled")
    if guest == "True":
        f.append(Finding(id="guest", collector="cis", title="Built-in Guest account is enabled",
                         severity="medium", detail="Guest allows unauthenticated local access.",
                         remediation="Disable-LocalUser -Name Guest.",
                         requires_admin=True, reversible=True))

    # 4. Legacy / risky services running (CIS: reduce attack surface).
    #    High-risk remote-access services vs low-risk discovery services.
    high_risk = {"TlntSvr": "Telnet Server", "FTPSVC": "FTP Server", "SNMP": "SNMP",
                 "RemoteRegistry": "Remote Registry"}
    low_risk = {"SSDPSRV": "SSDP Discovery", "upnphost": "UPnP Host"}
    running = _ps("(Get-Service -ErrorAction SilentlyContinue | Where-Object {$_.Status -eq 'Running'})"
                  ".Name -join ','").lower()
    hi = [n for s, n in high_risk.items() if running and s.lower() in running]
    lo = [n for s, n in low_risk.items() if running and s.lower() in running]
    if hi:
        f.append(Finding(id="legacy_svc_hi", collector="cis",
                         title=f"Remote-access services running: {', '.join(hi)}",
                         severity="medium", detail=f"Running: {', '.join(hi)}",
                         remediation="Disable services you don't use (Set-Service -StartupType Disabled).",
                         requires_admin=True, reversible=True))
    if lo:
        f.append(Finding(id="legacy_svc_lo", collector="cis",
                         title=f"Network-discovery services running: {', '.join(lo)}",
                         severity="low", detail=f"Running: {', '.join(lo)}",
                         remediation="Optional: disable UPnP/SSDP if you don't use device discovery.",
                         requires_admin=True, reversible=True))

    # 5. Pending reboot for updates (patch hygiene).
    pend = _ps("Test-Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\"
               "Component Based Servicing\\RebootPending'")
    if pend == "True":
        f.append(Finding(id="reboot", collector="cis", title="A reboot is pending for updates",
                         severity="low", detail="Pending servicing operations aren't complete.",
                         remediation="Restart to finish applying security updates.",
                         requires_admin=False, reversible=False))

    return f


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
        "For each finding below, write ONE short plain-English sentence (max 30 "
        "words) on what it means and why it matters. Do not repeat words. "
        "Return ONLY JSON: {\"explanations\":[{\"id\":\"...\",\"explanation\":\"...\"}]}\n\n"
        f"Findings: {payload}"
    )
    try:
        data = gemma.generate_json(prompt, model=model, num_predict=700)
        by_id = {e["id"]: e.get("explanation", "")
                 for e in data.get("explanations", [])}
        for f in findings:
            # collapse any degenerate repetition ("protect-less protect-less…")
            f.explanation = gemma.collapse_repeats(by_id.get(f.id, ""))
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


def perf_score(opts: list[Finding], reclaim_mb: int) -> int:
    """Performance/cleanup score (0-100). Deduct for reclaimable clutter + perf
    findings; formula shown to the user."""
    s = 100
    s -= min(30, reclaim_mb // 1024 * 5)         # -5 per GB reclaimable, cap 30
    for f in opts:
        s -= {"critical": 20, "high": 15, "medium": 8, "low": 4, "info": 0}.get(f.severity, 0)
    return max(0, s)


def run_scan(roots: list[str] | None, model: str, use_gemma=True, deep=True) -> ScanResult:
    roots = roots or [str(Path.home() / "Downloads"), str(Path.home() / "Documents"),
                      str(Path.home() / "Desktop")]
    findings = scan_secrets(roots) + scan_config() + scan_network() + scan_cis()
    optimizations, reclaim_mb = scan_optimization(deep=deep)
    if use_gemma:
        explain(findings, model)
        explain(optimizations, model)
    score, breakdown = safety_score(findings)
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    findings.sort(key=lambda f: order.get(f.severity, 9))
    optimizations.sort(key=lambda f: (-f.reclaimable_mb, order.get(f.severity, 9)))
    pscore = perf_score(optimizations, reclaim_mb)
    perf_summary = ""
    if use_gemma and optimizations:
        perf_summary = _perf_plan(optimizations, reclaim_mb, model)
    return ScanResult(findings=findings, safety_score=score,
                      score_breakdown=breakdown, admin=is_admin(),
                      generated_offline=True, optimizations=optimizations,
                      reclaimable_mb=reclaim_mb, performance_score=pscore,
                      perf_summary=perf_summary)


def _perf_plan(opts: list[Finding], reclaim_mb: int, model: str) -> str:
    """Gemma writes a short, prioritized, plain-English cleanup plan."""
    items = [{"title": o.title, "fix": o.remediation} for o in opts[:8]]
    prompt = (
        "You are a helpful PC optimization assistant for a non-technical laptop "
        "user. Given these cleanup/performance findings, write a short (3-4 "
        "sentence) prioritized plan in plain English — what to do first for the "
        "biggest win, and reassure them these are safe, built-in Windows actions "
        "(no risky registry edits). Do not repeat words.\n"
        f"Reclaimable space: ~{reclaim_mb} MB. Findings: {items}"
    )
    try:
        out = gemma.collapse_repeats(gemma.generate(prompt, model=model, num_predict=260).strip())
    except gemma.GemmaError:
        out = ""
    if out:
        return out
    # deterministic fallback if the model returns nothing (e.g. busy/cold)
    top = opts[0].title if opts else "temporary files"
    return (f"Start with the biggest win: {top}. Everything here uses built-in "
            f"Windows tools (Disk Cleanup, Storage Sense, Task Manager) — no risky "
            f"registry edits. About {reclaim_mb} MB is safely reclaimable.")
