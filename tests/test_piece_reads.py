"""Handoff 2.7 wave 1: piece reads come only from measured PV SANs."""

from lichess_analyzer_mcp.services.piece_reads import reads_for_flag

# After 1. e4 e5 2. Nf3 Nc6, White to move.
FEN = "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3"


def _flag(pv, fen=FEN):
    return {
        "ply": 5,
        "move_san": "Bb5",
        "fen_before": fen,
        "engine_lines": [{"rank": 1, "san": pv[0], "eval_cp": 30, "pv": pv}],
    }


def test_forcing_pv_move_becomes_a_monster_read():
    reads = reads_for_flag(_flag(["Nxe5", "Nxe5"]))
    assert reads[0]["th"] == "Nxe5"
    assert reads[0]["sq"] == "f3"
    assert reads[0]["pc"] == "N"
    assert reads[0]["role"] == "monster"


def test_quiet_pv_yields_no_read_instead_of_an_inferred_threat():
    assert reads_for_flag(_flag(["d3", "Nf6"])) == []


def test_missing_fen_or_lines_yield_no_read():
    assert reads_for_flag({"fen_before": "", "engine_lines": []}) == []
    assert reads_for_flag({"fen_before": FEN, "engine_lines": []}) == []
