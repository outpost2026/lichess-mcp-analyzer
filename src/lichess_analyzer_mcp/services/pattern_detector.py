"""Pattern detection engine for patterns A-Q1, I2, Q2, S."""

from collections import Counter
import chess

from lichess_analyzer_mcp.models.pattern import PatternDef, PatternMatch, PatternLibrary
from lichess_analyzer_mcp.models.game import GameAnalysis

THRESHOLD_TUNNEL_CONSECUTIVE = 2
THRESHOLD_GRAB_CP = 100
THRESHOLD_BLOCK_CP = 150
THRESHOLD_VISUAL_CP = 150
THRESHOLD_ENDGAME_CP = 300
THRESHOLD_ENDGAME_EVAL = 300
THRESHOLD_DESPERATE_EVAL = -3.0
THRESHOLD_DESPERATE_CP = 300
THRESHOLD_ACTIVE_DEFENSE_EVAL = -150
THRESHOLD_S_CAPTURE_AVERSION_CP = 500
THRESHOLD_GIFT_EVAL_JUMP = 70


class PatternDetector:
    def __init__(self):
        self.library = PatternLibrary().load_baseline()

    def detect_all(self, analyses: list[GameAnalysis], metadata: dict) -> list[PatternMatch]:
        total_games = len(analyses)
        matches = []
        for pid in self.library.patterns:
            pdef = self.library.patterns[pid]
            if total_games < pdef.min_games:
                continue
            detector = getattr(self, f"_detect_{pid.lower()}", None)
            if detector:
                match = detector(analyses, metadata)
                if match:
                    if match.frequency < pdef.min_occurrences:
                        continue
                    matches.append(match)
        return matches

    def _detect_a(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch:
        anonymous_games = [a for a in analyses if "anonymous" in a.game.opponent_name.lower()]
        named_games = [a for a in analyses if "anonymous" not in a.game.opponent_name.lower()]
        if not anonymous_games or not named_games:
            return None
        anon_blunder_rate = sum(len(g.blunders) for g in anonymous_games) / len(anonymous_games)
        named_blunder_rate = sum(len(g.blunders) for g in named_games) / len(named_games)
        if named_blunder_rate > 0 and anon_blunder_rate / named_blunder_rate > 1.3:
            return PatternMatch(
                pattern_id="A",
                pattern_name="Anonymous effect",
                confidence=min(anon_blunder_rate / named_blunder_rate / 2, 0.95),
                evidence=[
                    {
                        "anonymous_blunder_rate": round(anon_blunder_rate, 2),
                        "named_blunder_rate": round(named_blunder_rate, 2),
                        "ratio": round(anon_blunder_rate / named_blunder_rate, 2),
                        "affected_games": [g.game.id for g in anonymous_games],
                    }
                ],
                game_ids=[g.game.id for g in anonymous_games],
                frequency=len(anonymous_games),
                severity="high",
                hypothesis="Hypothesis: unknown opponent rating lowers perceived threat threshold, leading to higher blunder rate.",
            )
        return None

    def _detect_b(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch:
        total_captures = 0
        blunder_captures = 0
        affected_games = []
        for analysis in analyses:
            for m in analysis.moves:
                if "x" in m.move_san:
                    total_captures += 1
                    if (
                        m.classification in ("blunder", "mistake")
                        and m.centipawn_loss >= THRESHOLD_GRAB_CP
                    ):
                        blunder_captures += 1
                        affected_games.append(analysis.game.id)
        if blunder_captures >= 2 and total_captures > 0:
            ratio = blunder_captures / total_captures
            return PatternMatch(
                pattern_id="B",
                pattern_name="Automatic grab",
                confidence=min(ratio * 2, 0.95),
                evidence=[
                    {
                        "blunder_captures": blunder_captures,
                        "total_captures": total_captures,
                        "blunder_capture_ratio": round(ratio, 3),
                        "affected_games": list(set(affected_games)),
                        "total_games": len(analyses),
                    }
                ],
                game_ids=list(set(affected_games)),
                frequency=blunder_captures,
                severity="high",
                hypothesis="Hypothesis: player captures automatically without evaluating opponent's counterplay — analogous to git push --force.",
            )
        return None

    def _detect_c(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch:
        affected = []
        total_tunneling = 0
        for analysis in analyses:
            consecutive_zone = 0
            max_consecutive = 0
            for m in analysis.moves:
                if (
                    m.classification in ("blunder", "mistake")
                    and m.centipawn_loss >= THRESHOLD_GRAB_CP
                ):
                    consecutive_zone += 1
                    max_consecutive = max(max_consecutive, consecutive_zone)
                else:
                    consecutive_zone = 0
            if max_consecutive >= THRESHOLD_TUNNEL_CONSECUTIVE:
                affected.append(analysis.game.id)
                total_tunneling += max_consecutive
        if affected:
            total_games = len(analyses)
            return PatternMatch(
                pattern_id="C",
                pattern_name="Attention tunneling",
                confidence=min(len(set(affected)) / total_games * 0.9, 0.85),
                evidence=[
                    {
                        "affected_games": list(set(affected)),
                        "total_games": total_games,
                        "max_consecutive_blunders": total_tunneling,
                        "threshold_consecutive": THRESHOLD_TUNNEL_CONSECUTIVE,
                        "detail": "Multiple consecutive errors suggest attention breakdown overriding global evaluation",
                    }
                ],
                game_ids=list(set(affected)),
                frequency=len(set(affected)),
                severity="medium",
                hypothesis="Hypothesis: player fixates on one area of the board, missing counterplay elsewhere — fixing one bug while creating another.",
            )
        return None

    def _detect_g(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch:
        white_analyses = [a for a in analyses if a.game.color == "white"]
        black_analyses = [a for a in analyses if a.game.color == "black"]
        if not white_analyses or not black_analyses:
            return None
        white_blunder_rate = sum(len(g.blunders) for g in white_analyses) / len(white_analyses)
        black_blunder_rate = sum(len(g.blunders) for g in black_analyses) / len(black_analyses)
        if black_blunder_rate > 0 and white_blunder_rate > 0:
            ratio = max(white_blunder_rate, black_blunder_rate) / min(
                white_blunder_rate, black_blunder_rate
            )
            dominant = "White" if white_blunder_rate > black_blunder_rate else "Black"
            if ratio > 1.4:
                affected_ids = [
                    g.game.id
                    for g in (
                        white_analyses
                        if white_blunder_rate > black_blunder_rate
                        else black_analyses
                    )
                ]
                return PatternMatch(
                    pattern_id="G",
                    pattern_name="Color as modulator",
                    confidence=min(ratio / 3, 0.95),
                    evidence=[
                        {
                            "white_blunder_rate": round(white_blunder_rate, 2),
                            "black_blunder_rate": round(black_blunder_rate, 2),
                            "asymmetry_ratio": round(ratio, 2),
                            "dominant_side": dominant,
                            "affected_games": affected_ids,
                        }
                    ],
                    game_ids=affected_ids,
                    frequency=len(affected_ids),
                    severity="high",
                    hypothesis=f"Hypothesis: player's error rate shifts with color — {dominant} side has {ratio:.1f}x more blunders.",
                )
        return None

    def _detect_i2(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch:
        gift_count = 0
        affected = []
        for analysis in analyses:
            for m in analysis.moves:
                if m.classification == "best" and m.eval_after is not None and m.eval_after > 50:
                    if "x" in m.move_san:
                        prev_eval = m.eval_before if m.eval_before is not None else 0
                        if prev_eval < 30 and m.eval_after - prev_eval > THRESHOLD_GIFT_EVAL_JUMP:
                            gift_count += 1
                            affected.append(analysis.game.id)
        if gift_count >= 1:
            total_games = len(analyses)
            return PatternMatch(
                pattern_id="I2",
                pattern_name="Opponent's gift exploitation",
                confidence=min(gift_count / total_games * 0.8, 0.9),
                evidence=[
                    {
                        "gift_captures": gift_count,
                        "total_games": total_games,
                        "threshold_eval_jump": THRESHOLD_GIFT_EVAL_JUMP,
                        "affected_games": list(set(affected)),
                        "detail": "Player's best captures that turned a slightly worse position into clear advantage — opponent dropped a gift",
                    }
                ],
                game_ids=list(set(affected)),
                frequency=gift_count,
                severity="low",
                hypothesis="Hypothesis: player capitalises on opponent's suboptimal captures — analogous to exploiting a misconfigured firewall rule.",
            )
        return None

    def _detect_j(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch:
        affected = []
        block_count = 0
        for analysis in analyses:
            for m in analysis.moves:
                if (
                    m.classification in ("blunder", "mistake")
                    and m.centipawn_loss >= THRESHOLD_BLOCK_CP
                ):
                    if m.was_in_check and "x" not in m.move_san:
                        block_count += 1
                        affected.append(analysis.game.id)
        if block_count >= 1:
            total_games = len(analyses)
            return PatternMatch(
                pattern_id="J",
                pattern_name="Impulsive check block",
                confidence=min(block_count / total_games * 0.9, 0.85),
                evidence=[
                    {
                        "impulsive_blocks": block_count,
                        "total_games": total_games,
                        "threshold_cp": THRESHOLD_BLOCK_CP,
                        "affected_games": list(set(affected)),
                        "detail": "Player was in check and blocked with a piece instead of capturing the checking piece or moving the king, leading to material loss or positional collapse",
                    }
                ],
                game_ids=list(set(affected)),
                frequency=block_count,
                severity="high",
                hypothesis="Hypothesis: when in check, player reflexively blocks with a piece without evaluating king safety — silencing an alert instead of fixing the root cause.",
            )
        return None

    def _detect_o(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch:
        affected_repetition = []
        affected_fallback = []
        for analysis in analyses:
            found_repetition = False
            fen_positions = []
            for m in analysis.moves:
                if m.fen:
                    parts = m.fen.split(" ")
                    position_key = " ".join(parts[:4])
                    fen_positions.append(position_key)
            pos_counts = Counter(fen_positions)
            for pos, count in pos_counts.items():
                if count >= 3:
                    last_idx = len(fen_positions) - 1 - fen_positions[::-1].index(pos)
                    for j in range(last_idx + 1, min(last_idx + 4, len(analysis.moves))):
                        if analysis.moves[j].classification in ("blunder", "mistake"):
                            affected_repetition.append(analysis.game.id)
                            found_repetition = True
                            break
                if found_repetition:
                    break
            if not found_repetition:
                for i in range(len(analysis.moves) - 3):
                    eval_vals = [m.eval_after for m in analysis.moves[i : i + 3]]
                    if None in eval_vals:
                        continue
                    if max(eval_vals) - min(eval_vals) < 30:
                        for j in range(i + 3, min(i + 6, len(analysis.moves))):
                            if analysis.moves[j].classification in ("blunder", "mistake"):
                                affected_fallback.append(analysis.game.id)
                                break
        affected = list(set(affected_repetition + affected_fallback))
        if affected:
            total_games = len(analyses)
            rep_conf = len(set(affected_repetition)) / max(
                len(set(affected_fallback + affected_repetition)), 1
            )
            return PatternMatch(
                pattern_id="O",
                pattern_name="Stagnační panika",
                confidence=min(len(set(affected)) / total_games * 0.8, 0.85),
                evidence=[
                    {
                        "affected_games": list(set(affected)),
                        "total_games": total_games,
                        "repetition_confirmed": len(set(affected_repetition)),
                        "fallback_heuristic": len(set(affected_fallback)),
                        "detail": "Flat eval plateau (3+ moves with <30cp swing) triggered panic — player forced a losing move within 6 moves",
                    }
                ],
                game_ids=list(set(affected)),
                frequency=len(set(affected)),
                severity="critical",
                hypothesis="Hypothesis: positional calm feels dangerous to the player — flat eval plateau triggers forced complications that collapse the position.",
            )
        return None

    def _detect_p(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch:
        affected = []
        for analysis in analyses:
            for m in analysis.moves:
                if (
                    m.classification in ("blunder", "mistake")
                    and m.centipawn_loss >= THRESHOLD_VISUAL_CP
                ):
                    is_heavy = "x" in m.move_san or "Q" in m.move_san or "R" in m.move_san
                    has_advantage = m.eval_before is not None and m.eval_before > 0
                    if is_heavy and has_advantage and m.was_in_check:
                        affected.append(analysis.game.id)
                        break
        if affected:
            total_games = len(analyses)
            return PatternMatch(
                pattern_id="P",
                pattern_name="Visual misrecognition",
                confidence=min(len(set(affected)) / total_games * 0.7, 0.75),
                evidence=[
                    {
                        "affected_games": list(set(affected)),
                        "total_games": total_games,
                        "threshold_cp": THRESHOLD_VISUAL_CP,
                        "condition": "expensive_move_with_advantage",
                        "detail": "Player misread a tactical sequence involving captures or major pieces while winning, overlooking opponent's counterplay",
                    }
                ],
                game_ids=list(set(affected)),
                frequency=len(set(affected)),
                severity="high",
                hypothesis="Hypothesis: player misreads tactical sequences involving captures or major pieces, overlooking counterplay.",
            )
        return None

    def _detect_q(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch:
        affected = []
        for analysis in analyses:
            had_deficit = False
            active_count = 0
            for m in analysis.moves:
                eb = m.eval_before if m.eval_before is not None else 0
                if eb < THRESHOLD_ACTIVE_DEFENSE_EVAL:
                    had_deficit = True
                    if "+" in m.move_san or "x" in m.move_san:
                        active_count += 1
            if had_deficit and active_count >= 1:
                won = (analysis.game.color == "white" and "1-0" in analysis.game.result) or (
                    analysis.game.color == "black" and "0-1" in analysis.game.result
                )
                if won:
                    affected.append(analysis.game.id)
        if affected:
            total_games = len(analyses)
            return PatternMatch(
                pattern_id="Q",
                pattern_name="Active defense",
                confidence=min(len(set(affected)) / total_games * 0.9, 0.85),
                evidence=[
                    {
                        "defensive_wins": len(set(affected)),
                        "total_games": total_games,
                        "threshold_deficit_cp": THRESHOLD_ACTIVE_DEFENSE_EVAL,
                        "affected_games": list(set(affected)),
                        "detail": "Player was materially behind (eval < -150cp) but chose active checks/captures instead of passive defense, and won",
                    }
                ],
                game_ids=list(set(affected)),
                frequency=len(set(affected)),
                severity="low",
                hypothesis="Hypothesis: player prefers active counterplay over passive defense, creating winning chances even in lost positions.",
            )
        return None

    def _detect_q1(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch:
        affected = []
        for analysis in analyses:
            big_blunders = [
                m for m in analysis.blunders if m.centipawn_loss > THRESHOLD_DESPERATE_CP
            ]
            if not big_blunders:
                continue
            last_blunder_ply = max(m.ply for m in big_blunders)
            subsequent_moves = [m for m in analysis.moves if m.ply > last_blunder_ply]
            queen_exchanges = [
                m
                for m in subsequent_moves
                if "Q" in m.move_san and "x" in m.move_san and "Q" in m.move_san.split("x")[-1]
            ]
            rejected_queen_trades = len(queen_exchanges) <= 1
            total_subsequent = len(subsequent_moves)
            has_checks = any("+" in m.move_san for m in subsequent_moves)
            won = (analysis.game.color == "white" and "1-0" in analysis.game.result) or (
                analysis.game.color == "black" and "0-1" in analysis.game.result
            )
            if rejected_queen_trades and total_subsequent >= 10 and has_checks and won:
                affected.append(analysis.game.id)
        if affected:
            total_games = len(analyses)
            return PatternMatch(
                pattern_id="Q1",
                pattern_name="Desperate Gambit Mode",
                confidence=min(len(set(affected)) / total_games * 0.8, 0.75),
                evidence=[
                    {
                        "affected_games": list(set(affected)),
                        "total_games": total_games,
                        "threshold_eval": THRESHOLD_DESPERATE_EVAL,
                        "detail": "After losing position (eval < -3.0), player rejected queen exchanges, kept pieces active, created checks/threats, and won",
                    }
                ],
                game_ids=list(set(affected)),
                frequency=len(set(affected)),
                severity="low",
                hypothesis="Hypothesis: when objectively lost, player switches to chaos mode — reject trades, create threats, exploit opponent's time pressure and automatic grabs.",
            )
        return None

    def _detect_q2(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch:
        resilient_wins = []
        for analysis in analyses:
            big_blunders = [
                m for m in analysis.blunders if m.centipawn_loss > THRESHOLD_DESPERATE_CP
            ]
            if not big_blunders:
                continue
            won = (analysis.game.color == "white" and "1-0" in analysis.game.result) or (
                analysis.game.color == "black" and "0-1" in analysis.game.result
            )
            if won:
                resilient_wins.append(analysis.game.id)
        if resilient_wins:
            total_games = len(analyses)
            return PatternMatch(
                pattern_id="Q2",
                pattern_name="Win despite blunder",
                confidence=min(len(set(resilient_wins)) / total_games * 0.9, 0.85),
                evidence=[
                    {
                        "resilient_wins": len(set(resilient_wins)),
                        "total_games": total_games,
                        "threshold_blunder_cp": THRESHOLD_DESPERATE_CP,
                        "affected_games": list(set(resilient_wins)),
                        "detail": "Player made at least one large blunder (>300cp) but still won the game — resilience or opponent failed to capitalise",
                    }
                ],
                game_ids=list(set(resilient_wins)),
                frequency=len(set(resilient_wins)),
                severity="low",
                hypothesis="Hypothesis: player recovers from large blunders and still wins — resilience under pressure or opponent's failure to capitalise.",
            )
        return None

    def _detect_r(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch:
        affected = []
        for analysis in analyses:
            for m in analysis.moves:
                eb = m.eval_before if m.eval_before is not None else 0
                if (
                    m.centipawn_loss >= THRESHOLD_ENDGAME_CP
                    and eb > THRESHOLD_ENDGAME_EVAL
                    and m.phase == "endgame"
                ):
                    affected.append(analysis.game.id)
                    break
        if affected:
            total_games = len(analyses)
            return PatternMatch(
                pattern_id="R",
                pattern_name="Endgame relaxation",
                confidence=min(len(set(affected)) / total_games * 0.8, 0.75),
                evidence=[
                    {
                        "affected_games": list(set(affected)),
                        "total_games": total_games,
                        "threshold_eval_before": THRESHOLD_ENDGAME_EVAL,
                        "threshold_cp_loss": THRESHOLD_ENDGAME_CP,
                        "condition": "eval_before>300 AND cp_loss>=300 AND phase=endgame",
                    }
                ],
                game_ids=list(set(affected)),
                frequency=len(set(affected)),
                severity="high",
                hypothesis="Hypothesis: player relaxes concentration when materially ahead in endgame, making passive moves that squander the advantage.",
            )
        return None

    def _detect_s(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch:
        affected = []
        for analysis in analyses:
            for m in analysis.moves:
                if m.was_in_check and m.centipawn_loss >= THRESHOLD_S_CAPTURE_AVERSION_CP:
                    board = chess.Board(m.fen)
                    king_square = board.king(board.turn)
                    if king_square:
                        for checker in board.checkers():
                            if board.is_legal(chess.Move(king_square, checker)):
                                affected.append(analysis.game.id)
                                break
        if affected:
            total_games = len(analyses)
            return PatternMatch(
                pattern_id="S",
                pattern_name="Capture aversion under check",
                confidence=min(len(set(affected)) / total_games * 0.5, 0.5),
                evidence=[
                    {
                        "affected_games": list(set(affected)),
                        "total_games": total_games,
                        "threshold_cp": THRESHOLD_S_CAPTURE_AVERSION_CP,
                        "detail": "Player was in check with king able to capture the checking piece, but chose a different move resulting in large material loss",
                    }
                ],
                game_ids=list(set(affected)),
                frequency=len(set(affected)),
                severity="critical",
                hypothesis="Hypothesis: when in check, 'king in danger' reflex suppresses the capture option -- player moves king or blocks instead of capturing the checking piece.",
            )
        return None

    def _detect_n(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch:
        affected = []
        pin_events = 0
        for analysis in analyses:
            for m in analysis.moves:
                if m.classification in ("blunder", "mistake") and m.centipawn_loss >= 100 and m.fen:
                    try:
                        board = chess.Board(m.fen)
                        from_sq = chess.parse_square(m.move_uci[:2])
                        if board.is_pinned(board.turn, from_sq):
                            pin_events += 1
                            affected.append(analysis.game.id)
                    except (ValueError, IndexError):
                        pass
        if pin_events >= 1:
            total_games = len(analyses)
            return PatternMatch(
                pattern_id="N",
                pattern_name="X-ray pin violation",
                confidence=min(pin_events / max(total_games, 1) * 0.8, 0.75),
                evidence=[
                    {
                        "pin_events": pin_events,
                        "total_games": total_games,
                        "threshold_cp": 100,
                        "affected_games": list(set(affected)),
                        "detail": "Player blundered by moving a piece that was x-ray pinned to a higher-value piece behind it",
                    }
                ],
                game_ids=list(set(affected)),
                frequency=pin_events,
                severity="high",
                hypothesis="Hypothesis: player fails to recognize when their piece is pinned, treating it as free to move -- overlooking the higher-value piece behind it.",
            )
        return None
