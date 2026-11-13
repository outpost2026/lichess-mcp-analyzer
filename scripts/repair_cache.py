"""Repair stale cache: recompute accuracy and the three phase slices.

Uses the single source of truth (`GameAnalysis.auto_annotate`), so a repaired
cache file is grouped by exactly the same phase logic as a fresh analysis:

- `phase_stats`      -> effective_phase (what detectors use),
- `segment_stats`    -> ply segment,
- `chess_phase_stats`-> material-based chess_phase.

Only the aggregate fields are rewritten; every other key in the cache file is
left untouched.
"""

import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from lichess_analyzer_mcp.models.game import GameAnalysis

cache_dir = os.path.join(os.path.dirname(__file__), "..", "data", "game_cache")
files = sorted(glob.glob(os.path.join(cache_dir, "*_d*.json")))

fixed = 0
for path in files:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    try:
        analysis = GameAnalysis.from_dict(data)
    except (KeyError, TypeError):
        continue
    if not analysis.moves:
        continue

    analysis.auto_annotate()
    updates = {
        "accuracy": analysis.accuracy,
        "phase_stats": analysis.phase_stats,
        "segment_stats": analysis.segment_stats,
        "chess_phase_stats": analysis.chess_phase_stats,
    }
    if all(data.get(key) == value for key, value in updates.items()):
        continue

    data.update(updates)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    fixed += 1
    name = os.path.basename(path)
    print(
        f"  FIXED {name}: accuracy -> {analysis.accuracy}, phases -> {sorted(analysis.phase_stats)}"
    )

print(f"\nFixed {fixed} / {len(files)} cache files")
