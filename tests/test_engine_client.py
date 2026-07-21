"""Unit tests for engine_client with mocked Stockfish."""

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock
import chess
from src.services.engine_client import (
    _find_stockfish,
    analyze_position,
    evaluate_move,
    close_engine,
    _ENGINE_LOCK_TIMEOUT,
)


class TestFindStockfish:
    def test_returns_string(self):
        path = _find_stockfish()
        assert isinstance(path, str)
        assert len(path) > 0

    @patch("src.services.engine_client.os.path.isfile", return_value=True)
    def test_prefers_env_var(self, mock_isfile):
        with patch.dict(os.environ, {"STOCKFISH_PATH": "/custom/stockfish.exe"}, clear=False):
            path = _find_stockfish()
            assert path == "/custom/stockfish.exe"


class TestAnalyzePosition:
    def setup_method(self):
        self.fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    @patch("src.services.engine_client.get_engine")
    def test_returns_list(self, mock_get_engine):
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_analysis = MagicMock()
        mock_engine.analysis.return_value.__enter__.return_value = mock_analysis

        mock_score = MagicMock()
        mock_score.relative.score.return_value = 38
        mock_score.relative.mate.return_value = None

        mock_analysis.__iter__.return_value = [
            {"pv": [chess.Move.from_uci("e2e4")], "score": mock_score, "depth": 18}
        ]

        result = analyze_position(self.fen, depth=8, multipv=1)
        assert isinstance(result, list), f"Expected list, got {type(result)}: {result}"
        assert len(result) == 1


class TestEvaluateMove:
    def setup_method(self):
        self.fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    @patch("src.services.engine_client.get_engine")
    def test_returns_dict(self, mock_get_engine):
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine

        def fake_analyse(board, limit):
            result = MagicMock()
            fake_score = MagicMock()
            fake_score.relative.score.return_value = 38
            fake_score.relative.mate.return_value = None
            result.__getitem__.side_effect = lambda key: {
                "score": fake_score,
                "pv": [chess.Move.from_uci("e2e4")],
            }.get(key)
            return result

        mock_engine.analyse.side_effect = fake_analyse

        result = evaluate_move(self.fen, "e2e4", depth=8)
        assert isinstance(result, dict)
        assert "eval_before" in result
        assert "eval_after" in result


class TestCloseEngine:
    def test_close_none(self):
        close_engine()
