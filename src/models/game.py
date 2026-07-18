from dataclasses import dataclass, field
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
