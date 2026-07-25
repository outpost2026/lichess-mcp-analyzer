# Cross-LLM Audit Prompt — lichess-analyzer MCP

**Verze:** 1.0 | **Datum:** 2026-07-24
**Auditovaný systém:** lichess-analyzer-mcp v0.1.0
**Scope:** Kompletní pipeline: MCP server → Lichess API → Stockfish → Pattern Detection → LLM Cascade
**Author instructions:** Proveďte nezávislý audit na základě níže uvedené disekce (DIGITAL_TWIN). Neznáte autora ani historii vývoje. Vaše hodnocení musí být de novo — bez předchozí teze.

---

## Context for the Auditor

You are a senior software architect / security reviewer performing an independent audit of an MCP (Model Context Protocol) server for chess analysis. The server wraps Lichess API (via berserk SDK) + Stockfish 18 chess engine into 9 MCP tools accessible to LLM agents. It also provides cross-game pattern detection (11 patterns A-R) and an optional LLM cascade for coaching report generation.

The project is in **v0.1.0** — early stage, actively developed by a single developer. The codebase is written in Python 3.12+, uses FastMCP for the MCP transport layer (stdio), and runs on Windows via a PowerShell wrapper.

---

## Embedded Digital Twin

The following sections (1–11) contain the complete, neutral dissection of the pipeline. All source code has been read in full — no summarization or truncation. Use this as your sole source of truth for the audit.

[DIGITAL_TWIN_v1.0.md follows — full artifact embedded below]

### 1. Module Tree & File Sizes

```
lichess-analyzer-mcp/
├── pyproject.toml                          (0.8 KB)
├── .env                                    (LICHESS_TOKEN, API keys)
├── docs/
│   └── CONTEXT_INJECT.md                   (4.5 KB)
├── scripts/
│   ├── run_mcp_server.ps1                  (0.6 KB)
│   ├── batch_analyze_all.py                (8.0 KB)
│   └── batch_finalize.py                   (12 KB)
├── data/                                   (runtime caches + stores)
├── stockfish/
│   └── stockfish.exe
├── logs/
└── src/lichess_analyzer_mcp/
    ├── app.py                              (3 lines)
    ├── server.py                           (2.1 KB)
    ├── models/                             (7 files, 5 data models)
    ├── tools/                              (9 files, one per MCP tool)
    ├── services/                           (11 files, all business logic)
    ├── resources/                          (2 files, L2 Resources)
    └── kb/                                 (3 files, KB helpers)
```

### 2. Entry Point & Startup Sequence

**app.py:**
```python
from mcp.server.fastmcp import FastMCP
app = FastMCP("lichess-analyzer")
```

**server.py startup sequence:**
1. Set stdout encoding to utf-8, errors="replace"
2. Compute workspace root (3x `..` from server.py)
3. .env loading: read `.env` from project root with `encoding="utf-8-sig"`, parse key=value lines into `os.environ` (skip if already set in environ)
4. Print Stockfish path and Python version to stderr
5. Import all 9 tool modules → triggers `@app.tool()` decorators
6. Import L2 Resources (analysis_resources, pattern_resources) → `@app.resource()` decorators
7. API key health check: call `list_available_providers()`, print found keys to stderr
8. Call `app.run()` — blocks on FastMCP stdio transport

**run_mcp_server.ps1** (PowerShell wrapper):
```powershell
$envFile = Join-Path $projectRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^\s*([^#=]+)=(.*)\s*$") {
            $k = $matches[1].Trim()
            $v = $matches[2].Trim()
            if ($k -and -not [Environment]::GetEnvironmentVariable($k, "Process")) {
                [Environment]::SetEnvironmentVariable($k, $v, "Process")
            }
        }
    }
}
& $python -X utf8 -m lichess_analyzer_mcp.server
```

### 3. All 9 MCP Tools — Full Signatures & I/O

**T1: `lichess_fetch_games`**
- Source: `tools/fetch_games.py`
- **Args:** `username: str`, `max_games: int = 10` [1-50], `source: str = "lichess"` ("lichess"|"chesscom")
- Return: `{games: [{id, date, opening, result, white, black, white_elo, black_elo, time_control, url}], count, username}`
- Caching: L0 (`{username}_games.json`, TTL 3600s)
- Error: `{"error": str(e)}`

**T2: `lichess_analyze_game`**
- Source: `tools/analyze_game.py`
- **Args:** `game_id: str = ""`, `pgn: str = ""`, `username: str = ""`, `color: str = "white"`, `depth: int = 14` [8-24]
- Return: `{game: {id, opening, eco, result, player, opponent, player_rating, opponent_rating, date, automatic_grab, elo_estimate}, stats: {total_acpl, blunders, mistakes, inaccuracies, total_moves}, blunders: [str] (max 10)}`
- Caching: L1 + L2
- Error: `{"error": str(e)}`

**T3: `lichess_analyze_position`**
- Source: `tools/analyze_position.py`
- **Args:** `fen: str`, `depth: int = 18` [8-24], `use_cloud: bool = True`
- Return: `{fen, analysis_depth, top_lines: [{depth, score_cp, mate, pv[], pv_san[]}], cloud_eval?}`
- Error: `{"error": str(e)}`

**T4: `lichess_opening_explorer`**
- Source: `tools/opening_explorer.py`
- **Args:** `fen: str`, `source: str = "lichess"` ("lichess"|"masters")
- Return: `{fen, source, total_games, top_moves: [{uci, san, white, black, draws, total, win_rate}], opening}`
- Error: `{"error": str(e)}`

**T5: `lichess_player_profile`**
- Source: `tools/player_profile.py`
- **Args:** `username: str`
- Return: `{username, title?, ratings: {variant: {rating, games, prog}}, total_games, created_at, seen_at, url}`
- Error: `{"error": str(e)}`

**T6: `lichess_diagnose_player`**
- Source: `tools/diagnose_player.py`
- **Args:** `username: str`, `max_games: int = 20` [5-50], `depth: int = 12` [8-18]
- Return: `{username, games_analyzed, total_acpl, blunders, mistakes, inaccuracies, phase_weaknesses: {phase: {acpl, blunders, move_count}}, leaky_openings: [3], top_weaknesses: [str]}`
- Caching: L0+L1+L2
- Also stores to L2 Resource: `lichess://analysis/{username}_{timestamp}`
- Error: `{"error": str(e)}`

**T7: `lichess_match_patterns`**
- Source: `tools/match_patterns.py`
- Additional deps: `PatternDetector`, `compute_compression`, `validate_pattern_artifact`, `validate_against_schema`
- **Args:** `username: str`, `max_games: int = 20` [5-50], `depth: int = 12` [8-18]
- Return: `{username, games_analyzed, patterns_detected: [{pattern_id, pattern_name, confidence (0-100%), frequency, severity, evidence[], mitigation, hypothesis, compression_ratio?}], total_patterns, _schema_warnings?, _sanity_warnings?}`
- Also stores to L2 Resource: `lichess://patterns/{username}_{timestamp}`
- Error: `{"error": str(e)}`

**T8: `lichess_workspace_info`**
- Source: `tools/workspace_info.py`
- **Args:** none
- Return: `{workspace_root, server_name, python_version, stockfish_installed, stockfish_path?, lichess_token_configured, tools_total, tools: [str]}`
- No network calls; pure local FS + env vars

**T9: `lichess_import_pgn`**
- Source: `tools/import_pgn.py`
- **Args:** `pgn: str`, `color: str = "white"`, `depth: int = 14` [8-24], `game_id: str = ""`
- Return: `{game: {id, opening, eco, result, opponent, date}, stats: {total_acpl, blunders, mistakes, inaccuracies, total_moves}, blunders: [str] (max 10), resource_uri}`
- Caching: L2
- Also stores to L2 Resource: `lichess://analysis/import_{id}_{timestamp}`
- Error: `{"error": str(e)}`

### 4. All Data Models (dataclasses)

**GameSummary** (game.py):
```
id: str | platform: str | opening: str | opening_eco: str
color: str | result: str
player_name: str = "" | opponent_name: str = ""
player_rating: Optional[int] | opponent_rating: Optional[int]
time_control: str | date: str | url: str
automatic_grab: bool = False | bait_trap: bool = False
metacognition: str = "" | elo_estimate: int = 0
```

**MoveAnalysis** (game.py):
```
ply: int | move_uci: str | move_san: str
eval_before: float | eval_after: float
win_prob_before: float | win_prob_after: float
centipawn_loss: float | classification: str
best_move_uci: str | best_move_san: str
is_tactical_motif: bool | motif_type: Optional[str]
phase: str
```

**GameAnalysis** (game.py):
```
game: GameSummary
moves: list[MoveAnalysis]
total_acpl: float = 0.0 | accuracy: float = 0.0
blunders: list[MoveAnalysis]
mistakes: list[MoveAnalysis]
inaccuracies: list[MoveAnalysis]
phase_stats: dict = {}
```
Methods:
- `auto_annotate()`: sets automatic_grab=True if any capture-blunder; elo_estimate = opponent_rating - ACPL*0.8, clamped [800, 2800]; accuracy = avg(max(0, 100 - cp_loss*0.15)); phase_stats = per-phase ACPL, accuracy, errors
- `to_dict()`, `from_dict(d)`

**PositionAnalysis** (analysis.py):
```
fen: str | eval_cp: float | win_prob: float
mate_in: Optional[int]
best_moves: list[dict] = []
opening_name: Optional[str] | opening_eco: Optional[str]
```

**WeaknessReport** (analysis.py):
```
username: str | total_games_analyzed: int
total_acpl: float | blunder_count: int | mistake_count: int | inaccuracy_count: int
phase_weaknesses: dict = {}
tactical_blind_spots: dict = {}
leaky_openings: list[dict] = []
pattern_frequencies: dict = {}
top_weaknesses: list[str] = []
elo_trend: list[dict] = []
```

**PatternDef** (pattern.py):
```
id: str | name: str | pattern_type: str
mechanism: str | it_analogy: str
detection_method: str | severity: str
mitigation: str
detection_rules: dict = {}
min_games: int = 3 | min_occurrences: int = 2
```

**PatternMatch** (pattern.py):
```
pattern_id: str | pattern_name: str
confidence: float | evidence: list[dict]
game_ids: list[str] | frequency: int
severity: str
hypothesis: Optional[str]
compression_ratio: Optional[float]
```

**PatternLibrary** (pattern.py):
```
patterns: dict[str, PatternDef] = {}
load_baseline(): returns self with 11 predefined patterns
```

**PlayerProfile** (player_profile.py), **OpeningStats** (player_profile.py), **SRSCard** (srs_card.py), **FSRSState** (srs_card.py) — data-only structs.

### 5. Service Layer — Key Algorithms

#### 5.1 lichess_client.py
**Dependencies:** berserk SDK (Lichess API wrapper)
**Token resolution order:**
1. `os.environ.get("LICHESS_TOKEN")`
2. If None: re-read `.env` with `utf-8-sig`, parse `LICHESS_TOKEN=...` line
3. `get_client()`: create `berserk.TokenSession(token)` → `berserk.Client(session)`. No token → anonymous client.

**`_export_by_player()` — game fetch with retry:**
```python
for attempt in range(3):
    try:
        games = list(client.games.export_by_player(username, max=max_games, as_pgn=False, opening=True, analysed=True, evals=True))
        return games
    except Exception as e:
        if "429" in str(e): sleep(2^(attempt+1)); continue
        if "404" in str(e): return []
        raise
return []
```

**Caching:**
- L0: `{username}_games.json` — JSON list with `_cached_at` timestamp, TTL 3600s
- L1: `pgn_cache/{game_id}.pgn` — raw PGN text, no TTL
- Both use atomic writes (.tmp + os.replace)

#### 5.2 engine_client.py
**Dependencies:** python-chess (`chess.engine`)
**Stockfish path resolution:**
1. `STOCKFISH_PATH` env var
2. `{project_root}/stockfish/stockfish.exe` (3x `..` from `services/engine_client.py`)
3. `STOCKFISH_SEARCH_DIRS` env var (semicolon-separated)
4. `stockfish` / `stockfish.exe` on system PATH

**Engine lifecycle:** Lazy singleton with threading lock. `atexit` cleanup. Configured: Threads=2, Hash=128MB.

**Analysis lock with zombie recovery:**
```python
locked = _analysis_lock.acquire(timeout=120.0)
if not locked:
    _engine.quit()
    _engine = None
    get_engine()  # fresh start
    _analysis_lock.acquire()  # clean lock
```

**`evaluate_move(fen, move_uci, depth=16)`:**
```python
# eval position before
info_before = engine.analyse(board, chess.engine.Limit(depth=depth))
eval_before = info_before["score"].relative.score()
best_move = info_before["pv"][0]

# eval best move's resulting position
board_best = board.copy()
board_best.push(best_move)
best_res = engine.analyse(board_best, chess.engine.Limit(depth=depth))
best_score = best_res["score"].relative.score()
best_player = -best_score  # negate: player's perspective

# eval actual move's resulting position
board.push(move)
actual_res = engine.analyse(board, chess.engine.Limit(depth=depth))
actual_score = actual_res["score"].relative.score()
actual_player = -actual_score

cp_loss = max(0, best_player - actual_player)
```

#### 5.3 game_analyzer.py
**Move classification thresholds:**
```
cp_loss >= 300 → "blunder"
cp_loss >= 150 → "mistake"
cp_loss >= 50  → "inaccuracy"
cp_loss >= 20  → "good"
else           → "best"
```

**Phase detection:**
```
ply <= 20  → "opening"
ply <= 50  → "middlegame"
ply > 50   → "endgame"
```

**`_run_analyze_pgn()` walk:**
- Parse PGN via `chess.pgn.read_game()`
- Walk `node.variations[0]` (main line only, single-variation)
- For each ply at player's side: call `evaluate_move()`, classify, detect phase
- `total_acpl = sum(cp_loss) / move_count`
- Call `auto_annotate()`

**L2 cache:**
- Exact match: `{game_id}_{color}_d{depth}.json`
- Depth approximation: glob `{id}_{color}_d*.json` → take highest depth
- Atomic write via `.tmp` + `os.replace()`

#### 5.4 diagnostician.py
**Aggregation:**
```
for analysis in analyses:
    sum blunders/mistakes/inaccuracies
    collect cp_loss per phase → phase_acpl[phase].append(cp_loss)
    count blunders per phase → phase_blunders[phase]
    group leaky openings → openings[name] = {games, blunders}
```
**Top weaknesses (hardcoded rules):**
1. If middlegame blunders > opening+endgame → "Tactical awareness in middlegame transitions"
2. If total_acpl > 80 → "Overall precision: high centipawn loss"
3. If most-played opening has >2 blunders → "Opening preparation: {opening name}"

#### 5.5 pattern_detector.py
**11 detectors in PatternLibrary:**

| ID | Name | Type | Severity | Detection Logic | Min |
|----|------|------|----------|----------------|-----|
| A | Anonymous effect | trigger | high | Compare blunder rate anonymous vs named opponents; ratio > 1.3 → match | 3 games |
| B | Automatic grab | author_error | high | Count captures with cp_loss>=100 classified as blunder/mistake; confidence = blunder_captures/total_captures capped at 0.95 | 2 games |
| C | Attention tunneling | mechanism | medium | Consecutive blunders (>=2 in row, cp_loss>=100); confidence = len(affected)/5 capped at 0.85 | 3 games |
| G | Color as modulator | stylistic_shift | high | Compare blunder rate white vs black; asymmetry ratio > 1.4 → match; confidence = ratio/3 capped 0.95 | 3 games |
| I | Bait trap | strategy | low | "Best" captures where eval jumps from <30cp to >100cp; confidence = bait_count/5 capped 0.9 | 1 game |
| J | Impulsive check block | author_error | high | Blunders/mistakes with "+" or "#" in SAN; confidence = block_count/3 capped 0.85 | 1 game |
| O | Repetition avoidance greed | author_error | critical | Find 3-move stable eval window (<30cp variance), then check next 3 moves for blunder; confidence = 0.6 | 3 games |
| P | Visual misrecognition | author_error | high | Blunders involving captures or major pieces (Q/R) when eval > 0; confidence = 0.5 | 3 games |
| Q | Active defense | recovery_strategy | low | Games with 200+cp blunders that were still won; confidence = 0.8 | 3 games |
| Q1 | Desperate Gambit Mode | recovery_strategy | low | Lost position (300+cp blunder), reject queen trades, create checks, win; confidence = 0.7 | 1 game |
| R | Endgame relaxation | author_error | high | Blunders in endgame when eval was >300cp ahead; confidence = 0.7 | 3 games |

**Detect_all flow:**
```python
for pid in library.patterns:
    if total_games < pdef.min_games: continue
    detector = getattr(self, f"_detect_{pid.lower()}")
    if detector:
        match = detector(analyses, metadata)
        if match and match.frequency >= pdef.min_occurrences:
            matches.append(match)
```

Each detector operates on `list[GameAnalysis]`. No cross-detector communication. No state persists between detect_all calls.

#### 5.6 llm_client.py
**Provider cascade (tried in order):**

| # | Provider | API Key | Default Model | Base URL | Pricing |
|---|----------|---------|---------------|----------|---------|
| 1 | NVIDIA | `NVIDIA_API_KEY` | `nvidia/nemotron-3-super-120b-a12b` | `https://integrate.api.nvidia.com/v1` | Free |
| 2 | Cerebras | `CEREBRAS_API_KEY` | `gpt-oss-120b` | `https://api.cerebras.ai/v1` | Free |
| 3 | DeepSeek V4 Flash | `DEEPSEEK_API_KEY` | `deepseek-v4-flash` | `https://api.deepseek.com/v1` | $0.14/$0.28 per 1M tokens |

**Defaults:** max_tokens=2000, temperature=0.3, timeout=60s

**`_call_llm()`:**
1. Check API key → return None if absent
2. POST `{base_url}/chat/completions` with payload: `{model, messages[{system, user}], max_tokens, temperature}`
3. Handle HTTP 401/402/429 → return None with token_log
4. Parse response: extract usage (prompt/completion tokens), content
5. Estimate cost from PROVIDER_PRICING table
6. Return `(content, token_log)` or `(None, token_log)`

**Coaching prompt structure:**
```
Player: {username}
Games analyzed: {n}

=== Per-Game LLM Analysis ===  (if available)
- {game_id} ({color}): ACPL={x}, blunders={y}
  Analysis: {summary}

=== Pattern Detection Results ===
- [{SEVERITY}] {ID}: {name} (confidence: {conf}%, frequency: {freq})
  Hypothesis: ...
  Mitigation: ...

=== Weakness Report ===
Total ACPL: ... | Blunders: ... | Mistakes: ... | Inaccuracies: ...
Phase breakdown: ...
Leaky openings: ...

=== INSTRUCTIONS ===
Produce coaching report: 1. Summary  2. Priority Issues  3. Training Recs  4. Strengths  5. Next Focus
```

**System prompt rules:**
1. No invented evidence
2. Hedging language for unsupported findings
3. May group/prioritize patterns
4. Explicit if data ambiguous
5. Club-level language (1200-1800 Elo)
6. Never "you always"/"you never"
7. Output in Czech

**`_fallback_report()`:** raw data dump when all providers fail.

#### 5.7 game_llm_cache.py
Optional per-game LLM analysis (L3 cache). Content-tagged via SHA256 hash of Stockfish data. Used to enrich coaching prompt with per-game summaries.

#### 5.8 compressibility_validator.py
```python
compression_ratio = total_moves / (BASE_COST(10) + evidence_count * 2)
```
Maps to Mikolov compression philosophy: pattern must compress data.

#### 5.9 validator.py
Post-analysis sanity checks:
- Missing username / zero games
- Duplicate pattern IDs
- Confidence not in [0,100]
- Severity not in {low, medium, high, critical}
- Frequency < 1
- Hypothesis not starting with "Hypothesis:"
- Raises `ValidationError` on failure

#### 5.10 logger.py
- File: `logs/lichess_mcp_{YYYYMM}.log`
- Format: `timestamp | LEVEL | name | message`
- propagate=False (no console duplication)

### 6. L2 Resources

**`analysis_resources.py`:**
- `lichess://analysis/{key}` → JSON analysis data
- `lichess://analysis/list` → list of stored keys
- Store: `data/resource_store/analysis_store.json`

**`pattern_resources.py`:**
- `lichess://patterns/{key}` → JSON pattern data
- `lichess://patterns/list` → list of stored keys
- Store: `data/resource_store/pattern_store.json`

### 7. Cache Layer Architecture

| Layer | Location | Key | TTL | Write Trigger |
|-------|----------|-----|-----|---------------|
| L0 | `data/game_cache/{user}_games.json` | username | 3600s | fetch_user_games() |
| L1 | `data/pgn_cache/{game_id}.pgn` | game_id | ∞ | fetch_game_pgn() |
| L2 | `data/game_cache/{id}_{color}_d{depth}.json` | game_id+color+depth | ∞ | analyze_pgn() |
| L3 | `data/game_cache/{game_id}_llm.json` | game_id | ∞ (content-hash) | analyze_game_llm() |
| Analysis Resource | `data/resource_store/analysis_store.json` | key | ∞ | tool calls |
| Pattern Resource | `data/resource_store/pattern_store.json` | key | ∞ | tool calls |

All disk writes use `.tmp` + `os.replace()` for atomicity.

### 8. Dependencies

```toml
[project]
name = "lichess-analyzer-mcp"
version = "0.1.0"
requires-python = ">=3.12, <3.14"
dependencies = ["mcp>=1.0.0", "berserk>=0.14.0", "chess>=1.11.0,<2", "httpx>=0.28.0"]

[project.scripts]
lichess-mcp = "lichess_analyzer_mcp.server:main"

[tool.ruff]
line-length = 100
target-version = "py312"
select = ["F", "E", "W", "I", "N", "UP", "S"]

[dev]
pytest>=8, pytest-asyncio>=0.24, coverage>=7
```

### 9. Configuration & Environment Variables

Set via `.env` file (UTF-8 with BOM) + PowerShell wrapper:

```
LICHESS_TOKEN=lip_xxx              # Lichess API token (read-only)
NVIDIA_API_KEY=nvapi-xxx           # NVIDIA Nemotron
CEREBRAS_API_KEY=cere-xxx          # Cerebras
DEEPSEEK_API_KEY=sk-xxx            # DeepSeek V4 Flash
```

Optional overrides: `NVIDIA_MODEL`, `CEREBRAS_MODEL`, `DEEPSEEK_V4_MODEL`, `STOCKFISH_PATH`, `STOCKFISH_SEARCH_DIRS`, `LLM_MAX_TOKENS` (2000), `LLM_TEMPERATURE` (0.3), `LLM_TIMEOUT` (60.0)

### 10. Error Handling Patterns

**All tools:** universal try/except → `{"error": str(e)}`

**`_export_by_player()`:** 3 retries on 429, graceful 404 → []
**Zombie recovery:** analysis lock timeout >120s → restart engine
**Disk writes:** silent on OSError, atomic via .tmp
**Batch pipeline:** per-game try/except → skip + log anomaly, continue rest

### 11. Data Flow Diagram (Text)

```
LLM Agent/MCP Client
    │
    ▼ FastMCP (stdio)
    │
    ├─► T1 fetch_games
    │       └─► lichess_client.fetch_user_games()
    │               ├─► berserk API
    │               └─► L0 cache
    │
    ├─► T2 analyze_game
    │       ├─► lichess_client.fetch_game_pgn() → L1 cache
    │       └─► game_analyzer.analyze_pgn()
    │               └─► engine_client.evaluate_move() → Stockfish
    │               └─► L2 cache
    │
    ├─► T6 diagnose_player
    │       └─► [T2 × N games] → diagnostician.diagnose() → WeaknessReport
    │
    ├─► T7 match_patterns
    │       └─► [T2 × N games] → PatternDetector.detect_all() → PatternMatch[]
    │               └─► compressibility_validator
    │               └─► validator
    │
    ├─► T3/T4/T5/T8/T9 (thin wrappers, 1-2 service calls each)
    │
    └─► Phase 4 (optional): LLM Cascade
            WeaknessReport + PatternMatch[]
                └─► llm_client.build_coaching_prompt()
                        └─► NVIDIA → fallback → Cerebras → fallback → DeepSeek → fallback → _fallback_report()
```

---

## Audit Instructions

Please analyze the above pipeline and produce an audit report with the following sections. Your audit must be **de novo** — do not search for prior analyses, do not reference known issues from outside this document. Base your findings solely on the digital twin above.

### Section 1: Executive Summary
- 3-5 sentence overview of the system's overall health
- Number of findings by severity (Critical / Major / Minor / Info)
- Estimated maturity level (1-10)

### Section 2: Architecture Assessment
Evaluate:
- **Module separation**: Are responsibilities cleanly divided between tools, services, models, and resources?
- **Data flow**: Is the pipeline linear, composable, or tangled? Are there circular dependencies?
- **MCP compliance**: Does the server correctly implement MCP tool/resource semantics? Are there anti-patterns?
- **Extensibility**: How hard would it be to add a new tool, a new pattern detector, a new cache layer?

### Section 3: Correctness Analysis
Evaluate each layer for potential bugs:
- **Data acquisition**: berserk API usage, error handling, edge cases (rate limiting, 404, connection drops)
- **Stockfish analysis**: cp_loss algorithm correctness, color perspective (is the negation in evaluate_move correct?), depth approximation in cache, classification thresholds
- **Pattern detection**: Are the heuristics sound? False positive potential? Minimum thresholds (min_games, min_occurrences)?
- **Diagnostician**: hardcoded top_weaknesses rules — are they correct for all edge cases?

### Section 4: Security & Threat Model
Focus on risks specific to MCP servers exposed to LLM agents:
- **Token leakage**: .env handling, stderr logging of API key presence
- **SSRF / path traversal**: Any tool args that could be abused?
- **Resource exhaustion**: Stockfish engine (compute-bound), LLM cascade (API cost), disk cache growth
- **Input validation**: FEN validation, PGN validation, username validation — are there injection vectors?
- **Denial of service**: What happens if an LLM agent calls a tool with extreme parameters (depth=24, max_games=50, repeated calls)?

### Section 5: Performance Evaluation
- **Stockfish bottleneck**: per-move evaluation is ~16 depth per move at ~3.5s/game. Implications for batch analysis of 50 games?
- **Cache efficiency**: Do cache layers actually reduce latency? Depth approximation vs exact match — tradeoff?
- **Analysis lock**: threading lock with 120s timeout — does this serialise all tool calls? Impact on concurrent clients?
- **Serialization overhead**: GameAnalysis.to_dict/from_dict round-trips on every cache read/write

### Section 6: Reliability & Error Handling
- **The universal `{"error": str(e)}` pattern**: What information is lost? Is this an anti-pattern for MCP?
- **Zombie recovery**: Is the 120s timeout correct? What happens during recovery to in-flight analysis?
- **Graceful degradation**: What happens when LLM cascade fails? When Stockfish is missing? When Lichess API is down?
- **Silent failures**: Any paths where errors are swallowed without logging?

### Section 7: Code Quality Assessment
Score each module 1-5 on: Readability, Testability, Robustness, Error Handling

| Module | Readability | Testability | Robustness | Error Handling |
|--------|------------|-------------|------------|----------------|
| server.py | | | | |
| lichess_client.py | | | | |
| engine_client.py | | | | |
| game_analyzer.py | | | | |
| diagnostician.py | | | | |
| pattern_detector.py | | | | |
| llm_client.py | | | | |
| tools/* | | | | |

### Section 8: Top 5 Findings
Ranked by severity × likelihood:
1. **ID**: title (severity)
   - Location: file:line
   - Description
   - Why it matters
   - Suggested fix (conceptual, not code)

2. ... (repeat for top 5)

### Section 9: Recommendations
Organized by timeframe:
- **Immediate** (bugs that could produce wrong results today)
- **Short-term** (improvements for stability and correctness)
- **Medium-term** (architectural improvements)

### Section 10: Summary Assessment
- Overall score (1-10)
- Biggest strength
- Biggest weakness
- Is the system production-ready for personal use? For public MCP publishing?

---

## Output Format

Please produce your report as a structured Markdown document with the section headings above. For the Top 5 Findings, use a table:

| ID | Severity | Location | Description | Impact |
|----|----------|----------|-------------|--------|
| F1 | Critical | ... | ... | ... |

For the Code Quality Score, include the matrix table.

For MCP compliance analysis, reference specific MCP specification features (tools, resources, prompts, sampling, streaming, progress).

---

## Additional Notes

- The system runs on **Windows** (PowerShell stdio transport). Consider Windows-specific issues (path separators, process management, BOM handling).
- Stockfish is bundled as `stockfish/stockfish.exe` — verify this is the correct architecture for the deployment target.
- The `.env` file uses **UTF-8 BOM** encoding — the loader uses `utf-8-sig` to compensate.
- The SRS engine (FSRS) is present but no MCP tool exposes it directly. Consider whether this is dead code or intended for future use.
- The `kb/` module (schemas, writer, md_reporter) is imported but its usage is limited to validation. Evaluate whether this is properly integrated.

---

*End of audit prompt. Generate your independent audit report based solely on the above digital twin.*
