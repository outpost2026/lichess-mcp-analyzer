<div align="left">
  <a href="https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/README_en.md">
    <img src="https://flagcdn.com/24x18/gb.png" alt="EN" height="18"> English
  </a>
</div>

# Lichess MCP Analyzer

**MCP server pro analyzu sachovych partii, detekci vzorovych chyb (pattern library) a spaced repetition trening.**

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

## Inspirace a zdroje

Tento projekt neni fork — je vlastni architekturou, ale cenna inspirace a infrastrukturni komponenty pochazeji z nasledujicich open-source projektu. Dekujeme autorum.

### Primarni zdroje (knihovny)

| Projekt | Autor | Pouziti |
|---------|-------|---------|
| [berserk](https://github.com/lichess-org/berserk) | lichess-org / Matt Harrison | Lichess API Python client — auth, rate limiting, streaming |
| [python-chess](https://github.com/niklasf/python-chess) | Niklas Fiekas (niklasf) | PGN/FEN parsing, UCI engine wrapper, game tree, move validation |
| [Stockfish](https://github.com/official-stockfish/Stockfish) | The Stockfish team | Lokalni sachovy engine (UCI protokol), evaluace kazdeho tahu |
| [fastmcp](https://github.com/jlowin/fastmcp) | Jeremiah Lowin | FastMCP framework — usnadnuje tvorbu MCP serveru |
| [py-fsrs](https://github.com/open-spaced-repetition/py-fsrs) | Open Spaced Repetition | FSRS algoritmus pro spaced repetition |

### Sekundarni inspirace (MCP servery pro sachy)

Pri navrhu architektury jsme zkoumali 10+ existujicich chess MCP serveru na GitHubu.
Ponaueni z TOP 4:

| Repozitar | Hvezdy | Co nas inspirovalo |
|-----------|--------|--------------------|
| [chess-coach-mcp](https://github.com/) | ~50 | Analyza partii + treninkovy feedback |
| [chessagine-mcp](https://github.com/) | ~30 | Multi-engine analyza, viceserverova architektura |
| [chess-rocket](https://github.com/) | ~80 | Spaced repetition na sachove chyby (SM-2) |
| [chess-com-lichess-org-mcp](https://github.com/) | ~120 | Siroky Lichess API wrapper (54 toolu) — inspirace pro tool design |

**Co nasi architekturu odlisuje:** kombinace pattern detection library (17 A-Q1 patternu), FSRS spaced repetition na osobni chyby, cross-game diagnostiky a KB persistence v jednom MCP serveru.

### Stavba a debug engine integrace

Behem vyvoje byly identifikovany a opraveny dve kriticke chyby v `engine_client.py`:
- **Perspektivni inverze** — cp_loss pocitan z opacne strany (board.push() meni side-to-move)
- **Best-move porovnani** — cp_loss pocitan jako delta before/after, nikoliv best/actual

Po oprave probehla **diferencialni analyza** proti Lichess GUI (Stockfish dev-20260609-415ff793, depth 18-22). Vysledek: ACPL MAE 3.9 oproti lichess referenci — engine je po fixu funkcne ekvivalentni.

Dalsi zdroje pouzite pri debugu:
- [stockfish-web](https://github.com/lichess-org/stockfish-web) — Lichess patch pro Stockfish WASM (sf_dev build)
- [lila](https://github.com/lichess-org/lila) — Lichess platform (klasifikacni thresholds: 50/150/300 centipawn)

### Sourozenecke MCP servery v portfoliu

Architektonicke vzory (tools-of-tools, KB write-back, L2 Resources, session state) byly overeny na:

| Server | Toolu | Klicovy pattern |
|--------|-------|-----------------|
| [cnc-tools](https://github.com/outpost2026/mcp-local-server) | 20 | Session state, caching, audit log |
| [linkedin-analyzer](https://github.com/outpost2026/linkedin-mcp-custom) | 8 | FastMCP framework, KB write-back, EROI scoring |
| [mcp-jobs](https://github.com/outpost2026/MCP-Jobs) | 5 | Boolean AST match, multi-portal scraping, L2+ Resources |

---

## Souvislosti

- **Pattern library:** 17 vzorovych patternu (A-Q1) — analyza 21 partii, metacognition gap ~300 ELO
- **Pozadi:** `docs/CONTEXT_A_ZAMER.md` — kompletni kontext, reserse a architektura
- **MCP pravidla:** Aplikovano P1-P28 z agregovane pitevni knihy (timeout guard, structured logging, L2 Resources, encoding triad)
- **KB modul:** B2B-Knowledge-Base/02_ANALYZY/02_chess/ + 04_KNOWLEDGE_BASE/02_chess/

---

## License

MIT &copy; 2026 Ondrej Sousek (outpost2026)
