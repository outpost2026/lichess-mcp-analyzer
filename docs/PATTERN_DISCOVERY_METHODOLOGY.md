---
title: Metodologie pattern discovery a detection
date: 2026-11-14
verze: 1.7
status: ZÁVAZNÝ METODOLOGICKÝ ARTEFAKT
účel: Popsat, jak vznikají a jak se ověřují kandidátní chess patterny; porovnat metodologii s pattern discovery v jiných doménách; vyhodnotit originalitu a efektivitu.
návaznost: CANDIDATE_PATTERNS_2026-11-12.md, AUDIT_INTEGRATION_2026-11-13.md, REFACTOR_PLAN_2026-11-11.md, PLAN_SINGLE_GAME_CALIBRATION_2026-11-07.md, MIKOLOV_KOMPRESE_V_PATTERN_ARCHITEKTURE.md, COMPACT_JSON_FOR_LLM.md, DEEP_DIVE_SINGLE_GAME_PATTERNS_2026-08-02.md
změny_1_1: Univerza přejmenována na obsahové názvy (§2.1) a sjednocena s měřicím appendixem; přidána identita datasetu (§2.1.1).
změny_1_2: P1 — tři dimenze confidence (§2.4), coverage validator místo falešného MDL (§11.1), `strength` jako ordinální pole (§11.2); roadmap P1 rows aktualizovány.
změny_1_3: P1 uzavřeno — schema 1.3 s Wilson CI a podmíněným liftem (§5.2), pravidlo „lift se nevymýšlí“.
změny_1_4: P2 krok B — skutečná dvoučlenná MDL (`services/mdl.py`, §11.1) jako měřicí vrstva; naměřené gainy proxy mechanismů; `non_estimable` pro hraniční MLE.
změny_1_5: P2 krok C — split-half stabilita a časový drift (§5.5, §11.5); Page-Hinkley zamítnut pro nekalibrovatelnost `delta`/`lambda`, nahrazen dvouvýběrovým z-testem na chronologických polovinách; schema 1.4, `PatternMatch.stability`; roadmap P2 split-half uzavřen.
změny_1_6: Integrace auditu 2026-11-13 — hranice single-game (event, 1.2/2.1) vs cross-game (pattern, 1.4) v §1.1.1; důkazová úroveň opravena v §2.5; nová slabina §11.7 (jednoperspektivní single-game); paralelní track §12.2 s odkazem na `AUDIT_INTEGRATION_2026-11-13.md`. Cross-game kontrakty se nemění.
změny_1_7: Tier 3 hotov — `game_full` 1.0 implementován (`services/timeline.py`, `GAME_FULL_1.0.md`); §11.7 fix označen jako hotový, `interaction` events zůstávají neimplementované (T3.3 čeká na measurement spec). Cross-game kontrakty se nemění.
---

## 0. TL;DR

1. Pattern není „zajímavý tah“. Pattern je **podmínka na pozici a rozhodnutí**, která má (a) měřený support, (b) měřený kontrast proti dobrým tahům, (c) stabilitu, (d) deterministickou detekci a (e) kalibrovanou sílu. Bez (b) se jedná o popis, ne o pattern.
2. Discovery není hledání nových ID. Discovery je **falsifikační loop**: kandidát → měření na pojmenovaných univerzech (§2.1) → FP strop → taxonomie → implementační gate → monitoring. Většina kandidátů má skončit zamítnuta; to je úspěch procesu, ne selhání.
3. Současný systém má **15 definic v baseline knihovně** (A, B, C, G, I, I2, J, N, O, P, Q, Q1, Q2, R, S) a **6 per-move eventů** (B, C, J, R, S, T); B/C/J/R/S jsou sdílené, T je pouze per-move. Z 15 definic má **14 automatický detektor**; `I` (bait trap) je záměrně `manual_only` koncept a v runtime se nevydává. Per-move eventy nejsou patterny v cross-game smyslu: nemají jmenovatel ani kontrast.
4. Měřené pokrytí na cache (259 dedup her, 2137 flagged tahů): **375 matched (17,5 %), 1762 unclassified (82,5 %)**. To není bug, to je kalibrovaná hranice znalosti. Nízké pokrytí je cenou za to, že si systém nevymýšlí mechanismus.
5. Originalita je **v kombinaci kontraktů**, ne v algoritmech. Jednotlivé komponenty (frekvence, lift, MDL, conformance, motif discovery) mají prior art. Kombinace „explicitní unclassified + FP strop na dobrých tazích + dual single/cross-game kontrakt + deterministická evidence chain“ v publikovaných chess nástrojích doložena není (P~0,75; absence důkazu, ne důkaz absence).
6. Efektivita: **vysoká explanační, nízká discovery výtěžnost, neprokázaná diskriminační validita**. `compressibility_validator` je od 2026-11-13 **coverage validator** (`coverage_score`, `support`), ne MDL; `confidence` je jen alias `strength` a nikde se nečte jako pravděpodobnost. Skutečná dvoučlenná MDL je od 2026-11-13 implementovaná v měřicí vrstvě (§11.1); kalibrace zůstává P2.
7. Stabilita je od 2026-11-13 **měřená, ne tvrzená**: split-half s deterministickým hashem a časový drift na chronologických polovinách (§5.5). `unstable` je příznak k prošetření, ne verdikt; když není co testovat, je `null`, nikdy `false`.
8. Hranice produktu je od 2026-11-13 explicitní: **single-game vrstva vydává eventy jedné perspektivy** (detailed 1.2 / compact 2.1), **cross-game vrstva vydává patterny** (schema 1.4). Celopartiová timeline a dva pohledy jsou nový artefakt `game_full` 1.0, ne rozšíření 1.2/2.1 (§1.1.1, §11.7, §12.2).

---

## 1. Co je pattern a co není

### 1.1 Tři vrstvy

| Vrstva | Definice | Příklad | Jmenovatel | Čas |
|---|---|---|---|---|
| **Event** | Jednotlivé rozhodnutí s měřeným dopadem | `B` capture s cp_loss >= 100 | počet tahů | 1 tah |
| **Pattern** | Opakující se event s kontrastem proti referenci | „hráč grabuje materiál, když je v napětí“ | počet rozhodnutí / her | více her |
| **Lesson** | Pattern → příčina → trénink → měřený výsledek | „dril: napětí před grabem“ | počet tréninkových cyklů | týdny |

Současný systém je na úrovni **event + pattern**; lesson vrstva (tréninkový loop) zatím chybí. To je klíčové pro produktové hodnocení v §10.

#### 1.1.1 Dvě produktové schopnosti a jejich artefakty

Audit 2026-11-13 ukázal, že „pattern“ a „celá partie“ nejsou totéž. Kanonické rozdělení:

| Schopnost | Otázka | Vrstva | Artefakt | Perspektiva |
|---|---|---|---|---|
| **Player Behavior Analysis** | které chyby a mechanismy se u hráče opakují napříč hrami | pattern (E2–E3) | cross-game schema 1.4 | jedna barva hráče |
| **Full Game Dynamics** | jak se v jedné partii vyvíjela interakce obou hráčů | event + timeline | `game_full` 1.0 (implementováno 2026-11-14; `interaction` events ne) | obě, oddělené |

Single-game výstup dnes nese **eventy jedné perspektivy** (detailed 1.2 / compact 2.1). Cross-game výstup nese **patterny** (schema 1.4). `game_full` je nový aditivní artefakt, který obě schopnosti propojí, ale nesmí je slít: perspektivy zůstávají oddělené a do cohortu nikdy nevstupují obě (§11.7, D8 v `AUDIT_INTEGRATION_2026-11-13.md`).

### 1.2 Co pattern není

- Není to engine label (`blunder`, `mistake`, `inaccuracy`). Label je vstup, ne výstup.
- Není to jednorázová anomálie (viz `Z` — evidence gap).
- Není to LLM hypotéza bez měření (§6 v `CANDIDATE_PATTERNS_2026-11-12.md` je explicitně označena jako offline, ne runtime).
- Není to nový pattern ID bez taxonomie a FP kalibrace (rozhodnutí D4).

### 1.3 Proč je to doménově agnostické

Každý pattern discovery systém potřebuje stejnou kostru:

```
udalost -> token -> sekvence -> support -> kontrast -> stabilita -> model -> intervence
```

Chess je pouze konkrétní instance: token = (typ tahu, kontext pozice), sekvence = partie, kontrast = dobré tahy, intervence = trénink. Změna domény mění extrakci tokenů, ne logiku discovery. To je důvod, proč má smysl srovnávat s SPM, process miningem, motif discovery a anomaly detection (§7, §8).

---

## 2. Formální model důkazu

### 2.1 Univerza

Univerza mají **obsahové názvy**, ne indexy. Indexové zkratky (`U0/U1/U2`) jsou historické aliasy a v nových artefaktech se nepoužívají — dva dokumenty je dříve definovaly odlišně, což vyrobilo nekonzistentní čísla.

| Univerzum | Definice | Velikost (2026-11-12) | K čemu |
|---|---|---|---|
| **`cache_analyses_raw`** | každý soubor v `data/game_cache`, včetně duplicit hloubek | 282 analýz / 8 873 tahů | inventář a audit surových dat; **nikdy ne jmenovatel** |
| **`flagged_factsheets_dedup`** | blunder fact sheets dedup dle `game_id + color + ply`, vyhrává hlubší analýza | 880 sheetů (z 943) | měření mechanismu (E1) |
| **`all_moves_dedup`** | všechny tahy dedup dle `game_id + color`, na hru nejhlubší analýza | 8 109 tahů | **support** hráčových rate |
| **`good_moves_control`** | `all_moves_dedup` omezené na `classification == "best"` | 4 721 tahů | **FP strop** (kontrolní sada) |

Pravidla, která z toho plynou:

- **Support** patternu se počítá vždy z `all_moves_dedup` (ne z počtu her, ne z `cache_analyses_raw`).
- **FP strop** se počítá vždy z `good_moves_control`. „Všechny neflagged tahy“ je chybný jmenovatel: míchá `good` a `inaccuracy` a tím uměle snižuje FP.
- `flagged_factsheets_dedup` je jediné univerzum pro čtení mechanismu; obsahuje jen flagged tahy, takže nemá kontrast a **nesmí** sloužit jako support jmenovatel.
- Duplikáty hloubek nejsou data navíc. Dedup je `game_id + color + ply` pro tahy a `game_id + color` pro hru; bez něj 63 duplicitních sheetů zkreslí všechny poměry.

### 2.1.1 Identita datasetu

Každé měření musí publikovat `n_moves`, `n_games` a `dataset_sha256` (kanonický hash složení datasetu z `services/provenance.py`). Bez těchto tří hodnot není číslo reprodukovatelné: stejný lift na jiném datasetu je jiné tvrzení. Engine hloubka **není** součástí `dataset_sha256` — patří k analysis payloadu, ne k identitě datasetu.

Referenční naměřené hodnoty a jejich definice jsou v `docs/CANDIDATE_PATTERNS_2026-11-12.md` §1–2 (měřicí appendix této metodologie).

### 2.2 Veličiny

Pro kandidáta `k`, hráče `p`:

```
support(k)      = |{tahy v all_moves_dedup, kde k plati}| / |all_moves_dedup|
rate_flagged(k) = |{flagged tahy, kde k plati}| / |flagged tahy v all_moves_dedup|
rate_good(k)    = |{best tahy, kde k plati}| / |good_moves_control|
lift(k)         = rate_flagged(k) / rate_good(k)
fp_ceiling(k)   = rate_good(k)            # jak casto by vystrelil na dobrem tahu
N(k)            = pocet nezavislych pripadu (her, ne tahu)
```

`lift` je primární diskriminátor. `fp_ceiling` je primární guard. `N` je primární guard proti malému vzorku. `support` je hráčova rate a používá se pro prioritizaci lekce; pro diskriminaci je irelevantní, protože nemá kontrast.

Bez `good_moves_control` nelze odlišit „pattern“ od „běžná vlastnost pozice“. To je nejčastější chyba v pattern discovery obecně: systém najde vzorec, který je stejně častý u dobrých i špatných tahů.

### 2.3 Implementační gate (nové patterny)

| Podmínka | Threshold | Zdroj |
|---|---|---|
| Nezávislé případy | `N >= 30` | GT-070 / P54 |
| Kontrast | `lift >= 1.4` | GT-070 / P54 |
| Nezávislé analýzy | `>= 2` | GT-070 / P54 |
| FP strop na `good_moves_control` | musí být změřen a uveden | D4 |
| Taxonomie mechanismu | F1-F8/Z | `CANDIDATE_PATTERNS_2026-11-12.md` §4 |
| Deterministická detekce | bez LLM v runtime | REFACTOR_PLAN |

**Důležité rozlišení:** těchto `N >= 30` se týká **admission gate pro nové patterny**, ne runtime detekce. Runtime cross-game detektory mají `min_games = 3` a `min_occurrences = 2` (`models/pattern.py:55-56`). To je záměrné: runtime má vysoký recall, admission má vysokou precision. Obě hranice se nesmí zaměňovat.

### 2.4 Confidence — tři dimenze (P1 implementováno)

`PatternMatch` už nemá jedno číslo vydávané za pravděpodobnost. Má tři oddělené dimenze:

| Pole | Význam | Škála | Kalibrace |
|---|---|---|---|
| `strength` | ordinální síla detektoru (jak silně podmínka platí) | 0..1 | ne, ordinální |
| `support` | podíl analyzovaných her, ve kterých pattern nastal | 0..1 | měřený podíl |
| `hypothesis_confidence` | důvěra, že uvedený mechanismus je správný | 0..1 nebo `None` | `None` = nekalibrováno |

`confidence` zůstává **jen jako alias** `strength` pro starší skripty a 1.2 payload; v reportu se nesmí číst jako pravděpodobnost. `strength` se počítá v detektoru (ad hoc vzorce typu `min(pin_events / games * 0.8, 0.75)`) a **nikdy** ho nepřepisuje kompresní validátor.

Bývalý `compressibility_validator` je nyní **coverage validator**. Počítá:

```
compression_ratio = total_moves / (10 + 2 * evidence_count)
coverage_score    = min(compression_ratio / 10, 1)
support           = games_with_pattern / total_games
```

`coverage_score` je ordinální **proxy pokrytí**, ne MDL a ne pravděpodobnost. Při velkém korpusu saturuje (18 000 tahů / 110 = 164 → 1,0), takže měří velikost korpusu; proto je z reportu oddělený a `strength` neovlivňuje. Skutečné dvoučlenné MDL (`L(model) + L(data | model)`) zůstává P2.

### 2.5 Důkazová hierarchie

| Úroveň | Důkaz | Co dovoluje tvrdit |
|---|---|---|
| **E0** | event bez kontextu | „tah X měl cp_loss Y“ |
| **E1** | event + position facts (SAN, FEN, board_facts) | „tah X byl capture v napětí“ |
| **E2** | E1 + kontrast `rate_flagged` vs `rate_good` | „jev je častější u špatných tahů, lift Z“ |
| **E3** | E2 + split-half / časová stabilita | „jev je stabilní, ne artefakt okna“ |
| **E4** | E3 + out-of-sample hráč / stylometrie | „jev diskriminuje hráče“ |
| **E5** | E4 + intervenční test | „trénink jevu zlepšuje výsledek“ |

Současný stav: **cross-game korpus je na E1–E3** (E2 kontrast se měří při admission, E3 split-half a drift jsou implementované od 2026-11-13), **single-game výstup zůstává na E1** — jedna hra nemá kontrast ani stabilitu, takže její eventy nesmí být prezentovány jako potvrzený pattern. E1–E3 stačí na coaching report; na produktové tvrzení „toto je váš hlavní problém“ nestačí. E4 (external validity) a E5 (intervence) zůstávají otevřené.

---

## 3. Discovery loop

Discovery je osmi-krokový deterministický proces. Každý krok má vstup, výstup a gate; selhání gate znamená STOP, ne „doladíme to později“.

| # | Krok | Vstup | Výstup | Gate |
|---|---|---|---|---|
| 1 | **Inventory** | cache her, engine lines | seznam kritických momentů | dedup `game_id + color + ply` |
| 2 | **Proxy extrakce** | FEN, SAN, board_facts | free_capture_after, missed_capture, hanging_piece | deterministické predikáty |
| 3 | **Kandidát** | shluky proxy + digest | hypotéza mechanismu (F1-F8) | musí být falsifikovatelná |
| 4 | **Měření kontrastu** | kandidát + `all_moves_dedup` + `good_moves_control` | support, lift, fp_ceiling, N | `lift >= 1.4`, `N >= 30` |
| 5 | **FP kalibrace** | `good_moves_control` | FP strop | pokud `lift < 1.4` → ZAMÍTNOUT |
| 6 | **Taxonomie** | mechanismus | zařazení F1-F8/Z | žádný nový mechanismus bez definice |
| 7 | **Implementace** | spec + testy | detektor + schema | determinismus, unit testy, žádný LLM |
| 8 | **Monitoring** | produkce | drift, coverage, FP | pokles liftu → rekalibrace |

### 3.1 Proč je krok 5 nekompromisní

Příklad z reálných dat (`CANDIDATE_PATTERNS_2026-11-12.md` §5):

| Kandidát | rate_flagged | rate_good | Lift | Verdikt |
|---|---|---|---|---|
| K1 `loose_piece` | 7,7 % | 7,4 % | 1,04 | **zamítnuto** |
| K3 `unaddressed_check` | dobrý lift | - | - | kandidát, malý N |
| K5 `wrong_recapture` | nejčistší mechanika | - | - | kandidát |

K1 je učebnice discovery disciplíny: intuitivně „volná figura = příčina“ je empiricky prázdná. Bez `good_moves_control` by se K1 stal patternem a škodil by každému hráči, který má volnou figuru bez následku.

### 3.2 Proč většina kandidátů musí selhat

Pokud discovery loop generuje mnoho nových patternů, je to signál, že gate je příliš volný. Očekávaný výstup ze 40 kritických momentů je **1-3 implementované patterny**, ne 10. Zbytek je `unclassified` s důvodem — a to je informace, ne dluh.

---

## 4. Detection architecture

### 4.1 Tři vrstvy a jejich gates

| Vrstva | Funkce | Vstup | Výstup | Gate |
|---|---|---|---|---|
| **Per-move event** | `per_move_patterns()` | jeden tah + `prev_move` + `in_check` | B, J, R, S, C, T | práh cp_loss / fáze / board_facts |
| **Single-game** | `scan_single_game()` | jedna `GameAnalysis` | flags + `by_ply` + `unclassified` | `scope=single_game` |
| **Cross-game** | `PatternDetector.detect_all()` | `list[GameAnalysis]` | `PatternMatch` | `min_games=3`, `min_occurrences=2` |

Klíčové pravidlo (REFACTOR_PLAN §P0-2): **BFS a single-game musí volat stejnou implementaci**. `per_move_patterns()` je jediný zdroj pravdy pro B/J/R/S/C/T. Dva výstupy jedné pipeline si nesmí odporovat.

Poznámka k pokrytí knihovny: `PatternLibrary` definuje 15 ID, ale `PatternDetector` má 14 `_detect_*` metod. Chybějící `I` není bug — je to `manual_only` koncept (bait trap), který nelze deterministicky detekovat bez inferenci záměru. `detect_all` ho proto tiše přeskakuje; to je správné chování, ale musí být dokumentované, aby nevznikl dojem, že pattern `I` je aktivní.

### 4.2 Proč cross-game detektory nesmí být „unlocked“ pro jednu hru

Cross-game otázky typu „hraji hůř proti anonymním soupeřům?“ nemají v jedné hře jmenovatel. Snížení `min_games` na 1 by vyrobilo statistický nesmysl. Proto single-game vrstva **používá jen per-move signály** a výsledek je označen `scope=single_game`.

### 4.3 `unclassified` kontrakt (D4)

Každý flagged tah, který nemá matched pattern, dostane **explicitní event**:

```
status: unclassified
reason: quiet_positional | forcing | capture | evidence_gap
```

Pravidla:

- `reason` popisuje **měřený tvar tahu**, nikdy netvrdí mechanismus.
- `evidence_gap` je jen pro tahy bez SAN / bez potřebného kontextu. Chybějící PV není `evidence_gap`; je to globální vlastnost cache a reportuje se separátně.
- `unclassified` není chyba. Je to **kalibrovaná hranice znalosti** a vstup pro další discovery iteraci.

### 4.4 Determinismus

- Žádný LLM v detection path.
- Každý flag musí být rekonstruovatelný z `(game_id, color, ply, depth)`.
- Stejný vstup → stejný výstup; žádná náhodná složka.
- Cache se deduplikuje přes `game_id + color + ply` (jinak 63 duplicate depth sheets zkreslí všechny poměry).

---

## 5. Měřicí protokol

### 5.1 Správné jmenovatele

| Metrika | Správný jmenovatel | Chybný jmenovatel |
|---|---|---|
| Support patternu | `all_moves_dedup` (všechna rozhodnutí) | počet her; `cache_analyses_raw` |
| FP strop | `good_moves_control` (`best` only) | všechny tahy; „všechny neflagged“ |
| Konverze na výsledek | hry s patternem vs bez | všechny hry |
| Stabilita | split-half / časové okno | celý korpus |
| Identita čísla | `n_moves` + `n_games` + `dataset_sha256` | jen počet her |

### 5.2 Interval spolehlivosti (implementováno, schema 1.3)

Každý podíl má Wilsonův interval, každý lift má Katzův log interval. Bez CI nelze odlišit „lift 1,4 na N=30“ od „lift 1,4 na N=3000“. V reportu stačí `rate [CI95]`, `lift [CI95]`, `N`.

Implementace (`services/statistics.py`, deterministická, bez simulace a bez scipy):

```
rate  = n_games / n_units                    # jednotka = hra, ne event
CI    = Wilson(n_games, n_units, z=1.96)     # vždy uvnitř [0, 1]
lift  = (k1/n1) / (k2/n2)                    # jen když existuje kontrolní skupina
CI    = exp(ln(lift) ± 1.96 * sqrt(1/k1 + 1/k2))   # Katz, Poissonova variance
```

Kontraktní pravidla:

- **`n_games`** = počet unikátních her s patternem, **`n_units`** = počet analyzovaných her. `frequency` zůstává detektor-specifická (eventy u B/J/N, hry u C/P/R/S) a **nikdy se nesmí použít jako N.
- **`lift` se nevymýšlí.** Runtime kontrolní skupinu mají jen `A` (anonymous vs named) a `G` (white vs black). Ostatní patterny nesou `lift = null` a `lift_unavailable_reason`; jejich lift se měří při admission gate (§2.3), ne při každém běhu.
- Nulový počet eventů v kontrastní skupině = lift není estimovatelný (žádná konečná log-variace), proto `null`, ne nekonečno.
- Validátor (`kb/schemas.py`) odmítne artefakt, kde `n_games > n_units`, kde point estimate leží mimo vlastní CI, nebo kde chybí `lift_unavailable_reason` u `lift = null`.

### 5.3 PV sparsity

Měřeno: **PV je přítomno jen u 12,9 % flagged tahů**. Důsledek:

- Mechanismy závislé na linii (F2, F3, F5) mají malý efektivní N.
- Nelze tvrdit „hráč nevyužil best“, pokud best není v cache.
- Každý report musí uvést `pv_coverage` jako globální metriku.

### 5.4 Proxy vs mechanismus

Proxy (`free_capture_after`, `missed_capture`, `hanging_piece`) je **jen generátor kandidátů**. Mechanismu se rovná až po kontrastu a kalibraci. V dokumentaci musí být vždy označeno, co je proxy a co je potvrzený mechanismus.

**Pravidlo po P2 kroku B:** proxy bez kladného `gain_bits` proti `good_moves_control` se nesmí stát patternem ani novým ID — ani když má lift > 1,3. Naměřeno: `hanging_piece` lift 1,33, ale MDL −2,86 bitů (§11.1).

### 5.5 Stabilita a drift (implementováno, schema 1.4)

Pattern, který existuje jen v jedné polovině korpusu, není vlastnost hráče, ale artefakt vzorku. Proto každý cross-game pattern nese blok `stability` se dvěma nezávislými testy:

| Test | Metoda | Jednotka | Práh |
|---|---|---|---|
| `half` | deterministická polovina podle parity `sha256(salt + game_id + color)` | hra | dvouvýběrový z-test, `abs(z) >= 1,96` |
| `drift` | chronologické poloviny podle data, řez na mediánu | hra | stejný z-test, `abs(z) >= 1,96` |

Kontraktní pravidla:

- **Determinismus.** Žádný `random` seed; členství v polovině závisí jen na hashi klíče, takže přidání hry nepřesune ostatní hry a report je reprodukovatelný bez uloženého stavu.
- **Jednotka = hra (`game_id`),** stejná jako `n_games`. Když cache obsahuje tutéž hru analyzovanou za oba hráče, počítá se jednou.
- **`unstable` je jen `true`/`false`/`null`.** `true` nastane, jen když zabere estimovatelný sub-test. Když ani jeden sub-test není estimovatelný (málo her, málo datovaných her, nulová pooled variance), je `null` — nikdy `false`, protože „neměřeno“ není „stabilní“.
- **Nedatované hry se z driftu vyřazují,** nikdy se neřadí doprostřed. Počet je v `drift.n_dated`.
- **`cosine` je jen tvar profilu.** Při několika málo nezáporných dimenzích je blízko 1, kdykoli se v obou polovinách vyskytují stejné patterny; diskriminační je per-pattern z-test, ne cosine.
- **Family-wise error není kontrolován.** Dva testy na pattern znamenají, že při 24 testech a `alpha = 0,05` čekáme ~1 falešný poplach. `unstable` je proto příznak k prošetření, ne verdikt o existenci patternu.
- **Drift nemusí být hráč.** Když korpus míchá více hráčů nebo obě barvy, změna mezi érami může odrážet složení korpusu, ne vývoj hráče. Report musí uvést, z čeho je korpus složen (§2.1.1), jinak je drift neinterpretovatelný.

Proč ne Page-Hinkley: jeho dvě konstanty (`delta` tolerance, `lambda` alarm) nelze zvolit bez ladění na datech, což tento projekt zakazuje (§3.1, D4). Dvouvýběrový z-test na chronologických polovinách nepotřebuje žádnou novou konstantu — znovu použije `Z95` — a efekt (`delta`) reportuje, místo aby ho předpokládal. Vícenásobný scan s Bonferroniho korekcí je pozdější rozšíření, ne podmínka.

---

## 6. Současný stav měření

Dataset: 259 dedup her / 2137 flagged tahů (`all_moves_dedup` flagged subset). Čísla v této sekci jsou z jiného datasetu než měřicí appendix `CANDIDATE_PATTERNS_2026-11-12.md` (259 vs 282 analyzovaných souborů) — proto musí každý report nést `dataset_sha256` (§2.1.1).

| Metrika | Hodnota | Interpretace |
|---|---|---|
| Matched | 375 (17,5 %) | patterny pokrývají minoritu |
| Unclassified | 1762 (82,5 %) | dominantní stav je „nevíme“ |
| Blunder matched | 124 / 220 (56,4 %) | nejvyšší signál |
| `quiet_positional` | 1523 | jádro problému: tiché poziční ztráty |
| `forcing` | 148 | šach/forcing bez zisku |
| `capture` | 91 | capture bez matched mechanismu |
| PV coverage | 12,9 % | limituje mechanistické závěry |

**Interpretace (P>0,9):** systém je konzervativní a auditovatelný. **Interpretace (P>0,8):** 82,5 % unclassified je produktová mezera, ne jen epistemická ctnost. Pokud se nepodaří snížit pod ~60 % bez poklesu precision, coaching hodnota zůstane nízká.

**Co NENÍ cíl:** zvýšit matched na 50 % uvolněním gate. Cíl je zvýšit **kalibrovaný lift na held-out hrách**, i kdyby matched zůstal 20 %.

---

## 7. Pattern vector: jak to dělají jiné domény

„Pattern vector“ = jak je vzorec reprezentován jako vektor, který lze porovnávat, agregovat a sledovat v čase. Šest typů reprezentace:

| Typ | Domény | Reprezentace | Metrika | Co si brát |
|---|---|---|---|---|
| **Support vector** | SPM, association rules | one-hot / count itemsetu | support, confidence, lift | kontrast a minimální support |
| **Alignment vector** | process mining | edit distance trace vs model | fitness, precision | model musí mít i „precision“, ne jen coverage |
| **Distance vector** | time series (matrix profile) | vzdálenost k nejbližšímu sousedovi | z-normalizovaná euklidovská | parameter-free, exact, reusable |
| **Score vector** | anomaly detection | odchylka od modelu normality | anomaly score + threshold | threshold musí být kalibrovaný, ne ad hoc |
| **Graph vector** | causal discovery | adjacency / intervention | PC, GES, NOTEARS | asociace != kauzalita; nutná intervence |
| **Embedding** | NLP, chess stylometry | distribuční vektor | cosine, few-shot | identita hráče je testovatelná |

### 7.1 Co je v těchto doménách standardem

- **SPM**: `support` + `lift` + closed/maximal patterns; algoritmy GSP, SPADE, PrefixSpan, FreeSpan. Gap constraints pro časovou blízkost. (Wikipedia: Sequential pattern mining; survey arXiv:1805.10515.)
- **Process mining**: conformance checking porovnává model s event logem; kvalita má čtyři dimenze — fitness, precision, generalization, simplicity. Koncept drift je první třída problému, ne výjimka. (arXiv:2112.02000, 2310.15826.)
- **Time series**: matrix profile je „computed-once-use-many-times“ struktura pro motif/discord/shapelet discovery; exact a parameter-free. (arXiv:1811.03064.)
- **Anomaly detection**: point / contextual / collective; většina metod vrací spojité skóre, binární rozhodnutí je až threshold. (Chandola 2009; Wikipedia.)
- **MDL**: nejlepší model je ten, který nejkratší popíše data; MDL je aplikace Occamovy břitvy a je rozšiřitelné na sekvenční predikci. (Wikipedia: MDL, Kolmogorov complexity.)
- **Chess**: behavioral stylometry identifikuje hráče z tahů s 98% accuracy na 100 hrách (arXiv:2208.01366); Maia/Maia4All modelují individuální styl s málo daty (arXiv:2507.21488); vnímání „brilliant“ tahu není jen engine best (arXiv:2406.11895).

### 7.2 Náš návrh vektoru hráče

Pro hráče `p` a okno `W`:

```
r_i   = e_i / d                    # rate patternu i na rozhodnuti
b_i   = referencni rate (rating band, time control)
l_i   = r_i / b_i                  # lift
ci_i  = Wilson(r_i, d)
phase = [r_i^opening, r_i^middlegame, r_i^endgame]
color = [r_i^white, r_i^black]
clock = [r_i^low_time, r_i^normal]
T_ij  = P(pattern j | pattern i do k ply)   # sekvencni prechod
H     = entropy(T)                          # rozmanitost chovani
stab  = cosine(v_first_half, v_second_half)
drift = |v_window1 - v_window2|             # detekce zmeny
out   = P(win | pattern i) - P(win | no i)  # rizikovy rozdil
```

Vektor:

```
v_p = [r_i, log l_i, ci_i, phase, color, clock, H, stab, drift, out]
```

Použití:

1. **Similarita hráčů** — „hráči jako vy mají tento pattern silnější“.
2. **Drift monitoring** — změna `v_p` v čase je signál zlepšení nebo regrese.
3. **Externí validita** — pokud patterny nesou identitu, `v_p` musí diskriminovat hráče (stylometrie).
4. **Prioritizace lekcí** — lekce pro pattern s vysokým `r_i`, vysokým `out` a vysokým `drift`.

Tento vektor **není implementován**. Je to návrh datového kontraktu pro P7 (§12).

---

## 8. Cross-domain srovnání metodologie

Skóre 0-2 na osu (0 = chybí, 1 = částečně, 2 = silné). **Kvalitativní rating autora, P~0,6; účel je orientace, ne měření.**

| Metodologie | Support | FP kontrola | Generalizace | Drift | Vysvětlitelnost | Komprese | Součet |
|---|---|---|---|---|---|---|---|
| Naše (chess event+pattern) | 2 | 2 | 1 | 0 | 2 | 1 | **8** |
| Sequential pattern mining | 2 | 0 | 1 | 0 | 0 | 0 | 3 |
| Process mining / conformance | 2 | 1 | 1 | 2 | 2 | 1 | **9** |
| Matrix profile / motif | 2 | 1 | 2 | 1 | 0 | 2 | **8** |
| Anomaly detection + drift | 1 | 2 | 2 | 2 | 0 | 1 | **8** |
| Causal discovery | 1 | 2 | 2 | 1 | 2 | 1 | **9** |
| Behavioral stylometry | 1 | 2 | 2 | 0 | 0 | 1 | 6 |

### 8.1 Co z tabulky plyne

- Naše metodologie je **nadprůměrná v kontrole FP a vysvětlitelnosti**, podprůměrná v generalizaci a chybí jí drift úplně.
- Process mining a causal discovery jsou lepší v tom, co nám chybí: **model + precision + drift + intervence**.
- SPM je nejbližší algoritmicky, ale nemá kontrast — a přesně proto by samostatně nestačilo.
- Matrix profile je nejlepší v **parameter-free** discovery; to je inspirace pro snížení prahu při nových patternách.

### 8.2 Dvě chybějící dimenze

1. **Precision modelu**: kolik tahů model *dovoluje*, ne jen kolik jich vysvětlí. Naše `unclassified` je fitness, ale precision neměříme.
2. **Drift**: hráč se mění. Pattern z ledna nemusí platit v červnu. Bez drift detekce reportuje systém stále stejnou lekci.

---

## 9. Originalita

### 9.1 Co není originální (P>0,9)

| Komponenta | Prior art |
|---|---|
| Frekvenční patterny hráče | Lichess Insights, Chess.com Insights, Aimchess weakness reports (veřejně dokumentované feature sety) |
| Per-move blunder taxonomie | běžná engine/coaching praxe |
| Lift / kontrast | SPM, association rules |
| Komprese jako validita | MDL, Kolmogorov, Mikolov |
| Pattern language (problem-context-solution) | Alexander 1977 |
| Individuální styl hráče | behavioral stylometry (2022), Maia (2020+), Maia4All (2025) |
| „Brilliant“ není jen best | arXiv:2406.11895 |

### 9.2 Co je originální v kombinaci (P~0,75)

1. **`unclassified` jako first-class výstup** s důvodem vázaným na měřený tvar tahu. Většina nástrojů buď labeluje, nebo mlčí; málokdo publikuje „nevíme“ jako kontrakt.
2. **FP strop měřený na dobrých tazích** jako admission gate. Běžný přístup měří jen precision na flagged tazích.
3. **Dual kontrakt single-game vs cross-game** se sdíleným jedním zdrojem pravdy (`per_move_patterns`). Zabránuje tomu, aby dva výstupy stejné pipeline odporovaly.
4. **Deterministická evidence chain** od SAN/FEN/engine line k lekci, bez LLM v detection path.
5. **Explicitní separace event / pattern / lesson** a odmítnutí nového ID bez taxonomie.

**Kalibrace:** P~0,75, že tuto kombinaci (1)+(2)+(4) nepublikoval žádný chess nástroj. Je to absence důkazu v dostupných zdrojích, ne důkaz absence. Před produktovým tvrzením „unikátní“ je nutný patent/competitive scan (P7).

### 9.3 Verdikt

Metodologie je **epistemicky nadstandardní, algoritmicky neoriginální**. To je dobrá kombinace: algoritmy jsou komodita, kontrakt je obranyschopný. Riziko je, že originalita je „jen“ v dokumentaci a ne v měřeném výsledku.

---

## 10. Efektivita

| Dimenze | Hodnocení | Důkaz |
|---|---|---|
| **Explanace** | vysoká | 375 matched eventů s kontextem; každý auditovatelný |
| **Discovery výtěžnost** | nízká | 17,5 % matched; 82,5 % unclassified |
| **Precision** | dobrá u matched | blunder matched 56,4 %; žádný pattern bez `good_moves_control` |
| **Generalizace** | neprokázaná | žádný held-out test, žádná stylometrie |
| **Stabilita** | částečně prokázaná | split-half bez rozdílu (max `abs(z) = 1,58`, N=2), cosine 0,9962; drift: 4 příznaky z 24 testů, Bonferroni přežívá jen `B` (§11.5) |
| **Actionability** | střední | pattern → mitigation text, chybí tréninkový loop |
| **Škálovatelnost** | dobrá | determinismus, cache, 2s runtime |

### 10.1 Kde systém funguje

- Konkrétní coaching report pro jednoho hráče: patterny jsou čitelné a obhajitelné.
- Ochrana proti halucinaci: `unclassified` a `evidence_gap` zabraňují vymyšlenému mechanismu.
- Audit: každý závěr má `game_id + ply + cp_loss`.

### 10.2 Kde systém nefunguje

- **Tiché poziční ztráty** (1523 případů) — chybí poziční featury, které by je rozlišily.
- **Sekvence** — patterny jsou nezávislé; systém nevidí „F4 → F1 do 3 ply“.
- **Změna v čase** — chybí drift; hráč dostává stejnou lekci i po zlepšení.
- **Kauzalita** — lift není kauzalita; tréninkový efekt není změřen.

### 10.3 Verdikt

**Efektivita je asymetrická:** vysoká v tom, co systém tvrdí; nízká v tom, kolik toho pokryje. Pro coaching MVP to stačí. Pro „standalone chess-coaching SW“ to nestačí, dokud se neuzavře lesson loop a nezměří se generalizace.

---

## 11. Kritické slabiny a jejich dopad

### 11.1 `compressibility_validator` není MDL (P1 — OPRAVENO přejmenováním)

`compression_ratio = total_moves / (10 + 2 * evidence_count)` roste s korpusem a saturuje. Původně tento poměr vstupoval do `confidence`, takže >= 0,5 dostal i slabý pattern.

**Stav 2026-11-13 (P1):** varianta (a) implementována. Validátor je `coverage validator`, výstup je `coverage_score` a `support`; `strength` detektoru se nemění.

**Stav 2026-11-13 (P2, krok B):** skutečná dvoučlenná MDL implementována v `services/mdl.py` — jako **měřicí vrstva**, ne v runtime `PatternMatch`. Důvod je strukturální: cross-game detektory nemají per-move applicability a A/G počítají Poissonovy eventy (`k > n`), takže binomický model na hrách by byl misspecifikovaný. MDL tedy vstupuje do admission gate, nikdy do `confidence` ani do `DETECTOR_VERSION`.

```
L(k, n | p) = log2 C(n, k) + n * H(p)          # přesná binomická délka kódu
L_null      = L(k1,n1 | p_pool) + L(k0,n0 | p_pool)
L_model     = L(k1,n1 | p1) + L(k0,n0 | p0) + 0.5 * log2(N)   # BIC/MDL cena za parametr
gain_bits   = L_null - L_model
```

Kontraktní pravidla:

- **`gain_bits` není lineární v N.** Combinatoriální člen roste ~`0.5*log2 n`, takže zdvojnásobení korpusu gain více než zdvojnásobí. Srovnávat napříč datasety lze jen `gain_per_unit = gain_bits / N`, a i to jen asymptoticky.
- **Nulový event ve skupině = MLE na hranici** (`p = 0` nebo `1`). Split pak kóduje skupinu nulovými bity a gain roste s `n` bez jakéhokoli důkazu. Takový řádek je `non_estimable`, nikdy „silný důkaz“ — stejné pravidlo jako u Katze.
- **Prahy 2 / 6 / 10 bitů jsou pevné** (analogie Kass–Raftery na škále `2 ln BF`), ne laděné na datech: `weak` / `moderate` / `strong`; pod 2 bity `single_rate`.

Měřeno 2026-11-13 (`scripts/measure_pattern_mdl.py`, 263 dedup her, 679 critical tahů vs 4752 `best`; obě skupiny ze stejného univerza `moves`, jednotka = tah):

| proxy | flagged | control | lift | `gain_bits` | `gain_per_unit` | verdikt |
|---|---|---|---|---|---|---|
| `free_capture_after` | 218/679 (32,1 %) | 836/4752 (17,6 %) | 1,82 | 45,48 | 0,0084 | strong |
| `hanging_piece` | 67/679 (9,9 %) | 353/4752 (7,4 %) | 1,33 | −2,86 | −0,0005 | single_rate |
| `missed_capture` | 7/679 (1,0 %) | 0/4752 | n/a | — | — | non_estimable |
| `missed_mate` | 0/679 | 0/4752 | n/a | — | — | non_estimable |
| ANY (union) | 222/679 (32,7 %) | 847/4752 (17,8 %) | 1,83 | 47,48 | 0,0087 | strong |

Interpretace: **`free_capture_after` je jediná board-derived proxy, která zaplatí za svůj parametr** (45,5 bitů, lift 1,82). `hanging_piece` má sice lift 1,33, ale split nezaplatí (−2,86 bitů) — jako samostatný klasifikátor nenese nic. `missed_capture`/`missed_mate` jsou na best-only controlu **strukturálně nulové** (odehraný tah == engine best), takže FP strop pro ně měřit nelze; to je vlastnost univerza, ne výsledek. 67,3 % critical tahů nemá žádnou board-derived proxy — prostor pro P4, ne důvod rozvolnit gate.

### 11.2 Confidence je ordinální, ne kalibrovaná (P1 — OPRAVENO rozdělením dimenzí)

Ad hoc vzorce (`cp/500`, `pin_events/games*0.8`) nejsou pravděpodobnosti. **Stav 2026-11-13:** `PatternMatch` má `strength` (ordinální), `support` (měřený podíl) a `hypothesis_confidence` (`None` = nekalibrováno); `confidence` je už jen alias `strength`. Kalibrace (isotonic regression) zůstává P2 — do té doby se `strength` nesmí číst jako pravděpodobnost.

### 11.3 Nezávislost patternů (P2, dopad: střední)

`per_move_patterns` vyhodnocuje tah izolovaně (s `prev_move` pouze pro C). Chybí sekvenční model. **Fix:** PrefixSpan/SPADE nad abecedou eventů s gap constraint `k <= 4`, closed patterns, support `>= 0.05`, lift `>= 1.4`, N `>= 30`. Teprve pak nový ID.

### 11.4 Chybí precision modelu (P2, dopad: střední)

Měříme fitness (kolik tahů vysvětlíme), ne precision (kolik tahů model dovoluje). **Fix:** doplnit `precision = |model ∩ log| / |model|` na úrovni typu pozice; reportovat spolu s `unclassified`.

### 11.5 Drift a generalizace (P2 krok C — split-half a drift hotové)

**Stav:** split-half i časový drift jsou od 2026-11-13 implementované (`services/stability.py`, §5.5, schema 1.4). Otevřená zůstává external validity (few-shot stylometrie, P6).

**Proč ne Page-Hinkley.** Původní plán (§12, verze 1.4) předpokládal Page-Hinkley/ADWIN. Zamítnuto: `delta` i `lambda` jsou konstanty, jejichž správná hodnota závisí na délce streamu a velikosti efektu; na ~107 post-referenčních hrách každá pevná dvojice buď alarmuje pod nulou (statistika roste o `delta` na vzorek), nebo nikdy nezabere. Zvolit je na tomto korpusu = ladit na datech, což §3.1 a D4 zakazují. Nahrazeno dvouvýběrovým z-testem na chronologických polovinách: žádná nová konstanta, stejný `Z95` práh jako split-half, efekt (`delta`) se reportuje.

**Naměřeno** (cache 2026-11-13: 270 analýz `(game_id, color)`, 215 unikátních her, 214 s parsovatelným datem):

| Test | Výsledek |
|---|---|
| Split-half (96 / 119 her, hash parita) | žádný pattern nepřekročil `abs(z) >= 1,96`; max `abs(z) = 1,58` u `S` (N=2, test nic neříká); cosine profilu 0,9962 |
| Drift (řez 2026-08-02, 107 / 107 her) | `B` 0,336 → 0,579 (`z = -3,57`), `Q2` 0,122 → 0,234 (`z = -2,15`), `Q` 0,103 → 0,215 (`z = -2,24`), `R` 0,112 → 0,215 (`z = -2,03`); ostatní `abs(z) < 1,2` |
| Bonferroni (24 testů, `alpha = 0,05`) | `abs(z) > 3,08`; přežívá jen `B` |

Interpretace, kterou report **nesmí** přeskočit:

- Split-half je čistý: profil patternů se mezi dvěma deterministickými polovinami neliší. To je slabý, ale skutečný test reprodukovatelnosti, ne důkaz validity.
- Cosine 0,9962 není silný důkaz. S 12 nezápornými dimenzemi je blízko 1, kdykoli se v obou polovinách vyskytují stejné patterny; diskriminační je z-test.
- Čtyři drift příznaky při 24 testech nejsou překvapení (`alpha = 0,05` → ~1 očekávaný falešný poplach), ale `B` vydrží i Bonferroniho korekci. To je hypotéza k prošetření, ne potvrzený posun.
- **Korpus míchá hráče i barvy.** 55 her je v cache za oba hráče a část korpusu tvoří soupeři, ne jen `Systeq`. Změna mezi érami proto může odrážet změnu složení korpusu, ne vývoj hráče. Bez homogenního korpusu (§2.1.1) je drift neinterpretovatelný; to je přesně úloha P6, ne důvod číslo smazat.

**Zbývá:** (a) homogenní korpus pro interpretovatelný drift, (b) few-shot identifikace hráče jako external validity test (P6), (c) případný multi-cut scan s Bonferroniho korekcí, pokud se ukáže, že jeden řez na mediánu nestačí.

### 11.6 PV sparsity (P1, dopad: střední)

12,9 % PV znamená, že mechanistické závěry mají malý N. **Fix:** rozšířit depth policy nebo explicitně reportovat `pv_coverage` u každého patternu; neimplikovat mechanismus z chybějící linie.

### 11.7 Single-game je jednoperspektivní (produktová mezera, dopad: vysoký)

**Nález (audit 2026-11-13, potvrzeno v kódu):** `collect_single_game` volá `analyze_pgn` **jednou**; `_run_analyze_pgn` vyhodnocuje jen pozice, kde `board.turn == player_side`, a tah soupeře pouze přehraje na desce. `GameAnalysis.moves` proto obsahuje **jen rozhodnutí vybraného hráče**, a to včetně ACPL, fázových statistik, BFS a single-game eventů.

**Důsledky, které nejsou kosmetické:**

| Místo | Co dnes vzniká | Proč to vadí |
|---|---|---|
| `context_window` v BFS | iteruje `analysis.moves` | ±3 ply jsou dva **vlastní** tahy, ne bezprostřední odpověď soupeře |
| `moves_total` | `len(moves)` = počet tahů hráče | název sugeruje celkovou délku partie |
| LLM prompt | dostane jen jednu perspektivu, max 10 chyb/typ, FEN `[:60]`, `bfs_json[:2000]` | nemůže doložit „hrozba → reakce → exploitace“ |
| Pattern C | předchozí rozhodnutí **téhož** hráče | interakce mezi barvami není modelovaná |
| `interaction` events | neexistují | dynamika partie není měřená |

**Proč to není bug:** kód dělá přesně to, co deklaruje (analýza jednoho hráče). Chybějící schopnost je **produktová mezera**, ne defekt — a proto nemá být označena jako P0 (viz `AUDIT_INTEGRATION_2026-11-13.md` §2).

**Fix (implementováno 2026-11-14, Tier 3):** merge vrstva `services/timeline.py` nad **existující dual cache**. Bílý běh už dnes vyhodnocuje bílé tahy a černý běh černé, takže každý ply je vyhodnocen právě jednou. Výsledkem je artefakt `game_full` 1.0: `plies[]` s `mover_color`, White POV eval a `source` pro obě barvy. Chybějící pohled nebo měření je `status="partial"` s pojmenovanou dírou, ne dopočtená hodnota. `interaction` events **nejsou** součástí 1.0 - nemají měřenou definici ani FP kalibraci (T3.3 čeká na spec, D4 gate). Kanonický tvar: `GAME_FULL_1.0.md`; rozhodnutí a acceptance: `AUDIT_INTEGRATION_2026-11-13.md` §6 (T3.0–T3.4).

**Co se nesmí stát:** oba pohledy nesmí vstoupit do jednoho `detect_all` cohortu — `n_units` by se zdvojnásobil a stejná hra by se počítala dvakrát (D8).

---

## 12. Roadmap s acceptance criteria

| ID | Akce | Acceptance |
|---|---|---|
| **P1** ✅ | Odstranit falešný MDL; přejmenovat `confidence` → `strength` | hotovo 2026-11-13: `coverage_score`/`support` jsou mimo `strength`, `confidence` je alias; žádný report netvrdí „pravděpodobnost“ |
| **P1** ✅ | Wilson CI + lift + N do každého `PatternMatch` | hotovo 2026-11-13: schema 1.3, `n_games`/`n_units`/`rate` + Wilson CI pro každý cross-game pattern; `lift` + Katz CI jen u A a G, ostatní s explicitním důvodem |
| **P2** ✅ | Skutečná dvoučlenná MDL (měřicí vrstva) | hotovo 2026-11-13: `services/mdl.py` (`log2 C(n,k) + n*H(p)`, BIC cena za parametr); `scripts/measure_pattern_mdl.py`; hraniční MLE = `non_estimable`; 31 testů |
| **P2** ✅ | Split-half + časová stabilita | hotovo 2026-11-13: `services/stability.py`, schema 1.4, `PatternMatch.stability`; hash split + drift na chronologických polovinách; `unstable = null` při nedostatku dat; naměřeno §11.5 |
| **P2** | Precision modelu | `precision` a `fitness` v reportu vedle `unclassified` |
| **P3** | Sekvenční vrstva (PrefixSpan, gap <= 4) | nový pattern jen při `N>=30`, `lift>=1.4`, 2 analýzy |
| **P4** | Poziční featury pro `quiet_positional` | snížení unclassified pod 70 % bez poklesu precision |
| **P5** | Lesson compiler + tréninkový loop | pattern → drill → měřený outcome; A/B design |
| **P6** | External validity (stylometrie) | few-shot identifikace hráče nad baseline |
| **P7** | Pattern vector store + drift dashboard | `v_p` per hráč, stabilní schema, competitive scan |
| **P8** ✅ | `game_full` 1.0 — timeline + dvě perspektivy | hotovo 2026-11-14: merge dvou `GameAnalysis` bez nového engine volání; každý ply jednou; White POV eval; `status="partial"` pro chybějící data; `interaction` zůstává mimo 1.0 (T3.3, D4 gate); viz `GAME_FULL_1.0.md` |

### 12.1 Pořadí je závazné

P1 je epistemická oprava, ne feature. Bez ní je každé další číslo nedůvěryhodné. P3 (sekvence) může bez P1 vyrobit více falešných patternů, ne lepší coaching.

**Stav 2026-11-12:** T1 provenance blok implementován (`services/provenance.py`, `PatternMatch.provenance`, `--json-out` v measurement skriptu, 8 testů). T2 (skutečná komprese) a T3 (drift guard) jsou další v pořadí — viz `CROSS_REPO_TRANSFER_MAP.md` §5.

**Stav 2026-11-13:** P1 uzavřeno. Univerza obsahově (§2.1), `phase_stats` = `effective_phase` + dva auditní řezy, `accuracy_method = internal_cp_linear`, confidence rozdělená na `strength`/`support`/`hypothesis_confidence`, falešný MDL přejmenován na `coverage_score`, schema 1.3 s Wilson CI a podmíněným liftem. Z P2 hotové kroky B (skutečná dvoučlenná MDL, §11.1) a C (split-half + drift, §5.5, §11.5, schema 1.4); otevřený zůstává precision model a external validity.

### 12.2 Paralelní track: single-game kontrakt

Tato roadmapa (P1–P8) je **cross-game discovery track**. Single-game větev má vlastní pořadí prací a vlastní rozhodovací artefakt:

- **Kanon:** `docs/AUDIT_INTEGRATION_2026-11-13.md` — rozhodnutí D6–D11, Tier 1 (defekty), Tier 2 (sémantika a evidence), Tier 3 (timeline a perspektivy), testovací matice a pravidla proti driftu.
- **Proč oddělené:** cross-game pattern a celopartiová timeline odpovídají na jiné otázky (§1.1.1) a mají jiný jmenovatel. Sloučení do jedné roadmapy by míchalo jednotku `game` s jednotkou `event`.
- **Vazba:** P8 (`game_full`) je průsečík obou tracků. Do cross-game statistiky vstupuje jen jedna perspektiva na `game_id` (D8); timeline sama o sobě není pattern a nesmí generovat nová ID bez D4 gate.
- **Co se nemění:** schéma 1.4, admission gate (`N >= 30`, `lift >= 1.4`, `>= 2` analýzy) ani `DETECTOR_VERSION` (mimo T1.4, kde J mění klasifikaci).

---

## 13. Závěry

1. **Discovery je falsifikace, ne generování.** Hodnota systému je v tom, co odmítne (K1) a co přizná jako neznámé (82,5 % unclassified).
2. **Originalita je v kontraktu, ne v algoritmu.** Kombinace unclassified + FP strop + deterministická evidence chain je obhajitelná; jednotlivé komponenty jsou komodita.
3. **Efektivita je asymetrická.** Vysoká explanace, nízká výtěžnost, neprokázaná generalizace. Produktový další krok není „více patternů“, ale **lesson loop a external validity**.
4. **Největší technický dluh byl falešný MDL a nekalibrovaná confidence.** P1 ho 2026-11-13 odstranil přejmenováním (coverage, tři dimenze); skutečná MDL a kalibrace jsou P2 a musí být hotové dříve, než se přidá jakýkoli nový pattern.
5. **Cross-domain inspirace je konkrétní:** process mining (precision, drift), matrix profile (parameter-free discovery), causal discovery (intervence), stylometrie (external validity). Žádná z nich není „víc patternů“; všechny jsou „lepší důkaz“.

---

## 14. Reference

### Interní

- `docs/CANDIDATE_PATTERNS_2026-11-12.md` — taxonomie F1-F8/Z, FP strop, měřicí appendix univerz (§2.1), měření P0-7.
- `docs/AUDIT_INTEGRATION_2026-11-13.md` — kanonická integrace auditu 2026-11-13: D6–D11, Tier 1–3, testovací matice, pravidla proti driftu, §12.2.
- `docs/PLAN_SINGLE_GAME_CALIBRATION_2026-11-07.md` — zmražený kontrakt detailed 1.2 (single-game).
- `docs/REFACTOR_PLAN_2026-11-11.md` — D1-D6, Phase 0 kritéria, §355 mechanismus; pro single-game roadmapu **historický**, aktuální pořadí řídí `AUDIT_INTEGRATION_2026-11-13.md`.
- `docs/MIKOLOV_KOMPRESE_V_PATTERN_ARCHITEKTURE.md` — kompresní rámec (v1.0; viz korekce §11.1).
- `docs/COMPACT_JSON_FOR_LLM.md` — compact 2.1 kontrakt.
- `docs/DEEP_DIVE_SINGLE_GAME_PATTERNS_2026-08-02.md` — single-game pattern surface.
- `docs/CROSS_REPO_TRANSFER_MAP.md` — přenositelné kontrakty z `ML_Ops_edukace` a `mcp-retrieval` (abstention, data identity, drift guard, RRF, kompresní měření).
- `src/lichess_analyzer_mcp/services/pattern_detector.py` — `per_move_patterns`, `scan_single_game`, cross-game detektory.
- `src/lichess_analyzer_mcp/models/pattern.py` — `PatternDef`, `PatternLibrary.load_baseline`.
- `src/lichess_analyzer_mcp/services/compressibility_validator.py` — coverage validator (`coverage_score`, `support`); `strength` nemění (P1).
- `src/lichess_analyzer_mcp/services/statistics.py` — Wilson CI a Katz rate-ratio CI (schema 1.3).
- `src/lichess_analyzer_mcp/services/mdl.py` — skutečná dvoučlenná MDL (§11.1); `scripts/measure_pattern_mdl.py` — měření proxy mechanismů.
- `src/lichess_analyzer_mcp/services/stability.py` — split-half (hash parita) a drift (chronologické poloviny, z-test); §5.5, §11.5.
- `src/lichess_analyzer_mcp/kb/schemas.py` — validace artefaktu, schema 1.4 (`stability` invarianty).
- `scripts/measure_pattern_coverage.py`, `scripts/aggregate_candidate_moves.py` — měření.

### Externí (ověřeno 2026-11-12)

- Sequential pattern mining — Wikipedia; survey arXiv:1805.10515 (parallel SPM).
- Process mining — Wikipedia; conformance checking; drift v process mining arXiv:2112.02000; unsupervised drift arXiv:2310.15826.
- Matrix profile — arXiv:1811.03064 (motif/discord/shapelet, parameter-free).
- Anomaly detection — Chandola et al. 2009; Wikipedia (point/contextual/collective, anomaly score).
- Causal discovery — Wikipedia (exploratory causal analysis; asociace vs kauzalita).
- MDL / Kolmogorov complexity — Wikipedia (nejkratší popis jako model selection).
- Pattern language — Alexander 1977; Wikipedia.
- Behavioral stylometry — arXiv:2208.01366 (98% identifikace hráče, 100 her).
- Maia4All — arXiv:2507.21488 (individuální modelování s málo daty).
- Brilliance perception — arXiv:2406.11895 (brilliant != engine best).
