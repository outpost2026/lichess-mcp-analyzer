"""P17: Workspace context export for LLM agents.

Review 2026-11-18: no hardcoded tool list and no private FastMCP internals.
The tool inventory always comes from the live registry; the Stockfish binary
name is resolved from config/engine_identity.json per platform.
"""

import json
import os
import sys

from lichess_analyzer_mcp.app import app
from lichess_analyzer_mcp.services.audit import auditable

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_ENGINE_CONFIG = os.path.join(_ROOT, "config", "engine_identity.json")


def _stockfish_path(root: str) -> str | None:
    try:
        with open(_ENGINE_CONFIG, encoding="utf-8-sig") as fh:
            cfg = json.load(fh)
        key = "local_windows_bmi2" if os.name == "nt" else "linux_ci"
        field = "binary" if key == "local_windows_bmi2" else "binary_in_archive"
        name = os.path.basename(cfg[key][field])
    except (OSError, ValueError, KeyError):
        name = "stockfish-bmi2.exe" if os.name == "nt" else "stockfish"
    candidate = os.path.join(root, "stockfish", name)
    return candidate if os.path.isfile(candidate) else None


@app.tool("lichess_workspace_info")
@auditable
async def lichess_workspace_info():
    """Return workspace context for LLM agent orientation (live registry)."""
    sf = _stockfish_path(_ROOT)
    token_set = bool(os.environ.get("LICHESS_TOKEN")) or bool(os.environ.get("LICHESS_TOKEN_FILE"))

    try:
        tools = list(await app.list_tools())
    except (AttributeError, TypeError):
        tools = []

    return {
        "workspace_root": _ROOT,
        "server_name": "lichess-analyzer",
        "python_version": sys.version.split()[0],
        "stockfish_installed": sf is not None,
        "stockfish_path": sf,
        "lichess_token_configured": token_set,
        "tools_total": len(tools),
        "tools": [getattr(t, "name", str(t)) for t in tools],
    }
