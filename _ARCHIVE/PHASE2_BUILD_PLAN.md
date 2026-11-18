# Phase 2 — Build Plan v4.0

**Datum:** 2026-07-29 | **Verze:** 4.1
**Navazuje na:** `01_DBCL_unity_synthesis.md`, `02_DBCL_meta_evaluation.md`, `PHASE2_BUILD_PLAN.md` v3.0
**Status:** P0-1 hotov, P0-2 hotov, **P0-Audit (CHESS_PATTERNS_AUDIT_2026-07-28) — 10 nových nálezů W1-W10**

---

## Current State (2026-07-28)

| Komponenta | Stav |
|------------|------|
| Repo | `main` clean, HEAD `0f4eef5` |
| Tests | 68/68 pass (+ test_pattern_semantic_contract.py) |
| P0-1 (FEN + was_in_check v MoveAnalysis) | ✅ hotovo |
| P0-1 (pattern J semantika) | ✅ hotovo |
| P0-2 (detektor audit 14 patternů) | ✅ **HOTOVO** — viz AUDIT matrix níže |
| **Hloubkový audit (CHESS_PATTERNS_AUDIT_2026-07-28)** | ✅ **10 nových nálezů W1-W10** |
| Analýza halucinace (HALUCINACE_ROOT_CAUSE_ANALYSIS) | ✅ hotovo + DATA-FABRICATION-001 guard |
| 14 detectorů (A-S, krom I concept) | ✅ implementováno + otestováno |
| Analyzované partie | 35+ anonymních + 30 Systeq |
| LLM pipeline | ✅ 3 provider |
| DBCL architektura | ✅ Phase 2 hotovo |
| Merge feat→main | ✅ hotovo (34 files, +3352/−324) |

---

## Tři kanály šumu (z 02_DBCL §3)

Architektura DBCL rozpoznava **tri nezavisle kanaly**, kazdy s vlastnim typem sumu:

```
Kan�l 1 (K1): DETEKTOR     — deterministicky, ale muze byt semanticky chybny
Kan�l 2 (K2): KONTRAKT     — prenos mezi per-game a aggregate LLM
Kan�l 3 (K3): DEKODER/LLM  — inferencni sum LLM
```

Tento build plan je strukturovan podle kanalu, ne podle priority cisel.

---

## P0 — Detektor audit (K1) a infrastruktura

**Priorita: NEJVYSSI** — dokud neni K1 auditovan, DBCL v1 stoji na pisku.
Meta-evaluation §10.3: *"dokud nebude audit kompletni, DBCL v1 je experiment, ne reseni"*

### P0-2: Audit 11 detektoru A-R (K1 cleanup) ✅ HOTOVO

**Goal:** Pro kazdy pattern overit, ze `detection_method` testuje to, co tvrdi `pattern_name`.

**Datum auditu:** 2026-07-26 | **Metoda:** rucni pruchod `services/pattern_detector.py:27-350` radka po radce proti `models/pattern.py:37-155`

#### Audit Matrix

| # | Pattern | detection_method (PatternDef) | Code testuje (_detect_X) | Verdikt |
|---|---------|------------------------------|--------------------------|---------|
| A | Anonymous effect | `compare_blunder_rate` | Porovnava blunder rate anonymnich (opponent "anonymous") vs pojmenovanych her; ratio >1.3 trigger | ✅ **OK.** detection_method sedi. Confidence: `anon / named / 2`. Evidence obsahuje oba rates. |
| B | Automatic grab | `capture_eval_drop` | Detekuje blunder/mistake (cp_loss>=100) obsahujici "x" v SAN | ⚠️ **CONFIDENCE BUG.** total_captures se pocita jen z blunder moves, ne ze vsech captures → total_captures == blunder_captures vzdy → confidence vzdy cap 0.95. detection_method slibuje "eval_drop", kod testuje "capture blunder existence" (nevyhodnocuje eval drop pattern). |
| C | Attention tunneling | `sector_focus_sequence` | Pocita consecutive error >= 2. Zadny check na sektor/souradnice. | ❌ **SEMANTIC BUG.** detection_method slibuje "sector_focus_sequence" (lokalita na desce), kod testuje pouze "consecutive errors" globalne. Threshold 2 je implicitni, neni definovan v PatternDef. |
| G | Color as modulator | `compare_per_color` | Porovnava blunder rate white games vs black games; ratio >1.4 trigger | ✅ **OK.** detection_method sedi. Confidence: `ratio / 3`. Evidence obsahuje oba rates + dominant side. |
| I | Bait trap | `bait_detection` | Detekuje "best" capture, ktery zlepsil eval z <30cp na >100cp | ❌ **SIGNIFICANT SEMANTIC BUG.** Pattern tvrdi "player leaves hanging pieces to punish opponent's automatic grab" (aktivni strategie). Kod testuje "player captured well and it was the best move" (profit z chyby soupere). Jde o **opačný smer** — kod detekuje, ze hrac tezil z chyby soupere, ne ze hrac nastrazil past. |
| J | Impulsive check block | `check_block_analysis` | `m.was_in_check and "x" not in m.move_san` pro blunder/mistake (cp_loss>=150) | ✅ **FIXED** (P0-1). Drive "+" in m.move_san — opraveno na spravnou velicinu. |
| O | Repetition avoidance greed | `repetition_refusal` | Hleda ploche eval okno (max-min<30cp pres 3 tahy), pak blunder v nasledujicich 3-5 tazich | ❌ **SEVERE SEMANTIC BUG.** detection_method slibuje "refusing threefold repetition" — detekci, ze hrac odmítl trojnásobne opakovani. Kod testuje "flat eval then blunder" — neoveruje existenci repeat pozice vubec. Miri na jiny jev. |
| P | Visual misrecognition | `forcing_move_classification` | Blunder (cp_loss>=150) v capture/tezke figure (Q,R), kdyz eval_before>0 | ⚠️ **PARTIAL BUG.** detection_method slibuje "forcing move classification", kod testuje "expensive mistake with heavy piece when winning". Heuristika sedi (tezka figura + capture + vyhra = pravdepodobne misread forcing chain), ale neoveruje forcing nature. |
| Q | Active defense | `defensive_phase_analysis` | Hra, kde hrac mel big blunder (cp_loss>200) ale stejne vyhral | ❌ **SEMANTIC BUG.** detection_method slibuje "defensive phase analysis" — analyzu obrany pod tlakem. Kod testuje "blundered but still won", coz muze byt zpusobeno blunderem soupere, ne aktivni obranou. Chybi check na counterplay. |
| Q1 | Desperate Gambit Mode | `desperate_gambit_analysis` | Po big blunderu (cp_loss>300): rejected queen trades + 10+ dalsich tahu + checks + win | ✅ **OK.** detection_method sedi. Kod testuje klicove prvky mechanismu. |
| R | Endgame relaxation | `endgame_positional_blunder` | cp_loss>=300 + eval_before>300 + phase=endgame | ✅ **OK.** detection_method sedi. Presna operationalizace mechanismu. Evidence obsahuje condition string. |

#### Souhrn

| Kategorie | Pocet | Detektory |
|-----------|-------|-----------|
| ✅ SEMANTICKY SPRAVNE | 5 | A, G, J, Q1, R |
| ⚠️ PARTIAL / CONFIDENCE BUG | 2 | B (confidence vzdy 0.95), P (heuristika, ne forcing analysis) |
| ❌ SEMANTICKY BUG | 4 | C (sector chybi), I (opačný smer), O (repetition chybi), Q (obrana chybi) |

#### Dalsi nalezy (mimo hlavni matici)

1. **Pattern S chybi v produkcnim kode** — dokumentovan v 01_DBCL §2.2 (INC-B, capture aversion under check, confidence ~40%), ale neni v `models/pattern.py` ani `services/pattern_detector.py`. V build planu zustava v P3-1.

2. **Evidence format nekonzistentni**:
   - Detailni: B, G, J, R — obsahuji konkretni podminky a hodnoty
   - Minimalni: O, P, Q — pouze `{affected_games: N}` (nedostatecne pro audit)
   - A, I — nekolik poli, ale chybi referencni hodnoty

3. **Confidence vzorce**:
   - Data-driven: A (`anon/named/2`), B (`blunder_captures/total_captures` — BUG), C (`len(affected)/5`), G (`ratio/3`), I (`bait_count/5`), J (`block_count/3`)
   - Hardcoded: O (0.6), P (0.5), Q (0.8), Q1 (0.7), R (0.7)
   - Hardcoded confidence je anti-pattern — neodrazi sílu ani konzistenci evidence

4. **Chybi pattern_detector_version** — neni jednotne ID, ktere by umoznilo odlisit faktury pred/po oprave. Bude reseno v P0-3.

5. **D-F a H neexistuji** — v `models/pattern.py` ani `pattern_detector.py` nejsou zadne patterny D, E, F, H. Build plan v2.0 uvadi "11 detektoru (A-R)" ale skutecnost je 9 (A, B, C, G, I, J, O, P, Q, Q1, R — coz je 11 s Q/Q1 jako separatni). Vzor `detect_all()` iteruje pres vsechny klice v `self.library.patterns`, takze neexistujici patterny nejsou volany.

6. **B: total_captures bug detail** — v _detect_b() je promenna `total_captures` inkrementovana UVNITR bloku `if m.classification in ("blunder", "mistake") and m.centipawn_loss >= 100:`. Pokud tah neni blunder, neni zapocitan. Takze `total_captures == blunder_captures` vzdy, a confidence = `min(1.0, 0.95)` = 0.95. Spravne: `total_captures` by mel pocitat vsechny captures napric vsemi tahy, nejen blunder captures.

#### Nové nálezy z CHESS_PATTERNS_AUDIT_2026-07-28 (W1-W10)

| ID | Priorita | Popis | Lokace | Fix |
|----|----------|-------|--------|-----|
| **W1** | CRITICAL | `game_ids` dropped v serializaci — přímá příčina halucinace | `match_patterns.py:155-170` | Přidat `"affected_games": list(m.game_ids)` do entry |
| **W2** | HIGH | Evidence schema nekonzistentní napříč 14 detectory — 7/14 chybí `affected_games` | `pattern_detector.py` všechny `_detect_*` | Normalizovat na jednotný formát |
| **W3** | MEDIUM | `_detect_j` chytá king moves jako "blocks" — false positive | `pattern_detector.py:225` | Přidat `"K" not in m.move_san` |
| **W4** | LOW | Pattern S/J overlap bez dedup | `pattern_detector.py:216,492` | Dokumentovat / implementovat |
| **W5** | MEDIUM | `affected_games` type mismatch int vs list (6 patternů) | C,O,P,Q1,R,S | Změnit `len(set(...))` na `list(set(...))` |
| **W6** | HIGH | I2 confidence formula broken (1/35 = 2.3%) | `pattern_detector.py:200` | Upravit vzorec pro nízké frekvence |
| **W7** | MEDIUM | CompressibilityValidator neodpovídá README (chybí entropy + sample score) | `compressibility_validator.py:13-23` | Implementovat chybějící komponenty |
| **W8** | LOW | Artifact validator nevaliduje `affected_games` | `pattern_artifact_validator.py:17-48` | Přidat validaci typu a formátu |
| **W9** | CRITICAL | `mistakes` list vždy prázdný — bug v game_analyzer.py | `game_analyzer.py:_run_analyze_pgn()` | Rozlišit blunder/mistake větve |
| **W10** | MEDIUM | `frequency` má 3 různé významy napříč patterny | Všechny `_detect_*` | Standardizovat na jednotný význam |

Detailní analýza: `docs/CHESS_PATTERNS_AUDIT_2026-07-28.md`

#### Akce z auditu

| ID | Akce | Typ | Status |
|----|------|-----|--------|
| AUD-01 | B: opravit total_captures bug (pocitat vsechny captures, ne jen blunder) | CODE BUG | ⏳ P2 |
| AUD-02 | C: detection_method "sector_focus_sequence" neodpovida kodu | SPEC BUG | ⏳ P2 |
| AUD-03 | I: detection_method → concept | CODE BUG | ✅ RESOLVED |
| AUD-04 | O: rename → Stagnační panika | CODE BUG | ✅ RESOLVED |
| AUD-05 | Q: detection_method "defensive_phase_analysis" neodpovida kodu | CODE BUG | ⏳ P2 |
| AUD-06 | P: heuristika misto forcing analysis | SPEC BUG | ⏳ P2 |
| AUD-07 | Hardcoded confidence → data-driven | ENHANCEMENT | ⏳ P2 |
| AUD-08 | Standardizovat evidence format | ENHANCEMENT | **W2+W5** ⏳ P0 |
| AUD-09 | test_pattern_semantic_contract.py | TEST | ✅ RESOLVED |
| AUD-10 | Pattern S do produkce | FEATURE | ✅ RESOLVED |
| AUD-11 | I detection_method opraven (I→concept, code→I2) | CODE BUG | ✅ RESOLVED |
| **W1** | game_ids v serializaci | CODE BUG | **P0** |
| **W6** | I2 confidence fix | CODE BUG | **P0** |
| **W9** | mistakes bug | CODE BUG | **P0** |
| **W3** | J king move false positive | CODE BUG | **P1** |
| **W7** | compressibility alignment | ENHANCEMENT | **P1** |
| **W10** | frequency standardizace | ENHANCEMENT | **P1** |

#### Opravene polozky z puvodniho v2.0

| ID | Stav | Poznamka |
|----|------|----------|
| F-002 (fen propagace) | ✅ P0-1 | `models/game.py:50-51` |
| F-003 (board.is_check) | ✅ P0-1 | `services/game_analyzer.py` |
| F-007 (pattern J) | ✅ P0-1 | `services/pattern_detector.py:191` |
| N7 (sort persist) | ✅ P0-1 | `tools/match_patterns.py` |
| F-004 (samostatny context_extractor) | ❌ NEBUDE | inlinovat do _run_analyze_pgn (P1-1) |
| F-005 (multi-PV v blunder pipeline) | ⏳ P1-2 | existuje, jen zapojit |
| F-008 (dve prompt mista) | ⏳ P0-5 + P1-3 | navrh protokolu v P0-5 |
| F-009 (SRSCard konzument) | ⏳ P1-5 | existuje schema, chybi producent |
| F-010 (win_prob) | ⏳ P0-4 | pole existuji, hardcoded 0.0 |
| F-011 (validator kolize) | ⏳ P2-3 | prejmenovat |
| F-013 (validator spec) | ⏳ P1-4 | mapovani claim->field v 01_DBCL §7 |
| F-014 (cache integrace) | ⏳ P2-1 | |
| F-015 (engine lock timeout) | ⏳ P2-2 | |

### P0-3: detector_version konstanta

**Goal:** Verze detektoru, ktera umozni odlisit fact sheets pred/po oprave.

- Konstantni string napr. v `models/game.py` nebo `services/pattern_detector.py`
- Format: `"DBCL-{YYYYMMDD}-{commit_abbrev}"`
- Inkrementovat pri kazde zmene detection_method (at uz oprava nebo pridani)
- Ulozit do BlunderFactSheet.detector_version (unity doc §6)

**File:** nova konstanta, evidentne v `models/game.py` nebo `__init__.py`

### P0-4: win_prob vypocet

**Goal:** Nahradit hardcoded 0.0 v `_run_analyze_pgn()` realnym winning-chances sigmoidem.

- Implementovat winning-chances sigmoid z lila (prahy 10/20/30%) — viz 01_DBCL §6
- Vstup: eval_cp v centipawnech
- Vystup: win_prob (0.0–1.0) pred a po tahu
- Prepnout klasifikaci: misto plocheho cp prahu (50/150/300) pouzit win% delta jako primarni signal
- Ulozit do MoveAnalysis.win_prob_before/after a BlunderFactSheet.win_prob_delta

**Files:**
- `services/game_analyzer.py:_classify_move()` — pricist logiku
- `models/game.py:MoveAnalysis` — pole uz existuji, jen naplnit
- `docs/01_DBCL_unity_synthesis.md` §6 — schema reference

### P0-5: Kontrakt mezi per-game a aggregate (K2 cleanup)

**Goal:** Navrhnout informacni protokol mezi per-game a aggregate LLM, ktery zabrani prenosu halucinace.

Per-game LLM halucinace se muze maskovat jako fakt v aggregate (02_DBCL §3.4). Reseni:
1. Per-game LLM output MUSI mit strukturovane `critical_moments[]` s `blunder_fact_sheet_id` a `claim_type`
2. Kazdy claim MUSI projit narrative validatorem ($7 unity doc) PRED aggregate
3. `summary` NESMI obsahovat chess claims (piece-on-square, check, capture)
4. Pokud per-game validace selze → fallback na raw BlunderFactSheet (zadny LLM per-game)

Navrh protokolu:

```
=== PER-GAME FEEDBACK PROTOCOL ===
critical_moments: [
  {
    ply: int,
    blunder_fact_sheet_id: str,
    claim_type: "descriptive" | "explanatory" | "prescriptive",
    claim_text: str              # musi projit validatorem
  }
]
summary: str                      # NESMI mit chess claims
```

Tento navrh je odvozen z 02_DBCL §3.5 (de-novo), neni v originalnim auditu.

---

## P1 — DBCL core (K3)

**Priorita:** HIGH, ale az po P0-2 (detektor audit).

### P1-1: Inline context extraction

V `services/game_analyzer.py:_run_analyze_pgn()` implementovat jako jeden pruchod:

1. Detekovat blunder window: delta > 300cp || classification in (blunder, mistake)
2. Extrahovat: FEN, was_in_check, legal_moves klasifikovane (captures/king_moves/blocks/checks)
3. Zavolat `engine_client.analyze_position(fen_before, depth=14, multipv=3)` — existuje (F-005)
4. Zavolat per-blunder pattern matcher (B, J, S, R, C)
5. Sestavit BlunderFactSheet
6. Ulozit pod klic `"dbcl_fact_sheets"` v game_cache JSON

**Nepsat samostatny modul** (viz F-004). Vse v existujici smycce.

### P1-2: BlunderFactSheet schema

Schema v 01_DBCL §6 — implementovat jako `@dataclass` (nebo `TypedDict`) v `models/game.py` nebo `models/analysis.py`.

```python
@dataclass
class BlunderFactSheet:
    fen_before: str
    board_state: dict     # was_in_check, checking_pieces, capture_checking_piece_possible, king_capture...
    legal_moves: dict     # total, captures[], king_moves[], blocks[], checks[]
    engine_lines: list    # rank, move_san, eval_cp, win_prob, pv[]
    move_played: str
    centipawn_loss: int
    phase: str
    pattern_matches: list # pattern_id, pattern_name, confidence, evidence
    detector_version: str
    context_window: dict  # moves_before[], moves_after[]
```

### P1-3: Guard-clause injection do prompt builderu

- `llm_client.py:build_coaching_prompt()` — vlozit BlunderFactSheet[] misto agregovaneho blobu
- `game_llm_cache.py:_build_game_prompt()` — stejna zmena
- Guard-clause sablona z 01_DBCL §9.2:

```
=== GUARD: DBCL v1.1 ===
You are a chess narrator. You MUST NOT make chess claims (check, block, capture, eval)
that are not explicitly present in the BlunderFactSheet fields below.
If a claim type is not in the fact sheet, do NOT narrate it.
Every eval number must match eval_before/eval_after/engine_lines[].eval_cp within +-20cp.
Patterns are hypotheses with evidence, not facts.
Unknown = silence, not assumption.
=== END GUARD ===
```

### P1-4: narrative_validator.py

Implementovat v `services/narrative_validator.py` (NE validator.py — konflikt s existujicim, viz F-011).

5 kategorii claim operatoru (01_DBCL §7):

| Claim typ | Example | Validace operator | Cilove pole BFS |
|-----------|---------|------------------|-----------------|
| piece-on-square | "Qf4" | existence v fen_before | fen_before |
| check (pozitivni) | "+" | rovnost was_in_check=true | board_state.was_in_check |
| check (negativni) | "not check" | rovnost was_in_check=false | board_state.was_in_check |
| capture | "takes" | existence v legal_moves.captures | legal_moves.captures |
| eval-cislo | "+823" | tolerance +-20cp | eval_before/after/engine_lines[].eval_cp |
| king-move | "Kc1" | existence v legal_moves.king_moves | legal_moves.king_moves |
| variation | "Kxc5 Ba4" | existence jako prefix engine_lines[].pv | engine_lines[].pv |

Reject loop: pokud validator fail → zopakovat LLM call s guard clause.

### P1-5: SRSCard jako konzument BlunderFactSheet

`SRSCard` uz ma pole `fen`, `correct_move_uci/san`, `pattern_id` (F-009).
Po P1-1 az P1-4: producent v `_run_analyze_pgn()` muze vytvaret SRSCard primo z BlunderFactSheet.

---

## P2 — Schema completion & konzistence

**Priorita:** MEDIUM — po P1.

### P2-1: Cache integrace

- BlunderFactSheet[] ulozit pod klic `"dbcl_fact_sheets"` v existujicim `{game_id}_{color}_d{depth}.json`
- Resit logiku priblizne shody hloubky v `_load_cached_analysis()`

### P2-2: Engine lock timeout exception handling

V BlunderFactSheet pipeline osetrit timeout z `engine_client._acquire_analysis_lock()` (120s, F-015).

### P2-3: Prejmenovat services/validator.py

- Stary: `services/validator.py` → `services/pattern_artifact_validator.py`
- Novy: `services/narrative_validator.py` (z P1-4)

---

## P3 — Dlouhodobe

**Priorita:** LOW.

### P3-1: Pattern S — Capture aversion under check

- `models/pattern.py`: pridat `PatternDef(id="S", ...)`
- Detektor: `centipawn_loss > 500 && in_check && king_capture_possible && not king_capture_played`
- Confidence: ~40 % (N=2), severity: critical

### P3-2: FSRS integration

Nahradit SM-2 formuli za `fsrs.Card` + `fsrs.Scheduler`.

### P3-3: Structured logging (P19)

`logger.warning()` per-failed-game, `skipped` counter v kazdem batch toolu.

### P3-4: Cross-LLM audit artifact

Předat `DBCL_cross_audit_artifact.md` dalsimu modelu (DeepSeek?) k validaci.

---

## P4 — Opponent Analysis Pipeline (NOVÉ v4.1)

**Priorita:** HIGH — navazuje na P3 (hotové detektory) a využívá existující game cache s dual perspective.

**Motivace:** 68 cached game IDs, 103 cache files (N=1 + N=2 perspective). N=2 analýza odhalila zero-blunder finding (0.00 vs 0.78 blunder/game). 3 design dokumenty vytvořeny (2026-07-29). Design docs: `OPPONENT_PERSPECTIVE_TOOL_DESIGN.md`, `OPPONENT_ELO_ETL_DESIGN.md`, `OPPONENT_COUNTERMEASURES_N2.md`.

**Engineering reference:** dscape/outprep — 9 patternů převzato (mergeConfig, version tracking, source-agnostic interface, ETL 3-phase, phase detection, per-skill temperature, Boltzmann selection, FEN-keyed trie, complexity depth).

### P4-1: Opponent profiling tools (4 new MCP tools)

Goal: Implement 4 new tools defined in `OPPONENT_PERSPECTIVE_TOOL_DESIGN.md`.

| Tool | Účel | Vstup | Výstup |
|------|------|-------|--------|
| `lichess_opponent_profile` | Profil jednoho opponent-a z pool cache | `game_ids[]`, `opponent_name` (optional) | ACPL, blunder_rate, pattern_freq, opening_repertoire, phase_weakness |
| `lichess_compare_sides` | Dual-perspective N1 vs N2 komparace | `game_ids[]` | N1_stats, N2_stats, delta table, hSNR proxy |
| `lichess_group_profiler` | Pool aggregace (N2, N3, ELO bandy) | `game_ids[]`, `group_by` | Per-group stats, heterogeneity, band classification |
| `lichess_hsnr_extract` | hSNR extraction z dual-perspective | `game_ids[]` | hSNR_components, suppression_map, timeline |

**Files:**
- `src/tools/opponent_profile.py` — NOVÝ
- `src/tools/compare_sides.py` — NOVÝ
- `src/tools/group_profiler.py` — NOVÝ
- `src/tools/hsnr_extract.py` — NOVÝ
- `src/services/opponent_stats.py` — NOVÝ
- `src/services/pool_aggregator.py` — NOVÝ

### P4-2: ELO estimation from pipeline metrics

Goal: Implement multi-feature ELO estimator bez engine calls, only from cached metrics (ACPLE + blunder/mistake rates + best_move_pct + pattern_freq).

**Design doc:** `OPPONENT_ELO_ETL_DESIGN.md`

| Feature | Váha (dle FIDE 2024) | Zdroj |
|---------|----------------------|-------|
| ACPL (avg) | ~0.40 | game_cache ACPl |
| Blunder rate (avg/game) | ~0.20 | game_cache blunders |
| Mistake rate (avg/game) | ~0.15 | game_cache mistakes |
| Best move % | ~0.10 | game_cache best_pct |
| Pattern frequency | ~0.10 | match_patterns output |
| Clock time (avg/move) | ~0.05 | game_cache clock (if avail) |

**Files:**
- `src/services/elo_estimator.py` — NOVÝ (multi-feature regrese)
- `src/services/opponent_tracker.py` — NOVÝ (N-category + band tracking)
- `src/services/etl_pipeline.py` — NOVÝ (3-phase: extract→transform→load)

### P4-3: match_patterns extension — group_by parameter

Goal: Rozšířit existující `lichess_match_patterns` o `group_by` parametr.

| group_by value | Výstup |
|----------------|--------|
| `"all"` (default) | Single pool — current behavior |
| `"n1:n2"` | Per-group pattern frekvence + delta |
| `"elo_band"` | Pattern frekvence per ELO band (1100-2800, 7 bands) |
| `"result"` | Per-result pattern frekvence |

### P4-4: N3 category architecture

N3 (draws) category — schema must exist even when N3=0 in current dataset. 3-category classification = future-proofing.

- N1: losses (as author perspective)
- N2: wins (as opponent perspective)
- N3: draws (currently 0, but schema must exist)

**File change:** `src/services/opponent_tracker.py` — N3 slot in all aggregation, zero-handling, reporting with "(0 games)" not absent.

### P4-5: Dual-perspective pipeline

hSNR extraction requires dual perspective — flip PGNs and re-analyze. Pipeline:

```
1. Extract author-perspective metrics (N1, current)
2. Flip PGN → opponent perspective (N2)
3. Run same analysis pipeline on flipped games
4. Compare: hSNR = N1_signal / (N1_signal + N2_noise)
```

**File:** `src/services/etl_pipeline.py` — `dual_perspective_flow()`

---

## Sekvence (krizove zavislosti)

```
P0-A (data integrity) ────────── W1, W9, W2+W5, W6
  │
  ├── W1 (game_ids v response) ── 2 radky, bez zavislosti
  ├── W9 (mistakes bug) ───────── game_analyzer.py, bez zavislosti
  ├── W2+W5 (evidence normalizace) ── pattern_detector.py
  └── W6 (I2 confidence) ─────── pattern_detector.py
  │
  ↓
P0-B (DBCL audit items) ──────── AUD-01, AUD-07
  │
  ↓
P1 (semantic integrity) ──────── W3, W7, W10, AUD-02, AUD-05, AUD-06
  │
  ↓
P2 (quality) ────────────────── W4, W8, N2, N3, N7
  │
  ↓
P3 (DBCL Phase 2 core) ──────── P0-3, P0-4, P0-5, P1-1..P1-5
  │
  ↓
P4 (Opponent Analysis) ──────── P4-1 (4 tools), P4-2 (ELO estimator), P4-3 (group_by), P4-4 (N3), P4-5 (dual-perspective)
```

---

## Key Files Reference

| Cesta | Ucel |
|-------|------|
| `01_DBCL_unity_synthesis.md` | Synteza + BlunderFactSheet v1.1 + validator spec + incident analysis |
| `02_DBCL_meta_evaluation.md` | Tri kanaly sumu, SFE terminologie, dve tridy halucinace |
| `services/pattern_detector.py` | 14 detektoru A-S — vcetne W1-W10 nalezů |
| `models/pattern.py` | PatternDef + PatternLibrary — 14 patternu |
| `services/game_analyzer.py` | _run_analyze_pgn — W9 (mistakes bug) |
| `services/compressibility_validator.py` | W7 — alignment s README |
| `services/pattern_artifact_validator.py` | W8 — chybi affected_games validace |
| `tools/match_patterns.py` | W1 — game_ids dropped v serializaci |
| `docs/CHESS_PATTERNS_AUDIT_2026-07-28.md` | **Hloubkovy audit: W1-W10, plen oprav** |
| `docs/PATTERN_DETECTOR_AUDIT_INJECT.md` | Kontextovy injekt pro silnejsi LLM |
| `docs/HALUCINACE_ROOT_CAUSE_ANALYSIS.md` | Root cause halucinace Pattern J |
| `services/llm_client.py` | build_coaching_prompt — guard-clause inject (P1-3) |
| `services/game_llm_cache.py` | _build_game_prompt — guard-clause inject (P1-3) |
| `services/narrative_validator.py` | NOVY: 5 kategorii claim operatoru |
| `services/validator.py` | STARY: prejmenovat na pattern_artifact_validator.py (P2-3) |
| `tests/test_pattern_semantic_contract.py` | NOVY: 1 pozitivni + 1 negativni pripad na detector |
| `.session/2026-07-26_context.md` | Deni session context |
| `docs/OPPONENT_PERSPECTIVE_TOOL_DESIGN.md` | **NOVÝ v4.1:** 4 opponent tools + 3 services design |
| `docs/OPPONENT_ELO_ETL_DESIGN.md` | **NOVÝ v4.1:** ELO estimation, ETL pipeline, domain-agnostic core |
| `docs/OPPONENT_COUNTERMEASURES_N2.md` | **NOVÝ v4.1:** 6 countermeasures, zero-blunder finding (N2=0.00) |
| `src/services/opponent_stats.py` | **NOVÝ:** Per-opponent stat aggregation |
| `src/services/pool_aggregator.py` | **NOVÝ:** Pool-level aggregation per N-category/ELO band |
| `src/services/elo_estimator.py` | **NOVÝ:** Multi-feature ELO regression (6 features) |
| `src/services/opponent_tracker.py` | **NOVÝ:** N-category + band tracking |
| `src/services/etl_pipeline.py` | **NOVÝ:** 3-phase ETL + dual-perspective flow |
