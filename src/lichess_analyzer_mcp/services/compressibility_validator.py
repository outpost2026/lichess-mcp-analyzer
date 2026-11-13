"""Coverage validator for pattern matches (formerly "compressibility validator").

P1 correction: the old module claimed MDL compression, but its formula
`total_moves / (10 + 2 * evidence_count)` grows with corpus size and saturates.
It measures **coverage**, not compression, and it must never set the detector's
`strength` — otherwise a large corpus inflates confidence for a weak pattern.

Current contract:

- `compute_coverage(match, analyses)` fills `compression_ratio`, `coverage_score`
  and `support`; it leaves `strength` untouched.
- `coverage_score` is an ordinal 0..1 proxy: how much of the corpus the pattern
  definition covers relative to its evidence cost. It is not a probability and
  not an MDL length.
- `support` is measured: share of analysed games in which the pattern occurs.
- `hypothesis_confidence` stays None until calibrated on a held-out dataset.

The module keeps the old function names (`compute_compression`,
`compression_score`) as deprecated aliases so existing callers do not break.
"""

from lichess_analyzer_mcp.models.game import GameAnalysis
from lichess_analyzer_mcp.models.pattern import PatternMatch

# Cost of writing the pattern definition itself, in arbitrary "evidence units".
PATTERN_BASE_COST = 10


def compute_coverage(match: PatternMatch, analyses: list[GameAnalysis]) -> PatternMatch:
    """Fill coverage/support fields; never modify `strength`."""
    total_moves = sum(len(a.moves) for a in analyses)
    if total_moves == 0:
        match.compression_ratio = 1.0
        match.coverage_score = round(min(1.0 / PATTERN_BASE_COST, 1.0), 4)
        return match
    evidence_count = len(match.evidence) if match.evidence else 1
    pattern_cost = PATTERN_BASE_COST + evidence_count * 2
    match.compression_ratio = round(total_moves / pattern_cost, 1)
    match.coverage_score = round(min(match.compression_ratio / 10.0, 1.0), 4)
    if analyses:
        match.support = round(len(set(match.game_ids)) / len(analyses), 4)
    return match


def coverage_score(match: PatternMatch) -> float:
    """Ordinal coverage proxy 0..1 (None -> 0.0)."""
    return 0.0 if match.coverage_score is None else match.coverage_score


def entropy_score(match: PatternMatch, analyses: list[GameAnalysis]) -> float:
    """Share of games with the pattern (measured support, not entropy)."""
    if not analyses:
        return 0.0
    return min(len(set(match.game_ids)) / len(analyses), 1.0)


def sample_score(match: PatternMatch, analyses: list[GameAnalysis]) -> float:
    """Relative frequency of the pattern in the corpus."""
    if not analyses:
        return 0.0
    return min(match.frequency / max(len(analyses), 1) * 2, 1.0)


def compute_compression(match: PatternMatch, analyses: list[GameAnalysis]) -> PatternMatch:
    """Deprecated alias for `compute_coverage` (name kept for callers)."""
    return compute_coverage(match, analyses)


def compression_score(match: PatternMatch) -> float:
    """Deprecated alias for `coverage_score`."""
    return coverage_score(match)
