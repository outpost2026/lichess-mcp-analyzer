# IM Coaching Report: Anonymous Session (33 her)

**Datum:** 2026-07-28
**Analyza:** Pattern pipeline (depth 12) + IM reasoning
**Rozsah:** 33 anonymnich Lichess her (z txt: vse bez "loss" = win, 6 losses)
**Vysledek:** 26 W / 6 L (81.3%) | ACPL: 32.5 | Blunders: 13 (0.39/game)

---

## Executive Summary

33 her z `.data/lichess_anonymni_partie.txt` — 6 losses, 26 wins. Aggregate ACPL 32.5 je solidni na urovni ~1800-1900 Lichess. Dva dominantni patterny: **G — Color as modulator (92%)** — 2.75× vice blunderu jako White, a **O — Stagnacni panika (29%)** v 12/33 hrach. Hrac ma vyraznou recovery schopnost (Q: 4, Q2: 7, Q1: 3 her s obratem z prohrane pozice).

---

## 1. [DATA] Agregovane statistiky

### Souhrn

| Metrika | Hodnota |
|---------|---------|
| Celkem her | 33 |
| Wins | 26 (81.3%) |
| Losses | 6 (18.8%) |
| Aggregate ACPL | 32.5 |
| Celkem blunderu | 13 |
| Celkem mistake | 32 |
| Celkem inaccuracy | 120 |
| Prumerny blunder rate | 0.39/game |
| Prumerny pocet tahu | 22.8 |

### 6 Loss games (label "loss" v .txt)

| Hra | Zahajeni | ACPL | B | M | I | Klicovy blunder |
|-----|----------|------|---|---|---|-----------------|
| k9a1IXvp | Pirc Defense (B00) | 32.1 | 0 | 2 | 6 | — |
| tDcFRclj | QGD Semi-Tarrasch (D40) | 45.2 | 2 | 2 | 4 | dxc5 (328cp), Bd6 (459cp) |
| LpJ8wgDG | Semi-Slav (D45) | 50.4 | 0 | 3 | 4 | — |
| wrYUwz6A | Nimzowitsch Scandinavian (B00) | 32.4 | 1 | 0 | 3 | Rhc1 (302cp) |
| 8jqLVD9c | Trompowsky (A45) | 48.6 | 1 | 4 | 11 | Qc4 (333cp) |
| 4gOcfuaY | Caro-Kann Advance Short (B12) | 43.4 | 0 | 1 | 10 | — |

### Blunder distribution

13 blunderu ve 33 hrach. Hry s vicesi blundry:
- `hrLawxDC` — **3 blundry** (357cp, 765cp, 1373cp) — nejhorsi hra sessionu, ACPL 90.6
- `tDcFRclj` — 2 blundry (328cp, 459cp)

Zbyvajicich 8 blunderu: 1 blunder v kazde z 8 her (8g78OUn0, tuHR2dh1, sAtfdKTi, XmAlR7uM, y1N81zuJ, wrYUwz6A, mjnQZkQQ, 8jqLVD9c).

---

## 2. [DATA] Pattern Detection Results

| Pattern | Confidence | Frequency | Severity |
|---------|-----------|-----------|----------|
| **G** — Color as modulator | **92%** | 22 games | high |
| **O** — Stagnacni panika | 29% | 12 games | critical |
| **Q2** — Win despite blunder | 19% | 7 games | low |
| **Q** — Active defense | 11% | 4 games | low |
| **B** — Automatic grab | 9% | 8 captures in 8 games | high |
| **Q1** — Desperate Gambit | 7% | 3 games | low |
| **C** — Attention tunneling | 5% | 2 games | medium |
| **J** — Impulsive check block | 5% | 2 events | high |
| **I2** — Opponent's gift | 2% | 1 event | low |

Poznamka: MCP server pouziva starou verzi — `affected_games` v evidence chybi (pouzito int) pro vetsinu patternu. Pouze pattern B ma `affected_games: list[str]`. Kde je k dispozici, uvadim konkretni hry. Ostatni vychazi z cache analyz.

---

## 3. [IM] Top 3 nejkritictejsi patterny

### 3.1 Pattern G — Color as modulator (92%) ⚠️ NOVÝ oproti minulému reportu

**Problem:** Blunder rate jako White (0.5/game) je **2.75× vyssi** nez jako Black (0.18/game). To je extremni asymetrie — vice nez dvojnasobek oproti minulemu reportu (1.7× Anonymous effect).

| Side | Blunder rate | Poznamka |
|------|-------------|----------|
| White | 0.50/game | Impulzivni, preceňuje silu |
| Black | 0.18/game | Trpelivy, defensive-minded |

**Mechanismus:** Hrac jako White tlaci na tempo, hleda aktivitu, ale prehnana agresivita vede k chybam. Jako Black ceka na chybu soupere a tresta.

**DATA:** Pattern G nema `affected_games` v evidence — nelze rict ktere konkretni hry. Z cache: `hrLawxDC` (White, 3 blundry, ACPL 90.6) je typicky priklad — hrac pretlaci, nekolikrat chybuje, stejne vyhraje diky endgame.

**Mitigace:** Hrat White jako kdyz jsi o pesce dole. Pred kazdym agresivnim tahem: "Je to nutne, nebo jen chci neco delat?"

---

### 3.2 Pattern O — Stagnacni panika (29%)

**Problem:** 12/33 her (36%) obsahuje flat eval plateau nasledovane blunderem do 6 tahu. Mene nez minuly report (54%), ale porad nejvice frekventovany pattern.

**DATA:** `affected_games` neni k dispozici jako seznam. Z cache:

| Hra | Symptom | Blunder |
|-----|---------|---------|
| sAtfdKTi | Eval stagnuje ply 20-26 | 28...Ne4+ (330cp) — forcing bez vypoctu |
| mjnQZkQQ | Eval plati ply 20-24 | 26...Qb6 (318cp) — nefungujici hrozba |
| tDcFRclj | Ztrata centra ply 14-16 | 17.dxc5 (328cp), 19.Bd6 (459cp) — dva po sobe |
| 8jqLVD9c | Tlak od ply 30 | 45.Qc4 (333cp) — pozicni chyba |

Vsechny blundry Pattern O nasleduji stejny scener: hrac prestane mit plan, vyrobi forcing move bez vypoctu, ztrati material nebo pozici.

**Mitigace:** 5-sekundova pauza kdyz "se nic nedeje."

---

### 3.3 Pattern B — Automatic grab (9%, 8 her)

**Problem:** 8 captures ve 3 hrach kde hrac bral automaticky bez kontroly protisachu.

**DATA (z toolu — `affected_games` k dispozici):**
- KI0VF4GA, piZsN15I, k9a1IXvp, hrLawxDC, 8g78OUn0, tDcFRclj, klVu9v8t, XmAlR7uM

Pomer 8/179 captures = 4.5% chybovost. To neni extremni, ale kazdy capture blunder stoji ~300cp.

**Konkretni priklad** (z cache `tDcFRclj` ply 17): Hrac bere dxc5, otevre diagonal na vlastniho krale. Po souperove reply je pozice horsi — blunder 328cp.

**Mitigace:** Pred kazdym capture: 3s pauza, otazka "A CO ON?"

---

## 4. [DATA] Fázová analýza

Z per-game cache dat pro hry s player-side analyzou:

| Faze | ACPL (prumer) | Poznamka |
|------|------|----------|
| Opening | ~30 | Nejhorsi cast — zde vznikaji rane blundry |
| Middlegame | ~35 | Konzistentni s Patternem B a O |
| Endgame | ~25 | Nelepsi — hrac dobre konci |

IM: Endgame je vyrazne lepsi nez v minulem reportu (39.2 → ~25). To muze byt:
1. Rozdilna kvalita souperu
2. Hrac studoval endgame po minulem reportu
3. Mala variance v datech

---

## 5. [IM] Silne stranky

### 5.1 Recovery triple: Q + Q2 + Q1

Tri recovery patterny dohromady:
- **Q** (Active defense): 4 hry — vyhra z materialove ztraty
- **Q2** (Win despite blunder): 7 her — vyhra i pres blunder >300cp
- **Q1** (Desperate Gambit): 3 hry — chaos mode v prohranem stavu

Hrac ma mentalni odolnost vyrazne nad prumerem 1800. Schopnost:
1. Nevyhazet zbrane po chybe
2. Komplikovat pozici
3. Trestat souperovu nedukladnost

### 5.2 Black side performance

Blunder rate 0.18/game jako Black je **vynikajici** (~2000+ uroveň). Hrac je prirozeně defenzivne zalozeny.

---

## 6. [IM] Treningova doporuceni

### P0: White side management
- Nejvetsi single problem (Pattern G 92%, 2.75× vice blunderu jako White)
- Hrat kazdou hru jako kdybys byl o pesce pozadu
- Target: asymetrie < 1.5×

### P1: Stagnacni panika ritual
- 12/33 her (36%) — porad vysoka frekvence
- Kontrolni otazka: "Kdybych mel na desce o 100cp vic, co bych hral?"
- Target: < 25%

### P1: Check response (Pattern J)
- 2 vyskpty — malo, ale kazdy stoji ~150cp+
- Drill: Lichess puzzle "defense", "check evasion"

### P2: Opening precision
- tuHR2dh1, y1N81zuJ — blundry v prvnich 9 tazich
- Patterny O a B v openingu: "opening trap" misto solidniho developmentu
- Target: ACPL opening < 25

---

## 7. [IM] Verdikt

**Soucasna uroveň (anonymni hry): 1800-1900 Lichess**
**Potencial: 2000-2100**

Tento 33-game session je konzistentni s minulym 35-game reportem (ACPL 32.9 vs 32.5, win rate 80% vs 81.3%). Hrac je stabilni na ~1800-1900 urovni.

**Nejvetsi zmena:** Pattern G (Color as modulator) nahradil Pattern A (Anonymous effect) jako dominantni problem. V minulem reportu byl Anonymous effect 1.7× pro obe barvy. Nyni je asymetrie mezi barvami — hrac hraje vyrazne hur jako White, ale lepe jako Black.

IM hypoteza: Anonymita nizuje prah rizika, ale barevna asymetrie ukazuje na **stylovy problem** — hrac nevi, jak hrat White bez rizika. Jako Black se citi bezpecne (defenziva), jako White tlaci na tempo a chybuje.

> "Neni to o tom, ze bys hral hur jako White. Je to o tom, ze jako White **zkousis vic** — a vic zkouset v sachu znamena vic chybovat. Resilence neni o preziti chyb, ale o jejich ne-delani."

---

*Report generated by pattern detection pipeline (depth 12) + IM-level reasoning. 33 anonymous games from .data/lichess_anonymni_partie.txt. Engine: Stockfish BMI2 dev-20260609. Patterns detected: 9 (G, O, Q2, Q, B, Q1, C, J, I2).*
