# Session plán — FIX BATCH 2 (P2 runtime & architektura)

**Datum:** 2026-08-02 | **Zdroj:** docs/CODE_REVIEW_2026-08-01.md (§P1/P2, fix batch 2)
**HEAD:** fc5fc69 (po batch 1) | **Testy:** 109/109 baseline
**Cíl:** 4 P2 bugy — runtime chyby a architektura. Batch 1 = data-correctness, Batch 2 = stabilita/robustnost.

---

## Verifikace před fixem

```
pytest tests/ -q          # 109/109 (fc5fc69)
git status                # čistý
```

Po každém fixu: `pytest tests/ -q` zelená.

---

## B5 — timeout kill zabíjí špatný engine

**Lokace:** `services/engine_client.py:88-112` (`_run_engine_call`), `:77-85` (`_kill_engine`), `:218` (volání z evaluate_move)
**Jistota:** P>0.95 | **Dopad:** P2 — kolaterální ztráta konkurující analýzy

### Root cause
```python
def _run_engine_call(fn, timeout_s):
    ...
    if t.is_alive():
        _kill_engine()          # ← vždy zabije sdružený _engine
```

- `evaluate_move` (:169-241) používá **lokální engine** `chess.engine.SimpleEngine.popen_uci(sf_path)` (ř. 194).
- Když `_run_engine_call(_do_evaluate)` timeoutne, `_kill_engine()` ukončí **sdružený** `_engine` (globál z `get_engine()`) — engine, který tam ani nebyl volaný. Lokální engine zůstane viset (nakonec uklizen v `finally: engine.quit()`).
- Důsledek: ztráta probíhající konkurující analýzy (např. `analyze_position` na jiném vlákně přes sdružený engine) + zbytečný restart.

### Fix
1. **`_run_engine_call(fn, timeout_s, engine=None)`** — nový param, default None = sdružený `_engine` (backward-compat).
2. Timeout branch:
   ```python
   if t.is_alive():
       target = engine if engine is not None else _engine
       if target is not None:
           try:
               target.quit()
           except Exception:
               pass
           if engine is None:
               _engine = None          # sdružený → globál reset
       return {"error": f"engine call timed out after {timeout_s:.0f}s"}
   ```
3. **`evaluate_move` (:218)** — předat lokální referenci:
   ```python
   res = _run_engine_call(_do_evaluate, engine=engine)
   ```
4. **`analyze_position`/`get_best_move`** — bez změny (volají sdružený engine; default None → kill globál, správně).

### Alternativa zvážena
Přidat `engine` param i do `_kill_engine()` a kompletně přepsat — ne, minimální diff: `_kill_engine` zůstává pro sdružený, timeout logika inline v `_run_engine_call` s lokální referencí.

**Verifikace:** unit test — `_run_engine_call` s timeout a lokálním engine → lokální `.quit()` volán, globál `_engine` nedotčen. Mock `threading.Thread.join` (timeout simulace), mock `_engine`/lokální engine jako MagicMock.

---

## B16 — tiché selhání evaluate = zkreslená data

**Lokace:** `services/game_analyzer.py:326-335` + `models/game.py:64-87` (GameAnalysis)
**Jistota:** P>0.9 | **Dopad:** P2 — ACPL systematicky optimistický, bez markeru

### Root cause
```python
try:
    if move in board.legal_moves:
        eval_result = engine_client.evaluate_move(fen_before, move.uci(), depth=depth)
except Exception:
    pass
if eval_result:
    cp_loss = eval_result["centipawn_loss"]
else:
    cp_loss = 0        # ← error/exception → cp_loss=0 → tah "best" → ACPL optimistický
```

- `evaluate_move` na chybu vrací `{"error": ..., "centipawn_loss": 0}` (engine_client.py:219-226) NEBO vyhodí výjimku (zachycenou výše).
- `cp_loss=0` → `_classify_move(0)` = "best". Chyba v analýze vypadá jako perfektní tah.

### Fix
1. **Model** (`models/game.py:64-87`): přidat `evaluation_errors: int = 0` do `GameAnalysis` + do `to_dict()`/`from_dict()` (from_dict s `d.get("evaluation_errors", 0)` — staré cache bez crashu).
2. **GameAnalyzer** (`game_analyzer.py:326-335`):
   ```python
   eval_result = None
   try:
       if move in board.legal_moves:
           eval_result = engine_client.evaluate_move(fen_before, move.uci(), depth=depth)
   except Exception:
       eval_result = None
   if eval_result and "error" not in eval_result:
       cp_loss = eval_result["centipawn_loss"]
   else:
       cp_loss = 0
       analysis.evaluation_errors += 1
   ```
   - Rozlišení: `{"error": ...}` dict (bývalé tiché selhání) i výjimka → obojí inkrementuje čítač.
3. **Marker** — čítač jde do `GameAnalysis.to_dict()` → konzumovatelný LLM promptem.

### Contract testy (NUTNÉ — mění se závislost producer→consumer)
- **Producer:** `GameAnalysis.to_dict()` → nový top-level klíč `evaluation_errors: int`.
- **Consumer:** `_build_game_prompt()` (`game_llm_cache.py:100-118`) čte klíč s `.get("evaluation_errors", 0)` → řádek `Eval errors: N (ACPL may be optimistic)` když N>0. Default 0 → staré cache (149 souborů bez klíče) **bez** '?' v promptu, contract test `test_prompt_has_no_unknown_move` zelený.
- **`PROMPT_TOP_LEVEL_KEYS` NEPŘIDÁVAT** — je to seznam klíčů, které prompt čte a MUSÍ existovat v reálných cache (`test_top_level_keys` iteruje reálné cache soubory). Přidání `evaluation_errors` by spadlo na 149 starých cache. Místo toho **nový contract test** (additive, nezlomí staré cache):
  ```python
  class TestEvaluationErrorsContract:
      def test_to_dict_emits_counter(self):      # to_dict() má evaluation_errors int
      def test_prompt_reads_with_default(self):  # synthetic dict bez klíče → "Eval errors: 0", žádné '?'
      def test_prompt_renders_nonzero(self):     # synthetic dict s 3 → "Eval errors: 3"
  ```

### Verifikace
- Unit test: fixture `evaluate_move` vrací error dict → `GameAnalysis.evaluation_errors == 1`, move není v `blunders`.
- Contract test (nová třída v `test_prompt_contract.py`): to_dict emit + prompt default + prompt nonzero.

---

## B101 — source="chesscom" tiše ignorován

**Lokace:** `tools/fetch_games.py:29-35` (validace), `services/lichess_client.py:264-283` (fetch_user_games umí jen lichess)
**Jistota:** P>0.95 | **Dopad:** P2 — tiché vrácení lichess dat při žádosti o chesscom

### Root cause
```python
if source not in ("lichess", "chesscom"):
    return {"error": ...}
...
games = fetch_user_games(username, ...)   # ← žádný source param, vždy lichess
```

Validace přijme `"chesscom"`, ale `fetch_user_games` nemá source → vrátí lichess data bez varování.

### Fix — explicitní chyba (rozhodnutí)
**NEimplementovat chesscom** (EROI nízká, existuje dedikovaný pipeline jinde) → **fail fast + dokumentace**:

```python
if source == "chesscom":
    return {
        "error": "source='chesscom' not supported yet; only 'lichess' is implemented. "
                 "chesscom fetch returns lichess data silently (B101 fix) — refusing.",
    }
if source not in ("lichess", "chesscom"):
    return {"error": "source must be 'lichess' or 'chesscom'"}
```

### Alternativa zvážena
- Prohodit pořadí validace → špatný error message.
- Implementovat chesscom fetch → mimo scope batch 2, EROI nízká.

### Verifikace
- Unit test: `source="chesscom"` → response má `"error"` obsahující "not supported", žádná data `games`.

---

## B113 — _detect_s zhroucení na fen=""

**Lokace:** `services/pattern_detector.py:508-519` (`_detect_s`)
**Jistota:** P>0.95 | **Dopad:** P2 — `chess.Board(m.fen)` ValueError → zhroucení celého `detect_all` → match_patterns error

### Root cause
```python
for m in analysis.moves:
    if m.was_in_check and m.centipawn_loss >= THRESHOLD_S_CAPTURE_AVERSION_CP:
        board = chess.Board(m.fen)   # ← fen="" na starých cache → ValueError
```

`MoveAnalysis.fen` default `""` (models/game.py:52). Starší cache nemají fen → ValueError propaguje → `detect_all` padá.

### Fix
```python
for m in analysis.moves:
    if m.was_in_check and m.centipawn_loss >= THRESHOLD_S_CAPTURE_AVERSION_CP and m.fen:
        board = chess.Board(m.fen)
        ...
```

Vzor konzistentní s `_detect_n` (:546 `and m.fen` + try/except ValueError).

**Verifikace:** unit test — GameAnalysis s move `was_in_check=True`, `centipawn_loss>=THRESHOLD`, `fen=""` → `_detect_s` vrací None (ne vyjímka).

---

## Test plán (nové testy k batch 2)

**Lokace:** `tests/test_fix_batch2.py` (čistě unit — mock engine/thread, žádný reálný Stockfish)

| Test | Co ověřuje |
|------|-----------|
| `TestB5EngineRef` | `_run_engine_call(fn, engine=local)` timeout → lokalní `.quit()` volán, globál `_engine` nedotčen |
| `TestB5SharedDefault` | `_run_engine_call(fn)` timeout (engine=None) → globál `_engine` resetován na None |
| `TestB16EvalError` | `evaluate_move` error dict → `evaluation_errors=1`, cp_loss=0, move NENÍ blunder |
| `TestB16EvalException` | `evaluate_move` vyhazující výjimku → `evaluation_errors=1` |
| `TestB101Chesscom` | `source="chesscom"` → `error` + žádné games |
| `TestB101ValidLichess` | `source="lichess"` → normální flow (mock fetch) |
| `TestB113FenEmpty` | `_detect_s` s `fen=""` → None, žádná vyjímka |

**Contract testy (přidat do `test_prompt_contract.py`):**

| Test | Co ověřuje |
|------|-----------|
| `test_to_dict_emits_counter` | `GameAnalysis.to_dict()` má `evaluation_errors: int` (producer contract) |
| `test_prompt_reads_with_default` | synthetic dict BEZ klíče → prompt má `Eval errors: 0`, žádné `?` |
| `test_prompt_renders_nonzero` | synthetic dict s 3 → prompt má `Eval errors: 3` |

**Vzor:** `tests/test_fix_batch1.py` (pytest, `sys.path.insert(0, .../src)`), mock MagicMock pro engine/thread.

---

## Pořadí a commit

1. `[FIX] B5 engine reference` → pytest
2. `[FIX] B16 evaluation_errors` (model + analyzer + prompt contract) → pytest
3. `[FIX] B101 chesscom fail-fast` → pytest
4. `[FIX] B113 fen guard` → pytest
5. `[TEST] fix batch 2` (7 testů) → full suite
6. Commit + `.ai_state.json` (4× P2 → FIXED) + `.session/2026-08-02_context.md`

---

## Rizika / guardrails

| Riziko | Mitigace |
|--------|----------|
| B5: lokální engine timeout → quit v daemon threadu | `engine.quit()` v try/except; lokální engine nemá globální lock — bezpečné |
| B16: nové pole mění GameAnalysis.to_dict → cache invalidace | `from_dict` s `.get("evaluation_errors", 0)` — staré cache beze změny, nové s polem; contract test pokrývá |
| B16: `evaluation_errors` neexistuje na starých cache | default 0, žádný crash; prompt čte `.get()` → žádné '?' |
| B101: existující calleré s source="chesscom" | Žádní v codebase (grep) — fail-fast nezlomí nic; unit test potvrdí |
| B113: `m.fen` guard mění sémantiku | konzistentní s `_detect_n`; affected_games se nezmění (fen="" nikdy nemohl mít validní board) |
| Ruff debt pre-existing | Jen ručně dotčené řádky; NIKDY `ruff --fix` (GT-078) |
