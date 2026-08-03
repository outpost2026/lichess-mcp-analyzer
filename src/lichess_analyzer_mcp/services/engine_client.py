"""Stockfish UCI engine wrapper using python-chess."""

import os
import atexit
import logging
import threading
import chess
import chess.engine
from typing import Optional
from lichess_analyzer_mcp.config.depth import DEPTH_DEFAULTS

_engine: Optional[chess.engine.SimpleEngine] = None
_engine_init_lock = threading.Lock()
_analysis_lock = threading.Lock()
_ENGINE_LOCK_TIMEOUT = 120.0  # seconds — recovery from zombie lock
_ENGINE_CALL_TIMEOUT = 15.0  # seconds — P2: <= 25% of MCP client timeout (60s)


@atexit.register
def _cleanup_engine():
    close_engine()


def _find_stockfish() -> str:
    project_stockfish = os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "stockfish", "stockfish-bmi2.exe"
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
            "stockfish-bmi2.exe",
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
                _engine.configure({"Threads": 6, "Hash": 512, "NumaPolicy": "hardware"})
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


def _kill_engine():
    """Terminate the shared engine immediately (timeout recovery)."""
    global _engine
    if _engine is not None:
        try:
            _engine.quit()
        except Exception:  # noqa: S110 — engine already failing; quit is best-effort
            pass
        _engine = None


def _run_engine_call(fn, timeout_s: float = _ENGINE_CALL_TIMEOUT, engine=None):
    """Run a blocking engine call with a hard timeout.

    The engine call runs in a daemon thread; if it does not finish within
    timeout_s the engine is killed (otherwise the still-running call
    would corrupt subsequent analysis) and an error dict is returned.
    The `engine` reference (default: shared `_engine`) determines which
    engine gets terminated — callers with a LOCAL engine pass it so the
    shared engine is never killed as collateral.
    A worker exception is converted to an error dict as well.
    """
    global _engine
    result = {}

    def _worker():
        try:
            result["value"] = fn()
        except Exception as exc:  # noqa: BLE001
            result["error"] = str(exc)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout_s)
    if t.is_alive():
        target = engine if engine is not None else _engine
        if target is not None:
            try:
                target.quit()
            except Exception:  # noqa: S110 — engine already failing; quit is best-effort
                pass
            if engine is None:
                _engine = None
        return {"error": f"engine call timed out after {timeout_s:.0f}s"}
    if "error" in result:
        return {"error": result["error"]}
    return result["value"]


def analyze_position(fen: str, depth: int = 0, multipv: int = 3) -> list[dict]:
    if depth == 0:
        depth = DEPTH_DEFAULTS["standard"]["position"]
    engine = get_engine()
    board = chess.Board(fen)
    _acquire_analysis_lock()
    try:

        def _do_analysis():
            # Use engine.analyse() with multipv — returns results at exact target depth
            results = engine.analyse(board, chess.engine.Limit(depth=depth), multipv=multipv)
            items = []
            for info in results:
                if "pv" not in info or "score" not in info:
                    continue
                score = info["score"].relative
                moves_san = []
                tb = board.copy()
                for m in info["pv"][:5]:
                    try:
                        moves_san.append(tb.san(m))
                        tb.push(m)
                    except (AssertionError, ValueError):
                        break
                items.append(
                    {
                        "depth": info.get("depth", depth),
                        "score_cp": score.score() if score.score() is not None else None,
                        "mate": score.mate() if score.mate() is not None else None,
                        "pv": info["pv"][:5],
                        "pv_san": moves_san,
                    }
                )
            return items

        res = _run_engine_call(_do_analysis)
        if isinstance(res, dict) and "error" in res:
            return []
        return res
    finally:
        _analysis_lock.release()


_SF_PATH = None


def _get_sf_path() -> str:
    global _SF_PATH
    if _SF_PATH is None:
        _SF_PATH = _find_stockfish()
    return _SF_PATH


def evaluate_move(fen: str, move_uci: str, depth: int = 0) -> dict:
    if depth == 0:
        depth = DEPTH_DEFAULTS["standard"]["position"]

    board = chess.Board(fen)
    move = chess.Move.from_uci(move_uci)

    if move not in board.legal_moves:
        return {
            "eval_before": 0,
            "eval_after": 0,
            "centipawn_loss": 0,
            "best_move_uci": None,
            "error": f"Move {move_uci} not legal in position {fen}",
        }

    # D1: Cloud fallback for depth >= 18 (chess-api.com)
    if depth >= 14:
        from lichess_analyzer_mcp.services.cloud_client import cloud_evaluate_move

        cloud_result = cloud_evaluate_move(fen, move_uci, depth)
        if cloud_result is not None:
            return cloud_result

    engine = get_engine()
    _acquire_analysis_lock()
    try:

        def _do_evaluate():
            # D2: Use engine.analyse() for deterministic depth-specific result
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
            return eval_before, best_move, best_player, actual_player

        res = _run_engine_call(_do_evaluate, engine=engine)
        if isinstance(res, dict) and "error" in res:
            return {
                "eval_before": 0,
                "eval_after": 0,
                "centipawn_loss": 0,
                "best_move_uci": None,
                "error": res["error"],
            }
        eval_before, best_move, best_player, actual_player = res
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


def evaluate_move_with_confidence(fen: str, move_uci: str, depth: int = 0, runs: int = 3) -> dict:
    """D3: Run evaluate_move multiple times, return median cp_loss.

    Returns:
        dict with keys: eval_before, eval_after, centipawn_loss, best_move_uci,
                        centipawn_loss_median, centipawn_loss_min, centipawn_loss_max,
                        confidence_spread, anomaly
    """
    results = []
    for _ in range(runs):
        r = evaluate_move(fen, move_uci, depth)
        results.append(r)
        if "error" in r:
            return r

    cp_losses = [r["centipawn_loss"] for r in results]
    best_moves = [r.get("best_move_uci") for r in results]

    cp_losses_sorted = sorted(cp_losses)
    median_idx = len(cp_losses_sorted) // 2
    cp_loss_median = cp_losses_sorted[median_idx]
    cp_loss_min = cp_losses_sorted[0]
    cp_loss_max = cp_losses_sorted[-1]
    spread = cp_loss_max - cp_loss_min

    # Anomaly: spread > 100 cp or inconsistent best_move
    unique_moves = set(best_moves)
    anomaly = spread > 100 or len(unique_moves) > 1

    if anomaly:
        logging.warning(
            f"[D3-ANOMALY] evaluate_move anomaly: fen={fen[:50]}... move={move_uci} "
            f"cp_losses={cp_losses} best_moves={best_moves} spread={spread}"
        )

    return {
        "eval_before": results[0]["eval_before"],
        "eval_after": results[0]["eval_after"],
        "centipawn_loss": cp_loss_median,
        "centipawn_loss_median": cp_loss_median,
        "centipawn_loss_min": cp_loss_min,
        "centipawn_loss_max": cp_loss_max,
        "confidence_spread": spread,
        "best_move_uci": results[0]["best_move_uci"],
        "anomaly": anomaly,
        "all_cp_losses": cp_losses,
        "all_best_moves": best_moves,
    }


def check_blunder_sanity(
    fen: str, move_uci: str, cp_loss: int, game_result: str | None = None
) -> dict:
    """D4: Sanity check for blunder classification.

    Flags suspicious classifications:
    - Blunder (>= 300 cp) in a won position (game_result=1-0 for white, 0-1 for black)
    - Blunder classified but the move is actually the top engine choice

    Returns:
        dict with keys: valid (bool), warnings (list[str])
    """
    warnings = []
    board = chess.Board(fen)

    is_white_turn = board.turn == chess.WHITE
    is_blunder = cp_loss >= 300

    if not is_blunder:
        return {"valid": True, "warnings": []}

    # Check 1: Blunder in won position
    if game_result:
        if (is_white_turn and game_result == "1-0") or (not is_white_turn and game_result == "0-1"):
            warnings.append(
                f"BLUNDER_IN_WON_POSITION: {move_uci} classified as blunder "
                f"({cp_loss} cp) but game was won by {'white' if is_white_turn else 'black'}"
            )

    # Check 2: Blunder that is actually top engine choice (check top 3 moves)
    engine = get_engine()
    _acquire_analysis_lock()
    try:
        results = engine.analyse(board, chess.engine.Limit(depth=14), multipv=3)
        top_moves = []
        for info in results:
            if "pv" in info and info["pv"]:
                top_moves.append(info["pv"][0])
        if any(m.uci() == move_uci for m in top_moves):
            warnings.append(
                f"BLUNDER_IS_TOP_MOVE: {move_uci} classified as blunder ({cp_loss} cp) "
                f"but is in top engine choices"
            )
    finally:
        _analysis_lock.release()

    return {"valid": len(warnings) == 0, "warnings": warnings}


def get_best_move(fen: str, depth: int = 0) -> dict:
    if depth == 0:
        depth = DEPTH_DEFAULTS["standard"]["position"]
    engine = get_engine()
    board = chess.Board(fen)
    _acquire_analysis_lock()
    try:

        def _do_best():
            info = engine.analyse(board, chess.engine.Limit(depth=depth))
            score = info["score"].relative
            best_move = info["pv"][0] if "pv" in info else None
            return {
                "best_move_uci": best_move.uci() if best_move else None,
                "score_cp": score.score() if score.score() is not None else None,
                "mate": score.mate() if score.mate() is not None else None,
            }

        res = _run_engine_call(_do_best)
        if isinstance(res, dict) and "error" in res:
            return res
        return res
    finally:
        _analysis_lock.release()


def close_engine():
    global _engine
    if _engine is not None:
        _engine.quit()
        _engine = None
