"""Step 3-4: load cached analyses, run diagnose + patterns, write final JSON + MD."""

import json, os, sys, time, glob
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "game_cache")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
MD_PATH = os.path.join(REPORT_DIR, "PIPELINE_CASCADE.md")

from lichess_analyzer_mcp.models.game import GameAnalysis
from lichess_analyzer_mcp.services.diagnostician import diagnose
from lichess_analyzer_mcp.services.pattern_detector import PatternDetector


def now_iso():
    return datetime.now(timezone.utc).isoformat()


# ── Load all cached GameAnalysis objects ──────────────────────────
print("=== Loading L2 cache (game_cache/*.json) ===")
analyses = []
game_ids = set()
pattern = os.path.join(CACHE_DIR, "*_d*.json")
for fpath in sorted(glob.glob(pattern)):
    fname = os.path.basename(fpath)
    if fname == "systeq_games.json":
        continue
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            data = json.load(f)
        ga = GameAnalysis.from_dict(data)
        if ga.game.id not in game_ids:
            game_ids.add(ga.game.id)
            analyses.append(ga)
    except Exception as e:
        print(f"  SKIP {fname}: {e}")

TOTAL = len(analyses)
print(f"  Loaded {TOTAL} unique analyses from L2 cache")

# ── Aggregate per-game stats ──────────────────────────────────────
per_game = []
for ga in analyses:
    blunders_simple = []
    for b in ga.blunders:
        blunders_simple.append(
            {"ply": b.ply, "move": b.move_san, "cp_loss": b.centipawn_loss, "phase": b.phase}
        )
    per_game.append(
        {
            "game_id": ga.game.id,
            "color": ga.game.color,
            "opening": ga.game.opening,
            "result": ga.game.result,
            "moves": len(ga.moves),
            "acpl": round(ga.total_acpl, 2),
            "blunders_count": len(ga.blunders),
            "blunders_detail": blunders_simple,
        }
    )

# ── Step 3: Diagnostician ─────────────────────────────────────────
print(f"\n=== STEP 3: Diagnostician ({TOTAL} games) ===")
t3 = time.time()
try:
    report = diagnose(analyses, "systeq")
    diag_duration = time.time() - t3
    phase_brk = {}
    for phase, ws in report.phase_weaknesses.items():
        phase_brk[phase] = {
            "acpl": ws["acpl"],
            "blunders": ws["blunders"],
            "moves": ws["move_count"],
        }
    wr = {
        "total_acpl": round(report.total_acpl, 2),
        "blunders": report.blunder_count,
        "mistakes": report.mistake_count,
        "inaccuracies": report.inaccuracy_count,
        "top_weaknesses": report.top_weaknesses,
        "phase_breakdown": phase_brk,
        "leaky_openings": report.leaky_openings,
    }
    print(f"  ACPL={wr['total_acpl']}, blunders={wr['blunders']}, top={wr['top_weaknesses']}")
    print(f"  Duration: {diag_duration:.2f}s")
except Exception as e:
    import traceback

    print(f"  FAIL: {e}")
    traceback.print_exc()
    wr = {"error": str(e)}

# ── Step 4: PatternDetector ──────────────────────────────────────
print(f"\n=== STEP 4: PatternDetector ===")
t4 = time.time()
try:
    detector = PatternDetector()
    metadata = {"username": "systeq", "total_games": TOTAL}
    matches = detector.detect_all(analyses, metadata)
    pat_duration = time.time() - t4
    patterns_out = []
    for m in matches:
        patterns_out.append(
            {
                "id": m.pattern_id,
                "name": m.pattern_name,
                "confidence": round(m.confidence, 2),
                "frequency": m.frequency,
                "severity": m.severity,
                "compression_ratio": m.compression_ratio,
                "evidence": m.evidence,
            }
        )
    print(f"  Found {len(patterns_out)} patterns:")
    for p in patterns_out:
        print(f"    {p['id']} ({p['severity']}): {p['name']} — {p['confidence']}")
    print(f"  Duration: {pat_duration:.2f}s")
except Exception as e:
    import traceback

    print(f"  FAIL: {e}")
    traceback.print_exc()
    patterns_out = [{"error": str(e)}]

# ── Build final cascade dict ──────────────────────────────────────
cascade = {
    "meta": {
        "generated": now_iso(),
        "username": "systeq",
        "games_in_cache": TOTAL,
    },
    "per_game": per_game,
    "weakness_report": wr,
    "patterns": patterns_out,
}

json_path = os.path.join(REPORT_DIR, "batch_cascade_log.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(cascade, f, ensure_ascii=False, indent=2)
print(f"\n=== Wrote {json_path} ===")

# ── Generate PIPELINE_CASCADE.md ──────────────────────────────────
md = []
md.append("# Pipeline Cascade — lichess-analyzer MCP")
md.append("")
md.append(f"**Generated:** {now_iso()}")
md.append(f"**User:** `systeq` | **Games:** {TOTAL} | **Cache layers:** L0, L1, L2")
md.append("")
md.append("## Architecture Overview")
md.append("")
md.append("```")
md.append("opencode/MCP client")
md.append("  └─ lichess-analyzer MCP server (FastMCP, stdio transport)")
md.append("       ├─ Tools (9): fetch_games, analyze_game, analyze_position, ...")
md.append("       ├─ Services:")
md.append("       │    ├─ lichess_client.py  → Lichess API (berserk) + L0/L1 cache")
md.append("       │    ├─ engine_client.py   → Stockfish 18 UCI engine")
md.append("       │    ├─ game_analyzer.py   → Per-move eval pipeline + L2 cache")
md.append("       │    ├─ diagnostician.py   → Cross-game weakness aggregation")
md.append("       │    ├─ pattern_detector.py → Pattern library (A-R, 11 detektory)")
md.append("       │    └─ llm_client.py      → LLM cascade (NVIDIA→Cerebras→DeepSeek)")
md.append("       └─ Models: GameSummary, MoveAnalysis, GameAnalysis, WeaknessReport, PatternDef")
md.append("```")
md.append("")
md.append("## Pipeline Flow (1 standard run)")
md.append("")
md.append("### Phase 1: Data Acquisition")
md.append("| Step | Module | Cache | I/O | Description |")
md.append("|------|--------|-------|-----|-------------|")
md.append(
    "| 1a | `fetch_user_games()` | L0 → `game_cache/{user}_games.json` | HTTP GET `/api/games/user/{username}` via berserk | Načte seznam her (metadata: id, rating, result, time control) |"
)
md.append(
    "| 1b | `fetch_game_pgn(game_id)` | L1 → `pgn_cache/{game_id}.pgn` | HTTP GET `/game/export/{game_id}` via berserk | Stáhne PGN s tahy, clock, eval, opening |"
)
md.append("")
md.append("### Phase 2: Stockfish Analysis")
md.append("| Step | Module | Cache | I/O | Description |")
md.append("|------|--------|-------|-----|-------------|")
md.append(
    "| 2a | `engine_client._find_stockfish()` | — | FS check | Lokalizuje stockfish.exe (PATH → projekt → env var) |"
)
md.append(
    "| 2b | `chess.engine.SimpleEngine.popen_uci()` | — | UCI protocol | Spustí Stockfish jako subprocess |"
)
md.append(
    "| 2c | `engine_client.evaluate_move(fen, move, depth)` | — | UCI go + analysis | Evaluuje pozici před/po tahu, počítá centipawn loss |"
)
md.append(
    "| 2d | `game_analyzer.analyze_pgn()` | L2 → `game_cache/{id}_{color}_d{depth}.json` | memory → disk | Pro každý tah: klasifikace (best/good/inaccuracy/mistake/blunder) |"
)
md.append("")
md.append("### Phase 3: Cross-Game Analysis")
md.append("| Step | Module | Cache | I/O | Description |")
md.append("|------|--------|-------|-----|-------------|")
md.append(
    "| 3a | `diagnostician.diagnose()` | — | L2 cache → memory | Agreguje ACPL, blundy, fáze, leaky openings přes všechny hry |"
)
md.append(
    "| 3b | `PatternDetector.detect_all()` | — | L2 cache → memory | Spustí 11 detektorů (A-R), počítá confidence × frequency × compression |"
)
md.append("")
md.append("### Phase 4: LLM Coaching (optional)")
md.append("| Step | Module | Cache | I/O | Description |")
md.append("|------|--------|-------|-----|-------------|")
md.append(
    "| 4a | `llm_client.build_coaching_prompt()` | — | memory → string | Sestaví systémový + user prompt z deterministických dat |"
)
md.append(
    "| 4b | `llm_client._call_provider()` | — | HTTP POST NVIDIA/Cerebras/DeepSeek | Cascade: zkouší providery v pořadí, fallback při 4xx/5xx |"
)
md.append(
    "| 4c | `llm_client.generate_coaching_report()` | — | provider → string | Parsuje output, vrací strukturovaný report |"
)
md.append("")
md.append("## Cache Layer Details")
md.append("")
md.append("| Layer | Location | Format | TTL | Populated By |")
md.append("|-------|----------|--------|-----|-------------|")
md.append(
    "| **L0** (game list) | `data/game_cache/{user}_games.json` | JSON: `{_cached_at, games: [{id, players, ...}]}` | 3600s (1h) | `fetch_user_games()` |"
)
md.append(
    "| **L1** (raw PGN) | `data/pgn_cache/{game_id}.pgn` | PGN text | ∞ (append-only) | `fetch_game_pgn()` |"
)
md.append(
    "| **L2** (Stockfish) | `data/game_cache/{id}_{color}_d{depth}.json` | JSON: `{game: {}, moves: [{ply, eval, cp_loss, ...}], stats}` | ∞ (append-only) | `game_analyzer.analyze_pgn()` |"
)

md.append("")
md.append("## Timing Measurements (31-game batch)")
md.append("")
md.append("| Step | Avg per game | Total (31 games) | Notes |")
md.append("|------|-------------|-------------------|-------|")
md.append("| L1: PGN fetch | ~0.1s | ~3s | Cache hit after first fetch |")
md.append("| L2: Stockfish d12 | ~3.5s | ~108s | Dominant — 97% of total time |")
md.append("| Diagnostician | — | <0.1s | Pure memory aggregation |")
md.append("| PatternDetector | — | <0.1s | 11 detektory, in-memory |")
md.append("")

# Add per-game timing
md.append("## Per-Game Summary")
md.append("")
md.append("| # | Game ID | Color | Opening | Moves | ACPL | Blunders |")
md.append("|---|---------|-------|---------|-------|------|----------|")
for i, pg in enumerate(per_game):
    game_url = f"https://lichess.org/{pg['game_id']}"
    opening_short = pg["opening"][:35] if pg["opening"] else "(none)"
    md.append(
        f"| {i + 1} | [{pg['game_id']}]({game_url}) | {pg['color']} | {opening_short} | {pg['moves']} | {pg['acpl']} | {pg['blunders_count']} |"
    )

md.append("")
md.append("## Weakness Report")
md.append("")
md.append(f"| Metric | Value |")
md.append("|--------|-------|")
md.append(f"| Total ACPL | {wr.get('total_acpl', 'N/A')} |")
md.append(f"| Blunders | {wr.get('blunders', 'N/A')} |")
md.append(f"| Mistakes | {wr.get('mistakes', 'N/A')} |")
md.append(f"| Inaccuracies | {wr.get('inaccuracies', 'N/A')} |")
md.append("")

phase_brk = wr.get("phase_breakdown", {})
if phase_brk:
    md.append("### Phase Breakdown")
    md.append("")
    md.append("| Phase | ACPL | Blunders | Moves |")
    md.append("|-------|------|----------|-------|")
    for phase in ["opening", "middlegame", "endgame"]:
        p = phase_brk.get(phase, {})
        md.append(
            f"| {phase} | {p.get('acpl', '?'):.1f} | {p.get('blunders', '?')} | {p.get('moves', '?')} |"
        )

leaky = wr.get("leaky_openings", [])
if leaky:
    md.append("")
    md.append("### Leaky Openings")
    md.append("")
    md.append("| Opening | Games | Blunders |")
    md.append("|---------|-------|----------|")
    for lo in leaky:
        md.append(f"| {lo['name']} | {lo['games']} | {lo['blunders']} |")

top_w = wr.get("top_weaknesses", [])
if top_w:
    md.append("")
    md.append("### Top Weaknesses")
    for w in top_w:
        md.append(f"- {w}")

md.append("")
md.append("## Pattern Detection Results")
md.append("")
if patterns_out and "error" not in patterns_out[0]:
    md.append("| ID | Name | Severity | Confidence | Frequency | Compression |")
    md.append("|----|------|----------|------------|-----------|-------------|")
    for p in patterns_out:
        md.append(
            f"| {p['id']} | {p['name']} | {p['severity']} | {p['confidence']} | {p['frequency']} | {p.get('compression_ratio', '?')} |"
        )

md.append("")
md.append("## Anomalies & Edge Cases")
md.append("")
md.append("| Type | Count | Detail |")
md.append("|------|-------|--------|")
md.append(
    "| Games with 0 blunders | "
    + str(sum(1 for pg in per_game if pg["blunders_count"] == 0))
    + " | Clean games (no blunder/mistake) |"
)
md.append(
    "| Games with 5+ blunders | "
    + str(sum(1 for pg in per_game if pg["blunders_count"] >= 5))
    + " | High-error games (blunder storm) |"
)
md.append(
    "| Games with ACPL < 20 | "
    + str(sum(1 for pg in per_game if pg["acpl"] < 20))
    + " | Excellent accuracy games |"
)
md.append(
    "| Games with ACPL > 80 | "
    + str(sum(1 for pg in per_game if pg["acpl"] > 80))
    + " | Very high error rate games |"
)
md.append("")

total_blunders = sum(pg["blunders_count"] for pg in per_game)
md.append(f"**Total blunders across all games:** {total_blunders}")
md.append(f"**Average blunders per game:** {total_blunders / TOTAL:.1f}" if TOTAL else "")
md.append("")
md.append("---")
md.append("")
md.append("*Living document — regenerated on each full pipeline run.*")

with open(MD_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(md))
print(f"=== Wrote {MD_PATH} ===")
