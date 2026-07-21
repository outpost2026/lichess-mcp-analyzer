"""Game analysis: per-move Stockfish classification."""

import glob
import json
import os

from lichess_analyzer_mcp.models.game import GameSummary, MoveAnalysis, GameAnalysis
from lichess_analyzer_mcp.services import engine_client
from lichess_analyzer_mcp.services.lichess_client import fetch_game_pgn

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "game_cache")


def _cache_path(game_id: str, depth: int, color: str = "white") -> str:
    d = os.path.join(CACHE_DIR, f"{game_id}_{color}_d{depth}.json")
    return d


def _load_cached_analysis(game_id: str, depth: int, color: str = "white") -> GameAnalysis | None:
    path = _cache_path(game_id, depth, color)
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return GameAnalysis.from_dict(json.load(f))
        except Exception:
            pass
    # Depth approximation: try nearest depth if exact match not found
    pattern = os.path.join(CACHE_DIR, f"{game_id}_{color}_d*.json")
    for fpath in sorted(glob.glob(pattern), reverse=True):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                return GameAnalysis.from_dict(json.load(f))
        except Exception:
            continue
    return None


def _save_cached_analysis(game_id: str, depth: int, analysis: GameAnalysis) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    color = analysis.game.color
    path = _cache_path(game_id, depth, color)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(analysis.to_dict(), f, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception:
        pass


def analyze_pgn(
    pgn: str,
    player_color: str = "white",
    depth: int = 14,
    game_id: str | None = None,
    use_cache: bool = True,
) -> GameAnalysis:
    if use_cache:
        if game_id is None:
            import io
            import chess.pgn

            game_node = chess.pgn.read_game(io.StringIO(pgn))
            if game_node is not None:
                site = game_node.headers.get("Site", "")
                if "/" in site:
                    game_id = site.split("/")[-1]
        if game_id:
            cached = _load_cached_analysis(game_id, depth, player_color)
            if cached is not None:
                return cached

    analysis = _run_analyze_pgn(pgn, player_color, depth)

    if use_cache and game_id:
        _save_cached_analysis(game_id, depth, analysis)

    return analysis


def _run_analyze_pgn(pgn: str, player_color: str = "white", depth: int = 14) -> GameAnalysis:
    import chess.pgn
    import io

    game_node = chess.pgn.read_game(io.StringIO(pgn))
    if game_node is None:
        raise ValueError("Invalid PGN")
    headers = game_node.headers
    result = headers.get("Result", "*")
    site = headers.get("Site", "")

    def _safe_elo(val: str) -> int:
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    game_summary = GameSummary(
        id=site.split("/")[-1] if "/" in site else "",
        platform="lichess" if "lichess" in site else "chesscom",
        opening=headers.get("Opening", ""),
        opening_eco=headers.get("ECO", ""),
        color=player_color,
        result=result,
        player_name=headers.get("White", "")
        if player_color == "white"
        else headers.get("Black", ""),
        opponent_name=headers.get("Black", "")
        if player_color == "white"
        else headers.get("White", ""),
        opponent_rating=_safe_elo(headers.get("BlackElo", "0"))
        if player_color == "white"
        else _safe_elo(headers.get("WhiteElo", "0")),
        player_rating=_safe_elo(headers.get("WhiteElo", "0"))
        if player_color == "white"
        else _safe_elo(headers.get("BlackElo", "0")),
        time_control=headers.get("TimeControl", ""),
        date=headers.get("Date", ""),
        url=site,
    )
    analysis = GameAnalysis(game=game_summary)
    board = game_node.board()
    player_side = chess.WHITE if player_color == "white" else chess.BLACK
    ply = 0
    total_cp = 0
    move_count = 0
    node = game_node
    while node.variations:
        node = node.variations[0]
        move = node.move
        ply += 1
        fen_before = board.fen()
        if board.turn == player_side:
            eval_result = None
            try:
                eval_result = engine_client.evaluate_move(fen_before, move.uci(), depth=depth)
            except Exception:
                pass
            if eval_result:
                cp_loss = eval_result["centipawn_loss"]
            else:
                cp_loss = 0
            classification = _classify_move(cp_loss)
            phase = _detect_phase(ply)
            move_analysis = MoveAnalysis(
                ply=ply,
                move_uci=move.uci(),
                move_san=board.san(move),
                eval_before=eval_result.get("eval_before", 0) if eval_result else 0,
                eval_after=eval_result.get("eval_after", 0) if eval_result else 0,
                win_prob_before=0.0,
                win_prob_after=0.0,
                centipawn_loss=cp_loss,
                classification=classification,
                best_move_uci=eval_result.get("best_move_uci", "") if eval_result else "",
                best_move_san="",
                is_tactical_motif=False,
                motif_type=None,
                phase=phase,
            )
            if classification in ("blunder", "mistake"):
                analysis.blunders.append(move_analysis)
            elif classification == "inaccuracy":
                analysis.inaccuracies.append(move_analysis)
            total_cp += cp_loss
            move_count += 1
            analysis.moves.append(move_analysis)
        board.push(move)
    if move_count > 0:
        analysis.total_acpl = total_cp / move_count
    analysis.auto_annotate()
    return analysis


def _classify_move(cp_loss: float) -> str:
    if cp_loss >= 300:
        return "blunder"
    if cp_loss >= 150:
        return "mistake"
    if cp_loss >= 50:
        return "inaccuracy"
    if cp_loss >= 20:
        return "good"
    return "best"


def _detect_phase(ply: int) -> str:
    if ply <= 20:
        return "opening"
    if ply <= 50:
        return "middlegame"
    return "endgame"
