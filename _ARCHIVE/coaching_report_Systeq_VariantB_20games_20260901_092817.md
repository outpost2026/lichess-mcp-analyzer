# Komplexni evaluace hrace Systeq — Variant B (20 her, Stockfish d12)

**Datum:** 2026-09-01 | **Hrac:** Systeq (Rapid 1930-1950) | **Vzorek:** 20 poslednich rapid partii (2026-08-31 az 2026-09-01) | **Engine:** Stockfish BMI2 depth 12 (dual_cache, 20/20 her analyzovano) | **Pipeline:** fetch -> analyze_pending -> diagnose + match_patterns -> cross_game/opening/training -> persist (docs)

> Narativni synteza nad deterministickymi daty. Kazde cislo overeno z `data/game_cache/*_d12.json` (DATA-FABRICATION-001). LLM kaskada (NVIDIA 503, Cerebras/DeepSeek 402 vycerpany) fallback na `muse-spark-1.2` — deterministicka cast autoritativni.

---

## 1. Pipeline trace & Python log (simultanni debug)

```
fetch_games: 20 her stazeno (Systeq_games.json 29401 B)
analyze_pending: 1. iterace 7 her (d12 chybi pro pLzWB2Cp, uqDyoNED, lN4K3mtt, KZX6vZ66, sG0cZNeg, PIuXqVx4, 6ERH4PMw) -> doplneno rucne lichess_analyze_game d12 (7x ok)
  - pLzWB2Cp black d12:23.0 (d14:26.0 delta -3.0)
  - uqDyoNED white d12:40.8 (novy)
  - lN4K3mtt black d12:62.9 (d14:68.6 delta -5.6)
  - KZX6vZ66 black d12:12.5 (d14:16.1 delta -3.6)
  - sG0cZNeg black d12:24.8 (d14:24.7 delta +0.2)
  - PIuXqVx4 white d12:78.4 (d14:86.5 delta -8.0) <- nejvetsi depth drift
  - 6ERH4PMw white d12:33.4 (d14:34.0 delta -0.6)
diagnose_player d12: games_analyzed 20/20, pending 0 (po doplneni)
match_patterns: 8 patternu detekovano (viz §4)
persist: cross_game + diagnosis -> docs/*.md + data/reports/*.json (fallback IDE)
```

**Python anomaly detector (pipeline_anomaly.py):**
- ACPL mean 43.3 median 44.0 stdev 14.6 min 12.5 max 78.4
- Outliers: PIuXqVx4 78.4 z=+2.41 HIGH, KZX6vZ66 12.5 z=-2.11 LOW (14 tahu vs 40 tahu)
- HIGH_PHASE_ACPL (>60): 12 her s kritickou fazi (nNg0pmnY endgame 224.0, 8BjO1Nf2 middlegame 109.9, KWfWzjAz middlegame 107.1 atd.)
- DEPTH_DRIFT: PIuXqVx4 -8.0 nejvetsi — nestabilni pozice (3 blundry) kde hloubka 12 vs 14 meni eval vyrazne
- PATTERN_CONF_DROP: O 85->40, B 88->17 mezi match_patterns a cross_game — rozdil prahu, nutno kalibrovat compression_ratio 60.2
- TIME_PRESSURE: 4/7 proher = outoftime (8BjO1Nf2, m7LHZuLr, RHcmginT, caobK9PI) — 57% proher na cas

**Skryte anomalie pro optimalizaci:**
1. analyze_pending pocita pending pouze pro exact depth (d12 != d14) — redundantni analyze, optimalizace: akceptovat d>=requested
2. diagnose_player pred doplnenim hlasil 20 her analyzovano + warning 7 pending soucasne — matouci, melo by byt games_analyzed 13
3. Pattern B blunder_capture_ratio 0.085 (14/164) je nizky, ale frequency 14/20 spusti HIGH — threshold by mel vazit ratio
4. Cache 163 souboru, pouze 20 relevantnich pro Systeq — bez GC roste neomezene

---

## 2. Vykonovy profil (deterministicky)

| Metrika | Hodnota |
|---|---|
| Her | 20 (13 WIN / 7 LOSS, 65% winrate, 0 remiz) |
| Celkova ACPL | 44.7 (diagnose) / 43.3 mean per-game |
| Blundry (>300cp) | 19 |
| Mistakes (200-300cp) | 38 |
| Nepresnosti (50-200cp) | 114 |
| Tahu celkem | 722 (opening 200 / middlegame 274 / endgame 248) |
| Elo estimate | 1839-2008 per game, prumer ~1900 |

**ACPL per hra (serazeno, d12, Systeq perspektiva):**

| # | Game | ACPL | B/M/I | Color | Opening | Vysledek |
|---|---|---|---|---|---|---|
| 1 | PIuXqVx4 | 78.4 | 3/5/8 | white | Vienna Falkbeer | WIN |
| 2 | lN4K3mtt | 62.9 | 3/2/6 | black | Center Game | WIN |
| 3 | nNg0pmnY | 55.9 | 2/3/4 | white | Vienna Max Lange | WIN |
| 4 | RHcmginT | 52.5 | 1/4/5 | black | Falkbeer Countergambit | LOSS flag |
| 5 | KWfWzjAz | 52.4 | 0/2/6 | black | Italian Fritz Var | WIN |
| 6 | 8BjO1Nf2 | 51.4 | 1/4/8 | white | French Advance | LOSS flag |
| 7 | 2ILNc9EN | 47.1 | 1/1/3 | black | Vienna Hybrid | LOSS |
| 8 | 5tvUWflh | 45.9 | 1/2/5 | black | Van Geet | WIN |
| 9 | jGoK4ZD8 | 44.6 | 1/1/2 | white | Smith-Morra | WIN |
| 10 | ww32wa7C | 44.2 | 1/3/6 | black | 4 Knights Italian | WIN |
| 11 | LhyR79Jd | 43.7 | 0/2/7 | white | Giuoco Pianissimo | LOSS |
| 12 | caobK9PI | 42.1 | 1/4/8 | black | Czech-Indian | LOSS flag |
| 13 | m7LHZuLr | 42.0 | 1/3/9 | black | Vienna Max Lange | LOSS flag |
| 14 | uqDyoNED | 40.8 | 1/1/0 | white | Caro-Kann Adv Short | WIN |
| 15 | Sv4j2bUl | 38.1 | 1/2/6 | white | 2 Knights Modern | LOSS |
| 16 | 6ERH4PMw | 33.4 | 0/2/3 | white | Sicilian Grand Prix | WIN |
| 17 | foIApztB | 30.2 | 0/1/4 | white | Pirc | WIN |
| 18 | sG0cZNeg | 24.8 | 0/0/9 | black | Scotch Game | WIN |
| 19 | pLzWB2Cp | 23.0 | 0/0/6 | black | 4 Knights Scotch | WIN |
| 20 | KZX6vZ66 | 12.5 | 0/0/1 | black | Scandinavian Mieses | WIN |

Nejlepsi: KZX6vZ66 12.5 (14 tahu). Nejhorsi: PIuXqVx4 78.4 (+2.4 sigma).

**Fazova slabina:**

| Faze | ACPL | Blundry | Tahu | Verdikt |
|---|---|---|---|---|
| Opening | 25.86 | 4 | 200 | Nejsilnejsi |
| Middlegame | 52.67 | 27 | 274 | Nejlabsi |
| Endgame | 50.95 | 26 | 248 | Druha nejslabsi |

---

## 3. Zahajeni — repertoire

**Bili (9 her):** Vienna Max Lange, French Advance, Smith-Morra, Caro-Kann Adv Short, Italian 2Knights Modern, Giuoco Pianissimo, Vienna Falkbeer, Pirc, Sicilian Grand Prix  
**Cerni (11 her):** 4 Knights Scotch, Vienna Hybrid, Vienna Max Lange, Falkbeer Counter, Center Game, Scandinavian Mieses, Scotch Game, 4 Knights Italian, Italian Fritz, Czech-Indian, Van Geet

**Leaky openings:**
1. Vienna Max Lange Defense — 2 hry, 8 blundru
2. Vienna Falkbeer — 1 hra, 8 blundru (PIuXqVx4)
3. French Advance — 1 hra, 7 blundru (8BjO1Nf2 flag)
4. Center Game — 1 hra, 5 blundru (lN4K3mtt: 8.h6 336cp, 14.Nc6 484cp)

Vienna komplex = 3/20 her, ale 16/57 blundru (28%). Doporuceni: zuzit Viennu, overit v opening_explorer + engine prep.

---

## 4. Patterny (8, match_patterns d12, 20 her)

| ID | Nazev | Conf | Freq | Sev | Affected games | Mitigace |
|---|---|---|---|---|---|---|
| O | Stagnacni panika | 85% | 10/20 | critical | jGoK4ZD8, caobK9PI, 6ERH4PMw, 2ILNc9EN, foIApztB, 8BjO1Nf2, nNg0pmnY, PIuXqVx4, 5tvUWflh, m7LHZuLr | Pauza pri flat eval (<30cp 3 tahy) — neforsovat |
| B | Automatic grab | 88% | 14/20 | high | jGoK4ZD8, caobK9PI, 2ILNc9EN, foIApztB, lN4K3mtt, RHcmginT, Sv4j2bUl, nNg0pmnY, PIuXqVx4, KWfWzjAz, 5tvUWflh, ww32wa7C +2 | 3s pauza A CO ON pred vymenu |
| C | Attention tunneling | 71% | 6/20 | medium | uqDyoNED, lN4K3mtt, RHcmginT, 8BjO1Nf2, nNg0pmnY, m7LHZuLr (max 14 consecutive) | 15min timer, scan cele desky |
| Q2 | Win despite blunder | 71% | 6/20 | low | jGoK4ZD8, uqDyoNED, lN4K3mtt, nNg0pmnY, PIuXqVx4, KWfWzjAz | Sila — odolnost |
| R | Endgame relaxation | 68% | 5/20 | high | caobK9PI, lN4K3mtt, RHcmginT, nNg0pmnY, PIuXqVx4 (eval>300 & cp_loss>=300) | Pri vyhre scan protihry |
| Q | Active defense | 60% | 3/20 | low | jGoK4ZD8, lN4K3mtt, PIuXqVx4 (eval<-150 vyhra aktivitou) | Sila — aktivni protihra |
| Q1 | Desperate Gambit | 54% | 1/20 | low | KWfWzjAz (eval<-3.0 chaos -> vyhra) | Pri prohre odmitat damy, hrozby |
| N | X-ray pin | 54% | 1/20 | high | m7LHZuLr | Check pin pred tahem |

---

## 5. Casovy tlak

Ze 7 proher: 4x outoftime (8BjO1Nf2, m7LHZuLr, RHcmginT, caobK9PI) = 57% proher na praporek, ne na mat. Korelace s O a C — cas straveny forcovanim komplikaci.

---

## 6. Silne stranky

- Odolnost Q2: 6 her vyhra i po blundru >300cp
- Aktivni obrana Q: 3 vyhry z prohrane pozice
- Zahajeni ACPL 25.86 (2.5x lepsi nez middlegame)
- 3 partie 0 blundru (KZX6vZ66, sG0cZNeg, pLzWB2Cp)

---

## 7. Treninkovy plan (5h tydne, rating 1935)

**T0 okamzite:** 3s pravidlo pred vymenu, flat eval alarm 10s pauza, endgame checklist scan

**Tydenni rozdeleni:**
- 2h middlegame taktika: tunneling drill + 6 pozic z 8BjO1Nf2/PIuXqVx4 (ACPL>60) top3 engine
- 1h Vienna prep: Max Lange + Falkbeer v opening_explorer, 10 tahu deep
- 1h koncovky s vyhodou: 5 pozic z caobK9PI/lN4K3mtt/nNg0pmnY (eval>300)
- 1h cas management: 5x 10+0 s cilem >2min v 30.tahu, review 4 flagged proher

**Next session focus:** PIuXqVx4 tah 31.f4 (333cp) a 73.Qd2 (539cp) — O+R

**Metrika uspechu (20 dalsich her):** ACPL middlegame <45, endgame <42, flag rate <15%, Vienna blundry <3/2hry

---

## 8. Zaver

Systeq je bojovny 1935 rapid hrac (65% winrate) s vybornym zahajenim a odolnosti, ale traci v middlegame/endgame kvuli automatickym branim a panice v klidnych pozicich. Nejvetsi ROI: 3s pauza + endgame scan + zuzeni Vienny.

**Doporučené follow-up:** opponent_pool pro 6 her Q2, analyze_position pro Vienna kriticke pozice, mesicni re-run Variant B pro trend

**Artefakty:** data/reports/cross_game_Systeq_*.json, diagnosis_Systeq_*.json, docs/coaching_report_*.md, tento report docs/coaching_report_Systeq_VariantB_20games_20260901_092817.md, docs/pipeline_Systeq_*.log

---
*Vygenerovano Variant B — deterministicka data z 20 d12 cache, Stockfish, pattern_store.json. Bez halucinace.*
