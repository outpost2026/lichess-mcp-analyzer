"""P5: Per-tool audit metrics (ts, tool, duration_s, ok) for MCP tools.

Writes one JSONL entry per tool call to logs/audit_YYYYMM.jsonl.
Async-aware decorator; wraps the coroutine and measures wall-clock time.
functools.wraps preserves __wrapped__ so FastMCP schema introspection
keeps the original tool signature.
"""

import json
import os
import time
from datetime import UTC, datetime
from functools import wraps

from lichess_analyzer_mcp.services.logger import get_logger

log = get_logger("audit")

AUDIT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs")
AUDIT_FILE = os.path.join(AUDIT_DIR, f"audit_{datetime.now(UTC).strftime('%Y%m')}.jsonl")


def _write_entry(entry: dict) -> None:
    try:
        os.makedirs(AUDIT_DIR, exist_ok=True)
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        log.warning("audit write failed: %s", e)


def auditable(func):
    """Log per-call audit metric. Sets ok=False on error-dict return or exception."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        started = time.monotonic()
        tool = func.__name__
        ok = True
        error = None
        try:
            result = await func(*args, **kwargs)
            if isinstance(result, dict) and result.get("error") is not None:
                ok = False
                error = result.get("error")
            return result
        except Exception as e:
            ok = False
            error = e
            raise
        finally:
            entry = {
                "ts": datetime.now(UTC).isoformat(),
                "tool": tool,
                "duration_s": round(time.monotonic() - started, 3),
                "ok": bool(ok),
            }
            if error is not None:
                entry["error"] = str(error)[:300]
            _write_entry(entry)

    return wrapper
