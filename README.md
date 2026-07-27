[![](https://flagcdn.com/24x18/gb.png "EN")](./README_en.md)[ English ](./README_en.md)

# Lichess MCP Analyzer

**MCP server pro analýzu šachových partií, detekci vzorových chyb (pattern library jako kompresní model dle T. Mikolova) a spaced repetition trénink (FSRS/SM-2).**

Verze: `0.1.0` | Stav: **DBCL Phase 2 hotovo** | Testy: **68/68** | Nástrojů: **11**


## Proč?

Tento repozitář vzniká se **dvojím účelem**:

1. **Šachový analyzátor** — personalizovaný tréninkový nástroj, který stáhne tvoje partie z Lichess, analyzuje každý tah Stockfishem, detekuje 14+ vzorových patternů (A–S) z herní historie, diagnostikuje fázové slabiny a pomáhá se z nich učit pomocí spaced repetition.

2. **MCP stavebnice** — demonstrační projekt, na kterém se ověřují principy tvorby MCP serverů v praxi. Každá komponenta (Lichess API, Stockfish engine, pattern detection engine, SRS, B2B-Knowledge-Base persistence) je samostatně použitelná a přenositelná do jiné domény.

> "Build tools for yourself first. If they solve a real problem, they solve a general one."


## Jak to funguje?

```
Tvoje otázka (v opencode)
       |
       v JSON-RPC 2.0 (stdio)
       |
lichess-analyzer-mcp (Python FastMCP)
       |
       +--- Lichess API (berserk) --------- lichess.org
       +--- Stockfish 18 (UCI) ------------ lokální binary
       +--- Pattern detector -------------- kompresní model (Mikolov)
       +--- BlunderFactSheet -------------- DBCL Phase 2 (context window, engine_lines, pattern_matches)
       +--- Narrative validator ----------- LLM hallucination guard (5 claim categories)
       +--- LLM reasoning (cascade) ------- NVIDIA / Cerebras / DeepSeek V4 Flash
       +--- FSRS/SM-2 engine -------------- spaced repetition
       +--- KB writer --------------------- B2B-Knowledge-Base
       +--- MD reporter ------------------- docs/ coaching reports
```


## Pattern detection jako kompresní model

> "Reprezentace reality minimalizující komplexitu, predikční chybu a výpočetní náklady."

### Lossy Compression Principle (T. Mikolov / CPM)

Pattern detection = **lossy compression**. Cílem je najít vzory, které popíšou realitu s maximální entropickou hodnotou na minimum tokenů. Šachový pattern artifact je kompresní model hráče: minimalizuje komplexitu (14 patternů místo 1000+ tahů), predikční chybu (Stockfish cp_loss jako ground truth) a výpočetní náklady (2s cached runtime).

### Validace (MSE)

- MSE zprava: predikce tahů na základě patternů vs realita (Stockfish hodnocení)
- Pokud **MSE(pattern) < MSE(průměr)**, model je validní
- Pokud **MSE(pattern) ≈ MSE(průměr)**, pattern je noise

### Ztrátová komprese

Pattern library ignoruje jednotlivé tahy (šum) a extrahuje behaviorální vzory (signál). Ztrátová komprese = ztratit detaily (přesná hodnota cp_loss) kvůli zachycení vzoru (hráč preferuje X).

**Pravidlo:** Pattern je dobrý, pokud:
- zachycuje chování (signál)
- odstraňuje jednotlivé chyby (šum)
- neodstraňuje strukturu (trendy, fázové slabiny)

### Occamova břitva

Kompresní poměr (`compression_ratio` = raw_cost / pattern_cost) je měřítko Occamovy břitvy. Ze dvou patternů, které stejně dobře vysvětlují data, je ten s **vyšším kompresním poměrem správnější**.

### Confidence vzorec (Mikolov)

```
final_confidence = 0.5 × compression_score + 0.3 × entropy_score + 0.2 × sample_score
```

Řeší **small-N authority problem**: pattern je validní i při N < 25, pokud dobře komprimuje (compression_ratio > 1.5 = signal, > 10 = silný signal, < 1.0 = noise).

### Sémantická integrita — lekce z pattern O

**CR = N / (C_impl + C_udrz) dává smysl POUZE pokud N = počet instancí téže věci.**

Pattern O byl původně pojmenován "Repetition avoidance greed", ale kód detekoval *flat eval plateau → blunder*, nikoliv *repetition refusal*. Výsledek: CR=47.8 měřilo noise, ne signal. **Oprava:** rename na "Stagnační panika" (Option A) — popis nyní odpovídá kódu. Viz `docs/CONTEXT_INJECT.md` §8.

**Pravidlo:** Každý pattern musí projít sémantickým auditem (AUD fáze): shoduje se jméno, mechanismus, hypotéza s kódem? Pokud ne — opravit popis nebo opravit kód.


## Nástroje (11 MCP toolů)

| Tool | Popis |
|------|-------|
| `lichess_fetch_games` | Stáhne recentní partie hráče z Lichess (max 999, berserk pagination fix) |
| `lichess_games_index` | Vrátí cache index her dle resultu (win/loss/draw) |
| `lichess_analyze_game` | Analyzuje jednu partii Stockfishem (depth 8-24, per-move cp_loss, BlunderFactSheet) |
| `lichess_analyze_position` | Analyzuje FEN pozici (depth 8-24, multipv 3, cloud eval optional) |
| `lichess_opening_explorer` | Prozkoumá zahájení v Lichess / Masters databázi |
| `lichess_player_profile` | Vrátí profil, ratingy a statistiky hráče |
| `lichess_diagnose_player` | Diagnostikuje slabiny přes více partii (fáze, openings, ACPL) |
| `lichess_match_patterns` | Detekuje vzorové chyby A–S + podpora game_ids pro anonymní hry |
| `lichess_analyze_pending` | Batch analýza nezpracovaných her (pending detection consistency) |
| `lichess_analyze_anonymous_session` | Dávková analýza anonymních her (URL/ID/txt, label support, agregace) |
| `lichess_import_pgn` | Importuje PGN z libovolného zdroje do analyzy |
| `lichess_workspace_info` | Vrátí kontext pracovního prostoru |

L2 Resources:
- `lichess://analysis/{key}` — uložené výsledky analýzy
- `lichess://patterns/{key}` — uložené výsledky detekce patternů
- `lichess://analysis/list` — seznam všech analýz
- `lichess://patterns/list` — seznam všech pattern detekcí


## DBCL Phase 2 — Implementovaný stav

### BlunderFactSheet (`models/analysis.py`)

Per-blunder struktura s:
- `fen_before`, `board_state` (was_in_check, checking_pieces, capture/king check)
- `legal_moves` (captures/king_moves/blocks/checks)
- `engine_lines` (rank, move_san, eval_cp, win_prob, PV)
- `played_move_rank`, `pattern_matches` (pattern_id, name, confidence, evidence)
- `context_window` (3 tahy před/po s eval + win_prob)
- `detector_version`: `DBCL-20260727-dev`

### Narrative validator (`services/narrative_validator.py`)

5 claim categories pro LLM hallucination guard: piece-on-square, check, capture, eval-number, king-move. Každá kategorie má vlastní validační funkci.

### Engine lines silent fail — root cause fixed

30% BFS mělo 0 engine_lines kvůli `board.san(m)` AssertionError při multi-move PV. **Fix:** sequential `board.copy()` + try/except. RUN_005: 0% failure (ze 70/70 BFS). Viz `docs/CONTEXT_INJECT.md` §5.

### Pattern N — x-ray pin detection

Detekován v `_per_blunder_patterns()`: centipawn_loss ≥ 200 + phase=endgame + was_in_check. Testy v `tests/test_dbcl.py`.

### Pattern I → concept

Pattern I (Bait trap) přesunut na `manual_only`, auto-detekční kód sloučen do I2 (Gift exploitation). AUD-03/11 RESOLVED.


## LLM Reasoning Pipeline

Deterministický výstup (patterny + weakness report) je transformován do přirozeného tréninkového reportu pomocí kaskády LLM providerů.

### Architektura

```
Pipeline data (patterns + weakness)
       |
       v build_coaching_prompt()
       |
       v LLM cascade (první úspěšný vyhrává)
       |
       +--- NVIDIA (free) ............ nemotron-3-super-120b
       +--- Cerebras (free) .......... gpt-oss-120b
       +--- DeepSeek V4 Flash ($) .... deepseek-v4-flash ($0.14/$0.28 per 1M tok)
       |
       v generate_md_report()
       |
       v docs/coaching_report_{user}_{ts}.md
```

Přepíná se env var `DEFAULT_PROVIDER`:
- `""` (nezadáno) → NVIDIA → Cerebras → DS V4 Flash
- `cerebras` → Cerebras → NVIDIA → DS V4 Flash
- `deepseek` → DeepSeek V4 Flash → NVIDIA → Cerebras

### Pipeline mode

`run_coaching_pipeline(mode="auto")` volí architekturu dle golden rules:

| Mode | Kdy | Co dělá |
|------|-----|---------|
| `auto` | default | N≤30 → monolit, N>30 → inkrementální |
| `mono` | rychlá analýza | 1 LLM call, raw data v promptu |
| `incremental` | stovky her, PGN import | per-game LLM cache + agregace se sumárii |

### Porovnání providerů (5 her, stejná data)

| Provider | Model | Tokens | Latence | Cena/5her | SNR |
|----------|-------|--------|---------|-----------|-----|
| NVIDIA | nemotron-3-super-120b-a12b | 2 597 | 17s | $0.000 | 57% |
| Cerebras | gpt-oss-120b | 2 677 | - | $0.000 | 54% |
| DeepSeek V4 Flash | deepseek-v4-flash | 3 876 | 31s | $0.001 | **93%** |

SNR = sémantická věrnost vůči vstupním datům (konfidence %, phase ACPL, žádné inventované patterny).

### API klíče (volitelné)

Do `.env` (všechny jsou free kromě DeepSeek):
```
NVIDIA_API_KEY=nvapi-...
CEREBRAS_API_KEY=csk-...
DEEPSEEK_API_KEY=sk-...       # společný pro DS Chat i V4 Flash
LLM_MAX_TOKENS=4000            # default 2000, pro plný report 4000
```


## Rychlý start

### 1. Stáhnout repo

```
git clone https://github.com/outpost2026/lichess-mcp-analyzer.git
cd lichess-mcp-analyzer
```

### 2. Stáhnout Stockfish

```
powershell -File scripts\setup_stockfish.ps1
```

Nebo stáhni ručně z [official-stockfish/Stockfish](https://github.com/official-stockfish/Stockfish/releases) a vlož `stockfish.exe` do `stockfish/` adresáře.

### 3. Nastavit LICHESS_TOKEN

Vytvoř `.env` soubor v repo root:

```
LICHESS_TOKEN=lip_xxx
```

Token vytvoříš na [lichess.org/settings/oauth](https://lichess.org/settings/oauth).

### 4. Spustit MCP server

```
uv sync
uv run python -m lichess_analyzer_mcp.server
```

Server se připojí přes stdio. Pro opencode ho registruj v `opencode.jsonc`:

```json
"lichess-analyzer": {
    "type": "local",
    "command": ["cesta\\k\\repo\\.venv\\Scripts\\python.exe", "-X", "utf8", "-m", "lichess_analyzer_mcp.server"],
    "enabled": true,
    "timeout": 60000
}
```

### 5. Nebo použít CLI pipeline

```
# Analyzuj vlastní profil (posledních 20 partii)
uv run python scripts\run_pipeline.py outpost2026 --games 20 --depth 12

# Analyzuj + zapiš do KB
uv run python scripts\run_pipeline.py outpost2026 --games 10
```


## Ukázka použití

### "Co je za hráče?"

```
> lichess_player_profile("outpost2026")

{
  "username": "outpost2026",
  "ratings": {
    "blitz": {"rating": 1950, "games": 342},
    "rapid": {"rating": 1880, "games": 156}
  },
  "total_games": 523
}
```

### "Analýza poslední partie"

```
> lichess_analyze_game("abc12345")

{
  "game": {"opening": "Sicilian Defense", "result": "1-0"},
  "stats": {"total_acpl": 45.2, "blunders": 1, "total_moves": 42},
  "blunders": ["Move 28: Nxe5 (loss 450cp)"]
}
```

### "Diagnóza slabin"

```
> lichess_diagnose_player("outpost2026", max_games=15)

{
  "total_acpl": 62.3,
  "phase_weaknesses": {
    "middlegame": {"acpl": 78.1, "blunders": 4},
    "endgame": {"acpl": 45.0, "blunders": 1}
  },
  "top_weaknesses": [
    "Tactical awareness in middlegame transitions",
    "Opening preparation: Sicilian Defense"
  ]
}
```

### "Najdi vzorové chyby"

```
> lichess_match_patterns("outpost2026")

{
  "patterns_detected": [
    {
      "pattern_id": "B",
      "pattern_name": "Automatic grab",
      "confidence": 85,
      "severity": "high",
      "mitigation": "3-sec pause + 'A CO ON?' before every capture"
    }
  ]
}
```


## Struktura repozitáře

```
lichess-analyzer-mcp/
├── stockfish/               ← Stockfish 18 binary (necommitováno)
├── src/
│   └── lichess_analyzer_mcp/
│       ├── app.py               ← FastMCP instance
│       ├── server.py            ← Entry point + .env load + tool registrace
│       ├── models/              ← Datové modely (dataclasses)
│       │   ├── game.py          ← GameSummary, MoveAnalysis, GameAnalysis
│       │   ├── analysis.py      ← BlunderFactSheet, PositionAnalysis, WeaknessReport
│       │   ├── pattern.py       ← PatternDef, PatternMatch, PatternLibrary
│       │   ├── srs_card.py      ← SRSCard, FSRSState
│       │   └── player_profile.py ← PlayerProfile, OpeningStats
│       ├── services/
│       │   ├── lichess_client.py    ← berserk wrapper (fetch, index, cache)
│       │   ├── engine_client.py     ← Stockfish UCI wrapper (depth limit, PV SAN fix)
│       │   ├── game_analyzer.py     ← per-move eval + BlunderFactSheet + per-blunder patterns
│       │   ├── game_llm_cache.py    ← per-game LLM cache
│       │   ├── llm_client.py        ← multi-provider LLM cascade
│       │   ├── narrative_validator.py ← LLM hallucination guard (5 claims)
│       │   ├── pattern_detector.py  ← 14 detectorů (A–S, I→I2 merged)
│       │   ├── diagnostician.py     ← cross-game weakness report
│       │   ├── srs_engine.py        ← SM-2 spaced repetition
│       │   ├── compressibility_validator.py ← compression ratio validation
│       │   └── pattern_artifact_validator.py ← pattern semantic contract
│       ├── tools/               ← 11 MCP toolů
│       ├── resources/           ← L2 Resources (analysis, patterns)
│       ├── kb/
│       │   ├── writer.py        ← KB persistence layer
│       │   ├── md_reporter.py   ← MD report generování
│       │   └── schemas.py       ← KB schema definitions
│       └── patterns/
├── scripts/
│   ├── run_pipeline.py          ← CLI batch pipeline
│   ├── setup_stockfish.ps1      ← Automatické stažení Stockfish
│   └── ...                      ← 20+ pomocných scriptů
├── tests/
│   ├── test_services.py         ← 15 unit testů (modely, komprese, validace)
│   ├── test_prompt_contract.py  ← 13 contract testů (schema, mapping)
│   ├── test_engine_client.py    ← 5 testů s mocknutým Stockfish
│   ├── test_pattern_semantic_contract.py ← 17 testů (semantic contract + min_games)
│   └── test_dbcl.py             ← 17 testů (win_prob, BFS round-trip, narrative validator, N)
├── docs/
│   ├── CONTEXT_A_ZAMER.md       ← Kompletní kontext a záměr projektu
│   ├── CONTEXT_INJECT.md        ← Session timeline (v3.2), CPM lifecycle, anomaly log
│   ├── MERGE_EVAL_feat_to_main.md ← Merge evaluation + empirical run comparison
│   ├── PHASE2_BUILD_PLAN.md     ← Build plan + MCP pitva pravidla
│   ├── 01_DBCL_unity_synthesis.md ← DBCL architektura
│   ├── 02_DBCL_meta_evaluation.md ← 3-kanál noise framework
│   ├── MIKOLOV_KOMPRESE_V_PATTERN_ARCHITEKTURE.md ← Lossy Compression Principle formalizace
│   └── coaching_reports/        ← Generované tréninkové reporty
├── data/
│   ├── game_cache/              ← Cache analýz (JSON, Stockfish + LLM)
│   ├── pgn_cache/               ← PGN import cache
│   ├── resource_store/          ← L2 Resource persistence
│   └── runs/                    ← RUN_003–RUN_005 reporty
├── 00_STRATEGIE/                ← Coaching reporty, DALSÍ_KROKY, DBCL audit
├── .session/                    ← Session context
├── lichess-mcp.bat              ← Cross-shell launcher (Windows)
├── .env                         ← LICHESS_TOKEN (necommitovat)
├── README.md                    ← Tento soubor (CZ)
├── README_en.md                 ← Anglicka verze
├── pyproject.toml               ← Project config, dependencies
└── LICENSE                      ← MIT
```


## Stack

| Vrstva | Technologie |
|--------|-------------|
| Runtime | Python 3.12+, uv |
| Framework | FastMCP (mcp>=1.0.0) |
| Lichess API | berserk>=0.14.0 |
| Šachový engine | chess>=1.11.0 (python-chess) + Stockfish 18 BMI2 |
| Spaced repetition | SM-2 (FSRS připraven na upgrade) |
| HTTP / LLM API | httpx>=0.28.0 |
| LLM providers | NVIDIA (nemotron-3), Cerebras (gpt-oss), DeepSeek (deepseek-v4-flash) |
| Dokuments | python-docx>=1.2.0 |
| Persistence | B2B-Knowledge-Base (JSON + Markdown) |
| Testování | pytest 8+, pytest-cov, mypy |
| Lint | ruff (F, E, W, I, N, UP, S) |


## Stav projektu (2026-07-28)

| Co | Stav |
|---|------|
| Testy | **68/68 pass** |
| Patterny definované | **14** (A, B, C, G, I, I2, J, N, O, P, Q, Q1, Q2, R) + **S** aktivní |
| Patterny s detektorem | **13** aktivních + I manual_only (code→I2) |
| Analyzované partie | **63** (44W/17L/2D, depth 12, RUN_003) + 25 anonymních |
| Cache konzistence | ✅ Auto-konzistentní pipeline |
| Engine | Stockfish BMI2 dev-20260609, depth 12, ACPL MAE 3.9 vs Lichess |
| Engine lines | ✅ **0% silent fail** (70/70 BFS s 3/3 engine_lines) |
| BlunderFactSheet | ✅ Per-blunder: FEN, legal moves, engine_lines, context_window, pattern_matches |
| Narrative validator | ✅ 5 claim categories (pending reject loop) |
| Phase 1 | ✅ Hotova |
| DBCL Phase 2 | ✅ **Hotovo** (engine_lines fix, BFS, N, narrative validator) |
| Pipeline bugfixy | ✅ **6 fixes**: 50-fetch-clamp, pagination, index auto-update, cache, pending detection |
| LLM pipeline | ✅ NVIDIA, Cerebras, DeepSeek V4 Flash |
| DeepSeek Chat | ❌ **ZAKÁZÁN** |
| 25 anonymních her | ACPL=31.7, 21-4-0 winrate, 8 patternů detekováno |

### CPM Lifecycle — Pattern Status

| Pattern | Audit (Fáze 3) | Stav |
|---------|----------------|------|
| A, G, J, N, Q1, Q2, R | ✅ PASS | Produkce |
| B | ⚠️ AUD-01 | Čeká na opravu |
| C | ⚠️ AUD-02 | Čeká na opravu |
| I | ✅ FIXED (concept, manual_only) | Code→I2 |
| O | ✅ **RESOLVED** (rename → Stagnační panika) | Produkce |
| P | ⚠️ AUD-06 | Čeká |
| Q | ❌ AUD-05 | Merge Q+Q2 pending |
| S | ⏳ Čeká na produkci | AUD-10 pending |


## Odkazy na KB a dokumentaci

### Strategie a plány
- `00_STRATEGIE/02_chess/chess_mcp_strategy_v1.md` — strategický plán
- `00_STRATEGIE/DALSÍ_KROKY_po_RUN_003.md` — 15-commit follow-up checklist
- `docs/PHASE2_BUILD_PLAN.md` — build plan v3.0

### Pattern library a analýzy
- `B2B-KB/04_KNOWLEDGE_BASE/02_chess/player_pattern_library_v1.json` — zdrojová knihovna 17 patternů
- `B2B-KB/02_ANALÝZY/02_chess/chess_self_analysis_baseline_2026-04.md` — baseline analýza
- `data/runs/RUN_005_DBCL_v3_2026-07-27.md` — RUN_005 report (ACPL=46.1)

### Lossy Compression Principle
- `docs/MIKOLOV_KOMPRESE_V_PATTERN_ARCHITEKTURE.md` — LCP formalizace
- `B2B-KB/05_EPISTEMIKA/00_kompresni_realismus/Kompresni_modelovani_v_praxi_synteza_v1.md` — syntéza
- `B2B-KB/05_EPISTEMIKA/00_kompresni_realismus/brain_geometric_processor_summary_v2.1.md` — teoretické základy

### Merge evaluation
- `docs/MERGE_EVAL_feat_to_main.md` — empirical comparison feat vs main (3 hry, identické metriky)

### DBCL audit
- `00_STRATEGIE/DBCL_cross_audit_artifact.md` — Claude audit, 21 findings
- `docs/AUDIT_REPORT_lichess-analyzer-mcp_v2.md` — interní audit

### Session context
- `docs/CONTEXT_INJECT.md` v3.2 — session timeline, anomaly log, next steps
- `docs/CONTEXT_A_ZAMER.md` v1.0 — kompletní kontext a záměr projektu


## Inspirace a zdroje

Tento projekt není fork — je vlastní architekturou, ale cenná inspirace a infrastrukturní komponenty pocházejí z následujících open-source projektů.

### Primární zdroje (knihovny)

| Projekt | Autor | Použití |
|---------|-------|---------|
| [berserk](https://github.com/lichess-org/berserk) | lichess-org / Matt Harrison | Lichess API Python client |
| [python-chess](https://github.com/niklasf/python-chess) | Niklas Fiekas | PGN/FEN parsing, UCI wrapper |
| [Stockfish](https://github.com/official-stockfish/Stockfish) | The Stockfish team | Lokální šachový engine |
| [fastmcp](https://github.com/jlowin/fastmcp) | Jeremiah Lowin | FastMCP framework |
| [py-fsrs](https://github.com/open-spaced-repetition/py-fsrs) | Open Spaced Repetition | FSRS algoritmus |

### Sesterské MCP servery v portfoliu

| Server | Toolů | Klíčový pattern |
|--------|-------|-----------------|
| [cnc-tools](https://github.com/outpost2026/mcp-local-server) | 20 | Session state, caching, audit log |
| [linkedin-analyzer](https://github.com/outpost2026/linkedin-mcp-custom) | 8 | FastMCP, KB write-back, EROI scoring |
| [mcp-jobs](https://github.com/outpost2026/MCP-Jobs) | 5 | Boolean AST match, multi-portal scraping |

### Stavba a debug engine integrace

Během vývoje byly identifikovány a opraveny dvě kritické chyby v `engine_client.py`:
- **Inverze perspektivy** — cp_loss počítán z opačné strany
- **Best-move porovnání** — cp_loss počítán jako delta before/after, nikoliv best/actual

Po opravě: ACPL MAE 3.9 oproti Lichess referenci (depth 18-22). Viz `docs/MERGE_EVAL_feat_to_main.md`.

Později opraven **engine_lines silent fail**: 30% → 0% failure rate (sequential board.copy + try/except). Viz `docs/CONTEXT_INJECT.md` §5.


## License

MIT © 2026 Ondrej Sousek (outpost2026)
