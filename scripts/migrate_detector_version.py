"""Lokalni migrace cache po bumpu DETECTOR_VERSION (bez engine).

Prepocita z ulozenych FEN/moves (deterministicky, zadny Stockfish):
  - blunder_fact_sheets[].pattern_matches  (jedina implementace: per_move_patterns, P0-2)
  - blunder_fact_sheets[].board_state      (board_facts: ccp/kcp/kcp_played, P0-1)
  - blunder_fact_sheets[].detector_version (novy DETECTOR_VERSION)

Pouziti:
  python scripts/migrate_detector_version.py            # dry-run (nic nepise)
  python scripts/migrate_detector_version.py --apply    # zaloha + zapis

Zaloha: data/_backup_migrate_2026-11-11/ (P86/P87: pre count+bytes, po overeni).
Soubory bez blunder_fact_sheets (indexy, herni metadata) se preskakuji.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from lichess_analyzer_mcp.models.analysis import DETECTOR_VERSION  # noqa: E402
from lichess_analyzer_mcp.models.game import MoveAnalysis  # noqa: E402
from lichess_analyzer_mcp.services import board_facts  # noqa: E402
from lichess_analyzer_mcp.services.pattern_detector import per_move_patterns  # noqa: E402

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "game_cache")
BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "_backup_migrate_2026-11-11")


def _move_from(mv: dict, fallback: dict | None = None) -> MoveAnalysis:
    fallback = fallback or {}
    return MoveAnalysis(
        ply=mv.get("ply", fallback.get("ply", 0)),
        move_uci=mv.get("move_uci", fallback.get("move_played_uci", "")),
        move_san=mv.get("move_san", fallback.get("move_played_san", "")),
        eval_before=mv.get("eval_before", fallback.get("eval_before")) or 0,
        eval_after=mv.get("eval_after", fallback.get("eval_after")) or 0,
        win_prob_before=mv.get("win_prob_before", fallback.get("win_prob_before")) or 0,
        win_prob_after=mv.get("win_prob_after", fallback.get("win_prob_after")) or 0,
        centipawn_loss=mv.get("centipawn_loss", fallback.get("centipawn_loss")) or 0,
        classification=mv.get("classification", "blunder"),
        best_move_uci=mv.get("best_move_uci", ""),
        best_move_san=mv.get("best_move_san", ""),
        is_tactical_motif=bool(mv.get("is_tactical_motif", False)),
        motif_type=mv.get("motif_type"),
        phase=mv.get("phase", fallback.get("phase", "")),
        fen=mv.get("fen", fallback.get("fen_before", "")),
        was_in_check=bool(
            mv.get("was_in_check", fallback.get("board_state", {}).get("was_in_check", False))
        ),
    )


def migrate_file(path: str, apply: bool) -> dict:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or not data.get("blunder_fact_sheets"):
        return {"skip": True}

    moves = {m.get("ply"): m for m in data.get("moves", [])}
    order = sorted(moves)
    stats = {
        "skip": False,
        "sheets": 0,
        "pm_changed": 0,
        "pm_added": 0,
        "pm_removed": 0,
        "bs_changed": 0,
        "dv_changed": 0,
    }

    for sheet in data["blunder_fact_sheets"]:
        stats["sheets"] += 1
        ply = sheet.get("ply")
        mv = moves.get(ply, {})
        idx = order.index(ply) if ply in order else -1
        prev = _move_from(moves[order[idx - 1]]) if idx > 0 else None
        move = _move_from(mv, sheet)
        was_in_check = bool(
            mv.get("was_in_check", sheet.get("board_state", {}).get("was_in_check", False))
        )

        # 1) pattern_matches (P0-2: jedina implementace)
        new_pm = [
            {
                "pattern_id": c["pattern_id"],
                "pattern_name": c["pattern_name"],
                "confidence": c.get("strength", c.get("confidence")),
                "evidence": c["detail"],
            }
            for c in per_move_patterns(move, prev, was_in_check)
        ]
        old_pm = sheet.get("pattern_matches", [])
        if old_pm != new_pm:
            old_ids = {x.get("pattern_id") for x in old_pm}
            new_ids = {x.get("pattern_id") for x in new_pm}
            stats["pm_added"] += len(new_ids - old_ids)
            stats["pm_removed"] += len(old_ids - new_ids)
            stats["pm_changed"] += 1
            sheet["pattern_matches"] = new_pm

        # 2) board_state (P0-1)
        fen = sheet.get("fen_before", "")
        bs = sheet.get("board_state", {})
        new_bs = {
            "was_in_check": was_in_check,
            "checking_pieces": board_facts.checking_pieces(fen) if was_in_check else [],
            "capture_checking_piece_possible": board_facts.capture_checking_piece_possible(fen),
            "king_capture_possible": board_facts.king_capture_possible(fen),
            "king_capture_played": board_facts.king_capture_played(
                fen, sheet.get("move_played_uci", ""), was_in_check
            ),
        }
        if bs != new_bs:
            stats["bs_changed"] += 1
            sheet["board_state"] = new_bs

        # 3) detector_version
        if sheet.get("detector_version") != DETECTOR_VERSION:
            stats["dv_changed"] += 1
            sheet["detector_version"] = DETECTOR_VERSION

    if apply and (stats["pm_changed"] or stats["bs_changed"] or stats["dv_changed"]):
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, ensure_ascii=False)
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true", help="zaloha + zapis (bez toho jen dry-run)")
    args = ap.parse_args()

    files = sorted(f for f in os.listdir(CACHE_DIR) if f.endswith(".json"))
    total = dict(
        files=0,
        touched=0,
        sheets=0,
        pm_changed=0,
        pm_added=0,
        pm_removed=0,
        bs_changed=0,
        dv_changed=0,
    )
    roundtrip_ok = 0
    to_backup = []

    for fn in files:
        path = os.path.join(CACHE_DIR, fn)
        # round-trip sanity: format jako pipeline (jednoradkovy JSON, UTF-8 bez escapes)
        with open(path, encoding="utf-8") as fh:
            raw = fh.read()
        try:
            if json.dumps(json.loads(raw), ensure_ascii=False) == raw:
                roundtrip_ok += 1
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        st = migrate_file(path, apply=False)
        if st.get("skip"):
            continue
        total["files"] += 1
        to_backup.append(path)
        for k in ("sheets", "pm_changed", "pm_added", "pm_removed", "bs_changed", "dv_changed"):
            total[k] += st[k]
        if st["pm_changed"] or st["bs_changed"] or st["dv_changed"]:
            total["touched"] += 1

    print(f"DETECTOR_VERSION -> {DETECTOR_VERSION}")
    print(f"round-trip byte-identical: {roundtrip_ok}/{len(files)}")
    print(
        f"soubory s BFS: {total['files']}, k prepsani: {total['touched']}, "
        f"fact sheets: {total['sheets']}"
    )
    print(
        f"pattern_matches zmeny: {total['pm_changed']} (+{total['pm_added']} id, "
        f"-{total['pm_removed']} id), board_state zmeny: {total['bs_changed']}, "
        f"detector_version zmeny: {total['dv_changed']}"
    )

    if not args.apply:
        print("DRY-RUN: nic nezapsano. Spustte s --apply.")
        return 0

    # P86/P87: zaloha pred mazanim/prepisem
    os.makedirs(BACKUP_DIR, exist_ok=True)
    pre_n = pre_b = 0
    for path in to_backup:
        pre_n += 1
        pre_b += os.path.getsize(path)
        shutil.copy2(path, BACKUP_DIR)
    print(f"zaloha: {pre_n} souboru, {pre_b} B -> {BACKUP_DIR}")

    written = 0
    for path in to_backup:
        st = migrate_file(path, apply=True)
        if not st.get("skip") and (st["pm_changed"] or st["bs_changed"] or st["dv_changed"]):
            written += 1
    post_n = len([f for f in os.listdir(BACKUP_DIR) if f.endswith(".json")])
    print(
        f"zapsano: {written}; overeni zalohy: {post_n}/{pre_n} souboru, "
        f"{sum(os.path.getsize(os.path.join(BACKUP_DIR, f)) for f in os.listdir(BACKUP_DIR))} B"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
