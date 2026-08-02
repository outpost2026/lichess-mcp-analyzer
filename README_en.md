<div align="left">
  <a href="https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/README.md">
    <img src="https://flagcdn.com/24x18/cz.png" alt="CZ" height="18"> Cesky
  </a>
</div>

# Lichess MCP Analyzer

**MCP server for chess game analysis, pattern detection (compression model per T. Mikolov), and spaced repetition training (FSRS/SM-2).**

Version: `0.1.0` | Status: **DBCL Phase 2 complete** | Tests: **68/68** | Tools: **11**


## Why?

This repository has a **dual purpose**:

1. **Chess analyzer** — a personalized training tool that fetches your Lichess games, analyzes every move with Stockfish, detects 14+ behavioral patterns (A–S) from your play history, diagnoses phase weaknesses, and helps you learn from mistakes using spaced repetition.

2. **MCP construction kit** — a demonstration project that validates MCP server design principles on real case studies. Every component (Lichess API, Stockfish engine, pattern detection engine, SRS, B2B-Knowledge-Base persistence) is independently usable and transferable to other domains.

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
       +--- FSRS/SM-2 engine -------------- spaced repetition
       +--- KB writer --------------------- B2B-Knowledge-Base
       +--- MD reporter ------------------- docs/ coaching reports
```


## Pattern detection as a compression model

> "A representation of reality minimizing complexity, prediction error, and computational cost."

### Lossy Compression Principle (T. Mikolov / CPM)

Pattern detection = **lossy compression**. The goal is to find patterns that describe reality with maximum entropy value per minimum tokens. The chess pattern artifact is a compression model of the player: it minimizes complexity (14 patterns instead of 1000+ moves), prediction error (Stockfish cp_loss as ground truth), and computational cost (2s cached runtime).

### MSE Validation

- MSE feedback: predict moves based on patterns vs. reality (Stockfish evaluation)
- If **MSE(pattern) < MSE(average)**, the model is valid
- If **MSE(pattern) ≈ MSE(average)**, the pattern is noise

### Lossy compression

The pattern library discards individual moves (noise) and extracts behavioral patterns (signal). Lossy compression = lose details (exact cp_loss value) to capture the pattern (the player prefers X).

**Rule:** A pattern is good if it:
- captures behavior (signal)
- removes individual errors (noise)
- preserves structure (trends, phase weaknesses)

### Occam's razor

Compression ratio (`compression_ratio` = raw_cost / pattern_cost) is the measure of Occam's razor. Given two patterns that explain the data equally well, the one with the **higher compression ratio is more correct**.

### Confidence formula (Mikolov)

```
final_confidence = 0.5 × compression_score + 0.3 × entropy_score + 0.2 × sample_score
```

Solves the **small-N authority problem**: a pattern is valid even with N < 25 if it compresses well (compression_ratio > 1.5 = signal, > 10 = strong signal, < 1.0 = noise).

### Semantic integrity — the Pattern O lesson

**CR = N / (C_impl + C_udrz) is only meaningful when N = count of instances of the same thing.**

Pattern O was originally named "Repetition avoidance greed", but the code detected *flat eval plateau → blunder*, not *repetition refusal*. Result: CR=47.8 measured noise, not signal. **Fix:** rename to "Stagnační panika" (Panic stagnation) — the description now matches the code. See `docs/CONTEXT_INJECT.md` §8.

**Rule:** Every pattern must pass a semantic audit (AUD phase): does the name, mechanism, and hypothesis match the code? If not — fix the description or fix the code.


## Tools (11 MCP tools)

| Tool | Description |
|------|-------------|
| `lichess_fetch_games` | Fetch recent games from Lichess (max 999, berserk pagination fix) |
| `lichess_games_index` | Quick game index cache by result (win/loss/draw) |
| `lichess_analyze_game` | Analyze a single game with Stockfish (depth 8-24, per-move cp_loss, BlunderFactSheet) |
| `lichess_analyze_position` | Analyze a FEN position (depth 8-24, multipv 3, cloud eval optional) |
| `lichess_opening_explorer` | Explore openings in Lichess / Masters database |
| `lichess_player_profile` | Get profile, ratings, and stats |
| `lichess_diagnose_player` | Diagnose weaknesses across multiple games (phases, openings, ACPL) |
| `lichess_match_patterns` | Detect A–S playing patterns + game_ids support for anonymous games |
| `lichess_analyze_pending` | Batch analyze uncached games (pending detection consistency) |
| `lichess_analyze_anonymous_session` | Batch analyze anonymous games (URL/ID/txt, label support, aggregation) |
| `lichess_import_pgn` | Import PGN from any source into analysis |
| `lichess_workspace_info` | Get workspace context |

L2 Resources:
- `lichess://analysis/{key}` — stored analysis results
- `lichess://patterns/{key}` — stored pattern detection results
- `lichess://analysis/list` — list all analyses
- `lichess://patterns/list` — list all pattern detections


## DBCL Phase 2 — Implemented

### BlunderFactSheet (`models/analysis.py`)

Per-blunder structure with:
- `fen_before`, `board_state` (was_in_check, checking_pieces, capture/king check)
- `legal_moves` (captures/king_moves/blocks/checks)
- `engine_lines` (rank, move_san, eval_cp, win_prob, PV)
- `played_move_rank`, `pattern_matches` (pattern_id, name, confidence, evidence)
- `context_window` (3 moves before/after with eval + win_prob)
- `detector_version`: `DBCL-20260727-dev`

### Narrative validator (`services/narrative_validator.py`)

5 claim categories for LLM hallucination guard: piece-on-square, check, capture, eval-number, king-move. Each category has its own validator function.

### Engine lines silent fail — root cause fixed

30% of BFS had 0 engine_lines due to `board.san(m)` AssertionError on multi-move PV. **Fix:** sequential `board.copy()` + try/except. RUN_005: 0% failure (70/70 BFS). See `docs/CONTEXT_INJECT.md` §5.

### Pattern N — x-ray pin detection

Detected in `_per_blunder_patterns()`: centipawn_loss ≥ 200 + phase=endgame + was_in_check. Tests in `tests/test_dbcl.py`.

### Pattern I → concept

Pattern I (Bait trap) moved to `manual_only`, auto-detection code merged into I2 (Gift exploitation). AUD-03/11 RESOLVED.


## LLM Reasoning Pipeline

The deterministic pipeline output (patterns + weakness report) is transformed into a natural-language coaching report via a cascade of LLM providers.

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
       v docs/coaching_report_{user}_{ts}.md
```

Switched via `DEFAULT_PROVIDER` env var:
- `""` (unset) → NVIDIA → Cerebras → DS V4 Flash
- `cerebras` → Cerebras → NVIDIA → DS V4 Flash
- `deepseek` → DeepSeek V4 Flash → NVIDIA → Cerebras

### Pipeline mode

`run_coaching_pipeline(mode="auto")` selects architecture by golden rules:

| Mode | When | What it does |
|------|------|--------------|
| `auto` | default | N≤30 → monolithic, N>30 → incremental |
| `mono` | quick analysis | 1 LLM call, raw data in prompt |
| `incremental` | hundreds of games, PGN import | per-game LLM cache + aggregate with summaries |

### Provider comparison (5 games, same data)

| Provider | Model | Tokens | Latency | Cost/5games | SNR |
|----------|-------|--------|---------|-------------|-----|
| NVIDIA | nemotron-3-super-120b-a12b | 2,597 | 17s | $0.000 | 57% |
| Cerebras | gpt-oss-120b | 2,677 | - | $0.000 | 54% |
| DeepSeek V4 Flash | deepseek-v4-flash | 3,876 | 31s | $0.001 | **93%** |

SNR = semantic fidelity to input data (confidence %, phase ACPL, no hallucinated patterns).

### API keys (optional)

Add to `.env` (all providers free except DeepSeek):
```
NVIDIA_API_KEY=nvapi-...
CEREBRAS_API_KEY=csk-...
DEEPSEEK_API_KEY=sk-...       # shared for DS Chat and V4 Flash
LLM_MAX_TOKENS=4000            # default 2000, use 4000 for full reports
```


## Quick start

### 1. Clone

```bash
git clone https://github.com/outpost2026/lichess-mcp-analyzer.git
cd lichess-mcp-analyzer
```

### 2. Download Stockfish

```powershell
powershell -File scripts\setup_stockfish.ps1
```

Or download manually from [official-stockfish/Stockfish](https://github.com/official-stockfish/Stockfish/releases) and place `stockfish.exe` in the `stockfish/` directory.

### 3. Set LICHESS_TOKEN

Create a `.env` file in the repo root:

```
LICHESS_TOKEN=lip_xxx
```

Generate your token at [lichess.org/settings/oauth](https://lichess.org/settings/oauth).

### 4. Start the MCP server

```powershell
uv sync
uv run python -m lichess_analyzer_mcp.server
```

The server connects over stdio. Register it in `opencode.jsonc`:

```json
"lichess-analyzer": {
    "type": "local",
    "command": ["path\\to\\repo\\.venv\\Scripts\\python.exe", "-X", "utf8", "-m", "lichess_analyzer_mcp.server"],
    "enabled": true,
    "timeout": 60000
}
```

### 5. Or use the CLI pipeline

```powershell
# Analyze your own profile (last 20 games)
uv run python scripts\run_pipeline.py outpost2026 --games 20 --depth 12

# Analyze with KB write-back
uv run python scripts\run_pipeline.py outpost2026 --games 10
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

### "Analyze last game"

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

### "Find playing patterns"

```
> lichess_match_patterns("outpost2026")

{
  "patterns_detected": [
    {
      "pattern_id": "B",
      "pattern_name": "Automatic grab",
      "confidence": 85,
      "severity": "high",
      "mitigation": "3-sec pause + 'A CO ON?' before every capture"
    }
  ]
}
```


## Repository structure

```
lichess-analyzer-mcp/
├── stockfish/               ← Stockfish 18 binary (not committed)
├── src/
│   └── lichess_analyzer_mcp/
│       ├── app.py               ← FastMCP instance
│       ├── server.py            ← Entry point + .env load + tool registration
│       ├── models/              ← Data models (dataclasses)
│       │   ├── game.py          ← GameSummary, MoveAnalysis, GameAnalysis
│       │   ├── analysis.py      ← BlunderFactSheet, PositionAnalysis, WeaknessReport
│       │   ├── pattern.py       ← PatternDef, PatternMatch, PatternLibrary
│       │   ├── srs_card.py      ← SRSCard, FSRSState
│       │   └── player_profile.py ← PlayerProfile, OpeningStats
│       ├── services/
│       │   ├── lichess_client.py    ← berserk wrapper (fetch, index, cache)
│       │   ├── engine_client.py     ← Stockfish UCI wrapper (depth limit, PV SAN fix)
│       │   ├── game_analyzer.py     ← per-move eval + BlunderFactSheet + per-blunder patterns
│       │   ├── game_llm_cache.py    ← per-game LLM cache
│       │   ├── llm_client.py        ← multi-provider LLM cascade
│       │   ├── narrative_validator.py ← LLM hallucination guard (5 claims)
│       │   ├── pattern_detector.py  ← 14 detectors (A–S, I→I2 merged)
│       │   ├── diagnostician.py     ← cross-game weakness report
│       │   ├── srs_engine.py        ← SM-2 spaced repetition
│       │   ├── compressibility_validator.py ← compression ratio validation
│       │   └── pattern_artifact_validator.py ← pattern semantic contract
│       ├── tools/               ← 11 MCP tools
│       ├── resources/           ← L2 Resources (analysis, patterns)
│       ├── kb/
│       │   ├── writer.py        ← KB persistence layer
│       │   ├── md_reporter.py   ← MD report generation
│       │   └── schemas.py       ← KB schema definitions
│       └── patterns/
├── scripts/
│   ├── run_pipeline.py          ← CLI batch pipeline
│   ├── setup_stockfish.ps1      ← Automatic Stockfish download
│   └── ...                      ← 20+ helper scripts
├── tests/
│   ├── test_services.py         ← 15 unit tests (models, compression, validation)
│   ├── test_prompt_contract.py  ← 13 contract tests (schema, mapping)
│   ├── test_engine_client.py    ← 5 tests with mocked Stockfish
│   ├── test_pattern_semantic_contract.py ← 17 tests (semantic contract + min_games)
│   └── test_dbcl.py             ← 17 tests (win_prob, BFS round-trip, narrative validator, N)
├── docs/
│   ├── CONTEXT_A_ZAMER.md       ← Full project context (CZ)
│   ├── CONTEXT_INJECT.md        ← Session timeline (v3.2), CPM lifecycle, anomaly log
│   ├── MERGE_EVAL_feat_to_main.md ← Merge evaluation + empirical run comparison
│   ├── PHASE2_BUILD_PLAN.md     ← Build plan + MCP post-mortem rules
│   ├── 01_DBCL_unity_synthesis.md ← DBCL architecture
│   ├── 02_DBCL_meta_evaluation.md ← 3-channel noise framework
│   ├── MIKOLOV_KOMPRESE_V_PATTERN_ARCHITEKTURE.md ← Lossy Compression Principle formalization
│   └── coaching_reports/        ← Generated training reports
├── data/
│   ├── game_cache/              ← Analysis cache (JSON, Stockfish + LLM)
│   ├── pgn_cache/               ← PGN import cache
│   ├── resource_store/          ← L2 Resource persistence
│   └── runs/                    ← RUN_003–RUN_005 reports
├── 00_STRATEGIE/                ← Coaching reports, DALSÍ_KROKY, DBCL audit
├── .session/                    ← Session context
├── lichess-mcp.bat              ← Cross-shell launcher (Windows)
├── .env                         ← LICHESS_TOKEN (never commit)
├── README.md                    ← This file (CZ)
├── README_en.md                 ← English version
├── pyproject.toml               ← Project config, dependencies
└── LICENSE                      ← MIT
```


## Stack

| Layer | Technology |
|-------|------------|
| Runtime | Python 3.12+, uv |
| Framework | FastMCP (mcp>=1.0.0) |
| Lichess API | berserk>=0.14.0 |
| Chess engine | chess>=1.11.0 (python-chess) + Stockfish 18 BMI2 |
| Spaced repetition | SM-2 (FSRS ready for upgrade) |
| HTTP / LLM API | httpx>=0.28.0 |
| LLM providers | NVIDIA (nemotron-3), Cerebras (gpt-oss), DeepSeek (deepseek-v4-flash) |
| Documents | python-docx>=1.2.0 |
| Persistence | B2B-Knowledge-Base (JSON + Markdown) |
| Testing | pytest 8+, pytest-cov, mypy |
| Lint | ruff (F, E, W, I, N, UP, S) |


## Project status (2026-07-28)

| What | Status |
|------|--------|
| Tests | **68/68 pass** |
| Patterns defined | **14** (A, B, C, G, I, I2, J, N, O, P, Q, Q1, Q2, R) + **S** active |
| Patterns with detector | **13** active + I manual_only (code→I2) |
| Analyzed games | **63** (44W/17L/2D, depth 12, RUN_003) + 25 anonymous |
| Cache consistency | ✅ Auto-consistent pipeline |
| Engine | Stockfish BMI2 dev-20260609, depth 12, ACPL MAE 3.9 vs Lichess |
| Engine lines | ✅ **0% silent fail** (70/70 BFS with 3/3 engine_lines) |
| BlunderFactSheet | ✅ Per-blunder: FEN, legal moves, engine_lines, context_window, pattern_matches |
| Narrative validator | ✅ 5 claim categories (reject loop pending) |
| Phase 1 | ✅ Complete |
| DBCL Phase 2 | ✅ **Complete** (engine_lines fix, BFS, N, narrative validator) |
| Pipeline bugfixes | ✅ **6 fixes**: 50-fetch-clamp, pagination, index auto-update, cache, pending detection |
| LLM pipeline | ✅ NVIDIA, Cerebras, DeepSeek V4 Flash |
| DeepSeek Chat | ❌ **BANNED** |
| 25 anonymous games | ACPL=31.7, 21-4-0 winrate, 8 patterns detected |

### CPM Lifecycle — Pattern Status

| Pattern | Audit (Phase 3) | Status |
|---------|-----------------|--------|
| A, G, J, N, Q1, Q2, R | ✅ PASS | Production |
| B | ⚠️ AUD-01 | Pending fix |
| C | ⚠️ AUD-02 | Pending fix |
| I | ✅ FIXED (concept, manual_only) | Code→I2 |
| O | ✅ **RESOLVED** (rename → Stagnační panika) | Production |
| P | ⚠️ AUD-06 | Pending |
| Q | ❌ AUD-05 | Merge Q+Q2 pending |
| S | ⏳ Pending production | AUD-10 pending |


## KB references

### Strategy and plans
- `00_STRATEGIE/02_chess/chess_mcp_strategy_v1.md` — strategic plan
- `00_STRATEGIE/DALSI_KROKY_po_RUN_003.md` — 15-commit follow-up checklist
- `docs/PHASE2_BUILD_PLAN.md` — build plan v3.0

### Pattern library and analysis
- `B2B-KB/04_KNOWLEDGE_BASE/02_chess/player_pattern_library_v1.json` — source library of 17 patterns
- `B2B-KB/02_ANALYZY/02_chess/chess_self_analysis_baseline_2026-04.md` — baseline analysis
- `data/runs/RUN_005_DBCL_v3_2026-07-27.md` — RUN_005 report (ACPL=46.1)

### Lossy Compression Principle
- `docs/MIKOLOV_KOMPRESE_V_PATTERN_ARCHITEKTURE.md` — LCP formalization
- `B2B-KB/05_EPISTEMIKA/00_kompresni_realismus/Kompresni_modelovani_v_praxi_synteza_v1.md` — synthesis
- `B2B-KB/05_EPISTEMIKA/00_kompresni_realismus/brain_geometric_processor_summary_v2.1.md` — theoretical basis

### Merge evaluation
- `docs/MERGE_EVAL_feat_to_main.md` — empirical feat vs main comparison (3 games, identical metrics)

### DBCL audit
- `00_STRATEGIE/DBCL_cross_audit_artifact.md` — Claude audit, 21 findings
- `docs/AUDIT_REPORT_lichess-analyzer-mcp_v2.md` — internal audit

### Session context
- `docs/CONTEXT_INJECT.md` v3.2 — session timeline, anomaly log, next steps
- `docs/CONTEXT_A_ZAMER.md` v1.0 — complete project context and design


## Inspiration & Credits

This project is not a fork — it has its own architecture, but valuable inspiration and infrastructure components come from the following open-source projects.

### Primary sources (libraries)

| Project | Author | Usage |
|---------|--------|-------|
| [berserk](https://github.com/lichess-org/berserk) | lichess-org / Matt Harrison | Lichess API Python client |
| [python-chess](https://github.com/niklasf/python-chess) | Niklas Fiekas | PGN/FEN parsing, UCI wrapper |
| [Stockfish](https://github.com/official-stockfish/Stockfish) | The Stockfish team | Local chess engine |
| [fastmcp](https://github.com/jlowin/fastmcp) | Jeremiah Lowin | FastMCP framework |
| [py-fsrs](https://github.com/open-spaced-repetition/py-fsrs) | Open Spaced Repetition | FSRS algorithm |

### Sibling MCP servers in portfolio

| Server | Tools | Key pattern |
|--------|-------|-------------|
| [cnc-tools](https://github.com/outpost2026/mcp-local-server) | 20 | Session state, caching, audit log |
| [linkedin-analyzer](https://github.com/outpost2026/linkedin-mcp-custom) | 8 | FastMCP, KB write-back, EROI scoring |
| [mcp-jobs](https://github.com/outpost2026/MCP-Jobs) | 5 | Boolean AST matching, multi-portal scraping |

### Engine integration debugging

Two critical bugs were identified and fixed in `engine_client.py`:
- **Perspective inversion** — cp_loss calculated from the opponent's side
- **Missing best-move comparison** — cp_loss calculated as before/after delta instead of best/actual

After fix: ACPL MAE of 3.9 vs Lichess reference (depth 18-22). See `docs/MERGE_EVAL_feat_to_main.md`.

Later fixed **engine_lines silent fail**: 30% → 0% failure rate (sequential board.copy + try/except). See `docs/CONTEXT_INJECT.md` §5.


## License

MIT &copy; 2026 Ondrej Sousek (outpost2026)
