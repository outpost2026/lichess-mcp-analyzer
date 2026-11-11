"""P0-1: centralni board facts - fixtures a ekvivalence BFS vs single-game.

Fixtures dle docs/REFACTOR_PLAN_2026-11-11.md §2.1 a A1:
- CHECK: bily Ke1 v sachu od Dd2 (sousedni), Kxe2 je mozne, Qxe2 take (ne kralem),
- NO_CHECK: zadny sach, Pe4 muze sebrat Dd5 (A1: mimo sach = vzdy False),
- CHECK_NO_CAPTURE: sach od Re8 bez jakekoli legarni brani (False/False).

Oprava fixture 2026-11-11: "4q4" ma 9 police (neplatny FEN) a pesec na d2
daval dvojity sach - obe chyby byly v testu, ne v board_facts.
"""

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lichess_analyzer_mcp.services import board_facts
from lichess_analyzer_mcp.services.game_analyzer import _per_blunder_patterns
from lichess_analyzer_mcp.services.pattern_detector import _single_game_candidate
from lichess_analyzer_mcp.models.analysis import LegalMovesSummary
from lichess_analyzer_mcp.models.game import MoveAnalysis

# F1: bily Ke1 v sachu od cerneho De2 (e-file, sousedni), král muze Kxe2.
FEN_CHECK = "6k1/8/8/4Q3/8/8/4q3/4K3 w - - 0 1"
# F2: zadny sach, bily Pe4 muze sebrat Dd5 (exd5).
FEN_NO_CHECK = "4k3/8/8/3q4/4P3/8/8/4K3 w - - 0 1"
# F5: Ke1 v sachu od Re8, Bc4 nema ZADNE legarni brani => False/False.
FEN_CHECK_NO_CAPTURE = "4r1k1/8/8/8/2B5/8/8/4K3 w - - 0 1"


def _move(fen: str, uci: str, san: str, cp: float, in_check: bool) -> MoveAnalysis:
    return MoveAnalysis(
        ply=40,
        move_uci=uci,
        move_san=san,
        eval_before=100.0,
        eval_after=-500.0,
        win_prob_before=0.75,
        win_prob_after=0.25,
        centipawn_loss=cp,
        classification="blunder",
        best_move_uci="e1e2",
        best_move_san="Kxe2",
        is_tactical_motif=False,
        motif_type=None,
        phase="middlegame",
        fen=fen,
        was_in_check=in_check,
    )


class TestKingCapturePlayed:
    def test_king_capture_in_check_is_true(self):
        """Kxe2 v sachu => True (typ figury, ne SAN 'x')."""
        assert board_facts.king_capture_played(FEN_CHECK, "e1e2", True) is True

    def test_non_king_capture_in_check_is_false(self):
        """Qxe2 v sachu => False (drive SAN 'x' vracel True = false negative pro S)."""
        assert board_facts.king_capture_played(FEN_CHECK, "e5e2", True) is False

    def test_capture_outside_check_is_false(self):
        """Brani mimo sach => False (kontrakt board_state: boolean, ne null)."""
        assert board_facts.king_capture_played(FEN_NO_CHECK, "e4d5", False) is False

    def test_non_capture_in_check_is_false(self):
        """V sachu, ale tah neni brani (Be6 blokuje) => False."""
        assert board_facts.king_capture_played(FEN_CHECK_NO_CAPTURE, "c4e6", True) is False


class TestCaptureCheckingPiecePossible:
    def test_true_when_checker_capturable(self):
        assert board_facts.capture_checking_piece_possible(FEN_CHECK) is True

    def test_false_when_no_legal_capture_exists(self):
        """Sach od Re8, Bc4 nema zadne brani => False."""
        assert board_facts.capture_checking_piece_possible(FEN_CHECK_NO_CAPTURE) is False

    def test_false_outside_check_even_with_capture_available(self):
        """A1 regrese: exd5 je mozne, ale sach neni => False (drive 'jakekoli brani')."""
        assert board_facts.is_capture(FEN_NO_CHECK, "e4d5") is True
        assert board_facts.capture_checking_piece_possible(FEN_NO_CHECK) is False


class TestKingCanCaptureChecker:
    def test_true_when_king_takes_checker(self):
        assert board_facts.king_can_capture_checker(FEN_CHECK) is True

    def test_false_when_checker_out_of_reach(self):
        assert board_facts.king_can_capture_checker(FEN_CHECK_NO_CAPTURE) is False


class TestTotality:
    def test_malformed_fen_never_raises(self):
        for bad in ("", "not-a-fen", "8/8/8/8/8/8/8/8 w - - 0 1x"):
            assert board_facts.king_capture_possible(bad) is False
            assert board_facts.king_capture_moves(bad) == []
            assert board_facts.capture_checking_piece_possible(bad) is False
            assert board_facts.king_can_capture_checker(bad) is False
            assert board_facts.is_king_capture(bad, "e1e2") is False
            assert board_facts.king_capture_played(bad, "e1e2", True) is False
            assert board_facts.played_piece_type(bad, "e1e2") is None


class TestBfsSingleGameAgreement:
    """P0-1 acceptance: oba detektory musi pro tenze tah dat stejny verdikt S."""

    def _ids_bfs(self, move: MoveAnalysis) -> set[str]:
        matches = _per_blunder_patterns(move, LegalMovesSummary(), True, None)
        return {m.pattern_id for m in matches}

    def _ids_single(self, move: MoveAnalysis) -> set[str]:
        return {c["pattern_id"] for c in _single_game_candidate(move, None)}

    def test_s_fires_in_both_paths_when_king_capture_not_played(self):
        """Qxe2 (brani sachujiho, ale ne kralem) => S v obou cestach."""
        move = _move(FEN_CHECK, "e5e2", "Qxe2", 600.0, True)
        assert "S" in self._ids_bfs(move)
        assert "S" in self._ids_single(move)

    def test_s_absent_in_both_paths_when_king_capture_played(self):
        move = _move(FEN_CHECK, "e1e2", "Kxe2", 600.0, True)
        assert "S" not in self._ids_bfs(move)
        assert "S" not in self._ids_single(move)

    def test_s_absent_in_both_paths_without_king_capture_option(self):
        """V sachu, ale kral nemuze vzit sachujiho (Re8 daleko) => S nikde."""
        move = _move(FEN_CHECK_NO_CAPTURE, "c4e6", "Be6", 600.0, True)
        assert "S" not in self._ids_bfs(move)
        assert "S" not in self._ids_single(move)
