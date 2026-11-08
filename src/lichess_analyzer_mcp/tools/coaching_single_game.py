import json
import time

from lichess_analyzer_mcp.app import app
from lichess_analyzer_mcp.config.depth import BUDGETS, DEPTH_DEFAULTS, NODE_CAPS
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
from lichess_analyzer_mcp.services.pattern_detector import detect_single_game
from lichess_analyzer_mcp.services.prompt_builder import build_prompt
from lichess_analyzer_mcp.models.analysis import DETECTOR_VERSION

log = get_logger("coaching_single_game")

SCHEMA_VERSION = "1.1"
_FLAGGED = ("blunder", "mistake", "inaccuracy")


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
                "explanation": m.get("explanation") or "",
                "explanation_source": m.get("explanation_source") or "none",
            }
        )
    return out


def _phase_summary(analysis: dict) -> dict:
    moves = analysis.get("moves", [])
    result = {}
    for phase in ("opening", "middlegame", "endgame"):
        phase_moves = [m for m in moves if m.get("phase") == phase and m.get("analyzed", True)]
        if not phase_moves:
            continue
        measured = [m for m in phase_moves if isinstance(m.get("centipawn_loss"), (int, float))]
        acpl = (
            round(sum(m["centipawn_loss"] for m in measured) / len(measured), 1)
            if measured
            else None
        )
        result[phase] = {
            "acpl": acpl,
            "move_count": len(phase_moves),
            "flagged": sum(1 for m in phase_moves if m.get("classification") in _FLAGGED),
        }
    return result


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


@app.tool("lichess_coaching_single_game")
@auditable
async def lichess_coaching_single_game(
    game_id: str,
    username: str = "",
    color: str = "",
    depth: int = 0,
    mode: str = "fast",
    ctx=None,
):
    """Deep coaching report for a single game.

    Fetches PGN, runs Stockfish analysis, detects single-game patterns,
    and generates an LLM coaching report. Depth 0 = auto (14).

    The response follows contract v1.1 (see
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
        analysis = data.get("analysis", {})
        detected_color = data.get("color", color or "white")

        if analysis_obj is None or not analysis.get("moves"):
            raise ValueError("analysis produced no moves")

        patterns = detect_single_game(analysis_obj)
        flagged = _flagged_moves(analysis)
        unanalyzed = analysis.get("unanalyzed_plies", []) or []

        game_info = analysis.get("game", {})
        phase_stats = _phase_summary(analysis)
        phase_breakdown = (
            "; ".join(
                f"{p}: ACPL {s.get('acpl', '?')}, {s.get('flagged', 0)} chyb"
                for p, s in sorted(phase_stats.items())
            )
            or "(není k dispozici)"
        )

        def _move_lines(items: list[dict], limit: int = 10) -> str:
            return "\n".join(
                f"  ply {m.get('ply')}: {m.get('move_san')} (loss {_fmt_loss(m)}cp, "
                f"fáze={m.get('phase')}, check={m.get('was_in_check', False)}, "
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
            "bfs_json": json.dumps(bfs_raw, ensure_ascii=False, indent=2)[:2000],
            "time_control": game_info.get("time_control", "?"),
            "player_rating": game_info.get("player_rating", "?"),
            "opponent_rating": game_info.get("opponent_rating", "?"),
        }
        prompt = build_prompt(1, prompt_data)

        elapsed = time.perf_counter() - call_started
        llm_timeout = min(
            float(budget_cfg["llm_s"]),
            max(0.5, deadline_s - elapsed - float(budget_cfg["reserve_s"])),
        )
        t_llm = time.perf_counter()
        report, cascade_log, cascade_exhausted, report_source = safe_llm_call(
            prompt, f"single_game:{game_id}", timeout_s=llm_timeout
        )
        llm_s = time.perf_counter() - t_llm

        # MCP sampling fallback — use IDE's LLM when external APIs are exhausted.
        # `cascade_exhausted` is also True for the deterministic fallback, so a
        # real LLM gets a chance before the deterministic text is final.
        if cascade_exhausted and ctx is not None:
            try:
                mcp_content, mcp_log = await mcp_sample_fallback(
                    ctx, prompt, COACHING_SYSTEM_PROMPT
                )
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
            "llm"
            if llm_ok
            else ("deterministic" if report_source == "deterministic" else "data_dump")
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
        io_s = float(data.get("timings", {}).get("io_s", 0.0))
        cache_hit = bool(getattr(analysis_obj, "_cache_hit", False))
        # A cache hit ran no engine in this call; the stored stage timings
        # describe the run that produced the file, not this response.
        engine_s = 0.0 if cache_hit else float(analysis_timings.get("engine_s", 0.0))
        engine_calls = 0 if cache_hit else int(analysis.get("engine_calls", 0))
        engine_timeouts = 0 if cache_hit else int(analysis.get("engine_timeouts", 0))
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
                "Cross-game detectors need >=3 games and are suppressed."
            ),
            "detector_version": DETECTOR_VERSION,
        }

        moves = analysis.get("moves", [])
        acpl_value = analysis.get("total_acpl")
        analysis_block = {
            "acpl": round(acpl_value, 1) if isinstance(acpl_value, (int, float)) else None,
            "accuracy": analysis.get("accuracy"),
            "moves_analyzed": sum(1 for m in moves if m.get("analyzed", True)),
            "moves_total": len(moves),
            "evaluation_errors": analysis.get("evaluation_errors", 0),
            "phase_stats": phase_stats,
        }

        cache = {
            "hit": cache_hit,
            "layer": getattr(analysis_obj, "_cache_layer", "none"),
            "key": f"{game_id}_{detected_color}_d{depth}",
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
            "engine": {
                "limit": "depth",
                "depth": depth,
                "nodes_cap": NODE_CAPS.get(depth),
                "hash_mb": None if cache_hit else engine_client.get_current_hash(),
                "threads": 4,
            },
            "cache": cache,
            "analysis": analysis_block,
            "flagged_moves": flagged,
            "patterns": patterns,
            "patterns_meta": patterns_meta,
            "llm": {
                "status": "ok" if llm_ok else "degraded",
                "provider": report_source,
                "degraded": not llm_ok,
                "reason": "ok" if llm_ok else "all_providers_failed",
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
            },
            # Legacy alias kept for one release (K7).
            "cascade_log": cascade_log,
            "flags": {
                "cloud_eval": "off_by_default",
                "bfs_scope": "blunder+mistake+inaccuracy",
            },
        }
        return response
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
                "cache_hit": False,
            },
            "engine": {
                "limit": "depth",
                "depth": depth,
                "nodes_cap": NODE_CAPS.get(depth),
                "hash_mb": None,
                "threads": 4,
            },
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
            },
            "patterns": [],
            "patterns_meta": {
                "scope": "single_game",
                "cross_game_suppressed": True,
                "reason": "Pipeline failed before pattern detection.",
                "detector_version": DETECTOR_VERSION,
            },
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
