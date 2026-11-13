"""Deterministic interval statistics for pattern measurements (P1, schema v1.3).

Why this module exists
----------------------
`strength` is an ordinal detector score. It says nothing about how uncertain the
measured rate is. A pattern seen in 3 of 10 games and a pattern seen in 300 of
1000 games are not the same evidence, even when both have rate 0.30.

This module adds the missing uncertainty layer with closed-form, deterministic
formulas (no simulation, no randomness, no scipy):

- **Wilson score interval** for a proportion (games with pattern / games analysed).
  Preferred over the normal approximation because it stays inside [0, 1] and is
  well behaved for small k and for k = 0 or k = n.
- **Katz log method** for a rate ratio (lift), with Poisson variance
  `SE(log RR) = sqrt(1/k1 + 1/k2)`. Used only where a real contrast group exists.

Both functions are pure. Rounding happens at the boundary so the published
numbers are stable across runs.
"""

from __future__ import annotations

import math
from typing import Optional

# Two-sided 95 % normal quantile. Hard-coded so the output never depends on a
# statistics package version.
Z95 = 1.959963984540054


def wilson_interval(k: int, n: int, z: float = Z95) -> Optional[tuple[float, float]]:
    """95 % Wilson score interval for `k` successes out of `n` trials.

    Returns None when the interval is undefined (`n <= 0` or `k` outside
    `[0, n]`), never a fabricated fallback such as `(0, 1)`.
    """
    if n <= 0 or k < 0 or k > n:
        return None
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    margin = (z / denom) * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n))
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def rate_with_ci(k: int, n: int, digits: int = 4) -> dict:
    """Proportion with Wilson CI as a plain dict (JSON-ready).

    Keys: `k`, `n`, `rate`, `ci_low`, `ci_high`. `rate` is None when `n == 0`.
    """
    interval = wilson_interval(k, n)
    return {
        "k": k,
        "n": n,
        "rate": round(k / n, digits) if n > 0 else None,
        "ci_low": round(interval[0], digits) if interval else None,
        "ci_high": round(interval[1], digits) if interval else None,
    }


def rate_ratio_with_ci(k1: int, n1: int, k2: int, n2: int, digits: int = 3) -> Optional[dict]:
    """Rate ratio `(k1/n1) / (k2/n2)` with a 95 % Katz log-method interval.

    `k` are events (e.g. blunders), `n` are exposures (e.g. games). Returns None
    when the ratio is not estimable: any `n <= 0`, or either `k == 0` (a zero
    event count gives no finite log-scale variance). The caller must then omit
    lift rather than publish an unbounded number.
    """
    if n1 <= 0 or n2 <= 0 or k1 <= 0 or k2 <= 0:
        return None
    ratio = (k1 / n1) / (k2 / n2)
    se = math.sqrt(1.0 / k1 + 1.0 / k2)
    low = math.exp(math.log(ratio) - Z95 * se)
    high = math.exp(math.log(ratio) + Z95 * se)
    return {
        "lift": round(ratio, digits),
        "ci_low": round(low, digits),
        "ci_high": round(high, digits),
    }
