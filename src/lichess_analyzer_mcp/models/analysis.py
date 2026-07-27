from dataclasses import dataclass, field, asdict
from typing import Optional


DETECTOR_VERSION = "DBCL-20260727-dev"


@dataclass
class BoardState:
    was_in_check: bool = False
    checking_pieces: list[str] = field(default_factory=list)
    capture_checking_piece_possible: bool = False
    king_capture_possible: bool = False
    king_capture_played: Optional[bool] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "BoardState":
        valid = {k: v for k, v in d.items() if k in BoardState.__dataclass_fields__}
        return BoardState(**valid)


@dataclass
class LegalMovesSummary:
    total: int = 0
    captures: list[str] = field(default_factory=list)
    king_moves: list[str] = field(default_factory=list)
    blocks: list[str] = field(default_factory=list)
    checks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "LegalMovesSummary":
        valid = {k: v for k, v in d.items() if k in LegalMovesSummary.__dataclass_fields__}
        return LegalMovesSummary(**valid)


@dataclass
class EngineLine:
    rank: int = 0
    move_san: str = ""
    eval_cp: float = 0.0
    win_prob: Optional[float] = None
    pv: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "EngineLine":
        valid = {k: v for k, v in d.items() if k in EngineLine.__dataclass_fields__}
        return EngineLine(**valid)


@dataclass
class PatternMatchInfo:
    pattern_id: str = ""
    pattern_name: str = ""
    confidence: float = 0.0
    evidence: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "PatternMatchInfo":
        valid = {k: v for k, v in d.items() if k in PatternMatchInfo.__dataclass_fields__}
        return PatternMatchInfo(**valid)


@dataclass
class ContextWindowMove:
    ply: int = 0
    move_san: str = ""
    eval_after: float = 0.0
    win_prob_after: Optional[float] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "ContextWindowMove":
        valid = {k: v for k, v in d.items() if k in ContextWindowMove.__dataclass_fields__}
        return ContextWindowMove(**valid)


@dataclass
class ContextWindow:
    moves_before: list[ContextWindowMove] = field(default_factory=list)
    moves_after: list[ContextWindowMove] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "moves_before": [m.to_dict() for m in self.moves_before],
            "moves_after": [m.to_dict() for m in self.moves_after],
        }

    @staticmethod
    def from_dict(d: dict) -> "ContextWindow":
        return ContextWindow(
            moves_before=[ContextWindowMove.from_dict(m) for m in d.get("moves_before", [])],
            moves_after=[ContextWindowMove.from_dict(m) for m in d.get("moves_after", [])],
        )


@dataclass
class BlunderFactSheet:
    game_id: str = ""
    ply: int = 0
    move_played_san: str = ""
    move_played_uci: str = ""
    centipawn_loss: float = 0.0
    eval_before: Optional[float] = None
    eval_after: Optional[float] = None
    win_prob_before: Optional[float] = None
    win_prob_after: Optional[float] = None
    win_prob_delta: Optional[float] = None
    fen_before: str = ""
    board_state: BoardState = field(default_factory=BoardState)
    legal_moves: LegalMovesSummary = field(default_factory=LegalMovesSummary)
    engine_lines: list[EngineLine] = field(default_factory=list)
    played_move_rank: int = 0
    phase: str = ""
    pattern_matches: list[PatternMatchInfo] = field(default_factory=list)
    detector_version: str = DETECTOR_VERSION
    context_window: ContextWindow = field(default_factory=ContextWindow)

    def to_dict(self) -> dict:
        return {
            "game_id": self.game_id,
            "ply": self.ply,
            "move_played_san": self.move_played_san,
            "move_played_uci": self.move_played_uci,
            "centipawn_loss": self.centipawn_loss,
            "eval_before": self.eval_before,
            "eval_after": self.eval_after,
            "win_prob_before": self.win_prob_before,
            "win_prob_after": self.win_prob_after,
            "win_prob_delta": self.win_prob_delta,
            "fen_before": self.fen_before,
            "board_state": self.board_state.to_dict(),
            "legal_moves": self.legal_moves.to_dict(),
            "engine_lines": [e.to_dict() for e in self.engine_lines],
            "played_move_rank": self.played_move_rank,
            "phase": self.phase,
            "pattern_matches": [p.to_dict() for p in self.pattern_matches],
            "detector_version": self.detector_version,
            "context_window": self.context_window.to_dict(),
        }

    @staticmethod
    def from_dict(d: dict) -> "BlunderFactSheet":
        bfs = BlunderFactSheet(
            game_id=d.get("game_id", ""),
            ply=d.get("ply", 0),
            move_played_san=d.get("move_played_san", ""),
            move_played_uci=d.get("move_played_uci", ""),
            centipawn_loss=d.get("centipawn_loss", 0.0),
            eval_before=d.get("eval_before"),
            eval_after=d.get("eval_after"),
            win_prob_before=d.get("win_prob_before"),
            win_prob_after=d.get("win_prob_after"),
            win_prob_delta=d.get("win_prob_delta"),
            fen_before=d.get("fen_before", ""),
            board_state=BoardState.from_dict(d.get("board_state", {})),
            legal_moves=LegalMovesSummary.from_dict(d.get("legal_moves", {})),
            engine_lines=[EngineLine.from_dict(e) for e in d.get("engine_lines", [])],
            played_move_rank=d.get("played_move_rank", 0),
            phase=d.get("phase", ""),
            pattern_matches=[PatternMatchInfo.from_dict(p) for p in d.get("pattern_matches", [])],
            detector_version=d.get("detector_version", DETECTOR_VERSION),
            context_window=ContextWindow.from_dict(d.get("context_window", {})),
        )
        return bfs


@dataclass
class PositionAnalysis:
    fen: str
    eval_cp: float
    win_prob: float
    mate_in: Optional[int]
    best_moves: list[dict] = field(default_factory=list)
    opening_name: Optional[str] = None
    opening_eco: Optional[str] = None


@dataclass
class WeaknessReport:
    username: str
    total_games_analyzed: int
    total_acpl: float
    blunder_count: int
    mistake_count: int
    inaccuracy_count: int
    phase_weaknesses: dict = field(default_factory=dict)
    tactical_blind_spots: dict = field(default_factory=dict)
    leaky_openings: list[dict] = field(default_factory=list)
    pattern_frequencies: dict = field(default_factory=dict)
    top_weaknesses: list[str] = field(default_factory=list)
    elo_trend: list[dict] = field(default_factory=list)
