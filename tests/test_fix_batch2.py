"""Unit tests for FIX BATCH 2 (P2 bugs B5, B16, B101, B113).

Pure unit tests — mocked engine/threads, no real Stockfish, no network.
Vzor: tests/test_fix_batch1.py
"""

import asyncio
import os
import sys
import threading
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from lichess_analyzer_mcp.models.game import GameAnalysis, GameSummary
from lichess_analyzer_mcp.services import engine_client as ec
from lichess_analyzer_mcp.services.pattern_detector import PatternDetector
from lichess_analyzer_mcp.tools.fetch_games import lichess_fetch_games


def _summary(game_id: str = "g1") -> GameSummary:
    return GameSummary(
        id=game_id,
        platform="lichess",
        opening="",
        opening_eco="",
        color="white",
        result="1-0",
        opponent_name="opp",
        opponent_rating=1500,
        player_rating=1500,
        time_control="300+0",
        date="2026-07-26",
        url=f"https://lichess.org/{game_id}",
    )


# ── B5: _run_engine_call kills the engine reference it was given ───────────


class TestB5EngineRef:
    def _fake_timeout_thread(self):
        thread = MagicMock()
        thread.is_alive.return_value = True
        return thread

    def test_timeout_kills_local_engine_not_shared(self):
        local = MagicMock()
        shared = MagicMock()
        ec._engine = shared

        def _blocking():
            raise AssertionError("should never run to completion")

        with patch.object(threading, "Thread", return_value=self._fake_timeout_thread()):
            res = ec._run_engine_call(_blocking, timeout_s=0.001, engine=local)

        assert "error" in res and "timed out" in res["error"]
        local.quit.assert_called_once()
        shared.quit.assert_not_called()
        assert ec._engine is shared

    def test_timeout_shared_default_resets_global(self):
        shared = MagicMock()
        ec._engine = shared

        def _blocking():
            raise AssertionError("should never run to completion")

        with patch.object(threading, "Thread", return_value=self._fake_timeout_thread()):
            res = ec._run_engine_call(_blocking, timeout_s=0.001)

        assert "error" in res and "timed out" in res["error"]
        shared.quit.assert_called_once()
        assert ec._engine is None

    def test_worker_exception_returns_error(self):
        def _boom():
            raise ValueError("boom")

        res = ec._run_engine_call(_boom, timeout_s=0.01)
        assert res == {"error": "boom"}


# ── B16: evaluation_errors counter ─────────────────────────────────────────


class TestB16EvalError:
    def test_to_dict_emits_counter(self):
        d = GameAnalysis(game=_summary()).to_dict()
        assert isinstance(d["evaluation_errors"], int)
        assert d["evaluation_errors"] == 0

    def test_from_dict_handles_missing_key(self):
        a = GameAnalysis.from_dict(
            {
                "game": {
                    "id": "g1",
                    "platform": "lichess",
                    "opening": "",
                    "opening_eco": "",
                    "color": "white",
                    "result": "1-0",
                    "opponent_name": "opp",
                    "opponent_rating": 1500,
                    "player_rating": 1500,
                    "time_control": "",
                    "date": "",
                    "url": "",
                },
                "moves": [],
                "blunders": [],
                "mistakes": [],
                "inaccuracies": [],
            }
        )
        assert a.evaluation_errors == 0

    def test_from_dict_roundtrip_preserves_counter(self):
        a = GameAnalysis(game=_summary())
        a.evaluation_errors = 3
        b = GameAnalysis.from_dict(a.to_dict())
        assert b.evaluation_errors == 3


# ── B16 contract: prompt builder reads counter with default ────────────────


class TestEvaluationErrorsContract:
    def _prompt_data(self, **extra):
        data = {
            "game": {
                "id": "g1",
                "color": "white",
                "result": "1-0",
                "opening": "",
                "opponent_name": "opp",
                "opponent_rating": 1500,
            },
            "moves": [],
            "blunders": [],
            "mistakes": [],
            "inaccuracies": [],
            "phase_stats": {},
            "total_acpl": 10.0,
            "accuracy": 99.0,
        }
        data.update(extra)
        return data

    def test_prompt_reads_with_default(self):
        from lichess_analyzer_mcp.services.game_llm_cache import _build_game_prompt

        prompt = _build_game_prompt(self._prompt_data())
        assert "Eval errors: 0" not in prompt
        assert "?" not in prompt

    def test_prompt_renders_nonzero(self):
        from lichess_analyzer_mcp.services.game_llm_cache import _build_game_prompt

        prompt = _build_game_prompt(self._prompt_data(evaluation_errors=3))
        assert "Eval errors: 3" in prompt
        assert "ACPL may be optimistic" in prompt


# ── B101: source="chesscom" fail-fast ──────────────────────────────────────


class TestB101Chesscom:
    def test_chesscom_returns_error(self):
        res = asyncio.run(lichess_fetch_games("systeq", source="chesscom"))
        assert "error" in res
        assert "not supported" in res["error"]
        assert "games" not in res

    def test_invalid_source_returns_error(self):
        res = asyncio.run(lichess_fetch_games("systeq", source="chess.com"))
        assert "error" in res
        assert "games" not in res


# ── B113: _detect_s tolerates fen="" ───────────────────────────────────────


class TestB113FenEmpty:
    def _make_analysis(self, fen: str) -> GameAnalysis:
        from lichess_analyzer_mcp.models.game import MoveAnalysis

        a = GameAnalysis(game=_summary())
        m = MoveAnalysis(
            ply=1,
            move_uci="e2e4",
            move_san="e4",
            eval_before=0,
            eval_after=0,
            win_prob_before=0.5,
            win_prob_after=0.5,
            centipawn_loss=600,
            classification="blunder",
            best_move_uci="",
            best_move_san="",
            is_tactical_motif=False,
            motif_type=None,
            phase="middlegame",
            fen=fen,
            was_in_check=True,
        )
        a.moves.append(m)
        return a

    def test_empty_fen_no_crash(self):
        detector = PatternDetector()
        analyses = [self._make_analysis(fen="")]
        match = detector._detect_s(analyses, {})
        assert match is None

    def test_valid_fen_no_crash(self):
        fen = "4k3/8/8/8/8/8/4r3/4K3 w - - 0 1"
        detector = PatternDetector()
        analyses = [self._make_analysis(fen=fen)]
        detector._detect_s(analyses, {})
