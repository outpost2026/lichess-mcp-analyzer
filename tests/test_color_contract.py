"""D6/D6a: one colour contract across MCP, analysis and compact metadata."""

import asyncio
import sys, os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lichess_analyzer_mcp.services.color_contract import (
    ColorUndetectedError,
    InvalidColorError,
    normalize_color,
)
from lichess_analyzer_mcp.services import coaching_base
from lichess_analyzer_mcp.services import compact_serializer
from lichess_analyzer_mcp.services import game_analyzer
from lichess_analyzer_mcp.services import lichess_client
from lichess_analyzer_mcp.tools import coaching_single_game as cs


class _AnalysisStub:
    def to_dict(self):
        return {"game": {}, "moves": []}


def test_normalize_accepts_contract_colours():
    assert normalize_color("white") == "white"
    assert normalize_color(" Black ") == "black"


@pytest.mark.parametrize("value", ["both", "WHITE/BLACK", "w", 0])
def test_normalize_rejects_unknown(value):
    with pytest.raises(InvalidColorError):
        normalize_color(value)


def test_normalize_allows_empty_only_on_request():
    assert normalize_color("", allow_empty=True) == ""
    with pytest.raises(InvalidColorError):
        normalize_color("")


def test_analyze_pgn_rejects_both_before_any_engine_work():
    with pytest.raises(InvalidColorError):
        game_analyzer.analyze_pgn("", player_color="both")


def test_compact_serializer_does_not_rewrite_unknown_colour():
    with pytest.raises(InvalidColorError):
        compact_serializer.to_compact_v2(
            {"game_id": "g", "color": "both", "depth": 14},
            game_meta={},
        )


def test_detect_player_color_returns_none_instead_of_white(monkeypatch):
    monkeypatch.setattr(lichess_client, "fetch_game_by_id", lambda gid: {})
    monkeypatch.setattr(lichess_client, "fetch_game_pgn", lambda gid: "")
    assert coaching_base.detect_player_color("gid", "nobody") is None


def test_collect_raises_when_username_cannot_be_detected(monkeypatch):
    monkeypatch.setattr(coaching_base, "detect_player_color", lambda gid, user: None)
    with pytest.raises(ColorUndetectedError) as exc:
        coaching_base.collect_single_game("gid", color="", username="nobody")
    assert exc.value.code == "COLOR_UNDETECTED"


def test_collect_keeps_explicit_colour_when_detection_fails(monkeypatch):
    monkeypatch.setattr(coaching_base, "detect_player_color", lambda gid, user: None)
    monkeypatch.setattr(coaching_base, "fetch_game_pgn", lambda gid: "pgn")
    monkeypatch.setattr(coaching_base, "analyze_pgn", lambda *a, **k: _AnalysisStub())
    data = coaching_base.collect_single_game("gid", color="black", username="nobody")
    assert data["color"] == "black"


def test_mcp_tool_rejects_both_with_invalid_color():
    result = asyncio.run(
        cs.lichess_coaching_single_game("gid", color="both", depth=14, use_llm=False)
    )
    assert result["status"] == "error"
    assert result["errors"][0]["code"] == "INVALID_COLOR"
    assert result["color"] == ""


def test_mcp_tool_reports_color_undetected(monkeypatch):
    monkeypatch.setattr(coaching_base, "detect_player_color", lambda gid, user: None)
    result = asyncio.run(
        cs.lichess_coaching_single_game("gid", username="nobody", depth=14, use_llm=False)
    )
    assert result["status"] == "error"
    assert result["errors"][0]["code"] == "COLOR_UNDETECTED"


# ── T2.5: anonymous session must not invent a colour for a draw ──────────────

_PGN_WIN = '[Result "1-0"]\n\n1. e4 e5 *'
_PGN_LOSS = '[Result "0-1"]\n\n1. e4 e5 *'
_PGN_DRAW = '[Result "1/2-1/2"]\n\n1. e4 e5 *'


def test_anonymous_resolve_color_explicit_wins():
    from lichess_analyzer_mcp.tools.anonymous_session import _resolve_color

    assert _resolve_color(_PGN_DRAW, "white") == "white"
    assert _resolve_color(_PGN_DRAW, "black") == "black"


def test_anonymous_resolve_color_win_loss_decisive():
    from lichess_analyzer_mcp.tools.anonymous_session import _resolve_color

    assert _resolve_color(_PGN_WIN, "win") == "white"
    assert _resolve_color(_PGN_WIN, "loss") == "black"
    assert _resolve_color(_PGN_LOSS, "win") == "black"
    assert _resolve_color(_PGN_LOSS, "loss") == "white"


def test_anonymous_resolve_color_draw_is_an_error_not_white():
    from lichess_analyzer_mcp.tools.anonymous_session import _resolve_color

    with pytest.raises(ColorUndetectedError) as exc:
        _resolve_color(_PGN_DRAW, "win")
    assert exc.value.code == "COLOR_UNDETECTED"
    with pytest.raises(ColorUndetectedError):
        _resolve_color(_PGN_DRAW, None)


def test_anonymous_resolve_color_rejects_unknown_label():
    from lichess_analyzer_mcp.tools.anonymous_session import _resolve_color

    with pytest.raises(ColorUndetectedError):
        _resolve_color(_PGN_WIN, "draw")
