"""D25 / D24: the single-game payload must be readable without the cache.

Three gaps this pins:

1. `flagged_moves[]` had no position, so the LLM could not narrate a move.
   `fen_before` is already measured in the cache - publishing it costs no
   engine call.
2. The response had no `game` block, so a flag could not be attributed to a
   player. Anonymous placeholders must never reach the payload.
3. `scripts/coach_single.py` must never write an "empty" JSON: an error is a
   stderr message plus a non-zero exit, not a valid-looking file.
"""

import importlib.util
import os

ROOT = os.path.join(os.path.dirname(__file__), "..")
START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, relative))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


coach_single = _load("coach_single_cli", os.path.join("scripts", "coach_single.py"))

from lichess_analyzer_mcp.tools.coaching_single_game import (  # noqa: E402
    _accuracy_warning,
    _flagged_moves,
    _game_block,
    _llm_skip,
)


def _raw_move(**overrides) -> dict:
    move = {
        "ply": 71,
        "move_san": "Qe3",
        "move_uci": "d2e3",
        "classification": "blunder",
        "centipawn_loss": 9465.0,
        "eval_before": -548,
        "eval_after": -9999,
        "best_eval": -534,
        "win_prob_before": 0.1,
        "win_prob_after": 0.0,
        "phase": "endgame",
        "fen": START_FEN,
        "engine_lines": [],
        "motif_type": None,
        "gives_check": False,
        "was_in_check": False,
        "explanation": "",
        "explanation_source": "none",
        "played_rank": 4,
        "best_move_san": "Qxf7+",
    }
    move.update(overrides)
    return move


# --- 1. FEN ---------------------------------------------------------------


def test_flagged_move_carries_the_position_it_was_played_from():
    flag = _flagged_moves({"moves": [_raw_move()]})[0]
    assert flag["fen_before"] == START_FEN


def test_missing_fen_is_an_empty_string_not_a_guess():
    flag = _flagged_moves({"moves": [_raw_move(fen="")]})[0]
    assert flag["fen_before"] == ""


def test_fen_is_published_for_every_flagged_class():
    moves = [
        _raw_move(ply=13, classification="mistake", centipawn_loss=152.0),
        _raw_move(ply=23, classification="inaccuracy", centipawn_loss=87.0),
        _raw_move(ply=71, classification="blunder", centipawn_loss=9465.0),
    ]
    flags = _flagged_moves({"moves": moves})
    assert len(flags) == 3
    assert all(flag["fen_before"] == START_FEN for flag in flags)


# --- 2. game block --------------------------------------------------------


def test_named_game_publishes_both_names_and_ratings():
    block = _game_block(
        {
            "id": "iAIWvqPo",
            "player_name": "Heinzlinus",
            "opponent_name": "Systeq",
            "player_rating": 1942,
            "opponent_rating": 1898,
            "time_control": "600+0",
            "date": "2026.11.14",
            "url": "https://lichess.org/game/iAIWvqPo",
            "opening": "Scandinavian Defense",
            "opening_eco": "B01",
            "result": "0-1",
        },
        "iAIWvqPo",
    )
    assert block["player_name"] == "Heinzlinus"
    assert block["opponent_name"] == "Systeq"
    assert block["player_rating"] == 1942
    assert block["opponent_rating"] == 1898


def test_anonymous_placeholders_are_blanked():
    for placeholder in ("Anonymous", "anonymous", "?", "-", ""):
        block = _game_block({"player_name": placeholder, "opponent_name": placeholder}, "gid")
        assert block["player_name"] == ""
        assert block["opponent_name"] == ""


def test_unknown_rating_is_null_never_zero():
    block = _game_block({"player_rating": 0, "opponent_rating": None}, "gid")
    assert block["player_rating"] is None
    assert block["opponent_rating"] is None


def test_game_block_falls_back_to_the_requested_id():
    assert _game_block({}, "fallback")["id"] == "fallback"


# --- 3. CLI must not publish an empty payload ----------------------------


def test_perspectives_splits_a_keyed_payload():
    pairs = coach_single._perspectives({"white": {"a": 1}, "black": {"a": 2}})
    assert [label for label, _ in pairs] == ["white", "black"]


def test_perspectives_keeps_a_single_report_bare():
    assert coach_single._perspectives({"v": "2.1"}) == [("", {"v": "2.1"})]


def test_failures_are_labelled_by_perspective():
    payload = {
        "white": {"errors": [{"code": "PIPELINE_ERROR", "message": "404"}]},
        "black": {"errors": []},
    }
    assert coach_single._failures(payload) == ["white: PIPELINE_ERROR: 404"]


def test_failures_of_a_single_report_have_no_label():
    assert coach_single._failures({"errors": [{"code": "E", "message": "m"}]}) == ["E: m"]


def test_compact_of_finds_wrapped_and_bare_compact():
    wrapped = {"compact": {"v": "2.1"}, "detailed": {"schema_version": "1.2"}}
    assert coach_single._compact_of(wrapped) == {"v": "2.1"}
    bare = {"v": "2.1", "summary": {}, "flags": []}
    assert coach_single._compact_of(bare) is bare
    assert coach_single._compact_of({"schema_version": "1.2"}) is None


# --- 4. D15/T-18: game_impact ---------------------------------------------


def test_mate_against_the_mover_is_never_losing_to_losing():
    """P0-3 evidence: `Qe3` -548 -> -9999. `losing_to_losing` would hide the mate."""
    flag = _flagged_moves({"moves": [_raw_move()]})[0]
    assert flag["game_impact"] == "losing_to_mate"
    assert flag["mate_after"] == "against"


def test_mate_for_the_mover_is_reported_with_its_direction():
    flag = _flagged_moves({"moves": [_raw_move(eval_before=-548, eval_after=9998)]})[0]
    assert flag["game_impact"] == "losing_to_mate"
    assert flag["mate_after"] == "for"


def test_game_impact_marks_a_winning_position_thrown_away():
    """`S23Qm04u` white `Bxf6`: +197 -> -13. The audit called this
    "winning to losing"; with the documented +/-100 cp dead zone the position
    was given back (`winning_to_equal`), not lost outright."""
    flag = _flagged_moves({"moves": [_raw_move(eval_before=197, eval_after=-130)]})[0]
    assert flag["game_impact"] == "winning_to_losing"
    assert flag["mate_after"] is None
    equal = _flagged_moves({"moves": [_raw_move(eval_before=197, eval_after=-13)]})[0]
    assert equal["game_impact"] == "winning_to_equal"


def test_dead_zone_boundary_is_inclusive():
    """|eval| <= 100 cp is `equal`; the threshold is documented, not implicit."""
    at_boundary = _flagged_moves({"moves": [_raw_move(eval_before=100, eval_after=-100)]})[0]
    assert at_boundary["game_impact"] == "equal_to_equal"
    over_boundary = _flagged_moves({"moves": [_raw_move(eval_before=101, eval_after=-101)]})[0]
    assert over_boundary["game_impact"] == "winning_to_losing"


def test_mate_before_is_read_as_a_sign_not_as_a_state():
    """A mate already on the board is winning/losing, never a third pre-state."""
    flag = _flagged_moves({"moves": [_raw_move(eval_before=9999, eval_after=200)]})[0]
    assert flag["game_impact"] == "winning_to_winning"


def test_unmeasured_evals_publish_null_instead_of_a_guess():
    flag = _flagged_moves({"moves": [_raw_move(eval_before=None, eval_after=None)]})[0]
    assert flag["game_impact"] is None
    assert flag["mate_after"] is None


# --- 4b. D31/D32/D33: missed mate, played PV, accuracy warning ---------------

MATE_LINES = [
    {"rank": 1, "san": "e6+", "eval_cp": None, "mate_in": 10, "pv": ["e6+", "Kxe6", "fxg8=Q+"]},
    {"rank": 2, "san": "Kg2", "eval_cp": 780, "mate_in": None, "pv": ["Kg2", "Qf4"]},
    {"rank": 3, "san": "Bf5+", "eval_cp": 961, "mate_in": None, "pv": ["Bf5+", "Ke7"]},
]


def test_missed_mate_is_published_with_its_length_and_move():
    """`WHIbVLXk` white ply 67: +825 -> +961, best line e6+ mate in 10."""
    flag = _flagged_moves(
        {
            "moves": [
                _raw_move(
                    eval_before=825,
                    eval_after=961,
                    engine_lines=MATE_LINES,
                    played_rank=3,
                    best_move_san="e6+",
                )
            ]
        }
    )[0]
    assert flag["game_impact"] == "winning_to_winning"
    assert flag["mate_missed"] == 10
    assert flag["mate_via"] == "e6+"


def test_mate_already_reached_by_the_played_move_is_not_missed():
    flag = _flagged_moves(
        {
            "moves": [
                _raw_move(eval_before=300, eval_after=9998, engine_lines=MATE_LINES, played_rank=1)
            ]
        }
    )[0]
    assert flag["mate_after"] == "for"
    assert flag["mate_missed"] is None
    assert flag["mate_via"] is None


def test_played_pv_is_the_continuation_after_the_played_move():
    flag = _flagged_moves(
        {
            "moves": [
                _raw_move(
                    eval_before=825,
                    eval_after=961,
                    engine_lines=MATE_LINES,
                    played_rank=3,
                )
            ]
        }
    )[0]
    assert flag["pv_played"] == ["Ke7"]
    assert flag["pv_played_unavailable"] is None


def test_played_pv_outside_the_multipv_window_is_explicitly_unavailable():
    flag = _flagged_moves({"moves": [_raw_move(engine_lines=MATE_LINES, played_rank=4)]})[0]
    assert flag["pv_played"] == []
    assert flag["pv_played_unavailable"] == "rank_not_in_engine_lines"


def test_accuracy_warning_names_the_mate_level_outlier():
    missed = _flagged_moves(
        {
            "moves": [
                _raw_move(eval_before=825, eval_after=961, engine_lines=MATE_LINES, played_rank=3)
            ]
        }
    )
    assert _accuracy_warning(missed) == "contains_mate_level_outlier"
    ordinary = _flagged_moves(
        {"moves": [_raw_move(eval_before=200, eval_after=120, centipawn_loss=80.0)]}
    )
    assert _accuracy_warning(ordinary) is None
    # A forced mate after the move is the other mate-level shape.
    mated = _flagged_moves({"moves": [_raw_move(eval_before=-548, eval_after=-9999)]})
    assert _accuracy_warning(mated) == "contains_mate_level_outlier"


# --- 5. D28: llm_skipped --------------------------------------------------


def test_llm_disabled_is_an_explicit_skip():
    assert _llm_skip(False, [{"provider": "deterministic"}]) == (True, "llm_disabled")


def test_negative_cache_is_named_as_the_skip_reason():
    log = [
        {"provider": "NVIDIA", "skipped": True, "error": "Negative cache (recent 4xx)"},
        # The deterministic tail is not a provider attempt.
        {"provider": "Deterministic report", "fallback": True, "source": "deterministic"},
    ]
    assert _llm_skip(True, log) == (True, "negative_cache")


def test_missing_api_key_is_named_as_the_skip_reason():
    assert _llm_skip(True, [{"provider": "X", "skipped": True, "error": "No API key"}]) == (
        True,
        "no_api_key",
    )


def test_a_real_provider_attempt_is_not_a_skip():
    assert _llm_skip(True, [{"provider": "X", "error": "Payment required"}]) == (False, None)


def test_empty_cascade_log_means_no_provider_configured():
    assert _llm_skip(True, []) == (True, "no_provider_configured")
