# Opponent Perspective Tool Design — Chain-of-Thought Analysis

**Datum:** 2026-07-28
**Kontext:** Po provedení opponent-perspective analýzy 33 anonymních her (MCP pipeline, depth 12) a extrakci hSNR dat pro N=2 generalizaci (n1=27 proher, n2=6 vyher)
**Účel:** Vyhodnotit vhodnost tvorby nových MCP toolů pro perspektivu oponenta a navrhnout základ řešení

---

## [COT] Chain of Thought — Rekonstrukce poslední iterace

### Krok 1: Data extraction (coaching report, 33 games)

**Cíl:** Analyzovat anonymní pool z autorovy perspektivy
**Nástroj:** `lichess_analyze_anonymous_session` (existující, 209 lines)
**Výstup:** 33 her, 27W/6L, ACPL 32.5, 9 patternů (G 92%, O 29%, ...)
**Problém:** Vidíme POUZE autorovu stranu. Víme, že autor vyhrává 81.8%, ale nevíme CO oponenti dělají špatně.

### Krok 2: Manual labeling flip (opponent perspective)

**Cíl:** Analyzovat stejný pool z OPPONENTovy perspektivy
**Akce:** Ručně vytvořit `lichess_anonymni_partie_opponent_perspective.txt` s flipped labels
- Original win (27) → `- loss` (opponent prohrál)
- Original loss (6) → `- win` (opponent vyhrál)
**Nástroj:** Stejný `lichess_analyze_anonymous_session` — ale s jiným vstupem
**Problém:** Nástroj nepodporuje "analyze from opponent side" jako koncept. Musíme ručně překlopit label a znovu spustit celou pipeline.

### Krok 3: Dual cache vznik

**Mechanismus:** `game_analyzer.py:_save_cached_analysis()` ukládá cache jako `{game_id}_{color}_d{depth}.json`
- První běh (autor perspective, default color=white): vytvoří `_white_d12` pro většinu her
- Druhý běh (opponent perspective, flipped labels): vytvoří `_black_d12` pro hry kde label="win"/"loss" určil opačnou barvu
- Výsledek: 103 cache souborů (68 unikátních game ID, některé mají obě perspektivy)
**Problém:** ŽÁDNÝ nástroj neumí automaticky:
1. Detekovat, že pro danou hru existuje cache z obou perspektiv
2. Porovnat ACPL/blunder rate mezi author a opponent per-game
3. Agregovat statistiky za opponent group

### Krok 4: Ruční extrakce n1 vs n2 (PowerShell)

**Akce:** Manuální dotazování cache souborů PowerShell scriptem
```powershell
Get-Content "{id}_white_d12.json" | ConvertFrom-Json  # author perspective
Get-Content "{id}_black_d12.json" | ConvertFrom-Json  # opponent perspective
```
**Výstup:** Per-game srovnání author vs opponent ACPL, blunderů, mistakes, inaccuracies
**Zjištění:** n2 opponents (n=6) mají 0 blunderů — to je klíčová hSNR informace
**Problém:** Ruční práce ~30 min na 33 her. Není reprodukovatelné bez skriptu.

### Krok 5: Pattern detection z opponent perspektivy

**Nástroj:** `lichess_match_patterns` (existující, 213 lines)
**Aplikace:** Spuštěno s `game_ids` všech 33 her → pattern detection z opponent cache
**Výstup:** 8 patternů (O 44%, J 16%, Q2 14%, C 11%, B 8%, ...)
**Problém:** `match_patterns` analyzuje VŠECHNY hry dohromady. Neumí:
- Splitnout podle výsledku (n1 vs n2)
- Porovnat pattern frekvence mezi author a opponent
- Vypočítat "pattern delta" (co dělá opponent jinak než author)

### Krok 6: Syntéza countermeasures (LLM layer)

**Vstup:** Dual-perspective raw data + pattern detection + per-game breakdown
**Výstup:** `docs/opponent_countermeasures_N2.md` — 6 konkrétních countermeasures
**hSNR extraction:** Z 33 her jsme extrahovali ~10 high-signal datových bodů:
1. Zero blunder rate n2 opponents (0.00/game)
2. Color asymmetry (75% WR white, 92% WR black)
3. Inaccuracy drift (5.67 I/game v losses vs 3.64)
4. Specific opening errors (ply 19 Bd6, ply 23 Bd2, ply 37 Nd4)
5. Typ 1 vs Typ 2 loss pattern
6. Pattern delta: O 44% opponent vs 29% author
**Cena:** ~2 hodiny iterativní analýzy

---

## [EVAL] Vyhodnocení: Je tvorba nových toolů vhodná?

### Kritérium 1: Opakovatelnost

| Aspekt | Bez toolu | S toolem |
|--------|-----------|----------|
| Flip labels pro opponent perspective | Manual (1-2 min) | Automatický |
| Dual cache management | Manual (PowerShell) | Built-in |
| Per-game srovnání | 30 min na batch | 5s |
| n1 vs n2 grouping | Manual (group by result) | Automatický |
| Pattern delta (author vs opponent) | Manual cross-ref | Automatický |
| hSNR extraction | LLM manual inference | Strukturovaný výstup |

**Verdikt:** Bez toolu je opponent analýza jednorázová ruční práce. S toolem je to opakovatelný proces po každé session.

### Kritérium 2: Kvalita dat (hSNR)

Ruční analýza produkovala ~10 high-SNR datových bodů z 33 her. S dedikovanými tools:
- **Více dat:** Automatická extrakce per-phase, per-opening, per-color
- **Konzistentnější:** Stejná metrika napříč session, možnost trendování
- **Statisticky robustnější:** Možnost Fisher exact test, Cohen d, confidence intervals

**Kvantifikace:** Z 33 her jsme extrahovali ~10 hSNR bodů → ~0.3 hSNR/game. S toolem odhad ~0.8-1.2 hSNR/game (2-4× improvement).

### Kritérium 3: ROI vývoje

**Náklady na vývoj:**
- Opponent toolkit: ~400-600 lines Python
- Integrace do stávající architektury: ~200 lines (server registrace, modely)
- Testy: ~300 lines
- **Celkem: ~900-1100 lines**

**Přínosy:**
- Každá session her → automatická opponent analýza (ušetří ~1.5h)
- Možnost trendování napříč session → long-term improvement tracking
- hSNR data pro SRS engine (spaced repetition) → lepší learning karty
- Možnost publikovat jako samostatný tool pro komunitu

**Break-even:** Po 3-4 session (každá ~33 her) se investice vrátí.

**Verdikt:** **Vysoké ROI.** Dev je přesvědčen správně.

### Kritérium 4: Typ opponent (anonymní vs registered)

| Aspekt | Anonymní | Registered |
|--------|----------|------------|
| Známe uživatele? | Ne | Ano (username) |
| Rating k dispozici? | Ne (0) | Ano |
| Opponent profil per-player? | Ne (pool) | Ano |
| Cache klíč | game_id + color | username + game_id + color |
| Pattern trendování | Per-session | Per-user + cross-session |
| Use case | Pool profiling, N=2 generalizace | Individual opponent scouting |

**Závěr:** Oba typy sdílejí ~70% logiky. Rozdíl je v:
- Zdroji game IDs (anonymní: file/urls, registered: fetch_user_games)
- Cache klíči (anonymní: game_id, registered: username+game_id)
- Pattern historii (anonymní: session-only, registered: perzistentní)

**Doporučení:** Společný core engine s parametrickým rozlišením.

---

## [DESIGN] Návrh řešení

### Architektura (rozšíření stávající)

```
src/lichess_analyzer_mcp/
├── tools/
│   ├── analyze_game.py           (stávající)
│   ├── anonymous_session.py      (stávající)
│   ├── match_patterns.py         (stávající)
│   ├── ...
│   └── [NEW] opponent/           # NOVÝ MODUL
│       ├── __init__.py
│       ├── analyze_opponent.py   # tool: lichess_opponent_analysis
│       ├── compare_sides.py      # tool: lichess_compare_perspectives
│       ├── group_profiler.py     # tool: lichess_opponent_groups
│       └── hsnr_extract.py       # tool: lichess_hsnr_extract
├── services/
│   ├── game_analyzer.py          (stávající - rozšířit)
│   └── [NEW] opponent_stats.py   # agregační logika
└── models/
    └── [NEW] opponent_profile.py # OpponentProfile dataclass
```

### Tool 1: `lichess_opponent_analysis` — Opponent aggregate stats

**Účel:** Analyzovat hry z OPPONENTovy perspektivy — aggregate ACPL, blunder rate, per-opening performance.

**Input:**
- `game_ids` (str) — čárkou oddělené 8-char ID (anonymní)
- `username` (str, optional) — pro registered user (fetchne + flipne perspektivu)
- `depth` (int, default 12)

**Logic:**
1. Pro každé game_id: načíst cache z opačné barvy, než je author
2. Pokud cache neexistuje → analyzovat z opponent perspective (flipnout color)
3. Agregovat: ACPL, blunder_count, mistake_count, inaccuracy_count, per-opening, per-phase

**Output:**
```json
{
  "perspective": "opponent",
  "games_analyzed": 33,
  "aggregate_acpl": 52.0,
  "total_blunders": 21,
  "total_mistakes": 49,
  "total_inaccuracies": 140,
  "blunders_per_game": 0.64,
  "avg_moves": 22.4,
  "per_opening": {
    "Pirc Defense": {"games": 3, "acpl": 48.2, "blunders": 2},
    ...
  },
  "per_phase": {
    "opening": {"acpl": 44.1},
    "middlegame": {"acpl": 56.3},
    "endgame": {"acpl": 51.7}
  }
}
```

**Cache strategie:** Vytvořit `_black_d12` cache při prvním volání (pokud neexistuje).

### Tool 2: `lichess_compare_perspectives` — Author vs Opponent per-game

**Účel:** Porovnat author a opponent statistiky pro každou hru.

**Input:**
- `game_ids` (str) — čárkou oddělené 8-char ID
- `author_color` (str, default "auto") — "white", "black", nebo "auto" (detekuje z cache/result)

**Logic:**
1. Pro každé game_id: načíst author cache (daná barva) + opponent cache (opačná barva)
2. Pokud opponent cache neexistuje → vytvořit (analyze_pgn s flipped color)
3. Porovnat: ACPL delta, blunder delta, mistakes delta, inaccuracies delta
4. Označit asymetrie: games where author played well but lost (high delta)

**Output:**
```json
{
  "games_comparison": [
    {
      "id": "k9a1IXvp",
      "opening": "Pirc Defense",
      "result": "0-1 (author=white)",
      "author": {"acpl": 32.1, "blunders": 0, "mistakes": 2},
      "opponent": {"acpl": 16.1, "blunders": 0, "mistakes": 0},
      "delta_acpl": 16.0,
      "verdict": "opponent_dominated",
      "decisive_error": {"ply": 59, "move": "Rxe1", "cp_loss": 174, "phase": "endgame"}
    }
  ],
  "aggregate_comparison": {
    "author_acpl": 35.5,
    "opponent_acpl": 29.4,
    "author_blunders": 2,
    "opponent_blunders": 0,
    "gap_signature": "author_plays_well_loses_close"
  },
  "verdict": {
    "n_opponent_dominated": 4,
    "n_self_destruction": 2,
    "zero_blunder_games": 0
  }
}
```

### Tool 3: `lichess_opponent_groups` — N=2 (n1/n2) group profiling

**Účel:** Rozdělit hry podle výsledku a profilovat každou grupu zvlášť — to je to, co jsme dělali ručně.

**Input:**
- `game_ids` (str) — čárkou oddělené 8-char ID
- `author_username` (str, optional) — pro registered user
- `depth` (int, default 12)

**Logic:**
1. Načíst author perspective pro všechny hry (pro určení výsledku)
2. Rozdělit: wins = author won, losses = author lost
3. Pro každou grupu: analyzovat z OPPONENT perspective
4. Vypočítat: per-group ACPL, blunder rate, per-opening, per-phase

**Output:**
```json
{
  "total_games": 33,
  "n1_opponent_losses": {
    "count": 27,
    "aggregate_acpl": 57.0,
    "blunders_per_game": 0.70,
    "avg_game_length": 20.2,
    "signal": "opponent_self_destructs"
  },
  "n2_opponent_wins": {
    "count": 6,
    "aggregate_acpl": 29.4,
    "blunders_per_game": 0.00,
    "avg_game_length": 32.2,
    "signal": "opponent_zero_blunder"
  },
  "group_delta": {
    "acpl_gap": 27.6,
    "blunder_rate_ratio": null,
    "game_length_delta": 12.0
  },
  "inference": {
    "n2_blunder_rate_zero": true,
    "dominant_loss_type": "opponent_dominated",
    "recommended_focus": "opening_fix + endurance"
  }
}
```

### Tool 4: `lichess_hsnr_extract` — high Signal-to-Noise Ratio extraction

**Účel:** Extrahovat z poolu her ty datové body, které mají nejvyšší prediktivní hodnotu pro zlepšení hry.

**Input:**
- `game_ids` (str) — čárkou oddělené 8-char ID
- `min_signal` (float, default 0.3) — minimum SNR pro zařazení
- `focus` (str, default "all") — "blunders" | "patterns" | "openings" | "phases" | "all"

**Logic:**
1. Pro každou hru: dual-perspective analýza
2. Spočítat SNR pro každý datový bod: signal = |P(win|feature) - P(win|baseline)|
3. Seřadit sestupně podle SNR
4. Vrátit top-N datových bodů s kontextem

**Output:**
```json
{
  "total_games": 33,
  "hsnr_points": [
    {
      "rank": 1,
      "feature": "opponent_blunder_count == 0",
      "snr": 0.82,
      "p_win_with": 0.00,
      "p_win_without": 0.82,
      "games_affected": 6,
      "actionable": true,
      "recommendation": "Don't rely on opponent blunders — n2 opponents make zero"
    },
    {
      "rank": 2,
      "feature": "author_color == white AND game_length > 30",
      "snr": 0.71,
      "p_win_with": 0.40,
      "p_win_without": 0.85,
      "games_affected": 5,
      "actionable": true,
      "recommendation": "Add +10s check after move 25 in white games"
    },
    ...
  ],
  "inference_summary": {
    "top_3_countermeasures": ["opening_fix", "endurance_habit", "color_balance"],
    "estimated_improvement": "+16-25% win rate vs n2 group"
  }
}
```

### Tool 5 (rozšíření stávajícího): `lichess_match_patterns` — per-group patterns

**Rozšíření:** Přidat parameter `group_by` do existujícího toolu.

**Input rozšíření:**
- `group_by` (str, default "") — "" (všechny), "result" (split wins/losses)

**Logic:**
1. Pokud `group_by="result"`: rozdělit analyses na wins a losses
2. Spustit `detect_all()` na každou grupu zvlášť
3. Vrátit patterns per group + pattern delta

**Output navíc:**
```json
{
  "patterns_by_group": {
    "wins": {"O": 35, "G": 92, "B": 12, ...},
    "losses": {"O": 45, "J": 30, "C": 20, ...}
  },
  "pattern_delta": {
    "O_delta": 10,
    "J_delta": 25,
    "inference": "critical patterns spike in losses — fix these first"
  }
}
```

### Implementační detaily

**1. Shared core: `services/opponent_stats.py`**

```python
# Hlavní logika — použitelná pro anonymní i registered

def compute_opponent_aggregate(
    analyses: list[GameAnalysis],
    author_colors: dict[str, str]  # game_id -> author_color
) -> OpponentProfile:
    """Pro každou hru: flipnout barvu, extrahovat opponent stats, agregovat."""
    opponent_acpls = []
    opponent_blunders = []
    # ...
    return OpponentProfile(
        aggregate_acpl=mean(opponent_acpls),
        blunder_rate=sum_len(opponent_blunders),
        ...
    )

def compute_group_profile(
    analyses: list[GameAnalysis],
    group_mask: list[bool]  # True = n1 (opponent loss), False = n2 (opponent win)
) -> GroupProfile:
    """N=2 profil: rozdělit podle výsledku, profilovat každou grupu."""
    ...

def extract_hsnr(
    author_stats: list[GameStats],
    opponent_stats: list[GameStats],
    thresholds: dict
) -> list[HsnrPoint]:
    """Extrahovat high-SNR datové body z dual-perspective dat."""
    ...
```

**2. Model: `models/opponent_profile.py`**

```python
@dataclass
class OpponentProfile:
    perspective: str = "opponent"
    games_analyzed: int = 0
    aggregate_acpl: float = 0.0
    acpl_distribution: list[float] = field(default_factory=list)
    total_blunders: int = 0
    blunders_per_game: float = 0.0
    per_opening: dict = field(default_factory=dict)
    per_phase: dict = field(default_factory=dict)
    per_color: dict = field(default_factory=dict)
    zero_blunder_games: int = 0
    win_rate: float = 0.0

@dataclass
class GroupProfile:
    n1: OpponentProfile | None = None  # opponents who lost
    n2: OpponentProfile | None = None  # opponents who won
    delta_acpl: float = 0.0
    delta_blunder_rate: float = 0.0
    inference: dict = field(default_factory=dict)

@dataclass
class HsnrPoint:
    rank: int = 0
    feature: str = ""
    snr: float = 0.0
    p_win_with: float = 0.0
    p_win_without: float = 0.0
    games_affected: int = 0
    actionable: bool = False
    recommendation: str = ""
```

**3. Cache strategie**

Stávající cache (game_id + color + depth) je plně dostačující. Opponent cache:
- `{id}_white_d12.json` → autor nebo opponent podle kontextu
- `{id}_black_d12.json` → druhá perspektiva

**Problém:** Nevíme která cache je "author" a která "opponent" — závisí na barvě, kterou autor hrál.

**Řešení:** Přidat do cache metadatum `analysis_for: "author" | "opponent"` nebo jednoduše použít index souboru (např. `Anonymous_index.json` nebo `Systeq_index.json`), který mapuje game_id → author_color.

---

## [REF] Engineering reference: dscape/outprep

Design čerpá z 9 patternů extrahovaných z `dscape/outprep` (Nuno Job, Node.js architekt, tvůrce nock).

| # | Pattern | outprep source | Aplikace v tomto návrhu |
|---|---------|---------------|------------------------|
| 1 | **mergeConfig** | `packages/engine/src/config.ts` — deep merge s null-safe defaulty | Unified config pro tools 1-5: `OpponentConfig( depth=12, min_signal=0.3, group_by="" )` — výchozí hodnoty v jediném místě |
| 2 | **Version tracking** | Každý výstup obsahuje `git_commit` + `dirty` flag | OpponentProfile, GroupProfile, HsnrPoint — každý dataclass nese `detector_version` odvozenou z HEAD commit |
| 3 | **Source-agnostic interface** | Stejné API pro Lichess, PGN, FIDE | Opponent core engine: jednotný reader abstrahující zdroj (anonymní file → lichess API → PGN upload) |
| 4 | **ETL 3-phase** | `download → process → seed-db` | `opponent_stats.py` pipeline: `extract_metrics() → transform_perspective() → load_profile()` |
| 5 | **Phase detection** | Materiál-based phase tagy | `per_phase` v OpponentProfile — používá stejnou phase detection logiku jako game_analyzer |
| 6 | **Per-skill temperature** | 7 ELO bands (1100-2800), každý s vlastní teplotou | Band classification v `elo_estimator.py`: 7 bandů místo spojitého ELO |
| 7 | **Boltzmann selection** | Boltzmann-weighted random move selection | hSNR extraction: simulace opponent decision-making s váhami podle band teploty |
| 8 | **FEN-keyed trie** | {FEN → move, frequency, outcome} | Opponent opening repertoire: weighted frequencies per opening position |
| 9 | **Complexity depth scaling** | Hloubka podle komplexity pozice | Depth scaling v analyze_opponent: nižší depth (10-12) pro jednoduché pozice, vyšší (16-18) pro komplexní |

**Integrace:** Tyto patterny nejsou kopie kódu (Node.js → Python), ale principiální reference — každý je adaptován na stávající lichess-analyzer-mcp architekturu.

---

## [IM] Závěr a doporučení

### Verdikt: ANO, tvorba nových toolů je vhodná

**Hlavní argumenty:**
1. **ROI:** Break-even po 3-4 session. Každá další session generuje ~30-60 min úspory.
2. **Kvalita:** Dedikované tools produkují 2-4× více hSNR dat než ruční analýza.
3. **Opakovatelnost:** Možnost trendování napříč session → long-term improvement tracking.
4. **Architektura:** Stávající cache system (game_id + color + depth) je kompatibilní — není třeba měnit storage.

### Priority implementace

| # | Tool | Očekávaná hodnota | Náročnost | Dopad |
|---|------|-------------------|-----------|-------|
| 1 | `lichess_opponent_analysis` (aggregate stats) | Vysoká — toto jsme dělali ručně 30 min | 120 lines | Okamžitá úspora |
| 2 | `lichess_compare_perspectives` (per-game comparison) | Vysoká — odhalilo zero blunder pattern | 150 lines | Klíčový insight |
| 3 | `lichess_opponent_groups` (N=2 profiling) | Střední — specializovaný use case | 150 lines | n1/n2 grouping |
| 4 | Rozšíření `match_patterns` (per-group patterns) | Střední — pattern delta | 80 lines | Pattern srovnání |
| 5 | `lichess_hsnr_extract` (high SNR extraction) | Nízká (early) — závisí na předchozích | 150 lines | Automatická prioritizace |

### Rizika

| Riziko | Pravděpodobnost | Mitigace |
|--------|-----------------|----------|
| Bloat — příliš mnoho small tools | Medium | Modularizovat do jediného toolu s parametry |
| Cache konflikt (author vs opponent přepis) | Low | Už existuje separace per-color |
| nízký N pro registered user (málo her) | Medium | Tool musí fungovat s N≥1 (per-game fallback) |
| Pattern detection na n2 (N=6) má nízkou power | High | Dokumentovat confidence limits, nefabulovat |

### Návrh na rozhodnutí

**Doporučený postup:**
1. Implementovat Tool 1 (`lichess_opponent_analysis`) + Tool 2 (`lichess_compare_perspectives`) jako jeden tool s parametrem `mode="aggregate" | "compare"`
2. Rozšířit `match_patterns` o `group_by="result"` (low effort, high value)
3. Otestovat na stávajících 33 hrách (dual cache už existuje)
4. Dle výsledků: Tool 3 (N=2 profiling) a Tool 5 (hSNR) jako další iterace

**Timeline odhad:** 3-4 hodiny na Tools 1+2+rozšíření match_patterns. 4-6 hodin celý balík.

---

*Chain-of-thought rekonstrukce z reálné session (2026-07-28, 33 her, dual-perspektiva, 3 reporty). Zdůvodnění: stávající MCP nástroje umí analyzovat hry z obou perspektiv (díky cache designu), ale neumí je porovnávat, agregovat, nebo extrahovat hSNR — to vše zůstává na LLM agentovi/manuální práci. Dedikované tools by tuto mezeru uzavřely.*
