import glob as glob_mod
import os
from lichess_analyzer_mcp.app import app
from lichess_analyzer_mcp.services.lichess_client import fetch_user_games, fetch_game_pgn
from lichess_analyzer_mcp.services.game_analyzer import analyze_pgn, _load_cached_analysis
from lichess_analyzer_mcp.services.game_analyzer import CACHE_DIR as GAME_CACHE_DIR
from lichess_analyzer_mcp.services.pattern_detector import PatternDetector
from lichess_analyzer_mcp.services.compressibility_validator import compute_compression
from lichess_analyzer_mcp.services.pattern_artifact_validator import (
    validate_pattern_artifact,
    ValidationError,
)
from lichess_analyzer_mcp.kb.schemas import validate_against_schema
from lichess_analyzer_mcp.services.logger import get_logger

log = get_logger("match_patterns")


def _find_cached_analysis(game_id: str) -> object | None:
    """Load cached GameAnalysis for a game_id regardless of color/depth."""
    pattern = os.path.join(GAME_CACHE_DIR, f"{game_id}_*.json")
    for fpath in sorted(glob_mod.glob(pattern), reverse=True):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                import json
                from lichess_analyzer_mcp.models.game import GameAnalysis

                return GameAnalysis.from_dict(json.load(f))
        except Exception:
            continue
    return None


@app.tool("lichess_match_patterns")
async def lichess_match_patterns(
    username: str = "",
    max_games: int = 20,
    depth: int = 12,
    result: str = "all",
    game_ids: str = "",
):
    """Detects known playing patterns (A-Q1) from the player's pattern library.

    Analyzes recent games and matches them against the pattern library
    imported from chess_pattern_v5.json. Returns detected patterns with
    confidence scores, evidence, mitigation advice, and compression validation.
    Uses cache-first — pre-analyze games via lichess_analyze_game first.

    For anonymous games, pass comma-separated game_ids instead of username.
    Games must be pre-analyzed (cached via lichess_analyze_anonymous_session).

    Args:
        username: Lichess username (optional if game_ids provided)
        max_games: Number of games to analyze (5-50)
        depth: Stockfish depth (8-18)
        result: Filtr dle vysledku - 'all', 'win', 'loss', 'draw'
        game_ids: Comma-separated 8-char game IDs for anonymous/cached games
    """
    max_games = max(5, min(999, max_games))
    depth = max(8, min(18, depth))

    try:
        # ── Branch: cached game_ids (anonymous) ──
        if game_ids:
            ids = [g.strip()[:8] for g in game_ids.split(",") if g.strip()]
            log.info("patterns from ids | ids=%d | depth=%d", len(ids), depth)

            analyses = []
            for gid in ids:
                try:
                    cached = _find_cached_analysis(gid)
                    if cached is not None:
                        analyses.append(cached)
                    else:
                        log.warning("no cache for %s — skip", gid)
                except Exception as e:
                    log.warning("skip %s: %s", gid, e)

            if not analyses:
                return {
                    "error": "No cached analyses found for given game_ids. Run lichess_analyze_anonymous_session first."
                }

            username = username or "anonymous"
        # ── Branch: fetch by username ──
        else:
            if not username:
                return {"error": "Provide username or game_ids"}
            games_data = fetch_user_games(username, max_games=max_games, result=result)
            total_available = len(games_data)

            from lichess_analyzer_mcp.services.lichess_client import get_pending_analysis

            pending = get_pending_analysis(username, depth)

            log.info(
                "patterns start | user=%s | requested=%d | available=%d | pending=%d | depth=%d",
                username,
                max_games,
                total_available,
                len(pending),
                depth,
            )

            analyses = []
            skipped = 0

            for g in games_data[:max_games]:
                game_id = g.get("id", "")
                try:
                    color = "white"
                    if (
                        g.get("players", {})
                        .get("black", {})
                        .get("user", {})
                        .get("name", "")
                        .lower()
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

        # ── Shared detection pipeline ──
        detector = PatternDetector()
        metadata = {"username": username, "total_games": len(analyses)}
        matches = detector.detect_all(analyses, metadata)

        result_list = []
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
            result_list.append(entry)

        log.info("patterns detected | user=%s | total=%d", username, len(result_list))

        result_list.sort(key=lambda x: (x["severity"] == "critical", x["confidence"]), reverse=True)

        artifact = {
            "username": username,
            "games_analyzed": len(analyses),
            "patterns_detected": result_list,
            "total_patterns": len(result_list),
        }

        if not game_ids:
            artifact["total_available"] = total_available
            if pending:
                artifact["warning"] = (
                    f"{len(pending)} game(s) pending analysis at depth={depth}. "
                    f"Run lichess_analyze_pending(username='{username}', depth={depth}) "
                    "for a full dataset, or these will be analyzed on first use."
                )
                artifact["pending_analysis"] = pending

        schema_errors = validate_against_schema(artifact)
        if schema_errors:
            log.warning("schema issues | user=%s | count=%d", username, len(schema_errors))
            artifact["_schema_warnings"] = schema_errors

        sanity_issues = validate_pattern_artifact(artifact)
        if sanity_issues:
            log.warning("sanity issues | user=%s | count=%d", username, len(sanity_issues))
            artifact["_sanity_warnings"] = sanity_issues

        from datetime import datetime
        from lichess_analyzer_mcp.resources.pattern_resources import store_patterns

        resource_key = f"{username}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        store_patterns(resource_key, artifact)

        return artifact
    except Exception as e:
        log.exception("patterns error | user=%s", username)
        return {"error": str(e)}
