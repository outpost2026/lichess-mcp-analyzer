"""Two-part MDL for pattern measurements (P2, step B).

Why this module exists
----------------------
`coverage_score` (formerly mislabelled "compression") only measures how much of
the corpus a detector touches. It is not a compression argument. The admission
gate (methodology 2.3) needs a real, deterministic code-length comparison:

    gain_bits = L_null(data) - L_model(data)

where `L_null` codes the same observations with ONE pooled rate and `L_model`
codes them with TWO rates (flagged vs control). Positive gain means the split
buys more than the extra parameter costs.

Scope decision
--------------
MDL belongs to the measurement / admission layer, not to the runtime
`PatternMatch`:

- Cross-game detectors have no per-move applicability, so a per-move binomial
  code would be invalid for them.
- Patterns A and G count Poisson events (blunders can exceed games), so a
  binomial model on games would be misspecified.

This module is therefore called by measurement scripts only. It never runs
inside `detect_all` and never feeds `confidence`.

Model
-----
Data are coded **per group** (`n1` flagged moves, `n0` control moves), because
the group label is part of the observation:

    L(k, n | p) = log2 C(n, k) + n * H(p)          [exact binomial code length]
    p_pool      = (k1 + k0) / (n1 + n0)
    L_null      = L(k1, n1 | p_pool) + L(k0, n0 | p_pool)
    L_model     = L(k1, n1 | k1/n1) + L(k0, n0 | k0/n0) + n_params * 0.5 * log2(N)
    gain_bits   = L_null - L_model

The parameter prior is the BIC/MDL term `0.5 * log2(N)` per free parameter, so
a split is only accepted when the likelihood gain pays for the extra rate.

Scale note
----------
`gain_bits` is **not** linear in N: the `log2 C(n, k)` term grows like
`0.5 * log2 n`, so doubling the corpus does not exactly double the gain.
`gain_per_unit = gain_bits / (n1 + n0)` is the only quantity comparable across
studies, and only asymptotically (it converges to the Jensen-Shannon style
entropy gap between the pooled and the split model). Never compare raw
`gain_bits` across datasets of different size.

Verdict thresholds (fixed a priori, never tuned on data)
-------------------------------------------------------
2 / 6 / 10 bits are the conventional evidence steps (the bits analogue of the
Kass-Raftery 2/6/10 thresholds on `2 ln BF`):

    >= 10  "strong"
    >= 6   "moderate"
    >= 2   "weak"
    < 2    "single_rate"   (extra parameter is not paid for)
    -      "non_estimable" (zero events in a group, see `_estimability`)

Boundary tables are never scored: with `k = 0` the split model codes that group
in zero bits and the gain grows with N without any evidence.

All functions are pure and deterministic: no simulation, no scipy, no random.
"""

from __future__ import annotations

import math
from typing import Optional

# Evidence thresholds in bits, fixed before measurement (see module docstring).
EVIDENCE_WEAK = 2.0
EVIDENCE_MODERATE = 6.0
EVIDENCE_STRONG = 10.0


def binary_entropy(p: float) -> float:
    """Binary entropy H(p) in bits, with H(0) = H(1) = 0 (no NaN)."""
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def log2_comb(n: int, k: int) -> float:
    """log2 of the binomial coefficient C(n, k), via `lgamma`.

    Returns 0.0 for the degenerate `k = 0` and `k = n` cases. Raises
    `ValueError` for out-of-range input so a caller cannot silently code an
    impossible observation.
    """
    if n < 0 or k < 0 or k > n:
        raise ValueError(f"invalid binomial coefficient: n={n}, k={k}")
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)) / math.log(2.0)


def _binomial_bits(k: int, n: int, p: float) -> float:
    """Exact code length `-log2 P(k | n, p)` in bits."""
    return log2_comb(n, k) + n * binary_entropy(p)


def two_part_mdl(
    k1: int,
    n1: int,
    k0: int,
    n0: int,
    n_params: int = 1,
) -> Optional[dict]:
    """Compare one pooled rate against two rates (flagged vs control).

    `k1`/`n1` are events/exposures in the flagged group, `k0`/`n0` in the
    control group. `n_params` is the number of free parameters the split adds
    (1 for two independent rates, 0 to report the likelihood gain alone).

    Returns None when the comparison is undefined (`n <= 0` or `k` outside
    `[0, n]`), never a fabricated fallback.
    """
    for k, n in ((k1, n1), (k0, n0)):
        if n <= 0 or k < 0 or k > n:
            return None
    if n_params < 0:
        return None

    total = n1 + n0
    p1 = k1 / n1
    p0 = k0 / n0
    p_pool = (k1 + k0) / total

    l_null = _binomial_bits(k1, n1, p_pool) + _binomial_bits(k0, n0, p_pool)
    l_model = _binomial_bits(k1, n1, p1) + _binomial_bits(k0, n0, p0)
    param_bits = n_params * 0.5 * math.log2(total)
    gain_bits = l_null - (l_model + param_bits)

    estimable, reason = _estimability(k1, k0)
    return {
        "k1": k1,
        "n1": n1,
        "k0": k0,
        "n0": n0,
        "rate1": round(p1, 4),
        "rate0": round(p0, 4),
        "rate_pooled": round(p_pool, 4),
        "n_params": n_params,
        "param_bits": round(param_bits, 4),
        "l_null": round(l_null, 4),
        "l_model": round(l_model + param_bits, 4),
        "gain_bits": round(gain_bits, 4),
        "gain_per_unit": round(gain_bits / total, 6),
        "estimable": estimable,
        "non_estimable_reason": reason,
        "verdict": mdl_verdict(gain_bits) if estimable else "non_estimable",
    }


def _estimability(k1: int, k0: int) -> tuple[bool, Optional[str]]:
    """Reject boundary tables: a zero-event group has MLE 0 (or 1).

    At the boundary the split model codes that group in zero bits, so `gain_bits`
    grows with the control sample size even when nothing was observed. That is
    an artifact of the estimator, not evidence, and it is exactly the kind of
    fabricated number this project forbids. Same rule as the Katz lift: both
    groups need at least one event.
    """
    if k1 == 0 and k0 == 0:
        return False, "no events in either group; nothing to compare"
    if k1 == 0 or k0 == 0:
        return False, "zero events in a group; rate is on the boundary (MLE 0 or 1)"
    return True, None


def mdl_verdict(gain_bits: float) -> str:
    """Ordinal evidence label for a code-length gain in bits."""
    if gain_bits >= EVIDENCE_STRONG:
        return "strong"
    if gain_bits >= EVIDENCE_MODERATE:
        return "moderate"
    if gain_bits >= EVIDENCE_WEAK:
        return "weak"
    return "single_rate"
