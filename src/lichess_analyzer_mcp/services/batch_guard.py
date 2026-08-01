"""Batch budget guard for long-running tools (P13).

Wall-clock budget across a processing loop. Tools report how many items
were not processed so the client can resume with a follow-up call.
"""

import time


class BatchBudget:
    def __init__(self, max_seconds: float = 0.0):
        self.max_seconds = max_seconds
        self._start = time.monotonic()
        self._deadline = self._start + max_seconds if max_seconds > 0 else None

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self._start

    @property
    def exceeded(self) -> bool:
        return self._deadline is not None and time.monotonic() >= self._deadline

    def to_dict(self) -> dict:
        return {
            "max_seconds": self.max_seconds,
            "elapsed_seconds": round(self.elapsed, 1),
            "budget_exceeded": self.exceeded,
        }
