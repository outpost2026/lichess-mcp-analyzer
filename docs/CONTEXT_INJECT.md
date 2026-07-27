# Context Injection — lichess-analyzer-mcp

**Datum:** 2026-07-27 | **Verze 3.1**
**Branch:** `feat` | **HEAD:** `a3fc36d` [TOOL] feat: lichess_analyze_anonymous_session
**Working tree:** Clean (all fixes committed)

---

## 0. Branch & Session State

| Metrika | Hodnota |
|---------|---------|
| Branch | `feat` (odvozena z `main`, pushnuta na remote) |
| HEAD | `c928327` — I→concept, `269d425` — engine_lines fix + CONTEXT_INJECT v2.0 |
| Předchozí commity | `5572f53` — DBCL Phase 2 baseline |
| Test count | 35/35 pass (Phase 1) + 31 testů `tests/test_dbcl.py` |
| Python | 3.12, uv |
| Stockfish | 18 BMI2, Threads=6, Hash=512, NumaPolicy=hardware |
| Cache | `data/game_cache/` — RUN_005 fresh @ depth=12 (33 files) + INC depth=14 |
| Env file | `.env` s LICHESS_TOKEN (lokálně) |

### Důležité pravidlo: User directive — všechny změny na aktualním branchi, nikdy ne `main`

---

## 1. Session Timeline 2026-07-27

### Dopoledne: DBCL Phase 2 implementace
- **Commit `59e9fce`** — Pattern N (x-ray pin) feat + tests
- **Commit `03c49ab`** — Prompt redesign: FEN + guard clauses + translator role
- **Commit `cfc3805`** — Fix best_move_san → best_move_uci v promptu
- **Commit `5ddf175`** — 6 bugfixes: 999-clamp, berserk pagination, index hook, pending detection
- **Commit `5572f53`** — FINAL: BlunderFactSheet schema, narrative_validator.py, pattern N, context window, CPM korelace

### Odpoledne: RUN_004 + ROOT CAUSE FIX
- RUN_004: ACPL=51.4, 101 BFS, **30% engine_lines silent fail**
- Root cause: `board.san(m)` AssertionError for Stockfish PV multi-move sequences
- **Commit `269d425`** — [FIX] engine_client.py:81 depth limit, :86-93 sequential PV SAN; game_analyzer.py:330 silent→logging

### Večer: RUN_005 + INC ground truth + I→concept + anonymous session tool
- **RUN_005 @ depth=12**: 30 Systeq games, ACPL=46.1, 70 BFS, **0% engine_lines failure** (70/70 with 3/3)
- **INC-A/B/C @ depth=14**: kNAMNYUF (ACPL=54.4, 3 BFS), xUlQasD0 (ACPL=77.2, 7 BFS), qmodxzNF (ACPL=80.5, 7 BFS). All 17 BFS with 3/3 engine_lines. K0 variance 7-10%.
- **AUD-03/11 resolved**: I→concept (manual_only), auto-detection code merged into I2
- **Commit `c928327`** — [PATTERN] I→concept, merge code into I2
- **Commit `a3fc36d`** — [TOOL] `lichess_analyze_anonymous_session`: batch analyze anonymous games from txt/URLs/IDs, per-game + aggregate stats

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

### Fixes committed (269d425)
| Fix | File | Popis |
|-----|------|-------|
| 1 | engine_client.py:81 | `engine.analysis(board, Limit(depth=depth))` — explicit depth limit |
| 2 | game_analyzer.py:330-331 | Silent `pass` → `_logger.warning()` |
| 3 | engine_client.py:86-93 | Sequential `board.copy()` + try/except pro PV SAN |

### Cluster Files (2026-07-27)
| File | Status |
|------|--------|
| `docs/PHASE2_BUILD_PLAN.md` v3.0 | Build plan dle K1/K2/K3 |
| `docs/01_DBCL_unity_synthesis.md` | Synteza + BlunderFactSheet v1.1 |
| `docs/02_DBCL_meta_evaluation.md` | 3-kanál noise framework |
| `00_STRATEGIE/DALSÍ_KROKY_po_RUN_003.md` v2.0 | CPM-korelovaný plán, 15-commit checklist |
| `data/RUN_003_DBCL_v1_2026-07-27.md` | RUN_003: ACPL=39.4 |
| `data/RUN_004_DBCL_v2_2026-07-27.md` | RUN_004: ACPL=51.4 — 30% engine_lines fail |
| `data/RUN_005_DBCL_v3_2026-07-27.md` | RUN_005: ACPL=46.1 — 0% engine_lines fail ✅ |

---

## 3. CPM Correlation — Key Changes to Build Plan

### K0 channel added (explicitly)
```
Před: K1 → K2 → K3
Po:   K0 → K1 → K2 → K3
```

### K0-1/2/3: Stockfish config, depth mismatch, INC ground truth
- K0-3 dokončeno: INC-A/B/C depth=14 cache existuje
- K0-1 pending: RUN_config template
- K0-2 pending: depth mismatch warning

### 15-commit checklist (from DALSÍ_KROKY v2.0)
| # | Commit | Status |
|---|--------|--------|
| 1 | `[K0-3] INC-A/B/C depth=14` | ✅ hotovo (v cache) |
| 2 | `[K0-1] RUN_config template` | ⏳ |
| 3 | `[AUD-01] B total_captures scope` | ⏳ |
| 4 | `[AUD-03/11] I rename + hypothesis` | ✅ **RESOLVED** — I→concept, code→I2 |
| 5 | `[AUD-04] O real repetition detection` | ⏳ |
| 6 | `[AUD-05] Q + Q2 merge` | ⏳ |
| 7 | `[AUD-10] S capture aversion` | ⏳ |
| 8 | `[AUD-08] evidence format standard` | ⏳ |
| 9 | `[CPM] it_analogy / compression_ratio` | ⏳ |
| 10-15 | Další kroky | ⏳ |

---

## 4. RUN_005 Results (ACPL=46.1)

### Aggregate
| Metrika | RUN_003 | RUN_004 | RUN_005 |
|---------|---------|---------|---------|
| Depth | d12 | d12 | d12 |
| Games | 33 | 33 | 33 |
| ACPL | 39.4 | 51.4 | **46.1** |
| Blunders | 24 | 36 | **20** |
| BFS | — | 101 | **70** |
| engine_lines fail | 0% | **30%** | **0% ✅** |

### Pattern distribution (RUN_005)
| Pattern | Frekvence | Games |
|---------|-----------|-------|
| B | 13 | 9/33 |
| R | 14 | 9/33 |
| C | 8 | 7/33 |
| J | 6 | 4/33 |
| S | 2 | 2/33 |

### INC Ground Truth (depth=14)
| Game | ACPL | BFS | engine_lines | K0 variance |
|------|------|-----|-------------|-------------|
| kNAMNYUF | 54.4 | 3 | 3/3 ✅ | 7% vs d12 |
| xUlQasD0 | 77.2 | 7 | 3/3 ✅ | 10% vs d12 |
| qmodxzNF | 80.5 | 7 | 3/3 ✅ | 8% vs d12 |

---

## 5. ENGINE-LINES SILENT FAIL — Root Cause Analysis

### Symptom
30% BFS (30/101) have 0 engine_lines.

### Definitive Root Cause
`engine_client.py:86`: `board.san(m)` validates multi-move PV against ROOT board. After 1st PV move, board changes; subsequent moves fail AssertionError. Error propagates through engine lock, corrupting subsequent evaluations.

### Fix: Sequential board.copy() + try/except
```python
moves_san = []
tb = board.copy()
for m in line["pv"][:5]:
    try:
        moves_san.append(tb.san(m))
        tb.push(m)
    except (AssertionError, ValueError):
        break
```

### Verification
- 5 different failing FENs → 3/3 PV lines ✅
- RUN_005: 70/70 BFS with 3/3 engine_lines ✅ (0% fail, down from 30%)

---

## 6. hSNR Post-Mortem — Anomalies, Errors, Blind Spots

### ANOMALY-1: Silent engine_lines fail (CRITICAL — FIXED)
- **Type**: Silent data corruption
- **Fix**: Double fix — (1) sequential PV SAN, (2) silent→logging

### ANOMALY-2: K0 variance (CRITICAL — MONITOR)
- INC-A: 7-10% variance depth=12→14 (not 22% as earlier false result)
- Lesson: K0 must be reported with every run

### ERROR-1: `engine.analysis()` without depth limit (MAJOR — FIXED)

### ERROR-2: Cached stale BFS (MAJOR — PENDING)
- `detector_version` comparison during cache load not yet implemented

### BLIND-SPOT-1: Stockfish PV multi-move SAN conversion
- PV lines are sequential variations, not parallel alternatives

### BLIND-SPOT-2: Engine lock error propagation
- Single failure poisons subsequent analyses
- Mitigation: engine restart on AssertionError (pending)

### BLIND-SPOT-3: No per-game log of failed BFS (MEDIUM — PENDING)

---

## 7. Key Files Reference

### Source
| File | Role | Status |
|------|------|--------|
| `engine_client.py` | Stockfish wrapper | ✅ Committed (269d425) |
| `game_analyzer.py` | Per-move engine eval | ✅ Committed (269d425) |
| `pattern_detector.py` | 11 detectorů + I2, bez I | ✅ I→concept, code merged (c928327) |
| `models/pattern.py` | PatternDef I: manual_only | ✅ Updated |
| `narrative_validator.py` | 5 claim operatorů | ⏳ Pending integration |

### Data
| File | Status |
|------|--------|
| `data/RUN_005_DBCL_v3_2026-07-27.md` | ✅ RUN_005 report |
| `data/game_cache/` | 33 @ d12 + 3 INC @ d14 |

### Tools
| Tool | Vstup | Popis |
|------|-------|-------|
| `lichess_analyze_anonymous_session` | file_path / urls / game_ids, depth | Batch analýza anonymních her: txt→parse→fetch→analyze→agregace |

---

## 8. CPM Lifecycle — Pattern Status

| Pattern | Fáze 0-2 | Fáze 3 (Audit) | Fáze 4 | Fáze 5 | Fáze 6 |
|---------|----------|----------------|--------|--------|--------|
| A | ✅ | ✅ PASS | ✅ | ✅ | ⏳ |
| B | ✅ | ⚠️ AUD-01 | ⏳ | ✅ | ⏳ |
| C | ✅ | ⚠️ AUD-02 | ⏳ | ✅ | ⏳ |
| G | ✅ | ✅ PASS | ✅ | ✅ | ⏳ |
| **I** | ✅ | **✅ FIXED (concept)** | ✅ | ❌ manual_only | ⏳ |
| **I2** | ✅ | ✅ PASS | ✅ | ✅ | ⏳ |
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

## 9. Next Steps (Priority Order)

### P0: Continue P1 checklist (DALSÍ_KROKY)
1. `[AUD-04]` O real repetition detection — parsovat board history
2. `[AUD-05]` Q + Q2 merge — odstranit duplicitní detekci
3. `[AUD-10]` S capture aversion under check — do produkce
4. `[AUD-08]` evidence format standard

### P1: CPM features
1. `[CPM]` it_analogy do PatternDef + prompt
2. `[CPM]` compression_ratio do PatternMatch

### P2: DBCL Phase 2 completion
1. `[P1-4]` reject loop v LLM pipeline
2. `[P1-5]` SRSCard konzument BFS
3. `[K0-2]` depth mismatch warning v cache load
4. `[K0-1]` RUN_config template

---

*Version 3.0 — 2026-07-27. CPM-korelovaný. Session coverage: engine_lines fix committed, RUN_005 verified, INC ground truth cached, I→concept resolved.*
