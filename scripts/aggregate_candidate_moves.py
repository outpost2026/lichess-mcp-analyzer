"""Agregace cache pro pattern detection: kandidátní tahy vs kritické momenty Stockfishu.

Offline, deterministický skript (žádný engine, žádná síť). Prochází
data/game_cache/*_{white,black}_d*.json a:

  A) inventář: počty analýz, tahů, klasifikací, fact sheets (covered/quiet
     x blunder/mistake/inaccuracy - fact sheet dostává každý flagged tah);
     dedup dle game_id+barvy+ply (tutéž hru analyzovanou ve více hloubkách
     počítá jednou, preferuje hlubší analýzu; obě barvy stejné hry zůstávají
     odděleně);
  B) sémantické rysy quiet skupin (bez pattern_matches): fáze (segment),
     cp bandy, SAN tvary (x/#/+), rank odehraného tahu, motiv;
  C) deterministické proxy mechanismů z FEN (python-chess, bez engine):
       hanging_piece        - po tahu je naše figura na cílovém poli napadena
                              soupeřem a nebráněna
       free_capture_after   - po odehraném tahu má soupeř k dispozici capture,
                              po které nemáme možnost vrátit (volný materiál)
       missed_capture       - engine best = capture, odehraný tah ne
       missed_mate          - engine best končí matem (SAN '#')
     proxy NENI mechanismus - je to kandidát s FP testem (REFACTOR_PLAN §355);
     proxy "ignored_threat" byl vyřazen: best move z pozice před tahem je tah
     NAŠÍ barvy, po našem tahu je pro soupeře ilegální vždy (naměřeno 0/0).
  D) sémantický digest: top N kritických momentů (blunder+mistake) podle
     |win_prob_delta| s kontextem (engine linie, okno tahů) pro opakovanou
     sémantickou analýzu té části hry (ručně nebo LLM offline).

  E) FP strop (klasifikátorový pohled): jak často by hanging_piece/
     free_capture_after vystřelily na TAHCHE best/good - základna pro
     posouzení, zda je proxy dostatečně diskriminační kandidát na pattern;
     + zakladna "engine best je capture" (L1) u flagged tahů, pocet
     stejneho cile u oboustrannych capture (K5 wrong-recapture kandidat)
     + mapa fazi (podil tahu a crit_rate dle phase segmentu).

Použití:
  uv run python -X utf8 scripts/aggregate_candidate_moves.py --top 40

Výstup je měřený - každé číslo pochází z cache, nic se nedosazuje.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

import chess

CACHE_DIR = pathlib.Path("data/game_cache")
CRITICAL = ("blunder", "mistake")
# (lo, hi, label); hi = exkluzivní horní hranice
CP_BANDS = (
    (0, 150, "0-149"),
    (150, 300, "150-299"),
    (300, 400, "300-399"),
    (400, 600, "400-599"),
    (600, 1000, "600-999"),
    (1000, 10**9, "1000+"),
)


def dedup_key(source: str) -> int:
    """Hloubka analýzy ze jména souboru (d14n150000 -> 14); vyšší = hlubší."""
    try:
        tail = source.rsplit("_d", 1)[-1].replace(".json", "")
        digits = "".join(ch for ch in tail if ch.isdigit())
        return int(digits or 0)
    except (ValueError, IndexError):
        return 0


def color_of(source: str) -> str:
    """Barva analyzovaného hráče ze jména souboru (…_white_d12.json)."""
    if "_white_" in source:
        return "white"
    if "_black_" in source:
        return "black"
    return "?"


def dedup_sheets(
    sheets: list[tuple[str, dict, dict | None, str]],
) -> list[tuple[str, dict, dict | None, str]]:
    """Stejná hra+barva analyzovaná ve více hloubkách = duplicita.

    Klíč = (game_id, color, ply): tutéž hru hrály obě barvy jako samostatné
    soubory (bRBSphxo_white + _black) - klíč bez barvy by je sloučil chybně.
    Preferuje hlubší analýzu; bez game_id ponechává řádky (nelze dedupl.).
    Naměřeno v top-40 digestu před opravou: 2 páry d12/d14.
    """
    best: dict[tuple, tuple[str, dict, dict | None, str]] = {}
    keep: list[tuple[str, dict, dict | None, str]] = []
    for row in sheets:
        src, fs, mv, cls = row
        gid, ply = fs.get("game_id"), fs.get("ply")
        if not gid or ply is None:
            keep.append(row)
            continue
        key = (gid, color_of(src), ply)
        if key not in best or dedup_key(src) > dedup_key(best[key][0]):
            best[key] = row
    keep.extend(best.values())
    return keep


def load_analyses(cache_dir: pathlib.Path) -> list[dict]:
    out = []
    for path in sorted(cache_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(data, dict) and isinstance(data.get("moves"), list):
            data["_source"] = path.name
            out.append(data)
    return out


def class_of(cp: float | None, fallback: str | None) -> str:
    """Klasifikace tahy; fallback = klasifikace z joined move, jinak z cp prahu."""
    if fallback:
        return fallback
    if cp is None:
        return "?"
    if cp >= 300:
        return "blunder"
    if cp >= 150:
        return "mistake"
    if cp >= 50:
        return "inaccuracy"
    return "cp<50"


def san_shape(san: str | None) -> str:
    if not san:
        return "none"
    if "#" in san:
        return "mate"
    if "x" in san and "+" in san:
        return "capture_check"
    if "x" in san:
        return "capture"
    if "+" in san:
        return "check"
    return "quiet"


def piece_of_san(san: str | None) -> str:
    if not san:
        return "?"
    if san[0] in "KQRBN":
        return san[0]
    return "P"  # pěšec (vč. exd5)


def board_after(fen_before: str, uci: str) -> chess.Board | None:
    try:
        board = chess.Board(fen_before)
        move = chess.Move.from_uci(uci)
        if move not in board.legal_moves:
            return None
        board.push(move)
        return board
    except (ValueError, AssertionError):
        return None


PIECE_VALUE = {
    chess.PAWN: 100,
    chess.KNIGHT: 300,
    chess.BISHOP: 300,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}


def free_capture_after(board: chess.Board) -> bool:
    """Soupeř (na tahu) má capture, po které mu figuru nemůžeme vrátit."""
    for mv in board.legal_moves:
        if not board.is_capture(mv):
            continue
        captured = board.piece_at(mv.to_square)
        if board.is_en_passant(mv):
            value = PIECE_VALUE[chess.PAWN]
        elif captured is None:
            continue
        else:
            value = PIECE_VALUE[captured.piece_type]
        if value <= 0:
            continue
        board.push(mv)
        recapturable = board.is_attacked_by(board.turn, mv.to_square)  # board.turn = my
        board.pop()
        if not recapturable:
            return True
    return False


def best_san_of(fs: dict, move: dict | None) -> str:
    """Nejlepší tah engineu: move.best_move_san, jinak L1 z engine_lines.

    Naměřeno 2026-11-12: best_move_san jen u 282/943 sheetů, L1 u 897/943,
    při průniku 0 nesouladů - fallback je bezpečný.
    """
    bms = (move or {}).get("best_move_san")
    if bms:
        return bms
    lines = fs.get("engine_lines") or []
    if lines and isinstance(lines[0], dict):
        return lines[0].get("move_san") or ""
    return ""


def proxy_labels(fs: dict, move: dict | None) -> list[str]:
    """Deterministické proxy mechanismu z FEN + engine best tahu (bez engine)."""
    labels: list[str] = []
    fen_before = fs.get("fen_before") or (move or {}).get("fen")
    played_uci = fs.get("move_played_uci")
    best_san = best_san_of(fs, move)
    played_san = fs.get("move_played_san") or (move or {}).get("move_san") or ""

    if best_san and "#" in best_san:
        labels.append("missed_mate")
    if "x" in best_san and "x" not in played_san:
        labels.append("missed_capture")

    if not fen_before or not played_uci:
        return labels
    board = board_after(fen_before, played_uci)
    if board is None:
        return labels

    # 1) hanging piece: figuru, na kterou jsme právě tahli, soupeř (na tahu
    #    po našem tahu = board.turn) napadá a my nebráníme (not board.turn).
    #    POZOR na invertci: po push je board.turn = SOUPEŘ. Chybu odhalil
    #    FP-floor test (41% na best tazich = obrácená detekce).
    last = board.move_stack[-1] if board.move_stack else None
    to_sq = last.to_square if last else None
    if to_sq is not None and board.piece_at(to_sq):
        attacked = board.is_attacked_by(board.turn, to_sq)
        defended = board.is_attacked_by(not board.turn, to_sq)
        if attacked and not defended:
            labels.append("hanging_piece")

    # 2) free capture: po našem tahu má soupeř k dispozici capture, které
    #    nemůžeme vrátit = volný materiál už v tuto chvíli (ne až "později")
    if free_capture_after(board):
        labels.append("free_capture_after")
    return labels


def band(cp: float) -> str:
    for lo, hi, label in CP_BANDS:
        if lo <= cp < hi:
            return label
    return "?"


def profile(group: list[tuple[str, dict, dict | None, str]], name: str) -> None:
    print()
    print(f"--- profil: {name} (n={len(group)}) ---")
    by_phase = collections.Counter((g[1].get("phase") or "?") for g in group)
    print("  phase(segment): " + ", ".join(f"{k}={v}" for k, v in by_phase.most_common()))
    by_shape = collections.Counter(san_shape(g[1].get("move_played_san")) for g in group)
    print("  SAN tvar: " + ", ".join(f"{k}={v}" for k, v in by_shape.most_common()))
    by_piece = collections.Counter(piece_of_san(g[1].get("move_played_san")) for g in group)
    print("  odehrana figura: " + ", ".join(f"{k}={v}" for k, v in by_piece.most_common()))
    by_band = collections.Counter(
        band(g[1]["centipawn_loss"]) for g in group if g[1].get("centipawn_loss") is not None
    )
    print("  cp band: " + ", ".join(f"{k}={v}" for k, v in sorted(by_band.items())))
    by_rank = collections.Counter(str(g[1].get("played_move_rank") or "?") for g in group)
    print("  played_move_rank: " + ", ".join(f"{k}={v}" for k, v in sorted(by_rank.items())))
    in_check = collections.Counter(str(bool((g[2] or {}).get("was_in_check"))) for g in group)
    print("  was_in_check: " + ", ".join(f"{k}={v}" for k, v in in_check.most_common()))
    motif = collections.Counter((g[2] or {}).get("motif_type") or "bez_motivu" for g in group)
    print("  motif: " + ", ".join(f"{k}={v}" for k, v in motif.most_common()))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cache-dir", default=str(CACHE_DIR))
    ap.add_argument("--top", type=int, default=40, help="pocet momentu v sementickem digestu")
    args = ap.parse_args()

    analyses = load_analyses(pathlib.Path(args.cache_dir))
    if not analyses:
        print("CHYBA: zadne analyzy v cache", file=sys.stderr)
        return 1

    depths = collections.Counter()
    classes = collections.Counter()
    moves_total = 0
    # (source, fact_sheet, joined_move, classification)
    sheets: list[tuple[str, dict, dict | None, str]] = []

    for a in analyses:
        src = a["_source"]
        depths[src.rsplit("_d", 1)[-1].replace(".json", "")] += 1
        by_ply = {m.get("ply"): m for m in a["moves"]}
        moves_total += len(a["moves"])
        for m in a["moves"]:
            classes[m.get("classification") or "?"] += 1
        for fs in a.get("blunder_fact_sheets") or []:
            mv = by_ply.get(fs.get("ply"))
            cls = class_of(fs.get("centipawn_loss"), (mv or {}).get("classification"))
            sheets.append((src, fs, mv, cls))

    n_raw = len(sheets)
    sheets = dedup_sheets(sheets)
    covered = [s for s in sheets if s[1].get("pattern_matches")]
    quiet = [s for s in sheets if not s[1].get("pattern_matches")]

    print("=" * 72)
    print("A) INVENTAR")
    print("=" * 72)
    print(f"analyz: {len(analyses)}  (depth: {dict(sorted(depths.items()))})")
    print(f"tahu celkem: {moves_total}")
    print("klasifikace: " + ", ".join(f"{k}={v}" for k, v in classes.most_common()))
    print(f"critical moments (blunder+mistake): {sum(classes[c] for c in CRITICAL)}")
    print(
        f"fact sheets: {len(sheets)} (pred dedup {n_raw}, odstraneno "
        f"{n_raw - len(sheets)} duplicit dle game_id+barvy+ply)"
        f"  covered={len(covered)}  quiet={len(quiet)}"
        f"  ({100 * len(quiet) / len(sheets):.1f}% quiet)"
    )
    # sheets x class x quiet/covered
    tab: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for group_name, group in (("covered", covered), ("quiet", quiet)):
        for s in group:
            tab[s[3]][group_name] += 1
    for cls in ("blunder", "mistake", "inaccuracy", "cp<50", "?"):
        if cls in tab:
            c = tab[cls]
            total = c["quiet"] + c["covered"]
            print(
                f"  sheets[{cls}]: total={total} covered={c['covered']} quiet={c['quiet']}"
                f" ({100 * c['quiet'] / total:.1f}% quiet)"
            )

    print()
    print("=" * 72)
    print("B) RYSY QUIET SKUPIN (quiet = bez pattern_matches)")
    print("=" * 72)
    profile([s for s in quiet if s[3] == "blunder"], "quiet BLUNDER (cil §355)")
    profile([s for s in quiet if s[3] in ("mistake", "inaccuracy")], "quiet MISTAKE+INACCURACY")
    profile([s for s in covered if s[3] == "blunder"], "covered BLUNDER (baseline FP)")

    # --- C) proxy mechanismy --------------------------------------------------
    print()
    print("=" * 72)
    print("C) PROXY MECHANISMY (deterministicky z FEN, bez engine)")
    print("=" * 72)
    print("POZOR: proxy neni potvrzeny mechanismus - kazdy je kandidat s FP testem (§355).")
    groups = {
        "quiet_blunder": [s for s in quiet if s[3] == "blunder"],
        "quiet_other": [s for s in quiet if s[3] in ("mistake", "inaccuracy")],
        "covered_blunder": [s for s in covered if s[3] == "blunder"],
    }
    for gname, group in groups.items():
        counts: collections.Counter = collections.Counter()
        no_proxy = 0
        for _src, fs, mv, _cls in group:
            labels = proxy_labels(fs, mv)
            if not labels:
                no_proxy += 1
            for lb in labels:
                counts[lb] += 1
        line = ", ".join(f"{k}={v}" for k, v in counts.most_common())
        print(f"  {gname} (n={len(group)}): {line or 'bez proxy'} , zadny_proxy={no_proxy}")

    # --- D) sementicky digest -------------------------------------------------
    print()
    print("=" * 72)
    print(f"D) SEMENTICKY DIGEST: top {args.top} kritickych momentu dle |win_prob_delta|")
    print("=" * 72)
    print("Kriterium dulezitosti dle Stockfishu: classification v (blunder, mistake).")
    moments = []
    for src, fs, mv, cls in sheets:
        if cls not in CRITICAL:
            continue
        wpd = fs.get("win_prob_delta")
        if wpd is None and mv:
            wpd = (mv.get("win_prob_after") or 0) - (mv.get("win_prob_before") or 0)
        if wpd is None:
            continue
        moments.append((abs(wpd), wpd, src, fs, mv, cls))
    moments.sort(key=lambda t: t[0], reverse=True)

    for i, (_abs, wpd, src, fs, mv, cls) in enumerate(moments[: args.top], 1):
        quiet_tag = "QUIET" if not fs.get("pattern_matches") else "covered"
        labels = proxy_labels(fs, mv)
        print()
        print(
            f"[{i}] {src} ply={fs.get('ply')} {fs.get('move_played_san')} "
            f"class={cls} phase={fs.get('phase')}"
        )
        print(
            f"    cp_loss={fs.get('centipawn_loss')} wpd={wpd:+.3f} "
            f"rank={fs.get('played_move_rank')} {quiet_tag} proxy={labels or ['zadny']}"
        )
        lines = fs.get("engine_lines") or []
        for ln in lines[:3]:
            pv = " ".join((ln.get("pv") or [])[:6])
            print(f"    L{ln.get('rank')}: {ln.get('move_san')} cp={ln.get('eval_cp')} pv: {pv}")
        cw = fs.get("context_window") or {}

        def _w(items: list) -> str:
            return " ".join(
                f"{it.get('move_san')}({it.get('ply')})"
                for it in (items or [])
                if isinstance(it, dict)
            )

        before = _w((cw.get("moves_before") or [])[-6:])
        after = _w((cw.get("moves_after") or [])[:6])
        print(f"    pred: ... {before}")
        print(f"    po:   {after} ...")

    print()
    print(f"digest: {min(args.top, len(moments))}/{len(moments)} kritickych momentu")

    # --- E) FP strop ---------------------------------------------------------
    print()
    print("=" * 72)
    print("E) FP STROP: proxy na TAHCHE (dedup dle game id, nejhlubsi analýza)")
    print("=" * 72)
    print("Otázka: jak často by proxy vystřelily na best/good tazich,")
    print("        kdyby se pouzily jako klasifikator? (lift = blunder/base)")
    games: dict[tuple, tuple[str, dict]] = {}
    for a in analyses:
        g = a.get("game") or {}
        gid = g.get("id") or g.get("game_id") or a["_source"]
        # klic vcetne barvy: oba hraci stejne hry = dve samostatne analyzy
        key = (gid, g.get("color") or color_of(a["_source"]))
        if key not in games or dedup_key(a["_source"]) > dedup_key(games[key][0]):
            games[key] = (a["_source"], a)

    fp_tab: collections.Counter = collections.Counter()
    phase_tab: collections.Counter = collections.Counter()
    l1_cap: collections.Counter = collections.Counter()
    l1_n: collections.Counter = collections.Counter()
    same_tg = 0
    for _gsrc, a in games.values():
        ply_index = {m.get("ply"): m for m in a["moves"]}
        for fs in a.get("blunder_fact_sheets") or []:
            mv = ply_index.get(fs.get("ply"))
            if not mv:
                continue
            bs = best_san_of(fs, mv)
            if not bs:
                continue
            cls_e = class_of(fs.get("centipawn_loss"), mv.get("classification"))
            l1_n[cls_e] += 1
            if "x" in bs:
                l1_cap[cls_e] += 1
            pu = fs.get("move_played_uci") or ""
            bu = mv.get("best_move_uci") or ""
            if "x" in (fs.get("move_played_san") or "") and "x" in bs and pu and bu:
                if pu[-2:] == bu[-2:]:
                    same_tg += 1
        for m in a["moves"]:
            cls_e = m.get("classification") or "?"
            phase_tab[(m.get("phase") or "?", cls_e)] += 1
            fen, uci = m.get("fen"), m.get("move_uci")
            if not fen or not uci:
                continue
            b = board_after(fen, uci)
            if b is None:
                continue
            fp_tab[(cls_e, "n")] += 1
            last = b.move_stack[-1] if b.move_stack else None
            to_sq = last.to_square if last else None
            hang = bool(
                to_sq is not None
                and b.piece_at(to_sq)
                and b.is_attacked_by(b.turn, to_sq)
                and not b.is_attacked_by(not b.turn, to_sq)
            )
            fp_tab[(cls_e, "hang")] += int(hang)
            fp_tab[(cls_e, "free")] += int(free_capture_after(b))

    for cls_e in ("best", "good", "inaccuracy", "mistake", "blunder"):
        n = fp_tab[(cls_e, "n")]
        if n:
            print(
                f"  tahy[{cls_e}]: n={n} hang={fp_tab[(cls_e, 'hang')]} "
                f"({100 * fp_tab[(cls_e, 'hang')] / n:.1f}%) "
                f"free={fp_tab[(cls_e, 'free')]} "
                f"({100 * fp_tab[(cls_e, 'free')] / n:.1f}%)"
            )
    for cls_e in ("blunder", "mistake", "inaccuracy"):
        n = l1_n[cls_e]
        if n:
            print(
                f"  L1 best capture, sheets[{cls_e}]: {l1_cap[cls_e]}/{n} "
                f"({100 * l1_cap[cls_e] / n:.1f}%)"
            )
    print(f"  K5 kandidat (oba capture, stejny cil): {same_tg}")

    grand = sum(phase_tab.values())
    print("  mapa fazi (kde jsou kriticke momenty; zaklad = podil tahu):")
    for ph in ("opening", "middlegame", "endgame"):
        n_ph = sum(v for (p2, _c), v in phase_tab.items() if p2 == ph)
        bl = phase_tab[(ph, "blunder")]
        mi = phase_tab[(ph, "mistake")]
        if n_ph and grand:
            print(
                f"    {ph}: moves={n_ph} ({100 * n_ph / grand:.1f}%) "
                f"blunder={bl} ({100 * bl / n_ph:.1f}%) "
                f"mistake={mi} crit_rate={100 * (bl + mi) / n_ph:.1f}%"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
