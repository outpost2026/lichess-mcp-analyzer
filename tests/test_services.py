"""Basic unit tests for services."""

import sys

sys.path.insert(0, "src")

from src.models.game import GameSummary, MoveAnalysis, GameAnalysis
from src.models.analysis import WeaknessReport
from src.models.pattern import PatternDef, PatternMatch, PatternLibrary
from src.models.srs_card import SRSCard, FSRSState
from src.models.player_profile import PlayerProfile, OpeningStats


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
