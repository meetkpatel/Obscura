"""Obscura Companion — phone dispatch + monitor. Zero-cloud, zero-relay.

Lets the user watch what Obscura is doing and dispatch work from their phone
while away from the desk — WITHOUT weakening the product's core promise.

Confidentiality model (mirrors the app's "nothing leaves the room" spine):
- No third-party relay, no push service, no cloud account. The phone talks
  DIRECTLY to this process over the user's own Wi-Fi. For cellular access the
  documented path is the user's OWN encrypted overlay (Tailscale/WireGuard) —
  device-to-device, end-to-end encrypted; Obscura itself never adds an egress.
- Metadata-first: the companion surface serves job states, counts, categories,
  scores, and file NAMES — never document pixels, page text, or file contents.
  PHI stays on the desktop screen.
- Paired, not open: every request from a non-loopback address must present the
  session pairing token (shown as a QR code on the desktop, which only
  loopback can fetch). Unpaired requests get 403 before any route runs.
  The token is random per server start and lives only in memory.
- Provable: inbound companion connections are INBOUND to Obscura, not egress;
  /api/egress labels them separately and still counts outbound only.
"""
from __future__ import annotations

import hmac
import io
import secrets
import threading
import time
from collections import deque

from fastapi import Request
from fastapi.responses import JSONResponse

# Pairing token: per-run, memory-only. Rotating on restart is a feature — a
# lost/old phone silently unpairs the moment the desktop restarts Obscura.
TOKEN = secrets.token_urlsafe(16)
COOKIE = "obscura_token"
HEADER = "x-obscura-token"

_lock = threading.Lock()
_events: deque = deque(maxlen=400)
_next_id = 1


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else ""


def is_loopback(ip: str) -> bool:
    return ip.startswith("127.") or ip in ("::1", "localhost", "")


def _token_ok(request: Request) -> bool:
    presented = (request.headers.get(HEADER)
                 or request.cookies.get(COOKIE)
                 or request.query_params.get("t") or "")
    return hmac.compare_digest(presented, TOKEN)


def check(request: Request):
    """Gate for the auth middleware. None = allow; else a 403 response.
    Loopback (the desktop UI) always passes; anything else must be paired."""
    if is_loopback(_client_ip(request)):
        return None
    if _token_ok(request):
        return None
    return JSONResponse(
        {"error": "not paired — scan the pairing QR on the Obscura desktop"},
        status_code=403)


# --------------------------------------------------------------------------
# Activity feed — a small append-only event log the phone polls.
# Events are one-line summaries (counts/states), never document content.
# --------------------------------------------------------------------------

def log(phase: str, msg: str, kind: str = "info") -> None:
    global _next_id
    with _lock:
        _events.append({"id": _next_id, "ts": time.time(), "phase": phase,
                        "kind": kind, "msg": msg})
        _next_id += 1


def events_since(since: int, limit: int = 120) -> dict:
    with _lock:
        out = [e for e in _events if e["id"] > since]
    return {"events": out[-limit:], "latest": (out[-1]["id"] if out else since)}


# --------------------------------------------------------------------------
# Pairing info (loopback-only route in main.py serves this)
# --------------------------------------------------------------------------

def lan_addresses() -> list[str]:
    """This machine's non-loopback IPv4 addresses (the phone connects here)."""
    import psutil
    import socket
    out = []
    for _, addrs in psutil.net_if_addrs().items():
        for a in addrs:
            if a.family == socket.AF_INET and not a.address.startswith("127.") \
                    and not a.address.startswith("169.254."):
                out.append(a.address)
    return out


def qr_data_url(text: str) -> str | None:
    """QR PNG as a data URL, generated fully offline (qrcode + pillow).
    Returns None if the optional qrcode package isn't installed — the UI then
    falls back to showing the URL + token as text."""
    try:
        import base64
        import qrcode
    except ImportError:
        return None
    img = qrcode.make(text, box_size=7, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def pairing_info(port: int) -> dict:
    ips = lan_addresses()
    urls = [f"http://{ip}:{port}/m?t={TOKEN}" for ip in ips]
    return {
        "token": TOKEN,
        "urls": urls,
        "qr": qr_data_url(urls[0]) if urls else None,
        "note": ("Same Wi-Fi: scan and go. Away from home (cellular): join both "
                 "devices to your own Tailscale/WireGuard network and use the "
                 "same address — end-to-end encrypted, still no cloud in the "
                 "middle. Server must be started with --host 0.0.0.0."),
    }
