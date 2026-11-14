from dataclasses import dataclass, field, asdict
from typing import Optional

from lichess_analyzer_mcp.models.analysis import BlunderFactSheet

# P0-3 (D1): ktera faze je autoritativni pro detektory.
# "ply_segment" = historicky stav (phase = segment podle ply, vychozi);
# "material" = chess_phase (material-based, board_facts.chess_phase).
PHASE_METHOD_DEFAULT = "ply_segment"
PHASE_METHOD_MATERIAL = "material"

PHASES = ("opening", "middlegame", "endgame")
FLAGGED_CLASSES = ("blunder", "mistake", "inaccuracy")

# P1: `accuracy` je interní lineární skóre, ne kalibrovaná "Lichess accuracy".
# Metoda je součástí payloadu, aby report nikdy netvrdil standardní metriku.
ACCURACY_METHOD_INTERNAL = "internal_cp_linear"


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
    # D12: eval of the engine's best move from the mover's POV. `centipawn_loss`
    # is `max(0, best_eval - eval_after)`, so without this anchor the published
    # loss cannot be reconstructed from the eval pair (different searches).
    best_eval: Optional[float] = None
    was_in_check: bool = False
    gives_check: bool = False
    # P0.2: an analytical result is either measured or explicitly absent.
    analyzed: bool = True
    # P0.5: deterministic explanation surface for every flagged move.
    engine_lines: list[dict] = field(default_factory=list)
    played_rank: int = 0
    explanation: str = ""
    explanation_source: str = "none"
    # P0-3: ktera faze je autoritativni pro detektory (phase_method)
    # a materialova faze pozice ("" = nevypoctena, napr. legacy cache).
    phase_method: str = PHASE_METHOD_DEFAULT
    chess_phase: str = ""

    @property
    def segment(self) -> str:
        """Ply-segment podle ply (P0-3: ``phase`` je alias na segment, D1)."""
        return self.phase

    def to_dict(self) -> dict:
        data = asdict(self)
        # P0-3: publikujeme i alias segment (D1: v payloadu obojí).
        data["segment"] = self.phase
        # Contract: an unmeasured move must never look like a perfect one.
        if not self.analyzed:
            data["centipawn_loss"] = None
        return data

    @staticmethod
    def from_dict(d: dict) -> "MoveAnalysis":
        valid = {k: v for k, v in d.items() if k in MoveAnalysis.__dataclass_fields__}
        # Legacy payload zna jen `phase`; novy klic `segment` neni field
        # (alias je property) a ve filtru by zmizel - phase je povinny.
        if "phase" not in valid:
            valid["phase"] = d.get("segment", "")
        return MoveAnalysis(**valid)


def effective_phase(move: MoveAnalysis) -> str:
    """Fáze, podle které detektory rozhodují (P0-3: oba režimy `phase_method`).

    - `phase_method == "material"` a vyplněné `chess_phase` → chess_phase;
    - jinak (výchozí `ply_segment`, i legacy data bez nových klíčů) → `segment`,
      což je alias `phase` (ply-segmentace).

    Výchozí režim je chováním identický starému `move.phase == "endgame"`.
    """
    if getattr(move, "phase_method", PHASE_METHOD_DEFAULT) == PHASE_METHOD_MATERIAL:
        chess_phase = (getattr(move, "chess_phase", "") or "").strip()
        if chess_phase:
            return chess_phase
    return getattr(move, "segment", "") or getattr(move, "phase", "") or ""


def phase_stats_by(moves: list[MoveAnalysis], phase_of) -> dict:
    """Agregace měřených tahů podle jedné fázové funkce.

    Jediný zdroj pravdy pro všechny tři publikované řezy:

    - `phase_stats`     → `effective_phase` (stejná fáze, jakou vidí detektory),
    - `segment_stats`   → `segment` (ply-segmentace, historické chování),
    - `chess_phase_stats` → `chess_phase` (material-based, jen měřené tahy).

    Tah bez fáze (např. legacy cache bez `chess_phase`) se do daného řezu
    nezapočítá; chybějící fáze se nikdy nedopočítává odhadem.
    """
    stats: dict = {}
    for phase in PHASES:
        phase_moves = [m for m in moves if m.analyzed and phase_of(m) == phase]
        if not phase_moves:
            continue
        acpl = sum(m.centipawn_loss for m in phase_moves) / len(phase_moves)
        acc = sum(max(0, 100 - m.centipawn_loss * 0.15) for m in phase_moves) / len(phase_moves)
        flagged = sum(1 for m in phase_moves if m.classification in FLAGGED_CLASSES)
        stats[phase] = {
            "acpl": round(acpl, 1),
            "accuracy": round(acc, 1),
            "move_count": len(phase_moves),
            # `errors` je legacy klíč kontraktu 1.2 (prompt/LLM cache); hodnota
            # je totožná s `flagged` v detailed payloadu.
            "errors": flagged,
        }
    return stats


@dataclass
class GameAnalysis:
    game: GameSummary
    moves: list[MoveAnalysis] = field(default_factory=list)
    total_acpl: float = 0.0
    accuracy: float = 0.0
    # P1: `accuracy` je alias `internal_accuracy_score`; metoda je explicitní.
    accuracy_method: str = ACCURACY_METHOD_INTERNAL
    internal_accuracy_score: float = 0.0
    blunders: list[MoveAnalysis] = field(default_factory=list)
    mistakes: list[MoveAnalysis] = field(default_factory=list)
    inaccuracies: list[MoveAnalysis] = field(default_factory=list)
    phase_stats: dict = field(default_factory=dict)
    # P1: tři fáze-řezy. `phase_stats` = effective_phase (autoritativní pro
    # detektory), `segment_stats` = ply segment, `chess_phase_stats` = material.
    segment_stats: dict = field(default_factory=dict)
    chess_phase_stats: dict = field(default_factory=dict)
    blunder_fact_sheets: list[BlunderFactSheet] = field(default_factory=list)
    evaluation_errors: int = 0
    # T2.2: total plies in the game (both sides), so a payload can say
    # "player 20 of 40 plies" without guessing. 0 = legacy cache without it.
    game_plies_total: int = 0
    # P0.1/P0.2: observable contract fields.
    unanalyzed_plies: list[int] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)
    timings: dict = field(default_factory=dict)
    engine_calls: int = 0
    engine_timeouts: int = 0
    engine_retries: int = 0
    deadline_s: float = 0.0
    deadline_hit: bool = False
    mode: str = "fast"
    # Runtime-only cache provenance; intentionally not serialized by to_dict().
    _cache_hit: bool = False
    _cache_layer: str = "none"

    def to_dict(self) -> dict:
        return {
            "game": self.game.to_dict(),
            "moves": [m.to_dict() for m in self.moves],
            "total_acpl": self.total_acpl,
            "accuracy": self.accuracy,
            "accuracy_method": self.accuracy_method,
            "internal_accuracy_score": self.internal_accuracy_score,
            "blunders": [m.to_dict() for m in self.blunders],
            "mistakes": [m.to_dict() for m in self.mistakes],
            "inaccuracies": [m.to_dict() for m in self.inaccuracies],
            "phase_stats": self.phase_stats,
            "segment_stats": self.segment_stats,
            "chess_phase_stats": self.chess_phase_stats,
            "blunder_fact_sheets": [bfs.to_dict() for bfs in self.blunder_fact_sheets],
            "evaluation_errors": self.evaluation_errors,
            "game_plies_total": self.game_plies_total,
            "unanalyzed_plies": self.unanalyzed_plies,
            "errors": self.errors,
            "timings": self.timings,
            "engine_calls": self.engine_calls,
            "engine_timeouts": self.engine_timeouts,
            "engine_retries": self.engine_retries,
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
        self.internal_accuracy_score = self._compute_accuracy()
        # `accuracy` zůstává jako kompatibilní alias (1.2 kontrakt); nový
        # payload publikuje i metodu, aby skóre nešlo zaměnit za Lichess %.
        self.accuracy = self.internal_accuracy_score
        # P1: phase_stats je autoritativní řez (effective_phase), takže souhrn
        # a detektory mluví o stejné fázi. Oba alternativní řezy se publikují
        # vedle, aby šel rozdíl kdykoli auditovat.
        self.phase_stats = self._compute_phase_stats()
        self.segment_stats = self._compute_segment_stats()
        self.chess_phase_stats = self._compute_chess_phase_stats()

    def _compute_accuracy(self) -> float:
        """Interní lineární skóre: `mean(max(0, 100 - 0.15 * cp_loss))`.

        Není to kalibrovaná pravděpodobnost ani Lichess accuracy; je to
        deterministický souhrn cp_loss pro srovnání her mezi sebou. Metoda se
        publikuje jako `accuracy_method = internal_cp_linear`.
        """
        measured = [m for m in self.moves if m.analyzed]
        if not measured:
            return 0.0
        total = sum(max(0, 100 - m.centipawn_loss * 0.15) for m in measured)
        return round(max(0, min(100, total / len(measured))), 1)

    def _compute_phase_stats(self) -> dict:
        """Souhrn podle `effective_phase` — stejná fáze, jakou vidí detektory."""
        return phase_stats_by(self.moves, effective_phase)

    def _compute_segment_stats(self) -> dict:
        """Souhrn podle ply segmentu (historické chování, auditní řez)."""
        return phase_stats_by(self.moves, lambda m: m.segment)

    def _compute_chess_phase_stats(self) -> dict:
        """Souhrn podle material-based `chess_phase`; prázdná fáze se vynechá."""
        return phase_stats_by(self.moves, lambda m: (m.chess_phase or "").strip())

    @staticmethod
    def from_dict(d: dict) -> "GameAnalysis":
        analysis = GameAnalysis(
            game=GameSummary.from_dict(d["game"]),
            moves=[MoveAnalysis.from_dict(m) for m in d["moves"]],
            total_acpl=d.get("total_acpl", 0.0),
            accuracy=d.get("accuracy", 0.0),
            accuracy_method=d.get("accuracy_method", ACCURACY_METHOD_INTERNAL),
            internal_accuracy_score=d.get("internal_accuracy_score", d.get("accuracy", 0.0)),
            blunders=[MoveAnalysis.from_dict(m) for m in d.get("blunders", [])],
            mistakes=[MoveAnalysis.from_dict(m) for m in d.get("mistakes", [])],
            inaccuracies=[MoveAnalysis.from_dict(m) for m in d.get("inaccuracies", [])],
            phase_stats=d.get("phase_stats", {}),
            segment_stats=d.get("segment_stats", {}),
            chess_phase_stats=d.get("chess_phase_stats", {}),
            blunder_fact_sheets=[
                BlunderFactSheet.from_dict(bfs) for bfs in d.get("blunder_fact_sheets", [])
            ],
            evaluation_errors=d.get("evaluation_errors", 0),
            game_plies_total=d.get("game_plies_total", 0),
            unanalyzed_plies=d.get("unanalyzed_plies", []),
            errors=d.get("errors", []),
            timings=d.get("timings", {}),
            engine_calls=d.get("engine_calls", 0),
            engine_timeouts=d.get("engine_timeouts", 0),
            deadline_s=d.get("deadline_s", 0.0),
            deadline_hit=d.get("deadline_hit", False),
            mode=d.get("mode", "fast"),
        )
        # Legacy cache nemá alternativní řezy; dopočítají se z tahů (determinismus).
        # `phase_stats` z cache se nepřepisuje — starší payload mohl vzniknout
        # jinou fázovou metodou a jeho hodnota je součástí identity cache.
        if not analysis.segment_stats:
            analysis.segment_stats = analysis._compute_segment_stats()
        if not analysis.chess_phase_stats:
            analysis.chess_phase_stats = analysis._compute_chess_phase_stats()
        return analysis
