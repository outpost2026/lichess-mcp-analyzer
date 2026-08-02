"""Offline opponent_pool persist — CLI varianta lichess_persist_report.

Obejde MCP transport timeout (~60s) pro velke batchy (101 her):
spousti report_persister.persist_report primo, s plnym bash timeoutem.

Usage:
    python -X utf8 scripts/run_persist_opponent_pool.py <game_ids.txt> [--format both] [--target docs] [--depth 12]
"""

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("LICHESS_TOKEN", "")


def load_ids(path):
    ids = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.lower().startswith("perspective:"):
                continue
            import re

            m = re.match(r"^https://lichess\.org/([A-Za-z0-9]+)", line)
            if m:
                ids.append(m.group(1)[:8])
            elif len(line) == 8 and line.isalnum():
                ids.append(line)
    return ids


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "ids_file", type=str, help=".txt se hrami (URL label nebo jen 8-znakove ID)"
    )
    parser.add_argument("--format", type=str, default="both", choices=["json", "md", "both"])
    parser.add_argument("--target", type=str, default="docs", choices=["docs", "kb"])
    parser.add_argument("--depth", type=int, default=12)
    args = parser.parse_args()

    ids = load_ids(args.ids_file)
    if not ids:
        print("CHYBA: zadne ID nenacteno")
        sys.exit(1)
    print(f"ID nacteno: {len(ids)}")

    import asyncio
    from lichess_analyzer_mcp.services.report_persister import persist_report

    params = {"game_ids": ids, "depth": args.depth}
    t0 = time.time()

    async def run():
        return await persist_report("opponent_pool", params, fmt=args.format, target=args.target)

    result = asyncio.run(run())
    print(f"\n=== OPPONENT POOL PERSIST ===")
    print(f"dur: {time.time() - t0:.1f}s")
    import json

    print(json.dumps(result, ensure_ascii=False, indent=2)[:4000])


if __name__ == "__main__":
    main()
