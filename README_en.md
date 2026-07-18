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
       +---> Lichess API (berserk) -----> lichess.org
       +---> Stockfish 18 (UCI) --------> local binary
       +---> Pattern detector ----------> 17 patterns A-Q1
       +---> FSRS/SM-2 engine ---------> spaced repetition
       +---> KB writer ----------------> B2B-Knowledge-Base
```

---

## Tools (8 MCP tools)

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
│   ├── services/            ← Services (Lichess, Stockfish, SRS, diagnostics)
│   ├── tools/               ← 8 MCP tools
│   ├── resources/           ← L2 Resources
│   └── kb/                  ← KB persistence (B2B-Knowledge-Base)
├── scripts/
│   ├── run_pipeline.py      ← CLI batch pipeline
│   └── setup_stockfish.ps1  ← Automatic Stockfish download
├── tests/
│   └── test_services.py     ← 8 unit tests
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
| HTTP | httpx>=0.28.0 |
| Persistence | B2B-Knowledge-Base (JSON + Markdown) |

---

## References

- **Pattern library:** 17 patterns (A-Q1) — analysis of 21 games, metacognition gap ~300 ELO
- **Background:** `docs/CONTEXT_A_ZAMER.md` (CZ)
- **MCP rules:** P1-P28 from the aggregated post-mortem (timeout guard, structured logging, L2 Resources, encoding triad)
- **Sibling MCP servers:** `cnc-tools` (20 tools), `linkedin-analyzer` (8 tools), `mcp-jobs` (5 tools)

---

## License

MIT &copy; 2026 Ondrej Sousek (outpost2026)
