"""Determinism and field-consistency invariants.

Everything here runs without an engine process: it pins the *policy* that
makes repeated runs comparable, and the field semantics that made
`motif="check"` look like a contradiction next to `check=False`.
"""

from lichess_analyzer_mcp.config.depth import ENGINE_THREADS, NODE_CAPS
from lichess_analyzer_mcp.services import engine_client, game_analyzer
from lichess_analyzer_mcp.tools.coaching_single_game import _flagged_moves

CAP_14 = int(NODE_CAPS[14] or 0)

PGN_3_MOVES = """[Site "https://lichess.org/cccccccc"]
[White "systeq"]
[Black "opponent"]
[Result "*"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 *
"""

PGN_10_MOVES = """[Site "https://lichess.org/bbbbbbbb"]
[White "systeq"]
[Black "opponent"]
[Result "*"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 4. Ba4 Nf6 5. O-O Be7 6. Re1 b5 7. Bb3 d6 8. c3 O-O 9. h3 Nb8 10. d4 Nbd7 *
"""


# ── FIX-003: the search limit must not contain a wall clock ──────────────────


def test_limit_uses_search_counters_only():
    limit = engine_client._limit(14, CAP_14)
    assert limit.depth == 14
    assert limit.nodes == CAP_14
    assert limit.time is None


def test_legacy_limit_is_depth_only():
    limit = engine_client._limit(14, 0)
    assert limit.depth == 14
    assert limit.nodes is None


def test_single_thread_is_the_default():
    assert ENGINE_THREADS == 1


def test_cache_key_separates_engine_policies():
    policy = game_analyzer._policy_token(14, "fast")
    current = game_analyzer._cache_path("abc12345", 14, "white", policy)
    legacy = game_analyzer._cache_path("abc12345", 14, "white", "")
    assert policy == f"n{CAP_14}"
    assert current != legacy
    assert current.endswith(f"_d14{policy}.json")
    assert legacy.endswith("_d14.json")


def test_legacy_mode_keeps_its_cache_names():
    assert game_analyzer._policy_token(14, "legacy") == ""


def test_node_cap_is_defined_for_every_supported_depth():
    for depth in (12, 14, 16, 18):
        assert CAP_14 > 0
        assert int(NODE_CAPS[depth] or 0) > 0


# ── FIX-002: `check` means "the move gives check" ────────────────────────────


def _flag(move: dict) -> dict:
    return _flagged_moves({"moves": [move]})[0]


def test_motif_check_is_consistent_with_check_field():
    flagged = _flag(
        {
            "ply": 41,
            "move_san": "Qf5+",
            "classification": "blunder",
            "motif_type": "check",
            "gives_check": True,
            "was_in_check": False,
            "centipawn_loss": 308.0,
            "explanation": "…",
        }
    )
    assert flagged["motif"] == "check"
    assert flagged["check"] is True
    assert flagged["in_check_before"] is False


def test_checking_move_out_of_check_is_not_a_contradiction():
    flagged = _flag(
        {
            "ply": 12,
            "move_san": "Bb5+",
            "classification": "inaccuracy",
            "motif_type": None,
            "gives_check": True,
            "was_in_check": True,
            "centipawn_loss": 60.0,
        }
    )
    assert flagged["check"] is True
    assert flagged["in_check_before"] is True


# ── FIX-004: one BFS timeout must not strip a flagged move of its lines ─────


def test_engine_lines_timeout_retries_once(monkeypatch):
    calls = {"n": 0}

    def fake_evaluate(fen, move_uci, depth=0, timeout_s=None, nodes=0, use_cloud=False):
        return {
            "eval_before": 400,
            "eval_after": 50,
            "centipawn_loss": 350.0,
            "best_move_uci": "e2e4",
        }

    def flaky_lines(fen, depth=0, multipv=3, timeout_s=None, nodes=0):
        calls["n"] += 1
        if calls["n"] % 2 == 1:
            return [], "engine call timed out after 5s"
        return (
            [
                {"rank": 1, "san": "e2e4", "eval_cp": 400, "pv": ["e2e4"]},
                {"rank": 2, "san": "d2d4", "eval_cp": 380, "pv": ["d2d4"]},
            ],
            None,
        )

    monkeypatch.setattr(engine_client, "evaluate_move", fake_evaluate)
    monkeypatch.setattr(engine_client, "analyze_position_ex", flaky_lines)
    monkeypatch.setattr(engine_client, "get_engine", lambda hash_mb=None, threads=None: None)
    monkeypatch.setattr(engine_client, "clear_hash", lambda: None)

    analysis = game_analyzer._run_analyze_pgn(
        PGN_3_MOVES, "white", depth=14, deadline_s=60.0, mode="fast"
    )

    assert calls["n"] == 2 * len(
        [m for m in analysis.moves if m.classification in ("blunder", "mistake", "inaccuracy")]
    )
    assert analysis.engine_timeouts == 0
    explained = [m for m in analysis.moves if m.classification == "blunder"]
    assert explained
    assert all(m.engine_lines for m in explained)
    assert all(m.explanation_source == "deterministic" for m in explained)
