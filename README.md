<div align="left">
  <a href="https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/README_en.md">
    <img src="https://flagcdn.com/24x18/gb.png" alt="EN" height="18"> English
  </a>
</div>

# lichess-mcp-analyzer

**MCP server pro analyzu sachovych partii, detekci vzorovych chyb (pattern library) a spaced repetition trening.**

|

---

## Proc?

Tento repozitar vznika se **dvojakym ucelem**:

1. **Sachovy analyzator** — personalizovany treninkovy nastroj, ktery stahne tvoje partie z Lichess, analyzuje kazdy tah Stockfishem, detekuje 17 vzorovych patternu (A-Q1) z tve vlastni herni historie, diagnostikuje fazove slabiny a pomaha se z nich ucit pomoci spaced repetition.

2. **MCP stavebnice** — demonstracni projekt, na kterem si overuji principy tvorby MCP serveru v praxi. Kazda komponenta (Lichess API, Stockfish engine, pattern detection engine, SRS, B2B-Knowledge-Base persistence) je samostatne pouzitelna a prenositelna do jine domeny.

> "Build tools for yourself first. If they solve a real problem, they solve a general one."

---

## Jak to funguje?

```
Tvoje otazka (v opencode)
       |
       v JSON-RPC 2.0 (stdio)
       |
lichess-analyzer-mcp (Python FastMCP)
       |
       +---> Lichess API (berserk) -----> lichess.org
       +---> Stockfish 18 (UCI) --------> lokalni binary
       +---> Pattern detector ----------> 17 patternu A-Q1
       +---> FSRS/SM-2 engine ---------> spaced repetition
       +---> KB writer ----------------> B2B-Knowledge-Base
```

---

## Nastroje (8 MCP toolu)

| Tool | Co dela |
|------|---------|
| `lichess_fetch_games` | Stahne recent partie hrace z Lichess |
| `lichess_analyze_game` | Analyzuje jednu partii Stockfishem (kazdy tah, centipawn loss) |
| `lichess_analyze_position` | Analyzuje FEN pozici (depth 8-24, multipv 3) |
| `lichess_opening_explorer` | Prozkuma otvoreni v Lichess databazi |
| `lichess_player_profile` | Vrati profil, ratingy a statistiky hrace |
| `lichess_diagnose_player` | Diagnostikuje slabiny pres vice partii (faze, otvoreni, ACPL) |
| `lichess_match_patterns` | Detekuje vzorove chyby A-Q1 z tve pattern library |
| `lichess_workspace_info` | Vrati kontext pracovniho prostoru (P17) |

L2 Resources:
- `lichess://analysis/{key}` — ulozene vysledky analyzy
- `lichess://patterns/{key}` — ulozene vysledky detekce patternu
- `lichess://analysis/list` — seznam vsech analyz
- `lichess://patterns/list` — seznam vsech pattern detekci

---

## Rychly start

### 1. Stahnout repo

```bash
git clone https://github.com/outpost2026/lichess-mcp-analyzer.git
cd lichess-mcp-analyzer
```

### 2. Stahnout Stockfish

```powershell
powershell -File scripts\setup_stockfish.ps1
```

Nebo stahni rucne z [official-stockfish/Stockfish](https://github.com/official-stockfish/Stockfish/releases) a vloz `stockfish.exe` do `stockfish/` adresare.

### 3. Nastavit LICHESS_TOKEN

Vytvor `.env` soubor v repo root:

```
LICHESS_TOKEN=lip_xxx
```

Token vytvoris na [lichess.org/settings/oauth](https://lichess.org/settings/oauth).

### 4. Spustit MCP server

```powershell
uv sync
uv run python -m src.server
```

Server se pripoji pres stdio. Pro opencode ho registruj v `opencode.jsonc`:

```json
"lichess-analyzer": {
    "type": "local",
    "command": ["cesta\\k\\repo\\.venv\\Scripts\\python.exe", "-X", "utf8", "-m", "src.server"],
    "enabled": true,
    "timeout": 60000
}
```

### 5. Nebo pouzit CLI pipeline

```powershell
# Analyzuj vlastni profil (poslednich 20 partii)
uv run python scripts\run_pipeline.py outpost2026 --games 20 --depth 12

# Analyzuj + zapis do KB (bez --no-kb)
uv run python scripts\run_pipeline.py outpost2026 --games 10
```

---

## Ukazka pouziti

### "Co je za hrace?"

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

### "Analyza posledni partie"

```
> lichess_analyze_game("abc12345")

{
  "game": {"opening": "Sicilian Defense", "result": "1-0"},
  "stats": {"total_acpl": 45.2, "blunders": 1, "total_moves": 42},
  "blunders": ["Move 28: Nxe5 (loss 450cp)"]
}
```

### "Diagnoza slabin"

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

### "Najdi vzorove chyby"

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

## Struktura repozitare

```
lichess-analyzer-mcp/
├── stockfish/               ← Stockfish 18 binary (necommitovano)
├── src/
│   ├── app.py               ← FastMCP instance
│   ├── server.py            ← Entry point + workspace context
│   ├── models/              ← Datove modely (dataclasses)
│   ├── services/            ← Sluzby (Lichess, Stockfish, SRS, diagnostika)
│   ├── tools/               ← 8 MCP toolu
│   ├── resources/           ← L2 Resources
│   └── kb/                  ← KB persistence (B2B-Knowledge-Base)
├── scripts/
│   ├── run_pipeline.py      ← CLI batch pipeline
│   └── setup_stockfish.ps1  ← Automaticke stazeni Stockfish
├── tests/
│   └── test_services.py     ← 8 unit testu
├── docs/
│   ├── CONTEXT_A_ZAMER.md   ← Kompletni kontext a zamer projektu
│   └── PHASE2_BUILD_PLAN.md ← Build plan + MCP pitva pravidla
├── lichess-mcp.bat          ← Cross-shell launcher (Windows)
├── .env                     ← LICHESS_TOKEN (necommitovat)
├── README.md                ← Tento soubor
└── LICENSE                  ← MIT
```

---

## Stack

| Vrstva | Technologie |
|--------|------------|
| Runtime | Python 3.12+, uv |
| Framework | FastMCP (mcp>=1.0.0) |
| Lichess API | berserk>=0.14.0 |
| Sahovy engine | chess>=1.11.0 (python-chess) + Stockfish 18 |
| Spaced repetition | fsrs>=4.0.0 (py-fsrs) |
| HTTP | httpx>=0.28.0 |
| Persistence | B2B-Knowledge-Base (JSON + Markdown) |

---

## Zdroje a souvislosti

- **Pattern library:** 17 vzorovych patternu (A-Q1) — analyza 21 partii, metacognition gap ~300 ELO
- **Pozadi:** `docs/CONTEXT_A_ZAMER.md`
- **MCP pravidla:** Aplikovano P1-P28 z agregovane pitevni knihy (timeout guard, structured logging, L2 Resources, encoding triad)
- **Dalsi MCP servery v portfoliu:** `cnc-tools` (20 toolu), `linkedin-analyzer` (8 toolu), `mcp-jobs` (5 toolu)

---

## License

MIT &copy; 2026 Ondrej Sousek (outpost2026)
