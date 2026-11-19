# Compact JSON 2.9 - guide for an LLM agent

Compact JSON is the hand-off format between this pipeline and an LLM. It is
produced **offline** (no LLM at ETL time) and contains only what a coaching
answer needs. Schema: `schemas/single_game_v2_compact_2.9.json` (2.8, 2.7 and 2.6 are still read for backward compatibility).

It is the **default** output. Schema 1.2 (detailed) is opt-in via
`--format detailed` and exists for debugging and cross-game work.

Typical size: **1.2–4.5 kB** per game (hard budget 4500 chars for the primary
regression `FVhqtv1S`; measured 4400 chars) versus 13–26 kB for schema 1.2.

## One game, both colours (D24)

Compact 2.9 is single-perspective by contract, so a complete game is **two
compact payloads in one file**, keyed by colour:

```json
{"white": {"v": "2.7", "game": {"color": "white"}, …},
 "black": {"v": "2.7", "game": {"color": "black"}, …}}
```

This is the CLI default (`coach.py`, `coach_single.py` without `--color`).
Read the key as "whose moves am I looking at" — `flags[]`, `summary.acpl`,
`summary.phases`, `patterns[]` and `clusters` inside `white` describe White's
moves only. With `--color white|black` the output is the bare payload, not a
keyed object. A merged White-POV timeline is the separate `game_full` 1.0
artifact.

## What is in it

| Key | Meaning |
|---|---|
| `game` | id, username (omitted for anonymous games), color (`white` or `black` only — the side analysed), result, opening (ECO + name), tc, date, depth |
| `summary.acpl` / `summary.acc` | centipawn loss = lower is better; `acc` is the **internal** score 0–100 (`internal_cp_linear`), not Lichess accuracy (P1) |
| `summary.src` | 2.7: exact engine policy label (e.g. `d14n150k_h64_live`), from detailed `eval_provenance`. Reproduction signal for an LLM that must not assume depth 14 was used |
| `summary.acc_method` | how `acc` was computed: `internal_cp_linear` = `mean(max(0, 100 - 0.15*cp_loss))`; omitted only for payloads that predate the field |
| `summary.acc_warning` | `contains_mate_level_outlier` when at least one flag is mate-level (a missed mate or a forced mate after the move). The score itself is unchanged; never quote `acc` without this qualifier when it is present (D33) |
| `summary.phases` | `[acpl, flagged_count]` for opening / middlegame / endgame, grouped by `effective_phase` — the same phase the detectors used (`phase_method`), not the raw ply segment (P1) |
| `flags[]` | one entry per blunder/mistake/inaccuracy, ordered by ply |
| `flags[].ply` | half-move number (1 = White's 1st move) |
| `flags[].move` / `best` | SAN played vs SAN the engine preferred |
| `flags[].class` / `cp` / `rank` | severity, centipawn loss, played-move rank among engine candidates |
| `flags[].motif` | tactical tag when present (e.g. `discovered_check_capture`, `check`, `capture`) |
| `flags[].bcp` / `eval_after_mover_cp` | the D12 anchor and post-move eval, both **mover POV**; `cp == bcp - eval_after_mover_cp` whenever both are present. `bcp` is mandatory but nullable; `eval_after_mover_cp` appears only inside the FIX-015 window and only when the arithmetic holds |
| `flags[].eval_before_mover_cp` / `eval_before` / `eval_after` | **removed** (non-anchor before-eval in 2.6, aliases in 2.5); raw values remain in detailed 1.2 |
| `flags[].alts` | 2.7: one rank-2 SAN alternative for flags whose played rank >= 4, from the same engine search. Not the opponent's actual reply |
| `piece_reads` | 2.7: ply -> forcing piece seen in the measured PV (`sq`, `pc`, `role=monster`, `th` = threat SAN). At most one per game, only for `cp > 100`; never an inferred threat. **`sq` = `from_square` of the forcing SAN at its position inside `engine_lines[0].pv`**, after the preceding PV moves have been pushed — it is NOT necessarily the current board square. Example: white `Ng5` with PV `Kd1, Ne4, Qb7, Nxf2+` yields `sq=e4`, `th=Nxf2+` |
| `flags[].mate_in` | blunder only: forced mate in N moves from the best line (FIX-027); positive = for the player, negative = against |
| `flags[].game_impact` | **mandatory** since 2.2: did the game change, from the mover's POV. 9 sign transitions (`winning_to_winning` … `losing_to_losing`) with a ±100 cp dead zone, plus 3 mate transitions (`*_to_mate`). `null` = evals not measured. A 9000 cp loss with `winning_to_winning` is a missed conversion, not a catastrophe (D29) |
| `flags[].mate_missed` / `mate_via` | the best line mates for the mover in N moves and the played move does not; `mate_via` is the mating SAN. Present together, omitted otherwise. This is why `cp_loss` can be ~9000 while `game_impact` stays `winning_to_winning` (D31) |
| `flags[].mate_after` | 2.7: mandatory, nullable. `for` = the mover mates after the played move, `against` = the mover is mated. Non-null **exactly** when `game_impact` ends in `_to_mate`. Without it a `losing_to_mate` flag is ambiguous — always quote it with the impact |
| `flags[].patterns` | pattern ids whose evidence includes this ply; omitted when none |
| `flags[].pstatus` | `matched` or `unclassified` — every flag states whether a pattern covers it (P0-7) |
| `flags[].why` | reason code, present **only** when `pstatus == "unclassified"` (P0-7) |
| `patterns[]` | behavioural layer: id, short `nm`/`mit` (name and ≤50-char mitigation, 2.7/C-2), **ordinal `strength`** 0-1 (emitted as `conf`), frequency, severity, affected plies, and `support` (0-1 or null). Full name/mitigation stay in detailed. `conf` is not a probability (P1) and is **0-1**; the detailed payload's `confidence` is also **0-1** (same number, D26) - only cross-game artifacts use 0-100, so never mix the two families |
| `patterns[].support` | 2.3/P0-4: measured share of flagged moves in this game covered by that pattern (`flagged_moves_in_game` basis, denominator in detailed `evidence_support_n_units`). Null = no measured move. This is **evidence support**, not detector strength |
| `patterns[].pv_coverage` | 2.8: measured share of this pattern's plies that carry a PV (`pv`), 0-1 or null when the pattern has no plies. It tells an LLM how much of the pattern's evidence is actually observable — a low value means the pattern is less verifiable, not less present |
| `precision` | 2.8: `{opening, middlegame, endgame, basis}`. **Currently all phase values are `null` with `basis: not_calibrated`** — there are no labeled outcomes, so no precision number may be invented. Never replace `null` with a guessed value |
| `decisive_moves` | 2.9: `{ply, move, cp, game_impact, mate_missed, mate_via, best}[]` for **every mate transition** (`winning_to_mate`, `equal_to_mate`, `losing_to_mate`) plus `winning/equal_to_losing`, ranked by `cp` descending. A missed mate is decisive even when the impact stayed winning. `mate_via` names the mating SAN; `best` the engine choice |
| `momentum_moves` | 2.9: `{ply, move, cp, game_impact, mate_missed, mate_via, best}[]` for `winning_to_winning` swings that still deserve narration: `mate_missed > 0` OR `cp > 500`. Example: aFZC293b white 41 `Nxd6+` 9124 cp with `mate_missed=3 via Nf6+` — the single most important moment was previously absent from the structured decisive list |
| `confidence_dims` | 2.3/P0-4: mandatory. `kinds` = `detection_strength`, `evidence_support`, `behavioral_confidence`; `published_kind = detection_strength` names what `conf` means; `behavioral_confidence = null` with `behavioral_confidence_reason = not_calibrated`. Never present a pattern `conf` as a calibrated probability |
| `pipeline` | 2.7: mandatory. `analysis` = `complete`/`partial`/`failed`, `coaching` = `llm`/`deterministic_fallback`/`data_only`/`failed`, `llm_requested` = false when the caller deliberately ran offline. Do **not** read `status=degraded` as "analysis failed" while `pipeline.analysis=complete` |
| `phase_method` | which phase source the detectors used: `ply_segment`, `material`, or `mixed` (P0-3). `summary.phases` follows this source; the detailed payload additionally publishes `segment_stats` and `chess_phase_stats` so the difference is auditable (P1) |
| `patterns_meta` | mandatory: `scope`, `cross_game_suppressed`, `reason`, `coverage {flagged, matched, unclassified}`; an empty `patterns` list always has a reason |
| `unclassified` | discovery feed: `{ply, class, cp, why}` for flagged moves without a pattern |
| `pv` | `ply -> [SAN, SAN, SAN]` best line (max 3 moves) |
| `pv_unavailable` | `ply -> reason` when a blunder/mistake has no PV (explicit gap). This **is** the truncation signal: there is no separate `pv_truncated` flag |
| `pv_played` | `ply -> [SAN, …]` (max 3): the engine continuation **after the played move**, from the same multipv search as `pv`. It is a line, not the opponent's actual reply — never narrate it as "what was played next" (D32) |
| `pv_played_unavailable` | `ply -> reason` (`rank_not_in_engine_lines`, `rank_unknown`, `no_continuation`, `no_engine_lines`) when the played-move continuation is unavailable (D32, 2.7) |
| `clusters` | runs of >= 3 consecutive flagged own moves (time-pressure signal), each with `from`, `to`, `count`, `total_cp` and `plies` — the exact moves in the run (D32) |
| `fen_before` | `ply -> FEN`, only for `cp > 100` (reproducible drill positions). Detailed 1.2 carries `flagged_moves[].fen_before` for **every** flag, so a narrative that needs the position of a small inaccuracy must use the detailed payload |
| `report` | short deterministic summary, ≤900 chars, never truncated mid-structure |
| `llm` | `{status, provider, reason}`; `failed` + `deterministic` means no LLM was used |

### Perspective and eval POV

Compact 2.9 is **single-perspective**: every `flags[]` entry, `summary.acpl`,
`summary.phases`, `patterns[]` and `clusters` describe the moves of the colour
in `game.color` (always `white` or `black`). Opponent moves are not part of the
payload. A full-game view is a different artifact (`game_full` 1.0, implemented
2026-11-14 - see `COMPACT_JSON_FOR_LLM.md` Appendix A), not an extension of compact 2.9.

**Eval POV:** `bcp` and `eval_after_mover_cp` are both from the **mover's**
point of view — the player who made the flagged move. `eval_after_mover_cp`
is *not* the opponent's POV; the sign is not flipped after the move.
Therefore:

- `cp = bcp - eval_after_mover_cp` whenever both are present (2.6/C-1).
  `bcp` is the D12 anchor (the engine's best move), not the pre-move eval:
  using `eval_before_mover_cp` would give a different, non-reconstructible
  number, which is why that key was removed. Since [2.8] the detailed payload also
  carries `analysis.eval_provenance`: `anchor_coverage` tells you what share of
  measured moves can actually be reconstructed from that anchor, and
  `flagged_moves[].cp_loss_basis` says `unknown` when they cannot. Do not claim
  "100 % consistent" for a game whose coverage is below 1.
- a positive value always means "good for the mover", for both colours;
- never compare `bcp` of a White move with one of a Black move as if they
  shared a direction — they do not.

The legacy aliases `eval_before` / `eval_after` were removed in 2.5, and the non-anchor `eval_before_mover_cp` in 2.6 (P1-2/C-1; see SESSION_HANDOFF §2 and CHANGELOG [2.14]);
the validator still reads 2.4 files that contain them. A White-POV timeline is
a different artifact (`game_full` 1.0, Tier 3 in
`AUDIT_INTEGRATION_2026-11-13.md`).

### Null and omission policy

`null` means **not measured** — never treat it as zero and never fill it in.

- `flags[].rank = null` — the engine did not measure the played-move rank
  (typically a timeout). It is never 0 and never guessed as 1.
- `flags[].motif` absent — the move has no tactical motif. A present motif is
  always a string. (`null` is not used here.)
- `eval_after_mover_cp` absent — the flag is outside the FIX-015 window
  (`cp <= 200` and not blunder/mistake), the eval was not measured, or the
  anchor does not reconstruct `cp` (FIX-023). `bcp` stays present (nullable).
  **Never** reconstruct a swing when the key is absent, and never present it
  as the measured `cp` even when they are present (D12: `cp` is anchored to the
  best move).
- `mate_in` absent — the best line is not a forced mate, or the flag is not a
  blunder. When present, `eval_cp` is `null` for that engine line; say
  "mat v N", never "hodnocení 0".
- `flags[].game_impact = null` — the evals were not measured (legacy cache or
  cloud eval). Do not infer the state from `cp` alone; `cp` says how much was
  lost, not whether the game changed.
- `flags[].mate_missed` absent — no mate was available, the played move itself
  reaches a forced mate (`mate_after` says for whom), or the line was not
  measured. `mate_missed` and `mate_via` always appear together.
- `pv_played` absent but `pv_played_unavailable[ply]` present — say the engine
  continuation was unavailable and name the reason; never substitute the
  opponent's actual reply (it is not in the payload).
- `summary.acc_warning` present — quote it next to `acc`. A high accuracy with
  one missed mate is still a high accuracy for the other moves, but not a
  verdict on the game.
- `summary.acpl` / `summary.phases[*][0] = null` — no measured move in that
  scope.
- `game.username` absent — anonymous game or unknown player; never the literal
  placeholder `Anonymous`.
- `game.date` absent — PGN date is unknown (`????.??.??`); a placeholder is
  never published.
- `pv_unavailable[ply]` — a blunder/mistake has no PV and the reason is one of
  `engine_timeout`, `engine_error`, `no_engine_lines`, `engine_lines_empty`,
  `retry_budget_exhausted`, `no_fen`. Do not claim the position is simple;
  say the engine line was unavailable.
- `flags[].pstatus` — always present. `matched` means at least one pattern in
  `flags[].patterns`; `unclassified` means none did. `why` is present exactly
  when `pstatus == "unclassified"` and absent when matched.
- `why` values - `evidence_gap`, `quiet_positional`, `quiet_blunder`
  (quiet shape with `cp > 200`, D13), `check_escape` (non-capturing king move
  out of check, D14), `forcing_move_unexplained`, `capture_unexplained`,
  `mechanism_not_identified` (`not_classified` only in payloads that predate
  P0-7). A reason describes the measured **shape** of the move, never a
  mechanism: do not promote it to a named pattern.
- `patterns_meta.coverage` — always satisfies
  `matched + unclassified == flagged == len(flags)`.

## Aliases and collisions — count each fact once

Verified on live tool outputs (4 games × 2 colours, 2026-11-16). These are
intentional compatibility surfaces, not independent measurements:

- **Same value, two names.** Detailed 1.2 still mirrors `eval_before`/
  `eval_after` to `*_mover_cp`; compact 2.9 replaces the non-anchor before-eval
  with `bcp`. `accuracy` mirrors
  `internal_accuracy_score`; `strength` = `confidence` = `detection_strength`
  = compact `conf`; `segment` = `phase`; compact `acc_warning` = detailed
  `accuracy_warning`. Never add them twice or average them.
- **`flags` is not the same key in both schemas.** In detailed 1.2 `flags` is a
  small **config object** (`cloud_eval`, `bfs_scope`); in compact 2.x `flags`
  is the **array of flagged moves**. Use `detailed.flagged_moves` when you mean
  moves. This is the single most likely key collision when reading both files.
- **`report` is a restatement, not a second source of truth.** `output_format:
  "both"` returns the same report twice; compact clips/rewords it at 900 chars
  and may omit it, while `report_meta` only describes the detailed one. Trust
  `flags[]`/`patterns[]` for facts.
- **`cascade_log` (detailed) is raw provider telemetry; `llm.attempts` is the
  derived view.** Use `llm.attempts`; don't narrate raw log entries.
- **Bidirectional indexes repeat one relation.** `flags[].patterns` ↔
  `patterns[].plie`, `flags[].pstatus`/`why` ↔ top-level `unclassified[]`, and
  `clusters[].plies` ↔ `flags[].ply` all encode the same facts twice on purpose
  (LLM robustness). Pick one direction per claim.
- **`pv` and `pv_played` are different lines.** `pv` is the engine's best line;
  `pv_played` is the engine continuation after the played move. Neither is the
  opponent's actual reply (only the `game_full` timeline has real replies).

## What the agent must do

1. Validate the JSON (schema 2.7) before using it.
2. Pick the weakest phase from `summary.phases`: highest ACPL, tie-break by
   flagged count. A phase with `flagged == 0` **and** ACPL `0.0` (or `null`) is
   clean — it is never the weakest phase. If every phase is clean, say
   "žádná slabá fáze" instead of inventing one.
3. For every flag you discuss, read `pv[ply]` for the alternative and
   `fen_before[ply]` when you need the position. Do not reconstruct a FEN by
   hand. If the ply is in `pv_unavailable`, state the gap. `pv_played[ply]` is
   the engine's line after the played move — useful for "what the move allows",
   never for "what the opponent answered".
4. Use `flags[].bcp` and `eval_after_mover_cp` verbatim when present — you
   cannot derive a swing that was not measured.
4b. Read `flags[].game_impact` before choosing an adjective. `winning_to_mate`
   is fatal; `winning_to_winning` with `mate_missed: N` means "you missed the
   mate, the position stayed winning"; `losing_to_losing` is a lost position
   getting worse, not the decisive moment.
5. Cross-reference `patterns[].plie` with `flags[].ply`; `flags[].patterns`
   already tells you which pattern a specific mistake feeds. For a flag with
   `pstatus == "unclassified"`, say that no calibrated pattern covers it and
   quote `why`; never invent a mechanism. Read `confidence_dims` before quoting
   a pattern `conf`: it is an ordinal detection strength, `support` is measured
   coverage of flagged moves, and `behavioral_confidence` is null because no
   mechanism calibration exists.
6. Mention `clusters` as a time-pressure / attention hypothesis, not a proven
   cause. A cluster is a run of flagged own moves, not a diagnosis.
7. Answer in this order: one-sentence verdict, weakest phase + one drill, top
   two flags with the engine alternative, pattern-level advice.
8. Absolute rules:
   - never invent a move, eval, FEN or PV;
   - never say "no blunders" if any `flags[].class == "blunder"`;
   - never call an inaccuracy a blunder (severity is in `class`);
   - never claim a cause for `pstatus == "unclassified"` — report `why`;
   - if `llm.status == "failed"`, do not present `report` as LLM analysis.

## Prompt template (copy-paste)

System:

```text
You are a chess coach. You receive one compact JSON analysis (schema 2.7) of a
game played by the user. Base every statement on the JSON fields. Never invent
moves, evaluations, FENs or variations. If a value is null or a key is absent,
say it was not measured instead of guessing. The user's side is game.color.
```

User:

```text
Analyze this game for self-coaching.

Rules:
1. One-sentence verdict.
2. Weakest phase from summary.phases (highest ACPL) + one concrete drill.
3. Top 2 flags by cp: what was played, what pv[ply] says was better, why.
   Use bcp/eval_after_mover_cp when present. If pv_unavailable
   has the ply, say the engine line was unavailable.
3b. Check game_impact and mate_missed before calling a move a catastrophe.
   winning_to_winning + mate_missed = "missed mate, still winning".
   If summary.acc_warning is present, mention it with the accuracy.
3c. Never call a pattern conf a probability. confidence_dims says which
   dimension is published (detection strength); patterns[].support is measured
   coverage; behavioral_confidence is not calibrated.
4. Pattern advice only for patterns with conf >= 0.5 (conf is ordinal
   `strength`, not a probability). Use flags[].patterns to link a specific
   mistake to its pattern.
5. Do not claim "no blunders" if flags contains class=blunder.
6. A flag with pstatus=unclassified has no calibrated pattern: quote its why
   and say the cause was not identified. Never invent a mechanism.

JSON:
<PASTE COMPACT JSON HERE>
```

## Example (core fields)

Input (`Sl1s8KmU`, White, 0-1, rapid 600+0, depth 14). The example is a
historical 2.0 payload and is intentionally limited to the core keys; a current
2.7 payload additionally carries per-flag `pstatus`/`why`/`game_impact`,
top-level `phase_method` and mandatory `patterns_meta`, plus `username`,
`bcp/eval_after_mover_cp`, per-flag `patterns`, `mate_missed`/`mate_via`,
`pv_unavailable`, `pv_played`/`pv_played_unavailable`, `clusters[].plies`,
`summary.acc_warning`, `patterns[].support`/`nm`/`mit` and `confidence_dims`.

```json
{
  "v": "2.0",
  "game": {
    "id": "Sl1s8KmU",
    "color": "white",
    "result": "0-1",
    "opening": "B02 Alekhine Defense: Scandinavian Variation",
    "depth": 14,
    "tc": "600+0",
    "date": "2026-11-08"
  },
  "summary": {
    "acpl": 34.7,
    "acc": 94.8,
    "phases": {
      "opening": [34.5, 1],
      "middlegame": [33.0, 4],
      "endgame": [36.9, 2]
    }
  },
  "flags": [
    { "ply": 11, "move": "e6", "class": "mistake", "cp": 182, "best": "Qxd4", "rank": 3 },
    { "ply": 21, "move": "Na4", "class": "inaccuracy", "cp": 69, "best": "Bf4", "rank": 4 },
    { "ply": 25, "move": "Qd2", "class": "inaccuracy", "cp": 121, "best": "Qe3", "rank": 4 },
    { "ply": 33, "move": "Bb2", "class": "inaccuracy", "cp": 126, "best": "Bf4", "rank": 4 },
    { "ply": 45, "move": "f3", "class": "inaccuracy", "cp": 80, "best": "Qa6", "rank": 4 },
    { "ply": 69, "move": "Qf4+", "class": "inaccuracy", "cp": 83, "best": "Qa7+", "rank": 3, "motif": "check" },
    { "ply": 75, "move": "Qxd6", "class": "blunder", "cp": 346, "best": "Qe3", "rank": 4, "motif": "capture" }
  ],
  "patterns": [
    { "id": "B", "conf": 0.69, "freq": 1, "sev": "high", "plie": [75] },
    { "id": "T", "conf": 0.8, "freq": 2, "sev": "medium", "plie": [69, 75] }
  ],
  "pv": {
    "11": ["Qxd4"],
    "25": ["Qe3", "e5", "Ne2"],
    "75": ["Qe3", "Qe8", "Qa7"]
  },
  "fen_before": {
    "11": "rnbqkb1r/pp1npppp/8/1B1pP3/3p4/2N5/PPP2PPP/R1BQK1NR w KQkq - 0 6",
    "75": "6k1/6bp/3pp1p1/1q1p4/5Q2/3N1P2/4K1PP/1r6 w - - 10 38"
  },
  "report": "Hra 0-1 (B02 Alekhine Defense: Scandinavian Variation), ACPL 34.7, accuracy 94.8 %. 1 blunderů, 1 mistakes, 5 nepřesností. Nejslabší fáze: endgame (ACPL 36.9). Patterny: B (Automatic grab, conf 0.69), T (tactical_shaped_move_error, conf 0.8).",
  "llm": { "status": "failed", "provider": "deterministic", "reason": "llm_disabled" }
}
```

_Poznámka: ukázka je zkrácena na 3 položky `pv` a 2 položky `fen_before`;
plný výstup obsahuje PV pro všech 7 flagů a FEN pro každý flag s `cp > 100`.
Všechny uvedené hodnoty jsou skutečný výstup pro hru `Sl1s8KmU`._

Expected coaching output (abridged — facts must match the JSON):

```text
Verdict: a competitive game decided late — 94.8 % accuracy, but the endgame
blunder at move 38 turned a holdable position into a loss.

Weakest phase: endgame (ACPL 36.9, 2 flags incl. the only blunder).
Drill: 15 minutes of queen+rook endgame puzzles, focus on checks before captures.

Ply 75 Qxd6 (blunder, 346 cp). The engine prefers 75... Qe3, starting with
Qe3 Qe8 Qa7. The capture grabbed a pawn but left the king exposed.
Ply 11 e6 (mistake, 182 cp) instead of Qxd4 — the pawn push gave up the centre.

Patterns: B (Automatic grab, conf 0.69) — one capture-based blunder; T
(tactical_shaped_move_error, conf 0.8) — two tactical misses (plies 69, 75). Both are
above 0.5, so they justify targeted capture/check discipline work.
```

## How to produce it

```powershell
# one game -> compact JSON for BOTH colours, keyed {"white": …, "black": …}
.\.venv\Scripts\python.exe -X utf8 scripts\coach.py --game-id Sl1s8KmU --no-llm --out data\reports\compact_Sl1s8KmU.json

# one perspective only (bare payload, not keyed)
.\.venv\Scripts\python.exe -X utf8 scripts\coach.py --game-id Sl1s8KmU --color white --no-llm

# exact schema 1.2 (debugging / cross-game)
.\.venv\Scripts\python.exe -X utf8 scripts\coach.py --game-id Sl1s8KmU --format detailed --out detailed.json

# both shapes in one payload {"compact": ..., "detailed": ...}
.\.venv\Scripts\python.exe -X utf8 scripts\coach.py --game-id Sl1s8KmU --format both --out both.json

# from a PGN file
.\.venv\Scripts\python.exe -X utf8 scripts\coach.py --pgn-file data\reports\Sl1s8KmU.pgn --color white --no-llm --out out.json

# via MCP tool (when an IDE client is available)
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_coaching_single_game --args '{"game_id":"Sl1s8KmU","username":"systeq","output_format":"compact"}'
```

`output_format` accepts `compact` (default, schema 2.7), `detailed` (schema
1.2) and `both` → `{"compact": …, "detailed": …}`. `full` remains a deprecated
alias for `detailed` for one release cycle and logs a warning.

The MCP tool is always **single-perspective** (`color` is `white` or `black`,
`both` is rejected with `INVALID_COLOR`, D6a). Both colours in one file is a
CLI convenience: two explicit calls keyed by colour (D24).

---

## Appendix A — `game_full` 1.0 (merged timeline obou barev)

Původně samostatný `COMPACT_JSON_FOR_LLM.md` Appendix A (vtěleno ve W3). Závazné rozhodnutí D7a
viz `AUDIT_INTEGRATION_2026-11-13.md`. Kód: `src/lichess_analyzer_mcp/services/timeline.py`;
schema: `schemas/game_full_v1.0.json`; CLI: `scripts/coach.py --format game-full`.

**Co to je:** merge vrstva, **ne nová analýza**. Dual cache měří každý půltah právě jednou
(bílý běh = tahy Bílého, černý = tahy Černého). Merge z obou `GameAnalysis` postaví jednu
časovou osu: každý `ply` je tam právě jednou; všechna eval pole jsou **White POV**;
`cp_loss` zůstává velikost ztráty (nikdy se nepřeklápí); co nebylo změřeno, je `null`
(nikdy nula, nikdy odhad). Merge **nesmí spustit engine** — chybí-li jeden pohled,
výsledek je `status="partial"` s pojmenovanou dírou.

**Tvar payloadu (klíčová pole):**
```json
{"schema":"game_full","v":"1.0","pov":"white","game":{...},
 "status":"complete","plies_total":78,"missing_plies":[],"unanalyzed_plies":[],
 "coverage":{"white_plies":39,"black_plies":39,"merged_plies":78,
             "expected_plies":78,"missing_colours":[]},
 "source":{"white":{"available":true,"mode":"fast","acpl":24.1,"moves_measured":39},
           "black":{"available":true,"mode":"fast","acpl":31.7,"moves_measured":39}},
 "plies":[{"ply":1,"mover_color":"white","san":"e4","uci":"e2e4","class":"best",
           "cp_loss":0.0,"eval_before_mover_cp":20.0,"eval_after_mover_cp":18.0,
           "eval_before_white_cp":20.0,"eval_after_white_cp":18.0,
           "win_prob_white_before":0.53,"win_prob_white_after":0.52,
           "fen_before":"...","best":"d4","rank":1,"analyzed":true}]}
```

| Pole | Význam |
|---|---|
| `pov` | vždy `white`; jiná hodnota = validační chyba |
| `status` | `complete` jen při známém `plies_total`, všech plies, žádném nezměřeném tahu a obou barvách |
| `plies_total` | počet půltahů z PGN; `null` u legacy cache — nikdy odhad |
| `missing_plies` | plies v `1..plies_total` bez analýzy; prázdné, když `plies_total` neznámý |
| `unanalyzed_plies` | plies v payloadu explicitně nezměřené (engine timeout/budget) |
| `coverage` | počty po barvách + `missing_colours` |
| `source` | vždy obě barvy; `available=false` nesmí nést čísla |
| `plies[].mover_color` | `white` pro lichý ply, `black` pro sudý |
| `plies[].eval_*_white_cp` | White POV: pro Bílého stejné, pro Černého negované |
| `plies[].win_prob_white_*` | White POV: pro Černého `1 − p` ( ne znaménkem) |
| `plies[].cp_loss` | `>= 0`; `null` právě když `analyzed=false` |

**Invarianty `validate_game_full()`** (1–9): konstanty `schema`/`v`/`pov`, `status ∈ {complete,partial}`;
plies striktně rostoucí bez duplicit v `1..plies_total`; `mover_color` dle parity;
`eval_*_white_cp == ±eval_*_mover_cp` (tolerance 1e-6); `cp_loss >= 0` a `null` jen u
nezměřeného tahu; `unanalyzed_plies` = přesně nezměřené plies; `complete` nepřipouští díru;
`missing_plies` a `plies` se nepřekrývají; `source` má obě barvy. Testy: `tests/test_game_full.py` (14).

**Partial kontrakt (T3.4):** jen jedna barva → `partial` + `missing_colours`; legacy cache bez
`game_plies_total` → `partial`, `plies_total=null`; engine timeout → ply s `analyzed=false`.

**Determinismus:** merge jen čte cache (`_policy_token` sdílený s `lichess_analyze_game`),
žádné wall-clock / LLM / nové engine volání, pořadí dáno `ply`; dva běhy na stejných cache
dávají identický JSON.

**Co NEDĚLÁ:** není náhrada compact 2.9 ani detailed 1.2 (ty zůstávají jednoperspektivní);
**nemá `interaction` events** (T3.3 čeká na measurement spec a kalibraci FP); nedopočítává
chybějící plies.
