# 01 Evidence Digest — historická evidence a decision provenance

**Datum:** 2026-11-18 | **Autor:** LLM agent (opencode), extrakce z W2 trimmingu | **Status:** AKTIVNÍ
**Účel:** Jediné místo s unikátními root causes, měřeními a decision provenance vytěženými z 75 archivovaných artefaktů. Zabraňuje ztrátě faktů při kompresi `docs/` 81 → 9.

> **PRAVIDLO ČTENÍ:** Každé číslo níže je **dated evidence** pro uvedený HEAD / verzi / dataset, **ne aktuální kontrakt**. Aktuální stav: `SESSION_HANDOFF_2026-11-17.md`. Závazná rozhodnutí D1–D40: `AUDIT_INTEGRATION_2026-11-13.md`. Metodologie: `PATTERN_DISCOVERY_METHODOLOGY.md`. Runtime kontrakt: `COMPACT_JSON_FOR_LLM.md`. Zdrojové soubory jsou v `_ARCHIVE/` (git historie zůstává). Níže uvedené `file:line` odkazy míří do původních souborů před archivací.

---

## 1. Halucinace a fabrikace (kořeny, typologie, obrana)

| Fakt | Zdroj (před archivací) |
|---|---|
| Typologie **H1–H8** halucinací (např. H5 falešně pozitivní pattern, H8 přenos per-game → aggregate) | `01_DBCL_unity_synthesis.md` §3, L134–143 |
| „`board.is_check()` se v celém `src/` nevolá ani jednou"; `fen_before` se počítal a zahazoval | `01_DBCL_unity_synthesis.md` L37–41 (F-002/F-003) |
| Pattern J testoval `if "+" in m.move_san` → „tah dává šach", ne „hráč byl v šachu" | `01_DBCL_unity_synthesis.md` L76, L190 |
| Vyhození `game_ids` z tool odpovědi = „přímá příčina halucinace" | `CHESS_PATTERNS_AUDIT_2026-07-28.md` W1 L26–61, L48 |
| 3 kanály šumu **K1/K2/K3**; „Šum je strukturální, ne náhodný"; „Stockfish není ground truth" | `02_DBCL_meta_evaluation.md` L54, L104–204, L212–217 |
| „Halucinace není chyba pipeline — je chyba agentní disciplíny"; [DATA]/[IM] separace; `per_game_data:false`, když chybí `affected_games` | `HALUCINACE_ROOT_CAUSE_ANALYSIS.md` L64–71, L82–90, L120–121, L153 |
| Obrana v kanonickém kódu: `unclassified` a `evidence_gap` brání vymyšlenému mechanismu | `PATTERN_DISCOVERY_METHODOLOGY.md` L460 (kanon) |
| Pravidlo DATA-FABRICATION-001 (deterministická data jsou zdroj pravdy) | `_github/AGENTS.md` §6 (kanon) — **neduplikovat** |
| **Counterexample, ne fakt:** `sAtfdKTi` ply 16 „check/blok", eval 465→240 = *fabrikovaný příklad*, slouží jako důkaz selhání | `HALUCINACE_ROOT_CAUSE_ANALYSIS.md` L12–17 |

---

## 2. Katalog defectů s kořeny (historické, `file:line`)

| Defect / root cause | Zdroj |
|---|---|
| **N1** `mistakes` vždy prázdné (`game_analyzer.py:161–164`); **N2** `list(openings.values())[0]`; **N3** absolutní vs relativní ACPL (`diagnostician.py:52`); **N4** `frequency=int(blunder_rate)`; **F1'** mat → `cp_loss=0`; „ticho špatná data, ne crash" | `AUDIT_REPORT_lichess-analyzer-mcp_v2.md` §0–§3, L31–119, L145 |
| **W1–W10**: W2 evidence 1/14 správně, 6/14 `int`, 7/14 chybí; W6 `1/35*0.8 = 0.0228 → 2,3 %`; W10 `frequency` má 3 významy; W9=N1, W10=N4 | `CHESS_PATTERNS_AUDIT_2026-07-28.md` W1–W10 L26–363, L89–92, L209–213, L342–348 |
| Detektor semantic audit: C `sector_focus_sequence` vs po sobě jdoucí chyby; I „opačný směr"; O `repetition_refusal` vs flat-eval→blunder; Q `defensive_phase_analysis`; B `total_captures == blunder_captures` → confidence vždy 0,95; „Hardcoded confidence je anti-pattern" | `PHASE2_BUILD_PLAN.md` L55–75, L89, L95 |
| **B100** `getattr(a,"opening_name","Unknown")` → vše Unknown; **B98** opponent vždy black, `n1_count=0`; **B121** `KB_ROOT` 3× `..`; **B31** `{game_id}_llm.json` sdílený oběma barvami; **B16** eval error → `cp_loss=0` → „best"; **B5** kill sdíleného engine | `CODE_REVIEW_2026-08-01.md` §P1 L19–94 |
| **T1** `username` ignorován v `analyze_game.py:25` (default white) | `PIPELINE_TEST_REPORT_2026-07-24.md` L23–30 |
| Pattern J vývoj (3 opravy): `if "+" in SAN` → `was_in_check and "x" not in SAN` → `"K" not in SAN` (T1.4, bump `DETECTOR_VERSION`). **Konečné pravidlo je v `AUDIT_INTEGRATION` D11/T1.4, zde jen historie** | `01_DBCL` L76/L190; `CHESS_PATTERNS_AUDIT` W3 L115–135; `AUDIT_INTEGRATION` #8 L39, D11 L119–123 |
| **FIX-023 ≠ sign flip** — rozdílné referenční body + search variance + chybějící provenance; dual S implementace (SAN `x` vs `piece_type==KING`); quiet-blunder detector blind spot | `REFACTOR_PLAN_2026-11-11.md` L39, L41, L63, L200–204, L236–245 |
| Engine-dead sdílená reference (`_engine` zabit timeoutem); report parser `Blundry:` literál | `PLAN_SINGLE_GAME_CALIBRATION_2026-11-07.md` §11–12, L745, L759–763 |
| **F1 false positive**: hypotéza „mate-score crash" vyvrácena verifikací proti kódu | `AUDIT_REPORT_lichess-analyzer-mcp_v1.md` §3 L43, L129; `AUDIT_REPORT_v2` L115 |

---

## 3. Compact aritmetika a representation invarianty

| Fakt | Zdroj |
|---|---|
| `cp = bcp − eval_after_mover_cp`; jediný worked example: `RhkEoVUT` white 37 → `bcp=388`, `eval_after_mover_cp=124`, `cp=264` → **388 − 124 = 264** | `CALIBRATION_2_6_2026-11-17.md` L11, L26–28 |
| Před opravou R-1 gap **1–28 cp u 10 flagů**; po opravě 7/7, +74..+177 znaků, `nm`/`mit` ≤50 znaků | `CALIBRATION_2_6` L11, L20–24; `CHANGELOG.md` [2.14] L54–79 |
| Ne-anchor `eval_before_mover_cp` odstraněn v **2.6** (historicky se uvádělo 2.7 — opraveno ve W1) | `SESSION_HANDOFF_2026-11-17.md` §2; `CHANGELOG.md` [2.14] L62 |
| BlunderFactSheet v1.1 + claim→field validator (mapa tvrzení na pole payloadu) | `01_DBCL_unity_synthesis.md` §6–§7, L178–298 |
| Engine-lines silent fail: 30 % BFS mělo 0 `engine_lines` kvůli `board.san(m)` AssertionError u multi-move PV → sequential `board.copy()` + try/except; RUN_005 0/70 selhání | `README.md` L162–164, L657; `CONTEXT_INJECT.md` §5 |
| ACPL MAE **3.9** oproti Lichess referenci po perspective/best-move opravě | `README.md` L652–655 |

---

## 4. Cold re-run a reprodukovatelnost

| Fakt | Zdroj |
|---|---|
| Protokol: 4 hry × 2 barvy, `--no-cache`, backup `data/_backup_handoff_20261117/` | `HANDOFF_2_5_VERIFICATION_2026-11-17.md` L7–10 |
| **60/61 flagů má `|best_eval − engine_lines[0]| ≤ 10` cp (98,4 %)**; výjimka `QxL4Tr8u` black 58 `best=Re7` vs `Rxd6` `cp_loss=131` (legitimní); `zOk3TnoC` white 41 gap 16 „měřené, ne odhadnuté" | `HANDOFF_2_5` L16 |
| Cluster C strengths: 0.623 / 0.958 / 0.566 / 0.546 / 1.0; adaptivní `h128`/`h256`, ne `h512` | `HANDOFF_2_5` L17, L19 |
| Snapshot **13/14 souborů: evaly i metriky identické, sha256 NENÍ stabilní**; výjimka `RjV8Wvzo_white_d12` (25/25 odlišných eval, engine_calls 33→32); P0-1 dopad 115/138 změn (83 %) | `SNAPSHOT_SYSEQ_2026-11-11.json` L193–196 |
| FIX-003 determinism: `ENGINE_THREADS=1`, `Clear Hash` před top-level voláním, `use_cloud=False`, `LLM_TEMPERATURE=0.0`, `NODE_CAPS={12:80_000,14:150_000,16:400_000,18:1_000_000}`, cache `d14n150000`; byte-identické re-runs (`NxKgE4l8` 29.6 / 95.6 % / 6 flagů / T0.48 dvakrát; `lxO3gwd3` 18.2 / 97.3 % / 4 / T0.16 dvakrát); ACPL 43.3→29.6 „není zlepšení algoritmu" | `PLAN_SINGLE_GAME_CALIBRATION` §12 L782–812 |
| Pattern O: „Repetition avoidance greed" → „Stagnační panika"; `CR=47.8` měřil noise, ne signál | `CONTEXT_INJECT.md` §9; `README.md` L83 |

---

## 5. Dated experimenty (engine, komprese, pipeline, externí API)

| Experiment | Výsledek (historické) | Zdroj |
|---|---|---|
| Engine nutnost (N=2, d12, deepseek-v4-flash-free) | ACPL ~50–60 vs 32.7 a ~60–70 vs 35.0; halucinace 5 / přehlédnuté chyby 4 / kritické 6/12; „deterministická pipeline je nezbytná" | `LLM_DIFFERENTIAL_ANALYSIS_2026-07-19.md` L209–231 |
| TOT kandidát | MATCH >0.6 / TOT 0.3–0.6 / NO_MATCH <0.3; `min_games` eliminuje patterny z 1–2 her; „LLM nikdy negeneruje surová data" | `KALIBRACE_PLAN_2026-07-19.md` L194, L286–290, L423 |
| LCP / komprese | `final_confidence = 0.5×compression + 0.3×entropy + 0.2×sample`; příklad Q 227:1; >1.5 signál, >10 strong, <1 noise. **SUPERSEDED** (`PATTERN_DISCOVERY` §11.1: runtime je `coverage_score`, skutečná MDL v `services/mdl.py`) | `MIKOLOV_KOMPRESE_V_PATTERN_ARCHITEKTURE.md` L56–58, L155–158, L200–202 |
| Monolithic vs incremental LLM | +10 her = 68 873 tokenů ušetřeno (44 %); crossover ~30 her; N100 → 106 300 tok / 44,0 %; `token_ratio 3.64`, doporučení MONOLITHIC (N=5, free tier) | `differential_analysis_mono_vs_incr_20260720_160857.md` L39; `fullscale_comparison_20260720_183347.json` L29–40 |
| Externí API (2026-07-22) | berserk 0.14.0 odebral `client.users.get()` → `get_by_id()`; `/api/games/user/{username}` 404 = externí problém, použít `client.games.export(game_id)`; opening_explorer 401 → `client.opening_explorer.get_lichess_games(fen)` | `EXTERNAL_REFERENCE_REPORT_2026-07-22.md` L71–73, L114, L164, L168–172 |

---

## 6. Universa, baseline a data identity

| Položka | Hodnota | Zdroj |
|---|---|---|
| U0 `cache_analyses_raw` | 282 analýz, **8 873 tahů** | `CANDIDATE_PATTERNS_2026-11-12.md` L24 |
| U1 `flagged_factsheets_dedup` | **880 sheetů** (z 943; 63 duplicit) | `CANDIDATE_PATTERNS` L25, L38 |
| U2 `all_moves_dedup` | **8 109 tahů** | `CANDIDATE_PATTERNS` L26 |
| `good_moves_control` | **4 721 tahů** | `CANDIDATE_PATTERNS` L27 |
| Corpus | 259 dedup her / 2 137 flagged tahů | `PATTERN_DISCOVERY` L311; `CANDIDATE_PATTERNS` |
| 7-game Systeq snapshot | výběr 3 blitz + 3 rapid, 2 win / 2 loss / 2 draw; sha256 manifest | `SNAPSHOT_SYSEQ_2026-11-11.json` L7–10, L27–188 |
| Identity hashe | `dataset_sha256=5e41461a60453289268f6a919362a37f53efd701a438f32bbf19674e2a77b57f`; `pattern_lib_sha256=64ebbc6a4bd2cb8d8a9ea44ac2d328a08325e53b6cf6a49b1c4e14a7b31f4db2` | `CROSS_REPO_TRANSFER_MAP.md` L156–157 |
| Drift discrepance | 15 ID v baseline / 14 detektorů v PatternDetector (`I` manual_only) / 17 patternů v dokumentaci | `CROSS_REPO_TRANSFER_MAP` L123 |

---

## 7. FP limity, korekce proxy, depth a eval provenance

| Měření | Hodnota | Zdroj |
|---|---|---|
| FP strop | `hanging_piece` lift **1,04** (bez síly) vs `free_capture` lift **2,12** | `CANDIDATE_PATTERNS` L77–80 |
| Inverze proxy | `hanging_piece` 41,1 % → 7,4 % po opravě; dedup 6 477 → 8 109 | `CANDIDATE_PATTERNS` L299–304 |
| Bez proxy | **51/97** quiet blunderů | `CANDIDATE_PATTERNS` L172, L176 |
| Coverage | 375 matched (17,5 %) / 1762 unclassified (82,5 %); 1523 / 148 / 91; blunder matched 124/220 (56,4 %); PV 276/2137 (12,9 %) | `CANDIDATE_PATTERNS` L351–352; `README` L565–571; `PATTERN_DISCOVERY` L313–321 |
| Depth empirie | d12 29/58 s; d14 42/84 s; d18 4,9/9,8 min; d22 16,7/33,4 min; d=14 dává 95 % stejné klasifikace jako d=22 za 1/25 času | `DEPTH_POLICY.md` L88–100 |
| Depth scaling | `time(d) ≈ time(14) × 1,52^(d−14)`; d>20 odmítnuto (16,7 min > 15 min limit) | `depth_diff_report_NktJfZZy.md` L91, L105–125 |
| Konfigurace měření | 6 threads / Hash 512 / Stockfish 18 / i7-12700K / commit `89a0bf2`; **runtime truth je `src/lichess_analyzer_mcp/config/depth.py`**, nikoli `DEPTH_POLICY` §4.3 (`max_time_dual` smazán T3.0) | `depth_diff_report` L10–40; `SESSION_HANDOFF` §2 |
| Eval provenance | 101/7231 (1,4 %), 101/2010 (5,0 %), 228 blunderů, 98 (43,0 %), median 384; `FVhqtv1S` ply 89 cached 237 / fresh 168 | `REFACTOR_PLAN` L198, L554–572; `REPORT_STAV` L95, L105 |
| N-03 anchor gap | **97,8 %** tahů bez `best_eval` — 318 souborů, 9 412 tahů, 9 208 bez `best_eval` | `HANDOFF_V1_3_INTEGRATION_2026-11-15.md` L87–88 |
| `patterns: []` v single-game | **Není bug** — `min_games=3` gate (`pattern_detector.py:39`); N=1 confidence ceiling 25 ply→0,60 / 60→0,75 / 90→0,88; dual cache existuje, ale coaching je jednoperspektivní | `DEEP_DIVE_SINGLE_GAME_PATTERNS_2026-08-02.md` L17, L21, L36–43, L66–71, L104, L135–140 |

---

## 8. Decision provenance D1–D40

| Rozhodnutí / nález | Zdroj |
|---|---|
| D1–D6 původní návrhy (Feynman report §10) | `REPORT_STAV_2026-11-11.md` L203–208; `REFACTOR_PLAN` §8 L409–417 |
| Q1 = „Desperate Gambit Mode", Q2 = „Win despite blunder" (`pattern_detector.py:525,559`); J = „king move is an escape, never a block" (`:52`) | `HANDOFF_V1_3` L53–55, L103–115 |
| cp hodnoty `Qe3` 9465, `Qd3` 347, `Qg4` 152, `Kf3` 9197, `Kf1` 123; ACPL `a4bflvVZ` 828.0, `v6O0wNa7` 784.8 | `HANDOFF_V1_3` L53–55, L94 |
| N-01..N-06 detail (T-16 `%clk` parser, N-03 viz §7) | `HANDOFF_V1_3` L81–97 |
| **Závazné znění D1–D40 je v `AUDIT_INTEGRATION_2026-11-13.md` (§5, §11, §12, §14) — zde je pouze historická motivace, ne kopie** | `AUDIT_INTEGRATION` (kanon) |
| Audit workflow: 71 % nálezů potvrzeno (5/7), 9,6 nálezu/h, „dvoufázový audit jako standard", limit: twin neodhalí jednovětvové bugy (N1) | `PLAN_AUDIT_META_v1.0.md` §4 L236–258 |

---

## 9. Data identity, drift a negativní výsledky

| Položka | Zdroj |
|---|---|
| Audit taxonomie: defect / product gap / semantic debt / documentation drift; „Neuváděj čísla, která jsi neměřil"; „Kód je pravda, dokumenty jsou záměr" | `AUDIT_PROMPT_v2.0.md` L13–30 (kanon) |
| Drift pravidla obecně | `PATTERN_DISCOVERY` §11.5; `AUDIT_INTEGRATION` §10 L261–269 (kanon) |
| Negativní výsledky: Word2Vec 0,3107 / GloVe 0,2607 / MMR 0,5987 / SVD 0,5413; „`unclassified` není originální v informační vědě" (P~0,75) | `CROSS_REPO_TRANSFER_MAP` L39, L237–240, L253 |

---

## 10. Odmítnuté návrhy a záměrné ne-tvrzení

| Položka | Zdroj |
|---|---|
| CAND-A..J: přijaty **E** `flags[].patterns` (148 znaků) a **F** `clusters` (91 znaků); odmítnuty A/B/C/D/G/H/I/J; **CAND-C `position_type` odmítnut jako DATA-FABRICATION-001** | `v3_creative_proposals.json` L8–101 (zejm. L30–33, L48–64) |
| R1 „derive, don't store" (neukládat odvozené pole, počítat z deterministických dat) | `v3_creative_proposals.json` L15, L70 |
| Alias-once pravidlo; „report is summary, not fact source"; `behavioral_confidence` nekalibrované | `LLM_INPUT_AUDIT_2026-11-16.md` §4 L73–77 |
| MIKOLOV LCP vzorec označen jako **superseded** opravou v `PATTERN_DISCOVERY` §11.1 | `MIKOLOV` L7; `PATTERN_DISCOVERY` L480–484 |

---

## 11. Open / nekalibrované oblasti a anti-patterny

| Položka | Zdroj |
|---|---|
| `%clk` parser T-16; žádná Lichess parita; time trouble neměřen | `HANDOFF_V1_3` N-01 L81–82; `LLM_INPUT_AUDIT` L76–77 |
| Wave 2 gates Q3/Q4, `paired_blunder`, U1/U2 vyžadují ≥3-game cross-game validaci | `HANDOFF_2_7_WAVE1_VALIDATION.md` L29–32 |
| Anti-patterny v naracích: „Hra ? v zahájení ?, ACPL ?."; „Kritický moment: (žádné)"; `fallback (data dump)` + echo promptu; leakovaný CoT; „data nejsou k dispozici" | `coaching_report_*.md` (viz `02_COACHING_EXEMPLARS.md` §D) |
| VERIFY-1..9: nevyřešené rozpory cp loss 950 vs 778 a 1386 vs 1423 (stav k 2026-07-25) | `01_DBCL_unity_synthesis.md` §10 L452–464 |

---

*Extrakce provedena 2026-11-18 z 75 archivovaných artefaktů. Každý fakt má zdrojový anchor výše; před použitím v novém rozhodnutí ověř proti kanonickým souborům a deterministickým datům.*
