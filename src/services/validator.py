"""Post-analysis sanity validator for pattern artifacts.

Checks for inconsistent, missing, or anomalous data before output.
Maps to KALIBRACE_PLAN v2.3 task K7.1.
"""

import math
from typing import Any

VALID_SEVERITIES = {"low", "medium", "high", "critical"}


class ValidationError(Exception):
    pass


def validate_pattern_artifact(artifact: dict) -> list[str]:
    issues = []
    if not artifact.get("username"):
        issues.append("missing username")
    games = artifact.get("games_analyzed", 0)
    if games < 1:
        issues.append("games_analyzed must be >= 1")
    patterns = artifact.get("patterns_detected", [])
    if not isinstance(patterns, list):
        issues.append("patterns_detected must be a list")
    else:
        seen_ids = {}
        for i, p in enumerate(patterns):
            pid = p.get("pattern_id", "")
            if not pid:
                issues.append(f"pattern[{i}] missing pattern_id")
            if pid in seen_ids:
                issues.append(f"duplicate pattern_id {pid} at index {i} and {seen_ids[pid]}")
            seen_ids[pid] = i
            conf = p.get("confidence", 0)
            if not isinstance(conf, (int, float)) or conf < 0 or conf > 100:
                issues.append(f"pattern[{i}] confidence {conf} out of range 0-100")
            sev = p.get("severity", "")
            if sev not in VALID_SEVERITIES:
                issues.append(f"pattern[{i}] severity '{sev}' not in {VALID_SEVERITIES}")
            freq = p.get("frequency", 0)
            if not isinstance(freq, int) or freq < 1:
                issues.append(f"pattern[{i}] frequency must be >= 1")
            hyp = p.get("hypothesis", "")
            if hyp and not hyp.startswith("Hypothesis:"):
                issues.append(f"pattern[{i}] hypothesis must start with 'Hypothesis:'")
    return issues


def assert_valid_artifact(artifact: dict) -> None:
    issues = validate_pattern_artifact(artifact)
    if issues:
        raise ValidationError(" | ".join(issues))
