"""PGN import tool — analyze any PGN through the same Stockfish pipeline."""

from datetime import datetime

from lichess_analyzer_mcp.app import app
from lichess_analyzer_mcp.services.game_analyzer import analyze_pgn
from lichess_analyzer_mcp.resources.analysis_resources import store_analysis


@app.tool("lichess_import_pgn")
async def lichess_import_pgn(
    pgn: str,
    color: str = "white",
    depth: int = 14,
    game_id: str = "",
):
    """Import and analyze a chess game from a PGN string.

    Parses any PGN (lichess, chess.com, GM games, custom PGN) through the same
    Stockfish pipeline used for online games. Returns per-move evaluation,
    classification (blunder/mistake/inaccuracy/good/best), and phase detection.
    Results are stored in L2 Resources for later retrieval.

    Use this to:
    - Analyze your own games from any platform
    - Import GM games and compare against your patterns (via lichess_match_patterns)
    - Analyze opponent games you have PGN for
    - Build a custom game library from PGN files

    Args:
        pgn: Full PGN string of the game (including headers)
        color: Your color ('white' or 'black', default 'white')
        depth: Stockfish analysis depth (8-24, default 14)
        game_id: Optional game identifier (auto-detected from PGN Site header if empty)
    """
    depth = max(8, min(24, depth))
    try:
        result = analyze_pgn(
            pgn,
            player_color=color,
            depth=depth,
            game_id=game_id or None,
            use_cache=True,
        )

        key = f"import_{result.game.id or 'custom'}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        store_analysis(
            key,
            {
                "game": result.game.to_dict(),
                "stats": {
                    "total_acpl": result.total_acpl,
                    "blunders": len(result.blunders),
                    "mistakes": len(result.mistakes),
                    "inaccuracies": len(result.inaccuracies),
                    "total_moves": len(result.moves),
                },
                "moves": [m.to_dict() for m in result.moves],
                "source": "pgn_import",
            },
        )

        return {
            "game": {
                "id": result.game.id or key,
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
                f"Move {m.ply}: {m.move_san} (loss {m.centipawn_loss:.0f}cp, phase={m.phase})"
                for m in result.blunders[:10]
            ],
            "resource_uri": f"lichess://analysis/{key}",
        }
    except Exception as e:
        return {"error": str(e)}
