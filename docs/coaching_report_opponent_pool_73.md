# IM Coaching Report: Opponent Pool (73 her)

**Datum:** 2026-07-29
**Analyza:** Pattern pipeline (depth 12) + IM reasoning
**Perspektiva:** Opponent (flipped labels — "win" = opponent won = author loss, "loss" = opponent lost = author win)
**Rozsah:** 73 anonymnich Lichess her
**Vysledek:** 12 W / 61 L (16.4% opponent win rate)

---

## [DATA] Agregované statistiky

| Metrika | Hodnota |
|---------|---------|
| Celkem her | 73 |
| Opponent wins | 12 (16.4%) |
| Opponent losses | 61 (83.6%) |
| Aggregate ACPL | **50.1** |
| Celkem blunderu | 62 |
| Celkem mistake | 113 |
| Celkem inaccuracy | 347 |
| Prumerny blunder rate | 0.85/game |
| Prumerny pocet tahu | 25.7 |

### Per-batch konzistence

| Batch | Games | ACPL | Blunders/g |
|-------|-------|------|-----------|
| 1-20 | 20 | 54.2 | 0.80 |
| 21-40 | 20 | 47.5 | 0.45 |
| 41-60 | 20 | 44.1 | 0.90 |
| 61-73 | 13 | 57.3 | 1.46 |

ACPL variance 44.1-57.3 napříč batchem — konzistentní s jedním pool distribucí (zadny batch nevycníva extremne).

---

## [DATA] Pattern Detection Results

| Pattern | Confidence | Frequency | Severita |
|---------|-----------|-----------|----------|
| **O** — Stagnacni panika | 88% | 44/73 (60%) | critical |
| **B** — Automatic grab | 73% | 27 capture blunders (6.5% z 416 captures) | high |
| **G** — Color as modulator | 70% | 21 games | high |
| **C** — Attention tunneling | 66% | 17 games (max 36 consecutive errors) | medium |
| **Q2** — Win despite blunder | 58% | 8 games | low |
| **J** — Impulsive check block | 57% | 7 games | high |
| **R** — Endgame relaxation | 57% | 7 games | high |
| **Q** — Active defense | 55% | 5 games | low |
| **P** — Visual misrecognition | 53% | 3 games | high |
| **Q1** — Desperate Gambit | 53% | 3 games | low |
| **N** — X-ray pin violation | 53% | 3 games | high |

### Comparison: Opponent patterns vs Author baseline (z 33 her)

| Pattern | Opponent pool (73) | Author (33) | Signal |
|---------|-------------------|-------------|--------|
| O Stagnacni panika | **60%** | 29% | Opponents panic 2× vice |
| J Impulsive block | **9.6%** (7/73) | 5% | Opponents vice impulsivnich bloku |
| C Attention tunneling | **23%** | 5% | Opponents 4.6× vice consec errors |
| G Color asymmetry | 29% | **92%** | Autor ma vyrazne vyssi barevnou asymetrii |
| B Automatic grab | 6.5% captures | 4.5% captures | Podobna, opponents mirne vice |
| Q2 Resilience | 11% | **19%** | Autor ma vyssi resilienci |

---

## [IM] Top 3 nejkritičtější patterny

### 1. O — Stagnační panika (60%, 44 her)

**Nejdominantnější pattern celého poolu.** Tři ze pěti opponentu v každé hře podlehnou stagnační panice — po plochém eval okně (2-3 tahy bez změny) vynutí komplikace, které kolabují pozici.

Konkretni hry s timto patternem: hrLawxDC (nejhorsi hra poolu, ACPL 140.3, 5 blunderu), NnHdTc8h (ACPL 86.0, **6 blunderu** — nejvice v celem poolu), LIs9bhRc (ACPL 98.2, 3 blundery v middlegame).

**Pro autora:** Opponenti panicuji 2× casteji nez autor. To je silna zbran — staci udrzet pozicni tlak bez force, opponent se uzkosti zhrouti sam.

### 2. B — Automatic grab (27 blunder captures, 73%)

27 z 416 captures (6.5%) je blunder — opponent bere figuru automaticky bez vyhodnoceni protihrozby. Konkretni hry: hrLawxDC, 8g78OUn0, 9v3sUv8a, XmAlR7uM, NnHdTc8h, AgZ80H8W.

**Pro autora:** 6.5% chybovost v capturech je zranitelnost. Nabizet figurky s protihrozbou (discovered attack, fork) — opponent je vezme automaticky a spadne do pasti.

### 3. C — Attention tunneling (23%, 17 her)

17 her s consecutive errors (az 36 v rade u nejhorsich pripadu). Opponent se fixuje na jednu oblast desky a prehlizi protihrozbu jinde.

**Pro autora:** Po prvnim blundru opponent casto nasleduje dalsi — hrat aktivne a nebrzdit, opponent se dostahe sam.

---

## [IM] Fázová analýza

Dostupna data ukazuji koncentraci blunderu v **middlegame a endgame**:

- **hrLawxDC** (nejhorsi hra): 5 blunderu — 1 v opening (Nc6, 322cp), 4 v endgame (Kg8 2313cp, Qf1+ 807cp, Rb8 384cp, Ke8 333cp)
- **LIs9bhRc**: 3 blundery, vsechny v middlegame (d5 384cp, h5 640cp, b4 677cp)
- **NnHdTc8h**: 6 blunderu, rozlozeny mezi middlegame a endgame

Pattern R (Endgame relaxation, 7 her) potvrzuje: opponent ve vyhravajici koncovce relaxuje a dela fatalni chyby.

---

## [IM] Tréninková doporučení

### Pro autora (jak vyuzit opponent patterns)

1. **Stagnační panika jako zbraň** — udrzet pozicni tlak bez forcirovani. Po 2-3 tazich plocheho evala opponent vynuti kolaps. Neni treba vyhravat kazdou hru aktivne — staci neprohrat a opponent se zhrouti sam. P>0.8

2. **Automatic grab pasti** — nabizet figurky s protihrozbou (discovered attack, fork, mate threat). 6.5% capture blunder rate znamena, ze kazda 15. vezmuta figura je fatalni chyba. Hypotéza, nutno overit na vetsim vzorku.

3. **Po prvnim blundru zrychlit** — opponent s Attention tunneling (23% her) po prvnim blundru casto nasleduje dalsi. Hrat aktivne a nebrzdit. P>0.8

### Pro opponent pool (co by pomohlo jim)

4. **Pred kazdym capturem: 3s pauza + dotaz "A CO ON?"** — 6.5% capture blunder rate klesne na polovinu. Verifikovat na pristich 50 hrach.

5. **Flat eval → NE force** — misto vynuceni komplikaci pri plochem evalu: overit jestli pozice skutecne stagnuje, nebo je to pozicni klid. 60% her s timto patternem.

6. **Endgame drill: winning conversion** — 7 her (10%) ztraceno ve vyhravajici koncovce. Stack: Stockfish koncovkove pozice + planovani.

---

## [IM] Verdikt

**Opponent pool overall:** ACPL 50.1, blunder rate 0.85/game. To je ~1600-1700 Lichess urovne (odhad). Dominantni slabina: **stagnacni panika** (60% her) a **automatic grab** (6.5% captures).

**Autorova vyhoda:** Oproti autorove baseline (ACPL 32.5, blunder rate 0.39/game) je opponent o 60% slabsí. Autor dominuje v patternu G (barevna asymetrie 92%), opponents dominuji v O (panic) a J (impulsive blocks).

**Treninkova priorita:** Nezlepsovat vlastni hru — soucasna uroven je dostatecna (81.8% win rate). Misto toho: **systematicky vyuzivat opponent patterns** — udrzet tlak bez force, nabizet captures s protihrozbou, po opponentove prvnim blundru zrychlit. Odhad zlepseni: +5-10% win rate (z 81.8% na ~87-92%).

---

*[DATA] vsechna konktretni game ID a ACPL hodnoty overeny z cache. [IM] oznacuje interpretaci autora.*
