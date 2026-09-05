"""Cloud eval fallback client (chess-api.com).

Used for depth >= 18 evaluation when local Stockfish is too slow.
Disabled by default — enable with CHESS_API_CLOUD=1 env var.
Rate limit: 1 request per 100ms per API docs.
"""

import os
from typing import Optional

CLOUD_ENABLED = os.environ.get("CHESS_API_CLOUD", "0") == "1"
CLOUD_API_URL = "https://chess-api.com/v1"
CLOUD_MAX_DEPTH = 18
CLOUD_MIN_DEPTH = 14
CLOUD_TIMEOUT = 10.0


def cloud_evaluate_move(fen: str, move_uci: str, depth: int = 14) -> Optional[dict]:
    if not CLOUD_ENABLED:
        return None
    if depth < CLOUD_MIN_DEPTH:
        return None
    effective_depth = min(depth, CLOUD_MAX_DEPTH)
    try:
        import httpx

        payload = {
            "fen": fen,
            "move": move_uci,
            "depth": effective_depth,
        }
        resp = httpx.post(CLOUD_API_URL, json=payload, timeout=CLOUD_TIMEOUT)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if "centipawn_loss" in data:
            return {
                "eval_before": data.get("eval_before", 0),
                "eval_after": data.get("eval_after", 0),
                "centipawn_loss": data["centipawn_loss"],
                "best_move_uci": data.get("best_move", ""),
                "source": "chess-api.com",
            }
        if "score" in data or "cp" in data:
            cp_before = data.get("cp_before") or data.get("cp", 0)
            cp_after = data.get("cp_after", 0)
            best = data.get("bestmove") or data.get("best", "")
            loss = data.get("centipawn_loss") or data.get("cp_loss", 0)
            return {
                "eval_before": cp_before,
                "eval_after": cp_after,
                "centipawn_loss": loss,
                "best_move_uci": best,
                "source": "chess-api.com",
            }
        return None
    except Exception:
        return None
