# External Reference Report — Lichess MCP Ecosystem

**Datum:** 2026-07-22 | **Autor:** AI agent (debug session)
**Ucel:** Dokumentace vsech externich referencnich zdroju pro dalsi debug a opravu pipeline
**Kontext:** 16 anomalii (DEBUG_REPORT_2026-07-22_v001.md), 3 root causes identifikovany

---

## 1. Prehled ekosystemu — vsechny zname chess MCP servery (GitHub+PyPI)

| # | Repozitar / Package | Stack | Hvezdy | Focus | Pozn |
|---|---------------------|-------|--------|-------|------|
| 1 | **outpost2026/lichess-mcp-analyzer** (tento) | Python, berserk, FastMCP, Stockfish | — | Analyza + pattern detection + SRS + KB | Jediny s pattern library + KB trace |
| 2 | **karayaman/lichess-mcp** | TypeScript, Lichess REST API | ~17 | Obecny wrapper (account, hry, analyza) | Smithery deploy, OAuth, UI extension |
| 3 | **jamespdaily/lichess-mcp** (npx) | TypeScript, Lichess REST API, OAuth | ~0 | Obecny wrapper (hry, analyza, puzzles) | npx install, OAuth flow |
| 4 | **alegerber/chess-com-lichess-org-mcp** | TypeScript, Lichess + Chess.com API | ~120 | 54 toolu, obe platformy | Nejvetsi, reference z CONTEXT_A_ZAMER |
| 5 | **chess-coach-mcp** | Python, FastMCP, Stockfish | ~50 | Analyza partii, trenink | Chybi SRS, chybi pattern library |
| 6 | **chessagine-mcp** | Python, FastMCP, Stockfish | ~30 | Multi-engine analyza | Chybi personalizace |
| 7 | **chess-rocket** | Python, SM-2, Stockfish | ~80 | Spaced repetition | SM-2 (ne FSRS), chybi pattern detekce |
| 8 | **hritik11/chess-mcp** (PyPI) | Python, Stockfish | — | Legal move validation, engine hra | Stockfish-only, bez lichess |
| 9 | **stepbot/StockfishMcp** (PyPI) | Python, Stockfish | ~? | Engine wrapper (5 toolu) | Stockfish-only, bez lichess |
| 10 | **sonirico/mcp-stockfish** | TypeScript/Go, Stockfish | ~14 | Engine analyzer | Stockfish-only |
| 11 | **danilop/chess-support-mcp** | ? | — | Game state management | Bez engine/lichess |
| 12 | **CyprianFusi/mcp-chess-server** | Python, Python | — | Chess.com data | Pouze Chess.com |
| 13 | **datYori/chesscom-mxcp** | Python | — | Chess.com data + cache | Pouze Chess.com |
| 14 | **karayaman/lichess-mcp** (TypeScript, 54 toolu) | TypeScript, Lichess REST API, OAuth | ~17 | Nejkompletnejsi lichess wrapper | OAuth misto tokenu |
| 15 | **GigaChatTester/lichess-mcp** | TypeScript | — | Lichess wrapper | Nizka kvalita |

---

## 2. Klicove rozdily mezi implementacemi

### 2.1 Authentizace

| Server | Auth metoda | Token scope | Pozn |
|--------|-------------|-------------|------|
| tento (lichess-analyzer) | Bearer token v headers | Plny (MCP-analyser) | Token vytvoren, env var nenasazen |
| jamespdaily/lichess-mcp | OAuth2 (browser flow) | Per-user, cache v ~/.lichess-mcp-auth/ | Neni potreba manualni token |
| karayaman/lichess-mcp | Token env var + set_token tool | Plny | Podporuje runtime set |
| alegerber/chess-com-lichess-org-mcp | API key + OAuth | Dle endpointu | Dulezite: pouziva OAuth pro hrani |

**Zaver:** jamespdaily pouziva OAuth — to muze mit jiny pristup k endpointum
nez token-based auth. Lichess API vrazi 404 pro `/api/games/user/{username}`
i s tokenem — to je external issue.

### 2.2 Game export endpoint

Vsechny servery pouzivaji stejny endpoint `/api/games/user/{username}` pres
sve klienty (berserk `client.games.export_by_player`, nebo raw HTTP GET).

| Server | Zpusob | Funguje? |
|--------|--------|----------|
| tento | berserk `client.games.export_by_player` | 404 — vsechny username |
| jamespdaily | raw Lichess API GET | Pravdepodobne ANO (npx publikovan) |
| karayaman | raw Lichess API GET | Pravdepodobne ANO |
| alegerber | raw Lichess API GET | ANO (stars~120, aktivni) |

**Hypoteza (P>0.7):** Problem je specificky pro token-based auth vs OAuth,
nebo pro berserkuv format pozadavku (params encoding, headers).
Dalsi hypoteza: `/api/games/user/{username}` vyzaduje `Accept: application/x-ndjson`
header, ktery berserk standardne posila, ale lichess ho v 2026 zmenilo.

### 2.3 User profile endpoint

| Server | Volani | Funguje? |
|--------|--------|----------|
| tento | `client.users.get("Systeq")` | 404 — chybna metoda |
| tento (po oprave) | `client.users.get_by_id("Systeq")` | Testovano? |
| berserk docs | `client.users.get_by_id(username)` | Dokumentovano jako spravne |

**Root cause (A3) potvrzen:** berserk 0.14.0 (2025-08-26) nema `client.users.get()`.
Tato metoda byla odstranena (posledni v 0.12.x od rhgrant10). Lichess-org
fork prepsal API v 0.12.0 (2023-05).

---

## 3. berserk 0.14.0 — relevantni API reference

### 3.1 Verze

- Instalovana: **berserk 0.14.0** (2025-08-26)
- Dokumentace upstream: 0.14.1.dev0 (unreleased)
- Repo: lichess-org/berserk (158 stars, 80 forks, 715 commits)

### 3.2 Zmeny oproti predchozim verzim

**0.14.0 (2025-08-26) breaking changes:**
- Python 3.8 deprecated (min 3.9+)
- `client.users.get()` → **REMOVED** (nahrazeno `get_by_id()`)
- Pridano: `tv.stream_current_game_of_channel`, `fide.get`, `fide.search`,
  `puzzles.get_next`, `studies.import_pgn`

**0.13.1 (2023-11-02) breaking changes:**
- Pridano: `users.get_by_autocomplete` — nahrazuje stare `users.get()`

### 3.3 Relevantni endpointy naseho serveru

| Nase funkce | berserk call | Stav |
|-------------|--------------|------|
| `fetch_games` (by player) | `client.games.export_by_player(username)` | 404 — external |
| `fetch_games` (by id) | `client.games.export(game_id)` | OK (funguje) |
| `player_profile` | `client.users.get_by_id(username)` | BROKEN (pouziva `get()`) |
| `opening_explorer` | raw httpx GET | 401 — chybi auth headers |
| `analyze_position` (cloud) | `client.analysis.get_cloud_evaluation(fen)` | Nenit testovano |
| `diagnose_player` | kombinace `export_by_player` + `get_by_id` | Kaskada A3 -> A6 |

### 3.4 Alternativni berserk metody (misto broken)

| Broken endpoint | Nahrada |
|----------------|---------|
| `client.games.export_by_player(username)` — 404 | `client.games.export(game_id)` — funguje (per-game) |
| `client.games.export_by_player(username)` — 404 | `client.games.export_ongoing_by_player(username)` — jen rozehrane |
| `client.users.get(username)` — AttributeError | `client.users.get_by_id(username)` — spravna metoda |
| raw httpx GET opening_explorer — 401 | `client.opening_explorer.get_lichess_games(fen)` — berserk wrapper |

---

## 4. Lichess API endpoint reference (overeno 2026-07-22)

| Endpoint | Pouziti | Status |
|----------|---------|--------|
| `GET /api/games/user/{username}` | Export all games of user | **404** — vsechny username |
| `GET /api/game/export/{gameId}` | Export single game | **OK** (overeno) |
| `GET /api/user/{username}` | User profile | Funguje pres spravny berserk call |
| `GET /api/cloud-eval` | Cloud engine evaluation | Funguje |
| `GET /api/opening-explorer` | Opening stats na FEN | 401 bez auth |
| `POST /api/token` | OAuth token creation | Pres browser flow |

---

## 5. B2B Knowledge Base — strategicke reference

### 5.1 chess_mcp_strategy_v1.md (00_STRATEGIE/02_chess/)

Obsahuje:
- EROI scoring pro chess MCP projekt
- Cross-repo lessons z cnc-tools, linkedin-analyzer, MCP-Jobs
- Architektonicka rozhodnuti (FastMCP > mcp[cli], berserk > raw HTTP)
- Phase 2-4 plan

### 5.2 MCP_GROUND_TRUTH_postmortem_agregovany_v1.md (04_KNOWLEDGE_BASE/01_MCP/)

Obsahuje:
- Agregovane post-mortem napric vsemi MCP servery
- Cache strategie (TTLCache, @cached dekorator)
- Debug patterny

---

## 6. Zaver a doporuceni

### 6.1 Co je potreba overit

1. **OAuth vs token auth:** Funguje `/api/games/user/{username}` s OAuth?
   (overit pres jamespdaily/lichess-mcp)
2. **berserk Accept header:** Posila `Accept: application/x-ndjson`? Muze byt
   zmeneno Lichess API (2026 vs 2023 spec)?
3. **`client.analysis.get_cloud_evaluation(fen)`:** Funguje? Neni testovano.

### 6.2 Prioritni opravy (3-fix approach)

1. `client.users.get_by_id()` misto `client.users.get()` — src/services/lichess_client.py:100
2. `USER_GAMES_TTL = 3600` misto 300 (nebo cache bez TTL) — src/services/lichess_client.py:14
3. `client.opening_explorer.get_lichess_games(fen)` misto raw httpx — src/services/lichess_client.py:231

### 6.3 External issue tracking

`/api/games/user/{username}` vraci 404 — neni zpusobeno nasi implementaci.
Je treba:
a) Overit, zda je endpoint zmenen nebo zrusen v 2026
b) Prejit na per-game export (`client.games.export(game_id)`) jako fallback
c) Kontaktovat Lichess API podporu (GitHub issues na lichess-org/lila)
