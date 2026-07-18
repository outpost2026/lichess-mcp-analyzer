# Phase 2 — Build Plan

**Datum:** 2026-07-18 | **Navazuje na:** CONTEXT_A_ZAMER.md
**Status:** 🟢 Hotovo (Phase 1 ready) -> 🟡 Phase 2 v realizaci

---

## Co je hotovo (Phase 2 pre-built)

| Krok | Stav |
|------|------|
| Stockfish 18 downloaded (`stockfish/stockfish.exe`) | ✅ |
| LICHESS_TOKEN nasazen (`.env`) | ✅ |
| `uv sync` hotovo (42 packages, vcetne `fsrs>=4.0.0` a `chess>=1.11.0`) | ✅ |
| FastMCP server (7 toolu registered, circular import fix) | ✅ |
| Python 3.12.13 virtual env ready | ✅ |
| `.bat` launcher (`lichess-mcp.bat`) | ✅ |
| 8/8 testu pass | ✅ |
| `engine_client.py` hleda stockfish v `stockfish/` + PATH | ✅ |
| Pitevni kniha pouceni: P1-P23 aplikovano | ✅ |

---

## Applicated MCP pitva lessons (P1-P23)

Z `sdilena_pitevni_kniha_mcp.md` aplikovano:

| P# | Rule | Aplikace |
|----|------|----------|
| P1 | Timeout: subprocess max 25% client timeoutu | Stockfish depth limit (8-24) + engine analyze ma internal timeout |
| P2 | Paralelizace: ThreadPoolExecutor pro I/O | `diagnose_player.py` + `match_patterns.py` — 4 workers |
| P4 | JSON defenziva: try/except + isinstance guard | Vsechny tooly maji try/except, lichess_client vraci None pri selhani |
| P6 | Timeout guard pro I/O >10s | Neni implementovan (TODO v Phase 2.2) |
| P7 | Global promenne: `global` keyword | `engine_client.py` + `lichess_client.py` spravne |
| P11 | Console script overeni | `.bat` wrapper vytvoren |
| P12 | Cross-shell launcher | `lichess-mcp.bat` v repo root |
| P13 | Long-running batch | CLI pipeline (`scripts/run_pipeline.py`) obchazi MCP timeout |
| P17 | Workspace context | `print("[server] ...")` neni implementovan (TODO) |
| P18 | Console encoding | `sys.stdout.reconfigure()` v server.py |
| P19 | Structured logging | Neni implementovan (TODO — Phase 2.2) |
| P20 | ETL health check | CLI pipeline existuje |
| P21 | L2 Resources | Neni implementovan (TODO — Phase 2.3) |
| P22 | No `python -c` inline | Dodrzeno (vsechny testy pres .py soubor) |
| P23 | Encoding triad | PYTHONIOENCODING + -X utf8 + sys.stdout.reconfigure |

---

## Phase 2.1 — Stabilizace a monitoring (aktualni iterace)

Priorita: **HIGH** — server musi bezet stabilne a byt auditovatelny.

### Tasks

- [x] Opravit `game_analyzer.py` variable scope bug (`result` unbound)
- [x] Prepsat vsechny tooly na FastMCP `@app.tool()` dekorator
- [x] Opravit circular import (app -> src/app.py)
- [x] Pridat ThreadPoolExecutor do diagnose/match_patterns
- [x] `engine_client.py` — pridat `stockfish/stockfish.exe` do search paths
- [ ] Pridat workspace context print pri startu (P17)
- [ ] Pridat structured logging do vsech toolu (P19):
  - `logger.warning()` per-failed-game
  - `skipped` counter na konci kazdeho batch toolu
  - 0-games alert
- [ ] Pridat timeout guard na Stockfish call (P6):
  - `concurrent.futures.TimeoutError` wrapper v `engine_client`
  - Limit 30s na analyze, pri prekroceni vratit prazdny vysledek

---

## Phase 2.2 — Pattern detection upgrade

Priorita: **MEDIUM** — potrebujeme vice pattern detectoru pro plnou analyzu.

### Tasks

- [ ] Implementovat zbylych 11 detectoru (C, D, E, F, H, I, J, K, L, M, N, Q1)
- [ ] Pridat ritual effectiveness tracking (6 ritualu z player_pattern_library_v1.json)
- [ ] Pridat metacognition ratio scoring do diagnosticianu
- [ ] Rozsirit WeaknessReport o:
  - ELO trend (pokud hrac hraje na vice uctech)
  - Metacognition ON/OFF pomer
  - Ritual compliance rate

---

## Phase 2.3 — FSRS upgrade + L2 Resources

Priorita: **MEDIUM** — FSRS je v dependencies, neni integrovan.

### Tasks

- [ ] Integrovat `fsrs` knihovnu do SRS engine:
  - Nahradit SM-2 formuli za `fsrs.Card` + `fsrs.Scheduler`
  - Pridat `fsrs.ReviewLog` pro kazdy review
- [ ] Pridat tool: `lichess_srs_due_cards` (vrati karty k opakovani)
- [ ] Pridat tool: `lichess_srs_review` (review karty s quality)
- [ ] Pridat tool: `lichess_create_drill` (vytvori FSRS kartu z blunderu)
- [ ] L2 Resources (P21):
  - `lichess://analysis/{username}/{timestamp}` — JSON analyza
  - `lichess://patterns/{username}/{timestamp}` — JSON patterny
  - `lichess://srs/due` — karty k opakovani

---

## Phase 2.4 — Integrace a deployment

Priorita: **LOW** — az bude server funkcni.

### Tasks

- [ ] Pridat server do `opencode.jsonc`:
  ```json
  "lichess-analyzer": {
    "type": "local",
    "command": ["C:\\Users\\PC\\Documents\\Repozitar_Dev\\_github\\lichess-analyzer-mcp\\.venv\\Scripts\\python.exe", "-X", "utf8", "-m", "src.server"],
    "enabled": true,
    "timeout": 60000
  }
  ```
- [ ] Otestovat vsechny tooly pres opencode sandbox
- [ ] CLI pipeline test: `python scripts/run_pipeline.py outpost2026`
- [ ] Dokumentace v KB (02_ANALYZY/02_chess/)

---

## Struktura po Phase 2

```
lichess-analyzer-mcp/
├── stockfish/
│   └── stockfish.exe          ← Stockfish 18 binary
├── .env                        ← LICHESS_TOKEN (NEcommitovat)
├── lichess-mcp.bat             ← cross-shell launcher
├── src/
│   ├── app.py                  ← FastMCP instance (zde aby nedoslo k circular import)
│   ├── server.py               ← entry point (import tools + app.run)
│   ├── models/                 ← (beze zmen)
│   ├── services/               ← (engine_client hleda stockfish/stockfish.exe)
│   ├── tools/                  ← (7 toolu, FastMCP @app.tool())
│   └── kb/
│       └── writer.py           ← KB persistence
├── scripts/
│   └── run_pipeline.py         ← CLI batch pipeline
├── tests/
│   └── test_services.py        ← 8 testu
└── docs/
    ├── CONTEXT_A_ZAMER.md
    └── PHASE2_BUILD_PLAN.md    ← tento soubor
```

---

## Aktualni blockery

- [x] Stockfish binary — STAHNUTO (stockfish/stockfish.exe)
- [x] LICHESS_TOKEN — NASAZEN (.env, never commit)
- [x] uv sync — HOTOVO (42 packages)
- [x] FastMCP tool registration — FUNGUJE (7 tools)
- [x] Tests — 8/8 PASS
- [ ] opencode.jsonc registrace — ceka na overeni
- [ ] End-to-end test s realnym Lichess API — ceka na overeni
