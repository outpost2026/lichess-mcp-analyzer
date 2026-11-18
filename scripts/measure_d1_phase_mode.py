"""D1 measurement (offline): dual-run per-move detectors under both phase modes.

Compares `ply_segment` (current default) with `material` (`chess_phase`) on
cached d14 analyses. No engine calls, no LLM. Q4 experiment must be OFF.

Run: python -X utf8 scripts/measure_d1_phase_mode.py [--games 20]
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "game_cache"
OUT = ROOT / "data" / "runs" / "D1_phase_measurement_2026-11-18.json"

# The experiment must not contaminate a production decision measurement.
os.environ.pop("LICHESS_EXPERIMENTAL_Q4", None)

from lichess_analyzer_mcp.models.game import (  # noqa: E402
    GameAnalysis,
    PHASE_METHOD_DEFAULT,
    PHASE_METHOD_MATERIAL,
)
from lichess_analyzer_mcp.services.pattern_detector import per_move_patterns  # noqa: E402

FLAGGED = ("blunder", "mistake", "inaccuracy")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--games", type=int, default=20)
    args = parser.parse_args()

    files = sorted(CACHE.glob("*_d14n150000.json"))[: args.games]
    if not files:
        print(json.dumps({"error": "no d14n150000 cache files"}))
        return 2

    games = 0
    measured_moves = 0
    material_available = 0
    flips = 0
    r_flips = 0
    flipped_plies: list[dict] = []
    per_mode: dict[str, int] = {"ply_segment": 0, "material": 0}

    for path in files:
        with open(path, encoding="utf-8", errors="replace") as fh:
            data = json.load(fh)
        analysis = GameAnalysis.from_dict(data)
        games += 1
        for move in analysis.moves:
            if (
                not move.analyzed
                or move.centipawn_loss is None
                or move.classification not in FLAGGED
            ):
                continue
            measured_moves += 1
            has_material = bool((getattr(move, "chess_phase", "") or "").strip())
            if has_material:
                material_available += 1
            move.phase_method = PHASE_METHOD_DEFAULT
            segment_ids = {c["pattern_id"] for c in per_move_patterns(move)}
            move.phase_method = PHASE_METHOD_MATERIAL
            material_ids = {c["pattern_id"] for c in per_move_patterns(move)}
            per_mode["ply_segment"] += len(segment_ids)
            per_mode["material"] += len(material_ids)
            if segment_ids != material_ids:
                flips += 1
                flipped_plies.append(
                    {
                        "game": analysis.game.id,
                        "ply": move.ply,
                        "segment_phase": getattr(move, "segment", "") or move.phase,
                        "material_phase": getattr(move, "chess_phase", "") or "",
                        "segment_ids": sorted(segment_ids),
                        "material_ids": sorted(material_ids),
                    }
                )
            if ("R" in segment_ids) != ("R" in material_ids):
                r_flips += 1

    result = {
        "measurement": "D1 phase mode dual-run",
        "date": "2026-11-18",
        "games": games,
        "cache_pattern": "*_d14n150000.json",
        "measured_flagged_moves": measured_moves,
        "moves_with_material_phase": material_available,
        "pattern_assignments": per_mode,
        "pattern_set_flips": flips,
        "r_detector_flips": r_flips,
        "flip_rate": round(flips / measured_moves, 4) if measured_moves else None,
        "flipped_plies": flipped_plies[:30],
        "q4_experiment_enabled": False,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(json.dumps({k: v for k, v in result.items() if k != "flipped_plies"}, indent=2))
    print(f"full detail: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
