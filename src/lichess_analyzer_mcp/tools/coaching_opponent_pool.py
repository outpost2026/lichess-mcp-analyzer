import json
from lichess_analyzer_mcp.app import app
from lichess_analyzer_mcp.services.audit import auditable
from lichess_analyzer_mcp.services.batch_guard import BatchBudget
from lichess_analyzer_mcp.config.depth import DEPTH_DEFAULTS
from lichess_analyzer_mcp.services.lichess_client import fetch_game_pgn
from lichess_analyzer_mcp.services.game_analyzer import analyze_pgn, _load_cached_analysis
from lichess_analyzer_mcp.services.coaching_base import (
    collect_patterns_for_games,
    safe_llm_call,
)
from lichess_analyzer_mcp.services.prompt_builder import build_prompt
from lichess_analyzer_mcp.services.logger import get_logger

log = get_logger("coaching_opponent_pool")


@app.tool("lichess_coaching_opponent_pool")
@auditable
async def lichess_coaching_opponent_pool(
    game_ids: str,
    depth: int = 0,
    max_seconds: int = 0,
):
    """Opponent pool analysis — games analyzed from opponent's perspective.

    Takes game_ids where you played, flips the perspective to opponent,
    detects opponent patterns, and generates countermeasure report.

    Args:
        game_ids: Comma-separated Lichess game IDs (8 chars each)
        depth: Stockfish depth (8-18, 0=auto)
        max_seconds: Max wall-clock seconds for this batch (0 = unlimited).
            Returns unprocessed_ids when budget is exceeded.
    """
    if depth == 0:
        depth = DEPTH_DEFAULTS["batch"]["patterns"]
    depth = max(DEPTH_DEFAULTS["limits"]["min"], min(DEPTH_DEFAULTS["limits"]["max_batch"], depth))

    ids = [g.strip()[:8] for g in game_ids.split(",") if g.strip()]
    if not ids:
        return {"error": "Provide at least one game_id"}

    try:
        opponent_analyses = []
        author_analyses = []
        unprocessed_ids = []
        budget = BatchBudget(max_seconds)

        for gid in ids:
            if budget.exceeded:
                unprocessed_ids.append(gid)
                continue
            try:
                pgn = fetch_game_pgn(gid)
                if not pgn:
                    log.warning("empty pgn for %s", gid)
                    continue

                if "White" not in pgn.split("\n\n")[0]:
                    continue

                headers_line = pgn.split("\n\n")[0]
                import chess.pgn
                import io

                game = chess.pgn.read_game(io.StringIO(pgn))
                if game is None:
                    continue
                white_name = (game.headers.get("White") or "").lower()
                black_name = (game.headers.get("Black") or "").lower()

                opponent_color = "black"
                opponent_analysis = analyze_pgn(
                    pgn, player_color=opponent_color, depth=depth, game_id=gid
                )
                if opponent_analysis:
                    opponent_analyses.append(opponent_analysis)

                author_analysis = _load_cached_analysis(gid, depth, "white")
                if author_analysis:
                    author_analyses.append(author_analysis)
            except Exception as e:
                log.warning("skip %s: %s", gid, e)

        if not opponent_analyses:
            if unprocessed_ids:
                return {
                    "ids": ids,
                    "opponent_games_analyzed": 0,
                    "author_games_analyzed": 0,
                    "error": "No opponent analyses could be produced within budget",
                    "unprocessed_ids": unprocessed_ids,
                    **budget.to_dict(),
                }
            return {"error": "No opponent analyses could be produced"}

        opponent_patterns = collect_patterns_for_games(opponent_analyses, "opponent")
        author_patterns = (
            collect_patterns_for_games(author_analyses, "author") if author_analyses else []
        )

        n1_count = sum(
            1
            for a in opponent_analyses
            if getattr(a, "result", "") in ("0-1", "1-0")
            and getattr(a, "player_color", "") == "black"
        )
        n2_count = len(opponent_analyses) - n1_count

        prompt_data = {
            "N": len(opponent_analyses),
            "n1_počet": n1_count,
            "n2_počet": n2_count,
            "n1_acpl": "?",
            "n2_acpl": "?",
            "n1_blunder_rate": "?",
            "n2_blunder_rate": "?",
            "opponent_patterns_json": json.dumps(opponent_patterns, ensure_ascii=False, indent=2),
            "author_patterns_json": json.dumps(author_patterns, ensure_ascii=False, indent=2),
        }

        prompt = build_prompt(3, prompt_data)
        report, cascade_log = safe_llm_call(prompt, f"opponent_pool:{','.join(ids)}")

        return {
            "ids": ids,
            "opponent_games_analyzed": len(opponent_analyses),
            "author_games_analyzed": len(author_analyses),
            "report": report,
            "opponent_patterns": opponent_patterns,
            "cascade_log": cascade_log,
            "unprocessed_ids": unprocessed_ids,
            "elapsed_seconds": round(budget.elapsed, 1),
            "budget_exceeded": bool(unprocessed_ids),
        }
    except Exception as e:
        log.exception("coaching opponent pool error")
        return {"error": str(e)}
