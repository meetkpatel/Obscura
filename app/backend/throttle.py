"""Resource-considerate execution — run heavy work without disrupting the user.

The gate decides whether to proceed, wait, or slow down based on:
  * user idle time (GetLastInputInfo on Windows) — pause while someone is working
  * CPU load (psutil) — back off when the machine is busy

Three modes:
  * "idle"  — only work while the user is idle; pause the instant they touch the
              keyboard/mouse. Best for a whole-computer reorg left running.
  * "eco"   — always make progress, but throttled (small sleeps, low priority,
              yields when CPU is hot). The friendly default.
  * "now"   — full speed, no throttling.
"""
from __future__ import annotations

import sys
import time

import psutil

IS_WIN = sys.platform.startswith("win")

IDLE_THRESHOLD_S = 15      # user considered "active" if input within this window
CPU_BUSY_PCT = 70          # back off above this system CPU%
ECO_SLEEP_S = 0.15         # gentle pacing between items in eco mode


def idle_seconds() -> float:
    """Seconds since the last user input. Large value => user is away."""
    if not IS_WIN:
        return 999.0
    try:
        import ctypes
        from ctypes import wintypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

        li = LASTINPUTINFO()
        li.cbSize = ctypes.sizeof(li)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li)):
            millis = ctypes.windll.kernel32.GetTickCount() - li.dwTime
            return max(0.0, millis / 1000.0)
    except Exception:
        pass
    return 999.0


def set_low_priority() -> None:
    """Drop this process below normal priority so foreground apps stay snappy."""
    try:
        p = psutil.Process()
        if IS_WIN:
            p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        else:
            p.nice(10)
    except Exception:
        pass


def restore_priority() -> None:
    try:
        p = psutil.Process()
        p.nice(psutil.NORMAL_PRIORITY_CLASS if IS_WIN else 0)
    except Exception:
        pass


class Gate:
    """Call gate.wait() before each unit of work. It blocks until it's polite to
    proceed, honoring the mode and a cooperative pause/cancel flag."""

    def __init__(self, mode: str = "eco"):
        self.mode = mode if mode in ("idle", "eco", "now") else "eco"
        self.paused = False           # user-requested pause
        self.cancelled = False
        self.state = "running"        # running | waiting-idle | waiting-cpu | paused
        self._last_cpu = 0.0

    def wait(self) -> bool:
        """Block until OK to do the next unit. Returns False if cancelled."""
        while True:
            if self.cancelled:
                return False
            if self.paused:
                self.state = "paused"
                time.sleep(0.4)
                continue
            if self.mode == "now":
                self.state = "running"
                return True
            # idle mode: hold while the user is actively working
            if self.mode == "idle" and idle_seconds() < IDLE_THRESHOLD_S:
                self.state = "waiting-idle"
                time.sleep(0.6)
                continue
            # both eco + idle: back off when CPU is hot
            cpu = psutil.cpu_percent(interval=0.0)
            self._last_cpu = cpu
            if cpu >= CPU_BUSY_PCT:
                self.state = "waiting-cpu"
                time.sleep(0.5)
                continue
            self.state = "running"
            if self.mode == "eco":
                time.sleep(ECO_SLEEP_S)   # gentle pacing
            return True

    def snapshot(self) -> dict:
        return {"mode": self.mode, "state": self.state, "paused": self.paused,
                "cancelled": self.cancelled, "idle_s": round(idle_seconds(), 1),
                "cpu": round(self._last_cpu, 1)}
