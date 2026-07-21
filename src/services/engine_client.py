"""Stockfish UCI engine wrapper using python-chess."""

import os
import atexit
import threading
import chess
import chess.engine
from typing import Optional

_engine: Optional[chess.engine.SimpleEngine] = None
_engine_init_lock = threading.Lock()
_analysis_lock = threading.Lock()
_ENGINE_LOCK_TIMEOUT = 120.0  # seconds — recovery from zombie lock


@atexit.register
def _cleanup_engine():
    close_engine()


def _find_stockfish() -> str:
    project_stockfish = os.path.join(
        os.path.dirname(__file__), "..", "..", "stockfish", "stockfish.exe"
    )
    search_dirs = os.environ.get("STOCKFISH_SEARCH_DIRS", "")
    extra = search_dirs.split(";") if search_dirs else []
    paths = (
        [
            os.environ.get("STOCKFISH_PATH", ""),
            project_stockfish,
        ]
        + extra
        + [
            "stockfish",
            "stockfish.exe",
        ]
    )
    for p in paths:
        if p and os.path.isfile(p):
            return p
    return "stockfish"


def get_engine() -> chess.engine.SimpleEngine:
    global _engine
    if _engine is None:
        with _engine_init_lock:
            if _engine is None:
                sf_path = _find_stockfish()
                _engine = chess.engine.SimpleEngine.popen_uci(sf_path)
                _engine.configure({"Threads": 2, "Hash": 128})
    return _engine


def _acquire_analysis_lock() -> bool:
    """Acquire analysis lock with zombie recovery.

    Returns True if lock acquired, False if zombie recovery was needed.
    In both cases the caller holds the lock on return.
    """
    global _engine
    locked = _analysis_lock.acquire(timeout=_ENGINE_LOCK_TIMEOUT)
    if not locked:
        # Zombie detection: lock held >120s → restart engine
        if _engine is not None:
            _engine.quit()
            _engine = None
        get_engine()  # fresh engine
        _analysis_lock.acquire()  # clean lock (no prior holder)
        return False  # recovered from zombie
    return True


def analyze_position(fen: str, depth: int = 18, multipv: int = 3) -> list[dict]:
    engine = get_engine()
    board = chess.Board(fen)
    _acquire_analysis_lock()
    try:
        items = []
        with engine.analysis(board) as analysis:
            for line in analysis:
                if "pv" not in line or "score" not in line:
                    continue
                score = line["score"].relative
                moves_san = [board.san(m) for m in line["pv"][:5]]
                items.append(
                    {
                        "depth": line.get("depth", 0),
                        "score_cp": score.score() if score.score() is not None else None,
                        "mate": score.mate() if score.mate() is not None else None,
                        "pv": line["pv"][:5],
                        "pv_san": moves_san,
                    }
                )
                if len(items) >= multipv:
                    break
        return items
    finally:
        _analysis_lock.release()


def evaluate_move(fen: str, move_uci: str, depth: int = 16) -> dict:
    engine = get_engine()
    board = chess.Board(fen)
    move = chess.Move.from_uci(move_uci)

    _acquire_analysis_lock()
    try:
        info_before = engine.analyse(board, chess.engine.Limit(depth=depth))
        eval_before = info_before["score"].relative.score()
        best_move = info_before["pv"][0] if "pv" in info_before else None

        if best_move:
            board_best = board.copy()
            board_best.push(best_move)
            best_res = engine.analyse(board_best, chess.engine.Limit(depth=depth))
            best_score = best_res["score"].relative.score()
            best_player = -best_score if best_score is not None else None
        else:
            best_player = eval_before

        board.push(move)
        actual_res = engine.analyse(board, chess.engine.Limit(depth=depth))
        actual_score = actual_res["score"].relative.score()
        actual_player = -actual_score if actual_score is not None else None
    finally:
        _analysis_lock.release()

    if best_player is not None and actual_player is not None:
        cp_loss = max(0, best_player - actual_player)
    else:
        cp_loss = 0

    return {
        "eval_before": eval_before,
        "eval_after": actual_player if actual_player is not None else 0,
        "centipawn_loss": cp_loss,
        "best_move_uci": best_move.uci() if best_move else None,
    }


def get_best_move(fen: str, depth: int = 18) -> dict:
    engine = get_engine()
    board = chess.Board(fen)
    _acquire_analysis_lock()
    try:
        info = engine.analyse(board, chess.engine.Limit(depth=depth))
        score = info["score"].relative
        best_move = info["pv"][0] if "pv" in info else None
        return {
            "best_move_uci": best_move.uci() if best_move else None,
            "score_cp": score.score() if score.score() is not None else None,
            "mate": score.mate() if score.mate() is not None else None,
        }
    finally:
        _analysis_lock.release()


def close_engine():
    global _engine
    if _engine is not None:
        _engine.quit()
        _engine = None
