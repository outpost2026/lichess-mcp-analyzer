"""Pattern Definition Model — Lossy Compression Core.

Pattern detection implements Lossy Compression (T. Mikolov / CPM):
Find patterns that describe reality with maximum entropy value
per minimum tokens.

CR = N / (C_impl + C_udrz) is ONLY meaningful when N = count of
instances of THE SAME THING. Semantic integrity is a prerequisite:
if a pattern's name/mechanism/hypothesis does not match its code
detection, the compression ratio measures noise, not signal.
Every pattern must be falsifiable: the lexical description must
match the code detection logic exactly. Lossy compression loses
its unique advantage (high-confidence description of reality)
when the semantic layer is incorrect."""

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
                mechanism="Local tactical stimulus overrides global evaluation — attention breakdown manifests as consecutive errors regardless of board sector",
                it_analogy="Fixing one bug while creating another",
                detection_method="consecutive_errors",
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
                name="Bait trap (concept)",
                pattern_type="concept",
                mechanism="Conceptual: player deliberately leaves a piece seemingly hanging (eval-neutral or slightly suboptimal) to lure opponent into an automatic-grab blunder. Requires multi-layer intent inference: (1) bait move before opponent's capture, (2) opponent takes, (3) player has a forcing refutation visible to Stockfish before the bait move.",
                it_analogy="Honeypot endpoint in a DMZ — cannot be detected by static rules, only by retrospective intent analysis",
                detection_method="manual_only",
                severity="low",
                min_occurrences=1,
                mitigation="Core strength — continue developing; track bait success rate per opening manually",
            ),
            PatternDef(
                id="I2",
                name="Opponent's gift exploitation",
                pattern_type="strategy",
                mechanism="Capitalising on opponent's suboptimal capture — the player profits from opponent's automatic grab",
                it_analogy="Exploiting a misconfigured firewall rule",
                detection_method="gift_exploitation",
                severity="low",
                min_occurrences=1,
                mitigation="Core strength — continue developing; confirm intent vs luck per instance",
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
                name="Stagnační panika",
                pattern_type="author_error",
                mechanism="Flat eval plateau (3+ consecutive moves with <30cp swing) followed by blunder within 6 moves — player panics from positional stagnation and forces a losing move",
                it_analogy="Deploying a hotfix because CI has been green for 3 hours — no actual problem, but the silence feels dangerous",
                detection_method="stagnation_fallback",
                severity="critical",
                mitigation="When eval stays flat for 2+ moves: pause and ask 'Je to opravdu stagnace, nebo jen pozicni klid?' — do not force complications without a concrete target",
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
                mechanism="Creating threats under material deficit — active counterplay instead of passive defense",
                it_analogy="Server under DDoS returning fake 200 OKs",
                detection_method="defensive_phase_analysis",
                severity="low",
                mitigation="Core strength — but prevent lost positions first; never resign, complicate the position",
            ),
            PatternDef(
                id="Q2",
                name="Win despite blunder",
                pattern_type="recovery_strategy",
                mechanism="Winning a game despite making one or more large blunders — resilience or opponent's failure to capitalise",
                it_analogy="Production incident survived without rollback",
                detection_method="blundered_but_won",
                severity="low",
                mitigation="Reinforce — core strength. Review blunders to determine if resilience or luck.",
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
            PatternDef(
                id="S",
                name="Capture aversion under check",
                pattern_type="author_error",
                mechanism="When in check, player reflexively moves the king or blocks instead of capturing the checking piece -- 'king in danger' reflex suppresses the capture option",
                it_analogy="Silencing a process monitor alert by killing the monitor instead of reading the alert",
                detection_method="capture_aversion_under_check",
                severity="critical",
                min_occurrences=1,
                mitigation="When in check: pause and ask 'Muzu brat sachujici figuru?' before considering king moves or blocks.",
            ),
            PatternDef(
                id="N",
                name="X-ray pin violation",
                pattern_type="author_error",
                mechanism="Player moves a piece that is x-ray pinned to a higher-value piece behind it, losing material or position because the pin was ignored",
                it_analogy="Modifying a config file without checking if a service depends on it -- the dependency (pin) breaks when you move the config",
                detection_method="pinned_piece_blunder",
                severity="high",
                min_occurrences=1,
                mitigation="Before moving any piece: check if it's pinned to the king or queen. If pinned, verify the move doesn't expose the higher-value piece.",
            ),
        ]
        for p in patterns:
            self.patterns[p.id] = p
        return self
