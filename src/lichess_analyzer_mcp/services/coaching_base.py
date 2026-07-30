"""Shared data collectors + safe LLM wrapper for coaching MCP tools.

Each collector:
1. Resolves depth from DEPTH_DEFAULTS if caller passes 0
2. Fetches/caches pipeline data
3. Returns structured dict consumable by prompt_builder.build_prompt()
"""

from lichess_analyzer_mcp.config.depth import DEPTH_DEFAULTS
from lichess_analyzer_mcp.services.game_analyzer import analyze_pgn, _load_cached_analysis
from lichess_analyzer_mcp.services.lichess_client import fetch_game_pgn
from lichess_analyzer_mcp.services.logger import get_logger

log = get_logger("coaching_base")


def collect_single_game(game_id: str, color: str = "white", depth: int = 0) -> dict:
    if depth == 0:
        depth = DEPTH_DEFAULTS["standard"]["single_game"]
    pgn = fetch_game_pgn(game_id)
    analysis = analyze_pgn(pgn, color, depth, game_id, strict_depth=True)
    return {
        "game_id": game_id,
        "analysis": analysis.to_dict() if analysis else {},
        "depth": depth,
        "color": color,
    }


def collect_patterns_for_games(analyses: list, username: str) -> list[dict]:
    from lichess_analyzer_mcp.services.pattern_detector import PatternDetector

    detector = PatternDetector()
    metadata = {"username": username, "total_games": len(analyses)}
    matches = detector.detect_all(analyses, metadata)

    result = []
    for m in matches:
        entry = {
            "pattern_id": m.pattern_id,
            "pattern_name": m.pattern_name,
            "confidence": round(m.confidence * 100, 0),
            "frequency": m.frequency,
            "severity": m.severity,
            "evidence": m.evidence,
            "affected_games": list(m.game_ids),
        }
        if m.hypothesis:
            entry["hypothesis"] = m.hypothesis
        if m.mitigation:
            entry["mitigation"] = m.mitigation
        result.append(entry)
    result.sort(key=lambda x: (x["severity"] == "critical", x["confidence"]), reverse=True)
    return result


def collect_weakness_report(analyses: list, username: str) -> dict | None:
    from lichess_analyzer_mcp.services.diagnostician import diagnose

    if not analyses:
        return None
    wr = diagnose(analyses, username)
    return _weakness_to_dict(wr)


def _weakness_to_dict(wr) -> dict:
    return {
        "total_acpl": getattr(wr, "total_acpl", None),
        "blunder_count": getattr(wr, "blunder_count", 0),
        "mistake_count": getattr(wr, "mistake_count", 0),
        "inaccuracy_count": getattr(wr, "inaccuracy_count", 0),
        "phase_weaknesses": getattr(wr, "phase_weaknesses", {}),
        "leaky_openings": getattr(wr, "leaky_openings", []),
        "top_weaknesses": getattr(wr, "top_weaknesses", []),
    }


def safe_llm_call(prompt: str, context: str = "") -> tuple[str, list[dict]]:
    """LLM call with cascade fallback + token tracking.

    If no LLM is available, returns a structured data dump as fallback.
    """
    from lichess_analyzer_mcp.services.llm_client import (
        generate_coaching_report_with_logs,
        COACHING_SYSTEM_PROMPT,
    )

    report, cascade_log = generate_coaching_report_with_logs(
        username="lichess",
        games_analyzed=1,
        patterns=[{"prompt": prompt, "context": context}],
    )
    return report, cascade_log


def extract_game_id_color_from_analysis(analysis) -> tuple[str, str]:
    """Extract game_id + player color from a GameAnalysis object."""
    gid = getattr(analysis, "game_id", "") or ""
    color = getattr(analysis, "player_color", "white")
    return gid, color
