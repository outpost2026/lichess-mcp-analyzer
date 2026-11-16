"""P0-6 / T-02: provenance of the published evaluation numbers.

N-03 measured the corpus: 9 208 of 9 412 analysed moves carry no `best_eval`
anchor (97.8 %), because D12 added the anchor and older caches predate it.
`cp_loss = best_eval - eval_after` is therefore verifiable only on the newer
slice, and a payload that stays silent about that invites the reader to assume
the invariant holds everywhere.

The honest answer is neither backfilling nor claiming 100 % consistency:

  - every `cp_loss` names its basis (`cp_loss_basis`),
  - every eval names where it came from (`eval_source`),
  - every payload counts both (`eval_provenance`), so coverage is measurable
    per game instead of per corpus claim,
  - `run_id` fingerprints the analysis policy, so two identical runs produce
    the same id and a changed depth/policy/version produces a different one.

The module is pure: no engine, no IO, no guessing. A value that was not
measured stays `unknown`; it is never replaced by an inferred one.
"""

from __future__ import annotations

import hashlib
import json

from lichess_analyzer_mcp.services.eval_consistency import cp_loss_reconstructs

# `best_eval` = the D12 anchor is present and the triple reconstructs within
# 1 cp. `unknown` = no anchor (legacy cache, cloud eval) or a triple that does
# not reconstruct. There is deliberately no "eval_before" basis: cp_loss was
# never measured against eval_before, so such a label would be a lie.
CP_LOSS_BASIS_VALUES = ("best_eval", "unknown")
EVAL_SOURCE_VALUES = ("stockfish", "cloud", "unknown")

_CLOUD_SOURCE_ALIASES = ("cloud", "chess-api.com", "chess_api", "chess-api")


def cp_loss_basis(best_eval, eval_after, cp_loss) -> str:
    """Which anchor the published `cp_loss` was measured from.

    `best_eval` only when the anchor is present *and* the published triple
    reconstructs; everything else is `unknown` (N-03: that is the majority of
    the pre-D12 corpus, and every cloud evaluation).
    """
    return "best_eval" if cp_loss_reconstructs(best_eval, eval_after, cp_loss) else "unknown"


def normalize_eval_source(value) -> str:
    """Map an engine marker to the closed enum, never to a guess."""
    if not isinstance(value, str):
        return "unknown"
    token = value.strip().lower()
    if token == "stockfish":
        return "stockfish"
    if token in _CLOUD_SOURCE_ALIASES:
        return "cloud"
    return "unknown"


def provenance_summary(moves) -> dict:
    """Count the provenance of one payload's measured moves.

    Only measured moves are counted (analyzed and `cp_loss` numeric): an
    unanalyzed ply has no evaluation to attribute. `anchor_coverage` is the
    share of measured moves whose loss is reconstructible from the anchor -
    the per-game version of the N-03 corpus number.
    """
    basis = dict.fromkeys(CP_LOSS_BASIS_VALUES, 0)
    source = dict.fromkeys(EVAL_SOURCE_VALUES, 0)
    measured = 0
    anchored = 0
    for move in moves or []:
        if not isinstance(move, dict):
            continue
        if move.get("analyzed", True) is False:
            continue
        cp_loss = move.get("centipawn_loss")
        if not isinstance(cp_loss, (int, float)):
            continue
        measured += 1
        basis_value = move.get("cp_loss_basis") or cp_loss_basis(
            move.get("best_eval"), move.get("eval_after"), cp_loss
        )
        basis[basis_value] = basis.get(basis_value, 0) + 1
        source_value = normalize_eval_source(move.get("eval_source"))
        source[source_value] = source.get(source_value, 0) + 1
        if basis_value == "best_eval":
            anchored += 1
    return {
        "moves_measured": measured,
        # 3 decimals keeps the number honest without pretending precision.
        "anchor_coverage": round(anchored / measured, 3) if measured else None,
        "cp_loss_basis": {key: count for key, count in basis.items() if count},
        "eval_source": {key: count for key, count in source.items() if count},
    }


def run_id(
    *,
    depth: int,
    mode: str,
    nodes_cap: int,
    threads: int,
    detector_version: str,
    schema_version: str,
) -> str:
    """Deterministic fingerprint of the analysis policy (16 hex chars).

    Deliberately excludes the engine binary: a cache hit never starts an
    engine, so folding its identity in would give the same configuration two
    different ids. Engine identity belongs to `analysis_runs` (Fáze 1), not to
    a per-payload fingerprint.
    """
    payload = {
        "depth": int(depth),
        "mode": str(mode),
        "nodes_cap": int(nodes_cap or 0),
        "threads": int(threads),
        "detector_version": str(detector_version),
        "schema_version": str(schema_version),
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]
