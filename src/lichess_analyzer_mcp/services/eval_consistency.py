"""FIX-023: cp_loss vs eval_before/eval_after consistency.

`cp_loss` is measured against the best move (best_player - actual_player),
while `eval_before`/`eval_after` are eval values before/after the played move.
They normally agree, but at a fixed depth two separate searches can diverge:
the eval can even rise while the move still lost cp relative to the best line.

When the divergence is large the pair is not narratable ("eval fell from 638 to
682, loss 237"), so the compact serializer omits the eval fields instead of
publishing a contradiction. The raw values stay in the detailed payload and the
analyzer logs the anomaly with the original numbers.
"""

from __future__ import annotations

CP_EVAL_TOLERANCE_CP = 50.0


def eval_invariant_holds(
    eval_before,
    eval_after,
    cp_loss,
    tolerance: float = CP_EVAL_TOLERANCE_CP,
) -> bool:
    """True when `eval_before - eval_after` is consistent with `cp_loss`."""
    if not all(isinstance(v, (int, float)) for v in (eval_before, eval_after, cp_loss)):
        return False
    cp = abs(float(cp_loss))
    if cp <= tolerance:
        return True
    delta = float(eval_before) - float(eval_after)
    return abs(delta - float(cp_loss)) <= tolerance


def cp_loss_reconstructs(
    best_eval,
    eval_after,
    cp_loss,
    tolerance: float = 1.0,
) -> bool:
    """D12: True when `cp_loss` follows from the published best/actual pair.

    `cp_loss` is measured against the best move (`best_player - actual_player`),
    not against `eval_before`; two separate searches need not agree. Publishing
    `best_eval` makes the number reconstructible, and this predicate is the
    check that the published triple really is consistent.

    Unmeasurable inputs return False - the relation cannot be verified.
    """
    if not all(isinstance(v, (int, float)) for v in (best_eval, eval_after, cp_loss)):
        return False
    expected = max(0.0, float(best_eval) - float(eval_after))
    return abs(expected - float(cp_loss)) <= tolerance


def eval_delta(eval_before, eval_after) -> float | None:
    if not all(isinstance(v, (int, float)) for v in (eval_before, eval_after)):
        return None
    return float(eval_before) - float(eval_after)
