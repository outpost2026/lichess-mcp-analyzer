# CODE REVIEW — senior dev perspektiva

**Datum:** 2026-08-01 | **Branch:** main | **HEAD:** 0cb5aae
**Rozsah:** kompletní codebase (src/lichess_analyzer_mcp — 19 služeb, 17 toolů, modely, kb, resources)
**Testy:** 93/93 pass (6.9s)
**Výstup:** 4 P1 bugy (2 produkují systematicky špatná data), 3 latentní P1 rizika, P2/P3 backlog, test gap analýza

---

## Verdikt

Architektura zdravá: services/tools/models layered, cache-first, batch guard (P13), audit (P5),
DBCL guardrails, read-after-write (AGENTS.md 2.5). Žádná bezpečnostní díra ani data-loss
v hlavních cestách. Hlavní riziko: **data correctness v 2 coaching toolách (B100, B98) —
LLM reporty se generují ze špatných/neexistujících atributů bez jakékoli detekce.**

---

## P1 — kritické (fix batch 1: ranní session)

### B100 — opening_report produkuje systematicky špatná data
- **Lokace:** `tools/coaching_opening_report.py:94-97`
- **Jistota:** P>0.95
- **Popis:** `getattr(a, "opening_name", "Unknown")` — GameAnalysis tento atribut NEMÁ (správně `a.game.opening`). Stejně tak:
  - `player_color` neexistuje → vždy "white"
  - `acpl` neexistuje → vždy 0
  - `result` neexistuje → vždy "*" (draw)
- **Důsledek:** všechny hry spadnou do "Unknown" jako white s ACPL 0 a win_rate 0.
  `white_openings`, `worst_openings`, `best_openings` = garbage → LLM report postaven na garbage.
- **Oprava:** `a.game.opening`, `a.game.color`, `a.total_acpl`, `a.game.result`.

### B98 — opponent_pool: perspektiva hardcodovaná
- **Lokace:** `tools/coaching_opponent_pool.py:73-82` (opponent_color="black"), `:103-108` (n1_count)
- **Jistota:** P>0.9
- **Popis:** tool nepřijímá username; "opponent" = vždy černý, "author" = vždy bílý
  (`_load_cached_analysis(gid, depth, "white")`). U her, kde autor hrál černým, analyzuje
  autorovy vlastní tahy jako "oponentovy". Navíc `getattr(a, "player_color")` neexistuje
  → n1_count vždy 0, n2 = všechno; do promptu jdou `"?"` placeholdery.
- **Oprava:** přidat `username` param a odvodit barvy z PGN headerů (White/Black),
  nebo explicitně zdokumentovat konvenci (autor=bílý). Opravit n1/n2 výpočet
  (pro spárované game_id: author white vs author black přes cache obou barev).

### B121 — KB writer píše na špatnou absolutní cestu
- **Lokace:** `kb/writer.py:7-13`
- **Jistota:** P>0.95
- **Popis:** `KB_ROOT = dirname(__file__)/../../..` = **repo root**, ne `_github/`.
  Cíl: `lichess-analyzer-mcp/B2B-Knowledge-Base` (adresář NEexistuje — Test-Path=False,
  cesta se nikdy nespustila; target="kb" nikdy nevolán). První persist target="kb"
  vytvoří adresář uvnitř repa → zanese repo.
- **Oprava:** 4× `..` (do `_github/`) + kontrola existence na startupu.
- **Bonus (B119):** `chess_diagnosis_{user}_{date}.md` / `player_patterns_{user}_{date}.json`
  bez timestampu — same-day diagnóza tiše přepíše předchozí. Přidat `_HHMMSS`.

### B31 — LLM cache kolize barev
- **Lokace:** `services/game_llm_cache.py:49-50` (`_llm_cache_path` jen game_id)
- **Jistota:** P>0.9
- **Popis:** dual-cache analyzuje obě strany; LLM analýza white i black téhož game_id
  sdílí jeden soubor `{game_id}_llm.json`. content_tag obsahuje color → mismatch →
  regenerace + last-writer-wins přepíše opačnou perspektivu.
- **Oprava:** klíč `{game_id}_{color}_llm.json`.

---

## P1/P2 — runtime & architektura (fix batch 2)

### B29/F1 — sync blocking v async handlerech
- **Lokace:** `llm_client.py:46,116` (LLM_TIMEOUT 60s; sync httpx.post), `report_persister.py:178-288`
- **Popis:** celý pipeline (fetch, engine, LLM cascade 3×60s) běží na event loopu →
  MCP client timeout (60s) vs server work mismatch. Potvrzeno: 0× asyncio v src/.

### B5 — timeout kill zabíjí špatný engine
- **Lokace:** `engine_client.py:88-112` (`_run_engine_call`), `:77-85` (`_kill_engine`), `:218` (volání z evaluate_move)
- **Popis:** timeout vyvolá `evaluate_move` (LOCÁLNÍ engine), ale `_kill_engine()` ukončí
  SDRUŽENÝ `_engine` → kolaterální ztráta probíhající konkurující analýzy + zbytečný restart.
- **Oprava:** `_run_engine_call(fn, engine)` — killovat referenci toho, co volal.

### B16 — tiché selhání evaluate = zkreslená data
- **Lokace:** `game_analyzer.py:327-335`
- **Popis:** error/exception z `evaluate_move` → `cp_loss = 0` → tah "best". ACPL
  systematicky optimistický, bez markeru. Přidat čítač `evaluation_errors` do GameAnalysis.

### B58/B55 — dual-cache = 2× analýza v jednom tool callu
- **Lokace:** `tools/analyze_game.py:60-69`
- **Popis:** d14 ≈ 84s/perspektiva → 168s+ total > MCP client timeout. Engine guard 15s
  chrání jen jeden call. Dokumentovat timeout kontrakt; zvážit single-perspective default.

### B101 — source="chesscom" tiše ignorován
- **Lokace:** `tools/fetch_games.py:29-35` — validace přijme "chesscom", ale
  `fetch_user_games` umí jen lichess → vrací lichess data bez varování.

### B113 — _detect_s bez guard na fen=""
- **Lokace:** `pattern_detector.py:508-519` — `chess.Board(m.fen)` na starších cache
  (fen="") → ValueError → zhroucení celého `detect_all` (match_patterns error).

---

## P2/P3 — backlog

| ID | Nález | Lokace |
|----|-------|--------|
| B119 | Same-day overwrite v KB filenames (bez timestampu) | kb/writer.py:26-27,65 |
| B61/B64 | analyze_pending: fetch_user_games per game v loopu; N API callů na update indexu | tools/analyze_pending.py:85-96,109-117 |
| B107 | narrative_validator dead code (P1-4 reject loop nesplněn, DBCL jen promptová) | services/narrative_validator.py (0 callerů) |
| B118 | SRSEngine dead code + docstring "FSRS" (reálně SM-2) | services/srs_engine.py |
| B53 | extract_game_id_color_from_analysis dead code (vrací "" vždy) | services/coaching_base.py:113-116 |
| B93 | import_pgn bez force — stale cache pro aktualizovaný PGN | tools/import_pgn.py:45-51 |
| B95 | workspace_info: privátní API _tool_manager + _KNOWN_TOOLS fallback zastaralý (chybí 8 toolů) | tools/workspace_info.py:8-19,36 |
| B17/B67 | audit + log soubory: měsíční cutoff počítaný při importu | services/audit.py:20, logger.py:15-17 |
| B97 | křehká header detekce "White not in pgn.split()[0]" | tools/coaching_opponent_pool.py:60-61 |
| B116 | analyze_position default d18 + multipv=3 = 30-90s+ | tools/analyze_position.py:18-22 |
| B72/B94/B118 | datetime.utcnow() deprecation (4 výskyty) | match_patterns.py:212, diagnose_player.py:108, import_pgn.py:53, srs_engine.py |
| B112 | Pattern A: substring "anonymous" in opponent_name | pattern_detector.py:51-52 |
| B102 | duplicitní _safe/_json_safe | fetch_games.py:8-13 |
| B86/B87 | copy-paste fetch→cache→analyze loop ve 4 toolách | diagnose_player, analyze_pending, cross_game, opening_report |

---

## Test gap analýza

| Mezera | Důsledek |
|--------|----------|
| Žádný test na coaching tooly (opening_report/opponent_pool/cross_game/training_plan) | B100/B98 by chytil unit test |
| Žádný test na kb/writer cestu | B121 latentní |
| test_engine_client mockuje get_engine, ale evaluate_move ho nepoužívá (lokální engine) → reálně spawnuje Stockfish | Křehký test, pomalý na jiných strojích |
| Žádný test na audit.py, batch_guard.py, report_persister.py, game_llm_cache | B31 nechyceno |

---

## Doporučené pořadí oprav (ranní session)

1. **Fix batch 1** (15 min): B100 + B98 (data correctness) + B121 + B31
2. **Fix batch 2** (45 min): B5 + B16 + B101 + B113
3. **F1** asyncio.to_thread (coaching + persist cesta, 1-2 h) — známý P0
4. **Testy** k batch 1-2 (unit testy na coaching tooly + kb writer + game_llm_cache)
5. Ruff debt dedikovaný refactor (ručně, nikdy --fix — GT-078)
6. Exit-hang fix (nice-to-have)

*Reference: docs/CONTEXT_INJECT.md v5.0, .ai_state.json, .session/2026-08-01_context.md*
