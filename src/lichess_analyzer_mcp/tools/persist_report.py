"""On-demand persistence MCP tool: lichess_persist_report.

Generates a coaching report through the automatic LLM provider cascade
(same pipeline as the coaching_* tools) and persists the result to disk
on explicit request. Default behavior stays ephemeral everywhere else.
"""

from lichess_analyzer_mcp.app import app
from lichess_analyzer_mcp.services.logger import get_logger
from lichess_analyzer_mcp.services.report_persister import persist_report

log = get_logger("persist_report")


@app.tool("lichess_persist_report")
async def lichess_persist_report(
    kind: str,
    game_id: str = "",
    username: str = "",
    game_ids: str = "",
    color: str = "white",
    max_games: int = 20,
    depth: int = 0,
    hours_per_week: int = 5,
    rating: int = 0,
    result: str = "all",
    format: str = "both",
    target: str = "docs",
):
    """Generate a coaching report via LLM cascade and persist it to disk (on demand).

    Reuses the same data pipeline and provider cascade as the coaching tools,
    then writes persistent artifacts:
      - data/reports/{kind}_{ref}_{ts}.json (structured, always machine-readable)
      - docs/coaching_report_{kind}_{ref}_{ts}.md (human-readable)
      - B2B-Knowledge-Base (target="kb", kinds: diagnosis, cross_game)

    Args:
        kind: "single_game" | "cross_game" | "opponent_pool" | "training_plan"
              | "opening_report" | "diagnosis"
        game_id: Lichess game ID (kind=single_game)
        username: Lichess username (kind=cross_game/training_plan/opening_report/diagnosis)
        game_ids: Comma-separated game IDs (kind=opponent_pool)
        color: Your color ('white' or 'black', kind=single_game)
        max_games: Number of games to analyze (5-50)
        depth: Stockfish depth (0=auto per depth policy)
        hours_per_week: Available training hours (kind=training_plan)
        rating: Current rating (kind=training_plan)
        result: Filter - 'all', 'win', 'loss', 'draw'
        format: "json" | "md" | "both"
        target: "docs" | "kb"
    """
    try:
        ids = [x.strip() for x in game_ids.split(",") if x.strip()] if game_ids else []
        params = {
            "game_id": game_id.strip(),
            "username": username.strip(),
            "game_ids": ids,
            "color": color,
            "max_games": max_games,
            "depth": depth,
            "hours_per_week": hours_per_week,
            "rating": rating,
            "result": result,
        }
        return await persist_report(kind, params, fmt=format, target=target)
    except Exception as e:
        log.exception("persist report error | kind=%s", kind)
        return {"error": f"{type(e).__name__}: {e}", "kind": kind}
