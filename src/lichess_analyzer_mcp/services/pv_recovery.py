"""Recover engine lines (PV) for flagged moves that lost them to the deadline.

FIX-014: the top-level analysis has a hard wall-clock budget. When that budget
is exhausted, later flagged moves can end up with `engine_lines == []` -
including the single most important blunder of the game. Silently omitting the
PV makes the compact JSON unexplainable ("why was Qf4+ better than Re8+?").

This module retries only blunders and mistakes that have no engine lines, with
a dedicated per-position timeout. It never invents a PV: when the retry also
fails, the caller gets an explicit reason (`engine_timeout` / `engine_error`)
and the compact serializer emits `pv_unavailable`.
"""

from __future__ import annotations

from lichess_analyzer_mcp.config.depth import NODE_CAPS
from lichess_analyzer_mcp.services import engine_client
from lichess_analyzer_mcp.services.game_analyzer import (
    _build_explanation,
    _engine_lines_to_dicts,
)

RETRY_CLASSES = ("blunder", "mistake")
DEFAULT_TIMEOUT_S = 15.0
RETRY_HASH_MB = 64
MAX_RETRIES = 3


def _reason(error: str | None, lines: list[dict]) -> str:
    """Why a retry produced no usable PV (explicit, never silent)."""
    if lines:
        return ""
    if error and "timed out" in error.lower():
        return "engine_timeout"
    if error:
        return "engine_error"
    return "no_engine_lines"


def recover_missing_pv(
    analysis,
    *,
    depth: int,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    max_retries: int = MAX_RETRIES,
) -> dict[int, str]:
    """Retry the engine-line lookup for blunders/mistakes without a PV.

    Mutates `analysis.moves` in place (engine_lines, played_rank,
    best_move_san, explanation) and the engine counters. Returns
    `{ply: reason}` for flagged moves that still have no PV afterwards.

    The retry uses the same deterministic policy as the main analysis
    (depth + node ceiling, single thread, fresh hash) so a recovered line is
    reproducible. Only the wall-clock guard is new.
    """
    moves = getattr(analysis, "moves", None) or []
    candidates = [
        move
        for move in moves
        if getattr(move, "classification", None) in RETRY_CLASSES
        and not getattr(move, "engine_lines", None)
    ]
    if not candidates:
        return {}

    missing: dict[int, str] = {}
    prev_hash = engine_client.get_current_hash()
    if prev_hash is not None and prev_hash != RETRY_HASH_MB:
        try:
            engine_client.get_engine(hash_mb=RETRY_HASH_MB)
        except Exception:
            # A hash reconfiguration is an optimisation, never a hard error.
            pass

    try:
        for index, move in enumerate(candidates):
            ply = int(getattr(move, "ply", 0) or 0)
            if index >= max_retries:
                missing[ply] = "retry_budget_exhausted"
                continue
            fen = getattr(move, "fen", "") or ""
            if not fen:
                missing[ply] = "no_fen"
                continue
            lines, error = engine_client.analyze_position_ex(
                fen,
                depth=depth,
                multipv=3,
                timeout_s=timeout_s,
                nodes=int(NODE_CAPS.get(depth) or 0),
            )
            analysis.engine_calls = int(getattr(analysis, "engine_calls", 0)) + 1
            analysis.engine_retries = int(getattr(analysis, "engine_retries", 0)) + 1
            if not lines:
                reason = _reason(error, lines)
                if reason == "engine_timeout":
                    analysis.engine_timeouts = int(getattr(analysis, "engine_timeouts", 0)) + 1
                missing[ply] = reason
                continue

            move.engine_lines = _engine_lines_to_dicts(lines)
            rank = 0
            for entry in move.engine_lines:
                if entry.get("san") == getattr(move, "move_san", None):
                    rank = int(entry.get("rank") or 0)
                    break
            if rank == 0:
                rank = len(move.engine_lines) + 1
            move.played_rank = rank
            if not getattr(move, "best_move_san", ""):
                move.best_move_san = move.engine_lines[0].get("san") or ""
            move.explanation = _build_explanation(move, move.engine_lines)
            move.explanation_source = "deterministic"
    finally:
        if prev_hash is not None and prev_hash != RETRY_HASH_MB:
            try:
                engine_client.get_engine(hash_mb=prev_hash)
            except Exception:
                pass

    return missing
