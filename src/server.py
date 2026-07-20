import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.app import app

# P17: Workspace context at startup
_workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
print(f"[server] Workspace root: {_workspace_root}", file=sys.stderr)
print(
    f"[server] Stockfish: {os.path.join(_workspace_root, 'stockfish', 'stockfish.exe')}",
    file=sys.stderr,
)
print(f"[server] Python: {sys.version}", file=sys.stderr)

# Tool imports trigger @app.tool() decorator registration
from src.tools import fetch_games
from src.tools import analyze_game
from src.tools import analyze_position
from src.tools import opening_explorer
from src.tools import player_profile
from src.tools import diagnose_player
from src.tools import match_patterns
from src.tools import workspace_info
from src.tools import import_pgn

# P21: L2 Resources
from src.resources import analysis_resources
from src.resources import pattern_resources

# API key health check at startup (lazy — only validates env var presence, no network call)
from src.services.llm_client import list_available_providers

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
