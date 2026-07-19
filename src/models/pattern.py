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
                mitigation="Assign imaginary 2700 rating",
            ),
            PatternDef(
                id="B",
                name="Automatic grab",
                pattern_type="author_error",
                mechanism="Capturing without checking opponent's counterplay",
                it_analogy="git push --force",
                detection_method="capture_eval_drop",
                severity="high",
                mitigation="3-sec pause + A CO ON? before every capture",
            ),
            PatternDef(
                id="C",
                name="Attention tunneling",
                pattern_type="mechanism",
                mechanism="Local tactical stimulus overrides global evaluation",
                it_analogy="Fixing one bug while creating another",
                detection_method="sector_focus_sequence",
                severity="medium",
                mitigation="Set 15-min timer; check other board areas",
            ),
            PatternDef(
                id="G",
                name="Color as modulator",
                pattern_type="stylistic_shift",
                mechanism="As Black patient; as White impulsive",
                it_analogy="Proactive vs reactive dev roles",
                detection_method="compare_per_color",
                severity="high",
                mitigation="Play White as if Black",
            ),
            PatternDef(
                id="I",
                name="Bait trap",
                pattern_type="strategy",
                mechanism="Leave hanging piece to punish opponent's automatic grab",
                it_analogy="Honeypot endpoint",
                detection_method="bait_detection",
                severity="low",
                mitigation="Core strength — continue developing",
            ),
            PatternDef(
                id="O",
                name="Repetition avoidance greed",
                pattern_type="author_error",
                mechanism="Refusing threefold repetition leads to collapse",
                it_analogy="Refusing to merge stable PR",
                detection_method="repetition_refusal",
                severity="critical",
                mitigation="5-sec pause + draw evaluation before refusing",
            ),
            PatternDef(
                id="P",
                name="Visual misrecognition",
                pattern_type="author_error",
                mechanism="Mistaking non-forcing move for forcing sequence",
                it_analogy="Assuming function is idempotent by name alone",
                detection_method="forcing_move_classification",
                severity="high",
                mitigation="Check if move is actually forcing",
            ),
            PatternDef(
                id="Q",
                name="Active defense",
                pattern_type="recovery_strategy",
                mechanism="Creating threats under material deficit",
                it_analogy="Server under DDoS returning fake 200 OKs",
                detection_method="defensive_phase_analysis",
                severity="low",
                mitigation="Core strength — but prevent lost positions first",
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
