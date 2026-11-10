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


PROMPT_WITH_CLEAN_PHASE = """K DISPOZICI:
- Výsledek: 1-0, barva: white, zahájení: Sicilian Defense
- Celková ACPL: 239.4
- Počet chyb: 1 blunderů, 7 chyb, 9 nepřesností
- Blundry (s detaily): - ply 75 Re8+ (blunder, cp_loss=9473, endgame)
- Fázový breakdown: endgame: ACPL 438.7, 10 chyb; middlegame: ACPL 68.5, 7 chyb | čisté fáze: opening
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


def test_weakest_phase_excludes_clean_phases():
    """FIX-021: a 0.0-ACPL / 0-flag phase is clean, never weakest."""
    content, _ = generate_deterministic_report(PROMPT_WITH_CLEAN_PHASE)
    weakest = next(ln for ln in content.splitlines() if ln.startswith("- Fázově nejslabší:"))
    assert "endgame" in weakest
    assert "opening" not in weakest
    assert "- Čisté fáze: opening" in content


def test_weakest_phase_sorted_by_acpl():
    from lichess_analyzer_mcp.tools.coaching_single_game import _phase_breakdown

    stats = {
        "endgame": {"acpl": 438.7, "flagged": 10},
        "middlegame": {"acpl": 68.5, "flagged": 7},
        "opening": {"acpl": 17.4, "flagged": 0},
    }
    text = _phase_breakdown(stats)
    assert text.index("endgame") < text.index("middlegame") < text.index("opening")
    assert "čisté fáze" not in text  # opening has ACPL 17.4, so it is not clean


def test_all_clean_phases_say_no_weak_phase():
    from lichess_analyzer_mcp.tools.coaching_single_game import _phase_breakdown

    stats = {
        "opening": {"acpl": 0.0, "flagged": 0},
        "middlegame": {"acpl": 0.0, "flagged": 0},
        "endgame": {"acpl": None, "flagged": 0},
    }
    text = _phase_breakdown(stats)
    assert text.startswith("žádná slabá fáze")
    assert "čisté fáze: opening, middlegame, endgame" in text
    content, _ = generate_deterministic_report(
        PROMPT_WITH_CLEAN_PHASE.replace(
            "endgame: ACPL 438.7, 10 chyb; middlegame: ACPL 68.5, 7 chyb | čisté fáze: opening",
            "žádná slabá fáze | čisté fáze: opening, middlegame, endgame",
        )
    )
    assert "Fázově nejslabší" not in content
    assert "Žádná slabá fáze" in content


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
    assert "Qf5+" in line


def test_report_never_truncated_mid_structure():
    """FIX-011: raw JSON in the prompt must never be sliced mid-array."""
    raw_bfs = (
        "- Blundry (s detaily): - ply 41 Qf5+ (loss 308cp) "
        '{"fen":"r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/2N2N2/PPPP1PPP/R1BQK2R w KQkq - 6 5",'
        '"engine_lines":[{"rank":1,"san":"Qd6","eval_cp":208,"pv":["Qd6","Rf3","Bxc3"],'
        '"pattern_matches":[]}],"context_window":{"moves_before":[{"ply":40}]}},'
        '"moves_after":['
    )
    prompt = f"""K DISPOZICI:
- Počet chyb: 1 blunderů, 0 chyb, 0 nepřesností
{raw_bfs}
- Fázový breakdown: middlegame ACPL 56.3
"""
    content, _ = generate_deterministic_report(prompt)
    assert content.count("[") == content.count("]")
    assert content.count("{") == content.count("}")
    assert "moves_after" not in content
    line = next(ln for ln in content.splitlines() if ln.startswith("- Kritický moment:"))
    assert "ply 41" in line and "308cp" in line
