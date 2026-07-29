# Session Plan — 2026-07-29 Evening (v2)

**Commit base:** `cd136b5` — [P4] design docs + [PLAN] session plan v1 pushed
**Navazuje na:** CHESS_PATTERNS_AUDIT_2026-07-28.md (W1-W10), PHASE2_BUILD_PLAN.md v4.1 (P0-P4), DALSÍ_KROKY_po_RUN_003.md v2.0 (K0 + CPM korelace), OPPONENT_PERSPECTIVE_TOOL_DESIGN.md (4 tool design)

---

## Phase 0: Checkpoint

- [ ] `git pull --rebase`
- [ ] Restart MCP lichess-analyzer (blocker from .ai_state resolved)
- [ ] Clear stale game cache (RUN_005 pending)

---

## Track 0: K0 channel (z DALSÍ_KROKY_po_RUN_003 §1)

CPM korelace odhalila chybějící K0 kanál — Stockfish je měřicí přístroj, jeho konfigurace musí být explicitní.

| ID | Úkol | Soubor | Lines |
|----|------|--------|-------|
| **K0-1** | Run config template s K0 metrikami (engine_version, binary, Threads, Hash, depth, nps, total_time) | `data/runs/RUN_config.json` | 15 |
| **K0-2** | Depth mismatch warning v `_load_cached_analysis()` — logovat warning při mixed depth | `services/game_analyzer.py` | 10 |
| **K0-3** | ✅ **HOTOVO** — INC-A/B/C re-fetch depth=14 v cache | — | — |

**K0 standard:** Každý run reportuje: `engine_version`, `depth`, `Threads`, `Hash`, `nps_benchmark`, `total_time_seconds`

---

## Track A: P0-Audit fixes (W1-W10 + AUD items) — dle sekvence z PHASE2_BUILD_PLAN

### P0-A: Data integrity (bez křížových závislostí)

| ID | Severita | Soubor | Fix |
|----|----------|--------|-----|
| **W1** | CRITICAL | `tools/match_patterns.py:152-170` | Add `affected_games: list(m.game_ids)` do response builder |
| **W9** | CRITICAL | `services/game_analyzer.py` | Rozlišit blunder/mistake větve v `_classify_move()` — mistakes list není nikdy plněn |
| **W2** | HIGH | `services/pattern_detector.py` — všech 14 `_detect_*` | Normalizovat evidence schema: každý detector musí mít `affected_games: list[str]` + `total_games: int` |
| **W5** | MEDIUM | 6 detectorů (C,O,P,Q1,R,S) | `affected_games` z `int` (len(set)) na `list[str]` (list(set)) |
| **W6** | HIGH | `services/pattern_detector.py:_detect_i2` | I2 confidence: base 0.05 + max() proti division-by-zero (1/35 = 2.3% bug) |

### P0-B: DBCL audit items (AUD)

| ID | Soubor | Fix |
|----|--------|-----|
| **AUD-01** | `services/pattern_detector.py:_detect_b` | `total_captures` counter přesunout mimo blunder podmínku (teď = `blunder_captures` vždy) |
| **AUD-07** | `services/pattern_detector.py` — O,P,Q,R,Q1 | Hardcoded confidence → data-driven vzorce |

### P1: Semantic integrity

| ID | Severita | Soubor | Fix |
|----|----------|--------|-----|
| **W3** | MEDIUM | `_detect_j` | King moves (Kd3, Kf7) false positive — přidat `"K" not in m.move_san` |
| **W7** | MEDIUM | `services/compressibility_validator.py` | Align s README: `0.5×compression + 0.3×entropy + 0.2×sample` |
| **W10** | MEDIUM | All detectors | Unify `frequency` semantics — jeden význam napříč patterny |
| **AUD-02** | — | `_detect_c` | `sector_focus_sequence` neodpovídá kódu — opravit detection_method nebo kód |
| **AUD-05** | — | `_detect_q` | `defensive_phase_analysis` neodpovídá kódu — opravit detection_method |
| **AUD-06** | — | `_detect_p` | Heuristika místo forcing analysis — zdokumentovat limit |

### P2: Quality

| ID | Severita | Soubor | Fix |
|----|----------|--------|-----|
| **W4** | LOW | `pattern_detector.py` | Pattern S/J overlap deduplication |
| **W8** | LOW | `services/pattern_artifact_validator.py` | Add `affected_games` type + format validation |

### P3: DBCL Phase 2 core (až po W fixech)

| ID | Soubor | Úkol |
|----|--------|------|
| **P0-3** | `models/game.py` | `detector_version` konstanta (DBCL-{YYYYMMDD}) |
| **P0-4** | `services/game_analyzer.py` | `win_prob` výpočet — winning-chances sigmoid místo hardcoded 0.0 |
| **P0-5** | `services/llm_client.py` | K2 kontrakt per-game/aggregate — strukturovaný protokol |
| **P1-1** | `services/game_analyzer.py` | Inline context extraction (BlunderFactSheet) |
| **P1-2** | `models/analysis.py` | BlunderFactSheet `@dataclass` |
| **P1-3** | `services/llm_client.py`, `game_llm_cache.py` | Guard-clause injection do prompt builderu |
| **P1-4** | `services/narrative_validator.py` | 5 claim kategorií + reject loop |
| **P1-5** | — | SRSCard konzument BlunderFactSheet |

### CPM vylepšení (z DALSÍ_KROKY §2)

| ID | Soubor | Úkol |
|----|--------|------|
| **CPM-1** | `models/pattern.py` | Přidat `it_analogy: str = ""` do PatternDef — IT analogie pro generalizaci |
| **CPM-2** | `models/pattern.py`, `services/pattern_detector.py` | `compression_ratio: Optional[float]` do PatternMatch — CR = N / (C_impl + C_udrz), WARNING při CR<1 |
| **CPM-3** | — | Evidence standard AUD-08: structured dict místo string |

---

## Track B: P4 — Opponent Analysis Pipeline

**Design base:** `OPPONENT_PERSPECTIVE_TOOL_DESIGN.md` + `OPPONENT_ELO_ETL_DESIGN.md`

**Architektura (dle design docu):**
```
src/tools/opponent/          # NOVÝ modul (místo flat)
  ├── __init__.py
  ├── opponent_analysis.py   # Tool 1+2 sloučen: mode="aggregate"|"compare"
  ├── group_profiler.py      # Tool 3: N=2 group profiling
  └── hsnr_extract.py        # Tool 5: high-SNR extraction
```

### P4-1: Opponent profiling (sloučen Tool 1 + Tool 2 dle design docu)

**Tool:** `lichess_opponent_analysis` s parametrem `mode`:
- `mode="aggregate"` — agregované opponent statistiky (bývalý Tool 1)
- `mode="compare"` — per-game author vs opponent (bývalý Tool 2)

**Vstup:** `game_ids`, `mode`, `depth` (default 12)
**Soubor:** `src/tools/opponent/opponent_analysis.py` (nový)

### P4-2: 3 nové services

| Service | Soubor | Účel |
|---------|--------|-------|
| opponent_stats | `src/services/opponent_stats.py` | Core: compute_opponent_aggregate(), compute_group_profile(), extract_hsnr() |
| elo_estimator | `src/services/elo_estimator.py` | Multi-feature ELO regrese (6 features, FIDE 2024 weights) |
| etl_pipeline | `src/services/etl_pipeline.py` | 3-phase ETL + dual_perspective_flow() |

### P4-3: 1 nový model

| Model | Soubor | Účel |
|-------|--------|-------|
| OpponentProfile, GroupProfile, HsnrPoint | `src/models/opponent_profile.py` | Dataclasses pro opponent output |

### P4-4: match_patterns group_by extension

- Modify `tools/match_patterns.py` — přidat `group_by="all"|"n1:n2"|"elo_band"|"result"`
- **Design doc priorita:** #4 (low effort, high value)

### P4-5: N3 architecture + dual-perspective

- N3 slot v opponent_stats (draws, schema exists even when N=0)
- `etl_pipeline.dual_perspective_flow()` — flip PGN → re-analyze → hSNR

---

## Track C: Verification

- [ ] `pytest` — 63/63 + new tests
- [ ] `ruff check src/`
- [ ] `mypy src/`
- [ ] RUN_005 re-run (depth=12, 30 games) — verify W1-W10 fixes
- [ ] Coaching report smoke test

---

## Commit checklist (15 commitů z DALSÍ_KROKY §4)

```
 1. [K0-1] docs: RUN_config template s K0 metrikami
 2. [K0-2] feat: depth mismatch warning v cache load
 3. [W1] fix: game_ids dropped v serializaci (CRITICAL)
 4. [W9] fix: mistakes list always empty (CRITICAL)
 5. [W2+W5] fix: evidence normalizace affected_games schema (HIGH)
 6. [W6] fix: I2 confidence formula broken (HIGH)
 7. [AUD-01] fix: B total_captures scope
 8. [W3] fix: J king move false positive
 9. [W7] fix: CompressibilityValidator alignment
10. [W10] fix: frequency semantics standardizace
11. [W4+W8] fix: S/J overlap + artifact validator
12. [CPM] feat: it_analogy + compression_ratio
13. [P4] feat: opponent analysis tools + services
14. [P4] feat: match_patterns group_by extension
15. [RUN_005] data: fresh pipeline run + verification
```

---

## Flow

```
Phase 0: git pull → restart MCP → clear cache
   |
   v
Track 0: K0-1 → K0-2 (10 min)
   |
   v
Track A: W1→W9→W2+W5→W6→AUD-01→W3→W7→W10→W4→W8→CPM-1→CPM-2
   |       (pytest cycle after each P0 group)
   v
Track B: opponent_stats → opponent_analysis tool → group_profiler →
         elo_estimator → etl_pipeline → match_patterns group_by → N3
   |
   v
Track C: full test suite → RUN_005 → coaching smoke test
   |
   v
Commit & push (15 commitů dle checklistu)
```

---

*Vytvořeno: 2026-07-29 19:30 CET | v2 — K0 kanál + CPM korelace + P4 merge dle design docu | Base: cd136b5*
