"""Semantic contract tests: each detector's code matches its PatternDef.

1 positive + 1 negative case per detector.
"""

import sys

sys.path.insert(0, "src")

from chess import Board as ChessBoard
from lichess_analyzer_mcp.models.game import GameSummary, MoveAnalysis, GameAnalysis
from lichess_analyzer_mcp.models.pattern import PatternLibrary
from lichess_analyzer_mcp.services.pattern_detector import PatternDetector


def _make_analysis(
    game_id: str,
    color: str,
    result: str,
    moves: list[MoveAnalysis],
    opponent_name: str = "opp",
) -> GameAnalysis:
    gs = GameSummary(
        id=game_id,
        platform="lichess",
        opening="",
        opening_eco="",
        color=color,
        result=result,
        opponent_name=opponent_name,
        opponent_rating=1500,
        player_rating=1500,
        time_control="300+0",
        date="2026-07-26",
        url=f"https://lichess.org/{game_id}",
    )
    ga = GameAnalysis(game=gs)
    for m in moves:
        ga.moves.append(m)
        if m.classification == "blunder":
            ga.blunders.append(m)
        elif m.classification == "mistake":
            ga.mistakes.append(m)
        elif m.classification == "inaccuracy":
            ga.inaccuracies.append(m)
    if moves:
        ga.total_acpl = sum(m.centipawn_loss for m in moves) / len(moves)
    ga.auto_annotate()
    return ga


def _move(
    ply: int,
    san: str,
    uci: str,
    cp_loss: float,
    classification: str,
    phase: str = "middlegame",
    eval_before: float = 0,
    eval_after: float = 0,
    fen: str = "",
    was_in_check: bool = False,
) -> MoveAnalysis:
    return MoveAnalysis(
        ply=ply,
        move_uci=uci,
        move_san=san,
        eval_before=eval_before,
        eval_after=eval_after,
        win_prob_before=0.5,
        win_prob_after=0.5,
        centipawn_loss=cp_loss,
        classification=classification,
        best_move_uci="",
        best_move_san="",
        is_tactical_motif=False,
        motif_type=None,
        phase=phase,
        fen=fen,
        was_in_check=was_in_check,
    )


def _make_three(good_id, bad_id, base_moves, color="white"):
    return [
        _make_analysis(good_id, color, "0-1", list(base_moves)),
        _make_analysis(bad_id, color, "1-0", [_move(1, "e4", "e2e4", 0, "best")]),
        _make_analysis(f"{good_id}_bis", color, "0-1", list(base_moves)),
    ]


class TestPatternSemanticContract:
    def _detect(self, pid: str, analyses, metadata=None):
        detector = PatternDetector()
        for match in detector.detect_all(analyses, metadata or {}):
            if match.pattern_id == pid:
                return match
        return None

    def test_b_automatic_grab_positive(self):
        base = [
            _move(1, "e4", "e2e4", 0, "best"),
            _move(3, "Nf3", "g1f3", 0, "best"),
            _move(5, "Nxe5", "f3e5", 350, "blunder"),
            _move(7, "Bxc6", "f1c6", 250, "mistake"),
            _move(9, "Qd1", "d1d1", 0, "best"),
        ]
        match = self._detect("B", _make_three("g_b1", "g_b1n", base))
        assert match is not None, "B should detect capture blunders"
        assert match.frequency >= 2

    def test_b_automatic_grab_negative(self):
        analyses = [
            _make_analysis(
                "g1",
                "white",
                "1-0",
                [
                    _move(1, "e4", "e2e4", 0, "best"),
                    _move(3, "Nxe5", "f3e5", 0, "best"),
                ],
            ),
        ]
        assert self._detect("B", analyses) is None

    def test_c_tunneling_positive(self):
        base = [
            _move(1, "e4", "e2e4", 0, "best"),
            _move(3, "Nf3", "g1f3", 120, "mistake"),
            _move(5, "Be2", "f1e2", 150, "mistake"),
            _move(7, "O-O", "e1g1", 50, "inaccuracy"),
            _move(9, "Qd1", "d1d1", 200, "blunder"),
        ]
        match = self._detect("C", _make_three("g_c1", "g_c1n", base))
        assert match is not None, "C should detect consecutive errors >= 2"

    def test_c_tunneling_negative(self):
        analyses = [
            _make_analysis(
                "g1",
                "white",
                "1-0",
                [
                    _move(1, "e4", "e2e4", 0, "best"),
                    _move(3, "Nf3", "g1f3", 0, "best"),
                ],
            ),
        ]
        assert self._detect("C", analyses) is None

    def test_o_repetition_refusal_positive(self):
        board = ChessBoard()
        for _ in range(6):
            board.push_uci("g1f3")
            board.push_uci("g8f6")
            board.push_uci("f3g1")
            board.push_uci("f6g8")
        fen = board.fen()
        base = [
            _move(1, "Nf3", "g1f3", 0, "best", fen=ChessBoard().fen()),
            _move(
                3,
                "Ng1",
                "f3g1",
                0,
                "best",
                fen="rnbqkb1r/pppppppp/5n2/8/8/5N2/PPPPPPPP/RNBQKB1R w KQkq - 2 2",
            ),
            _move(5, "Nf3", "g1f3", 0, "best", fen=ChessBoard().fen()),
            _move(
                7,
                "Ng1",
                "f3g1",
                0,
                "best",
                fen="rnbqkb1r/pppppppp/5n2/8/8/5N2/PPPPPPPP/RNBQKB1R w KQkq - 2 2",
            ),
            _move(9, "Nxe5", "f3e5", 400, "blunder", fen=fen),
        ]
        match = self._detect("O", _make_three("g_o1", "g_o1n", base))
        assert match is not None, "O should detect repetition refusal followed by blunder"

    def test_o_repetition_refusal_negative(self):
        analyses = [
            _make_analysis(
                "g1",
                "white",
                "1-0",
                [
                    _move(1, "e4", "e2e4", 0, "best"),
                    _move(3, "Nf3", "g1f3", 0, "best"),
                ],
            ),
        ]
        assert self._detect("O", analyses) is None

    def test_p_visual_misrecognition_positive(self):
        base = [
            _move(1, "e4", "e2e4", 0, "best"),
            _move(3, "Nf3", "g1f3", 0, "best"),
            _move(
                5,
                "Rxe5",
                "f1e5",
                250,
                "blunder",
                eval_before=200,
                eval_after=-50,
                was_in_check=True,
            ),
        ]
        match = self._detect("P", _make_three("g_p1", "g_p1n", base))
        assert match is not None, "P should detect expensive capture with advantage"

    def test_p_visual_misrecognition_negative(self):
        analyses = [
            _make_analysis(
                "g1",
                "white",
                "0-1",
                [
                    _move(1, "e4", "e2e4", 0, "best"),
                    _move(3, "a3", "a2a3", 100, "mistake", eval_before=-100),
                ],
            ),
        ]
        assert self._detect("P", analyses) is None

    def test_q_active_defense_positive(self):
        base = [
            _move(1, "e4", "e2e4", 0, "best"),
            _move(3, "Qh5", "d1h5", 200, "blunder", eval_before=-200, eval_after=-350),
            _move(5, "Qxf7+", "h5f7", 50, "inaccuracy", eval_before=-300, eval_after=-200),
        ]
        analyses = [
            _make_analysis("g_q1", "white", "1-0", list(base)),
            _make_analysis("g_q1b", "white", "1-0", list(base)),
            _make_analysis("g_q1n", "white", "0-1", [_move(1, "e4", "e2e4", 0, "best")]),
        ]
        match = self._detect("Q", analyses)
        assert match is not None, "Q should detect deficit + active response + win"

    def test_q_active_defense_negative(self):
        analyses = [
            _make_analysis(
                "g1",
                "white",
                "0-1",
                [
                    _move(1, "e4", "e2e4", 0, "best"),
                    _move(3, "Qh5", "d1h5", 200, "blunder", eval_before=-200),
                    _move(5, "Qd1", "h5d1", 0, "best", eval_before=-300),
                ],
            ),
        ]
        assert self._detect("Q", analyses) is None

    def test_q2_resilience_positive(self):
        base = [
            _move(1, "e4", "e2e4", 0, "best"),
            _move(3, "Qh5", "d1h5", 400, "blunder"),
            _move(5, "Qd1", "h5d1", 0, "best"),
            _move(7, "Be2", "f1e2", 0, "best"),
        ]
        analyses = [
            _make_analysis("g_q2", "white", "1-0", list(base)),
            _make_analysis("g_q2b", "white", "1-0", list(base)),
            _make_analysis("g_q2n", "white", "0-1", [_move(1, "e4", "e2e4", 0, "best")]),
        ]
        match = self._detect("Q2", analyses)
        assert match is not None, "Q2 should detect win despite blunder"

    def test_q2_resilience_negative(self):
        analyses = [
            _make_analysis(
                "g1",
                "white",
                "0-1",
                [
                    _move(1, "e4", "e2e4", 0, "best"),
                    _move(3, "Qh5", "d1h5", 400, "blunder"),
                    _move(5, "Qxf7+", "h5f7", 0, "best"),
                ],
            ),
        ]
        assert self._detect("Q2", analyses) is None

    def test_s_capture_aversion_positive(self):
        fen_check = "4k3/8/8/8/8/8/4q3/4K3 w - - 0 1"
        base = [
            _move(
                1,
                "Kd2",
                "e1d2",
                600,
                "blunder",
                fen=fen_check,
                was_in_check=True,
                eval_before=500,
                eval_after=-100,
            ),
        ]
        analyses = [
            _make_analysis("g_s1", "white", "0-1", list(base)),
            _make_analysis("g_s1b", "white", "0-1", list(base)),
            _make_analysis("g_s1n", "white", "1-0", [_move(1, "e4", "e2e4", 0, "best")]),
        ]
        match = self._detect("S", analyses)
        assert match is not None, "S should detect king could capture checker but moved away"

    def test_s_capture_aversion_negative(self):
        analyses = [
            _make_analysis(
                "g1",
                "white",
                "1-0",
                [
                    _move(
                        1,
                        "e4",
                        "e2e4",
                        0,
                        "best",
                        fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                        was_in_check=False,
                    ),
                ],
            ),
        ]
        assert self._detect("S", analyses) is None

    def test_n_xray_pin_positive(self):
        fen_pin = "r3k3/8/8/4r3/8/8/4R3/4K3 w - - 0 1"
        base = [
            _move(1, "Re3", "e2e3", 300, "blunder", fen=fen_pin, eval_before=100, eval_after=-200),
        ]
        analyses = [
            _make_analysis("g_n1", "white", "0-1", list(base)),
            _make_analysis("g_n1b", "white", "0-1", list(base)),
            _make_analysis("g_n1n", "white", "1-0", [_move(1, "e4", "e2e4", 0, "best")]),
        ]
        match = self._detect("N", analyses)
        assert match is not None, "N should detect pinned piece blunder"

    def test_n_xray_pin_negative(self):
        fen_no_pin = "r3k3/8/8/8/8/8/4R3/4K3 w - - 0 1"
        analyses = [
            _make_analysis(
                "g1",
                "white",
                "1-0",
                [
                    _move(1, "Re3", "e2e3", 0, "best", fen=fen_no_pin),
                ],
            ),
        ]
        assert self._detect("N", analyses) is None

    def test_all_patterns_have_detectors(self):
        lib = PatternLibrary().load_baseline()
        detector = PatternDetector()
        for pid in lib.patterns:
            method = getattr(detector, f"_detect_{pid.lower()}", None)
            assert method is not None, f"Pattern {pid} has no _detect_{pid.lower()} method"

    def test_all_detectors_check_min_games(self):
        lib = PatternLibrary().load_baseline()
        detector = PatternDetector()
        single = [
            _make_analysis(
                "g1",
                "white",
                "1-0",
                [
                    _move(1, "e4", "e2e4", 0, "best"),
                ],
            )
        ]
        matches = detector.detect_all(single, {})
        matched_ids = {m.pattern_id for m in matches}
        for pid in lib.patterns:
            pdef = lib.patterns[pid]
            if pdef.min_games > 1:
                assert pid not in matched_ids, (
                    f"{pid} should not match with < {pdef.min_games} games"
                )
