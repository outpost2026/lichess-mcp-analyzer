"""Per-move game-impact facts shared by detailed 1.2 and compact 2.2.

`cp_loss` answers "how much was lost"; `game_impact` answers "did the game
change". Both are measured from the mover's point of view (`*_mover_cp`).

The module is pure: it never calls an engine and never guesses. A value that
was not measured stays `None`; the serializers decide whether to omit the key
or publish an explicit null.

Design notes (D15/D29/D31/D32):
  - Dead zone: |eval| <= 100 cp counts as `equal`. The threshold is published
    here, not implicit, because it decides every label.
  - `engine_client._cp_from_score` encodes mate as 10000 - |mate|, so any |cp|
    at or above `MATE_CP_THRESHOLD` is a forced mate, not a centipawn score.
  - `mate_missed` = the engine's best line mates for the mover while the played
    move does not (D31). `mate_via` names the mating SAN, so an LLM never has
    to reconstruct it from the engine lines.
  - `pv_played` = the engine continuation *after the played move*, taken from
    the same multipv search (D32). It is not the opponent's actual reply and
    must never be presented as one.
"""

from __future__ import annotations

GAME_IMPACT_DEAD_ZONE_CP = 100
# `engine_client._cp_from_score` encodes mate as 10000 - |mate|, so any |cp|
# at or above this bound is a forced mate, not a centipawn evaluation (N-05).
MATE_CP_THRESHOLD = 9000

GAME_IMPACT_STATES = ("winning", "equal", "losing")
GAME_IMPACT_POST_STATES = GAME_IMPACT_STATES + ("mate",)
# 9 sign transitions + 3 mate transitions, in a stable order for schemas.
GAME_IMPACT_VALUES = tuple(
    f"{pre}_to_{post}" for pre in GAME_IMPACT_STATES for post in GAME_IMPACT_POST_STATES
)
MATE_AFTER_VALUES = ("for", "against")

PV_PLAYED_UNAVAILABLE_REASONS = (
    "no_engine_lines",
    "rank_not_in_engine_lines",
    "no_continuation",
)


def impact_state(cp: float | None) -> str | None:
    """Coarse game state from the mover's eval: winning / equal / losing."""
    if not isinstance(cp, (int, float)):
        return None
    value = float(cp)
    if value >= MATE_CP_THRESHOLD:
        return "winning"
    if value <= -MATE_CP_THRESHOLD:
        return "losing"
    if value > GAME_IMPACT_DEAD_ZONE_CP:
        return "winning"
    if value < -GAME_IMPACT_DEAD_ZONE_CP:
        return "losing"
    return "equal"


def game_impact(before, after) -> tuple[str | None, str | None]:
    """`(game_impact, mate_after)` for one flagged move.

    Enum: 9 sign transitions (`winning_to_winning` ... `losing_to_losing`) plus
    3 mate transitions (`*_to_mate`). A forced mate after the move is never
    reported as `losing_to_losing` (P0-3): the label says `losing_to_mate` and
    `mate_after` says for whom (`for` = mover mates, `against` = mover is mated).

    `None` when either eval was not measured (legacy cache, cloud eval): the
    field never guesses.
    """
    pre = impact_state(before)
    post_cp = after if isinstance(after, (int, float)) else None
    if pre is None or post_cp is None:
        return None, None
    mate_after = None
    post: str | None
    if abs(float(post_cp)) >= MATE_CP_THRESHOLD:
        post = "mate"
        mate_after = "for" if float(post_cp) > 0 else "against"
    else:
        post = impact_state(post_cp)
    return f"{pre}_to_{post}", mate_after


def _mover_eval_after(move: dict):
    """Post-move eval from the mover's POV, whichever contract key exists."""
    for key in ("eval_after_mover_cp", "eval_after"):
        value = move.get(key)
        if isinstance(value, (int, float)):
            return value
    return None


def mate_missed(move: dict) -> tuple[int | None, str | None]:
    """`(mate_in, san)` when the best line mates and the played move does not.

    A move that itself reaches a forced mate (in either direction) is never
    reported as a missed mate: `eval_after` at mate level already says what
    happened, and `game_impact`/`mate_after` name it.
    """
    lines = [line for line in (move.get("engine_lines") or []) if isinstance(line, dict)]
    if not lines:
        return None, None
    best = min(lines, key=lambda line: line.get("rank") or 99)
    mate_in = best.get("mate_in")
    if not isinstance(mate_in, int) or isinstance(mate_in, bool) or mate_in <= 0:
        return None, None
    after = _mover_eval_after(move)
    if isinstance(after, (int, float)) and abs(float(after)) >= MATE_CP_THRESHOLD:
        return None, None
    return mate_in, best.get("san") or None


def pv_played(move: dict) -> tuple[list[str], str | None]:
    """`(continuation, unavailable_reason)` for the engine line of the played move.

    The continuation is what the engine searched after the played move in the
    same multipv call. It is a line, not a record of the game: the opponent's
    actual reply is not published anywhere.
    """
    lines = sorted(
        (line for line in (move.get("engine_lines") or []) if isinstance(line, dict)),
        key=lambda line: line.get("rank") or 99,
    )
    if not lines:
        return [], "no_engine_lines"
    rank = move.get("played_rank") or 0
    if not isinstance(rank, int) or isinstance(rank, bool) or not 1 <= rank <= len(lines):
        return [], "rank_not_in_engine_lines"
    pv = lines[rank - 1].get("pv") or []
    continuation = [san for san in pv[1:] if san]
    if not continuation:
        return [], "no_continuation"
    return continuation, None
