"""Schema 2.5 compact serializer - unit tests (no engine, no network)."""

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
    "pattern_status": "unclassified",
    "unclassified_reason": "quiet_positional",
}

FULL = {
    "schema_version": "1.2",
    "game_id": "lxO3gwd3",
    "username": "systeq",
    "color": "black",
    "mode": "fast",
    "depth": 14,
    "status": "degraded",
    "analysis": {
        "acpl": 18.2,
        "accuracy": 97.3,
        "accuracy_method": "internal_cp_linear",
        "internal_accuracy_score": 97.3,
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
            "pattern_status": "matched",
            "unclassified_reason": None,
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
            "pattern_name": "tactical_shaped_move_error",
            "confidence": 0.16,
            "frequency": 1,
            "severity": "medium",
            "scope": "single_game",
            "evidence": [{"ply": 40, "san": "Bxc5+", "cp_loss": 65.0}],
        }
    ],
    "patterns_meta": {
        "scope": "single_game",
        "cross_game_suppressed": True,
        "reason": "Single-game scope: only per-move evidence is aggregated. "
        "Cross-game detectors need >=3 games and are suppressed.",
        "detector_version": "DBCL-20261111-dev",
        "coverage": {"flagged": 4, "matched": 1, "unclassified": 3},
    },
    "unclassified": [
        {
            "ply": 34,
            "san": "Qg3",
            "class": "inaccuracy",
            "cp_loss": 84.0,
            "reason": "quiet_positional",
        },
        {
            "ply": 46,
            "san": "Rfe8",
            "class": "inaccuracy",
            "cp_loss": 66.0,
            "reason": "quiet_positional",
        },
        {
            "ply": 68,
            "san": "d3",
            "class": "inaccuracy",
            "cp_loss": 120.0,
            "reason": "quiet_positional",
        },
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


def test_v28_honesty_fields_present():
    """2.8: precision is honest null, pv_coverage is measured per pattern."""
    out = _compact()
    assert out["v"] == "2.8"
    assert out["precision"] == {
        "opening": None,
        "middlegame": None,
        "endgame": None,
        "basis": "not_calibrated",
    }
    assert isinstance(out["decisive_moves"], list)
    assert all("pv_coverage" in pattern for pattern in out["patterns"])


def test_decisive_moves_rank_by_impact_then_cp():
    from lichess_analyzer_mcp.services.compact_serializer import _decisive_moves

    flags = [
        {"ply": 77, "move": "Bxh2", "cp": 478, "game_impact": "winning_to_winning"},
        {"ply": 79, "move": "Rf4", "cp": 599, "game_impact": "winning_to_losing"},
        {"ply": 85, "move": "Kh1", "cp": 71, "game_impact": "equal_to_losing"},
    ]
    got = _decisive_moves(flags)
    assert [row["ply"] for row in got] == [79, 85]
    assert got[0]["move"] == "Rf4" and got[0]["cp"] == 599


def test_output_validates_against_manual_validator():
    validate_compact(_compact())


def test_output_validates_against_json_schema_file():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.load(
        open(os.path.join(ROOT, "schemas/single_game_v2_compact_2.8.json"), encoding="utf-8")
    )
    jsonschema.validate(_compact(), schema)


def test_metadata_and_summary():
    out = _compact()
    assert out["v"] == "2.8"
    assert out["phase_method"] == "ply_segment"
    assert out["patterns_meta"] == {
        "scope": "single_game",
        "cross_game_suppressed": True,
        "reason": "Single-game scope: only per-move evidence is aggregated. "
        "Cross-game detectors need >=3 games and are suppressed.",
        "detector_version": "DBCL-20261111-dev",
        "coverage": {"flagged": 4, "matched": 1, "unclassified": 3},
    }
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
    assert out["summary"]["acc_method"] == "internal_cp_linear"
    assert out["summary"]["phases"] == {
        "opening": [8.3, 0],
        "middlegame": [24.5, 3],
        "endgame": [18.6, 1],
    }


def test_acc_method_omitted_when_producer_does_not_declare_it():
    full = json.loads(json.dumps(FULL))
    full["analysis"].pop("accuracy_method")
    out = to_compact_v2(full, game_meta=GAME_META, moves=MOVES)
    # Older 1.2 payload: the serializer must not invent a method name.
    assert "acc_method" not in out["summary"]
    validate_compact(out)


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
        "pstatus": "unclassified",
        "why": "quiet_positional",
        "game_impact": "winning_to_winning",
        "mate_after": None,
        "bcp": None,
    }
    assert by_ply[40]["pstatus"] == "matched"
    assert "why" not in by_ply[40]
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
    assert out["patterns"] == [
        {
            "id": "T",
            "nm": "tactical_shaped_error",
            "mit": "Over dopad taktického tahu",
            "conf": 0.16,
            "freq": 1,
            "sev": "medium",
            "plie": [40],
            "support": None,
            "pv_coverage": 1.0,
        }
    ]
    assert out["confidence_dims"]["published_kind"] == "detection_strength"
    assert out["confidence_dims"]["behavioral_confidence"] is None


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
    assert out["clusters"] == [
        {"from": 87, "to": 91, "count": 3, "total_cp": 482, "plies": [87, 89, 91]}
    ]
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
            "best_eval": 9998,
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
            "best_eval": 727,
        }
    )
    out = to_compact_v2(full, game_meta=GAME_META, pv_unavailable={75: "engine_timeout"})
    validate_compact(out)
    by_ply = {f["ply"]: f for f in out["flags"]}
    assert by_ply[75]["bcp"] == 9998
    assert by_ply[75]["eval_after_mover_cp"] == 525
    assert by_ply[91]["bcp"] == 727  # cp > 200
    assert by_ply[34]["bcp"] is None  # inaccuracy at 84 cp, anchor not measured


def test_eval_fields_carry_mover_pov_names():
    """2.6/C-1: the anchor `bcp` replaces the non-anchor before-eval."""
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
            "best_eval": 9998,
            "engine_lines": [],
            "played_rank": None,
        }
    )
    out = to_compact_v2(full, game_meta=GAME_META)
    flag = next(f for f in out["flags"] if f["ply"] == 75)
    assert flag["bcp"] == 9998
    assert flag["eval_after_mover_cp"] == 525
    assert "eval_before_mover_cp" not in flag
    assert "eval_before" not in flag and "eval_after" not in flag
    validate_compact(out)


def test_summary_src_and_rank_unknown():
    """2.7 wave 1: exact engine policy in summary, explicit unknown rank."""
    full = json.loads(json.dumps(FULL))
    full["analysis"]["eval_provenance"] = {"eval_source": {"stockfish_d14_n150000_h64_live": 4}}
    full["flagged_moves"][0]["played_rank"] = None
    out = to_compact_v2(full, game_meta=GAME_META)
    validate_compact(out)
    assert out["summary"]["src"] == "d14n150k_h64_live"
    assert out["pv_played_unavailable"]["34"] == "rank_unknown"


def test_piece_reads_are_capped_and_measured():
    full = json.loads(json.dumps(FULL))
    full["flagged_moves"][0].update(
        {
            "cp_loss": 150.0,
            "fen_before": "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3",
            "engine_lines": [
                {
                    "rank": 1,
                    "san": "Nxe5",
                    "eval_cp": 30,
                    "pv": ["Nxe5", "Nxe5"],
                }
            ],
        }
    )
    out = to_compact_v2(full, game_meta=GAME_META)
    validate_compact(out)
    assert "34" in out.get("piece_reads", {})
    assert out["piece_reads"]["34"][0]["th"] == "Nxe5"
    assert len(out["piece_reads"]) <= 2


def test_mate_in_in_blunder_flag():
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
            "engine_lines": [
                {
                    "rank": 1,
                    "san": "Qf4+",
                    "eval_cp": None,
                    "mate_in": 5,
                    "pv": ["Qf4+", "Qf6", "Qxf6+", "Kg8", "Re8#"],
                }
            ],
            "played_rank": 4,
        }
    )
    out = to_compact_v2(full, game_meta=GAME_META)
    validate_compact(out)
    by_ply = {f["ply"]: f for f in out["flags"]}
    assert by_ply[75]["mate_in"] == 5
    # FIX-027 is blunder-only: ordinary flags never pay the ~15 chars.
    assert "mate_in" not in by_ply[34]

    not_mate = json.loads(json.dumps(FULL))
    not_mate["flagged_moves"].append(
        {
            **FLAG_TEMPLATE,
            "ply": 75,
            "classification": "blunder",
            "cp_loss": 400.0,
            "engine_lines": [{"rank": 1, "san": "Qf4+", "eval_cp": 300, "pv": ["Qf4+"]}],
        }
    )
    ordinary = to_compact_v2(not_mate, game_meta=GAME_META)
    validate_compact(ordinary)
    assert "mate_in" not in {f["ply"]: f for f in ordinary["flags"]}[75]


def test_anchor_based_eval_pair_is_consistent():
    """2.6/C-1: bcp - eval_after reproduces cp even when the old before-eval did not."""
    full = json.loads(json.dumps(FULL))
    full["flagged_moves"].append(
        {
            **FLAG_TEMPLATE,
            "ply": 89,
            "san": "Qe4+",
            "classification": "mistake",
            "cp_loss": 237.0,
            "eval_before": 638,
            "eval_after": 682,
            "best_eval": 919,
            "engine_lines": [],
            "played_rank": None,
        }
    )
    full["flagged_moves"].append(
        {
            **FLAG_TEMPLATE,
            "ply": 93,
            "san": "Kg1",
            "classification": "mistake",
            "cp_loss": 237.0,
            "eval_before": 682,
            "eval_after": 445,
            "best_eval": 682,
            "engine_lines": [],
            "played_rank": None,
        }
    )
    out = to_compact_v2(full, game_meta=GAME_META, pv_unavailable={89: "engine_timeout"})
    validate_compact(out)
    by_ply = {f["ply"]: f for f in out["flags"]}
    assert "eval_before_mover_cp" not in by_ply[89]
    assert by_ply[89]["bcp"] == 919
    assert by_ply[89]["eval_after_mover_cp"] == 682  # 919 - 682 = 237
    assert by_ply[93]["bcp"] == 682
    assert by_ply[93]["eval_after_mover_cp"] == 445


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
    # 2.6 adds bcp per flag + nm/mit per pattern (calibration wave 1).
    # Internal test budget stays far below the handoff's 4500-char ceiling.
    assert compact_size(_compact()) <= 2750


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


# ── P0-7 / P0-8: coverage semantics ─────────────────────────────────────────


def test_unclassified_feed_lists_exactly_the_unclassified_flags():
    out = _compact()
    assert out["unclassified"] == [
        {"ply": 34, "class": "inaccuracy", "cp": 84, "why": "quiet_positional"},
        {"ply": 46, "class": "inaccuracy", "cp": 66, "why": "quiet_positional"},
        {"ply": 68, "class": "inaccuracy", "cp": 120, "why": "quiet_positional"},
    ]
    assert out["patterns_meta"]["coverage"] == {"flagged": 4, "matched": 1, "unclassified": 3}


def test_empty_patterns_still_has_a_reason_and_full_coverage():
    full = json.loads(json.dumps(FULL))
    full["patterns"] = []
    for flag in full["flagged_moves"]:
        flag["pattern_status"] = "unclassified"
        flag["unclassified_reason"] = "quiet_positional"
    out = to_compact_v2(full, game_meta=GAME_META, moves=MOVES)
    validate_compact(out)
    assert out["patterns"] == []
    assert out["patterns_meta"]["reason"]
    assert out["patterns_meta"]["coverage"] == {"flagged": 4, "matched": 0, "unclassified": 4}
    assert len(out["unclassified"]) == 4


def test_legacy_payload_without_pstatus_is_explicitly_not_classified():
    """A payload predating P0-7 must not look classified."""
    full = json.loads(json.dumps(FULL))
    full.pop("patterns_meta")
    full.pop("unclassified")
    for flag in full["flagged_moves"]:
        flag.pop("pattern_status", None)
        flag.pop("unclassified_reason", None)
    out = to_compact_v2(full, game_meta=GAME_META, moves=MOVES)
    validate_compact(out)
    by_ply = {flag["ply"]: flag for flag in out["flags"]}
    assert by_ply[34]["pstatus"] == "unclassified"
    assert by_ply[34]["why"] == "not_classified"
    # The one ply covered by the pattern list is still matched.
    assert by_ply[40]["pstatus"] == "matched"


def test_validator_rejects_matched_flag_without_patterns():
    out = _compact()
    out["flags"][1].pop("patterns")
    with pytest.raises(ValueError):
        validate_compact(out)


def test_validator_rejects_unclassified_flag_without_reason():
    out = _compact()
    out["flags"][0].pop("why")
    with pytest.raises(ValueError):
        validate_compact(out)


def test_validator_rejects_coverage_that_does_not_add_up():
    out = _compact()
    out["patterns_meta"]["coverage"]["unclassified"] = 99
    with pytest.raises(ValueError):
        validate_compact(out)


# ── 2.2 / D29-D33: game_impact, missed mate, played PV, cluster plies ───────


def test_every_flag_carries_game_impact():
    """2.2: the label that separates a thrown win from a missed mate is
    mandatory. Null = the evals were not measured, never a guessed state."""
    out = _compact()
    assert all("game_impact" in flag for flag in out["flags"])
    full = json.loads(json.dumps(FULL))
    full["flagged_moves"][0]["eval_before"] = None
    full["flagged_moves"][0]["eval_after"] = None
    unmeasured = to_compact_v2(full, game_meta=GAME_META)
    assert unmeasured["flags"][0]["game_impact"] is None
    validate_compact(unmeasured)


def test_mate_missed_names_the_length_and_the_mating_move():
    """`WHIbVLXk` white ply 67: Bf5+ 9027cp while the best line is e6+ mate in 10."""
    full = json.loads(json.dumps(FULL))
    full["flagged_moves"].append(
        {
            **FLAG_TEMPLATE,
            "ply": 67,
            "san": "Bf5+",
            "classification": "blunder",
            "cp_loss": 9027.0,
            "eval_before": 825,
            "eval_after": 961,
            "best_move_san": "e6+",
            "played_rank": 3,
            "engine_lines": [
                {"rank": 1, "san": "e6+", "eval_cp": None, "mate_in": 10, "pv": ["e6+", "Kxe6"]},
                {"rank": 2, "san": "Kg2", "eval_cp": 780, "pv": ["Kg2", "Qf4"]},
                {"rank": 3, "san": "Bf5+", "eval_cp": 961, "pv": ["Bf5+", "Ke7"]},
            ],
        }
    )
    out = to_compact_v2(full, game_meta=GAME_META)
    validate_compact(out)
    flag = next(f for f in out["flags"] if f["ply"] == 67)
    assert flag["game_impact"] == "winning_to_winning"
    assert flag["mate_missed"] == 10
    assert flag["mate_via"] == "e6+"
    # The continuation after the played move is the third line, not the best one.
    assert out["pv_played"]["67"] == ["Ke7"]


def test_a_move_that_mates_is_not_a_missed_mate():
    full = json.loads(json.dumps(FULL))
    full["flagged_moves"].append(
        {
            **FLAG_TEMPLATE,
            "ply": 70,
            "san": "Qxh7+",
            "classification": "blunder",
            "cp_loss": 400.0,
            "eval_before": 300,
            "eval_after": 9998,
            "played_rank": 1,
            "engine_lines": [
                {"rank": 1, "san": "Qxh7+", "eval_cp": None, "mate_in": 2, "pv": ["Qxh7+", "Kxh7"]}
            ],
        }
    )
    out = to_compact_v2(full, game_meta=GAME_META)
    validate_compact(out)
    flag = next(f for f in out["flags"] if f["ply"] == 70)
    assert flag["game_impact"] == "winning_to_mate"
    assert "mate_missed" not in flag


def test_played_pv_unavailable_when_rank_is_outside_the_multipv_window():
    """`WHIbVLXk` white ply 63 `fxe6` was rank 4 of 3 searched lines."""
    full = json.loads(json.dumps(FULL))
    full["flagged_moves"].append(
        {
            **FLAG_TEMPLATE,
            "ply": 63,
            "san": "fxe6",
            "classification": "blunder",
            "cp_loss": 406.0,
            "eval_before": 179,
            "eval_after": -229,
            "played_rank": 4,
            "engine_lines": [
                {"rank": 1, "san": "Qf2", "eval_cp": 177, "pv": ["Qf2", "Rh8+"]},
                {"rank": 2, "san": "Kg2", "eval_cp": 150, "pv": ["Kg2", "Rh8"]},
                {"rank": 3, "san": "Rg1", "eval_cp": 120, "pv": ["Rg1", "bxa5"]},
            ],
        }
    )
    out = to_compact_v2(full, game_meta=GAME_META)
    validate_compact(out)
    assert out["pv_played_unavailable"]["63"] == "rank_not_in_engine_lines"
    assert "63" not in out.get("pv_played", {})


def test_mate_after_direction_survives_compaction():
    """2.4: `losing_to_mate` without a direction is not narratable (live ply 68 of WHIbVLXk)."""
    full = json.loads(json.dumps(FULL))
    full["flagged_moves"].append(
        {
            **FLAG_TEMPLATE,
            "ply": 70,
            "san": "Kc7",
            "classification": "blunder",
            "cp_loss": 9470.0,
            "eval_before": -961,
            "eval_after": -9996,
            "game_impact": "losing_to_mate",
            "mate_after": "against",
        }
    )
    out = to_compact_v2(full, game_meta=GAME_META)
    validate_compact(out)
    flag = next(f for f in out["flags"] if f["ply"] == 70)
    assert flag["game_impact"] == "losing_to_mate"
    assert flag["mate_after"] == "against"


def test_validator_rejects_mate_impact_without_direction():
    out = _compact()
    out["flags"][0]["game_impact"] = "winning_to_mate"
    out["flags"][0]["mate_after"] = None
    with pytest.raises(ValueError, match="mate_after"):
        validate_compact(out)


def test_pipeline_separates_offline_etl_from_a_failed_analysis():
    base = json.loads(json.dumps(FULL))
    base["report_meta"] = {"source": "deterministic"}
    out = to_compact_v2(base, game_meta=GAME_META)
    validate_compact(out)
    assert out["pipeline"] == {
        "analysis": "complete",
        "coaching": "deterministic_fallback",
        "llm_requested": True,
    }
    offline = json.loads(json.dumps(base))
    offline["llm"]["reason"] = "llm_disabled"
    out2 = to_compact_v2(offline, game_meta=GAME_META)
    validate_compact(out2)
    assert out2["pipeline"] == {
        "analysis": "complete",
        "coaching": "deterministic_fallback",
        "llm_requested": False,
    }


def test_accuracy_warning_travels_with_the_score():
    full = json.loads(json.dumps(FULL))
    full["analysis"]["accuracy_warning"] = "contains_mate_level_outlier"
    out = to_compact_v2(full, game_meta=GAME_META)
    validate_compact(out)
    assert out["summary"]["acc_warning"] == "contains_mate_level_outlier"


def test_validator_rejects_mate_via_without_mate_missed():
    out = _compact()
    out["flags"][0]["mate_via"] = "Qh5#"
    with pytest.raises(ValueError):
        validate_compact(out)


def test_validator_rejects_cluster_plies_that_do_not_match_the_run():
    full = json.loads(json.dumps(FULL))
    for ply, cp in ((87, 186.0), (89, 237.0), (91, 59.0)):
        full["flagged_moves"].append(
            {**FLAG_TEMPLATE, "ply": ply, "san": f"M{ply}", "cp_loss": cp, "engine_lines": []}
        )
    out = to_compact_v2(full, game_meta=GAME_META)
    out["clusters"][0]["plies"] = [87, 89]
    with pytest.raises(ValueError):
        validate_compact(out)
