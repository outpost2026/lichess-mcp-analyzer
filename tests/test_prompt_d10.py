"""D10/T2.3: the coaching prompt must allow 'insufficient_evidence'."""

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lichess_analyzer_mcp.services.prompt_builder import PROMPT_TEMPLATES


def test_template_1_allows_insufficient_evidence():
    prompt = PROMPT_TEMPLATES[1]
    assert "insufficient_evidence" in prompt
    assert "taktický, poziční, nebo `insufficient_evidence`" in prompt


def test_template_1_clock_contract():
    prompt = PROMPT_TEMPLATES[1]
    assert "clock_data_unavailable" in prompt
    assert "%clk" in prompt
    assert "odhadni z time control" not in prompt
