"""Deterministic split-half stability and temporal drift (P2, step C).

Why this module exists
----------------------
A pattern that only exists in one half of the corpus is not a trait, it is an
artefact of the sample. Until now the report said nothing about that. This
module adds two checks, both deterministic:

1. **Split-half stability** — games are split by a hash of `game_id|color`, so
   the split is stable across runs and independent of file order. For each
   pattern the two halves are compared with a two-proportion z-test, and the
   cosine of the cohort pattern-share vectors gives one profile-shape number.
2. **Temporal drift** — games ordered by date and split at the chronological
   median; the same two-proportion z-test asks whether the older half differs
   from the newer half.

Both are measurement tools. They do not change detection, `strength`, or
`DETECTOR_VERSION`; they only label a pattern `unstable` so a reader does not
treat a sample artefact as a trait.

Why hash and not a random seed
------------------------------
`random` would make the report non-reproducible. `sha256(salt|game_key)` is
stable, cheap, and independent of the order in which cache files are read.

Why chronological halves instead of Page-Hinkley
------------------------------------------------
Page-Hinkley needs two constants (`delta` tolerance, `lambda` alarm) whose
correct values depend on the stream length and on the effect size. With ~130
post-reference games any fixed pair either fires under the null (because the
statistic drifts by `delta` per sample) or never fires. Choosing those numbers
on this corpus would be exactly the uncalibrated tuning this project forbids.
A single two-proportion z-test at the chronological median needs no such
constant: it reuses the same 95 % threshold as the split-half test, and its
effect size (`delta`) is reported, not assumed. A multi-cut scan with
Bonferroni correction is a later refinement, not a prerequisite.

Thresholds (fixed a priori, never tuned on data)
------------------------------------------------
- `|z| >= 1.96` (two-sided 95 %) marks a difference worth investigating.
- Both halves need at least `MIN_HALF_GAMES = 15` games, and drift needs at
  least `2 * MIN_HALF_GAMES` dated games; otherwise the metric is `None` with a
  reason, never `False`.

`unstable` is a **flag to investigate**, not a verdict: with 4 patterns and two
tests per pattern the family-wise false-positive rate is not controlled. The
report must not turn it into "pattern is fake".
"""

from __future__ import annotations

import hashlib
import math
from typing import Iterable, Optional

from lichess_analyzer_mcp.services.statistics import Z95

SPLIT_SALT = "split-half-v1"
MIN_HALF_GAMES = 15


def split_halves(keys: Iterable[str], salt: str = SPLIT_SALT) -> tuple[list[str], list[str]]:
    """Deterministic ~50/50 split by `sha256(salt|key)` parity.

    Parity is used instead of "sort by hash, cut in the middle" so that adding
    one game does not move every other game to the other half.
    """
    a: list[str] = []
    b: list[str] = []
    for key in keys:
        digest = hashlib.sha256(f"{salt}|{key}".encode("utf-8")).digest()
        (a if digest[0] & 1 else b).append(key)
    return a, b


def two_proportion_z(k1: int, n1: int, k0: int, n0: int) -> Optional[float]:
    """Pooled two-proportion z statistic, or None when undefined.

    Undefined means an empty group or zero pooled variance (both groups 0 % or
    both 100 %): there is no evidence either way, and a fabricated `0.0` would
    read as "no difference".
    """
    if n1 <= 0 or n0 <= 0 or k1 < 0 or k0 < 0 or k1 > n1 or k0 > n0:
        return None
    pooled = (k1 + k0) / (n1 + n0)
    var = pooled * (1.0 - pooled) * (1.0 / n1 + 1.0 / n0)
    if var <= 0.0:
        return None
    return (k1 / n1 - k0 / n0) / math.sqrt(var)


def cosine_share(a: dict[str, int], b: dict[str, int]) -> Optional[float]:
    """Cosine of two pattern-share vectors (counts are normalised internally).

    Returns None when either half has no events at all. Note the limitation
    this number has by construction: with a handful of non-negative dimensions
    the cosine is close to 1 whenever the same patterns appear in both halves.
    It measures profile *shape*, not agreement of magnitudes — the per-pattern
    z-test is the discriminating check.
    """
    total_a = sum(a.values())
    total_b = sum(b.values())
    if total_a <= 0 or total_b <= 0:
        return None
    pids = sorted(set(a) | set(b))
    va = [a.get(p, 0) / total_a for p in pids]
    vb = [b.get(p, 0) / total_b for p in pids]
    norm_a = math.sqrt(sum(x * x for x in va))
    norm_b = math.sqrt(sum(x * x for x in vb))
    if norm_a == 0.0 or norm_b == 0.0:
        return None
    return sum(x * y for x, y in zip(va, vb)) / (norm_a * norm_b)


def dated_order(games: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """`(key, date)` pairs sorted oldest first; undated games are dropped.

    Accepts `YYYY-MM-DD` and `YYYY.MM.DD` (the cache uses dots); the returned
    date is normalised to `YYYY-MM-DD` so consumers see one format. Anything
    else is excluded rather than guessed.
    """
    dated = []
    for key, date in games:
        head = (date or "")[:10]
        if (
            len(head) == 10
            and head[:4].isdigit()
            and head[4] in "-."
            and head[7] in "-."
            and head[5:7].isdigit()
            and head[8:10].isdigit()
        ):
            dated.append((head.replace(".", "-"), key))
    dated.sort()
    return [(key, date) for date, key in dated]


def temporal_split(dated: list[tuple[str, str]]) -> dict:
    """Chronological halves: oldest 50 % vs newest 50 %.

    Returns the cut point and the group sizes. Empty halves are reported, never
    padded.
    """
    n = len(dated)
    mid = n // 2
    return {
        "n_dated": n,
        "n_old": mid,
        "n_new": n - mid,
        "cut_date": dated[mid][1] if mid < n else None,
    }


def build_stability(
    pattern_games: dict[str, list[str]],
    games: list[tuple[str, str]],
) -> dict:
    """Per-pattern stability + drift, plus the cohort split-half summary.

    `pattern_games` maps pattern id -> game keys in which the pattern occurred.
    `games` is `[(game_key, date_string)]` for every analysed game.

    Returns `{"split_half": {...}, "patterns": {pid: {...}}}`. The cohort
    `split_half` block is repeated inside every pattern entry so a single
    pattern record is self-contained for consumers.
    """
    seen: set[str] = set()
    unique_games: list[tuple[str, str]] = []
    for key, date in games:
        if key in seen:
            continue
        seen.add(key)
        unique_games.append((key, date))
    games = unique_games

    a_keys, b_keys = split_halves(key for key, _ in games)
    a_set, b_set = set(a_keys), set(b_keys)
    n_a, n_b = len(a_keys), len(b_keys)

    counts_a: dict[str, int] = {}
    counts_b: dict[str, int] = {}
    halves: dict[str, dict] = {}
    for pid, affected in pattern_games.items():
        aff = set(affected)
        k_a = len(aff & a_set)
        k_b = len(aff & b_set)
        counts_a[pid] = k_a
        counts_b[pid] = k_b
        halves[pid] = _z_block(k_a, n_a, k_b, n_b)

    cosine = cosine_share(counts_a, counts_b)
    split_half = {
        "method": "sha256_parity",
        "salt": SPLIT_SALT,
        "n_a": n_a,
        "n_b": n_b,
        "cosine": round(cosine, 4) if cosine is not None else None,
        "unavailable_reason": None
        if cosine is not None
        else "one half has no pattern events; profile cosine is undefined",
    }

    dated = dated_order(games)
    split = temporal_split(dated)
    old_keys = {key for key, _ in dated[: split["n_old"]]}
    new_keys = {key for key, _ in dated[split["n_old"] :]}

    per_pattern: dict[str, dict] = {}
    for pid, affected in pattern_games.items():
        aff = set(affected)
        drift = _drift_block(
            len(aff & old_keys),
            split["n_old"],
            len(aff & new_keys),
            split["n_new"],
            split["cut_date"],
            split["n_dated"],
        )
        half = halves[pid]
        if half["estimable"] or drift["estimable"]:
            unstable: Optional[bool] = bool(half["unstable"] or drift["flag"])
        else:
            unstable = None
        per_pattern[pid] = {
            "half": half,
            "split_half": split_half,
            "drift": drift,
            "unstable": unstable,
        }

    return {"split_half": split_half, "patterns": per_pattern}


def _z_block(k_a: int, n_a: int, k_b: int, n_b: int) -> dict:
    """One comparison of two rates (used for the hash split)."""
    estimable = n_a >= MIN_HALF_GAMES and n_b >= MIN_HALF_GAMES
    z = two_proportion_z(k_a, n_a, k_b, n_b)
    if not estimable:
        reason = f"needs >= {MIN_HALF_GAMES} games per half, got {n_a}/{n_b}"
    elif z is None:
        reason = "pooled variance is zero (no variation in either half)"
    else:
        reason = None
    testable = estimable and z is not None
    unstable = bool(abs(z) >= Z95) if testable and z is not None else None
    return {
        "rate_a": round(k_a / n_a, 4) if n_a else None,
        "rate_b": round(k_b / n_b, 4) if n_b else None,
        "delta": round(abs(k_a / n_a - k_b / n_b), 4) if n_a and n_b else None,
        "z": round(z, 3) if z is not None else None,
        "estimable": testable,
        "reason": reason,
        "unstable": unstable,
    }


def _drift_block(
    k_old: int,
    n_old: int,
    k_new: int,
    n_new: int,
    cut_date: Optional[str],
    n_dated: int,
) -> dict:
    """Temporal comparison of the older and newer halves."""
    estimable = n_old >= MIN_HALF_GAMES and n_new >= MIN_HALF_GAMES
    z = two_proportion_z(k_old, n_old, k_new, n_new)
    if not estimable:
        reason = f"needs >= {MIN_HALF_GAMES} dated games per era, got {n_old}/{n_new}"
    elif z is None:
        reason = "pooled variance is zero (no variation in either era)"
    else:
        reason = None
    testable = estimable and z is not None
    return {
        "method": "chronological_halves_z",
        "n_dated": n_dated,
        "n_old": n_old,
        "n_new": n_new,
        "cut_date": cut_date,
        "rate_old": round(k_old / n_old, 4) if n_old else None,
        "rate_new": round(k_new / n_new, 4) if n_new else None,
        "delta": round(abs(k_old / n_old - k_new / n_new), 4) if n_old and n_new else None,
        "z": round(z, 3) if z is not None else None,
        "estimable": testable,
        "reason": reason,
        "flag": bool(abs(z) >= Z95) if testable and z is not None else None,
    }
