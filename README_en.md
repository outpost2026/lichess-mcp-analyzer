<div align="left">
  <a href="https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/README.md">
    <img src="https://flagcdn.com/24x18/cz.png" alt="CZ" height="18"> Cesky
  </a>
</div>

# Lichess MCP Analyzer

**MCP server for chess game analysis, pattern detection, and spaced repetition training.**


---

## Why?

This repository has a **dual purpose**:

1. **Chess analyzer** — a personalized training tool that fetches your Lichess games, analyzes every move with Stockfish, detects 17 behavioral patterns (A-Q1) from your own play history, diagnoses phase weaknesses, and helps you learn from mistakes using spaced repetition.

2. **MCP construction kit** — a demonstration project that validates MCP server design principles on real case studies. Every component (Lichess API, Stockfish engine, pattern detection engine, SRS, B2B-Knowledge-Base persistence) is independently usable and transferable to other domains.

 >"Build tools for yourself first. If they solve a real problem, they solve a general one."

---

## How it works

```
Your question (in opencode)
       |
       v JSON-RPC 2.0 (stdio)
       |
lichess-analyzer-mcp (Python FastMCP)  
       |  
       +--- Lichess API (berserk) -------- lichess.org  
       +--- Stockfish 18 (UCI) ----------- local binary  
       +--- Pattern detector ------------- compression model (Mikolov)  
       +--- LLM reasoning (cascade) ------ NVIDIA / Cerebras / DeepSeek V4  
       +--- FSRS/SM-2 engine ------------- spaced repetition  
       +--- KB writer -------------------- B2B-Knowledge-Base  
       +--- MD reporter ------------------ docs/ coaching reports
```

## Pattern detection as a compression model

> "A representation of reality that minimizes complexity, prediction error, and computational cost."

The chess pattern artifact is a **compression model of the player**: it minimizes complexity (9 patterns instead of 1000+ moves), prediction error (Stockfish cp_loss as ground truth), and computational cost (2s cached runtime).

### Validation

- MSE feedback: predict moves based on patterns vs. reality
- If **MSE(pattern) < MSE(average)**, the model is valid
- If **MSE(pattern) ≈ MSE(average)**, the pattern is noise

### Lossy compression

> "Removing information with low predictive value."

The pattern library discards individual moves (noise) and extracts behavioral patterns (signal). Lossy compression in chess = lose details (exact cp_loss value) to capture the pattern (the player prefers X).

**Rule:** A pattern is good if it:
- captures behavior (signal)
- removes individual errors (noise)
- preserves structure (trends, phase weaknesses)

### Occam's razor

> "Prefer the simplest sufficiently accurate model."

Compression ratio (`compression_ratio` = raw_cost / pattern_cost) is the measure of Occam's razor. Given two patterns that explain the data equally well, the one with the **higher compression ratio is more correct**.

Practical problem: Pattern H (Mathematical naivete) and Pattern I (Material before initiative) may overlap. Occam via compression asks:
- Which has the higher compression ratio?
- Which requires fewer exceptions for the same explanation?

### Confidence formula (Mikolov)

```
final_confidence = 0.5 × compression_score + 0.3 × entropy_score + 0.2 × sample_score
```

Solves the **small-N authority problem**: a pattern is valid even with N < 25 if it compresses well (compression_ratio > 1.5 = signal, > 10 = strong signal, < 1.0 = noise).

---

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

### Pipeline mode (monolithic vs incremental)

`run_coaching_pipeline(mode="auto")` selects architecture by golden rules:

| Mode | When | What it does |
|---|---|---|
| `auto` | default | N≤30 → monolithic, N>30 → incremental |
| `mono` | quick analysis | 1 LLM call, raw data in prompt |
| `incremental` | hundreds of games, PGN import | per-game LLM cache + aggregate with summaries |

Switched via `PIPELINE_MODE` env var or function parameter.
Per-game LLM cache: `data/game_cache/{game_id}_llm.json`.
Per-game analysis (incremental) validated by contract tests (`tests/test_prompt_contract.py`).

### API keys (optional)

Add to `.env` (all providers are free except DeepSeek):
```
NVIDIA_API_KEY=nvapi-...
CEREBRAS_API_KEY=csk-...
DEEPSEEK_API_KEY=sk-...       # shared for DS Chat and V4 Flash
LLM_MAX_TOKENS=4000            # default 2000, use 4000 for full reports
```

### Provider comparison (5 games, same data)

| Provider | Model | Tokens | Latency | Cost/5games | SNR |
|---|---|---|---|---|---|
| NVIDIA | nemotron-3-super-120b-a12b | 2,597 | 17s | $0.000 | 57% |
| Cerebras | gpt-oss-120b | 2,677 | - | $0.000 | 54% |
| DeepSeek V4 Flash | deepseek-v4-flash | 3,876 | 31s | $0.001 | **93%** |

SNR = semantic fidelity to input data (confidence %, phase ACPL, no hallucinated patterns).

### Quality analysis

| Criterion | NVIDIA | Cerebras | DeepSeek V4 |
|---|---|---|---|
| Pattern grounding | ✅ all 6 | ⚠️ invents 7th pattern | ✅ all 6 |
| Confidence % from data | ❌ missing | ⚠️ partial | ✅ all present |
| Phase ACPL citation | ❌ missing | ⚠️ approximate | ✅ exact |
| Hallucinations | ❌ none | ⚠️ moderate | ✅ minimal |
| Coaching tone | formal | medium | **natural** |

**Verdict:** DeepSeek V4 Flash = highest SNR (93%). The only provider that consistently cites confidence and phase data. NVIDIA = solid free fallback. Cerebras has the best formatting but invents patterns.

### Cost projection (100 games)

| Provider | Cost/100games | Notes |
|---|---|---|
| NVIDIA | $0.00 | Free tier, unlimited |
| Cerebras | $0.00 | Free tier, unlimited |
| DeepSeek V4 Flash | ~$0.07 | ~1,460 games per $1 |
| DeepSeek Chat | ~$0.24 | **BANNED** — 3.6× more expensive than V4 Flash |

---

## Tools (9 MCP tools)

| Tool | Description |
|------|-------------|
| `lichess_fetch_games` | Fetch recent games from Lichess |
| `lichess_analyze_game` | Analyze a single game with Stockfish (per-move, centipawn loss) |
| `lichess_analyze_position` | Analyze a FEN position (depth 8-24, multipv 3) |
| `lichess_opening_explorer` | Explore openings in the Lichess database |
| `lichess_player_profile` | Get profile, ratings, and stats |
| `lichess_diagnose_player` | Diagnose weaknesses across multiple games (phases, openings, ACPL) |
| `lichess_match_patterns` | Detect A-Q1 playing patterns from your pattern library |
| `lichess_workspace_info` | Get workspace context (P17) |
| `lichess_import_pgn` | Import a PGN file as a game |

L2 Resources:
- `lichess://analysis/{key}` — stored analysis results
- `lichess://patterns/{key}` — stored pattern detection results
- `lichess://analysis/list` — list all analyses
- `lichess://patterns/list` — list all pattern detections

---

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
uv run python -m src.server
```

The server connects over stdio. Register it in `opencode.jsonc`:

```json
"lichess-analyzer": {
    "type": "local",
    "command": ["path\\to\\repo\\.venv\\Scripts\\python.exe", "-X", "utf8", "-m", "src.server"],
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

---

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

---

## Repository structure

```
lichess-analyzer-mcp/
├── stockfish/               ← Stockfish 18 binary (not committed)
├── src/
│   ├── app.py               ← FastMCP instance
│   ├── server.py            ← Entry point + workspace context
│   ├── models/              ← Data models (dataclasses)
│   ├── services/
│   │   ├── llm_client.py    ← Multi-provider LLM cascade (NVIDIA/Cerebras/DeepSeek)
│   │   └── ...              ← Lichess, Stockfish, SRS, diagnostics
│   ├── tools/               ← 9 MCP tools
│   ├── resources/           ← L2 Resources
│   └── kb/
│       ├── md_reporter.py   ← MD report generation to docs/
│       └── ...              ← KB persistence (B2B-Knowledge-Base)
├── scripts/
│   ├── run_pipeline.py      ← CLI batch pipeline
│   └── setup_stockfish.ps1  ← Automatic Stockfish download
├── tests/
│   ├── test_services.py       ← 15 unit tests (models, compression, validation)
│   └── test_prompt_contract.py ← 13 contract tests (schema, mapping, noise-floor)
├── docs/
│   ├── CONTEXT_A_ZAMER.md   ← Full project context (CZ)
│   └── PHASE2_BUILD_PLAN.md ← Build plan + MCP post-mortem rules
├── lichess-mcp.bat          ← Cross-shell launcher (Windows)
├── .env                     ← LICHESS_TOKEN (never commit)
├── README.md                ← This file (CZ)
├── README_en.md             ← English version
└── LICENSE                  ← MIT
```

---

## Stack

| Layer | Technology |
|-------|------------|
| Runtime | Python 3.12+, uv |
| Framework | FastMCP (mcp>=1.0.0) |
| Lichess API | berserk>=0.14.0 |
| Chess engine | chess>=1.11.0 (python-chess) + Stockfish 18 |
| Spaced repetition | fsrs>=4.0.0 (py-fsrs) |
| HTTP / LLM API | httpx>=0.28.0 |
| LLM providers | NVIDIA (nemotron-3-super-120b), Cerebras (gpt-oss-120b), DeepSeek (deepseek-v4-flash) |
| LLM cascade | first success wins, switchable via `DEFAULT_PROVIDER` env var |
| Persistence | B2B-Knowledge-Base (JSON + Markdown) |

---

## Inspiration & Credits

This project is not a fork — it has its own architecture, but valuable inspiration and infrastructure components come from the following open-source projects. Credit to the authors.

### Primary sources (libraries)

| Project | Author | Usage |
|---------|--------|-------|
| [berserk](https://github.com/lichess-org/berserk) | lichess-org / Matt Harrison | Lichess API Python client — auth, rate limiting, streaming |
| [python-chess](https://github.com/niklasf/python-chess) | Niklas Fiekas (niklasf) | PGN/FEN parsing, UCI engine wrapper, game tree, move validation |
| [Stockfish](https://github.com/official-stockfish/Stockfish) | The Stockfish team | Local chess engine (UCI protocol), per-move evaluation |
| [fastmcp](https://github.com/jlowin/fastmcp) | Jeremiah Lowin | FastMCP framework simplifies MCP server creation |
| [py-fsrs](https://github.com/open-spaced-repetition/py-fsrs) | Open Spaced Repetition | FSRS algorithm for spaced repetition |

### Secondary inspiration (chess MCP servers)

During architecture design, 10+ existing chess MCP servers on GitHub were reviewed.
Lessons from TOP 4:

| Repository | Stars | What inspired us |
|-----------|-------|------------------|
| [chess-coach-mcp](https://github.com/) | ~50 | Game analysis + training feedback |
| [chessagine-mcp](https://github.com/) | ~30 | Multi-engine analysis, multi-server architecture |
| [chess-rocket](https://github.com/) | ~80 | Spaced repetition on chess mistakes (SM-2) |
| [chess-com-lichess-org-mcp](https://github.com/) | ~120 | Broad Lichess API wrapper (54 tools) — tool design inspiration |

**What sets our architecture apart:** combination of pattern detection library as a **compression model of the player** (see "Pattern detection as a compression model" — MSE validation, lossy compression, Occam's razor, confidence via compression_ratio), FSRS spaced repetition on personal mistakes, cross-game diagnostics, and KB persistence in a single MCP server.

### Engine integration debugging

Two critical bugs were identified and fixed in `engine_client.py`:
- **Perspective inversion** — cp_loss calculated from opponent's side (board.push() switches side-to-move)
- **Missing best-move comparison** — cp_loss calculated as before/after delta instead of best/actual move

After the fix, a **differential analysis** was performed against Lichess GUI (Stockfish dev-20260609-415ff793, depth 18-22). Result: ACPL MAE of 3.9 versus the Lichess reference — the fixed engine is functionally equivalent.

Additional sources used during debugging:
- [stockfish-web](https://github.com/lichess-org/stockfish-web) — Lichess patch for Stockfish WASM (sf_dev build)
- [lila](https://github.com/lichess-org/lila) — Lichess platform (classification thresholds: 50/150/300 centipawn)

### Sibling MCP servers in portfolio

Architectural patterns (tools-of-tools, KB write-back, L2 Resources, session state) were validated on:

| Server | Tools | Key pattern |
|--------|-------|-------------|
| [cnc-tools](https://github.com/outpost2026/mcp-local-server) | 20 | Session state, caching, audit log |
| [linkedin-analyzer](https://github.com/outpost2026/linkedin-mcp-custom) | 8 | FastMCP framework, KB write-back, EROI scoring |
| [mcp-jobs](https://github.com/outpost2026/MCP-Jobs) | 5 | Boolean AST matching, multi-portal scraping, L2+ Resources |

---

## References

- **Pattern library:** 9 patterns (A-R) — analysis of 21 games
- **Tests:** 28/28 pass (15 unit + 13 contract)
- **LLM pipeline:** ✅ NVIDIA, Cerebras, DeepSeek V4 Flash operational
- **LLM reporting:** ✅ MD reports to `docs/` (summary, signal priority, training, strengths)
- **Provider switch:** ✅ `DEFAULT_PROVIDER` env var (nvidia/cerebras/deepseek)
- **Pipeline mode:** ✅ `PIPELINE_MODE` env var (mono/incremental/auto)
- **Contract tests:** ✅ 13 tests — Stockfish→LLM mapping, schema, noise-floor
- **Low SNR fix:** ✅ GT-059 — accuracy, phase_stats, key mapping fixed
- **DeepSeek Chat:** ❌ **BANNED** — too expensive ($0.27/$1.10 per 1M tokens)
- **Background:** `docs/CONTEXT_A_ZAMER.md` (CZ)
- **MCP rules:** P1-P44 from the aggregated post-mortem (timeout guard, structured logging, L2 Resources, encoding triad, contract testing)
- **KB module:** B2B-Knowledge-Base/02_ANALYZY/02_chess/ + 04_KNOWLEDGE_BASE/02_chess/

---

## License

MIT &copy; 2026 Ondrej Sousek (outpost2026)
