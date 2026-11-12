---
title: Metodologie pattern discovery a detection
date: 2026-11-12
verze: 1.0
status: ZÁVAZNÝ METODOLOGICKÝ ARTEFAKT
účel: Popsat, jak vznikají a jak se ověřují kandidátní chess patterny; porovnat metodologii s pattern discovery v jiných doménách; vyhodnotit originalitu a efektivitu.
návaznost: CANDIDATE_PATTERNS_2026-11-12.md, REFACTOR_PLAN_2026-11-11.md, MIKOLOV_KOMPRESE_V_PATTERN_ARCHITEKTURE.md, COMPACT_JSON_FOR_LLM.md, DEEP_DIVE_SINGLE_GAME_PATTERNS_2026-08-02.md
---

## 0. TL;DR

1. Pattern není „zajímavý tah“. Pattern je **podmínka na pozici a rozhodnutí**, která má (a) měřený support, (b) měřený kontrast proti dobrým tahům, (c) stabilitu, (d) deterministickou detekci a (e) kalibrovanou sílu. Bez (b) se jedná o popis, ne o pattern.
2. Discovery není hledání nových ID. Discovery je **falsifikační loop**: kandidát → měření na univerzech U0/U1/U2 → FP strop → taxonomie → implementační gate → monitoring. Většina kandidátů má skončit zamítnuta; to je úspěch procesu, ne selhání.
3. Současný systém má **15 definic v baseline knihovně** (A, B, C, G, I, I2, J, N, O, P, Q, Q1, Q2, R, S) a **6 per-move eventů** (B, C, J, R, S, T); B/C/J/R/S jsou sdílené, T je pouze per-move. Z 15 definic má **14 automatický detektor**; `I` (bait trap) je záměrně `manual_only` koncept a v runtime se nevydává. Per-move eventy nejsou patterny v cross-game smyslu: nemají jmenovatel ani kontrast.
4. Měřené pokrytí na cache (259 dedup her, 2137 flagged tahů): **375 matched (17,5 %), 1762 unclassified (82,5 %)**. To není bug, to je kalibrovaná hranice znalosti. Nízké pokrytí je cenou za to, že si systém nevymýšlí mechanismus.
5. Originalita je **v kombinaci kontraktů**, ne v algoritmech. Jednotlivé komponenty (frekvence, lift, MDL, conformance, motif discovery) mají prior art. Kombinace „explicitní unclassified + FP strop na dobrých tazích + dual single/cross-game kontrakt + deterministická evidence chain“ v publikovaných chess nástrojích doložena není (P~0,75; absence důkazu, ne důkaz absence).
6. Efektivita: **vysoká explanační, nízká discovery výtěžnost, neprokázaná diskriminační validita**. `compressibility_validator` je v současné podobě proxy, ne MDL; to je nutné opravit nebo přejmenovat (P1).

---

## 1. Co je pattern a co není

### 1.1 Tři vrstvy

| Vrstva | Definice | Příklad | Jmenovatel | Čas |
|---|---|---|---|---|
| **Event** | Jednotlivé rozhodnutí s měřeným dopadem | `B` capture s cp_loss >= 100 | počet tahů | 1 tah |
| **Pattern** | Opakující se event s kontrastem proti referenci | „hráč grabuje materiál, když je v napětí“ | počet rozhodnutí / her | více her |
| **Lesson** | Pattern → příčina → trénink → měřený výsledek | „dril: napětí před grabem“ | počet tréninkových cyklů | týdny |

Současný systém je na úrovni **event + pattern**; lesson vrstva (tréninkový loop) zatím chybí. To je klíčové pro produktové hodnocení v §10.

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

| Univerzum | Definice | K čemu |
|---|---|---|
| **U0** | všechny flagged tahy (blunder/mistake/inaccuracy) | maximální recall, orientační inventář |
| **U1** | flagged tahy s dostupným kontextem (SAN, FEN, engine lines) | měření mechanismu |
| **U2** | **dobré tahy** (best / excellent) ve stejném typu pozice | FP strop, kontrast |

Bez U2 nelze odlišit „pattern“ od „běžná vlastnost pozice“. To je nejčastější chyba v pattern discovery obecně: systém najde vzorec, který je stejně častý u dobrých i špatných tahů.

### 2.2 Veličiny

Pro kandidáta `k`, univerzum `U`, hráče `p`:

```
support(k, U)   = |{tahy v U, kde k plati}| / |U|
lift(k, U1, U2) = support(k, U1) / support(k, U2)
fp_ceiling(k)   = support(k, U2)          # jak casto by vystrelil na dobrem tahu
N(k)            = pocet nezavislych pripadu (her, ne tahu)
```

`lift` je primární diskriminátor. `fp_ceiling` je primární guard. `N` je primární guard proti malému vzorku.

### 2.3 Implementační gate (nové patterny)

| Podmínka | Threshold | Zdroj |
|---|---|---|
| Nezávislé případy | `N >= 30` | GT-070 / P54 |
| Kontrast | `lift >= 1.4` | GT-070 / P54 |
| Nezávislé analýzy | `>= 2` | GT-070 / P54 |
| FP strop na U2 | musí být změřen a uveden | D4 |
| Taxonomie mechanismu | F1-F8/Z | `CANDIDATE_PATTERNS_2026-11-12.md` §4 |
| Deterministická detekce | bez LLM v runtime | REFACTOR_PLAN |

**Důležité rozlišení:** těchto `N >= 30` se týká **admission gate pro nové patterny**, ne runtime detekce. Runtime cross-game detektory mají `min_games = 3` a `min_occurrences = 2` (`models/pattern.py:55-56`). To je záměrné: runtime má vysoký recall, admission má vysokou precision. Obě hranice se nesmí zaměňovat.

### 2.4 Confidence

Současné `PatternMatch.confidence` je **ordinální skóre**, ne pravděpodobnost. Vzorce v `pattern_detector.py` jsou ad hoc (např. `min(pin_events / games * 0.8, 0.75)`), v `compressibility_validator.py` je lineární mix:

```
confidence = 0.5 * compression_score + 0.3 * entropy_score + 0.2 * sample_score
```

kde:

```
compression_score = min(compression_ratio / 10, 1)
compression_ratio = total_moves / (10 + 2 * evidence_count)
entropy_score     = games_with_pattern / total_games
sample_score      = min(frequency / total_games * 2, 1)
```

**Nález (P>0,95):** při velkém korpusu `compression_ratio` saturuje (např. 18 000 tahů / 110 = 164 → skóre 1,0) a `confidence >= 0,5` dostane i slabý pattern. Vzorec tedy měří **velikost korpusu**, ne kvalitu komprese. To není MDL. Nápravu viz §11.1 a §12 P1.

### 2.5 Důkazová hierarchie

| Úroveň | Důkaz | Co dovoluje tvrdit |
|---|---|---|
| **E0** | event bez kontextu | „tah X měl cp_loss Y“ |
| **E1** | event + position facts (SAN, FEN, board_facts) | „tah X byl capture v napětí“ |
| **E2** | E1 + kontrast U1 vs U2 | „jev je častější u špatných tahů, lift Z“ |
| **E3** | E2 + split-half / časová stabilita | „jev je stabilní, ne artefakt okna“ |
| **E4** | E3 + out-of-sample hráč / stylometrie | „jev diskriminuje hráče“ |
| **E5** | E4 + intervenční test | „trénink jevu zlepšuje výsledek“ |

Současný systém je na **E1-E2**. To stačí na coaching report, nestačí na produktové tvrzení „toto je váš hlavní problém“.

---

## 3. Discovery loop

Discovery je osmi-krokový deterministický proces. Každý krok má vstup, výstup a gate; selhání gate znamená STOP, ne „doladíme to později“.

| # | Krok | Vstup | Výstup | Gate |
|---|---|---|---|---|
| 1 | **Inventory** | cache her, engine lines | seznam kritických momentů | dedup `game_id + color + ply` |
| 2 | **Proxy extrakce** | FEN, SAN, board_facts | free_capture_after, missed_capture, hanging_piece | deterministické predikáty |
| 3 | **Kandidát** | shluky proxy + digest | hypotéza mechanismu (F1-F8) | musí být falsifikovatelná |
| 4 | **Měření U1/U2** | kandidát + univerza | support, lift, fp_ceiling, N | `lift >= 1.4`, `N >= 30` |
| 5 | **FP kalibrace** | U2 | FP strop | pokud `lift < 1.4` → ZAMÍTNOUT |
| 6 | **Taxonomie** | mechanismus | zařazení F1-F8/Z | žádný nový mechanismus bez definice |
| 7 | **Implementace** | spec + testy | detektor + schema | determinismus, unit testy, žádný LLM |
| 8 | **Monitoring** | produkce | drift, coverage, FP | pokles liftu → rekalibrace |

### 3.1 Proč je krok 5 nekompromisní

Příklad z reálných dat (`CANDIDATE_PATTERNS_2026-11-12.md` §5):

| Kandidát | Support na blunder | Support na best | Lift | Verdikt |
|---|---|---|---|---|
| K1 `loose_piece` | 7,7 % | 7,4 % | 1,04 | **zamítnuto** |
| K3 `unaddressed_check` | dobrý lift | - | - | kandidát, malý N |
| K5 `wrong_recapture` | nejčistší mechanika | - | - | kandidát |

K1 je učebnice discovery disciplíny: intuitivně „volná figura = příčina“ je empiricky prázdná. Bez U2 by se K1 stal patternem a škodil by každému hráči, který má volnou figuru bez následku.

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
| Support patternu | všechna rozhodnutí v univerzu | počet her |
| FP strop | **dobré tahy** ve stejném typu pozice | všechny tahy |
| Konverze na výsledek | hry s patternem vs bez | všechny hry |
| Stabilita | split-half / časové okno | celý korpus |

### 5.2 Interval spolehlivosti

Každý podíl musí mít Wilsonův interval (deterministicky, bez simulace). Bez CI nelze odlišit „lift 1,4 na N=30“ od „lift 1,4 na N=3000“. V reportu stačí `rate [CI95]`, `lift [CI95]`, `N`.

### 5.3 PV sparsity

Měřeno: **PV je přítomno jen u 12,9 % flagged tahů**. Důsledek:

- Mechanismy závislé na linii (F2, F3, F5) mají malý efektivní N.
- Nelze tvrdit „hráč nevyužil best“, pokud best není v cache.
- Každý report musí uvést `pv_coverage` jako globální metriku.

### 5.4 Proxy vs mechanismus

Proxy (`free_capture_after`, `missed_capture`, `hanging_piece`) je **jen generátor kandidátů**. Mechanismu se rovná až po kontrastu a kalibraci. V dokumentaci musí být vždy označeno, co je proxy a co je potvrzený mechanismus.

---

## 6. Současný stav měření

Cache: 259 dedup her, 2137 flagged tahů.

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
| **Precision** | dobrá u matched | blunder matched 56,4 %; žádný pattern bez U2 |
| **Generalizace** | neprokázaná | žádný held-out test, žádná stylometrie |
| **Stabilita** | neprokázaná | žádný split-half / drift test |
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

### 11.1 `compressibility_validator` není MDL (P1, dopad: vysoký)

`compression_ratio = total_moves / (10 + 2 * evidence_count)` roste s korpusem a saturuje. `confidence` pak dostane >= 0,5 i slabý pattern. **Fix:** buď (a) přejmenovat na `coverage_score` a odstranit z confidence, nebo (b) implementovat dvoučlennou MDL:

```
L_total = L(model) + L(data | model)
L(model) = delka definice patternu (bity)
L(data | model) = -sum log2 P(tah | model)
```

Doporučení: (a) okamžitě, (b) v P2. Do té doby nesmí být `confidence` prezentována jako pravděpodobnost.

### 11.2 Confidence je ordinální, ne kalibrovaná (P1, dopad: vysoký)

Ad hoc vzorce (`cp/500`, `pin_events/games*0.8`) nejsou pravděpodobnosti. **Fix:** přejmenovat pole na `strength`, nebo kalibrovat isotonic regression na held-out labeled datasetu. Do té doby v reportu uvádět „strength“, ne „confidence“.

### 11.3 Nezávislost patternů (P2, dopad: střední)

`per_move_patterns` vyhodnocuje tah izolovaně (s `prev_move` pouze pro C). Chybí sekvenční model. **Fix:** PrefixSpan/SPADE nad abecedou eventů s gap constraint `k <= 4`, closed patterns, support `>= 0.05`, lift `>= 1.4`, N `>= 30`. Teprve pak nový ID.

### 11.4 Chybí precision modelu (P2, dopad: střední)

Měříme fitness (kolik tahů vysvětlíme), ne precision (kolik tahů model dovoluje). **Fix:** doplnit `precision = |model ∩ log| / |model|` na úrovni typu pozice; reportovat spolu s `unclassified`.

### 11.5 Chybí drift a generalizace (P2, dopad: vysoký)

Žádný split-half, žádný časový test, žádná stylometrie. **Fix:** (a) split-half cosine stabilita, (b) Page-Hinkley / ADWIN-like deterministická detekce změny na `v_p`, (c) few-shot identifikace hráče jako external validity test.

### 11.6 PV sparsity (P1, dopad: střední)

12,9 % PV znamená, že mechanistické závěry mají malý N. **Fix:** rozšířit depth policy nebo explicitně reportovat `pv_coverage` u každého patternu; neimplikovat mechanismus z chybějící linie.

---

## 12. Roadmap s acceptance criteria

| ID | Akce | Acceptance |
|---|---|---|
| **P1** | Odstranit falešný MDL; přejmenovat `confidence` → `strength` nebo kalibrovat | žádný report netvrdí „pravděpodobnost“; testy prošly |
| **P1** | Wilson CI + lift + N do každého `PatternMatch` | schema v1.3; všechny matched eventy mají CI |
| **P2** | Split-half + časová stabilita | `stab` a `drift` v reportu; pattern bez stability označen `unstable` |
| **P2** | Precision modelu | `precision` a `fitness` v reportu vedle `unclassified` |
| **P3** | Sekvenční vrstva (PrefixSpan, gap <= 4) | nový pattern jen při `N>=30`, `lift>=1.4`, 2 analýzy |
| **P4** | Poziční featury pro `quiet_positional` | snížení unclassified pod 70 % bez poklesu precision |
| **P5** | Lesson compiler + tréninkový loop | pattern → drill → měřený outcome; A/B design |
| **P6** | External validity (stylometrie) | few-shot identifikace hráče nad baseline |
| **P7** | Pattern vector store + drift dashboard | `v_p` per hráč, stabilní schema, competitive scan |

### 12.1 Pořadí je závazné

P1 je epistemická oprava, ne feature. Bez ní je každé další číslo nedůvěryhodné. P3 (sekvence) může bez P1 vyrobit více falešných patternů, ne lepší coaching.

---

## 13. Závěry

1. **Discovery je falsifikace, ne generování.** Hodnota systému je v tom, co odmítne (K1) a co přizná jako neznámé (82,5 % unclassified).
2. **Originalita je v kontraktu, ne v algoritmu.** Kombinace unclassified + FP strop + deterministická evidence chain je obhajitelná; jednotlivé komponenty jsou komodita.
3. **Efektivita je asymetrická.** Vysoká explanace, nízká výtěžnost, neprokázaná generalizace. Produktový další krok není „více patternů“, ale **lesson loop a external validity**.
4. **Největší technický dluh je falešný MDL a nekalibrovaná confidence.** To se musí opravit dříve, než se přidá jakýkoli nový pattern.
5. **Cross-domain inspirace je konkrétní:** process mining (precision, drift), matrix profile (parameter-free discovery), causal discovery (intervence), stylometrie (external validity). Žádná z nich není „víc patternů“; všechny jsou „lepší důkaz“.

---

## 14. Reference

### Interní

- `docs/CANDIDATE_PATTERNS_2026-11-12.md` — taxonomie F1-F8/Z, FP strop, U0/U1/U2, měření P0-7.
- `docs/REFACTOR_PLAN_2026-11-11.md` — D1-D6, Phase 0 kritéria, §355 mechanismus.
- `docs/MIKOLOV_KOMPRESE_V_PATTERN_ARCHITEKTURE.md` — kompresní rámec (v1.0; viz korekce §11.1).
- `docs/COMPACT_JSON_FOR_LLM.md` — compact 2.1 kontrakt.
- `docs/DEEP_DIVE_SINGLE_GAME_PATTERNS_2026-08-02.md` — single-game pattern surface.
- `src/lichess_analyzer_mcp/services/pattern_detector.py` — `per_move_patterns`, `scan_single_game`, cross-game detektory.
- `src/lichess_analyzer_mcp/models/pattern.py` — `PatternDef`, `PatternLibrary.load_baseline`.
- `src/lichess_analyzer_mcp/services/compressibility_validator.py` — confidence mix (předmět P1).
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
