"""Analyze a single game and output JSON to a file."""

import argparse, json, sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("game_id", type=str)
    parser.add_argument("--color", default=None)
    parser.add_argument("--depth", type=int, default=14)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    from lichess_analyzer_mcp.services.lichess_client import fetch_game_pgn
    from lichess_analyzer_mcp.services.game_analyzer import analyze_pgn

    pgn = fetch_game_pgn(args.game_id)
    color = args.color
    if color is None:
        if os.environ.get("EXPECTED_COLOR"):
            color = os.environ["EXPECTED_COLOR"]
        else:
            color = "white"

    analysis = analyze_pgn(pgn, player_color=color, depth=args.depth, game_id=args.game_id)

    s = analysis.game
    result = {
        "game_id": args.game_id,
        "branch": os.environ.get("CURRENT_BRANCH", "unknown"),
        "color": color,
        "players": {
            "player": {"name": s.player_name, "rating": s.player_rating},
            "opponent": {"name": s.opponent_name, "rating": s.opponent_rating},
        },
        "result": s.result,
        "accuracy": analysis.accuracy,
        "total_acpl": analysis.total_acpl,
        "blunders": len(analysis.blunders),
        "mistakes": len(analysis.mistakes),
        "inaccuracies": len(analysis.inaccuracies),
        "opening": {"name": s.opening, "eco": s.opening_eco},
        "moves_count": len(analysis.moves),
        "phase_stats": getattr(analysis, "phase_stats", {}),
        "time_control": s.time_control,
        "patterns": len(getattr(analysis, "patterns", [])),
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    print(f"Wrote {args.output}")
    summary = {
        "game": args.game_id,
        "acpl": result["total_acpl"],
        "accuracy": result["accuracy"],
        "blunders": result["blunders"],
        "mistakes": result["mistakes"],
        "inaccuracies": result["inaccuracies"],
    }
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
