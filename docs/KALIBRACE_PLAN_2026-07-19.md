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
version: 2.3
changes-v2.2:
  - Sekce 2.6: Tri operacni rezimy pipeline (Sharp Descent / Orbital Search / Disentanglement)
  - Sekce 2.7: Reality Calibration Loop — zpetnovazebni smycka
  - Sekce 3.4: TOT (Tip-of-the-Tongue) stav — treti moznost v pattern detection
  - Sekce 6.3: Task K10.1 (Konsolidacni protokol), K11.1 (TOT + Gated konsolidace)
  - Sekce 8: Acceptance criteria #7 (TOT), #8 (offline konsolidace)
  - Zdroj: 05_EPISTEMIKA/00_kompresni_realismus/ (SYSTEQ neuroarchitektura)
---

# Kalibracni plan MCP pipeline — vrstvena architektura

## 0. Filozofie autora: determinismus + LLM abstrakce

### 0.1 Princip (z profilove landing page)

> **"Fyzická realita je jedinečná absolutní metrika pravdy. Digitální svět je jen její abstrakce."**
>
> *"Nástroje, které tvořím s pomocí AI, slouží k pomyslnému hledání jehly v kupce sena = k datové analýze založené na filtraci vaty a všudypřítomného šumu."*
>
> *"Skutečná seniorita se měří úrovní abstrakce problému, který dokážete řešit."*

Autor kombinuje **dva svety**:

| Svet | Co to je | V pipeline | Priklad |
|------|---------|------------|---------|
| **Determinismus** | Strojove parsovana data, fyzicka realita jako metrika | Stockfish engine, lichess API, game cache, cp_loss | `engine_client.py` — per-move evaluace |
| **LLM abstrakce** | Prace se slovy a symboly na pripravenych artefaktech | Pattern detection, hypothesis, treninkova doporuceni | `lichess_match_patterns` → narativni vystup |

**Klicova teze:** LLM modely jsou v pripade **constrains a predem upravenych vstupu** (prevedenych na LLM-friendly artefakty) schopny naplno vyuzit svych schopnosti prace se slovy a symboly. Bez techto constrains produkuji stochasticky sum.

### 0.2 Jak se to projevuje v architektuře

| Autoruv princip | Implementace v pipeline | Odkud to vime |
|----------------|------------------------|---------------|
| Realita = metrika pravdy | Stockfish cp_loss jako ground truth pro kazdy tah | LLM differential test (odchylka +25-35cp bez enginu) |
| Filtrace sumu | Game-level cache eliminuje variance mezi runy | 21 min → 2 sec, 100% reprodukovatelne |
| Abstrakce problemu | Pattern library (A-Q1) jako behavioralni abstrakce nad cp_loss | Analyticky obsah, ne jen "prumer chyb" |
| Call to action | KB report + SRS karty + hypotezy = co delat | Diagnostician: "trenuj Italian Two Knights" |
| Golden master | Lichess GUI reference pro ACPL kalibraci | MAE 3.9 oproti Lichess depth 18 |
| Modularita, testovatelnost | 8 MCP tools, kazdy samostatne pouzitelny | 6/17 pattern detectoru, cache, diagnostician |

### 0.3 Vazba na chess pattern artifact

Chess pattern artifact je **konkretni realizaci teto filozofie**:

1. **Deterministicka vrstva** (engine + API) produkuje cp_loss, eval, klasifikaci — "realitu"
2. **LLM vrstva** (pattern detector + hypothesis generator) produkuje abstrakci — "vyznam"
3. **Artifact** (JSON output) je LLM-friendly struktura, se kterou muze LLM dale pracovat

Bez kroku 1 = stochasticita a halucinace (puvodni postup).
Bez kroku 2 = pouze cisla bez vyznamu (surovy Stockfish dump).
S obema = high SNR, high EROI.

---

## 1. Proc chess pattern artifact?

**Problem:** Chess pattern artifact (17 patternu A-Q1) vznikal rucni analyzou PGN s LLM + feedbackem autora (zkuseny hrac, ~2000 ELO). Proces: LLM cetl PGN, hledal vzory, autor korigoval halucinace. Vysledek: cenna, ale **stochasticka a neoveritelna** baseline — odporuje principu "realita = metrika pravdy".

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

### 2.3 Deterministicka vrstva → LLM abstrakce (tok dat)

Toto je **klicovy architektonicky princip** vyplivajici z autorovy filozofie:

```
┌─────────────────────────────────────────────────────────────────┐
│  DETERMINISTICKA VRSTVA (vrstvy 1-4)                            │
│                                                                  │
│  Stockfish engine ──► cp_loss, eval, best_move                   │
│       +             ──► blunder/mistake/inaccuracy klasifikace    │
│  Lichess API        ──► ACPL, phase_stats, leaky openings         │
│                                                                  │
│  Vystup: ----------------------------------------------------   │
│  JSON s cisly, zadny text, zadna interpretace                   │
│  "Hrac v tahu 5 ztratil 66cp. Best move byl Nf3." = fakt       │
│  Overitelno: kdykoliv, kazdym Stockfishem, stejny vysledek      │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  │ (data jsou predana jako
                                  │  LLM-friendly artifact)
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│  LLM ABSTRAKCE (vrstva 5 — hypotezy + narace)                   │
│                                                                  │
│  Pattern detector     ──► "Toto odpovida patternu Q: aktivni     │
│  + LLM explainer          obrana s confidence 0.72"              │
│                                                                  │
│  Vystup: ----------------------------------------------------   │
│  Text + hypotezy                                                │
│  "Hypothesis: Hrac preferuje aktivni obranu pred pasivnim       │
│   cekanim, coz je vetsinou spravne, ale nekdy prehlidne         │
│   jednodussi pasivni reseni."                                   │
│  Overitelno: pouze proti Stockfish datum (pattern match)        │
└─────────────────────────────────────────────────────────────────┘
```

**Pravidlo:** LLM nikdy negeneruje surova data (cp_loss, ACPL, klasifikaci). LLM pouze **interpretuje** jiz overena deterministicka data. Toto pravidlo je vynuceno architekturou — LLM nema pristup k engine ani API.

### 2.4 Call to action — kazdy vystup musi vest k rozhodnuti

Druhy klicovy princip: pipeline negeneruje "zajimave informace", ale **akcni vystupy**.

| Vystup | Call to action | Kdo rozhoduje |
|--------|---------------|---------------|
| Diagnoza: "ACPL 34.5, fazove slabiny: endgame" | "Trenuj koncovky — specificky pesecne koncovky s vezi" | LLM na zaklade diagnostician dat |
| Pattern Q: aktivni obrana (conf 0.72) | "Pred obrannym tahem si rekni: je pasivni reseni jednodussi?" | LLM na zaklade pattern detector dat |
| Leaky opening: Italian Two Knights (5 blunderu) | "Prostuduj variantu Italian: Two Knights Fritz pred dalsi hrou" | LLM na zaklade leaky openings |
| Blunder: 62...Ra1 (324cp) — SRS karta | "Opakuj FEN pozici za 3 dny (FSRS)" | SRS engine |

**Zadny vystup nesmi byt "pouze informativni"** (poruseni EROI). Toto je prinos LinkedIn analyzatoru (viz landing page: "reagovat, nereagovat, zvážit, doučit se") aplikovany na sachovou analyzu.

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

### 3.2 Vektory (vrstva 4 — analyzator + komprese)

| Entropie a komprese (Mikolov — nova dimenze) | | |

Z per-move dat se pocitaji **vektory** — kazdy vektor je jedna dimenze programoveho profilu hrace. Novy rozmer: entropie a komprese kazdeho patternu.

| Vektor | Původ | Vazba na Mikolov |
|--------|-------|------------------|
| **Kompresni pomer** | CompressibilityValidator | Pattern je validni = komprimuje data |
| **Entropy reduction** | raw_entropy - pattern_entropy | Cim vic entropie pattern odstrani, tim je silnejsi signal |
| **Exception ratio** | exceptions / matches | Occam: priority jednodussiho modelu s mene vyjimkami |



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

### 3.4 TOT (Tip-of-the-Tongue) stav v pattern detection

Z neuroarchitektury "mozek jako geometricky procesor": ne kazdy pattern match je binary. Pridat treti stav:

| Stav | Confidence | Vyhodnoceni | Akce |
|------|-----------|-------------|------|
| **MATCH** | > 0.6 | Pattern jednoznacne detekovan | Pridej do artifactu |
| **TOT** | 0.3-0.6 | "Vypada jako pattern X, ale neni jistota" | Pridej jako candidate + TOT flag |
| **NO_MATCH** | < 0.3 | Pattern neni pritomen | Ignoruj |

**TOT v artifactu:**
```json
{
  "pattern_id": "Q?",
  "pattern_name": "Active Defense (TOT)",
  "confidence": 0.42,
  "tot": true,
  "reason": "Pouze 2 vyskpty ve 3 hrach, ale struktura odpovida patternu Q (aktivni obrana s cp_loss > 100)"
}
```

**Prinos:** Detekce novych patternu drive, nez maji statistickou silu — Rezim 3 (Disentanglement) v pipeline.

---

## 4. Determinismus vs stochastika: kvantifikace prinosu

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
      "confidence": 0.76,
      "confidence_breakdown": {
        "compression_ratio": 227.3,
        "entropy_reduction": 0.58,
        "compression_score": 0.85,
        "entropy_score": 0.58,
        "sample_score": 0.44
      },
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
| **K8.1** | CompressibilityValidator | `src/services/compressibility_validator.py` (novy) | 1 hod | Rekalibrace confidence podle komprese + small-N robustnost |

### 6.3 Phase 2 — Vylepseni artifactu (1 tyden)

| Task | Co | Soubor | Odhad | Dopad |
|------|----|--------|-------|-------|
| **K5.2** | Confidence weighting by sample size | `pattern_detector.py` | 1 hod | SNR confidence |
| **K6.2** | Deduplikace pattern ID | `pattern_detector.py`, `kb/writer.py` | 30 min | Strukturalni cistota |
| **P1** | Rozsireni patternu (C, D, E, F, H, I, J-N) | `pattern_detector.py` | 4 hod | Vice dimenzi programoveho vektoru |
| **P2** | Program vector generator | `diagnostician.py` extension | 2 hod | Nova struktura artifactu (sekce 5.1) |
| **K9.1** | Lichess ACPL reference | `tools/compare_acpl.py` | 2 hod | Kalibracni metrika |
| **K10.1** | Konsolidacni protokol (offline pattern update) — periodic job, ktery prepocita pattern library z novych her, aktualizuje compression_ratio a confidence trend | `src/services/consolidator.py` (novy) | 2 hod | Dynamicka pattern library (ne staticka) |
| **K11.1** | TOT flag + Gated konsolidace — TOT stav v pattern detection (confidence 0.3-0.6 = kandidat) + gating: novy pattern vyzaduje lidsky souhlas pred zarazenim do detection rules | `pattern_detector.py`, `src/services/gate.py` (novy) | 1.5 hod | Signal detection drive, nez ma statistickou silu |

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

### 7.1 Call to action: kazdy vystup pipeline

Kazda vrstva pipeline produkuje vystup s explicitnim "co s tim":

| Vrstva | Vystup | Call to action signal | Prijemce |
|--------|--------|----------------------|----------|
| **3. Engine** | cp_loss, eval | "Tah X ztratil Y cp" (fakt) | Vrstva 4 |
| **4. Analyzator** | ACPL, fazove slabiny | "Endgame ACPL 44.8 = nejslabsi faze" | Vrstva 5 |
| **5. Pattern** | Pattern Q, conf 0.72 | "Hypothesis: aktivni obrana — overit pasivni alternativy" | LLM → hrac |
| **KB report** | Diagnoza v MD | "Trenuj Italian Two Knights (5 blunderu/2 hry)" | Hrac |
| **SRS** | Karty k opakovani | "Pozici z tahu 62 si zopakuj za 3 dny" | Hrac |

**Zadny vystup nesmi byt "pouze informativni"** bez dalsiho postupu.

### 2.5 Kompresni validator (Mikolov) — confidence podle komprese

**Problem:** Soucasny pattern artifact vznikl z N < 25 her. Statisticka autorita je nizka. Kompresni filozofie Tomase Mikolova (redukce entropie, Occamova britva) nabizi alternativu: pattern je validni, pokud **komprimuje data lepe nez surova data**.

**Formalne:**
```
compression_ratio = raw_cost / pattern_cost
kde:
  raw_cost = sum(L(move_data) for all analyzed games)
  pattern_cost = L(pattern_definition) + sum(L(exceptions))

pattern je signal: compression_ratio > 1.5
pattern je silny signal: compression_ratio > 10.0
pattern je noise: compression_ratio < 1.0
```

**Novy confidence vzorec:**
```
final_confidence = 0.5 × compression_score 
                + 0.3 × entropy_score 
                + 0.2 × sample_score
```

Kde compression_score ma nejvyssi vahu — pattern, ktery komprimuje data, je validni i pri malem N. Toto resi klicovy problem baseliny: pattern Q s pomerem 227:1 je relevantni i pri 9 hrach.

**Co to meni:**
- Pattern confidence uz neni "pocet vyskytu / N" ale "kompresni sila × entropie × sample"
- Patterns s vysokym compression_ratio = automaticky vyssi confidence (i pri N < 25)
- Patterns s nizkou kompresi (= mnoho vyjimek) = nizsi confidence (i pri N > 50)
- Pridan CompressibilityValidator (vrstva 4.5) jako samostatna komponenta

### 2.6 Tri operacni rezimy pipeline (Mikolov-SYSTEQ)

Z neuroarchitektury "mozek jako geometrický procesor" (SYSTEQ, 2026) — kazdy vstup pipeline (sada her) ma implicitni entropii, ktera urcuje rezim zpracovani:

| Rezim | Entropie | Kognitivni naklad | Co to znamena v pipeline | Priklad |
|-------|----------|-------------------|--------------------------|---------|
| **R1: Sharp Descent** | Nizka (ACPL < 50, variance < 15) | Nizky | Cache hit, znamy pattern, rychla inference | Hrac s 20 analyzovanymi hrami, pattern Q potvrzeny |
| **R2: Orbital Search** | Stredni (ACPL 50-100, variance < 30) | Vysoky | Nove hry, cache miss, candidate pattern s nizkou conf | 2 nove hry, pattern podezreni ale neni jistota |
| **R3: Disentanglement** | Vysoka (nova strategie, neznamy pattern) | Masivni | Vystup: navrh noveho patternu k validaci | Hrac pouziva strategii, ktera neodpovida zadnemu z 17 patternu |

**Implementace:** Do pipeline pridat explicitni `entropy_switch` — pred kazdou analyzou zmerit entropii vstupu (pocet novych her, variance ACPL, cache hit ratio) a zvolit rezim.

### 2.7 Reality Calibration Loop (zpetnovazebni smycka)

Z axiomu SYSTEQ Kernel v1.0 — kazdy vystup pipeline musi byt overitelny a zpetne kalibrovatelny:

```
Analyza → Vystup → Intervence (hrac/trenink) → Dalsi analyza → Mereni zmeny → Update modelu
```

**V chess kontextu:**
1. Pipeline detekuje pattern Q (conf 0.76)
2. Hrac obdrzi: "trenuj pasivni alternativy v obranych pozicich"
3. Hrac odehraje dalsich 10 her
4. Pipeline zmeri: changes in pattern Q frequency/severity
5. Pokud pattern Q klesl → pattern validni, conf se zvysi
6. Pokud pattern Q stejny nebo horsi → pattern byl falesny, conf se snizi

**Implementace:** Do pattern artifact pridat `calibration_history` — pole zmen confidence v case po kazde dalsi analyze.

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
6. **Kazdy pattern ma compression_ratio > 2:1** nebo je oznacen jako "low_signal" (prevence noise)
7. **Pattern detection podporuje TOT stav** (confidence 0.3-0.6 = kandidat, ne MATCH/NO_MATCH binary) — zachyceni novych patternu driv
8. **Konsolidacni protokol bezi offline** (pattern library se nemeni za behu, pouze v planovanych cyklech) — stabilita + reprodukovatelnost

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
                    🞄 Konsolidacni protokol (K10.1)
                    🞄 TOT + Gated konsolidace (K11.1)

Phase 3 (plan):    🞄 Backtesting 21 historickych her
                    🞄 Trend detection
                    🞄 Reality Calibration Loop
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

### C. Reference: Mikolov, T. — Komprese jako inteligence

Tomáš Mikolov (word2vec, RNN, kompresní teorie inteligence) — jeho filozofie aplikovaná na chess pattern artifact:

| Koncept | Implementace | Kontrola |
|---------|-------------|----------|
| **Redukce entropie** | Pattern komprimuje N her do jednoho behavioralniho vzoru | compression_ratio v PatternMatch |
| **Kompresni model reality** | Chess pattern artifact je model hrace | MSE(pattern) vs MSE(prumer) |
| **Ztratova komprese** | Jednotlive chyby (sum) jsou odstraneny, vzory (signal) zachovany | Exception ratio < 20% |
| **Occamova britva** | Ze dvou patternu preferujeme jednodussi | compression_ratio jako metric |

**Klicovy prinos:** Tento ramec umoznuje priznat patternum relevanci i pri N < 25, pokud jejich kompresni pomer > 2:1. Odpadá statistická slepá ulička "s málo hrami nemůžeme nic říct".

Viz samostatny dokument: `docs/MIKOLOV_KOMPRESE_V_PATTERN_ARCHITEKTURE.md`

---

