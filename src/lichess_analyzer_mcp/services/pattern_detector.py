"""Pattern detection engine for patterns A-Q1, I2, Q2, S.

Overlap note — S vs J:
  Both patterns fire when a player is in check and makes a non-capture, non-king
  block. Pattern S (capture_aversion_under_check) additionally requires that the
  KING COULD capture the checking piece. If king-capture is possible but player
  blocks, BOTH patterns trigger. Dedup strategy: prefer S (more specific) when
  (game_id, ply) match. Currently not implemented — both patterns report independently.
"""

from collections import Counter
import chess

from lichess_analyzer_mcp.models.pattern import (
    PATTERN_STATUS_MATCHED,
    PATTERN_STATUS_UNCLASSIFIED,
    PatternMatch,
    PatternLibrary,
    UNCLASSIFIED_CAPTURE,
    UNCLASSIFIED_EVIDENCE_GAP,
    UNCLASSIFIED_FORCING_MOVE,
    UNCLASSIFIED_MECHANISM,
    UNCLASSIFIED_QUIET_POSITIONAL,
)
from lichess_analyzer_mcp.models.game import GameAnalysis, effective_phase
from lichess_analyzer_mcp.services import board_facts
from lichess_analyzer_mcp.services.provenance import build_provenance
from lichess_analyzer_mcp.services.stability import build_stability
from lichess_analyzer_mcp.services.statistics import rate_ratio_with_ci, rate_with_ci

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

# P1 / schema 1.3: patterns without a runtime control group must say so instead
# of publishing a fabricated lift. Admission-time lift is measured offline
# (PATTERN_DISCOVERY_METHODOLOGY 2.3) and is not available per detection run.
LIFT_NO_CONTROL = (
    "runtime detector has no control group; lift is measured at admission time (methodology 2.3)"
)


def is_piece_block(move_san: str, was_in_check: bool) -> bool:
    """J predicate shared by single-game and cross-game detection (D11).

    A check block must be a non-capture by a **piece**. A king move is an
    escape, never a block, so it must not trigger J in either path.
    """
    san = move_san or ""
    return bool(was_in_check) and "x" not in san and not san.startswith("K")


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
        provenance = build_provenance(analyses, self.library)
        for match in matches:
            match.provenance = provenance
            self._attach_statistics(match, analyses)
        self._attach_stability(matches, analyses)
        return matches

    @staticmethod
    def _attach_stability(matches: list[PatternMatch], analyses: list[GameAnalysis]) -> None:
        """Attach split-half stability and temporal drift (schema 1.4).

        Both metrics are per-pattern and depend only on which games contain the
        pattern, so they are computed once for the cohort and copied onto every
        match. Nothing here changes detection or `strength`.
        """
        if not matches:
            return
        # Unit = game id, matching `n_games`: when the cache holds the same game
        # analysed for both colours, it collapses to one unit instead of
        # counting the same game twice.
        key_of: dict[str, str] = {}
        for a in analyses:
            key_of.setdefault(a.game.id, f"{a.game.id}|{a.game.color}")
        games = [(key_of[a.game.id], a.game.date) for a in analyses]
        pattern_games = {
            m.pattern_id: [key_of[gid] for gid in set(m.game_ids) if gid in key_of] for m in matches
        }
        stability = build_stability(pattern_games, games)
        for match in matches:
            match.stability = stability["patterns"].get(match.pattern_id)

    @staticmethod
    def _attach_statistics(match: PatternMatch, analyses: list[GameAnalysis]) -> None:
        """Fill N, rate and Wilson CI from the measured game set (schema 1.3).

        Unit is the game, not the event: `n_games` / `n_units` is the only
        denominator that is defined for every cross-game pattern. `frequency`
        stays detector-specific (events for B/J/N, games for C/P/R/S) and must
        never be read as N.
        """
        match.n_games = len(set(match.game_ids))
        match.n_units = len(analyses)
        stats = rate_with_ci(match.n_games, match.n_units)
        match.rate = stats["rate"]
        match.rate_ci_low = stats["ci_low"]
        match.rate_ci_high = stats["ci_high"]
        match.support = match.rate or 0.0
        if match.lift is None:
            match.lift_unavailable_reason = LIFT_NO_CONTROL

    @staticmethod
    def _set_lift(match: PatternMatch, k1: int, n1: int, k2: int, n2: int, basis: str) -> None:
        """Attach a rate ratio with a Katz log-method CI (only real contrasts)."""
        ratio = rate_ratio_with_ci(k1, n1, k2, n2)
        if ratio is None:
            match.lift_unavailable_reason = "contrast group has zero events; lift is not estimable"
            return
        match.lift = ratio["lift"]
        match.lift_ci_low = ratio["ci_low"]
        match.lift_ci_high = ratio["ci_high"]
        match.lift_basis = basis

    def _detect_a(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch | None:
        anonymous_games = [a for a in analyses if "anonymous" in a.game.opponent_name.lower()]
        named_games = [a for a in analyses if "anonymous" not in a.game.opponent_name.lower()]
        if not anonymous_games or not named_games:
            return None
        anon_blunder_rate = sum(len(g.blunders) for g in anonymous_games) / len(anonymous_games)
        named_blunder_rate = sum(len(g.blunders) for g in named_games) / len(named_games)
        if named_blunder_rate > 0 and anon_blunder_rate / named_blunder_rate > 1.3:
            match = PatternMatch(
                pattern_id="A",
                pattern_name="Anonymous effect",
                strength=min(anon_blunder_rate / named_blunder_rate / 2, 0.95),
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
            self._set_lift(
                match,
                sum(len(g.blunders) for g in anonymous_games),
                len(anonymous_games),
                sum(len(g.blunders) for g in named_games),
                len(named_games),
                "anonymous_vs_named",
            )
            return match
        return None

    def _detect_b(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch | None:
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
                strength=min(ratio * 2, 0.95),
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

    def _detect_c(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch | None:
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
                strength=min(len(set(affected)) / total_games * 0.9, 0.85),
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

    def _detect_g(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch | None:
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
                dominant_games = (
                    white_analyses if white_blunder_rate > black_blunder_rate else black_analyses
                )
                other_games = (
                    black_analyses if white_blunder_rate > black_blunder_rate else white_analyses
                )
                affected_ids = [g.game.id for g in dominant_games]
                match = PatternMatch(
                    pattern_id="G",
                    pattern_name="Color as modulator",
                    strength=min(ratio / 3, 0.95),
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
                self._set_lift(
                    match,
                    sum(len(g.blunders) for g in dominant_games),
                    len(dominant_games),
                    sum(len(g.blunders) for g in other_games),
                    len(other_games),
                    "white_vs_black",
                )
                return match
        return None

    def _detect_i2(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch | None:
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
                strength=min(0.05 + gift_count / max(total_games, 1) * 0.8, 0.9),
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

    def _detect_j(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch | None:
        affected = []
        block_count = 0
        for analysis in analyses:
            for m in analysis.moves:
                if (
                    m.classification in ("blunder", "mistake")
                    and m.centipawn_loss >= THRESHOLD_BLOCK_CP
                    and is_piece_block(m.move_san, m.was_in_check)
                ):
                    block_count += 1
                    affected.append(analysis.game.id)
        if block_count >= 1:
            total_games = len(analyses)
            return PatternMatch(
                pattern_id="J",
                pattern_name="Impulsive check block",
                strength=min(block_count / total_games * 0.9, 0.85),
                evidence=[
                    {
                        "impulsive_blocks": block_count,
                        "total_games": total_games,
                        "threshold_cp": THRESHOLD_BLOCK_CP,
                        "affected_games": list(set(affected)),
                        "detail": "Player was in check and blocked with a piece instead of capturing the checking piece or retreating the king, leading to material loss or positional collapse",
                    }
                ],
                game_ids=list(set(affected)),
                frequency=block_count,
                severity="high",
                hypothesis="Hypothesis: when in check, player reflexively blocks with a piece without evaluating king safety — silencing an alert instead of fixing the root cause.",
            )
        return None

    def _detect_o(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch | None:
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
            return PatternMatch(
                pattern_id="O",
                pattern_name="Stagnační panika",
                strength=min(len(set(affected)) / total_games * 0.8, 0.85),
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

    def _detect_p(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch | None:
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
                strength=min(len(set(affected)) / total_games * 0.7, 0.75),
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

    def _detect_q(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch | None:
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
                strength=min(len(set(affected)) / total_games * 0.9, 0.85),
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

    def _detect_q1(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch | None:
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
                strength=min(len(set(affected)) / total_games * 0.8, 0.75),
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

    def _detect_q2(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch | None:
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
                strength=min(len(set(resilient_wins)) / total_games * 0.9, 0.85),
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

    def _detect_r(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch | None:
        affected = []
        for analysis in analyses:
            for m in analysis.moves:
                eb = m.eval_before if m.eval_before is not None else 0
                if (
                    m.centipawn_loss >= THRESHOLD_ENDGAME_CP
                    and eb > THRESHOLD_ENDGAME_EVAL
                    and effective_phase(m) == "endgame"
                ):
                    affected.append(analysis.game.id)
                    break
        if affected:
            total_games = len(analyses)
            return PatternMatch(
                pattern_id="R",
                pattern_name="Endgame relaxation",
                strength=min(len(set(affected)) / total_games * 0.8, 0.75),
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

    def _detect_s(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch | None:
        affected = []
        for analysis in analyses:
            for m in analysis.moves:
                if (
                    m.was_in_check
                    and m.centipawn_loss >= THRESHOLD_S_CAPTURE_AVERSION_CP
                    and m.fen
                    and board_facts.king_can_capture_checker(m.fen)
                    and not board_facts.played_king_capture_of_checker(m.fen, m.move_uci)
                ):
                    affected.append(analysis.game.id)
        if affected:
            total_games = len(analyses)
            return PatternMatch(
                pattern_id="S",
                pattern_name="Capture aversion under check",
                strength=min(len(set(affected)) / total_games * 0.5, 0.5),
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

    def _detect_n(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch | None:
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
                strength=min(pin_events / max(total_games, 1) * 0.8, 0.75),
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


# ── Single-game pattern surface (P0.4) ───────────────────────────────────────
# Cross-game detectors above answer questions such as "do you play worse versus
# anonymous opponents?" — they have no denominator for one game and must not be
# unlocked by lowering `min_games`. This function only reuses per-move signals
# that exist inside a single game and labels its output with scope=single_game.


def per_move_patterns(
    move,
    prev_move=None,
    in_check: bool | None = None,
) -> list[dict]:
    """Jediná implementace per-move patternů B/J/R/S/C/T (P0-2).

    Obě cesty ji volají, takže BFS (``game_analyzer._per_blunder_patterns`` →
    BlunderFactSheet) a single-game (``_single_game_candidate`` → compact)
    musí pro stejný tah vrátit stejné patterny i confidence
    (akceptance REFACTOR_PLAN §P0-2: „BFS = single-game patterny").

    - ``in_check``: výchozí ``move.was_in_check``; BFS předává svůj parametr.
    - Práh ``R`` chrání ``(move.eval_before or 0)`` (P0-3/None politika).
    - Predikát S: ``board_facts`` (P0-1), typ figury, ne SAN ``x``.
    - Fáze ``R``: ``effective_phase`` (P0-3, oba režimy ``phase_method``).
    """
    if in_check is None:
        in_check = bool(getattr(move, "was_in_check", False))
    cp = float(move.centipawn_loss or 0)
    out: list[dict] = []

    # B — Automatic grab: capture that is a blunder/mistake
    if "x" in (move.move_san or "") and cp >= THRESHOLD_GRAB_CP:
        out.append(
            {
                "pattern_id": "B",
                "pattern_name": "Automatic grab",
                "strength": min(cp / 500, 0.95),
                "detail": f"capture with cp_loss={cp:.0f}",
            }
        )

    # J — Impulsive check block: in check, non-capture by a piece, cp_loss >= THRESHOLD_BLOCK_CP
    if is_piece_block(move.move_san, in_check) and cp >= THRESHOLD_BLOCK_CP:
        out.append(
            {
                "pattern_id": "J",
                "pattern_name": "Impulsive check block",
                "strength": min(cp / 600, 0.85),
                "detail": f"check block with cp_loss={cp:.0f}",
            }
        )

    # R — Endgame relaxation: endgame, eval_before > THRESHOLD_ENDGAME_EVAL, cp_loss >= THRESHOLD_ENDGAME_CP
    # P0-3: faze pres effective_phase (oba rezimy phase_method; default = segment).
    if (
        effective_phase(move) == "endgame"
        and (move.eval_before or 0) > THRESHOLD_ENDGAME_EVAL
        and cp >= THRESHOLD_ENDGAME_CP
    ):
        out.append(
            {
                "pattern_id": "R",
                "pattern_name": "Endgame relaxation",
                "strength": min(cp / 1000, 0.85),
                "detail": f"endgame eval_before={move.eval_before or 0:.0f}, cp_loss={cp:.0f}",
            }
        )

    # S — Capture aversion under check: in check, king could capture the checker
    # but did not. Same predicate as cross-game `_detect_s` (board_facts).
    if (
        in_check
        and cp >= THRESHOLD_S_CAPTURE_AVERSION_CP
        and board_facts.king_can_capture_checker(move.fen)
        and not board_facts.played_king_capture_of_checker(move.fen, move.move_uci)
    ):
        out.append(
            {
                "pattern_id": "S",
                "pattern_name": "Capture aversion under check",
                "strength": 0.4,
                "detail": "king capture available but not played",
            }
        )

    # C — Attention tunneling: consecutive errors
    if prev_move is not None and prev_move.classification in ("blunder", "mistake") and cp >= 200:
        out.append(
            {
                "pattern_id": "C",
                "pattern_name": "Attention tunneling",
                "strength": min(cp / 500, 0.8),
                "detail": f"consecutive error after ply={prev_move.ply} cp_loss={cp:.0f}",
            }
        )

    # T — Tactical oversight: motif present with real loss
    if move.is_tactical_motif and cp >= 50:
        out.append(
            {
                "pattern_id": "T",
                "pattern_name": "Tactical oversight",
                "strength": min(cp / 400, 0.8),
                "detail": f"motif={move.motif_type or 'tactical'} cp_loss={cp:.0f}",
            }
        )

    return out


def _single_game_candidate(move, prev_move) -> list[dict]:
    """Thin wrapper nad společným jádrem (P0-2: jediná implementace)."""
    return per_move_patterns(move, prev_move)


# ── P0-7: coverage of flagged moves ──────────────────────────────────────────
# A coaching payload must never stay silent about a flagged move. Every
# blunder/mistake/inaccuracy is either MATCHED by a per-move pattern or carries
# an explicit UNCLASSIFIED reason. The reason states WHY the detector is silent
# (a measured shape of the move), it is NOT a mechanism claim: D4 keeps new
# patterns out until the taxonomy is calibrated (docs/CANDIDATE_PATTERNS_2026-11-12.md).
# The vocabulary itself lives in `models.pattern` so the compact serializer can
# validate it without importing python-chess.


def unclassified_reason_for(
    *,
    san: str,
    in_check: bool,
    gives_check: bool,
    has_engine_evidence: bool,
) -> str:
    """Deterministic reason why no per-move pattern covers a flagged move.

    Decision order (first match wins) — each branch is a measured property of
    the move, not an interpretation:

    1. `evidence_gap` — no SAN text and no engine comparison: the move has no
       shape to describe (family Z). Measured 2026-11-12: the game cache carries
       SAN for every flagged move, so this branch is a guard, not the norm.
       Absence of a PV is NOT a per-move reason: it is a global property of the
       payload and is reported in `patterns_meta` instead. Otherwise 88 % of the
       cache would read "evidence_gap" while the shape (quiet/capture/check) is
       known — the reason must describe the move, not the cache fidelity.
    2. `quiet_positional` — no capture, no check, not in check (family F7 core:
       the measured 51/97 quiet blunders without any proxy).
    3. `forcing_move_unexplained` — the move gives check or was played out of
       check but no pattern fired (family F3 candidate).
    4. `capture_unexplained` — a capture below the `B` threshold (family F4).
    5. `mechanism_not_identified` — fallback; still explicit.
    """
    text = san or ""
    if not text:
        return UNCLASSIFIED_EVIDENCE_GAP if not has_engine_evidence else UNCLASSIFIED_MECHANISM
    is_capture = "x" in text
    is_check = bool(gives_check) or "+" in text or "#" in text
    if not is_capture and not is_check and not in_check:
        return UNCLASSIFIED_QUIET_POSITIONAL
    if is_check or in_check:
        return UNCLASSIFIED_FORCING_MOVE
    if is_capture:
        return UNCLASSIFIED_CAPTURE
    return UNCLASSIFIED_MECHANISM


def _has_engine_evidence(move) -> bool:
    if getattr(move, "best_move_san", ""):
        return True
    if getattr(move, "engine_lines", None):
        return True
    return int(getattr(move, "played_rank", 0) or 0) >= 1


def unclassified_reason(move) -> str:
    """Reason code for a `MoveAnalysis` that no per-move pattern covers."""
    return unclassified_reason_for(
        san=getattr(move, "move_san", "") or "",
        in_check=bool(getattr(move, "was_in_check", False)),
        gives_check=bool(getattr(move, "gives_check", False)),
        has_engine_evidence=_has_engine_evidence(move),
    )


def unclassified_reason_from_flag(flag: dict) -> str:
    """Same contract for a serialized flagged-move dict (payload/compact path).

    Accepts both raw `GameAnalysis.to_dict()` keys (`move_san`, `gives_check`,
    `was_in_check`) and `coaching_single_game._flagged_moves` keys (`san`,
    `check`, `in_check_before`).
    """
    san = flag.get("san") or flag.get("move_san") or ""
    in_check = flag.get("in_check_before")
    if in_check is None:
        in_check = flag.get("was_in_check", False)
    gives_check = flag.get("check")
    if gives_check is None:
        gives_check = flag.get("gives_check", False)
    has_evidence = bool(
        flag.get("best_move_san")
        or flag.get("engine_lines")
        or int(flag.get("played_rank") or 0) >= 1
    )
    return unclassified_reason_for(
        san=san,
        in_check=bool(in_check),
        gives_check=bool(gives_check),
        has_engine_evidence=has_evidence,
    )


def scan_single_game(analysis: GameAnalysis) -> tuple[list[dict], dict[int, dict]]:
    """Single pass over the game: aggregated patterns + per-ply coverage.

    Returns `(patterns, coverage)`. `coverage` has one entry per flagged move
    (blunder/mistake/inaccuracy) that was measured:

        {ply: {"pattern_status": "matched"|"unclassified",
               "unclassified_reason": str|None,
               "pattern_ids": [str, ...]}}

    Keeping both products in one function guarantees the pattern list and the
    coverage map can never disagree (P0-7 acceptance: 100 % of flagged moves
    has either a pattern or a reason).
    """
    library = PatternLibrary().load_baseline().patterns
    aggregated: dict[str, dict] = {}
    coverage: dict[int, dict] = {}

    for idx, move in enumerate(analysis.moves):
        if not move.analyzed or move.centipawn_loss is None:
            continue
        if move.classification not in ("blunder", "mistake", "inaccuracy"):
            continue
        prev_move = analysis.moves[idx - 1] if idx > 0 else None
        candidates = _single_game_candidate(move, prev_move)
        coverage[move.ply] = {
            "pattern_status": PATTERN_STATUS_MATCHED if candidates else PATTERN_STATUS_UNCLASSIFIED,
            "unclassified_reason": None if candidates else unclassified_reason(move),
            "pattern_ids": [cand["pattern_id"] for cand in candidates],
        }
        for cand in candidates:
            pid = cand["pattern_id"]
            entry = aggregated.get(pid)
            if entry is None:
                pdef = library.get(pid)
                entry = {
                    "pattern_id": pid,
                    "pattern_name": cand["pattern_name"],
                    # P1: strength = ordinal event strength (0..1), not a probability.
                    "strength": 0.0,
                    "confidence": 0.0,  # legacy alias kept for 1.2 consumers
                    "frequency": 0,
                    "severity": pdef.severity if pdef else "medium",
                    "scope": "single_game",
                    "evidence": [],
                    "affected_games": [analysis.game.id] if analysis.game.id else [],
                }
                entry["mitigation"] = (
                    pdef.mitigation
                    if pdef is not None
                    else (
                        "Review the engine line for each occurrence and compare the "
                        "played move with the top engine choice."
                    )
                )
                aggregated[pid] = entry
            entry["frequency"] += 1
            entry["strength"] = round(max(entry["strength"], cand["strength"]), 2)
            entry["confidence"] = entry["strength"]
            entry["evidence"].append(
                {
                    "ply": move.ply,
                    "san": move.move_san,
                    "cp_loss": round(float(move.centipawn_loss), 1),
                    "phase": effective_phase(move),
                    "detail": cand["detail"],
                }
            )

    order = {"B": 0, "J": 1, "S": 2, "C": 3, "R": 4, "T": 5}
    patterns = sorted(
        aggregated.values(),
        key=lambda x: (order.get(x["pattern_id"], 99), -x["strength"]),
    )
    return patterns, coverage


def detect_single_game(analysis: GameAnalysis) -> list[dict]:
    """Deterministic per-game pattern surface (list-only compatibility wrapper).

    Only per-move evidence is aggregated. Cross-game detectors are explicitly
    not run; the caller reports `cross_game_suppressed`. Callers that also need
    P0-7 coverage use :func:`scan_single_game` instead of calling both.
    """
    return scan_single_game(analysis)[0]
