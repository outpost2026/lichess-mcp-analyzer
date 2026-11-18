# TRIMMING & CLEANUP — lichess-analyzer-mcp (návrh, verze 2)

**Datum:** 2026-11-18 | **Autor:** LLM agent (opencode), ke schválení autorem | **Status:** NÁVRH — **žádná operace nebyla provedena**
**Účel:** Jediný LLM-ready podklad pro razantní kompresi `docs/` z **81 artefaktů na 9 aktivních souborů**; mapa unikátních faktů, cílová architektura a verifikovatelný plán.
**Verze 2** přepisuje verzi 1 (ta navrhovala 41 souborů) na základě **hloubkového sémantického čtení celého obsahu docs/**. Původní metodika, GT citace, gate a seznamy dangling odkazů zůstávají v platnosti.
**Inspirace:** `B2B-Knowledge-Base/TEMP_TRIMMING/gt_v2_parts/` (mapa superseded → kanonizace → assemble + verify → kvantifikovaná redukce).

---

## 0. Provenance, rozsah, omezení

| Položka | Hodnota |
|---|---|
| Stav při analýze | `git status --short` = pouze `?? docs/TRIMMING_SNR_PLAN_2026-11-18.md` (tento artefakt) |
| Provedené operace | **pouze čtení + výpočty** (SHA256, mtime, referenční graf, 6-gram Jaccard, kontrola 54 path referencí) |
| Destruktivní operace | **ŽÁDNÉ.** Gate P84–P89 (incident #2): echo-back cesty + počtu, soft-delete přes `git mv`, integrity snapshot count+bytes |
| Základní pravidla | `_github/AGENTS.md` §2.4/2.6/2.7; `B2B-Knowledge-Base/AGENTS.md` §4.4/P1–P5; GT-080 (ASCII názvy) |
| GT retrieval (checkpoint) | GT-052 **P38** SNR framework; GT-059 **P44** kontraktní testy; GT-074 **P58** cache version governance; GT-050 **P35** deterministické kroky cacheovat; GT-042 **P17** workspace context export |
| DATA-FABRICATION-001 | Deterministická vrstva (`data/reports/*.json`, `data/game_cache/`) = **zdroj pravdy**; `docs/coaching_report_*.md` = odvozená narace |
| Metodika skóre | Adaptace GT-052/P38 na úroveň souboru: autorita 30 %, aktuálnost 25 %, unikátnost 25 %, znovupoužitelnost 20 %; dampenery duplicita / banner / drift |
| Jistota | P>0.8 u claimů s quoted bannerem, `git grep`, SHA256 nebo 6-gram shodou; hypotézy označeny |

---

## 1. Diagnóza (verze 2)

| # | Nález | Důkaz | Dopad |
|---|---|---|---|
| D1 | 81 artefaktů / 1 053 689 B v `docs/`; autor je nikdy nevyužije | inventář 2026-11-18 | nepřehlednost, LLM neví, co číst |
| D2 | Kanonické uzly mají **téměř nulové lexikální překrytí**, redundance je jinde | 6-gram Jaccard: žádný kanonický pár nad 0,05; nejvyšší `AUDIT_PROMPT_v1`↔`DIGITAL_TWIN` 0,132 | komprese = odstranění historie + extrakce, **ne slučování kanonu** |
| D3 | Největší redundance v reportech | `diagnosis_sladekkule` = **74% podmnožinou** `cross_game_sladekkule`; `cross_game_Systeq` = **51% podmnožinou** `cross_game_sladekkule`; `pool_101_202248` = 19% podmnožinou `185218` | 23 reportů lze nahradit 1 digestem |
| D4 | 19 dokumentů má sebeprohlášený „historický/zastaralý" banner | CHANGELOG [2.16]: „Historické audity … mají banner"; 4 soubory jsou z **85–90 %** nahrazeny CHANGELOG/HANDOFF | archivace bez ztráty |
| D5 | Version drift **uvnitř kanonu** | `COMPACT_JSON` název 2.3 / tělo 2.7 / schema path 2.1; `README` 4× „compact 2.1" vs „2.7 default", 254/254 vs 536, detector 20261111 vs 20261117; `PATTERN_DISCOVERY` (v1.7, „ZÁVAZNÝ") nezná U/V a říká 2.1 | aktivní SOT je nekonsistentní |
| D6 | 54 neplatných path referencí v trackovaných MD | README/README_en → `docs/MERGE_EVAL_feat_to_main.md`, `00_STRATEGIE/02_chess/...` (neexistují) | rozpad navigace |
| D7 | Přesná duplicita + generational churn | `00_STRATEGIE/report_coaching_anonymous_35.md` = `docs/coaching_report_anonymous_session_35.md` (SHA256 `A0D09BE6…`); `NxKgE4l8` ×18 v datech | násobení šumu |
| D8 | Konfliktní čísla v reportech | `yBgAmaI7` 21.3 (2×) vs **18.9**; cache `total_acpl=18.923`, accuracy 97.2, Bd2 176 cp → `_144837` je autoritativní | DATA-FABRICATION-001 porušení v odvozené vrstvě |
| D9 | Leakovaný chain-of-thought v reportu | `coaching_report_single_game_HmUBpeoJ_20260801_222903.md:15–29` „We need to produce…", „Make sure not to invent…" | evidence že narace ≠ data |

**Cíl:** `docs/` 81 → **9 aktivních** (−89 %), ~1 054 KB → ~165 KB (−84 %); 75 souborů přesunout do `_ARCHIVE/` (git mv), 3 nové soubory vytvořit.

---

## 2. Hloubková sémantická analýza — výsledky podle clusterů

### 2.1 Kanonické jádro (8 souborů + root)

| Pár | Překrytí | Anchors | Rozhodnutí |
|---|---|---|---|
| `COMPACT_JSON` ↔ `README` | ~70 % README L111–132 je digest field listu COMPACT_JSON L30–70 | P>0.9 | README ponechat **jen odkaz** |
| `COMPACT_JSON` ↔ `CLI_USAGE` | CLI §3 L252–277 je **explicitní stub**; L272–273 „Detaily …: docs/COMPACT_JSON_FOR_LLM.md"; CLI L144–158 = verbatim field list | P>0.9 | CLI §3 zrušit, ponechat 1 řádek odkazu |
| `README` ↔ `CHANGELOG` | 15–20 %; README „Známé odchylky" L491–578 duplikuje [2.1]/[2.2]/[2.11] | 0.85 | odchylky → EVIDENCE_DIGEST, CHANGELOG = provenance |
| `AUDIT_INTEGRATION` ↔ `SESSION_HANDOFF` | **~10 %, jen křížové odkazy** (HANDOFF L64 ↔ AUDIT L437) | P>0.9 | **ponechat oba**, neslučovat |
| `AUDIT_INTEGRATION` ↔ `PATTERN_DISCOVERY` | 15–20 %, konceptuální hranice single vs cross-game; „Kanon: AUDIT_INTEGRATION" (PM L600) | P>0.9 | ponechat oba, oddělit odpovědnosti |
| `CHANGELOG` ↔ `PATTERN_DISCOVERY` | měřicí tabulka 375/1762/124-220 identická (CL L504–516 ↔ PM L313–321) | 0.9 | jedna kopie → EVIDENCE_DIGEST §7 |

**Závěr:** žádný kanonický soubor nelze odstranit **bez ztráty**, ale lze odstranit jeho *historické sekce*: `AUDIT` §12–12.3 (L286–395), `PATTERN` §7–9/§13–14, `README` §Stav/§Známé odchylky/§Odkazy.

**Nové self-kontradikce v kanonu (overeno grepem):**
- `COMPACT_JSON:1` „Compact JSON 2.3", `:5` schema `single_game_v2_compact.json` (=2.1), `:19` `"v": "2.7"`; `:97` vs CHANGELOG [2.14] se rozcházejí v tom, který release odstranil `eval_before_mover_cp`.
- `README:281`, `:481` „compact JSON 2.1" vs `:9` „2.7 default"; `:156` `DBCL-20261111-dev` vs HANDOFF `:7` `DBCL-20261117-dev`; `:476–477` 254/254 + 15/15 vs `:9` 536 + 18; `:489` označuje `CONTEXT_INJECT` za zastaralý, ale `:83/:164/:657` ho cituje jako autoritu.
- `CLI_USAGE:37` „2.1" vs `:42` „2.7"; `:252` „2.4" vs `:254` „2.7"; `:150` D35 přiřazuje `game_impact` do compact 2.7, ale CHANGELOG/AUDIT ho datují do 2.2.
- `PATTERN_DISCOVERY:21` „6 per-move eventů (B,C,J,R,S,T)" a `:26/:51` „detailed 1.2 / compact 2.1" — chybí U/V a compact 2.7.

### 2.2 Listopadová historie (13 souborů) — unikátní fakta → EVIDENCE_DIGEST

| Fakt (P>0.9, ověřeno grepem) | Zdroj | Cíl |
|---|---|---|
| `bcp=388 − eval_after_mover_cp=124 = cp=264`; R-1 gap 1–28 cp u 10 flagů | CALIBRATION_2_6 L11,L26–28 | EVIDENCE §2 |
| Cold re-run 4 hry × 2 barvy, `--no-cache`, backup dir; **60/61 flagů gap ≤10 cp (98,4 %)**; gap 16 u `zOk3TnoC`; C-strength 0.623/0.958/0.566/0.546/1.0 | HANDOFF_2_5 L7–19 | EVIDENCE §3 |
| Snapshot **13/14 metriky identické, sha256 nestabilní**; výjimka `RjV8Wvzo_white_d12`; P0-1 115/138 změn (83 %) | SNAPSHOT_SYSEQ L193–196 | EVIDENCE §3, §5 |
| FIX-003 determinism: `Threads=1`, `Clear Hash`, `NODE_CAPS={12:80k,14:150k,16:400k,18:1M}`, `LLM_TEMPERATURE=0`, `d14n150000`; byte-identické re-runs; ACPL 43.3→29.6 „není zlepšení algoritmu" | PLAN_SINGLE_GAME L782–812 | EVIDENCE §3 |
| Root cause FIX-023 **≠ sign flip** (referenční body + search variance + chybějící provenance); dual S; quiet-blunder blind spot | REFACTOR_PLAN L39,L63,L200–245 | EVIDENCE §2, §4 |
| 101/7231 (1,4 %), 101/2010 (5,0 %), 228/98 (43 %), median 384, `FVhqtv1S` 237→168 | REFACTOR_PLAN L198, L554–572 | EVIDENCE §7 |
| Universa **U0=8 873 / U1=880(z 943) / U2=8 109 / good=4 721** (grep: nikde jinde) | CANDIDATE_PATTERNS L24–27 | EVIDENCE §5 |
| FP: hanging lift 1,04 vs free_capture 2,12; inverze 41,1 %→7,4 %; dedup 6 477→8 109; 51/97 bez proxy; 17,5/82,5 % | CANDIDATE_PATTERNS L77–80,L172–176,L299–304,L351–352 | EVIDENCE §6 |
| D13–D25 rationale (Q1 „Desperate Gambit Mode", Q2 „Win despite blunder", J `was_in_check`), N-03 **97,8 % / 318 souborů / 9 412 / 9 208** | HANDOFF_V1_3 L53–55,L81–115 | EVIDENCE §8 |
| `dataset_sha256=5e41461a…`, `pattern_lib_sha256=64ebbc6a…`; drift 15 baseline / 14 detektorů / 17 dokumentů | CROSS_REPO_TRANSFER_MAP L123,L153–159 | EVIDENCE §9 |
| R1 „derive, don't store"; CAND-E 148 znaků / CAND-F 91 znaků; CAND-C odmítnut jako DATA-FABRICATION | v3_creative_proposals L15,L48–64,L70 | EVIDENCE §10 |

**100% subsumováno (pure ARCHIVE):** `LLM_INPUT_AUDIT_2026-11-16.md` (~90 %), `REPORT_STAV_2026-11-11.md` (~85 %), `HANDOFF_2_7_WAVE1_VALIDATION.md` (~85 %), `CODE_REVIEW_2026-11-16_VERIFICATION.md` (~80 %).

### 2.3 Červenec–srpen (27 souborů) — unikátní fakta → EVIDENCE_DIGEST

| Fakt | Zdroj | Cíl |
|---|---|---|
| Typologie **H1–H8** halucinací; „`board.is_check()` se v celém src/ nevolá ani jednou"; Pattern J test `if "+" in m.move_san` = tah dává šach, ne hráč byl v šachu | 01_DBCL L37–41,L76,L134–143,L190 | EVIDENCE §1, §2 |
| 3 kanály šumu K1/K2/K3; „Šum je strukturální, ne náhodný"; „Stockfish není ground truth" | 02_DBCL L54,L212–217 | EVIDENCE §1 |
| Defekty N1–N7 (např. `mistakes` vždy prázdné, `game_analyzer.py:161–164`); W1–W10 (W1 `game_ids` dropped = „přímá příčina halucinace", W2 1/14 správně, W6 2,3 %, W10 3 významy `frequency`); B100/B98/B121/B31, B16, B5; T1 `username` ignorován | AUDIT_REPORT_v2, CHESS_PATTERNS_AUDIT, CODE_REVIEW_08, PHASE2_BUILD_PLAN, PIPELINE_TEST_REPORT | EVIDENCE §1, §2 |
| „Halucinace není chyba pipeline — je chyba agentní disciplíny" + [DATA]/[IM] | HALUCINACE L82–90,L153 | EVIDENCE §1 (pravidlo už v AGENTS §6) |
| TOT 0,3–0,6, `min_games=3` proti noise, „LLM nikdy negeneruje surová data"; experiment ACPL +25–35 cp / 50 % FP / 6/12 kritických | KALIBRACE_PLAN L194,L286–290,L423; LLM_DIFFERENTIAL L209–231 | EVIDENCE §4 |
| Depth empirie d12 29/58 s, d14 42/84 s, d18 4,9/9,8 min, d22 16,7/33,4 min; `time(d)≈time(14)×1,52^(d−14)`; d>20 odmítnuto | depth_diff_report L14–19,L91,L105–125; DEPTH_POLICY L88–100 | EVIDENCE §7 |
| `patterns: []` = `min_games=3` gate, **ne bug**; N=1 confidence ceiling 0,60/0,75/0,88; motif vs Pattern T ontologie | DEEP_DIVE L17,L36–43,L66–71,L135–140 | EVIDENCE §7 + cross-link PD §11.7 |
| Audit workflow 71 % potvrzeno, 9,6 nálezu/h, dvoufázový standard | PLAN_AUDIT_META §4 L236–258 | EVIDENCE §9 |
| berserk `users.get()` → `get_by_id()`; `/api/games/user/...` 404 externí | EXTERNAL_REFERENCE L71–73,L168–172 | EVIDENCE §4 (ověřit proti kódu) |
| LLM nedeterminismus, crossover ~30 her, N100 44 % úspora | differential_analysis L43,L39; fullscale_comparison L29–40 | EVIDENCE §4 |

**Pure process (P2/P3, ARCHIVE):** `02_DBCL_meta_evaluation`, `AUDIT_PROMPT_v1.0` (sám „Drženo jen jako historie"), `AUDIT_REPORT_v1`, `DIGITAL_TWIN_v1.0`, `PLAN_AUDIT_META` §2–3, `META_ANALYZA_METODOLOGIE`, `IMPLEMENTACE_SINGLE_GAME...`, `PLAN_COACHING_TOOLS_v1`, `PLAN_DEPTH_POLICY_v1`, `lichess_mcp_user_guide`, velké části `PHASE2_BUILD_PLAN`/`KALIBRACE_PLAN`.

**Důležité:** ~60–70 % červencových nálezů má listopadového nástupce v `PD`/`AI`/`CD` (audit ~70–75 %, depth ~70 %, DBCL ~25–30 %). Zbylých 30–40 % je unikátní a tvoří povinný obsah EVIDENCE_DIGEST. Všechny převzaté hodnoty musí nést banner „historické měření pro HEAD X, není aktuální kontrakt".

### 2.4 Reporty (31 souborů / 234 KB → 1 digest ~25 KB, −85–90 %)

| Exemplář | Unikátní technika |
|---|---|
| `coaching_report_single_game_HmUBpeoJ_DSV4F.md` | deterministický [DATA]/[IM] formát bez LLM, DATA-FABRICATION-001 čistý → **vložit celý** |
| `coaching_report_NktJfZZy.md` | dual-perspective hSNR (49,4 vs 63,1 ACPL, koncovka 15,6 vs 95,6, „poslední chyba vyhrává") → **vložit celý** |
| `coaching_report_author_4losses.md` | autorova perspektiva + per-game→aggregate (Cm02bEZC 8 blunderů, c6 4081 cp, průměr 78,7 vs 26,9) |
| `coaching_report_Systeq_VariantB_20games_20260901_092817.md` + `coaching_report_sladekkule_VariantB...` + `comparison_Systeq_vs_sladekkule...` | cross-game N=20 + A/B + anomaly detector (depth drift −8,0, PATTERN_CONF_DROP O85→40/B88→17) |
| `coaching_report_opponent_pool_73.md` | opponent_pool + n1/n2 profiling (n2 ACPL 29,4 vs n1 54,2, 6/12 zero-blunder, O 60 % vs 29 %) |

**Konflikty vyřešeny deterministickou vrstvou:** `yBgAmaI7_20260905_144837` (ACPL 18,9) = cache 18,923 / 97,2 % / Bd2 176 cp; zbylé dvě generace (21,3) archivovat. `cross_game_Systeq` 44,66 vs 43,31 = rozdílné prahy detekce (log: PATTERN_CONF_DROP) → autoritativní je příslušný `data/reports/*.json`. Anonymous 33 (G 92 %/2,75×) vs 35 (A 85 %/1,7×) ponechat jako dvě položky katalogu s N a datem, neslučovat.

**Anti-patterny do katalogu:** fallback „(data dump)", „Hra ? v zahájení ?, ACPL ?.", „Kritický moment: (žádné)", leakovaný CoT (HmUBpeoJ cascade), self-congratulation „bez halucinace".

---

## 3. Cílová architektura `docs/` — 9 aktivních souborů

| # | Soubor | Stav | Velikost | Role |
|---|---|---|---|---|
| 1 | `00_DOCS_CONTRACT.md` | NOVÝ | ~2 KB | READ ORDER + autorita: HANDOFF = current state, DIGEST = evidence, COMPACT_JSON = runtime kontrakt, ostatní archiv; banner policy; P1 one-source rule |
| 2 | `SESSION_HANDOFF_2026-11-17.md` | KEEP + drift fix | 8 KB | vstupní bod nové session, otevřené položky, agent rules |
| 3 | `AUDIT_INTEGRATION_2026-11-13.md` | KEEP, ořezat §12–12.3 | ~28 KB | závazné rozhodnutí D1–D40 (binding) |
| 4 | `PATTERN_DISCOVERY_METHODOLOGY.md` | KEEP, ořezat §7–9/§13–14, fix U/V + 2.7 | ~35 KB | závazná metodologie v1.7 (binding) |
| 5 | `COMPACT_JSON_FOR_LLM.md` | KEEP + fix title/path + **GAME_FULL jako appendix** | ~28 KB | runtime kontrakt compact 2.7 + spec game_full 1.0 |
| 6 | `CLI_USAGE.md` | KEEP + zrušit §3 stub | ~13 KB | 18 tool invocations, PowerShell quoting, exit codes |
| 7 | `HALUCINACE_ROOT_CAUSE_ANALYSIS.md` | KEEP + banner | 7 KB | živě citovaný §5.2; pravidlo samotné je v AGENTS §6 |
| 8 | `01_EVIDENCE_DIGEST.md` | NOVÝ | ~22 KB | 13 sekcí unikátních root causes, měření a decision provenance |
| 9 | `02_COACHING_EXEMPLARS.md` | NOVÝ | ~27 KB | 2 plné exempláře + 3 summarizing + findings catalogue + anti-patterny |

**Root (mimo docs):** `README.md` (ztenčit: odstranit §Compact/§Stav/§Známé odchylky/§Odkazy → odkazy na 1–9), `CHANGELOG.md` (ponechat jako provenance; starší [2.0]–[2.3] lze archivovat, git history zůstává).

**Variantní decision (Q7):** pokud autor trvá na absolutním minimu, lze `CLI_USAGE.md` (6) sloučit do `SESSION_HANDOFF` §0/§3 + `COMPACT_JSON` a `HALUCINACE` (7) do DIGEST §1 → **7 souborů**. Doporučení: ponechat 8. a 7. pro operativní použití.

### 3.1 TOC `01_EVIDENCE_DIGEST.md` (13 sekcí)

| § | Název | Obsah (zdroje) |
|---|---|---|
| 0 | Provenance & banner rule | všechny archivované zdroje; „každé číslo je dated evidence, ne aktuální truth" |
| 1 | Halucinace a fabrikace | H1–H8, K1–K3, `game_ids` dropped, [DATA]/[IM], AGENTS §6, PD L460 |
| 2 | Katalog defectů s kořeny | N1–N7, W1–W10, B100/B98/B121/B31/B16/B5, T1, J predicate evolution, FIX-023 ≠ sign flip |
| 3 | Compact aritmetika & invarianty | 388−124=264, R-1 gap, 7/7, nm/mit, BFS v1.1, claim→field |
| 4 | Cold re-run & reprodukovatelnost | 4×2 `--no-cache`, 60/61, gap 16, 13/14 snapshot, FIX-003, byte-identické re-runs |
| 5 | Dated experimenty | engine necessity, mono-vs-incr 44 %, LCP 227:1 (označit jako superseded), TOT/min_games, berserk API |
| 6 | Universa & baseline | U0/U1/U2/good, 282/259/2137, 7-game snapshot, dataset/pattern_lib sha256 |
| 7 | FP limity & korekce proxy | lift 1,04/2,12, inverze 41,1→7,4 %, 51/97, 17,5/82,5 %, depth tabulka + 1,52^(d−14) |
| 8 | Eval provenance & quiet blunder | 101/7231, 101/2010, 228/98, median 384, N-03 97,8 %, D1–D25 decision ledger |
| 9 | Data identity & drift | sha256 hodnoty, 15/14/17, audit 71 %/9,6 nálezu/h, negativní výsledky Word2Vec 0,3107 atd. |
| 10 | Odmítnuté návrhy | CAND-A..J, E=148/F=91 znaků, R1 guardrail, MIKOLOV §11.1 korekce |
| 11 | Open / nekalibrované | T-16, žádná Lichess parita, wave-2 gates, no-data filler anti-patterny |

### 3.2 TOC `02_COACHING_EXEMPLARS.md`

1. **Header** — DATA-FABRICATION-001 kontrakt, odkazy na `data/reports/*.json`, P84–P89 pro ostatních 30 souborů.
2. **A. Plné vložení** — `HmUBpeoJ_DSV4F` (2,8 KB) + `NktJfZZy` (7,9 KB).
3. **B. 1 odstavec + odkaz** — `author_4losses`, `Systeq_VariantB` (+ sladekkule arm + comparison), `opponent_pool_73`, `cross_game_Systeq`, `anonymous_33/35` (jen čísla).
4. **C. Findings catalogue** — 11 řádků s konkrétními čísly + zdrojovým path/section (ACPL 18,92/cache; Ba2 161 cp; Cm02bEZC 4081 cp; dual 49,4/63,1; cross-game 44,66/64,98; A/B 44,7 vs 65,0; anomaly z+2,41; opponent n2 29,4; anonymous G/A; depth drift).
5. **D. Anti-patterny** — leaked CoT, placeholder narace, stale ACPL 21,3, „data nejsou k dispozici".

---

## 4. Plán provedení (waves) — **nezačít bez souhlasu autora**

Před každou destrukcí P84 echo-back (plná cesta + počet), P86 soft-delete, P87 integrity snapshot. Žádný `git clean`, `reset --hard`, `rebase`, `amend`, `Remove-Item -Recurse/-Force`.

| Vlna | Obsah | Riziko |
|---|---|---|
| **W0 — lokální hygiena** | 9 root logů + `.coverage` + 3 `docs/*.log` + staré `logs/` (vše gitignored). Index 811 KB regenovat ad hoc | nízké |
| **W1 — oprava driftu** | COMPACT title 2.3→2.7 + schema path → `single_game_v2_compact_2.7.json` + vyřešit L97; CLI §3 zrušit + 2.1→2.7; README 4× drift; PATTERN U/V + 2.7; 54 dangling referencí | nízké |
| **W2 — extrakce (P0 před přesunem)** | Vytvořit `01_EVIDENCE_DIGEST.md` ze 13sekčního TOC (§3.1) a `02_COACHING_EXEMPLARS.md` ze 4 exemplářů (§3.2); ověřit, že každé unikátní číslo má zdroj | **střední** |
| **W3 — komprese docs/** | `git mv` 75 souborů do `_ARCHIVE/` (vč. GAME_FULL po vtělení do COMPACT appendixu, SNAPSHOT po vtělení do DIGEST §3/§5, TRIMMING plánu po schválení); ořezat AUDIT §12–12.3 a PATTERN §7–9/§13–14; ztenčit README; vytvořit `00_DOCS_CONTRACT.md` | střední |
| **W4 — mimo docs** | `scripts/` 39→17, `schemas/` 10→5 (+ Q2 decision), `00_STRATEGIE/` 13→0, `.session/` 4→1, `data/reports` prune ~50–60 generací; **stockfish nemazat** | vyšší |
| **W5 — verifikace & prevence** | `scripts/verify_docs_trimming.py` (10 assertions); commit `[DOCS] trimming: hSNR komprese 81→9 (SNR)`; push jen na vyžádání | nízké |

**Doporučená kadence:** W1 → W2 → **kontrolní bod autora** → W3 → W4 → W5. Extrakce (W2) musí předcházet archivaci (W3).

---

## 5. Verifikace (mirror `TEMP_TRIMMING/assemble_verify.py`)

```
1. count(active docs) == 9                              [nebo schválená varianta 7]
2. 0_duplicate_SHA256 among tracked .md/.json           [přesná duplicita = FAIL]
3. 0_dangling path refs in 9 aktivních souborech         [regex...]
4. 0 references from active docs into _ARCHIVE/          [P5 drift check]
5. every unique fact from §2.2/§2.3 has source anchor in EVIDENCE_DIGEST
6. version consistency: 2.7 v COMPACT title+tělo, CLI, README, PATTERN
7. ASCII filenames: ^[A-Za-z0-9._/-]+$                  [GT-080]
8. 0 B tracked except */__init__.py                     [P3]
9. pre/post integrity snapshot: count + bytes per dir   [P87]
10. gates beze změny: pytest 536 passed, Ruff clean, mypy 74 files
```

`[OK]/[FAIL]` per assertion, `sys.exit(0 if ok else 1)`; `$env:PYTHONIOENCODING='utf-8'`, `python -X utf8`, `sys.stdout.reconfigure(encoding='utf-8', errors='replace')`.

---

## 6. Otevřené otázky

| # | Otázka | Doporučení | P |
|---|---|---|---|
| Q1 | `CONTEXT_INJECT.md` archivovat po extrakci §5/§9 do DIGEST §4? | Ano (README ho sám označuje za zastaralý) | 0,8 |
| Q2 | `single_game_v2_compact_2.3.json` — 2 testy ho čtou | Ponechat do úpravy testů | 0,9 |
| Q3 | Ponechat `AUDIT_REPORT_v2` + `DIGITAL_TWIN` jako auditní evidence v `_ARCHIVE/`? | Ano, oba (v2 = code-verified, twin = vstup) | 0,7 |
| Q4 | Stockfish `sse41` / `stockfish.exe` mazat? | **Ne** bez kontroly CPU (pin v `config/engine_identity.json`) | 0,95 |
| Q5 | Soft-delete přes `git mv`? | Ano, rollback přes git | 0,9 |
| Q6 | Archivovat `AUDIT_PROMPT_v2.0.md`? | Ne, ponechat jako reprodukovatelný protokol (v archivu je jen v1) | 0,75 |
| Q7 | 9 souborů nebo ultra-varianta 7 (sloučit CLI_USAGE + HALUCINACE)? | **9**; 7 jen na explicitní přání | 0,8 |

**Největší riziko:** ztráta unikátních faktů při hromadném `git mv`. Proto W2 (extrakce + kontrola zdrojových anchorů) předchází W3.

---

## Appendix A — archivovaných 75 souborů (přesun z `docs/` do `_ARCHIVE/`)

`01_DBCL_unity_synthesis`, `02_DBCL_meta_evaluation`, `AUDIT_PROMPT_v1.0`, `AUDIT_REPORT_v1`, `AUDIT_REPORT_v2`, `CALIBRATION_2_6`, `CANDIDATE_PATTERNS`, `CODE_REVIEW_2026-08-01`, `CODE_REVIEW_2026-11-16_VERIFICATION`, `CONTEXT_A_ZAMER`, `CONTEXT_INJECT`, `CROSS_REPO_TRANSFER_MAP`, `DEEP_DIVE_SINGLE_GAME_PATTERNS`, `depth_diff_report_NktJfZZy`, `DEPTH_POLICY`, `differential_analysis_mono_vs_incr`, `DIGITAL_TWIN_v1.0`, `EXTERNAL_REFERENCE_REPORT`, `fullscale_comparison_20260720_183347.json`, `GAME_FULL_1.0` (po vtělení), `HANDOFF_2_5`, `HANDOFF_2_7`, `HANDOFF_V1_3`, `CHESS_COACHING_PROMPT_TEMPLATES` (runtime = `prompt_builder.py`), `CHESS_PATTERNS_AUDIT`, `IMPLEMENTACE_SINGLE_GAME_PATTERN_DISCOVERY`, `KALIBRACE_PLAN`, `lichess_mcp_user_guide`, `LLM_DIFFERENTIAL_ANALYSIS`, `LLM_INPUT_AUDIT`, `META_ANALYZA_METODOLOGIE`, `MIKOLOV_KOMPRESE`, `opponent_analysis_anonymous_pool`, `opponent_countermeasures_N2`, `OPPONENT_ELO_ETL_DESIGN`, `OPPONENT_PERSPECTIVE_TOOL_DESIGN`, `PHASE2_BUILD_PLAN`, `pipeline_* ×3 (.log)`, `PIPELINE_TEST_REPORT`, `PLAN_AUDIT_META_v1.0`, `PLAN_COACHING_TOOLS_v1`, `PLAN_DEPTH_POLICY_v1`, `PLAN_SINGLE_GAME_CALIBRATION`, `REFACTOR_PLAN`, `REPORT_STAV`, `SNAPSHOT_SYSEQ_2026-11-11.json` (po vtělení), `TRIMMING_SNR_PLAN_2026-11-18.md` (po odsouhlasení), `v3_creative_proposals.json`, + **23 coaching_report_*.md** (až na 2 vložené do exempláře) + `comparison_Systeq_vs_sladekkule.md`.

## Appendix B — dangling path reference (54; priorita W1)

Kanonické: `README`/`README_en` → `docs/MERGE_EVAL_feat_to_main.md`, `00_STRATEGIE/02_chess/chess_mcp_strategy_v1.md`, `data/runs/RUN_005_DBCL_v3_2026-07-27.md`; `AUDIT_INTEGRATION`/`CONTEXT_INJECT`/`DEPTH_POLICY`/`PLAN_SINGLE_GAME`/`CHANGELOG` → `config/depth.py` (smazán T3.0); `PLAN_SINGLE_GAME` → `logs/audit_202611.json`, `scripts/run_golden_single_game.py`, `tests/test_golden_single_game.py`; `CROSS_REPO_TRANSFER_MAP` → `tests/test_drift.py`; `PHASE2_BUILD_PLAN` → `docs/PATTERN_DETECTOR_AUDIT_INJECT.md`, 9 `src/services|tools/...`.
Zbytek (37) pochází z archivované éry → řeší se W3 bez editace obsahu.

## Appendix C — použité zdroje a nástroje

- `_github/AGENTS.md`, `B2B-Knowledge-Base/AGENTS.md` (P1–P5, P84–P89, GT-080, DATA-FABRICATION-001)
- `gt_search`/`gt_get_entry`: GT-052/P38, GT-059/P44, GT-074/P58, GT-050/P35, GT-042/P17 (dataset `source_version 24`)
- `TEMP_TRIMMING/gt_v2_parts/01_header_intro.md`, `assemble_verify.py`, `extract_sections.py`
- 4 nezávislé hloubkové sémantické analýzy (kanonické jádro / listopadová éra / červenec–srpen / reporty) — plné čtení ~80 souborů
- Deterministické výpočty: `git ls-files`, SHA256, mtime, referenční in-degree graf, 6-gram Jaccard (80 souborů / 128 168 shingles), 54 path referencí, ověření cache `yBgAmaI7_white_d14.json`
