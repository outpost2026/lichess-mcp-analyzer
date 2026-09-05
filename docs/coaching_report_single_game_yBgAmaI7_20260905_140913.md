# Coaching Report — single_game (yBgAmaI7)

**Generated:** 2026-09-05 14:09 UTC
**Pipeline:** deterministic (Stockfish) + LLM cascade
**LLM provider:** IDE (Muse Spark)

---

*No patterns detected.*

---

## LLM Report

# Coaching Report (IDE Fallback — Muse Spark)

_Syntéza generována lokálním IDE modelem (muse-spark) — externí API nedostupné. Deterministická data níže jsou autoritativní._

## Summary
Hra 1-0 v zahájení Sicilian Defense: Closed, Traditional, ACPL 21.3. Pipeline detekovala chyby viz data níže. Tento report vznikl fallbackem na IDE model, protože kaskáda NVIDIA→Cerebras→DeepSeek selhala (timeout/402).

## Priority Issues (z dat)
- Kritický moment: (žádné)
-
- Fázově nejslabší: endgame: ACPL 0.0, 0 chyb; middlegame: ACPL 31.3, 5 chyb; opening: ACPL 8.6, 0 chyb

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

Vytvoř coaching report pro hru yBgAmaI7.

K DISPOZICI:
- Výsledek: 1-0, barva: white, zahájení: Sicilian Defense: Closed, Traditional
- Celková ACPL: 21.3
- Počet chyb: 0 blunderů, 0 chyb, 5 nepřesností
- Blundry: (žádné)
- Fázový breakdown: endgame: ACPL 0.0, 0 chyb; middlegame: ACPL 31.3, 5 chyb; opening: ACPL 8.6, 0 chyb
- Pattern detection: []
- BlunderFactSheet podrobnosti: []

---

## Provider Cascade

| # | Provider | Status | Tokens | Cost (USD) |
|---|----------|--------|--------|-----------|
| 1 | NVIDIA | ERROR: HTTPStatusError: Server error '503 Service Unavailable' for  | - | - |
| 2 | Cerebras | ERROR: Payment required (402) — Cerebras credits exhausted | - | - |
| 3 | DeepSeek V4 Flash | ERROR: Payment required (402) — DeepSeek V4 Flash credits exhausted | - | - |
| 4 | IDE (Muse Spark) | OK | 1088 | 0.0 |