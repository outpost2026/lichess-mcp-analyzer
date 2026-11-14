"""T2.2: move counts distinguish player plies from whole-game plies."""

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lichess_analyzer_mcp.models.game import GameAnalysis, GameSummary
from lichess_analyzer_mcp.tools.coaching_single_game import _move_counts


def _analysis(**kwargs) -> dict:
    base = {"moves": [{"ply": p} for p in range(1, 41, 2)]}
    base.update(kwargs)
    return base


def test_counts_split_player_and_opponent_plies():
    counts = _move_counts(_analysis(game_plies_total=40))
    assert counts["player_moves_total"] == 20
    assert counts["game_plies_total"] == 40
    assert counts["opponent_moves_total"] == 20
    # Deprecated alias keeps its old meaning (player plies) for one release.
    assert counts["moves_total"] == 20


def test_legacy_cache_without_total_publishes_null_not_a_guess():
    counts = _move_counts(_analysis())
    assert counts["player_moves_total"] == 20
    assert counts["game_plies_total"] is None
    assert counts["opponent_moves_total"] is None


def test_opponent_total_never_negative_on_inconsistent_input():
    counts = _move_counts(_analysis(game_plies_total=10))
    assert counts["opponent_moves_total"] == 0


def test_game_analysis_roundtrip_keeps_plies_total():
    summary = GameSummary(
        id="g",
        platform="lichess",
        opening="",
        opening_eco="",
        color="white",
        result="1-0",
    )
    analysis = GameAnalysis(game=summary, game_plies_total=42)
    restored = GameAnalysis.from_dict(analysis.to_dict())
    assert restored.game_plies_total == 42
