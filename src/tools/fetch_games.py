from mcp.server import Server
from src.services.lichess_client import fetch_user_games


def register_fetch_games(server: Server):
    @server.tool("lichess_fetch_games")
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
                result.append(
                    {
                        "id": g.get("id", ""),
                        "date": str(g.get("createdAt", "")),
                        "opening": g.get("opening", {}).get("name", "")
                        if isinstance(g.get("opening"), dict)
                        else "",
                        "result": g.get("result", ""),
                        "white": g.get("players", {})
                        .get("white", {})
                        .get("user", {})
                        .get("name", ""),
                        "black": g.get("players", {})
                        .get("black", {})
                        .get("user", {})
                        .get("name", ""),
                        "white_elo": g.get("players", {}).get("white", {}).get("rating", ""),
                        "black_elo": g.get("players", {}).get("black", {}).get("rating", ""),
                        "time_control": g.get("speed", ""),
                        "url": f"https://lichess.org/{g.get('id', '')}",
                    }
                )
            return {"games": result, "count": len(result), "username": username}
        except Exception as e:
            return {"error": str(e)}
