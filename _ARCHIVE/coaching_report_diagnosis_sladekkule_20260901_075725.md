# Coaching Report — diagnosis (sladekkule)

**Generated:** 2026-09-01 07:57 UTC
**Pipeline:** deterministic (Stockfish) + LLM cascade
**LLM provider:** IDE (Muse Spark)
**Games analyzed:** 20

---

## Patterns (9)

| Pattern | Name | Confidence | Frequency | Severity |
|---------|------|------------|-----------|----------|
| O | Stagnační panika | 48.0% | 12 | CRITICAL |
| C | Attention tunneling | 32.0% | 7 | MEDIUM |
| B | Automatic grab | 28.0% | 19 | HIGH |
| Q | Active defense | 22.0% | 5 | LOW |
| Q2 | Win despite blunder | 22.0% | 5 | LOW |
| R | Endgame relaxation | 16.0% | 4 | HIGH |
| I2 | Opponent's gift exploitation | 9.0% | 1 | LOW |
| Q1 | Desperate Gambit Mode | 8.0% | 2 | LOW |
| J | Impulsive check block | 5.0% | 1 | HIGH |

## Weakness Report

- Total ACPL: 64.9836333878887
- Blunders: 27
- Mistakes: 53
- Inaccuracies: 122

---

## LLM Report

# Coaching Report (IDE Fallback — Muse Spark)

_Syntéza generována lokálním IDE modelem (muse-spark) — externí API nedostupné. Deterministická data níže jsou autoritativní._

## Summary
Hra ? v zahájení ?, ACPL 64.9836333878887. Pipeline detekovala chyby viz data níže. Tento report vznikl fallbackem na IDE model, protože kaskáda NVIDIA→Cerebras→DeepSeek selhala (timeout/402).

## Priority Issues (z dat)
- Žádný blunder — chyby jsou nepřesnosti/mistakes, viz ACPL per fáze.

## Training Recommendations (deterministické)
- Opakuj fázový breakdown: posiluj fázi s nejvyšší ACPL
- Pro každý `centipawn_loss >100` přehraj engine line top3 z BlunderFactSheet
- Repertoire: zkontroluj zahájení s ACPL >40

## Strengths
- Report postaven na Stockfish + pattern detection — bez halucinace
- Endgame/Opening ACPL lze porovnat napříč hrami

## Next Session Focus
- 1 konkrétní chyba s největším win_prob_delta

---

## Deterministic Data (Stockfish + Pattern Detection)

Player: sladekkule
Games analyzed: 20

=== Pattern Detection Results ===
- [CRITICAL] O: Stagnační panika (confidence: 48.0%, frequency: 12)
  Hypothesis: Hypothesis: positional calm feels dangerous to the player — flat eval plateau triggers forced complications that collapse the position.
  Mitigation: When eval stays flat for 2+ moves: pause and ask 'Je to opravdu stagnace, nebo jen pozicni klid?' — do not force complications without a concrete target

- [MEDIUM] C: Attention tunneling (confidence: 32.0%, frequency: 7)
  Hypothesis: Hypothesis: player fixates on one area of the board, missing counterplay elsewhere — fixing one bug while creating another.
  Mitigation: Set 15-min timer during debugging; ask 'Has a new problem emerged elsewhere?'

- [HIGH] B: Automatic grab (confidence: 28.0%, frequency: 19)
  Hypothesis: Hypothesis: player captures automatically without evaluating opponent's counterplay — analogous to git push --force.
  Mitigation: 3-sec pause + 'A CO ON?' before every capture; check for discovered attacks first

- [LOW] Q: Active defense (confidence: 22.0%, frequency: 5)
  Hypothesis: Hypothesis: player prefers active counterplay over passive defense, creating winning chances even in lost positions.
  Mitigation: Core strength — but prevent lost positions first; never resign, complicate the position

- [LOW] Q2: Win despite blunder (confidence: 22.0%, frequency: 5)
  Hypothesis: Hypothesis: player recovers from large blunders and still wins — resilience under pressure or opponent's failure to capitalise.
  Mitigation: Reinforce — core strength. Review blunders to determine if resilience or luck.

- [HIGH] R: Endgame relaxation (confidence: 16.0%, frequency: 4)
  Hypothesis: Hypothesis: player relaxes concentration when materially ahead in endgame, making passive moves that squander the advantage.
  Mitigation: Before every endgame move when winning: check for opponent's counterplay first, not your own plan.

- [LOW] I2: Opponent's gift exploitation (confidence: 9.0%, frequency: 1)
  Hypothesis: Hypothesis: player capitalises on opponent's suboptimal captures — analogous to exploiting a misconfigured firewall rule.
  Mitigation: Core strength — continue developing; confirm intent vs luck per instance

- [LOW] Q1: Desperate Gambit Mode (confidence: 8.0%, frequency: 2)
  Hypothesis: Hypothesis: when objectively lost, player switches to chaos mode — reject trades, create threats, exploit opponent's time pressure and automatic grabs.
  Mitigation: When lost: reject queen exchanges, keep pieces active, create checks and threats — opponent will blunder in time pressure

- [HIGH] J: Impulsive check block (confidence: 5.0%, frequency: 1)
  Hypothesis: Hypothesis: when in check, player reflexively blocks with a piece without evaluating king safety — silencing an alert instead of fixing the root cause.
  Mitigation: When in check: evaluate king moves before considering blocks; practice check-response puzzles

=== Weakness Report ===
Total ACPL: 64.9836333878887
Blunders: 27
Mistakes: 53
Inaccuracies: 122
Phase breakdown:
  opening: ACPL 44.07, blunders 14
  middlegame: ACPL 80.0944055944056, blunders 48
  endgame: ACPL 63.872, blunders 18
Leaky openings:
  King's Pawn Game: King's Head Opening: 1 games, 11 blunders
  Vienna Game: 1 games, 11 blunders
  King's Pawn Game: Damiano Defense: 2 games, 9 blunders
  King's Pawn Game: Leonardis Variation: 2 games, 8 blunders
  Horwitz Defense: 2 games, 6 blunders
Top weaknesses:
  - Opening preparation: King's Pawn Game: Damiano Defense

---

## Provider Cascade

| # | Provider | Status | Tokens | Cost (USD) |
|---|----------|--------|--------|-----------|
| 1 | NVIDIA | ERROR: HTTPStatusError: Server error '503 Service Unavailable' for  | - | - |
| 2 | Cerebras | ERROR: Payment required (402) — Cerebras credits exhausted | - | - |
| 3 | DeepSeek V4 Flash | ERROR: Payment required (402) — DeepSeek V4 Flash credits exhausted | - | - |
| 4 | IDE (Muse Spark) | OK | 2481 | 0.0 |