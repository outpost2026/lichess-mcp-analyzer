DEPTH_DEFAULTS = {
    "standard": {
        "single_game": 14,
        "import_pgn": 14,
        "position": 14,
        "bullet": 12,
        "blitz": 12,
        "rapid": 14,
        "classical": 14,
        "correspondence": 18,
        "unknown": 14,
    },
    "batch": {
        "pending": 12,
        "diagnose": 12,
        "patterns": 12,
        "anonymous": 12,
    },
    "focused": {
        "tactical": 14,
        "endgame": 18,
        "opening": 18,
    },
    "limits": {
        "min": 8,
        "max_single_game": 24,
        "max_batch": 18,
        "max_time_single": 900,
        "max_time_dual": 1800,
    },
}

# ── Stage budgets (plan 2026-11-07, P0.2) ─────────────────────────────────────
# One monotonic deadline per game, split by stage. `reserve_s` covers JSON
# serialization, cache writes and interpreter overhead after the last stage.
BUDGETS = {
    "fast": {
        "total_s": 60.0,
        "engine_s": 40.0,
        "llm_s": 10.0,
        "io_s": 5.0,
        "reserve_s": 5.0,
    },
    "deep": {
        "total_s": 120.0,
        "engine_s": 85.0,
        "llm_s": 25.0,
        "io_s": 5.0,
        "reserve_s": 5.0,
    },
    "position": {
        "total_s": 5.0,
        "engine_s": 4.0,
        "llm_s": 0.0,
        "io_s": 1.0,
        "reserve_s": 0.0,
    },
}

# Node ceilings per depth. Filled in by P0.1 calibration; None = no ceiling
# (behaviour identical to the pre-2026-11 pipeline until measured).
NODE_CAPS = {12: None, 14: None, 16: None, 18: None}

# Minimum remaining engine time worth starting another move evaluation.
MIN_USEFUL_ENGINE_S = 0.15
