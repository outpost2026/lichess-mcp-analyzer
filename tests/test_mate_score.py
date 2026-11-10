"""FIX-027: mate score mapping + explanation (no engine)."""

from lichess_analyzer_mcp.models.game import MoveAnalysis
from lichess_analyzer_mcp.services.game_analyzer import (
    _build_explanation,
    _engine_lines_to_dicts,
)

RAW_MATE = {
    "score_cp": None,
    "mate": 5,
    "pv": [],
    "pv_san": ["Qf4+", "Qf6", "Qxf6+", "Kg8", "Re8#"],
}


def _move(**overrides):
    data = {
        "ply": 75,
        "move_uci": "e8e8",
        "move_san": "Re8+",
        "eval_before": 9997.0,
        "eval_after": 525.0,
        "win_prob_before": 0.99,
        "win_prob_after": 0.53,
        "centipawn_loss": 9473.0,
        "classification": "blunder",
        "best_move_uci": "f4f6",
        "best_move_san": "Qf4+",
        "is_tactical_motif": True,
        "motif_type": "check",
        "phase": "endgame",
        "played_rank": 4,
    }
    data.update(overrides)
    return MoveAnalysis(**data)


def test_engine_lines_to_dicts_keeps_mate():
    lines = _engine_lines_to_dicts([RAW_MATE])
    assert lines[0]["mate_in"] == 5
    assert lines[0]["eval_cp"] is None
    assert lines[0]["san"] == "Qf4+"


def test_explanation_uses_mate_not_question_mark():
    lines = _engine_lines_to_dicts([RAW_MATE])
    text = _build_explanation(_move(), lines)
    assert "mat v 5" in text
    assert "?" not in text


def test_explanation_negative_mate_is_explicit():
    lines = _engine_lines_to_dicts([{**RAW_MATE, "mate": -3}])
    text = _build_explanation(_move(), lines)
    assert "mat v 3 proti hráči" in text
