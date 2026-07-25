# Context Injection — lichess-analyzer-mcp

## Branch State
Base: `main` | Active: `debug/phase1-fixes` (commit `506b20c`, 2026-07-24)
Pushed to remote ✅ — `origin debug/phase1-fixes`
User directive: **všechny změny na `debug/phase1-fixes`, nikdy ne `main`**

## Fixes Applied (commits `2999136` → `506b20c`)

### Hotové (potvrzeno, funguje)
| Fix | File | Change | Status |
|-----|------|--------|--------|
| **A3** | `services/lichess_client.py:99-104` | `get()` → `get_by_id()` + `[0]` index (API vrací list) | ✅ OK |
| **B1** | `services/lichess_client.py:16` | TTL 300 → 3600 (1h cache) | ✅ OK |
| **A5** | `services/lichess_client.py:192-196` | `httpx.get(explorer.ovh)` → `client.opening_explorer.get_lichess_games(position=fen)` | ✅ OK |
| **+fix** | `tools/opening_explorer.py:41` | `data.get("opening") or {}` (handle None) | ✅ OK |
| **A4** | `services/lichess_client.py` | berserk `export_by_player` + 3× retry (429) + graceful 404 (hikaru) | ✅ OK |
| **+fix** | `tools/workspace_info.py` | Stockfish path z `config_path()` | ✅ OK |
| **+fix** | `server.py` | `.env` loader s `utf-8-sig` (BOM fix) | ✅ OK |
| **+fix** | `scripts/run_mcp_server.ps1` | wrapper pro .env loading | ✅ OK |
| **+fix** | `test_llm_cascade.py` | `_build_coaching_prompt` → `build_coaching_prompt` (rename) | ✅ OK |

### Audit Phase (cross-LLM) — v002
| Artifact | File | Status |
|----------|------|--------|
| **DIGITAL_TWIN.md** | `docs/audit/DIGITAL_TWIN.md` | ✅ OK — profile user's code+decision style |
| **AUDIT_PROMPT.md** | `docs/audit/AUDIT_PROMPT.md` | ✅ OK — standardizovaný prompt pro auditující LLM |
| **AUDIT_REPORT_v1.md** | `docs/audit/AUDIT_REPORT_v1.md` | ✅ OK — Nvidia NEMO audit |
| **AUDIT_REPORT_v2.md** | `docs/audit/AUDIT_REPORT_v2.md` | ✅ OK — Claude audit |
| **PLAN_AUDIT_META.md** | `docs/audit/PLAN_AUDIT_META.md` | ✅ OK — cross-referenční metareport |
| **batch_cascade_log.json** | `docs/audit/batch_cascade_log.json` | ✅ OK — 38-game analysis log |

### Ground Truth bugs (GT-061 to GT-065) — nalezeny auditem, čekají na code fix

| GT | Severita | File (line) | Problém | Dopad |
|----|----------|-------------|---------|-------|
| **GT-061** (lichess-019) | Critical | `game_analyzer.py:161-162` | Chybí `elif` — mistakes list vždy prázdný | ✅ Fix applied (session 2026-07-24) |
| **GT-063** (lichess-021) | Major | `pattern_detector.py` | Pattern G: `frequency = len(game_ids)` vs rate mixup; confidence hardcoded 0.6 | Systematické bias v pattern detecti |
| **GT-064** (lichess-022) | Major | `diagnostician.py:52` | Absolutní count → per-move rate chybí | Zkreslené phase weakness skóre |
| **GT-065** (lichess-023) | Major | `engine_client.py` + cache helpers | Path traversal: `_cache_path`, `_pgn_cache_path`, `_user_games_cache_path` — žádná sanitizace game_id/username | ✅ Fix applied — `_sanitize_id()` helper, `re.sub(r"[^a-zA-Z0-9_-]", "", raw)` ve všech 3 místech |
| **GT-047** (lichess-005) | Medium | report builders | Cascade status exposure v každém reportu | Zbytečný noise |

### False conclusions (poučení z auditu)
| Co jsme tvrdili | Skutečnost | Proč k chybě došlo |
|----------------|------------|-------------------|
| Endpoint odstraněn z produkce | Funguje pro normální účty | Testovali jsme jen hikaru + rate-limit |
| Všechny 3 endpointy 404 | 1. a 2. endpoint fungují (s rate-limit) | Rate-limit zamaskovaný jako 404 |
| A4 = BLOCKED, nutný workaround | A4 = funguje, stačí berserk + retry | Nedostatečný sample, 1 outlier = hikaru |
| Ground Truth je korektní | Claude audit našel B1/B2/C1-C5 v GT dokumentu samotném | Confirmation bias — auditovali jsme kód, ne dokument |
| PHASE2 BUILD PLAN = aktuální | Číslování P# zastaralé, cesty `src/`, test count `8/8` (je 33) | Nikdo neprovedl refresh planu |

## Token
Env var `LICHESS_TOKEN` — není nastavený persistentně v system/user env. Nastavuje se v PowerShell session.

## Timeline (rozšířená)
| Date | Event |
|------|-------|
| 18. 7. | Phase 1 skeleton (commit `4dd503a`) |
| 20. 7. 16:23 | Live test OK: `fetch_user_games("systeq",2)` → 200 ✅ |
| 20. 7. 20:43 | ALL HIGH/MEDIUM/LOW fixes (`98f0546`) |
| 21. 7. | Cache fix (datetime serialization) |
| 22. 7. 20:24 | Debug start — test hikaru → 404, drnykterstein → 404 (rate-limit), systeq → 404. Chybný závěr: endpoint mrtvý |
| 22. 7. 21:14 | A4 fix commit (`99f7b24`): vlastní `_export_by_player` se 3 endpointy |
| 22. 7. 21:48 | Push na remote — blocked kvůli tokenu v verify_a4_fix.py. Token odstraněn, amend, force-push OK |
| 22. 7. 21:48+ | Retest: endpoint vrací 200 s daty! Rate-limit objeven. hikaru = outlier |
| 22. 7. ~22:00 | Závěr: endpoint funguje, A4 fix zbytečný |
| 23. 7. | A4 refactor: berserk export_by_player + retry; .env loader; Stockfish path fix; token fallback |
| 24. 7. 00:01 | Cross-LLM audit pipeline spuštěn — batch 38-game analysis + cascade |
| 24. 7. 00:20 | DIGITAL_TWIN + AUDIT_PROMPT dokončeny (commit `d1b0cc6`) |
| 24. 7. ~01:00 | Nvidia NEMO audit → AUDIT_REPORT_v1 |
| 24. 7. ~02:00 | Claude audit → AUDIT_REPORT_v2 + PLAN_AUDIT_META |
| 24. 7. ~03:00 | GT-061 až GT-065 identifikovány, zapsány do KB |
| 24. 7. 14:00 | Ground Truth v4 sestaven (fix B1/B2/C1-C5 v dokumentu) |
| 24. 7. ~15:00 | Postmortem skill ecosystem integrován do kb-workflow |

## Test Results
| Suite | Status | Poznámka |
|-------|--------|----------|
| Pytest (`tests/`) | **35/35 pass** | ✅ All clean |
| MCP full pipeline (systeq, 5 games) | ✅✅ | Clean slate — A1/B1/B2/B3/T1 verified live |
| Full cascade (`test_llm_cascade.py`) | ✅ PASS | `_build_coaching_prompt` → `build_coaching_prompt` fix OK |
| Live 38-game batch | ✅ OK | Všechny fetch, analyze, cascade probehly |

## Potřebné změny pro tuto session
### Session A (P0) — DONE ✅
- [x] **A1 (GT-061)** — mistakes classification fix ✅
- [x] **A2 (GT-065)** — path traversal sanitize ✅
- [x] **A3** — guard-free test + `_classify_move` unit test ✅

### Session B (P1) — správnost agregací
- [x] **B1 (N3/GT-064)** — `diagnostician.py:52` per-move rate ✅
- [x] **B2 (N2)** — `diagnostician.py:56-57` sorted openings ✅
- [x] **B3 (N4/GT-063)** — `pattern_detector.py:149` frequency = `len(game_ids)` ✅

### Session C (P1) — error handling
- [ ] **C1 (F4)** — structured error format (`tools/*.py`)
- [ ] **C2 (F1')** — mate cp_loss dokumentace

### Session D (P2) — pattern metodologie
- [ ] **D1 (F3)** — weighted confidence (5 detectorů)

### Session E (P2) — úklid
- [ ] **E1 (N7)** — sort order v `match_patterns.py`
- [ ] **E2 (N5)** — old docs cleanup
- [ ] **E3** — dead code cleanup (`patterns/`, `kb/writer.py`)
- [ ] L2 Resources URI (`lichess://analysis/{username}`)
- [ ] FSRS integrace (Phase 2.3)

## Key Files
- `services/lichess_client.py` — všechny fixy (A3, A4, A5, B1, token fallback)
- `services/engine_client.py` — cache helpers, 3× path traversal místo (GT-065)
- `services/game_analyzer.py:161-162` — GT-061 (chybějící elif)
- `services/pattern_detector.py` — GT-063 (frequency/confidence)
- `services/diagnostician.py:52` — GT-064 (normalizace)
- `services/server.py` — .env loader
- `scripts/run_mcp_server.ps1` — .env loading wrapper
- `scripts/verify_a4_fix.py` — verifikace A4
- `scripts/run_audit_pipeline.py` — spuštění cross-LLM audit pipeline
- `docs/audit/` — 6 audit artifacts (DIGITAL_TWIN, PROMPT, v1, v2, META, batch log)
- `docs/GROUND_TRUTH.md` — ground truth v4 (po Claude auditu)
- `docs/PHASE2_BUILD_PLAN.md` — nutný refresh
