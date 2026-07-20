"""Verify DEFAULT_PROVIDER env var switch."""

import os, sys, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["LLM_MAX_TOKENS"] = "100"

dump_path = os.path.join(os.path.dirname(__file__), "..", "data", "test_optimized_output.json")
with open(dump_path) as f:
    data = json.load(f)
patterns = data.get("patterns_detected", [])
weakness = data.get("weakness_report", None)
games_count = len(data.get("games_analyzed", []))

from src.services.llm_client import generate_coaching_report_with_logs

for name, env_val in [
    ("default (NVIDIA→Cerebras→DS)", ""),
    ("Cerebras→NVIDIA→DS", "cerebras"),
    ("DS V4→NVIDIA→Cerebras", "deepseek"),
]:
    if env_val:
        os.environ["DEFAULT_PROVIDER"] = env_val
    else:
        os.environ.pop("DEFAULT_PROVIDER", None)
    report, log = generate_coaching_report_with_logs("systeq", games_count, patterns, weakness)
    first = log[0] if log else {}
    print(
        f"  {name:40s} -> first: {first.get('provider', '?')} ({'OK' if not first.get('error') else first.get('error', '?')[:40]})"
    )
