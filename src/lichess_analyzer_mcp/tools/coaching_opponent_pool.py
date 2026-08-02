import json
from lichess_analyzer_mcp.app import app
from lichess_analyzer_mcp.services.audit import auditable
from lichess_analyzer_mcp.services.batch_guard import BatchBudget
from lichess_analyzer_mcp.config.depth import DEPTH_DEFAULTS
from lichess_analyzer_mcp.services.lichess_client import fetch_game_pgn
from lichess_analyzer_mcp.services.game_analyzer import analyze_pgn
from lichess_analyzer_mcp.services.coaching_base import (
    collect_patterns_for_games,
    safe_llm_call,
)
from lichess_analyzer_mcp.services.prompt_builder import build_prompt
from lichess_analyzer_mcp.services.logger import get_logger

log = get_logger("coaching_opponent_pool")


def _resolve_colors(white_name: str, black_name: str, username: str = "") -> tuple[str, str]:
    """Resolve (author_color, opponent_color) from PGN header names.

    B98 fix: derives colors from headers when username is provided; otherwise
    falls back to the documented convention author=white.
    """
    author_color = "white"
    if username and username.lower() == black_name.lower():
        author_color = "black"
    opponent_color = "black" if author_color == "white" else "white"
    return author_color, opponent_color


def _opponent_won(a) -> bool:
    """True if the opponent (analysis perspective color) won the game."""
    return (a.game.color == "white" and a.game.result == "1-0") or (
        a.game.color == "black" and a.game.result == "0-1"
    )


@app.tool("lichess_coaching_opponent_pool")
@auditable
async def lichess_coaching_opponent_pool(
    game_ids: str,
    username: str = "",
    depth: int = 0,
    max_seconds: int = 0,
):
    """Opponent pool analysis — games analyzed from opponent's perspective.

    Takes game_ids where you played, flips the perspective to opponent,
    detects opponent patterns, and generates countermeasure report.

    Args:
        game_ids: Comma-separated Lichess game IDs (8 chars each)
        username: Lichess username (used to derive colors from PGN White/Black
            headers; if empty or not found, falls back to author=white)
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

                if username:
                    author_color, opponent_color = _resolve_colors(white_name, black_name, username)
                    if username.lower() != white_name and username.lower() != black_name:
                        log.warning(
                            "username %s not found in PGN headers for %s; "
                            "fallback author=white (White=%s Black=%s)",
                            username,
                            gid,
                            white_name,
                            black_name,
                        )
                else:
                    author_color, opponent_color = _resolve_colors(white_name, black_name)
                    log.info("no username for %s; fallback author=white", gid)

                opponent_analysis = analyze_pgn(
                    pgn, player_color=opponent_color, depth=depth, game_id=gid
                )
                if opponent_analysis:
                    opponent_analyses.append(opponent_analysis)

                author_analysis = analyze_pgn(
                    pgn, player_color=author_color, depth=depth, game_id=gid
                )
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

        n2_games = [a for a in opponent_analyses if _opponent_won(a)]
        n1_games = [a for a in opponent_analyses if not _opponent_won(a)]
        n1_count = len(n1_games)
        n2_count = len(n2_games)

        def _avg_acpl(games: list) -> float:
            return sum(a.total_acpl for a in games) / len(games) if games else 0.0

        def _blunder_rate(games: list) -> float:
            return (
                sum(len(a.blunders) + len(a.mistakes) for a in games) / len(games) if games else 0.0
            )

        n1_acpl = f"{_avg_acpl(n1_games):.1f}" if n1_games else "?"
        n2_acpl = f"{_avg_acpl(n2_games):.1f}" if n2_games else "?"
        n1_blunder_rate = f"{_blunder_rate(n1_games):.2f}" if n1_games else "?"
        n2_blunder_rate = f"{_blunder_rate(n2_games):.2f}" if n2_games else "?"

        prompt_data = {
            "N": len(opponent_analyses),
            "n1": n1_count,
            "n2": n2_count,
            "n1_počet": n1_count,
            "n2_počet": n2_count,
            "n1_acpl": n1_acpl,
            "n2_acpl": n2_acpl,
            "n1_blunder_rate": n1_blunder_rate,
            "n2_blunder_rate": n2_blunder_rate,
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
