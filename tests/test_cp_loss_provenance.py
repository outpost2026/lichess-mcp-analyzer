"""D12: `cp_loss` must be reconstructible from the published fields.

`cp_loss` is measured from the best move (`best_player - actual_player`), while
`eval_before` is a separate root search. Before D12 the detailed payload
published only `cp_loss`, `eval_before` and `eval_after`, so the loss could not
be recomputed and the three numbers looked contradictory - measured ply 62 of
game iAIWvqPo: eval_before=948, eval_after=161, cp_loss=697.

D12 publishes `best_eval_mover_cp` (the anchor). These tests pin the contract:
`cp_loss == max(0, best_eval_mover_cp - eval_after_mover_cp)`.
"""

from lichess_analyzer_mcp.models.game import MoveAnalysis
from lichess_analyzer_mcp.services.eval_consistency import cp_loss_reconstructs
from lichess_analyzer_mcp.tools.coaching_single_game import _flagged_moves

# ply, best_eval (anchor), eval_after, cp_loss - measured in iAIWvqPo, 2026-11-14.
MEASURED = [
    (22, -25, -100, 75.0),
    (26, 70, 17, 53.0),
    (40, 98, -13, 111.0),
    (60, 366, 305, 61.0),
    (62, 858, 161, 697.0),
    (64, 145, 0, 145.0),
]

# The `eval_before` of the same plies - a different search, never the anchor.
EVAL_BEFORE = {22: -30, 26: 81, 40: 103, 60: 327, 62: 948, 64: 126}


class TestCpLossReconstructs:
    def test_measured_triples_reconstruct(self):
        for ply, best, after, cp in MEASURED:
            assert cp_loss_reconstructs(best, after, cp), f"ply {ply}"

    def test_eval_before_is_not_the_anchor(self):
        # The old (wrong) reading: loss == eval_before - eval_after.
        for ply, _best, after, cp in MEASURED:
            naive = EVAL_BEFORE[ply] - after
            assert naive != cp, f"ply {ply} must expose the gap"

    def test_ply62_gap_is_visible(self):
        # 948 - 161 = 787, but the measured loss is 697 (90 cp apart).
        assert not cp_loss_reconstructs(948, 161, 697.0)
        assert cp_loss_reconstructs(858, 161, 697.0)

    def test_unmeasurable_inputs_are_not_reconstructible(self):
        assert not cp_loss_reconstructs(None, 161, 697.0)
        assert not cp_loss_reconstructs(858, None, 697.0)
        assert not cp_loss_reconstructs(858, 161, None)

    def test_clamped_at_zero(self):
        # A move better than the engine's best (search noise) loses nothing.
        assert cp_loss_reconstructs(100, 140, 0.0)


class TestMoveAnalysisCarriesAnchor:
    def test_roundtrip_keeps_best_eval(self):
        move = MoveAnalysis(
            ply=62,
            move_uci="a3a5",
            move_san="Ra5",
            eval_before=948.0,
            eval_after=161.0,
            best_eval=858.0,
            win_prob_before=0.99,
            win_prob_after=0.72,
            centipawn_loss=697.0,
            classification="blunder",
            best_move_uci="a3a2",
            best_move_san="Ra2",
            is_tactical_motif=False,
            motif_type=None,
            phase="endgame",
        )
        data = move.to_dict()
        assert data["best_eval"] == 858.0
        assert MoveAnalysis.from_dict(data).best_eval == 858.0

    def test_legacy_move_without_anchor_is_null(self):
        # A cache written before D12 has no `best_eval` key at all.
        legacy = {
            "ply": 1,
            "move_uci": "e2e4",
            "move_san": "e4",
            "eval_before": 30,
            "eval_after": 25,
            "win_prob_before": 0.5,
            "win_prob_after": 0.5,
            "centipawn_loss": 5.0,
            "classification": "good",
            "best_move_uci": "e2e4",
            "best_move_san": "e4",
            "is_tactical_motif": False,
            "motif_type": None,
            "phase": "opening",
        }
        assert MoveAnalysis.from_dict(legacy).best_eval is None


class TestFlaggedMovesPublishAnchor:
    def _analysis(self, **overrides):
        move = {
            "ply": 62,
            "move_san": "Ra5",
            "move_uci": "a3a5",
            "classification": "blunder",
            "centipawn_loss": 697.0,
            "eval_before": 948,
            "eval_after": 161,
            "best_eval": 858,
            "win_prob_before": 0.9957,
            "win_prob_after": 0.7164,
            "phase": "endgame",
            "best_move_san": "Ra2",
            "played_rank": 2,
            "engine_lines": [],
            "motif_type": None,
            "gives_check": False,
            "was_in_check": False,
            "explanation": "Hrano Ra5; motor preferuje Ra2.",
            "explanation_source": "deterministic",
        }
        move.update(overrides)
        return {"moves": [move]}

    def test_anchor_is_published(self):
        flag = _flagged_moves(self._analysis())[0]
        assert flag["best_eval_mover_cp"] == 858
        assert cp_loss_reconstructs(
            flag["best_eval_mover_cp"],
            flag["eval_after_mover_cp"],
            flag["cp_loss"],
        )

    def test_legacy_cache_publishes_null_not_a_guess(self):
        analysis = self._analysis()
        del analysis["moves"][0]["best_eval"]
        flag = _flagged_moves(analysis)[0]
        assert "best_eval_mover_cp" in flag
        assert flag["best_eval_mover_cp"] is None
