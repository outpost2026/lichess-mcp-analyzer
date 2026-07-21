from src.app import app
from src.services.lichess_client import fetch_user_games, fetch_game_pgn
from src.services.game_analyzer import analyze_pgn, _load_cached_analysis
from src.services.pattern_detector import PatternDetector
from src.services.compressibility_validator import compute_compression
from src.services.validator import validate_pattern_artifact, ValidationError
from src.kb.schemas import validate_against_schema
from src.services.logger import get_logger

log = get_logger("match_patterns")


@app.tool("lichess_match_patterns")
async def lichess_match_patterns(username: str, max_games: int = 20, depth: int = 12):
    """Detects known playing patterns (A-Q1) from the player's pattern library.

    Analyzes recent games and matches them against the pattern library
    imported from chess_pattern_v5.json. Returns detected patterns with
    confidence scores, evidence, mitigation advice, and compression validation.
    Uses cache-first — pre-analyze games via lichess_analyze_game first.

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
            "patterns analyze done | user=%s | analyzed=%d | skipped=%d",
            username,
            len(analyses),
            skipped,
        )
        detector = PatternDetector()
        metadata = {"username": username, "total_games": len(analyses)}
        matches = detector.detect_all(analyses, metadata)

        result = []
        for m in matches:
            m = compute_compression(m, analyses)
            entry = {
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
            if m.hypothesis:
                entry["hypothesis"] = m.hypothesis
            if m.compression_ratio is not None:
                entry["compression_ratio"] = m.compression_ratio
            result.append(entry)

        log.info("patterns detected | user=%s | total=%d", username, len(result))

        artifact = {
            "username": username,
            "games_analyzed": len(analyses),
            "patterns_detected": result,
            "total_patterns": len(result),
        }

        schema_errors = validate_against_schema(artifact)
        if schema_errors:
            log.warning("schema issues | user=%s | count=%d", username, len(schema_errors))
            artifact["_schema_warnings"] = schema_errors

        sanity_issues = validate_pattern_artifact(artifact)
        if sanity_issues:
            log.warning("sanity issues | user=%s | count=%d", username, len(sanity_issues))
            artifact["_sanity_warnings"] = sanity_issues

        from datetime import datetime
        from src.resources.pattern_resources import store_patterns

        resource_key = f"{username}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        store_patterns(resource_key, artifact)

        result.sort(key=lambda x: (x["severity"] == "critical", x["confidence"]), reverse=True)
        return artifact
    except Exception as e:
        log.exception("patterns error | user=%s", username)
        return {"error": str(e)}
