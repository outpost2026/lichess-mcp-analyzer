"""Test pipeline mode switch: auto / mono / incremental."""

import os, sys, json, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["LLM_MAX_TOKENS"] = "4000"

dump_path = os.path.join(os.path.dirname(__file__), "..", "data", "test_optimized_output.json")
with open(dump_path) as f:
    ref = json.load(f)
patterns = ref.get("patterns_detected", [])
weakness = ref.get("weakness_report", None)
games_list = ref.get("games_analyzed", [])
game_ids = [g["id"] for g in games_list]
game_colors = [g["color"] for g in games_list]

from lichess_analyzer_mcp.services.llm_client import run_coaching_pipeline

for mode in ["mono", "incremental", "auto"]:
    print(f"\n{'=' * 50}")
    print(f"  MODE: {mode} ({len(game_ids)} games)")
    print(f"{'=' * 50}")
    t0 = time.time()
    report, log, meta = run_coaching_pipeline(
        username="systeq",
        game_ids=game_ids,
        game_colors=game_colors,
        patterns=patterns,
        weakness_report=weakness,
        mode=mode,
    )
    elapsed = time.time() - t0
    att = log[-1] if log else {}
    total_tok = att.get("total_tokens", "?")
    lines = len(report.strip().split("\n"))
    print(
        f"  Mode: {meta['mode']}  |  Provider: {att.get('provider', '?')}  |  Tokens: {total_tok}"
    )
    print(
        f"  Per-game calls: {meta['per_game_calls']}  |  Per-game tok: {meta['per_game_tokens']}  |  Time: {elapsed:.1f}s"
    )
    print(f"  Report: {lines} lines")
    print(f"  First line: {report.strip().split(chr(10))[0][:80]}")

print(f"\n{'=' * 50}")
print(f"  GOLDEN RULES SUMMARY")
print(f"{'=' * 50}")
print(f"  N≤30  + quick analysis  → mono (faster, fewer tokens)")
print(f"  N>30  + batch analysis  → incremental (cache amortizes)")
print(f"  PGN import / GM games  → incremental (per-game deep analysis)")
print(f"  Env override: PIPELINE_MODE=mono|incremental")
print(f"{'=' * 50}")
