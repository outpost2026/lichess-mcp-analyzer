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

# Node ceilings per depth. Single thread + fixed node ceiling + fixed depth
# are all search-count limits (no wall clock), so the same position always
# yields the same evaluation (FIX-003). The ceiling also bounds the worst
# case time per analysis (~0.4 s at 150k nodes, measured).
NODE_CAPS = {12: 80_000, 14: 150_000, 16: 400_000, 18: 1_000_000}

# Determinism: one thread. Multi-thread search depends on thread scheduling,
# which made ACPL and flagged move sets differ between identical runs.
ENGINE_THREADS = 1

# Minimum remaining engine time worth starting another move evaluation.
MIN_USEFUL_ENGINE_S = 0.15
