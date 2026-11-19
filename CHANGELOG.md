# Changelog

Všechny změny formátu a pipeline. Verze odpovídají kontraktu compact JSON /
single-game pipeline, ne balíčku `0.1.0` (ten zůstává beze změny).

> **Poznámka k historickým odkazům (2026-11-18):** cesty v položkách před `[DOCS]`
> platily v době daného release. Soubory později přesunuté do `_ARCHIVE/` mají
> svůj obsah v git historii a unikátní fakta v `docs/01_EVIDENCE_DIGEST.md`.
> Historické záznamy se mají číst jako dobové, nikoli jako živé odkazy.

## [2.9] - 2026-11-19

Additive contract iteration over frozen 2.8, driven by the 3.LLM handoff and
verified claims V1–V27. **No detector, engine or ELO change.**

- `schemas/single_game_v2_compact_2.9.json`; `SCHEMA_V = "2.9"`,
  `SUPPORTED_VERSIONS = ("2.6","2.7","2.8","2.9")`; 2.8 stays frozen/readable.
- `decisive_moves[]`: every mate transition is now decisive, including
  **`winning_to_mate`** and **`losing_to_mate`** (V1/V22/V25 gap). Items carry
  optional `mate_missed`, `mate_via`, `best` so a missed mate in a still-winning
  position is no longer invisible (aFZC293b W41 `Nxd6+`, 9124 cp, mate in 3).
- New `momentum_moves[]`: `winning_to_winning` swings with `mate_missed > 0`
  or `cp > 500` (V3/V20 gap; DclcmVZy W49 646 cp).
- Deterministic report ranking uses the same extended impact set, so the
  narrative and the structured fields agree.
- Two new tests (all mate transitions, momentum rule); tests migrated 2.8→2.9.
  Gates: pytest **571 passed / 18 deselected**, Ruff clean, mypy 0/74,
  `verify_docs_trimming.py` 11/11 OK.

## [CLOCK-API] - 2026-11-19

Oprava Lichess PGN exportu pro D23 clock data (3.LLM handoff, 19.11.).

- `lichess_client.fetch_game_pgn()` nyní volá
  `client.games.export(game_id, as_pgn=True, clocks=True)` — bez `clocks=True`
  Lichess nevrací `[%clk ...]` komentáře a `parse_clock_data()` mohlo jen
  hlásit `clock_data_unavailable`. Berserk 0.14 `clocks` parametr podporuje
  (ověřeno z podpisu `Games.export`).
- Clock-aware PGN má vlastní cache jmenný prostor (`*.clocks.pgn`), aby se
  starý `.pgn` bez hodin nikdy nevracel jako clock data.
- 1 regresní test (`tests/test_clock_parser.py`): export volá `clocks=True`,
  vznikne `.clocks.pgn`, parser najde `[%clk`. Gates: pytest 569 passed,
  Ruff clean, mypy 0/74.

## [D41] - 2026-11-18

Rozhodnutí D1 (default phase mode) na základě měření, ne názoru. Žádná změna
kódu, schémat nebo `DETECTOR_VERSION`.

- Nový offline nástroj `scripts/measure_d1_phase_mode.py`: dual-run per-move
  detektorů nad 20 cache soubory `*_d14n150000.json`, Q4 experiment vypnutý.
- Výsledek (`data/runs/D1_phase_measurement_2026-11-18.json`): 162 flagů,
  81 s vyplněným `chess_phase`, 87 vs 86 patternů, **1 set-flip (0,62 %)**
  a 1 R-flip (`7l9g62Eo` ply 77 `Bxh2`: segment endgame přidává R, material
  middlegame jej odebírá).
- `AUDIT_INTEGRATION` §15: **D41 = `ply_segment` zůstává default**, `material`
  zůstává opt-in přes `phase_method`. D41a: měření nutno zopakovat po změně R
  detektoru nebo prahů.
- Roadmapa `SESSION_HANDOFF` §5 položka #7 uzavřena. Všechny položky #1–#7
  jsou nyní DONE (Q4 nadále jako experiment za flagem, D4 gate otevřený).

## [Q4-EXP] - 2026-11-18

Položka #5 roadmapy jako **experiment za flagem, ne produkční pattern**.
Žádná změna `DETECTOR_VERSION`, schémat ani výchozího chování.

- `pattern_detector.py`: `EXPERIMENTAL_Q4_ENABLED` z env
  `LICHESS_EXPERIMENTAL_Q4=1` (výchozí **vypnuto**). Kandidát
  `declined_forcing_move_at_pivot` (Q4) se emituje jen při zapnutém flagu a
  jen když `cp_loss > 50`, engine best je forcing (`x`/`+`/`#`), sehraný tah
  forcing není a hráč není v šachu.
- `scan_single_game` respektuje `cand["mitigation"]` pro experimentální
  kandidaty (produkční chování nezměněno).
- `coaching_single_game` označí flag-on payload jako
  `detector_version = DBCL-20261117-dev+Q4-exp`, aby nebyl zaměněn s produkčním
  během. **Cache je klíčována policy tokenem, ne detector verzí** — experiment
  proto musí běžet s čistou cache / `use_cache=False`, jinak Q4 neuvidí.
- 5 testu (`tests/test_experimental_q4.py`): vypnuto / zapnuto / forcing best /
  non-forcing played / cp prah. Gates: pytest 568 passed, Ruff clean, mypy 0/74.
- D4 gate zůstává otevřený: prod do kontraktu až po validaci na ≥10 hrách.

## [D23] - 2026-11-18

Položka #6 roadmapy (T-16 / D23 `%clk`). Žádná změna schémat 2.8 / 1.2.

- `services/game_analyzer.py:parse_clock_data()` parsuje `[%clk H:MM:SS]`
  komentáře z PGN na `ply -> zbývající čas`; bez měření vrací
  `{"status":"clock_data_unavailable"}` (nikdy odhad z time controlu).
- `coaching_base.collect_single_game()` vkládá clock data do **interního**
  coaching výsledku (ne do serializovaného detailed payloadu).
- `prompt_builder` šablona 1 a deterministický report nyní obsahují
  `Časová data (PGN %clk)` / `clock_data_unavailable` — LLM může mluvit o time
  trouble jen z parsovaných dat (pravidlo 7 promptu).
- 4 nové testy (`tests/test_clock_parser.py`); gates: pytest 563 passed,
  Ruff clean, mypy 0/74.

## [2.8] - 2026-11-18

Additive contract iteration over frozen 2.7 (author-approved bump). **No change
to `strength`/`confidence`, no detector or engine change.**

- New `schemas/single_game_v2_compact_2.8.json`; `SCHEMA_V = "2.8"`,
  `SUPPORTED_VERSIONS = ("2.6", "2.7", "2.8")`; 2.7 stays frozen and readable.
- `precision`: `{opening, middlegame, endgame, basis}`. All phase values are
  **null** with `basis: not_calibrated` until labeled outcomes exist — no
  fabricated accuracy (DATA-FABRICATION-001).
- `decisive_moves[]`: `{ply, move, cp, game_impact}` for flags whose impact left
  winning/equal, ranked by `cp`. Fixes the report bias toward the largest raw
  `cp` (7l9g62Eo p77 478 `winning→winning` vs p79 599 `winning→losing`;
  v2xHpqXG p29 vs p39). The deterministic report now applies the same ranking.
- `patterns[].pv_coverage`: measured share of a pattern's plies carrying a PV,
  so an LLM can tell how much of the evidence is actually observable.
- Implementation wave 1 (separate commit `cfa57a4`): decisive-first ordering in
  `services/ide_fallback.py` + `piece_reads.sq` documentation (from-square of
  the forcing SAN inside the PV, not the current board square).
- Gates: pytest **559 passed / 18 deselected**, Ruff clean, mypy 0/74,
  `verify_docs_trimming.py` 11/11 OK. Tests migrated from 2.7 to 2.8 where
  they asserted the emitted version; 2.7 backward-read paths untouched.

## [REVIEW-CROSS] - 2026-11-18

Ověřená integrace cizí analýzy (`3.LLM` pro `v2xHpqXG`) a vlastního čtení `7l9g62Eo`
do `SESSION_HANDOFF` §5. Žádná změna runtime kódu ani schémat; úrovně 0–5 a seznamy
DROP/DEFER zůstávají nezměněny.

- Roadmapa #4 rozšířena na **evidence honesty blok**: `precision`/`pv_coverage`
  + `decisive_moves[]` (priorita `game_impact` před `cp_loss`) + dokumentace
  `piece_reads.sq`. Podklad: `lpDh1fIx`, `v2xHpqXG`, `7l9g62Eo`.
- Roadmapa #5 (Wave 2): Q4 `declined_forcing_move_at_pivot` je nejsilnější kandidát,
  ale **pouze s podmínkou forcing best move** — většina z „7 případů" neprojde D4 gate.
- Zamítnuto jako interpretace: „Stafford výhra = důkaz GAMBIT vektoru" (výsledek
  vysvětluje blunder differential 2:0, použití `game.result` by bylo outcome leakage)
  a „hash 64→128 drift" (adaptivní tabulka podle ply, ověřeno 39/73 ply).
- Registr: `high_value_capture` **2 hry**, `V` **2 hry**; opraveno „B+T" → **C+T**
  u `v2xHpqXG` b34. `rank:null` znovu potvrzen jako poctivý REVIEW-FIX výstup.
- `retry_budget_exhausted` potvrzen i v `7l9g62Eo` (3+1 flagů) — není specifický
  pro extrémní hru `lpDh1fIx`.

## [REVIEW-FIX] - 2026-11-18

Autorizované opravy všech P0/P1 nálezů z `[REVIEW]` + 9 regresních testů
(`tests/test_review_fixes_2026_11_18.py`). **Žádná změna schémat ani kontraktů**
(kromě sémantického vyjasnění `llm.status` v rámci existujících hodnot).

- `report_persister.py:249` — `opponent_pool` nyní volá tool s keyword argumenty
  (`username`, `depth`); dříve nefunkční cesta `persist_report(kind="opponent_pool")`.
- `engine_client.py:59` — `get_engine()` bez argumentu **reuseuje** aktuální hash;
  odstraněno lživé `summary.src` (`h64` label vs reálných 512 MB).
- `game_analyzer.py:878`, `pv_recovery.py:108` — odstraněn fabrikovaný
  `played_rank = len(engine_lines)+1`; mimo multipv zůstává `0` → `rank:null` /
  `rank_not_in_engine_lines` (DATA-FABRICATION-001).
- `srs_engine.py:38` — `retention_rate` se obnovuje ze JSON po restartu.
- `diagnostician.py:68` — „nejhorší zahájení" se řadí podle blunderů (ne počtu her)
  a vyžaduje ≥3 hry.
- `compact_serializer.py:425` — `llm.status`: `all_providers_failed` zůstává
  `failed`, `llm_disabled`/offline ETL je `degraded` (dle 2.4 poznámek a
  `pipeline_status.py`).
- `audit.py:43` — rozpoznává `{status:"error", errors:[...]}`; selhání už není
  auditováno jako `ok`.
- `lichess-mcp.bat` — `-m lichess_analyzer_mcp.server` (dříve neexistující `-m src.server`).
- `workspace_info.py` — živý registry přes `app.list_tools()` (žádný 10-tool fallback),
  platformově resolved Stockfish z `config/engine_identity.json`.
- `verify_engine_identity.py` — neznámý binary už není důvěryhodný (`_hash_ok`).
- `anonymous_session.py:35` — `file_path` omezen na workspace, `utf-8-sig`.
- `kb/writer.py` + `tools/persist_report.py` — KB root přes `LICHESS_KB_ROOT`;
  zápis mimo repo vyžaduje `LICHESS_KB_WRITE=1`.
- Gates: pytest **556 passed / 18 deselected** (9 nových), Ruff clean, mypy 0/74,
  `verify_docs_trimming.py` 11/11 OK.

## [REVIEW] - 2026-11-18

Generální code review + sémantická/logická revize plánů po trimu. Tento záznam
identifikoval defekty a rekalibroval plány; **opravy kódu následovaly v [REVIEW-FIX]
níže** (autor odsouhlasil „vše P0+P1").

- **Decision/contract autorita obnovena:** D13–D35 mají opět závazné znění v
  `AUDIT_INTEGRATION` §12 (dříve jen odkaz do EVIDENCE_DIGEST, který odkazoval
  zpět → kruhová reference). EVIDENCE_DIGEST §8 zůstává evidencí, ne autoritou.
- `SESSION_HANDOFF` §5 rekalibrováno: 7 aktivních položek s acceptance criterion;
  vyřešené/obsoletní (`hash_mb`, `fen 100`, `ph`) odděleny; aspirace rozděleny
  na DROP (FSRS, frontend), DEFER (ELO ETL, SQLite, T3.3, MDL kalibrace) a NE.
- Opraveny rozpory v aktivních docs: test count 536 → **547**, historický „compact
  2.1" v AUDIT opatřen čtecí poznámkou (current = 2.7), `interaction` v D7 označen
  jako neimplementovaný (T3.3), `QUIET_BLUNDER_CP = 200` (ne „fen 100").
- **Hlavní review nálezy (kód, neopraveno v tomto záznamu):**
  - `report_persister.py:249` špatné poziční argumenty → `persist_report(opponent_pool)` nefunguje (P0).
  - `engine_client.py:59` + `game_analyzer.py:564,614` adaptivní hash zapsán do provenance, ale engine běžel na 512 MB → lživé `summary.src` (P1).
  - `game_analyzer.py:879` + `pv_recovery.py:109` fabrikovaný `played_rank` (DATA-FABRICATION-001, P1).
  - `srs_engine.py:38` ztracený `retention_rate` po restartu (P1); `diagnostician.py:68` „nejhorší zahájení" = nejhranější (P1).
  - `llm.status` si v `compact_serializer.py:67-68` a `:430-431` odporuje (P1).
  - `lichess-mcp.bat` volá neexistující `-m src.server`; `workspace_info.py` má zastaralý 10-tool fallback; `verify_engine_identity.py` důvěřuje neznámému binary.
  - Testy: zastaralý `DBCL-20261111-dev` fixture, tautologické engine testy, vacuous KB path testy; `srs_engine`/`llm_client` bez testů.
  - `verify_docs_trimming.py` neskenuje `src/tests/scripts` pro odkazy na archiv (P1 blind spot).

## [DOCS] - 2026-11-18

Documentation trimming and root-state synchronization. **No payload, schema,
detector, or runtime behavior change** - contract versions remain compact 2.7 /
detailed 1.2 / cross-game 1.4 / game_full 1.0 (viz SESSION_HANDOFF).

- `docs/` compressed from **81 artifacts (1 054 KB) to 9 active files (163 KB)**
  (-89 % files, -84 % bytes). 113 historical artifacts moved to `_ARCHIVE/`
  via `git mv` (git history preserved; no hard deletes of tracked content).
- New active docs: `00_DOCS_CONTRACT.md` (read order + authority),
  `01_EVIDENCE_DIGEST.md` (unique root causes, dated measurements, D1-D40
  provenance extracted from the archived era), `02_COACHING_EXEMPLARS.md`
  (4 representative techniques + findings catalogue + anti-patterns).
- `GAME_FULL_1.0.md` content merged into `COMPACT_JSON_FOR_LLM.md` Appendix A;
  historical sections of `AUDIT_INTEGRATION` (§12-12.3) and
  `PATTERN_DISCOVERY_METHODOLOGY` (§7-9, §13-14) moved to the digest/archive.
- Version drift fixed in active docs: title 2.3 -> 2.7, schema path -> 2.7,
  CLI 2.1 -> 2.7, D35 `game_impact` attributed to [2.2] (not 2.7),
  `eval_before_mover_cp` removal attributed to 2.6, U/V event and detector
  counts, stale test/detector figures in `README.md`.
- Auxiliary trimming: 22 unreferenced scripts, 4 superseded schemas (2.3 kept -
  two tests still read it), all 13 `00_STRATEGIE` and 3 old `.session` snapshots
  archived. `data/reports` locally pruned 186 -> 127 files (one newest generation
  per game_id/type); ~240 KB of gitignored local logs/cache removed.
- Root state synchronized: `README.md` and `README_en.md` reflect actual state
  (547 fast tests, 18 tools, 17 patterns, 9 active docs), `.ai_state.json`
  refreshed to HEAD `5bd81a3` with legacy sections preserved under
  `_archived_2026_11_12`.
- New `scripts/verify_docs_trimming.py` (11 assertions, mirror of the GT v2
  `assemble_verify.py` pattern). Gates: pytest **547 passed / 18 deselected**,
  Ruff clean, mypy **0 errors / 74 files**. Verification: **11/11 OK**.
- Commits: `6f2694d` (checkpoint), `f6eaa98` (W1), `4eb9741` (W2),
  `68e460e` (W3), `1af7942` (W4), `5bd81a3` (W5). Push not performed.

## [2.16] - 2026-11-17

Konsolidace pro předání do nové session. Žádná změna payloadu ani detekce.

- Nový předávací artifact `docs/SESSION_HANDOFF_2026-11-17.md`: current
  kontrakty, příkazy, validační vzorek, rozhodnutí, otevřené položky,
  artifact index a pravidla.
- `docs/REFACTOR_PLAN_2026-11-11.md` §11.1 doplněn o stav po [2.15].
- `docs/AUDIT_INTEGRATION_2026-11-13.md` §14 obsahuje rozhodnutí D38–D40.
- Historické audity (`LLM_INPUT_AUDIT`, `CODE_REVIEW_...`, `HANDOFF_V1_3`,
  `HANDOFF_2_5`, `CALIBRATION_2_6`) mají banner s odkazem na current handoff.
- Aktuální dokumenty (`GAME_FULL_1.0`, `PATTERN_DISCOVERY_METHODOLOGY`,
  `CLI_USAGE`, `COMPACT_JSON_FOR_LLM`) aktualizovány na compact 2.7.

Gates beze změny: pytest **536 passed**, Ruff clean, mypy 74 souborů.

## [2.15] - 2026-11-17

Handoff 2.7, vlna 1 (4 položky), validováno na 5 hrách × 2 barvy.
Compact **2.7**, 2.6 zůstává zmrazený a validator ho čte.

### Added

- **`summary.src`** — krátký štítek přesné engine politiky z detailed
  `eval_provenance` (`d14n150k_hash_unknown_cache`, `d14n150k_h64_live`).
- **`flags[].alts`** — jedna rank-2 SAN alternativa pro flagy s sehráno rank ≥ 4
  (bez nového engine callu, bez vymyšleného PV).
- **`piece_reads`** — maximálně jeden nejdůležitější flag s `cp > 100` dostane
  forcing figurku skutečně obsaženou v naměřeném PV (`sq`, `pc`, `role`, `th`).
  Žádné odvozené hrozby; modul `services/piece_reads.py`.
- **`pv_played_unavailable: rank_unknown`** pro `played_rank = null/0` a
  explicitní `rank_not_in_engine_lines` pro matched flagy mimo multipv.

### Verified

10 tool callů (5 her) validuje proti 2.7 + 1.2; chybějící `pv_played_unavailable`
kleslo z 10/10 her na 0. Delta compactu **+50 až +232 znaků** (limit +300).
`pytest` **536 passed**, Ruff clean, mypy **74 souborů** clean.

### Odchylky

- `piece_reads` je omezen na 1 flag a 1 alternativu `alts` kvůli size budgetu;
  plný „monster" narativ z uživatelského příkladu (Rf1 v `hJjXxxvq`) není v PV
  vždy přítomen — publikujeme jen to, co engine skutečně změřil.
- Žádný nový engine call pro rank-4 PV (`rank_not_in_engine_lines` zůstává).
- Wave 2 (Q3/Q4, paired_blunder, U1/U2), Wave 3 (konzistence) a GAMBIT
  nebyly v této iteraci implementovány — vyžadují cross-game validaci.

## [2.14] - 2026-11-17

Kalibrace compactu na 3 hrách / 6 JSONů (první vlna C-1 + C-2).
Compact **2.6**, 2.5 zůstává zmrazený a validator ho čte.

### Added / Fixed

- **C-1 aritmetika**: `flags[].bcp` = D12 anchor `best_eval_mover_cp`.
  Ne-anchor `eval_before_mover_cp` odstraněn; `cp == bcp − eval_after_mover_cp`
  platí 7/7 flagů v kalibračním vzorku (dříve mezera 1–28 cp u 10 flagů).
- **C-2 koučinkový signál**: `patterns[].nm` (krátký název) a `mit`
  (mitigace ≤50 znaků) — žádné holé IDs. Plné znění zůstává v detailed 1.2.
- Validator kontroluje `bcp` aritmetiku a délku `mit`; 2.5 payloady
  (bez `bcp`/`nm`/`mit`) jsou stále přijímány.

### Nezměněno / odloženo

C-3 (`src` v summary), C-4 (`ph`), C-5 (`pv_played` konzistence), C-6/C-7
(`username`, `llm.status`) a C-8 jdou v další vlně. N-1/N-2/N-4 zůstávají
zdokumentovány jako nálezy kalibrace.

### Verified

6 tool callů (`use_llm=false`) validuje proti 2.6 + 1.2; delta compactu
+74 až +177 znaků (limit +200). `pytest` **531 passed**, Ruff clean,
mypy **73 souborů** clean.

## [2.13] - 2026-11-17

Handoff „Schema 2.4 → 2.5“: P0 blokéry pro plnohodnotný LLM koučink.
Detailní verifikace s důkazy z 8 cold re-runů:
`docs/HANDOFF_2_5_VERIFICATION_2026-11-17.md`. Nový detector
`DBCL-20261117-dev`. Compact **2.5** (2.4 zůstává zmrazený a validator ho
čte), detailed 1.2 beze změny kontraktu.

### Fixed (P0)

- **P0-3** `engine_lines[0].eval_cp` je D12 anchor (přesun ranku, když anchor
  byl níž); `best_move_san` pojmenuje tah, ze kterého se měřil `cp_loss`.
  Když anchor == sehráno, `cp_loss = 0` a `best_eval = eval_after`. Vzorec
  `best_eval − eval_after` se nemění. 60/61 flagů má gap ≤ 10 cp.
- **P0-1** Pattern C se nyní emituje i pro celý cluster 3+ flagů
  (`strength = min(total_cp/1000,1)`, `severity high` nad 500).
- **P0-2** Nový pattern **U** (unseen-threat quiet blunder) místo kolizního
  Q1; `severity critical` nad 500 cp. Cross-game detektor `_detect_u`.
- **P0-4** `eval_source` nese přesnou politiku (`stockfish_d14_n150000_h128_live`
  apod.); `hash_mb` se při cache hitu načítá z metadat cache, už ne `null`.

### Fixed (P1)

- **P1-1** `acc_warning` rozlišuje `contains_blunder` / `contains_mistake`
  (kromě existujícího mate outlieru).
- **P1-2** Compact 2.5 odstraňuje aliasy `eval_before`/`eval_after`; validator
  přijímá i 2.4 payloady. Nový `schemas/single_game_v2_compact_2.5.json`.
- **P1-4** Nový pattern **V** (wrong check response) + cross-game detektor.
- **P1-6** Negative cache: HTTP 410 → 24 h, 402 → 1 h, 5xx → 60 s.

### Odchylky

- P1-3 `internal_accuracy_score` ponechán v detailed 1.2 (odstranění by
  vyžadovalo detailed 1.3, handoff povoluje jen bump compactu).
- P0-4 hash je existující adaptivní `h128`/`h256`, ne pevné `h512`.
- P0-3 jediný flag bez `best_move_uci` (`zOk3TnoC` white 41) nelze zarovnat;
  hodnoty zůstávají měřené, ne odhadnuté.
- P2-2 (medián ACPL) odložen jako report-only polish.

### Verified

`pytest` **531 passed**, Ruff clean, mypy **73 souborů** clean. 8 payloadů
validuje proti 2.5 + 1.2; maximální nárůst compactu +90 B (limit +200 B).

## [2.12] - 2026-11-16

P0-9: **fáze 0 uzavřena**. Rozdělení CI na `fast` a `engine`, pinnutý Stockfish
a žádné tiché preskakování testů. Žádná změna payload schémat.

### Added

- `.github/workflows/test.yml` má dva joby: `fast` (Python 3.12, Ruff, mypy,
  `pytest -m "not real_engine"` s coverage) a `engine` (pinnutý Stockfish 18,
  `pytest -m real_engine`). `--strict-markers` je i v `pyproject.toml`,
  takže neznámý marker nebo prázdný výběr znamená červený job.
- **`config/engine_identity.json`** — release `sf_18`, URL a SHA-256 archivu
  `stockfish-ubuntu-x86-64.tar` (`5c6f38b0…`), SHA-256 binárky
  (`7a44d64f…`), očekávaný UCI název `Stockfish 18` a hash lokálního
  Windows BMI2 buildu pro provenienci.
- **`scripts/verify_engine_identity.py`** — ověří UCI `id name` **a** hash
  spustitelného souboru; výstupem je jedna JSON linka do CI logu. Při driftu
  ukončí job s exit 1.
- **`tests/test_engine_identity.py`** — 3 testy konfigurace a přesného
  porovnání identity.

### Fixed

- **Visící engine job**: první CI běh sice zapsal `18 passed`, ale `uv run`
  nevrátil — Stockfish jako potomek držel zděděné stdout/stderr roury a runner
  čekal 21 minut do zrušení. `close_engine()` nyní po 2 s quit handshakeu
  a případném `close()` ověří PID a proces forcibly ukončí; v testech navíc
  session fixture zavře engine ještě před koncem pytestu. Archiv se cachuje
  podle hashu, `curl` má connect/max time a engine job má `timeout-minutes: 12`.

### Verified

Lokálně: fast **521 passed** (bez `test_engine_client.py`), real engine
**18 passed / 11 deselected za 12,8 s** (s lokálním `sf_18` binary, který prošel
verifikací), Ruff clean, mypy **73 souborů** clean. CI: fast job **532 passed /
18 deselected**, engine job **18 passed / 11 deselected**; verifikace vypsala
`stockfish-ubuntu-x86-64`, `uci_name: Stockfish 18`, `hash_ok: true`, `name_ok: true`. `pytest -m real_engine` vrací exit 5, pokud neexistuje žádný
engine test — job tedy nemůže projít „prázdným výběrem“.

## [2.11] - 2026-11-16

LLM input audit na reálných tool calls (4 hry × 2 barvy = 8 payloadů). Kompletní
evidence: `docs/LLM_INPUT_AUDIT_2026-11-16.md`. Nový read-only kontrolor:
`scripts/audit_single_game_output.py` (12 invariantů, 8/8 PASS).

### Fixed

- **Chybějící směr matu v compactu**: `WHIbVLXk` black ply 68 měl
  `game_impact=losing_to_mate`, ale `mate_after` se nepublikoval, přestože to
  dokumentace tvrdila. Compact **2.4** přidává povinné `flags[].mate_after`
  (`for`/`against`; null mimo `*_to_mate`). 2.3 zůstává zmrazený.
- **`--no-llm` vypadalo jako selhání analýzy**: nový `pipeline` blok v detailed
  1.2 i compact 2.4 odděluje `analysis` (complete/partial/failed), `coaching`
  (llm/deterministic_fallback/data_only/failed) a `llm_requested`. Sdílená
  logika v `services/pipeline_status.py`, aby se oba surface nemohly rozejít.

### Documented (beze změny schématu)

- `flags` kolize: detailed = config objekt, compact = pole flagů → v LLM guide
  nová sekce „Aliases and collisions“.
- Ponechané kompatibilní aliasy (`eval_before*`, `accuracy`/`internal_accuracy_score`,
  `strength`/`confidence`/`detection_strength`/`conf`, `cascade_log`/`llm.attempts`,
  `pstatus`/`unclassified[]`, `flags[].patterns`/`patterns[].plie`) se počítají
  jednou; `report` je shrnutí, ne zdroj faktů.

### Verified

8 MCP tool calls (`use_llm=false`, `output_format=both`), 12/12 kontrol PASS na
8/8 payloadů; obě schémata validují. `pytest` **518 passed**, `ruff` clean,
mypy **73 souborů** clean.

## [2.10] - 2026-11-16

Ověření externího generálního code review (3. LLM, `e136fee`) před P0-9.
Kompletní verifikační tabulka: `docs/CODE_REVIEW_2026-11-16_VERIFICATION.md`.
Auditní HEAD předcházel [2.9], takže jeho P0-4 a „compact 2.2 stable“ jsou
**stale** — P0-4 je hotové a current artefakt je compact 2.3.

### Fixed

- **P-03 `max_games` doc vs clamp**: 6 toolů uvádělo `5-50`, ale clamp byl
  `5..999`. Docstringy sjednoceny na skutečný hard clamp; `persist_report`
  (průchozí) zdokumentován stejně. Nový `tests/test_tool_param_contract.py`
  porovnává deklarovaný rozsah s clampem, aby se rozdíl nevrátil.
- **P-04 falešná FSRS informace**: `services/srs_engine.py` tvrdil 3parametrický
  model a gradient descent, ale `review_card()` je SM-2-like násobič. Docstring
  i README nyní říkají „SM-2-like, FSRS neimplementován“ a jmenují známé limity
  JSON prototypu. Algoritmus se nezměnil.
- **README drift**: statusní řádek má datum 2026-11-16, aktuální počty testů
  (515 fast / 11 engine), seznam schémat a žádné zastaralé `v4: 7ce7f61`;
  historická poznámka o 254 testech je označena jako snapshot z 11. 11.

### Nezměněno (záměr)

`game_full` 1.0 zůstává merge vrstva, `run_id` zůstává policy fingerprint (DB
identita až Phase 1), `status` 1.2 zůstává, žádný nový pattern ani frontend.
Auditní návrhy L-01/L-02/L-03/DB-01 patří do Phase 1–2, ne do P0-9.

### Verified

`pytest` **515 passed**, `ruff` clean, mypy **72 souborů** clean.

## [2.9] - 2026-11-16

P0-4 z originálního plánu refaktoru: **tři pojmenované dimenze confidence**
(D37, `docs/REFACTOR_PLAN_2026-11-11.md` §11). Cross-game schema 1.4, detailed
1.2 kontrakt a admission gate se nemění; změny jsou aditivní. Compact 2.2 je
zmrazený, nový artefakt je `schemas/single_game_v2_compact_2.3.json`.

### Added

- **Detailed 1.2**: každý pattern nese `detection_strength` (= `strength`),
  `evidence_support` (podíl flagovaných tahů pokrytých patternem, basis
  `flagged_moves_in_game` + jmenovatel `evidence_support_n_units`),
  `behavioral_confidence = null` s `behavioral_confidence_reason =
  "not_calibrated"` a `confidence_kind = "detection_strength"`. Plus
  `analysis.confidence_dimensions` s jedním vysvětlením pro celý payload.
- **Compact 2.3**: `patterns[].support` (nullable) a top-level
  `confidence_dims`; `conf` zůstává ordinální detection strength. `SCHEMA_V =
  "2.3"`, validátor a testy ve stejné iteraci.
- **`services/confidence_dims.py`** — sdílená čistá logika (bez engine/IO) pro
  oba formáty; support se nikdy neodhaduje, chybí-li jmenovatel.

### Záměrně nezměněno

- `strength` / `confidence` zůstávají 0–1 aliasy (D26/D27); cross-game 0–100
  zůstává nedotčené. `behavioral_confidence` se nevymýšlí — kalibrace
  mechanismů je fáze 3.
- 2.2 payloady se už negenerují, soubor schématu 2.2 se nemění.

### Verified

`pytest` **513 passed**, `ruff` clean, mypy **72 souborů** clean.

## [2.8] - 2026-11-16

P0-6 / T-02 z originálního plánu refaktoru (§4 `docs/REFACTOR_PLAN_2026-11-11.md`):
**provenance eval čísel**. Rozhodnutí D36 je zdokumentováno v §11 téhož plánu
(spolu se stavem všech P0 položek). Kompakt 2.2 a cross-game kontrakty se
nemění; detailed 1.2 dostává jen aditivní pole.

### Added

- **`analysis.run_id`** — 16 hex deterministický otisk politiky analýzy (depth,
  mode, nodes cap, threads, detector verze, schema verze). Stejná politika dává
  stejné ID; engine identita do něj nepatří, protože při cache hitu se engine
  nespustí (patří do `analysis_runs`, fáze 1).
- **`analysis.eval_provenance`** — počet měřených tahů, `anchor_coverage` a
  rozdělení podle `cp_loss_basis` / `eval_source`. N-03 (97,8 % tahů bez D12
  anchoru) je tak měřitelné **na úrovni jedné hry**, ne jen jako korpusové
  tvrzení v dokumentaci.
- **`flagged_moves[].cp_loss_basis` / `eval_source`** — `best_eval` jen při
  přítomném a rekonstruujícím anchoru, jinak `unknown`; zdroj `stockfish` /
  `cloud` / `unknown`. Basis se odvozuje z publikovaného anchoru, aby seděl
  s `eval_provenance`; zdroj odvodit nelze, proto legacy cache dostane `null`,
  ne odhad.
- **`services/eval_provenance.py`** — čistý modul (bez engine/IO) se sdílenou
  klasifikací; `engine_client` označuje zdroj už při měření, `MoveAnalysis` ho
  ukládá do cache.

### Záměrně nezměněno

- Compact 2.2: P0-6 říká, že compact zachovává potlačení nekonzistentního eval
  páru a explicitní provenance nese detailed. Žádný schema bump.
- `cp_loss` se nepřepočítává a `best_eval` se nedoplňuje do starých cache;
  chybějící data se označí, ne vyfabrikují (DATA-FABRICATION-001).

### Verified

`pytest` **505 passed**, `ruff` clean, mypy **71 souborů** clean.

## [2.7] - 2026-11-15

Integrace třetího auditu (`WHIbVLXk`, Caro-Kann B12) + **compact 2.2**.
Rozhodnutí D31–D35 v `docs/AUDIT_INTEGRATION_2026-11-13.md` §12.3. Cross-game
schema 1.4, detailed 1.2 a admission gate beze změny verze; všechny změny
payloadu jsou aditivní. `schemas/single_game_v2_compact.json` (2.1) zůstává
zmrazený, nový artefakt je `schemas/single_game_v2_compact_2.2.json`.

### Added

- **D35 compact 2.2**: `flags[].game_impact` je **povinné** (nullable) —
  autorovo „compact musí mít game_impact“. `SCHEMA_V = "2.2"`, validátor i
  testy ve stejné iteraci. 2.1 payloady se už negenerují, ale soubor schématu
  se nemění.
- **D31 `mate_missed` + `mate_via`** (detailed i compact): nejlepší linie matuje
  pro hráče v N tazích a sehráno tah ne. `WHIbVLXk` white ply 67 `Bf5+`:
  `mate_missed: 10`, `mate_via: "e6+"`, `game_impact: winning_to_winning` —
  `cp_loss 9027` je ztráta relativně k matu, ne katastrofa.
- **D32 `pv_played` / `pv_played_unavailable`** (detailed pole per flag, compact
  mapy `ply -> PV`): engine pokračování **po sehráno tahu** z téhož multipv
  search, max 3 tahy v compactu. Není to soupeřova skutečná odpověď a je to tak
  i dokumentováno. `clusters[].plies` doplňuje seznam plies k
  `{from,to,count,total_cp}`.
- **D33 `analysis.accuracy_warning` / `summary.acc_warning`**:
  `contains_mate_level_outlier`, když některý flag má `mate_missed` nebo
  `|eval_after| >= 9000`. Lineární `accuracy` se nepřepočítává.
- **D34 report a prompt používají `game_impact`**: `_move_lines` tiskne
  `impact=…` a `mate_missed=N via SAN`; `ide_fallback._critical_moments`
  je vypisuje v `- Kritický moment:`. White `WHIbVLXk` report už neříká
  „9027 cp“ bez kontextu, ale `[winning_to_winning, mate missed: 10 via e6+]`.
- **`services/game_impact.py`**: prahy a klasifikace na jednom místě pro
  detailed i compact (dřív jen v `tools/coaching_single_game.py`).

### Rejected (audit claims)

- **`mate_after: "for_missed"`**: `mate_after` popisuje mat **po** tahu
  (`for`/`against`); zmeškaný mat je jiný fakt a má vlastní pole `mate_missed`.
- **Pattern Q1 pro `quiet_positional`**: 11/17 flagů má `cp <= 149`,
  `quiet_blunder` (D13) platí až > 200 cp; behaviorální pattern bez měřitelné
  hranice porušuje D4.
- **`accuracy_excluding_outliers`**: druhý práh bez definice; warning (D33)
  je měřitelný a nemění publikovanou metriku.
- **`time_control` per move**: `%clk` se zatím neparsuje (T-16 / D23).

### Verified

`scripts/coach_single.py WHIbVLXk --no-llm --quiet` (obě barvy, 1.2 s z cache):
oba payloady validují proti 2.2 i 1.2 schématu; `mate_missed`/`mate_via` u white
ply 67 v compact i detailed; `acc_warning` na obou stranách; `pv_played_unavailable`
white `63` a black `66` = `rank_not_in_engine_lines`; clustery
white `59–63` (`plies [59,61,63]`) a black `62–68` (`plies [62,64,66,68]`).

## [2.6] - 2026-11-15

Integrace třetího auditu JSON výstupu (`S23Qm04u`, schema 2.1 + dual
perspective). Rozhodnutí D26-D30 v `docs/AUDIT_INTEGRATION_2026-11-13.md` §12.2.
Cross-game schema 1.4, compact 2.1 a admission gate beze změny; všechny změny
payloadu jsou aditivní (jediná výjimka je oprava jednotky, viz D26).

### Fixed

- **D26 `confidence` v detailed 1.2 je zpět 0-1.** `[2.5]` publikovalo 0-100,
  což porušuje `schemas/single_game_v1.2.json` (`patterns.items.confidence`
  má `minimum: 0, maximum: 1`) a rozešlo se s compact `conf: 0.48`. Detailní
  `confidence` = `strength` = 0-1; compact `conf` = 0-1 beze změny;
  cross-game (`schemas.py`) zůstává 0-100. Audit BUG-1/BUG-2 byl správný.
- **D27 `report_persister` normalizuje podle artefaktu.** `single_game`
  (0-1) se v reportu tiskne jako procenta a do KB slim jde 0-1; cross-game
  kindy (0-100) se nemění. Normalizace je `kind`-based, nikdy podle velikosti
  čísla (`1.0` by bylo ambiguous).

### Added

- **D15/T-18 `game_impact`** v detailed `flagged_moves[]`: 9 přechodů znaménka
  (`winning_to_winning` ... `losing_to_losing`) s dokumentovanou mrtvou zónou
  ±100 cp, plus 3 matové přechody (`*_to_mate`). `mate_after` (`for`/`against`)
  říká, kdo matuje. Vynucený mat po tahu se nikdy nepublikuje jako
  `losing_to_losing` (P0-3). `null` = eval neměřen. Detailed-only (D15).
- **D28 `timings.llm_skipped` + `timings.llm_skip_reason`**: `llm_s: 0.0` už
  není ambiguous. Reason je `llm_disabled`, `no_provider_configured`,
  `no_api_key`, `negative_cache`, `unknown_provider`,
  `all_providers_skipped` nebo `pipeline_error`. Deterministický fallback
  v `cascade_log` se nepočítá jako pokus o providera.
- **D13/T-19 `why=quiet_blunder`**: tichý tah (bez capture, bez šachu, ne
  v šachu) s `cp_loss > 200` a bez motivu. Prah je konstanta
  `pattern_detector.QUIET_BLUNDER_CP`. Žádný nový pattern ID.
- **D14/T-20 `why=check_escape`**: neberoucí královský tah v šachu. J zůstává
  "piece block, nikdy king move" (D11). Žádný nový pattern ID.
- **N-06** `schemas/single_game_v2_compact.json` a
  `schemas/single_game_v1.2.json` rozšiřují enum `why` / `unclassified_reason`
  o `quiet_blunder` a `check_escape`. Schema i validátor jdou spolu.

### Rejected (audit claims)

- **BUG-3** `best_eval_mover_cp` vs `engine_lines[0].eval_cp`: nejde o stejné
  měření. `best_eval` je eval **po** nejlepším tahu (post-move search),
  `engine_lines[]` pochází ze samostatného `analyze_position_ex(multipv=3)` na
  pozici **před** tahem. Srovnatelný pár je `eval_before_mover_cp` vs
  `engine_lines[0].eval_cp` (naměřeno max 36 cp). Dokumentováno, hodnota se
  nemění.
- **BUG-4** `patterns_meta.unclassified_reasons` v compact: compact už nese
  `unclassified[]` s `{ply, class, cp, why}` pro každý flag. Agregace by
  vyžadovala compact 2.2 (schema má `additionalProperties: false`).
- **BUG-6** `eval_before` == `eval_before_mover_cp`: záměrný alias 1.2 (D18),
  ne duplicita k opravě.

## [2.5] - 2026-11-15

Integrace handoffu v1.2 → v1.3 (11 her): `docs/HANDOFF_V1_3_INTEGRATION_2026-11-15.md`,
rozhodnutí D13–D25 v `docs/AUDIT_INTEGRATION_2026-11-13.md` §12. Cross-game
schema 1.4, compact 2.1 a admission gate beze změny; `game_full` 1.0 beze
změny. Všechny změny payloadu jsou aditivní.

### Added

- **D25** detailed `flagged_moves[].fen_before` — pozice, ze které byl tah
  zahrán. FEN už je v cache, takže to nestojí žádný engine call; prázdný
  string = FEN není změřen (nikdy se nedomýšlí).
- **D25** detailed `game` blok: `player_name`, `opponent_name`,
  `player_rating`, `opponent_rating`, `time_control`, `date`, `url`,
  `opening`, `opening_eco`, `result`. Anonymní placeholdery (`Anonymous`,
  `?`, `-`) se publikují jako prázdný string, neznámý rating jako `null`
  (nikdy `0`).
- **D24** CLI `--color` má default `""` = obě barvy. `scripts/coach.py` i
  `scripts/coach_single.py` vrací klíčovaný objekt `{"white": …, "black": …}`,
  takže jedna hra = jeden JSON s oběma perspektivami.
- **D24** `scripts/coach_single.py --format compact|detailed|both`
  (default `both`) a `--no-llm`.

### Changed

- **D18/N-02** `confidence` mělo mít jednu jednotku na artefakt. `[2.5]`
  publikovalo v detailed 1.2 hodnotu 0–100; to bylo **chybné** (porušovalo
  `schemas/single_game_v1.2.json`) a `[2.6]` je vrací na 0–1 (D26). `strength`
  zůstává 0–1 (ordinální síla, nikdy pravděpodobnost). Compact 2.1 `conf`
  zůstává 0–1 (zmrazená schema), cross-game `confidence` 0–100.
- **D24** `scripts/coach_single.py`: chyba pipeline je chybová zpráva na
  stderr + exit 1, **nikdy** validně vypadající prázdný JSON. Neznámý
  `--username` u PGN je chyba, ne tichý přepis na druhou barvu.
- **D24** `scripts/coach.py` dokumentace: compact 2.1, ne 2.0.

## [2.4] - 2026-11-14

Integrace auditu 2026-11-13 (Tier 1–3) + D12. Rozhodnutí a acceptance:
`docs/AUDIT_INTEGRATION_2026-11-13.md`. Cross-game schema 1.4, compact 2.1
a admission gate beze změny; všechny změny v detailed payloadu jsou aditivní.

### Added

- **D12 `best_eval_mover_cp`** v detailed `flagged_moves[]`. `cp_loss` se měří
  proti nejlepšímu tahu, ne proti `eval_before`: platí
  `cp_loss = max(0, best_eval_mover_cp - eval_after_mover_cp)`. `null` =
  neměřeno (legacy cache, cloud eval). Porušení loguje
  `ANOMALY_CP_LOSS_NOT_RECONSTRUCTIBLE`.
- **D9/T2.1** `eval_before_mover_cp` / `eval_after_mover_cp` (legacy
  `eval_before` / `eval_after` zůstávají jako aliasy).
- **T2.2** `player_moves_total`, `game_plies_total`, `opponent_moves_total`;
  `moves_total` je deprecated alias pro plies hráče.
- **T3** `game_full` 1.0: `services/timeline.py`, `schemas/game_full_v1.0.json`,
  CLI `--format game-full`.
- **T3.0** `mode` (`fast`/`deep`) v `lichess_analyze_game`, sdílená policy
  s coachingem.
- **T1** `services/color_contract.py`: `INVALID_COLOR`, `COLOR_UNDETECTED`.

### Changed

- **T2.4** T → `tactical_shaped_move_error` (jen label, pattern ID beze
  změny); `THRESHOLD_TACTICAL_SHAPED_CP`.
- **T1.4** `DETECTOR_VERSION = DBCL-20261113-dev`; J má jeden predikát
  (blokování figurou, královský ústup J nespustí).
- **T2.3** prompt: `insufficient_evidence`, `clock_data_unavailable`.

### Removed

- `max_time_dual` z `config/depth.py` (mrtvá konfigurace, nikdo ji nečetl).

## [2.3] - 2026-11-12

P0-7 (unclassified flagged moves) + P0-8 (compact schema 2.1). Bez nových
pattern ID a bez nových MCP toolů. D4: tichý blunder = explicitní
`unclassified` stav s důvodem, ne nový pattern bez kalibrace (GT-070/P54).

### Added

- **P0-7 coverage.** `pattern_detector.scan_single_game()` vrací
  `(patterns, coverage)`; `detect_single_game()` zůstává list-only wrapper.
  Každý flagged tah (blunder/mistake/inaccuracy) má právě jeden záznam
  `{pattern_status, unclassified_reason, pattern_ids}`.
- **Důvody unclassified** (`models/pattern.py`): `quiet_positional`,
  `forcing_move_unexplained`, `capture_unexplained`,
  `mechanism_not_identified`, `evidence_gap` (jen tah bez SAN textu),
  `not_classified` (jen legacy payloady). Důvod popisuje měřený tvar tahu,
  ne mechanismus.
- **Detailed kontrakt 1.2** (`schemas/single_game_v1.2.json`):
  `flagged_moves[].pattern_status` + `unclassified_reason`,
  `patterns_meta.coverage` + `unclassified_reasons`, top-level `unclassified`.
- **Compact 2.1** (`schemas/single_game_v2_compact.json`): `flags[].pstatus`
  + `why`, top-level `phase_method`, povinné `patterns_meta`
  (`scope`, `cross_game_suppressed`, `reason`, `coverage`), top-level
  `unclassified`. Validátor kontroluje aritmetiku coverage i coupling
  matched => `patterns`, unclassified => `why`.
- **Prompt** (`prompt_builder`): šablona má "Nezařazené chyby" a pravidlo
  nevymýšlet mechanismus.
- **`scripts/measure_pattern_coverage.py`**: offline měření na cache
  (dedup game_id+color, nejhlubší analýza, bez engine/sítě).

### Measured (2026-11-12, cache)

| Metrika | Hodnota |
|---|---|
| soubory / hry po dedupu | 282 / 259 |
| flagged tahy | 2137 (blunder 220, mistake 454, inaccuracy 1463) |
| matched | 375 (17,5 %) |
| unclassified | 1762 (82,5 %) |
| blunder matched | 124/220 (56,4 %) |
| mistake matched | 148/454 (32,6 %) |
| inaccuracy matched | 103/1463 (7,0 %) |
| quiet_positional | 1523 (86,4 % unclassified) |
| forcing_move_unexplained | 148 (8,4 %) |
| capture_unexplained | 91 (5,2 %) |
| flagged s best_move_san | 276/2137 (12,9 %) |

Nález: absence PV je globální vlastnost cache/payloadu (12,9 %), ne tvar tahu.
Proto `evidence_gap` není první větev klasifikace (jinak 88 % důvodů), ale
guard pro tah bez SAN; kvalita podkladu se reportuje zvlášť.

### Tests

263 passed (bez `tests/test_engine_client.py`), z toho 15 v
`tests/test_pattern_coverage.py` a 1 validace detailed payloadu proti
`schemas/single_game_v1.2.json`. `tests/test_engine_client.py` 13/13
prochází, ale proces po summary visí (REVIEW-EXIT-HANG, nesouvisí s P0-7/8).

## [2.2] — 2026-11-10

v4: tři P0 bugy blokující LLM narativ + overhead při cache hitu. Bez změny
schématu 1.1, bez nových MCP toolů, bez nových CAND-* položek.

### Fixed

- **FIX-027 — mate score.** `EngineLine.mate_in` (`models/analysis.py`),
  mapování `mate` v `_engine_lines_to_dicts` a v konstrukci `EngineLine`,
  `"mat v N"` / `"mat v N proti hráči"` v `_build_explanation`; compact
  `flags[].mate_in` jen pro bludery (`compact_serializer._flag`, validace,
  JSON Schema 2.0). Odstraněn `"?"` v explanation u matové linie.
- **FIX-023 — cp_loss vs eval invariant.** Nový
  `services/eval_consistency.py` (`CP_EVAL_TOLERANCE_CP = 50`,
  `eval_invariant_holds`, `eval_delta`). `game_analyzer` loguje
  `ANOMALY_CP_EVAL_MISMATCH` s původními hodnotami; compact vynechá
  `eval_before`/`eval_after`, pokud pár odporuje `cp`. Detailed payload
  ponechává raw hodnoty.
- **FIX-021 — weakest phase.** `coaching_single_game._phase_breakdown` dělí
  fáze na slabé a čisté (`flagged == 0` a ACPL `0.0`/`null`), slabé řadí podle
  ACPL desc (tie-break flagged desc); `ide_fallback` vypíše
  `- Čisté fáze: …`, případně `- Žádná slabá fáze — všechny fáze bez chyb.`
- **FIX-028 — cache-hit overhead.** `refresh_cached_analysis` uloží PV
  obnovenou `recover_missing_pv` do existující cache; cache hit už znovu
  nespouští engine retry.

### Verified (measured)

| Kontrola | Výsledek |
|---|---|
| `FVhqtv1S` ply 75 `engine_lines[0]` | `mate_in: 3`, `eval_cp: null` |
| `FVhqtv1S` ply 75 explanation | `mat v 3`, žádný `"?"` |
| `FVhqtv1S` compact ply 75 | `mate_in: 3` (handoff čekal 5 — viz odchylky) |
| `FVhqtv1S` ply 89 | `eval_before`/`eval_after` vynechány |
| Log FIX-023 | `ANOMALY_CP_EVAL_MISMATCH ply=89 cp_loss=237.0 eval_before=638 eval_after=682 eval_delta=-44.0` |
| `FVhqtv1S` report | endgame 438.7 první, žádná čistá fáze |
| `WpQOkpc0` report | weakest = opening 114.3; middlegame (`0.0/0`) jen v „Čisté fáze" |
| `FVhqtv1S` cache hit | `overhead_s 0.316`, `total_s 0.318` |
| `WpQOkpc0` / `bRBSphxo` cache hit | `overhead_s 0.284` / `0.443`, `total_s 0.286` / `0.445` |

### Odchylky

- **`mate_in` = 3, ne 5.** Stockfish v aktuální cache vrací `mate 3` pro
  `Qf4+` (PV `Qf4+ Qf6 Qxf6+ Kg8 Re8#` = mat na 3. tahu bílého). Hodnota
  z engine se nepřepisuje na 5 jen kvůli očekávání v handoffu.
- **`bRBSphxo` endgame závisí na perspektivě.** Hráč `systeq` hrál černého:
  endgame je čistá fáze (`ACPL 0.0`, 0 flagů), celkové ACPL 35.0. Hodnoty
  `ACPL 9565.0`, 1 flag a compact 3289 znaků pocházejí z analýzy bílého
  (`Hennessy3`, soupeř), tedy z opačné perspektivy. Handoff očekával `0,0`
  pro hráče správně; čísla 9565/3288 nejsou jeho slabina.

### Tests

- Suite: **193 passed** (`pytest tests -q --ignore=tests/test_engine_client.py`).
- Nové: `tests/test_mate_score.py`, `tests/test_eval_consistency.py`,
  `tests/test_cache_refresh.py`; rozšířené `tests/test_compact_serializer.py`
  a `tests/test_deterministic_report.py`; `test_engine_client.py::TestAnalyzePositionMate`.

## [2.1] — 2026-11-10

### Added

- **FIX-014 — PV recovery.** `services/pv_recovery.py` znovu požádá engine o
  engine lines pro blunder/mistake, kterému je deadline vyprázdnil. Retry má
  vlastní 15s timeout, 64 MB hash a max. 3 pozice. Když selže, compact JSON
  publikuje `pv_unavailable[ply]` s důvodem (`engine_timeout`, `engine_error`,
  `no_engine_lines`, `engine_lines_empty`, `retry_budget_exhausted`, `no_fen`)
  místo tichého vynechání.
- **FIX-015 — eval fields.** `flags[].eval_before` / `eval_after` se emitou pro
  `cp > 200` nebo class blunder/mistake. LLM tak nemusí odvozovat swing, který
  neměřený.
- **FIX-020 — username.** `game.username` se plní z `full.username` nebo
  `meta.player_name`; anonymní hry klíč nemají (placeholder `Anonymous` se
  nikdy nepublikuje). Neznámé PGN datum (`????.??.??`) se také vynechá.
- **CAND-E — patterns per flag.** `flags[].patterns` nese ids patternů, jejichž
  evidence obsahuje daný ply.
- **CAND-F — clusters.** Top-level `clusters` shrne ≥ 3 po sobě jdoucí vlastní
  flagy (krok 2 ply) jako `{from, to, count, total_cp}` — hypotéza časového
  tlaku, ne diagnóza.

### Changed

- **Report budget 1200 → 900 znaků** a deterministická preambule
  („Coaching Report (deterministický souhrn)…") se v compact JSON zahazuje;
  fakt, že LLM nebyl použit, už nese `llm.status`. Clip volí maximální bezpečnou
  hranici věty/odstavce, jinak report vynechá.
- **Schéma `schemas/single_game_v2_compact.json`** rozšířeno o výše uvedené
  klíče a explicitní null/omission politiku v popisech.
- **MCP tool `lichess_coaching_single_game`** nově používá stejný PV recovery
  jako CLI; `report_persister` a starší skripty volají `output_format="detailed"`,
  aby se jejich kontrakt 1.1 nezměnil.

### Verified (measured, ne odhad)

| Hra | Compact size | Flags | PV | Clusters | `pv_unavailable` |
|---|---:|---:|---:|---:|---|
| `FVhqtv1S` (white) | **4400** chars | 17 | 13 | 2 | žádné |
| `NxKgE4l8` (white) | **2292** chars | 6 | 6 | 0 | žádné |
| `lxO3gwd3` (black) | **1852** chars | 4 | 4 | 0 | žádné |

`FVhqtv1S` je primární regrese s limitem 4500 znaků. PV se podařilo obnovit pro
plies 75, 87 a 89 (blunder + 2 mistakes), které měly ve plném JSON
`engine_lines: []`. Všechny tři výstupy prošly `validate_compact` i
`jsonschema.validate` proti souboru schématu.

## [2.0] — 2026-11-10

### Changed

- **Compact JSON 2.0 je výchozí výstup** `lichess_coaching_single_game`
  (`output_format="compact"`). Schema 1.1 je opt-in jako `"detailed"`.
  `"both"` vrací `{"compact": …, "detailed": …}`. `"full"` zůstává deprecated
  alias pro `"detailed"` s warningem do logu.
- **Nový jednotný CLI `scripts/coach.py`** pro hru podle ID, lokální PGN i
  dávku posledních N her hráče. JSON jde na stdout/`--out`, progress a agregát
  na stderr. Exit kódy: 0 ok, 1 validace, 2 I/O, 3 engine, 4 síť.
  `--format compact|detailed|both`; batch podporuje jen `compact`.
- **Deprecated skripty** `pgn_to_compact.py`, `analyze_single_game.py`,
  `run_single_game_offline.py` a `coach_single.py` zůstávají funkční jako shimy
  nad `coach.py`, ale tisknou deprecation warning na stderr.

### Fixed

- FIX-016 null politika sjednocena: `rank: null` = neměřeno, `motif` se
  vynechává, eval fields mimo okno se vynechávají, ACPL fáze bez měření je
  `null`.
- FIX-017 validace `output_format`; neplatná hodnota vrací error envelope 1.1
  místo pádu pipeline.

### Tests

- Suite: **178 passed** (`pytest tests -q --ignore=tests/test_engine_client.py`).
- Nové soubory: `tests/test_coach_cli.py`, rozšířené
  `tests/test_compact_serializer.py` a `tests/test_compact_tool.py`.
