from dataclasses import dataclass, field, asdict
from typing import Optional

from lichess_analyzer_mcp.models.analysis import BlunderFactSheet


@dataclass
class GameSummary:
    id: str
    platform: str
    opening: str
    opening_eco: str
    color: str
    result: str
    player_name: str = ""
    opponent_name: str = ""
    player_rating: Optional[int] = None
    opponent_rating: Optional[int] = None
    time_control: str = ""
    date: str = ""
    url: str = ""
    automatic_grab: bool = False
    bait_trap: bool = False
    metacognition: str = ""
    elo_estimate: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "GameSummary":
        valid = {k: v for k, v in d.items() if k in GameSummary.__dataclass_fields__}
        return GameSummary(**valid)


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
    fen: str = ""
    was_in_check: bool = False
    # P0.2: an analytical result is either measured or explicitly absent.
    analyzed: bool = True
    # P0.5: deterministic explanation surface for every flagged move.
    engine_lines: list[dict] = field(default_factory=list)
    played_rank: int = 0
    explanation: str = ""
    explanation_source: str = "none"

    def to_dict(self) -> dict:
        data = asdict(self)
        # Contract v1.1: an unmeasured move must never look like a perfect one.
        if not self.analyzed:
            data["centipawn_loss"] = None
        return data

    @staticmethod
    def from_dict(d: dict) -> "MoveAnalysis":
        valid = {k: v for k, v in d.items() if k in MoveAnalysis.__dataclass_fields__}
        return MoveAnalysis(**valid)


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
    blunder_fact_sheets: list[BlunderFactSheet] = field(default_factory=list)
    evaluation_errors: int = 0
    # P0.1/P0.2: observable contract fields.
    unanalyzed_plies: list[int] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    timings: dict = field(default_factory=dict)
    engine_calls: int = 0
    engine_timeouts: int = 0
    deadline_s: float = 0.0
    deadline_hit: bool = False
    mode: str = "fast"

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
            "blunder_fact_sheets": [bfs.to_dict() for bfs in self.blunder_fact_sheets],
            "evaluation_errors": self.evaluation_errors,
            "unanalyzed_plies": self.unanalyzed_plies,
            "errors": self.errors,
            "timings": self.timings,
            "engine_calls": self.engine_calls,
            "engine_timeouts": self.engine_timeouts,
            "deadline_s": self.deadline_s,
            "deadline_hit": self.deadline_hit,
            "mode": self.mode,
        }

    def auto_annotate(self) -> None:
        capture_blunders = [
            m
            for m in self.moves
            if m.analyzed
            and m.classification in ("blunder", "mistake")
            and "x" in m.move_san
            and m.centipawn_loss >= 100
        ]
        self.game.automatic_grab = len(capture_blunders) > 0
        if self.game.opponent_rating and self.game.opponent_rating > 0:
            self.game.elo_estimate = min(
                max(
                    int(self.game.opponent_rating - self.total_acpl * 0.8),
                    800,
                ),
                2800,
            )
        self.accuracy = self._compute_accuracy()
        self.phase_stats = self._compute_phase_stats()

    def _compute_accuracy(self) -> float:
        measured = [m for m in self.moves if m.analyzed]
        if not measured:
            return 0.0
        total = sum(max(0, 100 - m.centipawn_loss * 0.15) for m in measured)
        return round(max(0, min(100, total / len(measured))), 1)

    def _compute_phase_stats(self) -> dict:
        stats = {}
        for phase in ("opening", "middlegame", "endgame"):
            phase_moves = [m for m in self.moves if m.analyzed and m.phase == phase]
            if not phase_moves:
                continue
            acpl = sum(m.centipawn_loss for m in phase_moves) / len(phase_moves)
            acc = sum(max(0, 100 - m.centipawn_loss * 0.15) for m in phase_moves) / len(phase_moves)
            errors = [
                m for m in phase_moves if m.classification in ("blunder", "mistake", "inaccuracy")
            ]
            stats[phase] = {
                "acpl": round(acpl, 1),
                "accuracy": round(acc, 1),
                "move_count": len(phase_moves),
                "errors": len(errors),
            }
        return stats

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
            blunder_fact_sheets=[
                BlunderFactSheet.from_dict(bfs) for bfs in d.get("blunder_fact_sheets", [])
            ],
            evaluation_errors=d.get("evaluation_errors", 0),
            unanalyzed_plies=d.get("unanalyzed_plies", []),
            errors=d.get("errors", []),
            timings=d.get("timings", {}),
            engine_calls=d.get("engine_calls", 0),
            engine_timeouts=d.get("engine_timeouts", 0),
            deadline_s=d.get("deadline_s", 0.0),
            deadline_hit=d.get("deadline_hit", False),
            mode=d.get("mode", "fast"),
        )

