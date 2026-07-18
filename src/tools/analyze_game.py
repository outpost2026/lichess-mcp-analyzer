from src.app import app
from src.services.game_analyzer import analyze_pgn
from src.services.lichess_client import fetch_game_pgn


@app.tool("lichess_analyze_game")
async def lichess_analyze_game(
    game_id: str = "", pgn: str = "", username: str = "", color: str = "white", depth: int = 14
):
    """Analyzes a chess game move by move using Stockfish.

    Args:
        game_id: Lichess game ID (8 chars), or empty if using PGN directly
        pgn: PGN string of the game, or empty if using game_id
        username: Your username (to determine your color), or specify color
        color: Your color if username not provided ('white' or 'black')
        depth: Stockfish analysis depth (8-24, default 14)
    """
    depth = max(8, min(24, depth))
    try:
        if game_id and not pgn:
            pgn = fetch_game_pgn(game_id)
        if not pgn:
            return {"error": "Provide either game_id or pgn"}
        result = analyze_pgn(pgn, player_color=color, depth=depth)
        return {
            "game": {
                "id": result.game.id,
                "opening": result.game.opening,
                "eco": result.game.opening_eco,
                "result": result.game.result,
                "opponent": result.game.opponent_name,
                "date": result.game.date,
            },
            "stats": {
                "total_acpl": round(result.total_acpl, 1),
                "blunders": len(result.blunders),
                "mistakes": len(result.mistakes),
                "inaccuracies": len(result.inaccuracies),
                "total_moves": len(result.moves),
            },
            "blunders": [
                f"Move {m.ply}: {m.move_san} (loss {m.centipawn_loss:.0f}cp)"
                for m in result.blunders[:10]
            ],
        }
    except Exception as e:
        return {"error": str(e)}
