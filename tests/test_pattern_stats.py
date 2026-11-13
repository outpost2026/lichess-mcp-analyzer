"""P1 / schema 1.3: every cross-game pattern publishes N, rate, Wilson CI and
(only where a real contrast exists) lift with a Katz CI.

Contract under test:
- `n_games` = unique affected games, `n_units` = analysed games,
- `rate` is `n_games / n_units`, always inside its own CI,
- `lift` is never fabricated: patterns without a runtime control group carry
  `lift_unavailable_reason` and `lift = None`,
- `stats_dict()` is the single serialization surface used by both publishers.
"""

from __future__ import annotations

from lichess_analyzer_mcp.kb.schemas import validate_against_schema
from lichess_analyzer_mcp.models.game import GameAnalysis, GameSummary, MoveAnalysis
from lichess_analyzer_mcp.services.coaching_base import collect_patterns_for_games
from lichess_analyzer_mcp.services.pattern_detector import LIFT_NO_CONTROL, PatternDetector


def _blunder(ply: int) -> MoveAnalysis:
    return MoveAnalysis(
        ply=ply,
        move_uci="e2e4",
        move_san="e4",
        eval_before=0.0,
        eval_after=-3.0,
        win_prob_before=0.5,
        win_prob_after=0.1,
        centipawn_loss=300.0,
        classification="blunder",
        best_move_uci="e2e4",
        best_move_san="e4",
        is_tactical_motif=False,
        motif_type=None,
        phase="middlegame",
    )


def _game(
    gid: str,
    color: str = "white",
    opponent: str = "Named",
    blunders: int = 1,
) -> GameAnalysis:
    moves = [_blunder(2 * i + 1) for i in range(blunders)]
    analysis = GameAnalysis(
        game=GameSummary(
            id=gid,
            platform="lichess",
            opening="",
            opening_eco="",
            color=color,
            result="1-0",
            opponent_name=opponent,
        ),
        moves=moves,
    )
    analysis.blunders = list(moves)
    return analysis


def _mixed_cohort() -> list[GameAnalysis]:
    """4 anonymous games with 3 blunders, 4 named games with 1 blunder."""
    games = [_game(f"a{i}", opponent="Anonymous 1500", blunders=3) for i in range(4)]
    games += [_game(f"n{i}", opponent="Named", blunders=1) for i in range(4)]
    return games


def _detect(games: list[GameAnalysis]) -> dict:
    matches = PatternDetector().detect_all(games, {"username": "t", "total_games": len(games)})
    return {m.pattern_id: m for m in matches}


class TestMeasuredUncertainty:
    def test_every_match_has_n_and_rate_inside_ci(self):
        games = _mixed_cohort()
        matches = _detect(games)
        assert matches
        for pid, m in matches.items():
            assert m.n_units == len(games), pid
            assert 0 < m.n_games <= m.n_units, pid
            assert m.rate == round(m.n_games / m.n_units, 4), pid
            assert m.rate_ci_low <= m.rate <= m.rate_ci_high, pid
            assert m.support == m.rate, pid

    def test_anonymous_pattern_has_contrast_lift(self):
        match = _detect(_mixed_cohort())["A"]
        assert match.lift_basis == "anonymous_vs_named"
        # 12 blunders / 4 anon games vs 4 / 4 named = 3.0
        assert match.lift == 3.0
        assert match.lift_ci_low <= match.lift <= match.lift_ci_high
        assert match.lift_unavailable_reason is None

    def test_color_pattern_has_contrast_lift(self):
        games = [_game(f"w{i}", color="white", blunders=3) for i in range(4)]
        games += [_game(f"b{i}", color="black", blunders=1) for i in range(4)]
        match = _detect(games)["G"]
        assert match.lift_basis == "white_vs_black"
        assert match.lift == 3.0

    def test_pattern_without_control_group_never_invents_lift(self):
        games = [_game(f"c{i}", blunders=2) for i in range(4)]
        matches = _detect(games)
        assert "C" in matches
        match = matches["C"]
        assert match.lift is None
        assert match.lift_ci_low is None
        assert match.lift_unavailable_reason == LIFT_NO_CONTROL

    def test_zero_event_contrast_omits_lift_but_keeps_reason(self):
        # Anonymous games exist but have no blunders: A cannot fire, so use G
        # with a zero-blunder side and check the fallback message path directly.
        games = [_game(f"w{i}", color="white", blunders=2) for i in range(4)]
        games += [_game(f"b{i}", color="black", blunders=0) for i in range(4)]
        matches = _detect(games)
        if "G" in matches:
            assert matches["G"].lift is None
            assert "zero events" in (matches["G"].lift_unavailable_reason or "")


class TestSerialization:
    def test_stats_dict_shape(self):
        match = _detect(_mixed_cohort())["A"]
        stats = match.stats_dict()
        assert stats["n_games"] == match.n_games
        assert stats["n_units"] == match.n_units
        assert stats["rate_ci"] == {"low": match.rate_ci_low, "high": match.rate_ci_high}
        assert stats["lift_ci"] == {"low": match.lift_ci_low, "high": match.lift_ci_high}
        assert stats["lift_basis"] == "anonymous_vs_named"
        assert "lift_unavailable_reason" not in stats

    def test_stats_dict_reason_for_non_contrast_pattern(self):
        games = [_game(f"c{i}", blunders=2) for i in range(4)]
        stats = _detect(games)["C"].stats_dict()
        assert stats["lift"] is None
        assert stats["lift_unavailable_reason"] == LIFT_NO_CONTROL
        assert "lift_basis" not in stats

    def test_coaching_base_publishes_uncertainty(self):
        entries = collect_patterns_for_games(_mixed_cohort(), "t")
        assert entries
        for entry in entries:
            assert {"n_games", "n_units", "rate", "rate_ci", "lift", "lift_ci"} <= set(entry)
            assert entry["rate_ci"]["low"] <= entry["rate"] <= entry["rate_ci"]["high"]
        entry_a = next(e for e in entries if e["pattern_id"] == "A")
        assert entry_a["lift_basis"] == "anonymous_vs_named"


class TestSchema13Validation:
    def _artifact(self, **pattern_overrides) -> dict:
        pattern = {
            "pattern_id": "C",
            "pattern_name": "Attention tunneling",
            "confidence": 60.0,
            "strength": 60.0,
            "support": 0.5,
            "frequency": 4,
            "severity": "medium",
            "n_games": 2,
            "n_units": 4,
            "rate": 0.5,
            "rate_ci": {"low": 0.15, "high": 0.85},
            "lift": None,
            "lift_ci": {"low": None, "high": None},
            "lift_unavailable_reason": LIFT_NO_CONTROL,
        }
        pattern.update(pattern_overrides)
        return {
            "schema_version": "1.3",
            "username": "t",
            "games_analyzed": 4,
            "patterns_detected": [pattern],
            "total_patterns": 1,
        }

    def test_valid_artifact_has_no_errors(self):
        assert validate_against_schema(self._artifact()) == []

    def test_n_games_above_units_is_rejected(self):
        errors = validate_against_schema(self._artifact(n_games=5))
        assert any("exceeds n_units" in e for e in errors)

    def test_rate_outside_ci_is_rejected(self):
        errors = validate_against_schema(
            self._artifact(rate=0.9, rate_ci={"low": 0.1, "high": 0.5})
        )
        assert any("outside its CI" in e for e in errors)

    def test_missing_lift_reason_is_rejected(self):
        errors = validate_against_schema(self._artifact(lift_unavailable_reason=""))
        assert any("no lift and no lift_unavailable_reason" in e for e in errors)

    def test_unsupported_schema_version_is_rejected(self):
        artifact = self._artifact()
        artifact["schema_version"] = "1.2"
        assert any("not supported" in e for e in validate_against_schema(artifact))
