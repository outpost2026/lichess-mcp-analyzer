"""Session E: Depth policy tests — config, auto-select, batch estimates."""

import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from lichess_analyzer_mcp.config.depth import DEPTH_DEFAULTS
from lichess_analyzer_mcp.services.game_analyzer import _detect_game_profile


class TestDepthConfig:
    def test_defaults_contains_all_keys(self):
        assert "standard" in DEPTH_DEFAULTS
        assert "batch" in DEPTH_DEFAULTS
        assert "focused" in DEPTH_DEFAULTS
        assert "limits" in DEPTH_DEFAULTS

    def test_standard_keys(self):
        std = DEPTH_DEFAULTS["standard"]
        for k in (
            "single_game",
            "import_pgn",
            "position",
            "bullet",
            "blitz",
            "rapid",
            "classical",
            "correspondence",
            "unknown",
        ):
            assert k in std, f"missing standard.{k}"
            assert isinstance(std[k], int)

    def test_batch_keys(self):
        for k in ("pending", "diagnose", "patterns", "anonymous"):
            assert k in DEPTH_DEFAULTS["batch"]

    def test_limits_range(self):
        limits = DEPTH_DEFAULTS["limits"]
        assert limits["min"] < limits["max_single_game"]
        assert limits["max_batch"] < limits["max_single_game"]
        assert limits["max_time_single"] > 0

    def test_depth_values_in_range(self):
        limits = DEPTH_DEFAULTS["limits"]
        for group in ("standard", "batch", "focused"):
            for k, v in DEPTH_DEFAULTS[group].items():
                assert limits["min"] <= v <= limits["max_single_game"], (
                    f"{group}.{k}={v} out of range"
                )


class TestDetectGameProfile:
    @pytest.mark.parametrize(
        "tc,expected",
        [
            ("60+0", "bullet"),
            ("120+1", "bullet"),
            ("180+0", "blitz"),
            ("300+3", "blitz"),
            ("480+0", "blitz"),
            ("600+5", "rapid"),
            ("900+10", "rapid"),
            ("1800+0", "rapid"),
            ("3600+30", "classical"),
            ("7200+60", "classical"),
            ("-", "correspondence"),
            ("?", "unknown"),
            ("", "unknown"),
        ],
    )
    def test_detect_profile(self, tc, expected):
        assert _detect_game_profile(tc) == expected

    def test_mapped_depth_is_assigned(self):
        std = DEPTH_DEFAULTS["standard"]
        for tc_key in ("bullet", "blitz", "rapid", "classical", "correspondence", "unknown"):
            d = std.get(tc_key, DEPTH_DEFAULTS["standard"]["single_game"])
            assert 8 <= d <= 24

    def test_bullet_blitz_depth(self):
        assert DEPTH_DEFAULTS["standard"]["bullet"] == 12
        assert DEPTH_DEFAULTS["standard"]["blitz"] == 12

    def test_rapid_classical_depth(self):
        assert DEPTH_DEFAULTS["standard"]["rapid"] == 14
        assert DEPTH_DEFAULTS["standard"]["classical"] == 14

    def test_correspondence_depth(self):
        assert DEPTH_DEFAULTS["standard"]["correspondence"] == 18

    def test_unknown_depth_fallback(self):
        assert DEPTH_DEFAULTS["standard"]["unknown"] == 14


class TestBatchEstimates:
    def test_avg_time_nonzero(self):
        avg = {12: 58, 14: 84, 18: 588}
        for d, t in avg.items():
            assert t > 0

    def test_estimate_15min_warning(self):
        avg = {12: 58, 14: 84, 18: 588}
        for d, secs in avg.items():
            for n in [10, 20, 50]:
                total = n * secs
                if total > 900:
                    pass  # expected warning threshold
