from src.app import app
from src.services.lichess_client import fetch_user_games, fetch_game_pgn
from src.services.game_analyzer import analyze_pgn, _load_cached_analysis
from src.services.diagnostician import diagnose
from src.services.logger import get_logger

log = get_logger("diagnose_player")


@app.tool("lichess_diagnose_player")
async def lichess_diagnose_player(username: str, max_games: int = 20, depth: int = 12):
    """Diagnoses a player's weaknesses across multiple games.

    Analyzes recent games and identifies recurring tactical blind spots,
    phase weaknesses (opening/middlegame/endgame), leaky openings,
    and pattern frequencies. Uses cache-first — analyze games individually
    first via lichess_analyze_game to build cache, then run this for instant
    cross-game diagnosis. Structured logging per P19.

    Args:
        username: Lichess username
        max_games: Number of recent games to analyze (5-50)
        depth: Stockfish depth for analysis (8-18, lower = faster)
    """
    max_games = max(5, min(50, max_games))
    depth = max(8, min(18, depth))
    try:
        games_data = fetch_user_games(username, max_games=max_games)
        total_available = len(games_data)
        log.info(
            "diagnose start | user=%s | requested=%d | available=%d | depth=%d",
            username,
            max_games,
            total_available,
            depth,
        )

        analyses = []
        skipped = 0

        for g in games_data[:max_games]:
            game_id = g.get("id", "")
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
                else:
                    skipped += 1
                    log.warning("empty analysis for %s", game_id)
            except Exception as e:
                log.warning("skip game %s: %s", game_id, e)
                skipped += 1

        if not analyses:
            log.error("0 games analyzed | user=%s", username)
            return {"error": "No games could be analyzed"}

        log.info(
            "diagnose done | user=%s | analyzed=%d | skipped=%d", username, len(analyses), skipped
        )
        report = diagnose(analyses, username)
        from datetime import datetime
        from src.resources.analysis_resources import store_analysis

        resource_key = f"{username}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        store_analysis(
            resource_key,
            {
                "username": username,
                "games_analyzed": report.total_games_analyzed,
                "total_acpl": round(report.total_acpl, 1),
                "blunders": report.blunder_count,
                "top_weaknesses": report.top_weaknesses,
            },
        )
        return {
            "username": username,
            "games_analyzed": report.total_games_analyzed,
            "total_acpl": round(report.total_acpl, 1),
            "blunders": report.blunder_count,
            "mistakes": report.mistake_count,
            "inaccuracies": report.inaccuracy_count,
            "phase_weaknesses": report.phase_weaknesses,
            "leaky_openings": report.leaky_openings[:3],
            "top_weaknesses": report.top_weaknesses,
        }
    except Exception as e:
        log.exception("diagnose error | user=%s", username)
        return {"error": str(e)}
