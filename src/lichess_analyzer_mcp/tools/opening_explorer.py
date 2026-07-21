from lichess_analyzer_mcp.app import app
from lichess_analyzer_mcp.services.lichess_client import fetch_opening_explorer


@app.tool("lichess_opening_explorer")
async def lichess_opening_explorer(fen: str, source: str = "lichess"):
    """Looks up a position in the Lichess Opening Explorer.

    Args:
        fen: FEN string of the position
        source: Database - 'lichess' (public games) or 'masters' (OTB master games)
    """
    if source not in ("lichess", "masters"):
        return {"error": "source must be 'lichess' or 'masters'"}
    try:
        data = fetch_opening_explorer(fen, source=source)
        moves = []
        for m in data.get("moves", []):
            moves.append(
                {
                    "uci": m.get("uci", ""),
                    "san": m.get("san", ""),
                    "white": m.get("white", 0),
                    "black": m.get("black", 0),
                    "draws": m.get("draws", 0),
                    "total": m.get("white", 0) + m.get("black", 0) + m.get("draws", 0),
                    "win_rate": round(
                        m.get("white", 0)
                        / max(1, m.get("white", 0) + m.get("black", 0) + m.get("draws", 0))
                        * 100,
                        1,
                    ),
                }
            )
        moves.sort(key=lambda x: x["total"], reverse=True)
        return {
            "fen": fen,
            "source": source,
            "total_games": data.get("total", 0),
            "top_moves": moves[:10],
            "opening": data.get("opening", {}),
        }
    except Exception as e:
        return {"error": str(e)}
