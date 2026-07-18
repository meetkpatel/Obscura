"""Hardware probe — decide which Gemma 4 model this machine should run.

Obscura is on-device, so the right model depends on YOUR silicon. We detect the
GPU (VRAM), system RAM, and CPU, then recommend E4B (fast, fits anything) or
offer 12B (quality) only when there is enough VRAM/RAM to run it acceptably.
"""
from __future__ import annotations

import platform
import shutil
import subprocess

import psutil

# Rough footprints (GB) of the QAT Q4 models plus KV cache headroom.
# 12B-it-qat is ~6.6 GB resident, so an 8 GB card (reports ~7.99) CAN run it —
# it just partially spills and runs ~14 tok/s. We OFFER it there but RECOMMEND
# E4B as the faster interactive default, and only recommend 12B outright when
# there is comfortable headroom.
VRAM_OFFER_12B = 7.5      # can run 12B (may be slower)
VRAM_COMFORT_12B = 11.0   # recommend 12B as the default
RAM_FALLBACK_12B = 24.0   # no big GPU: CPU/unified inference wants lots of RAM


def _nvidia_vram_gb() -> float | None:
    """Total VRAM of the largest NVIDIA GPU, via nvidia-smi. None if no NVIDIA."""
    if not shutil.which("nvidia-smi"):
        return None
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        vals = [float(x) for x in out.splitlines() if x.strip()]
        return max(vals) / 1024.0 if vals else None   # MiB -> GB
    except Exception:
        return None


def _gpu_name() -> str | None:
    if not shutil.which("nvidia-smi"):
        return None
    try:
        return subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip().splitlines()[0]
    except Exception:
        return None


def probe() -> dict:
    ram_gb = psutil.virtual_memory().total / 1e9
    cores = psutil.cpu_count(logical=True) or 0
    vram = _nvidia_vram_gb()
    gpu = _gpu_name()
    is_mac = platform.system() == "Darwin"
    apple_silicon = is_mac and platform.machine() == "arm64"

    # ----- decide -----
    can_run_12b = False      # can 12B run at all here? (offer it)
    recommend_12b = False    # is 12B the best default? (comfortable headroom)
    reason = ""
    if vram is not None and vram >= VRAM_COMFORT_12B:
        can_run_12b = recommend_12b = True
        reason = f"{gpu} with {vram:.1f} GB VRAM — plenty for the 12B model."
    elif vram is not None and vram >= VRAM_OFFER_12B:
        can_run_12b = True   # e.g. an 8 GB card: 12B runs (~14 tok/s, partial spill)
        reason = (f"{gpu} with {vram:.1f} GB VRAM — the 12B model runs here "
                  f"(a bit slower); E4B is the faster default, 12B is offered for quality.")
    elif apple_silicon and ram_gb >= 16:
        can_run_12b = True
        recommend_12b = ram_gb >= 32
        reason = f"Apple Silicon with {ram_gb:.0f} GB unified memory — 12B runs on-device."
    elif ram_gb >= RAM_FALLBACK_12B:
        can_run_12b = True
        reason = f"No discrete GPU, but {ram_gb:.0f} GB RAM — 12B is usable on CPU (slower). E4B recommended."
    elif vram is not None:
        reason = (f"{gpu} has {vram:.1f} GB VRAM (< {VRAM_OFFER_12B:.0f} GB). "
                  f"E4B is the right fit; 12B would spill to CPU and crawl.")
    else:
        reason = (f"No NVIDIA GPU detected and {ram_gb:.0f} GB RAM — "
                  f"E4B is the right fit; 12B would be too slow here.")

    recommended = "gemma4:12b-it-qat" if recommend_12b else "gemma4:e4b-it-qat"
    tier = "quality" if recommend_12b else "fast"

    return {
        "os": f"{platform.system()} {platform.release()}",
        "cpu": platform.processor() or platform.machine(),
        "cores": cores,
        "ram_gb": round(ram_gb, 1),
        "gpu": gpu or ("Apple Silicon" if apple_silicon else "none detected"),
        "vram_gb": round(vram, 1) if vram is not None else None,
        "can_run_12b": can_run_12b,
        "recommended_model": recommended,
        "recommended_tier": tier,
        "reason": reason,
        "models": [
            {"id": "gemma4:e4b-it-qat", "label": "Gemma 4 E4B — Fast",
             "note": "~38 tok/s here; fits any laptop. Best for a live demo.",
             "always_available": True},
            {"id": "gemma4:12b-it-qat", "label": "Gemma 4 12B — Quality",
             "note": "Higher recall, catches signatures & subtle context; slower.",
             "always_available": False, "offered": can_run_12b},
        ],
    }
