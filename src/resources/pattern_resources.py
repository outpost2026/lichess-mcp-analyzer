"""P21: L2 Resources for pattern detection results."""

import json
import os
from datetime import datetime
from src.app import app

STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "resource_store")
STORE_FILE = os.path.join(STORE_DIR, "pattern_store.json")

_pattern_store: dict = {}


def _load_store():
    global _pattern_store
    if not os.path.isfile(STORE_FILE):
        return
    try:
        with open(STORE_FILE, "r", encoding="utf-8") as f:
            _pattern_store = json.load(f)
    except (OSError, json.JSONDecodeError):
        pass


def _save_store():
    os.makedirs(STORE_DIR, exist_ok=True)
    tmp = STORE_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_pattern_store, f, ensure_ascii=False)
        os.replace(tmp, STORE_FILE)
    except OSError:
        pass


_load_store()


def store_patterns(key: str, data: dict):
    _pattern_store[key] = {
        "data": data,
        "ts": datetime.utcnow().isoformat(),
    }
    _save_store()
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
