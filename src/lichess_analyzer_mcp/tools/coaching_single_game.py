import json
from lichess_analyzer_mcp.app import app
from lichess_analyzer_mcp.config.depth import DEPTH_DEFAULTS
from lichess_analyzer_mcp.services.coaching_base import (
    collect_single_game,
    collect_patterns_for_games,
    safe_llm_call,
)
from lichess_analyzer_mcp.services.prompt_builder import build_prompt
from lichess_analyzer_mcp.services.logger import get_logger

log = get_logger("coaching_single_game")


@app.tool("lichess_coaching_single_game")
async def lichess_coaching_single_game(
    game_id: str,
    color: str = "white",
    depth: int = 0,
):
    """Deep coaching report for a single game.

    Fetches PGN, runs Stockfish analysis, detects patterns,
    and generates an LLM coaching report. Depth 0 = auto (14).

    Args:
        game_id: Lichess game ID (8 chars)
        color: Your color ('white' or 'black')
        depth: Stockfish analysis depth (8-24, 0=auto)
    """
    if depth == 0:
        depth = DEPTH_DEFAULTS["standard"]["single_game"]
    depth = max(
        DEPTH_DEFAULTS["limits"]["min"], min(DEPTH_DEFAULTS["limits"]["max_single_game"], depth)
    )

    try:
        data = collect_single_game(game_id, color, depth)
        analysis = data.get("analysis", {})
        patterns = collect_patterns_for_games([analysis], "lichess")

        prompt_data = {
            "game_id": game_id,
            "color": color,
            "depth": depth,
            "patterns_json": json.dumps(patterns, ensure_ascii=False, indent=2),
        }
        prompt = build_prompt(1, prompt_data)
        report, cascade_log = safe_llm_call(prompt, f"single_game:{game_id}")

        return {
            "game_id": game_id,
            "color": color,
            "depth": depth,
            "report": report,
            "patterns": patterns,
            "cascade_log": cascade_log,
        }
    except Exception as e:
        log.exception("coaching single game error | game=%s", game_id)
        return {"error": str(e), "game_id": game_id}
