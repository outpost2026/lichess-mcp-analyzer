"""
Test LLM reasoning layer: end-to-end test with real Lichess data.

1. Load .env for LICHESS_TOKEN
2. Fetch last N games for systeq
3. Run analyze_pgn + pattern detection
4. Generate coaching report via LLM layer
5. Log all anomalies, bugs, edge cases
"""

import os
import sys
import json
import traceback
from datetime import datetime

# ── Load .env manually (no python-dotenv dep) ──────────────────────────────
ENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.isfile(ENV_PATH):
    with open(ENV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    print(f"[.env] loaded from {ENV_PATH}")
else:
    print(f"[.env] NOT FOUND at {ENV_PATH} — Lichess API may fail")

# ── Ensure repo root is on path ───────────────────────────────────────────
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# ── Anomaly log ────────────────────────────────────────────────────────────
anomalies = []


def log_anomaly(severity: str, source: str, msg: str, detail: str = ""):
    entry = {
        "ts": datetime.utcnow().isoformat(),
        "severity": severity,
        "source": source,
        "message": msg,
        "detail": detail,
    }
    anomalies.append(entry)
    print(f"  [{severity}] {source}: {msg}")


print("=" * 70)
print("LLM REASONING LAYER TEST — systeq")
print(f"Started: {datetime.utcnow().isoformat()}")
print("=" * 70)

# ── Step 1: LLM provider status ───────────────────────────────────────────
print("\n[1/5] LLM provider status...")
from src.services.llm_client import get_llm_status, is_llm_available, generate_coaching_report

status = get_llm_status()
print(f"  Providers configured: {status['total_configured']}")
for p in status["available"]:
    print(f"    - {p['provider']}: model={p['model']}, key={'yes' if p['key_set'] else 'no'}")
print(f"  Active: {status['active_provider']}")
if not status["active_provider"]:
    log_anomaly("info", "llm_client", "No API key configured — will use fallback report")

# ── Step 2: Fetch games ───────────────────────────────────────────────────
print("\n[2/5] Fetching games for systeq...")
from src.services.lichess_client import fetch_user_games, fetch_game_pgn
from src.services.game_analyzer import analyze_pgn

try:
    games_data = fetch_user_games("systeq", max_games=20)
    print(f"  Fetched {len(games_data)} games from Lichess API")
except Exception as e:
    log_anomaly("error", "lichess_client", "Failed to fetch games", str(e))
    print(f"  ERROR: {e}")
    print("\nStopping test — cannot proceed without games.")
    sys.exit(1)

if len(games_data) == 0:
    log_anomaly(
        "warning",
        "lichess_client",
        "Zero games returned",
        "User may have no recent games or token issue",
    )
    print("  No games found. Cannot proceed.")
    sys.exit(1)

# ── Step 3: Analyze games ─────────────────────────────────────────────────
print(f"\n[3/5] Analyzing {len(games_data)} games (depth 12)...")
analyses = []
skipped = 0

for i, g in enumerate(games_data):
    game_id = g.get("id", f"unknown_{i}")
    try:
        # Determine player color
        color = "white"
        players = g.get("players", {})
        black_user = players.get("black", {}).get("user", {}).get("name", "").lower()
        if black_user == "systeq":
            color = "black"

        pgn = fetch_game_pgn(game_id)
        if not pgn or len(pgn) < 20:
            log_anomaly(
                "warning",
                "fetch_pgn",
                f"Game {game_id}: empty/short PGN (len={len(pgn) if pgn else 0})",
            )
            skipped += 1
            continue

        analysis = analyze_pgn(pgn, player_color=color, depth=12, game_id=game_id, use_cache=True)
        analyses.append(analysis)
        print(
            f"    [{i + 1}/{len(games_data)}] {game_id} ({color}): ACPL={analysis.total_acpl:.1f}, "
            f"blunders={len(analysis.blunders)}, moves={len(analysis.moves)}"
        )
    except Exception as e:
        log_anomaly("error", "analyze_pgn", f"Game {game_id} failed: {e}", traceback.format_exc())
        skipped += 1

print(f"\n  Analyzed: {len(analyses)}, Skipped: {skipped}")

if len(analyses) < 2:
    log_anomaly(
        "warning",
        "pipeline",
        f"Insufficient games analyzed ({len(analyses)}), min 2 needed for patterns",
    )
    print("  Not enough games. Cannot proceed.")
    sys.exit(1)

# ── Step 4: Pattern detection ─────────────────────────────────────────────
print(f"\n[4/5] Pattern detection on {len(analyses)} games...")
from src.services.pattern_detector import PatternDetector
from src.services.diagnostician import diagnose
from src.services.compressibility_validator import compute_compression

metadata = {"username": "systeq", "total_games": len(analyses)}
detector = PatternDetector()
try:
    matches = detector.detect_all(analyses, metadata)
except Exception as e:
    log_anomaly("error", "pattern_detector", "detect_all failed", traceback.format_exc())
    matches = []

print(
    f"  Raw matches before filters: {sum(1 for m in matches if m.frequency >= detector.library.patterns.get(m.pattern_id, type('', (), {'min_occurrences': 1})()).min_occurrences)}"
)

# Build result dicts (same format as match_patterns tool)
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

print(f"  Patterns detected: {len(pattern_results)}")
for p in pattern_results:
    print(
        f"    [{p['severity'].upper()}] {p['pattern_id']}: {p['pattern_name']} "
        f"(conf={p['confidence']}%, freq={p['frequency']})"
    )

# ── Weakness report ───────────────────────────────────────────────────────
print(f"\n  Generating weakness report...")
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
    print(f"    Total ACPL: {wr_dict['total_acpl']}")
    print(f"    Blunders: {wr_dict['blunder_count']}, Mistakes: {wr_dict['mistake_count']}")
    for w in wr_dict["top_weaknesses"]:
        print(f"    - {w}")
except Exception as e:
    log_anomaly("error", "diagnostician", "diagnose failed", traceback.format_exc())
    wr_dict = None

# ── Step 5: LLM Coaching Report ───────────────────────────────────────────
print(f"\n[5/5] Generating LLM coaching report...")
report = generate_coaching_report(
    username="systeq",
    games_analyzed=len(analyses),
    patterns=pattern_results,
    weakness_report=wr_dict,
)

print(f"\n{'=' * 70}")
print("COACHING REPORT")
print(f"{'=' * 70}\n")
print(report)
print(f"\n{'=' * 70}")

# ── Summary ───────────────────────────────────────────────────────────────
print(f"\n\nTEST SUMMARY")
print(f"{'=' * 70}")
print(f"  Games fetched:     {len(games_data)}")
print(f"  Games analyzed:    {len(analyses)}")
print(f"  Games skipped:     {skipped}")
print(f"  Patterns detected: {len(pattern_results)}")
print(f"  LLM active:        {is_llm_available()}")
print(f"  LLM provider:      {status['active_provider']}")
print(f"  Anomalies:         {len(anomalies)}")
for a in anomalies:
    print(f"    [{a['severity']}] {a['source']}: {a['message']}")
    if a["detail"]:
        print(f"      detail: {a['detail'][:200]}")

# ── Dump raw output to file ───────────────────────────────────────────────
output = {
    "test_date": datetime.utcnow().isoformat(),
    "username": "systeq",
    "games_fetched": len(games_data),
    "games_analyzed": len(analyses),
    "games_skipped": skipped,
    "llm_provider": status["active_provider"],
    "patterns_detected": pattern_results,
    "weakness_report": wr_dict,
    "coaching_report": report,
    "anomalies": anomalies,
}
out_path = os.path.join(REPO_ROOT, "data", "test_llm_layer_output.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\n  Full output saved to: data/test_llm_layer_output.json")

print(f"\n{'=' * 70}")
print("TEST COMPLETE")
print(f"{'=' * 70}")
