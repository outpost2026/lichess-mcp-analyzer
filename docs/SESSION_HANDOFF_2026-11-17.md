---
title: Session handoff — lichess-mcp-analyzer (konsolidace 2026-11-17)
status: CURRENT STATE / PŘEDÁVACÍ ARTIFACT
repo: outpost2026/lichess-mcp-analyzer
branch: main
contracts: compact 2.9 | detailed 1.2 | cross-game 1.4 | game_full 1.0
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
| Compact 2.9 + detailed 1.2, validace obou schémat | funkční |
| `cp = bcp − eval_after_mover_cp` v compactu | 7/7 ve vzorku |
| `acc_warning` (mate/blunder/mistake), `pipeline`, `confidence_dims` | funkční |
| `--no-llm` = deterministický fallback, `llm_requested=false` | funkční |
| CI fast/engine split, pinned SF18 (hash + UCI), `--strict-markers` | funkční |

## 2. Kontrakty a klíčová rozhodnutí

- **Compact 2.9** (`schemas/single_game_v2_compact_2.9.json`) je current.
  Starší soubory 2.2-2.8 jsou zmrazené; validator čte předchozí verze
  (`SUPPORTED_VERSIONS = ("2.6", "2.7", "2.8", "2.9")`). 2.9 rozšiřuje
  `decisive_moves[]` o všechny mate přechody + `mate_missed`/`mate_via`/`best`
  a přidává `momentum_moves[]` pro winning→winning swingy (mate_missed>0 nebo cp>500).
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
# full JSON = compact 2.9 + detailed 1.2, obě barvy (výchozí)
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

- 10/10 payloadů validuje proti compact 2.9 + detailed 1.2.
- Aritmetika `bcp − eval_after = cp`: 7/7 měřitelných flagů.
- Chybějící `pv_played_unavailable`: 10/10 → 0/10 souborů.
- Pattern C: `yXmiCYss` white freq 4, `hJjXxxvq` black freq 5.
- Delta compactu 2.7 oproti 2.6: **+50 až +232 znaků** (limit +300).
- Gates: pytest **556 passed / 18 deselected**, Ruff clean, mypy **74 souborů** clean,
  engine job 18 passed s pinned `Stockfish 18` (stav 2026-11-18 po REVIEW-FIX).

## 5. Otevřené položky — REKALIBROVÁNO 2026-11-18

Generální code review + sémantická revize plánů rozdělila původní seznam z handoffu 2.7
na (a) aktivní práci s acceptance criterion, (b) vyřešené/obsoletní, (c) aspirace.
Podklady: `AUDIT_INTEGRATION` §6/§12, `PATTERN_DISCOVERY_METHODOLOGY` §11-§12,
`01_EVIDENCE_DIGEST` §11, `CHANGELOG` [REVIEW 2026-11-18].

### Aktivní roadmapa (pořadí dle EROI)

| # | Položka | P | Acceptance criterion |
|---|---|---|---|
| 1 | Opravit decision/contract index: D13–D35 kanonicky v `AUDIT_INTEGRATION` §12 (hotovo 2026-11-18), sjednotit „current compact 2.9" ve všech aktivních docs | P0 | Každé D-id v HANDOFF/EVIDENCE/AUDIT má jednu status+autoritu; žádný aktivní soubor neříká, že 2.1 je current |
| 2 | Sjednotit `llm.status` (`compact_serializer.py:67-68` vs `:430-431`) | P1 | `use_llm=false` = jeden deklarovaný status v compactu i detailed; auditor 8/8; při změně sémantiky nová verze schématu |
| 3 | ~~Opravit P0/P1 defekty z review~~ **DONE 2026-11-18** (`[REVIEW-FIX]`): `report_persister`, engine hash provenance, fabrikovaný rank, SRS retention, diagnostician, `llm.status`, `.bat`, `workspace_info`, engine identity, audit, workspace hranice, KB opt-in | ~~P1~~ | 9 regresních testů v `tests/test_review_fixes_2026_11_18.py`; gates 556/18, Ruff/mypy/verify zelené |
| 4 | **Evidence honesty blok** (nová cross analýza): `precision`/`pv_coverage` + **`decisive_moves[]`** + dokumentace `piece_reads` (`sq` = from-square forcing tahu v PV) | P1 | Report nese `precision` per position type a `pv_coverage` per pattern; `decisive_moves[]` vybírá `winning→losing`/`equal→losing` **před** největším `cp`; žádná změna `strength`/`confidence`; `COMPACT_JSON_FOR_LLM.md` high-level obsahuje pravidlo `sq`; regrese na 5-herním vzorku |
| 5 | Wave 2 — Q4 `declined_forcing_move_at_pivot` **EXPERIMENT za flagem** (`LICHESS_EXPERIMENTAL_Q4=1`, výchozí OFF), ne produkční pattern (`[Q4-EXP]`) | P2 (exp) | D4 gate nadále otevřen: N≥30, lift≥1,4, ≥2 analýzy, FP strop, `behavioral_confidence: not_calibrated`; do produkce až po validaci na ≥10 hrách; flag-on payload má `detector_version+Q4-exp` a vyžaduje čistou cache |
| 6 | ~~D23/T-16 `%clk` parser~~ **DONE 2026-11-18** (`[D23]`): `parse_clock_data()`, interní coaching data, prompt + deterministický report nesou `clock_data_unavailable`, když chybí | ~~P2/P3~~ | 4 testy v `tests/test_clock_parser.py`; žádná změna schémat; gates 563/18 |
| 7 | ~~D1 default phase mode~~ **DONE 2026-11-18** (`D41` v `AUDIT_INTEGRATION` §15): 20 her / 162 flagů / **1 flip (0,62 %)** → `ply_segment` zůstává default, `material` opt-in | ~~P3~~ | `scripts/measure_d1_phase_mode.py` + `data/runs/D1_phase_measurement_2026-11-18.json`; žádná změna schémat ani `DETECTOR_VERSION` |

### Verifikovaná cross-game evidence (2026-11-18, vlna 2)

Vlastní čtení JSON `v2xHpqXG` (Stafford, 39 ply → `h64`) a `7l9g62Eo` (Bird, `h256`) proti kódu:

- **Platí:** v2x ACPL 70,3/40,7; bílý 5 flagů/2 bludery (p29 `cxd4` 430 `winning→losing`, p39 `Qxc6+` 425 `losing→losing`); černý 7 flagů/**0 blunderů**, p6 `Nc6` 104 cp best `d6` `unclassified` — a černý vyhrál. 7l9: oba po 19 flagů, bílý 2 bludery (p77 `Bxh2` 478 `winning→winning` motif `high_value_capture`, p79 `Rf4` 599 `winning→losing`), černý 0 blunderů, p85 `why=check_escape`.
- **Korekce 3.LLM:** (a) výhra černého v Staffordu **není důkazem GAMBIT vektoru** — výsledek vysvětluje blunder differential (2 vs 0), ne gambit; použití `game.result` k potlačení flagů by było outcome leakage (DATA-FABRICATION-001). Ponechat jako hypotézu, ne implementovat. (b) „Q4 — 7 případů napříč 3 hrami" neobstojí jako *forcing* pattern: většina engine best tahů je tichá (`h3`, `Bf3`, `Bh3`, `Qa3`, `d6`, `Ng4`, `Bd5`, `Qe6`, `O-O`); jen `dxe4`/`Bxg2+` jsou forcing. (c) `high_value_capture` už **2 hry** (v2x b34, 7l9 w77) → motif registrovaný, kandidát `greedy_capture` (pouze pokud `cp_loss>50`). (d) `V` už **2 hry** (7l9 w107/w119). (e) 3.LLM uvádí u v2x b34 patterny „B+T", JSON má **C+T**.
- **Potvrzeno znovu:** `rank:null` je poctivý výstup REVIEW-FIX (v2x 5/5 a 4/7; 7l9 18/19 a 17/19); `piece_reads.sq = from_square` forcing tahu v PV (7l9 w77 `Rh3+` z h2 a `Qxh3` z f5) — problém je dokumentace, ne kód; `retry_budget_exhausted` se objevuje i v 7l9 (3+1 flagů), takže **není specifický jen pro extrémní hru** `lpDh1fIx`.
- **Nový robustní nález pro report:** v obou hrách rozhoduje **rozdíl v bluderech, ne počet flagů** (v2x 5 vs 7; 7l9 19 vs 19, vždy 2 vs 0). `decisive_moves[]` musí přednostně brát změnu `game_impact`, nikoli největší `cp` (p77 478 cp je `winning→winning`, p79 599 cp je `winning→losing`).

### Vyřešené / obsoletní (odstraněno z aktivní práce)

- `hash_mb` 64 vs 512 → adaptivní **h128/h256** (AUDIT §14 D40, CHANGELOG [2.13]); 64/128/256 v datech sedí na počtu ply, **ne config drift**.
- threshold `fen 100` vs `eval_after 200` → **`QUIET_BLUNDER_CP = 200`** (D13, CHANGELOG [2.7]).
- Wave 3 `ph` per flag → kosmetické; cena nové verze schématu > přínos (defer).
- `username: ""` v detailed → jen pojmenovací konzistence (defer).

### Aspirace — KEEP-AS-idea / DEFER / DROP

- **DROP:** FSRS (RP §7 „rejected for now", CHANGELOG [2.10] P-04, `srs_engine.py` = SM-2-like); frontend/GUI (RP §7 non-goal).
- **DEFER:** ELO ETL/bands (dual-perspektiva je absorbována v `coaching_opponent_pool`; ELO nemá ground truth); SQLite `analysis_runs` (pouze design, dokud neexistuje čtenář); T3.3 `interaction` events (bez measurement spec neprojde D4 gate); plná MDL kalibrace (MDL je měřicí vrstva, ne pravděpodobnost).
- **NE:** R1/R2/R3 entropy modes, TOT třetí stav, nové nástroje `hsnr_extract`/`compare_sides`, detailed 1.3 jen kvůli odstranění `internal_accuracy_score`, SQLite migrace bez čtenáře, jakékoli „zvýšení matched na 50 %" uvolněním prahu (M §6: „Co NENÍ cíl").

## 6. Artifact index

| Soubor | Účel |
|---|---|
| `docs/00_DOCS_CONTRACT.md` | **Start** — read order, autorita, pravidla (P1–P5, P84–P89) |
| `CHANGELOG.md` | Historie releasů [2.1]–[2.16], přijaté/zamítnuté změny |
| `README.md` | Proč, jak to funguje, 18 toolů, CLI příklady |
| `docs/SESSION_HANDOFF_2026-11-17.md` | **Tento dokument** — current state |
| `docs/COMPACT_JSON_FOR_LLM.md` | Runtime kontrakt compact 2.9 + Appendix A (`game_full` 1.0) |
| `docs/CLI_USAGE.md` | CLI, MCP tool volání, výstupní cesty |
| `docs/AUDIT_INTEGRATION_2026-11-13.md` | Závazná rozhodnutí D1–D40 (§14 = D38–D40) |
| `docs/PATTERN_DISCOVERY_METHODOLOGY.md` | Závazná metodologie patternů v1.7 |
| `docs/01_EVIDENCE_DIGEST.md` | Historická evidence, root causes, decision provenance |
| `docs/02_COACHING_EXEMPLARS.md` | Reprezentativní reporty + findings catalogue |
| `_ARCHIVE/` | Původní 72+ artefaktů před trimingem 2026-11-18 (ne aktivní navigace) |

Klíčový kód: `services/compact_serializer.py` (2.7 serializer + validator),
`services/game_analyzer.py` (anchor alignment, hooky),
`services/pattern_detector.py` (C/U/V), `services/piece_reads.py`,
`services/eval_provenance.py`, `services/confidence_dims.py`,
`services/pipeline_status.py`, `services/provider_health.py`,
`tools/coaching_single_game.py`.

Schémata: `schemas/single_game_v2_compact_2.9.json` (current),
`schemas/single_game_v2_compact_2.8.json` (frozen, still read by validator),
`schemas/single_game_v2_compact_2.7.json` (frozen, still read by validator),
`schemas/single_game_v2_compact_2.6.json` (validator backward read),
`schemas/single_game_v2_compact.json` (2.1 alias),
`schemas/single_game_v1.2.json` (detailed),
`schemas/game_full_v1.0.json`. Cross-game 1.4 je inline v `kb/schemas.py`.

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
