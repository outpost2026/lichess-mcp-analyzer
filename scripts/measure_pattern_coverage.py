"""Měření pokrytí flagged tahů (P0-7) na offline cache.

Offline, deterministický skript (žádný engine, žádná síť). Prochází
data/game_cache/*.json, sestaví GameAnalysis a pro každou hru zavolá
`scan_single_game()` - stejnou funkci, kterou používá produkční payload.
Nic se nedosazuje: každé číslo je spočítané z cache.

Co se měří:
  A) inventář: analýzy, hry po dedupu, flagged tahy dle klasifikace;
  B) pokrytí: matched (pattern) vs unclassified (explicitní důvod) -
     invariant P0-7: matched + unclassified == flagged;
  C) histogram důvodů unclassified (evidence_gap, quiet_positional, ...);
  D) četnost pattern ID mezi matched tahy;
  E) kontrola konzistence: coverage mapa vs přepočet z `analysis.moves`.

Dedup: stejná hra+barva ve více hloubkách = jedna analýza (bere se nejhlubší),
klíč = (game_id, color). Obě barvy téže hry zůstávají oddělené - jsou to dvě
samostatné analýzy (viz aggregate_candidate_moves.py, naměřeno 63 duplicit).

Použití:
  uv run python -X utf8 scripts/measure_pattern_coverage.py
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

from lichess_analyzer_mcp.models.game import GameAnalysis
from lichess_analyzer_mcp.models.pattern import PatternLibrary
from lichess_analyzer_mcp.services.pattern_detector import scan_single_game
from lichess_analyzer_mcp.services.provenance import build_provenance

CACHE_DIR = pathlib.Path("data/game_cache")
FLAGGED = ("blunder", "mistake", "inaccuracy")


def depth_of(source: str) -> int:
    """Hloubka analýzy ze jména souboru (…_d14n150000 -> 14); vyšší = hlubší."""
    try:
        tail = source.rsplit("_d", 1)[-1].replace(".json", "")
        digits = "".join(ch for ch in tail if ch.isdigit())
        return int(digits or 0)
    except (ValueError, IndexError):
        return 0


def color_of(source: str) -> str:
    if "_white_" in source:
        return "white"
    if "_black_" in source:
        return "black"
    return "?"


def load_games(cache_dir: pathlib.Path) -> tuple[list[tuple[str, GameAnalysis]], int]:
    """Načte cache a dedupuje dle (game_id, color); vrací (hry, počet souborů)."""
    best: dict[tuple[str, str], tuple[str, GameAnalysis]] = {}
    files = 0
    for path in sorted(cache_dir.glob("*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(raw, dict) or not isinstance(raw.get("moves"), list):
            continue
        try:
            analysis = GameAnalysis.from_dict(raw)
        except (KeyError, TypeError, ValueError):
            continue
        files += 1
        gid = analysis.game.id or path.stem
        color = analysis.game.color or color_of(path.name)
        key = (gid, color)
        if key not in best or depth_of(path.name) > depth_of(best[key][0]):
            best[key] = (path.name, analysis)
    return list(best.values()), files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache-dir", default=str(CACHE_DIR))
    ap.add_argument(
        "--json-out",
        default="",
        help="zapsat strukturovany vysledek včetně provenance do JSON souboru",
    )
    args = ap.parse_args()

    games, files = load_games(pathlib.Path(args.cache_dir))
    if not games:
        print("CHYBA: zadne analyzy v cache", file=sys.stderr)
        return 1

    library = PatternLibrary().load_baseline()
    provenance = build_provenance([analysis for _, analysis in games], library)

    flagged_by_class: collections.Counter = collections.Counter()
    status_by_class: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    reason_by_class: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    reason_all: collections.Counter = collections.Counter()
    pattern_ids: collections.Counter = collections.Counter()
    evidence: collections.Counter = collections.Counter()
    multi_pattern = 0
    invariant_errors: list[str] = []
    total_flagged = 0
    total_matched = 0

    for source, analysis in games:
        patterns, coverage = scan_single_game(analysis)
        for pattern in patterns:
            pattern_ids[pattern["pattern_id"]] += 1

        measured = [
            m
            for m in analysis.moves
            if m.analyzed and m.centipawn_loss is not None and m.classification in FLAGGED
        ]
        # Invariant P0-7: coverage mapa má přesně jeden záznam na flagged tah.
        if len(coverage) != len(measured):
            invariant_errors.append(f"{source}: coverage={len(coverage)} flagged={len(measured)}")
        if set(coverage) != {m.ply for m in measured}:
            invariant_errors.append(f"{source}: coverage ply mnozina != flagged ply mnozina")

        for move in measured:
            cls = move.classification
            entry = coverage.get(move.ply)
            if entry is None:
                invariant_errors.append(f"{source}: chybi coverage pro ply={move.ply}")
                continue
            total_flagged += 1
            flagged_by_class[cls] += 1
            evidence["flagged"] += 1
            evidence["best_move_san"] += int(bool(move.best_move_san))
            evidence["engine_lines"] += int(bool(move.engine_lines))
            evidence["played_rank"] += int(bool(move.played_rank))
            status = entry["pattern_status"]
            status_by_class[cls][status] += 1
            if status == "matched":
                total_matched += 1
                if len(entry["pattern_ids"]) > 1:
                    multi_pattern += 1
            else:
                reason = entry["unclassified_reason"] or "?"
                reason_by_class[cls][reason] += 1
                reason_all[reason] += 1

    total_unclassified = total_flagged - total_matched
    print("=" * 72)
    print("A) INVENTAR")
    print("=" * 72)
    print(f"soubory v cache: {files}")
    print(f"hry po dedupu (game_id+color, nejhlubsi): {len(games)}")
    print(
        "flagged tahy: "
        + ", ".join(f"{k}={flagged_by_class[k]}" for k in FLAGGED if flagged_by_class[k])
        + f"  celkem={total_flagged}"
    )

    print()
    print("=" * 72)
    print("B) POKRYTI FLAGGED TAHU (P0-7)")
    print("=" * 72)
    pct = 100 * total_matched / total_flagged if total_flagged else 0.0
    print(
        f"matched={total_matched} ({pct:.1f}%)  "
        f"unclassified={total_unclassified} ({100 - pct:.1f}%)"
    )
    for cls in FLAGGED:
        n = flagged_by_class[cls]
        if not n:
            continue
        st = status_by_class[cls]
        m = st["matched"]
        print(f"  {cls}: n={n} matched={m} ({100 * m / n:.1f}%) unclassified={st['unclassified']}")
    print(f"  tahy s vice patterny soucasne: {multi_pattern}")

    print()
    print("=" * 72)
    print("C) HISTOGRAM DUVODU UNCLASSIFIED")
    print("=" * 72)
    if not reason_all:
        print("  (zadny unclassified tah)")
    for reason, n in reason_all.most_common():
        share = 100 * n / total_unclassified if total_unclassified else 0.0
        print(f"  {reason}: {n} ({share:.1f}% z unclassified)")
    for cls in FLAGGED:
        rc = reason_by_class.get(cls)
        if rc:
            print(f"  {cls}: " + ", ".join(f"{k}={v}" for k, v in rc.most_common()))

    print()
    print("=" * 72)
    print("D) PATTERN ID MEZI MATCHED TAHY")
    print("=" * 72)
    if not pattern_ids:
        print("  (zadny pattern)")
    for pid, n in sorted(pattern_ids.items()):
        print(f"  {pid}: {n} her s vyskytem")

    print()
    print("=" * 72)
    print("E) KONTROLA KONZISTENCE")
    print("=" * 72)
    if invariant_errors:
        print(f"  CHYBY: {len(invariant_errors)}")
        for err in invariant_errors[:20]:
            print(f"    {err}")
        return 2
    print("  OK: coverage mapa == flagged tahy u vsech her")

    print()
    print("=" * 72)
    print("F) KVALITA PODKLADU (globalni, NENI duvod per-tah)")
    print("=" * 72)
    n = evidence["flagged"]
    if n:
        for key, label in (
            ("best_move_san", "best_move_san"),
            ("engine_lines", "engine_lines"),
            ("played_rank", "played_rank>=1"),
        ):
            print(f"  flagged s {label}: {evidence[key]}/{n} ({100 * evidence[key] / n:.1f}%)")
    print("  Chybejici PV je vlastnost cache/payloadu, ne tvar tahu;")
    print("  proto se nepromita do unclassified_reason (viz pattern_detector).")

    print()
    print("=" * 72)
    print("G) PROVENANCE (T1)")
    print("=" * 72)
    for key in ("dataset_sha256", "pattern_lib_sha256", "code_commit", "n_games", "n_moves"):
        print(f"  {key}: {provenance[key]}")

    if args.json_out:
        summary = {
            "provenance": provenance,
            "cache_files": files,
            "games_deduped": len(games),
            "flagged": total_flagged,
            "matched": total_matched,
            "unclassified": total_unclassified,
            "flagged_by_class": dict(flagged_by_class),
            "status_by_class": {cls: dict(counter) for cls, counter in status_by_class.items()},
            "unclassified_reasons": dict(reason_all),
            "pattern_ids": dict(pattern_ids),
            "multi_pattern_moves": multi_pattern,
            "evidence_coverage": {
                "flagged": evidence["flagged"],
                "best_move_san": evidence["best_move_san"],
                "engine_lines": evidence["engine_lines"],
                "played_rank": evidence["played_rank"],
            },
            "invariant_errors": invariant_errors,
        }
        out = pathlib.Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"  json_out: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
