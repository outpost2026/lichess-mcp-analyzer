from dataclasses import dataclass, field
from typing import Optional


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
