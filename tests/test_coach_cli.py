"""Unified CLI (`scripts/coach.py`) — contract tests without engine or network."""

import importlib.util
import os

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _load_coach():
    path = os.path.join(ROOT, "scripts", "coach.py")
    spec = importlib.util.spec_from_file_location("coach_cli", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


coach = _load_coach()

PGN = """[Event "casual rapid game"]
[Site "https://lichess.org/game/Sl1s8KmU"]
[GameId "Sl1s8KmU"]
[White "Systeq"]
[Black "Apolon7b56ravda"]
[Result "0-1"]

1. e4 Nf6 2. Nc3 d5 *
"""

COMPACT_A = {
    "v": "2.0",
    "game": {"id": "a"},
    "summary": {"acpl": 20.0},
    "flags": [{"class": "blunder"}, {"class": "inaccuracy"}],
    "patterns": [{"id": "T"}, {"id": "B"}],
}
COMPACT_B = {
    "v": "2.0",
    "game": {"id": "b"},
    "summary": {"acpl": 30.0},
    "flags": [{"class": "mistake"}],
    "patterns": [{"id": "T"}],
}


def test_help_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        coach.main(["--help"])
    assert exc.value.code == 0
    assert "compact" in capsys.readouterr().out


def test_missing_source_exits_validation_error():
    with pytest.raises(SystemExit) as exc:
        coach.main(["--game-id", "x", "--pgn-file", "y.pgn"])
    assert exc.value.code == 1


def test_batch_requires_username():
    with pytest.raises(SystemExit) as exc:
        coach.main(["--batch", "3"])
    assert exc.value.code == 1


def test_batch_rejects_detailed_format():
    with pytest.raises(SystemExit) as exc:
        coach.main(["--username", "systeq", "--batch", "3", "--format", "detailed"])
    assert exc.value.code == 1


def test_pgn_metadata_helpers():
    assert coach._pgn_game_id(PGN) == "Sl1s8KmU"
    assert coach._pgn_color(PGN, "systeq") == "white"
    assert coach._pgn_color(PGN, "apolon7b56ravda") == "black"
    assert coach._pgn_color(PGN, "someone") == ""


def test_aggregate_compact_games():
    stats = coach.aggregate([COMPACT_A, COMPACT_B])
    assert stats["games"] == 2
    assert stats["mean_acpl"] == 25.0
    assert stats["flags"] == {"blunder": 1, "mistake": 1, "inaccuracy": 1}
    assert stats["patterns"] == {"B": 1, "T": 2}


def test_aggregate_ignores_unmeasured_acpl():
    payload = {**COMPACT_A, "summary": {"acpl": None}}
    stats = coach.aggregate([payload])
    assert stats["mean_acpl"] is None


def test_exit_code_classification():
    import chess.engine

    assert coach._classify_exception(FileNotFoundError("x")) == 2
    assert coach._classify_exception(ValueError("invalid pgn")) == 1
    assert coach._classify_exception(chess.engine.EngineError("boom")) == 3


def test_refresh_does_not_shrink_game_cache(monkeypatch):
    from lichess_analyzer_mcp.services import lichess_client

    previous = [
        {"id": "old1", "createdAt": "2026-11-09T20:00:00+00:00"},
        {"id": "old2", "createdAt": "2026-11-09T19:00:00+00:00"},
    ]
    saved = {}

    monkeypatch.setattr(lichess_client, "_load_user_games_cache", lambda u: previous)
    monkeypatch.setattr(
        lichess_client,
        "_export_by_player",
        lambda u, max_games: [{"id": "new1", "createdAt": "2026-11-09T21:00:00+00:00"}],
    )
    monkeypatch.setattr(
        lichess_client, "_save_user_games_cache", lambda u, g: saved.update(games=g)
    )
    monkeypatch.setattr(lichess_client, "_save_games_index", lambda u, i: None)

    games = lichess_client.fetch_user_games("systeq", max_games=3, refresh=True)
    assert len(games) == 3
    assert [g["id"] for g in games] == ["new1", "old1", "old2"]
    assert [g["id"] for g in saved["games"]] == ["new1", "old1", "old2"]
