from src.app import app
from src.services.lichess_client import fetch_user_games, fetch_game_pgn
from src.services.game_analyzer import analyze_pgn
from src.services.pattern_detector import PatternDetector
from src.services.logger import get_logger
from concurrent.futures import ThreadPoolExecutor, as_completed

log = get_logger("match_patterns")


@app.tool("lichess_match_patterns")
async def lichess_match_patterns(username: str, max_games: int = 20, depth: int = 12):
    """Detects known playing patterns (A-Q1) from the player's pattern library.

    Analyzes recent games and matches them against the pattern library
    imported from chess_pattern_v5.json. Returns detected patterns with
    confidence scores, evidence, and mitigation advice.

    Args:
        username: Lichess username
        max_games: Number of games to analyze (5-50)
        depth: Stockfish depth (8-18)
    """
    max_games = max(5, min(50, max_games))
    depth = max(8, min(18, depth))
    try:
        games_data = fetch_user_games(username, max_games=max_games)
        total_available = len(games_data)
        log.info(
            "patterns start | user=%s | requested=%d | available=%d | depth=%d",
            username,
            max_games,
            total_available,
            depth,
        )

        analyses = []
        skipped = 0

        def analyze_one(g):
            game_id = g.get("id", "")
            try:
                pgn = fetch_game_pgn(game_id)
                color = "white"
                if (
                    g.get("players", {}).get("black", {}).get("user", {}).get("name", "").lower()
                    == username.lower()
                ):
                    color = "black"
                return analyze_pgn(pgn, player_color=color, depth=depth)
            except Exception as e:
                log.warning("skip game %s: %s", game_id, e)
                return None

        with ThreadPoolExecutor(max_workers=min(4, max_games)) as pool:
            futures = [pool.submit(analyze_one, g) for g in games_data[:max_games]]
            for f in as_completed(futures):
                a = f.result()
                if a:
                    analyses.append(a)
                else:
                    skipped += 1

        if not analyses:
            log.error("0 games analyzed | user=%s", username)
            return {"error": "No games could be analyzed"}

        log.info(
            "patterns analyze done | user=%s | analyzed=%d | skipped=%d",
            username,
            len(analyses),
            skipped,
        )
        detector = PatternDetector()
        metadata = {"username": username, "total_games": len(analyses)}
        matches = detector.detect_all(analyses, metadata)
        log.info("patterns detected | user=%s | total=%d", username, len(matches))

        result = []
        for m in matches:
            result.append(
                {
                    "pattern_id": m.pattern_id,
                    "pattern_name": m.pattern_name,
                    "confidence": round(m.confidence * 100, 0),
                    "frequency": m.frequency,
                    "severity": m.severity,
                    "evidence": m.evidence,
                    "mitigation": detector.library.patterns[m.pattern_id].mitigation
                    if m.pattern_id in detector.library.patterns
                    else "",
                }
            )
        from datetime import datetime
        from src.resources.pattern_resources import store_patterns

        resource_key = f"{username}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        store_patterns(
            resource_key,
            {
                "username": username,
                "games_analyzed": len(analyses),
                "patterns_detected": result,
                "total_patterns": len(result),
            },
        )
        result.sort(key=lambda x: x["severity"] == "critical", reverse=True)
        result.sort(key=lambda x: x["confidence"], reverse=True)
        return {
            "username": username,
            "games_analyzed": len(analyses),
            "patterns_detected": result,
            "total_patterns": len(result),
        }
    except Exception as e:
        log.exception("patterns error | user=%s", username)
        return {"error": str(e)}
