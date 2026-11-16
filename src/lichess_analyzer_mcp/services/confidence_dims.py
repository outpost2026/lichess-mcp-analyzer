"""P0-4: the three confidence dimensions of a detected pattern.

`confidence` used to be read as if it meant one thing. It does not:

  - `detection_strength` - ordinal strength of the detector rule (0..1).
    This is what `strength` / `confidence` / compact `conf` actually carry.
  - `evidence_support` - measured share of flagged moves in this game that
    the pattern covers. It has a denominator (`flagged_moves_in_game`) and is
    null when there is no measured move to divide by.
  - `behavioral_confidence` - calibrated confidence in the *mechanism*. There
    is no calibration in this codebase yet (Phase 3), so it is null with an
    explicit reason, never a guess and never copied from strength.

`confidence_kind` names which dimension the legacy `confidence` alias maps to,
so an LLM cannot silently read an ordinal detector weight as a probability.

The module is pure; both the detailed response and compact 2.3 consume the
same vocabulary and the same support arithmetic.
"""

from __future__ import annotations

CONFIDENCE_KINDS = ("detection_strength", "evidence_support", "behavioral_confidence")
CONFIDENCE_KIND_DETECTION = "detection_strength"
BEHAVIORAL_REASON_NOT_CALIBRATED = "not_calibrated"
SUPPORT_BASIS_SINGLE_GAME = "flagged_moves_in_game"


def support_share(frequency, n_units) -> float | None:
    """Measured coverage share; null when the denominator is unavailable."""
    if not isinstance(frequency, int) or isinstance(frequency, bool) or frequency < 0:
        return None
    if not isinstance(n_units, int) or isinstance(n_units, bool) or n_units < 1:
        return None
    return round(min(frequency / n_units, 1.0), 3)


def detailed_dims(strength, frequency, n_units) -> dict:
    """Additive per-pattern block for contract 1.2."""
    return {
        "detection_strength": strength,
        "evidence_support": support_share(frequency, n_units),
        "evidence_support_basis": SUPPORT_BASIS_SINGLE_GAME,
        "evidence_support_n_units": n_units,
        "behavioral_confidence": None,
        "behavioral_confidence_reason": BEHAVIORAL_REASON_NOT_CALIBRATED,
        "confidence_kind": CONFIDENCE_KIND_DETECTION,
    }


def dimensions_block(n_patterns: int) -> dict:
    """One payload-level explanation instead of repeating prose per pattern."""
    return {
        "kinds": list(CONFIDENCE_KINDS),
        "published_kind": CONFIDENCE_KIND_DETECTION,
        "support_basis": SUPPORT_BASIS_SINGLE_GAME,
        "behavioral_confidence": None,
        "behavioral_confidence_reason": BEHAVIORAL_REASON_NOT_CALIBRATED,
        "n_patterns": int(n_patterns),
    }
