"""FIX-023: cp_loss vs eval_before/eval_after invariant (no engine)."""

from lichess_analyzer_mcp.services.eval_consistency import (
    CP_EVAL_TOLERANCE_CP,
    eval_delta,
    eval_invariant_holds,
)


def test_cp_loss_eval_invariant_fvhqtv1s_ply89():
    # Measured FVhqtv1S ply 89: eval rose by 44 cp while the move lost 237.
    assert not eval_invariant_holds(638, 682, 237.0)
    assert eval_delta(638, 682) == -44.0


def test_consistent_pair_holds():
    assert eval_invariant_holds(9997, 525, 9473.0)
    assert eval_invariant_holds(682, 445, 237.0)


def test_missing_values_are_not_consistent():
    assert not eval_invariant_holds(None, 682, 237.0)
    assert not eval_invariant_holds(638, None, 237.0)
    assert not eval_invariant_holds(638, 682, None)


def test_small_loss_always_holds():
    # Below the tolerance the eval pair is not worth suppressing.
    assert eval_invariant_holds(10, 600, CP_EVAL_TOLERANCE_CP)
    assert eval_delta("x", 1) is None
