"""Handoff P0-1/P0-2: cluster-based C and quiet-blunder U patterns."""

from lichess_analyzer_mcp.models.game import GameAnalysis, GameSummary, MoveAnalysis
from lichess_analyzer_mcp.services.pattern_detector import scan_single_game

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def _move(
    ply: int, san: str, cp: float, *, classification="inaccuracy", motif=None, in_check=False
):
    return MoveAnalysis(
        ply=ply,
        move_uci="e2e4",
        move_san=san,
        eval_before=100.0,
        eval_after=100.0 - cp,
        win_prob_before=0.5,
        win_prob_after=0.4,
        centipawn_loss=cp,
        classification=classification,
        best_move_uci="d2d4",
        best_move_san="d4",
        is_tactical_motif=bool(motif),
        motif_type=motif,
        phase="middlegame",
        fen=START_FEN,
        was_in_check=in_check,
    )


def _analysis(moves: list[MoveAnalysis]) -> GameAnalysis:
    return GameAnalysis(
        game=GameSummary(
            id="cluster1", platform="lichess", opening="", opening_eco="", color="white", result="*"
        ),
        moves=moves,
    )


def test_cluster_based_attention_tunneling():
    """P0-1: three consecutive own-move flags create Pattern C."""
    patterns, coverage = scan_single_game(
        _analysis(
            [
                _move(27, "a3", 180),
                _move(29, "b4", 190),
                _move(31, "c5", 200),
            ]
        )
    )
    c = next(p for p in patterns if p["pattern_id"] == "C")
    assert c["strength"] == 0.57  # min(1.0, 570/1000)
    assert c["severity"] == "high"  # total_cp 570 > 500
    assert [e["ply"] for e in c["evidence"]] == [27, 29, 31]
    assert all(coverage[ply]["pattern_status"] == "matched" for ply in (27, 29, 31))


def test_cluster_below_500_cp_is_medium():
    patterns, _ = scan_single_game(
        _analysis([_move(11, "a3", 100), _move(13, "b4", 100), _move(15, "c5", 100)])
    )
    c = next(p for p in patterns if p["pattern_id"] == "C")
    assert c["severity"] == "medium" and c["strength"] == 0.3


def test_quiet_blunder_pattern():
    """P0-2: mate-level quiet blunder gets U with critical severity."""
    patterns, coverage = scan_single_game(
        _analysis([_move(41, "Qb5", 9148, classification="blunder")])
    )
    u = next(p for p in patterns if p["pattern_id"] == "U")
    assert u["strength"] == 1.0
    assert u["severity"] == "critical"
    assert u["pattern_name"] == "unseen_threat_quiet_blunder"
    assert coverage[41]["pattern_ids"] == ["U"]


def test_quiet_blunder_high_severity_and_check_response_v():
    patterns, _ = scan_single_game(
        _analysis(
            [
                _move(21, "g3", 699, classification="blunder"),
                _move(50, "Kc7", 118, classification="mistake", in_check=True),
            ]
        )
    )
    u = next(p for p in patterns if p["pattern_id"] == "U")
    assert u["severity"] == "critical" and u["strength"] == 0.7  # 699 > 500
    v = next(p for p in patterns if p["pattern_id"] == "V")
    assert v["pattern_name"] == "wrong_check_response"
