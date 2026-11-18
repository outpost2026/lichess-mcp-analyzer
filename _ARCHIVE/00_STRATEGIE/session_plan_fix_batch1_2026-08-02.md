# Session plán — FIX BATCH 1 (P1 data-correctness)

**Datum:** 2026-08-02 | **Zdroj:** docs/CODE_REVIEW_2026-08-01.md (§P1, fix batch 1)
**HEAD:** b400c7d | **Testy:** 93/93 baseline
**Cíl:** 4 P1 bugy produkující systematicky špatná data. Žádné změny chování mimo dotčené cesty.

---

## Verifikace před fixem

```
cd lichess-analyzer-mcp
pytest tests/ -q            # baseline 93/93
git status                  # čistý (HEAD 03706e7 po commitu docs)
```

Po každém fixu: `pytest tests/ -q` — sada musí zůstat zelená.

---

## B100 — opening_report: getattr neexistujících atributů

**Lokace:** `tools/coaching_opening_report.py:94-97`
**Jistota:** P>0.95 | **Data:** 100 % garbage (Unknown/white/0/draw pro každou hru)

| Řádek | Původní (garbage) | Oprava |
|-------|-------------------|--------|
| 94 | `getattr(a, "opening_name", "Unknown") or "Unknown"` | `(a.game.opening if a and a.game else "") or "Unknown"` |
| 95 | `getattr(a, "player_color", "white")` | `a.game.color if a and a.game else "white"` |
| 96 | `getattr(a, "acpl", None) or 0` | `a.total_acpl if a else 0` |
| 97 | `getattr(a, "result", "*")` | `a.game.result if a and a.game else "*"` |

**Vazba modelu** (`models/game.py`):
- `GameAnalysis.game.opening` → str (GameSummary:11)
- `GameAnalysis.game.color` → str (GameSummary:13)
- `GameAnalysis.total_acpl` → float (GameAnalysis:68)
- `GameAnalysis.game.result` → str (GameSummary:14)

**Verifikace:** unit test `TestOpeningReport` s `GameAnalysis` fixture (viz test plán níže).

---

## B98 — opponent_pool: perspektiva hardcodovaná

**Lokace:** `tools/coaching_opponent_pool.py:73-82` (barvy), `:103-108` (n1/n2)
**Jistota:** P>0.9

### 2.1 Root cause
- `opponent_color = "black"` + `author = _load_cached_analysis(gid, depth, "white")` → u her, kde autor hrál černým, analyzuje autorovy vlastní tahy jako "oponentovy".
- `getattr(a, "player_color", "")` na GameAnalysis neexistuje → n1_count = vždy 0.
- `n1_acpl`/`n2_acpl`/`blunder_rate` = hardcoded `"?"` → prompt dostane placeholdery.

### 2.2 Fix (backward-compatible)
1. **Přidat `username: str = ""`** do signatury toolu (nový optional param).
2. **Odvodit barvy z PGN headerů** per hra:
   - `white_name = game.headers.get("White")`, `black_name = game.headers.get("Black")`
   - pokud `username` zadán: `author_color = "white"` iff `username.lower() == white_name.lower()`, jinak `"black"` (fallback: neznámý → autor=bílý, warning do logu)
   - `opponent_color = "black"` iff `author_color == "white"` else `"white"`
3. **Analyzy obou stran:**
   - `opponent_analysis = analyze_pgn(pgn, player_color=opponent_color, depth, gid)`
   - `author_analysis = _load_cached_analysis(gid, depth, author_color)`; pokud None → `analyze_pgn(pgn, author_color, depth, gid)` (naplní obě cache)
4. **n1/n2 výpočet** (`:103-108`) — z GameAnalysis atributů, ne z player_color:
   - `opp_won = (a.game.color == "white" and a.game.result == "1-0") or (a.game.color == "black" and a.game.result == "0-1")`
   - `n2_count += 1 if opp_won else 0`, `n1_count += 1 if not opp_won` (decisive only; `*` = draw → do n1 s draw flag)
   - **Doplníme placeholdery:** `n1_acpl`/`n2_acpl` = průměr `a.total_acpl` per skupina; `n1_blunder_rate`/`n2_blunder_rate` = `blunders+mistakes` / n
5. **Docstring** — popis konvence (author barva z headerů; bez username default autor=bílý).

**Verifikace:** unit test `TestOpponentPool` s PGN fixture white+black autora (viz test plán).

---

## B121 — kb/writer: špatná absolutní cesta

**Lokace:** `kb/writer.py:7-13`
**Jistota:** P>0.95 | **Dopad:** target="kb" nikdy nespustil; první run zanese repo

### 3.1 Root cause
- `os.path.dirname(__file__)` = `src/lichess_analyzer_mcp/kb`
- 3× `..` → **repo root** (`lichess-analyzer-mcp/`) → + `B2B-Knowledge-Base` = `lichess-analyzer-mcp/B2B-Knowledge-Base` (neexistuje, adresář by se vytvořil uvnitř repa)

### 3.2 Fix
- **4× `..`** → `_github/` → `C:\Users\PC\Documents\Repozitar_Dev\_github\B2B-Knowledge-Base` (existuje, potvrzeno)
- **Startup existence check** (import-time):
  ```python
  _KB_EXISTS = os.path.isdir(KB_ROOT)
  ```
  + `if not _KB_EXISTS: log.error(...)` v `_ensure_dirs()`.
- **Encoding poznámka:** `"02_ANAL\xddZY"` je Python escape `\xdd` = `Ý` (U+00DD) — funkčně OK, runtime se vyhodnotí jako `02_ANALÝZY`, což odpovídá reálnému adresáři. Neměnit (evolní a cp1250-safe).

### 3.3 Bonus B119 (P3, stejný soubor) — timestamp do filenames
- `kb/writer.py:26` `chess_diagnosis_{username}_{date}.md` → `chess_diagnosis_{username}_{date}_HHMMSS.md`
- `kb/writer.py:65` `player_patterns_{username}_{date}.json` → `..._{date}_HHMMSS.json`
- zdroj: `datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")`
- **Součástí BATCHU 1** (stejný soubor, read-after-write v report_persister.py:155,172 zůstává platný)

**Verifikace:** unit test `TestKbWriter` s tmpdir mockem KB_ROOT (monkeypatch) — cesta končí `_github/B2B-Knowledge-Base`, filename má `_HHMMSS`, soubor po zápisu existuje.

---

## B31 — game_llm_cache: kolize barev v LLM cache

**Lokace:** `services/game_llm_cache.py:49-50` (`_llm_cache_path` jen game_id)
**Jistota:** P>0.9

### 4.1 Root cause
- Dual-cache analyzuje obě strany; LLM analýza white i black téhož `game_id` sdílí `{game_id}_llm.json`.
- `content_tag` obsahuje color → mismatch → regenerace + last-writer-wins přepíše opačnou perspektivu.

### 4.2 Fix
- `_llm_cache_path(game_id: str, color: str)` → `{game_id}_{color}_llm.json`
- Update signatur a callerů:

| Funkce | Změna |
|--------|-------|
| `_load_llm_cache(game_id)` → `(game_id, color)` | předat color |
| `_save_llm_cache(game_id, data)` → `(game_id, color, data)` | předat color |
| `analyze_game_llm(...)` (:210, :247) | `_load_llm_cache(game_id, color)` / `_save_llm_cache(game_id, color, result)` |
| `get_game_summary(game_id)` → `(game_id, color)` | + color param (0 volajících — bezpečné) |
| `get_all_game_summaries(game_ids)` (:293) | odvodit color z stockfish cache (`g.get("color")`), fallback "white"; předat do `_load_llm_cache(gid, color)` |

- **Legacy soubory** `{game_id}_llm.json` (bez barev): neexistují (potvrzeno, 0 souborů) — žádná migrace.

**Verifikace:** unit test `TestLlmCacheKey` — `_llm_cache_path("abc", "white") != _llm_cache_path("abc", "black")`, round-trip save/load per color nekoliduje.

---

## Test plán (nové testy k batch 1)

**Lokace:** `tests/test_fix_batch1.py` (jeden soubor, čistě unit — žádný engine/LLM call)

| Test | Co ověřuje |
|------|-----------|
| `TestOpeningReport.test_extracts_real_attributes` | GameAnalysis fixture → opening/color/acpl/result čtené z `game.*`/`total_acpl`, ne defaulty |
| `TestOpponentPool.test_color_from_headers_white` | PGN s autorem=White → opponent_color="black", author_color="white" |
| `TestOpponentPool.test_color_from_headers_black` | PGN s autorem=Black → opponent_color="white", author_color="black" |
| `TestOpponentPool.test_n1_n2_computation` | GameAnalysis fixture (bílé výhry/prohry) → n1/n2 počty správně |
| `TestKbWriter.test_kb_root_path` | monkeypatch KB_ROOT → cesta = `_github/B2B-Knowledge-Base` |
| `TestKbWriter.test_filename_has_timestamp` | filename obsahuje `_HHMMSS` |
| `TestKbWriter.test_write_roundtrip` | zápis → `os.path.isfile` + obsah neprázdný |
| `TestLlmCacheKey.test_path_differs_by_color` | white vs black = různé soubory |
| `TestLlmCacheKey.test_roundtrip_per_color` | save white → load white OK, load black = None |

**Vzor:** `tests/test_services.py` (pytest, `sys.path.insert(0, "src")`), žádná network/dependency.

---

## Pořadí a commit

1. `[FIX] B100` → pytest
2. `[FIX] B98` + `[FIX] B121` (vč. B119) + `[FIX] B31` → pytest
3. `[TEST] fix batch 1: unit testy (opening_report, opponent_pool, kb_writer, llm_cache key)`
4. Full suite `pytest tests/ -q` → 93 + N nových, vše zelené
5. Commit dle repo konvence (tag `[FIX]` / `[TEST]`, popis s ID)
6. Aktualizace `.ai_state.json` (anomalies: 4× PENDING → FIXED) + `.session/2026-08-02_context.md`

---

## Rizika / guardrails

| Riziko | Mitigace |
|--------|----------|
| Změna signatury `get_all_game_summaries` rozbije llm_client | Kontrola calleru `llm_client.py:551` — předává jen `game_ids`; color z cache odvozen uvnitř, signatura BEZ změny |
| B98 fallback konvence (autor=bílý) maskuje chybu | Warning log při neznámém username; unit test pokrývá explicitní i fallback |
| `\xdd` encoding | Neměnit řádek; runtime ověřen jako `Ý` (U+00DD) |
| Ruff debt pre-existing | Jen ručně dotčené řádky; NIKDY `ruff --fix` (GT-078) |
