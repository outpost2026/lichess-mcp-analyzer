from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class SRSCard:
    card_id: str
    fen: str
    correct_move_uci: str
    correct_move_san: str
    pattern_id: Optional[str]
    game_id: Optional[str]
    opening: Optional[str]
    phase: str
    centipawn_loss: float
    created_at: str
    due: str
    stability: float = 0.0
    difficulty: float = 0.0
    elapsed_days: int = 0
    scheduled_days: int = 0
    reps: int = 0
    lapses: int = 0
    state: str = "New"
    last_review: Optional[str] = None


@dataclass
class FSRSState:
    cards: dict[str, SRSCard] = field(default_factory=dict)
    total_reviews: int = 0
    total_cards: int = 0
    retention_rate: float = 0.0
