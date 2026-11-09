"""MCP tool output_format integration (no engine, no network)."""

import asyncio

from lichess_analyzer_mcp.models.game import GameAnalysis, GameSummary, MoveAnalysis
from lichess_analyzer_mcp.tools import coaching_single_game as cs


def _analysis() -> GameAnalysis:
    game = GameSummary(
        id="testgame",
        platform="lichess",
        opening="Test Opening",
        opening_eco="C20",
        color="white",
        result="1-0",
        time_control="300+0",
        date="2026.11.09",
    )
    quiet = MoveAnalysis(
        ply=1,
        move_uci="e2e4",
        move_san="e4",
        eval_before=20,
        eval_after=20,
        win_prob_before=0.5,
        win_prob_after=0.5,
        centipawn_loss=0.0,
        classification="good",
        best_move_uci="e2e4",
        best_move_san="e4",
        is_tactical_motif=False,
        motif_type=None,
        phase="opening",
        fen="rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1",
    )
    bad = MoveAnalysis(
        ply=3,
        move_uci="d1h5",
        move_san="Qh5",
        eval_before=30,
        eval_after=-90,
        win_prob_before=0.55,
        win_prob_after=0.3,
        centipawn_loss=120.0,
        classification="inaccuracy",
        best_move_uci="g1f3",
        best_move_san="Nf3",
        is_tactical_motif=True,
        motif_type="check",
        phase="opening",
        fen="rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
        engine_lines=[{"rank": 1, "san": "Nf3", "eval_cp": 30, "pv": ["Nf3", "Nc6", "Bb5"]}],
        played_rank=4,
    )
    analysis = GameAnalysis(game=game, moves=[quiet, bad], total_acpl=40.0, accuracy=90.0)
    analysis.phase_stats = analysis._compute_phase_stats()
    return analysis


def _install(monkeypatch):
    analysis = _analysis()
    data = {
        "analysis": analysis.to_dict(),
        "analysis_obj": analysis,
        "color": "white",
        "timings": {"io_s": 0.0},
    }
    monkeypatch.setattr(cs, "collect_single_game", lambda *a, **k: data)
    monkeypatch.setattr(cs, "detect_single_game", lambda obj: [])


def test_default_is_full_v11(monkeypatch):
    _install(monkeypatch)
    result = asyncio.run(
        cs.lichess_coaching_single_game("testgame", color="white", depth=14, use_llm=False)
    )
    assert result["schema_version"] == "1.1"
    assert result["game_id"] == "testgame"
    assert result["report_meta"]["truncated"] is False


def test_compact_output_is_schema_20(monkeypatch):
    _install(monkeypatch)
    result = asyncio.run(
        cs.lichess_coaching_single_game(
            "testgame", color="white", depth=14, output_format="compact", use_llm=False
        )
    )
    assert result["v"] == "2.0"
    assert result["game"]["id"] == "testgame"
    assert result["flags"][0]["ply"] == 3
    assert result["flags"][0]["rank"] == 4
    assert result["summary"]["phases"]["opening"] == [60.0, 1]


def test_both_returns_full_and_compact(monkeypatch):
    _install(monkeypatch)
    result = asyncio.run(
        cs.lichess_coaching_single_game(
            "testgame", color="white", depth=14, output_format="both", use_llm=False
        )
    )
    assert set(result) == {"full", "compact"}
    assert result["full"]["schema_version"] == "1.1"
    assert result["compact"]["v"] == "2.0"


def test_use_llm_false_does_not_call_providers(monkeypatch):
    _install(monkeypatch)

    def boom(*args, **kwargs):
        raise AssertionError("LLM cascade must not be called")

    monkeypatch.setattr(cs, "safe_llm_call", boom)
    result = asyncio.run(
        cs.lichess_coaching_single_game("testgame", color="white", depth=14, use_llm=False)
    )
    assert result["llm"]["reason"] == "llm_disabled"
    assert result["report_meta"]["source"] == "deterministic"
