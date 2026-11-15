"""N-02 / D18: `confidence` has exactly one unit per artifact.

The unit is a contract, not a style choice - an LLM that reads `0.8` as
`0.8 %` produces a wrong coaching narrative. Pinned here:

| Artifact                  | Unit  | Owner                          |
|---------------------------|-------|--------------------------------|
| detailed 1.2 `confidence` | 0-100 | `pattern_detector.scan_single_game`, `schemas.py` |
| report text `{conf}%`     | 0-100 | `report_persister`             |
| KB slim `confidence`      | 0-1   | `report_persister._kb_pattern_slim` |
| compact 2.1 `conf`        | 0-1   | frozen schema `single_game_v2_compact.json` |

`strength` stays 0-1 everywhere: it is an ordinal event strength, never a
probability.
"""

from lichess_analyzer_mcp.models.game import GameAnalysis, GameSummary, MoveAnalysis
from lichess_analyzer_mcp.services.pattern_detector import scan_single_game
from lichess_analyzer_mcp.services.report_persister import _kb_pattern_slim

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def _move(ply: int, san: str, cp_loss: float, **kwargs) -> MoveAnalysis:
    return MoveAnalysis(
        ply=ply,
        move_uci="e2e4",
        move_san=san,
        eval_before=kwargs.get("eval_before", 0.0),
        eval_after=kwargs.get("eval_before", 0.0) - cp_loss,
        win_prob_before=0.5,
        win_prob_after=0.4,
        centipawn_loss=cp_loss,
        classification=kwargs.get("classification", "blunder"),
        best_move_uci="",
        best_move_san=kwargs.get("best", "Qf4+"),
        is_tactical_motif=kwargs.get("tactical", False),
        motif_type=kwargs.get("motif"),
        phase="middlegame",
        fen=START_FEN,
        was_in_check=kwargs.get("in_check", False),
        gives_check=kwargs.get("gives_check", False),
        engine_lines=[],
        played_rank=kwargs.get("rank", 4),
    )


def _analysis(moves: list[MoveAnalysis]) -> GameAnalysis:
    return GameAnalysis(
        game=GameSummary(
            id="confidence1",
            platform="lichess",
            opening="Test",
            opening_eco="C00",
            color="white",
            result="1-0",
        ),
        moves=moves,
    )


def _matched_patterns() -> list[dict]:
    """A capture (B) and a tactical motif (T) always match a pattern."""
    analysis = _analysis(
        [
            _move(25, "Qxa3", 500.0),
            _move(26, "h6", 0.0, classification="good", rank=1),
            _move(27, "g3", 300.0, tactical=True, motif="fork"),
        ]
    )
    patterns, _ = scan_single_game(analysis)
    assert patterns, "fixture must produce at least one pattern"
    return patterns


def test_scan_single_game_publishes_confidence_on_a_0_100_scale():
    for pattern in _matched_patterns():
        assert 0 <= pattern["strength"] <= 1
        assert 0 <= pattern["confidence"] <= 100
        # The alias is the same number, only in the published unit.
        assert pattern["confidence"] == round(pattern["strength"] * 100, 0)


def test_confidence_is_never_the_strength_value_itself():
    """Guards the 100x regression: 0.8 must never be published as `0.8`."""
    for pattern in _matched_patterns():
        if pattern["strength"] > 0:
            assert pattern["confidence"] > 1


def test_kb_slim_converts_back_to_0_1():
    slim = _kb_pattern_slim(_matched_patterns())
    for entry in slim:
        assert 0 <= entry["confidence"] <= 1
    source = {p["pattern_id"]: p for p in _matched_patterns()}
    for entry in slim:
        expected = round(source[entry["pattern_id"]]["confidence"] / 100, 2)
        assert entry["confidence"] == expected


def test_report_line_prints_percent_not_a_fraction():
    """`{confidence}%` must read `85.0%`, never `0.85%`."""
    from lichess_analyzer_mcp.services.report_persister import _build_md

    patterns = _matched_patterns()
    text = _build_md("single_game", "confidence1", {"patterns": patterns})
    assert "Confidence" in text
    for pattern in patterns:
        expected = f"{pattern['confidence']}%"
        assert expected in text
