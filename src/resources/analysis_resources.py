"""P21: L2 Resources for analysis results."""

import json
import os
from datetime import datetime
from src.app import app

STORE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "resource_store")
STORE_FILE = os.path.join(STORE_DIR, "analysis_store.json")

_analysis_store: dict = {}


def _load_store():
    global _analysis_store
    if not os.path.isfile(STORE_FILE):
        return
    try:
        with open(STORE_FILE, "r", encoding="utf-8") as f:
            _analysis_store = json.load(f)
    except (OSError, json.JSONDecodeError):
        pass


def _save_store():
    os.makedirs(STORE_DIR, exist_ok=True)
    tmp = STORE_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(_analysis_store, f, ensure_ascii=False)
        os.replace(tmp, STORE_FILE)
    except OSError:
        pass


_load_store()


def store_analysis(key: str, data: dict):
    _analysis_store[key] = {
        "data": data,
        "ts": datetime.utcnow().isoformat(),
    }
    _save_store()
    return f"lichess://analysis/{key}"


@app.resource("lichess://analysis/{key}")
async def get_analysis_resource(key: str) -> str:
    """Returns stored analysis data by key (username_timestamp)."""
    entry = _analysis_store.get(key)
    if not entry:
        return json.dumps({"error": f"Analysis '{key}' not found"}, ensure_ascii=False, indent=2)
    return json.dumps(entry["data"], ensure_ascii=False, indent=2)


@app.resource("lichess://analysis/list")
async def list_analysis_resources() -> str:
    """Lists all stored analysis results."""
    keys = list(_analysis_store.keys())
    return json.dumps({"resources": keys, "total": len(keys)}, ensure_ascii=False, indent=2)
