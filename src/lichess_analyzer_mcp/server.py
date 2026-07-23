import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from lichess_analyzer_mcp.app import app

# P17: Workspace context at startup
_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
print(f"[server] Workspace root: {_workspace_root}", file=sys.stderr)

# Load .env from project root into os.environ
_env_path = os.path.join(_workspace_root, ".env")
if os.path.isfile(_env_path):
    with open(_env_path, encoding="utf-8-sig") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                _k = _k.strip()
                if _k and _k not in os.environ:
                    os.environ[_k] = _v.strip()
    print(
        f"[server] .env loaded ({sum(1 for k in os.environ if k.endswith('_API_KEY') or k.endswith('_TOKEN'))} keys)",
        file=sys.stderr,
    )
print(
    f"[server] Stockfish: {os.path.join(_workspace_root, 'stockfish', 'stockfish.exe')}",
    file=sys.stderr,
)
print(f"[server] Python: {sys.version}", file=sys.stderr)

# Tool imports trigger @app.tool() decorator registration
from lichess_analyzer_mcp.tools import fetch_games
from lichess_analyzer_mcp.tools import analyze_game
from lichess_analyzer_mcp.tools import analyze_position
from lichess_analyzer_mcp.tools import opening_explorer
from lichess_analyzer_mcp.tools import player_profile
from lichess_analyzer_mcp.tools import diagnose_player
from lichess_analyzer_mcp.tools import match_patterns
from lichess_analyzer_mcp.tools import workspace_info
from lichess_analyzer_mcp.tools import import_pgn

# P21: L2 Resources
from lichess_analyzer_mcp.resources import analysis_resources
from lichess_analyzer_mcp.resources import pattern_resources

# API key health check at startup (lazy — only validates env var presence, no network call)
from lichess_analyzer_mcp.services.llm_client import list_available_providers

_key_available = list_available_providers()
for ka in _key_available:
    print(f"[server] API key found: {ka['provider']}", file=sys.stderr)
if not _key_available:
    print(
        "[server] WARNING: No LLM API keys configured — coaching will use fallback only",
        file=sys.stderr,
    )


def main():
    app.run()


if __name__ == "__main__":
    main()
