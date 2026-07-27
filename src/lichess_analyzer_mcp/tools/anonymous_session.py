"""Tool for batch analyzing anonymous games from URLs or text files."""

import os
import re
from lichess_analyzer_mcp.app import app
from lichess_analyzer_mcp.services.lichess_client import fetch_game_pgn
from lichess_analyzer_mcp.services.game_analyzer import analyze_pgn


def _parse_game_ids(source: str, is_file: bool = False) -> list[str]:
    if is_file:
        if not os.path.isfile(source):
            raise FileNotFoundError(f"File not found: {source}")
        with open(source, encoding="utf-8") as f:
            content = f.read()
    else:
        content = source

    ids = set()
    for token in re.split(r"[\s,;|\n]+", content.strip()):
        token = token.strip()
        if not token:
            continue
        if "/" in token:
            token = token.rstrip("/").split("/")[-1]
        token = re.sub(r"[^a-zA-Z0-9]", "", token)
        if len(token) >= 8:
            ids.add(token[:8])
        elif len(token) == 8:
            ids.add(token)
    return list(ids)


@app.tool("lichess_analyze_anonymous_session")
async def lichess_analyze_anonymous_session(
    file_path: str = "",
    game_ids: str = "",
    urls: str = "",
    depth: int = 12,
):
    """Analyze multiple anonymous games from URLs or a text file, return per-game + aggregate stats.

    Args:
        file_path: Path to a .txt file with one URL or game ID per line
        game_ids: Comma-separated list of 8-char game IDs
        urls: Comma-separated list of full Lichess URLs
        depth: Stockfish analysis depth (8-24, default 12 — anonymous = fast)

    Notes:
        - URLs like https://lichess.org/XXXXXXXXxxxx are trimmed to 8-char IDs
        - Games with errors are reported individually, not blocking the batch
    """
    depth = max(8, min(24, depth))
    ids: list[str] = []

    if file_path:
        ids = _parse_game_ids(file_path, is_file=True)
    elif urls:
        ids = _parse_game_ids(urls)
    elif game_ids:
        ids = [g.strip()[:8] for g in game_ids.split(",") if g.strip()]
    else:
        return {"error": "Provide one of: file_path, game_ids, or urls"}

    if not ids:
        return {"error": "No valid game IDs found in input"}

    games = []
    total_blunders = 0
    total_mistakes = 0
    total_inaccuracies = 0
    total_moves = 0
    acpl_values = []
    openings = {}
    results = {"1-0": 0, "0-1": 0, "1/2-1/2": 0}

    for gid in ids:
        try:
            pgn = fetch_game_pgn(gid)
            analysis = analyze_pgn(pgn, player_color="white", depth=depth, game_id=gid)
            g = analysis.game
            acpl = round(analysis.total_acpl, 1)
            blen = len(analysis.blunders)
            mlen = len(analysis.mistakes)
            ilen = len(analysis.inaccuracies)
            mcount = len(analysis.moves)

            total_blunders += blen
            total_mistakes += mlen
            total_inaccuracies += ilen
            total_moves += mcount
            acpl_values.append(acpl)

            eco = g.opening_eco or "?"
            openings[eco] = openings.get(eco, 0) + 1
            results[g.result] = results.get(g.result, 0) + 1

            games.append(
                {
                    "id": gid,
                    "opening": f"{g.opening} ({eco})",
                    "result": g.result,
                    "acpl": acpl,
                    "blunders": blen,
                    "mistakes": mlen,
                    "inaccuracies": ilen,
                    "moves": mcount,
                    "top_blunders": [
                        f"Move {m.ply}: {m.move_san} (loss {m.centipawn_loss:.0f}cp, {m.phase})"
                        for m in analysis.blunders[:5]
                    ],
                }
            )
        except Exception as e:
            games.append({"id": gid, "error": str(e)})

    n = len([g for g in games if "error" not in g])
    agg = {}
    if n > 0:
        agg = {
            "games_analyzed": n,
            "games_failed": len(ids) - n,
            "aggregate_acpl": round(sum(acpl_values) / n, 1) if acpl_values else 0,
            "total_blunders": total_blunders,
            "total_mistakes": total_mistakes,
            "total_inaccuracies": total_inaccuracies,
            "avg_blunders_per_game": round(total_blunders / n, 1) if n else 0,
            "avg_moves_per_game": round(total_moves / n, 1) if n else 0,
            "result_distribution": results,
            "top_openings": dict(sorted(openings.items(), key=lambda x: -x[1])[:5]),
        }

    return {"games": games, "aggregate": agg}
