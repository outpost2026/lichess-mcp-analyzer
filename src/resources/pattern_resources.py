"""P21: L2 Resources for pattern detection results."""

import json
from datetime import datetime
from src.app import app

_pattern_store: dict = {}


def store_patterns(key: str, data: dict):
    _pattern_store[key] = {
        "data": data,
        "ts": datetime.utcnow().isoformat(),
    }
    return f"lichess://patterns/{key}"


@app.resource("lichess://patterns/{key}")
async def get_pattern_resource(key: str) -> str:
    """Returns stored pattern data by key (username_timestamp)."""
    entry = _pattern_store.get(key)
    if not entry:
        return json.dumps({"error": f"Patterns '{key}' not found"}, ensure_ascii=False, indent=2)
    return json.dumps(entry["data"], ensure_ascii=False, indent=2)


@app.resource("lichess://patterns/list")
async def list_pattern_resources() -> str:
    """Lists all stored pattern detection results."""
    keys = list(_pattern_store.keys())
    return json.dumps({"resources": keys, "total": len(keys)}, ensure_ascii=False, indent=2)
