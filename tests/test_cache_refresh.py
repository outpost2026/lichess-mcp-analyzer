"""FIX-028: recovered PV must be persisted so cache hits do not re-run the engine."""

from lichess_analyzer_mcp.models.game import GameAnalysis, GameSummary, MoveAnalysis
from lichess_analyzer_mcp.services import game_analyzer as ga
from lichess_analyzer_mcp.services import pv_recovery


def _summary(game_id="AbCd1234"):
    return GameSummary(
        id=game_id,
        platform="lichess",
        opening="Test",
        opening_eco="C00",
        color="white",
        result="1-0",
    )


def _move(engine_lines=None):
    return MoveAnalysis(
        ply=75,
        move_uci="e8e8",
        move_san="Re8+",
        eval_before=9997.0,
        eval_after=525.0,
        win_prob_before=0.99,
        win_prob_after=0.53,
        centipawn_loss=9473.0,
        classification="blunder",
        best_move_uci="f4f6",
        best_move_san="Qf4+",
        is_tactical_motif=True,
        motif_type="check",
        phase="endgame",
        engine_lines=engine_lines or [],
    )


def test_refresh_never_creates_a_cache_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(ga, "CACHE_DIR", str(tmp_path))
    analysis = GameAnalysis(game=_summary())
    assert ga.refresh_cached_analysis("AbCd1234", 14, "fast", analysis) is False
    assert list(tmp_path.iterdir()) == []


def test_refresh_persists_recovered_engine_lines(tmp_path, monkeypatch):
    monkeypatch.setattr(ga, "CACHE_DIR", str(tmp_path))
    analysis = GameAnalysis(game=_summary(), moves=[_move()])
    policy = ga._policy_token(14, "fast")
    ga._save_cached_analysis("AbCd1234", 14, analysis, policy=policy)

    recovered = [{"rank": 1, "san": "Qf4+", "eval_cp": None, "mate_in": 5, "pv": ["Qf4+", "Qf6"]}]
    analysis.moves[0].engine_lines = recovered
    assert ga.refresh_cached_analysis("AbCd1234", 14, "fast", analysis) is True

    loaded = ga._load_cached_analysis("AbCd1234", 14, "white", exact_depth=True, policy=policy)
    assert loaded.moves[0].engine_lines == recovered


def test_cache_hit_recovery_is_a_noop(monkeypatch):
    """FIX-028: a hit whose blunders already carry a PV must not call the engine."""
    analysis = GameAnalysis(
        game=_summary(),
        moves=[
            _move(
                engine_lines=[
                    {
                        "rank": 1,
                        "san": "Qf4+",
                        "eval_cp": None,
                        "mate_in": 5,
                        "pv": ["Qf4+", "Qf6"],
                    }
                ]
            )
        ],
    )
    calls = []
    monkeypatch.setattr(
        pv_recovery.engine_client,
        "analyze_position_ex",
        lambda *a, **k: calls.append(1) or ([], None),
    )
    assert pv_recovery.recover_missing_pv(analysis, depth=14) == {}
    assert calls == []
