"""Offline batch analysis of anonymous games — OPPONENT perspective.

Reads the normalized record file (header line: `perspective: opponent`),
deterministically resolves the opponent's color per game from the PGN result
header + label, uses a color-aware cache lookup (falls back to Stockfish),
logs the full pipeline progress to data/pipeline_run_<ts>.log and writes a
checkpoint + final JSON report.

Usage:
    python -X utf8 scripts/run_anonymous_batch.py <file.txt> [--depth 12]
"""

import argparse
import glob
import json
import os
import re
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("LICHESS_TOKEN", "")

from lichess_analyzer_mcp.tools.anonymous_session import _resolve_color
from lichess_analyzer_mcp.services.lichess_client import fetch_game_pgn
from lichess_analyzer_mcp.services.game_analyzer import analyze_pgn
from lichess_analyzer_mcp.config.depth import DEPTH_DEFAULTS
from lichess_analyzer_mcp.models.game import GameAnalysis

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
CACHE_DIR = os.path.join(DATA_DIR, "game_cache")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


class PipelineLog:
    def __init__(self, path):
        self.path = path
        self.handle = open(path, "w", encoding="utf-8")

    def log(self, level, step, msg):
        line = f"{now_iso()} | {level:5s} | {step} | {msg}"
        print(line, flush=True)
        self.handle.write(line + "\n")
        self.handle.flush()

    def close(self):
        self.handle.close()


def parse_record_file(path):
    """Parse normalized record: header `perspective: <x>`, lines `URL win|loss|draw`."""
    lines = open(path, encoding="utf-8").read().splitlines()
    perspective = "unknown"
    entries = []
    for line in lines:
        line = line.strip().lstrip("\ufeff")
        if not line:
            continue
        if line.lower().startswith("perspective:"):
            perspective = line.split(":", 1)[1].strip().lower()
            continue
        m = re.match(
            r"^https://lichess\.org/([A-Za-z0-9]+)\s+(win|loss|draw)$", line, re.IGNORECASE
        )
        if m:
            gid = m.group(1)[:8]
            label = m.group(2).lower()
            entries.append((gid, label))
    return perspective, entries


def load_cached(gid, depth, want_color):
    pattern = os.path.join(CACHE_DIR, f"{gid}_{want_color}_d{depth}.json")
    hits = glob.glob(pattern)
    for hit in hits:
        try:
            with open(hit, encoding="utf-8") as f:
                data = json.load(f)
            return GameAnalysis.from_dict(data)
        except Exception as e:
            print(f"  [warn] cache read failed {os.path.basename(hit)}: {e}")
    return None


def main():
    parser = argparse.ArgumentParser(description="Offline anonymous batch (opponent perspective)")
    parser.add_argument("file_path", type=str, help=".txt record file, one URL + label per line")
    parser.add_argument("--depth", type=int, default=12, help="Stockfish depth (8-24)")
    parser.add_argument("--out", type=str, default="", help="Output JSON path (default: auto)")
    parser.add_argument("--log", type=str, default="", help="Pipeline log path (default: auto)")
    args = parser.parse_args()

    if not os.path.isfile(args.file_path):
        print(f"CHYBA: file not found: {args.file_path}")
        sys.exit(1)

    depth = args.depth
    if depth <= 0:
        depth = DEPTH_DEFAULTS["batch"]["anonymous"]
    depth = max(DEPTH_DEFAULTS["limits"]["min"], min(DEPTH_DEFAULTS["limits"]["max_batch"], depth))

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not args.log:
        args.log = os.path.join(DATA_DIR, f"pipeline_run_{stamp}.log")
    if not args.out:
        args.out = os.path.join(DATA_DIR, f"anonymous_batch_{stamp}.json")

    lg = PipelineLog(args.log)
    perspective, entries = parse_record_file(args.file_path)
    lg.log(
        "INFO",
        "START",
        f"file={os.path.basename(args.file_path)} perspective={perspective} "
        f"games={len(entries)} depth={depth}",
    )
    if perspective != "opponent":
        lg.log(
            "WARN",
            "START",
            f"perspective='{perspective}' != 'opponent' — barva se resi deterministicky "
            f"z PGN result + label (label=win -> oponent vitez, loss -> porazeny)",
        )

    games = []
    total_blunders = total_mistakes = total_inaccuracies = total_moves = 0
    acpl_values = []
    openings = {}
    player_wins = player_losses = player_draws = 0
    from_cache = 0
    from_engine = 0
    t0 = time.time()

    for i, (gid, label) in enumerate(entries, 1):
        tg = time.time()
        try:
            pgn = fetch_game_pgn(gid)
            opp_color = _resolve_color(pgn, label)
            cached = load_cached(gid, depth, opp_color)
            if cached is not None:
                analysis = cached
                from_cache += 1
            else:
                analysis = analyze_pgn(pgn, player_color=opp_color, depth=depth, game_id=gid)
                from_engine += 1

            g = analysis.game
            acpl = round(analysis.total_acpl, 1)
            blen = len(analysis.blunders)
            mlen = len(analysis.mistakes)
            ilen = len(analysis.inaccuracies)
            mcount = len(analysis.moves)

            total_blunders += blen
            total_mistakes += mlen
            total_inaccuracies += ilen
            total_moves += mcount
            acpl_values.append(acpl)

            eco = g.opening_eco or "?"
            openings[eco] = openings.get(eco, 0) + 1

            if g.result == "1-0":
                if opp_color == "white":
                    player_wins += 1
                else:
                    player_losses += 1
            elif g.result == "0-1":
                if opp_color == "black":
                    player_wins += 1
                else:
                    player_losses += 1
            else:
                player_draws += 1

            entry = {
                "id": gid,
                "label": label,
                "opp_color": opp_color,
                "opening": f"{g.opening} ({eco})",
                "result": g.result,
                "acpl": acpl,
                "blunders": blen,
                "mistakes": mlen,
                "inaccuracies": ilen,
                "moves": mcount,
                "top_blunders": [
                    f"Move {m.ply}: {m.move_san} (loss {m.centipawn_loss:.0f}cp, {m.phase})"
                    for m in analysis.blunders[:5]
                ],
                "duration_s": round(time.time() - tg, 2),
            }
            games.append(entry)
            src = "CACHE" if cached is not None else "ENGINE"
            lg.log(
                "INFO",
                f"GAME {i}/{len(entries)}",
                f"{gid} {src} color={opp_color} label={label} result={g.result} "
                f"ACPL={acpl} blunders={blen} ({time.time() - tg:.1f}s)",
            )
        except Exception as e:
            games.append(
                {
                    "id": gid,
                    "label": label,
                    "error": str(e),
                    "duration_s": round(time.time() - tg, 2),
                }
            )
            lg.log("ERROR", f"GAME {i}/{len(entries)}", f"{gid} CHYBA: {e}")

    n = len([g for g in games if "error" not in g])
    agg = {
        "perspective": perspective,
        "games_analyzed": n,
        "games_failed": len(entries) - n,
        "aggregate_acpl": round(sum(acpl_values) / n, 1) if acpl_values else 0,
        "total_blunders": total_blunders,
        "total_mistakes": total_mistakes,
        "total_inaccuracies": total_inaccuracies,
        "avg_blunders_per_game": round(total_blunders / n, 1) if n else 0,
        "avg_moves_per_game": round(total_moves / n, 1) if n else 0,
        "opponent_record": {"wins": player_wins, "losses": player_losses, "draws": player_draws},
        "top_openings": dict(sorted(openings.items(), key=lambda x: -x[1])[:5]),
    }

    report = {
        "meta": {
            "source_file": os.path.basename(args.file_path),
            "perspective": perspective,
            "depth": depth,
            "started": now_iso(),
            "finished": now_iso(),
            "total_duration_s": round(time.time() - t0, 2),
            "from_cache": from_cache,
            "from_engine": from_engine,
            "runner": "scripts/run_anonymous_batch.py",
        },
        "aggregate": agg,
        "games": games,
    }

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    lg.log(
        "INFO",
        "DONE",
        f"analyzed={n}/{len(entries)} cache={from_cache} engine={from_engine} "
        f"ACPL={agg['aggregate_acpl']} blunders={agg['total_blunders']} "
        f"record={agg['opponent_record']} dur={report['meta']['total_duration_s']}s",
    )
    lg.log("INFO", "OUT", f"report={args.out}")
    lg.close()

    print(f"\n=== BATCH COMPLETE ===")
    print(f"Analyzed: {n}/{len(entries)}, failed: {agg['games_failed']}")
    print(f"From cache: {from_cache}, from engine: {from_engine}")
    print(f"Opponent record: {agg['opponent_record']}")
    print(f"Aggregate ACPL (opponent): {agg['aggregate_acpl']}")
    print(f"Log: {args.log}")
    print(f"Report: {args.out}")


if __name__ == "__main__":
    main()
