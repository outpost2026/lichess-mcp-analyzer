"""Batch analyze all cached games for a user with full timing cascade log."""

import json, os, sys, time, traceback
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("LICHESS_TOKEN", "")

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "game_cache")
PGN_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "pgn_cache")
REPORT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

from lichess_analyzer_mcp.services.lichess_client import fetch_user_games, fetch_game_pgn
from lichess_analyzer_mcp.services.game_analyzer import analyze_pgn
from lichess_analyzer_mcp.services.diagnostician import diagnose
from lichess_analyzer_mcp.services.pattern_detector import PatternDetector


def now_iso():
    return datetime.now(timezone.utc).isoformat()


cascade = {
    "meta": {"started": now_iso(), "username": "systeq", "total_games_in_cache": 0},
    "steps": [],
    "anomalies": [],
    "per_game": [],
    "final_report": {},
}


def log_step(step_id: str, label: str, status: str, detail: str, duration_s: float):
    entry = {
        "step": step_id,
        "label": label,
        "status": status,
        "detail": detail,
        "duration_s": round(duration_s, 2),
        "ts": now_iso(),
    }
    cascade["steps"].append(entry)
    print(f"  [{status}] {step_id} {label} ({duration_s:.1f}s): {detail}")


def log_anomaly(severity: str, source: str, msg: str, detail: str = ""):
    entry = {"ts": now_iso(), "severity": severity, "source": source, "msg": msg, "detail": detail}
    cascade["anomalies"].append(entry)
    print(f"  [!{severity}] {source}: {msg}")


# ── Step 1: Load game list from cache ─────────────────────────────────
t0 = time.time()
print("\n=== STEP 1 — fetch_user_games (L0 cache load) ===")
try:
    games_data = fetch_user_games("systeq", max_games=50)
    cascade["meta"]["total_games_in_cache"] = len(games_data)
    log_step(
        "L0",
        "fetch_user_games -> L0 cache",
        "OK",
        f"{len(games_data)} games loaded",
        time.time() - t0,
    )
except Exception as e:
    log_step("L0", "fetch_user_games", "FAIL", str(e), time.time() - t0)
    log_anomaly("error", "L0", str(e), traceback.format_exc())
    sys.exit(1)

# ── Step 2: Per-game pipeline (PGN fetch + Stockfish) ─────────────────
print(f"\n=== STEP 2 — Analyze {len(games_data)} games (PGN -> Stockfish L2) ===")
analyses = []
TOTAL = len(games_data)
depth = 12

for i, g in enumerate(games_data):
    game_id = g.get("id", "???")
    t_game = time.time()
    print(f"\n  [{i + 1}/{TOTAL}] {game_id}...")

    # Step 2a: PGN fetch (L1 cache)
    t1 = time.time()
    try:
        pgn = fetch_game_pgn(game_id)
        pgn_duration = time.time() - t1
        pgn_len = len(pgn)
        log_step(
            f"L1/{game_id}", "fetch_game_pgn -> L1 cache", "OK", f"{pgn_len} chars", pgn_duration
        )
    except Exception as e:
        log_step(f"L1/{game_id}", "fetch_game_pgn", "FAIL", str(e), time.time() - t1)
        log_anomaly("error", f"L1/{game_id}", f"PGN fetch failed: {e}")
        continue

    # Determine color
    username_lower = "systeq"
    color = "white"
    players = g.get("players", {})
    if players.get("black", {}).get("user", {}).get("name", "").lower() == username_lower:
        color = "black"
    elif players.get("white", {}).get("user", {}).get("name", "").lower() == username_lower:
        color = "white"

    # Step 2b: Stockfish analysis (L2 cache)
    t2 = time.time()
    try:
        analysis = analyze_pgn(
            pgn, player_color=color, depth=depth, game_id=game_id, use_cache=True
        )
        sf_duration = time.time() - t2
        moves_n = len(analysis.moves)
        acpl = analysis.total_acpl
        blunders = analysis.blunders
        log_step(
            f"L2/{game_id}",
            f"analyze_pgn Stockfish d{depth} -> L2 cache",
            "OK",
            f"{moves_n} moves, ACPL={acpl:.1f}, blunders={blunders}",
            sf_duration,
        )
        analyses.append(analysis)
    except Exception as e:
        log_step(
            f"L2/{game_id}", f"analyze_pgn Stockfish d{depth}", "FAIL", str(e), time.time() - t2
        )
        log_anomaly("error", f"L2/{game_id}", f"Stockfish analysis failed: {e}")
        continue

    total_game_time = time.time() - t_game
    cascade["per_game"].append(
        {
            "game_id": game_id,
            "color": color,
            "pgn_chars": pgn_len,
            "moves": moves_n,
            "acpl": round(acpl, 2),
            "blunders": blunders,
            "depth": depth,
            "duration_s": round(total_game_time, 2),
            "opening": analysis.game.opening,
            "result": analysis.game.result,
        }
    )

print(f"\n  Analyzed: {len(analyses)}/{TOTAL} games")

# ── Step 3: Diagnostician ─────────────────────────────────────────────
print(f"\n=== STEP 3 — Diagnostician (cross-game weakness report) ===")
t3 = time.time()
if analyses:
    try:
        report = diagnose(analyses, "systeq")
        diag_duration = time.time() - t3
        cascade["final_report"]["weakness_report"] = {
            "total_acpl": report.total_acpl,
            "blunders": report.blunder_count,
            "mistakes": report.mistake_count,
            "inaccuracies": report.inaccuracy_count,
            "top_weaknesses": report.top_weaknesses,
            "phase_breakdown": {
                phase: {"acpl": ws.acpl, "blunders": ws.blunders, "moves": ws.move_count}
                for phase, ws in report.phase_weaknesses.items()
            }
            if hasattr(report, "phase_weaknesses")
            else {},
        }
        log_step(
            "D",
            "diagnose -> weakness report",
            "OK",
            f"ACPL={report.total_acpl:.1f}, {report.blunder_count} blunders, "
            f"{len(report.top_weaknesses)} weaknesses",
            diag_duration,
        )
    except Exception as e:
        log_step("D", "diagnose", "FAIL", str(e), time.time() - t3)
        log_anomaly("error", "diagnose", str(e), traceback.format_exc())

# ── Step 4: Pattern detection ─────────────────────────────────────────
print(f"\n=== STEP 4 — PatternDetector ===")
t4 = time.time()
if analyses:
    try:
        detector = PatternDetector()
        metadata = {"username": "systeq", "total_games": len(analyses)}
        matches = detector.detect_all(analyses, metadata)
        pat_duration = time.time() - t4
        cascade["final_report"]["patterns"] = [
            {
                "id": m.pattern_id,
                "name": m.pattern_name,
                "confidence": m.confidence,
                "frequency": m.frequency,
                "severity": m.severity,
            }
            for m in matches
        ]
        log_step(
            "P", "PatternDetector.detect_all", "OK", f"{len(matches)} patterns found", pat_duration
        )
        for m in matches:
            print(
                f"    {m.pattern_id} ({m.severity}): {m.pattern_name} — confidence={m.confidence}%"
            )
    except Exception as e:
        log_step("P", "PatternDetector.detect_all", "FAIL", str(e), time.time() - t4)
        log_anomaly("error", "pattern_detector", str(e), traceback.format_exc())

# ── Finalize ───────────────────────────────────────────────────────────
cascade["meta"]["finished"] = now_iso()
total_duration = sum(s["duration_s"] for s in cascade["steps"])
cascade["meta"]["total_duration_s"] = round(total_duration, 2)
cascade["meta"]["games_analyzed"] = len(analyses)
cascade["meta"]["games_total"] = TOTAL

output_path = os.path.join(REPORT_DIR, "batch_cascade_log.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(cascade, f, ensure_ascii=False, indent=2)

print(f"\n{'=' * 60}")
print(f"  BATCH COMPLETE")
print(f"  Games analyzed: {len(analyses)}/{TOTAL}")
print(f"  Total duration: {total_duration:.1f}s")
print(f"  Anomalies: {len(cascade['anomalies'])}")
print(f"  Steps logged: {len(cascade['steps'])}")
print(f"  Full cascade: {output_path}")
print(f"{'=' * 60}")
