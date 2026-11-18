"""Compare NVIDIA vs DeepSeek V4 Flash coaching report quality on same data."""

import os, sys, json, time, traceback
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

NVIDIA_KEY = os.environ.get("NVIDIA_API_KEY", "")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

print("=" * 60)
print("  LLM PROVIDER COMPARISON — NVIDIA vs DeepSeek V4 Flash")
print("=" * 60)

# Step 1: Load cached pipeline data
print("\n[1/4] Loading cached analysis data...")
dump_path = os.path.join(os.path.dirname(__file__), "..", "data", "test_optimized_output.json")
if os.path.exists(dump_path):
    with open(dump_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    patterns = data.get("patterns_detected", data.get("patterns", data.get("pattern_results", [])))
    weakness = data.get("weakness_report", data.get("weakness", None))
    games_list = data.get("games_analyzed", [])
    games_analyzed_count = len(games_list)
    games_summary = data.get("games_summary", {})
    print(f"  Loaded from: {dump_path}")
else:
    from lichess_analyzer_mcp.services.pattern_detector import PatternDetector
    from lichess_analyzer_mcp.services.diagnostician import diagnose
    from lichess_analyzer_mcp.services.analyzer import analyze_game
    import glob as glob_mod

    cache_dir = os.path.join(os.path.dirname(__file__), "..", "data", "game_cache")
    cache_files = glob_mod.glob(os.path.join(cache_dir, "*.json"))
    analyses = []
    for cf in sorted(cache_files)[:5]:
        with open(cf, "r", encoding="utf-8") as f:
            jd = json.load(f)

        class GameObj:
            pass

        class AnalysisResult:
            pass

        g = GameObj()
        g.id = jd.get("game_id", os.path.splitext(os.path.basename(cf))[0])
        g.color = jd.get("color", "white")
        g.result = jd.get("result", "*")
        g.opening = jd.get("opening", {})
        g.players = jd.get("players", {})
        a = AnalysisResult()
        a.game = g
        a.moves = jd.get("moves", [])
        a.blunders = jd.get("blunders", [])
        a.mistakes = jd.get("mistakes", [])
        a.inaccuracies = jd.get("inaccuracies", [])
        a.total_acpl = jd.get("total_acpl", 0)
        a.phase_acpl = jd.get("phase_acpl", {})
        analyses.append(a)
    metadata = {"username": "systeq", "total_games": len(analyses)}
    detector = PatternDetector()
    matches = detector.detect_all(analyses, metadata)
    from lichess_analyzer_mcp.services.compressibility_validator import compute_compression

    patterns = []
    for m in matches:
        pdef = detector.library.patterns.get(m.pattern_id)
        comp = compute_compression(m, analyses)
        entry = {
            "pattern_id": m.pattern_id,
            "pattern_name": m.pattern_name,
            "confidence": round(m.confidence * 100, 0),
            "frequency": m.frequency,
            "severity": m.severity,
            "evidence": m.evidence,
            "mitigation": pdef.mitigation if pdef else "",
        }
        if m.hypothesis:
            entry["hypothesis"] = m.hypothesis
        if comp.compression_ratio is not None:
            entry["compression_ratio"] = comp.compression_ratio
        patterns.append(entry)
    wr = diagnose(analyses, "systeq")
    weakness = {
        "total_acpl": round(wr.total_acpl, 1),
        "blunder_count": wr.blunder_count,
        "mistake_count": wr.mistake_count,
        "inaccuracy_count": wr.inaccuracy_count,
        "phase_weaknesses": wr.phase_weaknesses,
        "leaky_openings": wr.leaky_openings,
        "top_weaknesses": wr.top_weaknesses,
    }
    games = {"analyzed": len(analyses)}

print(f"  Games: {games_analyzed_count}")
print(f"  Patterns: {len(patterns)}")
print(f"  Weakness ACPL: {weakness.get('total_acpl', '?') if weakness else 'N/A'}")

# Step 2: Build prompt (same for both)
from lichess_analyzer_mcp.services.llm_client import (
    build_coaching_prompt,
    COACHING_SYSTEM_PROMPT,
    _call_llm,
    PROVIDERS,
)

user_prompt = build_coaching_prompt("systeq", games_analyzed_count, patterns, weakness)
prompt_chars = len(user_prompt) + len(COACHING_SYSTEM_PROMPT)
print(f"\n  Prompt size: {prompt_chars} chars (~{prompt_chars // 4} tokens)")

# Step 3: Call both providers
PROVIDERS_CFG = {
    "NVIDIA": next(p for p in PROVIDERS if p["name"] == "NVIDIA"),
    "DeepSeek V4 Flash": next(p for p in PROVIDERS if p["name"] == "DeepSeek V4 Flash"),
}

results = {}
for name, cfg in PROVIDERS_CFG.items():
    print(f"\n[2/4] Calling {name}...")
    key = os.environ.get(cfg["api_key_var"], "")
    if not key:
        print(f"  SKIP: no API key for {name}")
        continue
    t0 = time.time()
    content, log = _call_llm(COACHING_SYSTEM_PROMPT, user_prompt, cfg)
    elapsed = time.time() - t0
    if content:
        tokens = log.get("total_tokens", "?")
        cost = log.get("cost_usd", 0)
        print(f"  OK: {tokens} tokens, ${cost:.6f}, {elapsed:.1f}s")
        results[name] = {"content": content, "log": log, "elapsed": elapsed}
    else:
        print(f"  FAIL: {log.get('error', 'unknown')} ({elapsed:.1f}s)")

# Step 4: Write reports + comparison
print(f"\n[3/4] Writing comparison...")
docs_dir = os.path.join(os.path.dirname(__file__), "..", "docs")
ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

# Individual reports
for name, r in results.items():
    slug = name.lower().replace(" ", "_")
    path = os.path.join(docs_dir, f"coaching_report_systeq_{slug}_{ts}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Coaching Report: systeq ({name})\n\n")
        f.write(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  \n")
        f.write(f"**Provider:** {name}  \n")
        f.write(f"**Model:** {r['log'].get('model', '?')}  \n")
        f.write(f"**Tokens:** {r['log'].get('total_tokens', '?')}  \n")
        f.write(f"**Cost:** ${r['log'].get('cost_usd', 0):.6f}  \n")
        f.write(f"**Time:** {r['elapsed']:.1f}s  \n\n")
        f.write("---\n\n")
        f.write(r["content"])
    print(f"  Written: {path}")

# Comparison matrix
if len(results) == 2:
    comp_path = os.path.join(docs_dir, f"comparison_nvidia_vs_deepseek4_{ts}.md")
    with open(comp_path, "w", encoding="utf-8") as f:
        f.write("# Provider Comparison: NVIDIA vs DeepSeek V4 Flash\n\n")
        f.write(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  \n")
        f.write(f"**Data:** 5 cached game analyses (systeq)  \n")
        f.write(f"**Prompt:** {prompt_chars} chars  \n\n")

        f.write("## Metrics\n\n")
        f.write("| Metric | NVIDIA | DeepSeek V4 Flash |\n")
        f.write("|--------|--------|-------------------|\n")
        for name, r in results.items():
            r["_label"] = "NVIDIA" if "NVIDIA" in name else "DeepSeek V4 Flash"
        nv = results.get("NVIDIA", {})
        ds = results.get("DeepSeek V4 Flash", {})
        f.write(
            f"| Model | {nv.get('log', {}).get('model', '?')} | {ds.get('log', {}).get('model', '?')} |\n"
        )
        f.write(
            f"| Total tokens | {nv.get('log', {}).get('total_tokens', '?')} | {ds.get('log', {}).get('total_tokens', '?')} |\n"
        )
        f.write(
            f"| Cost | ${nv.get('log', {}).get('cost_usd', 0):.6f} | ${ds.get('log', {}).get('cost_usd', 0):.6f} |\n"
        )
        f.write(
            f"| Response time | {nv.get('elapsed', 0):.1f}s | {ds.get('elapsed', 0):.1f}s |\n\n"
        )

        f.write("## Report structure comparison\n\n")
        for name, r in results.items():
            short = "NVIDIA" if "NVIDIA" in name else "DeepSeek V4"
            f.write(f"### {short}\n\n")
            f.write(f"```\n{r['content'][:2000]}\n```\n\n")

    print(f"  Written: {comp_path}")

print(f"\n[4/4] Summary")
for name, r in results.items():
    print(
        f"  {name:25s}: {r['log'].get('total_tokens', '?'):>5} tokens, ${r['log'].get('cost_usd', 0):.6f}, {r['elapsed']:.1f}s"
    )
missing = [n for n in PROVIDERS_CFG if n not in results]
if missing:
    print(f"  FAILED: {', '.join(missing)}")
print("=" * 60)
