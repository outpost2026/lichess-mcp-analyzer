"""One decomposition of pipeline state for both output surfaces.

`status="degraded"` in contract 1.2 deliberately conflates two facts: the
deterministic analysis may be complete while the LLM was disabled. An LLM
reading only that field can conclude "the game analysis failed". The additive
`pipeline` block names the two states separately; this module is the single
source of truth so detailed 1.2 and compact 2.4 can never disagree.
"""

from __future__ import annotations

ANALYSIS_STATES = ("complete", "partial", "failed")
COACHING_STATES = ("llm", "deterministic_fallback", "data_only", "failed")

_REPORT_SOURCES = {
    "llm": "llm",
    "mcp_sampling": "llm",
    "deterministic": "deterministic_fallback",
    "data_dump": "data_only",
    "none": "failed",
}


def pipeline_block(
    *,
    status: str,
    partial: bool,
    llm_reason: str | None,
    report_source: str | None,
) -> dict:
    """Build the additive `pipeline` block from already-computed facts."""
    if status == "error":
        analysis = "failed"
    elif partial:
        analysis = "partial"
    else:
        analysis = "complete"
    coaching = _REPORT_SOURCES.get(str(report_source or "").lower(), "failed")
    return {
        "analysis": analysis,
        "coaching": coaching,
        # `llm_disabled` means the caller chose offline ETL, not provider failure.
        "llm_requested": llm_reason != "llm_disabled",
    }
