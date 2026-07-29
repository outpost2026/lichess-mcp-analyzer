# Deep Semantic Analysis: ELO jako kompresní pattern + ETL pipeline pro statistický pool

**Datum:** 2026-07-28
**Kontext:** Devova teze o N=kategoriích, ELO jako kompresním patternu a doménově agnostickém ETL řešení
**Rozsah:** Hloubková analýza + rešerše existujících nástrojů + implikace pro architekturu

---

## [COT] Sémantický rozbor devovy teze — 5 klíčových konceptů

### 1. N1/N2/N3 jsou relativní kategorie z pozice autora

**Teze:** Současné kategorie N1 (autor win), N2 (autor loss), N3 (draw) nejsou absolutní vlastnosti her — jsou to labeling artifacts definované perspektivou autora.

**Důsledek — symetrie perspektiv:**

```
Author perspective:  Opponent perspective:
N1 (autor win)     = N2 (opponent loss)
N2 (autor loss)    = N1 (opponent win)
N3 (draw)          = N3 (draw)
```

**Problém, který to řeší:** Pokud analyzujeme jen author perspective, vidíme jen jednu stranu rovnice. N2 opponents (kteří porazili autora) jsou z authorovy perspektivy "silnější hráči." Ale z OPPONENTovy perspektivy jsou to prostě "jejich N1 hry" — hry které vyhráli, možná proto že autor hrál podprůměrně, ne protože oni hráli nadprůměrně.

**Dual-perspective pipeline (jak jsme ji implementovali):**

```
Game k9a1IXvp:
  Author (white): ACPL 32.1, B=0  → perspective: "I played well but lost"
  Opponent (black): ACPL 16.1, B=0 → perspective: "I played near-perfectly and won"
  
  Závěr: Toto není "autorova chyba" — to je "opponent hrál lépe"
  
Game tDcFRclj:
  Author (white): ACPL 45.2, B=2  → perspective: "I self-destructed"
  Opponent (black): ACPL 34.8, B=0 → perspective: "I waited and opponent blundered"
  
  Závěr: Toto je "autorova chyba"
```

**Implikace pro nástroje:** Každý nástroj musí pracovat s dual-perspective daty. Nestačí říct "ACPL 52.0" — musíme vědět "ACPL 52.0 z OPPONENTovy perspektivy v hrách, které opponent prohrál."

### 2. N3 (draw) musí existovat jako kategorie — i když je aktuálně 0

**Teze:** I když aktuální dataset má N3=0, architektura musí kategorii draw podporovat.

**Proč je draw důležité:**
- **High-SNR data point:** Remíza indikuje ratingovou paritu — oba hráči hráli na podobné úrovni.
- **ELO estimation feature:** Remízy poskytují kalibrační body pro ELO odhad. Pokud autor remizuje s opponentem, jejich estimated ELO by měla být blízká.
- **Pattern detection:** Remízy mohou odhalit patterny "aktivní obrany" (pattern Q) nebo "vyhrané pozice které nebyly konvertovány."

**Architektonická implikace:**
```python
# Všechny nástroje musí podporovat 3 kategorie:
group_by_result(analyses) -> {"wins": [...], "losses": [...], "draws": [...]}

# I když je draws=[], struktura musí existovat:
# - prevence KeyError
# - future-proofing pro dataset s remízami
```

### 3. Registered user (systeq) — per-opponent tracking a frekvenční analýza

**Teze:** Pro registrovany účet (systeq) známe jména oponentů, jejich rating, historii vzájemných her. Opponenti se opakují → frekvence her systeq vs opponent_XYZ roste.

**Extrahovatelné statistiky pro per-opponent analýzu:**

```
Opponent: XYZ (lichess rating: 1750±50)
  Head-to-head: 12 games (7W-4L-1D, 58.3% WR)
  Trend: posledních 5 her: 2W-3L (WR klesá)
  Opening distribution:
    e4 (8×): 5W-3L → problém: Sicilian Najdorf (2L)
    d4 (4×): 2W-1L-1D → OK
  Pattern: opponent blunders in 3/5 losses (pattern B)
  Pattern: opponent plays better as black (1.5× lower ACPL)
```

**Frekvenční analýza — klíčová metrika:**

```
Autor vs Opponent_XYZ:
  Game 1-3:  → ACPL gap: +15 (opponent lepší) → 0% WR
  Game 4-6:  → ACPL gap: +5  → 33% WR  
  Game 7-12: → ACPL gap: -3  (autor lepší) → 66% WR
  - Trend: autor se učí hrát proti tomuto opponentovi
  - SNR: FREKVENCE je sama o sobě data — čím víc her, tím lepší odhad
```

**Implikace: Potřeba nové cache struktury:**

```
data/pool_cache/systeq/
├── opponents/
│   ├── opponent_XYZ.json    # per-opponent agregace
│   └── opponent_ABC.json
├── sessions/
│   └── 2026-07.json         # per-session snapshot
├── elo_bands/
│   ├── 1700_1800.json       # pool grouped by estimated ELO
│   └── 1800_1900.json
└── trends/
    └── acpl_trend.json      # time-series: ACPL per month
```

### 4. ELO jako kompresní pattern — "jedno číslo které reprezentuje vše"

**Teze:** ELO je maximálně komprimovaný pattern — jediné číslo, které vyjadřuje celkovou sílu hráče. Lze ho odhadovat z pipeline metrik.

**Co výzkum říká o ELO-ACPL korelaci:**

| Studie | Metoda | Přesnost | Rok |
|--------|--------|----------|-----|
| Chess Digits (Coulombe) | ACPL regrese, 1 game | R²=0.05-0.07 | 2017 |
| FIDE correlation study | ACPL + error types, 8000 games, depth 20 | **r=-0.95** | 2024 |
| Guess-the-Elo (foivoshn) | Multi-metric, 1M games | weak per-game, **strong N≥10** | 2024 |
| RatingNet (Omori) | CNN-LSTM + clock, 1.2M games | **MAE=182** | 2024 |
| DD-Elo (Zhou) | Drift-diffusion model + CPL | bounding dev od Elo | **2026** |

**Klíčová zjištění:**

1. **Single-game ACPL je špatný prediktor ELO** (R² ~5-7%). Problém: vysoký šum, styl hry, variance.
2. **Agregace přes N her dramaticky zlepšuje přesnost.** Při N≥10 her je korelace r=-0.85 až -0.95.
3. **Multi-feature > ACPL alone:** Chybové typy (blunder/mistake/inaccuracy rate), pattern frekvence, time management — všechny přidávají signal.
4. **Clock time je silný feature** — zlepšuje MAE o 24% (RatingNet). Čím delší čas na tah, tím přesnější odhad.
5. **DD-Elo (2026) je state-of-the-art** — integruje move-level CPL do ratingového systému pomocí drift-diffusion modelu. Není to jen statický odhad — je to dynamické přizpůsobení.

**Odhad ELO z pipeline metrik — navrhovaná metoda:**

```python
# Feature vector pro ELO estimation:
features = {
    "acpl":              float,    # -0.95 korelace s ELO při N≥10
    "blunder_rate":      float,    # blundrů/game
    "mistake_rate":      float,    # mistakes/game
    "inaccuracy_rate":   float,    # inaccuracies/game
    "best_move_pct":     float,    # % best moves
    "pattern_freq":      dict,     # per-pattern frequency
    "opening_diversity": float,    # unique openings / total games
    "avg_game_length":   float,    # průměrná délka hry
    "color_asymmetry":   float,    # |white_acpl - black_acpl|
    "time_control":      str,      # "blitz", "rapid", "classical"
}

# Regression model (jednoduchá verze pro MVP):
# ELO = a*ACPL + b*blunder_rate + c*pattern_O_freq + d*avg_moves + e*best_move_pct + intercept
# 
# S kalibrací na známých ELO (systeq games) + extrapolace na anonymous
```

**Pro anonymous pool (kde neznáme ELO):**

```
Metoda 1: Baseline — ACPL-based bands
  ACPL < 25  → 1900+
  ACPL 25-35 → 1700-1900
  ACPL 35-50 → 1500-1700
  ACPL 50+   → <1500

Metoda 2: Multi-feature regression
  - Kalibrovat na registered user data (kde známe ELO)
  - Aplikovat na anonymous pool
  - Výstup: estimated ELO s confidence interval

Metoda 3: Klasifikace do ELO bandů (200pt intervals)
  - 1400-1600, 1600-1800, 1800-2000, 2000+
  - Jednodušší, robustnější k šumu
  - Umožňuje stratifikovat pool podle síly
```

**Doporučení:** Začít s Metodou 3 (klasifikace do bandů). Přesnost je nižší, ale je robustní a snadno interpretovatelná. Později přidat regresní model.

### 5. ETL pipeline pro statistický pool — doménově agnostické řešení

**Teze:** Statistické zpracování (ETL = Extract, Transform, Load) není chess-specific. Stejná architektura může sloužit pro libovolnou doménu s opakovanými měřeními.

**Doménově agnostické jádro:**

```
EXTRACT:
  Vstup: raw data points (game_id, perspective, metrics)
  Výstup: normalizované recordy s jednotným schématem
  
TRANSFORM:
  - Agregace (per-group, per-time, per-feature)
  - Korelace (Pearson, Spearman)
  - SNR výpočet (signal vs noise pro každý feature)
  - Klasifikace (ELO bandy, pattern typy)
  - Trendování (time-series, moving average)
  
LOAD:
  - Pool cache (per-group agregáty)
  - Correlation cache (feature → outcome vazby)
  - Trend cache (time-series data)
```

**Přenositelnost na jiné domény:**

| Doména | Record | Features | Outcome |
|--------|--------|----------|---------|
| Chess | game_id + perspective | ACPL, blunders, patterns | Win/Loss/Draw |
| Trading | trade_id + side | P&L, holding_time, volatility | Profit/Loss |
| Sports | match_id + team | possession, shots, fouls | Win/Loss/Draw |
| Code review | PR_id + reviewer | lines_changed, comments, time | Approve/Reject |

**Stejná ETL architektura — jiné feature schéma.** To je devova doménově agnostická vize.

---

## [REŠERŠE] Existující nástroje a řešení

### 1. Lichess Insights (built-in)

| Aspekt | Hodnocení |
|--------|-----------|
| Per-player ACPL | ✅ Ano |
| Per-opening stats | ✅ Ano |
| Opponent perspective | ❌ Ne |
| Dual-perspective comparison | ❌ Ne |
| ELO estimation | ❌ Ne |
| Pool aggregation | ❌ Ne |
| Export/API | ✅ Lichess API |

**Verdikt:** Lichess Insights je výborný per-player nástroj, ale neřeší opponent pool analýzu.

### 2. OpeningScanner (jeffpalm/openingscanner)

| Aspekt | Hodnocení |
|--------|-----------|
| Opening repertoire scan | ✅ Až 2000 her |
| Weak spots | ✅ Ano |
| Gap analysis | ✅ Ano |
| Client-side only | ✅ (žádný server) |
| Opponent perspective | ❌ Jen per-player |
| ELO estimation | ❌ Ne |
| Pool aggregation | ❌ Ne |

**Verdikt:** Nejlepší nástroj pro opening scouting. Inspirace pro opening analýzu opponentů.

### 3. Outprep (dscape/outprep)

| Aspekt | Hodnocení |
|--------|-----------|
| Scout any player | ✅ Lichess API |
| Opening/weakness analysis | ✅ Ano |
| **Bot that plays like opponent** | ✅ **UNIKÁTNÍ** |
| Boltzmann move selection | ✅ MultiPV |
| Error profiling | ✅ Ano |
| Phase detection | ✅ Ano |
| BotConfig object | ✅ Plně parametrizovatelné |
| Statistical pool | ❌ Ne (zaměřeno na practice) |
| ELO estimation | ❌ Ne (používá actual ELO) |

**Verdikt:** Koncepčně nejbližší devově vizi, ale zaměřený na praxi (bot) místo analýzy (pool). **Inspirace pro error profiling a phase detection.**

### 4. Blindspot (White11010/Blindspot)

| Aspekt | Hodnocení |
|--------|-----------|
| Local-first desktop | ✅ Tauri + SQLite |
| Stockfish analysis | ✅ Lokální |
| Insights (patterns) | ✅ Taktika, psychologie |
| **Versus mode** | ✅ **Porovnání s opponentem** |
| Opponent rating | ✅ Ano |
| Per-opponent stats | ✅ Versus |
| Statistical pool | ❌ Ne |
| MCP pipeline | ❌ Desktop app |

**Verdikt:** Blindspot's Versus mode je jediný nástroj který umí per-opponent srovnání. Inspirace pro `lichess_compare_perspectives`.

### 5. RatingNet (Omori, 2024)

| Aspekt | Hodnocení |
|--------|-----------|
| ELO estimation | ✅ MAE=182 |
| CNN-LSTM | ✅ Move-by-move |
| Clock time integration | ✅ 24% improvement |
| No hand-crafted features | ✅ Ano |
| Lichess dataset | ✅ 1.2M games |
| **Production-ready** | ❌ **Research prototype** |
| MCP integrace | ❌ Ne |

**Verdikt:** Nejlepší ELO estimation model. MAE=182 je ~1 rating class. Možnost integrovat jako službu do pipeline.

### 6. DD-Elo (Zhou, 2026 — IEEE)

| Aspekt | Hodnocení |
|--------|-----------|
| Dynamické ELO | ✅ Drift-diffusion |
| Move-level CPL integrace | ✅ Ano |
| Bounded deviation from Elo | ✅ Matematicky dokázáno |
| Faster adaptation | ✅ Ano |
| **Nejnovější state-of-the-art** | ✅ **2026** |
| Production-ready | ❌ Research |
| MCP integrace | ❌ Ne |

**Verdikt:** Cutting-edge research (červen 2026). Koncepčně nejpokročilejší — ELO už není statická metrika, ale dynamický proces integrující move-level data.

### Srovnání — mezera na trhu

| Kritérium | Lichess Insights | OpeningScanner | Outprep | Blindspot | RatingNet | **Tento návrh** |
|-----------|:---:|:---:|:---:|:---:|:---:|:---:|
| Opponent perspective | ❌ | ❌ | ~ (scout) | ~ (Versus) | ❌ | **✅** |
| Pool aggregation | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |
| N=2/N=3 grouping | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |
| ELO estimation | ❌ | ❌ | ❌ | ❌ | research | **✅ (MVP)** |
| Per-opponent history | ❌ | ❌ | ❌ | ~ (Versus) | ❌ | **✅** |
| Pattern delta | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |
| MCP pipeline | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |
| Domain-agnostic ETL | ❌ | ❌ | ❌ | ❌ | ❌ | **✅** |

**Závěr rešerše:** Žádný existující nástroj nepokrývá opponent-perspective pool analýzu s ELO estimací a N=2/N=3 grouping. **Devova vize zaplňuje mezeru na trhu.**

---

## [ARCHITEKTURA] Implikace pro navrhované nástroje

### Rozšířená architektura

```
src/lichess_analyzer_mcp/
├── services/
│   ├── game_analyzer.py           (stávající)
│   ├── pattern_detector.py        (stávající)
│   ├── [NEW] elo_estimator.py     # ELO odhad z pipeline metrik
│   ├── [NEW] pool_aggregator.py   # Pool-level agregace + group profiling
│   ├── [NEW] opponent_tracker.py  # Per-opponent statistiky (systeq)
│   └── [NEW] etl_pipeline.py      # Doménově agnostické ETL jádro
├── tools/
│   ├── analyze_game.py            (stávající)
│   ├── anonymous_session.py       (stávající)
│   ├── match_patterns.py          (stávající - rozšířit group_by)
│   ├── opponent/
│   │   ├── analyze_opponent.py    # Opponent aggregate stats
│   │   ├── compare_sides.py       # Dual-perspective comparison
│   │   ├── group_profiler.py      # N=2/N=3 profiling
│   │   ├── elo_report.py          # ELO distribution + estimation
│   │   └── hsnr_extract.py        # High-SNR data extraction
│   └── etl/
│       └── run_etl.py             # ETL pipeline orchestration
├── data/
│   ├── game_cache/                (stávající)
│   ├── pool_cache/                [NEW] Pool-level statistiky
│   │   ├── anonymous/             # Anonymous session pools
│   │   │   └── 2026-07-28_n33.json
│   │   └── systeq/
│   │       ├── opponents/         # Per-opponent agregace
│   │       ├── sessions/          # Per-session snapshots
│   │       └── elo_bands/         # ELO band stratifikace
│   └── correlation_cache/         [NEW] Feature-outcome korelace
│       └── elo_correlation.json
└── models/
    ├── game.py                    (stávající)
    ├── pattern.py                 (stávající)
    ├── [NEW] opponent_profile.py   # OpponentProfile dataclass
    ├── [NEW] pool_stats.py         # PoolStats, GroupProfile
    └── [NEW] elo_estimate.py       # EloEstimate, EloBand
```

### Nový service: `elo_estimator.py`

```python
"""
ELO estimation z deterministic pipeline metrics.

Metoda: Multi-feature regrese (ACPL + blunder_rate + mistake_rate + 
        pattern_frequencies + best_move_pct + opening_diversity).
        
Kalibrace: Na registered user data (systeq) kde známe actual ELO z Lichess API.
Extrapolace: Na anonymous pool pomocí kalibrovaného modelu.

Referenční data:
  - r=-0.95 mezi ELO a ACPL při N≥10 (FIDE study, 2024)
  - MAE=182 pro CNN-LSTM s clock time (RatingNet, 2024)
  - DD-Elo drift-diffusion model (Zhou, 2026)
"""

ELO_BANDS = {
    "sub_1500":   (0, 1500),
    "1500_1700":  (1500, 1700),
    "1700_1900":  (1700, 1900),
    "1900_2100":  (1900, 2100),
    "2100_plus":  (2100, 9999),
}

def estimate_elo(acpl: float, blunder_rate: float, mistake_rate: float, 
                 inaccuracy_rate: float, best_move_pct: float,
                 n_games: int, pattern_freq: dict = None) -> EloEstimate:
    """
    Vrací estimated ELO + confidence interval.
    
    Single game: low confidence (CI ±400), band classification only.
    N≥10 games: high confidence (CI ±150), continuous estimate.
    """
    ...

def estimate_elo_band(acpl: float, n_games: int) -> str:
    """
    Klasifikace do ELO bandů (200pt intervals).
    Robustnější než continuous estimate pro small N.
    """
    ...

def calibrate_on_user(username: str) -> dict:
    """
    Kalibruje model na registered user games.
    Porovnává actual ELO (z Lichess API) s pipeline metrikami.
    Vrací kalibrační koeficienty pro regresní model.
    """
    ...
```

### Nový service: `pool_aggregator.py`

```python
"""
Pool-level statistická agregace.

Vstup: Seznam GameAnalysis objektů (z obou perspektiv).
Výstup: PoolStats s N=2/N=3 grouping, per-group profily, ELO distribuce.

Doménově agnostické jádro v etl_pipeline.py.
"""

@dataclass
class PoolStats:
    n_games: int
    n1: GroupProfile           # author wins → opponent losses
    n2: GroupProfile           # author losses → opponent wins
    n3: GroupProfile           # draws
    elo_distribution: dict     # band → count
    feature_correlation: dict  # feature → outcome correlation (SNR)

def aggregate_pool(analyses: list[GameAnalysis], 
                   author_colors: dict[str, str],
                   split_by: str = "result") -> PoolStats:
    """
    Agreguje pool her do pool statistik.
    
    split_by="result": rozdělí na n1/n2/n3 podle výsledku z author perspektivy
    split_by="elo": rozdělí podle estimated ELO bandů
    split_by="opponent": rozdělí podle opponent username (jen registered)
    """
    ...

def compute_feature_correlation(pool: PoolStats) -> dict:
    """
    Spočítá korelaci mezi features a outcomes.
    
    Výstup: {"acpl": {"pearson_r": -0.45, "snr": 0.72}, ...}
    
    SNR = |P(win|feature_X) - P(win|baseline)|
    
    Použití: Identifikuje které features mají nejvyšší prediktivní hodnotu.
    """
    ...
```

### Nový service: `opponent_tracker.py`

```python
"""
Per-opponent tracking pro registered user (systeq).

Sleduje:
  - Head-to-head record (W/L/D)
  - Trend (posledních N her)
  - Opening distribution
  - Opponent patterns
  - Frekvence her (learning curve)
"""

@dataclass 
class OpponentRecord:
    username: str
    total_games: int
    wins: int
    losses: int
    draws: int
    win_rate: float
    trend: list[GameResult]       # posledních 20 her
    openings: dict                 # opening → result
    estimated_elo: EloEstimate
    last_played: datetime
    frequency: int                 # celkový počet her s tímto opponentem

def track_opponent(game: GameAnalysis, username: str) -> OpponentRecord:
    """Aktualizuje per-opponent záznam po každé hře."""
    ...

def get_head_to_head(username: str, opponent: str) -> OpponentRecord:
    """Vrátí head-to-head statistiku."""
    ...

def get_opponent_pool(username: str, min_games: int = 3) -> list[OpponentRecord]:
    """Vrátí seznam opponentů se kterými měl uživatel ≥N her."""
    ...
```

### Rozšíření `match_patterns` o `group_by`

```python
@app.tool("lichess_match_patterns")
async def lichess_match_patterns(
    username: str = "",
    max_games: int = 20,
    depth: int = 12,
    result: str = "all",
    game_ids: str = "",
    group_by: str = "",          # [NEW] "" | "result" | "elo_band"
):
    """
    Extended: group_by="result" → patterns per group + pattern delta.
              group_by="elo_band" → patterns stratified by estimated ELO.
    
    Pattern delta = |pattern_confidence_in_n1 - pattern_confidence_in_n2|
    High delta = pattern that discriminates wins from losses.
    """
```

---

## [IM] Shrnutí a doporučení

### Devova teze — hodnocení

| Teze | Hodnocení | Status |
|------|-----------|--------|
| N1/N2 jsou labeling artifacts → nutnost dual-perspective | ✅ **Korektní.** Implementováno v opponent analysis pipeline. | Potvrzeno |
| N3 musí existovat jako kategorie | ✅ **Korektní.** Architektura musí podporovat 3 kategorie. | Navrženo |
| Per-opponent tracking pro registered user | ✅ **Korektní.** Frekvenční analýza je high-SNR data. | Navrženo |
| ELO jako kompresní pattern | ✅ **Korektní.** Potvrzeno výzkumem (r=-0.95). Metoda: multi-feature, ne jen ACPL. | Navrženo s kalibrací |
| ETL pipeline — doménově agnostické | ✅ **Korektní.** Stejná architektura pro libovolnou doménu s repeated measurements. | Navrženo |

### Mezera na trhu — potvrzena

Rešerše 6 existujících nástrojů (Lichess Insights, OpeningScanner, Outprep, Blindspot, RatingNet, DD-Elo) ukázala, že:

**Žádný nástroj nepokrývá opponent-perspective pool analýzu s ELO estimací a N=2/N=3 grouping.** Devova vize je originální a zaplňuje reálnou mezeru.

### Priority implementace (revidované)

| # | Tool | Závisí na | Odhad |
|---|------|-----------|-------|
| 1 | Services: `elo_estimator.py` + `pool_aggregator.py` | — | 200 lines |
| 2 | Tools: `analyze_opponent.py` + `compare_sides.py` | #1 | 250 lines |
| 3 | Rozšíření `match_patterns` o `group_by` | #1 | 100 lines |
| 4 | `pool_cache` struktura + ETL orchestrace | #1 | 150 lines |
| 5 | `opponent_tracker.py` (registered user) | #1, #4 | 180 lines |
| 6 | `elo_report.py` + `hsnr_extract.py` | #1, #2 | 200 lines |

**Architektonické rozhodnutí:** Services první (jádro), tools druhé (rozhraní), cache třetí (persistence). ETL jádro je doménově agnostické — chess-specific je jen feature schéma a modely.

### Otevřené otázky pro dev

1. **ELO band granularity:** Jaké intervaly? 200pt (5 bandů) nebo 100pt (10 bandů)? Užší bandy = větší variance, ale jemnější rozlišení.
2. **DD-Elo integrace:** Je zájem o implementaci drift-diffusion modelu, nebo stačí statická ELO estimace?
3. **Per-opponent tracking:** Automatický (každá hra systeq) nebo on-demand (tool call)?
4. **ETL frekvence:** Per-session, per-day, nebo per-week?
5. **Doménová agnostika:** Má být ETL jádro v samostatném repozitáři (např. `etl-core`), nebo inline v lichess-analyzer-mcp?

---

*Analýza založená na: (1) reálné session 33 her s dual-perspektivou, (2) rešerši 6 existujících nástrojů, (3) 5 akademických studií o ELO-ACPL korelaci, (4) sémantické analýze 5 devových tezí. Doménově agnostické ETL jádro je navrženo jako separátní vrstva s chess-specific feature schématem.*
