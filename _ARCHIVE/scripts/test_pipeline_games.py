"""Full pipeline test: analyze all 6 reference games from pitevni kniha."""

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lichess_analyzer_mcp.services.lichess_client import fetch_game_pgn
from lichess_analyzer_mcp.services.game_analyzer import analyze_pgn

GAMES = [
    ("rnoxbE5l", "white"),
    ("5ZgvxdL2", "white"),
    ("WwXPn8ye", "white"),
    ("Zz5EHOCF", "white"),
    ("4UrazyU5", "white"),
    ("BmraKP18", "white"),
]


def test():
    results = []
    for gid, color in GAMES:
        print(f"\n=== Game {gid} ({color}) ===")
        try:
            pgn = fetch_game_pgn(gid)
            result = analyze_pgn(pgn, player_color=color, depth=14, game_id=gid)
            s = result.game
            print(
                f"  Players: {s.player_name or '?'} ({s.player_rating or '?'}) vs {s.opponent_name} ({s.opponent_rating or '?'})"
            )
            print(f"  Result: {s.result}")
            print(f"  Accuracy: {result.accuracy:.1f}%")
            print(f"  Total ACPL: {result.total_acpl:.1f}")
            print(
                f"  Blunders: {len(result.blunders)}  Mistakes: {len(result.mistakes)}  Inaccuracies: {len(result.inaccuracies)}"
            )
            print(f"  Patterns: {len(result.patterns) if hasattr(result, 'patterns') else 'N/A'}")
            print(f"  Opening: {s.opening} ({s.opening_eco})")
            phases = getattr(result, "phase_stats", {})
            if phases:
                print(f"  Phases: {list(phases.keys())}")
                for p, st in phases.items():
                    acc = st.get("accuracy", 0)
                    print(
                        f"    {p}: acc={acc:.1f}%, acpl={st.get('acpl', 0):.1f}, moves={st.get('move_count', 0)}"
                    )
            a = result.total_acpl
            results.append(
                {"game": gid, "status": "OK", "acpl": a, "blunders": len(result.blunders)}
            )
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback

            traceback.print_exc()
            results.append({"game": gid, "status": "ERROR"})

    acpl_list = [r["acpl"] for r in results if r["status"] == "OK"]
    blunder_list = [r["blunders"] for r in results if r["status"] == "OK"]
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    ok = sum(1 for r in results if r["status"] == "OK")
    print(f"  Games: {ok}/{len(results)} OK, {len(results) - ok} FAIL")
    if acpl_list:
        print(f"  Avg ACPL: {sum(acpl_list) / len(acpl_list):.1f}")
        print(f"  Total blunders: {sum(blunder_list)}")
        ranked = sorted(results, key=lambda r: r.get("acpl", 999))
        print(f"  Ranked by ACPL:")
        for i, r in enumerate(ranked, 1):
            print(
                f"    {i}. {r['game']} - ACPL={r.get('acpl', '?')}, blunders={r.get('blunders', '?')}"
            )


if __name__ == "__main__":
    test()
