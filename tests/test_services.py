"""Unit tests for services."""

import sys

sys.path.insert(0, "src")

from lichess_analyzer_mcp.models.game import GameSummary, MoveAnalysis, GameAnalysis
from lichess_analyzer_mcp.models.analysis import WeaknessReport
from lichess_analyzer_mcp.models.pattern import PatternDef, PatternMatch, PatternLibrary
from lichess_analyzer_mcp.models.srs_card import SRSCard, FSRSState
from lichess_analyzer_mcp.models.player_profile import PlayerProfile, OpeningStats
from lichess_analyzer_mcp.services.compressibility_validator import compute_compression, compression_score
from lichess_analyzer_mcp.services.validator import validate_pattern_artifact, ValidationError
from lichess_analyzer_mcp.kb.schemas import validate_against_schema


class TestModels:
    def test_game_summary(self):
        g = GameSummary(
            id="abc123",
            platform="lichess",
            opening="Sicilian Defense",
            opening_eco="B20",
            color="white",
            result="1-0",
            opponent_name="opp",
            opponent_rating=2000,
            player_rating=1900,
            time_control="300+0",
            date="2026-04-01",
            url="https://lichess.org/abc123",
        )
        assert g.id == "abc123"
        assert g.color == "white"

    def test_move_analysis(self):
        m = MoveAnalysis(
            ply=12,
            move_uci="e2e4",
            move_san="e4",
            eval_before=0.2,
            eval_after=0.1,
            win_prob_before=0.5,
            win_prob_after=0.3,
            centipawn_loss=100,
            classification="mistake",
            best_move_uci="d2d4",
            best_move_san="d4",
            is_tactical_motif=False,
            motif_type=None,
            phase="opening",
        )
        assert m.classification == "mistake"
        assert m.centipawn_loss == 100

    def test_game_analysis(self):
        g = GameSummary(
            id="test",
            platform="lichess",
            opening="",
            opening_eco="",
            color="white",
            result="1-0",
            opponent_name="opp",
            opponent_rating=1500,
            player_rating=1500,
            time_control="",
            date="",
            url="",
        )
        a = GameAnalysis(game=g)
        assert a.total_acpl == 0.0
        assert len(a.moves) == 0

    def test_pattern_library_baseline(self):
        lib = PatternLibrary().load_baseline()
        assert "A" in lib.patterns
        assert "B" in lib.patterns
        assert "C" in lib.patterns
        assert len(lib.patterns) >= 8

    def test_pattern_match(self):
        m = PatternMatch(
            pattern_id="A",
            pattern_name="Test",
            confidence=0.8,
            evidence=[{"key": "val"}],
            game_ids=["g1"],
            frequency=3,
            severity="high",
        )
        assert m.pattern_id == "A"

    def test_srs_card(self):
        c = SRSCard(
            card_id="c1",
            fen="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
            correct_move_uci="e2e4",
            correct_move_san="e4",
            pattern_id="B",
            game_id="g1",
            opening="",
            phase="opening",
            centipawn_loss=300,
            created_at="2026-01-01",
            due="2026-01-01",
        )
        assert c.card_id == "c1"
        assert c.state == "New"

    def test_player_profile(self):
        p = PlayerProfile(username="test", platform="lichess")
        assert p.username == "test"
        assert p.total_games == 0

    def test_weakness_report(self):
        r = WeaknessReport(
            username="test",
            total_games_analyzed=5,
            total_acpl=80.0,
            blunder_count=10,
            mistake_count=5,
            inaccuracy_count=3,
        )
        assert r.total_acpl == 80.0
        assert r.blunder_count == 10

    def test_pattern_match_with_hypothesis(self):
        m = PatternMatch(
            pattern_id="Q",
            pattern_name="Active Defense",
            confidence=0.8,
            evidence=[{"key": "val"}],
            game_ids=["g1"],
            frequency=3,
            severity="low",
            hypothesis="Hypothesis: test",
        )
        assert m.hypothesis == "Hypothesis: test"
        assert m.hypothesis.startswith("Hypothesis:")

    def test_pattern_min_games_threshold(self):
        p = PatternDef(
            id="T",
            name="Test",
            pattern_type="test",
            mechanism="test",
            it_analogy="test",
            detection_method="test",
            severity="low",
            mitigation="test",
            min_games=5,
            min_occurrences=3,
        )
        assert p.min_games == 5
        assert p.min_occurrences == 3

    def test_compressibility_validator(self):
        g = GameSummary(
            id="g1",
            platform="lichess",
            opening="",
            opening_eco="",
            color="white",
            result="1-0",
            opponent_name="opp",
            opponent_rating=1500,
            player_rating=1500,
            time_control="",
            date="",
            url="",
        )
        a = GameAnalysis(game=g)
        for i in range(10):
            a.moves.append(
                MoveAnalysis(
                    ply=i,
                    move_uci="e2e4",
                    move_san="e4",
                    eval_before=0.2,
                    eval_after=0.1,
                    win_prob_before=0.5,
                    win_prob_after=0.3,
                    centipawn_loss=50,
                    classification="inaccuracy",
                    best_move_uci="d2d4",
                    best_move_san="d4",
                    is_tactical_motif=False,
                    motif_type=None,
                    phase="opening",
                )
            )
        m = PatternMatch(
            pattern_id="B",
            pattern_name="Auto grab",
            confidence=0.8,
            evidence=[{"cap": 2}],
            game_ids=["g1"],
            frequency=2,
            severity="high",
        )
        result = compute_compression(m, [a])
        assert result.compression_ratio is not None
        assert result.compression_ratio > 0
        assert compression_score(result) > 0

    def test_validator_passes(self):
        artifact = {
            "username": "test",
            "games_analyzed": 3,
            "patterns_detected": [
                {
                    "pattern_id": "Q",
                    "pattern_name": "Active Defense",
                    "confidence": 80,
                    "frequency": 2,
                    "severity": "low",
                    "hypothesis": "Hypothesis: test",
                }
            ],
        }
        issues = validate_pattern_artifact(artifact)
        assert len(issues) == 0

    def test_validator_fails_bad_conf(self):
        artifact = {
            "username": "test",
            "games_analyzed": 1,
            "patterns_detected": [
                {
                    "pattern_id": "Q",
                    "pattern_name": "Active Defense",
                    "confidence": 150,
                    "frequency": 1,
                    "severity": "low",
                }
            ],
        }
        issues = validate_pattern_artifact(artifact)
        assert len(issues) >= 1

    def test_validator_hypothesis_flag(self):
        artifact = {
            "username": "test",
            "games_analyzed": 1,
            "patterns_detected": [
                {
                    "pattern_id": "Q",
                    "pattern_name": "Active Defense",
                    "confidence": 50,
                    "frequency": 1,
                    "severity": "low",
                    "hypothesis": "not a hypothesis",
                }
            ],
        }
        issues = validate_pattern_artifact(artifact)
        assert any("hypothesis" in i for i in issues)

    def test_schema_validation(self):
        artifact = {
            "username": "test",
            "games_analyzed": 2,
            "patterns_detected": [
                {
                    "pattern_id": "A",
                    "pattern_name": "Test",
                    "confidence": 70,
                    "frequency": 2,
                    "severity": "high",
                    "hypothesis": "Hypothesis: test",
                }
            ],
            "total_patterns": 1,
        }
        errors = validate_against_schema(artifact)
        assert len(errors) == 0
