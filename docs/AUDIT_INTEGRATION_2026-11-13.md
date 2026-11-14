---
title: Integrace auditu 2026-11-13 — kanonická pravda pro single-game, perspektivy a timeline
date: 2026-11-14
verze: 1.1
status: ZÁVAZNÝ ROZHODOVACÍ ARTEFAKT
audit_head: 7e828b02
navaznost: PATTERN_DISCOVERY_METHODOLOGY.md (v1.7), GAME_FULL_1.0.md, REFACTOR_PLAN_2026-11-11.md, PLAN_SINGLE_GAME_CALIBRATION_2026-11-07.md, COMPACT_JSON_FOR_LLM.md, CANDIDATE_PATTERNS_2026-11-12.md
změny_1_1: Tier 1-3 provedeny 2026-11-14; `game_full` 1.0 implementován a zdokumentován (`GAME_FULL_1.0.md`); T3.3 (interaction events) vědomě neimplementováno do measurement spec.
účel: Zaznamenat, co z auditu 2026-11-13 platí, co bylo překlasifikováno a jak se tím mění plán. Nahrazuje dosavadní pořadí prací pro single-game větev; nemění cross-game kontrakty.
---

## 0. Účel a princip

Audit z 2026-11-13 (HEAD `7e828b02`) tvrdí, že single-game pipeline analyzuje jen jednu barvu a že z toho plyne architektonická mezera. Tento dokument je **integrace auditu do kanonické pravdy**, ne jeho kopie:

- každý nález má podobu **claim → důkaz v kódu → rozhodnutí**;
- každé rozhodnutí má ID (`D6`–`D11`), aby se na něj dalo odkazovat z kódu, testů a dalších dokumentů;
- každá změna plánu je explicitní; nic se nemění „mimochodem“.

**Proč to vzniká:** dosavadní iterace (P1, P2 kroky A–C) vycházely z plánu `REFACTOR_PLAN_2026-11-11.md` a `PATTERN_DISCOVERY_METHODOLOGY.md`. Audit mění priority pro single-game větev. Bez jednoho rozhodovacího artefaktu by vznikly dvě pravdy: metodologie by dál mluvila jen o cross-game a kód by se měnil podle auditu. To je drift.

**Co tento dokument NENÍ:** není to nový audit, není to implementace a není to náhrada metodologie. Je to rozhodovací vrstva mezi auditem a kódem.

---

## 1. Ověření auditu proti kódu

Metoda: každé tvrzení ověřeno čtením zdrojáků na HEAD `7e828b02`, ne z dokumentace. Uvedené funkce jsou primární důkaz; čísla řádků jsou orientační a nesmí se na ně vázat testy.

| # | Tvrzení auditu | Verdikt | Důkaz (funkce / soubor) |
|---|---|---|---|
| 1 | `coaching_single_game` analyzuje jen jednu barvu | **potvrzeno** | `collect_single_game` volá `analyze_pgn` jednou; `_run_analyze_pgn` vyhodnocuje jen `board.turn == player_side` |
| 2 | `--color both` + username vrátí dvakrát stejnou barvu | **potvrzeno** | `scripts/coach.py:_single_game` předá `username`; `collect_single_game` jím přepíše `color` |
| 3 | `color="both"` v MCP není validováno | **potvrzeno** | `coaching_single_game` bez validace; `_run_analyze_pgn` bere „non-white = black“; `compact_serializer` normalizuje neznámou barvu na `white` |
| 4 | `detect_player_color` tiše vrací `white` | **potvrzeno** | `detect_player_color` má `return "white"` jako fallback |
| 5 | legacy vs fast cache se nepotkají | **potvrzeno** | `_policy_token`: `legacy` = prázdný suffix, `fast` = `n{nodes}`; `lichess_analyze_game` neposílá `mode` |
| 6 | context window neobsahuje tah soupeře | **potvrzeno** | plnění `context_window` iteruje `analysis.moves`, což jsou jen tahy hráče |
| 7 | LLM nedostane celou hru | **potvrzeno** | `build_response`: limit 10 chyb na typ, FEN `[:60]`, `bfs_json[:2000]`, žádné opponent ply |
| 8 | J má jiný predikát single vs cross-game | **potvrzeno** | `_detect_j` vylučuje `"K"` v SAN; `per_move_patterns` ne |
| 9 | T je strukturální, ne taktický motiv | **potvrzeno s korekcí** | `_detect_tactical_motif` = capture/check/promotion; T navíc `cp >= 50`. Audit vynechal loss threshold i vyloučení útěku z šachu |
| 10 | Eval POV je zavádějící | **věcně ano, citace ne** | `evaluate_move`: `eval_after` je negovaný relative score = stále POV hráče na tahu. Formulaci „side-to-move POV“ repo neobsahuje; `COMPACT_JSON_FOR_LLM.md` říká jen „eval swing in cp“ |
| 11 | Prompt žádá klasifikaci nad evidence | **potvrzeno** | `prompt_builder.py`, template 1: „KAŽDÝ blunder/mistake MUSÍ být klasifikován“ a „Time trouble? odhadni z time control“ |
| 12 | Chybí clock data contract | **potvrzeno** | prompt dostává jen `time_control`, žádná clock data |
| 13 | Chybí interaction model | **potvrzeno** | žádný `interaction` typ v modelech ani detektorech |

**Souhrn:** 12/13 potvrzeno, 1 věcně platný s nepřesnou citací. Audit není třeba znovu ověřovat; je třeba ho překlasifikovat.

---

## 2. Překlasifikace nálezů

Audit míchá tři kategorie do jedné prioritní tabulky. Kanonické rozdělení:

| Kategorie | Definice | Nálezy | Co s tím |
|---|---|---|---|
| **Defekt** | kód vrací jiný výstup, než deklaruje | #2, #3, #4, #8 | opravit hned, bez změny schématu (Tier 1) |
| **Produktová mezera** | kód dělá, co má, ale chybí schopnost | #1, #6, #7, #13 | návrh + nový artefakt (Tier 3) |
| **Sémantický dluh** | výstup je technicky správný, ale název/kontrakt klame | #9, #10, #11, #12 | aditivní pole + kontrakt (Tier 2) |

**Důsledek pro priority:** „P0“ smí být jen defekt, protože jen ten dnes produkuje špatná data. Produktová mezera je P1 produktové rozhodnutí, ne bug. Tím se pořadí prací mění: nejdřív čtyři malé opravy, pak kontrakty, pak timeline.

---

## 3. Korekce auditu

1. **„Schema 1.4 není schéma single-game“** — správně, ale není to vada. Je to záměrné rozdělení: cross-game statistika nemá v jedné hře co měřit. Audit to vzápětí sám říká; v tabulce to však vypadá jako nález. Kanonicky: 1.4 = cross-game, 1.2/2.1 = single-game, bez překryvu.
2. **„T označí libovolné braní / šach“** — nepřesné. T vyžaduje `cp >= 50` a vylučuje útěk z šachu. Pointa (forma tahu ≠ mechanismus) platí, popis ne.
3. **„schema 3.0“** — v navržené podobě by nahradilo existující kontrakty, což zakazuje D5. Kanonicky: nový artefakt `game_full` 1.0, staré verze beze změny.
4. **Eval POV** — citovaná formulace v repo není; riziko je reálné, ale je to **absence definice**, ne chybná definice. Oprava je doplnění, ne přepis.
5. **„P0: chybí dual perspective“** — překlasifikováno na produktovou mezeru (viz §2). P0 zůstávají jen #2, #3, #4, #8.

---

## 4. Co audit minul

| Nález | Kde | Dopad | Zařazení |
|---|---|---|---|
| `_resolve_color` u remíz vrací `white` | `anonymous_session.py` | anonymní session může analyzovat špatnou barvu | Tier 2 — hotovo (T2.5) |
| `max_time_dual: 1800` je mrtvá konfigurace | `config/depth.py`; nikdo ji nečte | dual analýza běží bez stropu | Tier 3.0 — hotovo (klíč smazán, strop nemá měřené opodstatnění) |
| `unanalyzed_plies` eviduje jen plies hráče | `_run_analyze_pgn` | „partial“ kontrakt pro timeline nejde naplnit | Tier 3.4 — hotovo v `game_full` (union obou stran); single-game payload zůstává jednoperspektivní |
| `T` má hardcoded `50`, ostatní prahy jsou `THRESHOLD_*` | `pattern_detector.per_move_patterns` | nekonzistence s konvencí | Tier 2 — hotovo (`THRESHOLD_TACTICAL_SHAPED_CP`) |
| žádný test `--color both` | `tests/test_coach_cli.py` | režim není pokrytý | Tier 1 — hotovo |

---

## 5. Rozhodnutí

### D6 — Barva je jedna z `white` / `black`, nikdy `both`

- **Pravidlo:** `color` přijímá `""` (auto-detect z username), `white`, `black`. `both` je **režim**, ne barva. Neznámá hodnota = explicitní chyba `INVALID_COLOR`, nikdy tichá konverze.
- **Důvod:** dnes `color="both"` skončí jako černá analýza s `color="both"` v detailed a `color="white"` v compact. To je kontradikce kontraktu, ne kosmetika.
- **Důsledek:** `coaching_single_game` validuje vstup; `compact_serializer` neznámou barvu odmítne; `--color both` v CLI zůstává, ale je to dvě volání s explicitní barvou.

### D7 — Single-game a timeline jsou dva artefakty, ne jedna verze

- **Pravidlo:** detailed 1.2 a compact 2.1 zůstávají **jednoperspektivní** a nemění se. Celopartiový výstup je nový artefakt `game_full` 1.0 (`timeline` + `perspectives.white` + `perspectives.black` + `interaction`).
- **Důvod:** D5 (aditivní kontrakty) a existence konzumentů. Nahrazení by rozbilo reporty i LLM prompty.
- **Důsledek:** `game_full` se validuje vlastním schématem; compact 2.1 se nikdy „nepovýší“ na 3.0.

### D8 — Dvě perspektivy nikdy nevstoupí do jednoho cohortu

- **Pravidlo:** cohort pro `detect_all` obsahuje nejvýš jednu položku na `game_id`. Perspektivy jsou **pohledy**, ne jednotky. `n_units` = počet her.
- **Důvod:** schema 1.4 a step C používají jednotku `game_id`; vložení obou pohledů by zdvojnásobilo `n_units`, `support` i split-half počty.
- **Důsledek:** `game_full` se do `detect_all` neposílá; případně guard, který duplicitní `game_id` odmítne.

### D9 — Každé eval pole nese POV ve jménu

- **Pravidlo:** cílové názvy `eval_before_mover_cp` a `eval_after_mover_cp`; timeline vždy publikuje `eval_before_white_cp` / `eval_after_white_cp`. Legacy `eval_before` / `eval_after` zůstávají jako aliasy jeden release.
- **Důvod:** `eval_after` je stále POV hráče, který táhl; čtenář to může zaměnit za POV soupeře a otočit znaménko.
- **Důsledek:** změna je aditivní; žádný konzument není nucen migrovat hned.

### D10 — LLM nesmí být nucen k závěru bez evidence

- **Pravidlo:** klasifikace chyby připouští třetí hodnotu `insufficient_evidence`. Time trouble jen z parsovaných clock dat; bez nich `clock_data_unavailable`, nikdy odhad z čísla tahu.
- **Důvod:** D4 (žádný vymyšlený mechanismus) platí i pro prompt. Současný prompt žádá klasifikaci, kterou data nepokrývají.
- **Důsledek:** prompt template 1 se mění; `time_control` zůstává kontext, ne důkaz.

### D11 — J má jeden predikát, T nesmí tvrdit motiv

- **Pravidlo:** J = blokování **figurou** pod šachem; královský ústup J nikdy nespustí. Predikát je společný pro single-game i cross-game. T se přejmenuje na `tactical_shaped_move_error`, nebo se povýší na skutečné motivy (fork/pin/skewer) — to je ale nový detektor a podléhá D4.
- **Důvod:** dva predikáty téhož ID = dva různé výstupy pro stejný tah. T dnes měří formu tahu, ne mechanismus.
- **Důsledek:** J oprava mění klasifikaci → bump `DETECTOR_VERSION` + fixture. T přejmenování je aditivní (label), dokud nevznikne skutečný detektor.

---

## 6. Nová roadmapa

Pořadí je závazné. Tier 1 nesmí být přeskočen, protože produkuje špatná data.

### Tier 1 — defekty (bez změny schématu, 1 iterace) — **HOTOVO 2026-11-13**

| ID | Úkol | Soubory | Acceptance | Stav |
|---|---|---|---|---|
| T1.1 | Validace `color`; `both` odmítnout s `INVALID_COLOR` (D6a) | `services/color_contract.py`, `tools/coaching_single_game.py`, `services/game_analyzer.py`, `services/compact_serializer.py` | `color="both"` vrátí `INVALID_COLOR`; nikdy tichá konverze; compact neznámou barvu neopravuje na `white` | ✅ |
| T1.2 | `--color both` + `--username` | `scripts/coach.py` | dva různé výstupy; test pro white, black i bez username | ✅ |
| T1.3 | `detect_player_color` explicitně selže | `services/coaching_base.py` | neznámý username = `COLOR_UNDETECTED`, ne `white` | ✅ |
| T1.4 | J: společný predikát | `services/pattern_detector.py` (`is_piece_block`) | královský ústup nespustí J v žádné cestě; bump `DETECTOR_VERSION` na `DBCL-20261113-dev` | ✅ |
| T1.5 | Testovací mezera | `tests/test_color_contract.py`, `tests/test_coach_cli.py`, `tests/test_pattern_unification.py` | 17 nových testů; žádný není vyloučen z CI | ✅ |

**Implementační poznámky (Tier 1):**

- `services/color_contract.py` je jediné místo, kde je definováno `white | black`; `both` je odmítnuto s vysvětlením, že jde o CLI režim.
- Explicitní barva je **fallback**, když detekce z username selže; pokud není ani jedna, volání selže s `COLOR_UNDETECTED` (žádné tiché `white`).
- `compact_serializer` už neopravuje neznámou barvu na `white`; neplatná barva je chyba kontraktu.
- `both` v CLI předává `username=""`, takže detekce nemůže přepsat požadovanou stranu. Cena: oba reporty jsou bez `username`; to je poctivější než dva reporty stejného hráče.
- `DETECTOR_VERSION` = `DBCL-20261113-dev` (změna klasifikace J). Cache z předchozí verze se nesmí míchat s novou klasifikací.

### Tier 2 — sémantika a evidence (aditivní pole, 1–2 iterace) — **HOTOVO 2026-11-14**

| ID | Úkol | Acceptance | Stav |
|---|---|---|---|
| T2.1 | Eval POV názvy (D9) | `eval_before_mover_cp` / `eval_after_mover_cp` v detailed i compact; staré aliasy jeden release; dokumentace definuje POV | ✅ |
| T2.2 | `moves_total` rozdělit | `player_moves_total`, `game_plies_total`, `opponent_moves_total`; starý klíč jeden release; legacy cache bez `game_plies_total` publikuje `null`, ne odhad | ✅ |
| T2.3 | Prompt: `insufficient_evidence`, clock contract (D10) | prompt připouští třetí klasifikaci; bez `%clk` je `clock_data_unavailable`, žádný odhad z time control | ✅ |
| T2.4 | T label (D11) | `pattern_name = tactical_shaped_move_error`; ID `T` zůstává; žádný nárokovaný motiv | ✅ |
| T2.5 | `_resolve_color` u remíz | remíza/neznámý výsledek bez explicitní barvy = `COLOR_UNDETECTED`, ne `white` | ✅ |

**Implementační poznámky (Tier 2):**

- `eval_before_mover_cp` / `eval_after_mover_cp` jsou kanonické v detailed `flagged_moves[]` i compact `flags[]`; `eval_before` / `eval_after` nesou stejné hodnoty jako deprecated aliasy (D9).
- `game_plies_total` se počítá při průchodu PGN (`_run_analyze_pgn`), takže starý `moves_total` už nikdy nemůže vypadat jako délka partie. Cache z doby před tímto polem publikuje `null`; číslo se nedopočítává.
- Prompt template 1 připouští `insufficient_evidence` a time trouble jen z `%clk`. `time_control` zůstává kontext, ne důkaz (D10).
- T nese lidsky nečitelný, ale stabilní label `tactical_shaped_move_error`; důvod je v `detail` (`motif=...`). Skutečné motivy (fork/pin/skewer) by byly nový detektor pod D4.
- `_resolve_color` odmítne remízu i neznámý label; anonymní batch vypíše chybu k dané hře místo analýzy náhodné barvy.

### Tier 3 — timeline a perspektivy (2–3 iterace)

| ID | Úkol | Acceptance | Stav |
|---|---|---|---|
| T3.0 | Sjednotit cache policy a run identity | `lichess_analyze_game` a coaching sdílí `mode`; `max_time_dual` buď zapojen, nebo odstraněn | ✅ `mode` parametr + sdílený policy token; `max_time_dual` smazán |
| T3.1 | `services/timeline.py`: merge dvou `GameAnalysis` | každý ply jednou; White POV eval; deterministické proti cache | ✅ |
| T3.2 | `game_full` 1.0 + validace | schéma odmítne chybějící `mover_color` nebo nekonzistentní POV | ✅ schéma + `validate_game_full` |
| T3.3 | `interaction` events | pouze kandidátní měření s `unclassified` fallbackem; žádné nové ID bez D4 gate | ⏸ čeká na measurement spec |
| T3.4 | Partial game contract | chybějící plies obou stran; `status="partial"` | ✅ `missing_plies` + `unanalyzed_plies` + `missing_colours` |

**Poznámka k ceně:** dual cache už dnes vyhodnocuje každý ply právě jednou (bílý běh bílé tahy, černý běh černé). Timeline je proto **merge vrstva**, ne nové engine volání. To je důvod, proč Tier 3 začíná merge a ne přepisem analyzátoru.

**Implementační poznámky (Tier 3):**

- `lichess_analyze_game` má nově `mode` (`fast`/`deep`, default `fast`) a používá stejný policy token jako coaching, takže oba nástroje čtou a zapisují stejné cache soubory. Staré `_d{depth}.json` záznamy zůstávají na disku, ale nový běh je nepoužije - jsou jiná engine policy.
- `max_time_dual` byl smazán, protože ho nikdo nečetl. Dual běh nemá umělý wall-clock strop; limity jsou stage budget (`BUDGETS`) a node ceiling (`NODE_CAPS`).
- `services/timeline.py` staví `game_full` 1.0 z jedné nebo dvou analýz. Chybějící pohled není chyba, ale `status="partial"` s pojmenovanou dírou; dva různé game id, dvě analýzy stejné barvy nebo ply mimo paritu jsou `TIMELINE_MISMATCH`.
- `game_full` je CLI + souborový artefakt (`--format game-full`), ne MCP tool: kontraktní plocha zůstává malá. `--format full` zůstává deprecated alias pro `detailed`.
- T3.3 se záměrně neimplementoval. "Interakce" nemá měřenou definici ani FP kalibraci; dodat ji bez toho by znamenalo nový pattern ID mimo D4 gate. Až bude spec, jde o nový detektor, ne o rozšíření timeline.

---

## 7. Co se NEMĚNÍ

| Kontrakt | Stav |
|---|---|
| Cross-game artefakt schema 1.4 (`n_games`, `rate`, Wilson CI, `lift`, `stability`) | beze změny |
| Compact 2.1 a detailed 1.2 | beze změny; pouze aditivní pole v Tier 2 |
| `game_full` 1.0 | nový artefakt, ne rozšíření 2.1/1.2; verze 1.0 je neměnná |
| D4 (žádné nové pattern ID bez taxonomie a FP kalibrace) | beze změny |
| D5 (aditivní kontrakty) | beze změny; `game_full` je nový artefakt |
| Admission gate `N >= 30`, `lift >= 1.4`, `>= 2` analýzy | beze změny |
| `DETECTOR_VERSION` | beze změny do T1.4 (J predikát) |
| Deterministická detekce, žádný LLM v runtime | beze změny |

---

## 8. Dopad na dokumenty

| Dokument | Nový status | Co platí |
|---|---|---|
| `PATTERN_DISCOVERY_METHODOLOGY.md` | v1.6, závazný pro discovery | doplněna hranice single/cross-game, §11.7, §12.2 |
| `REFACTOR_PLAN_2026-11-11.md` | historický pro Fázi 1+; Fáze 0 hotová | roadmapu single-game větve řídí tento dokument |
| `PLAN_SINGLE_GAME_CALIBRATION_2026-11-07.md` | implementováno, kontrakt 1.2 zmrazen | poznámky k `moves_total` a eval POV |
| `COMPACT_JSON_FOR_LLM.md` | závazný pro compact 2.1 | doplněna definice POV a jednoperspektivnosti |
| `CLI_USAGE.md` | závazný pro CLI | opraveny verze 2.1/1.2; `both` + `username` vyřešeno v T1.2 (username se v `both` nepředává); `--format game-full` (T3.2) |
| `GAME_FULL_1.0.md` | závazný pro `game_full` 1.0 | White POV, `mover_color`, partial kontrakt, co artefakt nedělá (T3.3) |
| `CANDIDATE_PATTERNS_2026-11-12.md` | závazný measurement appendix | §8.5 potvrzeno auditem; merge vrstva hotová (T3.1), plnění `context_window` je další krok |
| `CHESS_COACHING_PROMPT_TEMPLATES.md` | design reference | runtime prompt = `prompt_builder.py`; runtime text změněn v T2.3 (design doc jen odkazuje) |
| `REPORT_STAV_2026-11-11.md` | historický snapshot | nemá se aktualizovat; jen banner |
| `DEEP_DIVE_SINGLE_GAME_PATTERNS_2026-08-02.md` | historický | — |
| `AUDIT_REPORT_lichess-analyzer-mcp_v1/v2.md` | historické audity | — |

---

## 9. Testovací matice

Audit navrhuje 14 testů. Kanonická matice je níže; poslední tři audit neměl.

| Test | Očekávaný výsledek | Tier |
|---|---|---|
| PGN s 20 půltahy | White 10 rozhodnutí, Black 10 rozhodnutí | T3.1 — hotovo |
| Union White + Black plies | přesně všech 20 půltahů | T3.1 — hotovo |
| Intersection White a Black plies | prázdná množina | T3.1 — hotovo |
| `color=both`, username White | dva různé výstupy | T1 |
| `color=both`, username Black | dva různé výstupy | T1 |
| `color=both`, bez username | dva různé výstupy | T1 |
| Neznámý username + explicit Black | Black zůstává Black, nebo jasná chyba | T1 |
| Přímé MCP `color=both` | dva pohledy, nebo validní odmítnutí | T1 |
| Cache dual analysis → coaching | stejná policy / run identity, bez přepočtu | T3.0 — hotovo (`mode` + policy token) |
| LLM joint report | obsahuje tahy obou barev a reakce | T3 — neimplementováno (LLM není v runtime) |
| Pattern C | předchozí rozhodnutí téhož hráče, ne tah soupeře | T1 |
| Pattern J | královský ústup se nezamění za blokování figurou | T1 |
| Pattern S | král mohl sebrat šachující figuru a neudělal to | existuje |
| Evaluační timeline | jednotně White POV | T3.1/T3.2 — hotovo |
| **`n_units` se nezdvojnásobí** | dvě perspektivy = jedna jednotka | T3.1 — merge neduplikuje |
| **Merged timeline = zdrojové cache** | stejné eval hodnoty, deterministicky | T3.1 — hotovo |
| **`game_full` validace** | chybějící `mover_color` / nekonzistentní POV = error | T3.2 — hotovo |
| **Partial timeline** | chybějící barva/plies = `status="partial"` + pojmenovaná díra | T3.4 — hotovo |
| **Eval POV klíče** | `eval_before_mover_cp` = `eval_before`, oba mover POV | T2.1 |
| **`game_plies_total`** | 40 plies, 20 tahů hráče → 20 opponent; legacy cache = `null` | T2.2 |
| **Remíza bez barvy** | `COLOR_UNDETECTED`, nikdy `white` | T2.5 |
| **Prompt bez evidence** | obsahuje `insufficient_evidence` a `clock_data_unavailable` | T2.3 |
| **T label** | `tactical_shaped_move_error`, žádný motiv v názvu | T2.4 |

---

## 10. Pravidla proti driftu

1. **Jeden kanonický dokument na vrstvu:** discovery = metodologie; single-game kontrakt = calibration plan; audit rozhodnutí = tento dokument; CLI = `CLI_USAGE.md`. Ostatní dokumenty odkazují, nekopírují.
2. **Capability claim vyžaduje kód + test.** Dokud feature není v kódu a v testu, dokument ji označí `plánováno (Txx)`. Žádné „umí“, pokud neumí.
3. **Verze schémat jsou neměnné.** Nový artefakt = nová verze (`game_full` 1.0), nikdy přečíslování existující.
4. **Historické dokumenty dostanou banner.** Snapshot se nepřepisuje; jinak vzniká falešná aktuálnost.
5. **Roadmapa je na jednom místě pro jeden track.** Cross-game = metodologie §12; single-game = tento dokument §6. Ostatní dokumenty jen odkazují.
6. **Změna klasifikace = bump `DETECTOR_VERSION` + fixture.** Týká se T1.4 a každého nového detektoru.
7. **Změna plánu = nové rozhodnutí s ID.** Žádná tichá editace; historii rozhodnutí drží `změny_X` v dotčených dokumentech.

---

## 11. Rozhodnutí autora (2026-11-13)

| ID | Otázka | Rozhodnutí | Dopad |
|---|---|---|---|
| **D6a** | `color="both"` v MCP | **Odmítnout s `INVALID_COLOR`.** `both` zůstává jen v CLI jako dvě volání s explicitní barvou. Dva pohledy v jednom volání přijdou až s `game_full`. | T1.1 je odmítnutí, ne dual implementace; testovací matice „Přímé MCP `color=both`“ = validní odmítnutí |
| **D7a** | Název artefaktu | **`game_full` 1.0.** | T3.2 a všechny odkazy používají `game_full`; `game_timeline` se nepoužívá |
| **D10a** | Zdroj clock dat | **Jen PGN `%clk`.** Bez `%clk` je výstup `clock_data_unavailable`, nikdy odhad. | T2.3 nečte Lichess API clock pole; determinismus zůstává |

Tato rozhodnutí jsou závazná a nemění se bez nového ID (`D6b` atd.).

---

## Appendix — jak nálezy znovu ověřit

Bez závislosti na číslech řádků:

```powershell
# 1. jedna perspektiva
Select-String -Path src\lichess_analyzer_mcp\services\coaching_base.py -Pattern 'def collect_single_game|detect_player_color'
Select-String -Path src\lichess_analyzer_mcp\services\game_analyzer.py -Pattern 'player_side|board.turn == player_side'

# 2. barva v CLI
Select-String -Path scripts\coach.py -Pattern 'colors =|username=username'

# 3. validace a normalizace barvy
Select-String -Path src\lichess_analyzer_mcp\services\compact_serializer.py -Pattern '"color"'

# 4. cache policy
Select-String -Path src\lichess_analyzer_mcp\services\game_analyzer.py -Pattern 'def _policy_token|mode == "legacy"'

# 5. J predikát
Select-String -Path src\lichess_analyzer_mcp\services\pattern_detector.py -Pattern 'pattern_id="J"|"K" in m.move_san'

# 6. prompt
Select-String -Path src\lichess_analyzer_mcp\services\prompt_builder.py -Pattern 'MUSÍ být klasifikován|Time trouble'
```
