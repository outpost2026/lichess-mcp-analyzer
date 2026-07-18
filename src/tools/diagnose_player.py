from src.app import app
from src.services.lichess_client import fetch_user_games, fetch_game_pgn
from src.services.game_analyzer import analyze_pgn
from src.services.diagnostician import diagnose
from concurrent.futures import ThreadPoolExecutor, as_completed


@app.tool("lichess_diagnose_player")
async def lichess_diagnose_player(username: str, max_games: int = 20, depth: int = 12):
    """Diagnoses a player's weaknesses across multiple games.

    Analyzes recent games and identifies recurring tactical blind spots,
    phase weaknesses (opening/middlegame/endgame), leaky openings,
    and pattern frequencies.

    Args:
        username: Lichess username
        max_games: Number of recent games to analyze (5-50)
        depth: Stockfish depth for analysis (8-18, lower = faster)
    """
    max_games = max(5, min(50, max_games))
    depth = max(8, min(18, depth))
    try:
        games_data = fetch_user_games(username, max_games=max_games)
        analyses = []

        def analyze_one(g):
            game_id = g.get("id", "")
            try:
                pgn = fetch_game_pgn(game_id)
                color = "white"
                if (
                    g.get("players", {}).get("black", {}).get("user", {}).get("name", "").lower()
                    == username.lower()
                ):
                    color = "black"
                return analyze_pgn(pgn, player_color=color, depth=depth)
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=min(4, max_games)) as pool:
            futures = [pool.submit(analyze_one, g) for g in games_data[:max_games]]
            for f in as_completed(futures):
                a = f.result()
                if a:
                    analyses.append(a)

        if not analyses:
            return {"error": "No games could be analyzed"}
        report = diagnose(analyses, username)
        return {
            "username": username,
            "games_analyzed": report.total_games_analyzed,
            "total_acpl": round(report.total_acpl, 1),
            "blunders": report.blunder_count,
            "mistakes": report.mistake_count,
            "inaccuracies": report.inaccuracy_count,
            "phase_weaknesses": report.phase_weaknesses,
            "leaky_openings": report.leaky_openings[:3],
            "top_weaknesses": report.top_weaknesses,
        }
    except Exception as e:
        return {"error": str(e)}
