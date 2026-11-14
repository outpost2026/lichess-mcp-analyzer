"""T3.0: both surfaces share one engine policy and therefore one cache key."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lichess_analyzer_mcp.config.depth import DEPTH_DEFAULTS
from lichess_analyzer_mcp.models.game import GameAnalysis, GameSummary
from lichess_analyzer_mcp.services.game_analyzer import _cache_path, _policy_token
from lichess_analyzer_mcp.tools import analyze_game as analyze_game_tool

PGN = '[Result "1-0"]\n\n1. e4 e5 *'


def test_dead_dual_time_cap_stays_removed():
    """A time constant without a reader was deleted, not silently re-added."""
    assert "max_time_dual" not in DEPTH_DEFAULTS["limits"]


def test_policy_token_is_shared_between_surfaces():
    assert _policy_token(14, "fast") == "n150000"
    assert _policy_token(14, "legacy") == ""
    assert _cache_path("abcd1234", 14, "white", _policy_token(14, "fast")).endswith(
        "abcd1234_white_d14n150000.json"
    )


def test_analyze_game_passes_mode_to_both_perspectives(monkeypatch):
    calls = []

    def fake_analyze(pgn, player_color="white", depth=0, game_id=None, **kwargs):
        calls.append((player_color, kwargs.get("mode")))
        summary = GameSummary(
            id="abcd1234",
            platform="lichess",
            opening="",
            opening_eco="",
            color=player_color,
            result="1-0",
        )
        analysis = GameAnalysis(game=summary)
        analysis.total_acpl = 10.0
        return analysis

    monkeypatch.setattr(analyze_game_tool, "analyze_pgn", fake_analyze)
    result = asyncio.run(
        analyze_game_tool.lichess_analyze_game(game_id="abcd1234", pgn=PGN, color="white", depth=14)
    )

    assert calls == [("white", "fast"), ("black", "fast")]
    assert result["mode"] == "fast"
    assert result["dual_cache"]["files"] == [
        "abcd1234_white_d14n150000.json",
        "abcd1234_black_d14n150000.json",
    ]


def test_analyze_game_mode_is_overridable(monkeypatch):
    calls = []

    def fake_analyze(pgn, player_color="white", depth=0, game_id=None, **kwargs):
        calls.append(kwargs.get("mode"))
        summary = GameSummary(
            id="abcd1234",
            platform="lichess",
            opening="",
            opening_eco="",
            color=player_color,
            result="1-0",
        )
        return GameAnalysis(game=summary)

    monkeypatch.setattr(analyze_game_tool, "analyze_pgn", fake_analyze)
    asyncio.run(
        analyze_game_tool.lichess_analyze_game(
            game_id="abcd1234", pgn=PGN, color="black", depth=14, mode="deep"
        )
    )
    assert calls == ["deep", "deep"]
