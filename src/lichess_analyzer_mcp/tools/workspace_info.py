"""P17: Workspace context export for LLM agents."""

import os
import sys
from lichess_analyzer_mcp.app import app

_KNOWN_TOOLS = [
    "lichess_fetch_games",
    "lichess_analyze_game",
    "lichess_analyze_position",
    "lichess_opening_explorer",
    "lichess_player_profile",
    "lichess_diagnose_player",
    "lichess_match_patterns",
    "lichess_workspace_info",
    "lichess_import_pgn",
]


@app.tool("lichess_workspace_info")
async def lichess_workspace_info():
    """Returns workspace context for LLM agent orientation.

    Provides root path, stockfish status, Python version,
    and registered tools count.
    """
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    sf_path = os.path.join(root, "stockfish", "stockfish.exe")
    stockfish_ok = os.path.isfile(sf_path)
    token_set = bool(os.environ.get("LICHESS_TOKEN")) or bool(os.environ.get("LICHESS_TOKEN_FILE"))

    try:
        tools = list(app._tool_manager.list_tools())
    except AttributeError:
        tools = []

    return {
        "workspace_root": root,
        "server_name": "lichess-analyzer",
        "python_version": sys.version.split()[0],
        "stockfish_installed": stockfish_ok,
        "stockfish_path": sf_path if stockfish_ok else None,
        "lichess_token_configured": token_set,
        "tools_total": len(tools) or len(_KNOWN_TOOLS),
        "tools": [t.name for t in tools] if tools else _KNOWN_TOOLS,
    }
