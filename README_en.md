[![](https://flagcdn.com/24x18/cz.png "CZ")][ CZ ](./README.md)

# Lichess MCP Analyzer

**An MCP server for analyzing chess games, detecting recurring mistake patterns (the pattern library as a compression model per T. Mikolov), and spaced-repetition training (SM-2-like; FSRS is not implemented yet).**

> **New session:** start at `docs/SESSION_HANDOFF_2026-11-17.md` (current state, commands, open items).

Version: `0.1.0` | State (2026-11-18): **single-game pipeline [2.15]** (compact 2.7 default, detailed 1.2) | Tests: **556 fast** (excluding `test_engine_client.py`) / 18 real-engine (pinned Stockfish 18) | Tools: **18** | Schemas: compact 2.7 / detailed 1.2 / cross-game 1.4 / game_full 1.0


## Why?

This repository has a **dual purpose**:

1. **Chess analyzer** — a personalized training tool that downloads your games from Lichess, analyzes every move with Stockfish, detects 17 recurring patterns (A-S + U/V) from your game history, diagnoses phase-specific weaknesses, and helps you learn from them with spaced repetition.

2. **MCP building block** — a demonstration project for validating MCP server design principles in practice. Every component (Lichess API, Stockfish engine, pattern detection engine, SRS, B2B-Knowledge-Base persistence) is independently usable and transferable to another domain.

> "Build tools for yourself first. If they solve a real problem, they solve a general one."


## How it works

```
Your question (in opencode)
       |
       v JSON-RPC 2.0 (stdio)
       |
lichess-analyzer-mcp (Python FastMCP)
       |
       +--- Lichess API (berserk) --------- lichess.org
       +--- Stockfish 18 (UCI) ------------ local binary
       +--- Pattern detector -------------- compression model (Mikolov)
       +--- BlunderFactSheet -------------- DBCL Phase 2 (context window, engine_lines, pattern_matches)
       +--- Narrative validator ----------- LLM hallucination guard (5 claim categories)
       +--- LLM reasoning (cascade) ------- NVIDIA / Cerebras / DeepSeek V4 Flash
       +--- SM-2-like engine -------------- spaced repetition
       +--- KB writer --------------------- B2B-Knowledge-Base
       +--- MD reporter ------------------- data/reports/ (gitignored)
```


## Pattern detection as a compression model

> "A representation of reality minimizing complexity, prediction error, and computational cost."

### Lossy Compression Principle (T. Mikolov / CPM)

Pattern detection = **lossy compression**. The goal is to find patterns that describe reality with maximum entropy value per minimum tokens. The chess pattern artifact is a compression model of the player: it minimizes complexity (17 patterns instead of 1000+ moves), prediction error (Stockfish cp_loss as ground truth), and computational cost (2s cached runtime).

### Validation (MSE)

- MSE from the right: move prediction from patterns vs. reality (Stockfish evaluation)
- If **MSE(pattern) < MSE(average)**, the model is valid
- If **MSE(pattern) ~ MSE(average)**, the pattern is noise

### Lossy compression

The pattern library ignores individual moves (noise) and extracts behavioral patterns (signal). Lossy compression = losing detail (exact cp_loss value) in order to capture the pattern (the player prefers X).

**Rule:** A pattern is good if it:
- captures behavior (signal)
- removes individual errors (noise)
- does not remove structure (trends, phase-specific weaknesses)

### Occam's razor

The compression ratio (`compression_ratio` = raw_cost / pattern_cost) is a measure of Occam's razor. Of two patterns explaining the data equally well, the one with the **higher compression ratio is more correct**.

### Confidence formula (Mikolov)

```
final_confidence = 0.5 x compression_score + 0.3 x entropy_score + 0.2 x sample_score
```

This addresses the **small-N authority problem**: a pattern is valid even at N < 25 if it compresses well (compression_ratio > 1.5 = signal, > 10 = strong signal, < 1.0 = noise).

> Historical note: this formula was superseded in `PATTERN_DISCOVERY_METHODOLOGY.md` section 11.1 - runtime now uses `coverage_score`, while true two-term MDL lives in the measurement layer (`services/mdl.py`). See `docs/01_EVIDENCE_DIGEST.md` section 4.

### Semantic integrity - the Pattern O lesson

**CR = N / (C_impl + C_udrz) only makes sense if N = the number of instances of the same thing.**

Pattern O was originally named "Repetition avoidance greed", but the code detected *flat eval plateau -> blunder*, not *repetition refusal*. Result: CR=47.8 measured noise, not signal. **Fix:** rename to "Stagnation panic" (Option A) - the description now matches the code. See `docs/01_EVIDENCE_DIGEST.md` section 4 (historical record).

**Rule:** Every pattern must pass a semantic audit (AUD phase): do the name, mechanism, and hypothesis match the code? If not - fix the description or fix the code.


## Tools (18 MCP tools)

| Tool | Description |
|------|-------------|
| `lichess_fetch_games` | Fetch a player's recent games from Lichess (max 999, berserk pagination fix) |
| `lichess_games_index` | Return a cache index of games by result (win/loss/draw) |
| `lichess_analyze_game` | Analyze one game with Stockfish (depth 8-24, per-move cp_loss, BlunderFactSheet) |
| `lichess_analyze_position` | Analyze a FEN position (depth 8-24, multipv 3, optional cloud eval) |
| `lichess_opening_explorer` | Explore an opening in Lichess / Masters database |
| `lichess_player_profile` | Return player profile, ratings, and statistics |
| `lichess_diagnose_player` | Diagnose weaknesses across multiple games (phases, openings, ACPL) |
| `lichess_match_patterns` | Detect recurring A-S + U/V patterns; supports `game_ids` for anonymous games |
| `lichess_analyze_pending` | Batch analysis of pending games (detection consistency) |
| `lichess_analyze_anonymous_session` | Batch analysis of anonymous games (URL/ID/txt, label support, aggregation) |
| `lichess_import_pgn` | Import PGN from any source for analysis |
| `lichess_coaching_single_game` | Single-game coaching report (contract 1.2, deterministic fallback) |
| `lichess_coaching_cross_game` | Cross-game coaching across multiple games |
| `lichess_coaching_opening_report` | Opening report from multiple games |
| `lichess_coaching_opponent_pool` | Opponent pool analysis from `game_ids` |
| `lichess_coaching_training_plan` | Training plan based on weaknesses and available time |
| `lichess_persist_report` | Generate and persist a report to disk (data/reports or KB) |
| `lichess_workspace_info` | Return workspace context |

### Compact JSON 2.7

The canonical runtime contract (fields, null/omission policy, alias collisions, prompt, and example) is `docs/COMPACT_JSON_FOR_LLM.md`. Schema: `schemas/single_game_v2_compact_2.7.json`.


## DBCL Phase 2 - implemented state

### BlunderFactSheet (`models/analysis.py`)

Per-blunder structure with:
- `fen_before`, `board_state` (was_in_check, checking_pieces, capture/king check)
- `legal_moves` (captures/king_moves/blocks/checks)
- `engine_lines` (rank, move_san, eval_cp, win_prob, PV)
- `played_move_rank`, `pattern_matches` (pattern_id, name, confidence, evidence)
- `context_window` (3 moves before/after with eval + win_prob)
- `detector_version`: `DBCL-20261117-dev`

### Narrative validator (`services/narrative_validator.py`)

5 claim categories for the LLM hallucination guard: piece-on-square, check, capture, eval-number, king-move. Each category has its own validation function.

### Engine lines silent fail - root cause fixed

30% of BFS had 0 `engine_lines` due to a `board.san(m)` AssertionError on multi-move PV. **Fix:** sequential `board.copy()` + try/except. RUN_005: 0% failure (out of 70/70 BFS). See `docs/01_EVIDENCE_DIGEST.md` section 3.

### Pattern N - x-ray pin detection

Detected in `_per_blunder_patterns()`: centipawn_loss >= 200 + phase=endgame + was_in_check. Tests in `tests/test_dbcl.py`.

### Pattern I -> concept

Pattern I (Bait trap) moved to `manual_only`; its auto-detection code was merged into I2 (Gift exploitation). AUD-03/11 RESOLVED.


## LLM reasoning pipeline

Deterministic output (patterns + weakness report) is transformed into a natural-language training report by an LLM provider cascade.

### Architecture

```
Pipeline data (patterns + weakness)
       |
       v build_coaching_prompt()
       |
       v LLM cascade (first success wins)
       |
       +--- NVIDIA (free) ............ nemotron-3-super-120b
       +--- Cerebras (free) .......... gpt-oss-120b
       +--- DeepSeek V4 Flash ($) .... deepseek-v4-flash ($0.14/$0.28 per 1M tok)
       |
       v generate_md_report()
       |
       v data/reports/coaching_report_{user}_{ts}.md (gitignored)
```

Controlled by the `DEFAULT_PROVIDER` env var:
- `""` (unset) -> NVIDIA -> Cerebras -> DS V4 Flash
- `cerebras` -> Cerebras -> NVIDIA -> DS V4 Flash
- `deepseek` -> DeepSeek V4 Flash -> NVIDIA -> Cerebras

### Pipeline mode

`run_coaching_pipeline(mode="auto")` picks an architecture per golden rules:

| Mode | When | What it does |
|------|------|--------------|
| `auto` | default | N<=30 -> monolithic, N>30 -> incremental |
| `mono` | quick analysis | 1 LLM call, raw data in prompt |
| `incremental` | hundreds of games, PGN import | per-game LLM cache + summary aggregation |

### Provider comparison (5 games, same data)

| Provider | Model | Tokens | Latency | Cost/5 games | SNR |
|----------|-------|--------|---------|--------------|-----|
| NVIDIA | nemotron-3-super-120b-a12b | 2 597 | 17s | $0.000 | 57% |
| Cerebras | gpt-oss-120b | 2 677 | - | $0.000 | 54% |
| DeepSeek V4 Flash | deepseek-v4-flash | 3 876 | 31s | $0.001 | **93%** |

SNR = semantic fidelity to the input data (confidence %, phase ACPL, no invented patterns).

### API keys (optional)

In `.env` (all free except DeepSeek):
```
NVIDIA_API_KEY=nvapi-...
CEREBRAS_API_KEY=csk-...
DEEPSEEK_API_KEY=sk-...       # shared for DS Chat and V4 Flash
LLM_MAX_TOKENS=4000            # default 2000, 4000 for a full report
```


## Quick start

### 1. Clone

```
git clone https://github.com/outpost2026/lichess-mcp-analyzer.git
cd lichess-mcp-analyzer
```

### 2. Download Stockfish

```
powershell -File scripts\setup_stockfish.ps1
```

Or download manually from [official-stockfish/Stockfish](https://github.com/official-stockfish/Stockfish/releases) and place `stockfish.exe` in the `stockfish/` directory.

### 3. Set LICHESS_TOKEN

Create a `.env` file in the repo root:

```
LICHESS_TOKEN=lip_xxx
```

Create the token at [lichess.org/settings/oauth](https://lichess.org/settings/oauth).

### 4. Start the MCP server

```
uv sync
uv run python -m lichess_analyzer_mcp.server
```

The server connects over stdio. For opencode, register it in `opencode.jsonc`:

```json
"lichess-analyzer": {
    "type": "local",
    "command": ["path\\to\\repo\\.venv\\Scripts\\python.exe", "-X", "utf8", "-m", "lichess_analyzer_mcp.server"],
    "enabled": true,
    "timeout": 60000
}
```

### 5. Or use the CLI pipeline

```
# One game -> compact JSON 2.7 (default, offline)
uv run python scripts\coach.py --game-id FVhqtv1S --username systeq --no-llm --out data\reports\FVhqtv1S.json

# Explicit detailed 1.2, or both forms
uv run python scripts\coach.py --game-id lxO3gwd3 --format detailed
uv run python scripts\coach.py --game-id lxO3gwd3 --format both --out both.json

# Last N games of a player (compact array / NDJSON)
uv run python scripts\coach.py --username systeq --batch 3 --no-llm --out data\runs\batch.json

# Batch pipeline over a whole profile (legacy, cross-game)
uv run python scripts\run_pipeline.py outpost2026 --games 20 --depth 12
```


## Usage examples

### "What is this player?"

```
> lichess_player_profile("outpost2026")

{
  "username": "outpost2026",
  "ratings": {
    "blitz": {"rating": 1950, "games": 342},
    "rapid": {"rating": 1880, "games": 156}
  },
  "total_games": 523
}
```

### "Analyze my last game"

```
> lichess_analyze_game("abc12345")

{
  "game": {"opening": "Sicilian Defense", "result": "1-0"},
  "stats": {"total_acpl": 45.2, "blunders": 1, "total_moves": 42},
  "blunders": ["Move 28: Nxe5 (loss 450cp)"]
}
```

### "Diagnose weaknesses"

```
> lichess_diagnose_player("outpost2026", max_games=15)

{
  "total_acpl": 62.3,
  "phase_weaknesses": {
    "middlegame": {"acpl": 78.1, "blunders": 4},
    "endgame": {"acpl": 45.0, "blunders": 1}
  },
  "top_weaknesses": [
    "Tactical awareness in middlegame transitions",
    "Opening preparation: Sicilian Defense"
  ]
}
```

### "Find recurring mistakes"

```
> lichess_match_patterns("outpost2026")

{
  "patterns_detected": [
    {
      "pattern_id": "B",
      "pattern_name": "Automatic grab",
      "confidence": 85,
      "severity": "high",
      "mitigation": "3-sec pause + 'WHAT IS THIS?' before every capture"
    }
  ]
}
```


## Repository structure

```
lichess-analyzer-mcp/
├── stockfish/               <- Stockfish 18 binary (not committed)
├── src/
│   └── lichess_analyzer_mcp/
│       ├── app.py               <- FastMCP instance
│       ├── server.py            <- Entry point + .env load + tool registration
│       ├── models/              <- Data models (dataclasses)
│       │   ├── game.py          <- GameSummary, MoveAnalysis, GameAnalysis
│       │   ├── analysis.py      <- BlunderFactSheet, PositionAnalysis, WeaknessReport
│       │   ├── pattern.py       <- PatternDef, PatternMatch, PatternLibrary
│       │   ├── srs_card.py      <- SRSCard, FSRSState
│       │   └── player_profile.py <- PlayerProfile, OpeningStats
│       ├── services/
│       │   ├── lichess_client.py    <- berserk wrapper (fetch, index, cache)
│       │   ├── engine_client.py     <- Stockfish UCI wrapper (depth limit, PV SAN fix)
│       │   ├── game_analyzer.py     <- per-move eval + BlunderFactSheet + per-blunder patterns
│       │   ├── pv_recovery.py       <- PV retry for blunders/mistakes without engine_lines (FIX-014)
│       │   ├── compact_serializer.py <- schema 2.7 (default) + validation + null policy
│       │   ├── game_llm_cache.py    <- per-game LLM cache
│       │   ├── llm_client.py        <- multi-provider LLM cascade
│       │   ├── narrative_validator.py <- LLM hallucination guard (5 claims)
│       │   ├── pattern_detector.py  <- 16 detectors (A-S + U/V; I manual_only)
│       │   ├── diagnostician.py     <- cross-game weakness report
│       │   ├── srs_engine.py        <- SM-2 spaced repetition
│       │   ├── compressibility_validator.py <- compression ratio validation
│       │   └── pattern_artifact_validator.py <- pattern semantic contract
│       ├── tools/               <- 18 MCP tools
│       ├── resources/           <- L2 Resources (analysis, patterns)
│       ├── kb/
│       │   ├── writer.py        <- KB persistence layer
│       │   ├── md_reporter.py   <- MD report generation
│       │   └── schemas.py       <- KB schema definitions
│       └── patterns/
├── scripts/
│   ├── coach.py                 <- Unified CLI: game / PGN / batch, compact 2.7 default
│   ├── run_pipeline.py          <- CLI batch pipeline
│   ├── coach_single.py          <- Legacy single-game CLI (deprecated)
│   ├── mcp_call.py              <- CLI runner for all 18 MCP tools
│   ├── pgn_to_compact.py        <- Deprecated shim over coach.py
│   ├── setup_stockfish.ps1      <- Automatic Stockfish download
│   └── verify_docs_trimming.py  <- Verify the 2026-11-18 docs trimming (11 assertions)
├── tests/                       <- 556 fast + 18 real-engine (2026-11-18; marker real_engine)
├── docs/                        <- 9 active files (trim 2026-11-18)
│   ├── 00_DOCS_CONTRACT.md      <- Read order, authority, rules
│   ├── SESSION_HANDOFF_*.md     <- Current state, commands, open items
│   ├── COMPACT_JSON_FOR_LLM.md  <- Runtime contract 2.7 + game_full Appendix A
│   ├── CLI_USAGE.md             <- CLI + 18 MCP tool invocations
│   ├── AUDIT_INTEGRATION_*.md   <- Binding decisions D1-D40
│   ├── PATTERN_DISCOVERY_*.md   <- Binding methodology v1.7
│   ├── HALUCINACE_ROOT_CAUSE_ANALYSIS.md <- Anti-fabrication
│   ├── 01_EVIDENCE_DIGEST.md    <- Historical evidence and decision provenance
│   └── 02_COACHING_EXEMPLARS.md <- Representative reports + findings catalogue
├── _ARCHIVE/                    <- 113 historical artifacts (git history, not active navigation)
├── data/                        <- gitignored: game_cache/, pgn_cache/, reports/, runs/
├── config/engine_identity.json  <- Pinned Stockfish identity (CI)
├── lichess-mcp.bat              <- Cross-shell launcher (Windows)
├── .env                         <- LICHESS_TOKEN (never commit)
├── README.md                    <- Czech version
├── README_en.md                 <- This file
├── CHANGELOG.md                 <- Release history
├── pyproject.toml               <- Project config, dependencies
└── LICENSE                      <- MIT
```


## Stack

| Layer | Technology |
|-------|------------|
| Runtime | Python 3.12+, uv |
| Framework | FastMCP (mcp>=1.0.0) |
| Lichess API | berserk>=0.14.0 |
| Chess engine | chess>=1.11.0 (python-chess) + Stockfish 18 BMI2 |
| Spaced repetition | SM-2-like (FSRS needs a separate implementation and state migration) |
| HTTP / LLM API | httpx>=0.28.0 |
| LLM providers | NVIDIA (nemotron-3), Cerebras (gpt-oss), DeepSeek (deepseek-v4-flash) |
| Documents | python-docx>=1.2.0 |
| Persistence | B2B-Knowledge-Base (JSON + Markdown) |
| Testing | pytest 8+, pytest-cov, mypy |
| Lint | ruff (CI: E4/E7/E9/F; wider I/UP/N/S/E501 set = tech debt) |


## Project status

Current contracts, validation sample, open items, and agent rules: `docs/SESSION_HANDOFF_2026-11-17.md`. Release history: `CHANGELOG.md`. Root causes and dated measurements from earlier iterations: `docs/01_EVIDENCE_DIGEST.md`. Representative coaching outputs: `docs/02_COACHING_EXEMPLARS.md`.


## Documentation

Read order, file authority, and the single-source-of-truth rule: `docs/00_DOCS_CONTRACT.md`. All historical artifacts are in `_ARCHIVE/`.


## Inspiration & credits

This project is not a fork - it is an original architecture - but valuable inspiration and infrastructure components come from the following open-source projects.

### Primary sources (libraries)

| Project | Author | Use |
|---------|--------|-----|
| [berserk](https://github.com/lichess-org/berserk) | lichess-org / Matt Harrison | Lichess API Python client |
| [python-chess](https://github.com/niklasf/python-chess) | Niklas Fiekas | PGN/FEN parsing, UCI wrapper |
| [Stockfish](https://github.com/official-stockfish/Stockfish) | The Stockfish team | Local chess engine |
| [fastmcp](https://github.com/jlowin/fastmcp) | Jeremiah Lowin | FastMCP framework |
| [py-fsrs](https://github.com/open-spaced-repetition/py-fsrs) | Open Spaced Repetition | FSRS algorithm |

### Sibling MCP servers in the portfolio

| Server | Tools | Key pattern |
|--------|-------|-------------|
| [cnc-tools](https://github.com/outpost2026/mcp-local-server) | 21 | Session state, caching, audit log |
| [linkedin-analyzer](https://github.com/outpost2026/linkedin-mcp-custom) | 7 | FastMCP, KB write-back, EROI scoring |
| [mcp-jobs](https://github.com/outpost2026/MCP-Jobs) | 6 | Boolean AST match, multi-portal scraping |
| [lichess-analyzer](https://github.com/outpost2026/lichess-mcp-analyzer) | 18 | Deterministic pipeline + LLM cascade |
| [mcp-retrieval](https://github.com/outpost2026/mcp-retrieval) | 5 | GT postmortem retrieval with abstention |

### Engine integration debugging

Two critical bugs in `engine_client.py` were identified and fixed during development:
- **Perspective inversion** - cp_loss computed from the opposite side
- **Best-move comparison** - cp_loss computed as a before/after delta rather than best/actual

After the fix: ACPL MAE of 3.9 vs the Lichess reference (depth 18-22). See `docs/01_EVIDENCE_DIGEST.md` section 4 (historical experiment).

Later, the **engine_lines silent fail** was fixed: 30% -> 0% failure rate (sequential board.copy + try/except). See `docs/01_EVIDENCE_DIGEST.md` section 3.


## License

MIT (c) 2026 Ondrej Sousek (outpost2026)
