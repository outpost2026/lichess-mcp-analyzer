"""Narrative claim-grounding validator for DBCL v1.1.

Validates LLM-generated chess claims against BlunderFactSheet data.
Each claim must trace to a specific BFS field with the correct operator.
Maps to 01_DBCL_unity_synthesis.md §7 and PHASE2_BUILD_PLAN.md §P1-4.

Usage:
  from lichess_analyzer_mcp.services.narrative_validator import (
      validate_narrative, extract_unsupported_claims
  )
  if extract_unsupported_claims(llm_output, bfs_list):
      # reject loop: retry LLM with guard clause
"""

import re
from typing import Optional

from lichess_analyzer_mcp.models.analysis import BlunderFactSheet


def check_piece_on_square(notation: str, fen: str) -> bool:
    """Check if a piece matching the notation exists on the given square.

    Supports 'e4' (any piece), 'Qf4' (queen on f4), 'Rdg1' (rook on g1).
    """
    import chess

    try:
        board = chess.Board(fen)
        if len(notation) >= 2:
            square = chess.parse_square(notation[-2:])
            piece = board.piece_at(square)
            if piece is None:
                return False
            if len(notation) >= 3 and notation[0].upper() in "KQRBNP":
                return piece.symbol().upper() == notation[0].upper()
            return True
        return False
    except Exception:
        return False


def check_check_claim(claims_check: bool, was_in_check: bool) -> bool:
    return claims_check == was_in_check


def check_capture_claim(san: str, legal_captures: list[str]) -> bool:
    return san in legal_captures


def check_king_move_claim(san: str, legal_king_moves: list[str]) -> bool:
    return san in legal_king_moves


def check_eval_claim(claimed_cp: float, refs: list[float], tol: float = 20.0) -> bool:
    return any(abs(claimed_cp - r) <= tol for r in refs)


def check_variation_claim(prefix: list[str], engine_pvs: list[list[str]]) -> bool:
    for pv in engine_pvs:
        if len(prefix) <= len(pv) and pv[: len(prefix)] == prefix:
            return True
    return False


CHECK_RE = re.compile(r"\b(dává šach|check|\+|nedává šach|není šach|not check)\b", re.IGNORECASE)
EVAL_RE = re.compile(r"([+-]?\d+)\s*cp", re.IGNORECASE)
WINPROB_RE = re.compile(r"(\d+)\s*%", re.IGNORECASE)
SQUARE_RE = re.compile(r"\b([KQRBNP]?[a-h][1-8])\b")
VARIATION_RE = re.compile(
    r"(?:mohl\s+(?:hrát|zahrát)|varianta|pv|line)\s*:\s*((?:[KQRBNP]?[a-h][1-8x=+#Oo-]+\s*)+)",
    re.IGNORECASE,
)
NEGATION_RE = re.compile(r"(není|ne|not\s+|\bnelze\b|\bbez\b)", re.IGNORECASE)


class ClaimValidation:
    def __init__(
        self, claim_type: str, claim_text: str, passed: bool, field: str = "", detail: str = ""
    ):
        self.claim_type = claim_type
        self.claim_text = claim_text
        self.passed = passed
        self.field = field
        self.detail = detail

    def to_dict(self) -> dict:
        return {
            "claim_type": self.claim_type,
            "claim_text": self.claim_text,
            "passed": self.passed,
            "field": self.field,
            "detail": self.detail,
        }


def _validate_check(text: str, bfs: BlunderFactSheet) -> Optional[ClaimValidation]:
    m = CHECK_RE.search(text)
    if not m:
        return None
    raw = m.group(0).lower()
    positive = raw not in ("nedává šach", "není šach", "not check")
    passed = check_check_claim(positive, bfs.board_state.was_in_check)
    field = "board_state.was_in_check"
    detail = f"claim={'check' if positive else 'not check'} actual={bfs.board_state.was_in_check}"
    return ClaimValidation("check", text, passed, field, detail)


def _validate_eval(text: str, bfs: BlunderFactSheet) -> Optional[ClaimValidation]:
    m = EVAL_RE.search(text)
    if not m:
        return None
    claimed = float(m.group(1))
    refs = [v for v in [bfs.eval_before, bfs.eval_after] if v is not None]
    refs += [el.eval_cp for el in bfs.engine_lines if el.eval_cp is not None]
    passed = check_eval_claim(claimed, refs)
    detail = f"claimed={claimed:.0f}cp refs={[f'{r:.0f}' for r in refs]}"
    return ClaimValidation(
        "eval", text, passed, "eval_before/eval_after/engine_lines[].eval_cp", detail
    )


def _validate_winprob(text: str, bfs: BlunderFactSheet) -> Optional[ClaimValidation]:
    m = WINPROB_RE.search(text)
    if not m:
        return None
    claimed = float(m.group(1))
    refs = [v for v in [bfs.win_prob_before, bfs.win_prob_after] if v is not None]
    refs += [el.win_prob for el in bfs.engine_lines if el.win_prob is not None]
    passed = check_eval_claim(claimed, [r * 100 for r in refs], tol=2.0)
    detail = f"claimed={claimed}% refs={[f'{r * 100:.0f}%' for r in refs]}"
    return ClaimValidation(
        "win-prob", text, passed, "win_prob_before/win_prob_after/engine_lines[].win_prob", detail
    )


def _validate_variation(text: str, bfs: BlunderFactSheet) -> Optional[ClaimValidation]:
    m = VARIATION_RE.search(text)
    if not m:
        return None
    moves = m.group(1).strip().split()
    pvs = [el.pv for el in bfs.engine_lines if el.pv]
    passed = check_variation_claim(moves, pvs)
    detail = f"claimed={' '.join(moves)} pvs={[' '.join(p[:3]) for p in pvs]}"
    return ClaimValidation("variation", text, passed, "engine_lines[].pv", detail)


def _validate_square_refs(text: str, bfs: BlunderFactSheet) -> Optional[ClaimValidation]:
    squares = SQUARE_RE.findall(text)
    for sq in squares:
        is_negated = bool(NEGATION_RE.search(text))
        if "x" in sq:
            passed = check_capture_claim(sq, bfs.legal_moves.captures)
            if is_negated:
                passed = not passed
            detail = f"capture={sq} in_legal={sq in bfs.legal_moves.captures}"
            return ClaimValidation("capture", text, passed, "legal_moves.captures", detail)
        if sq.startswith("K") and len(sq) >= 2:
            in_king = sq in bfs.legal_moves.king_moves
            passed = in_king
            if is_negated:
                passed = not passed
            detail = f"king_move={sq} in_legal={in_king}"
            return ClaimValidation("king-move", text, passed, "legal_moves.king_moves", detail)
        if check_piece_on_square(sq, bfs.fen_before):
            return ClaimValidation("piece-on-square", text, True, "fen_before", f"{sq} in fen")
    return None


CLAIM_VALIDATORS = [
    _validate_check,
    _validate_eval,
    _validate_winprob,
    _validate_variation,
    _validate_square_refs,
]


def validate_narrative(text: str, bfs_list: list[BlunderFactSheet]) -> list[ClaimValidation]:
    """Validate full narrative text against all BlunderFactSheets."""
    results = []
    for bfs in bfs_list:
        validated_this_bfs = False
        for sent in re.split(r"(?<=[.!?])\s+", text):
            sent = sent.strip()
            if not sent:
                continue
            for validator in CLAIM_VALIDATORS:
                result = validator(sent, bfs)
                if result is not None:
                    results.append(result)
                    validated_this_bfs = True
                    break
        if not validated_this_bfs and bfs_list:
            pass
    return results


def has_unsupported_claims(text: str, bfs_list: list[BlunderFactSheet]) -> bool:
    return any(not r.passed for r in validate_narrative(text, bfs_list))


def extract_unsupported_claims(text: str, bfs_list: list[BlunderFactSheet]) -> list[dict]:
    return [r.to_dict() for r in validate_narrative(text, bfs_list) if not r.passed]
