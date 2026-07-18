"""P21: L2 Resources for analysis results."""

import json
from datetime import datetime
from src.app import app

_analysis_store: dict = {}


def store_analysis(key: str, data: dict):
    _analysis_store[key] = {
        "data": data,
        "ts": datetime.utcnow().isoformat(),
    }
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
