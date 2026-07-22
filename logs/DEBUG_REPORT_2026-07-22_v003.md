# DEBUG REPORT v003 — A4 fix + final verification

**Datum:** 2026-07-22 | **Branch:** debug/phase1-fixes
**Status:** All 4 fixy aplikovany, 6/7 testu OK, 1 BLOCKED (A4 external)

---

## Fix Matrix

| # | Fix | Stav | Poznamka |
|---|-----|------|----------|
| A3 | `client.users.get()` → `get_by_id()` + index 0 | ✅ OK | `get_by_id` vraci list, potreba `[0]` |
| B1 | `USER_GAMES_TTL = 300` → `3600` | ✅ OK | Cache expirace 1h misto 5min |
| A5 | `httpx.get(bez auth)` → berserk session | ✅ OK | `position=` parametr, ne `fen=` |
| + | `opening = {}` → `or {}` | ✅ OK | Handle None z TypedDict |
| **A4** | **berserk `export_by_player` → vlastni `_export_by_player` s 3 endpointy + per-game fallback** | **⚠️ BLOCKED** | Lichess API endpointy pro listovani her uzivatele jsou na produkci nedostupne (vsechny 3 znama endpointy vraceji 404). Per-game export pres `fetch_game_pgn(game_id)` funguje. |

## Test Results (Python unit testy + functional testy)

| Test | Status | Detail |
|------|--------|--------|
| pytest (33) | 30 OK, 3 pre-existing FAIL | 3 fail = test_engine_client import path (nasi fixou nedotceno) |
| A3 fetch_user_profile hikaru | ✅ OK | id=hikaru |
| A3 fetch_user_profile systeq | ✅ OK | id=systeq |
| A4 fetch_user_games hikaru(2) | ⚠️ BLOCKED | Lichess API — vsechny 3 endpointy vrací 404 na produkci |
| A5 opening_explorer lichess | ✅ OK | 12 moves: e2e4, d2d4, g1f3 |
| A5 opening_explorer masters | ✅ OK | 12 moves: e2e4, d2d4, g1f3 |
| cloud_eval e4 start | ✅ OK | depth=75 |
| fetch_game_pgn NYcRejUc | ✅ OK | 5005 chars |

## A4 Root Cause — Final Verdict

**Problem:** All 3 známé Lichess API endpointy pro export her uživatele vrací 404:
1. `GET /api/games/user/{username}` — endpoint odstraněn z lila `conf/routes`
2. `GET /games/export/{username}` — existuje v routes master větve, ale na produkci 404
3. `GET /api/user/{username}/games` — neexistuje v routes (nepotvrzený)

**Evidence:**
- Lichess lila `conf/routes` (master branch): zadna routa pro `/api/games/user/{username}`
- Lichess lila `Game.scala`: handler `apiExportByUser` existuje, ale nema routu
- Lichess OpenAPI spec: `/api/games/user/{username}` stale dalsumentovan, ale soubor s definici endpointu chybi
- Raw HTTP testy: 404 pro kazdeho uzivatele (hikaru, drnykterstein, systeq) s i bez auth tokenu

**Fallback:** `client.games.export(game_id)` → `GET /game/export/{gameId}` funguje spravne.

## Nase reseni: `_export_by_player()`

Nahrazuje berserk `export_by_player` vlastni implementaci:
- Zkousi 3 endpointy v poradi: `/api/games/user/{username}`, `/games/export/{username}`, `/api/user/{username}/games`
- Pokud vsechny vrati 404, hodi `RuntimeError` s popisnou hlaskou

## Commity na debug/phase1-fixes

```
77e1831 [debug] 3-fix: get_by_id, TTL=3600, opening_explorer pres berserk auth
2999136 [debug] fix: get_by_id vraci list -> index 0; opening_explorer position= ne fen=
ee9c9c3 [log] DEBUG_REPORT v002 po 3-fix
[... novy commit pro A4 fix ...]
```
