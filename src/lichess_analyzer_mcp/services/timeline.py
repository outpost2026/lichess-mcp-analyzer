"""T3.1/T3.2: merge the two single-perspective analyses into `game_full` 1.0.

Why this module exists
----------------------
`analyze_pgn` walks the whole PGN but only evaluates the plies of one colour,
so the dual cache already holds every ply exactly once: the white run measured
White's plies, the black run measured Black's. The full-game view is therefore
a **merge layer**, not a second engine pass.

Two things the merge must not do:

- it must not re-evaluate or interpolate anything (values come from the two
  caches verbatim);
- it must not publish a mover-POV number under a White-POV name. Every eval
  field in `game_full` 1.0 is White POV, and the mover-POV value travels next
  to it so the invariant is checkable.

`cp_loss` is a loss magnitude, so it is never sign-flipped. `win_prob` is
flipped for Black (1 - p), because a probability is not a score.

Missing plies are reported, never filled: `status="partial"` plus
`missing_plies` (known length) or an explicit unknown total.
"""

from __future__ import annotations

from typing import Iterable, NoReturn

from lichess_analyzer_mcp.models.game import GameAnalysis, MoveAnalysis

SCHEMA_NAME = "game_full"
SCHEMA_V = "1.0"
POV = "white"

STATUS_COMPLETE = "complete"
STATUS_PARTIAL = "partial"

_EPS = 1e-6

_PLY_REQUIRED = {
    "ply",
    "mover_color",
    "san",
    "uci",
    "class",
    "cp_loss",
    "eval_before_mover_cp",
    "eval_after_mover_cp",
    "eval_before_white_cp",
    "eval_after_white_cp",
    "win_prob_white_before",
    "win_prob_white_after",
    "fen_before",
    "best",
    "rank",
    "analyzed",
}


class TimelineMismatchError(ValueError):
    """Two analyses cannot describe the same game."""

    code = "TIMELINE_MISMATCH"


def _fail(path: str, message: str) -> NoReturn:
    raise ValueError(f"game_full schema {SCHEMA_V}: {path} {message}")


def mover_color(ply: int) -> str:
    """Odd ply = White, even ply = Black. One definition, used everywhere."""
    return "white" if ply % 2 == 1 else "black"


def _to_white_cp(value: float | None, color: str) -> float | None:
    if value is None:
        return None
    return float(value) if color == "white" else -float(value)


def _to_white_prob(value: float | None, color: str) -> float | None:
    if value is None:
        return None
    return float(value) if color == "white" else 1.0 - float(value)


def _ply_entry(move: MoveAnalysis, color: str) -> dict:
    measured = bool(move.analyzed)
    return {
        "ply": int(move.ply),
        "mover_color": color,
        "san": move.move_san,
        "uci": move.move_uci,
        # An unmeasured move has no class and no loss; null is the contract.
        "class": move.classification if measured else None,
        "cp_loss": float(move.centipawn_loss) if measured else None,
        "eval_before_mover_cp": float(move.eval_before) if measured else None,
        "eval_after_mover_cp": float(move.eval_after) if measured else None,
        "eval_before_white_cp": _to_white_cp(move.eval_before, color) if measured else None,
        "eval_after_white_cp": _to_white_cp(move.eval_after, color) if measured else None,
        "win_prob_white_before": _to_white_prob(move.win_prob_before, color) if measured else None,
        "win_prob_white_after": _to_white_prob(move.win_prob_after, color) if measured else None,
        "fen_before": move.fen,
        "best": move.best_move_san,
        "rank": int(move.played_rank) if measured and move.played_rank >= 1 else None,
        "analyzed": measured,
    }


def _game_block(analyses: dict[str, GameAnalysis]) -> dict:
    first = next(iter(analyses.values()))
    game = first.game
    return {
        "id": game.id,
        "white": game.player_name if game.color == "white" else game.opponent_name,
        "black": game.player_name if game.color == "black" else game.opponent_name,
        "result": game.result,
        "opening": game.opening,
        "eco": game.opening_eco,
        "time_control": game.time_control,
        "date": game.date,
        "url": game.url,
    }


def _source_block(analyses: dict[str, GameAnalysis]) -> dict:
    """Both colours are always present; an absent perspective says so."""
    block = {}
    for color in ("white", "black"):
        analysis = analyses.get(color)
        if analysis is None:
            block[color] = {
                "available": False,
                "mode": "",
                "acpl": None,
                "moves_measured": 0,
            }
            continue
        block[color] = {
            "available": True,
            "mode": analysis.mode,
            "acpl": round(analysis.total_acpl, 1),
            "moves_measured": sum(1 for m in analysis.moves if m.analyzed),
        }
    return block


def build_full_game(*analyses: GameAnalysis) -> dict:
    """Merge one or two single-perspective analyses into `game_full` 1.0.

    One analysis is legal: the result is a `partial` payload that names the
    colour it does not have. Two analyses of the same colour, or two different
    games, are errors — a merge must never guess which game it is describing.
    """
    by_color: dict[str, GameAnalysis] = {}
    for analysis in analyses:
        color = analysis.game.color
        if color not in ("white", "black"):
            raise TimelineMismatchError(f"analysis colour must be white or black, got {color!r}")
        if color in by_color:
            raise TimelineMismatchError(f"two analyses for colour {color!r}")
        by_color[color] = analysis

    if not by_color:
        raise TimelineMismatchError("at least one analysis is required")

    ids = {a.game.id for a in by_color.values() if a.game.id}
    if len(ids) > 1:
        raise TimelineMismatchError(f"analyses describe different games: {sorted(ids)}")

    entries: dict[int, dict] = {}
    for color, analysis in by_color.items():
        for move in analysis.moves:
            expected_color = mover_color(int(move.ply))
            if expected_color != color:
                raise TimelineMismatchError(
                    f"ply {move.ply} belongs to {expected_color}, but the {color} "
                    "analysis reported it"
                )
            if int(move.ply) in entries:
                raise TimelineMismatchError(f"ply {move.ply} appears in both analyses")
            entries[int(move.ply)] = _ply_entry(move, color)

    totals = [a.game_plies_total for a in by_color.values() if a.game_plies_total > 0]
    plies_total = max(totals) if totals else None

    if plies_total is not None:
        missing = [ply for ply in range(1, plies_total + 1) if ply not in entries]
        if any(ply > plies_total for ply in entries):
            raise TimelineMismatchError(f"analysis contains a ply beyond plies_total={plies_total}")
    else:
        # No PGN walk recorded the game length: name the gap, never invent it.
        missing = []

    unanalyzed = sorted(ply for ply, entry in entries.items() if not entry["analyzed"])
    expected_colours = {"white", "black"}
    complete = (
        plies_total is not None
        and not missing
        and not unanalyzed
        and set(by_color) == expected_colours
        and len(entries) == plies_total
    )

    plies = [entries[ply] for ply in sorted(entries)]
    return {
        "schema": SCHEMA_NAME,
        "v": SCHEMA_V,
        "pov": POV,
        "game": _game_block(by_color),
        "status": STATUS_COMPLETE if complete else STATUS_PARTIAL,
        "plies_total": plies_total,
        "missing_plies": missing,
        "unanalyzed_plies": unanalyzed,
        "coverage": {
            "white_plies": sum(1 for e in plies if e["mover_color"] == "white"),
            "black_plies": sum(1 for e in plies if e["mover_color"] == "black"),
            "merged_plies": len(plies),
            "expected_plies": plies_total,
            "missing_colours": sorted(expected_colours - set(by_color)),
        },
        "source": _source_block(by_color),
        "plies": plies,
    }


def validate_game_full(data: dict) -> None:
    """Semantic validation of a `game_full` 1.0 payload.

    Mirrors `schemas/game_full_v1.0.json` and adds the invariants a JSON
    Schema cannot express:

    - ply order and parity vs `mover_color`;
    - White-POV eval is exactly the mover-POV value, negated for Black;
    - `cp_loss` is a magnitude (>= 0) and is null exactly when unmeasured;
    - `status="complete"` implies full coverage and no gaps.
    """
    if not isinstance(data, dict):
        _fail("$", "must be an object")
    if data.get("schema") != SCHEMA_NAME:
        _fail("$.schema", f"must be {SCHEMA_NAME!r}")
    if data.get("v") != SCHEMA_V:
        _fail("$.v", f"must be {SCHEMA_V!r}")
    if data.get("pov") != POV:
        _fail("$.pov", "must be 'white'")
    if data.get("status") not in (STATUS_COMPLETE, STATUS_PARTIAL):
        _fail("$.status", "must be 'complete' or 'partial'")

    plies = data.get("plies")
    if not isinstance(plies, list) or not plies:
        _fail("$.plies", "must be a non-empty array")

    plies_total = data.get("plies_total")
    if plies_total is not None and not isinstance(plies_total, int):
        _fail("$.plies_total", "must be an integer or null")

    previous = 0
    for index, entry in enumerate(plies):
        path = f"$.plies[{index}]"
        if not isinstance(entry, dict):
            _fail(path, "must be an object")
        missing = _PLY_REQUIRED - entry.keys()
        if missing:
            _fail(path, f"is missing {sorted(missing)}")
        extra = entry.keys() - _PLY_REQUIRED
        if extra:
            _fail(path, f"has unexpected keys {sorted(extra)}")

        ply = entry["ply"]
        if not isinstance(ply, int) or ply < 1:
            _fail(f"{path}.ply", "must be a positive integer")
        if ply <= previous:
            _fail(f"{path}.ply", "must be strictly increasing (no duplicate plies)")
        previous = ply
        if plies_total is not None and ply > plies_total:
            _fail(f"{path}.ply", f"exceeds plies_total={plies_total}")

        color = entry["mover_color"]
        if color != mover_color(ply):
            _fail(f"{path}.mover_color", f"must be {mover_color(ply)!r} for ply {ply}")

        analyzed = entry["analyzed"]
        if not isinstance(analyzed, bool):
            _fail(f"{path}.analyzed", "must be a boolean")

        cp_loss = entry["cp_loss"]
        if analyzed:
            if not isinstance(cp_loss, (int, float)) or cp_loss < 0:
                _fail(f"{path}.cp_loss", "must be a number >= 0 when analyzed")
        elif cp_loss is not None:
            _fail(f"{path}.cp_loss", "must be null when not analyzed")

        for mover_key, white_key in (
            ("eval_before_mover_cp", "eval_before_white_cp"),
            ("eval_after_mover_cp", "eval_after_white_cp"),
        ):
            mover_value = entry[mover_key]
            white_value = entry[white_key]
            if mover_value is None or white_value is None:
                if mover_value is not None or white_value is not None:
                    _fail(f"{path}.{white_key}", "must be null when the move is unmeasured")
                if analyzed:
                    _fail(f"{path}.{mover_key}", "must be a number when analyzed")
                continue
            if not isinstance(mover_value, (int, float)) or not isinstance(
                white_value, (int, float)
            ):
                _fail(f"{path}.{white_key}", "must be a number")
            expected = mover_value if color == "white" else -mover_value
            if abs(white_value - expected) > _EPS:
                _fail(
                    f"{path}.{white_key}",
                    f"breaks White-POV invariant: expected {expected}, got {white_value}",
                )

        for prob_key in ("win_prob_white_before", "win_prob_white_after"):
            prob = entry[prob_key]
            if prob is not None and not (0.0 <= prob <= 1.0):
                _fail(f"{path}.{prob_key}", "must be within [0, 1]")

    missing_plies = data.get("missing_plies")
    if not isinstance(missing_plies, list):
        _fail("$.missing_plies", "must be an array")
    if missing_plies != sorted(missing_plies) or len(set(missing_plies)) != len(missing_plies):
        _fail("$.missing_plies", "must be sorted and unique")
    present = {entry["ply"] for entry in plies}
    for ply in missing_plies:
        if ply in present:
            _fail("$.missing_plies", f"ply {ply} is both present and missing")
        if not isinstance(ply, int) or ply < 1:
            _fail("$.missing_plies", "must contain positive integers")

    unanalyzed = data.get("unanalyzed_plies")
    if not isinstance(unanalyzed, list):
        _fail("$.unanalyzed_plies", "must be an array")
    measured_failures = sorted(e["ply"] for e in plies if not e["analyzed"])
    if unanalyzed != measured_failures:
        _fail("$.unanalyzed_plies", "must list exactly the unmeasured plies")

    source = data.get("source")
    if not isinstance(source, dict) or set(source) != {"white", "black"}:
        _fail("$.source", "must contain exactly the white and black entries")
    for color in ("white", "black"):
        entry = source[color]
        path = f"$.source.{color}"
        if not isinstance(entry, dict):
            _fail(path, "must be an object")
        if set(entry) != {"available", "mode", "acpl", "moves_measured"}:
            _fail(path, "must have exactly available/mode/acpl/moves_measured")
        if not entry["available"]:
            if entry["moves_measured"] != 0 or entry["acpl"] is not None:
                _fail(path, "an unavailable perspective must not publish measurements")

    if data.get("status") == STATUS_COMPLETE:
        if missing_plies:
            _fail("$.status", "cannot be 'complete' with missing plies")
        if unanalyzed:
            _fail("$.status", "cannot be 'complete' with unmeasured plies")
        if plies_total is None:
            _fail("$.status", "cannot be 'complete' without plies_total")
        if len(plies) != plies_total:
            _fail("$.status", "cannot be 'complete' when merged plies != plies_total")
        if data.get("coverage", {}).get("missing_colours"):
            _fail("$.status", "cannot be 'complete' with a missing colour")
        if not all(source[c]["available"] for c in ("white", "black")):
            _fail("$.status", "cannot be 'complete' with an unavailable perspective")


def merge_cached(analyses: Iterable[GameAnalysis]) -> dict:
    """Convenience wrapper: build + validate, so callers cannot skip the gate."""
    payload = build_full_game(*analyses)
    validate_game_full(payload)
    return payload
