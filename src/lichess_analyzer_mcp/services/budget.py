"""Monotonic stage budget for a single game analysis (P0.2).

The budget is one deadline for the whole game, not a per-call constant.
Stages ask `remaining()` and receive only what is left; a stage that cannot
start within `MIN_USEFUL_ENGINE_S` is skipped and reported, never silently
replaced by a zero value.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from lichess_analyzer_mcp.config.depth import BUDGETS, MIN_USEFUL_ENGINE_S


class Budget:
    """Wall-clock budget anchored to a monotonic deadline."""

    def __init__(self, total_s: float, label: str = "") -> None:
        self.total_s = max(0.0, float(total_s))
        self.label = label
        self.started_at = time.perf_counter()
        self._deadline = self.started_at + self.total_s

    def remaining(self) -> float:
        return max(0.0, self._deadline - time.perf_counter())

    def elapsed(self) -> float:
        return time.perf_counter() - self.started_at

    def expired(self, min_useful_s: float = MIN_USEFUL_ENGINE_S) -> bool:
        return self.remaining() < min_useful_s

    def stage_cap(self, stage_max_s: float, reserve_s: float = 0.0) -> float:
        """Return how long a stage may run without eating the reserve."""
        return max(0.0, min(stage_max_s, self.remaining() - reserve_s))


@dataclass
class StageTimer:
    """Accumulate wall-clock seconds per stage (thread-safe, monotonic)."""

    _totals: dict[str, float] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def add(self, stage: str, seconds: float) -> None:
        with self._lock:
            self._totals[stage] = self._totals.get(stage, 0.0) + max(0.0, seconds)

    def timed(self, stage: str):
        return _StageScope(self, stage)

    def as_dict(self) -> dict[str, float]:
        with self._lock:
            return {k: round(v, 3) for k, v in self._totals.items()}


class _StageScope:
    def __init__(self, timer: StageTimer, stage: str) -> None:
        self._timer = timer
        self._stage = stage
        self._start = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb):
        self._timer.add(self._stage, time.perf_counter() - self._start)
        return False


def budget_for_mode(mode: str) -> dict:
    """Return the budget config for a mode, defaulting to `fast`."""
    return BUDGETS.get(mode, BUDGETS["fast"])
