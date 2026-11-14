"""T3.1/T3.2: `game_full` 1.0 merges two perspectives into one White-POV timeline."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lichess_analyzer_mcp.models.game import GameAnalysis, GameSummary, MoveAnalysis
from lichess_analyzer_mcp.services.timeline import (
    TimelineMismatchError,
    build_full_game,
    validate_game_full,
)

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _move(
    ply: int,
    *,
    san: str,
    eval_before: float,
    eval_after: float,
    cp: float,
    analyzed: bool = True,
) -> MoveAnalysis:
    return MoveAnalysis(
        ply=ply,
        move_uci="e2e4",
        move_san=san,
        eval_before=eval_before,
        eval_after=eval_after,
        win_prob_before=0.6 if ply % 2 == 1 else 0.4,
        win_prob_after=0.55 if ply % 2 == 1 else 0.45,
        centipawn_loss=cp,
        classification="inaccuracy" if analyzed else "unanalyzed",
        best_move_uci="d2d4",
        best_move_san="d4",
        is_tactical_motif=False,
        motif_type=None,
        phase="opening",
        fen="8/8/8/8/8/8/8/8 w - - 0 1",
        analyzed=analyzed,
        played_rank=1,
    )


def _analysis(color: str, plies: list[MoveAnalysis], total: int, game_id: str = "abcd1234"):
    summary = GameSummary(
        id=game_id,
        platform="lichess",
        opening="Test Opening",
        opening_eco="C20",
        color=color,
        result="1-0",
        player_name="Alice" if color == "white" else "Bob",
        opponent_name="Bob" if color == "white" else "Alice",
        time_control="600+0",
    )
    analysis = GameAnalysis(game=summary, game_plies_total=total, mode="fast")
    analysis.moves = plies
    analysis.total_acpl = 12.5
    return analysis


def _white():
    # Mover POV: White's evals are already White POV.
    return _analysis(
        "white",
        [
            _move(1, san="e4", eval_before=20, eval_after=10, cp=10),
            _move(3, san="Nf3", eval_before=40, eval_after=30, cp=10),
        ],
        4,
    )


def _black():
    # Mover POV: Black's evals are Black POV, so White POV is the negation.
    return _analysis(
        "black",
        [
            _move(2, san="e5", eval_before=-10, eval_after=-40, cp=30),
            _move(4, san="Nc6", eval_before=-30, eval_after=-25, cp=5),
        ],
        4,
    )


def test_merge_publishes_every_ply_once():
    payload = build_full_game(_white(), _black())
    assert [p["ply"] for p in payload["plies"]] == [1, 2, 3, 4]
    assert payload["status"] == "complete"
    assert payload["coverage"] == {
        "white_plies": 2,
        "black_plies": 2,
        "merged_plies": 4,
        "expected_plies": 4,
        "missing_colours": [],
    }
    validate_game_full(payload)


def test_black_moves_are_converted_to_white_pov():
    payload = build_full_game(_white(), _black())
    black = next(p for p in payload["plies"] if p["ply"] == 2)
    assert black["eval_before_mover_cp"] == -10
    assert black["eval_after_mover_cp"] == -40
    assert black["eval_before_white_cp"] == 10
    assert black["eval_after_white_cp"] == 40
    # A probability is flipped, not negated.
    assert black["win_prob_white_before"] == pytest.approx(0.6)
    assert black["win_prob_white_after"] == pytest.approx(0.55)


def test_cp_loss_is_a_magnitude_and_never_flipped():
    payload = build_full_game(_white(), _black())
    assert [p["cp_loss"] for p in payload["plies"]] == [10, 30, 10, 5]


def test_single_perspective_is_partial_and_names_the_gap():
    payload = build_full_game(_white())
    assert payload["status"] == "partial"
    assert payload["missing_plies"] == [2, 4]
    assert payload["coverage"]["missing_colours"] == ["black"]
    validate_game_full(payload)


def test_legacy_cache_without_total_is_partial_without_a_guess():
    white = _white()
    white.game_plies_total = 0
    payload = build_full_game(white)
    assert payload["plies_total"] is None
    assert payload["missing_plies"] == []
    assert payload["status"] == "partial"
    validate_game_full(payload)


def test_unmeasured_ply_publishes_null_not_zero():
    white = _analysis(
        "white",
        [
            _move(1, san="e4", eval_before=20, eval_after=10, cp=10),
            _move(3, san="Nf3", eval_before=0, eval_after=0, cp=0, analyzed=False),
        ],
        4,
    )
    payload = build_full_game(white, _black())
    entry = next(p for p in payload["plies"] if p["ply"] == 3)
    assert entry["analyzed"] is False
    assert entry["cp_loss"] is None
    assert entry["eval_before_white_cp"] is None
    assert entry["class"] is None
    assert payload["unanalyzed_plies"] == [3]
    assert payload["status"] == "partial"
    validate_game_full(payload)


def test_same_colour_twice_is_an_error():
    with pytest.raises(TimelineMismatchError):
        build_full_game(_white(), _white())


def test_different_games_are_an_error():
    with pytest.raises(TimelineMismatchError):
        build_full_game(_white(), _analysis("black", [], 4, game_id="zzzz9999"))


def test_ply_parity_mismatch_is_an_error():
    bad = _analysis(
        "white",
        [_move(2, san="e5", eval_before=0, eval_after=0, cp=0)],
        4,
    )
    with pytest.raises(TimelineMismatchError):
        build_full_game(bad)


def test_validation_rejects_broken_white_pov():
    payload = build_full_game(_white(), _black())
    black = next(p for p in payload["plies"] if p["ply"] == 2)
    black["eval_after_white_cp"] = -40  # forgot to negate
    with pytest.raises(ValueError) as exc:
        validate_game_full(payload)
    assert "White-POV invariant" in str(exc.value)


def test_validation_rejects_missing_mover_color():
    payload = build_full_game(_white(), _black())
    del payload["plies"][0]["mover_color"]
    with pytest.raises(ValueError) as exc:
        validate_game_full(payload)
    assert "mover_color" in str(exc.value)


def test_validation_rejects_complete_with_gap():
    payload = build_full_game(_white(), _black())
    payload["status"] = "complete"
    payload["missing_plies"] = [3]
    with pytest.raises(ValueError):
        validate_game_full(payload)


def test_output_validates_against_json_schema_file():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.load(open(os.path.join(ROOT, "schemas/game_full_v1.0.json"), encoding="utf-8"))
    jsonschema.validate(build_full_game(_white(), _black()), schema)
    jsonschema.validate(build_full_game(_white()), schema)


def test_merge_is_deterministic():
    assert build_full_game(_white(), _black()) == build_full_game(_white(), _black())
