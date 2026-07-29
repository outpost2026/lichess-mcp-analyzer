# IM Coaching Report: Anonymous Session (4 hry)

**Datum:** 2026-07-28
**Analyza:** Pattern pipeline (depth 12) + IM reasoning
**Rozsah:** 4 anonymni Lichess hry (Systeq jako black)
**Vysledek:** 2 W / 2 L (50%) | ACPL: 69.6 | Blunders: 4 (1.0/game)

---

## Executive Summary

Jen 4 hry — statisticky limitovany vzorek. Presto je signal jasny: ACPL 69.6 je **vyrazne nad beznym prumerem** (~35-40 pro hrace 1800+). Dve prohry (6I8A3S9K, tuHR2dh1) maji ACPL 77.4 a 104.0 — obe obsahuji kriticky blunder, ktery rozhodl partii. Dve vyhry (sAtfdKTi, mjnQZkQQ) maji ACPL ~48-51 — stale vysoke, ale hrac zvladnul recovery.

Nejvetsi problem: **Pattern O (stagnacni panika)** detekovan ve 4/4 hrach (100%). Hrac se dostava do ploche pozice a nasledne blundruje do 6 tahu. To je systemova chyba, ne nahoda.

---

## 1. [DATA] Agregovane statistiky

### Souhrn

| Hra | Vysledek | ACPL | Tahu | B | M | I | Faze nejvice chyb |
|-----|----------|------|------|---|---|---|-------------------|
| sAtfdKTi | win (black) | 51.0 | 26 | 1 | 2 | 5 | Middlegame (63.3) |
| mjnQZkQQ | win (black) | 45.9 | 31 | 1 | 2 | 9 | Opening (47.4) / MG (48.1) |
| 6I8A3S9K | loss (black) | 77.4 | 17 | 1 | 3 | 3 | — |
| tuHR2dh1 | loss (black) | 104.0 | 6 | 1 | 0 | 1 | Opening (1 blunder = konec) |

**Aggregate:** 4 hry, ACPL 69.6, 4B/7M/18I, prumer 20 tahu/hra

### Blunder detail

| Hra | Tah | CP loss | Faze |
|-----|-----|---------|------|
| sAtfdKTi | 28...Ne4+ | 323cp | Middlegame |
| mjnQZkQQ | 26...Qb6 | 346cp | Middlegame |
| 6I8A3S9K | 32...Bf8 | 364cp | Middlegame |
| tuHR2dh1 | 12...c6 | 510cp | Opening |

Vsechny 4 blundry jsou >300cp (threshold "desperate"). Ani jeden neni "tactical oversight" typu nevidim vidlicku — vsechny jsou **positional misevaluations**:

- `sAtfdKTi` ply 28: Ne4+ s myšlenkou forkovat krále a věž, ale po Kf1 je jezdec ztracen (chybi vypocet)
- `mjnQZkQQ` ply 26: Qb6 napada pb2, ale vez na b1 kryje → ztrata tempa + pozicne horsi
- `6I8A3S9K` ply 32: Bf8 pasivni ustup — lepsi bylo priznat chybu a hledat aktivitu
- `tuHR2dh1` ply 12: c6? snaha blokovat centrum, ale vytvari slabinu na d6

---

## 2. [DATA] Pattern Detection Results

| Pattern | Confidence | Frequency | Severity |
|---------|-----------|-----------|----------|
| **O** — Stagnacni panika | 80% | 4/4 (100%) | critical |
| **J** — Impulsivni block pod sach | 22% | 1/4 | high |

Pattern detection neposkytl seznam `affected_games` pro jednotlive patterny (stara verze MCP serveru). Nasledujici IM analyza vychazi z pruniku cache a tool dat.

---

## 3. [IM] Top 3 nejkritictejsi patterny

### 3.1 Pattern O — Stagnacni panika (80%)

**Problem:** Ve 4/4 hrach hrac stoji pred plochou evalvaci (flat eval plateau) a nasledne udela blunder do 6 tahu.

Analyza blunderu:

| Hra | Symptom | Blunder |
|-----|---------|---------|
| sAtfdKTi | Eval stagnuje po vymene dam (ply 20-26) | 28...Ne4+ — forcing move bez vypoctu |
| mjnQZkQQ | Eval plati ply 20-24 (+10cp swing) | 26...Qb6 — nefungujici hrozba |
| 6I8A3S9K | Ztrata iniciativy po ply 24 | 32...Bf8 — pasivita |
| tuHR2dh1 | Ztrata centra ply 8-10 | 12...c6 — positional blunder |

**Mechanismus:** V ploche pozici hrac "neco zkusi" — agresivni nebo nepromysleny tah — misto strategickeho planu.

**Mitigace:** 5-sekundova pauza kdyz "se nic nedeje." Otazka: "Mam plan, nebo jen reaguju?"

---

### 3.2 Pattern J — Impulsive check block (22%)

**Problem:** 1 hra s impulzivnim blokem pod sach.

Konkretni priklad (z cache `sAtfdKTi` ply 16): Hrac po tahu 16 blokuje sach figurov, ale alternativa (ustup kralem) by byla lepsi.

IM poznamka: Jen 1 vyskyt ve 4 hrach — neni statisticky signifikantni. Pattern J byl v minulem reportu (35 her) 5 her. S malym vzorkem nelze rici, zda se zlepsil nebo jen nemel prilezitost.

---

### 3.3 Blunder frequency (1.0/game)

4 blundry ve 4 hrach — to je **extremne vysoka frekvence**. V minulem reportu (35 her) to bylo 0.46/game. Tento vzorek ma 2× vyssi blunder rate.

Priciny:
1. **Small sample bias** — 4 hry staci na 1-2 blundry, 4 je outlier ale statisticky mozny
2. **Quality of opposition** — anonymni hraci mohli byt silnejsi nez prumer
3. **Fatigue / time management** — neni data, jen IM hypoteza

---

## 4. [IM] Fazova analyza

Na zaklade 2 her s per-phase cache daty:

| Faze | sAtfdKTi | mjnQZkQQ | Poznamka |
|------|-----------|-----------|----------|
| Opening | 37.5 (10) | 47.4 (10) | Vysoke — chyby v zahajeni |
| Middlegame | **63.3** (15) | 48.1 (15) | Nejhorsi — zde vznikaji blundry |
| Endgame | 0 (1) | 38.2 (6) | Malo dat |

**Middlegame ACPL 63.3 v sAtfdKTi** je critical. Hrac v middle game:
1. Ztrati iniciativu (ply 20-24)
2. Zpanikari (ply 28: blunder)
3. Uz se nevzpamatuje

V mjnQZkQQ je ACPL konzistentni napric fazemi (~46-48) — to je plato. Hrac nedela extremni chyby (krome 1 blundru), ale ani nevyrazuje.

---

## 5. [IM] Treningova doporuceni

### P0: Stagnacni panika management
- Ve 4/4 hrach — nejvetsi single problem
- Prakticky drill: pred kazdym tahem v ploche pozici "Co je plan na pristich 5 tahu?"
- Sledovat: frekvence O (target: <50% her)

### P1: Positional blunder awareness
- Vsechny 4 blundry jsou positional, ne tactical
- Trening: strategicke puzzle (plan-making, ne taktika)
- Zamereni na: rozpoznani kdy "agresivni tah" nema vypocetni oporu

### P1: Opening preparation
- ACPL v openingu u obou her ~37-47 — vysoke
- tuHR2dh1 (Scandinavian) — prohra v 6 tazich = catastrophic opening failure
- Trening: 1 opening reply pro Scandinavian (Kiel Variation)

### P2: Sample size expansion
- 4 hry nestačí na robustni diagnozu
- Doporuceni: 20+ anonymnich her pred dalsim reportem

---

## 6. [IM] Verdikt

**Soucasna uroveň (anonymni hry): ~1700-1800 Lichess**
**Potencial: 1900-2000**

Tento 4-game session je **vyrazne slabsí** nez 35-game session z 2026-07-28:
- ACPL 69.6 vs 32.9 (= 2.1× vyssi)
- Blunder rate 1.0/game vs 0.46/game
- Win rate 50% vs 80%

Je mozne, ze:
1. Hrac mel "bad day" — mala variance pri 4 hrach
2. Kvalita anonymnich opponentu byla vysoka (blitz rating neuveden)
3. Kombinace otevrenych zahajeni (Scandinavian, Petrov) neni v hlavnim repertoaru

IM odhad: realna uroveň hrace v anonymnim blitzu je ~1800. 4 hry s ACPL 69.6 jsou outlier — ale i outlieri se deji.

> Klicova otazka neni "proc jsem dnes prohral?" ale "proc se mi to same stalo ve 4 ruznych hrach?" A odpoved je: Pattern O. Dokud nebudes mit plan na ploche pozice, bude se to opakovat.

---

*Report generated by pattern detection pipeline (depth 12) + IM-level reasoning. 4 anonymous games (Systeq as black). Engine: Stockfish BMI2 dev-20260609. Cache: sAtfdKTi_black, mjnQZkQQ_black, 6I8A3S9K_black, tuHR2dh1_black.*
