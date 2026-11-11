[![](https://flagcdn.com/24x18/gb.png "EN")](./README_en.md)[ English ](./README_en.md)

# Lichess MCP Analyzer

**MCP server pro analýzu šachových partií, detekci vzorových chyb (pattern library jako kompresní model dle T. Mikolova) a spaced repetition trénink (FSRS/SM-2).**

Verze: `0.1.0` | Stav: **single-game pipeline v4** (compact 2.0 default) | Testy: **254 fast + 15 real engine** | Nástrojů: **18** | v4: `7ce7f61`


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


## Nástroje (18 MCP toolů)

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
| `lichess_coaching_single_game` | Coaching report jedné hry (contract v1.1, deterministický fallback) |
| `lichess_coaching_cross_game` | Cross-game coaching přes více partií |
| `lichess_coaching_opening_report` | Report zahájení z více partií |
| `lichess_coaching_opponent_pool` | Analýza poolu soupeřů z game_ids |
| `lichess_coaching_training_plan` | Tréninkový plán podle slabin a dostupného času |
| `lichess_persist_report` | Generuje a ukládá report na disk (docs / KB) |
| `lichess_workspace_info` | Vrátí kontext pracovního prostoru |

### Compact JSON 2.0
Compact 2.0 je **výchozí** výstup `lichess_coaching_single_game` i
`scripts/coach.py` (schema 2.0, obvykle 1,2–4,5 kB). Obsahuje mj. `eval_before/
eval_after` pro velké chyby, patterny u konkrétního flagu, `pv_unavailable` pro
explicitní chybějící PV a `clusters` pro série chyb. Plná schema 1.1 je opt-in
(`--format detailed`) pro debugging a cross-game. Formát, null/omission
politika, prompt šablona a příklady: `docs/COMPACT_JSON_FOR_LLM.md`.

V4 (commit `7ce7f61`) doplnila `flags[].mate_in` (mat v N z nejlepší linie;
kladné = pro hráče, záporné = proti), vynechání `eval_before`/`eval_after`
při rozporu s `cp_loss` (FIX-023), oddělení slabých a čistých fází (FIX-021)
a persistování obnovené PV do cache (FIX-028).

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
- `detector_version`: `DBCL-20261111-dev`

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
# Jedna hra -> compact JSON 2.0 (výchozí, offline)
uv run python scripts\coach.py --game-id FVhqtv1S --username systeq --no-llm --out data\reports\FVhqtv1S.json

# Explicitně schema 1.1, nebo oba tvary
uv run python scripts\coach.py --game-id lxO3gwd3 --format detailed
uv run python scripts\coach.py --game-id lxO3gwd3 --format both --out both.json

# Posledních N her hráče (compact array / NDJSON)
uv run python scripts\coach.py --username systeq --batch 3 --no-llm --out data\runs\batch.json

# Batch pipeline přes celý profil (starší, cross-game)
uv run python scripts\run_pipeline.py outpost2026 --games 20 --depth 12
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
│       │   ├── pv_recovery.py       ← retry PV pro blundery/mistaky bez engine_lines (FIX-014)
│       │   ├── compact_serializer.py ← schema 2.0 (default) + validace + null politika
│       │   ├── game_llm_cache.py    ← per-game LLM cache
│       │   ├── llm_client.py        ← multi-provider LLM cascade
│       │   ├── narrative_validator.py ← LLM hallucination guard (5 claims)
│       │   ├── pattern_detector.py  ← 14 detectorů (A–S, I→I2 merged)
│       │   ├── diagnostician.py     ← cross-game weakness report
│       │   ├── srs_engine.py        ← SM-2 spaced repetition
│       │   ├── compressibility_validator.py ← compression ratio validation
│       │   └── pattern_artifact_validator.py ← pattern semantic contract
│       ├── tools/               ← 18 MCP toolů
│       ├── resources/           ← L2 Resources (analysis, patterns)
│       ├── kb/
│       │   ├── writer.py        ← KB persistence layer
│       │   ├── md_reporter.py   ← MD report generování
│       │   └── schemas.py       ← KB schema definitions
│       └── patterns/
├── scripts/
│   ├── coach.py                 ← Jednotný CLI: hra / PGN / batch, compact 2.0 default
│   ├── run_pipeline.py          ← CLI batch pipeline
│   ├── coach_single.py          ← Starší CLI single-game (deprecated)
│   ├── mcp_call.py              ← CLI runner pro všech 18 MCP toolů
│   ├── pgn_to_compact.py        ← Deprecated shim nad coach.py
│   ├── setup_stockfish.ps1      ← Automatické stažení Stockfish
│   └── ...                      ← 20+ pomocných scriptů
├── tests/                       ← 254 fast testů + 15 real-engine (marker real_engine)
│   ├── test_services.py         ← modely, komprese, validace
│   ├── test_prompt_contract.py  ← schema a mapování promptů
│   ├── test_engine_client.py    ← Stockfish (sdílený engine; real-engine = marker real_engine)
│   ├── test_board_facts.py      ← P0-1: centrální predikáty S, A1 regrese, ekvivalence BFS/single-game
│   ├── test_pattern_unification.py ← P0-2: BFS = single-game patterny (B/J/R/S/C/T), shoda confidence
│   ├── test_phase_p03.py        ← P0-3: phase_method/chess_phase, oba režimy R, 14-figur test
│   ├── test_pattern_semantic_contract.py ← semantic contract + min_games
│   ├── test_dbcl.py             ← win_prob, BFS round-trip, narrative validator, N
│   ├── test_depth_policy.py     ← depth a časová politika
│   ├── test_determinism.py      ← determinismus výstupů
│   ├── test_deterministic_report.py ← deterministický report, slabé/čisté fáze
│   ├── test_compact_serializer.py ← schema 2.0, null politika, eval okno, PV fallback, mate_in
│   ├── test_compact_tool.py     ← default compact, detailed, full alias, both
│   ├── test_coach_cli.py        ← jednotný CLI (argumenty, exit kódy, agregace)
│   ├── test_single_game_contract.py ← kontrakt 1.1 single-game
│   ├── test_fix_batch1.py       ← CR-B100/B98/B121/B31 regresní testy
│   ├── test_fix_batch2.py       ← druhá dávka fixů
│   ├── test_mate_score.py       ← FIX-027 mate_in
│   ├── test_eval_consistency.py ← FIX-023 cp/eval invariant
│   └── test_cache_refresh.py    ← FIX-028 refresh cache a overhead
├── docs/
│   ├── CONTEXT_A_ZAMER.md       ← Kompletní kontext a záměr projektu
│   ├── CONTEXT_INJECT.md        ← Session timeline (v6.0 k 2026-09-05; aktuální stav v .ai_state.json)
│   ├── MERGE_EVAL_feat_to_main.md ← Merge evaluation + empirical run comparison
│   ├── PHASE2_BUILD_PLAN.md     ← Build plan + MCP pitva pravidla
│   ├── 01_DBCL_unity_synthesis.md ← DBCL architektura
│   ├── 02_DBCL_meta_evaluation.md ← 3-kanál noise framework
│   ├── MIKOLOV_KOMPRESE_V_PATTERN_ARCHITEKTURE.md ← Lossy Compression Principle formalizace
│   ├── CLI_USAGE.md             ← Spouštění bez MCP klienta (PowerShell příklady)
│   ├── COMPACT_JSON_FOR_LLM.md  ← Schema 2.0: formát + prompt pro LLM agenta
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
| Lint | ruff (CI: E4/E7/E9/F; širší sada I/UP/N/S/E501 = tech debt) |


## Stav projektu (2026-11-11)

| Co | Stav |
|---|------|
| Testy (fast) | **254/254 pass** (`pytest -q`, 7,7 s; default vylučuje `real_engine`) |
| Testy (real engine) | **15/15 pass** (`pytest -m real_engine`, 12,8 s); GREEN — deterministické díky `clear_hash()` ve fixture |
| MCP toolů | **18** (12 data + 5 coaching + `lichess_persist_report`) |
| v4 / push | `7ce7f61` na `origin/main`; dokumentační změny lokálně, push jen na pokyn |
| Single-game pipeline | **v4 hotová**: FIX-027 (mate), FIX-023 (containment v compactu; root fix pending), FIX-021 (slabé/čisté fáze), FIX-028 (cache refresh) |
| Výchozí výstup | compact JSON 2.0; detailed 1.1 opt-in (`--format detailed`) |
| Regresní compact | `FVhqtv1S` 4377, `WpQOkpc0` 2270, `bRBSphxo` (černý) 2342 znaků; limit 4500 pro FV |
| Cache-hit overhead | 0,28–0,45 s steady state; první hit po upgradu až ~1,56 s (FIX-028 warm-up) |
| Engine / cache | Stockfish depth 14, cache `d14n150000` |
| CI ruff | **GREEN** (`uvx ruff check src/ tests/`, ruff 0.17.4, select E4/E7/E9/F) |
| CI mypy | **RED** — 76 chyb/16 souborů (mypy 2.3.0, `python -m mypy src`; po P0-3 beze změny = 0 nových); gate dlouhodobě neprochází, CI pytest krok je za ním |
| CI pytest | lokálně fast **254/254** + engine **15/15**; v CI je krok za RED mypy gate a `addopts` engine sadu vylučuje (rozhodnutí o engine kroku = D6) |
| Patterny | 14 definovaných (A–S, I→I2), 13 aktivních detektorů + I manual_only |
| Dokumentace | `README.md` aktuální; `README_en.md` a `docs/CONTEXT_INJECT.md` zastaralé |

### Známé odchylky a technický dluh

- **`mate_in` = 3, ne 5** u `FVhqtv1S` ply 75: Stockfish v cache vrací
  `mate 3` (PV `Qf4+ Qf6 Qxf6+`), hodnota se nepřepisuje podle handoffu.
- **`bRBSphxo` endgame 9565/1 je perspektiva soupeře.** Hráč `systeq` hrál
  černého: endgame je čistý (`ACPL 0.0`, 0 flagů), celkové ACPL 35.0.
  Hodnoty 9565 a 3289 znaků pocházejí z analýzy bílého (`Hennessy3`).
- **První cache hit po upgradu** může ještě jednou spustit PV recovery
  (~1,56 s); další hity jsou <0,5 s. `refresh_cached_analysis` navíc
  aktualizuje jen existující cache — PGN run cache nevytváří.
- **`?` ve `_build_explanation`** se objeví, pokud chybí SAN nebo měřené
  `eval_cp` (mimo matovou linii); je to explicitní placeholder, ne data.
- **`engine_lines[].mate_in: null`** v detailed výstupu je šum (schema 1.1
  ho toleruje); compact ho vynechává.
- **FIX-023 warning** `ANOMALY_CP_EVAL_MISMATCH` se loguje pro každý tah,
  nejen flagovaný — může být hlučný.
- **Mypy dluh**: `pattern_detector` (16× return None), `diagnose_player`
  (10× shadowing), `game_analyzer` (21× `Move|None` + dynamické
  `_cache_hit`/`_cache_layer`), `md_reporter` (5× `.get()` na listu).
  Skupina C (`md_reporter`, `game_analyzer`) = kandidáti na latentní
  AttributeError, vyšetřit před ignorováním.
- **`scripts/` je mimo CI ruff gate**: 146 nálezů (F541 74, E402 41,
  E401 16, F401 11, F841 3, E722 1).
- **`tests/test_engine_client.py`** býval maskován dvakrát (lokálně
  `--ignore`, v CI za RED mypy gate). Od 2026-11-11 je rozdělen markerem
  `real_engine`: default `pytest` = 254 fast testů, `pytest -m real_engine`
  = 15 testů proti skutečnému Stockfish. Stale expectation `top_move == "f2c2"`
  (závislá na buildu a `multipv`; Stockfish 18 v `multipv=1` dává `b1h7`)
  nahrazeny invariantami: hloubka ≥ 12 + Qh4 není #1.
- **TT carry-over mění `cp_loss` v rámci procesu** (naměřeno 2026-11-11):
  stejný FEN + tah `f2h4` = 212 cp v čerstvém procesu, ale 402 → 545 →
  764/997 cp po předchozí `analyze_position(multipv=3)`, protože se překlopí
  i `best_move` (`b1h7` → `f2c2`). S `clear_hash()` před každým měřením:
  140/140/140 cp (3 identické běhy). Testy to řeší fixture
  `_fresh_engine_state` (GT-106/P97, GT-093/P73); v produkci se hash maže
  jednou za hru (`game_analyzer.py:929`). Dopad na FIX-023: provenance
  musí reportovat i stav engine, ne jen depth.
- **P0-1 `king_capture_played` OPRAVENO (2026-11-11)**: odvozovalo se z `x`
  v SAN během šachu, takže jakékoli braní potlačilo pattern S. Nově
  `services/board_facts.py` = jediný zdroj predikátů (typ figury přes
  `chess.Board`, totalita bez výjimek) pro všechna 4 místa: BFS
  `_per_blunder_patterns`, single-game `_single_game_candidate`, cross-game
  `_detect_s` a `BoardState`. A1: `capture_checking_piece_possible` už není
  „jakékoli braní" (mimo sach = False). Regrese: `tests/test_board_facts.py`
  (3 FEN fixtures + ekvivalence BFS/single-game).
- **P0-2 sjednocení detektorů B/J/R/S/C/T (2026-11-11)**: dvě paralelní
  implementace per-move patternů (`game_analyzer._per_blunder_patterns` a
  `pattern_detector._single_game_candidate`) sloučeny do jediného jádra
  `pattern_detector.per_move_patterns`; oba volající jsou thin wrappery.
  BFS nově zahrnuje i **T** (dříve jen compact) — naměřeno na 138 fact
  sheetch: **35 (25 %) získá T**, B/J/R/S/C beze změny. Dle plánu §288
  jde o změnu patternu → bump `DETECTOR_VERSION` **proveden 2026-11-11**
  (`DBCL-20260727-dev` → `DBCL-20261111-dev`) lokální migrací bez engine:
  `scripts/migrate_detector_version.py` přepočítal `pattern_matches`
  (277 změn, +65 id) a `board_state` (801/943) ze stored FEN, záloha
  236 souborů (6 186 463 B) v `data/_backup_migrate_2026-11-11/`.
- **P0-3 phase vs segment (2026-11-11)**: `_detect_phase` přejmenován na
  `_detect_segment` (ply 20/50 — segmentace, ne šachová fáze). Nově
  `board_facts.chess_phase` (material-based, Stockfish váhy Q=4/R=2/N,B=1,
  cap 24; prahy ≥20 opening / ≤8 endgame) + na každém tahu
  `chess_phase` a `phase_method` (default `ply_segment`); `phase` zůstává
  alias na segment, payload publikuje i `segment`. Detektory R (per-move
  i cross-game) čtou fázi přes `models.game.effective_phase` — v obou
  režimech `ply_segment` i `material`; defaultní režim je chováním
  identický starému `move.phase` → **0 změn patternů, bez bumpu verze**
  (§288). Testy: `tests/test_phase_p03.py` (24 testů vč. „14 figur není
  endgame" a skutečných koncovek).
- **Snapshoty `systeq` 2026-11-11**: 7 her (3 blitz d12 + 4 rapid d14,
  výsledky 3 win / 2 loss / 2 draw, 3 white + 4 black) analyzováno přes MCP,
  sha256 + metriky v `docs/SNAPSHOT_SYSEQ_2026-11-11.json` (cache je
  gitignored) — základ pro diffy po refaktoru. **Pozor:** opakovaný běh mění
  `timings`, takže sha256 se liší vždy; diff musí jít přes evaly/metriky
  (1/14 souborů se navíc neprodukoval identicky — viz CACHE-RERUN).
- **Quiet blunder**: 98/228 blunderů (43 %) v cache s aktuálním detektorem
  nemá motiv ani pattern (cp < 2000, medián 384). Tichý poziční blunder
  neprojde žádnou větví `_single_game_candidate`; řešení je explicitní
  `unclassified` stav, ne nový pattern bez mechanismu.
- **Compact 2.0 neobsahuje `patterns_meta`** (schema má
  `additionalProperties: false`), takže prázdný `patterns` list nemá důvod;
  detailed 1.1 ho má povinný.
- **MCP server může servírovat starý kód** po změně — po nasazení v4
  restartovat proces; CLI používá aktuální kód.
- **`datetime.utcnow()`** v `kb/writer.py:32` generuje 2 deprecation
  warningy v testech.

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
- `00_STRATEGIE/DALSI_KROKY_po_RUN_003.md` — 15-commit follow-up checklist
- `docs/PHASE2_BUILD_PLAN.md` — build plan v3.0
- `docs/REFACTOR_PLAN_2026-11-11.md` — audit handoffu v1.0 + fázovaný refaktor (Fáze 0–3, rozhodnutí D1–D6)
- `docs/REPORT_STAV_2026-11-11.md` — Feynmanovský report stavu, náročnosti a důsledků

### Pattern library a analýzy
- `B2B-KB/04_KNOWLEDGE_BASE/02_chess/player_pattern_library_v1.json` — zdrojová knihovna 17 patternů
- `B2B-KB/02_ANALYZY/02_chess/chess_self_analysis_baseline_2026-04.md` — baseline analýza
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
- `docs/CONTEXT_INJECT.md` v6.0 (stav k 2026-09-05; aktuální stav viz `.ai_state.json`) — session timeline, anomaly log
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
