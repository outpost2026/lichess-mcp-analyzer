from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class GameSummary:
    id: str
    platform: str
    opening: str
    opening_eco: str
    color: str
    result: str
    opponent_name: str
    opponent_rating: Optional[int]
    player_rating: Optional[int]
    time_control: str
    date: str
    url: str

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "GameSummary":
        return GameSummary(**d)


@dataclass
class MoveAnalysis:
    ply: int
    move_uci: str
    move_san: str
    eval_before: float
    eval_after: float
    win_prob_before: float
    win_prob_after: float
    centipawn_loss: float
    classification: str
    best_move_uci: str
    best_move_san: str
    is_tactical_motif: bool
    motif_type: Optional[str]
    phase: str

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "MoveAnalysis":
        return MoveAnalysis(**d)


@dataclass
class GameAnalysis:
    game: GameSummary
    moves: list[MoveAnalysis] = field(default_factory=list)
    total_acpl: float = 0.0
    accuracy: float = 0.0
    blunders: list[MoveAnalysis] = field(default_factory=list)
    mistakes: list[MoveAnalysis] = field(default_factory=list)
    inaccuracies: list[MoveAnalysis] = field(default_factory=list)
    phase_stats: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "game": self.game.to_dict(),
            "moves": [m.to_dict() for m in self.moves],
            "total_acpl": self.total_acpl,
            "accuracy": self.accuracy,
            "blunders": [m.to_dict() for m in self.blunders],
            "mistakes": [m.to_dict() for m in self.mistakes],
            "inaccuracies": [m.to_dict() for m in self.inaccuracies],
            "phase_stats": self.phase_stats,
        }

    @staticmethod
    def from_dict(d: dict) -> "GameAnalysis":
        return GameAnalysis(
            game=GameSummary.from_dict(d["game"]),
            moves=[MoveAnalysis.from_dict(m) for m in d["moves"]],
            total_acpl=d.get("total_acpl", 0.0),
            accuracy=d.get("accuracy", 0.0),
            blunders=[MoveAnalysis.from_dict(m) for m in d.get("blunders", [])],
            mistakes=[MoveAnalysis.from_dict(m) for m in d.get("mistakes", [])],
            inaccuracies=[MoveAnalysis.from_dict(m) for m in d.get("inaccuracies", [])],
            phase_stats=d.get("phase_stats", {}),
        )
