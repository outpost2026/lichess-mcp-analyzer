"""Deterministic report must never contradict the data it is built from.

Regression: the template label is "Blundry (s detaily):", but the parser
looked for the literal "Blundry:" — the value was always empty and every
report claimed "Žádný blunder" even when blunders existed
(DATA-FABRICATION-001).
"""

from lichess_analyzer_mcp.services.ide_fallback import generate_deterministic_report

PROMPT_WITH_BLUNDER = """Vytvoř coaching report pro hru NxKgE4l8.

K DISPOZICI:
- Výsledek: 1-0, barva: white, zahájení: Vienna Game
- Celková ACPL: 43.3
- Počet chyb: 1 blunderů, 2 chyb, 3 nepřesností
- Blundry (s detaily): - ply 41 Qf5+ (blunder, cp_loss=308, middlegame)
- Chyby (s detaily): - ply 23 a4 (mistake, cp_loss=218)
- Nepřesnosti: 3
- Fázový breakdown: middlegame ACPL 56.3

PRAVIDLA:
1. NEVYMÝŠLEJ.
"""

PROMPT_NO_BLUNDER = """Vytvoř coaching report pro hru abcd1234.

K DISPOZICI:
- Výsledek: 1/2-1/2, barva: black, zahájení: London System
- Celková ACPL: 18.0
- Počet chyb: 0 blunderů, 1 chyb, 2 nepřesností
- Blundry (s detaily): (žádné)
- Fázový breakdown: opening ACPL 12.0
"""

PROMPT_COUNT_ONLY = """K DISPOZICI:
- Počet chyb: 2 blunderů, 0 chyb, 0 nepřesností
- Blundry (s detaily):
- Fázový breakdown: endgame ACPL 90.0
"""


def test_blunder_detail_is_reported():
    content, log = generate_deterministic_report(PROMPT_WITH_BLUNDER)
    assert "Žádný blunder" not in content
    assert "Qf5+" in content
    assert "ply 41" in content
    assert log["source"] == "deterministic"
    assert log["degraded"] is True


def test_no_blunder_claim_only_when_count_is_zero():
    content, _ = generate_deterministic_report(PROMPT_NO_BLUNDER)
    assert "Žádný blunder" in content


def test_count_without_details_does_not_claim_no_blunder():
    content, _ = generate_deterministic_report(PROMPT_COUNT_ONLY)
    assert "Žádný blunder" not in content
    assert "Blunderů: 2" in content


def test_instruction_markers_do_not_leak():
    content, _ = generate_deterministic_report(PROMPT_WITH_BLUNDER)
    assert "NEVYMÝŠLEJ" not in content
    assert "PRAVIDLA:" not in content


def test_long_blunder_detail_is_clipped_at_field_boundary():
    detail = "; ".join(f"field{i}=value{i}" for i in range(20))
    prompt = f"""K DISPOZICI:
- Počet chyb: 1 blunderů, 0 chyb, 0 nepřesností
- Blundry (s detaily): - ply 41 Qf5+ {detail}
- Fázový breakdown: middlegame ACPL 56.3
"""
    content, _ = generate_deterministic_report(prompt)
    line = next(ln for ln in content.splitlines() if ln.startswith("- Kritický moment:"))
    assert len(line) <= 220
    assert "ply 41" in line
    assert line.endswith(tuple("0123456789"))
