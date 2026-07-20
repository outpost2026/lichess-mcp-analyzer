"""Repair stale cache: recompute accuracy and phase_stats using the fixed auto_annotate()."""

import os, json, glob

cache_dir = os.path.join(os.path.dirname(__file__), "..", "data", "game_cache")
files = sorted(glob.glob(os.path.join(cache_dir, "*_d*.json")))

fixed = 0
for path in files:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    moves = data.get("moves", [])
    if not moves:
        continue

    # Recompute accuracy from moves
    acc_sum = sum(max(0, 100 - m.get("centipawn_loss", 0) * 0.15) for m in moves)
    accuracy = round(max(0, min(100, acc_sum / len(moves))), 1)

    # Recompute phase_stats
    phases = {}
    for m in moves:
        phase = m.get("phase", "?")
        phases.setdefault(phase, []).append(m)

    phase_stats = {}
    for phase, phase_moves in sorted(phases.items()):
        acpl = sum(m.get("centipawn_loss", 0) for m in phase_moves) / len(phase_moves)
        acc = sum(max(0, 100 - m.get("centipawn_loss", 0) * 0.15) for m in phase_moves) / len(
            phase_moves
        )
        errors = sum(
            1
            for m in phase_moves
            if m.get("classification") in ("blunder", "mistake", "inaccuracy")
        )
        phase_stats[phase] = {
            "acpl": round(acpl, 1),
            "accuracy": round(acc, 1),
            "move_count": len(phase_moves),
            "errors": errors,
        }

    old_acc = data.get("accuracy", 0)
    old_ps = data.get("phase_stats", {})

    if old_acc != accuracy or old_ps != phase_stats:
        data["accuracy"] = accuracy
        data["phase_stats"] = phase_stats
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        fixed += 1
        name = os.path.basename(path)
        print(
            f"  FIXED {name}: accuracy {old_acc} -> {accuracy}, phase_stats {len(old_ps)} -> {len(phase_stats)} phases"
        )

print(f"\nFixed {fixed} / {len(files)} cache files")
