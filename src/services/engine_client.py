"""Stockfish UCI engine wrapper using python-chess."""

import os
import chess
import chess.engine
from typing import Optional

_engine: Optional[chess.engine.SimpleEngine] = None


def _find_stockfish() -> str:
    paths = [
        os.environ.get("STOCKFISH_PATH", ""),
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
    with engine.analysis(board) as analysis:
        for line in analysis:
            if "pv" not in line or "score" not in line:
                continue
            score = line["score"].relative
            moves_san = [board.san(m) for m in line["pv"][:5]]
            result.append(
                {
                    "depth": line.get("depth", 0),
                    "score_cp": score.score() if score.score() is not None else None,
                    "mate": score.mate() if score.mate() is not None else None,
                    "pv": line["pv"][:5],
                    "pv_san": moves_san,
                }
            )
            if len(result) >= multipv:
                break
    return result


def evaluate_move(fen: str, move_uci: str, depth: int = 16) -> dict:
    engine = get_engine()
    board = chess.Board(fen)
    move = chess.Move.from_uci(move_uci)
    eval_before = engine.analyse(board, chess.engine.Limit(depth=depth))["score"].relative.score()
    board.push(move)
    eval_after = engine.analyse(board, chess.engine.Limit(depth=depth))["score"].relative.score()
    best_move_info = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=1)
    best_move = best_move_info["pv"][0] if "pv" in best_move_info else None
    cp_loss = (
        (eval_before - eval_after) if eval_before is not None and eval_after is not None else 0
    )
    return {
        "eval_before": eval_before,
        "eval_after": eval_after,
        "centipawn_loss": cp_loss,
        "best_move_uci": best_move.uci() if best_move else None,
    }


def get_best_move(fen: str, depth: int = 18) -> dict:
    engine = get_engine()
    board = chess.Board(fen)
    info = engine.analyse(board, chess.engine.Limit(depth=depth))
    score = info["score"].relative
    best_move = info["pv"][0] if "pv" in info else None
    return {
        "best_move_uci": best_move.uci() if best_move else None,
        "score_cp": score.score() if score.score() is not None else None,
        "mate": score.mate() if score.mate() is not None else None,
    }


def close_engine():
    global _engine
    if _engine is not None:
        _engine.quit()
        _engine = None
