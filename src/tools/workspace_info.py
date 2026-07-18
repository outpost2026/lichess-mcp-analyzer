"""P17: Workspace context export for LLM agents."""

import os
import sys
from src.app import app


@app.tool("lichess_workspace_info")
async def lichess_workspace_info():
    """Returns workspace context for LLM agent orientation.

    Provides root path, stockfish status, Python version,
    and registered tools count.
    """
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    sf_path = os.path.join(root, "stockfish", "stockfish.exe")
    stockfish_ok = os.path.isfile(sf_path)
    token_set = bool(os.environ.get("LICHESS_TOKEN")) or bool(os.environ.get("LICHESS_TOKEN_FILE"))

    tools = app._tool_manager.list_tools()

    return {
        "workspace_root": root,
        "server_name": "lichess-analyzer",
        "python_version": sys.version.split()[0],
        "stockfish_installed": stockfish_ok,
        "stockfish_path": sf_path if stockfish_ok else None,
        "lichess_token_configured": token_set,
        "tools_total": len(tools),
        "tools": [t.name for t in tools],
    }
