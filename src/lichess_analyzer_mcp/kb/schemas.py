"""JSON schema definitions for KB pattern artifact output.

Maps to KALIBRACE_PLAN v2.3 task K6.1.
Ensures machine-readable, structurally consistent artifact output.
"""

PATTERN_SCHEMA = {
    "type": "object",
    "required": ["username", "games_analyzed", "patterns_detected"],
    "properties": {
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
                    "frequency": {"type": "integer", "minimum": 1},
                    "severity": {"enum": ["low", "medium", "high", "critical"]},
                    "hypothesis": {"type": "string", "pattern": "^(Hypothesis:|)"},
                    "compression_ratio": {"type": "number", "minimum": 0},
                },
            },
        },
        "total_patterns": {"type": "integer", "minimum": 0},
    },
}


def validate_against_schema(artifact: dict) -> list[str]:
    errors = []
    for req in PATTERN_SCHEMA["required"]:
        if req not in artifact:
            errors.append(f"missing required field: {req}")
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
    return errors
