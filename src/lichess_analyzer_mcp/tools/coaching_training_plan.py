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

log = get_logger("coaching_training_plan")


@app.tool("lichess_coaching_training_plan")
@auditable
async def lichess_coaching_training_plan(
    username: str,
    max_games: int = 20,
    hours_per_week: int = 5,
    rating: int = 0,
    depth: int = 0,
    result: str = "all",
    max_seconds: int = 0,
):
    """Personalized training plan based on cross-game diagnostics.

    Analyzes recent games, detects patterns, diagnoses weaknesses,
    and generates a structured monthly training plan.

    Args:
        username: Lichess username
        max_games: Number of games to analyze (5-50)
        hours_per_week: Available training hours per week
        rating: Current rating (0 = unknown)
        depth: Stockfish depth (8-18, 0=auto)
        result: Filter - 'all', 'win', 'loss', 'draw'
        max_seconds: Max wall-clock seconds for this batch (0 = unlimited).
            Returns unprocessed_ids when budget is exceeded.
    """
    max_games = max(5, min(999, max_games))
    if depth == 0:
        depth = DEPTH_DEFAULTS["batch"]["diagnose"]
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

        top_weaknesses_str = ""
        if weakness and weakness.get("top_weaknesses"):
            for i, w in enumerate(weakness["top_weaknesses"][:3], 1):
                top_weaknesses_str += f"  {i}. {w}\n"

        prompt_data = {
            "N": len(analyses),
            "username": username,
            "rating": rating or "unknown",
            "tc": "mixed",
            "hours_week": hours_per_week,
            "questions": "Z diagnostiky: co je největší slabina?",
            "weakness_json": json.dumps(weakness, ensure_ascii=False, indent=2)
            if weakness
            else "{}",
            "patterns_json": json.dumps(patterns, ensure_ascii=False, indent=2),
            "top_weaknesses": top_weaknesses_str,
        }
        prompt = build_prompt(4, prompt_data)
        report, cascade_log = safe_llm_call(prompt, f"training_plan:{username}")

        return {
            "username": username,
            "games_analyzed": len(analyses),
            "hours_per_week": hours_per_week,
            "report": report,
            "patterns": patterns[:5],
            "weakness": weakness,
            "cascade_log": cascade_log,
            "unprocessed_ids": unprocessed_ids,
            "elapsed_seconds": round(budget.elapsed, 1),
            "budget_exceeded": bool(unprocessed_ids),
        }
    except Exception as e:
        log.exception("coaching training plan error | user=%s", username)
        return {"error": str(e)}
