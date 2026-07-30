# Depth Policy — Stockfish depth management for lichess-analyzer-mcp

**Verze:** 1.0 | **Datum:** 2026-07-30
**Zdroj:** depth_diff_report_NktJfZZy.md (empiricke mereni Stockfish 18, 6 threads, Hash 512)
**Kontext:** CPU i7-12700K, 6 threads, Stockfish 18 bmi2

---

## 1. Soucasny stav: depth je definovan na 6 mistech, kazde jinak

### Tool-level defaults (hardcoded, bez centrální konfigurace)

| Tool | Default depth | Clamp | Typ analyze | Soubor:radek |
|------|:-----------:|:-----:|-------------|:------------:|
| `lichess_analyze_game` | **14** | 8-24 | Single game, manual | `tools/analyze_game.py:8` |
| `lichess_import_pgn` | **14** | 8-24 | Manual PGN import | `tools/import_pgn.py:14` |
| `lichess_analyze_pending` | **12** | 8-18 | Batch (nekolik her) | `tools/analyze_pending.py:22` |
| `lichess_analyze_anonymous_session` | **12** | 8-24 | Batch anonymnich her | `tools/anonymous_session.py:91` |
| `lichess_diagnose_player` | **12** | 8-18 | Cross-game (20-50 her) | `tools/diagnose_player.py:12` |
| `lichess_match_patterns` | **12** | 8-18 | Cross-game pattern detect | `tools/match_patterns.py:38` |
| `lichess_analyze_position` | **18** | 8-24 | Single FEN position | `tools/analyze_position.py:7` |

### Service-layer defaults (prepsane volajicim)

| Service | Default depth | Soubor:radek |
|---------|:-----------:|:------------:|
| `analyze_pgn()` | **14** | `services/game_analyzer.py:79` |
| `_run_analyze_pgn()` | **14** | `services/game_analyzer.py:233` |
| `evaluate_move()` | **16** | `services/engine_client.py:110` |
| `analyze_position()` | **18** | `services/engine_client.py:75` |
| `get_best_move()` | **18** | `services/engine_client.py:150` |
| `get_pending_analysis()` | **12** | `services/lichess_client.py:366` |

### Problem: zadna centralni konfigurace

- 6 ruznych default values **hardcodovany** napric 7+ soubory
- `pyproject.toml`, `server.py`, `app.py` neobsahuji zadnou depth referenci
- Neni konfig soubor, env var, ani constant pro default depth
- `get_pending_analysis()` pouziva **depth-agnostic** glob — jakykoli cache soubor (jakehokoli depth) se pocita jako "hotovy"

---

## 2. Auto-selection depth: NEEXISTUJE

### Co chybi

- **Zadna logika nerozlisuje** rated vs casual, time control (bullet/blitz/rapid/classical), ani pocet her v batchi
- `fetch_games.py:55` sice extrahuje `time_control` jako `g.get("speed", "")`, ale nikde se nepouziva pro depth decision
- Jedina "automatizace" je clamp (max(8, min(N, depth))) — rozsah se lisi per-tool (8-18 vs 8-24), ale nejde o inteligentni vyber

### Co by slo pouzit

- `fetch_games.py` uz vraci `time_control` (bullet/blitz/rapid/classical)
- `player_profile.py:16` detekuje `perfs` pro varianty
- PGN headers obsahuji `TimeControl`, `Date`, `WhiteElo`, `BlackElo`, `Result`
- Nic z toho se nepouziva pro depth decision

---

## 3. Depth v prompt templatech: d12 hardcoded

### CHESS_COACHING_PROMPT_TEMPLATES.md

| Radek | Obsah | Problem |
|:-----:|-------|---------|
| 27 | `cached analysis (_white_d12 / _black_d12)` | **d12 hardcoded** jako priklad |
| 34 | `data/game_cache/{game_id}_{color}_d{depth}.json` | OK — pouziva placeholder |
| 136 | `*_black_d12.json a *_white_d12.json (dual perspective)` | **d12 hardcoded** |

### Dulezite: parametry nejsou predavany

Zadny z templatu neinstruuje LLM, aby volal MCP tool s konkretnim `depth=` parametrem. Volaji pouze:
- `lichess_match_patterns(game_ids="...")` — bez depth
- `lichess_match_patterns(username="...", max_games=N)` — bez depth

LLM si musi sam odvodit, ze ma pouzit cache soubor s prislusnym depth. Pokud depth neni explicitne zminen, pouzije se implicitni dle toolu.

---

## 4. Navrh: default depth promenne (zalozeno na vyzkumu)

### 4.1 Empiricke zavery z depth_diff_report

| Depth | 1P cas | Dual cas | cp_loss delta oproti d=14 | Klasifikace stability |
|:-----:|:------:|:--------:|:-------------------------:|:--------------------:|
| **d=12** | 29s | 58s | +0-5cp | Identical |
| **d=14** | 42s | 84s | baseline | baseline |
| **d=18** | 4.9min | 9.8min | 0-34cp | Blunder stabilni, endgame se meni |
| **d=22** | 16.7min | 33.4min | 8-34cp | Blunder stabilni, ale cas presahuje limit |

Klice:
- d=14 da 95% stejne klasifikace jako d=22 za 1/25 casu
- d=18 prida hodnotu jen u quiet positional / endgame positions
- d=22 je zamitnut (>15min limit pro single game)

### 4.2 Navrh default promennych

#### A) Standardni analyze — pro 90% pripadu

| Use case | Depth | Rationale |
|----------|:-----:|-----------|
| Single game manual analyze (rated) | **14** | Optimal quality/cas pomer |
| Single game manual analyze (casual/anon) | **12** | Nizsi kvalita hry = nizsi narok |
| PGN import (manual) | **14** | Stejny jako analyze_game |
| Single position (FEN) | **18** | Jen jedna pozice, 1.5s |

#### B) Batch analyze — vice her najednou

| Use case | Depth | Rationale |
|----------|:-----:|-----------|
| Diagnose player (20-50 her) | **12** | 58s dual = 1 min herne |
| Match patterns (20 her) | **12** | 58s dual, staci pro pattern detekci |
| Pending analysis (vsechny) | **12** | Batch 20+ her, 12 je jediny realny |
| Anonymous session (N her) | **12** | CPU bottleneck pri vetsim batchi |

#### C) Focused analyze — detailni analyza

| Use case | Depth | Rationale |
|----------|:-----:|-----------|
| Tactical blunder analyze | **14** | Klasifikace blunderu stabilni napric depthy |
| Endgame / positional analyze | **18** | Zlepsuje klasifikaci quiet positions |
| Opening preparation | **18** | Jen 1-2 pozice, cas zanedbatelny |
| Coaching report (template 1) | **14** | Hlavni report pouziva single game |

### 4.3 Konfig soubor (navrh)

```python
# config.py nebo depth_policy.py
DEPTH_DEFAULTS = {
    "standard": {
        "single_game": 14,        # lichess_analyze_game
        "import_pgn": 14,         # lichess_import_pgn
        "position": 18,           # lichess_analyze_position
    },
    "batch": {
        "pending": 12,            # lichess_analyze_pending
        "diagnose": 12,           # lichess_diagnose_player
        "patterns": 12,           # lichess_match_patterns
        "anonymous": 12,          # lichess_analyze_anonymous_session
    },
    "focused": {
        "tactical": 14,           # Override pro blunder analyze
        "endgame": 18,            # Override pro positional analyze
        "opening": 18,            # Override pro opening prep
    },
    "limits": {
        "min": 8,
        "max_single_game": 24,    # Hard limit toolu
        "max_batch": 18,          # Batch nikdy neprevysuje 18
        "max_time_single": 900,   # 15 min v sekundach (CPU limit)
        "max_time_dual": 1800,    # 30 min v sekundach
    }
}
```

### 4.4 Doplneni prompt templatu

Do kazdeho template v `CHESS_COACHING_PROMPT_TEMPLATES.md` pridat:

```
POZNAMKA K DEPTH:
- Standardni analyze: d=14 (single game), d=12 (batch)
- Cache soubory: {game_id}_{color}_d{depth}.json
- Pro detailni endgame/positional analyze: pouzij d=18
- Depth neni parametr — pouzij default dle kontextu analyze
```

---

## 5. Cloud API alternatives for Stockfish analysis

### 5.1 chess-api.com (free)

| Aspekt | Hodnota |
|--------|---------|
| URL | https://chess-api.com/v1 (POST), wss://chess-api.com/v1 (WS) |
| Cena | **Free** (donation model) |
| Stockfish verze | 18 |
| Max depth | 18 free, D>20 pro supporters |
| Max thinking time | 100ms default |
| Hardware | 32 vCores, 128GB DDR5 |
| Rychlost | Až 80 MN/s |
| API | JSON POST / WebSocket |
| Limit | Single FEN evaluation (nema full game analyzu) |
| Zaruka | Nejaka — single developer, no SLA |

**Verdikt:** Vhodny jako doplnek pro rychlou pozicni analyzu (opening prep, endgame tablebase). Ne jako nahrada full game analyzy. Depth limit 18 je konzistentni s navrhem pro focused analyze.

### 5.2 Stockfish Cloud Services (paid)

| Service | Cena | Rychlost | Depth | Poznamka |
|---------|:----:|:--------:|:-----:|----------|
| stockfishcloud.com | $2-40/hod | 30-1050 MN/s | N/A | UCI protokol, ChessBase |
| stockfish.net | od $0 | 50+ MN/s | N/A | UCI protokol |
| stockfish.online | free tier | N/A | 10-24 | REST API, registration |

**Verdikt:** Predrazene pro lokalni analyze ($2-40/hod). Vhodne pouze pro hromadnou analyzu (100+ her) kde lokalni CPU nestaci. Pro standardnich 1-20 her je lokalni Stockfish 18 na 6 threads plne dostaCujici.

### 5.3 Lichess Cloud Eval (free, API)

| Aspekt | Hodnota |
|--------|---------|
| URL | https://lichess.org/api/cloud-eval |
| Cena | **Free** |
| Depth | Až 22+ (Lichess server) |
| Limit | Pouze pro pozice existujici v Lichess DB |
| API | GET request, JSON response |
| Vyhoda | Jiz implementovano v `lichess_analyze_position(use_cloud=True)` |

**Verdikt:** Jiz existuje v pipeline jako `use_cloud` parametr v `lichess_analyze_position`. Vhodny jako fallback nebo doplnek pro opening/known positions. Depth je vyssi (az 22+), ale pokryti je omezeno na Lichess DB.

### 5.4 Self-hosted Docker Stockfish API

- `github.com/TreelineInteractive/chess-engine-api` — production-ready REST API wrapper
- `github.com/alokvishy/chess-analysis-api` — FastAPI, engine pool
- Vyhoda: full kontrola nad depth, threads, hash
- Nevýhoda: requiruje samostatny server (Docker)

**Verdikt:** Neni potreba pro lokalni analyze. Pokud by nekdy beValo treba skálovat na 50+ soubeznych analyz, Docker reseni dava smysl.

---

## 6. Implementacni doporuceni

### Krok 1: Centrální konfigurace
- Vytvorit `src/lichess_analyzer_mcp/config/depth.py` s DEPTH_DEFAULTS (die Section 4.3)
- Vsechny tooly importuji konfig místo hardcoded hodnot

### Krok 2: Auto-selection podle typu hry
- V `analyze_game.py`: if PGN headers obsahuji `TimeControl`, prizpusobit depth
  - bullet/blitz → 12 (rychle hry = vice chyb, nizsi narok na precision)
  - rapid/classical → 14 (standard)
  - correspondence → 18 (mene tahu, vic casu na analyzu)

### Krok 3: Batch depth awareness
- V `get_pending_analysis()`: misto depth-agnostic glob pouzit exact depth match
- `analyze_pending()`: reportovat pocet her a estimated time pred analyzou

### Krok 4: Prompt templaty
- Nahradit hardcoded d12 za `{depth}` placeholder
- Pridat depth kontext do system promptu pro LLM

### Krok 5: Cloud fallback (volitelny)
- Implementovat chess-api.com jako fallback pro d=18 analyze kdyz lokalni CPU je busy
- V `engine_client.py`: if depth > 14, zkusit chess-api.com (free), pri neuspechu lokal

---

*Document vypracovan na zaklade depth_diff_report_NktJfZZy.md a codebase analyzy (commit 89a0bf2, 6e15d33).*
