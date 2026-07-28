#  Audit: Chess Patterns modul & MCP pipeline
### `lichess-mcp-analyzer` — hloubkový nezávislý audit + kompetenční pozice autora

| | |
|---|---|
| **Datum auditu** | 2026-07-28 |
| **Auditovaný commit** | `0f4eef5` (HEAD, `main`) |
| **Auditor** | Claude (Anthropic) — na základě injektovaného kontextu + vlastní ověření proti live repozitáři |
| **Rozsah** | MCP pipeline (lehký přehled) → Chess Patterns modul (hloubkově) |
| **Metoda** | Viz [Metodologická poznámka](#metodologická-poznámka) — toto NENÍ pouze parafráze dodaného kontextu |

---

## Executive Summary

Dodaný `PATTERN_DETECTOR_AUDIT_INJECT.md` je přesný. Všech pět jím tvrzených zjištění (W1–W5) jsem ověřil proti skutečnému zdrojovému kódu na `main` a tři z nich navíc **empiricky reprodukoval** spuštěním kódu (ne jen čtením). Nešlo o slepou důvěru vstupnímu artefaktu — samostatně jsem naklonoval repozitář, nainstaloval závislosti do izolovaného prostředí, spustil celou testovací sadu (68/68 zelených) a napsal tři reprodukční skripty.

Nad rámec injektovaného kontextu jsem našel **7 dalších nálezů (D1–D7)**, z toho jeden nový **CRITICAL crash bug** (nezachycená výjimka, která shodí celou dávkovou detekci) a jeden nález, který přímo podkopává teoretický základ projektu (kompresní poměr je matematicky konstantní napříč patterny, takže neměří to, co má).

**Verdikt:** Chess Patterns modul je koncepčně silný a testovaný, ale má systémový problém s **kontraktem výstupních dat** — 13 z 14 detektorů si evidenci formátuje samo bez sdíleného schématu, a obě validační vrstvy (schema + sanity) tento kontrakt nekontrolují. To je přesná příčina halucinačního incidentu z 28. 7. 2026 a je to opravitelné za odhadem **~4,5 h** čistě P0 prací (viz [roadmapa](#iterační-roadmapa-s-eroi)).

---

## 1. MCP pipeline — přehled (lehký sken)

Cílem není auditovat všech 12 nástrojů do hloubky (to by bylo scope creep) — jen ověřit, že **stavba je funkční** jako základ pro Chess Patterns.

| Signál | Zjištěno | Komentář |
|---|---|---|
| Registrované MCP nástroje | **12** (`@app.tool`) | README uvádí "11" — drobný, kosmetický nesoulad dokumentace (D7) |
| CI pipeline | `.github/workflows/test.yml`: ruff lint → mypy → pytest+coverage → codecov | Solidní baseline, spouští se na push i PR |
| Testovací sada | **68/68 passed** (ověřeno lokálním spuštěním, stejný příkaz jako CI) | Beze změny oproti README tvrzení |
| Bootstrap | `FastMCP` + registrace nástrojů přes side-effect importy v `server.py` | Standardní, čitelný vzor |
| Persistence patternů | `resources/pattern_resources.py` — JSON store s resource URI (`lichess://patterns/{key}`) | Má vlastní nález, viz D6 |

> 🧒 **Pro chytré dítě:** Představ si MCP server jako recepci v hotelu. Recepční (server.py) při startu "probudí" všechny služby hotelu (nástroje — analýza partie, vyhledání patternů, atd.) a čeká, až host (AI agent) o něco požádá přes okénko (JSON-RPC). CI pipeline je jako bezpečnostní kontrola před tím, než recepce vůbec otevře — zkontroluje, že žádná služba není rozbitá, než pustí prvního hosta dovnitř.

**Závěr k pipeline:** funkční, s běžnou CI hygienou. Žádný blokující nález mimo Chess Patterns modul nebyl v rámci tohoto skenu identifikován. Hloubkový audit zbylých 11 nástrojů je mimo scope tohoto reportu (viz doporučení v roadmapě).

---

## 2. Chess Patterns — architektura (ověřeno proti kódu)

```
lichess_match_patterns  (tools/match_patterns.py:34)
  │
  ├─ [game_ids větev]  _find_cached_analysis()  →  cache/*.json
  ├─ [username větev]  fetch_user_games() → analyze_pgn()
  │
  ▼ sdílený pipeline
  PatternDetector().detect_all(analyses, metadata)     (řádek 150)
      → 14 × _detect_{id}()  →  PatternMatch[]           (services/pattern_detector.py)
  compute_compression(m, analyses)                      (řádek 154)
      → compressibility_validator.py:13
  validate_against_schema()  +  validate_pattern_artifact()   (řádky 193, 198)
      → kb/schemas.py  +  services/pattern_artifact_validator.py
  store_patterns(resource_key, artifact)                (řádek 207)
      → resources/pattern_resources.py:39
  return artifact   ← AGENT TOTO VIDÍ
```

> 🧒 **Pro chytré dítě:** "Serializace" v kroku `entry = {...}` znamená: vezmi bohatý balíček dat, co má detektor uvnitř (`PatternMatch` s polem `game_ids`), a zabal ho do menší krabičky (JSON), kterou pošleš agentovi. Problém W1 níže je přesně to, že při balení krabičky **jedna položka vypadla ven a nikdo si toho nevšiml** — krabička vypadá plná, ale chybí v ní důkaz.

14 aktivních detektorů (patterny A, B, C, G, I2, J, O, P, Q, Q1, Q2, R, S, N). Patřičný 15. pattern "I" (Bait trap) je záměrně `manual_only` — bez `_detect_i` metody, `detect_all()` ho tiše přeskočí přes `getattr(..., None)`. To je správně a je to i otestované (`test_all_patterns_have_detectors`).

---

## 3. Nálezy — ověření injektovaného kontextu (W1–W5)

Všech pět tvrzení bylo **potvrzeno**. U W1 a W3 jsem navíc napsal a spustil reprodukční skript přímo proti `PatternDetector` třídě.

### W1 — CRITICAL — `game_ids` mizí při serializaci ✅ potvrzeno empiricky

`tools/match_patterns.py:155-165` — `entry` dict obsahuje `pattern_id`, `frequency`, `evidence`, `mitigation`... ale nikdy `m.game_ids`.

```
Reprodukce (3 hry, Pattern J s frequency=6):
  PatternMatch.game_ids (interní)  = ['game_AAA', 'game_CCC']
  Klíče v odpovědi pro agenta      = ['pattern_id', 'frequency', 'evidence']
  'game_ids' v odpovědi?             False
  'affected_games' v odpovědi?       False
→ Agent vidí frequency=6, ale NEMÁ ŽÁDNÝ ZDROJ, kterých 6 her to bylo.
```

Toto je přesně mechanismus, který 28. 7. 2026 vedl k fabrikaci konkrétního detailu partie, která s daným patternem neměla nic společného (`sAtfdKTi` ply 16 byl `O-O`, ne šach).

### W2 / W5 — HIGH — `evidence["affected_games"]` má tři různé typy napříč 14 detektory ✅ potvrzeno

| Formát | Počet | Patterny |
|---|---|---|
| `list[str]` ✅ (správně) | 1 | B |
| `int` (počet, ne seznam) ⚠️ | 6 | C, O, P, Q1, R, S |
| chybí úplně ❌ | 7 | A, G, I2, J, Q, Q2, N |

Toto jsem ověřil čtením všech 14 metod `_detect_*` v `services/pattern_detector.py` (řádky 42–558) — tabulka výše odpovídá kódu do posledního patternu.

### W3 — MEDIUM — `_detect_j` chybně klasifikuje tahy králem jako "blok" ✅ potvrzeno empiricky

`pattern_detector.py:225`:
```python
if m.was_in_check and "x" not in m.move_san:   # chybí "K" not in m.move_san
```

```
Reprodukce: tah Kd3 (král uniká šachu), was_in_check=True, mistake 282cp
→ Pattern J vystřelil s frequency=1 na čistém tahu králem.
→ Sémanticky rozporné s vlastní definicí patternu ("blok figurou").
```

### W4 — LOW — překryv patternů S a J ✅ potvrzeno na úrovni kódu

Stejný tah (v šachu, blok místo braní šachující figury) může splnit podmínky obou `_detect_s` (řádek 492) i `_detect_j` (řádek 216). Žádná deduplikace ani dokumentace tohoto překryvu v kódu neexistuje.

---

## 4. Nové nálezy — nad rámec injektovaného kontextu (D1–D7)

Toto je přidaná hodnota tohoto auditu: nálezy, které injektovaný dokument nezmiňuje, ale jsou reálné a ověřené proti kódu i behaviorálně.

### D1 — CRITICAL — `_detect_s` spadne na chybějícím/prázdném FEN 🆕 empiricky reprodukováno

`pattern_detector.py:497`:
```python
if m.was_in_check and m.centipawn_loss >= THRESHOLD_S_CAPTURE_AVERSION_CP:
    board = chess.Board(m.fen)   # ← žádný guard, na rozdíl od _detect_n (řádek 530-537)
```

`_detect_n` o pár desítek řádků níže dělá to samé (`chess.Board(m.fen)`), ale obalené v `try/except (ValueError, IndexError)` a s explicitní kontrolou `m.fen` před voláním. `_detect_s` nemá ani jedno.

```
Reprodukce: 1 tah s was_in_check=True, cp_loss=600, fen=""  (např. starší cache záznam
bez pole "fen" — MoveAnalysis.from_dict() takový záznam přijme a doplní default "").
→ CRASH: ValueError: empty fen
→ Vyhozeno z detect_all() → NEIZOLOVANÉ na jeden pattern nebo jednu hru.
→ CELÁ dávková detekce (všech 14 patternů, všechny hry v requestu) spadne.
→ Vnější try/except v lichess_match_patterns() to zachytí a vrátí generické
  {"error": "empty fen"} — agent nedostane VŮBEC ŽÁDNÝ pattern, ani ty nepostižené.
```

Toto je závažnější než W1–W5, protože nejde o ztrátu dat (silent fail), ale o **jeden špatný záznam v jedné hře, který zablokuje výsledek pro celou dávku**. Přímo se dotýká zadání "chybuvzdorný modul".

### D2 — HIGH — kompresní poměr je matematicky konstantní napříč patterny 🆕 empiricky reprodukováno

`compressibility_validator.py:13-23`:
```python
evidence_count = len(match.evidence) if match.evidence else 1
exception_cost = evidence_count * 2
pattern_cost = PATTERN_BASE_COST + exception_cost   # PATTERN_BASE_COST = 10
compression_ratio = total_moves / pattern_cost
```

Problém: **všech 14 detektorů vrací `evidence` jako jednoprvkový list** (`evidence=[{...}]`). `len(match.evidence)` je proto vždy `1`, `exception_cost` je vždy `2`, `pattern_cost` je vždy `12` — konstanta. `compression_ratio` tedy nezávisí na patternu vůbec, jen na `total_moves` v dávce (stejné pro všechny patterny v jednom volání).

```
Reprodukce: batch se 2 detekovanými patterny (B, C), různá bohatost evidence
→ Pattern B: compression_ratio = 0.6
→ Pattern C: compression_ratio = 0.6   (identické, přestože jde o odlišné patterny)
```

Toto přímo podkopává vlastní teoretický rámec projektu. Docstring v `models/pattern.py:7-14` výslovně varuje: *"if a pattern's name/mechanism/hypothesis does not match its code detection, the compression ratio measures noise, not signal."* Ironií je, že tady selhání není na sémantické vrstvě (jak dokument popisuje pro Pattern O), ale na **implementační vrstvě** metriky samotné — CR neměří nic patternově specifického, protože vstupní proměnná (`evidence_count`) je uzamčená na 1 už datovou strukturou.

### D3 — HIGH — konfidenční vzorec je v rozporu s `min_occurrences=1` designem 🆕 kvantifikováno

Pět patternů (I2, J, Q1, S, N) má v `PatternDef` explicitně `min_occurrences=1` — autor tím říká "jeden výskyt je dost, ať se to reportuje". Konfidenční vzorec u těchto pěti detektorů je ale postavený na poměru `výskyty / total_games`, což pro N=1 dává skoro nulovou hodnotu bez ohledu na to, že pattern už prošel filtrem jako "hodný nahlášení":

| Pattern | Severity | Confidence @ 1 výskyt / 35 her |
|---|---|---|
| I2 | low | 2,3 % |
| J | high | 2,6 % |
| Q1 | low | 2,3 % |
| **S** | **critical** | **1,4 %** |
| N | high | 2,3 % |

35 her je mimochodem přesně velikost referenčního datasetu, který projekt sám používá (`coaching_report_anonymous_session_35.md`) — čísla výše nejsou vykonstruovaná, jsou to reálné hodnoty, které by vzorec vrátil na vlastních datech projektu.

Nejzávažnější případ: **Pattern S — "Capture aversion under check" — má severity `critical`**, ale při jediném (byť zcela validním, threshold-splňujícím) výskytu dostane confidence 1,4 %. Agent nebo downstream konzument s prahem "ignoruj cokoliv pod 10 % confidence" by kriticky závažný, návrhem záměrně jedno-výskytový pattern odfiltroval. Injektovaný dokument tento problém zmiňuje jen u I2 (a s ne zcela přesným výpočtem) — ve skutečnosti jde o systémovou vlastnost páté patternů, ne o izolovanou chybu jednoho vzorce.

### D4 — MEDIUM — dvě validační vrstvy, jedna slepá skvrna 🆕

`kb/schemas.py` (`PATTERN_SCHEMA`) i `services/pattern_artifact_validator.py` (`validate_pattern_artifact`) jsou nezávislé, redundantní validační vrstvy — to je samo o sobě dobrý architektonický instinkt ("defense in depth"). Problém: **ani jedna z nich nekontroluje přítomnost `game_ids`/`affected_games`** — tedy přesně to pole, jehož absence způsobila halucinaci. Dvě sítě, stejná díra v obou.

> 🧒 **Pro chytré dítě:** Je to jako mít dva různé strážce u dveří — jeden kontroluje jméno na vstupence, druhý kontroluje razítko. Vypadá to bezpečně, dva strážci přece! Jenže kdyby někdo přišel úplně bez vstupenky, ani jeden strážce by to nekontroloval, protože "chybějící vstupenka" nikoho z nich vůbec nenapadlo hlídat.

### D5 — MEDIUM — validace je jen doporučující, nikdy vynucená 🆕

`pattern_artifact_validator.py:51` definuje `assert_valid_artifact()` — tvrdé selhání (výjimka) při neplatném artefaktu. **Nikde v `src/` ani `tests/` se ale nevolá** (ověřeno `grep -rn`). Používá se jen měkký `validate_pattern_artifact()`, jehož výstup se jen připojí jako `artifact["_sanity_warnings"]` — agent si toho může, ale nemusí všimnout. Přesně to se stalo v případové studii z injektovaného dokumentu (bod 4.2 tamtéž): agent měl k dispozici data, která fabrikaci vyvracela, a nezkontroloval je.

### D6 — LOW — persistovaný záznam patternů je prakticky nedohledatelný 🆕

`resources/pattern_resources.py`:
- `_save_store()` (řádek 25) polyká `OSError` tiše (`except OSError: pass`) — zápis na disk může selhat bez jakékoliv stopy.
- `store_patterns()` vrací `resource_key` / URI (`lichess://patterns/{key}`), ale `tools/match_patterns.py:207` tuto návratovou hodnotu **zahazuje** a nikde ji nepřidává do vraceného `artifact` dictu.

Výsledek: perzistovaná kopie patternů existuje (pokud zápis uspěl), ale agent nemá jak její `resource_key` zjistit, aniž by uhodl přesný formát `{username}_{timestamp}` včetně sekundové přesnosti.

### D7 — MINOR (kosmetické) — README neodpovídá počtu nástrojů 🆕

`README.md` tvrdí "Nástrojů: 11", reálně je registrováno 12 (`grep -c "@app.tool"`). Triviální, ale symptomatické pro rychlé tempo vývoje (dokumentace o commit pozadu za kódem).

---

## 5. Souhrnná tabulka nálezů

| ID | Závažnost | Zdroj | Lokace | Stav |
|---|---|---|---|---|
| **W1** | CRITICAL | injekt | `match_patterns.py:155-165` | ✅ ověřeno empiricky |
| **D1** | CRITICAL | nový | `pattern_detector.py:497` | ✅ ověřeno empiricky |
| **D3** | HIGH (crit. na patternu S) | nový | 5× confidence formule | ✅ kvantifikováno |
| **W2/W5** | HIGH | injekt | 14× `_detect_*` | ✅ ověřeno čtením |
| **D2** | HIGH | nový | `compressibility_validator.py:13-23` | ✅ ověřeno empiricky |
| **D4** | MEDIUM | nový | `kb/schemas.py` + `pattern_artifact_validator.py` | ✅ ověřeno |
| **D5** | MEDIUM | nový | `pattern_artifact_validator.py:51` | ✅ ověřeno (grep) |
| **W3** | MEDIUM | injekt | `pattern_detector.py:225` | ✅ ověřeno empiricky |
| **W4** | LOW | injekt | `pattern_detector.py:216,492` | ✅ ověřeno |
| **D6** | LOW | nový | `pattern_resources.py:25-44` | ✅ ověřeno |
| **D7** | MINOR | nový | `README.md` | ✅ ověřeno |

**12 nálezů celkem, 0 vyvrácených.** Vstupní artefakt měl 100% přesnost na tom, co tvrdil — jen nezachytil celý obraz.

---

## 6. Test coverage

Spustil jsem `tests/test_pattern_semantic_contract.py` v izolovaném venv (stejný postup jako CI): **18/18 passed**, celá sada **68/68 passed**.

Potvrzuji tabulku chybějícího pokrytí z injektovaného dokumentu — testy pro A, G, I2, J (pozitivní), Q1 skutečně neexistují, a **žádný test necílí na formát/přítomnost `affected_games`** ani na tool-response úroveň (`W1`). To znamená: **žádný z 68 zelených testů by nezachytil ani jeden z nálezů W1, W2, D1, D2, D3, D4, D5** — všechny leží mimo aktuální hranice testovacího kontraktu. To vysvětluje, jak mohly projít CI a přesto způsobit incident v produkci.

---

## 7. Zralost, úroveň a originalita pipeline (kvantitativně)

| Metrika | Hodnota | Interpretace |
|---|---|---|
| Commitů | 74 za 9 aktivních dní (18.–28. 7. 2026) | ~8 commitů/den — malé, časté přírůstky |
| LOC `src/` | 5 207 | |
| LOC `tests/` | 1 271 (~24 % poměr k src) | Solidní na solo projekt tohoto stáří |
| LOC `scripts/` (verifikační/diagnostické) | 3 221 | Neobvykle vysoké — silný sklon k ručnímu ověřování |
| LOC `docs/*.md` | 7 940 | **Převyšuje objem produkčního kódu** |
| CI | lint + type-check + test + coverage, na push i PR | Standard, který řada juniorních týmů nemá |
| Test výsledek | 68/68 zelených (nezávisle ověřeno) | |

**Co je skutečně originální:** pole `it_analogy` je napevno zabudované do datového schématu `PatternDef` (`models/pattern.py`), ne jen prózy v komentáři — každý pattern je strukturně nucen mít IT/DevOps analogii ("git push --force", "Silencing an alert instead of fixing the root cause", "Deploying to prod on Friday after a perfect sprint"). To je nezvyklé designové rozhodnutí — málokterý chess-analytický nástroj by toto formalizoval jako first-class schema field místo volné poznámky. Funkčně to nic nevaliduje, ale je to konzistentní stylistický podpis napříč celým projektem (a je to přesně ta technika, o kterou jste mě v zadání požádal pro tento report — už je v kódu, jen jsem ji zrcadlil).

**Co je koncepčně ambiciózní, ale implementačně nedotažené:** "Lossy Compression Principle" jako validační filosofie patternů je zajímavá myšlenka — ale D2 ukazuje, že current implementace ji nedodává. Je to typický případ *koncept napřed, implementace pozadu* — ne špatný nápad, ale nedokončený.

**Co signalizuje mezeru:** Naprostá většina nálezů (W1, W2, W5, D1, D3, D4) spadá do jedné kategorie — **absence sdíleného, vynucovaného datového kontraktu** pro `evidence`/`affected_games`. Každý z 14 detektorů si evidence dict staví ručně ad-hoc, místo aby všech 14 sdílelo jeden `Evidence`-typ (dataclass/TypedDict) s vynucenými poli. Toto je klasická mezera profilu "silný samouk bez formálních code review od seniorů" — ne chyba v architektonickém myšlení (`detect_all()`, dvouvrstvá validace, CI, testovací kontrakt — to všechno jsou správné instinkty), ale chybějící návyk "definuj kontrakt jednou, vynuť ho typovým systémem" mezera, kterou obvykle zachytí PR review, ne self-review.

---

## 8. Iterační roadmapa s EROI

**EROI = Impact (1–10) ÷ Effort (odhad v hodinách).** Vyšší číslo = lepší poměr přínos/čas. Řazeno sestupně dle EROI v rámci každé priority. Cíleno výhradně na funkční server + odolný Chess Patterns modul — žádné širší refaktory mimo tento scope.

### P0 — musí (integrita dat + prevence pádu) — celkem ~4,5 h

- **[EROI 18]** Přidat `"game_ids": list(m.game_ids)` do `entry` v `match_patterns.py:155-165` → Effort 0,5 h / Impact 9 — přímá oprava kořenové příčiny halucinace (W1)
- **[EROI 18]** Obalit `_detect_s` (řádek 497) stejným guardem jako `_detect_n` (`if m.fen:` + `try/except (ValueError, IndexError)`) → Effort 0,5 h / Impact 9 — zastaví pád celé dávky (D1)
- **[EROI 5,3]** Přidat regresní testy: formát `affected_games` na úrovni evidence + přítomnost `game_ids` na úrovni tool response → Effort 1,5 h / Impact 8 — bez toho se W1/D1 mohou tiše vrátit při dalším refaktoru
- **[EROI 4]** Sjednotit `evidence["affected_games"]` na `list[str]` napříč všemi 14 detektory (W2/W5) → Effort 2 h / Impact 8

### P1 — mělo by (sémantická integrita) — celkem ~5,5 h

- **[EROI 8]** Zapracovat `resource_key`/URI do vraceného artefaktu + logovat/raisovat při selhání `_save_store()` (D6) → Effort 0,5 h / Impact 4
- **[EROI 6]** `"K" not in m.move_san` do `_detect_j` (W3) + pozitivní/negativní test → Effort 1 h / Impact 6
- **[EROI 6]** Zavolat `assert_valid_artifact()` místo tichého `_sanity_warnings`, nebo warning aspoň zvýraznit v odpovědi (D5) → Effort 1 h / Impact 6
- **[EROI 4,7]** Opravit `compute_compression()` — použít reálnou proměnnou (např. počet klíčů v evidence dictu, nebo frekvenci vs. velikost datasetu), ne konstantní `len(evidence_list)` (D2) → Effort 1,5 h / Impact 7
- **[EROI 3,5]** Přepracovat confidence vzorec pro `min_occurrences=1` patterny — např. minimální confidence floor odvozený od severity, ne čistě frekvenční poměr (D3) → Effort 2 h / Impact 7

### P2 — pěkné mít (dokumentace/kosmetika) — celkem ~1 h

- **[EROI 3]** Zdokumentovat/deduplikovat překryv S↔J v docstringu (W4) → Effort 1 h / Impact 3
- **[EROI ~1]** Opravit počet nástrojů v README (11→12) (D7) → Effort 5 min / Impact 1

**Doporučení k rozsahu:** P0 (4,5 h) uzavírá přesně tu třídu chyb, která způsobila incident 28. 7. 2026, plus nově objevený crash vektor. To je jediná část, kterou bych označil za nutnou před dalším produkčním použitím nástroje. P1/P2 jsou zlepšení kvality, ne blokátory.

---

## Příloha: Kompetenční pozice autora

*Stručné, kvalifikované posouzení — repozitář jako proxy metrika, ověřeno tímto auditem, ne převzato bez kontroly.*

**Signály podporující vysoké umístění pro <1 rok zkušenosti:** CI s lintem, typovou kontrolou, testy a coverage od raných fází; 68/68 zelených testů; dokumentace (7 940 řádků) objemem převyšuje produkční kód (5 207 řádků) — u samouka bez formálního vedení neobvyklé, čitelně navázané na předchozí manufakturní/procesní disciplínu; existující vlastní adversariální audit kultura (dva předchozí `AUDIT_REPORT` dokumenty, formální RCA dokument po reálném incidentu, meta-audit plánovací dokument) — tento report je fakticky třetí vrstvou rekurzivního auditu, který si autor sám zorganizoval, ne první.

**Signály konzistentní s < 1 rokem praxe (ne s nezralostí architektury, ale s chybějícím code review):** Všech 12 nálezů kromě D6/D7 sdílí jeden kořen — chybějící vynucený datový kontrakt pro evidence. To je typická mezera profilu "silný self-taught bez seniorního PR review", ne mezera v systémovém myšlení. Dvouvrstvá validace, `detect_all()` abstrakce, i sama existence kompresní filosofie ukazují záměr správným směrem — chybí jen návyk "definuj typ jednou, vynuť ho", který se typicky učí od zkušenějšího kolegy v code review, ne samostudiem.

**Verdikt:** Repozitář jako proxy metrika obstojí — tempo (74 commitů/9 dní), hloubka sebereflexe (dokumentační objem, RCA kultura) a kvalita CI baseline odpovídají silnému horní pásmu pro vývojáře s < 6 měsíci formální praxe v Pythonu/Gitu. Konkrétní nálezy tohoto auditu jsou přesně ty, které by odhalilo jedno kolo seniorního code review — což potvrzuje tezi "chybí mentoring/review vrstva", ne tezi "chybí inženýrské myšlení".

---

## Metodologická poznámka

Tento audit nebyl pouhou parafrází dodaného `PATTERN_DETECTOR_AUDIT_INJECT.md`. Postup:

1. `git clone` skutečného repozitáře (`outpost2026/lichess-mcp-analyzer`, commit `0f4eef5`) — `github.com` a `codeload.github.com` jsou v tomto prostředí povolené domény.
2. Přečten kompletní zdrojový kód všech auditovaných souborů (ne jen úryvky z injektovaného kontextu).
3. Nainstalovány závislosti do izolovaného venv, spuštěna reálná testovací sada (68/68 passed) stejným příkazem jako CI.
4. Napsány a spuštěny tři samostatné reprodukční skripty (W1, W3, D1) proti živé `PatternDetector` třídě — výstupy jsou vloženy do tohoto reportu doslovně z konzole, ne přeformulované.
5. Numericky ověřen D2 (konstantní compression_ratio) a D3 (confidence @ N=1/35) skutečným voláním `compute_compression()` a confidenčních vzorců s reálnými parametry.
6. `assert_valid_artifact` ověřeno jako nikde nevolané přes `grep -rn` na `src/` i `tests/`.

CI stav na GitHubu (Actions API) nebyl nezávisle ověřen kvůli rate-limitu na neautentizovaném API volání — nahrazeno lokální reprodukcí identického test příkazu.
