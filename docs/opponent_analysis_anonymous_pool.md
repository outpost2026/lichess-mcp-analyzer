# Opponent Analysis: Anonymous Lichess Pool jako diskretni player

**Datum:** 2026-07-28
**Zdroj:** 33 anonymnich her (preanalyzovano z perspektivy protihrace)
**Metoda:** Fresh pipeline (depth 12) z `.data/lichess_anonymni_partie_opponent_perspective.txt` — kazda URL oznackovana opacne (autor win → label "loss", autor loss → label "win")
**Pool:** N=33 her jako jeden diskretni hrac
**Grupy:** n1 = 27 proher opponentu (autor win) | n2 = 6 vyher opponentu (autor loss)

---

## [DATA] Agregovane statistiky opponent pool (N=33)

| Metrika | Hodnota | Comparison (autor) |
|---------|---------|-------------------|
| Aggregate ACPL | **52.0** | 32.5 (+19.5 gap) |
| Celkem blunderu | 21 (0.64/game) | 13 (0.39/game) |
| Celkem mistake | 49 (1.48/game) | 32 (0.97/game) |
| Celkem inaccuracy | 140 (4.24/game) | 120 (3.64/game) |
| Prumerna delka hry | 22.4 tahu | 22.8 tahu |
| Win rate | 18.2% (6/33) | 81.8% (27/33) |

**Interpretace:** Opponent pool jako cely ma ACPL 52.0 — to je o 60% horsi nez autor (32.5). Blunder rate 0.64/game je 1.6× vyssi. Toto potvrzuje ze autor je v prumeru silnejsi hrac.

---

## [DATA] Pattern detection — Opponent jako discrete player

| Pattern | Confidence | Frequency | Severity |
|---------|-----------|-----------|----------|
| **O** — Stagnacni panika | **44%** | 18/33 (55%) | critical |
| **J** — Impulsivni block pod sach | 16% | 6 events | high |
| **Q2** — Win despite blunder | 14% | 5 games | low |
| **C** — Attention tunneling | 11% | 4 games | medium |
| **B** — Automatic grab | 8% | 7/174 captures | high |
| **Q** — Active defense | 8% | 3 games | low |
| **P** — Visual misrecognition | 4% | 2 games | high |
| **Q1** — Desperate Gambit | 2% | 1 game | low |

### Comparison: Opponent patterns vs Author patterns

| Pattern | Opponent | Author | Signal |
|---------|----------|--------|--------|
| **O** Stagnation panic | 44% (18/33) | 29% (12/33) | **Opponents panic MORE** |
| **J** Impulsive check block | 16% (6) | 5% (2) | **Opponents 3× více impulsivnich bloku** |
| **C** Attention tunneling | 11% (4) | 5% (2) | Opponents 2× vice consec errors |
| **B** Automatic grab | 8% (7/174) | 9% (8/179) | Podobna chybovost (~4-5%) |
| **Q2** Win despite blunder | 14% (5) | 19% (7) | Autor ma vyssi resilienci |
| **P** Visual misrecognition | 4% (2) | — | **Jen opponenti** — autor nema |
| **G** Color as modulator | — | 92% (22) | **Jen autor** — vyrazna barevna asymetrie |

**Signal:** Opponenti dominuji v patternu O a J — stagnacni panika a impulsivni blocky. To jsou systemove chyby slabejsich hracu. Autor dominuje v patternu G (barevna asymetrie) — to je stylovy problem, ne silova slabina.

---

## [DATA] Grupova analyza: n1 (opponenti lost, n=27) vs n2 (opponenti won, n=6)

### n2 — Opponenti, kteri porazili autora (n=6)

| Hra | ACPL | B | M | I | Moves | Zahajeni |
|-----|------|---|---|---|-------|----------|
| k9a1IXvp | **16.1** | 0 | 0 | 3 | 31 | Pirc Defense |
| tDcFRclj | 34.8 | 0 | 3 | 6 | 40 | QGD Semi-Tarrasch |
| LpJ8wgDG | **24.4** | 0 | 1 | 1 | 20 | Semi-Slav |
| wrYUwz6A | **19.5** | 0 | 0 | 3 | 23 | Nimzowitsch Scandinavian |
| 8jqLVD9c | 37.1 | 1 | 4 | 5 | 50 | Trompowsky |
| 4gOcfuaY | 44.3 | 1 | 1 | 4 | 29 | Caro-Kann Advance |

**n2 aggregate: ACPL 29.4 | B 2 (0.33/g) | M 9 (1.5/g) | I 22 (3.67/g) | avg moves 32.2**

### n1 — Opponenti, kteri prohrali s autorem (n=27)

**n1 aggregate: ACPL 57.0 | B 19 (0.70/g) | M 40 (1.48/g) | I 118 (4.37/g) | avg moves 20.2**

### Comparison n2 vs n1

| Metrika | n2 (winners, n=6) | n1 (losers, n=27) | Delta |
|---------|-------------------|-------------------|-------|
| ACPL | **29.4** | 57.0 | **-27.6 cp (1.9× lepsi)** |
| Blunders/game | **0.33** | 0.70 | -53% |
| Mistakes/game | 1.50 | 1.48 | ~same |
| Inaccuracies/game | 3.67 | 4.37 | -16% |
| Avg game length | **32.2** | 20.2 | +59% (delsi hry) |

### Klicove zjisteni z grupove analyzy

**n2 (winner opponents) hraji o 1.9× lepe nez n1 (loser opponents)** — a to neni prekvapive. Prekvapive je:

1. **n2 ACPL 29.4 je LEPSI nez autoruv prumer 32.5.** To znamena: opponent kteri porazili autora, hrali v prumeru na vyssi urovni nez autor. Potvrzuje to, ze prohry nebyly "autoruv bad day" ale **kvalita opponentu**.

2. **n2 blunder rate 0.33/game je stejny jako autoruv (0.39/game).** Kdo ma nizsi blunder rate, vyhrava.

3. **n2 hry jsou 1.6× delsi (32.2 vs 20.2 tahu).** Silnejsi opponent potrebuje vice tahu na konverzi — autor se brani dele. Slabsi opponenti (n1) prohravaji v prumeru ve 20 tazich — bud autor crushne, nebo opponent udela fatalni chybu.

4. **n1 ACPL 57.0 je extremni.** To je o 75% horsi nez autor. Tito opponenti:
   - Delaji 2× vice blunderu (0.70/game)
   - Neudrzi pozornost (Pattern O 44%)
   - Prohravaji kratke hry (20.2 tahu)

---

## [IM] Profil opponent poolu jako diskretniho hrace

### Zakladni charakteristika

**Celkovy ACPL: 52.0** — to odpovida ~1600-1700 Lichess blitz. Opponent pool je prumerne slabsí nez autor (32.5), ale s vyraznou variabilitou:

- **Dolni kvartil (n1 slabsi):** ~1400-1500 (ACPL 70+, 6+ blunderu na 3 hry)
- **Median (n1 prumer):** ~1600-1700 (ACPL ~50-60)
- **Horni kvartil (n2):** ~1800-1900 (ACPL ~30, vyhravaji nad autorem)

### Systemove chyby opponent poolu

1. **Stagnacni panika (O) — 55% her.** Nejvetsi single problem. Opponenti neumi hrat ploche pozice — panikari a blundruji. To je konzistentni s autorovym patternem O (36%) — oba delaji stejnou chybu, ale autor o neco mene.

2. **Impulsivni block pod sach (J) — 6 events.** Opponenti blokuji sach prvni figurou kterou vidi, misto aby zvazili utek nebo brani. Autor ma jen 2 — to je vyrazny rozdil.

3. **Automatic grab (B) — 4% captures.** Podobne jako autor (4.5%). Capture greed je univerzalni — obe strany delaji stejnou chybu ve stejne frekvenci.

4. **Attention tunneling (C) — 4 games.** Opponenti maji 2× vice consec chyb (4 vs 2). Po prvni chybe "vypnou" a udelaji dalsi.

### Co odlisuje n2 (winner) od n1 (loser)

**n2 neni "tactical genius" — n2 je "less broken":**

| Dovednost | n2 | n1 | Rozdil |
|-----------|----|----|--------|
| Blunder avoidance | 0.33/g | 0.70/g | **53% mene blunderu** |
| Koncentrace | normal | 70% vice inaccuracies | **Udrizej pozornost dele** |
| Game length | 32.2 | 20.2 | **Vydrzi v hre dele** |
| Opening play | solidnejs | chybovejsi | **Maji reply na vedlejsi linie** |

n2 vyhrava ne proto, ze by delali genialni tahy (jejich ACPL je jen 29.4, ne 15). Vyhrava proto, ze **nedelaji fatality v klicovych momentech.** n1 dela blunder v kazde 1.4 hre — to je smrtelna frekvence.

---

## [IM] Zaver: Co 81.8% win ratio vypovida o anonymnim poolu

### N=2 (dve grupy) staci k profilu

Rozdil mezi n1 a n2 neni kvantitativni (trochu lepsi) ale **kvalitativni (jina uroveň chybovosti):**

> n1 = hraci, kteri **systematicky sebeznicuji** ve 20 tazich
> n2 = hraci, kteri **vydrzi neudelat fatální chybu** po dobu 32 tahu

### Extrapolace na Lichess anonymous pool ~1800

1. **Pool je bimodalni:** existuji dve skupiny — ~80% slabich (~1600-1700) a ~20% silnych (~1800-1900). Prvni skupina pada na vzdy stejne systemove chyby (O, J, B), druha skupina vydrzi a tresta.

2. **Capture greed je konstanta:** Bez ohledu na grupu, ~4-5% captures je automatickych a chybnych. To neni otazka dovednosti — je to kognitivni bias. Na ~1800 je natolik predvidatelny, ze na nej lze stavit bait trap strategii (viz autoruv komentar k xZpB6uHC).

3. **Stagnacni panika (O) je nejcastejsi pricina prohry:**
   - Opponenti: 18/33 (55%) — vzdy jako prohravajici
   - Autor: 12/33 (36%) — nekdy jako vyhravajici, nekdy jako prohravajici
   - **Kdo zvladne ploche pozice, vyhrava 82% her na teto urovni.**

4. **Time management je sekundarni:** Opponenti neprohravaji primarne na cas (pouze 1-2 timeouty). Prohravaji na **systemove chyby v rozhodovani**.

### Bottom line

> "Anonymous hrac na ~1800 Lichess neni tajemny — je predvidatelny: stagnuje, blundruje, neveri. Jeho jedina sance je vydrzet dele nez ty. A ty, se svym ACPL 32.5, jsi o 60% presnejsi. To staci na 82% win rate, ale ne na 2000."

---

*Analyza generovana z fresh pipeline (depth 12) — 33 her analyzovanych z perspektivy protihrace. Pattern detection: 8 patternu (O, J, Q2, C, B, Q, P, Q1). Grupova analyza: n1 (27 proher) vs n2 (6 vyher). Stockfish BMI2 dev-20260609.*
