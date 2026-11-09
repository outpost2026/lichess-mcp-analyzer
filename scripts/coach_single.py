"""Coach one game from the command line — the standard single-game path.

Same pipeline as the MCP tool `lichess_coaching_single_game` (contract v1.1),
but usable without an MCP client / IDE.

Examples
--------
    .venv\\Scripts\\python.exe -X utf8 scripts\\coach_single.py nxKgE4l8 --color white
    .venv\\Scripts\\python.exe -X utf8 scripts\\coach_single.py lxO3gwd3 --username systeq --mode deep
    .venv\\Scripts\\python.exe -X utf8 scripts\\coach_single.py --pgn data\\reports\\game.pgn --color black --out out.json

Exit codes: 0 = ok/degraded, 2 = partial (some plies unanalyzed), 1 = error.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _load_env() -> None:
    path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                if key.strip() and key.strip() not in os.environ:
                    os.environ[key.strip()] = value.strip()


def _summary(result: dict) -> str:
    analysis = result.get("analysis") or {}
    llm = result.get("llm") or {}
    timings = result.get("timings") or {}
    lines = [
        f"game: {result.get('game_id')} | color: {result.get('color')} | "
        f"mode: {result.get('mode')} | depth: {result.get('depth')}",
        f"status: {result.get('status')} | partial: {result.get('partial')}",
        f"moves: {analysis.get('moves_analyzed')}/{analysis.get('moves_total')} | "
        f"ACPL: {analysis.get('acpl')} | accuracy: {analysis.get('accuracy')}",
        f"engine: {json.dumps(result.get('engine'), ensure_ascii=False)}",
        f"time: total {timings.get('total_s')}s (engine {timings.get('engine_s')}s, "
        f"llm {timings.get('llm_s')}s) | cache_hit: {timings.get('cache_hit')}",
        f"report: {result.get('report_meta')} | llm: {llm.get('status')}/{llm.get('provider')}",
    ]
    for move in result.get("flagged_moves") or []:
        lines.append(
            f"  ply {move.get('ply')} {move.get('san')} {move.get('classification')} "
            f"cp={move.get('cp_loss')} best={move.get('best_move_san')} "
            f"rank={move.get('played_rank')} src={move.get('explanation_source')}"
        )
    for pattern in result.get("patterns") or []:
        lines.append(
            f"  pattern {pattern.get('pattern_id')} {pattern.get('pattern_name')} "
            f"conf={pattern.get('confidence')} freq={pattern.get('frequency')}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Coach one chess game (single-game pipeline)")
    parser.add_argument("game_id", nargs="?", default="", help="Lichess game ID")
    parser.add_argument("--pgn", default="", help="Path to a PGN file (alternative to game_id)")
    parser.add_argument("--username", default="", help="Your Lichess username (auto-detects color)")
    parser.add_argument("--color", default="", choices=["", "white", "black"])
    parser.add_argument("--depth", type=int, default=14)
    parser.add_argument("--mode", default="fast", choices=["fast", "deep"])
    parser.add_argument("--out", default="", help="Output JSON path (default: data/reports/)")
    parser.add_argument("--no-cache", action="store_true", help="Force a cold analysis")
    parser.add_argument("--quiet", action="store_true", help="Do not print the report body")
    args = parser.parse_args()

    if not args.game_id and not args.pgn:
        parser.error("either game_id or --pgn is required")

    _load_env()

    from lichess_analyzer_mcp.services import game_analyzer
    from lichess_analyzer_mcp.tools.coaching_single_game import lichess_coaching_single_game

    started = time.time()
    if args.pgn:
        path = args.pgn
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(__file__), "..", path)
        with open(path, encoding="utf-8") as fh:
            pgn = fh.read()
        analysis = game_analyzer.analyze_pgn(
            pgn,
            args.color or "white",
            depth=args.depth,
            use_cache=not args.no_cache,
            mode=args.mode,
        )
        result = analysis.to_dict()
        print(f"pgn: {args.pgn} | plies: {len(result.get('moves', []))}")
        print(f"ACPL: {result.get('total_acpl')} | accuracy: {result.get('accuracy')}")
        payload = result
    else:
        payload = asyncio.run(
            lichess_coaching_single_game(
                args.game_id,
                username=args.username,
                color=args.color,
                depth=args.depth,
                mode=args.mode,
            )
        )
        print(_summary(payload))
        if not args.quiet:
            print("\n=== REPORT ===")
            print(payload.get("report") or "")

    out = args.out
    if not out:
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        label = args.game_id or "pgn"
        out = os.path.join(DATA_DIR, "reports", f"single_game_{label}_{stamp}.json")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print(f"\njson: {out} ({os.path.getsize(out)} bytes) in {time.time() - started:.1f}s")

    from lichess_analyzer_mcp.services.engine_client import close_engine

    close_engine()

    if payload.get("status") == "partial":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
