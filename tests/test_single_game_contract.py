"""Contract v1.1 invariants for the single-game path (no engine, no network).

Covers the defects the calibration plan targets:
- an unmeasured move must never look like a perfect move (P0.2),
- a single game gets its own pattern surface (P0.4),
- the deterministic fallback is not advertised as an LLM provider (P0.3).
"""

import time

from lichess_analyzer_mcp.models.game import GameAnalysis, GameSummary, MoveAnalysis
from lichess_analyzer_mcp.services import engine_client, game_analyzer
from lichess_analyzer_mcp.services.llm_client import get_llm_status
from lichess_analyzer_mcp.services.pattern_detector import detect_single_game


def _move(ply: int, san: str, cp_loss: float, **kwargs) -> MoveAnalysis:
    return MoveAnalysis(
        ply=ply,
        move_uci=kwargs.pop("uci", "e2e4"),
        move_san=san,
        eval_before=kwargs.pop("eval_before", 0.0),
        eval_after=kwargs.pop("eval_after", -cp_loss),
        win_prob_before=0.5,
        win_prob_after=0.4,
        centipawn_loss=cp_loss,
        classification=kwargs.pop("classification", "best"),
        best_move_uci="",
        best_move_san="",
        is_tactical_motif=kwargs.pop("is_tactical_motif", False),
        motif_type=kwargs.pop("motif_type", None),
        phase=kwargs.pop("phase", "middlegame"),
        analyzed=kwargs.pop("analyzed", True),
    )


def test_unanalyzed_move_serializes_null_cp_loss():
    move = _move(10, "Qh4", 0.0, analyzed=False)
    data = move.to_dict()
    assert data["centipawn_loss"] is None
    assert data["analyzed"] is False


def test_aggregates_ignore_unanalyzed_moves():
    game = GameAnalysis(
        game=GameSummary(
            id="testgame",
            platform="lichess",
            opening="Test",
            opening_eco="C00",
            color="white",
            result="1-0",
        )
    )
    game.moves = [
        _move(1, "e4", 10.0),
        _move(2, "Qh4", 0.0, analyzed=False),
    ]
    game.auto_annotate()
    # 10 cp only from the measured move, not (10 + 0) / 2
    assert game.accuracy == round(100 - 10.0 * 0.15, 1)


def test_detect_single_game_reports_capture_blunder():
    game = GameAnalysis(
        game=GameSummary(
            id="testgame",
            platform="lichess",
            opening="Test",
            opening_eco="C00",
            color="white",
            result="1-0",
        )
    )
    game.moves = [
        _move(1, "e4", 5.0),
        _move(
            2,
            "Bxh7+",
            320.0,
            classification="blunder",
            uci="c1h7",
        ),
    ]
    patterns = detect_single_game(game)
    ids = {p["pattern_id"] for p in patterns}
    assert "B" in ids
    for pattern in patterns:
        assert pattern["scope"] == "single_game"
        assert pattern["affected_games"] == ["testgame"]
        assert pattern["evidence"]


def test_llm_status_never_lists_deterministic_fallback_as_provider():
    status = get_llm_status()
    names = {p["provider"] for p in status["available"]}
    assert "IDE (Muse Spark)" not in names
    assert "Deterministic report" not in names
    assert status["deterministic_fallback"] is True


def test_deadline_marks_moves_unanalyzed_instead_of_zero(monkeypatch):
    pgn = """[Site "https://lichess.org/aaaaaaaa"]
[White "systeq"]
[Black "opponent"]
[Result "*"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O 9. h3 Nb8 10. d4 Nbd7 *
"""

    calls = {"n": 0}

    def slow_evaluate(fen, move_uci, depth=0, timeout_s=None, **kwargs):
        calls["n"] += 1
        time.sleep(0.15)
        return {
            "eval_before": 20,
            "eval_after": 10,
            "centipawn_loss": 10.0,
            "best_move_uci": "e2e4",
        }

    monkeypatch.setattr(engine_client, "evaluate_move", slow_evaluate)
    monkeypatch.setattr(engine_client, "get_engine", lambda hash_mb=None, **kwargs: None)
    monkeypatch.setattr(engine_client, "clear_hash", lambda: None)

    analysis = game_analyzer._run_analyze_pgn(pgn, "white", depth=14, deadline_s=0.5, mode="fast")

    assert analysis.unanalyzed_plies
    assert analysis.deadline_hit is True
    assert analysis.timings.get("engine_s", 0.0) >= 0.0
    assert calls["n"] < 10
    for move in analysis.moves:
        if not move.analyzed:
            assert move.to_dict()["centipawn_loss"] is None
        else:
            assert move.to_dict()["centipawn_loss"] is not None
    # ACPL must not be diluted by unanalyzed moves presented as 0.
    measured = [m for m in analysis.moves if m.analyzed]
    assert analysis.total_acpl == 10.0
    assert len(measured) >= 1


# ── Regression: one engine timeout must not cost the rest of the game ────────

PGN_10_MOVES = """[Site "https://lichess.org/bbbbbbbb"]
[White "systeq"]
[Black "opponent"]
[Result "*"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O 9. h3 Nb8 10. d4 Nbd7 *
"""


def test_timeout_clears_shared_engine_even_when_caller_passed_reference(monkeypatch):
    """A timeout on an explicitly passed engine must also clear `_engine`.

    Before the fix, `evaluate_move()` passed its own reference, so the dead
    engine stayed in `_engine` and every later call failed with
    "engine event loop dead" (observed: 13 lost moves after one timeout).
    """

    class FakeEngine:
        def quit(self):
            raise RuntimeError("engine already gone")

    fake = FakeEngine()
    monkeypatch.setattr(engine_client, "_engine", fake)

    result = engine_client._run_engine_call(lambda: time.sleep(0.5), timeout_s=0.1, engine=fake)

    assert "error" in result
    assert engine_client._engine is None


def test_dead_engine_costs_one_retry_not_the_whole_game(monkeypatch):
    """After an engine death the loop restarts it and finishes the game."""

    state = {"dead": True, "resets": 0}

    def flaky_evaluate(fen, move_uci, depth=0, timeout_s=None, **kwargs):
        if state["dead"]:
            state["dead"] = False
            return {
                "eval_before": None,
                "eval_after": None,
                "centipawn_loss": None,
                "best_move_uci": None,
                "error": "engine event loop dead",
            }
        return {
            "eval_before": 20,
            "eval_after": 10,
            "centipawn_loss": 10.0,
            "best_move_uci": "e2e4",
        }

    def fake_reset():
        state["resets"] += 1

    monkeypatch.setattr(engine_client, "evaluate_move", flaky_evaluate)
    monkeypatch.setattr(engine_client, "reset_engine", fake_reset)
    monkeypatch.setattr(engine_client, "get_engine", lambda hash_mb=None, **kwargs: None)
    monkeypatch.setattr(engine_client, "clear_hash", lambda: None)

    analysis = game_analyzer._run_analyze_pgn(
        PGN_10_MOVES, "white", depth=14, deadline_s=60.0, mode="fast"
    )

    assert state["resets"] == 1
    assert analysis.engine_retries == 1
    assert analysis.unanalyzed_plies == []
    assert len(analysis.moves) == 10
    assert all(m.analyzed for m in analysis.moves)


def test_partial_analysis_is_not_cached(monkeypatch):
    """A gap must not be persisted as the authoritative result."""

    saved = {"n": 0}

    def slow_evaluate(fen, move_uci, depth=0, timeout_s=None, **kwargs):
        time.sleep(0.15)
        return {
            "eval_before": 20,
            "eval_after": 10,
            "centipawn_loss": 10.0,
            "best_move_uci": "e2e4",
        }

    monkeypatch.setattr(engine_client, "evaluate_move", slow_evaluate)
    monkeypatch.setattr(engine_client, "get_engine", lambda hash_mb=None, **kwargs: None)
    monkeypatch.setattr(engine_client, "clear_hash", lambda: None)
    monkeypatch.setattr(
        game_analyzer,
        "_save_cached_analysis",
        lambda *a, **k: saved.__setitem__("n", saved["n"] + 1),
    )

    analysis = game_analyzer.analyze_pgn(
        PGN_10_MOVES,
        "white",
        depth=14,
        game_id="testcache0",
        deadline_s=0.4,
        mode="fast",
    )

    assert analysis.unanalyzed_plies
    assert saved["n"] == 0


def test_explanation_does_not_invent_rank_beyond_measured_candidates():
    """Played move outside the top-3 must not be labelled "4th"."""
    move = _move(11, "Bg5", 95.0, classification="inaccuracy")
    move.best_move_san = "Ne2"
    move.played_rank = 4
    move.engine_lines = [
        {"rank": 1, "san": "Ne2", "eval_cp": 260, "pv": ["Ne2"]},
        {"rank": 2, "san": "a3", "eval_cp": 250, "pv": ["a3"]},
        {"rank": 3, "san": "h4", "eval_cp": 240, "pv": ["h4"]},
    ]
    text = game_analyzer._build_explanation(move, move.engine_lines)
    assert "nebyl v top 3" in text
    assert "4. v pořadí" not in text


def test_explanation_keeps_measured_rank():
    move = _move(39, "O-O", 75.0, classification="inaccuracy")
    move.best_move_san = "Qf5+"
    move.played_rank = 2
    move.engine_lines = [
        {"rank": 1, "san": "Qf5+", "eval_cp": 719, "pv": ["Qf5+"]},
        {"rank": 2, "san": "O-O", "eval_cp": 644, "pv": ["O-O"]},
        {"rank": 3, "san": "Kh1", "eval_cp": 600, "pv": ["Kh1"]},
    ]
    text = game_analyzer._build_explanation(move, move.engine_lines)
    assert "2. v pořadí" in text
