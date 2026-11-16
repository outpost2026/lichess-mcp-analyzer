"""P-03 (external code review): a tool's documented range is its real clamp.

The docstrings used to say `5-50` while every tool clamped to `5..999`.
A range in an MCP tool signature is an API contract; it must be derivable
from the validation code, not from an older design document.
"""

import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..", "src", "lichess_analyzer_mcp", "tools")

CLAMPED_TOOLS = (
    "coaching_cross_game.py",
    "coaching_opening_report.py",
    "coaching_training_plan.py",
    "diagnose_player.py",
    "fetch_games.py",
    "match_patterns.py",
)
# `persist_report` forwards `max_games` to the coaching tools; it clamps nowhere.
FORWARDING_TOOLS = ("persist_report.py",)


def _text(name: str) -> str:
    with open(os.path.join(ROOT, name), encoding="utf-8") as handle:
        return handle.read()


def _doc_range(name: str) -> tuple[str, str]:
    match = re.search(r"max_games:[^\n]*?\((\d+)-(\d+)", _text(name))
    assert match is not None, f"{name}: no documented max_games range"
    return match.groups()


def test_max_games_doc_matches_clamp_in_every_tool():
    for name in CLAMPED_TOOLS:
        text = _text(name)
        clamp = re.search(r"max_games\s*=\s*max\((\d+),\s*min\((\d+),\s*max_games\)\)", text)
        assert clamp is not None, f"{name}: no max_games clamp"
        assert _doc_range(name) == clamp.groups(), (
            f"{name}: docstring {_doc_range(name)} != clamp {clamp.groups()}"
        )


def test_forwarding_tool_documents_the_same_range():
    assert _doc_range("persist_report.py") == ("5", "999")
