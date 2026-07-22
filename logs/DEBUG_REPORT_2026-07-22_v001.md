# DEBUG REPORT — Lichess Analyzer MCP

**Date:** 2026-07-22
**Session:** Komplexni test vsech 9 MCP toolu pres opencode sandbox
**User tested:** Systeq (Lichess)
**Environment:** Windows, Python 3.12.13, FastMCP, berserk 0.14.0, Stockfish 18
**Scope:** Only MCP tool invocations (no code edits, no CLI bypass)

---

## Test Matrix

| # | Tool | Input | Status | Note |
|---|------|-------|--------|------|
| 1 | workspace_info | — | ✅ OK | Returns metadata |
| 2 | player_profile | Systeq | ❌ FAIL | `'Users' object has no attribute 'get'` |
| 3 | player_profile | hikaru | ❌ FAIL | Same error — not user-specific |
| 4 | fetch_games | Systeq, 5 | ❌ FAIL | `HTTP 404: Not found` |
| 5 | fetch_games | hikaru, 3 | ❌ FAIL | Same 404 — not user-specific |
| 6 | analyze_game | NYcRejUc (cache, d8) | ✅ OK | Returns cached analysis |
| 7 | analyze_game | NYcRejUc (cache, d14) | ✅ OK | Returns cached analysis (same data) |
| 8 | analyze_game | kNAMNYUF (new, d8) | ✅ OK | 36 moves, ACPL 42.9 |
| 9 | analyze_game | ZZZZZZZZ (invalid) | ✅ OK | Clean error message |
| 10 | analyze_game | 9CkItDO4 (imported) | ❌ FAIL | 404 — tries Lichess API first, ignores cache |
| 11 | analyze_position | startpos, cloud, d10 | ✅ OK | Analysis works |
| 12 | analyze_position | midgame, no-cloud, d10 | ✅ OK | Analysis works |
| 13 | opening_explorer | lichess source | ❌ FAIL | `401 Unauthorized` |
| 14 | opening_explorer | masters source | ❌ FAIL | `401 Unauthorized` |
| 15 | diagnose_player | Systeq, 10, d10 | ❌ FAIL | `HTTP 404` — fetch_games fails first |
| 16 | diagnose_player | hikaru, 5, d10 | ❌ FAIL | Same 404 |
| 17 | match_patterns | Systeq, 5, d10 | ❌ FAIL | `HTTP 404` — fetch_games fails first |
| 18 | import_pgn | valid PGN, white, d10 | ✅ OK | Analysis works, saved to cache |
| 19 | import_pgn | verify via analyze_game | ❌ FAIL | 404 — cache not reachable via analyze_game |

---

## Anomalies (16 total)

### A) Lichess API / Berserk compatibility (6)

| ID | Severity | Tool | Symptom | Root cause |
|----|----------|------|---------|------------|
| A1 | HIGH | workspace_info | `stockfish_installed=false` but stockfish.exe exists | Path resolution — server checks wrong directory |
| A2 | HIGH | workspace_info | `lichess_token_configured=false` but LICHESS_TOKEN is set in env | Server not reading env correctly (process context?) |
| A3 | HIGH | player_profile | `'Users' object has no attribute 'get'` | berserk 0.14.0 API change — `client.users.get()` renamed/removed |
| A4 | HIGH | fetch_games | `HTTP 404` for all users | Lichess `/api/games/user/{username}` endpoint broken/changed |
| A5 | HIGH | opening_explorer | `401 Unauthorized` for lichess + masters | Lichess explorer.lichess.ovh requires auth now |
| A6 | HIGH | diagnose_player, match_patterns | Cascade failure — 404 from fetch_games | Batch tools depend on fetch_games which is broken |

### B) Cache & Data flow (4)

| ID | Severity | Tool | Symptom | Root cause |
|----|----------|------|---------|------------|
| B1 | MEDIUM | fetch_games | Cache ignored? diagnose fails despite systeq_games.json existing | Cache load path or parse issue; or fetch bypasses cache |
| B2 | MEDIUM | diagnose_player | Cannot diagnose Systeq despite 20 cached games | Blocked by A4 — no workaround for offline analysis |
| B3 | MEDIUM | match_patterns | Same cascade failure | Blocked by A4 |
| B4 | LOW | analyze_game | Imported PGN not reachable via analyze_game | analyze_game always fetches PGN from Lichess first, never checks local cache |

### C) Output quality (4)

| ID | Severity | Tool | Symptom | Root cause |
|----|----------|------|---------|------------|
| C1 | LOW | analyze_position | `pv_san` shows `exe5` instead of `e5` (capture syntax for non-capture) | SAN converter in analyze_position misparses UCI to SAN |
| C2 | LOW | analyze_position | `pv_san` shows `Nxc3` instead of `Nc3` (phantom capture) | Same root cause — UCI→SAN conversion bug |
| C3 | LOW | analyze_position | Top lines show depth 1,2,3 instead of multi-PV at requested depth | Server returns iterative deepening levels, not multi-PV |
| C4 | LOW | import_pgn | `player` field missing from output; `opening` empty (should detect Ruy Lopez) | GameSummary not populated from PGN headers |

### D) Stability (2)

| ID | Severity | Tool | Symptom | Root cause |
|----|----------|------|---------|------------|
| D1 | MEDIUM | analyze_game | Timeout on games >45 moves at depth 14 | Stockfish analysis exceeds 60s MCP timeout |
| D2 | MEDIUM | workspace_info | Server hung after parallel Stockfish calls | Concurrent analysis overloads single engine instance |

---

## Working Features (confirmed OK)

- `lichess_workspace_info` — basic health data (except A1, A2)
- `lichess_analyze_game` — cached games, new games (<45 moves), error handling
- `lichess_analyze_position` — both cloud and local engine (except C1-C3 cosmetic)
- `lichess_import_pgn` — full analysis, cache write (except C4)
- Stockfish engine — responsive (single analysis at depth 8-10 works)

## Broken Features (blocked)

- `lichess_player_profile` — berserk API incompatibility (A3)
- `lichess_fetch_games` — Lichess API endpoint dead (A4)
- `lichess_opening_explorer` — Lichess API auth required (A5)
- `lichess_diagnose_player` — cascade dependency on fetch_games (A6)
- `lichess_match_patterns` — cascade dependency on fetch_games (A6)
- `lichess_analyze_game` imported PGN recall — cache miss (B4)

---

*Generated from live MCP tool tests via opencode sandbox. 19 individual tool calls, 16 anomalies identified.*
