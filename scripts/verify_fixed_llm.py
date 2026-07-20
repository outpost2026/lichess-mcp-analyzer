"""Verify fixed per-game LLM output quality."""

import os, sys, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["LLM_MAX_TOKENS"] = "4000"

# Clear the old LLM cache to force regeneration with fixed data
cache_dir = os.path.join(os.path.dirname(__file__), "..", "data", "game_cache")
for fname in os.listdir(cache_dir):
    if fname.endswith("_llm.json"):
        os.remove(os.path.join(cache_dir, fname))
        print(f"  Removed old: {fname}")

from src.services.game_llm_cache import analyze_game_llm
from src.services.llm_client import run_coaching_pipeline

game_ids = ["MtEGzuvx", "qmodxzNF", "BAEXAHoW", "AczKbLug", "9PSKkXvK"]
game_colors = ["white", "black", "black", "white", "black"]

print(f"\n{'=' * 60}")
print("  PER-GAME LLM ANALYSIS (after fix)")
print(f"{'=' * 60}")
for gid, col in zip(game_ids, game_colors):
    result = analyze_game_llm(gid, col)
    output = result.get("llm_output", "") if result else ""
    tok = result.get("token_log", {}).get("total_tokens", "?")
    print(f"\n  [{gid}] Tokens: {tok}")
    print(f"  Output (first 300 chars):")
    for line in output.strip().split("\n")[:6]:
        print(f"    {line[:120]}")
