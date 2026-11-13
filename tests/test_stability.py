"""P2 / step C: deterministic split-half stability and temporal drift.

Contract under test:

- the hash split is reproducible, complete and disjoint,
- adding a game does not move existing games between halves,
- the two-proportion z is the closed-form pooled statistic,
- cosine is profile shape, not magnitude agreement,
- drift compares the older and newer half by date, and is `None` (never
  `False`) when there are not enough dated games,
- `unstable` is `True` only when an estimable sub-test fires.
"""

from __future__ import annotations

import datetime

import pytest

from lichess_analyzer_mcp.kb.schemas import validate_against_schema
from lichess_analyzer_mcp.services.statistics import Z95
from lichess_analyzer_mcp.services.stability import (
    MIN_HALF_GAMES,
    build_stability,
    cosine_share,
    dated_order,
    split_halves,
    temporal_split,
    two_proportion_z,
)


def _keys(n: int) -> list[str]:
    return [f"g{i:03d}|white" for i in range(n)]


def _dated(n: int, start: datetime.date = datetime.date(2026, 1, 1)) -> list[tuple[str, str]]:
    return [
        (key, (start + datetime.timedelta(days=i)).isoformat()) for i, key in enumerate(_keys(n))
    ]


class TestSplitHalves:
    def test_deterministic(self):
        keys = _keys(50)
        assert split_halves(keys) == split_halves(keys)

    def test_complete_and_disjoint(self):
        keys = _keys(101)
        a, b = split_halves(keys)
        assert set(a) & set(b) == set()
        assert sorted(a + b) == sorted(keys)

    def test_adding_a_game_does_not_move_existing_ones(self):
        keys = _keys(60)
        a, b = split_halves(keys)
        a2, b2 = split_halves(keys + ["newcomer|black"])
        assert set(a) <= set(a2) | set(b2)
        # Parity membership of every old key is unchanged.
        assert set(a) <= set(a2)
        assert set(b) <= set(b2)

    def test_roughly_balanced(self):
        a, b = split_halves(_keys(200))
        assert 70 <= len(a) <= 130
        assert 70 <= len(b) <= 130


class TestTwoProportionZ:
    def test_hand_derived_value(self):
        # 0.30 vs 0.10, pooled 0.20, SE = sqrt(0.16 * 0.02) = 0.05657
        assert two_proportion_z(30, 100, 10, 100) == pytest.approx(3.5355, abs=1e-4)

    def test_swap_flips_sign(self):
        forward = two_proportion_z(30, 100, 10, 100)
        backward = two_proportion_z(10, 100, 30, 100)
        assert forward is not None and backward is not None
        assert forward == pytest.approx(-backward)

    @pytest.mark.parametrize(
        "k1,n1,k0,n0",
        [(0, 0, 0, 10), (0, 10, 0, 10), (10, 10, 10, 10), (11, 10, 0, 10)],
    )
    def test_undefined_cases_return_none(self, k1, n1, k0, n0):
        assert two_proportion_z(k1, n1, k0, n0) is None


class TestCosine:
    def test_identical_profile_is_one(self):
        assert cosine_share({"A": 3, "B": 1}, {"A": 30, "B": 10}) == pytest.approx(1.0)

    def test_disjoint_profile_is_zero(self):
        assert cosine_share({"A": 5}, {"B": 5}) == pytest.approx(0.0)

    def test_empty_half_is_none(self):
        assert cosine_share({"A": 0}, {"A": 5}) is None


class TestTemporalSplit:
    def test_undated_games_are_dropped_and_order_is_oldest_first(self):
        games = [
            ("b", "2026-03-02"),
            ("a", "2026-03-01"),
            ("c", ""),
            ("d", "not-a-date"),
        ]
        assert [key for key, _ in dated_order(games)] == ["a", "b"]

    def test_dotted_dates_are_accepted_and_normalised(self):
        # The real cache stores `2026.08.31`; the report must show ISO dates.
        games = [("b", "2026.08.31"), ("a", "2026.07.25")]
        assert dated_order(games) == [("a", "2026-07-25"), ("b", "2026-08-31")]

    def test_cut_date_is_first_game_of_new_era(self):
        dated = dated_order(_dated(40))
        split = temporal_split(dated)
        assert split["n_old"] == 20
        assert split["n_new"] == 20
        assert split["cut_date"] == dated[20][1]


class TestBuildStability:
    def test_halves_cover_every_game(self):
        result = build_stability({"O": _keys(40)}, _dated(40))
        block = result["patterns"]["O"]
        assert block["split_half"]["n_a"] + block["split_half"]["n_b"] == 40
        assert result["split_half"]["cosine"] == pytest.approx(1.0)

    def test_pattern_in_one_half_only_is_unstable(self):
        keys = _keys(100)
        a_keys, _ = split_halves(keys)
        result = build_stability({"O": a_keys}, _dated(100))
        block = result["patterns"]["O"]
        assert block["half"]["rate_a"] == pytest.approx(1.0)
        assert block["half"]["rate_b"] == pytest.approx(0.0)
        assert block["half"]["unstable"] is True
        assert block["unstable"] is True

    def test_equal_rates_in_both_halves_are_stable(self):
        # Evenly spread over time so the temporal test does not fire either.
        keys = _keys(100)
        pattern = keys[::10]
        block = build_stability({"O": pattern}, _dated(100))["patterns"]["O"]
        assert block["half"]["delta"] < 0.05
        assert block["half"]["unstable"] is False
        assert block["drift"]["flag"] is False
        assert block["unstable"] is False

    def test_small_halves_are_not_estimable(self):
        keys = _keys(10)
        block = build_stability({"O": keys}, _dated(10))["patterns"]["O"]
        assert block["half"]["estimable"] is False
        assert block["half"]["unstable"] is None
        assert block["drift"]["estimable"] is False
        assert block["drift"]["flag"] is None
        assert block["unstable"] is None

    def test_temporal_change_is_detected(self):
        dated = _dated(80)
        old_keys = [key for key, _ in dated[:40]]
        block = build_stability({"O": old_keys}, dated)["patterns"]["O"]
        assert block["drift"]["estimable"] is True
        assert block["drift"]["rate_old"] == pytest.approx(1.0)
        assert block["drift"]["rate_new"] == pytest.approx(0.0)
        assert block["drift"]["flag"] is True

    def test_no_temporal_change(self):
        dated = _dated(80)
        pattern = [key for i, (key, _) in enumerate(dated) if i % 5 == 0]
        block = build_stability({"O": pattern}, dated)["patterns"]["O"]
        assert block["drift"]["estimable"] is True
        assert block["drift"]["delta"] == pytest.approx(0.0)
        assert block["drift"]["flag"] is False

    def test_undated_games_do_not_fake_drift(self):
        games = [(key, "") for key in _keys(80)]
        block = build_stability({"O": _keys(80)}, games)["patterns"]["O"]
        assert block["drift"]["n_dated"] == 0
        assert block["drift"]["estimable"] is False
        assert block["drift"]["flag"] is None

    def test_deterministic(self):
        games = _dated(60)
        first = build_stability({"O": _keys(60)}, games)
        second = build_stability({"O": _keys(60)}, games)
        assert first == second

    def test_min_half_games_constant_is_documented(self):
        assert MIN_HALF_GAMES == 15


class TestStabilitySchema:
    def _artifact(self, stability: dict) -> dict:
        return {
            "schema_version": "1.4",
            "username": "t",
            "games_analyzed": 100,
            "patterns_detected": [
                {
                    "pattern_id": "O",
                    "pattern_name": "Overextension",
                    "confidence": 50.0,
                    "frequency": 10,
                    "severity": "medium",
                    "n_games": 20,
                    "n_units": 100,
                    "rate": 0.2,
                    "rate_ci": {"low": 0.13, "high": 0.29},
                    "lift": None,
                    "lift_ci": {"low": None, "high": None},
                    "lift_unavailable_reason": "no control group",
                    "stability": stability,
                }
            ],
            "total_patterns": 1,
        }

    def _stability(self, **overrides) -> dict:
        block = {
            "half": {
                "rate_a": 0.2,
                "rate_b": 0.2,
                "delta": 0.0,
                "z": 0.0,
                "estimable": True,
                "reason": None,
                "unstable": False,
            },
            "split_half": {
                "method": "sha256_parity",
                "n_a": 50,
                "n_b": 50,
                "cosine": 0.99,
            },
            "drift": {
                "method": "chronological_halves_z",
                "estimable": True,
                "flag": False,
                "reason": None,
                "n_dated": 100,
                "n_old": 50,
                "n_new": 50,
                "cut_date": "2026-02-20",
                "rate_old": 0.2,
                "rate_new": 0.2,
                "delta": 0.0,
                "z": 0.0,
            },
            "unstable": False,
        }
        block.update(overrides)
        return block

    def test_valid_block_passes(self):
        assert validate_against_schema(self._artifact(self._stability())) == []

    def test_unstable_false_cannot_hide_unstable_subtest(self):
        stability = self._stability()
        stability["half"]["unstable"] = True
        errors = validate_against_schema(self._artifact(stability))
        assert any("contradicts" in e for e in errors)

    def test_unstable_true_requires_estimable_subtest(self):
        stability = self._stability()
        stability["half"]["estimable"] = False
        stability["drift"]["estimable"] = False
        stability["drift"]["flag"] = None
        stability["unstable"] = True
        errors = validate_against_schema(self._artifact(stability))
        assert any("requires an estimable" in e for e in errors)

    def test_drift_flag_must_be_null_when_not_estimable(self):
        stability = self._stability()
        stability["drift"]["estimable"] = False
        stability["drift"]["flag"] = False
        errors = validate_against_schema(self._artifact(stability))
        assert any("drift.flag must be null" in e for e in errors)

    def test_rate_out_of_range_is_rejected(self):
        stability = self._stability()
        stability["half"]["rate_a"] = 1.5
        errors = validate_against_schema(self._artifact(stability))
        assert any("out of [0, 1]" in e for e in errors)

    def test_schema_version_is_1_4(self):
        artifact = self._artifact(self._stability())
        artifact["schema_version"] = "1.3"
        errors = validate_against_schema(artifact)
        assert any("not supported" in e for e in errors)


def test_z95_is_used_as_threshold():
    assert Z95 == pytest.approx(1.959963984540054)
