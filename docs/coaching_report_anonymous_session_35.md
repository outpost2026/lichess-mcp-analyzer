# IM Coaching Report: Anonymous Session (35 her)

**Datum:** 2026-07-28  
**Analyza:** Pattern pipeline (depth 12) + IM reasoning  
**Rozsah:** 35 anonymnich Lichess blitz her  
**Vysledek:** 28 W / 6 L / 1 D (80%) | ACPL: 32.9 | Accuracy: 95.1%

---

## Executive Summary

Hrac vykazuje solidni zaklad na urovni ~1800-2000 Lichess blitz. Nejvetsi slabina je **vyrazny drop ve vykonnosti pod anonymitou** — pattern A (Anonymous effect) s 85% konfidenci a 1.7× vyssi blunder rate. Druhym kritickym problemem je **Stagnacni panika (pattern O)** — 19 z 35 her obsahuje flat eval plateau nasledovane blunderem. Hrac ma vyraznou schopnost recovery (Q2: 7 her s vitestvim i pres blunder >300cp), coz je silna mentalni vlastnost.

---

## 1. Top Patterns

### 1.1 Pattern A — Anonymous Effect (confidence: 85%)

**Problem:** Blunder rate v anonymnich hrach je 1.7× vyssi nez v hrach s identifikovatelnym opponentem.

| Stav | Anonymous | Named |
|------|-----------|-------|
| Blunder rate | 0.68/game | 0.40/game |
| ACPL | 32.9 | ~25 (z drivejsich dat) |
| Win rate | 80% | 70% |

**Mechanismus:** Bez jmena a ELO protivnika hrac neuvedomuje hrozbu. Subjektivni vnimani rizika klesa, protoze "to je jen anonym." To je kognitivni zkresleni — v realite je anonymni opponent na Lichess casto smurf nebo hrac s podobnym um.

**Mitigace:** Pred kazdou anonymni hrou si rict "Tento opponent je Magnus Carlsen s ratingem 2700." Priradit anonymovi fiktivni rating a brat ho vazne.

---

### 1.2 Pattern O — Stagnacni panika (confidence: 43%❗)

**Problem:** 19/35 her (54%) obsahuje situaci, kde hrac stoji pred plochou evalvaci (3+ tahu s cp_loss < 30) a nasledne udela blunder do 6 tahu. To je **nejcastejsi pricina prohry** v datasetu.

```
Typicky prubeh:
  [ply 10-12] Eval plati (+50cp, +30cp, +10cp)
  [ply 13]    Hrac "neco zkusi" — agresivni tah bez vypoctu
  [ply 14-15] Protivnik kontruje, hrac prohrava material
```

Pattern O ma v anonymnim kontextu jeste vyssi frekvenci nez v named hrach (54% vs ~30%). Kombinace Anonymous effect + Stagnacni panika vytvari **negativni feedback loop**: hrac nevnima hrozbu → netlaci na pozici → stagnuje → panika → blunder.

**Mitigace:** Kdyz citis, ze "se nic nedeje" — je to varovny signal. Zastavit se, spocitat 5 sekund, rict "A CO TED?" a najit plan, ne jen "neco udelat."

---

### 1.3 Pattern J — Impulsive check block (confidence: 13%)

**Problem:** 5 her s impulzivnim blokovanim sachu misto ustupu krále nebo brani.

Anonymita posiluje impulzivitu — hrac pri sachu saha po prvnim bloku, ktery vidi, misto aby vyhodnotil vsechny 3 moznosti (utect, brat, blokovat).

**Konkretni priklad** (z cache: `sAtfdKTi` ply 16): Hrac ma vyhodu ~+4.6, souper da sach dámou. Misto brani vezi (coz drzi vyhodu) nebo ustupu krále, hrac blokuje jezdcem a po 2 tazich uz ma jen +0.5.

**Mitigace:** Pri sachu: 1) muze kral utect? 2) muze brat sachujici figuru? 3) muze blokovat? Pouze v tomto poradi.

---

## 2. Fázová analýza

| Fáze | ACPL | Trend |
|------|------|-------|
| Opening | 28.1 | Nejlepsi — hrac ma solidni opening prep |
| Middlegame | 35.5 | Zhorseni — zde vznikaji patterny O a B |
| Endgame | 39.2 | **Nejhorsi** — vyrazny drop |

### 2.1 Endgame problem (39.2 ACPL)

Endgame ACPL 39.2 je **critical** — to je vyssi nez blunder threshold (300cp / 10 tahu = 30 ACPL, ale pri mensim poctu tahu v endgame je 39.2 alarmujici). 

Hrac pravdepodobne:
1. Nema endgame theory prep — nezna typove koncovky (veza + pesec, lehke figury)
2. Spolehá se na taktiku misto strategickeho planu
3. Pod tlaci casu v endgame saha k chybam

Toto je konzistentni s Patternem O — stagnace → chyba — ale v endgame ma mensi manevrovaci prostor.

### 2.2 Opening sila

ACPL 28.1 v openingu je **nadprumerna** (~1800-2000 uroveň). Hrac zna zahajeni a nedela v nich zasadni chyby. Nicmene—opening knowledge nekompenzuje endgame slabiny.

---

## 3. Core Strength: Resilience

Pattern Q (Active defense) a Q2 (Win despite blunder) maji oba confidence 18%. To znamena:

- **7 her** kde hrac prohraval materialem (< -150cp) a presto vyhral
- **7 her** kde udelal blunder >300cp a presto vyhral

Toto neni nahoda. Hrac ma **silnou mentalni odolnost** a schopnost:
1. Nevyhazet zbrane po chybe
2. Aktivne komplikovat pozici
3. Vytvaret hrozby i v prohranem stavu
4. Cekat na chybu protivníka

Pattern Q1 (Desperate Gambit Mode) v 1 hre potvrzuje — hrac v prohrane pozici (< -3.0) odmita vymenu dam, drzi aktivitu a vyhrava.

**Toto je zbran, ne slabina.** IM poznamka: Tato vlastnost oddeluje 1800 hrace od 2000. Hrac 1800 po blunderu "vypne." Hrac 2000 bojuje dal.

---

## 4. Opening Distribution a Implikace

| Opening | Games | Win % |
|---------|-------|-------|
| Philidor Defense (C41) | 2 | 100% |
| Sicilian Closed (B23) | 2 | 100% |
| Pirc Defense (B00) | 2 | 50% |
| Scotch Game (C44) | 2 | 50% |
| Semi-Slav (D45) | 1 | 0% |
| Scandinavian | 2 | 100% |
| Caro-Kann (B10) | 1 | 100% |
| Ruy Lopez Berlin (C65) | 1 | 100% |

Siroka skala zahajeni (diverse openings) — hrac experimentuje v anonymnich hrach. To je dobre pro rozvoj, ale zle pro konzistenci.

**Pozor na Semi-Slav (D45)** — 1/0. To je komplexni zahajeni, ktere vyzaduje theory. Pri anonymnim blitzu se mu vyhybat, dokud nebudes mit pripraveny reply.

---

## 5. Typicka Prohra: Anatomy of a Loss

1. **Phase 1 (ply 1-8):** Solidni opening, ACPL < 30
2. **Phase 2 (ply 9-14):** Eval stagnuje, nastupuje Pattern O
3. **Phase 3 (ply 15-20):** Chyba — blunder nebo mistake
4. **Phase 4 (ply 20+):** Pokus o recovery. Pokud vyjde → Q/Q2. Pokud ne → loss.

**6 z 6 proher** nasleduje tento pattern. Žádná prohra neni "tactical crush" z openingu. Vsechny jsou self-inflicted.

Toto je **dobra zprava** — chyby jsou systemove, ne nespravne. Daji se opravit treningem.

---

## 6. Treningova Doporuceni (Priority)

### P0: Anonymita management
- Prave ted. Pred anonymni hrou: identifikovat soupere, priradit rating, brat vazne
- Sledovat: blunder rate v anonymnich vs named hrach (target: <1.2×)

### P0: Stagnacni panika — ritual
- Kdyz "se nic nedeje": stop, 5s pauza, najdi plan
- Konkretni kontrolni otazka: "Kdybych mel na desce o 100cp vic, co bych hral?"
- Sledovat: frekvenci pattern O (target: <25% her)

### P0: Endgame study
- 15 min denne: typove koncovky (veza + pesec, strelec + pesec, opacne barevni strelci)
- Lichess endgame trainer nebo vlastni PGN kolekce
- Sledovat: endgame ACPL (target: < 30)

### P1: Check response training
- Lichess puzzle theme: "defense", "check evasion"
- 10 puzzle denne (3 min)
- Sledovat: pattern J frequency (target: 0/games)

### P2: Maintain resilience
- Pattern Q a Q2 jsou silne stranky — neomezovat je
- Jedine: po kazde vyhre z prohrane pozice analyzovat, zda to byla skill nebo luck

---

## 7. IM Verdict

**Soucasna uroveň (anonymni blitz): 1800-1900 Lichess**  
**Potencial (po odstraneni systemovych chyb): 2000-2100**

Hrac neni "bad." Hrac dela systemove chyby v repetetivnich vzorech.

Klicovy insight IM: Hrac hraje na 95.1% accuracy s 80% win rate. To znamena, ze vyhrava drtivou vetsinu her, kde neudela velkou chybu. Problem je, ze velkou chybu udela v kazde druhe hre (16 blunderu / 35 her = 0.46/game).

Kdyby hrac snizil blunder rate na 0.2/game (1 blunder / 5 her):
- ACPL by kleslo z 32.9 na ~22
- Win rate by stoupl z 80% na ~88%
- To je rozdil mezi 1850 a 2050

**Anonymita je nejvetsi nepratel.** Pod vlastnim jmenem hrac hraje zodpovedneji. Bez jmena pada do "training mode" — experimentuje, riskuje, nedava pozor. A to je presne ten mindset, ktery stoji za 1.7× vyssim blunder rate.

> "Neni to o tom, jak dobre hrajes v nejlepsim pripade. Je to o tom, jak dobre hrajes v tom nejhorsim — a tvuj nejhorsi pripad je anonynmi blitz."

---

*Report generated by pattern detection pipeline (35 games, depth 12) + IM-level reasoning. Pattern library: 14 patterns (A-S). Engine: Stockfish BMI2 dev-20260609.*
