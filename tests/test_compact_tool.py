"""MCP tool output_format integration (no engine, no network)."""

import asyncio
import json
import os

import pytest

from lichess_analyzer_mcp.models.game import GameAnalysis, GameSummary, MoveAnalysis
from lichess_analyzer_mcp.tools import coaching_single_game as cs

ROOT = os.path.join(os.path.dirname(__file__), "..")


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
    monkeypatch.setattr(cs, "scan_single_game", lambda obj: ([], {}))


def test_default_is_compact_v2(monkeypatch):
    _install(monkeypatch)
    result = asyncio.run(
        cs.lichess_coaching_single_game("testgame", color="white", depth=14, use_llm=False)
    )
    assert result["v"] == "2.1"
    assert result["game"]["id"] == "testgame"
    assert result["flags"][0]["ply"] == 3


def test_detailed_returns_schema_12(monkeypatch):
    _install(monkeypatch)
    result = asyncio.run(
        cs.lichess_coaching_single_game(
            "testgame", color="white", depth=14, output_format="detailed", use_llm=False
        )
    )
    assert result["schema_version"] == "1.2"
    assert result["game_id"] == "testgame"
    assert result["report_meta"]["truncated"] is False
    # P0-7: the flagged inaccuracy has no pattern (detection is stubbed) and
    # must therefore explain itself.
    flag = result["flagged_moves"][0]
    assert flag["pattern_status"] == "unclassified"
    assert flag["unclassified_reason"] in (
        "quiet_positional",
        "forcing_move_unexplained",
        "capture_unexplained",
        "evidence_gap",
        "mechanism_not_identified",
    )
    assert result["patterns_meta"]["coverage"] == {
        "flagged": 1,
        "matched": 0,
        "unclassified": 1,
    }
    assert result["unclassified"][0]["ply"] == 3


def test_detailed_payload_validates_against_schema_12(monkeypatch):
    jsonschema = pytest.importorskip("jsonschema")
    _install(monkeypatch)
    result = asyncio.run(
        cs.lichess_coaching_single_game(
            "testgame", color="white", depth=14, output_format="detailed", use_llm=False
        )
    )
    schema = json.load(open(os.path.join(ROOT, "schemas/single_game_v1.2.json"), encoding="utf-8"))
    jsonschema.validate(result, schema)


def test_full_is_deprecated_alias_for_detailed(monkeypatch):
    _install(monkeypatch)
    result = asyncio.run(
        cs.lichess_coaching_single_game(
            "testgame", color="white", depth=14, output_format="full", use_llm=False
        )
    )
    assert result["schema_version"] == "1.2"


def test_compact_output_is_schema_21(monkeypatch):
    _install(monkeypatch)
    result = asyncio.run(
        cs.lichess_coaching_single_game(
            "testgame", color="white", depth=14, output_format="compact", use_llm=False
        )
    )
    assert result["v"] == "2.1"
    assert result["game"]["id"] == "testgame"
    assert result["flags"][0]["ply"] == 3
    assert result["flags"][0]["rank"] == 4
    assert result["summary"]["phases"]["opening"] == [60.0, 1]
    assert result["flags"][0]["pstatus"] == "unclassified"
    assert result["flags"][0]["why"] == "quiet_positional"


def test_both_returns_compact_and_detailed(monkeypatch):
    _install(monkeypatch)
    result = asyncio.run(
        cs.lichess_coaching_single_game(
            "testgame", color="white", depth=14, output_format="both", use_llm=False
        )
    )
    assert set(result) == {"compact", "detailed"}
    assert result["compact"]["v"] == "2.1"
    assert result["detailed"]["schema_version"] == "1.2"


def test_invalid_output_format_returns_error(monkeypatch):
    _install(monkeypatch)
    result = asyncio.run(
        cs.lichess_coaching_single_game(
            "testgame", color="white", depth=14, output_format="xml", use_llm=False
        )
    )
    assert result["status"] == "error"
    assert result["error"]


def test_use_llm_false_does_not_call_providers(monkeypatch):
    _install(monkeypatch)

    def boom(*args, **kwargs):
        raise AssertionError("LLM cascade must not be called")

    monkeypatch.setattr(cs, "safe_llm_call", boom)
    result = asyncio.run(
        cs.lichess_coaching_single_game(
            "testgame", color="white", depth=14, output_format="detailed", use_llm=False
        )
    )
    assert result["llm"]["reason"] == "llm_disabled"
    assert result["report_meta"]["source"] == "deterministic"
