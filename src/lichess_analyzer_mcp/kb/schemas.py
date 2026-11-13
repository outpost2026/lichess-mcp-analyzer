"""JSON schema definitions for KB pattern artifact output.

Maps to KALIBRACE_PLAN v2.3 task K6.1 and schema 1.4 (P1 uncertainty + P2
stability). Ensures machine-readable, structurally consistent artifact output.

Schema 1.3 adds, per pattern: `n_games`, `n_units`, `rate` + Wilson `rate_ci`,
and `lift` + Katz `lift_ci` where a real contrast group exists. `confidence`
stays as a legacy alias of the ordinal `strength` (0-100), never a probability.

Schema 1.4 adds `stability`: split-half rates + two-proportion z, temporal
drift on chronological halves, and the resulting `unstable` flag. `unstable`
is a flag to investigate, not a verdict.
"""

PATTERN_SCHEMA = {
    "type": "object",
    "required": ["username", "games_analyzed", "patterns_detected"],
    "properties": {
        "schema_version": {"enum": ["1.4"]},
        "username": {"type": "string", "minLength": 1},
        "games_analyzed": {"type": "integer", "minimum": 1},
        "patterns_detected": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["pattern_id", "pattern_name", "confidence", "frequency", "severity"],
                "properties": {
                    "pattern_id": {"type": "string", "pattern": "^[A-Z][0-9]?$"},
                    "pattern_name": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 100},
                    "strength": {"type": "number", "minimum": 0, "maximum": 100},
                    "support": {"type": "number", "minimum": 0, "maximum": 1},
                    "frequency": {"type": "integer", "minimum": 1},
                    "severity": {"enum": ["low", "medium", "high", "critical"]},
                    "hypothesis": {"type": "string", "pattern": "^(Hypothesis:|)"},
                    "compression_ratio": {"type": "number", "minimum": 0},
                    "coverage_score": {"type": "number", "minimum": 0, "maximum": 1},
                    "hypothesis_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "n_games": {"type": "integer", "minimum": 0},
                    "n_units": {"type": "integer", "minimum": 0},
                    "rate": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
                    "rate_ci": {
                        "type": "object",
                        "required": ["low", "high"],
                        "properties": {
                            "low": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
                            "high": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
                        },
                    },
                    "lift": {"type": ["number", "null"], "minimum": 0},
                    "lift_ci": {
                        "type": "object",
                        "required": ["low", "high"],
                        "properties": {
                            "low": {"type": ["number", "null"], "minimum": 0},
                            "high": {"type": ["number", "null"], "minimum": 0},
                        },
                    },
                    "lift_basis": {"type": "string"},
                    "lift_unavailable_reason": {"type": "string"},
                    "stability": {
                        "type": "object",
                        "required": ["half", "split_half", "drift", "unstable"],
                        "properties": {
                            "half": {
                                "type": "object",
                                "required": ["estimable", "unstable"],
                                "properties": {
                                    "rate_a": {"type": ["number", "null"]},
                                    "rate_b": {"type": ["number", "null"]},
                                    "delta": {"type": ["number", "null"]},
                                    "z": {"type": ["number", "null"]},
                                    "estimable": {"type": "boolean"},
                                    "reason": {"type": ["string", "null"]},
                                    "unstable": {"type": ["boolean", "null"]},
                                },
                            },
                            "split_half": {
                                "type": "object",
                                "required": ["method", "n_a", "n_b", "cosine"],
                                "properties": {
                                    "method": {"type": "string"},
                                    "salt": {"type": "string"},
                                    "n_a": {"type": "integer", "minimum": 0},
                                    "n_b": {"type": "integer", "minimum": 0},
                                    "cosine": {"type": ["number", "null"]},
                                    "unavailable_reason": {"type": "string"},
                                },
                            },
                            "drift": {
                                "type": "object",
                                "required": ["estimable", "flag"],
                                "properties": {
                                    "method": {"type": "string"},
                                    "estimable": {"type": "boolean"},
                                    "flag": {"type": ["boolean", "null"]},
                                    "reason": {"type": ["string", "null"]},
                                    "n_dated": {"type": "integer", "minimum": 0},
                                    "n_old": {"type": "integer", "minimum": 0},
                                    "n_new": {"type": "integer", "minimum": 0},
                                    "cut_date": {"type": ["string", "null"]},
                                    "rate_old": {"type": ["number", "null"]},
                                    "rate_new": {"type": ["number", "null"]},
                                    "delta": {"type": ["number", "null"]},
                                    "z": {"type": ["number", "null"]},
                                },
                            },
                            "unstable": {"type": ["boolean", "null"]},
                        },
                    },
                },
            },
        },
        "total_patterns": {"type": "integer", "minimum": 0},
    },
}


def _check_ci(
    errors: list[str], index: int, field: str, point, ci: dict, upper: float | None = None
) -> None:
    """Point estimate must lie inside its own interval (or both are None)."""
    if not isinstance(ci, dict):
        errors.append(f"patterns[{index}].{field}_ci must be an object")
        return
    low, high = ci.get("low"), ci.get("high")
    if point is None:
        if low is not None or high is not None:
            errors.append(f"patterns[{index}].{field}_ci must be null when {field} is null")
        return
    if not isinstance(point, (int, float)):
        errors.append(f"patterns[{index}].{field} must be a number or null")
        return
    if low is None or high is None:
        errors.append(f"patterns[{index}].{field}_ci missing bounds for non-null {field}")
        return
    if not low <= point <= high:
        errors.append(f"patterns[{index}].{field} {point} outside its CI [{low}, {high}]")
    if upper is not None and high > upper:
        errors.append(f"patterns[{index}].{field}_ci.high {high} exceeds {upper}")


def validate_against_schema(artifact: dict) -> list[str]:
    errors = []
    for req in PATTERN_SCHEMA["required"]:
        if req not in artifact:
            errors.append(f"missing required field: {req}")
    version = artifact.get("schema_version")
    if version is not None and version != "1.4":
        errors.append(f"schema_version '{version}' not supported (expected 1.4)")
    username = artifact.get("username", "")
    if not isinstance(username, str) or len(username) < 1:
        errors.append("username must be non-empty string")
    games = artifact.get("games_analyzed", 0)
    if not isinstance(games, int) or games < 1:
        errors.append("games_analyzed must be int >= 1")
    patterns = artifact.get("patterns_detected", [])
    if not isinstance(patterns, list):
        errors.append("patterns_detected must be list")
    else:
        for i, p in enumerate(patterns):
            for req_field in ["pattern_id", "pattern_name", "confidence", "frequency", "severity"]:
                if req_field not in p:
                    errors.append(f"patterns[{i}] missing {req_field}")
            pid = p.get("pattern_id", "")
            if not isinstance(pid, str) or not pid:
                errors.append(f"patterns[{i}] pattern_id invalid")
            conf = p.get("confidence", 0)
            if not isinstance(conf, (int, float)) or conf < 0 or conf > 100:
                errors.append(f"patterns[{i}] confidence {conf} out of range")
            sev = p.get("severity", "")
            if sev not in ("low", "medium", "high", "critical"):
                errors.append(f"patterns[{i}] severity '{sev}' invalid")
            hyp = p.get("hypothesis", "")
            if hyp and not hyp.startswith("Hypothesis:"):
                errors.append(f"patterns[{i}] hypothesis must start with 'Hypothesis:'")

            # ── schema 1.3 uncertainty invariants ──
            n_games, n_units = p.get("n_games"), p.get("n_units")
            if isinstance(n_games, int) and isinstance(n_units, int) and n_games > n_units:
                errors.append(f"patterns[{i}].n_games {n_games} exceeds n_units {n_units}")
            if "rate" in p:
                _check_ci(errors, i, "rate", p.get("rate"), p.get("rate_ci"), upper=1.0)
            if "lift" in p:
                _check_ci(errors, i, "lift", p.get("lift"), p.get("lift_ci"))
            if "lift" in p and p.get("lift") is None and not p.get("lift_unavailable_reason"):
                errors.append(f"patterns[{i}] has no lift and no lift_unavailable_reason")

            # ── schema 1.4 stability invariants ──
            _check_stability(errors, i, p.get("stability"))
    return errors


def _check_stability(errors: list[str], index: int, stab) -> None:
    """A pattern cannot be called stable while one of its sub-tests is unstable."""
    if stab is None:
        return
    if not isinstance(stab, dict):
        errors.append(f"patterns[{index}].stability must be an object")
        return
    for key in ("half", "split_half", "drift", "unstable"):
        if key not in stab:
            errors.append(f"patterns[{index}].stability missing {key}")
    raw_half = stab.get("half")
    raw_drift = stab.get("drift")
    half = raw_half if isinstance(raw_half, dict) else {}
    drift = raw_drift if isinstance(raw_drift, dict) else {}
    unstable = stab.get("unstable")

    if unstable is not None and not isinstance(unstable, bool):
        errors.append(f"patterns[{index}].stability.unstable must be bool or null")
    for side in ("rate_a", "rate_b"):
        value = half.get(side)
        if value is not None and not (isinstance(value, (int, float)) and 0.0 <= value <= 1.0):
            errors.append(f"patterns[{index}].stability.half.{side} out of [0, 1]")
    if drift.get("estimable") is False and drift.get("flag") is not None:
        errors.append(
            f"patterns[{index}].stability.drift.flag must be null when drift is not estimable"
        )
    sub_flags = [half.get("unstable"), drift.get("flag")]
    if unstable is False and any(flag is True for flag in sub_flags):
        errors.append(
            f"patterns[{index}].stability.unstable=false contradicts an unstable sub-test"
        )
    if unstable is True and not (half.get("estimable") or drift.get("estimable")):
        errors.append(f"patterns[{index}].stability.unstable=true requires an estimable sub-test")
