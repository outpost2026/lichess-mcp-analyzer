"""Game analysis: per-move Stockfish classification."""

from src.models.game import GameSummary, MoveAnalysis, GameAnalysis
from src.services import engine_client
from src.services.lichess_client import fetch_game_pgn


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


def analyze_pgn(pgn: str, player_color: str = "white", depth: int = 14) -> GameAnalysis:
    import chess.pgn
    import io

    game_node = chess.pgn.read_game(io.StringIO(pgn))
    if game_node is None:
        raise ValueError("Invalid PGN")
    headers = game_node.headers
    result = headers.get("Result", "*")
    game_summary = GameSummary(
        id=headers.get("Site", "").split("/")[-1] if "/" in headers.get("Site", "") else "",
        platform="lichess" if "lichess" in headers.get("Site", "") else "chesscom",
        opening=headers.get("Opening", ""),
        opening_eco=headers.get("ECO", ""),
        color=player_color,
        result=result,
        opponent_name=headers.get("Black", "")
        if player_color == "white"
        else headers.get("White", ""),
        opponent_rating=int(headers.get("BlackElo", 0))
        if player_color == "white"
        else int(headers.get("WhiteElo", 0)),
        player_rating=int(headers.get("WhiteElo", 0))
        if player_color == "white"
        else int(headers.get("BlackElo", 0)),
        time_control=headers.get("TimeControl", ""),
        date=headers.get("Date", ""),
        url=headers.get("Site", ""),
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
    return analysis
