# Context Injection — lichess-analyzer-mcp

## Branch State
Base: `main` | Active: `debug/phase1-fixes` (commit `76387ff`, 2026-07-22)
User directive: **všechny změny na `debug/phase1-fixes`, nikdy ne `main`**

## Fixes Applied (commit 76387ff)
| Fix | File | Change |
|-----|------|--------|
| **A3** | `services/lichess_client.py:99-104` | `get()` → `get_by_id()` + `[0]` index (API vrací list) |
| **B1** | `services/lichess_client.py:16` | TTL 300 → 3600 (1h cache) |
| **A5** | `services/lichess_client.py:192-196` | `httpx.get(explorer.ovh)` → `client.opening_explorer.get_lichess_games(position=fen)` |
| **+fix** | `tools/opening_explorer.py:41` | `data.get("opening") or {}` (handle None) |
| **A4** | `services/lichess_client.py:117-158` | vlastní `_export_by_player()` se 3 endpointy místo berserk `export_by_player` |

## A4 — BLOCKED (Lichess Server-Side)
**Root cause**: `/api/games/user/{username}` removed from lila `conf/routes`. All 3 known endpoints return 404:
- `/api/games/user/{username}` — route deleted from lila master
- `/games/export/{username}` — in routes but 404 on production
- `/api/user/{username}/games` — also 404

**Historical twist**: Endpoint **fungoval 20. 7. 2026** při live testu (`test_llm_cascade.py` volá `fetch_user_games("systeq", 2)` → commit `c64a638`). Lichess endpoint odstranil mezi 21.–22. 7. 2026 (během našeho sprintu).

**Workarounds**:
- Per-game export (`/game/export/{gameId}`) funguje → `fetch_game_pgn()`, `analyze_game()`
- Cache (`data/game_cache/`) pro dříve analyzované uživatele (3600s TTL)
- Token (`$LICHESS_TOKEN`) validní pro vše kromě user-game listingu

**3 tools blocked**: `fetch_games`, `diagnose_player`, `match_patterns`

## Test Results (v003)
- **Tool matrix**: 6/7 OK, A4 BLOCKED (deskriptivní `RuntimeError` místo raw 404)
- **Pytest**: 30/33 pass (3 pre-existing import fails — `lichess_mcp/__init__.py` chybí)
- **Script**: `scripts/verify_a4_fix.py` reprodukuje v002 matici

## Token
Token v env var `LICHESS_TOKEN`

## Timeline
| Date | Event |
|------|-------|
| 18. 7. | Phase 1 skeleton (commit `4dd503a`) |
| 20. 7. 16:23 | Live test OK → `fetch_user_games("systeq",2)` works |
| 20. 7. 20:43 | ALL HIGH/MEDIUM/LOW fixes (`98f0546`) |
| 21. 7. | Cache fix (datetime serialization) |
| 22. 7. 20:24 | Debug session start — A4 discovered |
| 22. 7. 20:27 | 3-fix + A4-fix + verify → commit `76387ff` |

## Next Move
Rozhodnout: push `debug/phase1-fixes` → remote, merge to `main`, nebo dál řešit A4 workaround (např. chess.com fallback pro fetch_games, nebo sledovat Lichess release notes).

## Key Files
- `src/lichess_analyzer_mcp/services/lichess_client.py` — všechny fixy
- `src/lichess_analyzer_mcp/tools/opening_explorer.py` — `or {}` fix
- `scripts/verify_a4_fix.py` — verifikační skript
- `logs/DEBUG_REPORT_2026-07-22_v003.md` — v003 report
