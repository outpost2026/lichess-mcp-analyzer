"""T1: Provenance of pattern measurements.

Every number produced by the pattern pipeline must be reproducible from
(dataset, pattern library, code). This module builds that identity block.
It is deterministic and offline: no network, no wall-clock time.

Usage:
    prov = build_provenance(analyses, PatternLibrary().load_baseline())
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from functools import lru_cache
from pathlib import Path

from lichess_analyzer_mcp.models.game import GameAnalysis
from lichess_analyzer_mcp.models.pattern import PatternLibrary

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def pattern_lib_sha256(library: PatternLibrary) -> str:
    """Canonical hash of every field that can change detection behaviour."""
    rows = []
    for pid in sorted(library.patterns):
        p = library.patterns[pid]
        rows.append(
            {
                "id": p.id,
                "name": p.name,
                "pattern_type": p.pattern_type,
                "mechanism": p.mechanism,
                "detection_method": p.detection_method,
                "severity": p.severity,
                "min_games": p.min_games,
                "min_occurrences": p.min_occurrences,
                "detection_rules": p.detection_rules,
            }
        )
    payload = json.dumps(rows, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return _sha256(payload)


def dataset_sha256(analyses: list[GameAnalysis]) -> str:
    """Canonical hash of dataset composition: game, color, length, date.

    Order-independent: rows are sorted, so the same set of analyses gives the
    same hash regardless of input order. Engine depth is not part of this hash;
    it belongs to the analysis payload, not to the dataset identity.
    """
    rows = sorted(f"{a.game.id}|{a.game.color}|{len(a.moves)}|{a.game.date}" for a in analyses)
    return _sha256("\n".join(rows))


@lru_cache(maxsize=1)
def code_commit() -> str:
    """Git HEAD of the running code, or LICHESS_CODE_COMMIT, or 'unknown'."""
    env = os.environ.get("LICHESS_CODE_COMMIT")
    if env and env.strip():
        return env.strip()
    try:
        out = subprocess.run(
            ["git", "-C", str(_REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def build_provenance(analyses: list[GameAnalysis], library: PatternLibrary) -> dict:
    """Identity block to embed in every PatternMatch and measurement JSON."""
    return {
        "dataset_sha256": dataset_sha256(analyses),
        "pattern_lib_sha256": pattern_lib_sha256(library),
        "code_commit": code_commit(),
        "n_games": len(analyses),
        "n_moves": sum(len(a.moves) for a in analyses),
    }
