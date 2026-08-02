# Context Injection — lichess-analyzer-mcp

**Datum:** 2026-08-01 | **Verze 5.0**
**Branch:** `main` | **HEAD:** `4348b04` [REVIEW] F3/F4/F2 code-review fixes
**Working tree:** Clean
**Session 2026-08-01:** persist_report tool + MCP GT postmortem v7 (GT-078) + code review F3/F4/F2

---

## 0. Branch & Session State

| Metrika | Hodnota |
|---------|---------|
| Branch | `main` (přímé commity) |
| HEAD | `4348b04` — [REVIEW] F3/F4/F2 code-review fixes |
| Předchozí commity | `c92940f` — [PERSIST] lichess_persist_report, `984e78a` — [FIX] prompt #1, `f9f60b5`..`de16794` — depth policy + coaching tools |
| Test count | **93/93 pass** |
| MCP tools | **18** (12 data + 5 coaching + `lichess_persist_report`) |
| Python | 3.12, uv |
| Stockfish | 18 BMI2, Threads=6, Hash=512, NumaPolicy=hardware |
| Cache | `data/game_cache/` — 151 files (Systeq @ d12 + INC @ d14 + anonymní) |
| Env file | `.env` s LICHESS_TOKEN + LLM klíče (NVIDIA/Cerebras/DeepSeek V4 Flash cascade) |

### Workflow: commity přímo na `main` (od 2026-07-30), 93/93 testů před každým commitem

---

## 1. Session Timeline

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
- **Commit `548fcd8`** — [TOOL] label support (white/black/win/loss) pro `lichess_analyze_anonymous_session`
- **25 anonymních her analyzováno**: ACPL=31.7, 21-4-0 winrate
- **Commit `e6f3f13`** — [TOOL] `lichess_match_patterns` přidán `game_ids` parametr: umožňuje pattern detection na cachovaných anonymních hrách bez username
- **Pattern detection na anonymních hrách ověřen**: 8 patternů detekováno z 25 her ✅

### 2026-07-30: Depth policy + coaching tools
- **Commit `f9f60b5`** — [DEPTH+P1] centrální `config/depth.py` (DEPTH_DEFAULTS), refaktor 7 toolů + 5 coaching MCP toolů
- **Commit `0c4e452`** — [B+C] auto-select depth dle time control + prompt templates
- **Commit `de16794`** — [D+E] cloud eval fallback (chess-api.com) + depth policy test suite (93 total)
- **Commit `920fb5d`** — [REVIEW] safe_llm_call prompt leak fix, pattern threshold dedup, dead dir cleanup
- **Commit `05f819c`** — [PLAN] session_plan_2026-07-30

### 2026-08-01: Persistence + code review fixes
- **Commit `984e78a`** — [FIX] prompt template #1: game data (ACPL, blunders, phase, BFS) do promptu
- **Commit `c92940f`** — [PERSIST] `lichess_persist_report`: on-demand persistence přes LLM cascade (6 kinds, JSON/MD/KB, read-after-write) + report bbJRWReS (NVIDIA, 0 USD)
- **KB:** MCP GT postmortem v7 — GT-078 (ruff --fix destruktivní autofix, F401 side-effect importy) + P62 + checklist #37 (B2B-Knowledge-Base)
- **Commit `4348b04`** — [REVIEW] F3/F4/F2:
  - F3: `services/audit.py` — @auditable na 18 toolů (P5, JSONL do logs/audit_YYYYMM.jsonl)
  - F4: engine timeout guard 15 s (P2) — `_run_engine_call` daemon thread + kill engineu na timeout
  - F2: `services/batch_guard.py` — BatchBudget `max_seconds` + `unprocessed_ids` na 6 batch toolů (P13)
- **18 MCP toolů**, 93/93 testů, audit log funkční
- **Senior code review** — `docs/CODE_REVIEW_2026-08-01.md` (4 P1, 6 P2, P3 backlog, test gaps):
  - B100: opening_report čte neexistující atributy (opening_name/player_color/acpl/result) → data garbage
  - B98: opponent_pool — opponent hardcodovan "black" bez username; n1_count dead
  - B121: kb/writer KB_ROOT míří na repo root, ne _github/ — target="kb" nikdy nespuštěn
  - B31: LLM cache klíč bez color — dual-cache white/black se přepisují
  - P2: B5 (kill špatného engineu), B16 (tiché selhání evaluate→ACPL bias), B101 (chesscom tiše lichess), B113 (_detect_s crash na starých cache)

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
| `00_STRATEGIE/DALSI_KROKY_po_RUN_003.md` v2.0 | CPM-korelovaný plán, 15-commit checklist |
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
| 5 | `[AUD-04] O real repetition detection` | ✅ **RESOLVED** — renamed to Stagnační panika (option A) |
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
| `game_analyzer.py` | Per-move engine eval | ✅ Committed — **⚠️ W9 (mistakes bug)** |
| `pattern_detector.py` | 14 detectorů A-S | ✅ — **⚠️ W2, W3, W5, W6, W10 (5 nálezů)** |
| `models/pattern.py` | PatternDef + PatternMatch | ✅ — **⚠️ W1 (game_ids dropped v serializaci)** |
| `narrative_validator.py` | 5 claim operatorů | ⏳ Pending integration |
| `compressibility_validator.py` | CR computation | ✅ — **⚠️ W7 (neodpovídá README)** |
| `pattern_artifact_validator.py` | Post-analysis sanity | ✅ — **⚠️ W8 (nevaliduje affected_games)** |
| `report_persister.py` | On-demand report persistence (6 kinds, JSON/MD/KB) | ✅ (c92940f) |
| `audit.py` | P5 per-tool audit (JSONL, @auditable) | ✅ (4348b04) |
| `batch_guard.py` | P13 batch budget (max_seconds + unprocessed_ids) | ✅ (4348b04) |

### Data
| File | Status |
|------|--------|
| `data/RUN_005_DBCL_v3_2026-07-27.md` | ✅ RUN_005 report |
| `data/game_cache/` | 33 @ d12 + 3 INC @ d14 |

### Tools
| Tool | Vstup | Popis |
|------|-------|-------|
| `lichess_analyze_anonymous_session` | file_path / urls / game_ids, depth | Batch analýza anonymních her: txt→parse→fetch→analyze→agregace + label support |
| `lichess_match_patterns` | username / game_ids, max_games, depth, result | Pattern detection A-Q1 — nově podpora anonymních her přes game_ids |
| `lichess_coaching_*` (5) | game_id / username / game_ids, depth, max_games, result | Coaching reporty: single_game, cross_game, opponent_pool, training_plan, opening_report — LLM cascade (NVIDIA→Cerebras→DeepSeek V4 Flash) |
| `lichess_persist_report` | kind, game_id / username / game_ids, format, target | On-demand persistence reportu (docs/ + B2B-Knowledge-Base) |

---

## 8. Pattern Detector Audit — W1-W10 (CHESS_PATTERNS_AUDIT_2026-07-28)

### Prehled nalezů

| ID | Priorita | Popis | Lokace |
|----|----------|-------|--------|
| **W1** | CRITICAL | `game_ids` dropped v serializaci — přímá přičina halucinace | `match_patterns.py:155-170` |
| **W2** | HIGH | Evidence schema nekonzistentní napříč 14 detektory — 7/14 chybí `affected_games` | `pattern_detector.py` všechny `_detect_*` |
| **W3** | MEDIUM | `_detect_j` chytá king moves jako "blocks" — false positive | `pattern_detector.py:225` |
| **W4** | LOW | Pattern S/J overlap bez dedup | `pattern_detector.py:216,492` |
| **W5** | MEDIUM | `affected_games` type mismatch int vs list (6 patternů) | C,O,P,Q1,R,S evidence |
| **W6** | HIGH | I2 confidence formula broken (1/35 = 2.3%) | `pattern_detector.py:200` |
| **W7** | MEDIUM | CompressibilityValidator neodpovídá README (chybí entropy + sample score) | `compressibility_validator.py:13-23` |
| **W8** | LOW | Artifact validator nevaliduje `affected_games` | `pattern_artifact_validator.py:17-48` |
| **W9** | CRITICAL | `mistakes` list vždy prázdný — bug v game_analyzer.py | `game_analyzer.py:_run_analyze_pgn()` |
| **W10** | MEDIUM | `frequency` má 3 různé významy napříč patterny | Všechny `_detect_*` |

Detail: `docs/CHESS_PATTERNS_AUDIT_2026-07-28.md`

### Plán oprav

```
P0-A (data integrity):  W1, W9, W2+W5, W6
P0-B:                   AUD-01, AUD-07
P1 (semantic integrity): W3, W7, W10
P2 (quality):            W4, W8, N2, N3, N7
P3 (DBCL Phase 2 core):  P0-3, P0-4, P0-5, P1-1..P1-5
```

---

## 9. Lossy Compression Principle (Mikolov-Dev)

### Základní princip

> **Pattern detection = Lossy compression.** Cílem je najít vzory, které popíšou realitu s maximální entropickou hodnotou na minimum tokenů.

### Klíčový předpoklad

**CR = N / (C_impl + C_udrz) dává smysl POUZE pokud N = počet instancí téže věci.**

Pokud sémantický/lexikální popis patternu neodpovídá kódu (jako u pattern O — "repetition avoidance" vs "flat eval blunder"):
- CR není kompresní poměr, je to míra klamu
- Každá instance je falešně pozitivní vůči popisu
- Entropická hodnota = 0 (popis není pravdivý, nelze z něj odvodit realitu)
- Vysoká frekvence není výhoda — je to šíření systematické chyby

### Důsledky pro pipeline

| Vrstva | Povinnost |
|--------|-----------|
| **PatternDef.name** | Musí přesně odpovídat kódu |
| **PatternDef.mechanism** | Must be truth — ne "co bychom chtěli detekovat", ale "co kód reálně detekuje" |
| **PatternDef.hypothesis** | Falsifikovatelná vůči detection_method |
| **CR výpočet** | Validní jen při splnění výše uvedeného |
| **AUDIT fáze (CPM Fáze 3)** | Primárně ověřuje sémantickou integritu, ne jen code correctness |

### Pattern O jako exemplární selhání (AUD-04 — RESOLVED via rename)

| Vrstva | Tvrdilo | Realita | Následek |
|--------|---------|---------|----------|
| Jméno | "Repetition avoidance greed" | Flat eval → blunder | CR=47.8 měří noise |
| Mechanism | Refuses threefold repetition | Eval plateau → impatience | Hypotéza neplatí |
| Code | — | 3×<30cp → chyba do 6 tahů | ✅ |
| **Oprava** | **Option A: rename → "Stagnační panika"** | Popis nyní odpovídá kódu | ✅ RESOLVED |
| **Verdikt** | Lossy compression creates semantic debt | **Popis opraven — sémantická integrita obnovena** |

### Pravidlo pro iterační vývoj

1. Každý pattern musí projít **sémantickým auditem** (AUD fáze): shoduje se jméno, mechanismus, hypothesis s kódem?
2. Pokud ne — buď opravit popis (lossy > lexikální přesnost) nebo opravit kód (implementovat skutečnou detekci)
3. CR < 1 není jediný důvod k odmítnutí patternu — pattern s CR > 100 ale špatným popisem je horší než žádný pattern

---

## 10. CPM Lifecycle — Pattern Status

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
| O | ✅ | ✅ **RESOLVED (rename)** | ✅ | ✅ | ⏳ |
| P | ✅ | ⚠️ AUD-06 | ⏳ | ✅ | ⏳ |
| Q | ✅ | ❌ AUD-05 | ⏳ | ✅ | ⏳ |
| Q1 | ✅ | ✅ PASS | ✅ | ✅ | ⏳ |
| Q2 | ✅ | ✅ PASS | ✅ | ✅ | ⏳ |
| R | ✅ | ✅ PASS | ✅ | ✅ | ⏳ |
| **S** | ✅ | ⏳ | ❌ | ❌ | ❌ |

---

## 11. Next Steps (Priority Order)

### P0: Fix batch 1 — data correctness (z CODE_REVIEW_2026-08-01)
1. **[B100]** opening_report: `getattr(a, "opening_name")` → `a.game.opening` (též color/acpl/result) — 15 min
2. **[B98]** opponent_pool: username param + barvy z PGN headerů; opravit n1/n2 výpočet — 15 min
3. **[B121]** kb/writer KB_ROOT: 4× `..` do `_github/` + timestamp do filename (B119) — 5 min
4. **[B31]** game_llm_cache klíč `{game_id}_{color}_llm.json` — 10 min

### P0: Fix batch 2 — runtime
1. **[B5]** `_run_engine_call(fn, engine)` — killovat referenci volajícího, ne sdružený engine
2. **[B16]** `evaluation_errors` counter do GameAnalysis (tiché selhání evaluate→ACPL bias)
3. **[B101]** source="chesscom" — buď implementovat, nebo vrátit error
4. **[B113]** `_detect_s` guard na fen="" (staré cache → ValueError → crash detect_all)
5. **[F1] asyncio.to_thread** — sync engine/HTTP volání v async handlerech (0× asyncio v src/). První: coaching + persist cesta, pak zbytek. Odhad 1-2 h, EROI 7/10

### P1: Testy k batch 1-2
1. Unit testy na coaching tooly (opening_report/opponent_pool) — B100/B98 by chytily
2. Test kb/writer cesty (B121 latentní) + game_llm_cache (B31)
3. Oprava test_engine_client (mock get_engine neúčinný — evaluate_move reálně spawnuje SF)

### P2: Ostatní
1. **[EXIT-HANG]** proces s engine callem neexituje — pre-existing, nice-to-have
2. **[RUFF-DEBT]** 18+ pre-existing chyb v tools/ — dedikovaný refactor commit, **ručně, nikdy `ruff --fix`** (GT-078)
3. Dead code cleanup: narrative_validator (P1-4 reject loop), SRSEngine (docstring "FSRS" ale SM-2), extract_game_id_color_from_analysis
4. **[BLIND-SPOT-3]** per-game log truncated BFS (P61)
5. **[AUD-05]** Q + Q2 merge; **[AUD-10]** S capture aversion; **[AUD-08]** evidence format standard; CPM it_analogy/compression_ratio
6. **[K0-2]** depth mismatch warning v cache load; **[ANOMALY-2]** K0 variance reporting

---

*Version 5.0 — 2026-08-01. Session coverage: depth policy + coaching tools (07-30), persist_report + KB v7 + F3/F4/F2 review fixes (08-01). 18 toolů, 93/93 testů.*
