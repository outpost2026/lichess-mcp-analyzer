import json
from collections import defaultdict
from lichess_analyzer_mcp.app import app
from lichess_analyzer_mcp.services.audit import auditable
from lichess_analyzer_mcp.services.batch_guard import BatchBudget
from lichess_analyzer_mcp.config.depth import DEPTH_DEFAULTS
from lichess_analyzer_mcp.services.lichess_client import fetch_user_games, fetch_game_pgn
from lichess_analyzer_mcp.services.game_analyzer import analyze_pgn, _load_cached_analysis
from lichess_analyzer_mcp.services.coaching_base import (
    collect_patterns_for_games,
    safe_llm_call,
)
from lichess_analyzer_mcp.services.prompt_builder import build_prompt
from lichess_analyzer_mcp.services.logger import get_logger

log = get_logger("coaching_opening_report")


@app.tool("lichess_coaching_opening_report")
@auditable
async def lichess_coaching_opening_report(
    username: str,
    max_games: int = 20,
    depth: int = 0,
    result: str = "all",
    max_seconds: int = 0,
):
    """Opening repertoire report based on recent games.

    Analyzes performance per opening, identifies leaky lines,
    and generates repertoire recommendations.

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
        analyses_with_opening = []
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
                    analyses_with_opening.append(cached)
                    continue
                pgn = fetch_game_pgn(game_id)
                a = analyze_pgn(pgn, player_color=color, depth=depth, game_id=game_id)
                if a:
                    analyses_with_opening.append(a)
            except Exception as e:
                log.warning("skip %s: %s", game_id, e)

        if not analyses_with_opening:
            if unprocessed_ids:
                return {
                    "username": username,
                    "games_analyzed": 0,
                    "error": "No games could be analyzed within budget",
                    "unprocessed_ids": unprocessed_ids,
                    **budget.to_dict(),
                }
            return {"error": "No games could be analyzed"}

        patterns = collect_patterns_for_games(analyses_with_opening, username)

        white_by_opening = defaultdict(list)
        black_by_opening = defaultdict(list)

        for a in analyses_with_opening:
            opening = getattr(a, "opening_name", "Unknown") or "Unknown"
            color = getattr(a, "player_color", "white")
            acpl = getattr(a, "acpl", None) or 0
            result_val = getattr(a, "result", "*")
            if color == "white":
                white_by_opening[opening].append({"acpl": acpl, "result": result_val})
            else:
                black_by_opening[opening].append({"acpl": acpl, "result": result_val})

        def format_openings(data: dict) -> str:
            lines = []
            for opening, games_list in sorted(data.items(), key=lambda x: len(x[1]), reverse=True):
                n = len(games_list)
                avg_acpl = sum(g["acpl"] for g in games_list) / n if n else 0
                wins = sum(1 for g in games_list if g["result"] == "1-0")
                losses = sum(1 for g in games_list if g["result"] == "0-1")
                wr = wins / n if n else 0
                lines.append(f"  - {opening} ({n} her): win_rate={wr:.0%}, ACPL={avg_acpl:.0f}")
            return "\n".join(lines) or "  (žádná data)"

        def top_worst(data: dict, top: int = 3) -> str:
            items = sorted(
                data.items(),
                key=lambda x: sum(g["acpl"] for g in x[1]) / len(x[1]) if x[1] else 0,
                reverse=True,
            )
            lines = []
            for opening, games_list in items[:top]:
                n = len(games_list)
                avg_acpl = sum(g["acpl"] for g in games_list) / n if n else 0
                lines.append(f"  - {opening}: ACPL={avg_acpl:.0f} ({n} her)")
            return "\n".join(lines) or "  (žádná data)"

        def top_best(data: dict, top: int = 3) -> str:
            items = sorted(
                data.items(),
                key=lambda x: sum(g["acpl"] for g in x[1]) / len(x[1]) if x[1] else 9999,
            )
            lines = []
            for opening, games_list in items[:top]:
                n = len(games_list)
                avg_acpl = sum(g["acpl"] for g in games_list) / n if n else 0
                lines.append(f"  - {opening}: ACPL={avg_acpl:.0f} ({n} her)")
            return "\n".join(lines) or "  (žádná data)"

        prompt_data = {
            "N": len(analyses_with_opening),
            "username": username,
            "patterns_json": json.dumps(patterns, ensure_ascii=False, indent=2),
            "white_openings": format_openings(dict(white_by_opening)),
            "black_openings": format_openings(dict(black_by_opening)),
            "worst_openings": top_worst({**dict(white_by_opening), **dict(black_by_opening)}),
            "best_openings": top_best({**dict(white_by_opening), **dict(black_by_opening)}),
        }
        prompt = build_prompt(5, prompt_data)
        report, cascade_log = safe_llm_call(prompt, f"opening_report:{username}")

        return {
            "username": username,
            "games_analyzed": len(analyses_with_opening),
            "report": report,
            "patterns": patterns,
            "opening_stats": {
                "white": {k: len(v) for k, v in white_by_opening.items()},
                "black": {k: len(v) for k, v in black_by_opening.items()},
            },
            "cascade_log": cascade_log,
            "unprocessed_ids": unprocessed_ids,
            "elapsed_seconds": round(budget.elapsed, 1),
            "budget_exceeded": bool(unprocessed_ids),
        }
    except Exception as e:
        log.exception("coaching opening report error | user=%s", username)
        return {"error": str(e)}
