"""Verify all 3 free providers work end-to-end from cache."""

import os, sys, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["LLM_MAX_TOKENS"] = "4000"

dump_path = os.path.join(os.path.dirname(__file__), "..", "data", "test_optimized_output.json")
with open(dump_path, "r", encoding="utf-8") as f:
    data = json.load(f)

patterns = data.get("patterns_detected", [])
weakness = data.get("weakness_report", None)
games_count = len(data.get("games_analyzed", []))

from lichess_analyzer_mcp.services.llm_client import generate_coaching_report_with_logs

results = {}
for provider_name, env_var, model_var, model_val in [
    ("NVIDIA", "NVIDIA_API_KEY", "NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    ("Cerebras", "CEREBRAS_API_KEY", "CEREBRAS_MODEL", "gpt-oss-120b"),
    ("DeepSeek V4 Flash", "DEEPSEEK_API_KEY", "DEEPSEEK_V4_MODEL", "deepseek-v4-flash"),
]:
    key = os.environ.get(env_var, "")
    if not key:
        print(f"  SKIP {provider_name}: no API key")
        continue
    os.environ[model_var] = model_val
    report, log = generate_coaching_report_with_logs(
        username="systeq",
        games_analyzed=games_count,
        patterns=patterns,
        weakness_report=weakness,
        cascade_order=[provider_name],
    )
    att = log[-1] if log else {}
    err = att.get("error")
    results[provider_name] = {
        "ok": not err,
        "tokens": att.get("total_tokens", "?"),
        "cost": att.get("cost_usd", 0),
        "error": err,
    }
    if err:
        print(f"  ❌ {provider_name}: {err[:100]}")
    else:
        print(
            f"  ✅ {provider_name}: {att.get('total_tokens', '?')} tokens, ${att.get('cost_usd', 0):.6f}"
        )

print("\n=== SUMMARY ===")
for name, r in results.items():
    status = "OK" if r["ok"] else "FAIL"
    print(
        f"  {status} {name:25s}: {r['tokens']} tokens, ${r['cost']:.6f}"
        + (f" — {r['error'][:60]}" if r.get("error") else "")
    )
