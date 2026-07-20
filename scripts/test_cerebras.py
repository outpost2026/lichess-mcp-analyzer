"""Debug Cerebras gpt-oss-120b response and run pipeline."""

import os, sys, json, time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

KEY = os.environ.get("CEREBRAS_API_KEY", "")
import httpx

# Debug gpt-oss-120b response structure
model = "gpt-oss-120b"
print(f"Debug: {model}")
payload = {
    "model": model,
    "messages": [{"role": "user", "content": "Say exactly: OK"}],
    "max_tokens": 10,
}
r = httpx.post(
    "https://api.cerebras.ai/v1/chat/completions",
    headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"},
    json=payload,
    timeout=15.0,
)
print(f"Status: {r.status_code}")
data = r.json()
print(f"Keys: {list(data.keys())}")
if "choices" in data:
    print(f"Choices: {len(data['choices'])}")
    print(f"Choice[0] keys: {list(data['choices'][0].keys())}")
    msg = data["choices"][0].get("message", {})
    print(f"Message: {json.dumps(msg, ensure_ascii=False)[:200]}")
if "usage" in data:
    print(f"Usage: {data['usage']}")

# Now run the full pipeline with the working model
print(f"\n\nPipeline with {model}...")

# Set the model explicitly
os.environ["CEREBRAS_MODEL"] = model
os.environ["LLM_MAX_TOKENS"] = "4000"

from src.services.llm_client import (
    generate_coaching_report_with_logs,
)

dump_path = os.path.join(os.path.dirname(__file__), "..", "data", "test_optimized_output.json")
with open(dump_path, "r", encoding="utf-8") as f:
    data = json.load(f)

patterns = data.get("patterns_detected", [])
weakness = data.get("weakness_report", None)
games_list = data.get("games_analyzed", [])
games_count = len(games_list)

report, log = generate_coaching_report_with_logs(
    username="systeq",
    games_analyzed=games_count,
    patterns=patterns,
    weakness_report=weakness,
    cascade_order=["Cerebras"],
)

print(f"\nResult:")
for att in log:
    err = att.get("error")
    if err:
        print(f"  ❌ {att.get('provider', '?')}: {err[:150]}")
    else:
        print(
            f"  ✅ {att.get('provider', '?')}: {att.get('total_tokens', '?')} tokens, ${att.get('cost_usd', 0):.6f}"
        )

last = log[-1] if log else {}
if not last.get("error") and last.get("provider"):
    from datetime import datetime, timezone

    docs_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = os.path.join(docs_dir, f"coaching_report_systeq_cerebras_{ts}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Coaching Report: systeq (Cerebras)\n\n")
        f.write(f"**Model:** gpt-oss-120b  \n")
        f.write(f"**Tokens:** {last.get('total_tokens', '?')}  \n")
        f.write(f"**Cost:** ${last.get('cost_usd', 0):.6f}  \n\n---\n\n")
        f.write(report)
    print(f"\n  Written: {path}")
else:
    print(f"\n  (fallback output snippet):")
    print((report or "")[:500])
