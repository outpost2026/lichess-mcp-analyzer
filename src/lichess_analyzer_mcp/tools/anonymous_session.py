"""Tool for batch analyzing anonymous games from URLs or text files."""

import os
import re
import io
import chess.pgn
from lichess_analyzer_mcp.app import app
from lichess_analyzer_mcp.services.lichess_client import fetch_game_pgn
from lichess_analyzer_mcp.services.game_analyzer import analyze_pgn


def _extract_id(raw: str) -> str | None:
    if "/" in raw:
        raw = raw.rstrip("/").split("/")[-1]
    cleaned = re.sub(r"[^a-zA-Z0-9]", "", raw)
    if len(cleaned) >= 8:
        return cleaned[:8]
    return None


def _parse_game_entries(source: str, is_file: bool = False) -> list[tuple[str, str | None]]:
    """Parse input into [(game_id, label_or_None), ...].

    Input formats per line:
        https://lichess.org/XXXXXXXXXXXX           → (id, None)
        https://lichess.org/XXXXXXXXXXXX white     → (id, "white")
        https://lichess.org/XXXXXXXXXXXX black     → (id, "black")
        https://lichess.org/XXXXXXXXXXXX win       → (id, "win")
        https://lichess.org/XXXXXXXXXXXX loss      → (id, "loss")
        XXXXXXXXXXXX                                → (id, None)
    """
    if is_file:
        if not os.path.isfile(source):
            raise FileNotFoundError(f"File not found: {source}")
        with open(source, encoding="utf-8") as f:
            lines = f.readlines()
    else:
        lines = source.split("\n")

    seen = set()
    results = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        tokens = re.split(r"[\s,;|]+", line)
        found_id = None
        label = None
        for t in tokens:
            t = t.strip()
            if not t:
                continue
            candidate_id = _extract_id(t)
            if candidate_id:
                found_id = candidate_id
            elif t.lower() in ("white", "w"):
                label = "white"
            elif t.lower() in ("black", "b"):
                label = "black"
            elif t.lower() == "win":
                label = "win"
            elif t.lower() == "loss":
                label = "loss"
        if found_id and found_id not in seen:
            seen.add(found_id)
            results.append((found_id, label))
    return results


def _resolve_color(pgn: str, label: str | None) -> str:
    """Determine player color from label + PGN result header."""
    if label is None:
        label = "win"
    if label in ("white", "black"):
        return label
    if label in ("win", "loss"):
        game = chess.pgn.read_game(io.StringIO(pgn))
        result = game.headers.get("Result", "*") if game else "*"
        if label == "win":
            return "white" if result == "1-0" else ("black" if result == "0-1" else "white")
        if label == "loss":
            return "black" if result == "1-0" else ("white" if result == "0-1" else "white")
    return "white"


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
        - Optional label after URL:  white | black | win | loss
          Determines which side is "us" for ACPL/result stats.
          If omitted, assumes "white" and flags player_color="unknown".
    """
    depth = max(8, min(24, depth))
    entries: list[tuple[str, str | None]] = []

    if file_path:
        entries = _parse_game_entries(file_path, is_file=True)
    elif urls:
        entries = _parse_game_entries(urls)
    elif game_ids:
        entries = [(g.strip()[:8], None) for g in game_ids.split(",") if g.strip()]
    else:
        return {"error": "Provide one of: file_path, game_ids, or urls"}

    if not entries:
        return {"error": "No valid game IDs found in input"}

    games = []
    total_blunders = 0
    total_mistakes = 0
    total_inaccuracies = 0
    total_moves = 0
    acpl_values = []
    openings = {}
    player_wins = 0
    player_losses = 0
    player_draws = 0

    for gid, label in entries:
        try:
            pgn = fetch_game_pgn(gid)
            player_color = _resolve_color(pgn, label)
            analysis = analyze_pgn(pgn, player_color=player_color, depth=depth, game_id=gid)
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

            if g.result == "1-0":
                if player_color == "white":
                    player_wins += 1
                else:
                    player_losses += 1
            elif g.result == "0-1":
                if player_color == "black":
                    player_wins += 1
                else:
                    player_losses += 1
            else:
                player_draws += 1

            games.append(
                {
                    "id": gid,
                    "opening": f"{g.opening} ({eco})",
                    "result": g.result,
                    "player_color": player_color,
                    "label": label or "none",
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
            "games_failed": len(entries) - n,
            "aggregate_acpl": round(sum(acpl_values) / n, 1) if acpl_values else 0,
            "total_blunders": total_blunders,
            "total_mistakes": total_mistakes,
            "total_inaccuracies": total_inaccuracies,
            "avg_blunders_per_game": round(total_blunders / n, 1) if n else 0,
            "avg_moves_per_game": round(total_moves / n, 1) if n else 0,
            "player_record": {
                "wins": player_wins,
                "losses": player_losses,
                "draws": player_draws,
            },
            "top_openings": dict(sorted(openings.items(), key=lambda x: -x[1])[:5]),
        }

    return {"games": games, "aggregate": agg}
