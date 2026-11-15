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
    _flagged_moves,
    _game_block,
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
