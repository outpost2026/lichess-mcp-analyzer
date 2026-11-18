"""Q4 experiment: declined forcing move at pivot (off by default, D4 gate pending)."""

from types import SimpleNamespace

import lichess_analyzer_mcp.services.pattern_detector as pd


def _move(san="Ne3", best="Bxg2+", cp=158.0):
    return SimpleNamespace(
        centipawn_loss=cp,
        move_san=san,
        best_move_san=best,
        classification="mistake",
        was_in_check=False,
        gives_check=False,
        motif_type=None,
        is_tactical_motif=False,
        fen="",
        move_uci="b8e3",
        played_rank=0,
        best_eval=None,
        eval_before=297,
        eval_after=139,
    )


def _ids(move):
    return [candidate["pattern_id"] for candidate in pd.per_move_patterns(move)]


def test_q4_disabled_by_default(monkeypatch):
    monkeypatch.setattr(pd, "EXPERIMENTAL_Q4_ENABLED", False)
    assert "Q4" not in _ids(_move())


def test_q4_emits_only_with_flag_and_forcing_best(monkeypatch):
    monkeypatch.setattr(pd, "EXPERIMENTAL_Q4_ENABLED", True)
    candidates = pd.per_move_patterns(_move())
    assert "Q4" in _ids(_move())
    q4 = next(c for c in candidates if c["pattern_id"] == "Q4")
    assert q4["pattern_name"] == "declined_forcing_move_at_pivot"
    assert q4["severity"] == "high"
    assert "Bxg2+" in q4["detail"]


def test_q4_requires_forcing_best_move(monkeypatch):
    monkeypatch.setattr(pd, "EXPERIMENTAL_Q4_ENABLED", True)
    assert "Q4" not in _ids(_move(best="Qe5"))


def test_q4_requires_non_forcing_played_move(monkeypatch):
    monkeypatch.setattr(pd, "EXPERIMENTAL_Q4_ENABLED", True)
    assert "Q4" not in _ids(_move(san="Bxg2+"))


def test_q4_requires_cp_loss_above_threshold(monkeypatch):
    monkeypatch.setattr(pd, "EXPERIMENTAL_Q4_ENABLED", True)
    assert "Q4" not in _ids(_move(cp=40.0))
