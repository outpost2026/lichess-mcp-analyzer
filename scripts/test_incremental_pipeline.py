"""Test inkrementalni pipeline: per-game LLM cache + aggregate z cached summaries.
Demonstruje: 2 nove hry + 3 cache = jen 2 per-game LLM cally, aggregate pouzije summaries.
"""

import os, sys, json, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["LLM_MAX_TOKENS"] = "4000"

from src.services.game_llm_cache import analyze_game_llm, get_all_game_summaries

print("=" * 60)
print("  INCREMENTAL PIPELINE — per-game LLM cache")
print("=" * 60)

# Step 1: Load cached pipeline data
print("\n[1/5] Loading pipeline data...")
dump_path = os.path.join(os.path.dirname(__file__), "..", "data", "test_optimized_output.json")
with open(dump_path, "r", encoding="utf-8") as f:
    data = json.load(f)

patterns = data.get("patterns_detected", [])
weakness = data.get("weakness_report", None)
games_list = data.get("games_analyzed", [])
game_ids = [g["id"] for g in games_list]
print(f"  Games: {len(game_ids)} ({', '.join(game_ids)})")

# Step 2: Per-game LLM analysis (Level 2 cache)
print(f"\n[2/5] Per-game LLM analysis (Level 2 cache)...")
game_ids_llm = []
for gid in game_ids:
    color = next((g["color"] for g in games_list if g["id"] == gid), "white")
    t0 = time.time()
    result = analyze_game_llm(gid, color)
    elapsed = time.time() - t0
    if result:
        src = "cache" if result.get("generated") else "new"
        tok = result.get("token_log", {}).get("total_tokens", "?")
        print(f"  {'📦' if elapsed < 2 else '🌐'} {gid}: {tok} tokens, {elapsed:.1f}s")
        game_ids_llm.append(gid)
    else:
        print(f"  ❌ {gid}: failed")

# Step 3: Get cached summaries
print(f"\n[3/5] Building aggregate from cached summaries...")
tt = time.time()
game_summaries = get_all_game_summaries(game_ids)
print(f"  Summaries: {len(game_summaries)}")

# Step 4: Aggregate LLM call (lighter prompt — summaries instead of raw data)
print(f"\n[4/5] Aggregate LLM (using cached summaries)...")
from src.services.llm_client import generate_coaching_report_with_logs

report, log = generate_coaching_report_with_logs(
    username="systeq",
    games_analyzed=len(game_ids),
    patterns=patterns,
    weakness_report=weakness,
    game_summaries=game_summaries,
)

t_agg = time.time() - tt
print(f"\n  Result:")
for att in log:
    if att.get("error"):
        print(f"    ❌ {att['provider']}: {att['error'][:80]}")
    else:
        print(
            f"    ✅ {att['provider']}: {att.get('total_tokens', '?')} tokens, ${att.get('cost_usd', 0):.6f}"
        )

# Step 5: Write report
print(f"\n[5/5] Writing report...")
from datetime import datetime, timezone

ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
output_path = os.path.join(
    os.path.dirname(__file__), "..", "docs", f"coaching_report_systeq_incremental_{ts}.md"
)
with open(output_path, "w", encoding="utf-8") as f:
    f.write(f"# Coaching Report: systeq (Incremental)\n\n")
    f.write(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  \n")
    f.write(f"**Pipeline:** per-game LLM cache + aggregate  \n")
    f.write(f"**Games:** {len(game_ids)} (0 new, {len(game_ids)} from LLM cache)  \n")
    f.write(
        f"**Per-game LLM:** {len([g for g in os.listdir(os.path.join(os.path.dirname(__file__), '..', 'data', 'game_cache')) if g.endswith('_llm.json')])} cached  \n"
    )
    att = log[-1] if log else {}
    f.write(f"**Aggregate provider:** {att.get('provider', '?')}  \n")
    f.write(f"**Aggregate tokens:** {att.get('total_tokens', '?')}  \n")
    f.write(f"**Patterns detected:** {len(patterns)}  \n\n---\n\n")
    f.write(report)
print(f"  Written: {output_path}")

print(f"\n  Aggregate prompt tokens saved: per-game LLM precomputed, ")
print(f"  aggregate uses summaries instead of raw game data.")
print("=" * 60)
