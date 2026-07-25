import json
from datetime import datetime
from lichess_analyzer_mcp.app import app
from lichess_analyzer_mcp.services.lichess_client import fetch_user_games, fetch_user_games_metadata


def _safe(val):
    if isinstance(val, datetime):
        return val.isoformat()
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return val


@app.tool("lichess_fetch_games")
async def lichess_fetch_games(
    username: str, max_games: int = 10, source: str = "lichess", result: str = "all"
):
    """Stahne recent hry hrace z Lichess/Chess.com.

    Args:
        username: Lichess nebo Chess.com username
        max_games: Maximalni pocet her (1-50)
        source: Platforma - 'lichess' nebo 'chesscom'
        result: Filtr dle vysledku - 'all', 'win', 'loss', 'draw'
    """
    if source not in ("lichess", "chesscom"):
        return {"error": "source must be 'lichess' or 'chesscom'"}
    if result not in ("all", "win", "loss", "draw"):
        return {"error": "result must be 'all', 'win', 'loss', or 'draw'"}
    max_games = max(1, min(50, max_games))
    try:
        games = fetch_user_games(username, max_games=max_games, result=result)
        from lichess_analyzer_mcp.services.lichess_client import _game_result_for_player

        items = []
        for g in games:
            opening = g.get("opening", {})
            players = g.get("players", {})
            white = players.get("white", {})
            black = players.get("black", {})
            game_result = _game_result_for_player(g, username)
            items.append(
                {
                    "id": g.get("id", ""),
                    "date": _safe(g.get("createdAt", "")),
                    "opening": opening.get("name", "") if isinstance(opening, dict) else "",
                    "result": game_result or "",
                    "status": g.get("status", ""),
                    "winner": g.get("winner"),
                    "white": white.get("user", {}).get("name", ""),
                    "black": black.get("user", {}).get("name", ""),
                    "white_elo": white.get("rating", ""),
                    "black_elo": black.get("rating", ""),
                    "time_control": g.get("speed", ""),
                    "url": f"https://lichess.org/{g.get('id', '')}",
                }
            )
        return {"games": items, "count": len(items), "username": username, "filter": result}
    except Exception as e:
        return {"error": str(e)}


@app.tool("lichess_games_index")
async def lichess_games_index(username: str):
    """Vrati games index cache — rychly prehled her dle resultu (win/loss/draw).

    Pouzij po lichess_fetch_games pro okamzity prehled bez loadovani plnych dat.
    Vraci: total, by_result (pocty her + ID), metadata kazde hry.

    Args:
        username: Lichess username
    """
    try:
        meta = fetch_user_games_metadata(username)
        if meta is None:
            return {
                "error": "No cached data found. Call lichess_fetch_games first.",
                "hint": f"lichess_fetch_games(username='{username}', max_games=50, result='all')",
            }
        by_result = meta.get("by_result", {})
        summary = {}
        for res_key in ("win", "loss", "draw"):
            ids = by_result.get(res_key, [])
            summary[res_key] = {"count": len(ids), "game_ids": ids}
        return {
            "username": username,
            "total": meta.get("total", 0),
            "by_result": summary,
        }
    except Exception as e:
        return {"error": str(e)}
