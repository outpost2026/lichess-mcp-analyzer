"""
Test LLM reasoning layer: 2-game cascade test with token logging.

1. Load .env for LICHESS_TOKEN
2. Inject API keys: NVIDIA (free) -> Cerebras (free) -> DeepSeek (paid)
3. Fetch last 2 games for systeq
4. Run pipeline (analyze + pattern detection)
5. Cascade LLM providers with full token logging
6. Log ALL inputs/outputs/anomalies
"""

import os
import sys
import json
import traceback
from datetime import datetime, timezone

# ── Inject API keys ────────────────────────────────────────────────────────
# Set these env vars before running:
#   NVIDIA_API_KEY, CEREBRAS_API_KEY, DEEPSEEK_API_KEY
# Models (cheapest/free first):
os.environ.setdefault("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b")
os.environ.setdefault("CEREBRAS_MODEL", "cerebras/llama3.1-8b")
os.environ.setdefault("DEEPSEEK_MODEL", "deepseek-chat")

# ── Load .env for LICHESS_TOKEN ───────────────────────────────────────────
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

SYSPROMPT_DISPLAY = """You are a chess coach analyzing a player's game data.
You are given DETERMINISTIC data from Stockfish analysis + pattern detection.
Your task is to produce a human-readable coaching report.

RULES (strict — never violate these):
1. DO NOT invent any evidence, patterns, or statistics not present in the data
2. DO NOT claim findings not supported by the data — use hedging language
3. You MAY group related patterns, prioritize by severity, and suggest training focus
4. Always structure output as: summary -> prioritized findings -> actionable recommendations
5. If data is ambiguous or insufficient, say so explicitly
6. Use plain language suitable for a club-level chess player (1200-1800 Elo)
7. NEVER say "you always" or "you never" — patterns are tendencies, not absolutes

Write in Czech."""

# ── Logger ────────────────────────────────────────────────────────────────
anomalies = []
llm_attempts = []


def log_anomaly(severity: str, source: str, msg: str, detail: str = ""):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "severity": severity,
        "source": source,
        "msg": msg,
        "detail": detail,
    }
    anomalies.append(entry)
    print(f"  [{severity}] {source}: {msg}")


def log_llm_attempt(
    provider: str,
    model: str,
    status: str,
    token_log: dict,
    input_preview: str = "",
    output_preview: str = "",
):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "model": model,
        "status": status,
        "token_log": token_log,
        "input_preview": input_preview[:300],
        "output_preview": output_preview[:300],
    }
    llm_attempts.append(entry)


def section(title):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


# ═══════════════════════════════════════════════════════════════════════════
section("LLM CASCADE TEST — systeq (2 games)")
print(f"  Started: {datetime.now(timezone.utc).isoformat()}")

# ── Step 1: LLM status ────────────────────────────────────────────────────
section("[1/6] LLM provider check")
from lichess_analyzer_mcp.services.llm_client import get_llm_status, generate_coaching_report_with_logs

status = get_llm_status()
print(f"  Configured: {status['total_configured']}")
for p in status["available"]:
    print(f"    ✅ {p['provider']}: model={p['model']}")
if not status["active_provider"]:
    log_anomaly("error", "init", "No API key found — all cascade will fail")

# ── Step 2: Fetch last 2 games ─────────────────────────────────────────────
section("[2/6] Fetch games")
from lichess_analyzer_mcp.services.lichess_client import fetch_user_games, fetch_game_pgn
from lichess_analyzer_mcp.services.game_analyzer import analyze_pgn

try:
    games_data = fetch_user_games("systeq", max_games=2)
    print(f"  Fetched {len(games_data)} games (requested 2)")
except Exception as e:
    log_anomaly("error", "lichess_api", "Fetch failed", traceback.format_exc())
    print(f"  FATAL: {e}")
    sys.exit(1)

if len(games_data) == 0:
    log_anomaly("error", "lichess_api", "0 games returned")
    sys.exit(1)

# ── Step 3: Analyze games ──────────────────────────────────────────────────
section("[3/6] Analyze games (Stockfish depth 12)")
analyses = []
for i, g in enumerate(games_data):
    game_id = g.get("id", f"g{i}")
    try:
        color = (
            "black"
            if g.get("players", {}).get("black", {}).get("user", {}).get("name", "").lower()
            == "systeq"
            else "white"
        )
        pgn = fetch_game_pgn(game_id)
        if not pgn or len(pgn) < 20:
            log_anomaly(
                "warning", "pgn", f"Game {game_id}: short PGN ({len(pgn) if pgn else 0} chars)"
            )
            continue
        analysis = analyze_pgn(pgn, player_color=color, depth=12, game_id=game_id, use_cache=False)
        analyses.append(analysis)
        print(
            f"  ✅ {game_id} ({color}): ACPL={analysis.total_acpl:.1f}, blunders={len(analysis.blunders)}, moves={len(analysis.moves)}"
        )
    except Exception as e:
        log_anomaly("error", "analyze", f"Game {game_id}: {e}", traceback.format_exc())

print(f"  Analyzed: {len(analyses)}/{len(games_data)}")

if len(analyses) == 0:
    log_anomaly("error", "pipeline", "0 games analyzed — abort")
    sys.exit(1)

# ── Step 4: Pattern detection ──────────────────────────────────────────────
section("[4/6] Pattern detection")
from lichess_analyzer_mcp.services.pattern_detector import PatternDetector
from lichess_analyzer_mcp.services.diagnostician import diagnose
from lichess_analyzer_mcp.services.compressibility_validator import compute_compression

metadata = {"username": "systeq", "total_games": len(analyses)}
detector = PatternDetector()
try:
    matches = detector.detect_all(analyses, metadata)
except Exception as e:
    log_anomaly("error", "pattern", "detect_all failed", traceback.format_exc())
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

print(f"  Patterns detected: {len(pattern_results)}")
for p in pattern_results:
    print(
        f"    [{p['severity'].upper()}] {p['pattern_id']}: {p['pattern_name']} (conf={p['confidence']}%, freq={p['frequency']})"
    )

# ── Weakness report ────────────────────────────────────────────────────────
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
    print(f"\n  Weakness report: ACPL={wr_dict['total_acpl']}, blunders={wr_dict['blunder_count']}")
except Exception as e:
    log_anomaly("error", "diagnose", f"Failed: {e}", traceback.format_exc())

# ── Step 5: Build LLM input prompt (log it!) ──────────────────────────────
section("[5/6] LLM prompt (deterministic pipeline output)")
from lichess_analyzer_mcp.services.llm_client import _build_coaching_prompt

prompt_text = _build_coaching_prompt("systeq", len(analyses), pattern_results, wr_dict)
print(f"  System prompt: {len(SYSPROMPT_DISPLAY)} chars")
print(f"  User prompt:   {len(prompt_text)} chars ({len(prompt_text) // 4} est. tokens)")
print(f"\n  ── User prompt preview ──")
for line in prompt_text.split("\n")[:20]:
    print(f"  {line}")
if prompt_text.count("\n") > 20:
    print(f"  ... ({prompt_text.count('\n') - 20} more lines)")

# ── Step 6: LLM cascade with token logging ────────────────────────────────
section("[6/6] LLM cascade: NVIDIA -> Cerebras -> DeepSeek")

report, cascade_log = generate_coaching_report_with_logs(
    username="systeq",
    games_analyzed=len(analyses),
    patterns=pattern_results,
    weakness_report=wr_dict,
    cascade_order=["NVIDIA", "Cerebras", "DeepSeek"],
)

print(f"\n  Cascade results ({len(cascade_log)} attempts):")
for i, attempt in enumerate(cascade_log):
    prov = attempt.get("provider", "?")
    error = attempt.get("error")
    tokens = attempt.get("total_tokens", attempt.get("estimated_input_tokens", "?"))
    http = attempt.get("http_status", "-")
    if error:
        print(f"    [{i + 1}] {prov}: ❌ {error} (HTTP {http})")
    else:
        pt = attempt.get("prompt_tokens", "?")
        ct = attempt.get("completion_tokens", "?")
        tt = attempt.get("total_tokens", "?")
        print(f"    [{i + 1}] {prov}: ✅ prompt={pt}, completion={ct}, total={tt} tokens")

# ── LOG LLM attempts details ──────────────────────────────────────────────
# The cascade_log from generate_coaching_report_with_logs does NOT include
# the actual LLM input/output text. We extract that here and log it.
print(f"\n  ── LLM Input (system prompt) ──")
print(f"  {SYSPROMPT_DISPLAY}")
print(f"\n  ── LLM Input (user prompt) ──")
print(f"  {prompt_text}")

# Find the successful attempt to get its output
success_idx = None
for i, att in enumerate(cascade_log):
    if not att.get("error"):
        success_idx = i
        break

if success_idx is not None:
    print(f"\n  ── LLM Output (provider: {cascade_log[success_idx]['provider']}) ──")
else:
    print(f"\n  ── No successful LLM call — showing fallback report ──")

print(f"\n{report}")

# ── Summary ────────────────────────────────────────────────────────────────
section("SUMMARY")
print(f"  Games fetched:      {len(games_data)}")
print(f"  Games analyzed:     {len(analyses)}")
print(f"  Patterns detected:  {len(pattern_results)}")
for p in pattern_results:
    print(f"    {p['pattern_id']}: {p['pattern_name']} ({p['confidence']}%)")
print(f"  LLM cascade tries:  {len(cascade_log)}")
for att in cascade_log:
    if att.get("error"):
        print(f"    ❌ {att['provider']}: {att['error']}")
    else:
        print(f"    ✅ {att['provider']}: {att.get('total_tokens', '?')} tokens")
print(f"  Report generated:   {'✅' if report else '❌'}")
print(f"  Anomalies:          {len(anomalies)}")
for a in anomalies:
    print(f"    [{a['severity']}] {a['source']}: {a['msg']}")

# ── Save everything ────────────────────────────────────────────────────────
output = {
    "test_date": datetime.now(timezone.utc).isoformat(),
    "username": "systeq",
    "games_limit": 2,
    "games_fetched": [g.get("id", f"g{i}") for i, g in enumerate(games_data)],
    "games_analyzed": [
        {
            "id": a.game.id,
            "color": a.game.color,
            "acpl": round(a.total_acpl, 1),
            "blunders": len(a.blunders),
            "moves": len(a.moves),
            "opening": a.game.opening,
            "result": a.game.result,
        }
        for a in analyses
    ],
    "patterns_detected": pattern_results,
    "weakness_report": wr_dict,
    "llm_prompt_system": SYSPROMPT_DISPLAY,
    "llm_prompt_user": prompt_text,
    "llm_cascade_log": cascade_log,
    "llm_report": report,
    "anomalies": anomalies,
}
out_path = os.path.join(REPO_ROOT, "data", "test_llm_cascade_output.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"\n  Full dump: data/test_llm_cascade_output.json")

print(f"\n{'=' * 60}")
print("  TEST COMPLETE")
print(f"{'=' * 60}")
