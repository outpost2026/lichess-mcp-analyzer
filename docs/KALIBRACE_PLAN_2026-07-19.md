---
title: Kalibracni plan MCP pipeline — vrstvena architektura pro deterministicky chess pattern artifact
date: 2026-07-19
autor: opencode (deepseek-v4-flash-free)
ucel: Vyhodnoceni vsech MCP tools jako modularni pipeline pro tvorbu high-SNR, high-EROI chess pattern artifactu
vychozi-dokumenty:
  - Meta-analyza chyb LLM (historicke vlakno, N>8 iteraci)
  - LLM_DIFFERENTIAL_ANALYSIS_2026-07-19.md
  - docs/CONTEXT_A_ZAMER.md
  - docs/PHASE2_BUILD_PLAN.md
status: aktualizace
version: 2.0
---

# Kalibracni plan MCP pipeline — vrstvena architektura

## 1. Proc chess pattern artifact?

**Problem:** Chess pattern artifact (17 patternu A-Q1) vznikal rucni analyzou PGN s LLM + feedbackem autora (zkuseny hrac, ~2000 ELO). Proces: LLM cetl PGN, hledal vzory, autor korigoval halucinace. Vysledek: cenna, ale **stochasticka a neoveritelna** baseline.

**Reseni:** Soucasna MCP pipeline obsahuje deterministicky prvek (Stockfish 18 engine + lichess API). Ta muze posunout chess pattern artifact z oblasti pravdepodobnosti do oblasti **deterministicky podmienene analyzy** — kazdy pattern bude mit:

- **Detekcni pravidlo** formalizovane v kodu (ne v LLM promptu)
- **Kvantifikovatelny dopad** (prumerny cp_loss, frekvence, trend)
- **Statistickou validaci** (min sample size, confidence weighting)
- **Casovy trend** (zlepsuje se pattern nebo zhorsuje?)

To je **high EROI** a **high SNR** — zadny jiny znamy chess MCP server neprodukuje behavioralni pattern artifact na zaklade deterministickych dat.

---

## 2. Architektura: 5-vrstva modularni pipeline

```
                   ┌──────────────────────────────────────────┐
                   │           8. MCP TOOLS                   │
                   │  (lichess_fetch_games, analyze_game,      │
                   │   diagnose_player, match_patterns, ...)   │
                   └─────────────────────┬────────────────────┘
                                         │
                   ┌─────────────────────▼────────────────────┐
                   │   5. CHESS PATTERN ARTIFACT (vystup)      │
                   │  │  │  Programovy vektor hrace            │
                   │  │  │  + trendova data + hypotezy         │
                   │  └──┴────────────────────────────────────┘
                                         │
                   ┌─────────────────────▼────────────────────┐
                   │   4. DETERMINISTICKY ANALYZATOR           │
                   │  │  Diagnostician + PatternDetector       │
                   │  │  + Validator + StatisticalSignificance │
                   │  └───────────────────────────────────────┘
                                         │
                   ┌─────────────────────▼────────────────────┐
                   │   3. STOCKFISH ENGINE (depth 12-18)       │
                   │  │  per-move cp_loss, eval, best_move     │
                   │  │  + classification (blunder/mistake/...)│
                   │  └───────────────────────────────────────┘
                                         │
                   ┌─────────────────────▼────────────────────┐
                   │   2. LICHESS API GATEWAY                  │
                   │  │  berserk: PGN, profil, rating,         │
                   │  │  opening explorer, cloud eval          │
                   │  └───────────────────────────────────────┘
                                         │
                   ┌─────────────────────▼────────────────────┐
                   │   1. DATA LAYER                           │
                   │  │  Game cache (data/game_cache/)         │
                   │  │  SRS cards (data/srs_cards.json)       │
                   │  │  KB persistence (B2B-Knowledge-Base)   │
                   │  └───────────────────────────────────────┘
```

### 2.1 Popis vrstev

| Vrstva | Komponenty | Co dela | Deterministicka? |
|--------|-----------|---------|-----------------|
| **1. Data** | game cache, SRS, KB writer | Perzistentni ukladani + nacitani | ✅ |
| **2. Lichess API** | `lichess_client.py` | Stahovani PGN, profilu, statistik | ✅ (API response) |
| **3. Stockfish engine** | `engine_client.py` | Per-move evaluace (depth 12-18) | ✅ (deterministicky pri stejnem depth) |
| **4. Analyzator** | `game_analyzer.py`, `diagnostician.py`, `pattern_detector.py`, `validator.py` | Agregace + klasifikace + detekce | ✅ (formalni pravidla) |
| **5. Chess pattern** | `KB writer` → JSON vystup | Programovy vektor hrace | ⚠️ (zavisla na kvalite layer 4) |

### 2.2 MCP tools v kontextu vrstev

Kazdy z 8 MCP toolu pokryva jinou cast pipeline:

| Tool | Vrstva | Prinos k chess pattern artifactu |
|------|--------|----------------------------------|
| `lichess_fetch_games` | 2 | Vstupni data — seznam her k analyze |
| `lichess_analyze_game` | 3+4 | Per-move Stockfish data (cp_loss, eval) — surovina pro patterny |
| `lichess_analyze_position` | 3 | Ad-hoc pozicni analyza (neprispiva primo) |
| `lichess_opening_explorer` | 2 | Kontext k leaky openings (neprimy prinos) |
| `lichess_player_profile` | 2 | Rating, statistiky (kontext k patternum) |
| `lichess_diagnose_player` | 4 | Cross-game ACPL, fazove slabiny, leaky openings — prime vstupy |
| `lichess_match_patterns` | 4+5 | **Klicovy tool** — detekuje patterny A-Q1, generuje artifact |
| `lichess_workspace_info` | — | Pouze kontext pro LLM |

**Klicovy poznatek:** Celá pipeline je navrzena tak, aby kazdy tool prispival k chess pattern artifactu. Tool `lichess_match_patterns` je terminal point — vsechny ostatni tooly mu dodavaji data.

---

## 3. Data flow: jak vzniká chess pattern artifact

### 3.1 Surova data (vrstvy 1-3)

```
lichess API → GameAnalysis (per-move):
{
  "moves": [
    {
      "ply": 5,
      "move_san": "Bb5",
      "centipawn_loss": 66,
      "classification": "inaccuracy",
      "eval_before": 15,
      "eval_after": -54,
      "best_move_uci": "g1f3",
      "phase": "opening"
    },
    ...
  ],
  "total_acpl": 32.7,
  "blunders": [...],
  "phase_stats": {"opening": 22.1, "middlegame": 35.8, "endgame": 37.4}
}
```

### 3.2 Vektory (vrstva 4 — analyzator)

Z per-move dat se pocitaji **vektory** — kazdy vektor je jedna dimenze programoveho profilu hrace:

| Vektor | Vzorec | Příklad (Systeq, 9 her) |
|--------|--------|------------------------|
| **Preciznost** | ACPL + variance | 34.5 ± 18.2 |
| **Chybovost** | blunders/game | 1.78 blunderu/hru |
| **Phase imbalance** | ACPL(endgame) - ACPL(opening) | +24.9 (endgame slabs) |
| **Opening leak** | blunders v konkretnim otvoreni | Italian Two Knights: 5 blunderu/2 hry |
| **Color asymmetry** | | ACPL(white) - ACPL(black) | | 2.3 (minimalni) |
| **Tactical blindness** | Počet prehlednutych obeti / game | Vypocet z cp_loss pri captures |
| **Decision volatility** | | eval_before - eval_after | / move | 28.4 cp/tah |
| **Endgame conversion** | ACPL v koncovkach s +material | 44.8 (vysoka = neefektivni) |

### 3.3 Pattern detection (vrstva 4-5)

Kazdy pattern ma **formalni detekcni pravidlo** napsane v kodu:

```
Pattern B (Automatic Grab):
  Detekce: Tah je capture AND centipawn_loss > 200 AND eval_before > 0
  → Hrac bral automaticky bez vypoctu, pritom mel jinou, lepsi moznost

Pattern P (Visual Misrecognition):
  Detekce: centipawn_loss > 150 AND best_move je capture/check AND
            eval_before - eval_after > 200
  → Hrac prehledl takticky motiv (obet, vidlicku)

Pattern Q (Active Defense):
  Detekce: hrac je v obrane (eval < -150) AND jeho tah je utocny
            (zlepsuje jeho pozici o >50cp ale stale je v defenzive)
  → Hrac se brani aktivne misto pasivniho cekani
```

**Tim se chess pattern artifact meni z** "LLM si mysli, ze hrac ma sklon k X" **na** "Engine dokazuje, ze hrac v Y situacich ztratil v prumeru Z cp, coz odpovida patternu W s confidence C".

---

## 4. Determinismus vs stochastika: kvantifikace prinosu

Dnesni LLM differential test (2 hry, raw PGN vs Stockfish) umoznuje kvantifikovat, co presne engine prinas:

| Aspekt | LLM-only (stochasticka) | Stockfish pipeline (deterministicka) | Zlepseni |
|--------|------------------------|-------------------------------------|----------|
| **ACPL precision** | ±25-35cp odchylka | ±0cp (presna hodnota) | ∞ |
| **Blunder detection** | 50% (3/6 prehlednuto) | 100% | 2x |
| **False positives** | 5 chybne oznacenych | 0 | ∞ |
| **Koncovkova analyza** | Slepota (2 blundery prehlednuty) | Plna presnost | ∞ |
| **Skalovatelnost** | ~30 min na hru (rucni) | ~2s na hru (cached) | 900x |

**Duvera v pattern artifact:**
- **LLM-only baseline:** Confidence v pattern = ~50-70% (autor musel korigovat)
- **Deterministicka pipeline:** Confidence v pattern = az 95% (statisticky validovano)

---

## 5. High-EROI vystupy pipeline

### 5.1 Chess pattern artifact (primarni — nejoriginalnejsi)

Unikatni vystup, ktery zadny jiny MCP server neprodukuje:

```json
{
  "username": "Systeq",
  "date": "2026-07-19",
  "total_games": 9,
  "total_acpl": 34.5,
  "program_vector": {
    "precision": {"acpl": 34.5, "variance": 18.2},
    "phase_balance": {"opening": 19.9, "middlegame": 34.9, "endgame": 44.8},
    "color_asymmetry": 2.3,
    "decision_volatility": 28.4,
    "tactical_blindness_rate": 0.22
  },
  "patterns": [
    {
      "pattern_id": "Q",
      "pattern_name": "Active Defense",
      "confidence": 0.72,
      "severity": "low",
      "games_analyzed": 9,
      "occurrences": 4,
      "avg_cp_loss": 108,
      "evidence": [
        "Ply 26 (A96bH7jI): Bh5 in defensive position, loss 93cp",
        "Ply 48 (A96bH7jI): Qg5 instead of Qd5, loss 123cp"
      ],
      "hypothesis": "Hrac preferuje aktivni obranu pred pasivnim cekanim, coz je vetsinou spravne, ale nekdy prehlidne jednodussi pasivni reseni.",
      "trend": "stable",
      "first_seen": "2026-07-18",
      "last_seen": "2026-07-19"
    }
  ],
  "leakiest_openings": [
    {"name": "Italian: Two Knights Fritz", "games": 2, "blunders": 5, "acpl": 52.1}
  ],
  "meta": {
    "pipeline_version": "2.0",
    "engine": "Stockfish 18 depth 12",
    "games_analyzed": 9,
    "cache_hit_ratio": 1.0
  }
}
```

**Proc high EROI?** Tento artifact je:
- **Unikatni** — zadny jiny nastroj nekombinuje behavioralni patterny + ACPL vektor + hypotezy
- **Deterministicky** — kazda hodnota je dohledatelna ke konkretnimu tahu
- **Trendovatelny** — dalsi analyzy budou ukazovat zlepseni/zhorseni
- **Prenositelny** — stejna architektura muze detekovat patterny v jinych domenach

### 5.2 Sekundarni vystupy (take high EROI)

| Vystup | EROI ratio | Proc |
|--------|------------|------|
| **Diagnoza (MD report)** | 8/10 | Lidsky citelny, akcni — "trenuj Italian Two Knights" |
| **SRS karty** | 7/10 | Spaced repetition na konkretni chyby |
| **Pattern trend report** | 8/10 | Unikatni — zadny jiny nastroj nesleduje casovy vyvoj patternu |

---

## 6. Implementacni plan — kategorizace a harmonogram

### 6.1 Kategorie chyb LLM mapovane na implementaci

| Kategorie | Vazba na chess pattern | Reseno | Zbyva | Task ID |
|-----------|----------------------|--------|-------|---------|
| Zamena barvy/vysledku | Zkresluje metadata patternu | ✅ PGN parser | -- | -- |
| Nadhodnoceni kvality | Falesne pozitivni patterny | ✅ Stockfish cp_loss | -- | -- |
| Podhodnoceni chyb | Chybejici pattern evidence | ✅ Stockfish depth 12 | -- | -- |
| Falesne psych. atributy | Pattern hypothesis musi byt oznaceny | ⚠️ | Hypothesis flag | K4.1 |
| Predcasna generalizace | Pattern z 1 hry = noise | ❌ | min_games, confidence weighting | K5.1, K5.2 |
| JSON nekonzistence | Artefakt musi byt strojove citelny | ❌ | JSON schema, dedup | K6.1, K6.2 |
| Sanity checks | Artefakt musi davat smysl | ❌ | Validator | K7.1 |
| Koncovkova slepota | Zkresluje endgame ACPL | ✅ Stockfish | -- | -- |
| Falesna ACPL kalibrace | Zkresluje programovy vektor | ⚠️ | Lichess reference | K9.1 |
| Falesne pozitivni chyby | Zkresluje blunder count | ✅ Stockfish | -- | -- |

### 6.2 Phase 1 — Zaklad artifactu (2-3 dny)

Priorita: zabezpecit, aby artifact nebyl kontaminovan falesnymi signaly.

| Task | Co | Soubor | Odhad | Dopad na chess pattern |
|------|----|--------|-------|------------------------|
| **K5.1** | min_games threshold per pattern | `src/models/pattern.py`, `pattern_detector.py` | 30 min | Eliminuje patterny z 1-2 her (noise) |
| **K4.1** | hypothesis flag v PatternMatch | `src/models/pattern.py` | 20 min | Oddeli objektivni data od spekulaci |
| **K7.1** | Post-analysis sanity validator | `src/services/validator.py` (novy) | 1 hod | Zachyti nekonzistentni analyzy |
| **K6.1** | JSON schema pro KB output | `src/kb/schemas.py` (novy) | 1 hod | Zaruci strojovou citelnost artifactu |

### 6.3 Phase 2 — Vylepseni artifactu (1 tyden)

| Task | Co | Soubor | Odhad | Dopad |
|------|----|--------|-------|-------|
| **K5.2** | Confidence weighting by sample size | `pattern_detector.py` | 1 hod | SNR confidence |
| **K6.2** | Deduplikace pattern ID | `pattern_detector.py`, `kb/writer.py` | 30 min | Strukturalni cistota |
| **P1** | Rozsireni patternu (C, D, E, F, H, I, J-N) | `pattern_detector.py` | 4 hod | Vice dimenzi programoveho vektoru |
| **P2** | Program vector generator | `diagnostician.py` extension | 2 hod | Nova struktura artifactu (sekce 5.1) |
| **K9.1** | Lichess ACPL reference | `tools/compare_acpl.py` | 2 hod | Kalibracni metrika |

### 6.4 Phase 3 — Trendy a backtesting (1 mesic)

| Task | Odhad | Dopad |
|------|-------|-------|
| Backtesting 21 historickych her Stockfishem | 3 hod | Nova, engine-validovana baseline |
| Trend detection (first_seen, last_seen, slope) | 2 hod | Casovy vyvoj patternu |
| Cross-player comparison (volitelne) | 4 hod | Benchmark proti ostatnim hracum |
| KB update: nova baseline artifactu | 1 hod | Produkcni nasazeni |

---

## 7. MCP tools jako pipeline: vizualizace

```
LICHESS API ──► lichess_fetch_games
                      │
                      ▼
               lichess_analyze_game ──► game cache (data/game_cache/)
                      │                       │
                      ▼                       │
               lichess_diagnose_player ───────┤
                      │                       │
                      ▼                       ▼
               lichess_match_patterns ◄── cached GameAnalysis
                      │
                      ▼
               CHESS PATTERN ARTIFACT (JSON)
                      │
                      ├──► KB writer (B2B-Knowledge-Base)
                      │       └── 02_ANALÝZY/02_chess/
                      │       └── 04_KNOWLEDGE_BASE/02_chess/
                      │
                      └──► LLM (explainer role)
                              └── "Na zaklade dat: hrac ma pattern Q... 
                                   Hypoteza: preferuje aktivni obranu..."
```

**Klicovy bod:** LLM je v teto architekture az **posledni** clen pipeline — neanalyze, neprodukuje data. Pouze **interpretuje** jiz overena deterministicka data. To je opak puvodniho postupu (LLM analyzoval PGN → autor korigoval → vznikl pattern).

---

## 8. Kriterium uspechu

### Kvantitativni metriky

| Metrika | Soucasna hodnota | Cil po Phase 1 | Cil po Phase 3 |
|---------|-----------------|----------------|----------------|
| **Pattern precision** | ~50-80% (zavisi na patternu) | >75% | >90% |
| **Pattern recall** | ~60% (nektere patterny chybi) | >70% | >85% |
| **ACPL correlation s Lichess** | 0.97-0.99 | >0.95 | >0.98 |
| **False positive rate** | ~20% | <10% | <5% |
| **Cache hit ratio** | 100% (po prvnim runu) | >95% | >95% |
| **Pipeline runtime (10 her)** | 2s (cached) / ~10 min (fresh) | <3s / <12 min | <3s / <12 min |

### Acceptance criteria

1. **Chess pattern artifact je generovan vyhradne z deterministiclych dat** — zadna LLM-invented evidence
2. **Hypothesis flag je vzdy "hypothesis:" nebo None** — artifact nelze zamnenit s faktem
3. **Kazdy pattern ma min_games a min_occurrences** — pattern z 1 hry neni detekovan
4. **Program vector je kompletni** — vsech 6 vektoru (precision, phase, color, volatility, tactical, endgame)
5. **Artifact je validni JSON** — prosel schema validaci

---

## 9. Zaver a dalsi postup

### Aktualni stav vyvoje

```
Phase 0 (hotovo):  ✦ 8 MCP tools implementovano
                   ✦ Stockfish 18 depth 12
                   ✦ Game-level cache (2s runtime)
                   ✦ 6/17 pattern detectoru
                   ✦ Diagnostician + KB writer

Phase 1 (plan):    🞄 K5.1, K4.1, K7.1, K6.1 (2-3 dny)
                   🞄 Chess pattern artifact z deterministickych dat
                   🞄 Sanity checks + schema validace

Phase 2 (plan):    🞄 Rozsireni na 17 patternu
                   🞄 Program vector generator
                   🞄 Confidence weighting
                   🞄 Lichess ACPL reference

Phase 3 (plan):    🞄 Backtesting 21 historickych her
                   🞄 Trend detection
                   🞄 Nova baseline artifactu
```

### Doporuceny dalsi krok

Implementovat Phase 1 — 4 tasky, ~2-3 dny prace. Po Phase 1 bude chess pattern artifact produkovat **overitelne, deterministicke, strukturovane vystupy** s minimalnim rizikem kontaminace falesnymi signaly.

---

## 10. Dodatky

### A. Slovnicek pojmu pro chess pattern artifact

| Pojem | Vyznam | Pripad pouziti |
|-------|--------|----------------|
| **ACPL** | Average Centipawn Loss Per Move | Hlavni metrika preciznosti |
| **Programovy vektor** | Vicerozmerny profil hrace | 6 dimenzi (precision, phase, color, volatility, tactical, endgame) |
| **Pattern** | Behaviorální vzor detekovany formalnim pravidlem | Jeden ze 17 (A-Q1) |
| **Confidence** | 0-1, statistical significance weighted by sample size | Validita patternu |
| **Hypothesis** | Interpretacni text, explicitne oznaceny | Oddeleni faktu od spekulace |
| **Trend** | stable/improving/worsening | Casovy vyvoj |
| **EROI** | Efektivita vynalozenoho usili | Priorita implementace |

### B. Vazba na existujici dokumentaci

- **CONTEXT_A_ZAMER.md** — celkovy kontext projektu (section 4: reserse, section 5: architektura)
- **PHASE2_BUILD_PLAN.md** — puvodni build plan (FSRS, L2 Resources)
- **LLM_DIFFERENTIAL_ANALYSIS_2026-07-19.md** — experimentalni potvrzeni potreby engine
- **README.md** — Inspirace a zdroje (credits k library a inspiracnim serverum)

---

