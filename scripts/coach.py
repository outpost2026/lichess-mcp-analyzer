"""Unified single-game coaching CLI - compact JSON 2.0 by default.

One entry point for the three real workflows:

    # one Lichess game -> compact 2.0 (default)
    python scripts/coach.py --game-id FVhqtv1S

    # explicitly schema 1.1
    python scripts/coach.py --game-id FVhqtv1S --format detailed

    # both shapes in one payload {"compact": ..., "detailed": ...}
    python scripts/coach.py --game-id FVhqtv1S --format both

    # local PGN, fully offline (no Lichess fetch, no LLM)
    python scripts/coach.py --pgn-file game.pgn --color black --no-llm

    # last N games of a player -> array of compact games
    python scripts/coach.py --username systeq --batch 5 --out batch.json

JSON goes to stdout (or --out); progress and aggregates go to stderr, so
`coach.py ... | jq` always works.

Exit codes: 0 ok, 1 validation error (bad args / invalid PGN), 2 IO error,
3 engine error (Stockfish missing or timing out), 4 network error.
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

EXIT_OK = 0
EXIT_VALIDATION = 1
EXIT_IO = 2
EXIT_ENGINE = 3
EXIT_NETWORK = 4

_FORMATS = ("compact", "detailed", "both")


class _Parser(argparse.ArgumentParser):
    """argparse exits 2 on bad usage; the CLI contract says 1."""

    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"error: {message}", file=sys.stderr)
        raise SystemExit(EXIT_VALIDATION)


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


def _classify_exception(exc: Exception) -> int:
    """Map a failure to the documented exit code."""
    import chess.engine

    if isinstance(exc, chess.engine.EngineError):
        return EXIT_ENGINE
    try:
        import requests

        if isinstance(exc, requests.RequestException):
            return EXIT_NETWORK
    except Exception:  # requests is optional at CLI level
        pass
    if isinstance(exc, (FileNotFoundError, PermissionError, IsADirectoryError, OSError)):
        return EXIT_IO
    text = f"{type(exc).__name__}: {exc}".lower()
    if "stockfish" in text or "engine" in text:
        return EXIT_ENGINE
    if "lichess" in text or "http" in text or "network" in text or "connection" in text:
        return EXIT_NETWORK
    return EXIT_VALIDATION


def _pgn_header(pgn: str, key: str) -> str:
    match = re.search(rf'^\[{re.escape(key)}\s+"([^"]*)"\]', pgn, re.MULTILINE)
    return match.group(1) if match else ""


def _pgn_game_id(pgn: str) -> str:
    return (_pgn_header(pgn, "GameId") or _pgn_header(pgn, "Site").rstrip("/").split("/")[-1])[:8]


def _pgn_color(pgn: str, username: str) -> str:
    if username:
        if _pgn_header(pgn, "White").lower() == username.lower():
            return "white"
        if _pgn_header(pgn, "Black").lower() == username.lower():
            return "black"
    return ""


def _read_pgn(path: str) -> str:
    with open(path, encoding="utf-8-sig") as fh:
        return fh.read()


def _clear_cache(game_id: str, color: str, depth: int, mode: str) -> None:
    from lichess_analyzer_mcp.services.game_analyzer import _cache_path, _policy_token

    path = _cache_path(game_id, depth, color, _policy_token(depth, mode))
    if os.path.isfile(path):
        os.remove(path)


async def _single_game(
    game_id: str,
    *,
    username: str,
    color: str,
    depth: int,
    mode: str,
    fmt: str,
    use_llm: bool,
    no_cache: bool,
) -> dict | list:
    from lichess_analyzer_mcp.tools.coaching_single_game import (
        lichess_coaching_single_game,
    )

    colors = ["white", "black"] if color == "both" else [color]
    results = []
    for side in colors:
        if no_cache:
            _clear_cache(game_id, side, depth, mode)
        results.append(
            await lichess_coaching_single_game(
                game_id,
                username=username,
                color=side,
                depth=depth,
                mode=mode,
                output_format=fmt,
                use_llm=use_llm,
            )
        )
    return results[0] if len(results) == 1 else results


async def _single_pgn(
    path: str,
    *,
    username: str,
    color: str,
    depth: int,
    mode: str,
    fmt: str,
    use_llm: bool,
    no_cache: bool,
) -> dict | list:
    from lichess_analyzer_mcp.services.budget import budget_for_mode
    from lichess_analyzer_mcp.services.game_analyzer import analyze_pgn
    from lichess_analyzer_mcp.tools.coaching_single_game import build_response

    pgn = _read_pgn(path)
    game_id = _pgn_game_id(pgn) or os.path.splitext(os.path.basename(path))[0]
    side = _pgn_color(pgn, username) or color
    sides = ["white", "black"] if side == "both" else [side]
    deadline_s = float(budget_for_mode(mode)["total_s"])

    results = []
    for current in sides:
        started = time.perf_counter()
        analysis = analyze_pgn(
            pgn,
            current,
            depth,
            game_id or None,
            use_cache=not no_cache,
            strict_depth=True,
            mode=mode,
        )
        if not analysis.moves:
            raise ValueError("analysis produced no moves (invalid PGN?)")
        results.append(
            await build_response(
                game_id=game_id,
                username=username,
                detected_color=current,
                depth=depth,
                mode=mode,
                deadline_s=deadline_s,
                call_started=started,
                analysis_obj=analysis,
                io_s=0.0,
                use_llm=use_llm,
                ctx=None,
                output_format=fmt,
            )
        )
    return results[0] if len(results) == 1 else results


def _pattern_frequency(results: list[dict]) -> dict[str, int]:
    frequency: dict[str, int] = {}
    for result in results:
        for pattern in result.get("patterns") or []:
            pattern_id = pattern.get("id") or pattern.get("pattern_id")
            if pattern_id:
                frequency[pattern_id] = frequency.get(pattern_id, 0) + 1
    return dict(sorted(frequency.items()))


def aggregate(results: list[dict]) -> dict:
    """Session-level stats; computed from the compact payloads only."""
    acpls = [
        r["summary"]["acpl"]
        for r in results
        if isinstance((r.get("summary") or {}).get("acpl"), (int, float))
    ]
    classes = {"blunder": 0, "mistake": 0, "inaccuracy": 0}
    for result in results:
        for flag in result.get("flags") or []:
            if flag.get("class") in classes:
                classes[flag["class"]] += 1
    return {
        "games": len(results),
        "mean_acpl": round(sum(acpls) / len(acpls), 1) if acpls else None,
        "flags": classes,
        "patterns": _pattern_frequency(results),
    }


async def _batch(
    username: str,
    count: int,
    *,
    depth: int,
    mode: str,
    fmt: str,
    use_llm: bool,
    quiet: bool = False,
) -> list[dict]:
    from lichess_analyzer_mcp.services.lichess_client import fetch_user_games
    from lichess_analyzer_mcp.tools.coaching_single_game import (
        lichess_coaching_single_game,
    )

    games = fetch_user_games(username, max_games=count)
    if len(games) < count:
        # The local cache may be smaller than the requested batch; only a
        # refresh against Lichess can tell whether more games exist.
        games = fetch_user_games(username, max_games=count, refresh=True)
    games = sorted(games, key=lambda g: g.get("createdAt") or "", reverse=True)[:count]
    if not games:
        raise RuntimeError(f"Lichess returned no games for {username!r}")
    results = []
    for index, game in enumerate(games, start=1):
        game_id = game.get("id") or ""
        if not game_id:
            continue
        if not quiet:
            print(f"[{index}/{len(games)}] {game_id}", file=sys.stderr)
        results.append(
            await lichess_coaching_single_game(
                game_id,
                username=username,
                depth=depth,
                mode=mode,
                output_format=fmt,
                use_llm=use_llm,
            )
        )
    return results


def _write(payload, out: str, ndjson: bool) -> None:
    if ndjson:
        text = "\n".join(
            json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in payload
        )
    else:
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    if out:
        directory = os.path.dirname(os.path.abspath(out))
        os.makedirs(directory, exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text + ("\n" if not text.endswith("\n") else ""))
        print(f"json: {out}", file=sys.stderr)
    else:
        print(text)


def main(argv: list[str] | None = None) -> int:
    parser = _Parser(
        description="Coach chess games: compact JSON 2.0 by default (schema 1.1 on request)."
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--game-id", default="", help="Lichess game ID")
    source.add_argument("--pgn-file", default="", help="Path to a local PGN file")
    parser.add_argument("--username", default="", help="Lichess username (auto-detects color)")
    parser.add_argument(
        "--batch", type=int, default=0, help="Analyze the last N games of --username"
    )
    parser.add_argument("--color", default="white", choices=["white", "black", "both"])
    parser.add_argument("--depth", type=int, default=14)
    parser.add_argument("--mode", default="fast", choices=["fast", "deep"])
    parser.add_argument(
        "--format",
        dest="fmt",
        default="compact",
        choices=["compact", "detailed", "both", "full"],
        help="compact (default) | detailed (schema 1.1) | both | full (deprecated alias)",
    )
    parser.add_argument("--no-llm", action="store_true", help="Skip every LLM provider")
    parser.add_argument("--no-cache", action="store_true", help="Force a cold analysis")
    parser.add_argument(
        "--nodes-cap",
        type=int,
        default=0,
        help="Override the per-depth node ceiling for this process",
    )
    parser.add_argument("--out", default="", help="Output JSON path (default: stdout)")
    parser.add_argument("--ndjson", action="store_true", help="Batch only: one JSON per line")
    parser.add_argument("--quiet", action="store_true", help="Suppress progress messages")
    args = parser.parse_args(argv)

    if args.batch:
        if not args.username:
            parser.error("--batch requires --username")
        if args.game_id or args.pgn_file:
            parser.error("--batch cannot be combined with --game-id or --pgn-file")
        if args.batch < 1:
            parser.error("--batch must be >= 1")
        if args.fmt != "compact":
            parser.error("--batch supports --format compact only")
    else:
        if args.ndjson:
            parser.error("--ndjson is only valid with --batch")
        if bool(args.game_id) == bool(args.pgn_file):
            parser.error("exactly one of --game-id or --pgn-file is required")

    if args.fmt == "full":
        print("warning: --format full is deprecated; use --format detailed", file=sys.stderr)
        args.fmt = "detailed"

    _load_env()

    if args.nodes_cap:
        from lichess_analyzer_mcp.config import depth as depth_cfg

        depth_cfg.NODE_CAPS[args.depth] = int(args.nodes_cap)

    try:
        if args.batch:
            payload = asyncio.run(
                _batch(
                    args.username,
                    args.batch,
                    depth=args.depth,
                    mode=args.mode,
                    fmt=args.fmt,
                    use_llm=not args.no_llm,
                    quiet=args.quiet,
                )
            )
        elif args.game_id:
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
        else:
            payload = asyncio.run(
                _single_pgn(
                    args.pgn_file,
                    username=args.username,
                    color=args.color,
                    depth=args.depth,
                    mode=args.mode,
                    fmt=args.fmt,
                    use_llm=not args.no_llm,
                    no_cache=args.no_cache,
                )
            )
        _write(payload, args.out, args.ndjson)
        if args.batch and not args.quiet:
            stats = aggregate(payload)
            print(f"aggregate: {json.dumps(stats, ensure_ascii=False)}", file=sys.stderr)
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return _classify_exception(exc)
    finally:
        from lichess_analyzer_mcp.services.engine_client import close_engine

        close_engine()
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
