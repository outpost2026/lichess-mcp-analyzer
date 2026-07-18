"""CLI pipeline: analyze user, detect patterns, write to KB.

Usage:
    uv run python scripts/run_pipeline.py <username> [--games N] [--depth D]

Requires LICHESS_TOKEN environment variable.
Requires Stockfish binary in PATH or STOCKFISH_PATH env var.
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main():
    parser = argparse.ArgumentParser(description="Lichess analyzer pipeline")
    parser.add_argument("username", type=str, help="Lichess username")
    parser.add_argument("--games", type=int, default=10, help="Games to analyze (5-50)")
    parser.add_argument("--depth", type=int, default=12, help="Stockfish depth (8-18)")
    parser.add_argument("--no-kb", action="store_true", help="Skip KB write")
    args = parser.parse_args()

    if not os.environ.get("LICHESS_TOKEN"):
        print("CHYBA: LICHESS_TOKEN env var is not set")
        sys.exit(1)

    from src.services.lichess_client import fetch_user_games, fetch_game_pgn
    from src.services.game_analyzer import analyze_pgn
    from src.services.diagnostician import diagnose
    from src.services.pattern_detector import PatternDetector

    username = args.username
    max_games = max(5, min(50, args.games))
    depth = max(8, min(18, args.depth))

    print(f"[1/4] Stahuji {max_games} her hrace {username}...")
    games_data = fetch_user_games(username, max_games=max_games)
    print(f"  Nalezeno {len(games_data)} her")

    print(f"[2/4] Analyzuji {min(len(games_data), max_games)} her (depth={depth})...")
    analyses = []
    for i, g in enumerate(games_data[:max_games]):
        game_id = g.get("id", "")
        try:
            pgn = fetch_game_pgn(game_id)
            color = "white"
            if (
                g.get("players", {}).get("black", {}).get("user", {}).get("name", "").lower()
                == username.lower()
            ):
                color = "black"
            analysis = analyze_pgn(pgn, player_color=color, depth=depth)
            analyses.append(analysis)
            print(
                f"  [{i + 1}/{len(games_data[:max_games])}] {game_id} OK ({len(analysis.moves)} tahu)"
            )
        except Exception as e:
            print(f"  [{i + 1}/{len(games_data[:max_games])}] {game_id} CHYBA: {e}")
            continue

    if not analyses:
        print("CHYBA: Zadna hra nebyla analyzovana")
        sys.exit(1)

    print(f"[3/4] Diagnostikuji {len(analyses)} her...")
    report = diagnose(analyses, username)
    print(f"  Celkovy ACPL: {report.total_acpl:.1f}")
    print(f"  Chyby: {report.blunder_count} blatantnich + {report.mistake_count} chyb")
    print(f"  Hlavni nedostatky:")
    for w in report.top_weaknesses:
        print(f"    - {w}")

    print(f"[4/4] Detekuji patterny...")
    detector = PatternDetector()
    metadata = {"username": username, "total_games": len(analyses)}
    matches = detector.detect_all(analyses, metadata)
    print(f"  Nalezeno {len(matches)} patternu:")
    for m in sorted(matches, key=lambda x: x.confidence, reverse=True):
        print(
            f"    - {m.pattern_id}: {m.pattern_name} (conf={m.confidence:.0%}, severity={m.severity})"
        )

    if not args.no_kb:
        from src.kb.writer import write_analysis_report, write_pattern_report

        analysis_path = write_analysis_report(
            username,
            {
                "games_analyzed": len(analyses),
                "total_acpl": report.total_acpl,
                "blunders": report.blunder_count,
                "mistakes": report.mistake_count,
                "inaccuracies": report.inaccuracy_count,
                "phase_weaknesses": report.phase_weaknesses,
                "leaky_openings": report.leaky_openings,
                "top_weaknesses": report.top_weaknesses,
            },
        )
        pattern_path = write_pattern_report(
            username,
            [
                {
                    "pattern_id": m.pattern_id,
                    "pattern_name": m.pattern_name,
                    "confidence": round(m.confidence, 2),
                    "severity": m.severity,
                }
                for m in matches
            ],
        )
        print(f"  KB write:")
        print(f"    - {analysis_path}")
        print(f"    - {pattern_path}")

    print(f"\nHotovo! {len(analyses)} her, {report.blunder_count} chyb, {len(matches)} patternu.")


if __name__ == "__main__":
    main()
