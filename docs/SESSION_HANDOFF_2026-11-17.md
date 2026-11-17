---
title: Session handoff — lichess-mcp-analyzer (konsolidace 2026-11-17)
status: CURRENT STATE / PŘEDÁVACÍ ARTIFACT
repo: outpost2026/lichess-mcp-analyzer
branch: main
contracts: compact 2.7 | detailed 1.2 | cross-game 1.4 | game_full 1.0
detector: DBCL-20261117-dev
last_feature_release: 2.15
last_consolidation: 2.16
---

# Session handoff — aktuální stav pipeline

Tento dokument je **vstupní bod pro novou session**. Niže jsou ověřená fakta,
ne plány. Historické audity mají v čele banner odkazující sem; neměň je.

## 0. Rychlý start nového agenta

```powershell
cd C:\Users\PC\Documents\Repozitar_Dev\_github\lichess-analyzer-mcp
$env:PYTHONIOENCODING='utf-8'
git status --porcelain
git rev-parse --short HEAD
git log --oneline -5

# gates
.\.venv\Scripts\python.exe -X utf8 -m pytest tests/ -q --ignore=tests/test_engine_client.py
uv run ruff check src/ tests/
uv run python -m mypy src/ --ignore-missing-imports
.\.venv\Scripts\python.exe -X utf8 -m pytest tests/test_engine_client.py -m real_engine -q
```

CI: dva joby `fast (no engine)` a `engine (pinned Stockfish 18)`; oba musí být
zelené. `gh run list --limit 3`.

## 1. Co funguje (ověřeno, neregresovat)

| Vrstva | Stav |
|---|---|
| Lichess/PGN import, cache, depth/node budget | funkční |
| Stockfish analýza, D12 anchor, P0-3 zarovnání `engine_lines[0]` | funkční, gap 0 |
| Deterministické patterny B/C/J/R/S/T/U/V + `unclassified` důvody | funkční |
| Cluster Pattern C pro 3+ flagů, `clusters[].plies` | funkční |
| Compact 2.7 + detailed 1.2, validace obou schémat | funkční |
| `cp = bcp − eval_after_mover_cp` v compactu | 7/7 ve vzorku |
| `acc_warning` (mate/blunder/mistake), `pipeline`, `confidence_dims` | funkční |
| `--no-llm` = deterministický fallback, `llm_requested=false` | funkční |
| CI fast/engine split, pinned SF18 (hash + UCI), `--strict-markers` | funkční |

## 2. Kontrakty a klíčová rozhodnutí

- **Compact 2.7** (`schemas/single_game_v2_compact_2.7.json`) je current.
  Starší soubory 2.2–2.6 jsou zmrazené; validator čte předchozí verzi
  (`SUPPORTED_VERSIONS = ("2.6", "2.7")`).
- **Detailed 1.2** zůstává pro debug/cross-game; aliasy `eval_before`/
  `eval_after`, `internal_accuracy_score` tam stále jsou.
- `bcp` = D12 anchor; ne-anchor `eval_before_mover_cp` odstraněn v 2.6.
- `nm`/`mit` v patterns (krátký název + mitigace ≤50 zn., plná verze v detailed).
- `summary.src` = exact engine policy; `alts` = rank-2 SAN pro rank ≥ 4;
  `piece_reads` = forcing figurka z naměřeného PV (max 1 ply, `cp > 100`);
  `pv_played_unavailable` zahrnuje `rank_unknown`.
- `run_id` je **config fingerprint**, ne per-run DB identita (D02 auditu).
- Detektor verze `DBCL-20261117-dev`; nová pattern ID U/V, protože Q1/Q2
  jsou obsazené (D13). Rozhodnutí D38–D40 v `AUDIT_INTEGRATION` §14.

## 3. Příkazy pro výstup

```powershell
# full JSON = compact 2.7 + detailed 1.2, obě barvy (výchozí)
.\.venv\Scripts\python.exe -X utf8 scripts\coach_single.py zOk3TnoC

# jen compact
.\.venv\Scripts\python.exe -X utf8 scripts\coach_single.py zOk3TnoC --format compact --color both

# jeden tool call (pouze white|black)
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_coaching_single_game `
  --args '{"game_id":"zOk3TnoC","color":"white","output_format":"both","use_llm":false}' `
  --out data\reports\single.json
```

Výstupní adresář: `data\reports\` (gitignored). Chyba = stderr + exit 1,
nikdy validně vypadající prázdný soubor. `--color ""` je **CLI režim** obou
barev; MCP tool `color:""` vrací `INVALID_COLOR`.

## 4. Validační vzorek a důkazy

Hry: `RhkEoVUT`, `WxfSvX4y`, `0yeUi5EO`, `yXmiCYss`, `hJjXxxvq`
(+ baseline `WHIbVLXk`, `PbOhjKa8`, `QxL4Tr8u`, `zOk3TnoC`).

- 10/10 payloadů validuje proti compact 2.7 + detailed 1.2.
- Aritmetika `bcp − eval_after = cp`: 7/7 měřitelných flagů.
- Chybějící `pv_played_unavailable`: 10/10 → 0/10 souborů.
- Pattern C: `yXmiCYss` white freq 4, `hJjXxxvq` black freq 5.
- Delta compactu 2.7 oproti 2.6: **+50 až +232 znaků** (limit +300).
- Gates: pytest **536 passed**, Ruff clean, mypy **74 souborů** clean,
  engine job 18 passed s pinned `Stockfish 18`.

## 5. Otevřené položky (nejsou implementované)

Z handoffu 2.7 (§6, pořadí):

1. **Vlna 2** — Q3 `endgame_king_activity_error`, Q4
   `exchange_avoidance_at_pivot`, `paired_blunder`, rozdělení U na U1/U2.
   Podmínka: cross-game validace na ≥3 hrách, `behavioral_confidence:
   not_calibrated`.
2. **Vlna 3** — `ph` per flag, `username: ""` v detailed, sjednocení
   `llm.status` (`failed` vs `degraded`), `hash_mb` 64 vs 512 v dokumentaci,
   threshold `fen 100` vs `eval_after 200`, diakritika v mitigacích.
3. **GAMBIT vektor** — experimentální; depth 14 hodnotí gambitové tahy jako
   chyby (`yXmiCYss` 3 `d4`, 5 `c3`).
4. **Fáze 1 plánu** — SQLite, migrace, `analysis_runs`, `policy_fingerprint`
   odděleně od DB `analysis_run_id`; žádný frontend dřív než source of truth.
5. P1-3 (`internal_accuracy_score`) a P1-4 (`check_escape` jako pattern)
   zůstávají nevyřešené — změna detailed 1.2 vyžaduje novou verzi kontraktu.

## 6. Artifact index

| Soubor | Účel |
|---|---|
| `CHANGELOG.md` | Historie releasů [2.1]–[2.16], přijaté/zamítnuté změny |
| `README.md` | Stav, CLI, schémata, rychlé příklady |
| `docs/SESSION_HANDOFF_2026-11-17.md` | **Tento dokument** — current state |
| `docs/REFACTOR_PLAN_2026-11-11.md` | Originální plán fází + §11/11.1 aktuální stav |
| `docs/AUDIT_INTEGRATION_2026-11-13.md` | Rozhodnutí D1–D40 (§12.3 historie, §14 nové) |
| `docs/COMPACT_JSON_FOR_LLM.md` | Runtime kontrakt compact 2.7 pro LLM |
| `docs/CLI_USAGE.md` | CLI, MCP tool volání, výstupní cesty |
| `docs/HANDOFF_V1_3_INTEGRATION_2026-11-15.md` | Historický handoff (banner) |
| `docs/LLM_INPUT_AUDIT_2026-11-16.md` | Audit LLM inputu (historický, banner) |
| `docs/CODE_REVIEW_2026-11-16_VERIFICATION.md` | Verifikace externího review (historický) |
| `docs/HANDOFF_2_5_VERIFICATION_2026-11-17.md` | P0/P1 handoff 2.5. |
| `docs/CALIBRATION_2_6_2026-11-17.md` | Kalibrace `bcp`/`nm`/`mit` |
| `docs/HANDOFF_2_7_WAVE1_VALIDATION.md` | Validace vlny 1 handoffu 2.7 |
| `docs/HANDOFF_2_7_...` (vstup) | RLHF syntéza, hypotézy H-1..H-4, N-1..N-6, navržené architektury |
| `docs/GAME_FULL_1.0.md` | Merge vrstva obou perspektiv, ne joint coaching |
| `docs/PATTERN_DISCOVERY_METHODOLOGY.md` | Metodika patternů, candidate lifecycle |

Klíčový kód: `services/compact_serializer.py` (2.7 serializer + validator),
`services/game_analyzer.py` (anchor alignment, hooky),
`services/pattern_detector.py` (C/U/V), `services/piece_reads.py`,
`services/eval_provenance.py`, `services/confidence_dims.py`,
`services/pipeline_status.py`, `services/provider_health.py`,
`tools/coaching_single_game.py`.

Schémata: `schemas/single_game_v2_compact_2.7.json`,
`schemas/single_game_v1.2.json`, `schemas/single_game_v1.1.json`,
`schemas/single_game_v2_compact.json` (2.1),
`schemas/game_full_v1.0.json`.

## 7. Pravidla pro další agenta

- UTF-8 obsah, ASCII názvy souborů, `-X utf8` + `PYTHONIOENCODING=utf-8`.
- `data/` je gitignored — nikdy nestageovat. Master repo `_github` má vlastní
  změny; nikdy je nestageovat z podrepo. Globální `_github/.ai_state.json`
  zůstal v konsolidaci nedotčen (sdílí ho jiné repozitáře); current stav tohoto
  repozitáře je v tomto dokumentu a v `CHANGELOG.md`.
- Žádná změna klasifikace bez `DETECTOR_VERSION` bumpu a fixture.
- Žádná změna `cp_loss` vzorce; nový artifact = nová verze schématu.
- Commit/push až po zelených gates a CI. Ne destructivní git operace bez
  potvrzení.
- Každý nový nález formulovat jako hypotézu a validovat na historickém vzorku
  (min. 3 hry, u behaviorálních patternů dle §9 handoffu 2.7).
