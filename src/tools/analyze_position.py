from src.app import app
from src.services.engine_client import analyze_position
from src.services.lichess_client import fetch_cloud_eval


@app.tool("lichess_analyze_position")
async def lichess_analyze_position(fen: str, depth: int = 18, use_cloud: bool = True):
    """Analyzes a chess position using Stockfish or Lichess cloud eval.

    Args:
        fen: FEN string of the position
        depth: Stockfish analysis depth (8-24, default 18)
        use_cloud: Try Lichess cloud eval first (faster if cached)
    """
    depth = max(8, min(24, depth))
    try:
        cloud = None
        if use_cloud:
            cloud = fetch_cloud_eval(fen)
        lines = analyze_position(fen, depth=depth, multipv=3)
        top_lines = []
        for line in lines:
            top_lines.append(
                {
                    "depth": line["depth"],
                    "score_cp": line["score_cp"],
                    "mate": line["mate"],
                    "pv": [m.uci() if hasattr(m, "uci") else str(m) for m in line["pv"]],
                    "pv_san": line["pv_san"],
                }
            )
        result = {
            "fen": fen,
            "analysis_depth": depth,
            "top_lines": top_lines,
        }
        if cloud:
            result["cloud_eval"] = cloud
        return result
    except Exception as e:
        return {"error": str(e)}
