"""Offline single_game coaching report — CLI varianta lichess_coaching_single_game.

Obejde MCP transport timeout a pouzije aktualni default LLM_MAX_TOKENS
(z kodu, ne ze stareho beziho serveru).

Usage:
    python -X utf8 scripts/run_single_game_offline.py <game_id> [--color white] [--depth 14] [--out DIR]
"""

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("LICHESS_TOKEN", "")

# Nacti .env z projektoveho rootu (stejna logika jako server.py)
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.isfile(_env_path):
    with open(_env_path, encoding="utf-8-sig") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                _k = _k.strip()
                if _k and _k not in os.environ:
                    os.environ[_k] = _v.strip()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("game_id", type=str)
    parser.add_argument("--color", type=str, default="white", choices=["white", "black"])
    parser.add_argument("--depth", type=int, default=14)
    args = parser.parse_args()

    from lichess_analyzer_mcp.tools.coaching_single_game import lichess_coaching_single_game
    import asyncio

    t0 = time.time()
    result = asyncio.run(lichess_coaching_single_game(args.game_id, args.color, args.depth))
    print(f"\n=== SINGLE GAME COACHING ===")
    print(f"dur: {time.time() - t0:.1f}s")
    print(
        f"game_id: {result.get('game_id')} | color: {result.get('color')} | depth: {result.get('depth')}"
    )
    print(f"patterns: {len(result.get('patterns') or [])}")
    cl = result.get("cascade_log") or []
    prov = next((e for e in reversed(cl) if not e.get("error")), None)
    if prov:
        print(
            f"provider: {prov.get('provider')} | completion_tokens: {prov.get('completion_tokens')} | "
            f"total_tokens: {prov.get('total_tokens')}"
        )

    report = result.get("report", "")
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    out = os.path.join(DATA_DIR, "reports", f"single_game_{args.game_id}_{ts}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"report: {out}")
    print(f"len(report): {len(report)}")
    print("\n=== REPORT ===")
    print(report)


if __name__ == "__main__":
    main()
