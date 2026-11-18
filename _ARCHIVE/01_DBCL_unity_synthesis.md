# DBCL — Unity Synthesis Document

**Verze:** 1.0 (syntéza 3 artefaktů)
**Datum:** 2026-07-25
**Účel:** Datový a kontextuální injekt pro další debug session MCP. Sjednocuje (a) autorův návrh DBCL, (b) externí cross-audit (Claude), (c) evening coaching záznam s odhalenými halucinacemi. Slouží jako čitelný vstup pro **autora** i **LLM**, který bude do session přizván — každé tvrzení je dohledatelné ke zdroji `[SRC-1|2|3]`, každá halucinace má vyznačený důkaz, každá opora doporučení má `Finding ID` z auditu.

> **Konvence čtení:** Pokud jsi autor — čti sekce 1, 4, 6, 8, 9. Pokud jsi LLM, který se účastní další iterace debugu — čti sekce 2, 3, 5, 6, 7, 9, 10. Oba čtěte sekci `## 0. Source Provenance`, abyste věděli, odkud co pochází.

---

## 0. Source Provenance

| ID | Zdroj | Typ | Datum | Role v syntéze |
|----|-------|-----|-------|----------------|
| **SRC-1** | `DBCL_cross_audit_artifact.md` | Autorův návrh | 2026-07-24 | Diagnóza, principy P1–P6, BlunderFactSheet v1.0, audit protocol |
| **SRC-2** | `DBCL_Cross_Audit_Report.docx` | Externí audit (Claude) | 2026-07-24 | 21 findings F-001–F-021, kritická cesta, priorita oprav |
| **SRC-3** | `evening_coaching_2026-07-24.md` | Debug session výstup | 2026-07-24 19:20Z | Konkrétní halucinace (kNAMNYUF ply 63), nový pattern S, Stockfish ground truth |

**Syntéza NENÍ 4. hlasem.** Nepřidává nové architektonické závěry, pouze sjednocuje a zpřesňuje to, co již tři artify říkají. Pokud se v textu objeví věta, která není v `[SRC-1|2|3]`, je to buď explicitně označeno `[SYNTHESIS]` (jde o logický důsledek), nebo je to chyba — v takovém případě je to třeba opravit.

---

## 1. Rámec problému (z SRC-1 §1, potvrzeno SRC-2 F-001)

### 1.1 Co selhává

MCP server generující chess coaching narrative halucinuje, protože **LLM dostává agregované statistiky a je nucen dělat detekci i naraci najednou**. Konkrétně v `services/llm_client.py:build_coaching_prompt()` a `services/game_llm_cache.py:_build_game_prompt()` (SRC-2 F-008: existují **dvě** taková místa, DBCL pokrývá jedno) se předávají jen:
- `total_acpl`, `blunders[]`, `patterns[]`, `phase_stats`, `weakness_report`, `leaky_openings`
- **Chybí:** FEN před/po tahu, `board.is_check()`, legální tahy, žebříček enginu, pattern match per-blunder.

### 1.2 Důsledek

LLM odvozuje board-state fakty heuristikou (proximita figur ≈ šach) místo výpočtem (geometrie útoku). Toto je **typ halucinace, kterou P1 explicitně zakazuje**.

### 1.3 Co NENÍ problémem (naopak)

Data existují. V `services/game_analyzer.py:_run_analyze_pgn()` se při každém tahu počítá `fen_before = board.fen()` a `board` (python-chess) je k dispozici, ale:
- `fen_before` se **nepředává** do `MoveAnalysis` (dataclass `models/game.py` to pole nemá) — **SRC-2 F-002**.
- `board.is_check()` se **v celém `src/` nevolá ani jednou** (grep audit) — **SRC-2 F-003**.

To znamená: většina "nové" funkcionality z DBCL §5.2 je **zapojení existujícího výpočtu, ne jeho stavba**. (SRC-2 F-005, F-009 potvrzují: `analyze_position(multipv=3)` a `SRSCard.fen` pole existují, jen je nikdo nevolá v rámci blunder pipeline.)

---

## 2. Rekonstrukce incidentů (z SRC-3, ověřeno Stockfish analýzou)

Tyto tři incidenty jsou **injection-ready data**: každý má FEN, eval, legal moves, pattern match, halucinovaný výstup. Slouží jako test cases pro novou verzi pipeline.

### 2.1 INC-A: kNAMNYUF ply 63 (Rdg1) — `[INC-A]`

**Kanonický incident z DBCL §3. Nejvíce analyzovaný ze všech tří.**

```
FEN before:  r4r1k/1p1b3P/p3p1R1/3p3Q/3N1q2/8/PPP4P/1K1R4 w - - 1 32
Move played: Rdg1
Eval before: +823 cp
Eval after:  +45 cp
Loss:        950 cp (778 cp dle SRC-3 — rozdíl 172cp vychází z rounding/multi-PV, viz [VERIFY-1])
Phase:       endgame
Was in check: FALSE           ← výpočet z FEN, ne domněnka
```

**Legal moves (38):** top 3 dle SRC-1 §3.1: `Nxe6` (+920), `Rg8+` (+901), `Qe5+` (+887). `Rdg1` je rank 38/38 (nejhorší legální).

**Halucinovaný výstup (SRC-1 §3.2):**
> „Qf4+ dává šach. Místo ústupu králem (Ka1 nebo Kc1) jsi instinktivně zablokoval věží — Rdg1."

**Fakta o halucinaci (vše 100% jistota z FEN + legal_moves):**
1. `Qf4+` **nebyl šach** — Q na f4, K na b1, delta +3 řady +4 sloupce. Společná diagonála? Ne. Společná řada/sloupec? Ne. Topologicky nelze.
2. `Rdg1` **nic neblokuje** — Rd1→g1 nemění žádnou linii ani diagonálu ke králi. Šach neexistuje → blok neexistuje.
3. `Ka1` a `Kc1` nejsou relevantní — král nebyl v šachu, žádná evaze nutná. `Ka1` je legální (není třeba). `Kc1` **není legální** (král by musel projít kolem věže na d1, to square kontroluje).

**Pattern match (dle SRC-1 §3.4 + SRC-2 F-007):**
- `R` (endgame relaxation): eval_before > 300 + phase=endgame → confidence 0.7 ✅
- `C` (attention tunneling): consecutive errors v okně → confidence 0.8 ✅
- `J` (impulsive check block): **POZOR — viz SRC-2 F-007.** Detektor v `services/pattern_detector.py:_detect_j()` testuje `if "+" in m.move_san`, tedy jestli **odehraný tah dal šach**, ne jestli **hráč byl v šachu**. V tomto případě `Rdg1` nedává šach, takže `_detect_j()` neaktivuje J. Pokud by však LLM dostal J pattern s hypotézou „impulsive block" na této pozici, **guard-clause DBCL ochrání proti vymyšleným faktům, ale ne proti věrné narraci špatně vypočítaného faktu** (SRC-2 F-007 reasoning).

**Co se mělo odehrát:** v SRC-3 je v tomto incidentě pattern `B+J` (automatické brání + impulsivní blok). Beru SRC-3 variantu, protože k incidentu má přístup ke Stockfish top 3 včetně `Nxe6` (capture); `J` zde znamená „pokus o blok dámy věží, ačkoli král nebyl v šachu — což je sémanticky `B` (automatické brání) v kontextu, kdy brát nebylo třeba). **[VERIFY-1] Rozdíl v CP loss 950 vs 778 je třeba ověřit proti aktuálnímu Stockfish výstupu.**

### 2.2 INC-B: qmodxzNF ply 60 (Kd7) — `[INC-B]`

**Incident, který zrodil nový pattern S. V SRC-1 není (autoři DBCL neviděli SRC-3), ale v SRC-3 je plně rekonstruovaný Stockfishem.**

```
FEN before:  7r/2p2p2/3k4/p1QPp3/1pP1P2q/5P2/P1B2P2/2K3R1 b - - 3 30
Move played: Kd7
Loss:        1386 cp (SRC-3 uvádí 1423, rozdíl viz [VERIFY-2])
Phase:       endgame
Was in check: TRUE (Dáma na c5 dává šach králi na d6)
Legal king moves: Kc5, Kd7
Legal king capture: Kxc5 (capture_checking_piece_possible=true,
                       king_capture_possible=true,
                       king_capture_played=false)
```

**Top move:** `Kxc5` (+542 cp). Odehraný tah `Kd7` (−573 cp). Ztráta: **1386 cp** (dle SRC-3), **1423 cp** (dle rozdílu v SRC-3 — původní text uvádí 1 142, ale to je součet; ověřit).

**Halucinace:** V SRC-3 nebylo řečeno, že by k tomuto incidentu LLM halucinoval výstup — záznam vznikl jako „manuální inspekce" autora po Stockfish verifikaci. Tento incident je tedy **čistý detection, ne narration incident** — slouží jako benchmark pro pattern S, ne pro halucinaci.

**Pattern match:**
- `S` (capture aversion under check) — confidence ~40% (N=2, 1 miss; penalizace za N=2). Stockfish verifikace 100%, závažnost kritická.
- `R` (endgame relaxation) — confidence 70% (eval_before > 300 + endgame)
- `P` (visual misrecognition) — confidence 50% (částečný průnik; hráč neviděl, že d6-c5 je nekrytý)

**Třífázová mitigace (SRC-3 §4):** „Když jsi v šachu, zastav se a zeptej se: **MŮŽU BRÁT šachující figuru?** Teprve pokud ne, řeš ústup nebo blok."

### 2.3 INC-C: xUlQasD0 (multi-blunder) — `[INC-C]`

**4 bludery v jedné hře. Demonstrace, že pattern library vyžaduje revizi, nejen DBCL.**

| Tah | Move | CP před | CP po | Ztráta | Pattern (SRC-3) |
|-----|------|---------|-------|--------|-----------------|
| 40 | f5? | +681 | +336 | 369 | C (tunnel) |
| 41 | fxe6 | +336 | (pokračuje) | (řetěz) | B (auto grab) |
| 43 | Sf4 | +335 | −110 | 505 | P (visual) + B |
| 71 | Df5 | +208 | −115 | 338 | P (visual) |
| 89 | Vd7+ | −788 | −1248 | 464 | J (block) |

**Halucinace v SRC-3:** žádná explicitní halucinace, ale **souvislost s F-007**: pattern `J` zde **byl aktivován** (dle SRC-3 „J | Freq 1 | Conf 33% | Severity high" — citováno z PIPELINE_TEST_REPORT_2026-07-24 v SRC-2 F-007). To znamená, že detektor `_detect_j()` v produkci skutečně **špatně detekoval** — `Vd7+` dává šach (`+` v SAN), takže `if "+" in m.move_san` projde, ale **jde o útok z prohrané pozice, ne o reakci na šach** (král před tahem 89 nebyl v šachu). Tudíž: pattern J v datech je v tomto případě **falešně pozitivní**, což je přesně ten typ chyby, kterou DBCL guard-clause nechytá.

### 2.4 Společné rysy incidentů

- Všechny 3 incidenty v koncovce (8/10 blunderů v SRC-3 je v koncovce).
- Dva z nich (INC-A, INC-B) jsou s vysokým eval_before — pattern `R` je silně přítomen.
- Jeden z nich (INC-C 89) je z prohrané pozice a je falešně pozitivní pattern J.
- **Žádný incident nemá halucinovaný výstup v commitnutém souboru** (SRC-2 F-012 — `COACHING_REPORT` neobsahuje kNAMNYUF grep, halucinace pravděpodobně vznikla v interaktivní relaci mimo repozitář).

---

## 3. Halucinace — mapovaná typologie

Tato sekce je **LLM injection-ready**: definuje typy halucinací, které se v debug session mohou znovu objevit, s ověřením proti FEN/board_state.

| ID | Typ halucinace | Příklad | Detekce z | Ochrana v DBCL |
|----|---------------|---------|-----------|----------------|
| `H1` | **Falešný šach** | „Qf4+ dává šach" (INC-A) | `board_state.was_in_check` musí být `true` | Guard: `if was_in_check=false, DO NOT say check` |
| `H2` | **Falešný blok** | „Rdg1 blokuje šach" (INC-A) | `legal_moves.blocks` musí obsahovat hraný tah | Guard: `if move ∉ legal_moves.blocks, DO NOT say block` |
| `H3` | **Falešná legální evaze** | „místo Ka1 nebo Kc1" (INC-A) | `legal_moves.king_moves` musí obsahovat oba | Guard: `if move ∉ legal_moves.king_moves, DO NOT list as option` |
| `H4` | **Falešná capture možnost** | „mohl jsi vzít" když capture_checking_piece_possible=false | `legal_moves.captures` | Guard: `if capture_checking_piece_possible=false, DO NOT say capture possible` |
| `H5` | **Falešně pozitivní pattern** | Pattern J aktivovaný na „Vd7+" (INC-C) | Pattern match v `pattern_matches[]` musí korespondovat se `board_state.was_in_check` | **NEŘEŠENO v DBCL — viz SRC-2 F-007** |
| `H6` | **Vymyšlená variace** | „Kdybys zahrál X, pak Y, pak Z..." ne v engine_lines | `engine_lines[].pv` | Guard: `engine lines are SOLE source for "what should have been played"` |
| `H7` | **Falešný eval** | „pozice byla +800, pak −200" neodpovídá `eval_before/eval_after` | `eval_before`, `eval_after`, `win_prob_before`, `win_prob_after` | Guard: `if eval number is mentioned, it must match one of these` |
| `H8` | **Přenos halucinace z per-game do aggregate** | Per-game LLM call halucinoval, jeho JSON output prošel parsováním, agregátní LLM to cituje jako fakt | Kontrakt mezi `_build_game_prompt` a `build_coaching_prompt` | **NEŘEŠENO v DBCL — viz SRC-2 F-008** |

**Poznámka pro LLM v další iteraci:** Pokud generuješ naraci, procházej tyto typy jednu po druhé (`H1` až `H8`) a ověř, že žádný typ není aktivní v tvém draftu. Pokud nevíš, zda je `was_in_check` true/false, **nepiš o šachu vůbec** — `null` znamená `ticho`, ne `domněnka`.

---

## 4. Architektonická mapa — co existuje, co chybí, co se plánuje

Tato sekce sjednocuje SRC-1 §2 (autorova mapa) a SRC-2 F-001…F-015 (audit zjištění) do jedné tabulky.

| Komponenta | DBCL § | Existuje v repo? | Stav | Finding |
|------------|--------|------------------|------|---------|
| `fetch_recent_games` (Lichess API) | §2.2 | ✅ | produkce | — |
| Stockfish 18 BMI2 @ d14 | §2.2 | ✅ | produkce | — |
| `game_cache.json` per-ply eval | §2.2 | ✅ | produkce, **ale chybí `fen` pole** | F-002 |
| `pgn_cache/` | §2.2 | ✅ | produkce | — |
| `pattern_detector.py` (11 patterns A–R) | §2.2 | ✅ | **produkce, ale pattern J má sémantický bug** | F-007 |
| `match_patterns` tool (across games) | §2.2 | ✅ | produkce | — |
| `analyze_position` tool (MCP, single-position Stockfish) | §2.2 | ✅ | **produkce, ale nikdo nevolá v blunder pipeline** | F-005 |
| `engine_client.analyze_position(multipv=3)` | §5.2.3 | ✅ | **produkce, ale blunder pipeline volá jen single-PV** | F-005 |
| `SRSCard.fen` pole | §5.2.3 | ✅ | **schéma existuje, ale producent karty neexistuje** | F-009 |
| `build_coaching_prompt` (mono režim) | §5.2.4 | ✅ | **produkce, bez guard-clause, bez fact sheet** | F-001, F-008 |
| `_build_game_prompt` (per-game režim) | (chybí) | ✅ | **produkce, samostatný, bez guard-clause** | F-008 |
| `eval_delta_threshold.py` (nový) | §5.2.1 | ❌ | k implementaci | — |
| `context_extractor.py` (nový) | §5.2.2 | ❌ | **ale lze inlinovat do `_run_analyze_pgn`** | F-004 |
| `BlunderFactSheet[]` | §5.2.3 | ❌ | k implementaci, **ale v1.1 rozšířená o win_prob + detector_version** | F-010, F-007 |
| LLM prompt s guard-clause | §5.2.4 | ❌ | k implementaci, **aplikovat na OBA prompt build sites** | F-008 |
| `validator.py` (nový, narrative claim-grounder) | §5.2.5 | ❌ (kolize s existujícím `validator.py`) | k implementaci pod jiným jménem | F-011 |
| Cache integrace s `{game_id}_{color}_d{depth}.json` | (chybí) | ❌ | k integraci | F-014 |
| Engine lock timeout (120s) | (chybí) | ✅ | v `engine_client._acquire_analysis_lock` | F-015 |

**Závěr:** přibližně polovina DBCL „nové" práce je **zapojení existujícího kódu** (F-005, F-009, F-015). To by mělo posunout odhad náročnosti P1 fáze dolů, ale **P0 fáze by měla zůstat**, protože F-007 a F-013 jsou typy chyb, které se neprojeví bez reálných testů.

---

## 5. Revize Pattern Library A–R (SRC-2 F-007 extended)

**Toto je nejdůležitější sekce pro LLM v další iteraci.** SRC-2 F-007 nenašel chybu jen v pattern J — audit varuje, že **bez revize všech 11 detektorů** hrozí, že DBCL guard-clause bude fungovat, ale LLM bude věrně narrativizovat špatně vypočítaná fakta z chybných detektorů.

### 5.1 Inventář patternů a jejich testované podmínky (dle SRC-3 §3)

| ID | Pattern name (SRC-3) | Mechanismus deklarovaný | Testovaná podmínka (dle SRC-3) | Verdikt |
|----|---------------------|-------------------------|--------------------------------|---------|
| A | (nepopsán v SRC-3) | — | — | **[NEVERIFIKOVÁNO]** |
| B | Automatické brání | „bereš co je nabízeno" | capture blunder (cp_loss + capture) | ✅ Sémanticky správné |
| C | Tunnel vision | „přestaneš skenovat celou šachovnici" | consecutive errors | ⚠️ Sémanticky OK, ale `consecutive errors` threshold není specifikován — kolik chyb v řadě? |
| D–Q | (chybí v SRC-3, ale v A-Q1 knihovně) | — | — | **[NEVERIFIKOVÁNO — vyžaduje audit services/pattern_detector.py řádek po řádku]** |
| J | Impulsivní blok šachu | „blokovat bez vyhodnocení" | `if "+" in m.move_san` | ❌ **SÉMANTICKÝ BUG** (SRC-2 F-007) |
| O | Vyhýbání se trojáku | „odmítnutí trojnásobného opakování" | ? | **[NEVERIFIKOVÁNO]** |
| P | Vizuální chyba | „halucinace o jeden tah hluboká" | ? | **[NEVERIFIKOVÁNO]** |
| R | Relaxace v koncovce | „výhoda tě ukolébá" | eval_before > 300 + phase=endgame | ✅ Sémanticky správné |
| S | Capture aversion under check | „král může brát, ale nebere" | in_check + king_capture_possible + not_played | ✅ Sémanticky správné (ale **NENÍ dosud v produkci**, SRC-3 navrhuje jako nový) |
| I | Návnada | „silná stránka" | — | **[NEVERIFIKOVÁNO — ale SRC-3 říká „pokračovat"]** |

### 5.2 Audit protocol pro detektory

Pro každý pattern `X` je nutné ověřit:

1. **Pattern name (slovní popis v `models/pattern.py`)** — co tvrdí, že detekuje.
2. **Detection method (v `services/pattern_detector.py:_detect_X`)** — co reálně testuje.
3. **Match**: pokud detection method testuje **odlišnou board-state proměnnou**, než pattern name tvrdí → **SEMANTIC BUG**, podobný F-007.
4. **Production evidence**: poslední PIPELINE_TEST_REPORT, kolikrát a na jakých datech pattern aktivoval.

**Toto musí být hotové PŘED implementací DBCL v1** (SRC-2 doporučení). Doporučený postup: otevři `services/pattern_detector.py` a projdi _detect_A až _detect_S řádek po řádku, současně s `models/pattern.py`. Tento audit **nelze delegovat na LLM bez dozoru** — je to přesně ten typ úlohy, kde autorova kontrola CoT je nezbytná.

### 5.3 LLM guard pro pattern výstup (navrhuji `[SYNTHESIS]`)

```
=== GUARD: pattern_matches ===
For each pattern in pattern_matches:
  IF pattern_id == "J":
    ASSERT pattern's evidence references board_state.was_in_check=true
    ELSE REJECT pattern J as unsupported on this blunder
  IF pattern_id == "S":
    ASSERT board_state.king_capture_possible=true AND
           board_state.king_capture_played=false
    ELSE REJECT pattern S as unsupported
  IF pattern_id == "R":
    ASSERT eval_before > 300 AND phase="endgame"
    ELSE REJECT pattern R as unsupported
  IF pattern_id == "C":
    ASSERT consecutive errors in context_window ≥ THRESHOLD (TBD)
    ELSE REJECT pattern C as unsupported
```

Toto je `[SYNTHESIS]` — není v SRC-1 ani SRC-2. Doporučuji přidat do DBCL v1.1 jako explicitní pattern guard, protože řeší F-007 typ chyby strukturálně.

---

## 6. BlunderFactSheet v1.1 (sjednocení SRC-1 §5.2.3 a SRC-2 F-010, F-013)

```json
{
  "$schema": "DBCL v1.1",
  "game_id": "string",
  "ply": "integer",
  "move_played_san": "string",
  "move_played_uci": "string",
  "centipawn_loss": "float",
  "eval_before": "float | null",
  "eval_after": "float | null",
  "win_prob_before": "float | null",
  "win_prob_after": "float | null",
  "win_prob_delta": "float | null",
  "fen_before": "string (FEN)",
  "board_state": {
    "was_in_check": "boolean",
    "checking_pieces": ["square", "..."],
    "capture_checking_piece_possible": "boolean",
    "king_capture_possible": "boolean",
    "king_capture_played": "boolean | null"
  },
  "legal_moves": {
    "total": "integer",
    "captures": ["SAN", "..."],
    "king_moves": ["SAN", "..."],
    "blocks": ["SAN", "..."],
    "checks": ["SAN", "..."]
  },
  "engine_lines": [
    {
      "rank": "integer",
      "move_san": "string",
      "eval_cp": "float",
      "win_prob": "float | null",
      "pv": ["SAN", "..."]
    }
  ],
  "played_move_rank": "integer",
  "phase": "opening | middlegame | endgame",
  "pattern_matches": [
    {
      "pattern_id": "string (A-Q1 + S)",
      "pattern_name": "string",
      "confidence": "float (0-1)",
      "evidence": "string"
    }
  ],
  "detector_version": "string",
  "context_window": {
    "moves_before": [
      {"ply": "integer", "move_san": "string", "eval_after": "float", "win_prob_after": "float"}
    ],
    "moves_after": [
      {"ply": "integer", "move_san": "string", "eval_after": "float", "win_prob_after": "float"}
    ]
  }
}
```

**Přidaná pole oproti SRC-1 v1.0:**
- `win_prob_before`, `win_prob_after`, `win_prob_delta` (SRC-2 F-010)
- `detector_version` (SRC-2 F-007 — umožňuje odlišit fact sheets před/po opravě detektoru)
- `engine_lines[].win_prob` (konzistence s eval_cp)

**Poznámka k `win_prob`:** SRC-2 F-010 ukazuje, že `MoveAnalysis` tato pole již má, ale v `_run_analyze_pgn()` se natvrdo dosazují jako `0.0`. Je to tedy **zapojení stávajícího pole, ne nové schema**.

---

## 7. Validator spec v1.1 (SRC-2 F-013 extended)

SRC-2 F-013 kritizoval, že §5.2.5 DBCL neurčuje mapování claim → pole. Toto je návrh `[SYNTHESIS]` doplnění:

| Claim typ (regex kategorie) | Příklad | Validace operátor | Cílové pole v BlunderFactSheet |
|----------------------------|---------|------------------|-------------------------------|
| piece-on-square | `Qf4`, `Kd7`, `Re3` | existence (parsovat na figuru+pole) | `fen_before` |
| check (pozitivní) | `dává šach`, `+`, `is check` | rovnost `true` | `board_state.was_in_check` |
| check (negativní) | `nedává šach`, `not check` | rovnost `false` | `board_state.was_in_check` |
| capture (pozitivní) | `mohl vzít`, `takes` | existence | `legal_moves.captures` ∪ `engine_lines[].pv` |
| capture (negativní) | `capture není možný` | negace existence | `legal_moves.captures` ∪ `engine_lines[].pv` |
| king-move (pozitivní) | `můžeš Kc1` | existence | `legal_moves.king_moves` |
| king-move (negativní) | `Kc1 není legální` | negace existence | `legal_moves.king_moves` |
| eval-číslo | `+823`, `+45` | tolerance ±10cp | `eval_before` ∪ `eval_after` ∪ `engine_lines[].eval_cp` |
| win-prob číslo | `85 %` | tolerance ±2% | `win_prob_before` ∪ `win_prob_after` |
| pattern reference | `pattern J`, `relaxace v koncovce` | existence s evidence validací | `pattern_matches[]` (s pattern guard z §5.3) |
| variation | `Kxc5 Ba4 Qh6+ Kxb2` | existence jako prefix | `engine_lines[].pv` |
| phase | `v koncovce`, `v zahájení` | rovnost | `phase` |

**Operátory:**
- existence: `value ∈ target_set`
- negace: `value ∉ target_set`
- rovnost: `target == value`
- tolerance: `|target - value| ≤ threshold`

**Příklad validace (INC-A):**
- Claim: „Qf4+ dává šach"
  - piece-on-square: `Qf4` ∈ `fen_before`? ✅ (Q na f4 sedí)
  - check: `board_state.was_in_check` == `true`? ❌ (false) → **REJECT**
- Claim: „místo Ka1 nebo Kc1"
  - king-move (pozitivní): `Ka1` ∈ `legal_moves.king_moves`? ✅ (Ka1 je legální tah)
  - king-move (pozitivní): `Kc1` ∈ `legal_moves.king_moves`? ❌ (Kc1 není legální) → **REJECT „Kc1" část**
- Claim: „blokoval věží — Rdg1"
  - block: `Rdg1` ∈ `legal_moves.blocks`? ❌ (prázdné, žádný blok neexistuje) → **REJECT**

Všechny tři halucinace z INC-A by validátor zachytil **ještě před průchodem do aggregate promptu**. Toto je `[SYNTHESIS]` doplnění založené na SRC-1 §5.2.5 + SRC-2 F-013.

---

## 8. Implementační sekvence (dle SRC-2 kap. 6, priorita z poměru dopad/náklad)

### P0 — musí být hotové PŘED DBCL v1 (kritická cesta)

| ID | Úkol | Effort | Zdůvodnění | Finding |
|----|------|--------|------------|---------|
| P0-1 | Přidat `fen: str` do `MoveAnalysis` (models/game.py), předat `fen_before` z `_run_analyze_pgn` | 1 řádek | FEN se počítá a zahazuje | F-002 |
| P0-2 | Auditovat všech 11 detektorů A–S, opravit pattern J, doplnit evidence-reference | 1–2 dny | P1 princip stojí na správnosti detektorů; F-007 | F-007 |
| P0-3 | Definovat `detector_version` konstantu, inkrementovat při každé opravě detektoru | 0.5 dne | Umožní auditovat fact sheets před/po opravou | F-007 |
| P0-4 | Zapojit `win_prob` výpočet do `_classify_move` (regrese z cp + lila prahy 10/20/30%) | 1 den | Win-prob delta je lepší klasifikační signál než cp | F-010 |
| P0-5 | Rozšířit validátor na obě prompt místa (mono + per-game) + kontrakt mezi nimi | 1–2 dny | Per-game halucinace se nyní nese do aggregate jako fakt | F-008 |

### P1 — DBCL v1 implementace (zapojení existujícího kódu)

| ID | Úkol | Effort | Zdůvodnění | Finding |
|----|------|--------|------------|---------|
| P1-1 | Inlinovat context extraction do `_run_analyze_pgn` (NE nový modul) | 1–2 dny | Předejít druhému replay PGN; existující smyčka má vše k dispozici | F-004 |
| P1-2 | Vytvořit BlunderFactSheet[] per-blunder pomocí `engine_client.analyze_position(multipv=3)` | 1 den | Multi-PV engine_lines[] existuje, jen se nevolá v blunder pipeline | F-005 |
| P1-3 | Aplikovat guard-clause šablonu na `build_coaching_prompt` i `_build_game_prompt` | 1 den | Oba prompt build sites jsou zranitelné | F-008 |
| P1-4 | Validátor narrative claim-grounder s tabulkou claim→field z §7 tohoto dokumentu | 2–3 dny | P3 princip vyžaduje adversarial verification | F-013 |
| P1-5 | SRSCard jako první reálný konzument BlunderFactSheet (producent `_run_analyze_pgn` → SRSCard) | 1 den | Schéma existuje, chybí producent | F-009 |

### P2 — integrace a konzistence

| ID | Úkol | Effort | Finding |
|----|------|--------|---------|
| P2-1 | Integrace BlunderFactSheet[] s existující cache konvencí `{game_id}_{color}_d{depth}.json` | 1 den | F-014 |
| P2-2 | Engine lock timeout exception handling v BlunderFactSheet pipeline | 0.5 dne | F-015 |
| P2-3 | Přejmenovat `services/validator.py` na `services/pattern_artifact_validator.py`, nový `narrative_validator.py` | 0.5 dne | F-011 |

### P3 — plánování do budoucna (nepotřebné pro debug session)

| ID | Úkol | Finding |
|----|------|---------|
| P3-1 | Implementovat `BlunderFactSheet` build tool jako MCP tool `extract_blunder_context` (pro interaktivní debug) | extension navrhuji |
| P3-2 | Definovat `consecutive errors` threshold pro pattern C | C chybí threshold |

### Doporučené pořadí (s křížovou závislostí)

```
P0-3 (detector_version)
    ↓
P0-2 (revize 11 detektorů)
    ↓
P0-1 (MoveAnalysis.fen) ←→ P0-4 (win_prob)
    ↓
P1-1 (inlinovat context do _run_analyze_pgn)
    ↓
P1-2 (multi-PV engine_lines přes analyze_position)
    ↓
P1-3 (guard-clauses na obou prompt sites) ←→ P0-5 (kontrakt per-game ↔ aggregate)
    ↓
P1-4 (validátor s tabulkou claim→field)
    ↓
P1-5 (SRSCard jako konzument)
    ↓
P2-* (integrace)
```

---

## 9. LLM injektovatelný kontext (pro další debug session)

Tato sekce je **připravena k přímému vložení do kontextu LLM**, pokud bude v další iteraci debug session povolán. Pokyny:

### 9.1 Minimální injektovatelný kontext

```
=== CONTEXT INJECTION: DBCL v1.1 ===

You are debugging the lichess-analyzer-mcp DBCL bridge.
Source artifacts:
  SRC-1: DBCL_cross_audit_artifact.md (author's design, 6 principles P1–P6)
  SRC-2: DBCL_Cross_Audit_Report.docx (Claude's audit, 21 findings)
  SRC-3: evening_coaching_2026-07-24.md (debug session, 10 blunders, new pattern S)

Three known incidents with full FEN/eval reconstruction:
  INC-A: kNAMNYUF ply 63 (Rdg1) — 3 hallucinations (false check, false block, false legal moves)
  INC-B: qmodxzNF ply 60 (Kd7) — new pattern S (capture aversion under check)
  INC-C: xUlQasD0 multi-blunder — false-positive pattern J at ply 89 (Vd7+)

Hallucination typology (H1–H8) is enumerated; verify your output against each type.

Pattern library has 11 detectors A–S. Pattern J is known to have a semantic bug
(it tests if move GIVES check, not if player WAS in check).
Pattern S is proposed but not yet in production.

You are operating under guard-clause DBCL v1.1 (see §5.3, §7 of unity doc).
Every chess claim must trace to a BlunderFactSheet field.
Unknown field = silence, not assumption.

=== END CONTEXT INJECTION ===
```

### 9.2 Pravidla pro LLM v iteraci

1. **Každou halucinaci typu H1–H8 zkontroluj** procházením draftu.
2. **Každý pattern match ověř proti guardu z §5.3** — neakceptuj pattern J bez `was_in_check=true` v evidence.
3. **Každý eval-číselný údaj** musí být v toleranci ±10cp oproti `eval_before/eval_after/engine_lines[].eval_cp`.
4. **Pokud narazíš na fakt, který není v BlunderFactSheet**, napiš `[UNSUPPORTED CLAIM: <fakt>]` a nepokračuj v narraci přes toto místo. Autor rozhodne, zda fakt doplní do fact sheetu, nebo odstraní z narrace.
5. **Negeneruj celé bloky kódu najednou.** Pokud autor požádá o implementaci, navrhni **první 1–3 řádky**, vysvětli záměr, počkej na feedback. Toto je `[SYNTHESIS]` doporučení vycházející z autorovy metody iterativní kontroly.
6. **Každý CoT krok zveřejni.** Autor čte chain of thoughts — ne skrývej úvahy.

### 9.3 Co NEpokládat LLM v iteraci

- „Najdi všechny bugy v `pattern_detector.py`" — příliš široký scope, audit vyžaduje čtení kódu řádek po řádku.
- „Implementuj BlunderFactSheet celou" — viz pravidlo 5.
- „Navrhni novou architekturu" — máme DBCL, máme audit, není třeba vynalézat znovu.

---

## 10. Open questions / ověření k další iteraci

| ID | Otázka | Zdroj | Doporučený způsob ověření |
|----|--------|-------|---------------------------|
| [VERIFY-1] | INC-A: CP loss 950 (SRC-1) vs 778 (SRC-3) — původ v rounding, multi-PV, nebo jiné Stockfish verzi? | rozdíl v datech | Přepočítat Stockfish depth 14 multipv=3, porovnat |
| [VERIFY-2] | INC-B: CP loss 1386 vs 1423 (SRC-3) — aritmetika vs Stockfish | rozdíl v datech | Přepočítat z `eval_before - eval_after` |
| [VERIFY-3] | `consecutive errors` threshold pro pattern C — kolik chyb v řadě? | chybějící spec | Analyzovat SRC-3 data, najít korelaci mezi count a dalšími features |
| [VERIFY-4] | Win-prob regrese z cp — lila prahy (10/20/30%) platí i pro 300+ cp ztrátu v koncovce? | F-010 | Empiricky ověřit na datasetu stovek her |
| [VERIFY-5] | Per-game LLM call halucinuje i na reálných datech? | F-008 | Repro na 5 per-game outputech z game_llm_cache.py, ruční audit |
| [VERIFY-6] | Zdali `SRSCard.fen` pole je použitelné jako BlunderFactSheet konzument 1:1 | F-009 | Porovnat schémata field-by-field |
| [VERIFY-7] | Pattern S (capture aversion under check) — je confidence ~40% správná? | INC-B | Rozšířit dataset o další capture-under-check pozice, přepočítat |
| [VERIFY-8] | Zda kNAMNYUF halucinovaný výstup existuje v nedokumentované interaktivní relaci | F-012 | Prohledat lokální historii chatů / debug logy |
| [VERIFY-9] | Audit zbývajících 8 detektorů (A, D, E, F, G, H, I, O, P, Q) na sémantickou konzistenci | F-007 extended | Ruční audit `pattern_detector.py` řádek po řádku, P0 krok |

---

## 11. Reference Index

| Sekce v tomto dokumentu | Zdroj |
|------------------------|-------|
| §1 Rámec problému | SRC-1 §1, §2.3; SRC-2 F-001, F-008 |
| §2.1 INC-A | SRC-1 §3; SRC-3 §1.2 (kNAMNYUF) |
| §2.2 INC-B | SRC-3 §1.1 (qmodxzNF), §4 (pattern S) |
| §2.3 INC-C | SRC-3 §2 (xUlQasD0); SRC-2 F-007 (pattern J bug) |
| §3 Halucinace typologie | SRC-1 §3.2 + [SYNTHESIS] |
| §4 Architektonická mapa | SRC-1 §2.2, §5.2; SRC-2 F-002, F-005, F-009, F-015 |
| §5 Pattern library revize | SRC-3 §3; SRC-2 F-007; [SYNTHESIS] §5.3 |
| §6 BlunderFactSheet v1.1 | SRC-1 §5.2.3; SRC-2 F-007, F-010 |
| §7 Validator v1.1 | SRC-1 §5.2.5; SRC-2 F-013; [SYNTHESIS] |
| §8 Implementační sekvence | SRC-2 kap. 6; SRC-2 F-004, F-008, F-011, F-014 |
| §9 LLM injekce | [SYNTHESIS] z SRC-1 + SRC-2 + autorova metoda |
| §10 Open questions | průnik nesrovnalostí ze všech 3 zdrojů |

---

*End of Unity Synthesis Document v1.0*
*Připraveno 2026-07-25 07:58Z pro další debug session MCP DBCL bridge.*
*Verze je 1.0 — každá nová iterace (po zpětné vazbě) zvýší číslo verze a přidá `CHANGELOG.md` sekci.*
