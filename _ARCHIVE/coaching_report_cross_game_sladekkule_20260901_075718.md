# Coaching Report — cross_game (sladekkule)

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
Hra ? v zahájení ?, ACPL ?. Pipeline detekovala chyby viz data níže. Tento report vznikl fallbackem na IDE model, protože kaskáda NVIDIA→Cerebras→DeepSeek selhala (timeout/402).

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

Vytvoř cross-game pattern analysis pro 20 her hráče.

K DISPOZICI:
- Pattern detection: [
  {
    "pattern_id": "O",
    "pattern_name": "Stagnační panika",
    "confidence": 48.0,
    "frequency": 12,
    "severity": "critical",
    "evidence": [
      {
        "affected_games": [
          "8QDwfer2",
          "w7o2GAbg",
          "A3BxHmcS",
          "dRi8fzCE",
          "dA9VZuIz",
          "5sHCPoWg",
          "Vw0V4GVI",
          "J8INsw1j",
          "UEHcMBXU",
          "uK9f10pF",
          "juc5Yoyf",
          "4umZcRpq"
        ],
        "total_games": 20,
        "repetition_confirmed": 0,
        "fallback_heuristic": 12,
        "detail": "Flat eval plateau (3+ moves with <30cp swing) triggered panic — player forced a losing move within 6 moves"
      }
    ],
    "affected_games": [
      "8QDwfer2",
      "w7o2GAbg",
      "A3BxHmcS",
      "dRi8fzCE",
      "dA9VZuIz",
      "5sHCPoWg",
      "Vw0V4GVI",
      "J8INsw1j",
      "UEHcMBXU",
      "uK9f10pF",
      "juc5Yoyf",
      "4umZcRpq"
    ],
    "hypothesis": "Hypothesis: positional calm feels dangerous to the player — flat eval plateau triggers forced complications that collapse the position.",
    "mitigation": "When eval stays flat for 2+ moves: pause and ask 'Je to opravdu stagnace, nebo jen pozicni klid?' — do not force complications without a concrete target"
  },
  {
    "pattern_id": "C",
    "pattern_name": "Attention tunneling",
    "confidence": 32.0,
    "frequency": 7,
    "severity": "medium",
    "evidence": [
      {
        "affected_games": [
          "8QDwfer2",
          "w7o2GAbg",
          "BJUKoLPf",
          "dA9VZuIz",
          "S6KIaZn2",
          "UEHcMBXU",
          "A3BxHmcS"
        ],
        "total_games": 20,
        "max_consecutive_blunders": 18,
        "threshold_consecutive": 2,
        "detail": "Multiple consecutive errors suggest attention breakdown overriding global evaluation"
      }
    ],
    "affected_games": [
      "8QDwfer2",
      "w7o2GAbg",
      "BJUKoLPf",
      "dA9VZuIz",
      "S6KIaZn2",
      "UEHcMBXU",
      "A3BxHmcS"
    ],
    "hypothesis": "Hypothesis: player fixates on one area of the board, missing counterplay elsewhere — fixing one bug while creating another.",
    "mitigation": "Set 15-min timer during debugging; ask 'Has a new problem emerged elsewhere?'"
  },
  {
    "pattern_id": "B",
    "pattern_name": "Automatic grab",
    "confidence": 28.0,
    "frequency": 19,
    "severity": "high",
    "evidence": [
      {
        "blunder_captures": 19,
        "total_captures": 135,
        "blunder_capture_ratio": 0.141,
        "affected_games": [
          "8QDwfer2",
          "w7o2GAbg",
          "dRi8fzCE",
          "dA9VZuIz",
          "5sHCPoWg",
          "Vw0V4GVI",
          "S6KIaZn2",
          "a6UstoSV",
          "DfmqnwTf",
          "eAyNM35p",
          "juc5Yoyf",
          "UEHcMBXU"
        ],
        "total_games": 20
      }
    ],
    "affected_games": [
      "8QDwfer2",
      "w7o2GAbg",
      "dRi8fzCE",
      "dA9VZuIz",
      "5sHCPoWg",
      "Vw0V4GVI",
      "S6KIaZn2",
      "a6UstoSV",
      "DfmqnwTf",
      "eAyNM35p",
      "juc5Yoyf",
      "UEHcMBXU"
    ],
    "hypothesis": "Hypothesis: player captures automatically without evaluating opponent's counterplay — analogous to git push --force.",
    "mitigation": "3-sec pause + 'A CO ON?' before every capture; check for discovered attacks first"
  },
  {
    "pattern_id": "Q",
    "pattern_name": "Active defense",
    "confidence": 22.0,
    "frequency": 5,
    "severity": "low",
    "evidence": [
      {
        "defensive_wins": 5,
        "total_games": 20,
        "threshold_deficit_cp": -150,
        "affected_games": [
          "w7o2GAbg",
          "dA9VZuIz",
          "DfmqnwTf",
          "eAyNM35p",
          "juc5Yoyf"
        ],
        "detail": "Player was materially behind (eval < -150cp) but chose active checks/captures instead of passive defense, and won"
      }
    ],
    "affected_games": [
      "w7o2GAbg",
      "dA9VZuIz",
      "DfmqnwTf",
      "eAyNM35p",
      "juc5Yoyf"
    ],
    "hypothesis": "Hypothesis: player prefers active counterplay over passive defense, creating winning chances even in lost positions.",
    "mitigation": "Core strength — but prevent lost positions first; never resign, complicate the position"
  },
  {
    "pattern_id": "Q2",
    "pattern_name": "Win despite blunder",
    "confidence": 22.0,
    "frequency": 5,
    "severity": "low",
    "evidence": [
      {
        "resilient_wins": 5,
        "total_games": 20,
        "threshold_blunder_cp": 300,
        "affected_games": [
          "w7o2GAbg",
          "dA9VZuIz",
          "Vw0V4GVI",
          "DfmqnwTf",
          "juc5Yoyf"
        ],
        "detail": "Player made at least one large blunder (>300cp) but still won the game — resilience or opponent failed to capitalise"
      }
    ],
    "affected_games": [
      "w7o2GAbg",
      "dA9VZuIz",
      "Vw0V4GVI",
      "DfmqnwTf",
      "juc5Yoyf"
    ],
    "hypothesis": "Hypothesis: player recovers from large blunders and still wins — resilience under pressure or opponent's failure to capitalise.",
    "mitigation": "Reinforce — core strength. Review blunders to determine if resilience or luck."
  },
  {
    "pattern_id": "R",
    "pattern_name": "Endgame relaxation",
    "confidence": 16.0,
    "frequency": 4,
    "severity": "high",
    "evidence": [
      {
        "affected_games": [
          "DfmqnwTf",
          "w7o2GAbg",
          "S6KIaZn2",
          "Vw0V4GVI"
        ],
        "total_games": 20,
        "threshold_eval_before": 300,
        "threshold_cp_loss": 300,
        "condition": "eval_before>300 AND cp_loss>=300 AND phase=endgame"
      }
    ],
    "affected_games": [
      "DfmqnwTf",
      "w7o2GAbg",
      "S6KIaZn2",
      "Vw0V4GVI"
    ],
    "hypothesis": "Hypothesis: player relaxes concentration when materially ahead in endgame, making passive moves that squander the advantage.",
    "mitigation": "Before every endgame move when winning: check for opponent's counterplay first, not your own plan."
  },
  {
    "pattern_id": "I2",
    "pattern_name": "Opponent's gift exploitation",
    "confidence": 9.0,
    "frequency": 1,
    "severity": "low",
    "evidence": [
      {
        "gift_captures": 1,
        "total_games": 20,
        "threshold_eval_jump": 70,
        "affected_games": [
          "dA9VZuIz"
        ],
        "detail": "Player's best captures that turned a slightly worse position into clear advantage — opponent dropped a gift"
      }
    ],
    "affected_games": [
      "dA9VZuIz"
    ],
    "hypothesis": "Hypothesis: player capitalises on opponent's suboptimal captures — analogous to exploiting a misconfigured firewall rule.",
    "mitigation": "Core strength — continue developing; confirm intent vs luck per instance"
  },
  {
    "pattern_id": "Q1",
    "pattern_name": "Desperate Gambit Mode",
    "confidence": 8.0,
    "frequency": 2,
    "severity": "low",
    "evidence": [
      {
        "affected_games": [
          "dA9VZuIz",
          "juc5Yoyf"
        ],
        "total_games": 20,
        "threshold_eval": -3.0,
        "detail": "After losing position (eval < -3.0), player rejected queen exchanges, kept pieces active, created checks/threats, and won"
      }
    ],
    "affected_games": [
      "dA9VZuIz",
      "juc5Yoyf"
    ],
    "hypothesis": "Hypothesis: when objectively lost, player switches to chaos mode — reject trades, create threats, exploit opponent's time pressure and automatic grabs.",
    "mitigation": "When lost: reject queen exchanges, keep pieces active, create checks and threats — opponent will blunder in time pressure"
  },
  {
    "pattern_id": "J",
    "pattern_name": "Impulsive check block",
    "confidence": 5.0,
    "frequency": 1,
    "severity": "high",
    "evidence": [
      {
        "impulsive_blocks": 1,
        "total_games": 20,
        "threshold_cp": 150,
        "affected_games": [
          "juc5Yoyf"
        ],
        "detail": "Player was in check and blocked with a piece instead of capturing the checking piece or retreating the king, leading to material loss or positional collapse"
      }
    ],
    "affected_games": [
      "juc5Yoyf"
    ],
    "hypothesis": "Hypothesis: when in check, player reflexively blocks with a piece without evaluating king safety — silencing an alert instead of fixing the root cause.",
    "mitigation": "When in check: evaluate king moves before considering blocks; practice check-response puzzles"
  }
]
  s výsledky: confidence, frequency, severity, affected_games
- Cache všech her: data/game_cache/*.json (ACPL per game, blunder rate)
- BlunderFactSheets pro všechny blundry napříč hrami
- Weakness report: {
  "total_acpl": 64.9836333878887,
  "blunder_count": 27,
  "mistake_count": 53,
  "inaccuracy_count": 122,
  "phase_weaknesses": {
    "opening": {
      "acpl": 44.07,
      "blunders": 14,
      "move_count": 200
    },
    "middlegame": {
      "acpl": 80.0944055944056,
      "blunders": 48,
      "move_count": 286
    },
    "endgame": {
      "acpl": 63.872,
      "blunders": 18,
      "move_count": 125
    }
  },
  "leaky_openings": [
    {
      "name": "King's Pawn Game: King's Head Opening",
      "games": 1,
      "blunders": 11
    },
    {
      "name": "Vienna Game",
      "games": 1,
      "blunders": 11
    },
    {
      "name": "King's Pawn Game: Damiano Defense",
      "games": 2,
      "blunders": 9
    },
    {
      "name": "King's Pawn Game: Leonardis Variation",
      "games": 2,
      "blunders": 8
    },
    {
      "name": "Horwitz Defense",
      "games": 2,
      "blunders": 6
    }
  ],
  "top_weaknesses": [
    "Opening preparation: King's Pawn Game: Damiano Defense"
  ]
}

---

## Provider Cascade

| # | Provider | Status | Tokens | Cost (USD) |
|---|----------|--------|--------|-----------|
| 1 | NVIDIA | ERROR: HTTPStatusError: Server error '503 Service Unavailable' for  | - | - |
| 2 | Cerebras | ERROR: Payment required (402) — Cerebras credits exhausted | - | - |
| 3 | DeepSeek V4 Flash | ERROR: Payment required (402) — DeepSeek V4 Flash credits exhausted | - | - |
| 4 | IDE (Muse Spark) | OK | 6089 | 0.0 |