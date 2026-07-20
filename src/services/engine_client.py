"""Stockfish UCI engine wrapper using python-chess."""

import os
import atexit
import threading
import chess
import chess.engine
from typing import Optional

_engine: Optional[chess.engine.SimpleEngine] = None
_engine_lock = threading.Lock()
ENGINE_TIMEOUT = 30.0


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
        with _engine_lock:
            if _engine is None:
                sf_path = _find_stockfish()
                _engine = chess.engine.SimpleEngine.popen_uci(sf_path)
                _engine.configure({"Threads": 2, "Hash": 128})
    return _engine


def _run_with_timeout(fn, timeout: float = ENGINE_TIMEOUT):
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        try:
            fut = pool.submit(fn)
            return fut.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            return None


def analyze_position(fen: str, depth: int = 18, multipv: int = 3) -> list[dict]:
    engine = get_engine()
    board = chess.Board(fen)

    def _run():
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

    result = _run_with_timeout(_run)
    if result is None:
        return [{"error": f"Stockfish timeout after {ENGINE_TIMEOUT}s", "depth": depth}]
    return result


def evaluate_move(fen: str, move_uci: str, depth: int = 16) -> dict:
    engine = get_engine()
    board = chess.Board(fen)

    def _run():
        move = chess.Move.from_uci(move_uci)
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

    result = _run_with_timeout(_run)
    if result is None:
        return {
            "eval_before": 0,
            "eval_after": 0,
            "centipawn_loss": 0,
            "best_move_uci": None,
            "error": f"Stockfish timeout after {ENGINE_TIMEOUT}s",
        }
    return result


def get_best_move(fen: str, depth: int = 18) -> dict:
    engine = get_engine()
    board = chess.Board(fen)

    def _run():
        info = engine.analyse(board, chess.engine.Limit(depth=depth))
        score = info["score"].relative
        best_move = info["pv"][0] if "pv" in info else None
        return {
            "best_move_uci": best_move.uci() if best_move else None,
            "score_cp": score.score() if score.score() is not None else None,
            "mate": score.mate() if score.mate() is not None else None,
        }

    result = _run_with_timeout(_run)
    if result is None:
        return {
            "best_move_uci": None,
            "score_cp": None,
            "mate": None,
            "error": f"Stockfish timeout after {ENGINE_TIMEOUT}s",
        }
    return result


def close_engine():
    global _engine
    if _engine is not None:
        _engine.quit()
        _engine = None
