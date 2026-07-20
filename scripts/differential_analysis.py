"""Diferencialni analyza: monoliticka vs inkrementalni pipeline.
Testuje: tokens, time, cost, determinismus, kvalita."""

import os, sys, json, time, hashlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["LLM_MAX_TOKENS"] = "4000"

from src.services.game_llm_cache import analyze_game_llm, get_all_game_summaries
from src.services.llm_client import generate_coaching_report_with_logs, PROVIDERS

print("=" * 65)
print("  DIFFERENTIAL ANALYSIS: Monolithic vs Incremental Pipeline")
print("=" * 65)

# Load reference data
dump_path = os.path.join(os.path.dirname(__file__), "..", "data", "test_optimized_output.json")
with open(dump_path, "r", encoding="utf-8") as f:
    ref = json.load(f)
patterns = ref.get("patterns_detected", [])
weakness = ref.get("weakness_report", None)
games_list = ref.get("games_analyzed", [])
game_ids = [g["id"] for g in games_list]

# Reference: monolitni beh (drivejsi data z compare_providers)
ref_costs = {
    "NVIDIA": {"tokens": 2597, "cost": 0.0, "time": 17.4},
    "DeepSeek V4 Flash": {"tokens": 3876, "cost": 0.000960, "time": 31.0},
    "Cerebras": {"tokens": 2677, "cost": 0.0, "time": None},
}

print(f"\n  Games: {len(game_ids)} ({', '.join(game_ids)})")
print(f"  Patterns: {len(patterns)}")

# === RUN 1: First incremental (no LLM cache) ===
print(f"\n{'=' * 65}")
print(f"  RUN 1: First incremental (cold cache)")
print(f"{'=' * 65}")

t0_total = time.time()

t_per_game_start = time.time()
per_game_log = []
for gid in game_ids:
    color = next((g["color"] for g in games_list if g["id"] == gid), "white")
    tt = time.time()
    result = analyze_game_llm(gid, color, force=False)
    elapsed = time.time() - tt
    if result:
        src = "cache" if elapsed < 2 else "new"
        tok = result.get("token_log", {}).get("total_tokens", "?")
        cost = result.get("token_log", {}).get("cost_usd", 0)
        per_game_log.append(
            {"game_id": gid, "tokens": tok, "cost": cost, "time": elapsed, "src": src}
        )
        print(f"    {gid}: {tok} tokens, ${cost:.6f}, {elapsed:.1f}s [{src}]")
    else:
        print(f"    {gid}: FAILED")

t_per_game = time.time() - t_per_game_start
total_per_game_tokens = sum(
    g.get("tokens", 0) if isinstance(g.get("tokens"), int) else 0 for g in per_game_log
)
total_per_game_cost = sum(g.get("cost", 0) for g in per_game_log)
print(
    f"  Per-game total: {total_per_game_tokens} tokens, ${total_per_game_cost:.6f}, {t_per_game:.1f}s"
)

# Aggregate
print(f"\n  Aggregate call...")
game_summaries = get_all_game_summaries(game_ids)
t_agg_start = time.time()
report_1, log_1 = generate_coaching_report_with_logs(
    username="systeq",
    games_analyzed=len(game_ids),
    patterns=patterns,
    weakness_report=weakness,
    game_summaries=game_summaries,
)
t_agg = time.time() - t_agg_start
att_1 = log_1[-1] if log_1 else {}
agg_provider_1 = att_1.get("provider", "?")
agg_tokens_1 = att_1.get("total_tokens", "?")
agg_cost_1 = att_1.get("cost_usd", 0)
print(f"    {agg_provider_1}: {agg_tokens_1} tokens, ${agg_cost_1:.6f}, {t_agg:.1f}s")

t_total_1 = time.time() - t0_total
run_1_total_tokens = total_per_game_tokens + (agg_tokens_1 if isinstance(agg_tokens_1, int) else 0)
run_1_total_cost = total_per_game_cost + agg_cost_1

# === RUN 2: Second incremental (warm cache — determinism test) ===
print(f"\n{'=' * 65}")
print(f"  RUN 2: Second incremental (warm cache)")
print(f"{'=' * 65}")

t0_total = time.time()
per_game_log_2 = []
for gid in game_ids:
    color = next((g["color"] for g in games_list if g["id"] == gid), "white")
    tt = time.time()
    result = analyze_game_llm(gid, color, force=False)
    elapsed = time.time() - tt
    tok = result.get("token_log", {}).get("total_tokens", "?") if result else "?"
    cost = result.get("token_log", {}).get("cost_usd", 0) if result else 0
    per_game_log_2.append(
        {
            "game_id": gid,
            "tokens": tok,
            "cost": cost,
            "time": elapsed,
            "src": "cache" if elapsed < 2 else "new",
        }
    )
    print(f"    {gid}: {tok} tokens, ${cost:.6f}, {elapsed:.1f}s [cache]")

t_per_game_2 = time.time() - t0_total
print(f"  Per-game total: {t_per_game_2:.1f}s")

game_summaries_2 = get_all_game_summaries(game_ids)
t_agg_start = time.time()
report_2, log_2 = generate_coaching_report_with_logs(
    username="systeq",
    games_analyzed=len(game_ids),
    patterns=patterns,
    weakness_report=weakness,
    game_summaries=game_summaries,
)
t_agg_2 = time.time() - t_agg_start
att_2 = log_2[-1] if log_2 else {}
agg_provider_2 = att_2.get("provider", "?")
agg_tokens_2 = att_2.get("total_tokens", "?")
agg_cost_2 = att_2.get("cost_usd", 0)
print(f"    {agg_provider_2}: {agg_tokens_2} tokens, ${agg_cost_2:.6f}, {t_agg_2:.1f}s")

t_total_2 = time.time() - t0_total

# === DETERMINISM CHECK ===
print(f"\n{'=' * 65}")
print(f"  DETERMINISM CHECK")
print(f"{'=' * 65}")

# Compare report content
r1_lines = report_1.strip().split("\n")
r2_lines = report_2.strip().split("\n")
if len(r1_lines) == len(r2_lines):
    identical = report_1.strip() == report_2.strip()
    print(f"  Report length: {len(r1_lines)} lines (both runs)")
    print(f"  Identical content: {'YES' if identical else 'NO'}")
    if not identical:
        # Show diff
        for i, (a, b) in enumerate(zip(r1_lines, r2_lines)):
            if a != b:
                print(f"  Diff at line {i + 1}:")
                print(f"    Run1: {a[:100]}")
                print(f"    Run2: {b[:100]}")
                break
else:
    print(f"  Report length: Run1={len(r1_lines)} lines, Run2={len(r2_lines)} lines")

# === COMPARISON TABLE ===
print(f"\n{'=' * 65}")
print(f"  COMPARISON: Monolithic vs Incremental (Run 1 / Run 2)")
print(f"{'=' * 65}")


# Format helpers
def fmt_tok(v):
    if isinstance(v, int):
        return str(v)
    try:
        return str(int(v))
    except:
        return str(v)


def fmt_cost(v):
    return f"${v:.4f}" if v else "$0.0000"


def fmt_time(v):
    return f"{v:.1f}s" if v else "N/A"


print(f"\n{'Metric':<30} {'Monolithic':<20} {'Incremental R1':<20} {'Incremental R2':<20}")
print(f"{'-' * 30} {'-' * 20} {'-' * 20} {'-' * 20}")

# Pick monolithic reference based on which provider won
ref_providers = ["NVIDIA", "DeepSeek V4 Flash", "Cerebras"]
mono_provider = None
for p in ref_providers:
    if att_1.get("provider") == p or att_2.get("provider") == p:
        # Use the same provider for comparison
        pass
mono_provider = agg_provider_1 if agg_provider_1 in ref_costs else "NVIDIA"
mono = ref_costs.get(mono_provider, {"tokens": "?", "cost": 0, "time": "?"})

print(f"{'Provider':<30} {mono_provider:<20} {agg_provider_1:<20} {agg_provider_2:<20}")

# Total tokens (per-game + aggregate)
r1_tok = f"{total_per_game_tokens} + {fmt_tok(agg_tokens_1)} = {run_1_total_tokens}"
r2_tok = f"0 + {fmt_tok(agg_tokens_2)} = {fmt_tok(agg_tokens_2)}"
print(f"{'Total tokens':<30} {fmt_tok(mono['tokens']):<20} {r1_tok:<20} {r2_tok:<20}")

print(
    f"{'LLM cost':<30} {fmt_cost(mono['cost']):<20} {fmt_cost(run_1_total_cost):<20} {fmt_cost(agg_cost_2):<20}"
)
print(
    f"{'Pipeline time':<30} {fmt_time(mono['time']):<20} {fmt_time(t_total_1):<20} {fmt_time(t_total_2):<20}"
)

# Per-game breakdown
print(f"\n  Per-game LLM calls:")
print(f"  {'Game':<15} {'Run1 tok':<12} {'Run1 cost':<14} {'Run1 time':<12} {'Run2 time':<12}")
for g in per_game_log:
    g2 = next((x for x in per_game_log_2 if x["game_id"] == g["game_id"]), {})
    print(
        f"  {g['game_id']:<15} {fmt_tok(g['tokens']):<12} {fmt_cost(g['cost']):<14} {fmt_time(g['time']):<12} {fmt_time(g2.get('time', 0)):<12}"
    )

# Token savings projection
print(f"\n  PROJECTION: 50 games + 10 new")
old_50 = 50 * (mono["tokens"] if isinstance(mono["tokens"], int) else 2500)
old_10_new = 60 * (mono["tokens"] if isinstance(mono["tokens"], int) else 2500)
incr_50 = 50 * (
    per_game_log[0]["tokens"] if isinstance(per_game_log[0]["tokens"], int) else 1300
) + (agg_tokens_1 if isinstance(agg_tokens_1, int) else 3000)
incr_10_new = (
    10 * (per_game_log[0]["tokens"] if isinstance(per_game_log[0]["tokens"], int) else 1300)
    + incr_50
)
print(f"  Monolithic 50 games: {old_50:,} tokens")
print(
    f"  Incremental 50 games: {incr_50:,} tokens (per-game {50 * 1300:,} + aggregate {agg_tokens_1})"
)
print(f"  Monolithic +10 new: {old_10_new:,} tokens (re-run all 60)")
print(
    f"  Incremental +10 new: {incr_10_new:,} tokens (10 per-game + 1 aggregate, reuses 50 cached)"
)

# Quality comparison
print(f"\n  QUALITY: Report length comparison")
print(f"  Monolithic (last NVIDIA): 39 lines, ~2600 tokens")
print(
    f"  Incremental Run 1: {len(report_1.strip().split(chr(10)))} lines, {run_1_total_tokens} total tokens"
)
print(
    f"  Incremental Run 2: {len(report_2.strip().split(chr(10)))} lines, {agg_tokens_2} aggregate tokens"
)

# Write report
print(f"\n  Writing differential analysis...")
from datetime import datetime, timezone

ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
path = os.path.join(
    os.path.dirname(__file__), "..", "docs", f"differential_analysis_mono_vs_incr_{ts}.md"
)
with open(path, "w", encoding="utf-8") as f:
    f.write(f"# Differential Analysis: Monolithic vs Incremental Pipeline\n\n")
    f.write(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  \n")
    f.write(f"**Games:** {len(game_ids)} (same data)  \n")
    f.write(f"**Reference monolithic:** {mono_provider}, {mono['tokens']} tokens  \n")
    f.write(f"**Incremental provider (R1):** {agg_provider_1}  \n")
    f.write(f"**Incremental provider (R2):** {agg_provider_2}  \n\n---\n\n")

    f.write("## Metrics Comparison\n\n")
    f.write("| Metric | Monolithic | Incremental R1 (cold) | Incremental R2 (warm) |\n")
    f.write("|---|---|---|---|\n")
    f.write(f"| Provider | {mono_provider} | {agg_provider_1} | {agg_provider_2} |\n")
    f.write(
        f"| Total tokens | {mono['tokens']} | {run_1_total_tokens} ({total_per_game_tokens} per-game + {agg_tokens_1} agg) | {agg_tokens_2} (0 per-game + {agg_tokens_2} agg) |\n"
    )
    f.write(f"| LLM cost | ${mono['cost']:.4f} | ${run_1_total_cost:.4f} | ${agg_cost_2:.4f} |\n")
    f.write(
        f"| Pipeline time | {mono.get('time', 0):.1f}s | {t_total_1:.1f}s | {t_total_2:.1f}s |\n"
    )
    f.write(
        f"| Report length | 39 lines | {len(report_1.strip().split(chr(10)))} lines | {len(report_2.strip().split(chr(10)))} lines |\n"
    )
    f.write(
        f"| Deterministic | N/A (single run) | Run1 baseline | {'YES' if report_1.strip() == report_2.strip() else 'NO'} |\n\n"
    )

    f.write("## Per-Game LLM Cache (cold run)\n\n")
    f.write("| Game | Tokens | Cost | Time |\n")
    f.write("|---|---|---|---|\n")
    for g in per_game_log:
        f.write(f"| {g['game_id']} | {g['tokens']} | ${g['cost']:.6f} | {g['time']:.1f}s |\n")
    f.write(
        f"| **Total** | **{total_per_game_tokens}** | **${total_per_game_cost:.6f}** | **{t_per_game:.1f}s** |\n\n"
    )

    f.write("## Cost/Time Projection\n\n")
    f.write(f"| Scenario | Monolithic | Incremental |\n")
    f.write("|---|---|---|\n")
    f.write(
        f"| 50 games (initial) | {old_50:,} tok, ~${50 * mono['cost']:.4f} | {incr_50:,} tok, ~${50 * per_game_log[0]['cost'] + agg_cost_1:.4f} |\n"
    )
    f.write(
        f"| +10 new games | {old_10_new:,} tok (re-run 60) | {incr_10_new:,} tok (10 per-game + aggregate) |\n"
    )
    incr_save = old_10_new - incr_10_new
    f.write(
        f"| Token savings on +10 | baseline | **{incr_save:,} tok saved** ({incr_save / old_10_new * 100:.0f}%) |\n\n"
    )

    f.write("## Report Quality\n\n")
    if report_1.strip() != report_2.strip():
        f.write("**Reports differ between runs** (non-deterministic LLM output).\n\n")
    else:
        f.write("**Reports identical** (deterministic LLM output across runs).\n\n")

    f.write("### Incremental Run 1 (first 20 lines)\n\n")
    f.write("```\n")
    f.write("\n".join(report_1.strip().split("\n")[:20]))
    f.write("\n```\n\n")

    f.write("### Incremental Run 2 (first 20 lines)\n\n")
    f.write("```\n")
    f.write("\n".join(report_2.strip().split("\n")[:20]))
    f.write("\n```\n")

print(f"  Written: {path}")
print(f"\n{'=' * 65}")
print(f"  DIFFERENTIAL ANALYSIS COMPLETE")
print(f"{'=' * 65}")
