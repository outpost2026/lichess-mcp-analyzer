"""Game analysis: per-move Stockfish classification."""

import glob
import json
import os
import re

import chess

from lichess_analyzer_mcp.models.game import GameSummary, MoveAnalysis, GameAnalysis
from lichess_analyzer_mcp.config.depth import DEPTH_DEFAULTS
from lichess_analyzer_mcp.models.analysis import (
    BlunderFactSheet,
    BoardState,
    LegalMovesSummary,
    EngineLine,
    PatternMatchInfo,
    ContextWindowMove,
    ContextWindow,
    DETECTOR_VERSION,
)
from lichess_analyzer_mcp.services import engine_client
from lichess_analyzer_mcp.services.lichess_client import fetch_game_pgn
from lichess_analyzer_mcp.services.logger import get_logger
from lichess_analyzer_mcp.services.pattern_detector import (
    THRESHOLD_GRAB_CP,
    THRESHOLD_BLOCK_CP,
    THRESHOLD_ENDGAME_CP,
    THRESHOLD_ENDGAME_EVAL,
    THRESHOLD_S_CAPTURE_AVERSION_CP,
)

_logger = get_logger("game_analyzer")

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "game_cache")

# ── Adaptive Hash (deterministic, zero heuristics) ───────────────────────────
# Ply = total half-moves from PGN, depth = Stockfish depth.
# Volba hash podle měření depth 12/14 na 20 hrách systeq (hashfull <10% target).
# 64 MB stačí pro <40 ply depth 14, 128 pro 40-80 ply, 256 pro 80+ ply nebo depth 18.
# Deterministická tabulka, žádná heuristika, jen ply+depth → hash.

ADAPTIVE_HASH_TABLE = {
    # (max_ply, depth): hash_mb
    # depth 12
    (40, 12): 64,
    (80, 12): 64,
    (999, 12): 64,
    # depth 14
    (40, 14): 64,
    (80, 14): 128,
    (999, 14): 256,
    # depth 18
    (40, 18): 128,
    (80, 18): 256,
    (999, 18): 512,
}


def choose_adaptive_hash(ply_count: int, depth: int) -> int:
    """Deterministická volba hash podle ply a depth. Žádná heuristika."""
    # depth bucket
    d = 12 if depth <= 12 else 14 if depth <= 14 else 18
    for max_ply, d_key in sorted(ADAPTIVE_HASH_TABLE):
        if d_key == d and ply_count <= max_ply:
            return ADAPTIVE_HASH_TABLE[(max_ply, d_key)]
    return 64


def _ply_count_from_pgn(pgn: str) -> int:
    try:
        import chess.pgn
        import io

        game = chess.pgn.read_game(io.StringIO(pgn))
        if game is None:
            return 30
        return sum(1 for _ in game.mainline_moves())
    except Exception:
        return 30


def _sanitize_id(raw: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "", raw)


def _cache_path(game_id: str, depth: int, color: str = "white") -> str:
    safe = _sanitize_id(game_id)
    d = os.path.join(CACHE_DIR, f"{safe}_{color}_d{depth}.json")
    return d


def _detect_game_profile(tc: str) -> str:
    """Vrátí klíč do DEPTH_DEFAULTS podle time control.

    Returns 'bullet' | 'blitz' | 'rapid' | 'classical' | 'correspondence' | 'unknown'.
    """
    if not tc or tc == "?":
        return "unknown"
    tc = tc.strip()
    if tc.startswith("-"):
        return "correspondence"
    match = re.match(r"^(\d+)", tc)
    if not match:
        return "unknown"
    seconds = int(match.group(1))
    if seconds <= 120:
        return "bullet"
    if seconds <= 480:
        return "blitz"
    if seconds <= 1800:
        return "rapid"
    return "classical"


def _load_cached_analysis(
    game_id: str, depth: int, color: str = "white", exact_depth: bool = False
) -> GameAnalysis | None:
    path = _cache_path(game_id, depth, color)
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return GameAnalysis.from_dict(json.load(f))
        except Exception:
            pass
    if exact_depth:
        return None
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
    depth: int = 0,
    game_id: str | None = None,
    use_cache: bool = True,
    strict_depth: bool = False,
) -> GameAnalysis:
    if depth == 0:
        depth = DEPTH_DEFAULTS["standard"]["single_game"]
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
            cached = _load_cached_analysis(game_id, depth, player_color, exact_depth=strict_depth)
            if cached is not None:
                return cached

    analysis = _run_analyze_pgn(pgn, player_color, depth)

    if use_cache and game_id:
        _save_cached_analysis(game_id, depth, analysis)

    return analysis


def _extract_legal_moves(board: chess.Board) -> LegalMovesSummary:
    """Classify legal moves into captures, king_moves, blocks, checks."""
    if board.turn is None:
        return LegalMovesSummary()
    legal = list(board.legal_moves)
    captures = []
    king_moves = []
    blocks = []
    checks = []
    in_check = board.is_check()
    for mv in legal:
        san = board.san(mv)
        if board.gives_check(mv):
            checks.append(san)
        piece = board.piece_at(mv.from_square)
        is_king = piece is not None and piece.piece_type == chess.KING
        is_capture = board.is_capture(mv)
        if is_king:
            king_moves.append(san)
        elif is_capture:
            captures.append(san)
        if in_check and not is_king and not is_capture:
            sim = board.copy()
            sim.push(mv)
            if not sim.is_check():
                blocks.append(san)
    return LegalMovesSummary(
        total=len(legal),
        captures=captures,
        king_moves=king_moves,
        blocks=blocks,
        checks=checks,
    )


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


def _per_blunder_patterns(
    move: MoveAnalysis,
    legal: LegalMovesSummary,
    in_check: bool,
    prev_move: MoveAnalysis | None = None,
) -> list[PatternMatchInfo]:
    matches = []
    cp = move.centipawn_loss
    # B — Automatic grab: capture that is a blunder/mistake
    if "x" in move.move_san and cp >= THRESHOLD_GRAB_CP:
        matches.append(
            PatternMatchInfo(
                pattern_id="B",
                pattern_name="Automatic grab",
                confidence=min(cp / 500, 0.95),
                evidence=f"capture blunder cp_loss={cp:.0f}",
            )
        )
    # J — Impulsive check block: in check, non-capture, cp_loss >= THRESHOLD_BLOCK_CP
    if in_check and "x" not in move.move_san and cp >= THRESHOLD_BLOCK_CP:
        matches.append(
            PatternMatchInfo(
                pattern_id="J",
                pattern_name="Impulsive check block",
                confidence=min(cp / 600, 0.85),
                evidence=f"in_check block cp_loss={cp:.0f}",
            )
        )
    # R — Endgame relaxation: endgame, eval_before > THRESHOLD_ENDGAME_EVAL, cp_loss >= THRESHOLD_ENDGAME_CP
    if (
        move.phase == "endgame"
        and move.eval_before > THRESHOLD_ENDGAME_EVAL
        and cp >= THRESHOLD_ENDGAME_CP
    ):
        matches.append(
            PatternMatchInfo(
                pattern_id="R",
                pattern_name="Endgame relaxation",
                confidence=min(cp / 1000, 0.85),
                evidence=f"endgame eval_before={move.eval_before:.0f} cp_loss={cp:.0f}",
            )
        )
    # S — Capture aversion under check: in check, king capture possible but not played
    if in_check:
        king_capture_san = [s for s in legal.king_moves if "x" in s]
        king_capture_played = any("x" in move.move_san for s in legal.king_moves if "x" in s)
        if king_capture_san and not king_capture_played and cp >= THRESHOLD_S_CAPTURE_AVERSION_CP:
            matches.append(
                PatternMatchInfo(
                    pattern_id="S",
                    pattern_name="Capture aversion under check",
                    confidence=0.4,
                    evidence=f"king capture available but not taken cp_loss={cp:.0f}",
                )
            )
    # C — Attention tunneling: consecutive errors
    if prev_move and prev_move.classification in ("blunder", "mistake") and cp >= 200:
        matches.append(
            PatternMatchInfo(
                pattern_id="C",
                pattern_name="Attention tunneling",
                confidence=min(cp / 500, 0.8),
                evidence=f"consecutive error after ply={prev_move.ply} cp_loss={cp:.0f}",
            )
        )
    return matches


def _win_prob_from_cp(cp: float) -> float:
    """Winning chances sigmoid from lila (lichess internal)."""
    if cp is None:
        return 0.5
    return 1.0 / (1.0 + 10 ** (-cp / 400.0))


def _run_analyze_pgn(pgn: str, player_color: str = "white", depth: int = 0) -> GameAnalysis:
    if depth == 0:
        depth = DEPTH_DEFAULTS["standard"]["single_game"]
    # Adaptive hash — deterministic, zero heuristics (ply+depth → hash)
    try:
        ply_cnt = _ply_count_from_pgn(pgn)
        h = choose_adaptive_hash(ply_cnt, depth)
        engine_client.get_engine(hash_mb=h)
        _logger.info("adaptive hash %d MB for ply %d depth %d", h, ply_cnt, depth)
    except Exception:
        pass
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

    game_id = site.split("/")[-1] if "/" in site else ""
    game_summary = GameSummary(
        id=game_id,
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
                if move in board.legal_moves:
                    eval_result = engine_client.evaluate_move(fen_before, move.uci(), depth=depth)
            except Exception:
                eval_result = None
            if eval_result and "error" not in eval_result:
                cp_loss = eval_result["centipawn_loss"]
            else:
                cp_loss = 0
                analysis.evaluation_errors += 1
            classification = _classify_move(cp_loss)
            phase = _detect_phase(ply)
            was_in_check = board.is_check()
            eval_before_val = eval_result.get("eval_before", 0) if eval_result else 0
            eval_after_val = eval_result.get("eval_after", 0) if eval_result else 0
            move_analysis = MoveAnalysis(
                ply=ply,
                move_uci=move.uci(),
                move_san=board.san(move),
                eval_before=eval_before_val,
                eval_after=eval_after_val,
                win_prob_before=_win_prob_from_cp(eval_before_val),
                win_prob_after=_win_prob_from_cp(eval_after_val),
                centipawn_loss=cp_loss,
                classification=classification,
                best_move_uci=eval_result.get("best_move_uci", "") if eval_result else "",
                best_move_san="",
                is_tactical_motif=False,
                motif_type=None,
                phase=phase,
                fen=fen_before,
                was_in_check=was_in_check,
            )
            if classification == "blunder":
                analysis.blunders.append(move_analysis)
            elif classification == "mistake":
                analysis.mistakes.append(move_analysis)
            elif classification == "inaccuracy":
                analysis.inaccuracies.append(move_analysis)
            total_cp += cp_loss
            move_count += 1
            analysis.moves.append(move_analysis)
            # DBCL: build BlunderFactSheet for blunders and deep mistakes
            if classification in ("blunder", "mistake") and cp_loss >= 150:
                legal = _extract_legal_moves(board)
                prev_move = analysis.moves[-2] if len(analysis.moves) >= 2 else None
                patterns = _per_blunder_patterns(move_analysis, legal, was_in_check, prev_move)
                engine_lines_raw = []
                try:
                    engine_lines_raw = engine_client.analyze_position(
                        fen_before, depth=depth, multipv=3
                    )
                except Exception as e:
                    _logger.warning(
                        "analyze_position failed for %s ply %d: %s",
                        game_id,
                        ply,
                        e,
                    )
                engine_lines = []
                for rank, el in enumerate(engine_lines_raw, start=1):
                    score_cp = el.get("score_cp") or 0
                    pv_san = el.get("pv_san", [])
                    engine_lines.append(
                        EngineLine(
                            rank=rank,
                            move_san=pv_san[0] if pv_san else "",
                            eval_cp=score_cp,
                            win_prob=_win_prob_from_cp(score_cp),
                            pv=pv_san,
                        )
                    )
                eval_before = move_analysis.eval_before or 0
                eval_after = move_analysis.eval_after or 0
                win_before = _win_prob_from_cp(eval_before)
                win_after = _win_prob_from_cp(eval_after)
                played_move_rank = 0
                for el in engine_lines:
                    if el.move_san == move_analysis.move_san:
                        played_move_rank = el.rank
                        break
                if played_move_rank == 0:
                    played_move_rank = (
                        len(engine_lines) + 1
                        if engine_lines
                        else len(legal.captures) + len(legal.king_moves) + 1
                    )
                bfs = BlunderFactSheet(
                    game_id=game_id,
                    ply=ply,
                    move_played_san=move_analysis.move_san,
                    move_played_uci=move_analysis.move_uci,
                    centipawn_loss=cp_loss,
                    eval_before=eval_before,
                    eval_after=eval_after,
                    win_prob_before=win_before,
                    win_prob_after=win_after,
                    win_prob_delta=win_after - win_before,
                    fen_before=fen_before,
                    board_state=BoardState(
                        was_in_check=was_in_check,
                        checking_pieces=[chess.square_name(sq) for sq in board.checkers()]
                        if was_in_check
                        else [],
                        capture_checking_piece_possible=any("x" in s for s in legal.captures),
                        king_capture_possible=any("x" in s for s in legal.king_moves),
                        king_capture_played="x" in move_analysis.move_san and was_in_check,
                    ),
                    legal_moves=legal,
                    engine_lines=engine_lines,
                    played_move_rank=played_move_rank,
                    phase=phase,
                    pattern_matches=patterns,
                    detector_version=DETECTOR_VERSION,
                )
                analysis.blunder_fact_sheets.append(bfs)
        board.push(move)
    if move_count > 0:
        analysis.total_acpl = total_cp / move_count
    # Fill context window for each BFS
    for bfs in analysis.blunder_fact_sheets:
        before = []
        after = []
        bfs_ply = bfs.ply
        for m in analysis.moves:
            if abs(m.ply - bfs_ply) <= 3 and m.ply != bfs_ply:
                cwm = ContextWindowMove(
                    ply=m.ply,
                    move_san=m.move_san,
                    eval_after=m.eval_after,
                    win_prob_after=m.win_prob_after,
                )
                if m.ply < bfs_ply:
                    before.append(cwm)
                else:
                    after.append(cwm)
        before.sort(key=lambda x: x.ply)
        after.sort(key=lambda x: x.ply)
        bfs.context_window = ContextWindow(moves_before=before, moves_after=after)
    analysis.auto_annotate()
    # Clear hash deterministically for next game (prevent pollution, keep <10% hashfull)
    try:
        engine_client.clear_hash()
    except Exception:
        pass
    return analysis
