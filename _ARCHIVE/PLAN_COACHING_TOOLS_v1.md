# Implementační plán — Coaching Report MCP Tools

**Vstup:** `CHESS_COACHING_PROMPT_TEMPLATES.md` (5 templates), `llm_client.py` (existující LLM infrastruktura)
**Stav:** LLM pipeline existuje jako Python funkce, ale NENÍ vystavena jako MCP tool (11 stávajících tools jsou data-only)
**Závislost:** Session A z `PLAN_DEPTH_POLICY_v1.md` — `config/depth.py` musí existovat před implementací
**Datum:** 2026-07-30 | **Priorita:** P1

---

## 1. Současný stav — pipeline je "rozpůlená"

### Data layer (11 MCP tools — hotovo, funguje)
### LLM layer (0 MCP tools — chybí)

LLM musí manuálně: analyzovat → pattern detect → formátovat prompt → generovat.
**Cíl:** Vše v jediném MCP tool callu, depth z centrální konfigurace.

---

## 2. Synchronizace s Depth Policy

Depth NESMÍ být hardcoded v nových coaching tool parametrech. Každý tool bere default z `config/depth.py`:

| Tool | Depth key v `config/depth.py` | Rozsah |
|------|-------------------------------|:------:|
| T1 — single game | `standard.single_game` (14) | 8-24 |
| T2 — cross-game | `batch.patterns` (12) | 8-18 |
| T3 — opponent pool | `batch.patterns` (12) | 8-18 |
| T4 — training plan | `batch.diagnose` (12) | 8-18 |
| T5 — opening report | `batch.patterns` (12) | 8-18 |

### Povinné pořadí implementace

```
Krok 0: Session A (PLAN_DEPTH_POLICY_v1) — vytvořit config/depth.py + refaktor existujících toolů
  ↓
Krok 1-5: Implementovat 5 coaching tools — import DEPTH_DEFAULTS z config/depth.py
```

---

## 3. Nová architektura — 5 MCP toolů + 2 sdílené moduly

### 3.1 Sdílená infrastruktura (implementovat jako první)

#### `services/prompt_builder.py`
Převod 5 template z `CHESS_COACHING_PROMPT_TEMPLATES.md` do Python stringů s `{placeholder}` pro data z pipeline.

```python
from lichess_analyzer_mcp.config.depth import DEPTH_DEFAULTS

PROMPT_TEMPLATES = {
    1: """Vytvoř coaching report pro hru {game_id}.
K DISPOZICI:
- Cache analýza: data/game_cache/{game_id}_{color}_d{depth}.json
  (per-move Stockfish eval, cp_loss, was_in_check, phase)
- Pattern detection: {patterns_json}
- BlunderFactSheet: každý blunder s context_window a engine_lines
...""",
    2: """...""",
    3: """...""",
    4: """...""",
    5: """...""",
}

def build_prompt(template_id: int, data: dict) -> str:
    return PROMPT_TEMPLATES[template_id].format(**data)
```

#### `services/coaching_base.py` (data collectory)
Sdílené helpery, které volají data pipeline a volí depth z konfigurace:

```python
from lichess_analyzer_mcp.config.depth import DEPTH_DEFAULTS
from lichess_analyzer_mcp.services.game_analyzer import analyze_pgn
from lichess_analyzer_mcp.services.lichess_client import fetch_game_pgn

def collect_single_game(game_id: str, color: str = "white", depth: int = 0) -> dict:
    if depth == 0:
        depth = DEPTH_DEFAULTS["standard"]["single_game"]
    pgn = fetch_game_pgn(game_id)
    analysis = analyze_pgn(pgn, color, depth, game_id, strict_depth=True)
    return {"game_id": game_id, "analysis": analysis.to_dict(), "depth": depth}

def collect_patterns_for_game(game_id: str) -> list:
    """Wrapper pro per-game pattern detection."""

def safe_llm_call(prompt: str, context: str = "") -> dict:
    """LLM s fallback na data dump."""
```

### 3.2 Pět MCP toolů

#### T1 — `lichess_coaching_single_game`
- **Soubor:** `tools/coaching_single_game.py`
- **Vstup:** `game_id, color="white", depth=0`
- **Default depth:** 0 → auto: `DEPTH_DEFAULTS["standard"]["single_game"]` (14)
- **Pipeline:** fetch PGN → Stockfish → match_patterns per-game → LLM → report

#### T2 — `lichess_coaching_cross_game`
- **Soubor:** `tools/coaching_cross_game.py`
- **Vstup:** `username, max_games=20, depth=0`
- **Default depth:** 0 → auto: `DEPTH_DEFAULTS["batch"]["patterns"]` (12)
- **Pipeline:** fetch games → diagnose_player → match_patterns → LLM → report

#### T3 — `lichess_coaching_opponent_pool`
- **Soubor:** `tools/coaching_opponent_pool.py`
- **Vstup:** `game_ids: list[str], depth=0`
- **Default depth:** 0 → auto: `DEPTH_DEFAULTS["batch"]["patterns"]` (12)
- **Pipeline:** dual analyze (flipped) → opponent patterns → LLM → report

#### T4 — `lichess_coaching_training_plan`
- **Soubor:** `tools/coaching_training_plan.py`
- **Vstup:** `username, max_games=20, hours_per_week=5, rating=0, depth=0`
- **Default depth:** 0 → auto: `DEPTH_DEFAULTS["batch"]["diagnose"]` (12)
- **Pipeline:** diagnose → patterns → LLM plan → report

#### T5 — `lichess_coaching_opening_report`
- **Soubor:** `tools/coaching_opening_report.py`
- **Vstup:** `username, max_games=20, depth=0`
- **Default depth:** 0 → auto: `DEPTH_DEFAULTS["batch"]["patterns"]` (12)
- **Pipeline:** fetch games → analyze per opening → LLM → report

---

## 4. Závislosti

| Potřebuji | Status |
|-----------|:------:|
| `config/depth.py` (Session A z DEPTH_POLICY) | ❌ **Nutno implementovat před coaching tools** |
| Refaktor existujících 7 toolů na centrální config | ❌ **Nutno před coaching tools** (konzistence) |
| `services/prompt_builder.py` | ❌ Nový — 5 template z MD do Python |
| `services/coaching_base.py` | ❌ Nový — data collectory + safe_llm_call |
| 5x `tools/coaching_*.py` | ❌ Nový |
| `server.py` — přidat import new tools | ❌ Edit |

Všechna data pipeline již existuje:
- `analyze_pgn()` ✅ | `match_patterns` / `pattern_detector` ✅ | `diagnostician.diagnose()` ✅
- `generate_coaching_report_with_logs()` ✅ | `COACHING_SYSTEM_PROMPT` ✅
- `_fallback_report()` ✅ | `narrative_validator.py` ✅

---

## 5. Odhad náročnosti (včetně závislosti)

| Fáze | Co | Soubory | Čas |
|:----:|----|:-------:|:---:|
| **0a** | Vytvořit `config/depth.py` | 1 nový | 10 min |
| **0b** | Refaktor 7 existujících toolů na centrální depth | 7 edit | 20 min |
| **1** | Vytvořit `services/prompt_builder.py` | 1 nový | 30 min |
| **2** | Vytvořit `services/coaching_base.py` | 1 nový | 20 min |
| **3** | Implementovat T1 (single game) | 1 nový | 30 min |
| **4** | Implementovat T2 (cross-game) | 1 nový | 45 min |
| **5** | Implementovat T3 (opponent pool) | 1 nový | 30 min |
| **6** | Implementovat T4 (training plan) | 1 nový | 20 min |
| **7** | Implementovat T5 (opening report) | 1 nový | 30 min |
| **8** | Upravit `server.py` | 1 edit | 5 min |
| **9** | Testování (smoke test per tool) | — | 30 min |
| | **Celkem** | **9 nových + 8 edit** | **~4.5 hod** |

**Z toho závislost (fáze 0a+0b):** 30 min — musí být hotovo před fází 3.
**Samotné coaching tools (fáze 1-9):** ~4 hod (po splnění závislosti).

---

## 6. Postup implementace (doporučené pořadí)

```
Den 1 — Session A (DEPTH_POLICY)
├── config/depth.py
├── Refaktor analyze_game.py, import_pgn.py, analyze_position.py
├── Refaktor analyze_pending.py, diagnose_player.py, match_patterns.py, anonymous_session.py
└── Commit + restart MCP

Den 2 — Coaching tools
├── prompt_builder.py (5 template z MD do Python)
├── coaching_base.py (collectory + safe_llm_call)
├── coaching_single_game.py (T1)
├── coaching_cross_game.py (T2)
├── coaching_opponent_pool.py (T3)
├── coaching_training_plan.py (T4)
├── coaching_opening_report.py (T5)
├── server.py (importy)
└── Smoke test + commit + restart
```
