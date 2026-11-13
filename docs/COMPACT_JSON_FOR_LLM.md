# Compact JSON 2.1 — guide for an LLM agent

Compact JSON is the hand-off format between this pipeline and an LLM. It is
produced **offline** (no LLM at ETL time) and contains only what a coaching
answer needs. Schema: `schemas/single_game_v2_compact.json`.

It is the **default** output. Schema 1.2 (detailed) is opt-in via
`--format detailed` and exists for debugging and cross-game work.

Typical size: **1.2–4.5 kB** per game (hard budget 4500 chars for the primary
regression `FVhqtv1S`; measured 4400 chars) versus 13–26 kB for schema 1.2.

## What is in it

| Key | Meaning |
|---|---|
| `game` | id, username (omitted for anonymous games), color (`white` or `black` only — the side analysed), result, opening (ECO + name), tc, date, depth |
| `summary.acpl` / `summary.acc` | centipawn loss = lower is better; `acc` is the **internal** score 0–100 (`internal_cp_linear`), not Lichess accuracy (P1) |
| `summary.acc_method` | how `acc` was computed: `internal_cp_linear` = `mean(max(0, 100 - 0.15*cp_loss))`; omitted only for payloads that predate the field |
| `summary.phases` | `[acpl, flagged_count]` for opening / middlegame / endgame, grouped by `effective_phase` — the same phase the detectors used (`phase_method`), not the raw ply segment (P1) |
| `flags[]` | one entry per blunder/mistake/inaccuracy, ordered by ply |
| `flags[].ply` | half-move number (1 = White's 1st move) |
| `flags[].move` / `best` | SAN played vs SAN the engine preferred |
| `flags[].class` / `cp` / `rank` | severity, centipawn loss, played-move rank among engine candidates |
| `flags[].motif` | tactical tag when present (e.g. `discovered_check_capture`, `check`, `capture`) |
| `flags[].eval_before` / `eval_after` | eval swing in cp, **mover POV** (see "Perspective and eval POV"); present only for `cp > 200` or class blunder/mistake **and** consistent with `cp` (FIX-023) |
| `flags[].mate_in` | blunder only: forced mate in N moves from the best line (FIX-027); positive = for the player, negative = against |
| `flags[].patterns` | pattern ids whose evidence includes this ply; omitted when none |
| `flags[].pstatus` | `matched` or `unclassified` — every flag states whether a pattern covers it (P0-7) |
| `flags[].why` | reason code, present **only** when `pstatus == "unclassified"` (P0-7) |
| `patterns[]` | behavioural layer: id, **ordinal `strength`** 0–1 (emitted as `conf`), frequency, severity, affected plies. `conf` is not a probability (P1) |
| `phase_method` | which phase source the detectors used: `ply_segment`, `material`, or `mixed` (P0-3). `summary.phases` follows this source; the detailed payload additionally publishes `segment_stats` and `chess_phase_stats` so the difference is auditable (P1) |
| `patterns_meta` | mandatory: `scope`, `cross_game_suppressed`, `reason`, `coverage {flagged, matched, unclassified}`; an empty `patterns` list always has a reason |
| `unclassified` | discovery feed: `{ply, class, cp, why}` for flagged moves without a pattern |
| `pv` | `ply -> [SAN, SAN, SAN]` best line (max 3 moves) |
| `pv_unavailable` | `ply -> reason` when a blunder/mistake has no PV (explicit gap) |
| `clusters` | runs of >= 3 consecutive flagged own moves (time-pressure signal) |
| `fen_before` | `ply -> FEN`, only for `cp > 100` (reproducible drill positions) |
| `report` | short deterministic summary, ≤900 chars, never truncated mid-structure |
| `llm` | `{status, provider, reason}`; `failed` + `deterministic` means no LLM was used |

### Perspective and eval POV

Compact 2.1 is **single-perspective**: every `flags[]` entry, `summary.acpl`,
`summary.phases`, `patterns[]` and `clusters` describe the moves of the colour
in `game.color` (always `white` or `black`). Opponent moves are not part of the
payload. A full-game view is a different artifact (`game_full` 1.0, planned —
see `AUDIT_INTEGRATION_2026-11-13.md` §6), not an extension of compact 2.1.

**Eval POV:** `eval_before` and `eval_after` are both from the **mover's**
point of view — the player who made the flagged move. `eval_after` is *not* the
opponent's POV; the sign is not flipped after the move. Therefore:

- `cp ≈ eval_before - eval_after` (positive = loss for the mover);
- a positive value always means "good for the mover", for both colours;
- never compare `eval_before` of a White move with `eval_before` of a Black
  move as if they shared a direction — they do not.

Additive renames `eval_before_mover_cp` / `eval_after_mover_cp` and a White-POV
timeline are Tier 2.1 / Tier 3 in `AUDIT_INTEGRATION_2026-11-13.md` (D9).
Legacy keys stay as aliases for one release.

### Null and omission policy

`null` means **not measured** — never treat it as zero and never fill it in.

- `flags[].rank = null` — the engine did not measure the played-move rank
  (typically a timeout). It is never 0 and never guessed as 1.
- `flags[].motif` absent — the move has no tactical motif. A present motif is
  always a string. (`null` is not used here.)
- `eval_before` / `eval_after` absent — the flag is outside the FIX-015 window
  (`cp <= 200` and not blunder/mistake), the eval was not measured, or the pair
  contradicts `cp` (FIX-023). **Never** reconstruct a swing from `eval_before -
  eval_after` when those keys are absent.
- `mate_in` absent — the best line is not a forced mate, or the flag is not a
  blunder. When present, `eval_cp` is `null` for that engine line; say
  "mat v N", never "hodnocení 0".
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
- `why` values — `evidence_gap`, `quiet_positional`,
  `forcing_move_unexplained`, `capture_unexplained`,
  `mechanism_not_identified` (`not_classified` only in payloads that predate
  P0-7). A reason describes the measured **shape** of the move, never a
  mechanism: do not promote it to a named pattern.
- `patterns_meta.coverage` — always satisfies
  `matched + unclassified == flagged == len(flags)`.

## What the agent must do

1. Validate the JSON (schema 2.1) before using it.
2. Pick the weakest phase from `summary.phases`: highest ACPL, tie-break by
   flagged count. A phase with `flagged == 0` **and** ACPL `0.0` (or `null`) is
   clean — it is never the weakest phase. If every phase is clean, say
   "žádná slabá fáze" instead of inventing one.
3. For every flag you discuss, read `pv[ply]` for the alternative and
   `fen_before[ply]` when you need the position. Do not reconstruct a FEN by
   hand. If the ply is in `pv_unavailable`, state the gap.
4. Use `flags[].eval_before/eval_after` verbatim when present — you cannot
   derive a swing that was not measured.
5. Cross-reference `patterns[].plie` with `flags[].ply`; `flags[].patterns`
   already tells you which pattern a specific mistake feeds. For a flag with
   `pstatus == "unclassified"`, say that no calibrated pattern covers it and
   quote `why`; never invent a mechanism.
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
You are a chess coach. You receive one compact JSON analysis (schema 2.1) of a
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
   Use eval_before/eval_after when present. If pv_unavailable has the ply, say
   the engine line was unavailable.
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
2.1 payload additionally carries per-flag `pstatus`/`why`, top-level
`phase_method` and mandatory `patterns_meta`, plus `username`,
`eval_before/eval_after`, per-flag `patterns`, `pv_unavailable` and `clusters`.

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
  "report": "Hra 0-1 (B02 Alekhine Defense: Scandinavian Variation), ACPL 34.7, accuracy 94.8 %. 1 blunderů, 1 mistakes, 5 nepřesností. Nejslabší fáze: endgame (ACPL 36.9). Patterny: B (Automatic grab, conf 0.69), T (Tactical oversight, conf 0.8).",
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
(Tactical oversight, conf 0.8) — two tactical misses (plies 69, 75). Both are
above 0.5, so they justify targeted capture/check discipline work.
```

## How to produce it

```powershell
# one game -> compact JSON (default, offline without --no-llm only if desired)
.\.venv\Scripts\python.exe -X utf8 scripts\coach.py --game-id Sl1s8KmU --username systeq --no-llm --out data\reports\compact_Sl1s8KmU.json

# exact schema 1.2 (debugging / cross-game)
.\.venv\Scripts\python.exe -X utf8 scripts\coach.py --game-id Sl1s8KmU --format detailed --out detailed.json

# both shapes in one payload {"compact": ..., "detailed": ...}
.\.venv\Scripts\python.exe -X utf8 scripts\coach.py --game-id Sl1s8KmU --format both --out both.json

# from a PGN file
.\.venv\Scripts\python.exe -X utf8 scripts\coach.py --pgn-file data\reports\Sl1s8KmU.pgn --color white --no-llm --out out.json

# via MCP tool (when an IDE client is available)
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_coaching_single_game --args '{"game_id":"Sl1s8KmU","username":"systeq","output_format":"compact"}'
```

`output_format` accepts `compact` (default, schema 2.1), `detailed` (schema
1.2) and `both` → `{"compact": …, "detailed": …}`. `full` remains a deprecated
alias for `detailed` for one release cycle and logs a warning.
