"""
Optimized pipeline test: 5 games, cache-first, LLM cascade, MD output.

Key mitigations for slow 5G (2mb DL):
1. Use cached analyses whenever possible (data/game_cache/)
2. Only fetch PGN from Lichess API for uncached games
3. Parallel analysis with ThreadPoolExecutor
4. Profile timing per phase to identify bottlenecks
5. Cache Lichess game list to avoid redundant API calls
"""

import os
import sys
import json
import time
import traceback
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# ── Inject API keys ────────────────────────────────────────────────────────
os.environ.setdefault("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b")
os.environ.setdefault("CEREBRAS_MODEL", "llama3.1-8b")
os.environ.setdefault("DEEPSEEK_MODEL", "deepseek-chat")
os.environ.setdefault("DEEPSEEK_V4_MODEL", "deepseek-v4-flash")

# Load .env for LICHESS_TOKEN
ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.isfile(ENV_PATH):
    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# ── Timing ─────────────────────────────────────────────────────────────────
_timers = {}


def tic(label: str):
    _timers[label] = time.time()


def toc(label: str) -> float:
    return time.time() - _timers.get(label, 0)


# ── Logging ────────────────────────────────────────────────────────────────
anomalies = []


def log_anomaly(severity: str, source: str, msg: str, detail: str = ""):
    anomalies.append(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "severity": severity,
            "source": source,
            "msg": msg,
            "detail": detail,
        }
    )
    print(f"  [{severity}] {source}: {msg}")


def section(title):
    print(f"\n{'─' * 60}\n  {title}\n{'─' * 60}")


# ═══════════════════════════════════════════════════════════════════════════
section(f"OPTIMIZED PIPELINE TEST — systeq (5 games)")
print(f"  Started: {datetime.now(timezone.utc).isoformat()}")
print(f"  Connection: 5G (2mb DL) — cache-first strategy")
tic("total")

# ── Step 1: LLM status ────────────────────────────────────────────────────
section("[1/6] LLM provider check")
from src.services.llm_client import get_llm_status, generate_coaching_report_with_logs

status = get_llm_status()
print(f"  Configured: {status['total_configured']}")
for p in status["available"]:
    print(f"    ✅ {p['provider']}: model={p['model']}")
if not status["active_provider"]:
    log_anomaly("error", "init", "No API key — cascade will fail")

# ── Step 2: Fetch game list ──────────────────────────────────────────────
section("[2/6] Fetch game list from Lichess")
tic("fetch_list")
from src.services.lichess_client import fetch_user_games

try:
    games_data = fetch_user_games("systeq", max_games=5)
    print(f"  Fetched {len(games_data)} game IDs from Lichess API")
except Exception as e:
    log_anomaly("error", "lichess_api", f"Fetch failed: {e}", traceback.format_exc())
    sys.exit(1)
t_fetch_list = toc("fetch_list")
print(f"  Time: {t_fetch_list:.1f}s")

# ── Step 3: Cache-first analysis ─────────────────────────────────────────
section("[3/6] Cache-first analysis")
tic("analysis")
from src.services.game_analyzer import analyze_pgn, _load_cached_analysis
from src.services.lichess_client import fetch_game_pgn
from src.models.game import GameAnalysis

analyses = []
game_cache_status = {"total": len(games_data), "new": 0, "cached": 0}
analysis_details = []


def process_game(g):
    game_id = g.get("id", "")
    color = (
        "black"
        if g.get("players", {}).get("black", {}).get("user", {}).get("name", "").lower() == "systeq"
        else "white"
    )
    depth = 12

    # Try cache first
    cached = _load_cached_analysis(game_id, depth, color)
    if cached is not None:
        return cached, True

    # Fetch + analyze
    try:
        pgn = fetch_game_pgn(game_id)
        if not pgn or len(pgn) < 20:
            log_anomaly("warning", "pgn", f"Game {game_id}: short PGN ({len(pgn or '')} chars)")
            return None, False
        analysis = analyze_pgn(
            pgn, player_color=color, depth=depth, game_id=game_id, use_cache=True
        )
        return analysis, False
    except Exception as e:
        log_anomaly("error", "analyze", f"Game {game_id}: {e}", traceback.format_exc())
        return None, False


with ThreadPoolExecutor(max_workers=4) as pool:
    futures = [pool.submit(process_game, g) for g in games_data]
    for f in as_completed(futures):
        result, from_cache = f.result()
        if result:
            analyses.append(result)
            if from_cache:
                game_cache_status["cached"] += 1
            else:
                game_cache_status["new"] += 1
            analysis_details.append(
                {
                    "id": result.game.id,
                    "color": result.game.color,
                    "opening": result.game.opening,
                    "result": result.game.result,
                    "acpl": round(result.total_acpl, 1),
                    "blunders": len(result.blunders),
                    "moves": len(result.moves),
                    "from_cache": from_cache,
                }
            )
            src = "cache" if from_cache else "API"
            print(
                f"    {'📦' if from_cache else '🌐'} {result.game.id} ({result.game.color}): ACPL={result.total_acpl:.1f}, "
                f"blunders={len(result.blunders)}, moves={len(result.moves)} [{src}]"
            )

t_analysis = toc("analysis")
print(
    f"\n  Analyzed: {len(analyses)}/{len(games_data)} ({game_cache_status['cached']} cache, {game_cache_status['new']} new)"
)
print(f"  Time: {t_analysis:.1f}s")

if len(analyses) < 2:
    log_anomaly("error", "pipeline", "Insufficient games")
    sys.exit(1)

# ── Step 4: Pattern detection ──────────────────────────────────────────────
section("[4/6] Pattern detection")
tic("patterns")
from src.services.pattern_detector import PatternDetector
from src.services.diagnostician import diagnose
from src.services.compressibility_validator import compute_compression

metadata = {"username": "systeq", "total_games": len(analyses)}
detector = PatternDetector()
try:
    matches = detector.detect_all(analyses, metadata)
except Exception as e:
    log_anomaly("error", "pattern", f"detect_all failed: {e}", traceback.format_exc())
    matches = []

pattern_results = []
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
    pattern_results.append(entry)

t_patterns = toc("patterns")
print(f"  Detected: {len(pattern_results)}")
for p in pattern_results:
    print(
        f"    [{p['severity'].upper()}] {p['pattern_id']}: {p['pattern_name']} (conf={p['confidence']}%, freq={p['frequency']})"
    )
print(f"  Time: {t_patterns:.1f}s")

# Weakness report
tic("diagnose")
wr_dict = None
try:
    wr = diagnose(analyses, "systeq")
    wr_dict = {
        "total_acpl": round(wr.total_acpl, 1),
        "blunder_count": wr.blunder_count,
        "mistake_count": wr.mistake_count,
        "inaccuracy_count": wr.inaccuracy_count,
        "phase_weaknesses": wr.phase_weaknesses,
        "leaky_openings": wr.leaky_openings,
        "top_weaknesses": wr.top_weaknesses,
    }
    print(f"\n  Weakness: ACPL={wr_dict['total_acpl']}, blunders={wr_dict['blunder_count']}")
except Exception as e:
    log_anomaly("error", "diagnose", f"Failed: {e}", traceback.format_exc())
t_diag = toc("diagnose")

# ── Step 5: LLM cascade ────────────────────────────────────────────────────
section("[5/6] LLM cascade: NVIDIA -> Cerebras -> DeepSeek V4 Flash")
tic("llm")

report, cascade_log = generate_coaching_report_with_logs(
    username="systeq",
    games_analyzed=len(analyses),
    patterns=pattern_results,
    weakness_report=wr_dict,
    cascade_order=["NVIDIA", "Cerebras", "DeepSeek V4 Flash"],
)

t_llm = toc("llm")
print(f"\n  Cascade ({len(cascade_log)} attempts):")
for att in cascade_log:
    if att.get("error"):
        print(f"    ❌ {att['provider']}: {att['error'][:80]}")
    else:
        print(
            f"    ✅ {att['provider']}: {att.get('total_tokens', '?')} tokens, ${att.get('cost_usd', 0):.6f}"
        )

# Print LLM output
success_idx = None
for i, att in enumerate(cascade_log):
    if not att.get("error"):
        success_idx = i
        break

print(f"\n  ── LLM Output ──")
if success_idx is not None:
    print(
        f"  (provider: {cascade_log[success_idx]['provider']}, "
        f"tokens: {cascade_log[success_idx].get('total_tokens', '?')})"
    )
else:
    print(f"  (fallback — no provider succeeded)")
print(f"\n{report}")

# ── Step 6: Write MD report ────────────────────────────────────────────────
section("[6/6] Write MD report to ./docs")
tic("md_write")
from src.kb.md_reporter import generate_md_report, write_md_report

timing = {
    "total": {"duration": toc("total"), "label": "Total"},
    "fetch_list": {"duration": t_fetch_list, "label": "Fetch game list (Lichess API)"},
    "analysis": {"duration": t_analysis, "label": "Game analysis (cache + new)"},
    "patterns": {"duration": t_patterns, "label": "Pattern detection"},
    "diagnose": {"duration": t_diag, "label": "Weakness diagnosis"},
    "llm": {"duration": t_llm, "label": "LLM cascade"},
}

games_data_dict = {
    "total": game_cache_status["total"],
    "new": game_cache_status["new"],
    "cached": game_cache_status["cached"],
}
analyses_data_dict = {"analyzed": len(analyses), "games": analysis_details}

md = generate_md_report(
    username="systeq",
    games_data=games_data_dict,
    analyses_data=analyses_data_dict,
    pattern_results=pattern_results,
    weakness_report=wr_dict,
    llm_report=report,
    cascade_log=cascade_log,
    timing=timing,
    anomalies=anomalies,
)

path = write_md_report(md, "systeq")
print(f"  Written: {path}")

t_total = toc("total")

# ── Summary ────────────────────────────────────────────────────────────────
section("SUMMARY")
print(
    f"  Games:           {game_cache_status['total']} ({game_cache_status['cached']} cache, {game_cache_status['new']} new)"
)
print(f"  Patterns:        {len(pattern_results)}")
success_prov = next((a for a in cascade_log if not a.get("error")), None)
if success_prov:
    print(
        f"  LLM:             ✅ {success_prov['provider']} ({success_prov.get('total_tokens', '?')} tokens, ${success_prov.get('cost_usd', 0):.6f})"
    )
else:
    print(f"  LLM:             ❌ fallback (all providers failed)")
print(f"  Total time:      {t_total:.1f}s")
print(f"  Anomalies:       {len(anomalies)}")
for a in anomalies:
    print(f"    [{a['severity']}] {a['source']}: {a['msg']}")

# Save full dump
output = {
    "test_date": datetime.now(timezone.utc).isoformat(),
    "username": "systeq",
    "games_summary": game_cache_status,
    "games_analyzed": analysis_details,
    "patterns_detected": pattern_results,
    "weakness_report": wr_dict,
    "cascade_log": cascade_log,
    "llm_report": report,
    "timing_seconds": {k: v["duration"] for k, v in timing.items()},
    "anomalies": anomalies,
    "md_output_path": path,
}
out_path = os.path.join(REPO_ROOT, "data", "test_optimized_output.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\n  Full dump: {out_path}")

print(f"\n{'=' * 60}")
print(f"  TEST COMPLETE ({t_total:.1f}s)")
print(f"{'=' * 60}")
