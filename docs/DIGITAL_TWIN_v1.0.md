# Digital Twin — lichess-analyzer MCP v0.1.0

**Účel:** Úplná, neutrální disekce pipeline pro nezávislý cross-LLM audit.
**Verze:** 1.0 | **Datum:** 2026-07-24
**Scope:** Kompletní zdrojový kód, architektura, data flow, cache, konfigurace — bez vložených tezí.

---

## 1. Module Tree & File Sizes

```
lichess-analyzer-mcp/
├── pyproject.toml                          (0.8 KB)
├── .env                                    (LICHESS_TOKEN, API keys)
├── docs/
│   └── CONTEXT_INJECT.md                   (4.5 KB — session context, fix history)
├── scripts/
│   ├── run_mcp_server.ps1                  (0.6 KB — PowerShell wrapper, BOM-safe .env read)
│   ├── batch_analyze_all.py                (8.0 KB — full cascade runner: L0→L1→L2→D→P)
│   └── batch_finalize.py                   (12 KB — steps 3-4 + PIPELINE_CASCADE.md gen)
├── data/
│   ├── pgn_cache/{game_id}.pgn             (L1 — raw PGN files)
│   ├── game_cache/
│   │   ├── {user}_games.json               (L0 — game list with metadata)
│   │   ├── {id}_{color}_d{depth}.json      (L2 — Stockfish analysis per game)
│   │   └── {game_id}_llm.json              (L3 — per-game LLM analysis if run)
│   └── resource_store/
│       ├── analysis_store.json             (L2 Resources — analysis results)
│       └── pattern_store.json              (L2 Resources — pattern results)
├── stockfish/
│   └── stockfish.exe                       (Stockfish 18 binary)
├── logs/
│   └── lichess_mcp_202607.log
└── src/lichess_analyzer_mcp/
    ├── app.py                              (0.1 KB — FastMCP instance)
    ├── server.py                           (2.1 KB — entry point, .env loader, tool imports)
    ├── __init__.py                         (empty)
    ├── models/
    │   ├── __init__.py                     (empty)
    │   ├── game.py                         (5.3 KB — GameSummary, MoveAnalysis, GameAnalysis)
    │   ├── analysis.py                     (1.1 KB — PositionAnalysis, WeaknessReport)
    │   ├── pattern.py                      (6.1 KB — PatternDef, PatternMatch, PatternLibrary)
    │   ├── player_profile.py               (1.0 KB — PlayerProfile, OpeningStats)
    │   └── srs_card.py                     (1.2 KB — SRSCard, FSRSState)
    ├── tools/                              (9 files, one per MCP tool)
    │   ├── __init__.py                     (empty)
    │   ├── fetch_games.py                  (1.8 KB)
    │   ├── analyze_game.py                 (1.7 KB)
    │   ├── analyze_position.py             (1.3 KB)
    │   ├── opening_explorer.py             (1.6 KB)
    │   ├── player_profile.py               (1.3 KB)
    │   ├── diagnose_player.py              (3.5 KB)
    │   ├── match_patterns.py               (4.5 KB)
    │   ├── import_pgn.py                   (3.0 KB)
    │   └── workspace_info.py               (1.7 KB)
    ├── services/
    │   ├── __init__.py                     (empty)
    │   ├── lichess_client.py               (5.9 KB — berserk API wrapper, L0/L1 cache)
    │   ├── engine_client.py                (5.2 KB — Stockfish UCI wrapper)
    │   ├── game_analyzer.py                (6.4 KB — per-move eval pipeline, L2 cache)
    │   ├── diagnostician.py                (3.0 KB — cross-game weakness aggregation)
    │   ├── pattern_detector.py             (16 KB — 11 pattern detectors A-R)
    │   ├── llm_client.py                   (20 KB — LLM cascade with 3 providers)
    │   ├── game_llm_cache.py               (8.2 KB — per-game LLM analysis cache)
    │   ├── srs_engine.py                   (3.2 KB — FSRS spaced repetition scheduler)
    │   ├── compressibility_validator.py    (1.1 KB — Mikolov compression ratio)
    │   ├── validator.py                    (2.0 KB — post-analysis sanity checks)
    │   └── logger.py                       (0.9 KB — structured logging, P19)
    ├── resources/
    │   ├── __init__.py                     (empty)
    │   ├── analysis_resources.py           (2.1 KB — L2 Resources: lichess://analysis/{key})
    │   └── pattern_resources.py            (2.1 KB — L2 Resources: lichess://patterns/{key})
    └── kb/
        ├── __init__.py                     (empty)
        ├── schemas.py                      (3.0 KB — validation schemas for pattern artifacts)
        ├── writer.py                       (2.6 KB — KB write helpers)
        └── md_reporter.py                  (8.0 KB — markdown report generation)
```

## 2. Entry Point & Startup Sequence

### `app.py`
```python
from mcp.server.fastmcp import FastMCP
app = FastMCP("lichess-analyzer")
```
Single FastMCP instance. All tools/resources register via `@app.tool()` and `@app.resource()` decorators.

### `server.py` — startup sequence
1. Set stdout encoding to utf-8
2. Compute workspace root (`server.py`'s grandparent = project root)
3. **.env loading**: read `.env` from project root with `utf-8-sig` encoding, parse key=value lines, set into `os.environ` (skip if already set)
4. Print Stockfish path and Python version to stderr
5. **Import all 9 tool modules** → triggers `@app.tool()` decorator registration
6. **Import L2 Resources** (analysis_resources, pattern_resources) → `@app.resource()` registration
7. **API key health check**: call `list_available_providers()`, print found keys to stderr
8. Call `app.run()` — blocks, starts FastMCP stdio transport

### `run_mcp_server.ps1` — PowerShell wrapper
- Project root = grandparent of script dir
- Read `.env` via regex `^\s*([^#=]+)=(.*)\s*$` (handles BOM, spaces)
- Set each env var at Process scope (if not already set)
- Launch `python -X utf8 -m lichess_analyzer_mcp.server`

## 3. All 9 MCP Tools — Signatures, I/O Schemas, Dependencies

### T1: `lichess_fetch_games`
- **File:** `tools/fetch_games.py`
- **Service:** `lichess_client.fetch_user_games()`
- **Args:**
  - `username: str` — Lichess or Chess.com username
  - `max_games: int = 10` — range [1, 50]
  - `source: str = "lichess"` — must be "lichess" or "chesscom"
- **Return keys:** `games[]`, `count`, `username`
- **Game fields:** id, date, opening, result, white, black, white_elo, black_elo, time_control, url
- **Caching:** L0 (`{username}_games.json`, TTL 3600s)
- **Error:** `{"error": str(e)}`

### T2: `lichess_analyze_game`
- **File:** `tools/analyze_game.py`
- **Service:** `lichess_client.fetch_game_pgn()` → `game_analyzer.analyze_pgn()`
- **Args:**
  - `game_id: str = ""` — Lichess 8-char game ID
  - `pgn: str = ""` — raw PGN string (alternative to game_id)
  - `username: str = ""` — for auto-determine color
  - `color: str = "white"` — if username not provided
  - `depth: int = 14` — Stockfish depth [8, 24]
- **Return keys:** game {id, opening, eco, result, player, opponent, ratings, automatic_grab, elo_estimate}, stats {total_acpl, blunders, mistakes, inaccuracies, total_moves}, blunders[] (max 10)
- **Caching:** L1 (PGN) + L2 (Stockfish analysis `{id}_{color}_d{depth}.json`)
- **Error:** `{"error": str(e)}`

### T3: `lichess_analyze_position`
- **File:** `tools/analyze_position.py`
- **Service:** `lichess_client.fetch_cloud_eval()` + `engine_client.analyze_position()`
- **Args:**
  - `fen: str` — position FEN
  - `depth: int = 18` — Stockfish depth [8, 24]
  - `use_cloud: bool = True` — try Lichess cloud eval first
- **Return keys:** fen, analysis_depth, top_lines[] (depth, score_cp, mate, pv[], pv_san[]), cloud_eval (optional)
- **Error:** `{"error": str(e)}`

### T4: `lichess_opening_explorer`
- **File:** `tools/opening_explorer.py`
- **Service:** `lichess_client.fetch_opening_explorer()`
  - Internally: `client.opening_explorer.get_lichess_games(position=fen)` or `.get_masters_games(position=fen)`
- **Args:**
  - `fen: str`
  - `source: str = "lichess"` — must be "lichess" or "masters"
- **Return keys:** fen, source, total_games, top_moves[] (uci, san, white, black, draws, total, win_rate), opening
- **Error:** `{"error": str(e)}`

### T5: `lichess_player_profile`
- **File:** `tools/player_profile.py`
- **Service:** `lichess_client.fetch_user_profile()` → `client.users.get_by_id()`
- **Args:**
  - `username: str`
- **Return keys:** username, title, ratings {blitz, rapid, classical, bullet, correspondence → {rating, games, prog}}, total_games, created_at, seen_at, url
- **Error:** `{"error": str(e)}`

### T6: `lichess_diagnose_player`
- **File:** `tools/diagnose_player.py`
- **Services:** `lichess_client.fetch_user_games()`, `fetch_game_pgn()`, `game_analyzer.analyze_pgn()`, `diagnostician.diagnose()`
- **Args:**
  - `username: str`
  - `max_games: int = 20` — [5, 50]
  - `depth: int = 12` — [8, 18]
- **Return keys:** username, games_analyzed, total_acpl, blunders, mistakes, inaccuracies, phase_weaknesses {phase → {acpl, blunders, move_count}}, leaky_openings[] (top 3), top_weaknesses[]
- **Stores to L2 Resources:** `lichess://analysis/{username}_{timestamp}`
- **Caching:** L0 + L1 + L2
- **Error:** `{"error": str(e)}`

### T7: `lichess_match_patterns`
- **File:** `tools/match_patterns.py`
- **Services:** Same as T6 + `PatternDetector.detect_all()`, `compute_compression()`, `validate_pattern_artifact()`, `validate_against_schema()`
- **Args:**
  - `username: str`
  - `max_games: int = 20` — [5, 50]
  - `depth: int = 12` — [8, 18]
- **Return keys:** username, games_analyzed, patterns_detected[] {pattern_id, pattern_name, confidence, frequency, severity, evidence[], mitigation, hypothesis, compression_ratio (optional)}, total_patterns, _schema_warnings[], _sanity_warnings[]
- **Stores to L2 Resources:** `lichess://patterns/{username}_{timestamp}`
- **Caching:** L0 + L1 + L2
- **Error:** `{"error": str(e)}`

### T8: `lichess_workspace_info`
- **File:** `tools/workspace_info.py`
- **No service dependency**
- **Args:** none
- **Return keys:** workspace_root, server_name, python_version, stockfish_installed, stockfish_path, lichess_token_configured, tools_total, tools[] (list of 9 tool names)
- **Error:** none

### T9: `lichess_import_pgn`
- **File:** `tools/import_pgn.py`
- **Service:** `game_analyzer.analyze_pgn()`
- **Args:**
  - `pgn: str` — full PGN string with headers
  - `color: str = "white"`
  - `depth: int = 14` — [8, 24]
  - `game_id: str = ""` — auto-detected from Site header if empty
- **Return keys:** game {id, opening, eco, result, opponent, date}, stats {total_acpl, blunders, mistakes, inaccuracies, total_moves}, blunders[] (max 10), resource_uri
- **Stores to L2 Resources:** `lichess://analysis/import_{id}_{timestamp}`
- **Caching:** L2
- **Error:** `{"error": str(e)}`

## 4. All Data Models (dataclasses)

### `GameSummary` (game.py)
```
id: str | platform: str | opening: str | opening_eco: str
color: str | result: str
player_name: str = "" | opponent_name: str = ""
player_rating: Optional[int] | opponent_rating: Optional[int]
time_control: str | date: str | url: str
automatic_grab: bool = False | bait_trap: bool = False
metacognition: str = "" | elo_estimate: int = 0
```
Methods: `to_dict()`, `from_dict(d)`

### `MoveAnalysis` (game.py)
```
ply: int | move_uci: str | move_san: str
eval_before: float | eval_after: float
win_prob_before: float | win_prob_after: float
centipawn_loss: float | classification: str
best_move_uci: str | best_move_san: str
is_tactical_motif: bool | motif_type: Optional[str]
phase: str
```
Methods: `to_dict()`, `from_dict(d)`

### `GameAnalysis` (game.py)
```
game: GameSummary
moves: list[MoveAnalysis]
total_acpl: float = 0.0 | accuracy: float = 0.0
blunders: list[MoveAnalysis]
mistakes: list[MoveAnalysis]
inaccuracies: list[MoveAnalysis]
phase_stats: dict = {}  # {phase: {acpl, accuracy, move_count, errors}}
```
Key methods:
- `auto_annotate()`: sets automatic_grab, elo_estimate, accuracy (100 - cp_loss*0.15 capped at [0,100]), phase_stats
- `to_dict()`, `from_dict(d)`

### `PositionAnalysis` (analysis.py)
```
fen: str | eval_cp: float | win_prob: float
mate_in: Optional[int]
best_moves: list[dict] = []
opening_name: Optional[str]
opening_eco: Optional[str]
```

### `WeaknessReport` (analysis.py)
```
username: str | total_games_analyzed: int
total_acpl: float | blunder_count: int
mistake_count: int | inaccuracy_count: int
phase_weaknesses: dict = {}  # {phase: {acpl, blunders, move_count}}
tactical_blind_spots: dict = {}
leaky_openings: list[dict] = []  # [{name, games, blunders}]
pattern_frequencies: dict = {}
top_weaknesses: list[str] = []
elo_trend: list[dict] = []
```

### `PatternDef` (pattern.py)
```
id: str | name: str | pattern_type: str
mechanism: str | it_analogy: str
detection_method: str | severity: str
mitigation: str
detection_rules: dict = {}
min_games: int = 3 | min_occurrences: int = 2
```

### `PatternMatch` (pattern.py)
```
pattern_id: str | pattern_name: str
confidence: float | evidence: list[dict]
game_ids: list[str] | frequency: int
severity: str
hypothesis: Optional[str]
compression_ratio: Optional[float]
```

### `PatternLibrary` (pattern.py)
```
patterns: dict[str, PatternDef] = {}
load_baseline(): returns self with 11 predefined PatternDefs
```

### `PlayerProfile` (player_profile.py)
```
username: str | platform: str
rating: dict | rating_history: list[dict]
total_games: int | wins/losses/draws: int
top_openings: list[dict]
perf_by_time_control: dict
```

### `OpeningStats` (player_profile.py)
```
eco: str | name: str | games_played: int
wins/losses/draws: int | avg_acpl: float | win_rate: float
```

### `SRSCard` (srs_card.py)
```
card_id: str | fen: str
correct_move_uci: str | correct_move_san: str
pattern_id: Optional[str] | game_id: Optional[str]
opening: Optional[str] | phase: str
centipawn_loss: float
created_at: str | due: str
stability/difficulty/elapsed_days/scheduled_days: float/int
reps/lapses: int | state: str ("New") | last_review: Optional[str]
```

### `FSRSState` (srs_card.py)
```
cards: dict[str, SRSCard]
total_reviews: int | total_cards: int | retention_rate: float
```

## 5. Service Layer — Key Algorithms

### 5.1 `lichess_client.py`
**Dependencies:** `berserk` (Lichess API SDK)
**Token resolution order:**
1. `os.environ.get("LICHESS_TOKEN")` → global `_token`
2. If None: re-read `.env` with `utf-8-sig`, parse `LICHESS_TOKEN=...` line
3. `get_client()`: create `berserk.TokenSession(token)` → `berserk.Client(session)`. No token → anonymous client.

**Key method — `_export_by_player()`:**
```
for attempt in range(3):
    try:
        games = list(client.games.export_by_player(username, max=max_games, as_pgn=False, opening=True, analysed=True, evals=True))
        return games
    except Exception:
        if "429" in str(e): sleep(2^(attempt+1)); continue
        if "404" in str(e): return []
        raise
return []
```

**Other methods:** `fetch_user_profile()`, `fetch_game_pgn()` (with L1 cache), `fetch_cloud_eval()`, `fetch_opening_explorer()` (lichess/masters)

### 5.2 `engine_client.py`
**Dependencies:** `chess.engine` (python-chess)
**Stockfish path resolution order:**
1. `STOCKFISH_PATH` env var
2. `{project_root}/stockfish/stockfish.exe` (3x `..` from `services/engine_client.py`)
3. `STOCKFISH_SEARCH_DIRS` env var (semicolon-separated)
4. `stockfish` / `stockfish.exe` on PATH

**Engine lifecycle:**
- Lazy singleton pattern with `_engine_init_lock` (threading.Lock)
- `atexit.register(_cleanup_engine)` → quit on process exit
- Configured: Threads=2, Hash=128 MB

**Analysis lock with zombie recovery:**
```
_analysis_lock.acquire(timeout=120.0)
If timeout: kill engine, restart, acquire fresh lock
```
Returns bool: True = clean lock, False = zombie recovery performed.

**Key methods:**
- `analyze_position(fen, depth=18, multipv=3)` → list of {depth, score_cp, mate, pv[], pv_san[]}
- `evaluate_move(fen, move_uci, depth=16)` → {eval_before, eval_after, centipawn_loss, best_move_uci}
  - Algorithm: eval position before → get best move → eval best line → eval actual move → cp_loss = max(0, best_score - actual_score) (from player's perspective, negated)
- `get_best_move(fen, depth=18)` → {best_move_uci, score_cp, mate}
- `close_engine()` → `.quit()`, reset global

### 5.3 `game_analyzer.py`
**Per-move classification thresholds:**
```
cp_loss >= 300 → "blunder"
cp_loss >= 150 → "mistake"
cp_loss >= 50  → "inaccuracy"
cp_loss >= 20  → "good"
else           → "best"
```

**Phase detection by ply:**
```
ply <= 20  → "opening"
ply <= 50  → "middlegame"
ply > 50   → "endgame"
```

**`_run_analyze_pgn()` algorithm:**
1. Parse PGN via `chess.pgn.read_game()`
2. Extract headers: Result, Site, Opening, ECO, White/Black, Elo, TimeControl, Date
3. Create `GameSummary` and `GameAnalysis`
4. Walk move tree (node.variations[0] → single main line)
5. For each ply where it's player's turn:
   - Call `engine_client.evaluate_move(fen_before, move.uci(), depth)`
   - Classify move, detect phase
   - Append to moves, blunders/mistakes/inaccuracies lists
6. Compute `total_acpl = sum(cp_loss) / move_count`
7. Call `auto_annotate()` for derived fields

**L2 cache:**
- `_load_cached_analysis(game_id, depth, color)`: try exact path, then glob `{id}_{color}_d*.json` for depth approximation
- `_save_cached_analysis()`: atomic write via `.tmp` + `os.replace()`

### 5.4 `diagnostician.py`
**Aggregation across all GameAnalysis:**
1. Sum blunders/mistakes/inaccuracies across all games
2. Per-phase: collect cp_loss values, count errors, compute ACPL
3. Leaky openings: top 5 by blunder count across games
4. Top weaknesses (heuristic rules):
   - If middlegame errors > opening+endgame: "Tactical awareness in middlegame transitions"
   - If total_acpl > 80: "Overall precision: high centipawn loss"
   - If most-played opening has >2 blunders: "Opening preparation: {opening name}"

### 5.5 `pattern_detector.py`
**11 detectors registered in `PatternLibrary.load_baseline()`:**

| ID | Name | Type | Severity | Detection | Min |
|----|------|------|----------|-----------|-----|
| A | Anonymous effect | trigger | high | Compare blunder rate: anonymous vs named opponents; trigger if ratio > 1.3x | 3 games |
| B | Automatic grab | author_error | high | Count captures with cp_loss >= 100 that are blunders/mistakes | 2 games |
| C | Attention tunneling | mechanism | medium | Consecutive blunders (>=2 in row with cp_loss>=100) | 3 games |
| G | Color as modulator | stylistic_shift | high | Compare blunder rate by color; trigger if asymmetry ratio > 1.4x | 3 games |
| I | Bait trap | strategy | low | "Best" captures where eval jumps from <30cp to >100cp (opponent took poisoned pawn) | 1 game |
| J | Impulsive check block | author_error | high | Blunders/mistakes with check (+) or mate (#) in SAN | 1 game |
| O | Repetition avoidance greed | author_error | critical | Blunders after a 3-move stable eval window (flat <30cp variance) — refusing repetition | 3 games |
| P | Visual misrecognition | author_error | high | Blunders involving captures or major pieces (Q/R) when eval > 0 | 3 games |
| Q | Active defense | recovery_strategy | low | Games with 200+cp blunders but still won | 3 games |
| Q1 | Desperate Gambit Mode | recovery_strategy | low | Lost position (300+cp blunder) → reject queen trades → checks → win | 1 game |
| R | Endgame relaxation | author_error | high | Blunders in endgame when eval was >300cp ahead | 3 games |

**Detect_all flow:**
```
for pid in library.patterns:
    if total_games < pdef.min_games: skip
    detector = getattr(self, f"_detect_{pid.lower()}")  # e.g. _detect_b, _detect_j
    if detector:
        match = detector(analyses, metadata)
        if match and match.frequency >= pdef.min_occurrences:
            matches.append(match)
```

**Each detector:** returns `PatternMatch` or `None`. Confidence is heuristic (e.g. blunder_captures/total_captures capped at 0.95). Evidence dict contains raw counts/ratios. Hypothesis is a string template in Czech or English.

### 5.6 `llm_client.py`
**Provider cascade configuration (3 providers, tried in order):**

| Provider | API Key Env Var | Model Env Var | Default Model | Base URL | Pricing |
|----------|----------------|---------------|---------------|----------|---------|
| NVIDIA | `NVIDIA_API_KEY` | `NVIDIA_MODEL` | `nvidia/nemotron-3-super-120b-a12b` | `https://integrate.api.nvidia.com/v1` | Free |
| Cerebras | `CEREBRAS_API_KEY` | `CEREBRAS_MODEL` | `gpt-oss-120b` | `https://api.cerebras.ai/v1` | Free |
| DeepSeek V4 Flash | `DEEPSEEK_API_KEY` | `DEEPSEEK_V4_MODEL` | `deepseek-v4-flash` | `https://api.deepseek.com/v1` | $0.14/$0.28 per 1M |

**LLM config defaults:** max_tokens=2000, temperature=0.3, timeout=60s

**`_call_llm()` algorithm:**
1. Check API key present → return None if not
2. Build payload: {model, messages[{system, user}], max_tokens, temperature}
3. POST to `{base_url}/chat/completions` with httpx
4. Handle error codes: 401→unauthorized, 402→credits, 429→rate limit
5. Parse response: extract usage (prompt/completion tokens), content from choices
6. Estimate cost via PROVIDER_PRICING table
7. Return (content, token_log) or (None, token_log)

**`list_available_providers()`:** iterates PROVIDERS, checks env vars, returns list of {provider, model, key_set}

**Coaching prompt structure (built by `build_coaching_prompt()`):**
```
Player: {username}
Games analyzed: {n}

=== Per-Game LLM Analysis ===  (if game_summaries provided)
- {game_id} ({color}): ACPL={x}, blunders={y}
  Analysis: {llm_summary}

=== Pattern Detection Results ===
- [{SEVERITY}] {ID}: {name} (confidence: {conf}%, frequency: {freq})
  Hypothesis: {hypothesis}
  Mitigation: {mitigation}

=== Weakness Report ===
Total ACPL: {x} | Blunders: {y} | Mistakes: {z} | Inaccuracies: {w}
Phase breakdown: {phase: ACPL, blunders}
Leaky openings: {name: games, blunders}
Top weaknesses: [...]

=== INSTRUCTIONS ===
Produce coaching report:
1. Summary (2-3 sentences)
2. Priority Issues (ranked by severity x frequency)
3. Training Recommendations (concrete, actionable)
4. Strengths (patterns showing good play)
5. Next Session Focus
```

**System prompt rules:**
1. Do NOT invent evidence not present in data
2. Do NOT claim unsupported findings — use hedging language
3. May group patterns, prioritize by severity, suggest training focus
4. If data ambiguous → say so explicitly
5. Plain language for club-level player (1200-1800 Elo)
6. Never say "you always"/"you never"
7. Output in Czech

**`_fallback_report()`:** raw data dump when all LLM providers fail.

### 5.7 `game_llm_cache.py`
Per-game LLM analysis (L3 cache). Not part of main cascade — optional.

- `analyze_game_llm(game_id, color, force=False)`: loads Stockfish cache, calls LLM, saves to `{game_id}_llm.json`
- Content tag: SHA256 hash of Stockfish data → detect staleness
- Validates LLM output as JSON (extracts from ```json blocks)
- `get_all_game_summaries()`: aggregates per-game LLM analyses for coaching prompt

### 5.8 `srs_engine.py`
FSRS spaced repetition:
- Cards stored in `data/srs_cards.json`
- SM-2 derived algorithm: quality < 3 → lapse (schedule=1 day), quality >= 3 → multiplier 2.5 - 0.1*(5 - quality)
- Retention rate tracked as running average

### 5.9 `compressibility_validator.py`
- `compute_compression(match, analyses)`: `compression_ratio = total_moves / (BASE_COST + evidence_count * 2)`
- Based on Mikolov compression philosophy: pattern is valid if it compresses data better than raw

### 5.10 `validator.py`
Sanity checks for pattern artifacts:
- Missing username, games_analyzed < 1
- Duplicate pattern IDs, confidence out of range [0,100]
- Severity not in {low, medium, high, critical}
- Frequency < 1
- Hypothesis doesn't start with "Hypothesis:"
- Raises `ValidationError`

### 5.11 `logger.py`
- File handler: `logs/lichess_mcp_{YYYYMM}.log`
- Format: `timestamp | LEVEL | name | message`
- Propagate = False (no console)

## 6. L2 Resources

### `analysis_resources.py`
- Store: `data/resource_store/analysis_store.json`
- Resource URIs:
  - `lichess://analysis/{key}` → returns stored analysis data (JSON formatted)
  - `lichess://analysis/list` → returns {resources: [key1, key2, ...], total: N}
- `store_analysis(key, data)`: writes to store, returns URI string

### `pattern_resources.py`
- Store: `data/resource_store/pattern_store.json`
- Resource URIs:
  - `lichess://patterns/{key}` → stored pattern data
  - `lichess://patterns/list` → list all stored keys

## 7. Cache Layer Architecture

| Layer | Location | Format | Key | TTL | Write Trigger |
|-------|----------|--------|-----|-----|---------------|
| **L0** | `data/game_cache/{user}_games.json` | JSON: `{_cached_at, games: [...]}` | username | 3600s (1h) | `fetch_user_games()` |
| **L1** | `data/pgn_cache/{game_id}.pgn` | Raw PGN text | game_id | ∞ | `fetch_game_pgn()` |
| **L2** | `data/game_cache/{id}_{color}_d{depth}.json` | JSON: GameAnalysis{game, moves[], stats} | game_id+color+depth | ∞ | `analyze_pgn()` |
| **L3** | `data/game_cache/{game_id}_llm.json` | JSON: per-game LLM analysis | game_id | ∞ (regen on content_tag mismatch) | `analyze_game_llm()` |
| **Resource** | `data/resource_store/analysis_store.json` | JSON dict | username_timestamp | ∞ | `diagnose_player()`, `import_pgn()` |
| **Resource** | `data/resource_store/pattern_store.json` | JSON dict | username_timestamp | ∞ | `match_patterns()` |
| **SRS** | `data/srs_cards.json` | JSON: cards[], stats | — | ∞ | `SRSEngine.review_card()` |

All disk writes use atomic pattern: write to `.tmp` → `os.replace(tmp, path)`

## 8. Dependencies (pyproject.toml)

```toml
[project]
name = "lichess-analyzer-mcp"
version = "0.1.0"
requires-python = ">=3.12, <3.14"
dependencies = [
    "mcp>=1.0.0",
    "berserk>=0.14.0",
    "chess>=1.11.0,<2",
    "httpx>=0.28.0",
]

[project.scripts]
lichess-mcp = "lichess_analyzer_mcp.server:main"

[tool.ruff]
line-length = 100
target-version = "py312"
[tool.ruff.lint]
select = ["F", "E", "W", "I", "N", "UP", "S"]

[dependency-groups]
dev = ["pytest>=8", "pytest-asyncio>=0.24", "coverage>=7"]
```

## 9. Configuration & Environment Variables

**`.env` file (project root, UTF-8-BOM):**
```
LICHESS_TOKEN=lip_xxx
NVIDIA_API_KEY=nvapi-xxx
CEREBRAS_API_KEY=cere-xxx
DEEPSEEK_API_KEY=sk-xxx
```

**Runtime environment variables (set by .env loader + wrapper):**
- `LICHESS_TOKEN` — Lichess API personal token (read-only)
- `NVIDIA_API_KEY` — NVIDIA Nemotron API key
- `CEREBRAS_API_KEY` — Cerebras API key
- `DEEPSEEK_API_KEY` — DeepSeek V4 API key
- `NVIDIA_MODEL` (optional) — override default model
- `CEREBRAS_MODEL` (optional) — override default model
- `DEEPSEEK_V4_MODEL` (optional) — override default model
- `STOCKFISH_PATH` (optional) — alternative Stockfish path
- `STOCKFISH_SEARCH_DIRS` (optional) — semicolon-separated search dirs
- `LLM_MAX_TOKENS` (default 2000)
- `LLM_TEMPERATURE` (default 0.3)
- `LLM_TIMEOUT` (default 60.0)

## 10. Error Handling Patterns

**Global pattern across all tools:**
```python
try:
    ...operation...
    return result
except Exception as e:
    return {"error": str(e)}
```

**In `_export_by_player()`:** retry 3x with exponential backoff (2, 4, 8s) on 429. Graceful 404 → empty list.

**In `engine_client.py`:** zombie recovery — if analysis lock held >120s, kill engine and restart.

**In `batch_analyze_all.py`:** per-game try/except — failed games skipped, logged as anomaly. Continues pipeline.

**In `diagnose_player.py` / `match_patterns.py`:** per-game try/except with skip counter. If 0 analyses → return error.

**Disk writes:** all use atomic `.tmp` + `os.replace()`. Silent on OSError.

## 11. Data Flow Diagram (Text)

```
LLM Agent / Client
    │
    ▼
FastMCP (stdio transport)
    │
    ├─► T1 fetch_games ──► lichess_client.fetch_user_games() ──► berserk ──► Lichess API
    │                                               │
    │                                               └── L0 cache {user}_games.json
    │
    ├─► T2 analyze_game ──► lichess_client.fetch_game_pgn() ──► berserk ──► Lichess API
    │       │                              │
    │       │                              └── L1 cache {game_id}.pgn
    │       │
    │       └──► game_analyzer.analyze_pgn()
    │               │
    │               └──► engine_client.evaluate_move() ──► Stockfish 18 UCI
    │               │
    │               └── L2 cache {id}_{color}_d{depth}.json
    │
    ├─► T6 diagnose_player ──► [L0→L1→L2 for each game] ──► diagnostician.diagnose()
    │                                                              │
    │                                                              └── WeaknessReport
    │                                                              └── L2 Resource store
    │
    ├─► T7 match_patterns ──► [L0→L1→L2 for each game] ──► PatternDetector.detect_all()
    │                                                              │
    │                                                              └── PatternMatch[] + compression
    │                                                              └── validator + schema check
    │                                                              └── L2 Resource store
    │
    ├─► T3 analyze_position ──► engine_client.analyze_position() ──► Stockfish
    │                       └── lichess_client.fetch_cloud_eval() (optional)
    │
    ├─► T4 opening_explorer ──► berserk opening_explorer ──► Lichess API
    ├─► T5 player_profile ──► berserk users.get_by_id()
    ├─► T8 workspace_info ──► (no service call, local FS + env check)
    └─► T9 import_pgn ──► game_analyzer.analyze_pgn() ──► [L2 cache]
                           └── L2 Resource store

LLM Cascade (optional, Phase 4):
    WeaknessReport + PatternMatch[]
        │
        └──► llm_client.build_coaching_prompt()
                │
                └──► NVIDIA Nemotron (free)
                        │ fail →
                        └──► Cerebras (free)
                                │ fail →
                                └──► DeepSeek V4 Flash ($0.14/$0.28)
                                        │ fail →
                                        └──► _fallback_report() (raw data dump)
```
