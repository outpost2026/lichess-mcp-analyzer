"""Shared data collectors + safe LLM wrapper for coaching MCP tools.

Each collector:
1. Resolves depth from DEPTH_DEFAULTS if caller passes 0
2. Fetches/caches pipeline data
3. Returns structured dict consumable by prompt_builder.build_prompt()
"""

import os

from lichess_analyzer_mcp.config.depth import DEPTH_DEFAULTS
from lichess_analyzer_mcp.services.game_analyzer import analyze_pgn
from lichess_analyzer_mcp.services.lichess_client import fetch_game_pgn
from lichess_analyzer_mcp.services.logger import get_logger

log = get_logger("coaching_base")


def detect_player_color(game_id: str, username: str) -> str:
    """Detect player color from game metadata or PGN headers.

    Priority:
    1. Game metadata via Lichess API (fetch_game_by_id)
    2. PGN headers ([White]/[Black])
    3. Default 'white'
    """
    if not username:
        return "white"

    # 1) API metadata (most reliable)
    try:
        from lichess_analyzer_mcp.services.lichess_client import fetch_game_by_id

        raw = fetch_game_by_id(game_id)
        if isinstance(raw, dict):
            players = raw.get("players", {})
            for color_key in ("white", "black"):
                player_name = players.get(color_key, {}).get("user", {}).get("name", "").lower()
                if player_name == username.lower():
                    return color_key
    except Exception:
        pass

    # 2) Fallback: parse PGN headers
    try:
        import io
        import chess.pgn

        from lichess_analyzer_mcp.services.lichess_client import fetch_game_pgn

        pgn = fetch_game_pgn(game_id)
        game_node = chess.pgn.read_game(io.StringIO(pgn))
        if game_node is not None:
            white_name = game_node.headers.get("White", "").lower()
            black_name = game_node.headers.get("Black", "").lower()
            if username.lower() == black_name:
                return "black"
            if username.lower() == white_name:
                return "white"
    except Exception:
        pass

    return "white"


def collect_single_game(
    game_id: str,
    color: str = "white",
    depth: int = 0,
    username: str = "",
) -> dict:
    if depth == 0:
        depth = DEPTH_DEFAULTS["standard"]["single_game"]

    # Auto-detect color from username if provided
    if username:
        color = detect_player_color(game_id, username)

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
        mitigation = detector.library.patterns.get(m.pattern_id)
        if mitigation:
            entry["mitigation"] = mitigation.mitigation
        result.append(entry)
    result.sort(key=lambda x: (x["severity"] == "critical", x["confidence"]), reverse=True)
    return result


def collect_weakness_report(analyses: list, username: str) -> dict | None:
    from lichess_analyzer_mcp.services.diagnostician import diagnose

    if not analyses:
        return None
    wr = diagnose(analyses, username)
    result = _weakness_to_dict(wr)

    # Aggregate tactical motif data from per-move analysis
    tactical_count = 0
    positional_count = 0
    motif_counts: dict[str, int] = {}
    for a in analyses:
        moves = a.get("moves", []) if isinstance(a, dict) else getattr(a, "moves", [])
        for m in moves:
            if isinstance(m, dict):
                is_tac = m.get("is_tactical_motif", False)
                motif = m.get("motif_type")
                cl = m.get("classification", "")
            else:
                is_tac = getattr(m, "is_tactical_motif", False)
                motif = getattr(m, "motif_type", None)
                cl = getattr(m, "classification", "")
            if cl in ("blunder", "mistake", "inaccuracy"):
                if is_tac:
                    tactical_count += 1
                    if motif:
                        motif_counts[motif] = motif_counts.get(motif, 0) + 1
                else:
                    positional_count += 1

    total_classified = tactical_count + positional_count
    result["tactical_summary"] = {
        "tactical_count": tactical_count,
        "positional_count": positional_count,
        "tactical_ratio": round(tactical_count / total_classified, 2) if total_classified else 0,
        "motif_distribution": motif_counts,
    }
    return result


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


def _strip_instructions(prompt: str) -> str:
    """Remove instruction boilerplate from prompt for fallback display."""
    for marker in ("=== INSTRUCTIONS ===", "PRAVIDLA:", "STRUKTURA:"):
        if marker in prompt:
            prompt = prompt.split(marker)[0]
    return prompt.strip()


def _is_valid_coaching_content(content: str | None) -> bool:
    """Validate LLM output is actual coaching, not echoed instructions or empty."""
    if content is None:
        return False
    stripped = content.strip()
    if not stripped:
        return False
    if len(stripped) < 50:
        return False
    # LLM echoed back the prompt instructions instead of generating coaching
    instruction_markers = ("=== INSTRUCTIONS ===", "PRAVIDLA:", "STRUKTURA:", "K DISPOZICI:")
    for marker in instruction_markers:
        # If content contains instruction header verbatim it is likely an echo
        if marker in stripped and stripped.count(marker) >= 1:
            # Allow data quoting but reject content that IS the instruction template
            if (
                "Vytvo\u0159 coaching report pro hru" in stripped
                and "[DATA]" in stripped
                and "[IM]" in stripped
            ):
                return False
            if marker == "=== INSTRUCTIONS ===":
                return False
    return True


def safe_llm_call(prompt: str, context: str = "") -> tuple[str, list[dict], bool]:
    """LLM call with cascade fallback + token tracking.

    Sends pre-built prompt directly to LLM providers in cascade order.
    Falls back to structured data dump (without instructions) if no LLM is available.
    Validates LLM output — echo or empty responses are treated as failures.

    Returns:
        (report, cascade_log, cascade_exhausted)
        cascade_exhausted=True means all providers failed — caller can try MCP sampling.
    """
    from lichess_analyzer_mcp.services.llm_client import (
        PROVIDERS,
        COACHING_SYSTEM_PROMPT,
        _call_llm,
    )

    cascade_log = []
    for prov_cfg in PROVIDERS:
        api_key = os.environ.get(prov_cfg["api_key_var"], "")
        if not api_key:
            cascade_log.append(
                {
                    "provider": prov_cfg["name"],
                    "skipped": True,
                    "error": "No API key",
                }
            )
            continue
        content, token_log = _call_llm(COACHING_SYSTEM_PROMPT, prompt, prov_cfg)
        cascade_log.append(token_log)
        if _is_valid_coaching_content(content):
            return content, cascade_log, False  # cascade_exhausted = False
        # Invalid content (echo, empty, too short) — treat as provider failure
        if content is not None:
            token_log["error"] = (
                token_log.get("error") or "Invalid LLM output (echo/empty) — trying next provider"
            )
            # mark as not usable; continue cascade

    # ── IDE fallback (Muse Spark / Cursor / opencode) — high ROI, 0 cost ──
    try:
        from lichess_analyzer_mcp.services.ide_fallback import (
            generate_ide_report,
            is_ide_available,
        )

        if is_ide_available():
            ide_content, ide_log = generate_ide_report(prompt, COACHING_SYSTEM_PROMPT)
            if _is_valid_coaching_content(ide_content):
                cascade_log.append(ide_log)
                return ide_content, cascade_log, False  # cascade_exhausted = False
            # IDE returned invalid — log and continue to data dump
            ide_log["error"] = "IDE fallback returned invalid content"
            cascade_log.append(ide_log)
    except Exception as e:
        cascade_log.append({"provider": "IDE (Muse Spark)", "error": f"IDE fallback failed: {e}"})

    data_part = _strip_instructions(prompt)
    fallback = (
        "# Coaching Report\n\n"
        "_LLM coaching unavailable after cascade — all providers failed or returned invalid output._\n\n"
        "## Deterministic Data (Stockfish + Pattern Detection)\n\n"
        f"{data_part}\n\n"
        "---\n\n"
        "_No LLM synthesis was performed. Review the data above or retry when a provider is available._"
    )
    return fallback, cascade_log, True  # cascade_exhausted = True


def extract_game_id_color_from_analysis(analysis) -> tuple[str, str]:
    """Extract game_id + player color from a GameAnalysis object."""
    gid = getattr(analysis, "game_id", "") or ""
    color = getattr(analysis, "player_color", "white")
    return gid, color


async def mcp_sample_fallback(ctx, prompt: str, system_prompt: str = "") -> tuple[str, dict]:
    """MCP sampling fallback — uses the IDE's current LLM via ctx.sample().

    Called when all external API providers are exhausted.
    Requires MCP Context object from the tool function.
    """
    messages = []
    if system_prompt:
        messages.append({"role": "user", "content": f"System: {system_prompt}\n\n{prompt}"})
    else:
        messages.append({"role": "user", "content": prompt})

    response = await ctx.sample(messages=messages)
    content = response.text if hasattr(response, "text") else str(response)

    token_log = {
        "provider": "MCP Sampling (IDE model)",
        "model": getattr(response, "model", "unknown"),
        "input_chars": len(prompt) + len(system_prompt),
        "output_chars": len(content),
        "estimated_input_tokens": (len(prompt) + len(system_prompt)) // 4,
        "completion_tokens": len(content) // 4,
        "total_tokens": (len(prompt) + len(system_prompt)) // 4 + len(content) // 4,
        "cost_usd": 0.0,
        "error": None,
    }
    return content, token_log
