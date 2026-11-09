# Compact JSON 2.0 — guide for an LLM agent

Compact JSON is the hand-off format between this pipeline and an LLM. It is
produced **offline** (no LLM at ETL time) and contains only what a coaching
answer needs. Schema: `schemas/single_game_v2_compact.json`.

Typical size: **1.1–1.8 kB** (≈300–450 tokens) versus 13–16 kB for schema 1.1.

## What is in it

| Key | Meaning |
|---|---|
| `game` | id, color (side you played), result, opening (ECO + name), tc, date, depth |
| `summary.acpl` / `summary.acc` | centipawn loss = lower is better; accuracy 0–100 |
| `summary.phases` | `[acpl, flagged_count]` for opening / middlegame / endgame |
| `flags[]` | one entry per blunder/mistake/inaccuracy, ordered by ply |
| `flags[].ply` | half-move number (1 = White's 1st move) |
| `flags[].move` / `best` | SAN played vs SAN the engine preferred |
| `flags[].class` / `cp` / `rank` | severity, centipawn loss, played-move rank among engine candidates |
| `flags[].motif` | tactical tag when present (e.g. `discovered_check_capture`, `check`, `capture`) |
| `patterns[]` | behavioural layer: id, confidence 0–1, frequency, severity, affected plies |
| `pv` | `ply -> [SAN, SAN, SAN]` best line (max 3 moves) |
| `fen_before` | `ply -> FEN`, only for `cp > 100` (reproducible drill positions) |
| `report` | short deterministic summary, ≤1200 chars, never truncated mid-structure |
| `llm` | `{status, provider, reason}`; `failed` + `deterministic` means no LLM was used |

`null` means **not measured** — never treat it as zero and never fill it in.
A missing `rank`, `motif`, `pv` or `fen_before` key means the same: no data.

## What the agent must do

1. Validate the JSON (schema 2.0) before using it.
2. Pick the weakest phase from `summary.phases`: highest ACPL, tie-break by
   flagged count. If all ACPL are similar, say so instead of inventing one.
3. For every flag you discuss, read `pv[ply]` for the alternative and
   `fen_before[ply]` when you need the position. Do not reconstruct a FEN by
   hand.
4. Cross-reference `patterns[].plie` with `flags[].ply` — a pattern with
   `conf >= 0.5` is worth a general recommendation; below that mention it as a
   weak signal only.
5. Answer in this order: one-sentence verdict, weakest phase + one drill, top
   two flags with the engine alternative, pattern-level advice.
6. Absolute rules:
   - never invent a move, eval, FEN or PV;
   - never say "no blunders" if any `flags[].class == "blunder"`;
   - never call an inaccuracy a blunder (severity is in `class`);
   - if `llm.status == "failed"`, do not present `report` as LLM analysis.

## Prompt template (copy-paste)

System:

```text
You are a chess coach. You receive one compact JSON analysis (schema 2.0) of a
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
4. Pattern advice only for patterns with conf >= 0.5.
5. Do not claim "no blunders" if flags contains class=blunder.

JSON:
<PASTE COMPACT JSON HERE>
```

## Example

Input (`Sl1s8KmU`, White, 0-1, rapid 600+0, depth 14):

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
# one game -> compact JSON (offline, no LLM)
.\.venv\Scripts\python.exe -X utf8 scripts\pgn_to_compact.py --game-id Sl1s8KmU --color white --out data\reports\compact_Sl1s8KmU.json

# from a PGN file
.\.venv\Scripts\python.exe -X utf8 scripts\pgn_to_compact.py --pgn-file data\reports\Sl1s8KmU.pgn --color white --out out.json

# via MCP tool (when an IDE client is available)
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_coaching_single_game --args '{"game_id":"Sl1s8KmU","username":"systeq","output_format":"compact"}'
```

`output_format` accepts `full` (default, contract 1.1), `compact` (2.0) and
`both` → `{"full": …, "compact": …}`.
