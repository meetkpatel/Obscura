"""Gemma 4 client — the single on-device model gateway.

- One serialized queue (a global lock) so concurrent phase requests don't
  thrash VRAM on an 8 GB card.
- Structured output + json-repair + Pydantic-friendly dict return, 2 retries.
- Everything points at localhost:11434. No network path exists in this file.

Benchmarked on the demo machine (RTX 4070 8GB, warm):
    gemma4:12b-it-qat  ~14 tok/s   (quality mode, dense docs)
    gemma4:e4b-it-qat  ~38 tok/s   (interactive default)
"""
from __future__ import annotations

import base64
import json
import threading
import urllib.request
import urllib.error
from typing import Optional

from json_repair import repair_json

OLLAMA = "http://localhost:11434/api/generate"

# Interactive default = E4B (3x faster on this card). Flip to 12B for quality.
FAST_MODEL = "gemma4:e4b-it-qat"
QUALITY_MODEL = "gemma4:12b-it-qat"

_LOCK = threading.Lock()  # serialize model calls — one GPU, one worker


class GemmaError(RuntimeError):
    pass


def _post(payload: dict, timeout: int) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(OLLAMA, data, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.URLError as e:
        raise GemmaError(
            f"Ollama unreachable at {OLLAMA} ({e}). Is `ollama serve` running "
            f"and the model pulled? This app never falls back to a network model."
        )
    except (TimeoutError, OSError) as e:
        # A slow page (large scan on the 12B model) can exceed the timeout and
        # raise TimeoutError/socket errors — NOT a URLError. Surface as GemmaError
        # so per-page callers skip that page gracefully instead of 500-ing.
        raise GemmaError(f"Ollama request timed out/failed after {timeout}s ({e}).")
    except Exception as e:  # noqa: BLE001 — never let the model layer 500 the app
        raise GemmaError(f"Ollama request error: {type(e).__name__}: {e}")


def generate(
    prompt: str,
    *,
    model: str = FAST_MODEL,
    images: Optional[list[bytes]] = None,
    num_predict: int = 1024,
    num_ctx: int = 4096,
    timeout: int = 240,
) -> str:
    """Raw text generation. `images` = list of raw bytes (PNG/JPG)."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": 0,
            "num_ctx": num_ctx,
            "num_predict": num_predict,
        },
    }
    if images:
        payload["images"] = [base64.b64encode(b).decode() for b in images]
    with _LOCK:
        r = _post(payload, timeout)
    return r.get("response", "")


def generate_json(
    prompt: str,
    *,
    model: str = FAST_MODEL,
    images: Optional[list[bytes]] = None,
    num_predict: int = 1024,
    retries: int = 2,
    timeout: int = 240,
):
    """Generate and coerce to a Python object.

    Uses Ollama's structured `format: json` to bias decoding, then json-repair
    to survive fences / trailing commas, then json.loads. Retries on failure.
    """
    last = ""
    for attempt in range(retries + 1):
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "10m",
            "format": "json",
            "options": {
                "temperature": 0,
                "num_ctx": num_ctx_for(prompt),
                "num_predict": num_predict,
            },
        }
        if images:
            payload["images"] = [base64.b64encode(b).decode() for b in images]
        with _LOCK:
            r = _post(payload, timeout)
        last = r.get("response", "")
        try:
            return json.loads(repair_json(last))
        except Exception:
            if attempt == retries:
                break
    raise GemmaError(f"Model did not return valid JSON after {retries + 1} tries. "
                     f"Last 200 chars: {last[-200:]!r}")


def num_ctx_for(prompt: str, base: int = 4096) -> int:
    # crude: bump context if the prompt is long (chars/4 ~ tokens)
    est = len(prompt) // 4 + 512
    return max(base, min(8192, est))


def health() -> dict:
    """Confirm Ollama is up and both demo models are present."""
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=10) as r:
            tags = json.loads(r.read())
        names = {m["name"] for m in tags.get("models", [])}
        return {
            "ok": True,
            "fast_model": FAST_MODEL,
            "fast_present": FAST_MODEL in names,
            "quality_model": QUALITY_MODEL,
            "quality_present": QUALITY_MODEL in names,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
