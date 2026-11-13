import json
import time

from lichess_analyzer_mcp.app import app
from lichess_analyzer_mcp.config.depth import (
    BUDGETS,
    DEPTH_DEFAULTS,
    ENGINE_THREADS,
    NODE_CAPS,
)
from lichess_analyzer_mcp.services import engine_client
from lichess_analyzer_mcp.services.audit import auditable
from lichess_analyzer_mcp.services.budget import budget_for_mode
from lichess_analyzer_mcp.services.coaching_base import (
    collect_single_game,
    mcp_sample_fallback,
    safe_llm_call,
)
from lichess_analyzer_mcp.services.llm_client import (
    COACHING_SYSTEM_PROMPT,
    get_llm_status,
)
from lichess_analyzer_mcp.services.logger import get_logger
from lichess_analyzer_mcp.services.pattern_detector import (
    PATTERN_STATUS_MATCHED,
    PATTERN_STATUS_UNCLASSIFIED,
    scan_single_game,
    unclassified_reason_from_flag,
)
from lichess_analyzer_mcp.services.prompt_builder import build_prompt
from lichess_analyzer_mcp.models.analysis import DETECTOR_VERSION
from lichess_analyzer_mcp.models.game import GameAnalysis, effective_phase

log = get_logger("coaching_single_game")

SCHEMA_VERSION = "1.2"
_FLAGGED = ("blunder", "mistake", "inaccuracy")
_OUTPUT_FORMATS = ("compact", "detailed", "both")


def _normalize_format(value: str) -> str:
    """Validate `output_format`; `full` stays a deprecated alias for one cycle."""
    requested = (value or "compact").strip().lower()
    if requested == "full":
        log.warning("output_format='full' is deprecated; use 'detailed'")
        return "detailed"
    if requested not in _OUTPUT_FORMATS:
        raise ValueError(f"invalid output_format {value!r}; expected one of {_OUTPUT_FORMATS}")
    return requested


def _report_truncated(text: str) -> bool:
    """True when the text ends inside an unclosed JSON-like structure.

    FIX-011: a report must never end mid-array/object. A deterministic report
    built by `ide_fallback._critical_moments()` cannot, but an LLM or a future
    formatter might truncate; the flag makes that observable instead of silent.
    """
    stripped = text.rstrip()
    if not stripped:
        return False
    if stripped[-1] in "[{,:":
        return True
    return stripped.count("[") != stripped.count("]") or stripped.count("{") != stripped.count("}")


def _node_cap(depth: int) -> int:
    """Fixed node ceiling for this depth (0 = depth-only, legacy policy)."""
    return int(NODE_CAPS.get(depth) or 0)


def _cache_policy(depth: int) -> str:
    """Cache-key suffix; must match game_analyzer._policy_token."""
    cap = _node_cap(depth)
    return f"n{cap}" if cap else ""


def _engine_block(depth: int, hash_mb: int | None) -> dict:
    cap = _node_cap(depth)
    return {
        "limit": "depth+nodes" if cap else "depth",
        "depth": depth,
        "nodes_cap": cap or None,
        "hash_mb": hash_mb,
        "threads": ENGINE_THREADS,
    }


def _fmt_loss(move: dict) -> str:
    value = move.get("centipawn_loss")
    return f"{value:.0f}" if isinstance(value, (int, float)) else "n/a"


def _flagged_moves(analysis: dict) -> list[dict]:
    out = []
    for m in analysis.get("moves", []):
        if m.get("classification") not in _FLAGGED:
            continue
        out.append(
            {
                "ply": m.get("ply"),
                "san": m.get("move_san"),
                "uci": m.get("move_uci"),
                "classification": m.get("classification"),
                "cp_loss": m.get("centipawn_loss"),
                "eval_before": m.get("eval_before"),
                "eval_after": m.get("eval_after"),
                "win_prob_before": m.get("win_prob_before"),
                "win_prob_after": m.get("win_prob_after"),
                "phase": m.get("phase"),
                "best_move_san": m.get("best_move_san") or None,
                "played_rank": m.get("played_rank") or None,
                "engine_lines": m.get("engine_lines") or [],
                "motif": m.get("motif_type"),
                # `check` = the played move gives check (matches motif
                # semantics). The pre-move state has its own field.
                "check": bool(m.get("gives_check")),
                "in_check_before": bool(m.get("was_in_check")),
                "explanation": m.get("explanation") or "",
                "explanation_source": m.get("explanation_source") or "none",
            }
        )
    return out


def _annotate_coverage(flagged: list[dict], coverage: dict[int, dict]) -> None:
    """P0-7: attach pattern coverage to every flagged move in place.

    A flagged move that is missing from `coverage` (legacy cache without the
    measurement) is still never silent: it becomes `unclassified` with a
    derived reason instead of an empty story.
    """
    for item in flagged:
        raw_ply = item.get("ply")
        try:
            cov = coverage.get(int(raw_ply)) if raw_ply is not None else None
        except (TypeError, ValueError):
            cov = None
        if cov is None:
            item["pattern_status"] = PATTERN_STATUS_UNCLASSIFIED
            item["unclassified_reason"] = unclassified_reason_from_flag(item)
        else:
            item["pattern_status"] = cov["pattern_status"]
            item["unclassified_reason"] = cov.get("unclassified_reason")


def _coverage_summary(flagged: list[dict]) -> tuple[dict, dict]:
    """Counts for `patterns_meta.coverage` and the reason histogram (P0-7/P0-8).

    Derived from the annotated flags, never from a parallel map: the compact
    validator requires `coverage.flagged == len(flags)`, so a stubbed or
    legacy detection path must still add up.
    """
    flagged_count = len(flagged)
    matched = sum(1 for item in flagged if item.get("pattern_status") == PATTERN_STATUS_MATCHED)
    reasons: dict[str, int] = {}
    for item in flagged:
        if item.get("pattern_status") == PATTERN_STATUS_MATCHED:
            continue
        reason = item.get("unclassified_reason")
        if reason:
            reasons[reason] = reasons.get(reason, 0) + 1
    summary = {
        "flagged": flagged_count,
        "matched": matched,
        "unclassified": flagged_count - matched,
    }
    return summary, dict(sorted(reasons.items()))


def _unclassified_items(flagged: list[dict]) -> list[dict]:
    """Explicit queue of critical moments no pattern explains (discovery feed)."""
    return [
        {
            "ply": item.get("ply"),
            "san": item.get("san"),
            "class": item.get("classification"),
            "cp_loss": item.get("cp_loss"),
            "reason": item.get("unclassified_reason"),
        }
        for item in flagged
        if item.get("pattern_status") == PATTERN_STATUS_UNCLASSIFIED
    ]


def _phase_summary(analysis: GameAnalysis) -> dict:
    """Souhrn po fázích — stejná fáze, jakou používají detektory (P1).

    Dřív se četl surový `phase` (ply segment), zatímco detektory rozhodují
    přes `effective_phase`; u `phase_method=material` se tím souhrn a detekce
    rozešly. `segment_stats` a `chess_phase_stats` zůstávají jako auditní řezy.
    """
    result = {}
    moves = analysis.moves
    for phase in ("opening", "middlegame", "endgame"):
        phase_moves = [m for m in moves if m.analyzed and effective_phase(m) == phase]
        if not phase_moves:
            continue
        measured = [m for m in phase_moves if isinstance(m.centipawn_loss, (int, float))]
        acpl = (
            round(sum(m.centipawn_loss for m in measured) / len(measured), 1) if measured else None
        )
        result[phase] = {
            "acpl": acpl,
            "move_count": len(phase_moves),
            "flagged": sum(1 for m in phase_moves if m.classification in _FLAGGED),
        }
    return result


def _phase_breakdown(phase_stats: dict) -> str:
    """FIX-021: weakest phases first, clean phases never called weakest.

    A phase is clean only when it measured 0 flagged moves *and* ACPL 0.0
    (or no measured move). Weak phases are sorted by ACPL desc, tie-break
    flagged desc. Returns "žádná slabá fáze" when every phase is clean.
    """
    weak = {
        p: s
        for p, s in phase_stats.items()
        if not (
            s.get("flagged", 0) == 0
            and (s.get("acpl") is None or float(s.get("acpl") or 0.0) == 0.0)
        )
    }
    clean = [p for p in phase_stats if p not in weak]
    ordered = sorted(
        weak.items(),
        key=lambda kv: (
            kv[1].get("acpl") if isinstance(kv[1].get("acpl"), (int, float)) else -1.0,
            kv[1].get("flagged", 0),
        ),
        reverse=True,
    )
    if ordered:
        text = "; ".join(
            f"{p}: ACPL {s.get('acpl', '?')}, {s.get('flagged', 0)} chyb" for p, s in ordered
        )
    else:
        text = "žádná slabá fáze"
    if clean:
        text += f" | čisté fáze: {', '.join(clean)}"
    return text


def _llm_attempts(cascade_log: list[dict]) -> list[dict]:
    attempts = []
    for entry in cascade_log:
        status = entry.get("http_status")
        error = entry.get("error") or ""
        retryable = status in (429,) or (isinstance(status, int) and status >= 500)
        if status is None and "timed out" in error.lower():
            retryable = True
        attempts.append(
            {
                "provider": entry.get("provider", "?"),
                "http_status": status,
                "skipped": bool(entry.get("skipped")),
                "error": error or None,
                "retryable": retryable,
            }
        )
    return attempts


def _token_totals(cascade_log: list[dict]) -> dict:
    inp = 0
    out = 0
    for entry in cascade_log:
        inp += int(entry.get("prompt_tokens") or entry.get("estimated_input_tokens") or 0)
        out += int(entry.get("completion_tokens") or 0)
    return {"input": inp, "output": out}


async def build_response(
    *,
    game_id: str,
    username: str,
    detected_color: str,
    depth: int,
    mode: str,
    deadline_s: float,
    call_started: float,
    analysis_obj,
    io_s: float,
    use_llm: bool,
    ctx,
    output_format: str,
) -> dict:
    """Build a contract v1.2 response (optionally serialized to the 2.1 shape).

    Public so the CLI (`scripts/coach.py`) can reuse the exact same pipeline for
    PGN input, which never reaches the MCP tool's Lichess fetch.
    """
    from lichess_analyzer_mcp.services.pv_recovery import recover_missing_pv

    # FIX-014: a blunder whose PV was lost to the analysis deadline is retried
    # here, after the budget is released. Failures stay explicit.
    pv_unavailable = recover_missing_pv(analysis_obj, depth=depth)
    # FIX-028: persist the recovered PV so a later cache hit does not re-run
    # the engine retry (the analysis cache was written before this step).
    try:
        from lichess_analyzer_mcp.services.game_analyzer import refresh_cached_analysis

        refresh_cached_analysis(game_id, depth, mode, analysis_obj)
    except Exception:
        pass
    analysis = analysis_obj.to_dict()
    if not analysis.get("moves"):
        raise ValueError("analysis produced no moves")

    patterns, coverage = scan_single_game(analysis_obj)
    flagged = _flagged_moves(analysis)
    _annotate_coverage(flagged, coverage)
    unclassified = _unclassified_items(flagged)
    coverage_counts, unclassified_reasons = _coverage_summary(flagged)
    unanalyzed = analysis.get("unanalyzed_plies", []) or []

    game_info = analysis.get("game", {})
    phase_stats = _phase_summary(analysis_obj)
    phase_breakdown = _phase_breakdown(phase_stats)

    def _move_lines(items: list[dict], limit: int = 10) -> str:
        return "\n".join(
            f"  ply {m.get('ply')}: {m.get('move_san')} (loss {_fmt_loss(m)}cp, "
            f"fáze={m.get('phase')}, gives_check={m.get('gives_check', False)}, "
            f"in_check_before={m.get('was_in_check', False)}, "
            f"tactical={m.get('is_tactical_motif', False)}, motif={m.get('motif_type')}, "
            f"best={m.get('best_move_san') or '?'}, rank={m.get('played_rank') or '?'}, "
            f"explanation={m.get('explanation') or 'n/a'}, "
            f"fen={m.get('fen', '')[:60]})"
            for m in items[:limit]
        )

    blunders_list = _move_lines(analysis.get("blunders", []))
    mistakes_list = _move_lines(analysis.get("mistakes", []))
    inacc_list = _move_lines(analysis.get("inaccuracies", []))
    bfs_raw = analysis.get("blunder_fact_sheets", [])

    prompt_data = {
        "game_id": game_id,
        "color": detected_color,
        "depth": depth,
        "result": game_info.get("result", "?"),
        "opening": game_info.get("opening", "?"),
        "acpl": round(analysis.get("total_acpl", 0), 1),
        "blunders_count": len(analysis.get("blunders", [])),
        "mistakes_count": len(analysis.get("mistakes", [])),
        "inaccuracies_count": len(analysis.get("inaccuracies", [])),
        "blunders_list": blunders_list or "(žádné)",
        "mistakes_list": mistakes_list or "(žádné)",
        "inacc_list": inacc_list or "(žádné)",
        "phase_breakdown": phase_breakdown,
        "patterns_json": json.dumps(patterns, ensure_ascii=False, indent=2),
        "unclassified_json": json.dumps(unclassified, ensure_ascii=False, indent=2),
        "bfs_json": json.dumps(bfs_raw, ensure_ascii=False, indent=2)[:2000],
        "time_control": game_info.get("time_control", "?"),
        "player_rating": game_info.get("player_rating", "?"),
        "opponent_rating": game_info.get("opponent_rating", "?"),
    }
    prompt = build_prompt(1, prompt_data)

    elapsed = time.perf_counter() - call_started
    llm_timeout = min(
        float(budget_for_mode(mode)["llm_s"]),
        max(0.5, deadline_s - elapsed - float(budget_for_mode(mode)["reserve_s"])),
    )
    t_llm = time.perf_counter()
    if use_llm:
        report, cascade_log, cascade_exhausted, report_source = safe_llm_call(
            prompt, f"single_game:{game_id}", timeout_s=llm_timeout
        )
    else:
        # Offline ETL contract: no provider is contacted. The report is the
        # deterministic summary, never labelled as LLM output.
        from lichess_analyzer_mcp.services.ide_fallback import generate_ide_report

        report, token_log = generate_ide_report(prompt, COACHING_SYSTEM_PROMPT)
        cascade_log = [token_log]
        cascade_exhausted = True
        report_source = "deterministic"
    llm_s = time.perf_counter() - t_llm

    # MCP sampling fallback — use IDE's LLM when external APIs are exhausted.
    # `cascade_exhausted` is also True for the deterministic fallback, so a
    # real LLM gets a chance before the deterministic text is final.
    if use_llm and cascade_exhausted and ctx is not None:
        try:
            mcp_content, mcp_log = await mcp_sample_fallback(ctx, prompt, COACHING_SYSTEM_PROMPT)
            from lichess_analyzer_mcp.services.coaching_base import (
                _is_valid_coaching_content,
            )

            if _is_valid_coaching_content(mcp_content):
                report = mcp_content
                report_source = "mcp_sampling"
                cascade_log.append(mcp_log)
        except Exception as e:
            log.warning("MCP sampling fallback failed: %s", e)
            cascade_log.append({"provider": "MCP Sampling", "error": str(e)})

    llm_ok = report_source not in ("deterministic", "data_dump", "none", None)
    source_label = (
        "llm" if llm_ok else ("deterministic" if report_source == "deterministic" else "data_dump")
    )

    # ── status precedence: error > partial > degraded > ok ──
    errors = analysis.get("errors", []) or []
    if unanalyzed:
        status = "partial"
    elif errors or not llm_ok:
        status = "degraded"
    else:
        status = "ok"

    total_s = time.perf_counter() - call_started
    analysis_timings = analysis.get("timings", {}) or {}
    cache_hit = bool(getattr(analysis_obj, "_cache_hit", False))
    # A cache hit ran no engine in this call; the stored stage timings
    # describe the run that produced the file, not this response.
    engine_s = 0.0 if cache_hit else float(analysis_timings.get("engine_s", 0.0))
    engine_calls = 0 if cache_hit else int(analysis.get("engine_calls", 0))
    engine_timeouts = 0 if cache_hit else int(analysis.get("engine_timeouts", 0))
    engine_retries = 0 if cache_hit else int(analysis.get("engine_retries", 0))
    overhead_s = max(0.0, total_s - io_s - engine_s - llm_s)
    timings = {
        "io_s": round(io_s, 3),
        "engine_s": round(engine_s, 3),
        "llm_s": round(llm_s, 3),
        "overhead_s": round(overhead_s, 3),
        "total_s": round(total_s, 3),
        "deadline_s": round(float(analysis.get("deadline_s") or deadline_s), 3),
        "budget_used": round(total_s / deadline_s, 3) if deadline_s else None,
        "engine_calls": engine_calls,
        "engine_timeouts": engine_timeouts,
        "engine_retries": engine_retries,
        "cache_hit": cache_hit,
    }

    llm_status = get_llm_status()
    tokens = _token_totals(cascade_log)
    patterns_meta = {
        "scope": "single_game",
        "cross_game_suppressed": True,
        "reason": (
            "Single-game scope: only per-move evidence is aggregated. "
            "Cross-game detectors need >=3 games and are suppressed."
            if patterns
            else "No flagged move met a single-game pattern threshold. "
            "Every flagged move carries an explicit unclassified_reason. "
            "Cross-game detectors need >=3 games and are suppressed."
        ),
        "detector_version": DETECTOR_VERSION,
        "coverage": coverage_counts,
    }
    if unclassified_reasons:
        patterns_meta["unclassified_reasons"] = unclassified_reasons

    moves = analysis.get("moves", [])
    acpl_value = analysis.get("total_acpl")
    analysis_block = {
        "acpl": round(acpl_value, 1) if isinstance(acpl_value, (int, float)) else None,
        "accuracy": analysis.get("accuracy"),
        "moves_analyzed": sum(1 for m in moves if m.get("analyzed", True)),
        "moves_total": len(moves),
        "evaluation_errors": analysis.get("evaluation_errors", 0),
        "phase_stats": phase_stats,
        "segment_stats": analysis_obj.segment_stats,
        "chess_phase_stats": analysis_obj.chess_phase_stats,
    }

    cache = {
        "hit": cache_hit,
        "layer": getattr(analysis_obj, "_cache_layer", "none"),
        "key": f"{game_id}_{detected_color}_d{depth}{_cache_policy(depth)}",
    }

    report_text = report or ""
    response = {
        "schema_version": SCHEMA_VERSION,
        "game_id": game_id,
        "username": username,
        "color": detected_color,
        "mode": mode,
        "depth": depth,
        "status": status,
        "partial": bool(unanalyzed),
        "errors": errors,
        "unanalyzed_plies": unanalyzed,
        "timings": timings,
        "engine": _engine_block(depth, None if cache_hit else engine_client.get_current_hash()),
        "cache": cache,
        "analysis": analysis_block,
        "flagged_moves": flagged,
        "patterns": patterns,
        "patterns_meta": patterns_meta,
        "unclassified": unclassified,
        "llm": {
            "status": "ok" if llm_ok else "degraded",
            "provider": report_source,
            "degraded": not llm_ok,
            "reason": (
                "ok" if llm_ok else ("llm_disabled" if not use_llm else "all_providers_failed")
            ),
            "attempts": _llm_attempts(cascade_log),
            "configured_providers": llm_status.get("total_configured", 0),
            "timeout_s": round(llm_timeout, 3),
            "tokens": tokens,
        },
        "report": report_text,
        "report_meta": {
            "source": source_label,
            "format": "markdown",
            "chars": len(report_text),
            "full_chars": len(report_text),
            "truncated": _report_truncated(report_text),
        },
        # Legacy alias kept for one release (K7).
        "cascade_log": cascade_log,
        "flags": {
            "cloud_eval": "off_by_default",
            "bfs_scope": "blunder+mistake+inaccuracy",
        },
    }

    # FIX-017: compact 2.1 is the default; schema 1.2 is opt-in as "detailed".
    if output_format in ("compact", "both"):
        from lichess_analyzer_mcp.services.compact_serializer import (
            to_compact_v2,
            validate_compact,
        )

        compact = to_compact_v2(
            response,
            game_meta=game_info,
            moves=moves,
            pv_unavailable=pv_unavailable,
        )
        validate_compact(compact)
        if output_format == "compact":
            return compact
        return {"compact": compact, "detailed": response}
    return response


@app.tool("lichess_coaching_single_game")
@auditable
async def lichess_coaching_single_game(
    game_id: str,
    username: str = "",
    color: str = "",
    depth: int = 0,
    mode: str = "fast",
    output_format: str = "compact",
    use_llm: bool = True,
    ctx=None,
):
    """Deep coaching report for a single game.

    Fetches PGN, runs Stockfish analysis, detects single-game patterns,
    and generates an LLM coaching report. Depth 0 = auto (14).

    The detailed response follows contract v1.2 (see
    docs/PLAN_SINGLE_GAME_CALIBRATION_2026-11-07.md): every stage reports
    time, every flagged move carries an explanation or an explicit
    `explanation_source="none"`, and an unmeasured move never looks like a
    perfect one (`cp_loss=null`, `analyzed=false`).

    Auto-detects player color from username via game metadata or PGN headers.
    If username is provided, color parameter is ignored.

    Falls back to MCP sampling (IDE's current LLM) when external API providers
    are unavailable.

    Args:
        game_id: Lichess game ID (8 chars)
        username: Lichess username (auto-detects color — recommended)
        color: Your color ('white' or 'black', fallback if no username)
        depth: Stockfish analysis depth (8-24, 0=auto)
        mode: Budget profile — 'fast' (60 s hard deadline) or 'deep' (120 s)
        output_format: 'compact' (schema 2.1, default), 'detailed' (contract
            v1.2) or 'both' -> {"compact": ..., "detailed": ...}.
            'full' is a deprecated alias for 'detailed'.
        use_llm: False skips every LLM provider (deterministic report only)
    """
    call_started = time.perf_counter()
    mode = mode if mode in BUDGETS else "fast"
    budget_cfg = budget_for_mode(mode)

    if depth == 0:
        depth = DEPTH_DEFAULTS["standard"]["single_game"]
    depth = max(
        DEPTH_DEFAULTS["limits"]["min"],
        min(DEPTH_DEFAULTS["limits"]["max_single_game"], depth),
    )

    deadline_s = float(budget_cfg["total_s"])

    try:
        output_format = _normalize_format(output_format)
        data = collect_single_game(
            game_id,
            color or "white",
            depth,
            username=username,
            deadline_s=deadline_s,
            mode=mode,
            include_obj=True,
        )
        analysis_obj = data.get("analysis_obj")
        if analysis_obj is None:
            raise ValueError("analysis produced no moves")
        return await build_response(
            game_id=game_id,
            username=username,
            detected_color=data.get("color", color or "white"),
            depth=depth,
            mode=mode,
            deadline_s=deadline_s,
            call_started=call_started,
            analysis_obj=analysis_obj,
            io_s=float(data.get("timings", {}).get("io_s", 0.0)),
            use_llm=use_llm,
            ctx=ctx,
            output_format=output_format,
        )
    except Exception as e:
        log.exception("coaching single game error | game=%s", game_id)
        return {
            "schema_version": SCHEMA_VERSION,
            "game_id": game_id,
            "username": username,
            "color": color or "white",
            "mode": mode,
            "depth": depth,
            "status": "error",
            "partial": False,
            "errors": [{"code": "PIPELINE_ERROR", "message": str(e)}],
            "unanalyzed_plies": [],
            "timings": {
                "io_s": 0.0,
                "engine_s": 0.0,
                "llm_s": 0.0,
                "overhead_s": round(time.perf_counter() - call_started, 3),
                "total_s": round(time.perf_counter() - call_started, 3),
                "deadline_s": deadline_s,
                "budget_used": None,
                "engine_calls": 0,
                "engine_timeouts": 0,
                "engine_retries": 0,
                "cache_hit": False,
            },
            "engine": _engine_block(depth, None),
            "cache": {"hit": False, "layer": "none", "key": None},
            "analysis": {
                "acpl": None,
                "accuracy": None,
                "moves_analyzed": 0,
                "moves_total": 0,
                "evaluation_errors": 0,
                "phase_stats": {},
            },
            "flagged_moves": [],
            "report": "",
            "report_meta": {
                "source": "none",
                "format": "markdown",
                "chars": 0,
                "full_chars": 0,
                "truncated": False,
            },
            "patterns": [],
            "patterns_meta": {
                "scope": "single_game",
                "cross_game_suppressed": True,
                "reason": "Pipeline failed before pattern detection.",
                "detector_version": DETECTOR_VERSION,
                "coverage": {"flagged": 0, "matched": 0, "unclassified": 0},
            },
            "unclassified": [],
            "llm": {
                "status": "degraded",
                "provider": "none",
                "degraded": True,
                "reason": "pipeline_error",
                "attempts": [],
                "configured_providers": get_llm_status().get("total_configured", 0),
                "timeout_s": 0.0,
                "tokens": {"input": 0, "output": 0},
            },
            "cascade_log": [],
            "error": str(e),
        }
