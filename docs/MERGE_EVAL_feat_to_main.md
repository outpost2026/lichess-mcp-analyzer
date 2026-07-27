# Merge Evaluation: feat → main — lichess-analyzer-mcp

**Datum:** 2026-07-28 | **Evaluator:** LLM agent  
**Metoda:** Empirické runy 3 her (systeq) + test suite diff + code review

---

## 1. Výsledky empirických runů (3 hry, depth=14)

### Game A: `iVT2w2wl` (French Defense C02, win/white, blitz)
| Metrika | main | feat | Δ |
|---------|------|------|---|
| ACPL | 29.4 | 29.4 | 0 |
| Accuracy | 95.6% | 95.6% | 0 |
| Blunders | 1 | 1 | 0 |
| Mistakes | 0 | 0 | 0 |
| Inaccuracies | 2 | 2 | 0 |

### Game B: `JTi4Aen4` (Ponziani Opening, win/black, rapid)
| Metrika | main | feat | Δ |
|---------|------|------|---|
| ACPL | 32.7 | 32.7 | 0 |
| Accuracy | 95.1% | 95.1% | 0 |
| Blunders | 0 | 0 | 0 |
| Mistakes | 1 | 1 | 0 |
| Inaccuracies | 5 | 5 | 0 |

### Game C: `kPS7cYNV` (Vienna Game, loss/white, rapid)
| Metrika | main | feat | Δ |
|---------|------|------|---|
| ACPL | 45.9 | 45.9 | 0 |
| Accuracy | 93.1% | 93.1% | 0 |
| Blunders | 2 | 2 | 0 |
| Mistakes | 0 | 0 | 0 |
| Inaccuracies | 7 | 7 | 0 |

**Verdikt:** `feat` je **plně zpětně kompatibilní** — numerické metriky jsou identické.  
Žádná regrese v core analysis pipeline.

---

## 2. Test Suite Comparison

| Kritérium | main | feat |
|-----------|------|------|
| Počet testů | 51 | 68 |
| Passed | 51 (100%) | 67 (98.5%) |
| Failed | 0 | 1 |
| Nové testy | — | +17 (DBCL: win prob, BlunderFactSheet round-trip, narrative validator + Pattern N) |

### Jediný fail — analyzován a schválen

```
FAILED test_pattern_semantic_contract::test_all_patterns_have_detectors
  → Pattern I has no _detect_i method
```

**Příčina:** Commit `c928327` — Pattern I byl přesunut na `manual_only` a merge do I2.  
**Následek:** Kontraktní test nekoreluje. Je třeba buď: (a) přidat `skip_if_manual` do testu, nebo (b) restartovat Pattern I jako auto-detektor.  
**Závažnost:** LOW — jedná se o test, který neodráží novou architekturu. Ostatních 67 testů prochází.

---

## 3. Kvalitativní analýza změn (feat → main)

### 3.1 Nové funkce — DBCL Phase 2

| Komponenta | Soubor | Hodnocení |
|------------|--------|-----------|
| **BlunderFactSheet** | `models/analysis.py` | ⭐ Robustní model se serializací to_dict/from_dict, 7 podmodelů (BoardState, LegalMovesSummary, EngineLine, ...) |
| **Context window** | `models/analysis.py` | ±3 tahy kolem každého blundru — umožňuje hlubší analýzu |
| **Engine lines (multipv=3)** | `services/game_analyzer.py` | Top 3 engine variace s rankem — klíčové pro LLM coaching |
| **Per-blunder pattern detection** | `services/game_analyzer.py` | B/J/R/S/C detekce s evidence stringem — granularita na úrovni tahu |
| **Narrative validator** | `services/narrative_validator.py` | **204 řádků** — regex-based hallucination detection (check/square/eval/variation claims). Produkční kvalita. |
| **Win probability** | `services/game_analyzer.py` | Nahrazen `0.0` placeholder → lichess sigmoid (správná hodnota) |
| **Detector versioning** | `models/analysis.py` | `DETECTOR_VERSION = "DBCL-20260727-dev"` — audit trail |

### 3.2 Nové MCP nástroje

| Nástroj | Účel | Kvalita |
|---------|------|---------|
| `lichess_analyze_anonymous_session` | Dávková analýza anonymních her | ⭐ 209 řádků, label support, batch processing |
| `lichess_analyze_pending` | Analýza nezpracovaných her | ⭐ 109 řádků, detekuje pending games z index cache |
| `lichess_match_patterns` (enhanced) | Přidán `game_ids` parametr | Umožňuje pattern match pro anonymní/cached hry |

### 3.3 Vylepšení stávajícího kódu

| Změna | Kvalita |
|-------|---------|
| `lichess_client.py` +115 řádků: `fetch_game_by_id()`, `update_games_index_with_game()` | Umožňuje single-game workflow |
| `engine_client.py`: silent fail → logged warning | Lepší debuggovatelnost |
| `pattern_detector.py`: pattern I merged do I2 | Cleaner architecture |
| `validator.py` → `pattern_artifact_validator.py` | Konzistentní naming |

### 3.4 Dokumentace a artifacts

- CONTEXT_INJECT.md: v3.0 → v3.2 (3 update cykly)
- Nové coaching reporty (v3, deepseek, RUN_005)
- KROKY_po_RUN_003.md: 248 řádků follow-up plánu
- Lossy Compression Principle formalizován do 3 artifactů

---

## 4. Rizika a blokery

| Riziko | Závažnost | Mitigace |
|--------|-----------|----------|
| 1 failující test (Pattern I) | LOW | Opravit test před mergem — přidat `if pattern.manual_only: continue` |
| `games_index_cache` → file-based persistence | MEDIUM | Nový kód závisí na JSON cache souborech; cache migrace neřešena |
| DBCL Phase 2 není nasazená v produkci | LOW | Testy pokrývají round-trip serializaci; žádná runtime závislost na produkčních datech |
| `engine_client.py` silent fail fix → nový warning log | LOW | Zlepšení, žádné riziko |
| Berserk pagination (max_games 50→999) | LOW | Ošetřeno slicingem `page[:max_games]` |

---

## 5. Vyspělost branchí

### main — Stabilita
- 51/51 testů ✅
- Ověřeno na 3 reálných hrách ✅
- Produkční MCP server ✅
- **Score: 9/10** (chybí DBCL Phase 2)

### feat — Vyspělost
- 67/68 testů ✅ (1 známý, triviální fail)
- Ověřeno na 3 reálných hrách ✅
- 4 nové produkční nástroje ✅
- DBCL v1.1 architektura ✅
- Narrative validator (LLM hallucination guard) ✅
- Lossy Compression Principle formalizace ✅
- **Score: 9.5/10** (1 minoritní test fail)

---

## 6. Merge Recommendation

**DOPORUČENÍ: MERGE — podmíněný**

```
Merge:   ✅ SCHVÁLENO
Podmínka: ❗ Opravit 1 test (Pattern I manual_only skip)
Priorita:  HIGH
Typ:       Fast-forward (feat je 14 commitů ahead of main)
```

### Odůvodnění

1. **Žádná numerická regrese** — 3/3 hry produkují identické ACPL/accuracy/blunder metriky
2. **100→98.5% test pass rate** — jediný fail je kontraktní test, který neodráží intentional refactoring
3. **Nové funkce jsou produkční kvality** — BlunderFactSheet, narrative validator, anonymous session, analyze_pending
4. **Architektura je čistší** — pattern I merge do I2, renamed validator, better pagination
5. **Dokumentace je aktuální** — CONTEXT_INJECT, coaching reporty, principy

### Před-merge checklist
- [x] `git diff main..feat --stat` — 32 files, +3107/−324 lines
- [x] Games analysis comparison — identical
- [x] Test comparison — 68 tests (main: 51)
- [x] Code review — no security issues, no secrets, no API key leaks
- [ ] Fix `test_all_patterns_have_detectors` — add `if p.manual_only: continue`
- [ ] Verify CI pipeline (`.github/workflows/test.yml`) passes on feat

---

## 7. Výstupy v _TEMP_LICHES_MCP

```
_TEMP_LICHES_MCP/
├── main/
│   ├── iVT2w2wl.json  (ACPL 29.4, acc 95.6%, 1 blunder)
│   ├── JTi4Aen4.json  (ACPL 32.7, acc 95.1%, 0 blunders)
│   └── kPS7cYNV.json  (ACPL 45.9, acc 93.1%, 2 blunders)
└── feat/
    ├── iVT2w2wl.json  (identický)
    ├── JTi4Aen4.json  (identický)
    └── kPS7cYNV.json  (identický)
```
