"""Schema 2.0 compact serializer — unit tests (no engine, no network)."""

import json
import os

import pytest

from lichess_analyzer_mcp.services.compact_serializer import (
    MAX_REPORT_CHARS,
    compact_size,
    to_compact_v2,
    validate_compact,
)

ROOT = os.path.join(os.path.dirname(__file__), "..")

GAME_META = {
    "id": "lxO3gwd3",
    "platform": "lichess",
    "opening": "Ruy Lopez: Berlin Defense",
    "opening_eco": "C65",
    "color": "black",
    "result": "0-1",
    "time_control": "300+3",
    "date": "2026.11.08",
}

FLAG_TEMPLATE = {
    "ply": 34,
    "san": "Qg3",
    "uci": "g5g3",
    "classification": "inaccuracy",
    "cp_loss": 84.0,
    "eval_before": 409,
    "eval_after": 314,
    "win_prob_before": 0.91,
    "win_prob_after": 0.85,
    "phase": "middlegame",
    "best_move_san": "Qg6",
    "played_rank": 3,
    "engine_lines": [
        {"rank": 1, "san": "Qg6", "eval_cp": 397, "pv": ["Qg6", "Rf3", "Bxc3", "Bxc3", "cxd4"]},
        {"rank": 2, "san": "Bxc3", "eval_cp": 352, "pv": ["Bxc3", "fxg5"]},
    ],
    "motif": None,
    "check": False,
    "in_check_before": False,
    "explanation": "Hráno Qg3; motor preferuje Qg6.",
    "explanation_source": "deterministic",
}

FULL = {
    "schema_version": "1.1",
    "game_id": "lxO3gwd3",
    "username": "systeq",
    "color": "black",
    "mode": "fast",
    "depth": 14,
    "status": "degraded",
    "analysis": {
        "acpl": 18.2,
        "accuracy": 97.3,
        "moves_analyzed": 34,
        "moves_total": 34,
        "evaluation_errors": 0,
        "phase_stats": {
            "opening": {"acpl": 8.3, "move_count": 10, "flagged": 0},
            "middlegame": {"acpl": 24.5, "move_count": 15, "flagged": 3},
            "endgame": {"acpl": 18.6, "move_count": 9, "flagged": 1},
        },
    },
    "flagged_moves": [
        FLAG_TEMPLATE,
        {
            **FLAG_TEMPLATE,
            "ply": 40,
            "san": "Bxc5+",
            "cp_loss": 65.0,
            "best_move_san": "Nxe5",
            "played_rank": 2,
            "motif": "discovered_check_capture",
        },
        {
            **FLAG_TEMPLATE,
            "ply": 46,
            "san": "Rfe8",
            "cp_loss": 66.0,
            "best_move_san": "Rbe8",
            "played_rank": 2,
        },
        {
            **FLAG_TEMPLATE,
            "ply": 68,
            "san": "d3",
            "cp_loss": 120.0,
            "best_move_san": "f6",
            "played_rank": 4,
        },
    ],
    "patterns": [
        {
            "pattern_id": "T",
            "pattern_name": "Tactical oversight",
            "confidence": 0.16,
            "frequency": 1,
            "severity": "medium",
            "scope": "single_game",
            "evidence": [{"ply": 40, "san": "Bxc5+", "cp_loss": 65.0}],
        }
    ],
    "llm": {"status": "degraded", "provider": "deterministic", "reason": "all_providers_failed"},
    "report": "ACPL 18.2, accuracy 97.3 %. Čtyři nepřesnosti. Nejs slabší fáze: middlegame.",
}

MOVES = [
    {"ply": 34, "fen": "r1bq1rk1/ppp2ppp/2np4/8/2B1P3/2N2N2/PPP2PPP/R2Q1RK1 w - - 0 17"},
    {"ply": 40, "fen": "r1bq1rk1/pp3ppp/2np4/2b1P3/2B5/2N2N2/PPP2PPP/R2Q1RK1 w - - 0 20"},
    {"ply": 46, "fen": "r2q1rk1/pp3ppp/2np4/2b1P3/2B5/2N2N2/PPP2PPP/R2Q1RK1 w - - 0 23"},
    {"ply": 68, "fen": "1r2r1k1/p4ppp/2pq4/8/N2p2P1/1P2bR2/PB4K1/8 b - - 0 34"},
]


def _compact():
    return to_compact_v2(FULL, game_meta=GAME_META, moves=MOVES)


def test_output_validates_against_manual_validator():
    validate_compact(_compact())


def test_output_validates_against_json_schema_file():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.load(
        open(os.path.join(ROOT, "schemas/single_game_v2_compact.json"), encoding="utf-8")
    )
    jsonschema.validate(_compact(), schema)


def test_metadata_and_summary():
    out = _compact()
    assert out["v"] == "2.0"
    assert out["game"] == {
        "id": "lxO3gwd3",
        "username": "systeq",
        "color": "black",
        "result": "0-1",
        "opening": "C65 Ruy Lopez: Berlin Defense",
        "depth": 14,
        "tc": "300+3",
        "date": "2026-11-08",
    }
    assert out["summary"]["acpl"] == 18.2
    assert out["summary"]["acc"] == 97.3
    assert out["summary"]["phases"] == {
        "opening": [8.3, 0],
        "middlegame": [24.5, 3],
        "endgame": [18.6, 1],
    }


def test_anonymous_game_has_no_username():
    full = json.loads(json.dumps(FULL))
    full["username"] = ""
    meta = dict(GAME_META)
    meta["player_name"] = "Anonymous"
    out = to_compact_v2(full, game_meta=meta)
    validate_compact(out)
    assert "username" not in out["game"]


def test_unknown_pgn_date_is_omitted():
    full = json.loads(json.dumps(FULL))
    meta = dict(GAME_META)
    meta["date"] = "????.??.??"
    out = to_compact_v2(full, game_meta=meta)
    validate_compact(out)
    assert "date" not in out["game"]


def test_all_flags_preserved_in_ply_order():
    out = _compact()
    assert [f["ply"] for f in out["flags"]] == [34, 40, 46, 68]
    by_ply = {f["ply"]: f for f in out["flags"]}
    assert by_ply[34] == {
        "ply": 34,
        "move": "Qg3",
        "class": "inaccuracy",
        "cp": 84,
        "best": "Qg6",
        "rank": 3,
    }
    assert by_ply[40]["motif"] == "discovered_check_capture"
    assert "motif" not in by_ply[46]  # R8: no null noise
    assert by_ply[68]["cp"] == 120


def test_pv_capped_at_three_moves():
    out = _compact()
    assert out["pv"]["34"] == ["Qg6", "Rf3", "Bxc3"]
    assert all(1 <= len(line) <= 3 for line in out["pv"].values())


def test_fen_only_above_100cp():
    out = _compact()
    assert set(out["fen_before"]) == {"68"}
    assert out["fen_before"]["68"].endswith("b - - 0 34")


def test_patterns_preserved():
    out = _compact()
    assert out["patterns"] == [{"id": "T", "conf": 0.16, "freq": 1, "sev": "medium", "plie": [40]}]


def test_patterns_per_flag_and_error_cluster():
    full = json.loads(json.dumps(FULL))
    for ply, cp, cls in ((87, 186.0, "mistake"), (89, 237.0, "mistake"), (91, 59.0, "inaccuracy")):
        full["flagged_moves"].append(
            {
                **FLAG_TEMPLATE,
                "ply": ply,
                "san": f"M{ply}",
                "classification": cls,
                "cp_loss": cp,
                "engine_lines": [],
                "played_rank": None,
            }
        )
    out = to_compact_v2(full, game_meta=GAME_META)
    validate_compact(out)
    assert out["clusters"] == [{"from": 87, "to": 91, "count": 3, "total_cp": 482}]
    by_ply = {f["ply"]: f for f in out["flags"]}
    # CAND-E: the flag itself says which behavioural patterns it feeds.
    assert by_ply[40]["patterns"] == ["T"]
    assert "patterns" not in by_ply[34]


def test_eval_fields_follow_fix015_window():
    full = json.loads(json.dumps(FULL))
    full["flagged_moves"].append(
        {
            **FLAG_TEMPLATE,
            "ply": 75,
            "san": "Re8+",
            "classification": "blunder",
            "cp_loss": 9473.0,
            "eval_before": 9997,
            "eval_after": 525,
            "engine_lines": [],
            "played_rank": None,
        }
    )
    full["flagged_moves"].append(
        {
            **FLAG_TEMPLATE,
            "ply": 91,
            "san": "Qc4+",
            "classification": "inaccuracy",
            "cp_loss": 250.0,
            "eval_before": 727,
            "eval_after": 477,
        }
    )
    out = to_compact_v2(full, game_meta=GAME_META, pv_unavailable={75: "engine_timeout"})
    validate_compact(out)
    by_ply = {f["ply"]: f for f in out["flags"]}
    assert by_ply[75]["eval_before"] == 9997
    assert by_ply[75]["eval_after"] == 525
    assert by_ply[91]["eval_before"] == 727  # cp > 200, inaccuracy still counts
    assert "eval_before" not in by_ply[34]  # inaccuracy at 84 cp


def test_blunder_pv_fallback():
    full = json.loads(json.dumps(FULL))
    full["flagged_moves"].append(
        {
            **FLAG_TEMPLATE,
            "ply": 75,
            "san": "Re8+",
            "classification": "blunder",
            "cp_loss": 9473.0,
            "engine_lines": [],
            "played_rank": None,
            "motif": "check",
        }
    )
    out = to_compact_v2(full, game_meta=GAME_META, pv_unavailable={75: "engine_timeout"})
    validate_compact(out)
    assert out["pv_unavailable"] == {"75": "engine_timeout"}
    assert "75" not in out.get("pv", {})
    # Without an explicit reason the serializer still refuses to be silent.
    derived = to_compact_v2(full, game_meta=GAME_META)
    assert derived["pv_unavailable"]["75"] == "engine_lines_empty"


def test_null_policy_consistent():
    out = _compact()
    by_ply = {f["ply"]: f for f in out["flags"]}
    assert by_ply[34]["rank"] == 3
    assert "motif" not in by_ply[34]  # no tactical motif -> key absent
    assert by_ply[40]["motif"] == "discovered_check_capture"
    full = json.loads(json.dumps(FULL))
    for flag in full["flagged_moves"]:
        flag["played_rank"] = 0
    unmeasured = to_compact_v2(full, game_meta=GAME_META)
    validate_compact(unmeasured)
    assert all(flag["rank"] is None for flag in unmeasured["flags"])
    # Only the flag that genuinely has a motif keeps it; the rest omit the key.
    assert [flag["ply"] for flag in unmeasured["flags"] if "motif" in flag] == [40]


def test_llm_deterministic_is_reported_as_failed():
    assert _compact()["llm"] == {
        "status": "failed",
        "provider": "deterministic",
        "reason": "all_providers_failed",
    }


def test_no_derived_or_instrumentation_fields():
    dumped = json.dumps(_compact(), ensure_ascii=False)
    for needle in (
        "win_prob",
        "explanation",
        "in_check_before",
        "timings",
        "cascade_log",
        "nodes_cap",
        "legal_moves",
        "pattern_matches",
    ):
        assert needle not in dumped


def test_compact_size_under_budget():
    assert compact_size(_compact()) <= 2500


def test_report_clipped_at_sentence_boundary():
    full = {**FULL, "report": ("Veta jedna. " * 200)}
    out = to_compact_v2(full, game_meta=GAME_META)
    assert len(out["report"]) <= MAX_REPORT_CHARS
    assert out["report"].rstrip().endswith(".")


def test_report_omitted_when_no_safe_boundary():
    full = {**FULL, "report": "x" * (MAX_REPORT_CHARS + 50)}
    out = to_compact_v2(full, game_meta=GAME_META)
    assert "report" not in out


def test_unmeasured_values_are_null_not_guessed():
    full = json.loads(json.dumps(FULL))
    full["analysis"]["acpl"] = None
    full["analysis"]["accuracy"] = None
    full["analysis"]["phase_stats"] = {}
    full["flagged_moves"][0]["played_rank"] = 0
    out = to_compact_v2(full, game_meta=GAME_META)
    assert out["summary"]["acpl"] is None
    assert out["summary"]["phases"] == {
        "opening": [None, 0],
        "middlegame": [None, 0],
        "endgame": [None, 0],
    }
    assert out["flags"][0]["rank"] is None
    validate_compact(out)


def test_missing_game_meta_does_not_crash():
    out = to_compact_v2(FULL)
    validate_compact(out)
    assert out["game"]["result"] == "*"
    assert out["game"]["opening"] == ""


def test_validator_rejects_broken_shape():
    out = _compact()
    out["flags"][0]["class"] = "blunder!!"
    with pytest.raises(ValueError):
        validate_compact(out)
