"""PGN -> compact schema 2.0 JSON (offline ETL, no LLM).

Examples
--------
    .venv\\Scripts\\python.exe -X utf8 scripts\\pgn_to_compact.py --game-id lxO3gwd3 --color black --out data\\reports\\lx.json
    .venv\\Scripts\\python.exe -X utf8 scripts\\pgn_to_compact.py --pgn-file game.pgn --color white --out x.json
    .venv\\Scripts\\python.exe -X utf8 scripts\\pgn_to_compact.py --game-id Sl1s8KmU --color black --nodes-cap 200000

The ETL never calls an LLM. It runs the deterministic engine policy
(1 thread, depth + node cap, clear hash) and serializes the result to the
compact 2.0 shape. Exit code 0 = OK, 1 = error (message on stderr).
"""

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_FLAGGED = ("blunder", "mistake", "inaccuracy")


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


def _flagged_from_analysis(analysis) -> list[dict]:
    out = []
    for move in analysis.moves:
        if move.classification not in _FLAGGED:
            continue
        out.append(
            {
                "ply": move.ply,
                "san": move.move_san,
                "classification": move.classification,
                "cp_loss": move.centipawn_loss,
                "best_move_san": move.best_move_san,
                "played_rank": move.played_rank,
                "engine_lines": move.engine_lines,
                "motif": move.motif_type,
                "fen": move.fen,
            }
        )
    return out


def _summary_text(analysis, patterns: list[dict]) -> str:
    game = analysis.game
    stats = analysis.phase_stats or {}
    measured = {
        p: s.get("acpl") for p, s in stats.items() if isinstance(s.get("acpl"), (int, float))
    }
    weakest = max(measured, key=measured.get) if measured else None
    counts = {"blunder": 0, "mistake": 0, "inaccuracy": 0}
    for move in analysis.moves:
        if move.classification in counts:
            counts[move.classification] += 1
    opening = " ".join(x for x in (game.opening_eco, game.opening) if x) or "?"
    parts = [
        f"Hra {game.result} ({opening}), ACPL {round(analysis.total_acpl, 1)}, "
        f"accuracy {round(analysis.accuracy, 1)} %.",
        f"{counts['blunder']} blunderů, {counts['mistake']} mistakes, "
        f"{counts['inaccuracy']} nepřesností.",
    ]
    if weakest:
        parts.append(f"Nejslabší fáze: {weakest} (ACPL {measured[weakest]}).")
    if patterns:
        parts.append(
            "Patterny: "
            + ", ".join(
                f"{p.get('pattern_id')} ({p.get('pattern_name', '?')}, conf {p.get('confidence')})"
                for p in patterns
            )
            + "."
        )
    return " ".join(parts)


def main() -> int:
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

    _load_env()

    from lichess_analyzer_mcp.services import engine_client
    from lichess_analyzer_mcp.services.compact_serializer import (
        compact_size,
        to_compact_v2,
        validate_compact,
    )
    from lichess_analyzer_mcp.services.game_analyzer import analyze_pgn
    from lichess_analyzer_mcp.services.pattern_detector import detect_single_game

    started = time.perf_counter()
    try:
        if args.nodes_cap:
            from lichess_analyzer_mcp.config import depth as depth_cfg

            depth_cfg.NODE_CAPS[args.depth] = int(args.nodes_cap)

        if args.pgn_file:
            path = args.pgn_file
            if not os.path.isabs(path):
                path = os.path.join(os.path.dirname(__file__), "..", path)
            with open(path, encoding="utf-8") as fh:
                pgn = fh.read()
            game_id = ""
        else:
            from lichess_analyzer_mcp.services.lichess_client import fetch_game_pgn

            game_id = args.game_id
            pgn = fetch_game_pgn(game_id)

        analysis = analyze_pgn(
            pgn,
            args.color,
            args.depth,
            game_id or None,
            use_cache=not args.no_cache,
            strict_depth=True,
            mode=args.mode,
        )
        if not analysis.moves:
            print("error: analysis produced no moves", file=sys.stderr)
            return 1

        patterns = detect_single_game(analysis)
        full = {
            "game_id": game_id or analysis.game.id,
            "color": args.color,
            "depth": args.depth,
            "analysis": {
                "acpl": round(analysis.total_acpl, 1),
                "accuracy": analysis.accuracy,
                "phase_stats": analysis.phase_stats,
            },
            "flagged_moves": _flagged_from_analysis(analysis),
            "patterns": patterns,
            "report": _summary_text(analysis, patterns),
            "llm": {
                "status": "failed",
                "provider": "deterministic",
                "reason": "llm_disabled",
            },
        }
        compact = to_compact_v2(
            full,
            game_meta=analysis.game.to_dict(),
            moves=[m.to_dict() for m in analysis.moves],
        )
        validate_compact(compact)
    except Exception as exc:  # CLI boundary: message + non-zero exit
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        engine_client.close_engine()

    out = args.out
    if not out:
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        label = game_id or "pgn"
        out = os.path.join(DATA_DIR, "reports", f"compact_{label}_{stamp}.json")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(compact, fh, ensure_ascii=False, indent=2)

    elapsed = time.perf_counter() - started
    print(
        f"compact: {out} ({compact_size(compact)} chars, "
        f"{len(compact['flags'])} flags, {len(compact['patterns'])} patterns) "
        f"in {elapsed:.1f}s"
    )
    if analysis.unanalyzed_plies:
        print(
            f"warning: {len(analysis.unanalyzed_plies)} unanalyzed plies: "
            f"{analysis.unanalyzed_plies[:10]}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
