"""Stockfish UCI engine wrapper using python-chess."""

import os
import chess
import chess.engine
from typing import Optional

_engine: Optional[chess.engine.SimpleEngine] = None
ENGINE_TIMEOUT = 30.0


def _find_stockfish() -> str:
    project_stockfish = os.path.join(
        os.path.dirname(__file__), "..", "..", "stockfish", "stockfish.exe"
    )
    paths = [
        os.environ.get("STOCKFISH_PATH", ""),
        project_stockfish,
        "stockfish",
        "stockfish.exe",
        r"C:\Program Files\Stockfish\stockfish.exe",
        r"C:\Users\PC\AppData\Local\Programs\Stockfish\stockfish.exe",
    ]
    for p in paths:
        if p and os.path.isfile(p):
            return p
    return "stockfish"


def get_engine() -> chess.engine.SimpleEngine:
    global _engine
    if _engine is None:
        sf_path = _find_stockfish()
        _engine = chess.engine.SimpleEngine.popen_uci(sf_path)
        _engine.configure({"Threads": 2, "Hash": 128})
    return _engine


def analyze_position(fen: str, depth: int = 18, multipv: int = 3) -> list[dict]:
    engine = get_engine()
    board = chess.Board(fen)
    result = []
    import concurrent.futures

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

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        try:
            fut = pool.submit(_run)
            result = fut.result(timeout=ENGINE_TIMEOUT)
        except concurrent.futures.TimeoutError:
            result = [{"error": f"Stockfish timeout after {ENGINE_TIMEOUT}s", "depth": depth}]
    return result


def evaluate_move(fen: str, move_uci: str, depth: int = 16) -> dict:
    engine = get_engine()
    board = chess.Board(fen)
    import concurrent.futures

    def _run():
        move = chess.Move.from_uci(move_uci)
        eval_before = engine.analyse(board, chess.engine.Limit(depth=depth))[
            "score"
        ].relative.score()
        board.push(move)
        eval_after = engine.analyse(board, chess.engine.Limit(depth=depth))[
            "score"
        ].relative.score()
        best_move_info = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=1)
        best_move = best_move_info["pv"][0] if "pv" in best_move_info else None
        # eval_before is from player's perspective (side-to-move before push)
        # eval_after is from opponent's perspective (side-to-move after push)
        # Converting eval_after to player's perspective: -eval_after
        if eval_before is not None and eval_after is not None:
            cp_loss = eval_before + eval_after
        else:
            cp_loss = 0
        return {
            "eval_before": eval_before,
            "eval_after": -eval_after if eval_after is not None else 0,
            "centipawn_loss": cp_loss,
            "best_move_uci": best_move.uci() if best_move else None,
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        try:
            fut = pool.submit(_run)
            return fut.result(timeout=ENGINE_TIMEOUT)
        except concurrent.futures.TimeoutError:
            return {
                "eval_before": 0,
                "eval_after": 0,
                "centipawn_loss": 0,
                "best_move_uci": None,
                "error": f"Stockfish timeout after {ENGINE_TIMEOUT}s",
            }


def get_best_move(fen: str, depth: int = 18) -> dict:
    engine = get_engine()
    board = chess.Board(fen)
    import concurrent.futures

    def _run():
        info = engine.analyse(board, chess.engine.Limit(depth=depth))
        score = info["score"].relative
        best_move = info["pv"][0] if "pv" in info else None
        return {
            "best_move_uci": best_move.uci() if best_move else None,
            "score_cp": score.score() if score.score() is not None else None,
            "mate": score.mate() if score.mate() is not None else None,
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        try:
            fut = pool.submit(_run)
            return fut.result(timeout=ENGINE_TIMEOUT)
        except concurrent.futures.TimeoutError:
            return {
                "best_move_uci": None,
                "score_cp": None,
                "mate": None,
                "error": f"Stockfish timeout after {ENGINE_TIMEOUT}s",
            }


def close_engine():
    global _engine
    if _engine is not None:
        _engine.quit()
        _engine = None
