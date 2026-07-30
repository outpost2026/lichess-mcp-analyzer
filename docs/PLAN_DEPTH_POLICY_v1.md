# Implementační plán — Depth Policy

**Vstup:** `DEPTH_POLICY.md` (depth audit, empirická data z depth_diff_report)
**Navazující na:** commit `6e15d33` (diff report), commit `17dd5fb` (policy doc)
**Datum:** 2026-07-30 | **Priorita:** P2 (batch: P1)

---

## Session A — P1: Centrální konfigurace depth

Cíl: odstranit 6 hardcoded defaultů, sjednotit do jediného konfiguračního zdroje.

### A1 — Vytvořit src/lichess_analyzer_mcp/config/depth.py

- **Soubor:** nový `src/lichess_analyzer_mcp/config/depth.py`
- **Obsah:**
  ```python
  """Centralized depth defaults for Stockfish analysis.
  
  Based on empirical measurements from depth_diff_report_NktJfZZy.md:
  - d=14: optimal quality/time for single game (42s 1P, 84s dual)
  - d=12: recommended for batch analysis (58s dual)
  - d=18: focused positional/endgame (d>20 rejected: 16.7min single > 15min limit)
  """
  
  DEPTH_DEFAULTS = {
      "standard": {
          "single_game": 14,
          "import_pgn": 14,
          "position": 18,
      },
      "batch": {
          "pending": 12,
          "diagnose": 12,
          "patterns": 12,
          "anonymous": 12,
      },
      "focused": {
          "tactical": 14,
          "endgame": 18,
          "opening": 18,
      },
      "limits": {
          "min": 8,
          "max_single_game": 24,
          "max_batch": 18,
          "max_time_single": 900,
          "max_time_dual": 1800,
      },
  }
  ```
- **Rozsah:** 1 nový soubor, ~30 řádků
- **Test:** `from lichess_analyzer_mcp.config.depth import DEPTH_DEFAULTS` bez chyby

### A2 — Refaktorovat tools/*.py: nahradit hardcoded defaulty

- **Soubory:**
  - `tools/analyze_game.py:8` → `depth=DEPTH_DEFAULTS["standard"]["single_game"]`
  - `tools/import_pgn.py:14` → `depth=DEPTH_DEFAULTS["standard"]["import_pgn"]`
  - `tools/analyze_position.py:7` → `depth=DEPTH_DEFAULTS["standard"]["position"]`
  - `tools/analyze_pending.py:22` → `depth=DEPTH_DEFAULTS["batch"]["pending"]`
  - `tools/diagnose_player.py:12` → `depth=DEPTH_DEFAULTS["batch"]["diagnose"]`
  - `tools/match_patterns.py:38` → `depth=DEPTH_DEFAULTS["batch"]["patterns"]`
  - `tools/anonymous_session.py:91` → `depth=DEPTH_DEFAULTS["batch"]["anonymous"]`
- **Zachovat:** clamp `max(8, min(N, depth))` — ale N bude brát z `DEPTH_DEFAULTS["limits"]`
- **Rozsah:** 7 souborů, každý ~2-3 řádky změny
- **Test:** Každý tool volán s implicitním depth → použije se nový default (shodný se starým)

### A3 — Refaktorovat service layer: nahradit hardcoded defaulty

- **Soubory:**
  - `services/game_analyzer.py:79` (`analyze_pgn` default 14 → `standard.single_game`)
  - `services/engine_client.py:110` (`evaluate_move` default 16 → sladit na `standard.single_game` — depth 16 je osamocený, mimo konvenci)
- **Poznámka:** `evaluate_move` default 16 je anomálie — jediný default 16 v celé pipeline. Sjednotit na 14 (standard). Volající stejně předávají explicitní depth.
- **Rozsah:** 2 soubory, 2 řádky
- **Test:** `analyze_pgn(pgn, use_cache=False)` → použije 14

---

## Session B — P1: Auto-selection depth podle typu hry

Cíl: pipeline automaticky volí depth na základě time control a typu hry.

### B1 — Extraktor game info v fetch_games / PGN parser

- **Soubor:** `services/game_analyzer.py` — v `_build_game_summary()` nebo nový helper `_detect_game_profile()`
- **Logika:**
  ```python
  def _detect_game_profile(headers: dict) -> str:
      """Vrátí klíč do DEPTH_DEFAULTS podle time control.
      
      'bullet' → depth 12 (rychlé hry = více chyb)
      'blitz'  → depth 12
      'rapid'  → depth 14 (standard, baseline)
      'classical' → depth 14
      'correspondence' → depth 18 (málo tahů, kvalitnější hra)
      'unknown' → depth 14 (fallback)
      """
      tc = headers.get("TimeControl", "")
      ...
  ```
- **Input:** PGN headers (TimeControl), Lichess API speed field
- **Output:** string key pro DEPTH_DEFAULTS
- **Rozsah:** 1 nová funkce, ~20 řádků

### B2 — Aplikace v analyze_game tool

- **Soubor:** `tools/analyze_game.py` — před `analyze_pgn()`
- **Změna:** Pokud uživatel explicitně nezadá depth (detekovat `depth == DEPTH_DEFAULTS["standard"]["single_game"]`), použít auto-selected depth z game profilu
- **Logika:**
  ```python
  if not user_explicit_depth:
      profile = _detect_game_profile(headers)
      auto_depth = DEPTH_DEFAULTS["standard"].get(profile, DEPTH_DEFAULTS["standard"]["single_game"])
      depth = auto_depth
  ```
- **Vyžaduje:** PGN headers parsed před voláním analyze_pgn
- **Rozsah:** ~10 řádků v analyze_game.py

### B3 — Batch depth awareness (get_pending_analysis fix)

- **Soubor:** `services/lichess_client.py:366` — `get_pending_analysis()`
- **Změna:** Aktuálně používá depth-agnostic glob `*_d*.json`. Místo toho použít exact depth match:
  ```python
  # současný (bug): 
  pattern = os.path.join(GAMES_CACHE_DIR, f"{gid}_{color}_d*.json")
  # nový (správný):
  pattern = os.path.join(GAMES_CACHE_DIR, f"{gid}_{color}_d{depth}.json")
  ```
- **Důsledek:** Hra analyzovaná při d=14 bude stále "pending" při dotazu s d=12 — to je korektní, protože depth má být exaktní
- **Rozsah:** 1 řádek (změna glob patternu)

### B4 — Estimated time reporting

- **Soubor:** `tools/analyze_pending.py` — před začátkem batch analyzy
- **Přidat:** Kalkulaci estimated time podle `len(pending) * avg_time_per_game[depth]`
  ```python
  # Empirická data z depth_diff_report:
  AVG_TIME_PER_GAME = {12: 58, 14: 84, 18: 588}  # seconds, dual perspective
  estimated = len(pending) * AVG_TIME_PER_GAME.get(depth, 84)
  ```
- **Rozsah:** ~10 řádků, log warning pokud estimated > 900s (15min)

---

## Session C — P2: Prompt template updates

Cíl: odstranit hardcoded d12, přidat depth kontext pro LLM.

### C1 — Update CHESS_COACHING_PROMPT_TEMPLATES.md

- **Soubor:** `docs/CHESS_COACHING_PROMPT_TEMPLATES.md`
- **Změny:**
  - Řádek 27: nahradit `_white_d12 / _black_d12` → `_white_d{depth} / _black_d{depth}`
  - Řádek 136: nahradit `*_black_d12.json a *_white_d12.json` → `*_black_d{depth}.json a *_white_d{depth}.json`
  - Přidat na konec Template 1 poznámku:
    ```
    POZNAMKA K DEPTH:
    - Standardni analyze: d=14 (single game), d=12 (batch)
    - Cache soubory: {game_id}_{color}_d{depth}.json
    - Pro detailni endgame/positional analyze: pouzij d=18
    - Depth neni tool parametr — MCP tool pouzije default podle profilu hry
    ```
- **Rozsah:** ~15 řádků změn

### C2 — Přidat depth parametr do MCP tool calls v promptech

- **Soubor:** `docs/CHESS_COACHING_PROMPT_TEMPLATES.md`
- **Změna:** Aktuálně LLM volá `lichess_match_patterns(game_ids="{game_id}")` bez depth. Přidat depth:
  ```
  lichess_match_patterns(game_ids="{game_id}", depth=14)
  ```
- **Důvod:** LLM musí explicitně uvést depth, aby MCP tool věděl, jakou cache očekávat
- **Rozsah:** 3 řádky (T1, T2, T3 tool calls)

---

## Session D — P3: Cloud fallback

Cíl: implementovat chess-api.com jako fallback pro d=18 analyze.

### D1 — Implementovat chess-api.com klienta

- **Soubor:** nový `services/cloud_client.py`
- **API:**
  ```python
  CLOUD_API_URL = "https://chess-api.com/v1"
  CLOUD_MAX_DEPTH = 18  # free tier limit
  CLOUD_MAX_THINKING = 100  # ms
  
  def cloud_evaluate_move(fen: str, move_uci: str, depth: int = 14) -> dict | None:
      """Fallback: evaluate move via chess-api.com. Vrací None při chybě."""
      ...
  ```
- **Rozsah:** ~50 řádků
- **Závislost:** `httpx` nebo `aiohttp` (nutno přidat do pyproject.toml, pokud již není)
- **Rate limiting:** max 1 request/100ms (dle API dokumentace)

### D2 — Integrovat do engine_client.py

- **Soubor:** `services/engine_client.py` — v `evaluate_move()`
- **Změna:** Pokud depth >= 18 a lokální Stockfish timeout/already busy, fallback na cloud:
  ```python
  def evaluate_move(fen, move_uci, depth=14):
      cloud_eligible = depth >= 18 and CLOUD_ENABLED
      if cloud_eligible:
          result = cloud_evaluate_move(fen, move_uci, depth)
          if result is not None:
              return result
      # fallback na lokální Stockfish
      ...
  ```
- **Globální vypínač:** `CLOUD_ENABLED = os.environ.get("CHESS_API_CLOUD", "0") == "1"`
- **Rozsah:** ~15 řádků

---

## Session E — P3: Testování a verifikace

Cíl: ověřit, že změny nemění stávající chování u implicitních hodnot.

### E1 — Unit testy

- **Soubor:** nový `tests/test_depth_policy.py`
- **Test cases:**
  - `DEPTH_DEFAULTS` obsahuje všechny klíče
  - `_detect_game_profile("300+3")` → "rapid"
  - `_detect_game_profile("60+0")` → "bullet"
  - `_detect_game_profile("")` → "unknown"
  - `get_pending_analysis("Systeq")` s novým exact-depth globem
  - `AVG_TIME_PER_GAME` odhad není nulový

### E2 — Integration test

- Zavolat `lichess_analyze_game(game_id="NktJfZZy")` s implicitním depth → ověřit `dual_cache.files` obsahuje `_d14`
- Zavolat `lichess_analyze_pending("Systeq")` → ověřit estimated time reporting

### E3 — Regression check

- Porovnat statistiky z `depth_diff_report` (d=14 baseline) s novou implementací
- Ověřit, že blunder klasifikace zůstává stejná

---

## Harmonogram

| Session | Priorita | Soubory | Odhad | Závislost |
|---------|:--------:|:-------:|:-----:|:---------:|
| **A** (config) | **P1** | 9 | 30 min | — |
| **B** (auto-select) | **P1** | 3 | 45 min | A hotovo |
| **C** (templates) | **P2** | 1 | 15 min | — |
| **D** (cloud) | **P3** | 2 | 1 hod | A hotovo |
| **E** (testy) | **P1** | 1 | 30 min | A+B hotovo |

**Celkem:** ~3 hodiny čistého času. **Session A+B** (P1, ~75 min) jsou kritické — řeší depth anomálie a chybějící auto-selection. **Session C** (P2) je triviální a lze paralelizovat. **Session D** (P3) je volitelná — cloud fallback není nezbytný pro standardní analýzy.

---

## Rizika

| Riziko | Dopad | Mitigace |
|--------|:-----:|----------|
| Změna get_pending_analysis depth-agnostic globu způsobí falešně "pending" hry | Medium | Dokumentovat v changelogu; batch analysis stejně vždy volá s depth=12 |
| `_detect_game_profile` selže na ne-standardním TimeControl formátu | Low | Výchozí "unknown" → depth 14 (safe fallback) |
| chess-api.com API změní formát | Low | `cloud_evaluate_move` vrací None při jakékoli chybě; lokální engine je vždy fallback |
| Uživatelé zvyklí na depth 16 v evaluate_move | Low | Depth 16 nebyl nikde v tool parametrech; sladění na 14 je konzistentní s policy |
