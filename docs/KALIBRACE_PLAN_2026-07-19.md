---
title: Kalibracni plan MCP pipeline — z historicke meta-analyzy LLM chyb
date: 2026-07-19
autor: opencode (deepseek-v4-flash-free)
ucel: Mapovani identifikovanych chyb LLM na konkretni implementacni zlepseni MCP serveru
vychozi-dokumenty:
  - Meta-analyza chyb LLM (historicke vlakno, N>8 iteraci)
  - LLM_DIFFERENTIAL_ANALYSIS_2026-07-19.md (dnesni test raw PGN vs Stockfish)
status: navrh
version: 1.0
---

# Kalibracni plan MCP pipeline

## 1. Ucel dokumentu

Tento dokument mapuje **7 kategorii systematickych chyb LLM pri analyze sachovych PGN** (identifikovanych v historickem vlakne o 8+ iteracich) na konkretni implementacni ukoly pro MCP server `lichess-analyzer-mcp`. Kazda kategorie obsahuje:

- Povodni chybu z meta-analyzy
- Soucasny stav pipeline (co uz resi)
- Co jeste chybi (mezera)
- Konkretni implementacni task
- Kriterium uspechu (test pass)

---

## 2. Prehled 7 kategorii chyb a stav reseni

| # | Kategorie | Stav v pipeline | Reseno | Zbyva |
|---|-----------|----------------|--------|-------|
| 1 | Zamena barvy/vysledku | ✅ Licenses client + PGN parser extrahuje header | Automaticke z PGN Site/Result/White/Black headers | -- |
| 2 | Nadhodnoceni kvality | ✅ Stockfish depth 12 per-move | Engine poskytuje cp_loss, ne nazor | -- |
| 3 | Podhodnoceni chyb (prehlednute blundery) | ✅ Stockfish detekuje vsechny chyby | Engine klasifikuje blunder/mistake/inaccuracy | -- |
| 4 | Falesne psychologicke atributy | ⚠️ Pattern detector generuje confidence | Detekce podle objektivnich cp_loss kriterii | Chybi psychologicky layer (volitelny) |
| 5 | Predcasna generalizace (pattern z 1 hry) | ❌ Pattern detector pouziva staticke prahy | Kazdy pattern ma fixed thresholds | Chybi statisticka validace na vice hrach |
| 6 | Nekonzistence v JSON structure | ❌ KB writer generuje strukturu | Writer je jednoduchy (write-only) | Chybi validace, schema enforcement |
| 7 | Chybejici sanity checks (vysledek vs analyza) | ❌ Zadne post-analyza sanity kontroly | -- | Chybi krizova validace (result, color, material) |

---

## 3. Detailni rozpad na implementacni tasky

### 3.1 Kategorie 5: Predcasna generalizace patternu

**Problem:** LLM navrhl Pattern P z jedine hry (game 20). V soucasne pipeline kazdy pattern detektor pouziva staticke prahy a vraci confidence i pri n=1 game.

**Soucasny stav:** `PatternDetector.detect_all()` iteruje pres patterny, pro kazdy pocita confidence na zaklade pomeru (napr. pocet vyhovujicich situaci / celkem situaci). Bez minima vzorku.

**Co chybi:**
- Minimum game requirements per pattern
- Confidence weighting by sample size
- Statistical significance test (napr. binomial test)

**Task K5.1 — Minimum game threshold**
```python
# v src/models/pattern.py
@dataclass
class PatternDef:
    id: str
    name: str
    description: str
    detection_method: str
    min_games: int = 3  # NOVE: minimalni pocet her pro detekci
    min_occurrences: int = 2  # NOVE: minimalni pocet vyskytu
```

Modifikovat `PatternDetector.detect_all()`: pokud `metadata.total_games < pattern.min_games`, skip pattern.

**Kriterium:** S 9 gameami by se Pattern P (min_games=3) jeste nespustil. Az pri >=3 hrach.

**Task K5.2 — Confidence weighting by sample size**
```python
# Upravit vypocet confidence v PatternDetector
def _weighted_confidence(self, raw_conf: float, n_games: int, n_occurrences: int) -> float:
    # Cim vice her, tim vyssi vaha
    game_factor = min(1.0, n_games / 10.0)
    occ_factor = min(1.0, n_occurrences / 5.0)
    return raw_conf * (0.3 + 0.7 * (game_factor * occ_factor))
```

**Kriterium:** S 1 hrou a 1 vyskytem = confidence capped na ~30% raw. S 10 hrami a 5 vyskpty = plna vaha.

### 3.2 Kategorie 6: Validace JSON struktury

**Problem:** Historicky JSON mel duplicitni ritualy, chybejici zaznamy. Writer generuje strukturu bez kontroly.

**Soucasny stav:** `KBWriter` zapisuje reporty + patterny do JSON/MD. Zadna validace pred zapisem.

**Co chybi:**
- Schema validace (JSON Schema nebo dataclass validation)
- Cross-reference (game_id v patterns existuji v analyses)
- Duplicita detection

**Task K6.1 — JSON Schema for pattern output**
```python
# Novy: src/kb/schemas.py nebo pouzit dataclass validation
PATTERN_SCHEMA = {
    "type": "object",
    "required": ["username", "date", "patterns", "total"],
    "properties": {
        "patterns": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["pattern_id", "pattern_name", "confidence", "severity"],
                "properties": {
                    "pattern_id": {"type": "string", "pattern": "^[A-Z][A-Z0-9]?$"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "severity": {"enum": ["critical", "high", "medium", "low"]},
                }
            }
        }
    }
}
```

**Kriterium:** Validace pred kazdym zapisem do KB. Pri selhani: log warning + zastavit zapis.

**Task K6.2 — Deduplikace pattern ID v reportu**
```python
# V PatternDetector.detect_all() nebo KB writeru
pattern_ids = [m.pattern_id for m in matches]
if len(pattern_ids) != len(set(pattern_ids)):
    log.error("Duplicate pattern IDs detected: %s", pattern_ids)
    # Merge duplicit nebo reject
```

### 3.3 Kategorie 7: Sanity checks po analyze

**Problem:** Pipeline neoveruje, ze vysledek analyzy je konzistentni s PGNaN hlavickou.

**Soucasny stav:** `GameSummary` obsahuje `result`, `color`, `opponent_name`. Diagnostician je pouzije, ale nevaliduje.

**Co chybi:**
- Kontrola: vysledek analyzy (blunder count) neni podezrele vysoky/nizky
- Kontrola: barva hrace odpovida vysledku
- Kontrola: ACPL neni extrem (napr. >500 nebo <5)

**Task K7.1 — Post-analysis sanity validator**
```python
# Novy: src/services/validator.py
def validate_analysis(analysis: GameAnalysis) -> list[str]:
    warnings = []
    # 1. Neni podezrele moc chyb
    if len(analysis.blunders) > len(analysis.moves) * 0.3:
        warnings.append(f"Too many blunders: {len(analysis.blunders)}/{len(analysis.moves)}")
    # 2. Barva a vysledek jsou konzistentni
    if analysis.game.color == "white" and analysis.game.result == "0-1":
        warnings.append("White player lost but result suggests black win - check")
    if analysis.game.color == "black" and analysis.game.result == "1-0":
        warnings.append("Black player lost but result suggests white win - check")
    # 3. ACPL v rozumnem rozsahu
    if analysis.total_acpl > 500:
        warnings.append(f"Suspiciously high ACPL: {analysis.total_acpl}")
    if analysis.total_acpl < 1 and len(analysis.moves) > 5:
        warnings.append(f"Suspiciously low ACPL: {analysis.total_acpl}")
    return warnings
```

Integrovat do `run_pipeline.py` a `diagnostician.py`.

**Kriterium:** Validace probehne po kazde analyze. Pri warning: log + pokracovat. Pri error: skip game.

### 3.4 Kategorie 4: Psychologicke atributy

**Problem:** LLM historicky generoval "metacognition: partial" jako spekulativni stitek.

**Soucasny stav:** Pattern detector negeneruje psychologicke atributy. Confidence je objektivni.

**Rozhodnuti:** Psychologicke atributy NEMAJI byt soucasti pipeline. Jsou to spekulace. Misto toho:

- Pattern detector vraci pouze objektivni metriky (cp_loss, frequency)
- LLM (v roli explainera) muze na zaklade techto dat formulovat hypotezy, ale musi je oznacit jako "hypothesis: ..."
- Zadny pattern nebo diagnosis nesmi obsahovat neoveritelne psychologicke tvrzeni

**Task K4.1 — Add hypothesis flag to pattern output**
```python
# v src/models/pattern.py
@dataclass
class PatternMatch:
    pattern_id: str
    pattern_name: str
    confidence: float
    severity: str
    evidence: list[str]  # objektivni dukazy (cp_loss, frequencies)
    hypothesis: str | None = None  # NOVE: volitelny interpretacni text, explicitne oznaceny
```

### 3.5 Kategorie 1-3: Uz reseno engine

Kategorie 1 (barva/vysledek), 2 (nadhodnoceni), 3 (podhodnoceni) jsou **jiz vyreseny** Stockfish engine + PGN parserem. Pro uplnost:

| Kontrola | Kde je implementovano |
|----------|----------------------|
| Barva hrace | `game_analyzer.py:_run_analyze_pgn()` — cte PGN headers White/Black |
| Vysledek partie | `game_analyzer.py:_run_analyze_pgn()` — cte Result header |
| Presne cp_loss | `engine_client.py:evaluate_move()` — Stockfish depth 12 |
| Klasifikace (blunder/mistake/inaccuracy) | `game_analyzer.py:_classify_move()` — Lichess standard 50/150/300 |

---

## 4. Chyby identifikovane v dnesnim LLM differential testu

Dnesni test (raw PGN vs Stockfish-assisted) odhalil **dalsi 3 kategorie** chyb, ktere historicka meta-analyza nezachytila:

| # | Nova kategorie | Popis | Reseni |
|---|---------------|-------|--------|
| 8 | **Koncovkova slepota** | LLM bez enginu nedokaze vyhodnotit koncovky — prehledl 62...Ra1 (blunder 324cp) a 65...a3 (mistake 200cp) | ✅ Stockfish resi — engine neni slepy ke koncovkam |
| 9 | **Falesna ACPL kalibrace** | LLM odhadl ACPL 50-70, realita 32-35 (odchylka +54%). Chyba je systematicka | ⚠️ Diagnostician ACPL je presny (pocitano z cp_loss), ale chybi srovnani s Lichess referenci |
| 10 | **Falesne pozitivni chyby** | 5 tahu oznaceno jako chyba, Stockfish ukazuje OK | ✅ Engine resi — klasifikace podle cp_loss |

**Task K9.1 — Add Lichess GUI reference comparison**
```python
# Novy nastroj: lichess_compare_acpl(username, game_ids)
# Porovna nase ACPL s Lichess GUI ACPL (pokud je k dispozici)
# Ulozi do KB jako referencni metriku
```

---

## 5. Implementacni harmonogram

### Phase 1 — Okamzite (1-2 dny)
| Task | Soubor | Odhad |
|------|--------|-------|
| K5.1: min_games threshold | `src/models/pattern.py`, `src/services/pattern_detector.py` | 30 min |
| K6.1: JSON schema | `src/kb/schemas.py` (novy) | 1 hod |
| K7.1: Sanity validator | `src/services/validator.py` (novy) | 1 hod |
| K4.1: Hypothesis flag | `src/models/pattern.py` | 20 min |

### Phase 2 — Strednedobe (1 tyden)
| Task | Soubor | Odhad |
|------|--------|-------|
| K5.2: Confidence weighting | `src/services/pattern_detector.py` | 1 hod |
| K6.2: Deduplikace | `src/services/pattern_detector.py`, `src/kb/writer.py` | 30 min |
| K9.1: Lichess reference | `src/tools/compare_acpl.py` (novy) | 2 hod |
| Rozsireni patternu (C, I, D, E, F, H, J-N) | `src/services/pattern_detector.py` | 4 hod |

### Phase 3 — Pozdni (1 mesic)
| Task | Odhad |
|------|-------|
| Backtesting: prepocteni vsech 21 historickych her Stockfishem | 3 hod (automatizovane pres pipeline) |
| Srovnavaci report: LLM baseline vs Stockfish pipeline | 2 hod |
| KB update: nova baseline s engine-validovanymi daty | 1 hod |

---

## 6. Kriterium uspechu

### Acceptance criteria (vsechny phase 1):

1. **Pattern s min_games=3 se nespusti na 1 game** — test: 1 game input -> 0 patterns
2. **KB JSON je validni proti schema** — test: schema validation pass
3. **Sanity validator odchyti opacnou barvu/vysledek** — test: force wrong color -> warning
4. **Hypothesis flag je vzdy None nebo explicitni string** — test: zkontrolovat vystup

### Long-term (phase 2-3):

5. **ACPL korelace s Lichess GUI > 0.95** (aktualne 0.97-0.99)
6. **Pattern precision > 80%** (aktualne ~50-80% dle patternu)
7. **Nova baseline z 9+ her nahradi starou baseline z 21 ruci analyzovanych**

---

## 7. Zaver

Z 10 identifikovanych kategorii chyb LLM je 5 jiz plne reseno Stockfish enginem (1, 2, 3, 8, 10).
Zbyva 5 kategorii (4-7, 9) k implementaci, rozclenenych do 3 fasi.
Plan pokryva 11 konkretnich tasku s odhadem ~2 dny prace + 1 mesic na backtesting.

Priorita: **K5.1 + K7.1 + K4.1** (phase 1) — tyto 3 tasky pokryvaji nejzavaznejsi kategorie (predcasna generalizace, sanity checks, spekulativni atributy) a lze je implementovat behem 2 hodin.

---
