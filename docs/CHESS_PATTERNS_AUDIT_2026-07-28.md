# Chess Patterns Audit 2026-07-28

**Verze:** 1.0 | **Datum:** 2026-07-28  
**Repo:** https://github.com/outpost2026/lichess-mcp-analyzer  
**Audit scope:** Pattern detection engine (14 detectorů), serializace, evidence, testy  
**Navazuje na:** PATTERN_DETECTOR_AUDIT_INJECT.md, HALUCINACE_ROOT_CAUSE_ANALYSIS.md, AUDIT_REPORT_v2

---

## Obsah
1. [W1 — game_ids dropped v serializaci (CRITICAL)](#w1--game_ids-dropped-v-serializaci-critical)
2. [W2 — Evidence schema nekonzistentní napříč 14 detectory (HIGH)](#w2--evidence-schema-nekonzistentní-napříč-14-detectory-high)
3. [W3 — _detect_j semantic mismatch: king moves jako blocks (MEDIUM)](#w3--_detect_j-semantic-mismatch-king-moves-jako-blocks-medium)
4. [W4 — Pattern S/J overlap bez dedup (LOW)](#w4--pattern-sj-overlap-bez-dedup-low)
5. [W5 — affected_games type mismatch int vs list (MEDIUM)](#w5--affected_games-type-mismatch-int-vs-list-medium)
6. [W6 — I2 confidence formula broken (HIGH)](#w6--i2-confidence-formula-broken-high)
7. [W7 — CompressibilityValidator neodpovídá README (MEDIUM)](#w7--compressibilityvalidator-neodpovídá-readme-medium)
8. [W8 — Pattern artifact validator nevaliduje affected_games (LOW)](#w8--pattern-artifact-validator-nevaliduje-affected_games-low)
9. [W9 — mistakes list vždy prázdný (CRITICAL)](#w9--mistakes-list-vždy-prázdný-critical)
10. [W10 — Nekonzistentní sémantika frequency napříč patterny (MEDIUM)](#w10--nekonzistentní-sémantika-frequency-napříč-patterny-medium)
11. [Cross-reference s předchozími AUD nálezy](#11-cross-reference-s-předchozími-aud-nálezy)
12. [Plán oprav](#12-plán-oprav)

---

## W1 — game_ids dropped v serializaci (CRITICAL)

### Lokace
`tools/match_patterns.py:152-170`

### Popis
`PatternMatch.game_ids: list[str]` je povinné pole v modelu (`models/pattern.py:41`). Všech 14 detectorů ho správně plní. Ale tool response builder ho **nikde nepoužije**:

```python
entry = {
    "pattern_id": m.pattern_id,
    "pattern_name": m.pattern_name,
    "confidence": round(m.confidence * 100, 0),
    "frequency": m.frequency,
    "severity": m.severity,
    "evidence": m.evidence,        # ← passthrough
    "mitigation": ...,
    # m.game_ids NENÍ
}
```

### Dopad
Agent vidí `frequency=5` pro Pattern J, ale neví **kterých 5 her**. Nemůže uvést konkrétní příklad. Toto je **přímá příčina halucinace** v coaching reportu (viz HALUCINACE_ROOT_CAUSE_ANALYSIS.md).

### Fix (2 řádky)
```python
entry = {
    # ... stávající pole ...
    "evidence": m.evidence,
    "affected_games": list(m.game_ids),    # ← ADD
    "mitigation": ...,
}
```

### Regresní test
`tests/test_pattern_semantic_contract.py` — přidat test, který po `detect_all()` ověří že `response["affected_games"]` je `list[str]` a non-empty pro každý pattern s frequency > 0.

---

## W2 — Evidence schema nekonzistentní napříč 14 detectory (HIGH)

### Lokace
`services/pattern_detector.py` — všechny `_detect_*` metody

### Audit evidence[0] keys

| Pattern | evidence[0] keys | affected_games? | Typ | Lokace |
|---------|-----------------|-----------------|-----|--------|
| **A** | anonymous_blunder_rate, named_blunder_rate, ratio | ❌ | — | line 54-59 |
| **B** | blunder_captures, total_captures, blunder_capture_ratio, **affected_games**, total_games | ✅ | `list[str]` | line 88-95 |
| **C** | **affected_games**, total_games, max_consecutive_blunders, threshold_consecutive, detail | ⚠️ | `int` (count) | line 128-135 |
| **G** | white_blunder_rate, black_blunder_rate, asymmetry_ratio, dominant_side | ❌ | — | line 169-175 |
| **I2** | gift_captures, total_games, threshold_eval_jump, detail | ❌ | — | line 201-207 |
| **J** | impulsive_blocks, total_games, threshold_cp, detail | ❌ | — | line 234-239 |
| **O** | **affected_games**, total_games, repetition_confirmed, fallback_heuristic, detail | ⚠️ | `int` | line 291-298 |
| **P** | **affected_games**, total_games, threshold_cp, condition, detail | ⚠️ | `int` | line 326-333 |
| **Q** | defensive_wins, total_games, threshold_deficit_cp, detail | ❌ | — | line 365-371 |
| **Q1** | **affected_games**, total_games, threshold_eval, detail | ⚠️ | `int` | line 409-414 |
| **Q2** | resilient_wins, total_games, threshold_blunder_cp, detail | ❌ | — | line 443-449 |
| **R** | **affected_games**, total_games, threshold_eval_before, threshold_cp_loss, condition | ⚠️ | `int` | line 476-483 |
| **S** | **affected_games**, total_games, threshold_cp, detail | ⚠️ | `int` | line 510-516 |
| **N** | pin_events, total_games, threshold_cp, detail | ❌ | — | line 545-551 |

### Statistika
- **1/14** správně (B: `list[str]`)
- **6/14** chybně (C,O,P,Q1,R,S: `int` místo `list[str]`)
- **7/14** chybí úplně (A,G,I2,J,Q,Q2,N)

### Fix
Normalizovat všech 14 detectorů na jednotný formát:
```python
evidence=[{
    "affected_games": list(set(affected)),   # ← list[str] vždy
    "total_games": total_games,
    # ... specifická pole patternu ...
}]
```

---

## W3 — _detect_j semantic mismatch: king moves jako blocks (MEDIUM)

### Lokace
`services/pattern_detector.py:221-225`

### Popis
PatternDef (line 117-126) definuje Pattern J jako "Blocking a check with a piece without calculating king safety or material loss." Ale kód detekuje:

```python
if m.was_in_check and "x" not in m.move_san:
```

To zachytí **všechny** špatné necapture odpovědi na šach, včetně:
- ✅ Blok figurou (Rb3, Qe2, Bc3) — correct
- ❌ Ústup králem (Kd3, Kf7) — false positive
- ❌ Ústup dámou/ věží bez bloku — false positive

### Příklad false positive
`tDcFRclj` ply 29: Kd3 (king move, mistake 282cp, was_in_check=true). Tento tah není "block s figurou" — je to ústup králem. Pattern J by ho neměl detekovat.

### Dopad na frekvenci
Frequency Pattern J je uměle zvýšená o king-move false positives. Reálná frekvence "check blocků" je nižší.

### Fix
```python
if m.was_in_check and "x" not in m.move_san:
    # Exclude king moves — pattern J = BLOCK with piece, not king retreat
    if "K" in m.move_san:
        continue
```

### Alternativa
Přejmenovat pattern na "Impulsive check response" a akceptovat king moves jako validní detekci. Toto je méně přesné ale jednodušší.

---

## W4 — Pattern S/J overlap bez dedup (LOW)

### Lokace
`services/pattern_detector.py:216` (J), `pattern_detector.py:492` (S)

### Popis
Pattern S (Capture aversion under check): detekuje situace kdy hráč **mohl brát šachující figurou králem** ale neudělal to.
Pattern J (Impulsive check block): detekuje situace kdy hráč **blokoval šach figurou** místo ústupu nebo brání.

Pokud hráč:
1. Je v šachu
2. Král MŮŽE brát šachující figuru
3. Ale hráč místo brání **blokuje figurou**

Pak stejný tah splní podmínky pro **oba** patterny — S i J. Aktuálně není implementována deduplikace ani mutual exclusion.

### Fix (volitelný)
Pokud oba patterny detekují stejné `(game_id, ply)`, preferovat S (specifictější — king capture possible) před J (obecnější).

---

## W5 — affected_games type mismatch int vs list (MEDIUM)

### Lokace
Pattern C (line 130), O (293), P (328), Q1 (411), R (478), S (512)

### Popis
Těchto 6 patternů ukládá `"affected_games"` jako **int** (počet her):

```python
evidence=[{
    "affected_games": len(set(affected)),   # int, not list!
}]
```

Místo seznamu game IDs:

```python
evidence=[{
    "affected_games": list(set(affected)),  # list[str]
}]
```

### Dopad
I po fixu W1 (přidání `m.game_ids` do response) by těchto 6 patternů stále nemělo per-game data v `evidence[]`. Agent by musel číst z `affected_games` na úrovni patternu, ne z `evidence` — ale to je matoucí a nekonzistentní.

### Fix
```python
# BEFORE:
"affected_games": len(set(affected))

# AFTER:
"affected_games": list(set(affected))
```

---

## W6 — I2 confidence formula broken (HIGH)

### Lokace
`services/pattern_detector.py:200`

### Popis
```python
confidence=min(gift_count / total_games * 0.8, 0.9),
```

Pro `gift_count=1` a `total_games=35`:
- `1 / 35 * 0.8 = 0.0228`
- `min(0.0228, 0.9)` = `0.0228` → po vynásobení 100 v tool response = **2.3%**

To je **EXTREMÉNĚ nízká** confidence pro pattern, který je detekován. I kdyby byl pattern perfektní, confidence je 2.3%. Pattern I2 je v reportech prakticky neviditelný.

### Root cause
Vzorec penalizuje nízkou frekvenci **příliš agresivně**. `gift_count / total_games` je poměr výskytů na hru — pro 1 výskyt ve 35 hrách = 2.8%. To je pak násobeno 0.8 → 2.3%.

### Porovnání s ostatními patterny
- Pattern B: `blunder_captures / total_captures * 2` — pokud 5 blunder captures z 10 total = 0.5*2 = 1.0 → cap 0.95
- Pattern J: `block_count / total_games * 0.9` — 5/35*0.9 = 0.128 → 12.8%
- Pattern I2: `gift_count / total_games * 0.8` — 1/35*0.8 = 0.022 → 2.3%

### Fix
Použít konzistentní vzorec jako ostatní patterny:
```python
confidence=min(gift_count / max(total_games, 1) * 0.9, 0.85),
```
Nebo lépe: upravit poměr na `max(gift_count, 1) / max(total_games, 1) * 0.9` s garancí že 1 výskyt dá alespoň ~5% confidence.

### Alternativa
Přidat per-pattern base confidence: `min(0.05 + gift_count / total_games * 0.8, 0.85)` — garantuje minimálně 5% i při 1 výskytu.

---

## W7 — CompressibilityValidator neodpovídá README (MEDIUM)

### Lokace
`services/compressibility_validator.py:13-23` vs `README.md:69-75`

### README říká
```
final_confidence = 0.5 × compression_score + 0.3 × entropy_score + 0.2 × sample_score
```

### Kód dělá
```python
compression_ratio = total_moves / (PATTERN_BASE_COST + evidence_count * 2)
```

### Gap
Chybí:
1. **Entropy score** — měření entropie patternu (kolik šumu odstranil)
2. **Sample score** — penalizace za malý vzorek / bonus za konzistenci
3. **Integrace do confidence** — v README se počítá finální confidence, v kódu se compression_ratio pouze ukládá do PatternMatch a v tool response se zobrazuje jako samostatné pole, ale confidence zůstává z pattern_detector.py (data-driven nebo hardcoded)

### Fix návrh
Implementovat chybějící 2 komponenty a integrovat do confidence:
```python
def compute_compression(match, analyses):
    total_moves = sum(len(a.moves) for a in analyses)
    evidence_count = len(match.evidence) or 1
    pattern_cost = PATTERN_BASE_COST + evidence_count * 2
    compression_ratio = total_moves / pattern_cost
    match.compression_ratio = round(compression_ratio, 1)

    # Entropy score: jak moc pattern redukuje variabilitu
    games_with_pattern = len(set(match.game_ids))
    entropy_score = min(games_with_pattern / len(analyses), 1.0) if analyses else 0

    # Sample score: penalizace za malý vzorek
    sample_score = min(match.frequency / max(len(analyses), 1) * 2, 1.0)

    # Compression score z ratio
    compression_score = min(compression_ratio / 10.0, 1.0)

    # Final confidence dle README
    match.confidence = 0.5 * compression_score + 0.3 * entropy_score + 0.2 * sample_score
    return match
```

---

## W8 — Pattern artifact validator nevaliduje affected_games (LOW)

### Lokace
`services/pattern_artifact_validator.py:17-48`

### Popis
Validátor kontroluje: username, games_analyzed, pattern_id unikátnost, confidence 0-100, severity valid, frequency >= 1, hypothesis prefix. **Nekontroluje affected_games.**

### Fix
Přidat validaci:
```python
affected = p.get("affected_games", [])
if not isinstance(affected, list):
    issues.append(f"pattern[{i}] affected_games must be a list")
elif isinstance(affected, list) and affected and not all(isinstance(g, str) for g in affected):
    issues.append(f"pattern[{i}] affected_games items must be strings")
```

---

## W9 — mistakes list vždy prázdný (CRITICAL)

### Lokace
`services/game_analyzer.py:_run_analyze_pgn()` (AUDIT_REPORT_v2 N1)

### Popis
Tahy klasifikované jako `"mistake"` (150-299 cp ztráta) se ukládají do `analysis.blunders`, nikdy do `analysis.mistakes`:

```python
if classification in ("blunder", "mistake"):
    analysis.blunders.append(move_analysis)       # BUG: i mistakes jdou sem
elif classification == "inaccuracy":
    analysis.inaccuracies.append(move_analysis)
```

### Dopad
- `GameAnalysis.mistakes` je vždy prázdný
- `diagnostician.py` agreguje `total_mistakes += len(analysis.mistakes)` = vždy 0
- Coaching prompt ukazuje "Mistakes: 0" i když jich je 10+
- Existence testů neodhalila bug (test `test_mistake_subkeys` má guard `if not mistakes: return`)

### Fix
```python
if classification == "blunder":
    analysis.blunders.append(move_analysis)
elif classification == "mistake":
    analysis.mistakes.append(move_analysis)
elif classification == "inaccuracy":
    analysis.inaccuracies.append(move_analysis)
```

---

## W10 — Nekonzistentní sémantika frequency napříč patterny (MEDIUM)

### Lokace
Všechny `_detect_*` metody v `services/pattern_detector.py`

### Popis
`frequency` má 3 různé významy:

| Význam | Patterny | Příklad |
|--------|----------|---------|
| **Počet her** (game count) | A, C, G, O, P, Q, Q1, Q2, R, S | O: `frequency=len(set(affected))` = 19 her |
| **Počet výskytů** (event count) | B, J, I2, N | J: `frequency=block_count` = 5 bloků (ale jen ve 2 hrách) |
| **Blunder rate** (float→int) | G | G: `frequency=int(max(white_blunder_rate, black_blunder_rate))` = 1.4→1 |

Pattern G je nejhorší — míchá blunder rate (desetinné číslo) do frequency, která je jinde počet her/událostí.

### Dopad
- `min_occurrences` v `PatternDef` (výchozí 2) filtruje podle různé metriky
- Pattern G s `frequency=1` (blunder rate 1.4) neprojde `min_occurrences=2`, i když postižených her je 7

### Fix
Standardizovat `frequency` na jednotný význam napříč všemi patterny. Doporučeno: **počet výskytů** (event count) jako primární, protože to umožňuje rozlišit "1 hra s 5 bloky" od "5 her s 1 blokem".

Pro Pattern G změnit:
```python
frequency=len(affected_ids)  # počet her, ne blunder rate
```

---

## 11. Cross-reference s předchozími AUD nálezy

### Z PHASE2_BUILD_PLAN.md (AUD-01 až AUD-11)

| AUD ID | Status | Vazba na W* |
|--------|--------|-------------|
| AUD-01 | ⏳ OPEN | B: total_captures bug — samostatný, nesouvisí s W* |
| AUD-02 | ⏳ OPEN | C: detection_method "sector_focus_sequence" neodpovídá kódu |
| AUD-03 | ✅ RESOLVED | I→concept, code merged do I2 — vyřešeno rename |
| AUD-04 | ✅ RESOLVED | O rename → Stagnační panika — vyřešeno |
| AUD-05 | ⏳ OPEN | Q: detection_method "defensive_phase_analysis" neodpovídá kódu |
| AUD-06 | ⏳ OPEN | P: heuristika místo forcing analysis |
| AUD-07 | ⏳ OPEN | Hardcoded confidence (O,P,Q,Q1,R) → data-driven |
| AUD-08 | ⏳ OPEN | **W2, W5** — standardizace evidence formatu |
| AUD-09 | ✅ RESOLVED | test_pattern_semantic_contract.py existuje (18 testů) |
| AUD-10 | ✅ RESOLVED | Pattern S v produkci (detector + PatternDef) |
| AUD-11 | ✅ RESOLVED | I detection_method opraven (I→concept, code→I2) |

### Z AUDIT_REPORT_v2

| Nález ze v2 | Status | Vazba na W* |
|-------------|--------|-------------|
| N1 — mistakes list vždy prázdný | ❌ STILL OPEN | **W9** |
| N2 — "most-played opening" bere první, ne nejčastější | ❌ STILL OPEN | samostatný |
| N3 — Middlegame weakness pravidlo absolutní počty | ❌ STILL OPEN | samostatný |
| N4 — Pattern G frequency = blunder rate mix | ❌ STILL OPEN | **W10** |
| N7 — Pořadí operací v match_patterns.py | ❌ STILL OPEN | samostatný |

### Nově identifikované v tomto auditu (W*)

| ID | Priorita | Typ | 
|----|----------|-----|
| **W1** | CRITICAL | serializace — game_ids dropped |
| **W2** | HIGH | evidence schema nekonzistentní |
| **W3** | MEDIUM | _detect_j semantic mismatch (king moves) |
| **W4** | LOW | S/J overlap bez dedup |
| **W5** | MEDIUM | affected_games int vs list |
| **W6** | HIGH | I2 confidence broken |
| **W7** | MEDIUM | compressibility vs README gap |
| **W8** | LOW | validator nevaliduje affected_games |
| **W9** | CRITICAL | mistakes list vždy prázdný |
| **W10** | MEDIUM | frequency sémantika nekonzistentní |

---

## 12. Plán oprav

### Fáze 1 — Data integrity (P0)

| Pořadí | ID | Fix | Soubor | Očekávaný dopad |
|--------|----|-----|--------|-----------------|
| 1 | **W9** | Rozlišit blunder/mistake v game_analyzer.py | `services/game_analyzer.py` | Mistakes přestanou být 0 |
| 2 | **W1** | Přidat `affected_games` do response entry | `tools/match_patterns.py:155` | Každý pattern vrátí seznam game IDs |
| 3 | **W2+W5** | Normalizovat evidence napříč 14 detectory | `services/pattern_detector.py` | Jednotný formát affected_games |
| 4 | **W6** | Opravit I2 confidence vzorec | `services/pattern_detector.py:200` | I2 přestane být neviditelný |

### Fáze 2 — Semantic integrity (P1)

| Pořadí | ID | Fix | Soubor |
|--------|----|-----|--------|
| 5 | **W3** | Vyloučit king moves z _detect_j | `services/pattern_detector.py:225` |
| 6 | **W7** | Implementovat entropy + sample score | `services/compressibility_validator.py` |
| 7 | **W10** | Standardizovat frequency sémantiku | `services/pattern_detector.py` |

### Fáze 3 — Quality (P2)

| Pořadí | ID | Fix | Soubor |
|--------|----|-----|--------|
| 8 | **W4** | Dokumentovat S/J overlap | `services/pattern_detector.py` docstring |
| 9 | **W8** | Přidat affected_games validaci | `services/pattern_artifact_validator.py` |
| 10 | **AUD-07** | Nahradit hardcoded confidence data-driven | `services/pattern_detector.py` |
| 11 | **N2** | Opravit "most-played opening" pravidlo | `services/diagnostician.py:56` |
| 12 | **N3** | Opravit middlegame weakness na rate | `services/diagnostician.py:52` |
| 13 | **N7** | Pořadí: sort before store | `tools/match_patterns.py` |
| 14 | **AUD-01** | Opravit B total_captures scope | `services/pattern_detector.py:68-102` |

### Nové testy (P0)

| Test | Co ověřuje | Vazba na fix |
|------|-----------|-------------|
| `test_mistakes_not_empty` | mistakes list není vždy prázdný | W9 |
| `test_response_has_affected_games` | response obsahuje affected_games: list[str] | W1 |
| `test_every_pattern_has_affected_games` | každý PatternMatch má non-empty affected_games | W2 |
| `test_pattern_j_no_king_moves` | Pattern J nedetekuje king moves | W3 |
| `test_i2_confidence_reasonable` | I2 confidence > 5% pro 1 výskyt | W6 |
| `test_pattern_g_frequency_is_count` | G frequency = počet her, ne blunder rate | W10 |
| `test_pattern_b_total_captures_all` | B total_captures počítá všechny captures | AUD-01 |

---

## Reference

| Dokument | Odkaz |
|----------|-------|
| PATTERN_DETECTOR_AUDIT_INJECT.md | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/docs/PATTERN_DETECTOR_AUDIT_INJECT.md |
| HALUCINACE_ROOT_CAUSE_ANALYSIS.md | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/docs/HALUCINACE_ROOT_CAUSE_ANALYSIS.md |
| AUDIT_REPORT_v2 | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/docs/AUDIT_REPORT_lichess-analyzer-mcp_v2.md |
| PHASE2_BUILD_PLAN.md | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/docs/PHASE2_BUILD_PLAN.md |
| Pattern detector (kód) | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/src/lichess_analyzer_mcp/services/pattern_detector.py |
| Tool response builder | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/src/lichess_analyzer_mcp/tools/match_patterns.py |
| Game analyzer | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/src/lichess_analyzer_mcp/services/game_analyzer.py |
| Compressibility validator | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/src/lichess_analyzer_mcp/services/compressibility_validator.py |
| Semantic contract tests | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/tests/test_pattern_semantic_contract.py |
