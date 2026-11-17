"""P0-6 / T-02: eval provenance gates (no engine, no network).

N-03: only 2.2 % of the historical corpus carries the D12 `best_eval` anchor.
The payload must therefore say what each `cp_loss` rests on instead of
implying the invariant holds everywhere.
"""

import re

from lichess_analyzer_mcp.services.eval_provenance import (
    configured_eval_source,
    cp_loss_basis,
    normalize_eval_source,
    provenance_summary,
    run_id,
)
from lichess_analyzer_mcp.tools.coaching_single_game import _flagged_moves


def _raw_move(**overrides):
    move = {
        "ply": 12,
        "move_san": "Qh5",
        "move_uci": "d1h5",
        "classification": "blunder",
        "centipawn_loss": 500.0,
        "eval_before": 400,
        "eval_after": -100,
        "best_eval": 400,
        "engine_lines": [],
        "played_rank": 4,
    }
    move.update(overrides)
    return move


# --- basis: measured or unknown, never inferred -----------------------------


def test_basis_is_best_eval_only_when_the_anchor_reconstructs():
    assert cp_loss_basis(400, -100, 500) == "best_eval"


def test_basis_is_unknown_without_an_anchor():
    assert cp_loss_basis(None, -100, 500) == "unknown"
    assert cp_loss_basis(400, None, 500) == "unknown"


def test_basis_is_unknown_when_the_published_triple_contradicts_itself():
    assert cp_loss_basis(100, -100, 500) == "unknown"


# --- source: closed enum, no guessing ---------------------------------------


def test_source_is_normalised_to_the_closed_enum():
    assert normalize_eval_source("stockfish") == "stockfish"
    assert normalize_eval_source("chess-api.com") == "cloud"
    assert normalize_eval_source("cloud") == "cloud"


def test_unknown_source_never_becomes_stockfish():
    assert normalize_eval_source("") == "unknown"
    assert normalize_eval_source(None) == "unknown"
    assert normalize_eval_source("mystery-engine") == "unknown"


# --- per-payload aggregate ---------------------------------------------------


def test_summary_counts_only_measured_moves_and_reports_coverage():
    moves = [
        {
            "analyzed": True,
            "centipawn_loss": 120.0,
            "best_eval": 40,
            "eval_after": -80,
            "cp_loss_basis": "best_eval",
            "eval_source": "stockfish",
        },
        {
            "analyzed": True,
            "centipawn_loss": 300.0,
            "best_eval": None,
            "eval_after": -200,
            "cp_loss_basis": "unknown",
            "eval_source": "cloud",
        },
        {"analyzed": False, "centipawn_loss": None},
    ]
    out = provenance_summary(moves)
    assert out["moves_measured"] == 2
    assert out["anchor_coverage"] == 0.5
    assert out["cp_loss_basis"] == {"best_eval": 1, "unknown": 1}
    assert out["eval_source"] == {"stockfish": 1, "cloud": 1}


def test_summary_derives_basis_for_legacy_moves_without_the_field():
    moves = [{"centipawn_loss": 50.0, "best_eval": 60, "eval_after": 10}]
    out = provenance_summary(moves)
    assert out["cp_loss_basis"] == {"best_eval": 1}
    assert out["eval_source"] == {"unknown": 1}


def test_empty_payload_has_no_invented_coverage():
    out = provenance_summary([])
    assert out == {
        "moves_measured": 0,
        "anchor_coverage": None,
        "cp_loss_basis": {},
        "eval_source": {},
    }


# --- run identity ------------------------------------------------------------

_POLICY = {
    "depth": 14,
    "mode": "fast",
    "nodes_cap": 150000,
    "threads": 1,
    "detector_version": "DBCL-20261113-dev",
    "schema_version": "1.2",
}


def test_run_id_is_a_stable_short_fingerprint():
    first = run_id(**_POLICY)
    assert re.fullmatch(r"[0-9a-f]{16}", first)
    assert run_id(**_POLICY) == first


def test_run_id_changes_with_any_policy_dimension():
    base = run_id(**_POLICY)
    assert run_id(**{**_POLICY, "depth": 16}) != base
    assert run_id(**{**_POLICY, "mode": "deep"}) != base
    assert run_id(**{**_POLICY, "nodes_cap": 0}) != base
    assert run_id(**{**_POLICY, "detector_version": "v-next"}) != base


# --- detailed surface --------------------------------------------------------


def test_flagged_moves_publish_provenance_and_never_guess_the_source():
    measured = _flagged_moves(
        {"moves": [_raw_move(cp_loss_basis="best_eval", eval_source="stockfish")]}
    )[0]
    assert measured["cp_loss_basis"] == "best_eval"
    assert measured["eval_source"] == "stockfish"

    # A legacy cache has no recorded basis, but its published anchor is enough
    # to derive it — the aggregate and the flag must never disagree.
    legacy = _flagged_moves({"moves": [_raw_move()]})[0]
    assert legacy["cp_loss_basis"] == "best_eval"
    # P0-4: without configuration the honest label is `unknown`, not a guess.
    assert legacy["eval_source"] == "unknown"

    unanchored = _flagged_moves({"moves": [_raw_move(best_eval=None)]})[0]
    assert unanchored["cp_loss_basis"] == "unknown"


# --- P0-4: exact engine policy in the source label --------------------------


def test_eval_provenance_contains_config():
    assert (
        configured_eval_source("stockfish", depth=14, nodes_cap=150000, hash_mb=512)
        == "stockfish_d14_n150000_h512_live"
    )
    assert (
        configured_eval_source(
            "stockfish",
            depth=14,
            nodes_cap=150000,
            hash_mb=512,
            cache_hit=True,
            run_id="6d1af88445f154ad",
        )
        == "stockfish_d14_n150000_h512_cache_run_6d1af88445f154ad"
    )
    assert (
        configured_eval_source("stockfish", depth=14, nodes_cap=150000, cache_hit=True)
        == "stockfish_d14_n150000_hash_unknown_cache"
    )
