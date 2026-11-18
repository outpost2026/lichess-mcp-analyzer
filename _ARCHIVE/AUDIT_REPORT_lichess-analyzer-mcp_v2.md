# Aktualizovaný audit — lichess-analyzer-mcp

**Auditor:** Claude (Anthropic)
**Datum:** 2026-07-24
**Zdroj v1:** DIGITAL_TWIN_v1.0.md (audit de novo, bez přístupu ke kódu)
**Zdroj v2 (tento dokument):** skutečný zdrojový kód, `github.com/outpost2026/lichess-mcp-analyzer`, branch `debug/phase1-fixes` (HEAD: `506b20c`)
**Metodologická poznámka:** Tento audit staví na v1 a **verifikuje každý nález proti reálnému kódu**. U každé položky je uvedeno, zda šlo o (a) potvrzený nález, (b) vyvrácený nález (kód je v pořádku / jinak, než twin naznačoval), nebo (c) nové zjištění, které twin nezachytil. Zahrnuty jsou i souvislosti z historie commitů a existující interní dokumentace (DEBUG_REPORT, testy).

---

## Section 0: Co se změnilo oproti auditu v1

Toto je nejdůležitější sekce — shrnuje, jak moc se de novo audit nad digital twinem shodoval se skutečností.

| Nález z v1 | Verdikt po čtení kódu |
|---|---|
| F1 — mate score `None` → crash v `evaluate_move()` | **Vyvráceno.** Kód explicitně ošetřuje `None` na všech třech místech (`if best_score is not None`, `if actual_score is not None`). Žádný crash. Ale objevil se **jemnější problém**: na mate pozicích `cp_loss` tiše spadne na `0` místo skutečné hodnoty — viz F1' níže. |
| F2 — path traversal přes `username`/`game_id` v cache cestách | **Potvrzeno.** `_pgn_cache_path`, `_user_games_cache_path`, `_cache_path` v `lichess_client.py`/`game_analyzer.py` vkládají řetězec přímo do `os.path.join()` bez sanitizace. Tool vrstva (`fetch_games.py` atd.) také nevaliduje formát. Riziko reálné, viz F2 níže. |
| F3 — pattern confidence fixní/neváhované u malých vzorků | **Potvrzeno beze změny.** `_detect_o/p/q/q1/r` mají hardcoded confidence (0.6/0.5/0.8/0.7/0.7) bez ohledu na frekvenci nebo velikost vzorku, přesně jak popisoval twin. |
| F4 — univerzální `{"error": str(e)}` | **Potvrzeno.** Všech 9 tools má identický vzor. Nadto: `match_patterns.py` navíc loguje přes `log.exception()` před vrácením chyby — o něco lepší observabilita (do log souboru), ale k volajícímu jde pořád jen holý string. |
| F5 — globální analysis lock serializuje Stockfish | **Potvrzeno přesně dle popisu**, včetně zombie-recovery mechanismu. Kód odpovídá twinu 1:1. |
| Token leakage (Section 4 v1) | **Vyvráceno / zmírněno.** `server.py` loguje jen `ka['provider']` (jméno poskytovatele) a počet nalezených klíčů — nikdy hodnotu. `.env` je navíc správně v `.gitignore`. Toto riziko bylo v v1 nadhodnoceno. |
| kb/ modul nejasná role | **Potvrzeno + upřesněno.** `kb/schemas.py` (`validate_against_schema`) je jediná reálně použitá část, volaná z `match_patterns.py`. `kb/writer.py` a `kb/md_reporter.py` nejsou nikde importovány — mrtvý kód. |

**Zcela nové nálezy, které v1 (bez kódu) nemohl odhalit**, jsou popsány níže v Section 1.

---

## Section 1: Nové nálezy z reálného kódu

### N1 — `mistakes` list je vždy prázdný (Critical, potvrzený datový bug)

**Lokace:** `services/game_analyzer.py`, `_run_analyze_pgn()`, řádek 161-164:
```python
if classification in ("blunder", "mistake"):
    analysis.blunders.append(move_analysis)
elif classification == "inaccuracy":
    analysis.inaccuracies.append(move_analysis)
```
Tahy klasifikované jako `"mistake"` (150-299 cp ztráta) se ukládají do `analysis.blunders`, nikdy do `analysis.mistakes`. Datový model `GameAnalysis.mistakes` (viz `models/game.py`) existuje a je serializován (`to_dict`/`from_dict`), ale nikdy se nenaplní.

**Dopad:**
- T2 (`analyze_game`) vrací `stats.mistakes` vždy jako `0`, bez ohledu na skutečný počet.
- `diagnostician.py` (`total_mistakes += len(analysis.mistakes)`) tedy agreguje vždy 0 přes všechny hry → `WeaknessReport.mistake_count` je systematicky nesprávné pro každého uživatele, každé volání T6.
- Coaching prompt (`llm_client.py`) obsahuje `Mistakes: {z}` — vždy 0, což LLM kaskádě dává zkreslený vstup a produkuje nekorektní/matoucí coaching text ("žádné mistakes" navzdory reálným 150-299cp chybám).
- Existující test `test_mistake_subkeys` v `tests/test_prompt_contract.py` tento bug **nezachytí**, protože obsahuje guard `if not mistakes: return` — test ověřuje strukturu klíčů, pokud nějaké záznamy existují, ale neověřuje, že vůbec existují. Testovací sada tedy běží "zeleně" i s aktivním bugem.

**Fix (koncepčně):** V `_run_analyze_pgn()` rozlišit klasifikaci `"blunder"` a `"mistake"` do samostatných větví (`if classification == "blunder": ... elif classification == "mistake": analysis.mistakes.append(...) elif classification == "inaccuracy": ...`). Doporučuji přidat i nechráněný test (bez `if not X: return` guardu), který explicitně vygeneruje partii se zaručenou 150-299cp chybou a ověří, že skončí v `mistakes`, ne v `blunders`.

### N2 — "most-played opening" pravidlo bere první, ne nejčastější opening (Minor, logická chyba)

**Lokace:** `services/diagnostician.py`, řádek 56-57:
```python
if openings and list(openings.values())[0]["blunders"] > 2:
    top_weaknesses.append(f"Opening preparation: {list(openings.keys())[0]}")
```
`openings` je běžný `dict` naplňovaný v pořadí, v jakém se otevření objeví při iteraci přes hry — **není** seřazený podle počtu her ani blunderů. `list(openings.values())[0]` tedy bere první opening, na který systém narazil, ne opening s nejvíce blundery nebo nejvíc hraný. (Pozn.: `leaky_openings` o pár řádků výše *je* správně seřazený přes `sorted(..., key=lambda x: x[1]["blunders"], reverse=True)` — nekonzistence naznačuje, že šlo o přehlédnutí, ne záměr.)

**Dopad:** Textové doporučení "Opening preparation: {jméno}" v `top_weaknesses` může ukazovat na opening, který není tím se skutečně nejvyšším počtem chyb.

**Fix:** Použít `sorted(openings.items(), key=lambda x: x[1]["blunders"], reverse=True)[0]` stejně jako o pár řádků výše u `leaky_openings`.

### N3 — Middlegame-weakness pravidlo srovnává absolutní počty, ne rate (Major, potvrzeno z v1 + upřesněno)

**Lokace:** `services/diagnostician.py`, řádek 52:
```python
if phase_blunders["middlegame"] >= phase_blunders["opening"] + phase_blunders["endgame"]:
```
Toto přesně odpovídá nálezu z v1 (Section 3) — potvrzeno beze změny. Middlegame typicky obsahuje 2-3× více tahů než opening/endgame dohromady, takže pravidlo bude téměř vždy pravdivé bez ohledu na skutečnou per-move chybovost. Vzhledem k tomu, že `phase_stats` (v `models/game.py`, `_compute_phase_stats()`) už počítá `errors` per fázi i `move_count`, **oprava je triviální** — data pro normalizaci na rate už existují, jen se nepoužívají v `diagnostician.py`.

### N4 — Pattern G (`_detect_g`) míchá "frequency" s blunder rate (Minor, nová nesrovnalost)

**Lokace:** `services/pattern_detector.py`, řádek 149:
```python
frequency=int(max(white_blunder_rate, black_blunder_rate)),
```
U ostatních detektorů (A, B, C, J, O, P, Q, Q1, R) `frequency` znamená počet postižených her/výskytů. U patternu G je to zaokrouhlená blunder rate (desetinné číslo zaokrouhlené na int) — sémanticky jiná veličina. Protože `detect_all()` filtruje `match.frequency >= pdef.min_occurrences` (výchozí `min_occurrences=2` pro G dle PatternDef), může toto rozdílné škálování způsobit, že pattern G projde nebo neprojde filtrem z jiného důvodu, než autor zamýšlel (např. blunder rate 1.4 → `frequency=1` → nesplní `min_occurrences=2`, i když jde o 5 postižených her).

### N5 — `_export_by_player` fallback logika: historie ukazuje aktivně řešenou nejistotu (Info, kontext, ne nový bug)

Git historie (`99f7b24` → `a85ff8c`) ukazuje, že autor nejprve zjistil, že Lichess API endpoint pro výpis her uživatele vrací na produkci 404 na všech 3 známých variantách cesty, implementoval vlastní httpx-based 3-endpoint fallback s explicitním `RuntimeError`, a následně to **zpět nahradil** jednodušším `client.games.export_by_player()` (aktuální stav HEAD). Verifikační skript `scripts/verify_a4_fix.py` očekává úspěšný běh (`assert len(games) > 0`) pro testovací účet — což naznačuje, že problém byl nakonec identifikován jinde (pravděpodobně v samotném volání/parametrech berserk klienta, ne v cestě endpointu jako takové) a byl vyřešen. **Nejde o nález auditu**, ale stojí za zmínku, že `DEBUG_REPORT_2026-07-22_v003.md` v repozitáři je vzhledem k tomuto pozdějšímu revertu **zastaralý** — popisuje stav, který už neplatí, a mohl by matoucím způsobem sloužit jako reference při budoucím ladění.

### N6 — `patterns/` je prázdný, neimportovaný balíček (Info, potvrzuje "dead code" hypotézu z v1)

`src/lichess_analyzer_mcp/patterns/__init__.py` existuje, je prázdný, a nikde v repozitáři není importován (`grep` na `from lichess_analyzer_mcp.patterns` nevrací žádný skutečný import mimo docstring zmínku o `chess_pattern_v5.json`). Pravděpodobně příprava na budoucí extrakci pattern definic z `models/pattern.py` do samostatného modulu — v aktuálním stavu je to čistě mrtvý adresář.

### N7 — Pořadí operací v `match_patterns.py`: řazení proběhne až po persist a schema validaci (Minor)

**Lokace:** `tools/match_patterns.py`, řádky 103-126. `artifact["patterns_detected"] = result` se nastaví na řádku 106, poté proběhne schema/sanity validace (110-118) a `store_patterns()` (124) — teprve na řádku 126 se `result` in-place seřadí podle severity/confidence. Díky sdílené referenci na list se řazení nakonec promítne i do `artifact`, takže to, co se vrátí volajícímu, je seřazené — ale **uložený resource artifact (`store_patterns`) a schema validace proběhly nad neseřazenými daty**. Funkčně to pravděpodobně nevadí (validace je na obsahu položek, ne na pořadí), ale je to křehké pořadí kódu, které při budoucí refaktorizaci snadno praskne (např. pokud by `store_patterns` dělal hlubokou kopii).

---

## Section 2: Bezpečnostní review — upřesnění

- **Token leakage:** zmírněno na základě čtení `server.py` — bezpečné logování (jen jméno poskytovatele + count).
- **`.env` handling:** `.gitignore` správně obsahuje `.env`, `data/`, `stockfish/`. Riziko commitnutí klíčů je nízké.
- **Path traversal (F2):** potvrzeno v `lichess_client.py` (`_pgn_cache_path`, `_user_games_cache_path`) a `game_analyzer.py` (`_cache_path`) — žádná validace `username`/`game_id` proti `../` nebo neplatným znakům cesty pro souborový systém, ani na úrovni tool vrstvy (`fetch_games.py` validuje jen `source` a `max_games`, ne `username`). Toto zůstává nejkonkrétnější doporučenou opravou z celého auditu — je levná (jeden regex whitelist) a odstraňuje reálné, byť nízkopravděpodobné riziko.
- **Input validace obecně:** `depth`/`max_games` jsou ošetřeny `max(min(...))` clampingem na tool úrovni ve všech relevantních tools (potvrzeno v `match_patterns.py`, `analyze_position.py`) — to je lépe, než twin naznačoval ("range [x,y]" v twinu byl popis, teď potvrzeno jako reálně vynucené v kódu, ne jen v docstringu).
- **FEN validace:** neexistuje explicitní validace před `chess.Board(fen)`, ale `python-chess` vyhodí `ValueError` na neplatný vstup, který spadne do univerzálního except handleru → `{"error": ...}`. Bezpečné, i když ne elegantní.

---

## Section 3: Aktualizovaná tabulka nálezů (Top findings, v2)

| ID | Severity | Lokace | Popis | Stav |
|----|----------|--------|-------|------|
| N1 | **Critical** | `game_analyzer.py:161-164` | `mistakes` list nikdy nenaplněn — vše jde do `blunders` | **Nové** |
| F2 | **Critical** | `lichess_client.py`, `game_analyzer.py` (cache paths) | Path traversal risk přes nesanitizovaný `username`/`game_id` | Potvrzeno |
| N3 | Major | `diagnostician.py:52` | Middlegame-weakness pravidlo na absolutních počtech, ne rate | Potvrzeno (= F z v1) |
| F3 | Major | `pattern_detector.py` (`_detect_o/p/q/q1/r`) | Fixní confidence bez ohledu na evidenci | Potvrzeno |
| F4 | Major | všechny `tools/*.py` | `{"error": str(e)}` bez kategorie chyby | Potvrzeno |
| N2 | Minor | `diagnostician.py:56-57` | "most-played opening" bere první, ne nejčastější | **Nové** |
| N4 | Minor | `pattern_detector.py:149` | Pattern G míchá frequency s blunder rate | **Nové** |
| N7 | Minor | `match_patterns.py:103-126` | Řazení po persist/validaci — křehké pořadí | **Nové** |
| F1' | Minor | `engine_client.py:129-132` | Mate pozice → `cp_loss` tiše `0` místo skutečné hodnoty | Upřesněno (dříve Critical crash, nyní tichá ztráta signálu) |
| — | Info | `kb/writer.py`, `kb/md_reporter.py` | Neimportováno nikde — mrtvý kód | Potvrzeno |
| N6 | Info | `patterns/` | Prázdný balíček, neimportováno | **Nové** |
| N5 | Info | git historie `_export_by_player` | `DEBUG_REPORT_v003.md` zastaralý vůči aktuálnímu HEAD | **Nové** |

---

## Section 4: Doporučení (aktualizováno)

**Immediate:**
1. Opravit N1 (`mistakes` klasifikace) — nejvyšší dopad na korektnost reportovaných dat, nejlevnější oprava (jedna větev if/elif).
2. Přidat test bez guard-return, který ověří, že `mistakes` list se skutečně naplňuje na syntetické partii se zaručenou 150-299cp chybou.
3. Sanitizovat `username`/`game_id` (whitelist regex) před použitím v cestách k souborům — F2.

**Short-term:**
4. Opravit N3 (per-move rate místo absolutního počtu) — data pro to už existují v `phase_stats`.
5. Opravit N2 (`sorted()` na `openings` stejně jako u `leaky_openings`).
6. Sjednotit sémantiku `frequency` napříč pattern detektory (N4) — buď všude "počet postižených her", nebo explicitně jinak pojmenované pole pro G.
7. Odstranit nebo aktualizovat `DEBUG_REPORT_2026-07-22_v003.md`, aby neodkazoval na revertnutý fix (N5) — riziko matení budoucího debugování.

**Medium-term:**
8. Rozhodnout osud `patterns/` (dokončit extrakci, nebo smazat prázdný adresář) a `kb/writer.py`/`kb/md_reporter.py` (dokončit integraci, nebo odstranit).
9. Zavést statistickou váhu na pattern confidence u detektorů s hardcoded hodnotami (F3) — beze změny oproti v1.
10. Strukturovaný error formát napříč tools (F4) — beze změny oproti v1.

---

## Section 5: Celkové hodnocení (aktualizováno)

- **Skóre v1 (de novo nad twinem):** 5/10
- **Skóre v2 (po čtení kódu):** **5.5/10** — mírně nahoru. Důvod: dvě obavy z v1 (mate-score crash, token leakage) se ukázaly jako neopodstatněné nebo přehnané, což svědčí o tom, že autor tato místa už řešil. Zároveň se ale objevil nový, konkrétní a snadno ověřitelný datový bug (N1), který má větší reálný dopad na kvalitu výstupu než cokoli, co bylo v twinu popsáno — protože jde o ticho špatná data, ne o crash, který by si někdo všiml.
- **Klíčové ponaučení pro cross-audit workflow:** Digital twin jako zdroj pravdy je silný na architektuře a explicitně zdokumentovaném chování, ale nemůže odhalit bugy, které leží v **detailu implementace jedné větve kódu** (N1) nebo v **nekonzistenci mezi dvěma podobně vyhlížejícími bloky kódu** (N2 vs. `leaky_openings`, N4 vs. ostatní detektory) — tyto vyžadují čtení skutečného zdrojového kódu řádek po řádku. Doporučuji do budoucna kombinovat: twin pro rychlý architektonický scan + namátkové čtení zdrojového kódu klíčových agregačních funkcí (diagnostician, pattern_detector) pro logické nekonzistence.
- **Production-ready pro osobní použití?** Ano, s výhradou opravy N1 — bez ní jsou coaching reporty o `mistakes` prakticky bezcenné (vždy nula).
- **Production-ready pro veřejné MCP publikování?** Ne, ze stejných důvodů jako v1 (F2, F3, F4), plus nově N1 jako blokující položka pro korektnost dat.
