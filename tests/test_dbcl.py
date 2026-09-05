"""Tests for DBCL v1.1 components: BlunderFactSheet, context extraction, narrative validator."""

import sys

sys.path.insert(0, "src")

import pytest

from lichess_analyzer_mcp.models.analysis import (
    BlunderFactSheet,
    BoardState,
    LegalMovesSummary,
    EngineLine,
    PatternMatchInfo,
    ContextWindowMove,
    ContextWindow,
    DETECTOR_VERSION,
)
from lichess_analyzer_mcp.services.game_analyzer import _win_prob_from_cp
from lichess_analyzer_mcp.services.narrative_validator import (
    has_unsupported_claims,
    extract_unsupported_claims,
    check_piece_on_square,
    check_check_claim,
    check_eval_claim,
    check_variation_claim,
)


class TestWinProb:
    def test_win_prob_zero(self):
        assert _win_prob_from_cp(0) == 0.5

    def test_win_prob_positive(self):
        wp = _win_prob_from_cp(400)
        assert 0.8 < wp < 1.0

    def test_win_prob_negative(self):
        wp = _win_prob_from_cp(-400)
        assert 0.0 < wp < 0.2

    def test_win_prob_none(self):
        assert _win_prob_from_cp(None) == 0.5

    def test_win_prob_large(self):
        wp = _win_prob_from_cp(1000)
        assert wp > 0.99


class TestBlunderFactSheetRoundTrip:
    def test_round_trip_empty(self):
        bfs = BlunderFactSheet()
        d = bfs.to_dict()
        restored = BlunderFactSheet.from_dict(d)
        assert restored.game_id == ""
        assert restored.board_state.was_in_check is False

    def test_round_trip_full(self):
        bfs = BlunderFactSheet(
            game_id="test123",
            ply=32,
            move_played_san="Rdg1",
            move_played_uci="d1g1",
            centipawn_loss=950,
            eval_before=823,
            eval_after=45,
            win_prob_before=0.95,
            win_prob_after=0.35,
            win_prob_delta=-0.60,
            fen_before="r4r1k/1p1b3P/p3p1R1/3p3Q/3N1q2/8/PPP4P/1K1R4 w - - 1 32",
            board_state=BoardState(
                was_in_check=False,
                checking_pieces=[],
                capture_checking_piece_possible=True,
                king_capture_possible=False,
                king_capture_played=False,
            ),
            legal_moves=LegalMovesSummary(
                total=38,
                captures=["Nxe6", "Rg8+"],
                king_moves=["Ka1", "Kb1", "Kc1"],
                blocks=[],
                checks=["Qe5+", "Rg8+"],
            ),
            engine_lines=[
                EngineLine(
                    rank=1, move_san="Nxe6", eval_cp=920, win_prob=0.97, pv=["Nxe6", "fxe6"]
                ),
                EngineLine(
                    rank=2, move_san="Rg8+", eval_cp=901, win_prob=0.96, pv=["Rg8+", "Kxg8"]
                ),
                EngineLine(
                    rank=3, move_san="Qe5+", eval_cp=887, win_prob=0.95, pv=["Qe5+", "Qxe5"]
                ),
            ],
            played_move_rank=38,
            phase="endgame",
            pattern_matches=[
                PatternMatchInfo(
                    pattern_id="R",
                    pattern_name="Endgame relaxation",
                    confidence=0.7,
                    evidence="endgame eval_before=823",
                ),
                PatternMatchInfo(
                    pattern_id="C",
                    pattern_name="Attention tunneling",
                    confidence=0.8,
                    evidence="consecutive error",
                ),
            ],
            detector_version=DETECTOR_VERSION,
            context_window=ContextWindow(
                moves_before=[
                    ContextWindowMove(ply=30, move_san="Qh5", eval_after=850, win_prob_after=0.96)
                ],
                moves_after=[
                    ContextWindowMove(ply=34, move_san="Qxe6", eval_after=0, win_prob_after=0.50)
                ],
            ),
        )
        d = bfs.to_dict()
        restored = BlunderFactSheet.from_dict(d)
        assert restored.game_id == "test123"
        assert restored.ply == 32
        assert restored.move_played_san == "Rdg1"
        assert restored.centipawn_loss == 950
        assert restored.eval_before == 823
        assert restored.win_prob_delta == pytest.approx(-0.60, abs=0.01)
        assert restored.board_state.was_in_check is False
        assert len(restored.board_state.checking_pieces) == 0
        assert restored.legal_moves.total == 38
        assert len(restored.engine_lines) == 3
        assert restored.engine_lines[0].move_san == "Nxe6"
        assert restored.played_move_rank == 38
        assert restored.phase == "endgame"
        assert len(restored.pattern_matches) == 2
        assert restored.pattern_matches[0].pattern_id == "R"
        assert len(restored.context_window.moves_before) == 1
        assert len(restored.context_window.moves_after) == 1
        assert restored.context_window.moves_before[0].ply == 30

    def test_from_dict_partial(self):
        raw = {"game_id": "abc", "ply": 15, "centipawn_loss": 200}
        bfs = BlunderFactSheet.from_dict(raw)
        assert bfs.game_id == "abc"
        assert bfs.ply == 15
        assert bfs.centipawn_loss == 200
        assert bfs.detector_version == DETECTOR_VERSION


class TestNarrativeValidator:
    def test_check_piece_on_square_found(self):
        fen = "r4r1k/1p1b3P/p3p1R1/3p3Q/3N1q2/8/PPP4P/1K1R4 w - - 1 32"
        # Q on f4 exists (black queen at f4 in FEN)
        assert check_piece_on_square("Qf4", fen) is True
        # N on d4
        assert check_piece_on_square("Nd4", fen) is True
        # R on g6
        assert check_piece_on_square("Rg6", fen) is True
        # Ke1 does not exist (K is on b1)
        assert check_piece_on_square("Ke1", fen) is False

    def test_check_check_claim_positive_pass(self):
        assert check_check_claim(True, True) is True
        assert check_check_claim(True, False) is False
        assert check_check_claim(False, False) is True

    def test_check_eval_claim(self):
        refs = [823, 45]
        assert check_eval_claim(820, refs, tol=20) is True
        assert check_eval_claim(800, refs, tol=20) is False

    def test_check_variation_claim(self):
        pvs = [["Nxe6", "fxe6", "Qf5"], ["Rg8+", "Kxg8"]]
        assert check_variation_claim(["Nxe6", "fxe6"], pvs) is True
        assert check_variation_claim(["Qh6"], pvs) is False

    def test_validate_inc_a_hallucinations(self):
        bfs = BlunderFactSheet(
            game_id="kNAMNYUF",
            ply=63,
            move_played_san="Rdg1",
            centipawn_loss=950,
            eval_before=823,
            eval_after=45,
            fen_before="r4r1k/1p1b3P/p3p1R1/3p3Q/3N1q2/8/PPP4P/1K1R4 w - - 1 32",
            board_state=BoardState(was_in_check=False),
            legal_moves=LegalMovesSummary(
                total=38,
                captures=["Nxe6", "Rg8+"],
                king_moves=["Ka1", "Kb1"],
                blocks=[],
                checks=["Qe5+", "Rg8+"],
            ),
            engine_lines=[
                EngineLine(rank=1, move_san="Nxe6", eval_cp=920, pv=["Nxe6"]),
                EngineLine(rank=2, move_san="Rg8+", eval_cp=901, pv=["Rg8+"]),
                EngineLine(rank=3, move_san="Qe5+", eval_cp=887, pv=["Qe5+"]),
            ],
        )
        # H1: False check claim should be caught by validator
        assert has_unsupported_claims("Qf4+ dává šach.", [bfs])
        # H3: False king move — Kc1 not in legal king_moves (only Ka1, Kb1)
        assert has_unsupported_claims("Měl jsi hrát Kc1.", [bfs])

    def test_valid_narrative_passes(self):
        bfs = BlunderFactSheet(
            game_id="test",
            ply=10,
            fen_before="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 2",
            board_state=BoardState(was_in_check=False),
            legal_moves=LegalMovesSummary(total=30, king_moves=["Ke8", "Ke7"]),
        )
        # Valid narrative — no check claim, no false assertions
        text = "V zahájení jsi ztratil rovnováhu. V koncovce se zlepšuješ."
        assert not has_unsupported_claims(text, [bfs])

    def test_extract_unsupported_claims(self):
        bfs = BlunderFactSheet(
            game_id="test",
            ply=10,
            board_state=BoardState(was_in_check=False),
        )
        claims = extract_unsupported_claims("Dává šach dámou.", [bfs])
        assert len(claims) >= 1
        assert not claims[0]["passed"]
