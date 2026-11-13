"""T1: provenance block for pattern measurements."""

from __future__ import annotations

from lichess_analyzer_mcp.models.game import GameAnalysis, GameSummary, MoveAnalysis
from lichess_analyzer_mcp.models.pattern import PatternLibrary, PatternMatch
from lichess_analyzer_mcp.services.coaching_base import collect_patterns_for_games
from lichess_analyzer_mcp.services.pattern_detector import PatternDetector
from lichess_analyzer_mcp.services.provenance import (
    build_provenance,
    code_commit,
    dataset_sha256,
    pattern_lib_sha256,
)


def _move(ply: int = 1) -> MoveAnalysis:
    return MoveAnalysis(
        ply=ply,
        move_uci="e2e4",
        move_san="e4",
        eval_before=0.0,
        eval_after=0.0,
        win_prob_before=0.5,
        win_prob_after=0.5,
        centipawn_loss=0.0,
        classification="best",
        best_move_uci="e2e4",
        best_move_san="e4",
        is_tactical_motif=False,
        motif_type=None,
        phase="opening",
    )


def _game(
    gid: str,
    color: str = "white",
    opponent: str = "Named",
    n_moves: int = 2,
    date: str = "2026-01-01",
) -> GameAnalysis:
    return GameAnalysis(
        game=GameSummary(
            id=gid,
            platform="lichess",
            opening="",
            opening_eco="",
            color=color,
            result="1-0",
            opponent_name=opponent,
            date=date,
        ),
        moves=[_move(i + 1) for i in range(n_moves)],
    )


def _library() -> PatternLibrary:
    return PatternLibrary().load_baseline()


def test_dataset_hash_is_order_independent() -> None:
    games = [_game("g1"), _game("g2"), _game("g3", color="black")]
    assert dataset_sha256(games) == dataset_sha256(list(reversed(games)))


def test_dataset_hash_changes_with_composition() -> None:
    base = [_game("g1"), _game("g2")]
    changed = [_game("g1"), _game("g2", n_moves=3)]
    assert dataset_sha256(base) != dataset_sha256(changed)


def test_pattern_lib_hash_is_stable_and_sensitive() -> None:
    library = _library()
    assert pattern_lib_sha256(library) == pattern_lib_sha256(_library())

    mutated = _library()
    mutated.patterns["A"].min_games += 1
    assert pattern_lib_sha256(mutated) != pattern_lib_sha256(library)


def test_build_provenance_shape() -> None:
    games = [_game("g1"), _game("g2")]
    prov = build_provenance(games, _library())

    assert set(prov) == {
        "dataset_sha256",
        "pattern_lib_sha256",
        "code_commit",
        "n_games",
        "n_moves",
    }
    assert len(prov["dataset_sha256"]) == 64
    assert len(prov["pattern_lib_sha256"]) == 64
    assert prov["n_games"] == 2
    assert prov["n_moves"] == 4
    assert isinstance(prov["code_commit"], str) and prov["code_commit"]


def test_code_commit_has_fallback(monkeypatch) -> None:
    monkeypatch.setenv("LICHESS_CODE_COMMIT", "test-commit")
    code_commit.cache_clear()
    try:
        assert code_commit() == "test-commit"
    finally:
        code_commit.cache_clear()


def test_pattern_match_provenance_defaults_to_none() -> None:
    match = PatternMatch(
        pattern_id="A",
        pattern_name="Anonymous effect",
        strength=0.5,
        evidence=[],
        game_ids=[],
        frequency=1,
        severity="high",
    )
    assert match.provenance is None


def test_detect_all_attaches_provenance() -> None:
    games = [
        _game("anon1", opponent="Anonymous 1"),
        _game("anon2", opponent="Anonymous 2"),
        _game("named1"),
    ]
    games[0].blunders = [_move(1), _move(2)]
    games[1].blunders = [_move(1), _move(2)]
    games[2].blunders = [_move(1)]

    matches = PatternDetector().detect_all(games, {"username": "tester"})
    assert matches
    prov = matches[0].provenance
    assert prov is not None
    assert prov["dataset_sha256"] == dataset_sha256(games)
    assert prov["n_games"] == 3
    assert prov["n_moves"] == 6


def test_report_dict_carries_provenance() -> None:
    games = [
        _game("anon1", opponent="Anonymous 1"),
        _game("anon2", opponent="Anonymous 2"),
        _game("named1"),
    ]
    games[0].blunders = [_move(1), _move(2)]
    games[1].blunders = [_move(1), _move(2)]
    games[2].blunders = [_move(1)]

    report = collect_patterns_for_games(games, "tester")
    assert report
    assert report[0]["provenance"]["dataset_sha256"] == dataset_sha256(games)
