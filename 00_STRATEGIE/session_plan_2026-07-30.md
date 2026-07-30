# Session Plan — 2026-07-30

**Předchozí base:** `cd136b5` — [PLAN] v2: K0 kanal + CPM korelace + P4 merge
**Aktuální HEAD:** `e3cd453` — [PLAN] session plan v3
**Navazuje na:** CHESS_PATTERNS_AUDIT_2026-07-28.md, PHASE2_BUILD_PLAN.md v4.1

---

## Co se udělalo (2026-07-30)

Místo Track B (P4 Opponent Pipeline) byla implementována **depth policy + coaching tools**:

| Session | Commity | Co se udělalo |
|---------|---------|---------------|
| **A** | `f9f60b5` | `config/depth.py` (DEPTH_DEFAULTS), refaktor 7 toolů na centralní config |
| **B+C** | `0c4e452` | auto-select depth dle time control; prompt templates s `{depth}` placeholder |
| **D+E** | `de16794` | cloud eval fallback (chess-api.com); 25 testů depth policy (93 total) |
| **FIX** | `4a55f1f` | evaluate_move: legal-move guard + local engine per call |
| **REVIEW** | `920fb5d` | safe_llm_call fix (prompt leak); pattern threshold dedup; dead dir cleanup |

**Místo P4 Opponent Pipeline → 5 coaching MCP toolů:** coaching_single_game, coaching_cross_game, coaching_opponent_pool, coaching_training_plan, coaching_opening_report

**17 MCP toolů celkem** (12 data + 5 coaching), **93 testů** ✅

---

## Stav původních položek (co je hotovo, co zbývá)

### Track 0: K0 channel — ZMĚNĚNO

Depth policy + auto-select nahrazuje K0-1/K0-2. K0 metrika je implementovaná v `config/depth.py` a `_detect_game_profile()`.

| ID | Status | Poznámka |
|----|--------|----------|
| K0-1 | ✅ | Run config v `config/depth.py` (profily: standard/batch/focused) |
| K0-2 | ✅ | Depth mismatch warning — strict_depth flag v `_load_cached_analysis()` |
| K0-3 | ✅ | Hotovo před plánem |

### Track A: P0-Audit fixes — VĚTŠINOU HOTOVO

| ID | Status | Commit |
|----|--------|--------|
| W1 (CRITICAL) | ✅ | `9de0aba` |
| W9 (CRITICAL) | ✅ | `9de0aba` |
| W2 (HIGH) | ✅ | `4e7f473` |
| W5 (MEDIUM) | ✅ | `4e7f473` |
| W6 (HIGH) | ✅ | `e6200df` |

### P0-B: DBCL audit items

| ID | Status | Poznámka |
|----|--------|----------|
| AUD-01 | ✅ `97c8aee` | |
| AUD-07 | ❌ Zbývá | hardcoded confidence → data-driven vzorce |

### P1: Semantic integrity

| ID | Status | Poznámka |
|----|--------|----------|
| W3 (MEDIUM) | ✅ `97c8aee` | |
| W7 (MEDIUM) | ✅ `1f02421` | |
| W10 (MEDIUM) | ❌ Zbývá | frequency semantics standardizace |
| AUD-02 | ❌ Zbývá | sector_focus_sequence mismatch |
| AUD-05 | ❌ Zbývá | defensive_phase_analysis mismatch |
| AUD-06 | ❌ Zbývá | forcing analysis limit docs |

### P2: Quality

| ID | Status | Poznámka |
|----|--------|----------|
| W4 (LOW) | ✅ `6724acb` | |
| W8 (LOW) | ✅ `6724acb` | |

### P3: DBCL Phase 2 core — HOTOVO

Všechny položky P0-3 až P1-5 implementovány v aktuálním kódu.

### CPM vylepšení

| ID | Status | Poznámka |
|----|--------|----------|
| CPM-1 | ✅ `4b03dba` | it_analogy v PatternDef |
| CPM-2 | ✅ `1f02421` | compression_ratio v PatternMatch |
| CPM-3 | ❌ Zbývá | Evidence standard structured dict |

### Track B: P4 Opponent Analysis Pipeline — NAHRACENO

Původní plán (opponent_stats.py, elo_estimator.py, etl_pipeline.py) nebyl implementován. Místo toho vzniklo **5 coaching MCP toolů**, které pokrývají část funkcionality:

| Tool | Pokrytí P4 |
|------|-----------|
| `coaching_opponent_pool` | ✅ N1/N2 group analysis z opponentovy perspektivy |
| `coaching_cross_game` | ✅ Agregovaná analýza patternů napříč hrami |
| `coaching_single_game` | ✅ Hluboký report jedné hry |
| `coaching_training_plan` | ✅ Tréninkový plán na základě diagnostiky |
| `coaching_opening_report` | ✅ Opening repertoire report |

**Nechybí:** elo_estimator, etl_pipeline, group_profiler, match_patterns group_by extension

---

## Aktuální toolset (17 tools)

### Data tools (12)
1. `lichess_fetch_games`
2. `lichess_analyze_game` — dual cache white+black
3. `lichess_analyze_position`
4. `lichess_opening_explorer`
5. `lichess_player_profile`
6. `lichess_diagnose_player`
7. `lichess_match_patterns` — 14 patternů A-Q2
8. `lichess_import_pgn`
9. `lichess_games_index`
10. `lichess_analyze_anonymous_session`
11. `lichess_analyze_pending`
12. `lichess_workspace_info`

### Coaching tools (5)
13. `lichess_coaching_single_game`
14. `lichess_coaching_cross_game`
15. `lichess_coaching_opponent_pool`
16. `lichess_coaching_training_plan`
17. `lichess_coaching_opening_report`

---

## Depth Policy

| Time control | Depth |
|-------------|-------|
| Bullet (≤120s) | 12 |
| Blitz (≤480s) | 12 |
| Rapid (≤1800s) | 14 |
| Classical | 14 |
| Correspondence | 18 |
| Batch/pending | 12 |

Cloud fallback: chess-api.com pro depth ≥14 (CHESS_API_CLOUD=1)

---

## Zbývající úkoly (prioritizováno)

### P1 (nevyřízené)
- **AUD-07**: Nahradit hardcoded confidence data-driven vzorci (pattern_detector.py)
- **W10**: Unifikovat frequency semantics napříč patterny
- **AUD-02**: sector_focus_sequence opravit detection_method nebo kód
- **AUD-05**: defensive_phase_analysis opravit detection_method
- **AUD-06**: Zdokumentovat limit forcing analysis v P

### P4 (částečně pokryto coaching tools)
- **elo_estimator**: Multi-feature ELO regrese
- **etl_pipeline**: 3-phase ETL + dual_perspective_flow
- **group_profiler**: N=2 group profiling
- **match_patterns group_by**: group_by="all"|"n1:n2"|"elo_band"|"result"

### Nové nálezy z REVIEW (920fb5d)
- `srs_engine.py`: 5× `datetime.utcnow()` → `datetime.now(timezone.utc)`
- `analysis_resources.py`, `pattern_resources.py`, `kb/writer.py`: `utcnow()` → fix
- `engine_client.py`: dokumentovat nekonzistenci singleton vs per-call engine
- `cloud_client.py`: komentář "depth >= 18" vs realita "depth >= 14"

---

## Flow pro příští session

```
Phase 0: git status → checkpoint
   |
   v
Phase 1: P1 audit items (AUD-07 → W10 → AUD-02/05/06)
   |       pytest cycle
   v
Phase 2: utcnow() fix napříč 3 soubory
   |
   v
Phase 3: P4 doplnění (elo_estimator → group_profiler → etl_pipeline)
   |
   v
Phase 4: full test suite → RUN_005 → smoke test
   |
   v
Commit & push
```

---

*Verze: v3 (2026-07-30) | Aktualizace po codebase review + 3 fixech | HEAD: 920fb5d*
