"""P0-7 coverage: every flagged move is matched by a pattern or explains itself.

No engine, no network. The tests pin the deterministic reason taxonomy
(`docs/CANDIDATE_PATTERNS_2026-11-12.md` families F1-F8/Z are candidates, not
implemented patterns: a reason is a measured shape of the move, never a
mechanism claim).
"""

import pytest

from lichess_analyzer_mcp.models.game import GameAnalysis, GameSummary, MoveAnalysis
from lichess_analyzer_mcp.services.pattern_detector import (
    PATTERN_STATUS_MATCHED,
    PATTERN_STATUS_UNCLASSIFIED,
    UNCLASSIFIED_CAPTURE,
    UNCLASSIFIED_EVIDENCE_GAP,
    UNCLASSIFIED_FORCING_MOVE,
    UNCLASSIFIED_QUIET_POSITIONAL,
    detect_single_game,
    scan_single_game,
    unclassified_reason,
    unclassified_reason_for,
    unclassified_reason_from_flag,
)

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
KNOWN_PATTERNS = {"B", "J", "R", "S", "C", "T"}


def _move(
    ply: int,
    san: str,
    cp_loss: float,
    *,
    classification: str = "blunder",
    fen: str = START_FEN,
    best: str = "Qf4+",
    rank: int = 4,
    in_check: bool = False,
    gives_check: bool = False,
    motif: str | None = None,
    tactical: bool = False,
    phase: str = "middlegame",
    eval_before: float = 0.0,
    engine_lines: list | None = None,
) -> MoveAnalysis:
    return MoveAnalysis(
        ply=ply,
        move_uci="e2e4",
        move_san=san,
        eval_before=eval_before,
        eval_after=eval_before - cp_loss,
        win_prob_before=0.5,
        win_prob_after=0.4,
        centipawn_loss=cp_loss,
        classification=classification,
        best_move_uci="",
        best_move_san=best,
        is_tactical_motif=tactical,
        motif_type=motif,
        phase=phase,
        fen=fen,
        was_in_check=in_check,
        gives_check=gives_check,
        engine_lines=engine_lines or [],
        played_rank=rank,
    )


def _analysis(moves: list[MoveAnalysis]) -> GameAnalysis:
    return GameAnalysis(
        game=GameSummary(
            id="coverage1",
            platform="lichess",
            opening="Test",
            opening_eco="C00",
            color="white",
            result="1-0",
        ),
        moves=moves,
    )


# ── reason taxonomy ─────────────────────────────────────────────────────────


def test_reason_shape_wins_over_missing_pv():
    """Absence of a PV is not a per-move reason (measured: 88 % of cache)."""
    assert (
        unclassified_reason_for(
            san="Ne3", in_check=False, gives_check=False, has_engine_evidence=False
        )
        == UNCLASSIFIED_QUIET_POSITIONAL
    )


def test_reason_evidence_gap_only_without_move_text():
    assert (
        unclassified_reason_for(
            san="", in_check=False, gives_check=False, has_engine_evidence=False
        )
        == UNCLASSIFIED_EVIDENCE_GAP
    )
    assert (
        unclassified_reason_for(san="", in_check=False, gives_check=False, has_engine_evidence=True)
        == "mechanism_not_identified"
    )


def test_reason_quiet_positional():
    assert (
        unclassified_reason_for(
            san="Ne3", in_check=False, gives_check=False, has_engine_evidence=True
        )
        == UNCLASSIFIED_QUIET_POSITIONAL
    )


def test_reason_forcing_move_when_check_given():
    assert (
        unclassified_reason_for(
            san="Qe5+", in_check=False, gives_check=True, has_engine_evidence=True
        )
        == UNCLASSIFIED_FORCING_MOVE
    )


def test_reason_forcing_move_when_out_of_check():
    assert (
        unclassified_reason_for(
            san="Bd2", in_check=True, gives_check=False, has_engine_evidence=True
        )
        == UNCLASSIFIED_FORCING_MOVE
    )


def test_reason_capture_without_pattern():
    assert (
        unclassified_reason_for(
            san="Nxd5", in_check=False, gives_check=False, has_engine_evidence=True
        )
        == UNCLASSIFIED_CAPTURE
    )


def test_reason_from_flagged_payload_accepts_both_key_styles():
    flagged = {"san": "Ne3", "in_check_before": False, "check": False, "best_move_san": "Qf4+"}
    raw = {"move_san": "Ne3", "was_in_check": False, "gives_check": False, "best_move_san": "Qf4+"}
    assert unclassified_reason_from_flag(flagged) == UNCLASSIFIED_QUIET_POSITIONAL
    assert unclassified_reason_from_flag(raw) == UNCLASSIFIED_QUIET_POSITIONAL


def test_reason_from_move_object():
    move = _move(25, "Bf4", 543.0, best="Qf4+")
    assert unclassified_reason(move) == UNCLASSIFIED_QUIET_POSITIONAL
    blind = _move(27, "", 400.0, best="", rank=0)
    assert unclassified_reason(blind) == UNCLASSIFIED_EVIDENCE_GAP


# ── coverage of a whole game ────────────────────────────────────────────────


def test_coverage_accounts_for_every_flagged_move():
    analysis = _analysis(
        [
            _move(1, "e4", 0.0, classification="best", rank=1),
            _move(3, "Nf3", 0.0, classification="good", rank=1),
            _move(25, "Bf4", 543.0),  # quiet, no pattern -> unclassified
            _move(26, "h6", 0.0, classification="good", rank=1),
            _move(27, "Qxa3", 500.0),  # capture -> B
            _move(28, "a6", 0.0, classification="good", rank=1),
            _move(29, "g3", 300.0, tactical=True, motif="fork"),  # motif -> T
            _move(30, "b6", 0.0, classification="good", rank=1),
            _move(31, "", 400.0, best="", rank=0),  # evidence gap
        ]
    )
    patterns, coverage = scan_single_game(analysis)

    assert set(coverage) == {25, 27, 29, 31}  # only flagged plies
    assert all(
        cov["pattern_status"] in (PATTERN_STATUS_MATCHED, PATTERN_STATUS_UNCLASSIFIED)
        for cov in coverage.values()
    )
    matched = [
        ply for ply, cov in coverage.items() if cov["pattern_status"] == PATTERN_STATUS_MATCHED
    ]
    unclassified = [
        ply for ply, cov in coverage.items() if cov["pattern_status"] == PATTERN_STATUS_UNCLASSIFIED
    ]
    assert matched == [27, 29]
    assert unclassified == [25, 31]
    assert coverage[25]["unclassified_reason"] == UNCLASSIFIED_QUIET_POSITIONAL
    assert coverage[31]["unclassified_reason"] == UNCLASSIFIED_EVIDENCE_GAP
    assert coverage[25]["pattern_ids"] == []
    assert coverage[27]["pattern_ids"] == ["B"]
    assert coverage[29]["pattern_ids"] == ["T"]
    # The aggregated list and the coverage map cannot disagree.
    for pattern in patterns:
        for evidence in pattern["evidence"]:
            assert coverage[evidence["ply"]]["pattern_status"] == PATTERN_STATUS_MATCHED


def test_detect_single_game_is_a_thin_wrapper_over_scan():
    analysis = _analysis([_move(25, "Bf4", 543.0), _move(27, "Qxa3", 500.0)])
    assert detect_single_game(analysis) == scan_single_game(analysis)[0]


def test_unclassified_moves_never_invent_a_new_pattern():
    analysis = _analysis(
        [
            _move(25, "Bf4", 543.0),
            _move(26, "h6", 0.0, classification="good", rank=1),
            _move(31, "", 400.0, best="", rank=0),
        ]
    )
    patterns, coverage = scan_single_game(analysis)
    assert patterns == []
    assert {cov["pattern_status"] for cov in coverage.values()} == {PATTERN_STATUS_UNCLASSIFIED}
    assert all(pid in KNOWN_PATTERNS for pattern in patterns for pid in [pattern["pattern_id"]])


def test_inaccuracy_below_all_thresholds_is_still_explained():
    analysis = _analysis([_move(40, "h3", 60.0, classification="inaccuracy")])
    _, coverage = scan_single_game(analysis)
    assert coverage[40]["pattern_status"] == PATTERN_STATUS_UNCLASSIFIED
    assert coverage[40]["unclassified_reason"] == UNCLASSIFIED_QUIET_POSITIONAL


@pytest.mark.parametrize("classification", ["blunder", "mistake", "inaccuracy"])
def test_every_flagged_class_gets_a_status(classification):
    analysis = _analysis([_move(12, "c6", 120.0, classification=classification)])
    _, coverage = scan_single_game(analysis)
    assert coverage[12]["pattern_status"] in (PATTERN_STATUS_MATCHED, PATTERN_STATUS_UNCLASSIFIED)
