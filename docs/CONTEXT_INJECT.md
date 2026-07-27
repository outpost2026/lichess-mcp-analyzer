# Context Injection — lichess-analyzer-mcp

**Datum:** 2026-07-27 | **Verze 2.0**
**Branch:** `feat` | **HEAD:** `5572f53` [DBCL] Phase 2 + DALSÍ_KROKY CPM korelace
**Working tree:** 2 modified files (engine_client.py, game_analyzer.py) — uncommitted fixes

---

## 0. Branch & Session State

| Metrika | Hodnota |
|---------|---------|
| Branch | `feat` (odvozena z `main`, pushnuta na remote) |
| HEAD | `5572f53` — DBCL Phase 2: BlunderFactSheet schema, narrative validator, pattern N, context window, CPM korelace |
| Předchozí branch | `debug/phase1-fixes` (mergeován do `main`, pak branch `feat`) |
| Test count | 35/35 pass (Phase 1) + 31 testů v `tests/test_dbcl.py` (Phase 2, create only) |
| Python | 3.12, uv |
| Stockfish | 18 BMI2, Threads=6, Hash=512, NumaPolicy=hardware |
| Cache | `data/game_cache/` — fresh RUN_004 data @ depth=12 (33 files) |
| Env file | `.env` s LICHESS_TOKEN (nastaveno lokálně, NENÍ v system env) |

### Důležité pravidlo: User directive — všechny změny na aktualním branchi, nikdy ne `main`

---

## 1. Session Timeline 2026-07-27

### Dopoledne: DBCL Phase 2 implementace (committed)
- **Commit `59e9fce`** — Pattern N (x-ray pin) feat + tests
- **Commit `03c49ab`** — Prompt redesign: FEN + guard clauses + translator role
- **Commit `cfc3805`** — Fix best_move_san → best_move_uci v promptu
- **Commit `5ddf175`** — 6 bugfixes: 999-clamp, berserk pagination, index hook, pending detection
- **Commit `5572f53`** — FINAL: BlunderFactSheet schema, narrative_validator.py, pattern N, context window, CPM korelace dokument

### Odpoledne: RUN_004 + root cause analysis (uncommitted fixes)
- **RUN_004 executed**: 30 Systeq games @ depth=12 (fresh cache)
- **Report `data/RUN_004_DBCL_v2_2026-07-27.md`**: ACPL=51.4, 36 blunders, 101 BFS, 71/101 s engine_lines (30% silent fail)
- **ANOMALY-1 identified**: engine_lines=0 u 30% BFS
- **Fix 1 applied**: `engine_client.py:81` — depth limit v `engine.analysis()`
- **Fix 2 applied**: `game_analyzer.py:330-331` — silent `pass` → `_logger.warning()`
- **Re-run anomalies**: 20 games re-analyzed, 10/30 zero→populated, 20/30 still zero
- **Root cause definitively found**: `board.san(m)` v `engine_client.py:86` — AssertionError pro Stockfish PV illegal moves
- **Fix 3 applied**: `engine_client.py:86-93` — sequential board.copy() + try/except
- **Fix 3 verified**: 5/5 previously-failing FENs now return 3/3 PV lines; full game 4j0sNlrT: 0 blunders with zero engine_lines

---

## 2. DBCL Phase 2 — Implemented State

### BlunderFactSheet schema (`models/analysis.py`)
- `fen_before`, `board_state` (was_in_check, checking_pieces, capture/king check), `legal_moves` (captures/king_moves/blocks/checks)
- `engine_lines` (rank, move_san, eval_cp, win_prob, pv), `played_move_rank`
- `pattern_matches` (pattern_id, pattern_name, confidence, evidence)
- `context_window` (3 moves before/after with eval+win_prob)
- `detector_version` constant: `DBCL-20260727-dev`

### narrative_validator (`services/narrative_validator.py`)
- 5 claim categories: piece-on-square, check, capture, eval-number, king-move
- Validator function per category
- **Not yet integrated** into LLM pipeline (reject loop pending)

### Pattern N — x-ray pin detection
- Detected in `_per_blunder_patterns()`: centipawn_loss ≥ 200 + phase=endgame
- Tests in `tests/test_dbcl.py`

### Cluster Files (2026-07-27)
| File | Status |
|------|--------|
| `docs/PHASE2_BUILD_PLAN.md` v3.0 | Build plan strukturovaný dle K1/K2/K3 kanálů |
| `docs/01_DBCL_unity_synthesis.md` | Synteza architektury + BlunderFactSheet v1.1 |
| `docs/02_DBCL_meta_evaluation.md` | 3-kanál noise framework |
| `00_STRATEGIE/DALSÍ_KROKY_po_RUN_003.md` v2.0 | CPM-korelovaný plán, 15-commit checklist |
| `data/RUN_003_DBCL_v1_2026-07-27.md` | RUN_003: ACPL=39.4, 24 blunderů |
| `data/RUN_004_DBCL_v2_2026-07-27.md` | RUN_004: ACPL=51.4, 36 blunderů, 101 BFS, 70% engine_lines |

---

## 3. CPM Correlation — Key Changes to Build Plan

### K0 channel added (explicitly)
```
Před: K1 (detektor) → K2 (kontrakt) → K3 (dekodér)
Po:   K0 (orákulum) → K1 (detektor) → K2 (kontrakt) → K3 (dekodér)
```

### K0-1: Stockfish config dokumentace pro každý run
### K0-2: Depth mismatch warning při cache load
### K0-3: INC-A/B/C re-fetch na depth=14

### 15-commit checklist (z DALSÍ_KROKY v2.0)
1. `[K0-3] feat: INC-A/B/C re-fetch depth=14`
2. `[K0-1] docs: RUN_config template s K0 metrikami`
3. `[AUD-01] fix: B total_captures scope`
4. `[AUD-03/11] fix: I rename + hypothesis`
5. `[AUD-04] fix: O real repetition detection`
6. `[AUD-05] fix: Q + Q2 merge`
7. `[AUD-10] feat: S capture aversion under check`
8. `[AUD-08] fix: evidence format standard`
9. `[CPM] feat: it_analogy do PatternDef + prompt`
10. `[CPM] feat: compression_ratio do PatternMatch`
11. `[P1-4] feat: reject loop v LLM pipeline`
12. `[P1-5] feat: SRSCard konzument BFS`
13. `[P0-5] feat: K2 kontrakt per-game/aggregate`
14. `[K0-2] feat: depth mismatch warning v cache load`
15. `[RUN_005] data: fresh pipeline run depth=14`

---

## 4. RUN_004 Results (ACPL=51.4)

### Aggregate
| Metrika | Hodnota |
|---------|---------|
| Games total | 33 (30 + 3 INC) |
| Total moves | 1192 |
| ACPL | **51.4** (vs RUN_003: 39.4) — vyšší na téže depth, očekávaná variance |
| Blunders | 36 (1.09/game) |
| BFS (blunders+mistakes) | 101 (3.1/game) |
| BFS s engine_lines | **71/101 (70%)** — 30% silent fail |
| BFS s pattern match | 44/101 (44%) |

### Pattern distribution (RUN_004)
| Pattern | Frekvence | Games | Avg conf |
|---------|-----------|-------|----------|
| B | 22 | 14/33 | 0.493 |
| R | 16 | 9/33 | 0.561 |
| C | 11 | 8/33 | 0.644 |
| J | 5 | 5/33 | 0.556 |
| S | 1 | 1/33 | 0.400 |

### INC Ground Truth
| Game | Verdict |
|------|---------|
| kNAMNYUF (white) | Both BFS have 3/3 engine_lines ✅. CP loss 607 (d12) vs 773 (d14) — K0 variance confirmed |
| xUlQasD0 (white) | 2 BFS with 0 engine_lines (ply 19, 91) ❌ |
| qmodxzNF (black) | 1 BFS with 0 engine_lines (ply 60) ❌ |

---

## 5. ENGINE-LINES SILENT FAIL — Root Cause Analysis

### Symptom
30% BFS (30/101) have 0 engine_lines. `engine_client.analyze_position(multipv=3)` returns `[]`.

### Discovery chain
1. `game_analyzer.py:329-333` — `try/except Exception: pass` hides the error completely
2. After adding logging (Fix 2): `analyze_position` raises for ~30% of positions
3. Isolated test: `engine_client.analyze_position(fen, depth=12)` raises `AssertionError`
4. Stockfish PV lines contain multi-move sequences that include illegal moves from root position

### Definitive Root Cause
`engine_client.py:86` (old code):
```python
moves_san = [board.san(m) for m in line["pv"][:5]]
```

`board.san(m)` validates each PV move against the **ROOT** board position. Stockfish outputs PV lines with sequential moves (e.g., `f3g5, g6e5, g5e6`). After the first move `f3g5` (Nf3-g5), the board changes. The THIRD move `g5e6` (Ng5xe6) requires the knight to be on g5 — but in the ROOT position, g5 is **empty**.

This assertion error propagates through the entire engine lock, corrupting the engine state for subsequent calls.

**Demonstrated:**
```
PV:       f3g5(Nf3-g5),  g6e5(Nxg6xe5),  g5e6(Ng5xe6)
Root:     f3->g5 OK       g6->e5 OK       g5->e6 FAILS (g5 empty before Nf3-g5!)
Sequential: copy board, f3g5→push, g6e5→push, g5e6→OK ✓
```

### Secondary finding
`engine.analysis(board)` (without depth limit) was used instead of `engine.analysis(board, chess.engine.Limit(depth=depth))`. This caused depth drift — Stockfish could search to arbitrary depth on unstable positions, increasing timeout risk and wasting compute. This was NOT the root cause of engine_lines=0 but WAS a K0 noise contributor.

---

## 6. Fixes Applied (uncommitted — working tree)

### Fix 1: `engine_client.py:81` — depth limit
```
- with engine.analysis(board) as analysis:
+ with engine.analysis(board, chess.engine.Limit(depth=depth)) as analysis:
```

### Fix 2: `game_analyzer.py:330-331` — silent except → logging
```
- except Exception:
-     pass
+ except Exception as e:
+     _logger.warning("analyze_position failed for %s ply %d: %s", game_id, ply, e)
```

### Fix 3: `engine_client.py:86-93` — sequential PV SAN conversion
```
- moves_san = [board.san(m) for m in line["pv"][:5]]
+ moves_san = []
+ tb = board.copy()
+ for m in line["pv"][:5]:
+     try:
+         moves_san.append(tb.san(m))
+         tb.push(m)
+     except (AssertionError, ValueError):
+         break
```

### Verification results
- **Before fix**: `analyze_position(failing_fen, depth=12, multipv=3)` → AssertionError, engine_lines=[], 30% BFS empty
- **After fix**: `analyze_position(same_fen)` → 3/3 PV lines: `[O-O, O-O Nxe5, O-O Nxe5 Nxe5]` ✅
- **5 different failing FENs tested**: all return 3/3 valid PV lines ✅
- **Full game 4j0sNlrT**: 1 blunder, 0 with zero engine_lines ✅ (down from 30%)

### Important caveat
Cached game files (`data/game_cache/`) were generated with **broken code**. Running `use_cache=True` returns stale BFS with 0 engine_lines. Must clear cache for previously-failing games before re-analysis.

---

## 7. hSNR Post-Mortem — Anomalies, Errors, Blind Spots

### ANOMALY-1: Silent engine_lines fail (CRITICAL — FIXED)
- **Type**: Silent data corruption
- **Signal**: 30% BFS with 0 engine_lines, zero warnings in log
- **Root cause**: Double silent exception — (1) `engine_client.py` AssertionError in `board.san(m)`, (2) `game_analyzer.py` `except Exception: pass`
- **Lesson**: Any `except Exception: pass` is a bug unless proven otherwise. All silent excepts must be logged.

### ANOMALY-2: K0 variance (CRITICAL — MONITOR)
- **Type**: Measurement noise
- **Signal**: kNAMNYUF ply 63 cp_loss: 607 (d12) vs 773 (d14) — 22% difference
- **Root cause**: Depth impacts eval precision directly. Depth=12 is faster but less accurate.
- **Lesson**: ACPL numbers from different depths are NOT comparable. K0 must be reported with every run.

### ERROR-1: `engine.analysis()` without depth limit (MAJOR — FIXED)
- **Type**: Architecture bug
- **Signal**: No depth constraint on Stockfish analysis calls
- **Root cause**: copy-paste error from earlier API usage
- **Lesson**: Every `engine.analysis()` call must have explicit `Limit()`.

### ERROR-2: Cached stale BFS (MAJOR — WORKAROUND)
- **Type**: Cache invalidation
- **Signal**: Re-running with `use_cache=True` returns old BFS with 0 engine_lines
- **Root cause**: Cache is never invalidated. Engine code changes don't trigger cache refresh.
- **Lesson**: `detector_version` should be compared during cache load. On mismatch → re-analyze.

### BLIND-SPOT-1: Stockfish PV multi-move SAN conversion
- **Type**: Domain knowledge gap
- **Trigger**: Assumed Stockfish PV lines contain only single-move evaluations
- **Reality**: Stockfish sends multi-move PV sequences in multi-PV mode. Each PV line is a full variation, not a single move evaluation.
- **Lesson**: PV lines are sequential variations, not parallel alternatives. Must be applied to a copy of the board, one move at a time.

### BLIND-SPOT-2: Absence of deterministic error propagation
- **Type**: Architecture gap
- **Trigger**: AssertionError in `analyze_position` crashes the engine lock, corrupting subsequent evaluations
- **Reality**: Single failed `analyze_position` call can poison the engine for ALL subsequent positions in the game analysis
- **Lesson**: The engine lock (`_acquire_analysis_lock` / `_release`) creates coupling between independent analysis calls. A failure in one position can corrupt the next. Mitigation: add engine restart on AssertionError.

### BLIND-SPOT-3: No per-game log of failed BFS (MEDIUM — PENDING)
- **Current**: Zero engine_lines BFS pass silently through the pipeline
- **Impact**: Cannot easily identify which games/positions are affected without data-level inspection
- **Fix**: Add a `truncated` flag to BlunderFactSheet or log a warning per BFS when engine_lines < multipv_target

---

## 8. Key Files Reference

### Source (services)
| File | Role | Modifikace |
|------|------|------------|
| `src/lichess_analyzer_mcp/services/engine_client.py` | Stockfish wrapper | Fix 1 (depth limit) + Fix 3 (sequential PV SAN) applied, **uncommitted** |
| `src/lichess_analyzer_mcp/services/game_analyzer.py` | Per-move engine eval + BFS builder | Fix 2 (logging) applied, **uncommitted** |
| `src/lichess_analyzer_mcp/services/narrative_validator.py` | NOVÝ: 5 claim operatorů | Committed |
| `src/lichess_analyzer_mcp/services/pattern_detector.py` | 11 pattern detectorů | 4 semantic bugs (AUD-01/03/04/05) pending |
| `src/lichess_analyzer_mcp/services/lichess_client.py` | Lichess API wrapper | A3/A4/A5/B1 fixes OK |
| `src/lichess_analyzer_mcp/services/llm_client.py` | Per-game LLM coaching prompt | Guard-clause injection pending (P1-3) |
| `src/lichess_analyzer_mcp/services/game_llm_cache.py` | Game prompt cache | Guard-clause injection pending (P1-3) |
| `src/lichess_analyzer_mcp/services/diagnostician.py` | Cross-game weakness | GT-062/064 fix OK |
| `src/lichess_analyzer_mcp/services/validator.py` | OLD: pattern artifact validator | Přejmenovat na pattern_artifact_validator (P2-3) |

### Source (models)
| File | Role |
|------|------|
| `src/lichess_analyzer_mcp/models/analysis.py` | BlunderFactSheet, EngineLine, PatternMatchInfo, ContextWindow, DETECTOR_VERSION |
| `src/lichess_analyzer_mcp/models/game.py` | GameSummary, MoveAnalysis, GameAnalysis (moves/mistakes/blunders/blunder_fact_sheets) |
| `src/lichess_analyzer_mcp/models/pattern.py` | PatternDef, PatternLibrary — obsahuje detection_method (některé zastaralé per audit) |

### Data
| File | Role |
|------|------|
| `data/RUN_003_DBCL_v1_2026-07-27.md` | RUN_003: ACPL=39.4, 24 blunderů @ d12 |
| `data/RUN_004_DBCL_v2_2026-07-27.md` | RUN_004: ACPL=51.4, 101 BFS, 70% engine_lines @ d12 |
| `data/game_cache/` | 33 cache files @ depth=12 (generated with broken analyze_position) |

### Strategy
| File | Role |
|------|------|
| `00_STRATEGIE/DALSÍ_KROKY_po_RUN_003.md` v2.0 | CPM-korelovaný plán, 15-commit checklist, K0 channel |
| `docs/PHASE2_BUILD_PLAN.md` v3.0 | Build plan strukturovaný dle kanálů |
| `docs/01_DBCL_unity_synthesis.md` | Synteza + BlunderFactSheet v1.1 |
| `docs/02_DBCL_meta_evaluation.md` | 3-kanál noise framework |
| `docs/CONTEXT_A_ZAMER.md` | Původní záměr projektu (Phase 1) |
| `docs/CONTEXT_INJECT.md` | Tento soubor — session context v2.0 |

### Tests
| File | Status |
|------|--------|
| `tests/test_services.py` | 35/35 pass |
| `tests/test_dbcl.py` | 31 tests (create only) |

---

## 9. Uncommitted Changes Summary

### `src/lichess_analyzer_mcp/services/engine_client.py`
```diff
- with engine.analysis(board) as analysis:
+ with engine.analysis(board, chess.engine.Limit(depth=depth)) as analysis:

- moves_san = [board.san(m) for m in line["pv"][:5]]
+ moves_san = []
+ tb = board.copy()
+ for m in line["pv"][:5]:
+     try:
+         moves_san.append(tb.san(m))
+         tb.push(m)
+     except (AssertionError, ValueError):
+         break
```

### `src/lichess_analyzer_mcp/services/game_analyzer.py`
```python
# Added import
from lichess_analyzer_mcp.services.logger import get_logger
_logger = get_logger("game_analyzer")

# Changed silent except to logged
except Exception as e:
    _logger.warning("analyze_position failed for %s ply %d: %s", game_id, ply, e)
```

---

## 10. Next Steps (Priority Order)

### P0: Commit current fixes + re-run pipeline
1. Committnout engine_client.py + game_analyzer.py fixy
2. Clear cache for 20 games with zero engine_lines
3. Re-run all 30 games @ depth=12
4. Generate RUN_005 report — verify 0% engine_lines failure
5. Verify INC-A/B/C ground truth: all BFS must have 3/3 engine_lines

### P1: CPM-korelovaný build plan (DALSÍ_KROKY checklist)
1. `[K0-3]` INC-A/B/C re-fetch depth=14 (ground truth cache)
2. `[K0-1]` RUN_config template
3. `[AUD-01]` B total_captures scope fix
4. `[AUD-03/11]` I rename + hypothesis
5. `[AUD-04]` O real repetition detection
6. `[AUD-05]` Q + Q2 merge
7. `[AUD-10]` S capture aversion — do produkce
8. `[AUD-08]` evidence format standard
9. `[CPM]` it_analogy / compression_ratio

### P2: DBCL Phase 2 completion
1. `[P1-4]` reject loop v LLM pipeline
2. `[P1-5]` SRSCard konzument BFS
3. `[P0-5]` K2 kontrakt design
4. `[K0-2]` depth mismatch warning v cache load

### P3: RUN_005 final
1. Clear all cache
2. Full pipeline run @ depth=14
3. Generate final report

---

## 11. CPM Lifecycle — Pattern Status

| Pattern | Fáze 0-2 | Fáze 3 (Audit) | Fáze 4 | Fáze 5 | Fáze 6 |
|---------|----------|----------------|--------|--------|--------|
| A | ✅ | ✅ PASS | ✅ | ✅ | ⏳ |
| B | ✅ | ⚠️ AUD-01 | ⏳ | ✅ | ⏳ |
| C | ✅ | ⚠️ AUD-02 | ⏳ | ✅ | ⏳ |
| G | ✅ | ✅ PASS | ✅ | ✅ | ⏳ |
| I | ✅ | ❌ AUD-03 | ⏳ | ✅ | ⏳ |
| J | ✅ | ✅ FIXED | ✅ | ✅ | ⏳ |
| N | ✅ | ✅ PASS | ✅ | ✅ | ⏳ |
| O | ✅ | ❌ AUD-04 | ⏳ | ✅ | ⏳ |
| P | ✅ | ⚠️ AUD-06 | ⏳ | ✅ | ⏳ |
| Q | ✅ | ❌ AUD-05 | ⏳ | ✅ | ⏳ |
| Q1 | ✅ | ✅ PASS | ✅ | ✅ | ⏳ |
| Q2 | ✅ | ✅ PASS | ✅ | ✅ | ⏳ |
| R | ✅ | ✅ PASS | ✅ | ✅ | ⏳ |
| **S** | ✅ | ⏳ | ❌ | ❌ | ❌ |

---

*Version 2.0 — 2026-07-27. CPM-korelovaný. Session coverage: DBCL Phase 2 implementace, RUN_004, root cause analysis, engine_lines silent fail fix.*
