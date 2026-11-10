"""DEPRECATED - use `scripts/coach.py --pgn-file ... --format compact`.

Kept for one release cycle so existing commands keep working. The pipeline is
the same as the unified CLI (including PV recovery for blunders), only the
argument names and the default output path differ.

    # old
    python scripts/pgn_to_compact.py --game-id lxO3gwd3 --color black --out x.json

    # new
    python scripts/coach.py --game-id lxO3gwd3 --color black --out x.json
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime

sys.path.insert(0, os.path.dirname(__file__))

import coach  # noqa: E402  (same directory, imported on purpose)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

DEPRECATION = (
    "warning: pgn_to_compact.py is deprecated; "
    "use scripts/coach.py --pgn-file <path> --format compact"
)


def main() -> int:
    print(DEPRECATION, file=sys.stderr)

    parser = argparse.ArgumentParser(description="PGN -> compact single-game JSON (schema 2.0)")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--game-id", default="", help="Lichess game ID")
    src.add_argument("--pgn-file", default="", help="Path to a PGN file")
    parser.add_argument("--color", default="white", choices=["white", "black"])
    parser.add_argument("--depth", type=int, default=14)
    parser.add_argument(
        "--nodes-cap",
        type=int,
        default=0,
        help="Override the per-depth node ceiling (0 = policy default)",
    )
    parser.add_argument("--mode", default="fast", choices=["fast", "deep"])
    parser.add_argument("--out", default="", help="Output JSON path")
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Accepted for compatibility; this ETL never calls an LLM",
    )
    parser.add_argument("--no-cache", action="store_true", help="Force a cold analysis")
    args = parser.parse_args()

    coach._load_env()

    if args.nodes_cap:
        from lichess_analyzer_mcp.config import depth as depth_cfg

        depth_cfg.NODE_CAPS[args.depth] = int(args.nodes_cap)

    try:
        if args.pgn_file:
            payload = asyncio.run(
                coach._single_pgn(
                    args.pgn_file,
                    username="",
                    color=args.color,
                    depth=args.depth,
                    mode=args.mode,
                    fmt="compact",
                    use_llm=False,
                    no_cache=args.no_cache,
                )
            )
        else:
            payload = asyncio.run(
                coach._single_game(
                    args.game_id,
                    username="",
                    color=args.color,
                    depth=args.depth,
                    mode=args.mode,
                    fmt="compact",
                    use_llm=False,
                    no_cache=args.no_cache,
                )
            )
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return coach._classify_exception(exc)
    finally:
        from lichess_analyzer_mcp.services.engine_client import close_engine

        close_engine()

    if not isinstance(payload, dict) or payload.get("v") != "2.0":
        print(f"error: unexpected payload: {str(payload)[:200]}", file=sys.stderr)
        return coach.EXIT_VALIDATION

    out = args.out
    if not out:
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        label = args.game_id or os.path.splitext(os.path.basename(args.pgn_file))[0]
        out = os.path.join(DATA_DIR, "reports", f"compact_{label}_{stamp}.json")
    try:
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
    except OSError as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return coach.EXIT_IO

    from lichess_analyzer_mcp.services.compact_serializer import compact_size

    print(
        f"compact: {out} ({compact_size(payload)} chars, "
        f"{len(payload.get('flags') or [])} flags, "
        f"{len(payload.get('patterns') or [])} patterns)"
    )
    return coach.EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
