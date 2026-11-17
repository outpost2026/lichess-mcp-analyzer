"""P0 (handoff 2.7) piece_reads: qualitative board facts from measured PVs.

An LLM can say "Nxe4 lost 320 cp" from the numbers, but not "you left the
rook on f1 alive and it threatens Rxf2+" unless the JSON carries that fact.
This module derives piece reads ONLY from SANs that the engine actually
published in `engine_lines` (and from the FEN of the position). It never infers
a threat that is not in the search output, and it skips unparsable SANs.
"""

from __future__ import annotations

import chess

_MAX_READS = 2
_MAX_PV_SANS = 4


def reads_for_flag(flag: dict) -> list[dict]:
    """Return at most two piece reads for one flagged move."""
    fen = flag.get("fen_before") or ""
    lines = flag.get("engine_lines") or []
    if not fen or not lines:
        return []
    try:
        board = chess.Board(fen)
    except ValueError:
        return []

    out: list[dict] = []
    seen: set[tuple[str, str]] = set()
    pv = list(lines[0].get("pv") or [])[:_MAX_PV_SANS]
    for san in pv:
        if not isinstance(san, str) or not san:
            continue
        try:
            move = board.parse_san(san)
        except (ValueError, AssertionError):
            break  # a broken PV must not produce a made-up piece read
        piece = board.piece_at(move.from_square)
        forcing = "x" in san or "+" in san or "#" in san
        if piece and forcing:
            square = chess.square_name(move.from_square)
            key = (square, piece.symbol())
            if key not in seen:
                seen.add(key)
                out.append(
                    {
                        "sq": square,
                        "pc": piece.symbol(),
                        "role": "monster",
                        "th": san,
                    }
                )
                if len(out) >= _MAX_READS:
                    break
        board.push(move)
    return out
