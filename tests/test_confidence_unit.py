"""D26/D27: `confidence` has exactly one unit per artifact.

The unit is a contract, not a style choice - an LLM that reads `0.8` as
`0.8 %` produces a wrong coaching narrative. Pinned here:

| Artifact                          | Unit  | Owner                                   |
|-----------------------------------|-------|-----------------------------------------|
| detailed 1.2 `confidence`         | 0-1   | `pattern_detector.scan_single_game`     |
| compact 2.3 `conf`                | 0-1   | `schemas/single_game_v2_compact_2.3.json` |
| cross-game `confidence`           | 0-100 | `schemas.py`, `coaching_base`           |
| report text                       | %     | `report_persister._build_md`            |
| KB slim `confidence`              | 0-1   | `report_persister._kb_pattern_slim`     |

`strength` stays 0-1 everywhere: it is an ordinal event strength, never a
probability. `schemas/single_game_v1.2.json` pins `patterns.items.confidence`
to `minimum: 0, maximum: 1`; a 0-100 value in detailed single-game output is a
schema violation, not a feature ([2.5] got this wrong, D26 corrects it).
"""

from lichess_analyzer_mcp.models.game import GameAnalysis, GameSummary, MoveAnalysis
from lichess_analyzer_mcp.services.pattern_detector import scan_single_game
from lichess_analyzer_mcp.services.report_persister import (
    _build_md,
    _kb_pattern_slim,
)

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


def test_scan_single_game_publishes_confidence_on_a_0_1_scale():
    """Schema 1.2 pins 0-1; `confidence` is the same number as `strength`."""
    for pattern in _matched_patterns():
        assert 0 <= pattern["strength"] <= 1
        assert 0 <= pattern["confidence"] <= 1
        assert pattern["confidence"] == pattern["strength"]


def test_detailed_confidence_never_uses_the_percentage_scale():
    """Guards the 100x regression in both directions."""
    for pattern in _matched_patterns():
        assert pattern["confidence"] <= 1
        if pattern["strength"] > 0:
            assert pattern["confidence"] != round(pattern["strength"] * 100, 0)


def test_report_prints_single_game_confidence_as_percent():
    """`single_game` confidence is 0-1 but the report cell is a percentage."""
    patterns = _matched_patterns()
    text = _build_md("single_game", "confidence1", {"patterns": patterns})
    assert "Confidence" in text
    for pattern in patterns:
        expected = f"{pattern['confidence'] * 100:g}%"
        assert expected in text


def test_report_prints_cross_game_confidence_unchanged():
    """Cross-game kinds already publish 0-100; the report must not multiply."""
    patterns = [
        {
            "pattern_id": "B",
            "pattern_name": "Automatic grab",
            "confidence": 60.0,
            "frequency": 2,
            "severity": "high",
        }
    ]
    text = _build_md("cross_game", "tester", {"patterns": patterns})
    assert "60%" in text
    assert "6000%" not in text


def test_kb_slim_keeps_single_game_confidence_at_0_1():
    source = {p["pattern_id"]: p for p in _matched_patterns()}
    slim = _kb_pattern_slim(_matched_patterns(), fraction=True)
    for entry in slim:
        assert 0 <= entry["confidence"] <= 1
        assert entry["confidence"] == round(source[entry["pattern_id"]]["confidence"], 2)


def test_kb_slim_converts_cross_game_confidence_to_0_1():
    slim = _kb_pattern_slim(
        [{"pattern_id": "B", "pattern_name": "Automatic grab", "confidence": 60.0}],
        fraction=False,
    )
    assert slim[0]["confidence"] == 0.6
