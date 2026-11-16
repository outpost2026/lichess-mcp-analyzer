"""Audit real single-game tool outputs for consistency and LLM fitness.

Read-only: validates both contract surfaces, checks cross-surface invariants,
and reports redundant/ambiguous fields. Usage:

    python -X utf8 scripts/audit_single_game_output.py data/reports/audit_mcp_*.json
"""

from __future__ import annotations

import json
import os
import sys

import jsonschema

ROOT = os.path.join(os.path.dirname(__file__), "..")
SCHEMAS = {
    "compact": os.path.join(ROOT, "schemas/single_game_v2_compact_2.4.json"),
    "detailed": os.path.join(ROOT, "schemas/single_game_v1.2.json"),
}
MATE_IMPACTS = ("winning_to_mate", "equal_to_mate", "losing_to_mate")


def _load(path: str) -> tuple[dict | None, str | None]:
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle), None
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)


def audit(path: str, schemas: dict) -> dict:
    payload, error = _load(path)
    if error:
        return {"file": path, "error": error}
    result: dict = {"file": os.path.basename(path), "checks": {}, "findings": []}
    compact, detailed = payload.get("compact"), payload.get("detailed")
    if not compact or not detailed:
        result["error"] = "payload has no compact/detailed pair"
        return result

    for name, surface in (("compact", compact), ("detailed", detailed)):
        try:
            jsonschema.validate(surface, schemas[name])
            result["checks"][f"schema_{name}"] = "PASS"
        except jsonschema.ValidationError as exc:
            result["checks"][f"schema_{name}"] = f"FAIL: {exc.message[:120]}"
    result["size_bytes"] = {
        "compact": len(json.dumps(compact, ensure_ascii=False).encode("utf-8")),
        "detailed": len(json.dumps(detailed, ensure_ascii=False).encode("utf-8")),
    }

    cg, dg = compact["game"], detailed["game"]
    # Detailed 1.2 keeps colour/depth at the top level; compact 2.3 puts them
    # in `game`. Only shared, identically formatted keys are compared.
    same_game = cg.get("id") == dg.get("id") and cg.get("result") == dg.get("result")
    result["checks"]["same_game_identity"] = "PASS" if same_game else "FAIL"
    result["checks"]["color_is_contract"] = (
        "PASS"
        if cg["color"] == detailed["color"] and detailed["color"] in ("white", "black")
        else "FAIL"
    )
    result["checks"]["depth_mirror"] = "PASS" if cg["depth"] == detailed["depth"] else "FAIL"

    flags, moves = compact["flags"], detailed["flagged_moves"]
    cov = compact["patterns_meta"]["coverage"]
    result["checks"]["coverage_flagged"] = (
        "PASS" if cov["flagged"] == len(flags) == len(moves) else "FAIL"
    )
    result["counts"] = {
        "flags": len(flags),
        "patterns": len(compact["patterns"]),
        "clusters": len(compact.get("clusters") or []),
        "unclassified": len(compact.get("unclassified") or []),
        "report_chars": len(detailed.get("report") or ""),
    }
    result["checks"]["confidence_dims_count"] = (
        "PASS"
        if compact["confidence_dims"]["n_patterns"]
        == len(compact["patterns"])
        == detailed["analysis"]["confidence_dimensions"]["n_patterns"]
        else "FAIL"
    )
    result["checks"]["acc_warning_mirror"] = (
        "PASS"
        if compact["summary"].get("acc_warning") == detailed["analysis"].get("accuracy_warning")
        else "FAIL"
    )
    result["checks"]["report_present_both"] = (
        "PASS" if isinstance(compact.get("report"), str) and detailed.get("report") else "MISSING"
    )
    result["checks"]["cache_hit_mirror"] = (
        "PASS" if detailed["cache"]["hit"] == detailed["timings"]["cache_hit"] else "FAIL"
    )

    mate_without_direction = [
        f["ply"] for f in flags if f["game_impact"] in MATE_IMPACTS and f.get("mate_after") is None
    ]
    if mate_without_direction:
        result["findings"].append(
            {
                "id": "F1_mate_direction_absent_in_compact",
                "severity": "high",
                "detail": f"plies {mate_without_direction} have *_to_mate but no mate_after",
            }
        )
    result["checks"]["pipeline_mirror"] = (
        "PASS" if compact["pipeline"] == detailed["pipeline"] else "FAIL"
    )
    result["checks"]["offline_not_failed"] = (
        "PASS"
        if compact["pipeline"]["llm_requested"]
        or compact["pipeline"]["coaching"] == "deterministic_fallback"
        else "FAIL"
    )

    alias_pairs = 0
    for flag in moves:
        if flag.get("eval_before") == flag.get("eval_before_mover_cp"):
            alias_pairs += 1
        if flag.get("eval_after") == flag.get("eval_after_mover_cp"):
            alias_pairs += 1
    result["findings"].append(
        {
            "id": "F2_alias_pairs",
            "severity": "info",
            "detail": f"{alias_pairs} duplicated eval alias values in detailed flags (D9, required)",
        }
    )
    if detailed.get("report") != compact.get("report"):
        result["findings"].append(
            {
                "id": "F3_report_rewritten_in_compact",
                "severity": "info",
                "detail": "compact report is clipped/rephrased, not a prefix of detailed report",
            }
        )
    if detailed.get("cascade_log"):
        result["findings"].append(
            {
                "id": "F4_cascade_log_duplicate",
                "severity": "info",
                "detail": f"{len(detailed['cascade_log'])} raw cascade entries derived again in llm.attempts",
            }
        )
    if (
        "flags" in detailed
        and isinstance(detailed["flags"], dict)
        and isinstance(compact["flags"], list)
    ):
        result["findings"].append(
            {
                "id": "F5_flags_name_collision",
                "severity": "medium",
                "detail": "detailed.flags = config object, compact.flags = flagged-move array",
            }
        )
    detail_status = detailed["status"]
    llm_status = detailed["llm"]["status"]
    source = detailed["report_meta"]["source"]
    result["checks"]["status_triad"] = f"{detail_status}/{llm_status}/{source}"
    return result


def main() -> int:
    paths = [p for p in sys.argv[1:] if os.path.isfile(p)]
    if not paths:
        print("no input files", file=sys.stderr)
        return 2
    schemas = {name: json.load(open(path, encoding="utf-8")) for name, path in SCHEMAS.items()}
    results = []
    for path in paths:
        try:
            results.append(audit(path, schemas))
        except (KeyError, TypeError, ValueError) as exc:
            results.append(
                {"file": os.path.basename(path), "error": f"{type(exc).__name__}: {exc}"}
            )
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
