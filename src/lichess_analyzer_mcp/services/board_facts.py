"""Centralni zdroj sachovych predikatu (P0-1, docs/REFACTOR_PLAN_2026-11-11 §2.1).

Drive byly stejne predikaty odvozovany opakovane a casto z pritomnosti 'x'
v SAN, co nedokazuje, ze táhla figura byl král (GT-101/P101: jeden generujici
zdroj pro duplicitni implementace). Tady plati:

- kazdy predikat pocita pres ``chess.Board`` a typ figury, ne pres SAN;
- vsechny funkce jsou totalni: chybny/nekorektni FEN vrati ``False``/``[]``,
  nikdy nevyhodi vyjimku (volaji je oba detektory bez try/except);
- ziadna logika prahu ani patternu sem nepatri - to zustava v detektorech.

Konzumenti (maji zustat v sync):
- ``game_analyzer._per_blunder_patterns``  (BFS / BlunderFactSheet)
- ``pattern_detector._single_game_candidate`` (single-game, compact)
- ``pattern_detector._detect_s`` (cross-game knihovna)
- ``game_analyzer`` konstrukce ``BoardState``
"""

from __future__ import annotations

import chess


def _board(fen: str) -> chess.Board | None:
    """Parse FEN; ``None`` pri chybe (totalita - viz modulovy docstring)."""
    if not fen:
        return None
    try:
        return chess.Board(fen)
    except (ValueError, TypeError):
        return None


def _move(fen: str, move_uci: str) -> tuple[chess.Board, chess.Move] | None:
    board = _board(fen)
    if board is None or not move_uci:
        return None
    try:
        return board, chess.Move.from_uci(move_uci)
    except (ValueError, TypeError):
        return None


def king_capture_moves(fen: str) -> list[chess.Move]:
    """Vsechny legálni tahu, ktere tahnou kralem a berou (libovolnou figuru)."""
    board = _board(fen)
    if board is None:
        return []
    king_captures = []
    for mv in board.legal_moves:
        piece = board.piece_at(mv.from_square)
        if piece is not None and piece.piece_type == chess.KING and board.is_capture(mv):
            king_captures.append(mv)
    return king_captures


def king_capture_possible(fen: str) -> bool:
    """``king_capture_possible`` z board_state: existuje legální braní králem."""
    return bool(king_capture_moves(fen))


def is_king_capture(fen: str, move_uci: str) -> bool:
    """Odehrany tah je braní králem (typ figury + is_capture, ne SAN 'x')."""
    parsed = _move(fen, move_uci)
    if parsed is None:
        return False
    board, move = parsed
    piece = board.piece_at(move.from_square)
    if piece is None or piece.piece_type != chess.KING:
        return False
    return board.is_capture(move)


def king_capture_played(fen: str, move_uci: str, was_in_check: bool) -> bool:
    """``king_capture_played`` z board_state: v sachu a tah byl braní králem.

    Mimo sach je vzdy ``False`` (kontrakt board_state.z
    docs/01_DBCL_unity_synthesis.md - boolean, ne null).
    """
    if not was_in_check:
        return False
    return is_king_capture(fen, move_uci)


def is_capture(fen: str, move_uci: str) -> bool:
    """Odehrany tah je jakékoli braní (legální tah podle boardu)."""
    parsed = _move(fen, move_uci)
    if parsed is None:
        return False
    board, move = parsed
    if move not in board.legal_moves:
        return False
    return board.is_capture(move)


def capture_checking_piece_possible(fen: str) -> bool:
    """Existuje braní figury, ktera dává šach (A1 - neplést s 'jakekoli braní').

    Drive ``game_analyzer.py:881`` vracel ``True`` pri jakemkoli legálním
    braní, takze konzument mohl cist 'bylo mozne sebrat sachuji' o tah, ktery
    s sachem nesouvisel. Pri dvojsem sachu plati True, pokud lze sebrat
    alespon jednoho sachujiho.
    """
    board = _board(fen)
    if board is None or not board.is_check():
        return False
    checkers = board.checkers()
    for move in board.legal_moves:
        if board.is_capture(move) and move.to_square in checkers:
            return True
    return False


def checking_pieces(fen: str) -> list[str]:
    """Sachujici figury pro ``board_state.checking_pieces`` (P0-1 totalita).

    Volano jen pri ``was_in_check=True``; mimo sach nebo pri chybe FEN = [].
    """
    board = _board(fen)
    if board is None or not board.is_check():
        return []
    return [chess.square_name(sq) for sq in board.checkers()]


def king_can_capture_checker(fen: str) -> bool:
    """Kral muze primo sebrat sachujiho figurou (cross-game detektor S)."""
    board = _board(fen)
    if board is None or not board.is_check():
        return False
    king_square = board.king(board.turn)
    if king_square is None:
        return False
    for checker in board.checkers():
        if board.is_legal(chess.Move(king_square, checker)):
            return True
    return False


def played_piece_type(fen: str, move_uci: str) -> int | None:
    """Typ figury, ktera tah provedla (None = chybny FEN/tah)."""
    parsed = _move(fen, move_uci)
    if parsed is None:
        return None
    board, move = parsed
    piece = board.piece_at(move.from_square)
    return piece.piece_type if piece is not None else None
