"""P0-2: jediná implementace per-move patternů B/J/R/S/C/T.

Akceptance (docs/REFACTOR_PLAN_2026-11-11.md §P0-2):
- jediná implementace (`pattern_detector.per_move_patterns`),
- BFS a single-game patterny se rovnají (stejné id i confidence).

Poznámka k plánu: tabulka §P0-2 píše „Qxd4 = S false, Kxd4 = S true".
Podle §2.1 jde o pole `king_capture_played` (Qxd4 false / Kxd4 true) —
testováno v `test_board_facts.py`. Polarita patternu S je opačná:
S = „král mohl brát a nebral" → Qxd4 (cizí braní) = S true, Kxd4 = S false.
"""

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lichess_analyzer_mcp.services.game_analyzer import _per_blunder_patterns
from lichess_analyzer_mcp.services.pattern_detector import _single_game_candidate, per_move_patterns
from lichess_analyzer_mcp.models.game import MoveAnalysis

FEN_CHECK = "6k1/8/8/4Q3/8/8/4q3/4K3 w - - 0 1"
FEN_PLAIN = "4k3/8/8/8/8/8/8/4K3 w - - 0 1"


def _move(
    *,
    san: str = "e1e2",
    uci: str = "e1e2",
    cp: float = 100.0,
    phase: str = "middlegame",
    eval_before: float = 0.0,
    fen: str = FEN_PLAIN,
    in_check: bool = False,
    motif: bool = False,
    motif_type: str | None = None,
) -> MoveAnalysis:
    return MoveAnalysis(
        ply=40,
        move_uci=uci,
        move_san=san,
        eval_before=eval_before,
        eval_after=eval_before - cp,
        win_prob_before=0.75,
        win_prob_after=0.5,
        centipawn_loss=cp,
        classification="blunder",
        best_move_uci="e1e2",
        best_move_san="Kxe2",
        is_tactical_motif=motif,
        motif_type=motif_type,
        phase=phase,
        fen=fen,
        was_in_check=in_check,
    )


def _bfs(move, in_check, prev=None) -> dict[str, float]:
    return {m.pattern_id: m.confidence for m in _per_blunder_patterns(move, in_check, prev)}


def _single(move, prev=None) -> dict[str, float]:
    return {c["pattern_id"]: c["strength"] for c in _single_game_candidate(move, prev)}


def test_per_move_candidates_expose_strength_not_confidence():
    """P1: per-move event nese `strength`; `confidence` zůstává jen v 1.2 payloadu."""
    candidates = per_move_patterns(_move(san="Qxe5", uci="e5e5", cp=400.0), None, False)
    assert candidates
    for candidate in candidates:
        assert "strength" in candidate
        assert "confidence" not in candidate
        assert 0.0 <= candidate["strength"] <= 1.0


class TestBfsEqualsSingleGame:
    """Stejný tah → stejné patterny i confidence v obou cestách."""

    def _assert_equal(self, move, in_check, prev=None):
        b, s = _bfs(move, in_check, prev), _single(move, prev)
        assert b == s, f"BFS={b} single={s}"

    def test_b_pattern_capture(self):
        move = _move(san="exd5", uci="e4d5", cp=150.0)
        self._assert_equal(move, False)
        assert "B" in _bfs(move, False)

    def test_j_pattern_check_block(self):
        move = _move(san="Be6", uci="c4e6", cp=200.0, in_check=True)
        self._assert_equal(move, True)
        assert "J" in _bfs(move, True)

    def test_r_pattern_endgame(self):
        move = _move(cp=350.0, phase="endgame", eval_before=500.0)
        self._assert_equal(move, False)
        assert "R" in _bfs(move, False)

    def test_s_pattern_king_capture_not_played(self):
        move = _move(san="Qxe2", uci="e5e2", cp=600.0, fen=FEN_CHECK, in_check=True)
        self._assert_equal(move, True)
        assert "S" in _bfs(move, True)

    def test_s_pattern_absent_when_king_captured(self):
        move = _move(san="Kxe2", uci="e1e2", cp=600.0, fen=FEN_CHECK, in_check=True)
        self._assert_equal(move, True)
        assert "S" not in _bfs(move, True)

    def test_c_pattern_consecutive_error(self):
        prev = _move(san="??", uci="a2a3", cp=400.0)
        prev.classification = "blunder"
        move = _move(cp=250.0)
        self._assert_equal(move, False, prev)
        assert "C" in _bfs(move, False, prev)

    def test_t_pattern_tactical_motif(self):
        move = _move(cp=60.0, motif=True, motif_type="fork")
        self._assert_equal(move, False)
        assert "T" in _bfs(move, False)

    def test_quiet_move_no_patterns(self):
        move = _move(cp=30.0)
        self._assert_equal(move, False)
        assert _bfs(move, False) == {}

    def test_multi_pattern_move(self):
        """Tah může splnit více patternů naráz — obě cesty musí souhlasit."""
        prev = _move(cp=400.0)
        prev.classification = "mistake"
        move = _move(
            san="Qxe2",
            uci="e5e2",
            cp=650.0,
            fen=FEN_CHECK,
            in_check=True,
            phase="endgame",
            eval_before=400.0,
            motif=True,
            motif_type="capture",
        )
        self._assert_equal(move, True, prev)
        ids = set(_bfs(move, True, prev))
        assert ids >= {"B", "R", "S", "C", "T"}


class TestSingleImplementation:
    """Jediná implementace: oba volající směřují na per_move_patterns."""

    def test_single_game_candidate_delegates(self):
        move = _move(san="exd5", uci="e4d5", cp=150.0)
        core = per_move_patterns(move, None, False)
        assert _single_game_candidate(move, None) == core

    def test_bfs_is_mapping_of_core(self):
        move = _move(san="exd5", uci="e4d5", cp=150.0)
        core = per_move_patterns(move, None, False)
        assert [(m.pattern_id, m.confidence) for m in _per_blunder_patterns(move, False)] == [
            (c["pattern_id"], c["strength"]) for c in core
        ]
