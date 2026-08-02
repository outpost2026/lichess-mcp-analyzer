"""Offline opponent_pool persist s deterministickymi oponent barvami.

Pro anonymni hry je fallback author=white v lichess_coaching_opponent_pool
nepouzitelny (oba hraci = 'Anonymous'). Tento skript cte oponent barvy
deterministicky z anonymous_batch reportu a replikuje opponent_pool flow
(pattern detection + LLM cascade + persist do data/reports/ a docs/).

Usage:
    python -X utf8 scripts/run_opponent_pool_offline.py
"""

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
REPORTS_DIR = os.path.join(DATA_DIR, "reports")
DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")
REPORT_SRC = os.path.join(DATA_DIR, "anonymous_batch_20260802_194453.json")
DEPTH = 12


def _write_verified(path: str, content: str) -> dict:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, path)
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        raise OSError(f"read-after-write verification failed: {path}")
    return {"path": path, "size_bytes": os.path.getsize(path)}


def main():
    from lichess_analyzer_mcp.services.game_analyzer import _load_cached_analysis
    from lichess_analyzer_mcp.services.coaching_base import (
        collect_patterns_for_games,
        safe_llm_call,
    )
    from lichess_analyzer_mcp.services.prompt_builder import build_prompt

    src = json.load(open(REPORT_SRC, encoding="utf-8"))
    games = [g for g in src["games"] if "error" not in g]
    print(f"her v reportu: {len(games)}")

    opponent_analyses = []
    n1 = n2 = 0
    missing = []
    for g in games:
        gid, opp = g["id"], g["opp_color"]
        a = _load_cached_analysis(gid, DEPTH, opp, exact_depth=False)
        if a is None:
            missing.append(gid)
            continue
        opponent_analyses.append(a)
        won = (opp == "white" and g["result"] == "1-0") or (opp == "black" and g["result"] == "0-1")
        if won:
            n2 += 1
        else:
            n1 += 1

    print(
        f"oponent analýz: {len(opponent_analyses)} | n1 (opp prohrál): {n1} | n2 (opp vyhrál): {n2}"
    )
    if missing:
        print(f"VAROVANI: chybi cache: {missing}")
        return

    t0 = time.time()
    opponent_patterns = collect_patterns_for_games(opponent_analyses, "opponent")
    n = len(opponent_analyses)

    def _avg_acpl(games):
        return sum(a.total_acpl for a in games) / len(games) if games else 0.0

    def _blunder_rate(games):
        return sum(len(a.blunders) + len(a.mistakes) for a in games) / len(games) if games else 0.0

    n1_games = [
        a
        for a, g in zip(opponent_analyses, games)
        if not (
            (g["opp_color"] == "white" and g["result"] == "1-0")
            or (g["opp_color"] == "black" and g["result"] == "0-1")
        )
    ]
    n2_games = [
        a
        for a, g in zip(opponent_analyses, games)
        if (g["opp_color"] == "white" and g["result"] == "1-0")
        or (g["opp_color"] == "black" and g["result"] == "0-1")
    ]

    prompt_data = {
        "N": n,
        "n1": n1,
        "n2": n2,
        "n1_počet": n1,
        "n2_počet": n2,
        "n1_acpl": f"{_avg_acpl(n1_games):.1f}" if n1_games else "?",
        "n2_acpl": f"{_avg_acpl(n2_games):.1f}" if n2_games else "?",
        "n1_blunder_rate": f"{_blunder_rate(n1_games):.2f}" if n1_games else "?",
        "n2_blunder_rate": f"{_blunder_rate(n2_games):.2f}" if n2_games else "?",
        "opponent_patterns_json": json.dumps(opponent_patterns, ensure_ascii=False, indent=2),
        "author_patterns_json": "[]",
    }

    prompt = build_prompt(3, prompt_data)
    report, cascade_log = safe_llm_call(prompt, f"opponent_pool:offline_{n}")

    result = {
        "ids": [g["id"] for g in games],
        "opponent_games_analyzed": n,
        "author_games_analyzed": 0,
        "report": report,
        "opponent_patterns": opponent_patterns,
        "n1": n1,
        "n2": n2,
        "n1_acpl": prompt_data["n1_acpl"],
        "n2_acpl": prompt_data["n2_acpl"],
        "n1_blunder_rate": prompt_data["n1_blunder_rate"],
        "n2_blunder_rate": prompt_data["n2_blunder_rate"],
        "cascade_log": cascade_log,
        "elapsed_seconds": round(time.time() - t0, 1),
    }

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    ref = f"pool_{n}"
    artifacts = []
    artifacts.append(
        _write_verified(
            os.path.join(REPORTS_DIR, f"opponent_pool_{ref}_{ts}.json"),
            json.dumps(result, ensure_ascii=False, indent=2),
        )
    )
    md_lines = [
        f"# Coaching Report — opponent_pool ({ref})",
        "",
        f"**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Pipeline:** deterministic (Stockfish) + LLM cascade",
        f"**Perspective:** OPPONENT (deterministické barvy z anonymous_batch reportu)",
        f"**Games analyzed:** {n}",
        f"**n1 (opponent prohrál):** {n1} | **n2 (opponent vyhrál):** {n2}",
        "",
        "---",
        "",
        "## Opponent Patterns",
        "",
        "| Pattern | Name | Confidence | Frequency | Severity |",
        "|---------|------|------------|-----------|----------|",
    ]
    for p in opponent_patterns:
        md_lines.append(
            f"| {p.get('pattern_id', '?')} | {p.get('pattern_name', '?')} | "
            f"{p.get('confidence', '?')}% | {p.get('frequency', '?')} | "
            f"{p.get('severity', '?').upper()} |"
        )
    md_lines += ["", "---", "", "## LLM Report", "", report]
    prov = "n/a"
    for entry in reversed(cascade_log):
        if entry.get("provider") and not entry.get("error"):
            prov = entry["provider"]
            break
    md_lines += ["", "---", "", "## Provider Cascade", ""]
    for i, entry in enumerate(cascade_log):
        if entry.get("error"):
            md_lines.append(
                f"| {i + 1} | {entry.get('provider', '?')} | ERROR: {entry['error'][:60]} |"
            )
        else:
            md_lines.append(f"| {i + 1} | {entry.get('provider', '?')} | OK |")
    artifacts.append(
        _write_verified(
            os.path.join(DOCS_DIR, f"coaching_report_opponent_pool_{ref}_{ts}.md"),
            "\n".join(md_lines),
        )
    )

    print(f"\n=== OPPONENT POOL OFFLINE PERSIST ===")
    print(f"dur: {result['elapsed_seconds']}s | LLM provider: {prov}")
    for a in artifacts:
        print(f"  {a['path']} ({a['size_bytes']} B)")


if __name__ == "__main__":
    main()
