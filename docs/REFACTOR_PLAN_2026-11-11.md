# Audit handoffu v1.0 a plán iterativního refaktoru

- **Datum:** 2026-11-11
- **Auditovaný repozitář:** `outpost2026/lichess-mcp-analyzer`
- **Auditovaný HEAD:** `d6892c2` (kód identický s `7ce7f61`; dva navazující commity jsou pouze dokumentační)
- **Auditované vstupy:** `LICHESS_MCP_ANALYZER_DEVELOPMENT_HANDOFF_v1.0.md` a kritická reakce na něj
- **Rozsah:** ověření tvrzení proti kódu, schématům a reálným cache datům; návrh fázovaného refaktoru
- **Mimo rozsah:** implementace, volání placených LLM providerů, push

Metoda: každé tvrzení má podobu **claim → důkaz → verdikt → confidence**. Kde nebylo možné tvrzení ověřit, je to uvedeno explicitně. Číselné údaje pocházejí z repozitáře a z `data/game_cache`, ne z odhadů.

---

## 1. Executive verdict

Handoff v1.0 je strategicky správný: prioritizuje správnost a konzistenci před SQLite a GUI. Čtyři P0 nálezy jsou věcné. Kritika handoffu má věcně správné postřehy u FIX-029 a FIX-031, ale její diagnóza FIX-023 („sign flip“) je nepřesná.

**Souhrn:**

| # | Tvrzení | Verdikt | Confidence |
|---|---|---|---|
| 1 | P0.1 `king_capture_played` je odvozen z `x` v SAN | **Potvrzeno, Závažnější než handoff tvrdí** | P>0.95 |
| 2 | P0.2 `_detect_phase` je segmentace podle ply, ne fáze | **Potvrzeno** | P>0.95 |
| 3 | P0.3 `confidence` má více významů | **Potvrzeno, minimálně 4 významy** | P>0.95 |
| 4 | P0.4 `accuracy` je lokální heuristika, ne Lichess | **Potvrzeno** | P>0.95 |
| 5 | „FIX-023 done“ vs. data vykazující „sign flip“ | **Data mají pravdu, diagnóza ne** | P>0.90 |
| 6 | `test_engine_client.py` je vyloučen z počtu testů | **Potvrzeno; suite je navíc RED (1 failed)** | P>0.95 |
| 7 | FIX-029 quiet blunder není řešen | **Potvrzeno a kvantifikováno** | P>0.95 |
| 8 | FIX-031 `patterns_meta` chybí v compactu | **Potvrzeno** | P>0.95 |
| 9 | LLM providery jsou 404/402 | **Neověřeno v této session** | — |
| 10 | Handoffu chybí effort estimates, non-goals, LLM strategie | **Potvrzeno (obsahová absence)** | P>0.95 |

**Zásadní korekce:** FIX-023 není chyba znaménka. `cp_loss` a dvojice `eval_before`/`eval_after` pocházejí ze dvou různých výpočtů se dvěma různými baseline. Jakákoli „oprava znaménka“ by byla chybná. Skutečná vada je chybějící provenance a presentace derived hodnoty jako měření.

**Druhá zásadní korekce:** P0.1 není jen bug v `game_analyzer.py`. Stejný pattern `S` je implementován dvakrát: v `game_analyzer._per_blunder_patterns` **chybně** (SAN `x`) a v `pattern_detector._single_game_candidate` **správně** (kontrola typu figury). Dva výstupy téže pipeline si mohou odporovat.

---

## 2. Claim audit — handoff P0

### 2.1 P0.1 — `king_capture_played`

**Claim:** pole je odvozeno z přítomnosti `x` v SAN během šachu, což nedokazuje, že táhla figura byl král.

**Důkaz:**

- `src/lichess_analyzer_mcp/services/game_analyzer.py:887`
  ```python
  king_capture_played="x" in move_analysis.move_san and was_in_check,
  ```
- `src/lichess_analyzer_mcp/services/game_analyzer.py:391-394` — pattern S používá stejnou logiku:
  ```python
  king_capture_san = [s for s in legal.king_moves if "x" in s]
  king_capture_played = any("x" in move.move_san for s in legal.king_moves if "x" in s)
  ```
  Druhý výraz je navíc tautologický: `move.move_san` nezávisí na `s`, takže jde o `"x" in SAN and bool(king_capture_san)`.
- `src/lichess_analyzer_mcp/services/pattern_detector.py:621-646` — správná implementace přes `board.piece_at(played.from_square).piece_type == chess.KING`.

**Verdikt:** Potvrzeno. Dopad je dvojí:

1. **False negative pro pattern S:** jakékoli braní v šachu (např. `Qxd4`) potlačí detekci „hráč nebral králem“.
2. **Nekonzistence výstupů:** BFS `pattern_matches` (prompt, detailed) a top-level `patterns` (compact) používají různé implementace stejného patternu.

**Nový nález A1 (nad rámec handoffu):** `capture_checking_piece_possible` je také širší než název. Na řádku 885 se nastaví `True` při jakémkoli legálním braní, ne pouze při braní figura, která dává šach:
```python
capture_checking_piece_possible=any("x" in s for s in legal.captures),
```
Konzument to může číst jako „bylo možné sebrat šachující figuru“, což kód neověřuje.

**Doporučení:** centralizovat predikáty do jednoho modulu (`services/board_facts.py`), používat `chess.Board` a typy figur; `king_capture_played` definovat jako `played_piece == KING and board.is_capture(played) and was_in_check`. Přidat fixtures: `Qxd4` v šachu (must be false), `Kxd4` v šachu (must be true), braní mimo šach (must be false/None).

---

### 2.2 P0.2 — `_detect_phase`

**Claim:** `_detect_phase(ply)` je časová segmentace, nikoli fázová detekce.

**Důkaz:**

- `game_analyzer.py:340-345`:
  ```python
  if ply <= 20: return "opening"
  if ply <= 50: return "middlegame"
  return "endgame"
  ```
- `phase` se přiřazuje každému tahu (`move.phase`) a agreguje v `GameAnalysis._compute_phase_stats` (`models/game.py:150-167`).
- `pattern_detector.py:607-619` používá `move.phase == "endgame"` jako podmínku patternu R. Změna definice fáze tedy mění detekci, ne jen label.

**Verdikt:** Potvrzeno. Handoff správně odmítá tvrzení, že „ply 51 = endgame“ je fázová detekce. Je to segment. To ale neznamená, že segmentace je bezcenná: je stabilní, deterministická a pro mnoho reportů dostačující. Vada je v pojmenování a v tom, že payload nevydává, jak byla fáze určena.

**Doporučení:** additive change — zavést `segment` (`opening`/`middlegame`/`endgame` podle ply) a `chess_phase` (material-based) s explicitním `phase_method`. Do rozhodnutí (D1) publikovat obojí; staré `phase` do té doby aliasovat na segment. Material-based detector musí mít testy na pozice se 14 figurami (není endgame) a na skutečné koncovky.

---

### 2.3 P0.3 — `confidence`

**Claim:** stejný název nese různé významy.

**Důkaz — minimálně čtyři významy:**

| Význam | Kde | Vzorec |
|---|---|---|
| Síla rule matchu (per move) | `pattern_detector._single_game_candidate` | `min(cp / 500, 0.95)`, `0.4`, … |
| Frekvence napříč hrami | `pattern_detector` cross-game detektory | `min(affected / total * 0.8, 0.85)` |
| Kompozitní skóre patternu | `compressibility_validator._compute_final_confidence` | `0.5*compression + 0.3*entropy + 0.2*sample`; přepisuje `confidence` |
| Rozptyl cp_loss | `engine_client.evaluate_move_with_confidence` | `spread = max - min` (název `confidence_spread`) |

**Dopad:** `compact_serializer._severity` (řádky 68-79) mapuje `conf` na `critical/high/medium/low`. Prezentační závažnost patternu je tak odvozena z čísla, které může znamenat frekvenci výskytu, ne sílu důkazu. LLM agent nemá jak rozlišit, co `conf: 0.8` znamená.

**Verdikt:** Potvrzeno. Handoff tuto část podceňuje jako dokumentační; jde o kontraktní vadu s dopadem na klasifikaci.

**Doporučení:** zavést tři dimenze (`detection_strength`, `evidence_support`, `behavioral_confidence`) a `confidence` dočasně ponechat jako deprecated alias s explicitním `confidence_kind`. `sev` musí být odvozeno z cp_loss / klasifikace, ne z `conf`.

---

### 2.4 P0.4 — `accuracy`

**Claim:** `accuracy` je lokální heuristika, nikoli Lichess accuracy.

**Důkaz:**

- `models/game.py:143-148`:
  ```python
  total = sum(max(0, 100 - m.centipawn_loss * 0.15) for m in measured)
  return round(max(0, min(100, total / len(measured))), 1)
  ```
- Compact vystavuje totéž jako `summary.acc` (`compact_serializer.py:274`).
- Schéma 1.1 vyžaduje `analysis.accuracy` (`schemas/single_game_v1.1.json:103-117`).

**Verdikt:** Potvrzeno. Je to monotónní heuristika s lineární penalizací; s Lichess metodou (win-probability based) nesdílí nic než rozsah 0-100. Pojmenování `accuracy` vytváří riziko přímého srovnání.

**Doporučení:** zavést `accuracy_method` a `heuristic_score`; `accuracy` dočasně ponechat kvůli kompatibilitě, ale v reportu ji nikdy neprezentovat jako Lichess accuracy. Pokud má být Lichess-parity, implementovat přes win% a kalibrovat na veřejných datech; do té doby to neslibovat.

---

## 3. Claim audit — handoff P1 a kritika

### 3.1 P1.4 — nedosažitelný kód

**Důkaz:** `game_analyzer.py:321-325` — za `return False, None` následuje druhá větev `if is_capture`. Mrtvý kód.

**Verdikt:** Potvrzeno, P3, triviální oprava. Není blocker.

---

### 3.2 P1.5 — `test_engine_client.py` a 600 cp

**Důkaz:**

- Soubor má 28 testů; část je mockovaná, část volá reálný Stockfish (`TestEvaluateMoveRealEngine`, `TestEvaluateMoveLegalGuard`, `TestEvaluateMoveD2Fix`, `TestEvaluateMoveConfidence`, `TestIDGameQh4`).
- `tests/test_engine_client.py:179-193` připouští spread až **600 cp**; test `test_qh4_cp_loss_range` připouští **0-1200 cp** (řádek 255). Docstringy výslovně říkají „evaluate_move is nondeterministic between sessions“.
- `tests/test_engine_client.py:169-177` vyžaduje deterministický `best_move`, ale připouští jakékoli cp_loss.
- `.github/workflows/test.yml:51` spouští `pytest tests/ -v` **včetně** tohoto souboru.
- Lokální měření v `.ai_state.json` používá `--ignore=tests/test_engine_client.py`; proto „193/193“.

**Verdikt:** Potvrzeno s upřesněním: test není „skrytý z CI“, je skrytý z **reportovaného počtu 193**. CI ho spouští. To je horší: lokální a CI sada nejsou identické a zelené číslo lokálně nic neříká o engine vrstvě.

**Doplňkové zjištění — suite je RED:** plný běh v této session:

```
27 passed, 1 failed in 26.21s
FAILED tests/test_engine_client.py::TestIDGameQh4::test_analyze_position_qh4_rank1
AssertionError: Expected #1 move f2c2 at depth 14, got b1h7
```

Příčina není flakiness v klasickém smyslu. Stockfish 18 vrací:

- `analyze_position(fen, depth=14, multipv=1)` → `b1h7` (3/3 běhy)
- `analyze_position(fen, depth=14, multipv=3)` → první linie `f2c2`, druhá `b1h7` (2/2 běhy)

Test tedy testuje konkrétní tah, který závisí na `multipv` a na buildu enginu. Je to stale expectation, ne náhodný rozptyl. Zároveň je to přesně důkaz pro tvrzení handoffu, že „one thread + fixed depth“ není determinismus.

**Proč to nikdo nevidí:** CI pořadí kroků je ruff → mypy → pytest (`test.yml:44-51`). Mypy je RED, takže pytest krok se v CI vůbec nespustí. Lokálně je soubor vyloučen. Failing test je tedy maskován dvakrát.

Poznámka k předchozímu 900s timeoutu: šlo o artefakt invocation s pipingem (`| Select-Object`), ne o dobu běhu testů. Stejná sada s `Tee-Object` doběhla za 26 s. Problém s ukončením procesu (`REVIEW-EXIT-HANG`) tím není vyvrácen, ale není příčinou 900s timeoutu u testů samotných.

**Doporučení:** rozdělit testy markery `real_engine` / `fast`; v CI dva joby; pinnout build Stockfish a hash/threads; nahradit 600 cp toleranci testem klasifikační stability (blunder/mistake/inaccuracy bucket) plus dokumentovanou distribucí cp rozptylu. Teprve potom lze mluvit o determinismu.

---

### 3.3 Kritika: FIX-023 je „sign flip“

**Claim kritiky:** `eval_before=638`, `eval_after=682`, `cp_loss=237` dokazuje sign flip.

**Důkaz:**

- `engine_client.py:287-380`: `eval_before` je evaluace rodičovské pozice; `best_player` a `actual_player` pocházejí z **odděleného** searchu po zahrání tahu; `cp_loss = max(0, best_player - actual_player)` (řádek 371); `eval_after = actual_player` (řádek 377).
- `eval_consistency.py:1-32` to popisuje správně: „two separate searches can diverge: the eval can even rise while the move still lost cp relative to the best line.“
- Reprodukce `FVhqtv1S`, ply 89 (`Qe4+`, FEN `8/8/7P/5Q2/pp1k4/3P4/6PK/1r6 w - - 3 45`):
  - cached: `eval_before 638`, `eval_after 682`, `cp_loss 237`
  - fresh `evaluate_move(depth=14)`: `eval_before 638`, `eval_after 668`, `cp_loss 168`
- Prevalence v cache (224 souborů s aktuálním detektorem, non-mate pozice): **101/7231 měřených tahů (1,4 %)** porušuje invariant; u flagovaných tahů **101/2010 (5,0 %)**.

**Verdikt:** Pozorování je správné, diagnóza „sign flip“ je **nepřesná**. Nejde o převrácené znaménko; jde o:

1. **Rozdílné referenční body** — `cp_loss` je kotven k re-searchi nejlepšího tahu (`best_player - actual_player`), zatímco eval dvojice k evaluaci rodiče (`eval_before`) a sehrávky (`actual_player`). Invariant `eval_before - eval_after ≈ cp_loss` platí jen tehdy, když `eval_before ≈ best_player`. Právě rozdíl `eval_before` vs. `best_player` je search instability, ne chyba znaménka.
2. **Search variance** — separátní searchy na fixed depth se mohou rozejít; fresh vs. cached se liší o 69 cp při stejném depth (`237` vs `168`).
3. **Chybějící provenance** — cache klíč nese jen `d14n150000`, ne engine build, hash, threads ani verzi detektoru. Stará cache je proto nevysvětlitelná.

**Důsledek pro hodnocení FIX-023:** Implementace je **containment v compact výstupu** (vynechá eval pole při porušení invariantu) + log. Není to root fix. Detailed payload dál publikuje raw dvojici, která může být nenarativní. To je obhajitelné jako dočasné opatření, ale nesmí se to prezentovat jako vyřešený invariant.

---

### 3.4 Kritika: FIX-029 quiet blunder

**Claim kritiky:** blundery bez motivu a bez patternu nejsou ojedinělé.

**Důkaz — sken cache (224 souborů s `DBCL-20260727-dev`, všechny barvy):**

| Metrika | Hodnota |
|---|---|
| Blundery s cp_loss | 228 |
| `motif_type == null` | 223 (97,8 %) |
| `motif_type == null` **a** žádný BFS pattern | 100 (43,9 %) |
| z toho cp_loss < 2000 (vyloučeny matové artefakty) | **98 (43,0 %)** |
| medián cp_loss u těchto 98 | **384** |
| rozdělení podle segmentu | middlegame 66, endgame 24, opening 8 |
| cp pásma | 300-499: 77, 500-999: 21 |

Konkrétní reprodukce (všechny s `motif_type: null`, BFS `pattern_matches: []`):

| Hra | Barva | Ply | Tah | cp_loss |
|---|---|---|---|---|
| `NxK1MuwN` | white | 25 | Bf4 | 543 |
| `rgQlsl0s` | white | 21 | g3 | 699 |
| `fJeKgpJa` | white | 45 | Na6 | 419 |

**Mechanické vysvětlení (nový nález A2):** `_single_game_candidate` umí jen:

- B: braní (`x` v SAN) s cp ≥ 100,
- J: šach a netáhl-braní s cp ≥ 150,
- R: `phase == endgame` a eval_before > 300 a cp ≥ 300,
- S: v šachu a dostupné braní králem,
- C: předchozí tah blunder/mistake a cp ≥ 200,
- T: `is_tactical_motif` a cp ≥ 50.

Tichý poziční blunder bez braní, bez šachu, mimo endgame a bez taktického motivu **nemůže** projít žádnou větví. Nejde tedy o „chybějící pattern pro pár her“; je to strukturální slepá skvrna detektoru.

**Verdikt:** Potvrzeno a kvantifikováno. Kritika má pravdu, že to má být P0. Nemá ale pravdu v tom, že řešením je okamžitě přidat pattern. Pattern bez mechanismu by porušil princip „every reported pattern has traceable evidence“.

**Doporučení:** nejdřív explicitní stav `unclassified` s důvodem (`no_matching_detector`), teprve po taxonomii a kalibraci nový pattern (např. `Q3 — positional oversight`) s definovaným mechanismem a testy na false positives. To je i odpověď na otázku, zda FIX-029 je pattern: **není, dokud není mechanisms.**

---

### 3.5 Kritika: FIX-031 `patterns_meta` v compactu

**Důkaz:**

- Detailed 1.1 obsahuje `patterns_meta` jako **required** (`schemas/single_game_v1.1.json:24, 186-193`), plněný v `coaching_single_game.py:368-375`.
- Compact 2.0 má `additionalProperties: false` (`schemas/single_game_v2_compact.json:8`) a `patterns_meta` mezi properties **není**.
- Validator připouští top-level klíče `_REQUIRED_TOP | {"pv", "pv_unavailable", "clusters", "fen_before", "report", "llm"}` (`compact_serializer.py:381-383`) — `patterns_meta` tam chybí.
- Reprodukce `rgQlsl0s` white: detailed `patterns_meta.reason = "No flagged move met a single-game pattern threshold. Cross-game detectors need >=3 games and are suppressed."`, compact `patterns: []` bez vysvětlení.

**Verdikt:** Potvrzeno. Jde o malou, ale kontraktně viditelnou vadu: prázdné pole bez důvodu je přesně to, co plán `PLAN_SINGLE_GAME_CALIBRATION_2026-11-07.md` (K5) zakazoval.

**Doporučení:** compact 2.1 s volitelným `patterns_meta` (scope, suppressed, reason). Cena ~20-40 znaků; přínos pro LLM je vyšší než cena.

---

### 3.6 Kritika: LLM providery jsou 404/402

**Verdikt:** **Neověřeno.** V této session nebyl proveden žádný LLM call a nejsou k dispozici logy z aktuálního běhu. Tvrzení nelze použít jako fakt ani jako argument pro nebo proti handoffu. LLM strategie v plánu musí být navržena tak, aby fungovala i při výpadku všech providerů (deterministický fallback), a musí obsahovat health check.

---

### 3.7 Nové nálezy nad rámec obou dokumentů

| ID | Nález | Důkaz | Dopad |
|---|---|---|---|
| A1 | `capture_checking_piece_possible` je true při jakémkoli braní | `game_analyzer.py:885` | false positive v BFS; LLM může dostat nepravdivý fakt |
| A2 | Quiet blunder je strukturálně nedosažitelný pro všechny detektory | `pattern_detector.py:582-668` | 43 % blunderů bez patternu |
| A3 | `sev` v compactu je odvozeno z `conf` | `compact_serializer.py:68-79` | závažnost patternu závisí na významu confidence |
| A4 | Cache klíč neobsahuje engine build/hash/threads | názvy `*_d14n150000.json`; `ADAPTIVE_HASH_TABLE` | nereprodukovatelnost, slepé místo při srovnání běhů |
| A5 | Pattern S má dvě implementace s různou správností | `game_analyzer.py:391-394` vs `pattern_detector.py:621-646` | BFS a compact si mohou odporovat |
| A6 | `phase` je vstupem detektoru R | `pattern_detector.py:607-619` | změna fáze není kosmetická, mění detekci |
| A7 | Reálný engine test je RED a maskovaný mypy gate | `test_engine_client.py:363`; `test.yml:47-51` | CI nikdy nedojde k pytestu; „zelené“ číslo je neúplné |

---

## 4. Plán refaktoru

### Principy

1. **Zachovat funkční jádro.** Analýza tahů, engine wrapper a deterministické reporty fungují; refaktor je nesmí rozbít.
2. **Additive first.** Nové sémantické pole + deprecated alias; removal až ve velké verzi kontraktu.
3. **Žádná změna chování bez testu a verze.** Každá změna, která mění klasifikaci nebo pattern, musí mít fixture a bump `DETECTOR_VERSION`.
4. **Provenance před SQLite.** Nejdřív vědět, co které číslo znamená; teprve pak to ukládat do DB.
5. **Malé kroky s měřitelným acceptance criteria.** Žádný „big bang“ refaktor.

### Fáze 0 — Sémantika a správnost (odhad 7-9 pracovních dní)

| ID | Úkol | Soubory | Acceptance criteria |
|---|---|---|---|
| P0-1 | Centrální board facts: `king_capture_played`, `capture_checking_piece_possible`, typ táhnuté figury | nový `services/board_facts.py`; `game_analyzer.py`; `pattern_detector.py` | 3 FEN fixtures projdou; obě cesty (BFS i single-game) vrací stejný výsledek |
| P0-2 | Odstranit duplikaci pattern S a mrtvý kód | `game_analyzer.py:321-325, 348-420` | jediná implementace; test na `Qxd4` v šachu = S false, `Kxd4` = S true |
| P0-3 | `phase` vs `segment`: přidat `phase_method` a `chess_phase` (material-based), `phase` aliasovat | `models/game.py`, `game_analyzer.py`, `pattern_detector.py` | payload vždy nese `phase_method`; R detektor testován pro oba režimy |
| P0-4 | `confidence` dimenze: `detection_strength`, `evidence_support`, `behavioral_confidence`, `confidence_kind` | `models/pattern.py`, detektory, compact | každý pattern má vyplněnou dimenzi nebo explicitní `null` + důvod |
| P0-5 | `accuracy`: `accuracy_method`, `heuristic_score`; zákaz prezentace jako Lichess | `models/game.py`, `compact_serializer.py`, reporty | `accuracy_method="dbcl_heuristic_v1"` vždy; report neuvádí „Lichess accuracy“ |
| P0-6 | Eval provenance: `cp_loss_basis`, `eval_source`, `analysis_run_id`; compact už nepublikuje rozporné dvojice | `engine_client.py`, `eval_consistency.py`, `compact_serializer.py` | 0 publikovaných párů porušujících invariant; detailed má explicitní `eval_consistency: false` |
| P0-7 | `unclassified` blunder: `pattern_status`, `unclassified_reason` | `pattern_detector.py`, `coaching_single_game.py`, schemas | 100 % blunderů má buď pattern, nebo důvod |
| P0-8 | Compact 2.1: `patterns_meta`, `phase_method`, `unclassified` | `compact_serializer.py`, `schemas/single_game_v2_compact.json` | schema validace projde; prázdný pattern list má vždy důvod |
| P0-9 | Test split + pinned engine | `tests/`, `pyproject.toml`, `.github/workflows/test.yml` | fast job < 60 s bez engine; engine job s pinnutým buildem; žádný test není tiše vyloučen |

**Výstup fáze 0:** detailed 1.2, compact 2.1, `DETECTOR_VERSION` bump, migrační poznámka v CHANGELOG.

### Fáze 1 — Provenance a storage (odhad 3-4 týdny)

Cíl: každá analýza je reprodukovatelná a verzovaná. Nejdřív schéma, potom migrace.

Minimální tabulky (z handoffu, zúžené):

```
games(id, pgn_hash, ...)
analysis_runs(id, game_id, engine_version, engine_hash_mb, engine_threads,
              engine_nodes_cap, depth, detector_version, serializer_version,
              started_at, finished_at, status)
move_evaluations(run_id, ply, cp_loss, eval_before, eval_after,
                 cp_loss_basis, eval_source, classification, phase_method, ...)
pattern_definitions(id, version, mechanism, evidence_threshold, ...)
pattern_occurrences(run_id, ply, pattern_id, detection_strength,
                    evidence_support, behavioral_confidence, evidence_json)
```

Povinné provenance sloupce v `analysis_runs`: `engine_version`, `engine_hash_mb`, `engine_threads`, `engine_nodes_cap`, `detector_version`, `serializer_version`. Bez nich nelze odpovědět na „zlepšil jsem se, nebo se změnil engine?“.

Migrace: JSON cache zůstává read-only fallback; SQLite je nový zdroj pravdy. Dvojí zápis po dobu jednoho režimu, pak odstranit.

**Acceptance:** dvakrát spuštěný stejný PGN se stejným buildem a konfigurací dá stejný `run_fingerprint`; rozdílný hash/build je vidět v DB; GUI i CLI čtou stejný run.

### Fáze 1.5 — LLM strategie (odhad 3-5 dní design + 5-7 dní implementace)

- Provider chain s health checkem a explicitním fallbackem na deterministický report.
- Cost budget per hra: vstupy 3-6k tokenů, výstupy 0,7-1,2k; cena se doplní z aktuálního ceníku při implementaci, ne odhadem.
- Prompt templates verzované v `prompts/`, ne v kódu.
- Output contract: LLM nesmí zavést ply, tah ani pattern, který není v payloadu; validator to odmítne a použije deterministický report.
- Local fallback (Ollama/llama.cpp) jako volitelný, ne jako náhradu kvality.

**Acceptance:** při vypnutých všech providerech pipeline vrátí `status=degraded`, deterministický report a důvod; žádná LLM věta neobsahuje neověřený fakt.

### Fáze 2 — GUI read-only (odhad 3-4 týdny)

- Streamlit, ale veškerá logika v service vrstvě; GUI nesmí volat engine ani importovat analyzátor přímo.
- `st.cache_data` s explicitní invalidací podle `analysis_run_id`; žádná stale data.
- Testy: unit pro services, `streamlit.testing.v1.AppTest` pro kritické obrazovky.
- Deployment: lokální desktop první; remote až po auth a read-only garanci.

**Acceptance:** GUI umí jen čtení; každá obrazovka má test; po nové analýze se data obnoví bez restartu.

### Fáze 3 — Pattern lifecycle a kalibrace (odhad 2-3 týdny, pak ongoing)

- Stavy: `candidate → observed → supported → validated → intervention_tested`.
- Přechody mají číselná kritéria (počet occurrences, počet her, konzistence napříč engine buildy), ne jen slovníček.
- Quiet blunder: nejdřív taxonomie mechanismů (např. ignorovaná hrozba, otevřená diagonála, ztráta obrany), pak kandidátní pattern s testy na false positives.
- Kalibrace proti ground truth: ručně označený vzorek 50-100 tahů, měřit precision/recall, ne jen „pattern se objevil“.

**Acceptance:** každý `supported` pattern má doložené occurrence napříč ≥ 3 hrami a ≥ 2 runy; každý `validated` má lidsky ověřený vzorek.

---

## 5. Effort estimates

| Fáze | Odhad | Confidence | Podmínky |
|---|---|---|---|
| 0 — sémantika | 7-9 dní | Střední | bez změny SQLite; 1 vývojář; testy průběžně |
| 1 — provenance + SQLite | 3-4 týdny | Střední | migrace JSON cache, žádné GUI |
| 1.5 — LLM strategie | 8-12 dní | Střední | bez placených experimentů nad rámec budgetu |
| 2 — GUI read-only | 3-4 týdny | Nízká až střední | service vrstva hotová, testovací strategie schválená |
| 3 — lifecycle + kalibrace | 2-3 týdny + ongoing | Nízká | lidské značení vzorku je úzké hrdlo |

Celkem do použitelného GUI: cca 2-2,5 měsíce při jednom vývojáři a bez regresí. Odhady nezahrnují LLM cost a lidské ladění promptů.

---

## 6. Test strategy

1. **Dva joby:** `fast` (bez reálného engine, < 60 s) a `engine` (pinnutý build, markery `real_engine`).
2. **Pinned build:** `engine_version` z UCI `id name` + hash SHA; uložit do fixture a do `analysis_runs`.
3. **Mock vs real:** mockované UCI transkripty pro parsování a timeouty; reálný engine pro klasifikační stabilitu.
4. **Golden fixtures:** pevné FEN + tah + očekávaný bucket (`best/good/inaccuracy/mistake/blunder`) a prefix PV, ne přesné cp.
5. **Property testy:** `king_capture_played` implikuje král + braní; `phase` pokrývá všechny ply; `confidence` dimenze v [0,1]; publikovaná eval dvojice splňuje invariant.
6. **Kontraktní testy:** JSON Schema 1.2 a 2.1, oba formáty, včetně `patterns_meta` a `unclassified_reason`.
7. **SQLite testy:** migrace, round-trip provenance, stejný `run_fingerprint` při stejné konfiguraci.
8. **Zákaz tichých výjimek:** každý `--ignore` nebo `deselect` musí být v README s důvodem a odkazem na issue.

---

## 7. Explicit non-goals (do konce 2026)

- Mobilní aplikace, multiplayer, cloud sync, remote auth.
- Tvrzení o paritě s Lichess accuracy bez implementace a kalibrace.
- Nové pattern ID bez mechanismu a bez testů na false positives.
- Automatický refaktor `scripts/` (146 ruff nálezů) nad rámec nových skriptů.
- GUI zápisové operace (spouštění analýzy z GUI) — jen read-only.
- FSRS: rozhodnutí odloženo; SM-2 zůstává. Není to „deferred feature“, je to „rejected for now“ s revizí po Fázi 3.
- Optimalizace LLM nákladů nad rámec per-game budgetu.

---

## 8. Rozhodnutí vyžadující schválení autora

| ID | Otázka | Doporučení | Dopad |
|---|---|---|---|
| D1 | `phase` = segment, nebo chess phase? | Obojí: `segment` + `chess_phase` + `phase_method`; `phase` alias na segment | mění pattern R a všechny phase_stats |
| D2 | `confidence` kompatibilní alias, nebo nové dimenze? | Additive: 3 dimenze + `confidence_kind`; alias ponechat do 3.0 | kontrakt 1.2/2.1, LLM payload |
| D3 | `accuracy` rename? | `heuristic_score` + `accuracy_method`; `accuracy` ponechat jako deprecated | reporty, compact `acc` |
| D4 | Quiet blunder = nový pattern, nebo event? | Nejdřív `unclassified` event; pattern až po taxonomii | FIX-029, pattern schema |
| D5 | Compact schema bump? | 2.1 additive (`patterns_meta`, `phase_method`, `unclassified`) | serializer, validator, testy |
| D6 | Test policy: real engine v CI? | Ano, samostatný job s pinnutým buildem; fast job bez engine | CI čas, flakiness, důvěryhodnost |

Bez rozhodnutí D1-D6 nelze Fázi 0 dokončit; lze ale začít P0-1, P0-2 a P0-9, které jsou na těchto rozhodnutích nezávislé.

---

## 9. Acceptance criteria pro „refaktor hotový“

1. Žádný publikovaný eval pár neporušuje invariant; detailed má explicitní `eval_consistency`.
2. `king_capture_played` a `capture_checking_piece_possible` mají jedinou implementaci a fixtures.
3. Payload vždy říká, jak byla určena fáze, a jak byla vypočtena accuracy.
4. Každý pattern má tři dimenze nebo explicitní `null` s důvodem; `sev` není odvozeno z `conf`.
5. Každý blunder má pattern nebo `unclassified_reason`; prázdný pattern list má v compactu důvod.
6. `analysis_runs` obsahuje kompletní provenance a stejná konfigurace dá stejný fingerprint.
7. Fast test job < 60 s; engine job zelený s pinnutým buildem; žádný test není tiše vyloučen.
8. GUI je read-only a nevolá engine; cache invalidace je testovaná.
9. LLM výpadek vede na deterministický report s `status=degraded`, ne na prázdný nebo vymyšlený výstup.

---

## 10. Rizika a mitigace

| Riziko | Pravděpodobnost | Mitigace |
|---|---|---|
| Schema churn rozbije staré cache | Vysoká | additive pole, read-only fallback, `serializer_version` |
| Material-based phase změní pattern R | Střední | dual-run a srovnání na 20 hrách před zapnutím |
| SQLite duplikuje JSON jako zdroj pravdy | Vysoká | explicitní `source_of_truth` v konfiguraci, migrační testy |
| Streamlit cache zobrazuje stale data | Střední | invalidace podle `analysis_run_id`, test |
| Odhady jsou podceněné | Střední | fázové branky, žádný big bang |
| LLM vrací neověřené tahy | Střední | output validator + deterministický fallback |
| Engine testy zůstanou flaky | Vysoká | pinned build, klasifikační stabilita místo cp, samostatný job |

---

## Appendix A — Reprodukce

```powershell
cd C:\Users\PC\Documents\Repozitar_Dev\_github\lichess-analyzer-mcp
$env:PYTHONIOENCODING='utf-8'

# FIX-023: cached vs fresh
.\.venv\Scripts\python.exe -X utf8 <temp>\eval89.py

# FIX-029: scan cache
.\.venv\Scripts\python.exe -X utf8 <temp>\quiet_blunder_scan2.py

# FIX-031: detailed vs compact
.\.venv\Scripts\python.exe -X utf8 scripts\coach.py --game-id rgQlsl0s --color white --format detailed --no-llm --quiet
.\.venv\Scripts\python.exe -X utf8 scripts\coach.py --game-id rgQlsl0s --color white --format compact --no-llm --quiet

# test scope
.\.venv\Scripts\python.exe -X utf8 -m pytest tests -q --ignore=tests/test_engine_client.py
.\.venv\Scripts\python.exe -X utf8 -m pytest tests\test_engine_client.py -v
```

## Appendix B — Měřená data

| Metrika | Hodnota | Zdroj |
|---|---|---|
| Cache souborů s aktuálním detektorem | 224 | `data/game_cache` |
| Měřené non-mate tahy s evaly | 7231 | sken cache |
| Porušení eval invariantu | 101 (1,4 %) | `eval_invariant_holds` |
| Flagované tahy celkem | 2010 | sken cache |
| Porušení invariantu u flagovaných | 101 (5,0 %) | sken cache |
| Blundery celkem | 228 | sken cache |
| Blundery bez motivu a bez patternu (cp < 2000) | 98 (43,0 %) | sken cache |
| Medián cp_loss u quiet blunderů | 384 | sken cache |
| Testů v `test_engine_client.py` | 28 | pytest collect |
| Běh `test_engine_client.py` | 27 passed, 1 failed, 26,21 s | tato session |
| Failing test | `TestIDGameQh4::test_analyze_position_qh4_rank1` (`b1h7` vs `f2c2`) | tato session |
| Engine build | `Stockfish 18` | UCI `id name` |
| `multipv=1` na Qh4 FEN | `b1h7` (3/3) | tato session |
| `multipv=3` na Qh4 FEN | `f2c2` první linie (2/2) | tato session |
| Fast suite bez engine | 193 passed, 7,24 s | `.ai_state.json` |
| `FVhqtv1S` ply 89 cached | cp 237, eval 638/682 | cache |
| `FVhqtv1S` ply 89 fresh d14 | cp 168, eval 638/668 | `evaluate_move` |
