# Implementační plán — Coaching Report MCP Tools

**Vstup:** `CHESS_COACHING_PROMPT_TEMPLATES.md` (5 templates), `llm_client.py` (existující LLM infrastruktura)
**Stav:** LLM pipeline existuje jako Python funkce, ale NENÍ vystavena jako MCP tool (všechny stávající 11 tools jsou data-only)
**Datum:** 2026-07-30 | **Priorita:** P1

---

## 1. Současný stav — pipeline je "rozpůlená"

### Data layer (11 MCP tools — hotovo, funguje)

| Tool | Výstup |
|------|--------|
| `lichess_analyze_game` | Stockfish analysis JSON |
| `lichess_match_patterns` | Pattern detection JSON |
| `lichess_diagnose_player` | Weakness report JSON |
| Ostatní 8 | Data pipelines |

### LLM layer (0 MCP tools — chybí)

| Co existuje jako Python funkce | Co chybí jako MCP tool |
|-------------------------------|----------------------|
| `generate_coaching_report()` | ❌ `lichess_generate_coaching_report` |
| `run_coaching_pipeline()` | ❌ `lichess_run_coaching_pipeline` |
| `build_coaching_prompt()` | ❌ (pouze interní) |
| `scripts/test_llm_cascade.py`, `test_incremental_pipeline.py` | ❌ (jen testy, ne tools) |

### Problém

LLM musí manuálně:
1. Zavolat `lichess_analyze_game(game_id="...")` 
2. Zavolat `lichess_match_patterns(username="...")`
3. Ručně naformátovat prompt podle CHESS_COACHING_PROMPT_TEMPLATES.md
4. Zavolat `generate_coaching_report()` přes script/shell

**Cíl:** Všechny 4 kroky automatizovat do jediného MCP tool callu.

---

## 2. Architektura — 5 nových MCP toolů

### T1 — `lichess_coaching_single_game`

**Template:** 1 (Per-Game Coaching Report)
**Vstup:** `game_id: str, color: str = "white", depth: int = 14`
**Pipeline:**
```
1. fetch_game_pgn(game_id)
2. analyze_pgn(pgn, color, depth) → Stockfish analysis
3. match_patterns(game_ids=[game_id]) → per-game pattern detection
4. build_coaching_prompt(template=1, analysis, patterns)
5. _call_llm(prompt) → report text
6. return {"report": report, "game_id": game_id, "stats": {...}}
```

**Soubor:** `tools/coaching_single_game.py` (~120 řádků)

### T2 — `lichess_coaching_cross_game`

**Template:** 2 (Cross-Game Pattern Analysis)
**Vstup:** `username: str, max_games: int = 20, depth: int = 12`
**Pipeline:**
```
1. fetch_games(username, max_games) → seznam game_ids
2. diagnose_player(username, max_games, depth) → weakness report
3. match_patterns(username, max_games, depth) → pattern detection
4. build_coaching_prompt(template=2, patterns, weakness, summaries)
5. _call_llm(prompt) → report text
6. return {"report": report, "games": n, "username": username}
```

**Soubor:** `tools/coaching_cross_game.py` (~150 řádků)

### T3 — `lichess_coaching_opponent_pool`

**Template:** 3 (Opponent Pool Analysis)
**Vstup:** `game_ids: list[str], depth: int = 12`
**Pipeline:**
```
1. Pro každou hru: analyze_pgn(pgn, opponent_color, depth) → flipped perspective
2. match_patterns(game_ids=game_ids) → opponent patterns
3. build_coaching_prompt(template=3, opponent_patterns, dual_cache)
4. _call_llm(prompt) → report text
5. return {"report": report, "games": n}
```

**Soubor:** `tools/coaching_opponent_pool.py` (~130 řádků)

### T4 — `lichess_coaching_training_plan`

**Template:** 4 (Training Plan Generator)
**Vstup:** `username: str, max_games: int = 20, hours_per_week: int = 5, rating: int = 0`
**Pipeline:**
```
1. diagnose_player(username, max_games) → weakness report
2. match_patterns(username, max_games) → patterns
3. build_coaching_prompt(template=4, weakness, patterns, hours_per_week, rating)
4. _call_llm(prompt) → report text
5. return {"report": report, "plan": {...}}
```

**Soubor:** `tools/coaching_training_plan.py` (~100 řádků)

### T5 — `lichess_coaching_opening_report`

**Template:** 5 (Opening Repertoire Report)
**Vstup:** `username: str, max_games: int = 20, depth: int = 12`
**Pipeline:**
```
1. fetch_games(username, max_games) → game_ids + opening info
2. analyze_pgn pro každou hru → ACPL per opening
3. build_coaching_prompt(template=5, openings, acpl_per_opening)
4. _call_llm(prompt) → report text
5. return {"report": report, "openings": [...]}
```

**Soubor:** `tools/coaching_opening_report.py` (~130 řádků)

---

## 3. Sdílená infrastruktura

### 3.1 Prompt builder modul

Vytvořit `services/prompt_builder.py` — převezme šablony z `CHESS_COACHING_PROMPT_TEMPLATES.md` a naplní je daty:

```python
PROMPT_TEMPLATES = {
    1: """Vytvoř coaching report pro hru {game_id}.

K DISPOZICI:
- Cache analýza: {cache_path}
  (per-move Stockfish eval, cp_loss, was_in_check, phase)
- Pattern detection: {patterns_json}
- BlunderFactSheet: {blunders}

PRAVIDLA:
... (template 1 rules from CHESS_COACHING_PROMPT_TEMPLATES.md)
""",
    2: """...""",  # template 2
    3: """...""",  # template 3
    4: """...""",  # template 4
    5: """...""",  # template 5
}

def build_prompt(template_id: int, data: dict) -> str:
    """Naplní template daty z pipeline."""
    template = PROMPT_TEMPLATES[template_id]
    return template.format(**data)
```

### 3.2 Data collector helpers

Pro každý template vytvořit helper, který sesbírá data z existujících MCP toolů:

```python
def _collect_single_game_data(game_id: str, color: str, depth: int) -> dict:
    """Sesbírá data pro Template 1."""
    pgn = fetch_game_pgn(game_id)
    analysis = analyze_pgn(pgn, color, depth, game_id, strict_depth=True)
    patterns = _match_patterns_for_game(game_id)  # light wrapper
    return {
        "game_id": game_id,
        "cache_path": f"data/game_cache/{game_id}_{color}_d{depth}.json",
        "analysis": analysis.to_dict(),
        "patterns": patterns,
    }
```

### 3.3 LLM tool error helper

Sjednotit error handling pro LLM volání:

```python
def _safe_llm_call(prompt: str, context: str = "") -> dict:
    """Zavolá LLM s fallback na data-only report."""
    try:
        report, cascade_log = generate_coaching_report_with_logs(...)
        return {"report": report, "cascade": cascade_log}
    except Exception as e:
        return {
            "report": f"[DATA ONLY — LLM unavailable: {e}]\n{_fallback_data_dump(context)}",
            "error": str(e),
        }
```

---

## 4. Závislosti na existující pipeline

| Potřebuji | Již existuje | Kde |
|-----------|:------------:|-----|
| Stockfish analysis per game | ✅ | `analyze_pgn()`, `_run_analyze_pgn()` |
| Pattern detection per user | ✅ | `match_patterns` volá `pattern_detector.detect_all()` |
| Weakness report | ✅ | `diagnose_player` volá `diagnostician.diagnose()` |
| LLM call s cascading providers | ✅ | `generate_coaching_report_with_logs()` |
| System prompt s DBCL guard | ✅ | `COACHING_SYSTEM_PROMPT` v `llm_client.py` |
| Fallback report | ✅ | `_fallback_report()` v `llm_client.py` |
| Prompt templates | ✅ | `CHESS_COACHING_PROMPT_TEMPLATES.md` (docs — nutno převést do kódu) |
| Auto-fetch game info | ✅ | `fetch_game_pgn()`, `fetch_user_games()` |
| Data fabrication validator | ✅ | `narrative_validator.py` |

### Co je NOVÉ

| Komponenta | Status |
|-----------|--------|
| `services/prompt_builder.py` | **Nový** — převést 5 template z MD do Python stringů |
| `tools/coaching_single_game.py` | **Nový** — T1 MCP tool |
| `tools/coaching_cross_game.py` | **Nový** — T2 MCP tool |
| `tools/coaching_opponent_pool.py` | **Nový** — T3 MCP tool |
| `tools/coaching_training_plan.py` | **Nový** — T4 MCP tool |
| `tools/coaching_opening_report.py` | **Nový** — T5 MCP tool |
| `server.py` | **Edit** — přidat import nových toolů |

---

## 5. Odhad náročnosti

| Krok | Soubory | Odhad | Komentář |
|------|:-------:|:-----:|----------|
| 1. Vytvořit `prompt_builder.py` | 1 nový | 30 min | Převod 5 template z MD do Python |
| 2. Implementovat T1 tool | 1 nový | 30 min | Nejjednodušší — 1 game_id |
| 3. Implementovat T2 tool | 1 nový | 45 min | Složitější — agregace N her |
| 4. Implementovat T3 tool | 1 nový | 30 min | Fliped perspective |
| 5. Implementovat T4 tool | 1 nový | 20 min | Wrapper nad T2 daty |
| 6. Implementovat T5 tool | 1 nový | 30 min | Opening aggregation |
| 7. Upravit `server.py` | 1 existující | 5 min | Import tools |
| 8. Testování | — | 30 min | Smoke test každého toolu |
| **Celkem** | **7 nových + 1 edit** | **~3.5 hod** | |

---

## 6. Rizika a mitigace

| Riziko | Dopad | Mitigace |
|--------|:-----:|----------|
| LLM API klíč nefunguje / vypršel | Medium | Cascade order (NVIDIA → Cerebras → DeepSeek), fallback na data dump |
| Prompt template je příliš dlouhý (token limit) | Medium | Monitorovat token usage, zkrátit template u verbose section |
| Uživatel zadá 100+ her pro T2 | Low | Omezit max_games=50, warning při >30 |
| LLM halucinace i přes DBCL guard | Medium | `narrative_validator.py` — post-processing validace faktů |
| Template 3 (opponent) vyžaduje dual cache | Low | Dual cache již implementován (commit ea19336) |
