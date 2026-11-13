"""P2 / step B: real two-part MDL for measurement (not runtime confidence).

The contract under test:

- code lengths are exact binomial code lengths (`log2 C(n,k) + n*H(p)`),
- a split into two rates must PAY for its extra parameter (`0.5*log2 N`),
- identical rates give a negative gain (the pooled model wins),
- `gain_bits` is not linear in N; only `gain_per_unit` is comparable,
- undefined tables return None instead of a fabricated number.

All expected values below are hand-derived, not copied from the implementation.
"""

from __future__ import annotations

import math

import pytest

from lichess_analyzer_mcp.services.mdl import (
    EVIDENCE_MODERATE,
    EVIDENCE_STRONG,
    EVIDENCE_WEAK,
    binary_entropy,
    log2_comb,
    mdl_verdict,
    two_part_mdl,
)


class TestCodeLengthPrimitives:
    def test_log2_comb_small_exact(self):
        assert log2_comb(4, 2) == pytest.approx(math.log2(6))
        assert log2_comb(10, 8) == pytest.approx(math.log2(45))

    @pytest.mark.parametrize("n,k", [(0, 0), (7, 0), (7, 7)])
    def test_log2_comb_degenerate_is_zero(self, n, k):
        assert log2_comb(n, k) == 0.0

    @pytest.mark.parametrize("n,k", [(3, 4), (5, -1), (-1, 0)])
    def test_log2_comb_rejects_impossible_input(self, n, k):
        with pytest.raises(ValueError):
            log2_comb(n, k)

    def test_binary_entropy_bounds_and_midpoint(self):
        assert binary_entropy(0.0) == 0.0
        assert binary_entropy(1.0) == 0.0
        assert binary_entropy(0.5) == pytest.approx(1.0)

    def test_binary_entropy_is_symmetric(self):
        assert binary_entropy(0.2) == pytest.approx(binary_entropy(0.8))


class TestTwoPartMdl:
    def test_hand_derived_large_split_is_strong(self):
        # 30/40 (p=0.75) vs 10/40 (p=0.25), pooled 0.5:
        # L_null  = 2*(log2 C(40,30) + 40) = 139.318
        # L_model = 2*(log2 C(40,30) + 40*H(0.75)) + 0.5*log2(80) = 127.381
        result = two_part_mdl(30, 40, 10, 40)
        assert result is not None
        assert result["l_null"] == pytest.approx(139.318, abs=1e-3)
        assert result["l_model"] == pytest.approx(127.381, abs=1e-3)
        assert result["gain_bits"] == pytest.approx(11.937, abs=1e-3)
        assert result["verdict"] == "strong"
        assert result["estimable"] is True

    def test_small_interior_table_does_not_pay(self):
        # 2/3 vs 1/3: the likelihood gain (0.49 bits) is below the 1.29-bit
        # parameter cost, so the pooled model wins even with separated rates.
        result = two_part_mdl(2, 3, 1, 3)
        assert result is not None
        assert result["gain_bits"] == pytest.approx(-0.802, abs=1e-3)
        assert result["verdict"] == "single_rate"

    def test_boundary_table_is_computed_but_never_scored(self):
        # k0=0 makes the MLE degenerate: the split codes the control group in
        # zero bits, so the gain is an artifact and must not be reported.
        result = two_part_mdl(2, 2, 0, 2)
        assert result is not None
        assert result["gain_bits"] == pytest.approx(3.0)
        assert result["estimable"] is False
        assert result["verdict"] == "non_estimable"
        assert "boundary" in (result["non_estimable_reason"] or "")

    def test_identical_rates_must_be_negative(self):
        # Same 5/10 in both groups: the split buys nothing and pays 0.5*log2(20).
        result = two_part_mdl(5, 10, 5, 10)
        assert result is not None
        assert result["gain_bits"] == pytest.approx(-2.161, abs=1e-3)
        assert result["verdict"] == "single_rate"

    def test_identical_rates_stay_negative_when_corpus_doubles(self):
        result = two_part_mdl(10, 20, 10, 20)
        assert result is not None
        assert result["gain_bits"] < 0
        assert result["verdict"] == "single_rate"

    def test_group_swap_is_symmetric(self):
        a = two_part_mdl(8, 10, 2, 10)
        b = two_part_mdl(2, 10, 8, 10)
        assert a is not None and b is not None
        assert a["gain_bits"] == pytest.approx(b["gain_bits"])
        assert a["l_null"] == pytest.approx(b["l_null"])

    def test_parameter_prior_is_exactly_bic_term(self):
        with_prior = two_part_mdl(30, 40, 10, 40, n_params=1)
        without = two_part_mdl(30, 40, 10, 40, n_params=0)
        assert with_prior is not None and without is not None
        assert with_prior["gain_bits"] == pytest.approx(
            without["gain_bits"] - 0.5 * math.log2(80), abs=1e-3
        )

    def test_gain_per_unit_is_bounded_by_entropy_gap(self):
        # p1=0.8, p0=0.2, pooled 0.5: the asymptotic per-move gain is
        # H(0.5) - (H(0.8) + H(0.2))/2 = 1 - 0.7219 = 0.2781 bits.
        result = two_part_mdl(8, 10, 2, 10)
        assert result is not None
        gap = 1.0 - binary_entropy(0.8)
        assert 0 < result["gain_per_unit"] < gap

    def test_gain_per_unit_approaches_gap_but_gain_bits_is_not_linear(self):
        small = two_part_mdl(8, 10, 2, 10)
        large = two_part_mdl(16, 20, 4, 20)
        assert small is not None and large is not None
        gap = 1.0 - binary_entropy(0.8)
        # Documented non-linearity: the combinatorial term grows, so raw
        # gain_bits more than doubles while per-unit gain only creeps up.
        assert large["gain_bits"] > 2 * small["gain_bits"]
        assert large["gain_per_unit"] > small["gain_per_unit"]
        assert large["gain_per_unit"] < gap

    def test_zero_event_control_is_not_estimable(self):
        # Without control events the split codes that group in 0 bits and the
        # gain grows with n0 — an estimator artifact, never a finding.
        result = two_part_mdl(10, 50, 0, 200)
        assert result is not None
        assert result["rate0"] == 0.0
        assert result["estimable"] is False
        assert result["verdict"] == "non_estimable"

    def test_no_events_at_all_is_not_estimable(self):
        result = two_part_mdl(0, 50, 0, 200)
        assert result is not None
        assert result["estimable"] is False
        assert "no events" in (result["non_estimable_reason"] or "")

    @pytest.mark.parametrize(
        "k1,n1,k0,n0",
        [(0, 0, 0, 10), (5, 0, 0, 10), (11, 10, 0, 10), (0, 10, 5, -1)],
    )
    def test_undefined_table_returns_none(self, k1, n1, k0, n0):
        assert two_part_mdl(k1, n1, k0, n0) is None

    def test_negative_parameter_count_returns_none(self):
        assert two_part_mdl(5, 10, 1, 10, n_params=-1) is None

    def test_deterministic(self):
        assert two_part_mdl(7, 19, 3, 41) == two_part_mdl(7, 19, 3, 41)


class TestVerdict:
    @pytest.mark.parametrize(
        "gain,expected",
        [
            (EVIDENCE_STRONG + 0.1, "strong"),
            (EVIDENCE_MODERATE, "moderate"),
            (EVIDENCE_WEAK, "weak"),
            (EVIDENCE_WEAK - 0.01, "single_rate"),
            (-5.0, "single_rate"),
        ],
    )
    def test_thresholds(self, gain, expected):
        assert mdl_verdict(gain) == expected
