# DEBUG REPORT v002 — Po 3-fix aplikaci

**Datum:** 2026-07-22 | **Branch:** debug/phase1-fixes
**Status:** 3 fixy aplikovany, 6/7 testu OK, 1 zbyva (A4 external)

---

## Fix Matrix

| # | Fix | Stav | Poznamka |
|---|-----|------|----------|
| A3 | `client.users.get()` → `get_by_id()` + index 0 | ✅ OK | `get_by_id` vraci list, potreba `[0]` |
| B1 | `USER_GAMES_TTL = 300` → `3600` | ✅ OK | Cache expirace 1h misto 5min |
| A5 | `httpx.get(bez auth)` → berserk session | ✅ OK | `position=` parametr, ne `fen=` |
| — | `opening = {}` → `or {}` | ✅ OK | Handle None z TypedDict |

## Test Results (Python unit testy + functional testy)

| Test | Status | Detail |
|------|--------|--------|
| pytest (33) | 30 OK, 3 pre-existing FAIL | 3 fail = test_engine_client import path (nasi fixou nedotceno) |
| A3 fetch_user_profile hikaru | ✅ OK | id=hikaru |
| A3 fetch_user_profile systeq | ✅ OK | id=systeq |
| A4 fetch_user_games hikaru(2) | ❌ 404 | Lichess API `/api/games/user/{username}` — external |
| A5 opening_explorer lichess | ✅ OK | 3 moves: e5, c5, d5 |
| A5 opening_explorer masters | ✅ OK | 3 moves: c5, e5, e6 |
| cloud_eval e4 start | ✅ OK | depth=70 |
| fetch_game_pgn NYcRejUc | ✅ OK | 5005 chars |

## Zbyvajici problem: A4 (404 na games export)

`client.games.export_by_player(username)` → `GET /api/games/user/{username}` → **404**

Toto neni zpusobeno nasi implementaci — endpoint vraci 404 i pri rucnim curl testu.
Zbyvajici reseni:
- Overit, zda endpoint vyzaduje `Accept: application/x-ndjson` header (lich Lichess 2026?)
- Fallback: per-game export `client.games.export(game_id)` — funguje, ale je per-game
- Alternativa: `client.games.get_ongoing()` — jen rozehrane hry
- Kontaktovat Lichess API support

## Commity na debug/phase1-fixes

```
77e1831 [debug] 3-fix: get_by_id, TTL=3600, opening_explorer pres berserk auth
2999136 [debug] fix: get_by_id vraci list -> index 0; opening_explorer position= ne fen=
```
