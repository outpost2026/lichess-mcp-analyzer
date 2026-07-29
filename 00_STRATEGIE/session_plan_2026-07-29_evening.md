# Session Plan — 2026-07-29 Evening

**Commit base:** `f241f40` — [P4] design docs + coaching reporty pushed to origin/main
**Navazuje na:** CHESS_PATTERNS_AUDIT_2026-07-28.md → W1-W10, PHASE2_BUILD_PLAN.md v4.1 → P4

---

## Phase 0: Checkpoint + MCP restart

- [ ] `git status` — clean?
- [ ] Restart MCP lichess-analyzer (blocker from .ai_state resolved)
- [ ] Clear stale game cache (RUN_005 pending)

---

## Track A: P0-Audit fixes (W1-W10) — implement code fixes

| ID | Severita | File | Fix |
|----|----------|------|-----|
| **W1** | CRITICAL | `tools/match_patterns.py:152-170` | Add `affected_games: list(m.game_ids)` to response builder |
| **W9** | CRITICAL | `game_analyzer.py` | Fix `mistakes` list — currently always empty |
| **W2** | HIGH | `pattern_detector.py` all `_detect_*` | Normalize evidence schema: `affected_games: list[str]` + `total_games` across all 14 detectors |
| **W6** | HIGH | `pattern_detector.py:_detect_i2` | Fix I2 confidence: add base 0.05 + max() proti division-by-zero |
| **W3** | MEDIUM | `_detect_j` | King moves (Kd3, Kf7) nesmí být detekovány jako 'impulsive block' |
| **W5** | MEDIUM | 6 detectors (C,O,P,Q1,R,S) | `affected_games` z `int` na `list[str]` |
| **W7** | MEDIUM | `compressibility_validator.py` | Align with README: 0.5×compression + 0.3×entropy + 0.2×sample |
| **W10** | MEDIUM | All detectors | Unify frequency semantics across patterns |
| **W4** | LOW | `pattern_detector.py` | S/J overlap deduplication |
| **W8** | LOW | `pattern_artifact_validator.py` | Add affected_games validation |

**Tests:** `tests/test_pattern_semantic_contract.py` — 1 positive + 1 negative per detector

---

## Track B: P4 — Opponent Analysis Pipeline (implementation)

### P4-1: 4 new MCP tools

| Tool | Nový soubor | Závisí na |
|------|-------------|-----------|
| `lichess_opponent_profile` | `src/tools/opponent_profile.py` | `opponent_stats.py` |
| `lichess_compare_sides` | `src/tools/compare_sides.py` | `pool_aggregator.py` |
| `lichess_group_profiler` | `src/tools/group_profiler.py` | `pool_aggregator.py` |
| `lichess_hsnr_extract` | `src/tools/hsnr_extract.py` | `etl_pipeline.py` |

### P4-2: 4 new services

| Service | Nový soubor | Účel |
|---------|-------------|-------|
| opponent_stats | `src/services/opponent_stats.py` | Per-opponent stat aggregation z game_cache |
| pool_aggregator | `src/services/pool_aggregator.py` | Pool-level aggregation per N-category/ELO band |
| elo_estimator | `src/services/elo_estimator.py` | Multi-feature ELO regrese (6 features, FIDE 2024 weights) |
| etl_pipeline | `src/services/etl_pipeline.py` | 3-phase ETL + dual_perspective_flow |

### P4-3: match_patterns extension

- Add `group_by` parameter: `"all"` / `"n1:n2"` / `"elo_band"` / `"result"`
- Modify `tools/match_patterns.py`

### P4-4: N3 architecture

- N3 (draws) slot in all aggregation — schema exists even when N=0
- File: `opponent_tracker.py`

### P4-5: Dual-perspective pipeline

- `etl_pipeline.dual_perspective_flow()` — flip PGN → re-analyze → compare N1 vs N2

---

## Track C: Verification

- [ ] `pytest` — all tests pass (expected: 63/63 + new)
- [ ] `ruff check src/` — lint clean
- [ ] `mypy src/` — types clean
- [ ] RUN_005 re-run (depth=12, 30 games) — verify fixes
- [ ] Coaching report generation smoke test

---

## Flow

```
1. git pull --rebase (check remote state)
2. Implement W1 + W9 (CRITICAL)
3. Implement W2 + W6 (HIGH)
4. Implement W3-W5, W7, W10 (MEDIUM)
5. Implement W4, W8 (LOW)
6. pytest cycle after each severity level
7. P4-2 services (opponent_stats, pool_aggregator, elo_estimator)
8. P4-1 tools (opponent_profile, compare_sides, group_profiler, hsnr_extract)
9. P4-3 group_by extension
10. P4-4 N3 architecture
11. P4-5 dual-perspective pipeline
12. Full verification suite
13. Commit + push
```

---

*Vytvořeno: 2026-07-29 18:00 CET | Base: f241f40*
