"""P1 / schema 1.3: deterministic interval statistics.

No randomness, no scipy: every expected value below is the closed-form
Wilson / Katz result, so the tests pin the formula rather than a library.
"""

from __future__ import annotations

import pytest

from lichess_analyzer_mcp.services.statistics import (
    Z95,
    rate_ratio_with_ci,
    rate_with_ci,
    wilson_interval,
)


class TestWilsonInterval:
    def test_half_of_thirty(self):
        low, high = wilson_interval(15, 30)
        # centre 0.5, margin ~0.1685 at z=1.96
        assert low == pytest.approx(0.3315, abs=1e-4)
        assert high == pytest.approx(0.6685, abs=1e-4)

    def test_zero_successes_lower_bound_is_zero(self):
        low, high = wilson_interval(0, 10)
        assert low == 0.0
        assert high == pytest.approx(0.2775, abs=1e-4)

    def test_all_successes_upper_bound_is_one(self):
        low, high = wilson_interval(10, 10)
        assert high == pytest.approx(1.0)
        assert low == pytest.approx(0.7225, abs=1e-4)

    def test_single_case_is_wide(self):
        low, high = wilson_interval(1, 3)
        assert low < 0.1
        assert high > 0.75

    @pytest.mark.parametrize("k,n", [(0, 0), (1, 0), (-1, 10), (11, 10)])
    def test_undefined_inputs_return_none(self, k, n):
        assert wilson_interval(k, n) is None

    def test_interval_contains_point_estimate(self):
        for k, n in [(0, 5), (1, 5), (3, 7), (99, 100)]:
            low, high = wilson_interval(k, n)
            assert low <= k / n <= high


class TestRateWithCi:
    def test_shape_and_rounding(self):
        stats = rate_with_ci(15, 30)
        assert stats["k"] == 15
        assert stats["n"] == 30
        assert stats["rate"] == 0.5
        assert stats["ci_low"] < stats["rate"] < stats["ci_high"]

    def test_empty_denominator_is_null_not_zero(self):
        stats = rate_with_ci(0, 0)
        assert stats["rate"] is None
        assert stats["ci_low"] is None
        assert stats["ci_high"] is None

    def test_deterministic(self):
        assert rate_with_ci(7, 19) == rate_with_ci(7, 19)


class TestRateRatio:
    def test_fourfold_lift(self):
        result = rate_ratio_with_ci(20, 10, 5, 10)
        assert result is not None
        assert result["lift"] == 4.0
        # SE(log RR) = sqrt(1/20 + 1/5) = 0.5
        assert result["ci_low"] == pytest.approx(1.501, abs=1e-3)
        assert result["ci_high"] == pytest.approx(10.658, abs=1e-3)

    def test_interval_contains_point_estimate(self):
        result = rate_ratio_with_ci(12, 8, 4, 8)
        assert result is not None
        assert result["ci_low"] <= result["lift"] <= result["ci_high"]

    @pytest.mark.parametrize(
        "k1,n1,k2,n2",
        [(0, 10, 5, 10), (5, 10, 0, 10), (5, 0, 5, 10), (5, 10, 5, 0)],
    )
    def test_not_estimable_returns_none(self, k1, n1, k2, n2):
        assert rate_ratio_with_ci(k1, n1, k2, n2) is None

    def test_z95_is_two_sided_95_percent(self):
        assert Z95 == pytest.approx(1.959963984540054)
