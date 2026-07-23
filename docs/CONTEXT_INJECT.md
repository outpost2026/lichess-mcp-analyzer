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

### A4 — OPRAVENO ✅

**Problém:** Starý fix používal vlastní `_export_by_player()` se 3 HTTP endpointy místo berserk `export_by_player`.

**Nový fix** (commit `e03ab5f`): přepsáno na berserk `client.games.export_by_player()` s:
- Retry na 429 (rate-limit) — 3 pokusy s exponenciálním backoffem
- Graceful 404 (hikaru-like účty) — vrací `[]` místo `RuntimeError`
- Odstraněn `_USER_GAMES_ENDPOINTS` seznam
- Odstraněn `import httpx` (dead dependency)

**Důkaz:** Live test 23. 7. 2026 — `fetch_user_games("systeq",3)` vrátil 3 hry ✅. 9/9 MCP toolů PASS přes reálné API.

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
| 23. 7. | A4 refactor: berserk export_by_player + retry; .env loader (BOM fix); Stockfish path fix; token fallback |

## Test Results
- **v003 (starý):** 6/7 OK, A4 BLOCKED — neplatí, A4 není blocked
- **Pytest:** 30/33 pass (3 pre-existing import fails)

## Potřebné změny pro příští session
- ~~Přepsat A4 fix~~ ✅ Hotovo (commit `e03ab5f`)
- ~~Odstranit `_USER_GAMES_ENDPOINTS`~~ ✅ Hotovo
- ~~Aktualizovat `verify_a4_fix.py`~~ ✅ Hotovo
- [ ] Test LLM cascade (NVIDIA → Cerebras → DeepSeek V4)
- [ ] Stress test rate-limitu (15+ requestů)

## Key Files
- `src/lichess_analyzer_mcp/services/lichess_client.py` — všechny fixy (A3, A4 ✅, A5, B1, token fallback)
- `src/lichess_analyzer_mcp/tools/workspace_info.py` — opravena Stockfish cesta
- `src/lichess_analyzer_mcp/server.py` — .env loader (utf-8-sig)
- `scripts/run_mcp_server.ps1` — PowerShell wrapper pro .env loading
- `scripts/verify_a4_fix.py` — verifikace A4 (berserk export_by_player + hikaru graceful)
