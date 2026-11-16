# Changelog

Všechny změny formátu a pipeline. Verze odpovídají kontraktu compact JSON /
single-game pipeline, ne balíčku `0.1.0` (ten zůstává beze změny).

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

Lokálně: fast **521 passed**, real engine **18 passed / 11 deselected za 12,8 s**
(s lokálním `sf_18` binary, který prošel verifikací), Ruff clean, mypy
**73 souborů** clean. `pytest -m real_engine` vrací exit 5, pokud neexistuje žádný
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
