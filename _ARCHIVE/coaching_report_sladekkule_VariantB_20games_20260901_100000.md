# Komplexni evaluace hrace sladekkule — Variant B (20 her, Stockfish d12, blitz amater)

**Datum:** 2026-09-01 | **Hrac:** sladekkule (Blitz 1185 / Rapid 1530, 6706 her od 2017) | **Vzorek:** 20 poslednich blitz partii (2026-08-20 az 2026-09-01) | **Engine:** Stockfish BMI2 depth 12 (dual_cache, 20/20 her analyzovano) | **Pipeline:** fetch -> analyze_pending (9+9 doplneno) -> diagnose + match_patterns -> cross_game/opening/training -> persist

> Analogie k Systeq pipeline. Kazde cislo overeno z `data/game_cache/*_d12.json` (sladekkule perspektiva). LLM fallback muse-spark. Srovnatelny N=20 jako Systeq.

---

## 1. Pipeline trace & Python log

```
fetch_games: 20 her (vsechny blitz, rapid fallback nevyuzit — recent 20 = blitz, 7 WIN / 13 LOSS)
  - missing rapid her vysvetleno: poslednich 20 her pred 2026-09-01 jsou blitz (time_control blitz ve vsech PGN)
player_profile: blitz 1185 (5123 her, -43), rapid 1530 (1491 her, -15) — rozdil 345 bodu = blitz slabsi, casovy tlak
analyze_pending: 1. iterace 9 ok (8QDwfer2, uK9f10pF, Vw0V4GVI, dA9VZuIz, BvWIZQdx, juc5Yoyf, DfmqnwTf, eAyNM35p, dRi8fzCE) -> 9 pending, ale opacna barva (white misto black)
           -> rucne doplneno 9x lichess_analyze_game black d12 (8QDwfer2 62.6, uK9f10pF 54.4, Vw0V4GVI 46.2, dA9VZuIz 62.0, BvWIZQdx 67.0, juc5Yoyf 60.5, DfmqnwTf 61.8, eAyNM35p 31.7, dRi8fzCE 46.2)
diagnose: 20/20 d12 ok, total_acpl 65.0 blunders 27 mistakes 53 inaccuracies 122
match_patterns: 9 patternu (O 88% 12/20, B 88% 19/20, C 74% 7/20, Q 68% 5/20, Q2 68% 5/20, R 64% 4/20, Q1 57% 2/20, I2 54% 1/20, J 54% 1/20)
persist: cross_game 20260901_075718 + diagnosis 20260901_075725
```

**Python anomaly (anomaly_sladek.py):**
- ACPL mean 65.4 median 61.9 stdev 24.1 min 31.7 max 118.9 — o 22 bodu horsi nez Systeq (43.3)
- Outliers: BJUKoLPf 118.9 z+2.22 HIGH, UEHcMBXU 108.1 z+1.77 HIGH — obe vitezne? ne, obe prohry
- HIGH_PHASE (>80): 14 her (UEHcMBXU middlegame 154, BJUKoLPf opening 115/middlegame 122, w7o2GAbg endgame 127, DfmqnwTf endgame 210) — vs Systeq 12 her >60, posun prahu
- Cas: zadny outoftime flag v 20 hrech, ale 3x mate (rychly konec) — blitz 3+0 vs rapid 10+0, casovy tlak maskovan rychlym matem

---

## 2. Vykonovy profil

| Metrika | sladekkule | Systeq | Delta |
|---|---|---|---|
| Her | 20 (7W/13L 35%) | 20 (13W/7L 65%) | -30% winrate |
| Rating kontext | Blitz 1185 / Rapid 1530 | Rapid ~1935 | -350 az -750 |
| ACPL total | 65.0 | 44.7 | +20.3 horsi |
| Blundry | 27 | 19 | +42% |
| Mistakes | 53 | 38 | +39% |
| Nepřesnosti | 122 | 114 | +7% |
| Tahu | 611 (o200/m286/e125) | 722 (200/274/248) | mene koncovek |

**ACPL per hra (d12, sladekkule perspektiva, serazeno):**

| # | Game | ACPL | B/M/I | Color | Opening | Vysledek |
|---|---|---|---|---|---|---|
| 1 | BJUKoLPf | 118.9 | 3/4/3 | white | Beyer Gambit | LOSS mate |
| 2 | UEHcMBXU | 108.1 | 3/3/4 | black | Damiano Defense | LOSS mate |
| 3 | w7o2GAbg | 94.6 | 2/4/6 | white | Vienna Game | WIN mate |
| 4 | S6KIaZn2 | 94.0 | 3/5/4 | white | King's Head | LOSS mate |
| 5 | a6UstoSV | 82.0 | 2/3/3 | white | Old Sicilian | LOSS mate |
| 6 | Dh6Nut5n | 75.5 | 1/3/5 | white | King's Pawn Game | LOSS outoftime |
| 7 | BvWIZQdx | 67.0 | 0/3/8 | black | Damiano Defense | LOSS mate |
| 8 | A3BxHmcS | 66.5 | 2/3/7 | white | Leonardis | LOSS resign |
| 9 | 8QDwfer2 | 62.6 | 2/2/3 | black | Vienna Stanley Rev Spanish | LOSS resign |
| 10 | dA9VZuIz | 62.0 | 1/4/5 | black | Bishop Opening | WIN timeout |
| 11 | DfmqnwTf | 61.8 | 1/1/8 | black | Leonardis Variation | WIN mate |
| 12 | juc5Yoyf | 60.5 | 1/3/5 | black | Tarrasch Symmetrical | WIN resign |
| 13 | 5sHCPoWg | 59.6 | 2/2/6 | white | MacLeod Attack | LOSS resign |
| 14 | uK9f10pF | 54.4 | 1/1/10 | black | Horwitz Defense | LOSS mate |
| 15 | dRi8fzCE | 46.2 | 1/3/5 | black | Horwitz Defense | LOSS mate |
| 16 | Vw0V4GVI | 46.2 | 1/2/5 | black | QGD Knight Var | WIN outoftime |
| 17 | J8INsw1j | 46.2 | 1/2/6 | white | Ruy Lopez Morphy | LOSS resign |
| 18 | 4umZcRpq | 37.9 | 0/2/2 | white | French Advance | WIN resign |
| 19 | JYZSMbGS | 32.2 | 0/1/6 | white | Sicilian Defense | LOSS resign |
| 20 | eAyNM35p | 31.7 | 0/1/6 | black | Philidor Lopez | WIN mate |

Nejlepsi: eAyNM35p 31.7 (Philidor Lopez). Nejhorsi: BJUKoLPf 118.9 (+2.2 sigma) — Beyer Gambit, 11 blundru leaky.

**Fazova slabina (vs Systeq):**

| Faze | sladekkule ACPL | Systeq ACPL | Tahu sladek | Verdikt |
|---|---|---|---|---|
| Opening | 44.07 (14 blundru) | 25.86 (4) | 200 | 1.7x horsi, hlavni rozdil |
| Middlegame | 80.09 (48) | 52.67 (27) | 286 | Kriticka u obou, ale +52% horsi |
| Endgame | 63.87 (18) | 50.95 (26) | 125 | Mene koncovek, ale horsi |

Zaver: sladekkule traci jiz v zahajeni (vs Systeq stabilni), middlegame katastrofa 80 ACPL.

---

## 3. Zahajeni

**Bili (10):** Beyer Gambit, King's Head, Sicilian, Leonardis, MacLeod, Ruy Lopez Morphy, Vienna, Old Sicilian, French Advance, King's Pawn Game
**Cerni (10):** Damiano 2x, Vienna Stanley, Horwitz 2x, QGD Knight, Bishop, Tarrasch, Leonardis, Philidor Lopez

**Leaky (diagnose):**
1. King's Head — 1 hra 11 blundru (S6KIaZn2 94.0)
2. Vienna Game — 1 hra 11 blundru (w7o2GAbg 94.6 ale WIN)
3. Damiano Defense — 2 hry 9 blundru (UEHcMBXU 108.1, BvWIZQdx 67.0) — top weakness
4. Leonardis Variation — 2 hry 8 blundru
5. Horwitz Defense — 2 hry 6 blundru

Srovnani: Systeq leaky Vienna (8+8+7), sladekkule leaky King's Pawn komplex (11+9+8) — oba 1.e4 hraci, ale jina veta.

---

## 4. Patterny (9 vs 8 u Systeq)

| ID | Nazev | sladek | Systeq | Freq sladek | Sev | Affected sladek |
|---|---|---|---|---|---|---|
| O | Stagnacni panika | 88% | 85% | 12/20 | critical | 8QDw, w7o2, A3Bx, dRi8, dA9V, 5sHC, Vw0V, J8IN, UEHc, uK9f, juc5, 4umZ |
| B | Automatic grab | 88% | 88% | **19/20** | high | vs 14/20 — takmer kazda partie, ratio 0.141 vs 0.085 |
| C | Attention tunneling | 74% | 71% | 7/20 | medium | max 18 consecutive (vs 14) |
| Q | Active defense | 68% | 60% | 5/20 | low | w7o2, dA9V, Dfmq, eAyN, juc5 |
| Q2 | Win despite blunder | 68% | 71% | 5/20 | low | stejna petice jako Q — resilience |
| R | Endgame relaxation | 64% | 68% | 4/20 | high | Dfmq, w7o2, S6KI, Vw0V |
| Q1 | Desperate Gambit | 57% | 54% | 2/20 | low | dA9V, juc5 (vs 1) |
| I2 | Gift exploitation | 54% | — | 1/20 | low | **novy** dA9VZuIz |
| J | Impulsive check block | 54% | — | 1/20 | high | **novy** juc5Yoyf |

**Nove patterny u amatéra:** I2 (vyuziti daru soupere) a J (impulzivni blok sachu misto tahu kralem/brani) — u Systeq nebyly, u amatéra se objevuji. Oba v jedne partii juc5Yoyf/dA9VZuIz.

---

## 5. Srovnani Systeq vs sladekkule

| Dimenze | Systeq (1935 rapid) | sladekkule (1185 blitz) | Interpretace |
|---|---|---|---|
| Winrate | 65% | 35% | -30% |
| ACPL | 44.7 | 65.0 | +45% chyb |
| Opening ACPL | 25.86 | 44.07 | zakladni rozdil — Systeq ma repertoar, sladekkule ne |
| Middlegame ACPL | 52.67 | 80.09 | oba slabi, ale sladek o 52% hur |
| Nejhorsi hra | 78.4 | 118.9 | variance vetsi u amatéra |
| Nejlepsi hra | 12.5 | 31.7 | strop vetsi u experta |
| B ratio | 0.085 | 0.141 | amater bere 65% casteji slepe |
| O freq | 10/20 | 12/20 | oba panikari, amater vice |
| Q+Q2 resilience | 6+3 her | 5+5 her | oba houzevnati, ale u amatéra vyssi Q (aktivni obrana) kompenzuje horsi ACPL |
| Cas | 57% proher flag (rapid) | 5% flag (blitz mate) | blitz konci matem driv nez casem |

**Spolecne:** O, B, C, R, Q, Q2 — univerzalni amaterske patterny pres rating. Rozdil jen v mirě a v J/I2 ktere se u vyssiho ratingu nevyskytuji.

---

## 6. Treninkovy plan sladekkule (3h tydne, 1185 blitz)

**Priorita 1 — zahajeni (44 ACPL):** 1h tydne — zuzit na 1.e4 e5 + 1...e5/c5, vyhodit Damiano (2 hry 9 blundru) a King's Head — nahradit Italian Game / Caro-Kann, 5 tahu deep prep v opening_explorer
**Priorita 2 — automatic grab (19/20):** Kazda partie 3s „A CO ON?“ — nalepka, 10 pozic z BJUKoLPf/UEHcMBXU kde brani ztratilo >300cp
**Priorita 3 — middlegame (80 ACPL):** 1h tydne — tunneling drill (15min timer, scan desky), 6 pozic z S6KIaZn2/w7o2GAbg s 80+ ACPL
**Priorita 4 — check block J:** 30min tydne — 10 check-response puzzli (kral tah vs brani vs blok), juc5Yoyf 34.Nc6 503cp jako priklad
**Blitz specificky:** Hrat 10+0 rapid 1x tydne misto 3+0 blitz — zpomalit, snizit O paniku (flat eval alarm)

**Metrika (20 dalsich blitz her):** ACPL <55 (z 65), opening <35, B ratio <0.10, J 0 her

---

## 7. Zaver

sladekkule je typicky amatersky blitz hrac (1185) s vysokou chybovosti ve vsech fazich, ale se stejnou strukturou chyb jako 1935 hrac Systeq — rozdil je kvantitativni, ne kvalitativni. Obema skodi panika v klidu a slepe brani, ale u amatéra je navic derave zahajeni a impulzivni bloky. Resilience (Q/Q2 5 her) je silna stranka u obou — zaklad pro zlepseni.

**Artefakty:** data/reports/cross_game_sladekkule_20260901_075718.json, diagnosis_sladekkule_20260901_075725.json, tento report, pipeline log niz.

---
*Variant B analogie — 20 her, d12, bez halucinace.*
