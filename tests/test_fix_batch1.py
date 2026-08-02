"""Unit tests for FIX BATCH 1 (P1 data-correctness).

Covers:
  - B100: opening_report reads real model attributes (a.game.opening/color/result, a.total_acpl)
  - B98:  opponent_pool color derivation from PGN headers + n1/n2 computation
  - B121: kb/writer KB_ROOT points at _github/B2B-Knowledge-Base
  - B119: kb/writer filenames carry _HHMMSS timestamp
  - B31:  game_llm_cache key is per-color

Pure unit tests — no engine/LLM/network calls.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from lichess_analyzer_mcp.models.game import GameAnalysis, GameSummary
from lichess_analyzer_mcp.tools.coaching_opening_report import _game_opening_stats
from lichess_analyzer_mcp.tools.coaching_opponent_pool import _opponent_won, _resolve_colors


def _analysis(
    game_id: str, color: str, result: str, opening: str = "Sicilian Defense", acpl: float = 42.0
) -> GameAnalysis:
    g = GameSummary(
        id=game_id,
        platform="lichess",
        opening=opening,
        opening_eco="B20",
        color=color,
        result=result,
        player_name="author" if color == "white" else "opp",
        opponent_name="opp" if color == "white" else "author",
        opponent_rating=1900,
        player_rating=2000,
        time_control="300+0",
        date="2026-08-01",
        url=f"https://lichess.org/{game_id}",
    )
    a = GameAnalysis(game=g)
    a.total_acpl = acpl
    return a


class TestOpeningReport:
    """B100 — attributes must come from real model fields."""

    def test_extracts_real_attributes_white(self):
        a = _analysis("abc123", "white", "1-0", opening="Ruy Lopez", acpl=35.5)
        s = _game_opening_stats(a)
        assert s["opening"] == "Ruy Lopez"
        assert s["color"] == "white"
        assert s["acpl"] == 35.5
        assert s["result"] == "1-0"

    def test_extracts_real_attributes_black(self):
        a = _analysis("def456", "black", "0-1", opening="Sicilian Defense", acpl=71.0)
        s = _game_opening_stats(a)
        assert s["opening"] == "Sicilian Defense"
        assert s["color"] == "black"
        assert s["acpl"] == 71.0
        assert s["result"] == "0-1"

    def test_unknown_fallback(self):
        # Empty GameSummary -> "Unknown" opening, white, acpl 0, result "*"
        g = GameSummary(id="x", platform="lichess", opening="", opening_eco="", color="", result="")
        a = GameAnalysis(game=g)
        s = _game_opening_stats(a)
        assert s["opening"] == "Unknown"
        assert s["acpl"] == 0
        assert s["result"] == "*"


class TestOpponentPool:
    """B98 — color resolution + n1/n2."""

    def test_author_is_white(self):
        author, opponent = _resolve_colors("systeq", "otherplayer", "systeq")
        assert author == "white"
        assert opponent == "black"

    def test_author_is_black(self):
        author, opponent = _resolve_colors("otherplayer", "systeq", "systeq")
        assert author == "black"
        assert opponent == "white"

    def test_unknown_username_fallback(self):
        # username not in headers -> convention author=white
        author, opponent = _resolve_colors("whiteguy", "blackguy", "systeq")
        assert author == "white"
        assert opponent == "black"

    def test_no_username_fallback(self):
        author, opponent = _resolve_colors("whiteguy", "blackguy")
        assert author == "white"
        assert opponent == "black"

    def test_opponent_won_white(self):
        a = _analysis("g1", "white", "1-0")
        assert _opponent_won(a) is True

    def test_opponent_won_black(self):
        a = _analysis("g2", "black", "0-1")
        assert _opponent_won(a) is True

    def test_opponent_lost(self):
        a = _analysis("g3", "white", "0-1")
        assert _opponent_won(a) is False


class TestKbWriter:
    """B121 + B119."""

    def test_kb_root_points_to_github(self, monkeypatch, tmp_path):
        from lichess_analyzer_mcp.kb import writer

        fake_root = tmp_path / "B2B-Knowledge-Base"
        fake_root.mkdir()
        monkeypatch.setattr(writer, "KB_ROOT", str(fake_root))
        monkeypatch.setattr(writer, "_KB_EXISTS", True)
        monkeypatch.setattr(
            writer, "ANALYSIS_DIR", os.path.join(str(fake_root), "02_ANAL\xddZY", "02_chess")
        )
        monkeypatch.setattr(
            writer, "PATTERN_DIR", os.path.join(str(fake_root), "04_KNOWLEDGE_BASE", "02_chess")
        )

        path = writer.write_pattern_report("testuser", [])
        assert os.path.isfile(path)
        assert os.path.getsize(path) > 0
        assert "testuser" in os.path.basename(path)
        assert path.startswith(str(fake_root))
        # real KB_ROOT resolution points at _github
        assert "B2B-Knowledge-Base" in writer.KB_ROOT

    def test_kb_root_real_path(self):
        from lichess_analyzer_mcp.kb import writer

        # KB_ROOT normalized must point at the workspace B2B-Knowledge-Base,
        # not the repo root (B121: 4x .. resolves to _github/)
        root = os.path.normpath(writer.KB_ROOT)
        assert writer._KB_EXISTS is True
        assert root.endswith("_github" + os.sep + "B2B-Knowledge-Base") or root.endswith(
            "B2B-Knowledge-Base"
        )
        assert "lichess-analyzer-mcp" not in root

    def test_filename_has_timestamp(self, monkeypatch, tmp_path):
        from lichess_analyzer_mcp.kb import writer

        fake_root = tmp_path / "B2B-Knowledge-Base"
        fake_root.mkdir()
        monkeypatch.setattr(writer, "KB_ROOT", str(fake_root))
        monkeypatch.setattr(writer, "_KB_EXISTS", True)
        monkeypatch.setattr(
            writer, "ANALYSIS_DIR", os.path.join(str(fake_root), "02_ANAL\xddZY", "02_chess")
        )
        monkeypatch.setattr(
            writer, "PATTERN_DIR", os.path.join(str(fake_root), "04_KNOWLEDGE_BASE", "02_chess")
        )

        path = writer.write_analysis_report("testuser", {"games_analyzed": 1, "total_acpl": 30.0})
        name = os.path.basename(path)
        # format: chess_diagnosis_<user>_YYYY-MM-DD_HHMMSS.md
        assert re.match(r"chess_diagnosis_testuser_\d{4}-\d{2}-\d{2}_\d{6}\.md$", name)

    def test_kb_missing_root_raises(self, monkeypatch, tmp_path):
        from lichess_analyzer_mcp.kb import writer

        missing = tmp_path / "nope"
        monkeypatch.setattr(writer, "KB_ROOT", str(missing))
        monkeypatch.setattr(writer, "_KB_EXISTS", False)
        try:
            writer._ensure_dirs()
            assert False, "expected FileNotFoundError"
        except FileNotFoundError:
            pass


class TestLlmCacheKey:
    """B31 — per-color LLM cache key."""

    def test_path_differs_by_color(self, tmp_path, monkeypatch):
        from lichess_analyzer_mcp.services import game_llm_cache as g

        monkeypatch.setattr(g, "CACHE_DIR", str(tmp_path))
        p_white = g._llm_cache_path("abc123", "white")
        p_black = g._llm_cache_path("abc123", "black")
        assert p_white != p_black
        assert p_white.endswith("abc123_white_llm.json")
        assert p_black.endswith("abc123_black_llm.json")

    def test_roundtrip_per_color(self, tmp_path, monkeypatch):
        from lichess_analyzer_mcp.services import game_llm_cache as g

        monkeypatch.setattr(g, "CACHE_DIR", str(tmp_path))
        g._save_llm_cache(
            "abc123", "white", {"game_id": "abc123", "color": "white", "content_tag": "t1"}
        )
        g._save_llm_cache(
            "abc123", "black", {"game_id": "abc123", "color": "black", "content_tag": "t2"}
        )

        w = g._load_llm_cache("abc123", "white")
        b = g._load_llm_cache("abc123", "black")
        assert w is not None and w["color"] == "white"
        assert b is not None and b["color"] == "black"
        assert w["content_tag"] == "t1"
        assert b["content_tag"] == "t2"
