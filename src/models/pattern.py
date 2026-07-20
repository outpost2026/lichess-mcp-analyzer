from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PatternDef:
    id: str
    name: str
    pattern_type: str
    mechanism: str
    it_analogy: str
    detection_method: str
    severity: str
    mitigation: str
    detection_rules: dict = field(default_factory=dict)
    min_games: int = 3
    min_occurrences: int = 2


@dataclass
class PatternMatch:
    pattern_id: str
    pattern_name: str
    confidence: float
    evidence: list[dict]
    game_ids: list[str]
    frequency: int
    severity: str
    hypothesis: Optional[str] = None
    compression_ratio: Optional[float] = None


@dataclass
class PatternLibrary:
    patterns: dict[str, PatternDef] = field(default_factory=dict)

    def load_baseline(self):
        patterns = [
            PatternDef(
                id="A",
                name="Anonymous effect",
                pattern_type="trigger",
                mechanism="Absence of rating lowers perceived threat",
                it_analogy="Production deployment without dry-run",
                detection_method="compare_blunder_rate",
                severity="high",
                mitigation="Assign imaginary 2700 rating; before every anonymous game say 'This opponent is Magnus Carlsen'",
            ),
            PatternDef(
                id="B",
                name="Automatic grab",
                pattern_type="author_error",
                mechanism="Capturing without checking opponent's counterplay",
                it_analogy="git push --force",
                detection_method="capture_eval_drop",
                severity="high",
                mitigation="3-sec pause + 'A CO ON?' before every capture; check for discovered attacks first",
            ),
            PatternDef(
                id="C",
                name="Attention tunneling",
                pattern_type="mechanism",
                mechanism="Local tactical stimulus overrides global evaluation",
                it_analogy="Fixing one bug while creating another",
                detection_method="sector_focus_sequence",
                severity="medium",
                mitigation="Set 15-min timer during debugging; ask 'Has a new problem emerged elsewhere?'",
            ),
            PatternDef(
                id="G",
                name="Color as modulator",
                pattern_type="stylistic_shift",
                mechanism="As Black patient; as White impulsive",
                it_analogy="Proactive vs reactive dev roles",
                detection_method="compare_per_color",
                severity="high",
                mitigation="Play White as if Black; imagine being down a pawn to compensate for impulsivity",
            ),
            PatternDef(
                id="I",
                name="Bait trap",
                pattern_type="strategy",
                mechanism="Leave hanging piece to punish opponent's automatic grab",
                it_analogy="Honeypot endpoint",
                detection_method="bait_detection",
                severity="low",
                min_occurrences=1,
                mitigation="Core strength — continue developing; track bait success rate per opening",
            ),
            PatternDef(
                id="J",
                name="Impulsive check block",
                pattern_type="author_error",
                mechanism="Blocking a check with a piece without calculating king safety or material loss",
                it_analogy="Silencing an alert instead of fixing the root cause",
                detection_method="check_block_analysis",
                severity="high",
                min_occurrences=1,
                mitigation="When in check: evaluate king moves before considering blocks; practice check-response puzzles",
            ),
            PatternDef(
                id="O",
                name="Repetition avoidance greed",
                pattern_type="author_error",
                mechanism="Refusing threefold repetition leads to collapse",
                it_analogy="Refusing to merge stable PR",
                detection_method="repetition_refusal",
                severity="critical",
                mitigation="5-sec pause + 'A CO ON?' before refusing; evaluate opponent's next check",
            ),
            PatternDef(
                id="P",
                name="Visual misrecognition",
                pattern_type="author_error",
                mechanism="Mistaking non-forcing move for forcing sequence",
                it_analogy="Assuming function is idempotent by name alone",
                detection_method="forcing_move_classification",
                severity="high",
                mitigation="Before a piece move that looks 'forcing': ask 'Is it actually forcing, or just a visual illusion?'",
            ),
            PatternDef(
                id="Q",
                name="Active defense",
                pattern_type="recovery_strategy",
                mechanism="Creating threats under material deficit",
                it_analogy="Server under DDoS returning fake 200 OKs",
                detection_method="defensive_phase_analysis",
                severity="low",
                mitigation="Core strength — but prevent lost positions first; never resign, complicate the position",
            ),
            PatternDef(
                id="Q1",
                name="Desperate Gambit Mode",
                pattern_type="recovery_strategy",
                mechanism="When objectively lost (eval < -3), reject simplifying exchanges, seek tactical chaos on opponent's kingside, and wait for opponent's automatic grab",
                it_analogy="When server is crashing, start random port scans to confuse the attacker instead of graceful shutdown",
                detection_method="desperate_gambit_analysis",
                severity="low",
                min_occurrences=1,
                mitigation="When lost: reject queen exchanges, keep pieces active, create checks and threats — opponent will blunder in time pressure",
            ),
            PatternDef(
                id="R",
                name="Endgame relaxation",
                pattern_type="author_error",
                mechanism="Losing concentration when ahead materially in endgame — passive move throws away advantage",
                it_analogy="Deploying to prod on Friday after a perfect sprint",
                detection_method="endgame_positional_blunder",
                severity="high",
                mitigation="Before every endgame move when winning: check for opponent's counterplay first, not your own plan.",
            ),
        ]
        for p in patterns:
            self.patterns[p.id] = p
        return self
