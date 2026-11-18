# Coaching Report — single_game (6ERH4PMw)

**Generated:** 2026-08-31 09:37 UTC
**Pipeline:** deterministic (Stockfish) + LLM cascade
**LLM provider:** fallback (data dump)

---

*No patterns detected.*

---

## LLM Report

# Coaching Report

_LLM unavailable after cascade._

## Data

Vytvoř coaching report pro hru 6ERH4PMw.

K DISPOZICI:
- Výsledek: 1-0, barva: white, zahájení: Sicilian Defense: Grand Prix Attack
- Celková ACPL: 34.0
- Počet chyb: 0 blunderů, 3 chyb, 4 nepřesností
- Blundry: (žádné)
- Fázový breakdown: endgame: ACPL 0.0, 0 chyb; middlegame: ACPL 46.7, 4 chyb; opening: ACPL 25.1, 3 chyb
- Pattern detection: []
- BlunderFactSheet podrobnosti: [
  {
    "game_id": "6ERH4PMw",
    "ply": 23,
    "move_played_san": "f5",
    "move_played_uci": "f4f5",
    "centipawn_loss": 156,
    "eval_before": 129,
    "eval_after": -35,
    "win_prob_before": 0.6775605800851006,
    "win_prob_after": 0.449800646746463,
    "win_prob_delta": -0.2277599333386376,
    "fen_before": "1r1q1rk1/p4pbp/b1pppnp1/2p5/4PP2/2NP1N2/PPPB2PP/1R2QRK1 w - - 8 12",
    "board_state": {
      "was_in_check": false,
      "checking_pieces": [],
      "capture_checking_piece_possible": false,
      "king_capture_possible": false,
      "king_capture_played": false
    },
    "legal_moves": {
      "total": 35,
      "captures": [],
      "king_moves": [
        "Kf2",
        "Kh1"
      ],
      "blocks": [],
      "checks": []
    },
    "engine_lines": [
      {
        "rank": 1,
        "move_san": "b3",
        "eval_cp": 125,
        "win_prob": 0.672509643334985,
        "pv": [
          "b3",
          "Nd7",
          "Na4",
          "e5",
          "f5"
        ]
      },
      {
        "rank": 2,
        "move_san": "e5",
        "eval_cp": 118,
        "win_prob": 0.6635740980412955,
        "pv": [
          "e5",
          "Nd7",
          "b3",
          "dxe5",
          "fxe5"
        ]
      },
      {
        "rank": 3,
        "move_san": "h3",
        "eval_cp": 82,
        "win_prob": 0.615864104253756,
        "pv": [
          "h3",
          "c4",
          "d4",
          "c5",
          "dxc5"
        ]
      }
    ],
    "played_move_rank": 4,
    "phase": "middlegame",
    "pattern_matches": [],
    "detector_version": "DBCL-20260727-dev",
    "context_window": {
      "moves_before": [
        {
          "ply": 21,
          "move_san": "Qe1",
          "eval_after": 110,
          "win_prob_after": 0.6532171672188698
        }
      ],
      "moves_after": [
        {
          "ply": 25,
          "move_san": "exf5",
          "eval_after": -9,
          "win_prob_after": 0.48705085510713625
        }
  

PRAVIDLA:
1. KAŽDÉ konkrétní tvrzení o tahu, cp_loss, eval, FEN, patternu MUSÍ být ověřeno z dat výše.
2. Pokud tool nevrátí affected_games pro pattern — neuváděj konkrétní game_id.
3. Pokud nemáš data — NEVYMÝŠLEJ. Nahraď obecným popisem.
4. [DATA] a [IM] oddělené sekce.

STRUKTURA:
[DATA] Základní info: výsledek, barva, zahájení, celková ACPL, accuracy %
[DATA] Fazovy breakdown:
  - Opening: ACPL, hlavní chyby
  - Middlegame: ACPL, kritické momenty
  - Endgame: ACPL, konverze/obrana
[DATA] Error klasifikace:
  - Blunders: každý s ply, cp_loss, fází, popis
  - Mistakes: seznam
  - Inaccuracies: počet
[DATA] Pattern detection výsledky pro tuto hru
[DATA] BlunderFactSheet: engine_lines top3, legal_moves, board_state pro každý blunder

[IM] Heisman-style error analýza:
  - Která chyba byla nejkritičtější
  - Taktická nebo poziční?
  - Time trouble?
[IM] Tři věci co hráč udělal dobře
[IM] Jedna věc na zlepšení do příště
[IM] Tréninková doporučení

---

## Provider Cascade

| # | Provider | Status | Tokens | Cost (USD) |
|---|----------|--------|--------|-----------|
| 1 | NVIDIA | ERROR: Timeout: The read operation timed out | - | - |
| 2 | Cerebras | ERROR: Payment required (402) — Cerebras credits exhausted | - | - |
| 3 | DeepSeek V4 Flash | ERROR: Payment required (402) — DeepSeek V4 Flash credits exhausted | - | - |