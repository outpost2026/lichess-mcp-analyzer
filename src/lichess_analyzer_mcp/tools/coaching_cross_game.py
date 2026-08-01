import json
from lichess_analyzer_mcp.app import app
from lichess_analyzer_mcp.services.audit import auditable
from lichess_analyzer_mcp.services.batch_guard import BatchBudget
from lichess_analyzer_mcp.config.depth import DEPTH_DEFAULTS
from lichess_analyzer_mcp.services.lichess_client import fetch_user_games, fetch_game_pgn
from lichess_analyzer_mcp.services.game_analyzer import analyze_pgn, _load_cached_analysis
from lichess_analyzer_mcp.services.coaching_base import (
    collect_patterns_for_games,
    collect_weakness_report,
    safe_llm_call,
)
from lichess_analyzer_mcp.services.prompt_builder import build_prompt
from lichess_analyzer_mcp.services.logger import get_logger

log = get_logger("coaching_cross_game")


@app.tool("lichess_coaching_cross_game")
@auditable
async def lichess_coaching_cross_game(
    username: str,
    max_games: int = 20,
    depth: int = 0,
    result: str = "all",
    max_seconds: int = 0,
):
    """Cross-game pattern analysis with LLM coaching report.

    Aggregates N games, detects recurring patterns, diagnoses weaknesses,
    and generates a prioritized coaching report.

    Args:
        username: Lichess username
        max_games: Number of games to analyze (5-50)
        depth: Stockfish depth (8-18, 0=auto)
        result: Filter - 'all', 'win', 'loss', 'draw'
        max_seconds: Max wall-clock seconds for this batch (0 = unlimited).
            Returns unprocessed_ids when budget is exceeded.
    """
    max_games = max(5, min(999, max_games))
    if depth == 0:
        depth = DEPTH_DEFAULTS["batch"]["patterns"]
    depth = max(DEPTH_DEFAULTS["limits"]["min"], min(DEPTH_DEFAULTS["limits"]["max_batch"], depth))

    if not username:
        return {"error": "Provide username"}

    try:
        games_data = fetch_user_games(username, max_games=max_games, result=result)
        analyses = []
        unprocessed_ids = []
        budget = BatchBudget(max_seconds)
        for g in games_data[:max_games]:
            game_id = g.get("id", "")
            if budget.exceeded:
                unprocessed_ids.append(game_id)
                continue
            try:
                color = "white"
                if (
                    g.get("players", {}).get("black", {}).get("user", {}).get("name", "").lower()
                    == username.lower()
                ):
                    color = "black"
                cached = _load_cached_analysis(game_id, depth, color)
                if cached is not None:
                    analyses.append(cached)
                    continue
                pgn = fetch_game_pgn(game_id)
                a = analyze_pgn(pgn, player_color=color, depth=depth, game_id=game_id)
                if a:
                    analyses.append(a)
            except Exception as e:
                log.warning("skip %s: %s", game_id, e)

        if not analyses:
            if unprocessed_ids:
                return {
                    "username": username,
                    "games_analyzed": 0,
                    "error": "No games could be analyzed within budget",
                    "unprocessed_ids": unprocessed_ids,
                    **budget.to_dict(),
                }
            return {"error": "No games could be analyzed"}

        patterns = collect_patterns_for_games(analyses, username)
        weakness = collect_weakness_report(analyses, username)

        pattern_ranking = "\n".join(
            f"{i + 1}. {p['pattern_name']} — frequency={p['frequency']}, severity={p['severity']}, confidence={p['confidence']}%"
            for i, p in enumerate(patterns[:10])
        )

        prompt_data = {
            "N": len(analyses),
            "username": username,
            "patterns_json": json.dumps(patterns, ensure_ascii=False, indent=2),
            "weakness_json": json.dumps(weakness, ensure_ascii=False, indent=2)
            if weakness
            else "{}",
            "pattern_ranking": pattern_ranking,
        }
        prompt = build_prompt(2, prompt_data)
        report, cascade_log = safe_llm_call(prompt, f"cross_game:{username}")

        return {
            "username": username,
            "games_analyzed": len(analyses),
            "report": report,
            "patterns": patterns,
            "weakness": weakness,
            "cascade_log": cascade_log,
            "unprocessed_ids": unprocessed_ids,
            "elapsed_seconds": round(budget.elapsed, 1),
            "budget_exceeded": bool(unprocessed_ids),
        }
    except Exception as e:
        log.exception("coaching cross game error | user=%s", username)
        return {"error": str(e)}
