from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PlayerProfile:
    username: str
    platform: str
    rating: dict = field(default_factory=dict)
    rating_history: list[dict] = field(default_factory=list)
    total_games: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    top_openings: list[dict] = field(default_factory=list)
    perf_by_time_control: dict = field(default_factory=dict)


@dataclass
class OpeningStats:
    eco: str
    name: str
    games_played: int
    wins: int
    losses: int
    draws: int
    avg_acpl: float
    win_rate: float
