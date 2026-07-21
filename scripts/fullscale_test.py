"""Full-scale comparison: monolithic vs incremental pipeline."""

import os, sys, json, time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["LLM_MAX_TOKENS"] = "4000"

# ── Load reference data ──────────────────────────────────────────────────
dump_path = os.path.join(os.path.dirname(__file__), "..", "data", "test_optimized_output.json")
with open(dump_path) as f:
    ref = json.load(f)

patterns = ref.get("patterns_detected", [])
weakness = ref.get("weakness_report", None)
games_list = ref.get("games_analyzed", [])
game_ids = [g["id"] for g in games_list]
game_colors = [g["color"] for g in games_list]

print(f"┌{'─' * 60}┐")
print(f"│  FULL-SCALE TEST:  {len(game_ids)} games  ({', '.join(game_ids)})")
print(f"│  Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
print(f"│  Patterns: {len(patterns)}  │  Weakness: {'yes' if weakness else 'no'}")
print(f"└{'─' * 60}┘")

# ── Cache status ──────────────────────────────────────────────────────────
cache_dir = os.path.join(os.path.dirname(__file__), "..", "data", "game_cache")
llm_cache_hits = 0
for gid in game_ids:
    path = os.path.join(cache_dir, f"{gid}_llm.json")
    if os.path.exists(path):
        llm_cache_hits += 1
print(f"\nLLM cache: {llm_cache_hits}/{len(game_ids)} games cached")
print(
    f"Stockfish cache: {len([f for f in os.listdir(cache_dir) if f.endswith('.json') and '_llm' not in f])} files"
)

# ── Import pipeline ──────────────────────────────────────────────────────
from lichess_analyzer_mcp.services.llm_client import run_coaching_pipeline

# ── 1. MONOLITHIC ─────────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print(f"  1. MONOLITHIC PIPELINE")
print(f"{'=' * 60}")

t0 = time.time()
mono_report, mono_log, mono_meta = run_coaching_pipeline(
    username="systeq",
    game_ids=game_ids,
    game_colors=game_colors,
    patterns=patterns,
    weakness_report=weakness,
    mode="mono",
)
mono_elapsed = time.time() - t0

mono_att = mono_log[-1] if mono_log else {}
mono_tok = mono_att.get("total_tokens", 0)
mono_prov = mono_att.get("provider", "?")
mono_lines = len(mono_report.strip().split("\n"))
mono_cost = mono_att.get("cost", 0)

print(f"  Provider:   {mono_prov}")
print(f"  Tokens:     {mono_tok}")
print(f"  Cost:       ${mono_cost}")
print(f"  Time:       {mono_elapsed:.1f}s")
print(f"  Report:     {mono_lines} lines")
print(f"  First line: {mono_report.strip().split(chr(10))[0][:80]}")

# ── 2. INCREMENTAL ────────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print(f"  2. INCREMENTAL PIPELINE (per-game LLM cache + aggregate)")
print(f"{'=' * 60}")

t0 = time.time()
inc_report, inc_log, inc_meta = run_coaching_pipeline(
    username="systeq",
    game_ids=game_ids,
    game_colors=game_colors,
    patterns=patterns,
    weakness_report=weakness,
    mode="incremental",
)
inc_elapsed = time.time() - t0

inc_att = inc_log[-1] if inc_log else {}
inc_tok = inc_att.get("total_tokens", 0)
inc_prov = inc_att.get("provider", "?")
inc_lines = len(inc_report.strip().split("\n"))
inc_cost = inc_att.get("cost", 0)

print(f"  Provider:       {inc_prov}")
print(f"  Aggregate tok:  {inc_tok}")
print(f"  Per-game tok:   {inc_meta['per_game_tokens']}")
print(f"  Total tok:      {inc_tok + inc_meta['per_game_tokens']}")
print(f"  Per-game calls: {inc_meta['per_game_calls']}")
print(f"  Cost:           ${inc_cost}")
print(f"  Time:           {inc_elapsed:.1f}s")
print(f"  Report:         {inc_lines} lines")
print(f"  First line:     {inc_report.strip().split(chr(10))[0][:80]}")

# ── 3. COMPARISON ──────────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print(f"  3. COMPARISON & ANALYSIS")
print(f"{'=' * 60}")

# Cold incremental = no cache (simulate by counting per-game calls that actually hit API)
total_inc = inc_tok + inc_meta["per_game_tokens"]
tok_diff = total_inc - mono_tok
tok_ratio = total_inc / mono_tok if mono_tok else 0
time_diff = inc_elapsed - mono_elapsed

print(f"\n  TOKEN COMPARISON:")
print(f"    Monolithic:       {mono_tok:>6} tokens")
print(
    f"    Incremental:      {total_inc:>6} tokens (agg {inc_tok} + per-game {inc_meta['per_game_tokens']})"
)
print(f"    Difference:       {tok_diff:+>6} tokens ({tok_ratio:.1f}x)")
print(f"    Verdict:          {'MONO wins' if tok_diff > 0 else 'INCR wins'} for N={len(game_ids)}")

print(f"\n  TIME COMPARISON:")
print(f"    Monolithic:       {mono_elapsed:>6.1f}s")
print(f"    Incremental:      {inc_elapsed:>6.1f}s")
print(f"    Difference:       {time_diff:+>6.1f}s")
print(f"    Verdict:          {'MONO faster' if time_diff > 0 else 'INCR faster'}")

print(f"\n  COST COMPARISON:")
print(f"    Monolithic:       ${mono_cost}")
print(f"    Incremental:      ${inc_cost}")
print(
    f"    Verdict:          {'Equal' if mono_cost == inc_cost else 'MONO cheaper' if mono_cost <= inc_cost else 'INCR cheaper'}"
)

print(f"\n  QUALITY COMPARISON:")
print(f"    Mono report:      {mono_lines} lines")
print(f"    Incr report:      {inc_lines} lines")
print(
    f"    Same provider:    {'YES' if mono_prov == inc_prov else f'NO ({mono_prov} vs {inc_prov})'}"
)

# LLM output diff summary
print(f"\n  OUTPUT DIFF (first 100 chars of each section):")
mono_sections = mono_report.strip().split("\n## ")
inc_sections = inc_report.strip().split("\n## ")
print(f"    Mono sections:    {len(mono_sections)}")
print(f"    Incr sections:    {len(inc_sections)}")

# ── 4. RECOMMENDATION ──────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print(f"  4. RECOMMENDATION")
print(f"{'=' * 60}")

if tok_diff > 0 and time_diff > 0:
    rec = "MONOLITHIC"
    reason = f"N={len(game_ids)} je pod crossover pointem (~30). Monolit je {tok_ratio:.1f}x méne tokenů a {abs(time_diff):.1f}s rychlejsí."
elif tok_diff <= 0 and time_diff <= 0:
    rec = "INCREMENTAL"
    reason = f"N={len(game_ids)} uz presahlo crossover point. Inkremental je {tok_ratio:.1f}x méne tokenů a {abs(time_diff):.1f}s rychlejsí."
else:
    rec = "TRADE-OFF"
    reason = f"Tokeny preferují {'mono' if tok_diff > 0 else 'incr'}, cas preferuje {'mono' if time_diff > 0 else 'incr'}."

print(f"  Recommended:  {rec}")
print(f"  Reason:       {reason}")

# Projection for large N
print(f"\n  PROJECTION for N=100:")
n_proj = 100
per_game_proj = 1300 * n_proj  # ~1300 tok/game
agg_proj = 3800  # aggregate ~3800 tok
mono_proj = 2600 + (n_proj - 5) * 2500  # rough linear extrapolation
inc_total_proj = per_game_proj + agg_proj
savings = mono_proj - inc_total_proj
print(f"    Mono tokens:      {mono_proj:>8}")
print(f"    Incr tokens:      {inc_total_proj:>8}")
print(f"    Savings:          {savings:>8} ({savings / mono_proj * 100:.0f}%)")
print(f"    Verdict:          {'INCR wins at scale' if savings > 0 else 'MONO wins at scale'}")

# Save comparison
result = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "games": game_ids,
    "n_games": len(game_ids),
    "monolithic": {
        "provider": mono_prov,
        "tokens": mono_tok,
        "cost": mono_cost,
        "time_s": round(mono_elapsed, 1),
        "lines": mono_lines,
    },
    "incremental": {
        "provider": inc_prov,
        "aggregate_tokens": inc_tok,
        "per_game_tokens": inc_meta["per_game_tokens"],
        "total_tokens": total_inc,
        "cost": inc_cost,
        "time_s": round(inc_elapsed, 1),
        "lines": inc_lines,
        "per_game_calls": inc_meta["per_game_calls"],
    },
    "comparison": {
        "token_diff": tok_diff,
        "token_ratio": round(tok_ratio, 2),
        "time_diff": round(time_diff, 1),
        "recommendation": rec,
        "reason": reason,
    },
    "projection_n100": {
        "mono_tokens": mono_proj,
        "incr_tokens": inc_total_proj,
        "savings": savings,
        "savings_pct": round(savings / mono_proj * 100, 0),
    },
}

out_path = os.path.join(
    os.path.dirname(__file__),
    "..",
    "docs",
    f"fullscale_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\n  Saved to: {out_path}")
print(f"{'=' * 60}")
