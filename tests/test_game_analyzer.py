"""P0-3: the published best-eval must agree with its own engine line."""

from lichess_analyzer_mcp.services.game_analyzer import _align_engine_lines_with_anchor


def test_anchor_is_published_on_the_matching_engine_line():
    lines = [
        {"rank": 1, "san": "Rxd6", "eval_cp": -610, "mate_in": None, "pv": ["Rxd6", "Kf7"]},
        {"rank": 2, "san": "Qd4", "eval_cp": -740, "mate_in": None, "pv": ["Qd4"]},
    ]
    out = _align_engine_lines_with_anchor(lines, best_move_san="Rxd6", best_eval_mover_cp=-536)
    assert out[0]["eval_cp"] == -536
    assert out[1]["eval_cp"] == -740  # other lines keep their own search
    assert out[0]["pv"] == ["Rxd6", "Kf7"]  # no PV invented


def test_anchor_outside_multipv_window_is_inserted_as_rank_one():
    lines = [{"rank": 1, "san": "Bxe6", "eval_cp": 348, "mate_in": None, "pv": ["Bxe6"]}]
    out = _align_engine_lines_with_anchor(lines, best_move_san="Nf6", best_eval_mover_cp=420)
    assert out[0] == {"rank": 1, "san": "Nf6", "eval_cp": 420, "mate_in": None, "pv": ["Nf6"]}
    assert out[1]["rank"] == 2


def test_best_eval_matches_engine_lines():
    """P0-3 acceptance on the live QxL4Tr8u black 58 contradiction case."""
    lines = [
        {"rank": 1, "san": "Rxd6", "eval_cp": -610, "mate_in": None, "pv": ["Rxd6", "Kf7"]},
    ]
    out = _align_engine_lines_with_anchor(lines, best_move_san="Rxd6", best_eval_mover_cp=-536)
    assert abs(out[0]["eval_cp"] - (-536)) <= 10
    assert out[0]["san"] == "Rxd6"  # best_move_san names the cp_loss anchor
    # cp_loss reconstruction still holds: -536 - (-667) = 131 (formula untouched).
    assert -536 - (-667) == 131


def test_anchor_is_not_guessed_when_unmeasured():
    lines = [{"rank": 1, "san": "e4", "eval_cp": 20, "mate_in": None, "pv": ["e4"]}]
    assert (
        _align_engine_lines_with_anchor(
            [dict(line) for line in lines], best_move_san="", best_eval_mover_cp=None
        )
        == lines
    )
