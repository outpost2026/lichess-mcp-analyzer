"""P0-4 / D37: three named confidence dimensions (no engine, no network).

`confidence` alone invited reading an ordinal detector weight as a
probability. The payload now names the dimension and states that mechanism
calibration does not exist yet, instead of inventing a number for it.
"""

import json
import os

from lichess_analyzer_mcp.models.game import GameAnalysis, GameSummary, MoveAnalysis
from lichess_analyzer_mcp.services.confidence_dims import (
    BEHAVIORAL_REASON_NOT_CALIBRATED,
    CONFIDENCE_KIND_DETECTION,
    SUPPORT_BASIS_SINGLE_GAME,
    detailed_dims,
    dimensions_block,
    support_share,
)
from lichess_analyzer_mcp.services.compact_serializer import (
    to_compact_v2,
    validate_compact,
)
from lichess_analyzer_mcp.services.pattern_detector import scan_single_game

ROOT = os.path.join(os.path.dirname(__file__), "..")
START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def _move(ply, san, cp_loss, **kwargs):
    return MoveAnalysis(
        ply=ply,
        move_uci="e2e4",
        move_san=san,
        eval_before=0.0,
        eval_after=-cp_loss,
        win_prob_before=0.5,
        win_prob_after=0.4,
        centipawn_loss=cp_loss,
        classification=kwargs.get("classification", "blunder"),
        best_move_uci="",
        best_move_san="Qf4+",
        is_tactical_motif=kwargs.get("tactical", False),
        motif_type=kwargs.get("motif"),
        phase="middlegame",
        fen=START_FEN,
        played_rank=kwargs.get("rank", 4),
    )


def _analysis():
    return GameAnalysis(
        game=GameSummary(
            id="dims1",
            platform="lichess",
            opening="Test",
            opening_eco="C00",
            color="white",
            result="1-0",
        ),
        moves=[
            _move(25, "Qxa3", 500.0),
            _move(26, "h6", 0.0, classification="good", rank=1),
            _move(27, "g3", 300.0, tactical=True, motif="fork"),
        ],
    )


# --- pure arithmetic and vocabulary -----------------------------------------


def test_support_share_uses_the_measured_denominator():
    assert support_share(2, 5) == 0.4
    assert support_share(3, 3) == 1.0
    assert support_share(4, 3) == 1.0  # never publish > 1


def test_support_share_without_a_denominator_is_null():
    assert support_share(1, 0) is None
    assert support_share(1, None) is None
    assert support_share(None, 3) is None


def test_dims_never_invent_behavioral_calibration():
    dims = detailed_dims(0.42, 1, 4)
    assert dims["detection_strength"] == 0.42
    assert dims["evidence_support"] == 0.25
    assert dims["evidence_support_basis"] == SUPPORT_BASIS_SINGLE_GAME
    assert dims["evidence_support_n_units"] == 4
    assert dims["behavioral_confidence"] is None
    assert dims["behavioral_confidence_reason"] == BEHAVIORAL_REASON_NOT_CALIBRATED
    assert dims["confidence_kind"] == CONFIDENCE_KIND_DETECTION


def test_dimensions_block_counts_patterns_without_repeating_prose():
    block = dimensions_block(2)
    assert block["n_patterns"] == 2
    assert block["published_kind"] == CONFIDENCE_KIND_DETECTION
    assert set(block["kinds"]) == {
        "detection_strength",
        "evidence_support",
        "behavioral_confidence",
    }


# --- detector surface --------------------------------------------------------


def test_single_game_patterns_carry_all_three_dimensions():
    patterns, coverage = scan_single_game(_analysis())
    assert patterns
    assert len(coverage) == 2  # the `good` move is not a measured flagged move
    for pattern in patterns:
        assert pattern["detection_strength"] == pattern["strength"]
        assert pattern["confidence_kind"] == CONFIDENCE_KIND_DETECTION
        assert pattern["evidence_support"] == round(pattern["frequency"] / 2, 3)
        assert pattern["evidence_support_n_units"] == 2
        assert pattern["behavioral_confidence"] is None
        assert pattern["behavioral_confidence_reason"] == BEHAVIORAL_REASON_NOT_CALIBRATED


# --- compact 2.3 contract ----------------------------------------------------


def _compact():
    analysis = _analysis()
    patterns, coverage = scan_single_game(analysis)
    full = {
        "depth": 14,
        "analysis": {},
        "flagged_moves": [],
        "patterns": patterns,
        "patterns_meta": {
            "scope": "single_game",
            "cross_game_suppressed": True,
            "reason": "Single-game scope: cross-game detectors are suppressed.",
            "coverage": {
                "flagged": len(coverage),
                "matched": len(coverage),
                "unclassified": 0,
            },
        },
        "game": {"id": "dims1"},
    }
    meta = {
        "id": "dims1",
        "color": "white",
        "result": "1-0",
        "opening": "Test Opening",
        "depth": 14,
    }
    compact = to_compact_v2(full, game_meta=meta)
    validate_compact(compact)
    return compact


def test_compact_publishes_support_and_the_payload_level_explanation():
    compact = _compact()
    assert compact["v"] == "2.7"
    assert compact["confidence_dims"]["published_kind"] == "detection_strength"
    for pattern in compact["patterns"]:
        assert "support" in pattern
        assert pattern["support"] is not None


def test_compact_validator_rejects_a_wrong_pattern_count():
    compact = _compact()
    compact["confidence_dims"]["n_patterns"] += 1
    try:
        validate_compact(compact)
    except ValueError as exc:
        assert "n_patterns" in str(exc)
    else:
        raise AssertionError("validator accepted an inconsistent n_patterns")


def test_schema_file_is_a_valid_draft_2020_12_schema():
    jsonschema = __import__("jsonschema")
    schema = json.load(
        open(os.path.join(ROOT, "schemas/single_game_v2_compact_2.3.json"), encoding="utf-8")
    )
    jsonschema.Draft202012Validator.check_schema(schema)
    assert schema["properties"]["v"]["const"] == "2.3"
