# Changelog

Všechny změny formátu a pipeline. Verze odpovídají kontraktu compact JSON /
single-game pipeline, ne balíčku `0.1.0` (ten zůstává beze změny).

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
