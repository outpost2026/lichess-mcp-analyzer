"""Měření skutečné dvoučlenné MDL pro proxy mechanismy (P2, krok B).

Offline, deterministický skript (žádný engine, žádná síť). Pro každou proxy
spočítá kontingenční tabulku na úrovni TAHU:

  flagged = tahy klasifikované jako `blunder`/`mistake`
  control = tahy klasifikované jako `best` (univerzum `good_moves_control`)

Obě skupiny pocházejí ze stejného zdroje (`moves`), takže jsou srovnatelné.
`blunder_fact_sheets` se záměrně nepoužívají: pokrývají jen podmnožinu
kritických tahů (679 z 2137), což by do flagged skupiny vneslo selektivní bias.

a porovná dva kódovací modely:

  L_null  = jeden společný podíl (p_pool)
  L_model = dva podíly (flagged vs control) + parametrická cena 0.5*log2(N)

  gain_bits = L_null - L_model

Proč tah a ne hra: proxy je per-move vlastnost pozice (`free_capture_after`,
`hanging_piece`, ...). Hra jako jednotka by míchala 40 tahů do jednoho bitu.
MDL se proto měří na tazích; herní kontrakt (`n_games`/`n_units`) zůstává
v `PatternMatch` a v tomto skriptu se nepoužívá.

Co se NESMÍ dělat: interpretovat `gain_bits` napříč datasety různé velikosti.
Combinatoriální člen roste ~0.5*log2(n); srovnávat lze jen `gain_per_unit`.

Použití:
  uv run python -X utf8 scripts/measure_pattern_mdl.py
  uv run python -X utf8 scripts/measure_pattern_mdl.py --json-out data/mdl.json
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from aggregate_candidate_moves import (  # noqa: E402
    CACHE_DIR,
    color_of,
    dedup_key,
    load_analyses,
    proxy_labels,
)
from lichess_analyzer_mcp.services.mdl import two_part_mdl  # noqa: E402
from lichess_analyzer_mcp.services.statistics import rate_ratio_with_ci  # noqa: E402

CRITICAL = ("blunder", "mistake")
PROXIES = ("free_capture_after", "hanging_piece", "missed_capture", "missed_mate")
CONTROL_CLASS = "best"
# Proxy, které porovnávají odehraný tah s engine best. Na best-only controlu
# jsou strukturálně nulové (odehraný tah == best), takže FP strop neměřitelný.
BEST_COMPARISON_PROXIES = {
    "missed_capture": (
        "definitionally zero on a best-only control: played move equals the "
        "engine best, so no false-positive ceiling is measurable"
    ),
    "missed_mate": (
        "definitionally zero on a best-only control: played move equals the "
        "engine best, so no false-positive ceiling is measurable"
    ),
}


def dedup_games(analyses: list[dict]) -> list[dict]:
    """Jedna analýza na (game_id, color); při duplicitě bere nejhlubší."""
    best: dict[tuple, dict] = {}
    for a in analyses:
        g = a.get("game") or {}
        gid = g.get("id") or g.get("game_id") or a["_source"]
        key = (gid, g.get("color") or color_of(a["_source"]))
        if key not in best or dedup_key(a["_source"]) > dedup_key(best[key]["_source"]):
            best[key] = a
    return list(best.values())


def move_sheet(move: dict) -> dict:
    """Převod tahu z `moves` na tvar fact sheetu, který `proxy_labels` očekává."""
    return {
        "fen_before": move.get("fen") or "",
        "move_played_uci": move.get("move_uci") or "",
        "move_played_san": move.get("move_san") or "",
        "engine_lines": move.get("engine_lines") or [],
    }


def collect(
    analyses: list[dict],
) -> tuple[
    collections.Counter, collections.Counter, dict, collections.Counter, collections.Counter
]:
    """Vrátí (flagged_hits, control_hits, inventory, flagged_games, control_games).

    `*_hits` počítají tahy, `*_games` počítají hry s alespoň jedním výskytem
    (herní jednotka je relevantní pro admission gate, §2.3).
    """
    flagged_hits: collections.Counter = collections.Counter()
    control_hits: collections.Counter = collections.Counter()
    flagged_games: collections.Counter = collections.Counter()
    control_games: collections.Counter = collections.Counter()
    inventory = {
        "analyses": len(analyses),
        "games": 0,
        "flagged_moves": 0,
        "control_moves": 0,
        "flagged_without_proxy": 0,
        "control_without_proxy": 0,
        "flagged_with_best_san": 0,
        "control_with_best_san": 0,
    }

    for a in dedup_games(analyses):
        inventory["games"] += 1
        game_flagged: set[str] = set()
        game_control: set[str] = set()
        for mv in a.get("moves") or []:
            if not mv.get("fen") or not mv.get("move_uci"):
                continue
            cls = mv.get("classification") or ""
            if cls in CRITICAL:
                hits, total, empty, best_san = (
                    flagged_hits,
                    "flagged_moves",
                    "flagged_without_proxy",
                    "flagged_with_best_san",
                )
                game_labels = game_flagged
            elif cls == CONTROL_CLASS:
                hits, total, empty, best_san = (
                    control_hits,
                    "control_moves",
                    "control_without_proxy",
                    "control_with_best_san",
                )
                game_labels = game_control
            else:
                continue
            labels = proxy_labels(move_sheet(mv), mv)
            inventory[total] += 1
            inventory[best_san] += int(bool(mv.get("best_move_san")))
            if not labels:
                inventory[empty] += 1
            else:
                hits["ANY"] += 1
                game_labels.add("ANY")
            for label in labels:
                hits[label] += 1
                game_labels.add(label)

        for label in game_flagged:
            flagged_games[label] += 1
        for label in game_control:
            control_games[label] += 1

    return flagged_hits, control_hits, inventory, flagged_games, control_games


def evaluate(
    label: str,
    flagged: int,
    control: int,
    inv: dict,
    games1: int = 0,
    games0: int = 0,
) -> dict:
    """Jeden řádek měření: podíly, lift a MDL."""
    n1, n0 = inv["flagged_moves"], inv["control_moves"]
    mdl = two_part_mdl(flagged, n1, control, n0, n_params=1)
    ratio = rate_ratio_with_ci(flagged, n1, control, n0)

    row = {
        "proxy": label,
        "k1": flagged,
        "n1": n1,
        "k0": control,
        "n0": n0,
        "games1": games1,
        "games0": games0,
        "games_total": inv["games"],
        "rate1": round(flagged / n1, 4) if n1 else None,
        "rate0": round(control / n0, 4) if n0 else None,
        "lift": ratio["lift"] if ratio else None,
        "lift_ci": ({"low": ratio["ci_low"], "high": ratio["ci_high"]} if ratio else None),
        "lift_unavailable_reason": None
        if ratio
        else "control group has zero events; lift is not estimable",
        "mdl": mdl,
    }
    if mdl is None:
        row["mdl_unavailable_reason"] = "undefined contingency table"
    elif not mdl["estimable"] and control == 0 and label in BEST_COMPARISON_PROXIES:
        mdl["non_estimable_reason"] = BEST_COMPARISON_PROXIES[label]
    return row


def fmt_pct(k: int, n: int) -> str:
    return f"{k}/{n} ({100 * k / n:.1f}%)" if n else f"{k}/{n} (-)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache-dir", default=str(CACHE_DIR))
    ap.add_argument("--json-out", default="", help="zapsat výsledky jako JSON")
    args = ap.parse_args()

    analyses = load_analyses(pathlib.Path(args.cache_dir))
    if not analyses:
        print("CHYBA: zadne analyzy v cache", file=sys.stderr)
        return 1

    flagged_hits, control_hits, inv, flagged_games, control_games = collect(analyses)
    rows = [
        evaluate(p, flagged_hits[p], control_hits[p], inv, flagged_games[p], control_games[p])
        for p in PROXIES
    ]
    # Kompozitní klasifikátor: vystřelí jakákoli proxy.
    rows.append(
        evaluate(
            "ANY",
            flagged_hits["ANY"],
            control_hits["ANY"],
            inv,
            flagged_games["ANY"],
            control_games["ANY"],
        )
    )

    print("=" * 78)
    print("DVOUCLENNA MDL: proxy mechanismy na tazich (flagged vs best)")
    print("=" * 78)
    print(
        f"analyzy={inv['analyses']}  hry_po_dedupu={inv['games']}  "
        f"flagged={inv['flagged_moves']}  control(best)={inv['control_moves']}"
    )
    print(
        f"bez proxy: flagged={inv['flagged_without_proxy']} "
        f"({100 * inv['flagged_without_proxy'] / max(inv['flagged_moves'], 1):.1f}%)  "
        f"control={inv['control_without_proxy']} "
        f"({100 * inv['control_without_proxy'] / max(inv['control_moves'], 1):.1f}%)"
    )
    print(
        f"best_san coverage: flagged={inv['flagged_with_best_san']}/{inv['flagged_moves']}  "
        f"control={inv['control_with_best_san']}/{inv['control_moves']} "
        f"(missed_* proxy bez best SAN nemeri)"
    )
    print()
    header = (
        f"{'proxy':<20} {'flagged':>18} {'control':>18} {'lift':>8} "
        f"{'gain_bits':>10} {'per_unit':>10}  verdict"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        mdl = row["mdl"] or {}
        lift = f"{row['lift']:.2f}" if row["lift"] is not None else "n/a"
        if mdl.get("estimable"):
            gain = f"{mdl['gain_bits']:.3f}"
            per_unit = f"{mdl['gain_per_unit']:.4f}"
        else:
            gain = per_unit = "-"
        print(
            f"{row['proxy']:<20} {fmt_pct(row['k1'], row['n1']):>18} "
            f"{fmt_pct(row['k0'], row['n0']):>18} {lift:>8} "
            f"{gain:>10} {per_unit:>10}  {mdl.get('verdict', 'n/a')}"
        )
    notes = [r for r in rows if r["mdl"] and not r["mdl"].get("estimable")]
    if notes:
        print()
        print("NEESTIMOVATELNE (nulovy event v jedne skupine, MLE na hranici):")
        for r in notes:
            print(f"  {r['proxy']}: {r['mdl']['non_estimable_reason']}")
    print()
    print("POZOR: proxy neni potvrzeny mechanismus. Kladny gain = split na dva")
    print("podily se vyplati; zaporny = jeden spolecny podil staci (proxy nic nenese).")
    print("gain_bits neni srovnatelny napric datasety; srovnavej jen gain_per_unit.")

    if args.json_out:
        out = pathlib.Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "inventory": inv,
            "unit": "move",
            "control_universe": "good_moves_control (classification == best)",
            "rows": rows,
        }
        out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"JSON: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
