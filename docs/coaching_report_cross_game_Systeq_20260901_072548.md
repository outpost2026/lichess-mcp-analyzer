# Coaching Report — cross_game (Systeq)

**Generated:** 2026-09-01 07:25 UTC
**Pipeline:** deterministic (Stockfish) + LLM cascade
**LLM provider:** IDE (Muse Spark)
**Games analyzed:** 20

---

## Patterns (8)

| Pattern | Name | Confidence | Frequency | Severity |
|---------|------|------------|-----------|----------|
| O | Stagnační panika | 40.0% | 10 | CRITICAL |
| C | Attention tunneling | 27.0% | 6 | MEDIUM |
| Q2 | Win despite blunder | 27.0% | 6 | LOW |
| R | Endgame relaxation | 20.0% | 5 | HIGH |
| B | Automatic grab | 17.0% | 14 | HIGH |
| Q | Active defense | 14.0% | 3 | LOW |
| Q1 | Desperate Gambit Mode | 4.0% | 1 | LOW |
| N | X-ray pin violation | 4.0% | 1 | HIGH |

## Weakness Report

- Total ACPL: 44.65650969529086
- Blunders: 19
- Mistakes: 38
- Inaccuracies: 114

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
    "confidence": 40.0,
    "frequency": 10,
    "severity": "critical",
    "evidence": [
      {
        "affected_games": [
          "jGoK4ZD8",
          "caobK9PI",
          "6ERH4PMw",
          "2ILNc9EN",
          "foIApztB",
          "8BjO1Nf2",
          "nNg0pmnY",
          "PIuXqVx4",
          "5tvUWflh",
          "m7LHZuLr"
        ],
        "total_games": 20,
        "repetition_confirmed": 0,
        "fallback_heuristic": 10,
        "detail": "Flat eval plateau (3+ moves with <30cp swing) triggered panic — player forced a losing move within 6 moves"
      }
    ],
    "affected_games": [
      "jGoK4ZD8",
      "caobK9PI",
      "6ERH4PMw",
      "2ILNc9EN",
      "foIApztB",
      "8BjO1Nf2",
      "nNg0pmnY",
      "PIuXqVx4",
      "5tvUWflh",
      "m7LHZuLr"
    ],
    "hypothesis": "Hypothesis: positional calm feels dangerous to the player — flat eval plateau triggers forced complications that collapse the position.",
    "mitigation": "When eval stays flat for 2+ moves: pause and ask 'Je to opravdu stagnace, nebo jen pozicni klid?' — do not force complications without a concrete target"
  },
  {
    "pattern_id": "C",
    "pattern_name": "Attention tunneling",
    "confidence": 27.0,
    "frequency": 6,
    "severity": "medium",
    "evidence": [
      {
        "affected_games": [
          "uqDyoNED",
          "lN4K3mtt",
          "RHcmginT",
          "8BjO1Nf2",
          "nNg0pmnY",
          "m7LHZuLr"
        ],
        "total_games": 20,
        "max_consecutive_blunders": 14,
        "threshold_consecutive": 2,
        "detail": "Multiple consecutive errors suggest attention breakdown overriding global evaluation"
      }
    ],
    "affected_games": [
      "uqDyoNED",
      "lN4K3mtt",
      "RHcmginT",
      "8BjO1Nf2",
      "nNg0pmnY",
      "m7LHZuLr"
    ],
    "hypothesis": "Hypothesis: player fixates on one area of the board, missing counterplay elsewhere — fixing one bug while creating another.",
    "mitigation": "Set 15-min timer during debugging; ask 'Has a new problem emerged elsewhere?'"
  },
  {
    "pattern_id": "Q2",
    "pattern_name": "Win despite blunder",
    "confidence": 27.0,
    "frequency": 6,
    "severity": "low",
    "evidence": [
      {
        "resilient_wins": 6,
        "total_games": 20,
        "threshold_blunder_cp": 300,
        "affected_games": [
          "jGoK4ZD8",
          "uqDyoNED",
          "lN4K3mtt",
          "nNg0pmnY",
          "PIuXqVx4",
          "KWfWzjAz"
        ],
        "detail": "Player made at least one large blunder (>300cp) but still won the game — resilience or opponent failed to capitalise"
      }
    ],
    "affected_games": [
      "jGoK4ZD8",
      "uqDyoNED",
      "lN4K3mtt",
      "nNg0pmnY",
      "PIuXqVx4",
      "KWfWzjAz"
    ],
    "hypothesis": "Hypothesis: player recovers from large blunders and still wins — resilience under pressure or opponent's failure to capitalise.",
    "mitigation": "Reinforce — core strength. Review blunders to determine if resilience or luck."
  },
  {
    "pattern_id": "R",
    "pattern_name": "Endgame relaxation",
    "confidence": 20.0,
    "frequency": 5,
    "severity": "high",
    "evidence": [
      {
        "affected_games": [
          "caobK9PI",
          "lN4K3mtt",
          "RHcmginT",
          "nNg0pmnY",
          "PIuXqVx4"
        ],
        "total_games": 20,
        "threshold_eval_before": 300,
        "threshold_cp_loss": 300,
        "condition": "eval_before>300 AND cp_loss>=300 AND phase=endgame"
      }
    ],
    "affected_games": [
      "caobK9PI",
      "lN4K3mtt",
      "RHcmginT",
      "nNg0pmnY",
      "PIuXqVx4"
    ],
    "hypothesis": "Hypothesis: player relaxes concentration when materially ahead in endgame, making passive moves that squander the advantage.",
    "mitigation": "Before every endgame move when winning: check for opponent's counterplay first, not your own plan."
  },
  {
    "pattern_id": "B",
    "pattern_name": "Automatic grab",
    "confidence": 17.0,
    "frequency": 14,
    "severity": "high",
    "evidence": [
      {
        "blunder_captures": 14,
        "total_captures": 164,
        "blunder_capture_ratio": 0.085,
        "affected_games": [
          "jGoK4ZD8",
          "caobK9PI",
          "2ILNc9EN",
          "foIApztB",
          "lN4K3mtt",
          "RHcmginT",
          "Sv4j2bUl",
          "nNg0pmnY",
          "PIuXqVx4",
          "KWfWzjAz",
          "5tvUWflh",
          "ww32wa7C"
        ],
        "total_games": 20
      }
    ],
    "affected_games": [
      "jGoK4ZD8",
      "caobK9PI",
      "2ILNc9EN",
      "foIApztB",
      "lN4K3mtt",
      "RHcmginT",
      "Sv4j2bUl",
      "nNg0pmnY",
      "PIuXqVx4",
      "KWfWzjAz",
      "5tvUWflh",
      "ww32wa7C"
    ],
    "hypothesis": "Hypothesis: player captures automatically without evaluating opponent's counterplay — analogous to git push --force.",
    "mitigation": "3-sec pause + 'A CO ON?' before every capture; check for discovered attacks first"
  },
  {
    "pattern_id": "Q",
    "pattern_name": "Active defense",
    "confidence": 14.0,
    "frequency": 3,
    "severity": "low",
    "evidence": [
      {
        "defensive_wins": 3,
        "total_games": 20,
        "threshold_deficit_cp": -150,
        "affected_games": [
          "jGoK4ZD8",
          "lN4K3mtt",
          "PIuXqVx4"
        ],
        "detail": "Player was materially behind (eval < -150cp) but chose active checks/captures instead of passive defense, and won"
      }
    ],
    "affected_games": [
      "jGoK4ZD8",
      "lN4K3mtt",
      "PIuXqVx4"
    ],
    "hypothesis": "Hypothesis: player prefers active counterplay over passive defense, creating winning chances even in lost positions.",
    "mitigation": "Core strength — but prevent lost positions first; never resign, complicate the position"
  },
  {
    "pattern_id": "Q1",
    "pattern_name": "Desperate Gambit Mode",
    "confidence": 4.0,
    "frequency": 1,
    "severity": "low",
    "evidence": [
      {
        "affected_games": [
          "KWfWzjAz"
        ],
        "total_games": 20,
        "threshold_eval": -3.0,
        "detail": "After losing position (eval < -3.0), player rejected queen exchanges, kept pieces active, created checks/threats, and won"
      }
    ],
    "affected_games": [
      "KWfWzjAz"
    ],
    "hypothesis": "Hypothesis: when objectively lost, player switches to chaos mode — reject trades, create threats, exploit opponent's time pressure and automatic grabs.",
    "mitigation": "When lost: reject queen exchanges, keep pieces active, create checks and threats — opponent will blunder in time pressure"
  },
  {
    "pattern_id": "N",
    "pattern_name": "X-ray pin violation",
    "confidence": 4.0,
    "frequency": 1,
    "severity": "high",
    "evidence": [
      {
        "pin_events": 1,
        "total_games": 20,
        "threshold_cp": 100,
        "affected_games": [
          "m7LHZuLr"
        ],
        "detail": "Player blundered by moving a piece that was x-ray pinned to a higher-value piece behind it"
      }
    ],
    "affected_games": [
      "m7LHZuLr"
    ],
    "hypothesis": "Hypothesis: player fails to recognize when their piece is pinned, treating it as free to move -- overlooking the higher-value piece behind it.",
    "mitigation": "Before moving any piece: check if it's pinned to the king or queen. If pinned, verify the move doesn't expose the higher-value piece."
  }
]
  s výsledky: confidence, frequency, severity, affected_games
- Cache všech her: data/game_cache/*.json (ACPL per game, blunder rate)
- BlunderFactSheets pro všechny blundry napříč hrami
- Weakness report: {
  "total_acpl": 44.65650969529086,
  "blunder_count": 19,
  "mistake_count": 38,
  "inaccuracy_count": 114,
  "phase_weaknesses": {
    "opening": {
      "acpl": 25.86,
      "blunders": 4,
      "move_count": 200
    },
    "middlegame": {
      "acpl": 52.67883211678832,
      "blunders": 27,
      "move_count": 274
    },
    "endgame": {
      "acpl": 50.95161290322581,
      "blunders": 26,
      "move_count": 248
    }
  },
  "leaky_openings": [
    {
      "name": "Vienna Game: Max Lange Defense",
      "games": 2,
      "blunders": 8
    },
    {
      "name": "Vienna Game: Falkbeer Variation",
      "games": 1,
      "blunders": 8
    },
    {
      "name": "French Defense: Advance Variation",
      "games": 1,
      "blunders": 7
    },
    {
      "name": "Center Game",
      "games": 1,
      "blunders": 5
    },
    {
      "name": "King's Gambit Declined: Falkbeer Countergambit",
      "games": 1,
      "blunders": 4
    }
  ],
  "top_weaknesses": [
    "Opening preparation: Vienna Game: Max Lange Defense"
  ]
}

---

## Provider Cascade

| # | Provider | Status | Tokens | Cost (USD) |
|---|----------|--------|--------|-----------|
| 1 | NVIDIA | ERROR: HTTPStatusError: Server error '503 Service Unavailable' for  | - | - |
| 2 | Cerebras | ERROR: Payment required (402) — Cerebras credits exhausted | - | - |
| 3 | DeepSeek V4 Flash | ERROR: Payment required (402) — DeepSeek V4 Flash credits exhausted | - | - |
| 4 | IDE (Muse Spark) | OK | 5603 | 0.0 |