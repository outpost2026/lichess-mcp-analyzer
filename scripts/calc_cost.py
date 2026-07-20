"""Quick cost projection for chess coaching via LLM."""

import json, os

prompt_tokens = 891  # from actual run (3565 chars / 4)

providers = {
    "NVIDIA (free)": {"input": 0.0, "output": 0.0},
    "DeepSeek V4 Flash": {"input": 0.14, "output": 0.28},
    "DeepSeek Chat": {"input": 0.27, "output": 1.10},
}

print("=" * 70)
print("  LLM COST PROJECTION — Chess Coaching Pipeline")
print("=" * 70)

print(f"\nBase: {prompt_tokens} input tokens, 2000 output tokens (typical game)")
print()

header = f"{'Provider':<25} {'$/game':<12} {'games/$1':<12} {'100 games':<12}"
print(header)
print("-" * 70)
for name, p in providers.items():
    cost = (prompt_tokens * p["input"] + 2000 * p["output"]) / 1_000_000
    games_per_dollar = 1 / cost if cost > 0 else float("inf")
    cost_100 = cost * 100
    gpd = "inf" if games_per_dollar == float("inf") else f"{games_per_dollar:,.0f}"
    c100 = "$0.00" if cost == 0 else f"${cost_100:.4f}"
    print(f"  {name:<25} ${cost:<10.6f} {gpd:<12} {c100:<12}")

print()
print("Actual run (DS V4 Flash, LLM_MAX_TOKENS=4000):")
print(f"  Total tokens: 3472, cost: $0.000847")
print(f"  Equivalent games/$1: {1 / 0.000847:,.0f}")
print()

# 50-game portfolio
print("-" * 70)
print("50-game portfolio cost (author's data scale):")
for name, p in providers.items():
    c = 50 * (prompt_tokens * p["input"] + 2000 * p["output"]) / 1_000_000
    c_str = "$0.00" if c == 0 else f"${c:.4f}"
    print(f"  {name:<25} {c_str:<12}")
print("=" * 70)
