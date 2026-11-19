"""D23/T-16: PGN %clk parsing and honest time-trouble reporting."""

import lichess_analyzer_mcp.services.lichess_client as lc
from lichess_analyzer_mcp.services.game_analyzer import parse_clock_data
from lichess_analyzer_mcp.services.ide_fallback import generate_ide_report

PGN_WITH_CLOCK = """[Event "test"]

1. e4 e5 {[%clk 0:09:55]} 2. Nf3 {[%clk 0:09:50]} Nc6 {[%clk 0:09:45]} *"""

PGN_WITHOUT_CLOCK = """[Event "test"]

1. e4 e5 2. Nf3 Nc6 *"""


def test_parse_clock_data_with_pgn_comments():
    got = parse_clock_data(PGN_WITH_CLOCK)
    assert got["status"] == "ok"
    assert got["plies"] == {2: "0:09:55", 3: "0:09:50", 4: "0:09:45"}


def test_parse_clock_data_without_comments_is_honest():
    got = parse_clock_data(PGN_WITHOUT_CLOCK)
    assert got == {"status": "clock_data_unavailable"}


def test_parse_clock_data_handles_empty_pgn():
    assert parse_clock_data("") == {"status": "clock_data_unavailable"}


def test_pgn_export_requests_clocks_and_uses_separate_cache(monkeypatch, tmp_path):
    """Lichess API needs clocks=true; legacy .pgn must not serve as clock data."""
    calls = []

    class FakeGames:
        def export(self, game_id, **kwargs):
            calls.append(kwargs)
            return PGN_WITH_CLOCK

    class FakeClient:
        games = FakeGames()

    monkeypatch.setattr(lc, "PGN_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(lc, "get_client", lambda: FakeClient())

    pgn = lc.fetch_game_pgn("clockgame")
    assert calls and calls[0]["as_pgn"] is True and calls[0]["clocks"] is True
    assert "[%clk" in pgn
    assert (tmp_path / "clockgame.clocks.pgn").is_file()
    assert not (tmp_path / "clockgame.pgn").exists()
    assert parse_clock_data(pgn)["status"] == "ok"


def test_deterministic_report_shows_clock_marker():
    prompt = """K DISPOZICI:
- Časová data (PGN %clk): clock_data_unavailable
- Blundry (s detaily): - ply 9 e5 (loss 120cp, impact=equal_to_losing)
- Fázový breakdown: middlegame ACPL 44.0
"""
    content, _ = generate_ide_report(prompt)
    assert "clock_data_unavailable" in content
