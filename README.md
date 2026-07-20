[![](https://flagcdn.com/24x18/gb.png "EN")](https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/README_en.md)[ English ](https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/README_en.md)

# Lichess MCP Analyzer

**MCP server pro analyzu sachovych partii, detekci vzorovych chyb (pattern library jako kompresni model dle Mikolova) a spaced repetition trening.**


## Proc?

Tento repozitar vznika se **dvojim ucelem**:

1. **Sachovy analyzator** — personalizovany treninkovy nastroj, ktery stahne tvoje partie z Lichess, analyzuje kazdy tah Stockfishem, detekuje 17 vzorovych patternu (A-Q1) z tve vlastni herni historie, diagnostikuje fazove slabiny a pomaha se z nich ucit pomoci spaced repetition.

2. **MCP stavebnice** — demonstracni projekt, na kterem si overuji principy tvorby MCP serveru v praxi. Kazda komponenta (Lichess API, Stockfish engine, pattern detection engine, SRS, B2B-Knowledge-Base persistence) je samostatne pouzitelna a prenositelna do jine domeny.

> "Build tools for yourself first. If they solve a real problem, they solve a general one."


## Jak to funguje?

```
Tvoje otazka (v opencode)  
       |  
       v JSON-RPC 2.0 (stdio)  
       |  
lichess-analyzer-mcp (Python FastMCP)  
       |  
       +---\> Lichess API (berserk) -----\> lichess.org  
       +---\> Stockfish 18 (UCI) --------\> lokalni binary  
       +---\> Pattern detector ----------\> kompresni model (Mikolov)  
       +---\> FSRS/SM-2 engine ---------\> spaced repetition  
       +---\> KB writer ----------------\> B2B-Knowledge-Base
```

> **Pattern detection = kompresni model.** Transformuje ~5000 tahu surovych her na ~50 tokenu strukturovaneho profilu (99% komprese). Kazdy pattern ma `compression_ratio` = raw_cost / pattern_cost; pomer > 1.5 = signal, > 10 = silny signal. Confidence se pocita jako `0.5 × compression + 0.3 × entropy + 0.2 × sample` (Mikolov, 2026). Resi small-N authority problem: pattern je validni i pri N < 25, pokud dobre komprimuje.


## Nastroje (8 MCP toolu)

| Tool | Co dela |
| - | - |
| `lichess\_fetch\_games` | Stahne recent partie hrace z Lichess |
| `lichess\_analyze\_game` | Analyzuje jednu partii Stockfishem (kazdy tah, centipawn loss) |
| `lichess\_analyze\_position` | Analyzuje FEN pozici (depth 8-24, multipv 3) |
| `lichess\_opening\_explorer` | Prozkuma zahajeni v Lichess databazi |
| `lichess\_player\_profile` | Vrati profil, ratingy a statistiky hrace |
| `lichess\_diagnose\_player` | Diagnostikuje slabiny pres vice partii (faze, otvoreni, ACPL) |
| `lichess\_match\_patterns` | Detekuje vzorove chyby A-Q1 z tve pattern library |
| `lichess\_workspace\_info` | Vrati kontext pracovniho prostoru (P17) |


L2 Resources:

- `lichess://analysis/\{key\}` — ulozene vysledky analyzy

- `lichess://patterns/\{key\}` — ulozene vysledky detekce patternu

- `lichess://analysis/list` — seznam vsech analyz

- `lichess://patterns/list` — seznam vsech pattern detekci


## Rychly start

### 1. Stahnout repo

```
git clone https://github.com/outpost2026/lichess-mcp-analyzer.git  
cd lichess-mcp-analyzer
```

### 2. Stahnout Stockfish

```
powershell -File scripts\\setup\_stockfish.ps1
```

Nebo stahni rucne z [official-stockfish/Stockfish](https://github.com/official-stockfish/Stockfish/releases) a vloz `stockfish.exe` do `stockfish/` adresare.

### 3. Nastavit LICHESS\_TOKEN

Vytvor `.env` soubor v repo root:

```
LICHESS\_TOKEN=lip\_xxx
```

Token vytvoris na [lichess.org/settings/oauth](https://lichess.org/settings/oauth).

### 4. Spustit MCP server

```
uv sync  
uv run python -m src.server
```

Server se pripoji pres stdio. Pro opencode ho registruj v `opencode.jsonc`:

```
"lichess-analyzer": \{  
    "type": "local",  
    "command": \["cesta\\\\k\\\\repo\\\\.venv\\\\Scripts\\\\python.exe", "-X", "utf8", "-m", "src.server"\],  
    "enabled": true,  
    "timeout": 60000  
\}
```

### 5. Nebo pouzit CLI pipeline

```
\# Analyzuj vlastni profil (poslednich 20 partii)  
uv run python scripts\\run\_pipeline.py outpost2026 --games 20 --depth 12  
  
\# Analyzuj + zapis do KB (bez --no-kb)  
uv run python scripts\\run\_pipeline.py outpost2026 --games 10
```


## Ukazka pouziti

### "Co je za hrace?"

```
\> lichess\_player\_profile("outpost2026")  
  
\{  
  "username": "outpost2026",  
  "ratings": \{  
    "blitz": \{"rating": 1950, "games": 342\},  
    "rapid": \{"rating": 1880, "games": 156\}  
  \},  
  "total\_games": 523  
\}
```

### "Analyza posledni partie"

```
\> lichess\_analyze\_game("abc12345")  
  
\{  
  "game": \{"opening": "Sicilian Defense", "result": "1-0"\},  
  "stats": \{"total\_acpl": 45.2, "blunders": 1, "total\_moves": 42\},  
  "blunders": \["Move 28: Nxe5 (loss 450cp)"\]  
\}
```

### "Diagnoza slabin"

```
\> lichess\_diagnose\_player("outpost2026", max\_games=15)  
  
\{  
  "total\_acpl": 62.3,  
  "phase\_weaknesses": \{  
    "middlegame": \{"acpl": 78.1, "blunders": 4\},  
    "endgame": \{"acpl": 45.0, "blunders": 1\}  
  \},  
  "top\_weaknesses": \[  
    "Tactical awareness in middlegame transitions",  
    "Opening preparation: Sicilian Defense"  
  \]  
\}
```

### "Najdi vzorove chyby"

```
\> lichess\_match\_patterns("outpost2026")  
  
\{  
  "patterns\_detected": \[  
    \{  
      "pattern\_id": "B",  
      "pattern\_name": "Automatic grab",  
      "confidence": 85,  
      "severity": "high",  
      "mitigation": "3-sec pause + 'A CO ON?' before every capture"  
    \}  
  \]  
\}
```


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
│   ├── run\_pipeline.py      ← CLI batch pipeline  
│   └── setup\_stockfish.ps1  ← Automaticke stazeni Stockfish  
├── tests/  
│   └── test\_services.py     ← 15 unit testu (Phase 1: K4.1-K8.1)  
├── docs/  
│   ├── CONTEXT\_A\_ZAMER.md   ← Kompletni kontext a zamer projektu  
│   └── PHASE2\_BUILD\_PLAN.md ← Build plan + MCP pitva pravidla  
├── lichess-mcp.bat          ← Cross-shell launcher (Windows)  
├── .env                     ← LICHESS\_TOKEN (necommitovat)  
├── README.md                ← Tento soubor  
└── LICENSE                  ← MIT
```


## Stack

| Vrstva | Technologie |
| - | - |
| Runtime | Python 3.12+, uv |
| Framework | FastMCP (mcp\>=1.0.0) |
| Lichess API | berserk\>=0.14.0 |
| Sahovy engine | chess\>=1.11.0 (python-chess) + Stockfish 18 |
| Spaced repetition | fsrs\>=4.0.0 (py-fsrs) |
| HTTP | httpx\>=0.28.0 |
| Persistence | B2B-Knowledge-Base (JSON + Markdown) |



## Inspirace a zdroje

Tento projekt neni fork — je vlastni architekturou, ale cenna inspirace a infrastrukturni komponenty pochazeji z nasledujicich open-source projektu. Dekujeme autorum.

### Primarni zdroje (knihovny)

| Projekt | Autor | Pouziti |
| - | - | - |
| [berserk](https://github.com/lichess-org/berserk) | lichess-org / Matt Harrison | Lichess API Python client — auth, rate limiting, streaming |
| [python-chess](https://github.com/niklasf/python-chess) | Niklas Fiekas (niklasf) | PGN/FEN parsing, UCI engine wrapper, game tree, move validation |
| [Stockfish](https://github.com/official-stockfish/Stockfish) | The Stockfish team | Lokalni sachovy engine (UCI protokol), evaluace kazdeho tahu |
| [fastmcp](https://github.com/jlowin/fastmcp) | Jeremiah Lowin | FastMCP framework — usnadnuje tvorbu MCP serveru |
| [py-fsrs](https://github.com/open-spaced-repetition/py-fsrs) | Open Spaced Repetition | FSRS algoritmus pro spaced repetition |


### Sekundarni inspirace (MCP servery pro sachy)

Pri navrhu architektury jsme zkoumali 10+ existujicich chess MCP serveru na GitHubu. Ponauceni z TOP 4:

| Repozitar | Hvezdy | Co nas inspirovalo |
| - | - | - |
| [chess-coach-mcp](https://github.com/) | ~50 | Analyza partii + treninkovy feedback |
| [chessagine-mcp](https://github.com/) | ~30 | Multi-engine analyza, viceserverova architektura |
| [chess-rocket](https://github.com/) | ~80 | Spaced repetition na sachove chyby (SM-2) |
| [chess-com-lichess-org-mcp](https://github.com/) | ~120 | Siroky Lichess API wrapper (54 toolu) — inspirace pro tool design |


**Co nasi architekturu odlisuje:** kombinace pattern detection library jako **kompresniho modelu hrace** (Mikolov: patterns komprimuji 5000 tahu na ~50 tokenu, confidence pres compression_ratio), FSRS spaced repetition na osobni chyby, cross-game diagnostiky a KB persistence v jednom MCP serveru.

### Stavba a debug engine integrace

Behem vyvoje byly identifikovany a opraveny dve kriticke chyby v `engine\_client.py`:

- **Perspektivni inverze** — cp\_loss pocitan z opacne strany (board.push() meni side-to-move)

- **Best-move porovnani** — cp\_loss pocitan jako delta before/after, nikoliv best/actual

Po oprave probehla **diferencialni analyza** proti Lichess GUI (Stockfish dev-20260609-415ff793, depth 18-22). Vysledek: ACPL MAE 3.9 oproti lichess referenci — engine je po fixu funkcne ekvivalentni.

Dalsi zdroje pouzite pri debugu:

- [stockfish-web](https://github.com/lichess-org/stockfish-web) — Lichess patch pro Stockfish WASM (sf\_dev build)

- [lila](https://github.com/lichess-org/lila) — Lichess platform (klasifikacni thresholds: 50/150/300 centipawn)

### Sourozenecke MCP servery v portfoliu

Architektonicke vzory (tools-of-tools, KB write-back, L2 Resources, session state) byly overeny na:

| Server | Toolu | Klicovy pattern |
| - | - | - |
| [cnc-tools](https://github.com/outpost2026/mcp-local-server) | 20 | Session state, caching, audit log |
| [linkedin-analyzer](https://github.com/outpost2026/linkedin-mcp-custom) | 8 | FastMCP framework, KB write-back, EROI scoring |
| [mcp-jobs](https://github.com/outpost2026/MCP-Jobs) | 5 | Boolean AST match, multi-portal scraping, L2+ Resources |



## Souvislosti

- **Pattern library:** 9 definovanych (A-R), 7 s detektory — analyza 13 partii, Phase 1 hotova (commit a536845)

- **Pozadi:** `docs/CONTEXT\_A\_ZAMER.md` — kompletni kontext, reserse a architektura

- **MCP pravidla:** Aplikovano P1-P28 z agregovane pitevni knihy (timeout guard, structured logging, L2 Resources, encoding triad)

- **KB modul:** B2B-Knowledge-Base/02\_ANALYZY/02\_chess/ + 04\_KNOWLEDGE\_BASE/02\_chess/


## Stav (2026-07-20)

| Co | Stav |
| - | - |
| Tests | 15/15 pass |
| Patterny definovane | 9 (A, B, C, G, I, O, P, Q, R) |
| Patterny s detektorem | 7 (A, B, G, O, P, Q, R) |
| Cached games | 13 (12W/1L, depth 12) |
| Phase 1 | Hotova (K4.1-K8.1: hypothesis, min_games, compressibility, validator, schema) |
| Kalibrace detectoru | Hotova (sezeni 2026-07-20: P B/G/Q bi-directional, P fix, R novy) |
| Pipeline (13 games) | Pred kalibraci: 0 pattern matchu (prilis prisme prahy). Ceka na overeni. |

Kalibracni plan: `docs/KALIBRACE_PLAN_2026-07-19.md` (v2.3, ~600 lines).
Session state: `.ai_state.json`

## License

MIT  2026 Ondrej Sousek (outpost2026)

