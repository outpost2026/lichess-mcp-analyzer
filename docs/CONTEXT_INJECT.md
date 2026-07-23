# Context Injection — lichess-analyzer-mcp

## Branch State
Base: `main` | Active: `debug/phase1-fixes` (commit `3e821dd`, 2026-07-22)
Pushed to remote ✅ — `origin debug/phase1-fixes`
User directive: **všechny změny na `debug/phase1-fixes`, nikdy ne `main`**

## Fixes Applied (commits `99f7b24` + `3e821dd`)

### Hotové (potvrzeno, funguje)
| Fix | File | Change | Status |
|-----|------|--------|--------|
| **A3** | `services/lichess_client.py:99-104` | `get()` → `get_by_id()` + `[0]` index (API vrací list) | ✅ OK |
| **B1** | `services/lichess_client.py:16` | TTL 300 → 3600 (1h cache) | ✅ OK |
| **A5** | `services/lichess_client.py:192-196` | `httpx.get(explorer.ovh)` → `client.opening_explorer.get_lichess_games(position=fen)` | ✅ OK |
| **+fix** | `tools/opening_explorer.py:41` | `data.get("opening") or {}` (handle None) | ✅ OK |

### A4 — PŘEZKUMÁNO (potřebuje přepracovat)

**Starý závěr (nepravdivý):** Endpoint `/api/games/user/{username}` odstraněn z lila produkce. Všechny 3 známé cesty → 404.

**Skutečnost:** Endpoint **funguje** pro normální účty. Naše testování selhalo kvůli:
1. **První test na hikaru** — streamer účet, Lichess záměrně vrací 404 (designové rozhodnutí)
2. **Rate-limit maskovaný jako 404** — po 2-3 requestech Lichess vrací 404 místo 429. Cloudflare po ~15 req blokuje úplně.
3. **conf/routes důkaz** — řádek v routes souboru chybí, ale endpoint v produkci obsluhuje. Pravděpodobně dynamické routování nebo jiný konfigurační soubor.

**Důkaz:** `GET /api/games/user/systeq?max=5` vrátil 200 s 5 reálnými hrami (NDJSON). Potvrzeno opakovaně při čistém rate-limitu.

**Aktuální A4 fix** (`services/lichess_client.py:117-158`): vlastní `_export_by_player()` se 3 endpointy → **zbytečný**. Stačí berserk `export_by_player` + tenacity retry na 429.

**3 tools označené jako "blocked"** (`fetch_games`, `diagnose_player`, `match_patterns`): **nejsou blocked** — endpoint funguje, nástroje pojedou.

### Chybné závěry v minulé session (poučení)

| Co jsme tvrdili | Skutečnost | Proč k chybě došlo |
|----------------|------------|-------------------|
| Endpoint odstraněn z produkce | Funguje pro normální účty | Testovali jsme jen hikaru + rate-limit |
| Všechny 3 endpointy 404 | 1. a 2. endpoint fungují (s rate-limit) | Rate-limit zamaskovaný jako 404 |
| Důkaz z conf/routes | Route je definovaná jinde/dynamicky | Potvrzovací zkreslení |
| A4 = BLOCKED, nutný workaround | A4 = funguje, stačí berserk + retry | Nedostatečný sample, 1 outlier = hikaru |

## Token
Env var `LICHESS_TOKEN` — není nastavený persistentně v system/user env. Nastavuje se v PowerShell session.

## Timeline (upravená)
| Date | Event |
|------|-------|
| 18. 7. | Phase 1 skeleton (commit `4dd503a`) |
| 20. 7. 16:23 | Live test OK: `fetch_user_games("systeq",2)` → 200 ✅ |
| 20. 7. 20:43 | ALL HIGH/MEDIUM/LOW fixes (`98f0546`) |
| 21. 7. | Cache fix (datetime serialization) |
| 22. 7. 20:24 | Debug start — test hikaru → 404, test drnykterstein → 404 (rate-limit), test systeq → 404. Chybný závěr: endpoint mrtvý |
| 22. 7. 21:14 | A4 fix commit (`99f7b24`): vlastní `_export_by_player` se 3 endpointy |
| 22. 7. 21:48 | Push na remote — blocked kvůli tokenu v verify_a4_fix.py. Token odstraněn, amend, force-push OK |
| 22. 7. 21:48+ | Retest: endpoint vrací 200 s daty! Rate-limit objeven. hikaru identifikován jako outlier |
| 22. 7. ~22:00 | Závěr: endpoint funguje, A4 fix je zbytečný |

## Test Results
- **v003 (starý):** 6/7 OK, A4 BLOCKED — neplatí, A4 není blocked
- **Pytest:** 30/33 pass (3 pre-existing import fails)

## Potřebné změny pro příští session
1. **Přepsat A4 fix** — zjednodušit `_export_by_player` na berserk `export_by_player` + tenacity retry (429) + graceful 404 (hikaru-like)
2. **Odstranit `_USER_GAMES_ENDPOINTS`** seznam (3 endpointy) — nepotřebný
3. **Aktualizovat `verify_a4_fix.py`** — otestovat, že berserk export_by_player vrací data pro normální účty
4. **Aktualizovat DEBUG_REPORT** na v004 s korektními závěry

## Key Files
- `src/lichess_analyzer_mcp/services/lichess_client.py` — A3, B1, A5 OK; A4 čeká na přepsání
- `src/lichess_analyzer_mcp/tools/opening_explorer.py` — `or {}` fix
- `scripts/verify_a4_fix.py` — token removed, čeká na update test logiky
- `scripts/REPORT_A4.md` (temp, `C:\Users\PC\AppData\Local\Temp\opencode\REPORT_A4.md`) — detailní narativní analýza A4
