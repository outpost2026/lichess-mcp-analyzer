"""Batch analyzer for pending (uncached) games.

After lichess_fetch_games fetches new games that lack Stockfish analysis
cache, this tool processes them: fetch PGN -> Stockfish analysis -> save
cache -> update index.  Reports progress per game and final summary.
"""

from lichess_analyzer_mcp.app import app
from lichess_analyzer_mcp.services.audit import auditable
from lichess_analyzer_mcp.services.batch_guard import BatchBudget
from lichess_analyzer_mcp.config.depth import DEPTH_DEFAULTS
from lichess_analyzer_mcp.services.lichess_client import (
    fetch_user_games,
    fetch_game_pgn,
    get_pending_analysis,
    update_games_index_with_game,
)
from lichess_analyzer_mcp.services.game_analyzer import analyze_pgn
from lichess_analyzer_mcp.services.logger import get_logger

log = get_logger("analyze_pending")


@app.tool("lichess_analyze_pending")
@auditable
async def lichess_analyze_pending(
    username: str = "Systeq", depth: int = 0, max_games: int = 0, max_seconds: int = 0
):
    """Analyze all pending (uncached) games in batch.

    Detects which games from the user's fetched list lack per-game
    Stockfish analysis cache and processes them one by one.  After
    completion, the entire dataset is consistent — match_patterns
    and diagnose_player will report 0 pending.

    Args:
        username: Lichess username
        depth: Stockfish analysis depth (8-18, default 12 — 0=auto)
        max_games: Max games to process (0 = all pending)
        max_seconds: Max wall-clock seconds for this batch (0 = unlimited).
            Returns unprocessed_ids when budget is exceeded.
    """
    if depth == 0:
        depth = DEPTH_DEFAULTS["batch"]["pending"]
    depth = max(DEPTH_DEFAULTS["limits"]["min"], min(DEPTH_DEFAULTS["limits"]["max_batch"], depth))

    pending = get_pending_analysis(username, depth)
    if not pending:
        return {
            "username": username,
            "status": "complete",
            "analyzed": 0,
            "total_pending": 0,
            "message": "All games are already cached — nothing to analyze.",
        }

    if max_games > 0:
        pending = pending[:max_games]

    # B4: Estimated time reporting
    AVG_TIME_PER_GAME = {12: 58, 14: 84, 18: 588}
    est_seconds = len(pending) * AVG_TIME_PER_GAME.get(depth, 84)
    if est_seconds > 900:
        log.warning(
            "estimated batch time %.0fs (%d games at depth=%d) exceeds 15min limit",
            est_seconds,
            len(pending),
            depth,
        )

    results = []
    errors = 0
    unprocessed_ids = []
    budget = BatchBudget(max_seconds)

    for i, game_id in enumerate(pending):
        if budget.exceeded:
            unprocessed_ids.append(game_id)
            continue
        log.info("analyze_pending [%d/%d] game_id=%s", i + 1, len(pending), game_id)
        try:
            pgn = fetch_game_pgn(game_id)

            # Determine player color from game data
            games_data = fetch_user_games(username, max_games=1)
            color = "white"
            for g in games_data:
                if g.get("id") == game_id:
                    white_name = (
                        g.get("players", {}).get("white", {}).get("user", {}).get("name", "") or ""
                    )
                    if white_name.lower() == username.lower():
                        color = "white"
                    else:
                        color = "black"
                    break

            a = analyze_pgn(pgn, player_color=color, depth=depth, game_id=game_id)
            if a:
                results.append({"game_id": game_id, "status": "ok", "acpl": round(a.total_acpl, 1)})
            else:
                results.append({"game_id": game_id, "status": "empty_analysis"})
                errors += 1
        except Exception as e:
            log.warning("analyze_pending error game_id=%s: %s", game_id, e)
            results.append({"game_id": game_id, "status": "error", "detail": str(e)})
            errors += 1

    # After batch is done, update index for each successfully analyzed game
    for r in results:
        if r["status"] == "ok":
            try:
                update_games_index_with_game(username, r["game_id"])
            except Exception:
                pass

    # Final pending check
    remaining = get_pending_analysis(username, depth)

    return {
        "username": username,
        "status": "complete" if not unprocessed_ids else "partial",
        "analyzed": len([r for r in results if r["status"] == "ok"]),
        "errors": errors,
        "total_pending": len(pending),
        "remaining": len(remaining),
        "estimated_seconds": est_seconds,
        "results": results,
        "unprocessed_ids": unprocessed_ids,
        "elapsed_seconds": round(budget.elapsed, 1),
        "budget_exceeded": bool(unprocessed_ids),
        "suggestion": (
            "All games cached — dataset is fully consistent."
            if not remaining
            else (
                f"{len(remaining)} game(s) still pending. Increase depth or check for API errors."
                if not unprocessed_ids
                else (
                    f"{len(unprocessed_ids)} game(s) not processed (budget). "
                    "Call again with higher max_seconds."
                )
            )
        ),
    }
