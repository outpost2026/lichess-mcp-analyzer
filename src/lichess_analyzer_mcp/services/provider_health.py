"""Provider health / negative cache (P0.3).

A provider that returned 401/402/403/404 is not retried for 10 minutes.
Transient failures (5xx, timeout, network) are retried after 60 seconds.
This keeps a dead cascade from costing 3 HTTP round-trips per coaching call.
"""

from __future__ import annotations

import threading
import time

HARD_TTL_S = 600.0
SOFT_TTL_S = 60.0

_HARD_STATUSES = {401, 402, 403, 404}

_lock = threading.Lock()
_state: dict[str, dict] = {}


def _now() -> float:
    return time.monotonic()


def should_attempt(provider_name: str) -> bool:
    with _lock:
        entry = _state.get(provider_name)
        if not entry:
            return True
        return _now() >= entry["until"]


def record_result(
    provider_name: str,
    http_status: int | None = None,
    error: str | None = None,
) -> None:
    """Update health after a provider call.

    Success clears the entry; hard failures (auth/payment/not-found) are
    cached for 10 minutes, everything else for 60 seconds.
    """
    with _lock:
        if http_status is not None and 200 <= http_status < 300:
            _state.pop(provider_name, None)
            return
        ttl = HARD_TTL_S if http_status in _HARD_STATUSES else SOFT_TTL_S
        _state[provider_name] = {
            "until": _now() + ttl,
            "http_status": http_status,
            "error": (error or "")[:200],
            "ttl_s": ttl,
        }


def mark_success(provider_name: str) -> None:
    with _lock:
        _state.pop(provider_name, None)


def snapshot() -> dict:
    with _lock:
        out = {}
        now = _now()
        for name, entry in _state.items():
            remaining = max(0.0, entry["until"] - now)
            out[name] = {
                "available": remaining == 0.0,
                "retry_in_s": round(remaining, 1),
                "http_status": entry.get("http_status"),
                "error": entry.get("error", ""),
            }
        return out


def reset() -> None:
    """Test helper: clear all health state."""
    with _lock:
        _state.clear()
