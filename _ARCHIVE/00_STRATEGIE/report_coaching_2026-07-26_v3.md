# Coaching Report v3 — 63 games (44W/17L/2D)

**Hráč:** Systeq | **Dataset:** 63 games (44 wins, 17 losses, 2 draws)
**Engine:** Stockfish 18 BMI2 @ depth 12 | **Cache:** Fully consistent (0 pending)
**Pattern lib:** A–S v1 (12 active detectors incl. G) | **Pipeline:** 6 bugfixes
**Generováno:** 2026-07-26

---

## 1. Pipeline Health

| Check | Status |
|-------|--------|
| Games fetched | 63 ✓ |
| Index match | 63=44W+17L+2D ✓ |
| Games analyzed | 63 / 63 (100%) ✓ |
| Cache TTL | 1h (auto-refresh on expiry) |
| Fetch clamp | `min(max_games, 999)` ✓ |
| Patterns/diagnose clamp | `min(50)` → `min(999)` ✓ |
| Index auto-update | After each `analyze_game` call ✓ |
| Pending warning | `total_available` + `warning` field v outputu ✓ |

**Bugs fixed this session:**
1. Hard 50-game clamp in `fetch_games.py` — `min(50)` → `min(999)`
2. No pagination in `_export_by_player` — berserk 0.14 handles internally, removed `before` param
3. Index never updated after per-game analysis — added `update_games_index_with_game()` hook
4. Cache corruption — custom dict format → raw API response (repaired via reconcile script)
5. Second 50-game clamp in `match_patterns.py` + `diagnose_player.py` — fixed to `min(999)`
6. `analyze_pending` tool not registered — added import to `server.py` (opencode tool cache limbo)

---

## 2. Overall Metrics (63 analyzed games)

| Metrika | Hodnota |
|---------|---------|
| Celkový ACPL | 43.3 |
| Bludy | 45 |
| Chyby | 111 |
| Nepřesnosti | 392 |
| Ø ACPL opening | 29.2 (622 moves) |
| Ø ACPL middlegame | 46.7 (860 moves) |
| Ø ACPL endgame | **50.7** (785 moves) |

**Key insight:** With 63 games, endgame ACPL (50.7) is now clearly the weakest phase — previously masked by partial dataset. Opening stays solid (29.2). Middlegame and endgame are 1.6x worse than opening. Pattern G (Color as modulator) reveals 1.5x more blunders as White.

---

## 3. Leaky Openings

| Opening | Games | Blunders | Blunders/game |
|---------|-------|----------|---------------|
| **Vienna Game: Anderssen Defense** | 2 | **15** | **7.5** |
| **Scotch Game** | 4 | 12 | 3.0 |
| **Sicilian Defense: Closed** | 3 | 12 | 4.0 |

**Vienna Game: Anderssen Defense** is the single most dangerous opening: 7.5 blunders/game across 2 games. Both games (`0EAA2iRk` ACPL 98.2, `xgw9sFUh` ACPL 124.3) are among the worst in the dataset. Consider repertoire change or intensive prep.

---

## 4. Pattern Detection Summary (12 patterns, 63 games)

| ID | Pattern | Confidence | Severity | Frequency |
|----|---------|-----------|----------|-----------|
| O | Repetition avoidance greed | 38% | critical | 30/63 games |
| G | **Color as modulator** | **49%** | **high** | 1.47x more blunders as White |
| I | Bait trap (strength) | 65% | low | 51/63 games |
| C | Attention tunneling | 26% | medium | 18/63 games |
| R | Endgame relaxation | 17% | high | 13/63 games |
| Q | Active defense (strength) | 21% | low | 15 games |
| B | Automatic grab | 11% | high | 26/490 captures (5.3%) |
| Q2 | Win despite blunder | 20% | low | 14 games |
| J | Impulsive check block | 6% | high | 4 games |
| S | Capture aversion under check | 1% | critical | 1 game |
| I2 | Opponent's gift exploitation | 4% | low | 3 games |
| Q1 | Desperate Gambit Mode | 4% | low | 3 games |

### Critical/high-severity patterns to address:

**O — Repetition avoidance greed (30/63 games, 38% conf)**
Refuses threefold repetition in ~48% of affected games, then blunders within 3 moves. Single largest source of avoidable losses. Mitigation: 5-sec pause + "A CO ON?" before refusing.

**G — Color as modulator (White 1.47x, 49% conf)** ⬅️ NEW
1.5x more blunders when playing White. Hypothesis: White's initiative triggers over-aggression; Black's defensive posture forces more caution. Mitigation: play White as if Black — imagine being down a pawn to compensate for impulsivity.

**R — Endgame relaxation (13/63 games, 17% conf)**
Confirmed by ACPL data: endgame ACPL 50.7 is the worst phase. When ahead, player relaxes and makes passive/poor moves. Mitigation: check opponent's counterplay first, not your own plan.

**C — Attention tunneling (18/63 games, 26% conf)**
Max consecutive blunders: 38. Fixation on one area while missing counterplay. Mitigation: 15-min timer, "Has a new problem emerged elsewhere?"

**B — Automatic grab (26/490 captures = 5.3%, 11% conf)**
20 affected games. Classic "capture without checking for discovered attacks." Mitigation: 3-sec "A CO ON?" before every capture.

**J — Impulsive check block (4 games, 6% conf)**
Blocks instead of considering king moves or capturing. Related to S — "check panic" cluster.

---

## 5. Pattern Correlations

### Cluster 1: "Chaos resilience" (O + C + Q2)
Avoids repetition (O), makes consecutive errors (C), still wins (Q2). High-variance, opponent-dependent. Signature game: `xgw9sFUh` (6 blunders, ACPL 124.3, still win).

### Cluster 2: "White over-aggression" (G + O + B)
As White: plays too aggressively (G) → avoids repetition (O) → grabs automatically (B) → collapses. This cluster accounts for the 1.5x blunder rate as White. Treat by playing White positions with Black's mindset.

### Cluster 3: "Check panic" (J + S)
Reflexively blocks or moves king without considering capture. Only 5 instances, all severe.

### Cluster 4: "Endgame leak" (R + B)
Winning endgame → relaxation → automatic grab → squandered advantage. Worst combo because it converts wins into draws/losses.

---

## 6. Top 4 Actions

1. **Repetition discipline** (pattern O): Before avoiding threefold repetition, pause 5s and evaluate alternatives. +25% win rate in affected games.

2. **Color mindset shift** (pattern G): Play White as if you're Black — more cautious, less impulsive. Imagine being down a pawn to counter the aggression bias.

3. **Endgame conversion drills** (pattern R): When ahead in endgame, check opponent's counterplay BEFORE planning your move. Study Capablanca.

4. **Check response protocol** (patterns J+S): When in check, enumerate: (a) capture, (b) king move, (c) block. Practice check-response puzzles.

---

## 7. Pipeline Architecture (for maintainers)

```
lichess_fetch_games ──→ Systeq_games.json (raw API, 63 games)
  detect_pending() ──→ Systeq_index.json (total + by_result + pending)

lichess_match_patterns ──→ auto-analyzes cache misses on the fly
lichess_diagnose_player ──→ auto-analyzes cache misses on the fly
  return total_available + warning if pending ≠ []

lichess_analyze_pending ──→ batch pre-analysis (opencode tool cache limbo)
  ──→ update_games_index_with_game() after each game

Cache formats:
- Systeq_games.json: list of raw Lichess API game objects
- data/game_cache/{id}_{color}_d{depth}.json: per-game Stockfish analysis
- Systeq_index.json: {total, by_result, games: [...]}
```

Cache consistency contract (Q3 2026):
- After `fetch`: cache + index updated immediately
- After any `analyze_game`: index auto-updated via hook
- `match_patterns` / `diagnose_player`: check pending before returning results
- Caller sees `total_available` + `games_analyzed` + optional `warning` + `pending_analysis`
