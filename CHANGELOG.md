# Changelog

Všechny změny formátu a pipeline. Verze odpovídají kontraktu compact JSON /
single-game pipeline, ne balíčku `0.1.0` (ten zůstává beze změny).

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
