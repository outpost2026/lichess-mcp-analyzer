"""Coach one game from the command line - the standard single-game path.

Same pipeline as the MCP tool `lichess_coaching_single_game`, but usable
without an MCP client / IDE. Both colours are analysed by default, so one
JSON file carries the complete game dynamic (D24).

Examples
--------
    # both colours, compact 2.1 + detailed 1.2 in one file (default)
    .venv\\Scripts\\python.exe -X utf8 scripts\\coach_single.py quOLOThu

    # one perspective only
    .venv\\Scripts\\python.exe -X utf8 scripts\\coach_single.py nxKgE4l8 --color white

    # let the pipeline detect the side (Lichess account game)
    .venv\\Scripts\\python.exe -X utf8 scripts\\coach_single.py lxO3gwd3 --username systeq

    # local PGN, no LLM
    .venv\\Scripts\\python.exe -X utf8 scripts\\coach_single.py --pgn game.pgn --no-llm

Exit codes: 0 = ok/degraded, 2 = partial (some plies unanalyzed), 1 = error.
An error is reported on stderr and no JSON file is written - an empty payload
is never a valid result.
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import UTC, datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.coach import (  # noqa: E402  (sys.path must be set first)
    DATA_DIR,
    _load_env,
    _single_game,
    _single_pgn,
)

_COLOR_KEYS = ("white", "black")


def _perspectives(payload: dict) -> list[tuple[str, dict]]:
    """Split the keyed both-colour payload into `(label, report)` pairs."""
    if payload and all(key in _COLOR_KEYS for key in payload):
        return [(key, payload[key]) for key in _COLOR_KEYS if key in payload]
    return [("", payload)]


def _detailed(report: dict) -> dict:
    """`--format both` wraps the shapes; the summary always reads detailed."""
    inner = report.get("detailed")
    return inner if isinstance(inner, dict) else report


def _compact_of(report: dict) -> dict | None:
    """Return the compact payload whether it is wrapped or bare."""
    inner = report.get("compact")
    if isinstance(inner, dict):
        return inner
    if "v" in report and "summary" in report and "flags" in report:
        return report
    return None


def _compact_summary(label: str, compact: dict) -> str:
    game = compact.get("game") or {}
    summary = compact.get("summary") or {}
    header = f"game: {game.get('id')}"
    if label:
        header += f" | perspective: {label}"
    header += f" | color: {game.get('color')} | schema: {compact.get('v')}"
    return "\n".join(
        [
            header,
            f"players: {game.get('username') or 'anonymous'} | "
            f"result: {game.get('result')} | tc: {game.get('tc')}",
            f"acpl: {summary.get('acpl')} | acc: {summary.get('acc')} "
            f"({summary.get('acc_method')})",
            f"phases: {json.dumps(summary.get('phases'), ensure_ascii=False)}",
            f"flags: {len(compact.get('flags') or [])} | "
            f"patterns: {len(compact.get('patterns') or [])}",
        ]
    )


def _summary(label: str, report: dict) -> str:
    compact = _compact_of(report)
    if compact is not None:
        return _compact_summary(label, compact)
    result = _detailed(report)
    analysis = result.get("analysis") or {}
    llm = result.get("llm") or {}
    timings = result.get("timings") or {}
    game = result.get("game") or {}
    who = " vs ".join(
        part
        for part in (
            str(game.get("player_name") or "").strip(),
            str(game.get("opponent_name") or "").strip(),
        )
        if part
    )
    header = f"game: {result.get('game_id')}"
    if label:
        header += f" | perspective: {label}"
    header += (
        f" | color: {result.get('color')} | mode: {result.get('mode')}"
        f" | depth: {result.get('depth')}"
    )
    lines = [
        header,
        f"players: {who or 'anonymous'} | result: {game.get('result') or '?'}"
        f" | tc: {game.get('time_control') or '?'}",
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


def _failures(payload: dict) -> list[str]:
    """Every error the pipeline reported, labelled by perspective."""
    out: list[str] = []
    for label, report in _perspectives(payload):
        for err in report.get("errors") or []:
            prefix = f"{label}: " if label else ""
            out.append(f"{prefix}{err.get('code')}: {err.get('message')}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Coach one chess game (both colours by default)")
    parser.add_argument("game_id", nargs="?", default="", help="Lichess game ID")
    parser.add_argument("--pgn", default="", help="Path to a PGN file (alternative to game_id)")
    parser.add_argument("--username", default="", help="Your Lichess username (auto-detects color)")
    parser.add_argument(
        "--color",
        default="",
        choices=["", "white", "black", "both"],
        help="Perspective: white | black | both. Omit it to analyse both colours; "
        "with --username alone the side is detected",
    )
    parser.add_argument(
        "--format",
        dest="fmt",
        default="both",
        choices=["compact", "detailed", "both"],
        help="compact 2.1 | detailed 1.2 | both (default)",
    )
    parser.add_argument("--depth", type=int, default=14)
    parser.add_argument("--mode", default="fast", choices=["fast", "deep"])
    parser.add_argument("--out", default="", help="Output JSON path (default: data/reports/)")
    parser.add_argument("--no-cache", action="store_true", help="Force a cold analysis")
    parser.add_argument("--no-llm", action="store_true", help="Skip every LLM provider")
    parser.add_argument("--quiet", action="store_true", help="Do not print the report body")
    args = parser.parse_args()

    if not args.game_id and not args.pgn:
        parser.error("either game_id or --pgn is required")

    _load_env()

    started = time.time()
    try:
        if args.pgn:
            path = args.pgn
            if not os.path.isabs(path):
                path = os.path.join(os.path.dirname(__file__), "..", path)
            payload = asyncio.run(
                _single_pgn(
                    path,
                    username=args.username,
                    color=args.color,
                    depth=args.depth,
                    mode=args.mode,
                    fmt=args.fmt,
                    use_llm=not args.no_llm,
                    no_cache=args.no_cache,
                )
            )
        else:
            payload = asyncio.run(
                _single_game(
                    args.game_id,
                    username=args.username,
                    color=args.color,
                    depth=args.depth,
                    mode=args.mode,
                    fmt=args.fmt,
                    use_llm=not args.no_llm,
                    no_cache=args.no_cache,
                )
            )
    except Exception as exc:  # noqa: BLE001 - CLI boundary, message is the product
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        from lichess_analyzer_mcp.services.engine_client import close_engine

        close_engine()

    failures = _failures(payload)
    if failures:
        # The tool reports errors inside a valid-looking payload; publishing
        # that file would hand the LLM an empty game. Fail loudly instead.
        for line in failures:
            print(f"error: {line}", file=sys.stderr)
        return 1

    partial = False
    for label, report in _perspectives(payload):
        if not args.quiet:
            print(_summary(label, report))
            body = _detailed(report).get("report") or ""
            if body:
                print(f"\n=== REPORT {label.upper() or ''} ===".rstrip())
                print(body)
        if report.get("status") == "partial":
            partial = True

    out = args.out
    if not out:
        stamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        label = args.game_id or "pgn"
        out = os.path.join(DATA_DIR, "reports", f"single_game_{label}_{stamp}.json")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print(f"\njson: {out} ({os.path.getsize(out)} bytes) in {time.time() - started:.1f}s")

    return 2 if partial else 0


if __name__ == "__main__":
    raise SystemExit(main())
