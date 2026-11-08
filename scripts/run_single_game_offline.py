"""Offline single_game coaching report — CLI variant of lichess_coaching_single_game.

Runs the CURRENT code in a fresh process, bypassing any stale MCP server
session. This is the recommended way to verify a change before restarting
the server.

Usage:
    python -X utf8 scripts/run_single_game_offline.py <game_id> [--color white] [--depth 14] [--mode fast]
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("LICHESS_TOKEN", "")

# Load .env from the project root (same logic as server.py)
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
    parser.add_argument("--username", type=str, default="systeq")
    parser.add_argument("--color", type=str, default="", choices=["", "white", "black"])
    parser.add_argument("--depth", type=int, default=14)
    parser.add_argument("--mode", type=str, default="fast", choices=["fast", "deep"])
    args = parser.parse_args()

    from lichess_analyzer_mcp.tools.coaching_single_game import lichess_coaching_single_game

    t0 = time.time()
    result = asyncio.run(
        lichess_coaching_single_game(
            args.game_id,
            username=args.username,
            color=args.color,
            depth=args.depth,
            mode=args.mode,
        )
    )
    duration = time.time() - t0

    print("\n=== SINGLE GAME COACHING ===")
    print(f"dur: {duration:.1f}s")
    print(
        f"game_id: {result.get('game_id')} | color: {result.get('color')} | "
        f"depth: {result.get('depth')} | mode: {result.get('mode')}"
    )
    print(f"status: {result.get('status')} | partial: {result.get('partial')}")
    print(f"schema: {result.get('schema_version')}")

    timings = result.get("timings") or {}
    if timings:
        print(
            "timings: "
            f"io={timings.get('io_s')}s engine={timings.get('engine_s')}s "
            f"llm={timings.get('llm_s')}s total={timings.get('total_s')}s "
            f"deadline={timings.get('deadline_s')}s "
            f"calls={timings.get('engine_calls')} timeouts={timings.get('engine_timeouts')}"
        )

    analysis = result.get("analysis") or {}
    print(
        f"ACPL: {analysis.get('acpl')} | accuracy: {analysis.get('accuracy')} | "
        f"moves {analysis.get('moves_analyzed')}/{analysis.get('moves_total')} | "
        f"eval_errors: {analysis.get('evaluation_errors')}"
    )
    print(f"unanalyzed_plies: {result.get('unanalyzed_plies')}")
    print(f"cache: {result.get('cache')}")

    llm = result.get("llm") or {}
    print(
        f"llm: status={llm.get('status')} provider={llm.get('provider')} "
        f"degraded={llm.get('degraded')}"
    )
    meta = result.get("report_meta") or {}
    print(f"report: source={meta.get('source')} chars={meta.get('chars')}")

    patterns = result.get("patterns") or []
    print(f"patterns: {len(patterns)}")
    for p in patterns:
        print(
            f"  {p.get('pattern_id')} {p.get('pattern_name')} "
            f"conf={p.get('confidence')} freq={p.get('frequency')} scope={p.get('scope')}"
        )

    flagged = result.get("flagged_moves") or []
    print(f"flagged_moves: {len(flagged)}")
    for m in flagged[:10]:
        print(
            f"  ply {m.get('ply')} {m.get('san')} {m.get('classification')} "
            f"cp_loss={m.get('cp_loss')} best={m.get('best_move_san')} "
            f"rank={m.get('played_rank')} explanation_source={m.get('explanation_source')}"
        )

    report = result.get("report", "") or ""
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
