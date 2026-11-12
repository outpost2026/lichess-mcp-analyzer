"""Compact single-game JSON (schema 2.1) — pure serialization, no IO.

The full contract v1.2 payload exists for debugging and cross-game work. For
LLM consumption only a small, lossless-for-coaching subset is needed: game
metadata, summary, flagged moves, patterns, short PVs and FENs for the
expensive moments.

Design rules (handoff lichess_fix_v2):
  R1 derive, don't store   — win_prob / check / explanation are dropped
  R2 one source of truth   — flags[] is authoritative, report is a summary
  R3 count, don't enumerate — no legal-move lists
  R4 PV capped at 3 moves
  R5 instrumentation out   — timings, cache, engine policy not emitted
  R6 no empty arrays       — patterns only at top level
  R7 FEN only above 100 cp
  R8 no null noise         — optional keys omitted when empty

v3 additions (handoff lichess_fix_v3):
  - eval_before/eval_after for cp > 200 or blunder/mistake (FIX-015)
  - username in the game block when known (FIX-020)
  - patterns per flag (CAND-E) and consecutive-error clusters (CAND-F)
  - pv_unavailable[ply] = reason when a blunder/mistake has no PV (FIX-014)

2.1 additions (P0-7 / P0-8):
  - flags[].pstatus = "matched" | "unclassified"; an unclassified flag always
    carries `why` (the measured reason no pattern covers it, never a guessed
    mechanism — D4 keeps new patterns out until the taxonomy is calibrated).
  - patterns_meta is mandatory, so an empty `patterns` list always has a reason.
  - patterns_meta.coverage = {flagged, matched, unclassified}.
  - phase_method = which phase source the detectors used (P0-3).
  - top-level `unclassified` = the discovery feed: critical moments no pattern
    explains, ordered by ply. Omitted only when empty.

Null policy (FIX-016), documented in the schema as well:
  - `rank: null`  -> rank was not measured (engine timeout), never 0 or 1.
  - `motif`        -> omitted when the move has no tactical motif; a motif is
                      always a string when present.
  - eval fields    -> omitted when the flag is outside the FIX-015 window or
                      the evaluation was not measured.
  - `acpl` / phase ACPL -> null when the phase had no measured move.

Nothing here invents data: unavailable values are emitted as `null` (and the
schema explicitly allows it) or the key is omitted.
"""

from __future__ import annotations

import json
import re

from lichess_analyzer_mcp.models.pattern import (
    PATTERN_STATUSES,
    PATTERN_STATUS_MATCHED,
    PATTERN_STATUS_UNCLASSIFIED,
    UNCLASSIFIED_NOT_CLASSIFIED,
    UNCLASSIFIED_REASONS,
)
from lichess_analyzer_mcp.services.eval_consistency import eval_invariant_holds

SCHEMA_V = "2.1"
MAX_REPORT_CHARS = 900
FEN_CP_THRESHOLD = 100
EVAL_CP_THRESHOLD = 200
PV_UNAVAILABLE_REASONS = (
    "engine_timeout",
    "engine_error",
    "no_engine_lines",
    "engine_lines_empty",
    "retry_budget_exhausted",
    "no_fen",
)

_PHASES = ("opening", "middlegame", "endgame")
_CLASSES = ("blunder", "mistake", "inaccuracy")
_SEVERITIES = ("low", "medium", "high", "critical")
_RESULTS = ("1-0", "0-1", "1/2-1/2", "*")


def _cp(value) -> float | int | None:
    if not isinstance(value, (int, float)):
        return None
    return int(value) if float(value).is_integer() else round(float(value), 1)


def _severity(conf: float | None, declared: str | None) -> str:
    if declared in _SEVERITIES:
        return declared
    # Deterministic mapping used only when the detector omitted the field.
    c = conf if isinstance(conf, (int, float)) else 0.0
    if c >= 0.75:
        return "critical"
    if c >= 0.5:
        return "high"
    if c >= 0.25:
        return "medium"
    return "low"


def _opening(meta: dict) -> str:
    name = (meta.get("opening") or "").strip()
    eco = (meta.get("opening_eco") or "").strip()
    if eco and name:
        return f"{eco} {name}"
    return name or eco


def _phase(stats: dict, phase: str) -> list:
    entry = stats.get(phase) or {}
    acpl = entry.get("acpl")
    flagged = entry.get("flagged", entry.get("errors", 0))
    return [acpl if isinstance(acpl, (int, float)) else None, int(flagged or 0)]


def _fen_by_ply(moves: list[dict] | None) -> dict[int, str]:
    if not moves:
        return {}
    return {int(m["ply"]): m.get("fen", "") for m in moves if m.get("ply") and m.get("fen")}


def _flag(
    flag: dict,
    fens: dict[int, str],
    cover: dict[int, list[str]] | None = None,
) -> dict:
    ply = int(flag.get("ply") or 0)
    cp = _cp(flag.get("cp_loss"))
    out = {
        "ply": ply,
        "move": flag.get("san") or "",
        "class": flag.get("classification"),
        "cp": cp,
        "best": flag.get("best_move_san") or "",
        # FIX-016: null means "not measured", never zero and never a guess.
        "rank": int(flag["played_rank"]) if int(flag.get("played_rank") or 0) >= 1 else None,
    }
    # FIX-015: an LLM cannot narrate a swing it cannot see.
    # FIX-023: ... and it must not narrate a contradiction: when the eval pair
    # disagrees with cp_loss, omit both fields (raw values stay in detailed).
    if isinstance(cp, (int, float)) and (
        cp > EVAL_CP_THRESHOLD or out["class"] in ("blunder", "mistake")
    ):
        eval_before = _cp(flag.get("eval_before"))
        eval_after = _cp(flag.get("eval_after"))
        if (
            eval_before is not None
            and eval_after is not None
            and eval_invariant_holds(eval_before, eval_after, cp)
        ):
            out["eval_before"] = eval_before
            out["eval_after"] = eval_after
    # FIX-016: a genuinely absent motif is omitted; present motifs stay strings.
    motif = flag.get("motif")
    if motif:
        out["motif"] = motif
    # FIX-027: a blunder whose best line is a forced mate must not read as
    # "eval unknown". Only blunders carry the field (compact size budget).
    if out["class"] == "blunder":
        lines = flag.get("engine_lines") or []
        best_line = min(lines, key=lambda line: line.get("rank") or 99) if lines else {}
        mate_in = best_line.get("mate_in")
        if isinstance(mate_in, int) and mate_in != 0:
            out["mate_in"] = mate_in
    # CAND-E: which behavioural patterns this single mistake feeds.
    if cover and ply in cover:
        out["patterns"] = cover[ply]
    # P0-7: silence about a flagged move is a contract violation. `pstatus` is
    # always present; an unclassified move always carries `why`.
    status = flag.get("pattern_status")
    why = flag.get("unclassified_reason")
    if status not in PATTERN_STATUSES:
        status = PATTERN_STATUS_MATCHED if (cover and ply in cover) else PATTERN_STATUS_UNCLASSIFIED
        why = None
    out["pstatus"] = status
    if status == PATTERN_STATUS_UNCLASSIFIED:
        # A payload that predates P0-7 is reported as `not_classified`; the
        # serializer never invents a mechanism it cannot measure.
        out["why"] = why or UNCLASSIFIED_NOT_CLASSIFIED
    return out


def _clusters(flags: list[dict], min_count: int = 3) -> list[dict]:
    """CAND-F: consecutive flagged moves (same side, every second ply)."""
    out: list[dict] = []
    run: list[dict] = []
    for flag in flags:
        if not isinstance(flag.get("cp"), (int, float)):
            continue
        if run and int(flag["ply"]) == int(run[-1]["ply"]) + 2:
            run.append(flag)
            continue
        if len(run) >= min_count:
            out.append(_cluster(run))
        run = [flag]
    if len(run) >= min_count:
        out.append(_cluster(run))
    return out


def _cluster(run: list[dict]) -> dict:
    return {
        "from": int(run[0]["ply"]),
        "to": int(run[-1]["ply"]),
        "count": len(run),
        "total_cp": _cp(sum(flag["cp"] for flag in run)),
    }


def _pv(flag: dict) -> list[str]:
    lines = flag.get("engine_lines") or []
    ranked = sorted(lines, key=lambda line: line.get("rank") or 99)
    if not ranked:
        return []
    return [san for san in (ranked[0].get("pv") or [])[:3] if san]


def _clip_report(text: str, limit: int = MAX_REPORT_CHARS) -> str | None:
    """Clip at the last sentence/paragraph boundary inside the limit.

    The deterministic report starts with a ~250-char disclaimer that the
    pipeline never called an LLM. In compact JSON that fact already lives in
    `llm.status`, so the preamble is dropped and the budget goes to the actual
    coaching content instead.
    """
    text = (text or "").strip()
    if not text:
        return None
    first_section = text.find("\n## ")
    if text.startswith("# ") and first_section > 0:
        preamble = text[:first_section].lower()
        if "deterministick" in preamble:
            text = text[first_section + 1 :]
    if len(text) <= limit:
        return text
    window = text[:limit]
    cuts = [window.rfind(sep) for sep in (". ", ".\n", "\n\n")]
    cut = max(cuts)
    if cut >= limit // 3:
        return window[: cut + 1].rstrip()
    return None  # no safe boundary — omit rather than emit broken text


def _llm(block: dict | None) -> dict | None:
    if not block:
        return None
    provider = block.get("provider") or "unknown"
    status = block.get("status")
    if provider == "deterministic" or status == "degraded":
        status = "failed"
    if status not in ("ok", "degraded", "failed"):
        status = "failed"
    out = {"status": status, "provider": provider}
    reason = block.get("reason")
    if reason and reason != "ok":
        out["reason"] = reason
    return out


def _phase_method(moves: list[dict] | None) -> str:
    """Which phase source the detectors used (P0-3) — never guessed."""
    values = {
        m.get("phase_method")
        for m in (moves or [])
        if isinstance(m, dict) and m.get("phase_method")
    }
    if not values:
        return "ply_segment"
    if len(values) == 1:
        return str(next(iter(values)))
    return "mixed"


def _patterns_meta(full: dict, coverage: dict) -> dict:
    """P0-8: patterns_meta is mandatory, so an empty `patterns` list has a reason."""
    src = full.get("patterns_meta") or {}
    reason = (src.get("reason") or "").strip()
    if not reason:
        reason = (
            "No flagged move met a single-game pattern threshold. "
            "Cross-game detectors need >=3 games and are suppressed."
            if coverage["unclassified"]
            else "Single-game scope: only per-move evidence is aggregated. "
            "Cross-game detectors need >=3 games and are suppressed."
        )
    out = {
        "scope": "single_game",
        "cross_game_suppressed": True,
        "reason": reason,
        "coverage": coverage,
    }
    detector_version = src.get("detector_version")
    if isinstance(detector_version, str) and detector_version:
        out["detector_version"] = detector_version
    return out


def to_compact_v2(
    full: dict,
    *,
    game_meta: dict | None = None,
    moves: list[dict] | None = None,
    pv_unavailable: dict[int | str, str] | None = None,
) -> dict:
    """Serialize a contract v1.2 coaching payload to schema 2.1.

    Args:
        full: `lichess_coaching_single_game` response (schema 1.2).
        game_meta: `analysis["game"]` (GameSummary dict) — full payload does
            not carry it, so callers that have it should pass it.
        moves: optional `analysis["moves"]`; used for `fen_before` when the
            flagged move itself does not carry a FEN.
        pv_unavailable: optional `{ply: reason}` from `pv_recovery`. When a
            blunder/mistake still has no PV, the reason is published instead
            of silently omitting the key (FIX-014).
    """
    meta = game_meta or {}
    analysis = full.get("analysis") or {}
    fens = _fen_by_ply(moves)

    game = {
        "id": full.get("game_id") or meta.get("id") or "",
        "color": full.get("color") if full.get("color") in ("white", "black") else "white",
        "result": meta.get("result") if meta.get("result") in _RESULTS else "*",
        "opening": _opening(meta),
        "depth": int(full.get("depth") or 0),
    }
    if meta.get("time_control"):
        game["tc"] = meta["time_control"]
    # FIX-020: keeps compact JSONs groupable by player without the full payload.
    # Anonymous games (Lichess/PGN placeholder) must not look like a real player.
    username = (full.get("username") or meta.get("player_name") or "").strip()
    if username.lower() in ("anonymous", "?", "-"):
        username = ""
    if username:
        game["username"] = username
    date = (meta.get("date") or "").strip()
    if re.fullmatch(r"\d{4}\.\d{2}\.\d{2}", date):
        date = date.replace(".", "-")  # PGN style -> ISO-ish, stable for LLM
    # An unknown PGN date is "????.??.??" - never publish a placeholder.
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        game["date"] = date

    stats = analysis.get("phase_stats") or {}
    summary = {
        "acpl": analysis.get("acpl"),
        "acc": analysis.get("accuracy"),
        "phases": {phase: _phase(stats, phase) for phase in _PHASES},
    }

    patterns = []
    pattern_plies: dict[int, list[str]] = {}
    for pattern in full.get("patterns") or []:
        plies = sorted({int(e["ply"]) for e in pattern.get("evidence") or [] if e.get("ply")})
        pattern_id = pattern.get("pattern_id") or ""
        patterns.append(
            {
                "id": pattern_id,
                "conf": pattern.get("confidence"),
                "freq": int(pattern.get("frequency") or 1),
                "sev": _severity(pattern.get("confidence"), pattern.get("severity")),
                "plie": plies,
            }
        )
        for ply in plies:
            if pattern_id:
                pattern_plies.setdefault(ply, []).append(pattern_id)

    flags = []
    pv: dict[str, list[str]] = {}
    missing_pv: list[tuple[str, str | None]] = []
    for raw in sorted(full.get("flagged_moves") or [], key=lambda f: f.get("ply") or 0):
        if raw.get("classification") not in _CLASSES:
            continue
        flag = _flag(raw, fens, pattern_plies)
        flags.append(flag)
        ply = str(flag["ply"])
        line = _pv(raw)
        if line:
            pv[ply] = line
        elif flag["class"] in ("blunder", "mistake"):
            missing_pv.append((ply, raw.get("pv_error")))

    coverage = {
        "flagged": len(flags),
        "matched": sum(1 for flag in flags if flag["pstatus"] == PATTERN_STATUS_MATCHED),
        "unclassified": sum(1 for flag in flags if flag["pstatus"] == PATTERN_STATUS_UNCLASSIFIED),
    }
    unclassified = [
        {"ply": flag["ply"], "class": flag["class"], "cp": flag["cp"], "why": flag["why"]}
        for flag in flags
        if flag["pstatus"] == PATTERN_STATUS_UNCLASSIFIED
    ]

    compact: dict = {
        "v": SCHEMA_V,
        "game": game,
        "summary": summary,
        "phase_method": _phase_method(moves),
        "flags": flags,
        "patterns": patterns,
        "patterns_meta": _patterns_meta(full, coverage),
    }

    # P0-7: the discovery feed — critical moments no pattern explains. Omitted
    # when empty (R8: no null noise), never omitted when non-empty.
    if unclassified:
        compact["unclassified"] = unclassified

    if pv:
        compact["pv"] = pv
    unavailable: dict[str, str] = {}
    for key, reason in (pv_unavailable or {}).items():
        ply = str(int(key))
        if ply not in pv and reason:
            unavailable[ply] = str(reason)
    for ply, reason in missing_pv:
        if ply not in pv and ply not in unavailable:
            unavailable[ply] = str(reason or "engine_lines_empty")
    if unavailable:
        compact["pv_unavailable"] = unavailable

    clusters = _clusters(flags)
    if clusters:
        compact["clusters"] = clusters
    fen_before = {
        str(flag["ply"]): fens[flag["ply"]]
        for flag in flags
        if flag["cp"] is not None and flag["cp"] > FEN_CP_THRESHOLD and flag["ply"] in fens
    }
    if fen_before:
        compact["fen_before"] = fen_before
    report = _clip_report(full.get("report") or "")
    if report:
        compact["report"] = report
    llm = _llm(full.get("llm"))
    if llm:
        compact["llm"] = llm
    return compact


_REQUIRED_TOP = {"v", "game", "summary", "phase_method", "flags", "patterns", "patterns_meta"}
_REQUIRED_GAME = {"id", "color", "result", "opening", "depth"}
_REQUIRED_FLAG = {"ply", "move", "class", "cp", "best", "rank", "pstatus"}
_REQUIRED_PATTERN = {"id", "conf", "freq", "sev", "plie"}
_REQUIRED_PATTERNS_META = {"scope", "cross_game_suppressed", "reason", "coverage"}
_PHASE_METHODS = ("ply_segment", "material", "mixed")


def _fail(path: str, message: str) -> None:
    raise ValueError(f"compact schema {SCHEMA_V}: {path} {message}")


def _check_keys(obj: dict, required: set[str], allowed: set[str], path: str) -> None:
    missing = required - obj.keys()
    if missing:
        _fail(path, f"missing keys {sorted(missing)}")
    extra = obj.keys() - allowed
    if extra:
        _fail(path, f"unexpected keys {sorted(extra)}")


def validate_compact(data: dict) -> None:
    """Structural validation mirroring `schemas/single_game_v2_compact.json`.

    Dependency-free on purpose: ETL must run in any environment. The test
    suite additionally validates real output against the JSON Schema file.
    Raises ValueError on the first problem.
    """
    if not isinstance(data, dict):
        _fail("$", "must be an object")
    _check_keys(
        data,
        _REQUIRED_TOP,
        _REQUIRED_TOP
        | {"pv", "pv_unavailable", "clusters", "fen_before", "report", "llm", "unclassified"},
        "$",
    )
    if data["v"] != SCHEMA_V:
        _fail("$.v", f"must be {SCHEMA_V!r}")
    if data["phase_method"] not in _PHASE_METHODS:
        _fail("$.phase_method", f"must be one of {_PHASE_METHODS}")

    game = data["game"]
    _check_keys(game, _REQUIRED_GAME, _REQUIRED_GAME | {"username", "tc", "date"}, "$.game")
    if not isinstance(game["id"], str) or not game["id"]:
        _fail("$.game.id", "must be a non-empty string")
    if game["color"] not in ("white", "black"):
        _fail("$.game.color", "must be white or black")
    if game["result"] not in _RESULTS:
        _fail("$.game.result", f"must be one of {_RESULTS}")
    if not isinstance(game["opening"], str):
        _fail("$.game.opening", "must be a string")
    if not isinstance(game["depth"], int) or not 8 <= game["depth"] <= 24:
        _fail("$.game.depth", "must be an integer 8..24")
    if "username" in game and (not isinstance(game["username"], str) or not game["username"]):
        _fail("$.game.username", "must be a non-empty string when present")

    summary = data["summary"]
    _check_keys(summary, {"acpl", "acc", "phases"}, {"acpl", "acc", "phases"}, "$.summary")
    for key in ("acpl", "acc"):
        value = summary[key]
        if value is not None and not isinstance(value, (int, float)):
            _fail(f"$.summary.{key}", "must be number or null")
    phases = summary["phases"]
    _check_keys(phases, set(_PHASES), set(_PHASES), "$.summary.phases")
    for phase in _PHASES:
        entry = phases[phase]
        if not isinstance(entry, list) or len(entry) != 2:
            _fail(f"$.summary.phases.{phase}", "must be [acpl, flag_count]")
        acpl, count = entry
        if acpl is not None and not isinstance(acpl, (int, float)):
            _fail(f"$.summary.phases.{phase}[0]", "must be number or null")
        if not isinstance(count, int) or count < 0:
            _fail(f"$.summary.phases.{phase}[1]", "must be an integer >= 0")

    for idx, flag in enumerate(data["flags"]):
        path = f"$.flags[{idx}]"
        _check_keys(
            flag,
            _REQUIRED_FLAG,
            _REQUIRED_FLAG | {"motif", "eval_before", "eval_after", "patterns", "mate_in", "why"},
            path,
        )
        if not isinstance(flag["ply"], int) or flag["ply"] < 1:
            _fail(f"{path}.ply", "must be an integer >= 1")
        if flag["class"] not in _CLASSES:
            _fail(f"{path}.class", f"must be one of {_CLASSES}")
        if not isinstance(flag["cp"], (int, float)):
            _fail(f"{path}.cp", "must be a number")
        if not isinstance(flag["best"], str):
            _fail(f"{path}.best", "must be a string")
        if flag["rank"] is not None and (not isinstance(flag["rank"], int) or flag["rank"] < 1):
            _fail(f"{path}.rank", "must be an integer >= 1 or null")
        if "motif" in flag and not isinstance(flag["motif"], str):
            _fail(f"{path}.motif", "must be a string")
        for key in ("eval_before", "eval_after"):
            if key in flag and not isinstance(flag[key], (int, float)):
                _fail(f"{path}.{key}", "must be a number")
        if "mate_in" in flag:
            if not isinstance(flag["mate_in"], int) or flag["mate_in"] == 0:
                _fail(f"{path}.mate_in", "must be a non-zero integer")
        if "patterns" in flag:
            if not isinstance(flag["patterns"], list) or not flag["patterns"]:
                _fail(f"{path}.patterns", "must be a non-empty array")
            if not all(isinstance(p, str) and p for p in flag["patterns"]):
                _fail(f"{path}.patterns", "must contain non-empty strings")
        # P0-7: a flagged move is either covered by a pattern or explains itself.
        if flag["pstatus"] not in PATTERN_STATUSES:
            _fail(f"{path}.pstatus", f"must be one of {PATTERN_STATUSES}")
        if flag["pstatus"] == PATTERN_STATUS_UNCLASSIFIED:
            if flag.get("why") not in UNCLASSIFIED_REASONS:
                _fail(f"{path}.why", f"must be one of {UNCLASSIFIED_REASONS} when unclassified")
            if "patterns" in flag:
                _fail(f"{path}.patterns", "must be absent when pstatus is unclassified")
        else:
            if "why" in flag:
                _fail(f"{path}.why", "must be absent when pstatus is matched")
            if "patterns" not in flag:
                _fail(f"{path}.patterns", "must be present when pstatus is matched")

    for idx, pattern in enumerate(data["patterns"]):
        path = f"$.patterns[{idx}]"
        _check_keys(pattern, _REQUIRED_PATTERN, _REQUIRED_PATTERN, path)
        if not isinstance(pattern["id"], str) or not pattern["id"]:
            _fail(f"{path}.id", "must be a non-empty string")
        if not isinstance(pattern["conf"], (int, float)) or not 0 <= pattern["conf"] <= 1:
            _fail(f"{path}.conf", "must be a number 0..1")
        if not isinstance(pattern["freq"], int) or pattern["freq"] < 1:
            _fail(f"{path}.freq", "must be an integer >= 1")
        if pattern["sev"] not in _SEVERITIES:
            _fail(f"{path}.sev", f"must be one of {_SEVERITIES}")
        if not isinstance(pattern["plie"], list) or not all(
            isinstance(p, int) for p in pattern["plie"]
        ):
            _fail(f"{path}.plie", "must be an array of integers")

    meta = data["patterns_meta"]
    _check_keys(
        meta,
        _REQUIRED_PATTERNS_META,
        _REQUIRED_PATTERNS_META | {"detector_version"},
        "$.patterns_meta",
    )
    if meta["scope"] != "single_game":
        _fail("$.patterns_meta.scope", "must be 'single_game'")
    if meta["cross_game_suppressed"] is not True:
        _fail("$.patterns_meta.cross_game_suppressed", "must be true")
    if not isinstance(meta["reason"], str) or not meta["reason"]:
        _fail("$.patterns_meta.reason", "must be a non-empty string")
    counts = meta["coverage"]
    _check_keys(
        counts,
        {"flagged", "matched", "unclassified"},
        {"flagged", "matched", "unclassified"},
        "$.patterns_meta.coverage",
    )
    for key in ("flagged", "matched", "unclassified"):
        if not isinstance(counts[key], int) or counts[key] < 0:
            _fail(f"$.patterns_meta.coverage.{key}", "must be an integer >= 0")
    if counts["matched"] + counts["unclassified"] != counts["flagged"]:
        _fail(
            "$.patterns_meta.coverage",
            "matched + unclassified must equal flagged",
        )
    if counts["flagged"] != len(data["flags"]):
        _fail("$.patterns_meta.coverage.flagged", "must equal the number of flags")

    unclassified = data.get("unclassified")
    if unclassified is not None:
        if not isinstance(unclassified, list) or not unclassified:
            _fail("$.unclassified", "must be a non-empty array when present")
        expected = {
            (flag["ply"], flag["class"])
            for flag in data["flags"]
            if flag["pstatus"] == PATTERN_STATUS_UNCLASSIFIED
        }
        seen = set()
        for idx, item in enumerate(unclassified):
            path = f"$.unclassified[{idx}]"
            _check_keys(item, {"ply", "class", "cp", "why"}, {"ply", "class", "cp", "why"}, path)
            if not isinstance(item["ply"], int) or item["ply"] < 1:
                _fail(f"{path}.ply", "must be an integer >= 1")
            if item["class"] not in _CLASSES:
                _fail(f"{path}.class", f"must be one of {_CLASSES}")
            if not isinstance(item["cp"], (int, float)):
                _fail(f"{path}.cp", "must be a number")
            if item["why"] not in UNCLASSIFIED_REASONS:
                _fail(f"{path}.why", f"must be one of {UNCLASSIFIED_REASONS}")
            seen.add((item["ply"], item["class"]))
        if seen != expected:
            _fail("$.unclassified", "must list exactly the unclassified flags")

    pv = data.get("pv")
    if pv is not None:
        if not isinstance(pv, dict):
            _fail("$.pv", "must be an object")
        for key, line in pv.items():
            if not re.fullmatch(r"[1-9]\d*", str(key)):
                _fail(f"$.pv[{key!r}]", "key must be a ply number")
            if not isinstance(line, list) or not 1 <= len(line) <= 3:
                _fail(f"$.pv[{key!r}]", "must be an array of 1..3 SAN moves")
            if not all(isinstance(san, str) for san in line):
                _fail(f"$.pv[{key!r}]", "SAN moves must be strings")

    pv_unavailable = data.get("pv_unavailable")
    if pv_unavailable is not None:
        if not isinstance(pv_unavailable, dict):
            _fail("$.pv_unavailable", "must be an object")
        for key, reason in pv_unavailable.items():
            if not re.fullmatch(r"[1-9]\d*", str(key)):
                _fail(f"$.pv_unavailable[{key!r}]", "key must be a ply number")
            if reason not in PV_UNAVAILABLE_REASONS:
                _fail(
                    f"$.pv_unavailable[{key!r}]",
                    f"reason must be one of {PV_UNAVAILABLE_REASONS}",
                )

    clusters = data.get("clusters")
    if clusters is not None:
        if not isinstance(clusters, list):
            _fail("$.clusters", "must be an array")
        for idx, cluster in enumerate(clusters):
            path = f"$.clusters[{idx}]"
            _check_keys(
                cluster,
                {"from", "to", "count", "total_cp"},
                {"from", "to", "count", "total_cp"},
                path,
            )
            if not isinstance(cluster["from"], int) or cluster["from"] < 1:
                _fail(f"{path}.from", "must be an integer >= 1")
            if not isinstance(cluster["to"], int) or cluster["to"] < cluster["from"]:
                _fail(f"{path}.to", "must be an integer >= from")
            if not isinstance(cluster["count"], int) or cluster["count"] < 3:
                _fail(f"{path}.count", "must be an integer >= 3")
            if not isinstance(cluster["total_cp"], (int, float)):
                _fail(f"{path}.total_cp", "must be a number")

    fen_before = data.get("fen_before")
    if fen_before is not None:
        if not isinstance(fen_before, dict):
            _fail("$.fen_before", "must be an object")
        for key, fen in fen_before.items():
            if not re.fullmatch(r"[1-9]\d*", str(key)):
                _fail(f"$.fen_before[{key!r}]", "key must be a ply number")
            if not isinstance(fen, str) or len(fen.split()) < 4:
                _fail(f"$.fen_before[{key!r}]", "must be a FEN string")

    report = data.get("report")
    if report is not None:
        if not isinstance(report, str):
            _fail("$.report", "must be a string or null")
        if len(report) > MAX_REPORT_CHARS:
            _fail("$.report", f"must be <= {MAX_REPORT_CHARS} chars")

    llm = data.get("llm")
    if llm is not None:
        _check_keys(llm, {"status", "provider"}, {"status", "provider", "reason"}, "$.llm")
        if llm["status"] not in ("ok", "degraded", "failed"):
            _fail("$.llm.status", "must be ok/degraded/failed")
        if not isinstance(llm["provider"], str):
            _fail("$.llm.provider", "must be a string")


def compact_size(data: dict) -> int:
    """Characters of the minified JSON — the number used in the size budget."""
    return len(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
