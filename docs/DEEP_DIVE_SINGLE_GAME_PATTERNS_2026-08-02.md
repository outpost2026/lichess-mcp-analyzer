# Deep Dive: Single-Game Pattern Identification & Library Calibration

**Verze:** 1.0 | **Datum:** 2026-08-02 | **Status:** analytická rešerše + feasibility verdikt
**Rozsah:** lichess-analyzer-mcp — mechanismus identifikace kandidátních patternů ze single game (obě strany, conf>0.7) + kalibrace knihovny z jednotlivých her
**Trigger:** hra HmUBpeoJ (ply 24–25, deflekce Bxf7+! Kxf7 Rxa5)

---

## 1. Verdikt (shrnutí)

**ANO — mechanismus je proveditelný, a to při minimální změně existujícího kódu.** Klíčové zjištění: infrastruktura pro obě strany i per-move analýzu **již existuje**; single game vrací `patterns: []` nikoli kvůli chybějící detekci, ale kvůli **jedinému gate** — `min_games=3` v `pattern_detector.py:39`.

| Otázka | Odpověď |
|--------|---------|
| Může MCP analyzovat single game obě strany? | **Už umí** — `analyze_game` dělá dual cache (`HmUBpeoJ_white_d14.json` + `_black_d14.json`). Chybí jen zapojení do coaching pipeline |
| Proč `patterns: []`? | Gate `min_games=3` (ř. 39) + `min_occurrences=2` (ř. 45) + strukturální požadavky A/G. Záměrné anti-noise (K5.1), ne chyba |
| Jde conf>0.7 na 1 hře? | **Ano, za podmínek** — viz §5. Krátké hry dají ~0.6, dlouhé (60+ ply) >0.7 |
| Deflekce v knihovně? | **Není** — knihovna jsou behaviorální author-error patterny (A-Q1), ne taktické motivy. Motif layer je stub (`is_tactical_motif=False` hardcoded) |
| Doménově agnostické mechanismy? | Ano — **declarative process mining (DECLARE/LTLf)** je strukturně identický problém (traces × constrainty), viz §7 |

---

## 2. Root-cause: proč single game vrací []

### 2.1 Hard gates v `detect_all` (`services/pattern_detector.py:34-48`)

```python
for pid in self.library.patterns:
    pdef = self.library.patterns[pid]
    if total_games < pdef.min_games:      # ř. 39 ← PŘÍČINA: 1 < 3 → continue pro VŠE
        continue
    ...
    if match.frequency < pdef.min_occurrences:   # ř. 45 ← sekundární
        continue
```

Všechny patterny v baselinu mají `min_games=3` (default `models/pattern.py:31`). `total_games=1` → žádný detector se nikdy nespustí.

### 2.2 Strukturální nemožnosti na 1 hře

- **A**: vyžaduje anonymous i named hry (`pattern_detector.py:51-54`) — v 1 hře nesplnitelné
- **G**: vyžaduje white i black hry (`pattern_detector.py:154-157`)

→ Tyto 2 patterny na single-game úrovni korektně nelze reportovat (nejde o chybu, ale o sémantiku). Zbytek (B, C, I, I2, J, N, O, P, Q, Q1, Q2, R, S) **lze detekovat per-move**, jen se k nim kód nedostane.

### 2.3 Bug W9 (vedlejší, ale blokuje kalibraci)

`game_analyzer.py:359-364`: mistake i blunder se ukládají do `analysis.blunders`; `analysis.mistakes` je vždy prázdný. Fix je nutný pro kalibraci, jinak se chybové statistiky kumulují špatně.

### 2.4 Co NEJDE (a je to OK)

- `min_games=3` je **záměrné** pravidlo proti noise (`KALIBRACE_PLAN_2026-07-19.md:410,423,574`; test `test_all_detectors_check_min_games`). Řešení není odstranit gate, ale **parametrizovat** ho per kontext (single-game režim → `min_games=1`, jiný confidence výpočet).

---

## 3. Deflekce — zařazení jako kandidátní pattern

### 3.1 Ontologický konflikt (musí se vyřešit designově)

Současná knihovna = **behaviorální autor-error patterny** (`pattern_type="author_error"`): B (automatic grab), C (error streak), O (flat plateau → blunder), S (capture aversion)…

Deflekce = **taktický motiv** (vlastnost pozice, ne hráče). Nejde o pattern stejné třídy → navrhuji **dvě ortogonální vrstvy**:

1. **Per-move motif layer** (nová): `motif_type` taxonomie — vyplní stub pole `is_tactical_motif`/`motif_type` (`game_analyzer.py:353-354`), na **hraném tahu i na best tahu** (missed tactic detekce)
2. **Pattern T** (nový, author_error): *"opakovaná nepozornost na deflekční sekvence"* — detekce = motif layer na hráčových tazích × kumulovaná evidence

### 3.2 Deflekce v HmUBpeoJ — ověřená data

| Ply | Událost | Data (cache d14) |
|-----|---------|-------------------|
| 25 | **Bxf7+! (a2f7)** — oběť střelce, Kxf7 vynuceno, pak Rxa5 vyhraje dámu | klasifikace `best`, eval +387→+409, win 0.91, ACPL 2 |
| — | Engine linie: `Bxf7+ Kxf7 Rxa5` (potvrzeno lichess_analyze_position d18, +3.2) | deflekce je **vynucující sled** (oběť → check → zisk dámy) |

**Detekční pravidlo deflekce (návrh):**
```
hraný_tah == oběť (materiál 3 vs zisk ≥5 do 2 ply) 
  AND vynucující (check/capture v sekvenci)
  AND engine best-linie potvrdí zisk > prah (např. +300cp)
  AND win_prob skok > 0.15
```

### 3.3 Externí taxonomie (existuje! — nemusíme vymýšlet)

- **Lichess puzzle themes** obsahují `deflection`, `decoy`, `sacrifice`, `discoveredAttack`, `hangingPiece` — veřejná kalibrační taxonomie s miliony otagovaných pozic (300M her analyzovaných Stockfish NNUE)
- **chess-detect** (PyPI 0.2.1, MIT, 2026-02): 10 taktických detektorů (fork, pin, skewer, discovered check, trapped, hanging capture, removing defender, exploiting pin…) — **deflection je v "Planned", NEIMplementováno** → máme volné pole pro vlastní detektor, ale architekturu `BaseDetector`+`MoveContext` lze přímo převzít (MIT)
- **Springer 2022 (ICCS) "Automatic Recognition of Similar Chess Motifs"**: statické + dynamické feature, automatická generace taktických puzzle z her — validace, že motiv = pozice + sekvence

---

## 4. Single-game full analýza (obě strany) — co je potřeba

### 4.1 Infrastruktura existuje, jen není zapojená

| Součást | Stav | Lokace |
|---------|------|--------|
| Dual cache (white+black) | ✅ funguje | `tools/analyze_game.py:64-69` |
| Per-move data (ply, eval, class, fen, phase, win_prob) | ✅ existuje | `data/game_cache/{id}_{color}_d{depth}.json` |
| Coaching pipeline | ⚠️ dělá jen 1 stranu | `collect_single_game` (`coaching_base.py:19-29`) — na rozdíl od `analyze_game` |
| Tactical motif | ❌ stub | `game_analyzer.py:353-354` (hardcoded False/None) |
| Pattern detector | ✅ funguje per-move | `pattern_detector.py` |
| Compression confidence | ✅ funguje | `compressibility_validator.py` |
| Pattern store | ✅ funguje | `data/resource_store/pattern_store.json` |

### 4.2 Změny (odhad: 3 modifikace + 1 nový modul)

1. **`detect_all(analyses, metadata, min_games_override=None)`** — parametrizace gate (§2.1). Single-game režim → `min_games=1`
2. **Fix W9** — oddělit mistakes od blunders (§2.3)
3. **`coaching_single_game` → dual** — zavolat `analyze_pgn` pro obě barvy (stejný vzor jako `analyze_game`)
4. **NOVÝ: motif engine** — taxonomie motivů (fork/pin/skewer/deflection/decoy/removing-defender…), detekce na hraném i best tahu, python-chess (již je dependency)

---

## 5. Confidence na single game — poctivá kalkulace

### 5.1 Existující vzorec (`compressibility_validator.py:48-52`)

```
final = 0.5*compression_score + 0.3*entropy_score + 0.2*sample_score
compression_score = min(compression_ratio/10, 1.0)
entropy_score     = min(games_with_pattern/len(analyses), 1.0)
sample_score      = min(frequency/len(analyses)*2, 1.0)
compression_ratio = total_moves / (PATTERN_BASE_COST + exception_cost)  # BASE=10
```

### 5.2 Dosažitelnost conf>0.7 při N=1 (deterministická kalkulace)

Pro N=1: `entropy_score = 1.0`, `sample_score = 1.0` → **bottleneck je compression_score**.

| Scénář (1 hra, 1 pattern) | total_moves | ratio | comp | **final** |
|---------------------------|-------------|-------|------|-----------|
| HmUBpeoJ (25 ply) | 25 | 25/12=2.1 | 0.21 | **0.60** |
| Standardní hra (60 ply) | 60 | 60/12=5.0 | 0.50 | **0.75 ✓** |
| Dlouhá hra (90 ply) | 90 | 90/12=7.5 | 0.75 | **0.88 ✓** |
| Hra + 2 evidence | 60 | 60/14=4.3 | 0.43 | 0.71 ✓ |

→ **conf>0.7 na single game JE dosažitelný**, ale není garantovaný pro krátké hry. Vlastní kalibrační plán autora toto řeší konceptem **TOT kandidát 0.3–0.6** (`KALIBRACE_PLAN:282-303`): pattern s conf 0.3–0.6 = kandidát, teprve replikace na ≥2–3 hrách posune nad 0.7.

**Doporučení:** single game → kandidátní vrstva (candidate registry v `pattern_store.json`, TOT flag, `min_occurrences=1`), kalibrace z N her → promotion na plný pattern. To přesně kopíruje historickou metodu autora (21 her ručně → knihovna), jen automatizovaně.

---

## 6. Kalibrace knihovny z jednotlivých her (feedback loop)

### 6.1 Historická metoda (autor, `CONTEXT_A_ZAMER.md:49-70`)

> "Analyza 21 partii (2023-2026) odhalila … Patternu identifikovano 17 (A-Q1) … Predchozi analyza probehla rucne — LLM + manualni zapis 21 partii."
> "vznikal rucni analyzou PGN s LLM + feedbackem autora (zkuseny hrac, ~2000 ELO) … cenna, ale stochasticka a neoveritelna baseline" (`KALIBRACE_PLAN:77`)

→ Cíl mechanismu: **stejný proces, deterministicky a opakovatelně.**

### 6.2 Navržený feedback loop

```
hry (obě strany) → motif engine + pattern detector (min_games=1)
  → candidate registry (conf, evidence, game_ids, TOT flag)
  → N≥3 her se stejnou signaturou → rekalibrace confidence kompresí
  → promotion → knihovna (PatternDef) + test pattern_semantic_contract
```

- Validace promoce: `validate_against_schema` + `validate_pattern_artifact` (existují, `match_patterns.py:199-204`)
- Evidence se ukládá s `game_ids` → **žádná fabrikace** (pravidlo DATA-FABRICATION-001: neuvádět game_id bez affected_games)
- Pattern z 1 hry zůstává kandidátem, **nikdy** ne promovaným patternem — konzistentní s K5.1

---

## 7. Rešerše veřejných zdrojů (doménově agnostické)

### 7.1 Declarative process mining — NEJBLIŽŠÍ ANOLOGIE (doporučeno k prostudování)

**Problém je strukturně identický:** šachová hra = trace (sekvence eventů), pattern = constraint. DECLARE/DCR formalizuje to, co autor postavil ad-hoc jako PatternDef.

| Zdroj | Co dává |
|-------|---------|
| **PM4Py** (Python, ~1M+ downloads) | process discovery, conformance checking (alignments, footprint, LTL), DECLARE templates |
| **Declare4Py** (Python) | DECLARE/LTLf: existence, response, precedence, alternation… conformance + **model discovery** + ML encodings |
| **DCR4Py** (Python, DTU) | Dynamic Condition Response Graphs — discovery + rule conformance |
| **MINERful / RuM toolkit** | automatická discovery Declare specifikací z event logů |
| **IEEE XES** | standardní formát event logu — hra → XES trace = přímý vstup do celého ekosystému |

**Vazba na náš problém:** místo psaní `_detect_B()`, `_detect_C()`… lze knihovnu A-Q1 vyjádřit jako DECLARE constrainty a:
- **Conformance**: trace hry × constraint → splněno/porušeno + metriky fitness (existence "error po flat plateau", response "po capture bez kontroly následuje error")
- **Discovery**: MINERful-style automatická extrakce constraintů z logu her → **to je přesně "kalibrace knihovny z jednotlivých her"**, matematicky podložená
- Confidence → DECLARE má vlastní statistiky (support/vacuous satisfaction)

### 7.2 Sekvenční pattern mining

| Zdroj | Co dává |
|-------|---------|
| **SPMF / PrefixSpan** (Pei et al., IEEE TKDE 2004; PySpark `pyspark.ml.fpm.PrefixSpan`) | frequent subsequence mining — opakující se tahové sekvence napříč hrami |
| **GSP / SPADE / FreeSpan** | varianty s časovými okny a hierarchií — sekvence s gap constraints |
| **ComplexPrefixSpan** (ICAICE 2023) | multi-sequence framework — aplikace např. na click-streamy (anologie: tahová data) |

**Vazba:** "frequent error-adjacent sequence" (např. capture → blunder ≤3 tahy) = sekvenční pattern → možný automatický kandidátní pattern T2, T3…

### 7.3 Šachově-specifické zdroje (implementační reuse)

| Zdroj | Relevance |
|-------|-----------|
| **chess-detect** (PyPI 0.2.1, MIT) | 10 taktických detektorů, `BaseDetector`+`MoveContext` architektura — převzít vzor; deflection chybí (Planned) |
| **Blunder prediction (Rokach & Shapira, Appl. Intell. 56:92, 2026)** | personalizovaná predikce blunderů, **collaborative user embeddings**, immediate (taktické) vs non-immediate (strategické) blunders, stylometrie hráčů 98% — akademická validace, že chybové vzorce hráče jsou identifikovatelné z tahů |
| **arXiv 2512.01880 (2025)** | n-gram jazykové modely tahů per skill-group — **tahy jako behaviorální jazyk**, skill klasifikace z 16 ply |
| **arXiv 2504.05425 (2025)** | Behavioral Programming (b-thread request/watch/block) + anti-scenarios, +25% move prediction — "co hráč NEdělá" = anti-patterny |
| **Maia chess (McIlroy-Young et al., KDD 2020)** | predikce lidských tahů, sladění AI s lidským chováním |
| **Springer 2022 ICCS — Similar Chess Motifs** | statické + dynamické featurace motivů, auto-puzzle generace |
| **Chessalytics / Chess Weakness Scanner (komerční)** | archetypy hráčů (Endgame Grinder…), 5 kategorií slabin, clustering chyb — komerční validace konceptu cross-game weakness profiling |
| **Lichess puzzle pipeline** | 300M her → Stockfish NNUE 40M nodes → tématicky tagované puzzle (deflection je standardní Lichess theme) — **kalibrační korpus pro motif taxonomii** |

### 7.4 Co vzít dál (seřazeno dle poměru přínos/úsilí)

1. **Motif engine** (vlastní, ~10 detektorů, python-chess) — nejmenší krok, nejvyšší přínos, vyplní stub, umožní Pattern T (deflekce)
2. **Parametrizace min_games + fix W9 + dual coaching** — 3 malé změny, odemknou single-game candidates
3. **Declare4Py pilot** — vyjádřit 3–5 stávajících patternů jako constrainty, otestovat discovery na 21 historických hrách → první verze automatické kalibrace
4. **Candidate registry + promotion loop** — rozšíření `pattern_store.json`

---

## 8. Návrh nového patternu — T (Deflekce)

```python
PatternDef(
    id="T",
    name="Deflection Blindspot",
    pattern_type="author_error",
    mechanism="Player misses or fails to see deflection/decoy sequences "
              "(sacrifice forcing a piece off its defensive duty, e.g. Bxf7+ Kxf7 Rxa5)",
    it_analogy="Opening a trap door under a load-bearing wall instead of checking what it supports",
    detection_method="deflection_motif",
    severity="high",
    min_games=3,
    min_occurrences=2,   # single-game režim: 1
    detection_rules={
        "motif": "deflection|decoy",
        "sacrifice_floor": 3,        # oběť materiálu (body)
        "gain_floor": 5,             # zisk do 2 ply
        "forcing": True,             # check/capture sekvence
        "engine_confirm_cp": 300,
        "win_prob_delta": 0.15,
    },
)
```

**Evidence z HmUBpeoJ:** ply 25 (Bxf7+ → Kxf7 → Rxa5, eval +387→+409, engine potvrzuje d18) — **1 evidence** → single-game conf ~0.60 → TOT kandidát. Dvě replikace v dalších hrách → >0.7 → promotion.

---

## 9. Akční kroky (další krok)

1. Rozhodnout o ontologii: motif layer vs Pattern T (§3.1) — bez toho nelze implementovat
2. Pilot: implementovat motif engine + `min_games` parametrizaci na HmUBpeoJ, změřit conf
3. Pilot: Declare4Py discovery na 21 historických hrách → srovnat s existující knihovnou A-Q1

---

## 10. Zdroje

- Repo: `lichess-analyzer-mcp` — `models/pattern.py`, `services/pattern_detector.py`, `services/compressibility_validator.py`, `services/game_analyzer.py` (W9: ř.359-364, stub: ř.353-354), `tools/analyze_game.py:64-69`, `tools/coaching_single_game.py`, `docs/KALIBRACE_PLAN_2026-07-19.md`, `docs/CONTEXT_A_ZAMER.md`, `docs/MIKOLOV_KOMPRESE_V_PATTERN_ARCHITEKTURE.md`, `docs/CHESS_PATTERNS_AUDIT_2026-07-28.md` (W9: ř.303-333)
- Data: `data/game_cache/HmUBpeoJ_{white,black}_d14.json`, `data/resource_store/pattern_store.json`
- Externí: chess-detect (PyPI 0.2.1), PM4Py/Declare4Py/DCR4Py, SPMF/PrefixSpan (Pei et al. 2004), Rokach & Shapira 2026 (Appl Intell), arXiv 2512.01880, arXiv 2504.05425, Springer ICCS 2022, lichess puzzle DB
