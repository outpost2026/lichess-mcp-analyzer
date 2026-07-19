"""Pattern detection engine for patterns A-Q1."""

from src.models.pattern import PatternDef, PatternMatch, PatternLibrary
from src.models.game import GameAnalysis


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
                        "anonymous_blunder_rate": anon_blunder_rate,
                        "named_blunder_rate": named_blunder_rate,
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
                if m.classification in ("blunder", "mistake") and m.centipawn_loss > 150:
                    if "x" in m.move_san:
                        total_captures += 1
                        blunder_captures += 1
                        affected_games.append(analysis.game.id)
        if blunder_captures >= 2:
            return PatternMatch(
                pattern_id="B",
                pattern_name="Automatic grab",
                confidence=min(blunder_captures / max(total_captures, 1), 0.95),
                evidence=[{"blunder_captures": blunder_captures, "total_captures": total_captures}],
                game_ids=list(set(affected_games)),
                frequency=blunder_captures,
                severity="high",
                hypothesis="Hypothesis: player captures automatically without evaluating opponent's counterplay — analogous to git push --force.",
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
                return PatternMatch(
                    pattern_id="G",
                    pattern_name="Color as modulator",
                    confidence=min(ratio / 3, 0.95),
                    evidence=[
                        {
                            "white_blunder_rate": white_blunder_rate,
                            "black_blunder_rate": black_blunder_rate,
                            "asymmetry_ratio": round(ratio, 2),
                            "dominant_side": dominant,
                        }
                    ],
                    game_ids=[
                        g.game.id
                        for g in (
                            white_analyses
                            if white_blunder_rate > black_blunder_rate
                            else black_analyses
                        )
                    ],
                    frequency=int(max(white_blunder_rate, black_blunder_rate)),
                    severity="high",
                    hypothesis=f"Hypothesis: player's error rate shifts with color — {dominant} side has {ratio:.1f}x more blunders.",
                )
        return None

    def _detect_o(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch:
        affected = []
        for analysis in analyses:
            for i in range(len(analysis.moves) - 3):
                eval_vals = [m.eval_after for m in analysis.moves[i : i + 3]]
                if None in eval_vals:
                    continue
                if max(eval_vals) - min(eval_vals) < 0.3:
                    for j in range(i + 3, min(i + 6, len(analysis.moves))):
                        if analysis.moves[j].classification in ("blunder", "mistake"):
                            affected.append(analysis.game.id)
                            break
        if affected:
            return PatternMatch(
                pattern_id="O",
                pattern_name="Repetition avoidance greed",
                confidence=0.6,
                evidence=[{"affected_games": len(set(affected))}],
                game_ids=list(set(affected)),
                frequency=len(set(affected)),
                severity="critical",
                hypothesis="Hypothesis: player refuses threefold repetition hoping for more, which often leads to position collapse.",
            )
        return None

    def _detect_p(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch:
        affected = []
        for analysis in analyses:
            for m in analysis.moves:
                if m.classification in ("blunder", "mistake") and m.centipawn_loss >= 150:
                    if "x" in m.move_san or "Q" in m.move_san or "R" in m.move_san:
                        if m.eval_before is not None and m.eval_before > 0:
                            affected.append(analysis.game.id)
                            break
        if affected:
            return PatternMatch(
                pattern_id="P",
                pattern_name="Visual misrecognition",
                confidence=0.5,
                evidence=[{"affected_games": len(set(affected))}],
                game_ids=list(set(affected)),
                frequency=len(set(affected)),
                severity="high",
                hypothesis="Hypothesis: player misreads tactical sequences involving captures or major pieces, overlooking counterplay.",
            )
        return None

    def _detect_r(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch:
        affected = []
        for analysis in analyses:
            for m in analysis.moves:
                eb = m.eval_before if m.eval_before is not None else 0
                if m.centipawn_loss >= 300 and eb > 300 and m.phase == "endgame":
                    affected.append(analysis.game.id)
                    break
        if affected:
            return PatternMatch(
                pattern_id="R",
                pattern_name="Endgame relaxation",
                confidence=0.7,
                evidence=[
                    {
                        "affected_games": len(set(affected)),
                        "condition": "eval_before>300 AND cp_loss>=300 AND phase=endgame",
                    }
                ],
                game_ids=list(set(affected)),
                frequency=len(set(affected)),
                severity="high",
                hypothesis="Hypothesis: player relaxes concentration when materially ahead in endgame, making passive moves that squander the advantage.",
            )
        return None

    def _detect_q(self, analyses: list[GameAnalysis], metadata: dict) -> PatternMatch:
        defensive_wins = []
        for analysis in analyses:
            big_blunders = [m for m in analysis.blunders if m.centipawn_loss > 200]
            if not big_blunders:
                continue
            won = (analysis.game.color == "white" and "1-0" in analysis.game.result) or (
                analysis.game.color == "black" and "0-1" in analysis.game.result
            )
            if won:
                defensive_wins.append(analysis.game.id)
        if defensive_wins:
            return PatternMatch(
                pattern_id="Q",
                pattern_name="Active defense",
                confidence=0.8,
                evidence=[{"defensive_wins": len(defensive_wins)}],
                game_ids=defensive_wins,
                frequency=len(defensive_wins),
                severity="low",
                hypothesis="Hypothesis: player prefers active counterplay over passive defense, creating winning chances even in lost positions.",
            )
        return None
