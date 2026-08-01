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
    f"[server] Stockfish: {os.path.join(_workspace_root, 'stockfish', 'stockfish-bmi2.exe')}",
    file=sys.stderr,
)
print(f"[server] Python: {sys.version}", file=sys.stderr)

# Tool imports trigger @app.tool() decorator registration (side-effect imports)
from lichess_analyzer_mcp.tools import fetch_games  # noqa: F401
from lichess_analyzer_mcp.tools import analyze_game  # noqa: F401
from lichess_analyzer_mcp.tools import analyze_position  # noqa: F401
from lichess_analyzer_mcp.tools import opening_explorer  # noqa: F401
from lichess_analyzer_mcp.tools import player_profile  # noqa: F401
from lichess_analyzer_mcp.tools import diagnose_player  # noqa: F401
from lichess_analyzer_mcp.tools import match_patterns  # noqa: F401
from lichess_analyzer_mcp.tools import workspace_info  # noqa: F401
from lichess_analyzer_mcp.tools import import_pgn  # noqa: F401
from lichess_analyzer_mcp.tools import analyze_pending  # noqa: F401
from lichess_analyzer_mcp.tools import anonymous_session  # noqa: F401

# Coaching tools
from lichess_analyzer_mcp.tools import coaching_single_game  # noqa: F401
from lichess_analyzer_mcp.tools import coaching_cross_game  # noqa: F401
from lichess_analyzer_mcp.tools import coaching_opponent_pool  # noqa: F401
from lichess_analyzer_mcp.tools import coaching_training_plan  # noqa: F401
from lichess_analyzer_mcp.tools import coaching_opening_report  # noqa: F401

# On-demand persistence
from lichess_analyzer_mcp.tools import persist_report  # noqa: F401

# P21: L2 Resources
from lichess_analyzer_mcp.resources import analysis_resources  # noqa: F401
from lichess_analyzer_mcp.resources import pattern_resources  # noqa: F401

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
