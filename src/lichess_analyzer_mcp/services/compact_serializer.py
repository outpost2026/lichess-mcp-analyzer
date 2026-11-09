"""Compact single-game JSON (schema 2.0) — pure serialization, no IO.

The full contract v1.1 payload exists for debugging and cross-game work. For
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

Nothing here invents data: unavailable values are emitted as `null` (and the
schema explicitly allows it) or the key is omitted.
"""

from __future__ import annotations

import json
import re

SCHEMA_V = "2.0"
MAX_REPORT_CHARS = 1200
FEN_CP_THRESHOLD = 100

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


def _flag(flag: dict, fens: dict[int, str]) -> dict:
    ply = int(flag.get("ply") or 0)
    cp = _cp(flag.get("cp_loss"))
    out = {
        "ply": ply,
        "move": flag.get("san") or "",
        "class": flag.get("classification"),
        "cp": cp,
        "best": flag.get("best_move_san") or "",
        "rank": int(flag["played_rank"]) if int(flag.get("played_rank") or 0) >= 1 else None,
    }
    motif = flag.get("motif")
    if motif:
        out["motif"] = motif
    return out


def _pv(flag: dict) -> list[str]:
    lines = flag.get("engine_lines") or []
    ranked = sorted(lines, key=lambda line: line.get("rank") or 99)
    if not ranked:
        return []
    return [san for san in (ranked[0].get("pv") or [])[:3] if san]


def _clip_report(text: str, limit: int = MAX_REPORT_CHARS) -> str | None:
    """Clip at a sentence boundary; a report never ends mid-structure."""
    text = (text or "").strip()
    if not text:
        return None
    if len(text) <= limit:
        return text
    window = text[:limit]
    for sep in (". ", ".\n", "\n\n"):
        cut = window.rfind(sep)
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


def to_compact_v2(
    full: dict,
    *,
    game_meta: dict | None = None,
    moves: list[dict] | None = None,
) -> dict:
    """Serialize a contract v1.1 coaching payload to schema 2.0.

    Args:
        full: `lichess_coaching_single_game` response (schema 1.1).
        game_meta: `analysis["game"]` (GameSummary dict) — full payload does
            not carry it, so callers that have it should pass it.
        moves: optional `analysis["moves"]`; used for `fen_before` when the
            flagged move itself does not carry a FEN.
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
    date = (meta.get("date") or "").strip()
    if re.fullmatch(r"\d{4}\.\d{2}\.\d{2}", date):
        date = date.replace(".", "-")  # PGN style -> ISO-ish, stable for LLM
    if date:
        game["date"] = date

    stats = analysis.get("phase_stats") or {}
    summary = {
        "acpl": analysis.get("acpl"),
        "acc": analysis.get("accuracy"),
        "phases": {phase: _phase(stats, phase) for phase in _PHASES},
    }

    flags = []
    pv: dict[str, list[str]] = {}
    for raw in sorted(full.get("flagged_moves") or [], key=lambda f: f.get("ply") or 0):
        if raw.get("classification") not in _CLASSES:
            continue
        flag = _flag(raw, fens)
        flags.append(flag)
        line = _pv(raw)
        if line:
            pv[str(flag["ply"])] = line
    patterns = []
    for pattern in full.get("patterns") or []:
        plies = sorted({int(e["ply"]) for e in pattern.get("evidence") or [] if e.get("ply")})
        patterns.append(
            {
                "id": pattern.get("pattern_id") or "",
                "conf": pattern.get("confidence"),
                "freq": int(pattern.get("frequency") or 1),
                "sev": _severity(pattern.get("confidence"), pattern.get("severity")),
                "plie": plies,
            }
        )

    compact: dict = {
        "v": SCHEMA_V,
        "game": game,
        "summary": summary,
        "flags": flags,
        "patterns": patterns,
    }

    pv = {ply: line for ply, line in pv.items() if line}
    if pv:
        compact["pv"] = pv
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


_REQUIRED_TOP = {"v", "game", "summary", "flags", "patterns"}
_REQUIRED_GAME = {"id", "color", "result", "opening", "depth"}
_REQUIRED_FLAG = {"ply", "move", "class", "cp", "best", "rank"}
_REQUIRED_PATTERN = {"id", "conf", "freq", "sev", "plie"}


def _fail(path: str, message: str) -> None:
    raise ValueError(f"compact schema 2.0: {path} {message}")


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
        _REQUIRED_TOP | {"pv", "fen_before", "report", "llm"},
        "$",
    )
    if data["v"] != SCHEMA_V:
        _fail("$.v", f"must be {SCHEMA_V!r}")

    game = data["game"]
    _check_keys(game, _REQUIRED_GAME, _REQUIRED_GAME | {"tc", "date"}, "$.game")
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
        _check_keys(flag, _REQUIRED_FLAG, _REQUIRED_FLAG | {"motif"}, path)
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
