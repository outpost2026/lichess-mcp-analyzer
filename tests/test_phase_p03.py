"""P0-3: phase vs segment — phase_method, chess_phase, oba režimy R.

Akceptance (docs/REFACTOR_PLAN_2026-11-11.md §P0-3):
- payload vždy nese `phase_method` (MoveAnalysis.to_dict, i po from_dict),
- R detektor testován pro oba režimy (`ply_segment` i `material`),
- material-based detector: pozice se 14 figurami (vysoký materiál) NENÍ
  endgame, skutečné koncovky ANO (§2.2).

Výchozí režim `ply_segment` musí být chováním identický starému
`move.phase == "endgame"` — proto se bump DETECTOR_VERSION nekoná (§288:
bump jen při změně klasifikace/patternu; defaultní režim je bitově stejný).
"""

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import chess

from lichess_analyzer_mcp.models.game import (
    PHASE_METHOD_DEFAULT,
    PHASE_METHOD_MATERIAL,
    GameAnalysis,
    GameSummary,
    MoveAnalysis,
    effective_phase,
)
from lichess_analyzer_mcp.services import board_facts
from lichess_analyzer_mcp.services.game_analyzer import _detect_segment, _unanalyzed_move
from lichess_analyzer_mcp.services.pattern_detector import PatternDetector, per_move_patterns

FEN_ENDGAME_ROOK = "8/8/4k3/8/8/4K3/4R3/8 w - - 0 1"  # K+R vs K, material 2
FEN_ENDGAME_QUEEN = "8/8/4k3/8/8/4K3/4Q3/8 w - - 0 1"  # K+Q vs K, material 4
FEN_EMPTY = "8/8/8/8/8/8/8/8 w - - 0 1"


def _move(
    *,
    phase: str = "middlegame",
    chess_phase: str = "",
    phase_method: str = PHASE_METHOD_DEFAULT,
    cp: float = 400.0,
    eval_before: float = 500.0,
    fen: str = FEN_EMPTY,
) -> MoveAnalysis:
    return MoveAnalysis(
        ply=40,
        move_uci="a1a2",
        move_san="Ra2",
        eval_before=eval_before,
        eval_after=eval_before - cp,
        win_prob_before=0.9,
        win_prob_after=0.6,
        centipawn_loss=cp,
        classification="blunder",
        best_move_uci="b1b2",
        best_move_san="Rb2",
        is_tactical_motif=False,
        motif_type=None,
        phase=phase,
        fen=fen,
        chess_phase=chess_phase,
        phase_method=phase_method,
    )


def _r_ids(move: MoveAnalysis) -> list[str]:
    return [c["pattern_id"] for c in per_move_patterns(move, None, False)]


def _analysis(move: MoveAnalysis) -> GameAnalysis:
    return GameAnalysis(
        game=GameSummary(
            id="g1",
            platform="lichess",
            opening="",
            opening_eco="",
            color="white",
            result="0-1",
        ),
        moves=[move],
    )


class TestChessPhaseMaterial:
    """board_facts.chess_phase: 14 figur není endgame, koncovky ano (§2.2)."""

    def test_start_position_is_opening(self):
        assert board_facts.material_phase_value(chess.STARTING_FEN) == 24
        assert board_facts.chess_phase(chess.STARTING_FEN) == "opening"

    def test_fourteen_pieces_high_material_not_endgame(self):
        # Start bez pěšců a se dvěma jezdci = 14 figur, materiál 22.
        board = chess.Board(chess.STARTING_FEN)
        pawns = [
            sq
            for sq in chess.SQUARES
            if board.piece_at(sq) is not None and board.piece_at(sq).piece_type == chess.PAWN
        ]
        for sq in pawns:
            board.remove_piece_at(sq)
        board.remove_piece_at(chess.parse_square("b8"))
        board.remove_piece_at(chess.parse_square("g8"))
        fen = board.fen()
        assert len(board.piece_map()) == 14
        assert board_facts.material_phase_value(fen) == 22
        assert board_facts.chess_phase(fen) == "opening"
        assert board_facts.chess_phase(fen) != "endgame"

    def test_real_endgames(self):
        assert board_facts.material_phase_value(FEN_ENDGAME_ROOK) == 2
        assert board_facts.chess_phase(FEN_ENDGAME_ROOK) == "endgame"
        assert board_facts.material_phase_value(FEN_ENDGAME_QUEEN) == 4
        assert board_facts.chess_phase(FEN_ENDGAME_QUEEN) == "endgame"

    def test_threshold_boundaries(self):
        # 20 (ztráta jedné dámy) -> opening; 19 -> middlegame.
        board = chess.Board(chess.STARTING_FEN)
        board.remove_piece_at(chess.parse_square("d8"))
        assert board_facts.material_phase_value(board.fen()) == 20
        assert board_facts.chess_phase(board.fen()) == "opening"
        board.remove_piece_at(chess.parse_square("b8"))
        assert board_facts.material_phase_value(board.fen()) == 19
        assert board_facts.chess_phase(board.fen()) == "middlegame"

        # 9 -> middlegame; 8 -> endgame.
        board = chess.Board(chess.STARTING_FEN)
        for square in ("d8", "d1", "a8", "a1", "b8", "b1", "c8"):
            board.remove_piece_at(chess.parse_square(square))
        assert board_facts.material_phase_value(board.fen()) == 9
        assert board_facts.chess_phase(board.fen()) == "middlegame"
        board.remove_piece_at(chess.parse_square("c1"))
        assert board_facts.material_phase_value(board.fen()) == 8
        assert board_facts.chess_phase(board.fen()) == "endgame"

    def test_totality_invalid_fen(self):
        assert board_facts.chess_phase("") == ""
        assert board_facts.chess_phase("not-a-fen") == ""
        assert board_facts.material_phase_value("") is None
        assert board_facts.material_phase_value("not-a-fen") is None

    def test_material_value_capped_at_24(self):
        # Sedm dam = 28, cap 24 (promoce se nepočítají přes limit).
        board = chess.Board(FEN_EMPTY)
        for square in ("a1", "b1", "c1", "d1", "e1", "f1", "g1"):
            board.set_piece_at(chess.parse_square(square), chess.Piece(chess.QUEEN, chess.WHITE))
        assert board_facts.material_phase_value(board.fen()) == 24


class TestSegmentRename:
    """`_detect_segment` (dříve `_detect_phase`) je ply-segmentace, ne fáze."""

    def test_boundaries_unchanged(self):
        assert _detect_segment(1) == "opening"
        assert _detect_segment(20) == "opening"
        assert _detect_segment(21) == "middlegame"
        assert _detect_segment(50) == "middlegame"
        assert _detect_segment(51) == "endgame"


class TestPayloadContract:
    """Payload vždy nese `phase_method`; `phase` je alias na segment."""

    def test_to_dict_always_carries_phase_method(self):
        data = _move().to_dict()
        assert data["phase_method"] == PHASE_METHOD_DEFAULT == "ply_segment"
        assert data["segment"] == data["phase"]
        assert data["chess_phase"] == ""

    def test_to_dict_material_mode(self):
        data = _move(phase_method=PHASE_METHOD_MATERIAL, chess_phase="endgame").to_dict()
        assert data["phase_method"] == "material"
        assert data["chess_phase"] == "endgame"
        # alias zůstává segment (D1: phase = segment, ne chess_phase)
        assert data["segment"] == data["phase"] == "middlegame"

    def test_legacy_payload_from_dict_defaults(self):
        legacy = _move().to_dict()
        for key in ("phase_method", "chess_phase", "segment"):
            legacy.pop(key)
        move = MoveAnalysis.from_dict(legacy)
        assert move.phase_method == PHASE_METHOD_DEFAULT
        assert move.chess_phase == ""
        assert move.segment == move.phase == "middlegame"
        assert move.to_dict()["phase_method"] == "ply_segment"

    def test_round_trip_stable(self):
        original = _move(
            phase_method=PHASE_METHOD_MATERIAL, chess_phase="middlegame", phase="endgame"
        )
        assert MoveAnalysis.from_dict(original.to_dict()).to_dict() == original.to_dict()

    def test_game_payload_contains_phase_method_in_moves(self):
        analysis = GameAnalysis(
            game=GameSummary(
                id="g1", platform="lichess", opening="", opening_eco="", color="white", result="1-0"
            ),
            moves=[_move()],
        )
        payload = analysis.to_dict()
        assert payload["moves"][0]["phase_method"] == "ply_segment"


class TestEffectivePhaseBothModes:
    """effective_phase: default = segment (staré chování), material = chess_phase."""

    def test_default_mode_uses_segment(self):
        move = _move(phase="endgame", chess_phase="middlegame")
        assert move.phase_method == PHASE_METHOD_DEFAULT
        assert effective_phase(move) == "endgame"

    def test_material_mode_uses_chess_phase(self):
        move = _move(phase="middlegame", chess_phase="endgame", phase_method=PHASE_METHOD_MATERIAL)
        assert effective_phase(move) == "endgame"

    def test_material_mode_ignores_segment_endgame(self):
        move = _move(phase="endgame", chess_phase="middlegame", phase_method=PHASE_METHOD_MATERIAL)
        assert effective_phase(move) == "middlegame"

    def test_material_mode_without_chess_phase_falls_back(self):
        # Legacy data: material režim, ale chess_phase nevypočtena.
        move = _move(phase="endgame", chess_phase="", phase_method=PHASE_METHOD_MATERIAL)
        assert effective_phase(move) == "endgame"


class TestRDetectorBothModes:
    """R detektor testován pro oba režimy (akceptance §P0-3)."""

    def test_r_fires_default_mode_segment_endgame(self):
        move = _move(phase="endgame", chess_phase="middlegame")
        assert _r_ids(move) == ["R"]

    def test_r_fires_material_mode(self):
        move = _move(phase="middlegame", chess_phase="endgame", phase_method=PHASE_METHOD_MATERIAL)
        assert _r_ids(move) == ["R"]

    def test_r_not_fired_when_material_says_not_endgame(self):
        move = _move(phase="endgame", chess_phase="middlegame", phase_method=PHASE_METHOD_MATERIAL)
        assert "R" not in _r_ids(move)

    def test_r_not_fired_when_segment_says_not_endgame(self):
        move = _move(phase="middlegame", chess_phase="")
        assert "R" not in _r_ids(move)

    def test_cross_game_r_default_mode(self):
        detector = PatternDetector()
        match = detector._detect_r([_analysis(_move(phase="endgame"))], {})
        assert match is not None and match.pattern_id == "R"

    def test_cross_game_r_material_mode(self):
        detector = PatternDetector()
        material_endgame = _move(
            phase="middlegame", chess_phase="endgame", phase_method=PHASE_METHOD_MATERIAL
        )
        match = detector._detect_r([_analysis(material_endgame)], {})
        assert match is not None and match.pattern_id == "R"

    def test_cross_game_r_material_mode_not_endgame(self):
        detector = PatternDetector()
        material_opening = _move(
            phase="endgame", chess_phase="middlegame", phase_method=PHASE_METHOD_MATERIAL
        )
        assert detector._detect_r([_analysis(material_opening)], {}) is None


class TestAnalyzerConstruction:
    """game_analyzer plní chess_phase při konstrukci tahů (bez engine)."""

    def test_unanalyzed_move_carries_chess_phase(self):
        board = chess.Board(chess.STARTING_FEN)
        move = chess.Move.from_uci("e2e4")
        result = _unanalyzed_move(1, board, move, board.fen())
        assert result.phase == "opening"
        assert result.chess_phase == "opening"
        assert result.phase_method == PHASE_METHOD_DEFAULT
        assert effective_phase(result) == "opening"
