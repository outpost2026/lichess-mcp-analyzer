"""CompressibilityValidator: computes compression_ratio for pattern matches.

Based on Mikolov compression philosophy — a pattern is valid if it compresses
game data better than raw data. Maps to KALIBRACE_PLAN v2.3 section 2.5.
"""

from lichess_analyzer_mcp.models.game import GameAnalysis
from lichess_analyzer_mcp.models.pattern import PatternMatch

PATTERN_BASE_COST = 10


def compute_compression(match: PatternMatch, analyses: list[GameAnalysis]) -> PatternMatch:
    total_moves = sum(len(a.moves) for a in analyses)
    if total_moves == 0:
        match.compression_ratio = 1.0
        return match
    evidence_count = len(match.evidence) if match.evidence else 1
    exception_cost = evidence_count * 2
    pattern_cost = PATTERN_BASE_COST + exception_cost
    compression_ratio = total_moves / pattern_cost
    match.compression_ratio = round(compression_ratio, 1)
    return match


def compression_score(match: PatternMatch) -> float:
    if match.compression_ratio is None:
        return 0.0
    return min(match.compression_ratio / 10.0, 1.0)
