import json
from datetime import datetime
from lichess_analyzer_mcp.app import app
from lichess_analyzer_mcp.services.lichess_client import fetch_user_games


def _safe(val):
    if isinstance(val, datetime):
        return val.isoformat()
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return val


@app.tool("lichess_fetch_games")
async def lichess_fetch_games(username: str, max_games: int = 10, source: str = "lichess"):
    """Stahne recent hry hrace z Lichess/Chess.com.

    Args:
        username: Lichess nebo Chess.com username
        max_games: Maximalni pocet her (1-50)
        source: Platforma - 'lichess' nebo 'chesscom'
    """
    if source not in ("lichess", "chesscom"):
        return {"error": "source must be 'lichess' or 'chesscom'"}
    max_games = max(1, min(50, max_games))
    try:
        games = fetch_user_games(username, max_games=max_games)
        result = []
        for g in games:
            opening = g.get("opening", {})
            players = g.get("players", {})
            white = players.get("white", {})
            black = players.get("black", {})
            result.append(
                {
                    "id": g.get("id", ""),
                    "date": _safe(g.get("createdAt", "")),
                    "opening": opening.get("name", "") if isinstance(opening, dict) else "",
                    "result": g.get("result", ""),
                    "white": white.get("user", {}).get("name", ""),
                    "black": black.get("user", {}).get("name", ""),
                    "white_elo": white.get("rating", ""),
                    "black_elo": black.get("rating", ""),
                    "time_control": g.get("speed", ""),
                    "url": f"https://lichess.org/{g.get('id', '')}",
                }
            )
        return {"games": result, "count": len(result), "username": username}
    except Exception as e:
        return {"error": str(e)}
