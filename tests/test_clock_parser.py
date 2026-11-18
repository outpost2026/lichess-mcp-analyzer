"""D23/T-16: PGN %clk parsing and honest time-trouble reporting."""

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


def test_deterministic_report_shows_clock_marker():
    prompt = """K DISPOZICI:
- Časová data (PGN %clk): clock_data_unavailable
- Blundry (s detaily): - ply 9 e5 (loss 120cp, impact=equal_to_losing)
- Fázový breakdown: middlegame ACPL 44.0
"""
    content, _ = generate_ide_report(prompt)
    assert "clock_data_unavailable" in content
