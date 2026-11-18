# IM Coaching Report: Author Perspective — 4 Losses (N2 Games)

**Datum:** 2026-07-29 | **Perspektiva:** Autor (original player)
**Vyber:** 4 hry z N2 poolu kde autor PROHRAL (opponent won)
**Rozsah:** k9a1IXvp (Pirc, 0 blunderu autora), G40ssnlG (Italian, 0 blunderu autora), 8jqLVD9c (Trompowsky, 1 blunder), Cm02bEZC (Vienna, 8 blunderu)
**Zdroj:** data/game_cache/*_d12.json | lichess_analyze_game + lichess_match_patterns (author perspective)
**Metodika:** Template 1 — Per-Game Coaching Report — [DATA]/[IM] split, overeno z cache

---

## Game 1: k9a1IXvp — Pirc Defense (B00)

### [DATA] Zakladni info

| Metrika | Hodnota |
|---------|---------|
| Strana | White (autor) |
| Result | 0-1 (autor prohral) |
| Time control | 300+3 (Rapid) |
| ACPL | **32.1** |
| Accuracy | 95.2% |
| Delka hry | 31 ply (15.5 moves) |
| Blundy | 0 |
| Chyby (mistakes) | 2 |
| Nepresnosti | 6 |

### [DATA] Fazovy breakdown

| Faze | Tahu | ACPL | Errors |
|------|------|------|--------|
| Opening (ply 1-20) | 10 | **38.0** | 2 mistakes + 1 inaccuracy |
| Middlegame (ply 21-40) | 15 | 21.0 | 3 inaccuracies |
| Endgame (ply 41+) | 6 | 50.0 | 1 mistake + 1 inaccuracy |

### [DATA] Error klasifikace

**Blunders (0):** None.

**Mistakes (2):**
| Ply | Tah | cp_loss | Faze | Co se stalo |
|-----|-----|---------|------|------------|
| 17 | **Nd5** | **160** | op | Eval: -60 → -221. Jezdec skoci na d5, ale po Bxg5 a Nxd5 cerny vyhraje figuru. Spatny vyber pole pro jezdce — d5 je kryty cernym jezdcem na f6 a strelcem na e7. |
| 59 | **Rxe1** | **174** | end | Eval: -486 → -657. V koncovce bere vez damu, ale po Kxe1 je cerny král v bezpeci. Spravne bylo Kxe1 (kral bere). Klasicky Pattern B (Automatic grab). |

**Inaccuracies (6):** Bg5 (144), cxd4 (53), Qd5 (53), Qh5 (71), Rb3 (95), Bc2 (93)

### [DATA] Pattern detection

| Pattern | Konfidence | Postihuje |
|---------|-----------|-----------|
| **O — Stagnacni panika** | 85% | ANO |
| **B — Automatic grab** | 85% | ANO |

**Pattern O:** Eval plato v ply 20-26 (stagnace +0.5 → Qd5). Nasledne Qh5 (ply 31, 71cp inaccuracy) — forcing bez vypoctu.
**Pattern B:** Rxe1 (ply 59, 174cp) — capture blunder v koncovce. 5.7% vsech captures autora jsou blundry.

### [DATA] Silman imbalance assessment

- **Ply 9 (Bg5):** Spatne nacasovany presun strelce. Po e5 od cerneho je Bg5 mimo hru. **Imbalance:** Cerny ma centrum (e5), bily strelec na g5 je neaktivni a muze byt napaden.
- **Ply 13-17 (Qa4+ → Nd5):** Qa4+ je dobry sach, ale Nd5 je krok do pasti. Cerny ma pripraven Bxg5 a Nxd5. **Imbalance:** Po Nd5 ztrati bily figuru za nic. Material ve prospech cerneho.
- **Ply 25-31 (Qd5 → Qh5):** Po ztrate figury autor bloudi — Qd5 je OK, ale Qh5 je zbytecny presun. **Imbalance:** Cerny ma figuru navic a aktivni figury.
- **Ply 45+ (endgame):** Autor se snazi o aktivitu, ale s figurou mene je to beznadejne. Rxe1 je posledni kapka.

### [IM] Heisman-style error analyza

**Nejkritictejsi error:** Nd5 (ply 17, cp_loss=160). Tento tah ztrati figuru v otevrene pozici. Prvni velka chyba v hre — a posledni, ktera rozhodla. Po Bxg5 a Nxd5 je cerny +1.5.

**Typ chyby:** **Takticka** — prehlednul, ze cerny kryje d5 dvakrat (Nf6 + Be7). Neni to pozicni — je to selhani v basic tactice (pocitani kdo koho kryje).

**Time trouble:** Nepravdepodobna (pouhych 31 tahu, 300+3 cas).

### [IM] Tri veci co autor udelal dobre

1. **Solidni tlak po Nd5 (ply 17-24).** Po ztrate figury se autor nevzdal, Qxc6+ a Qd5 davaly nejakou aktivitu.
2. **Snaha o koncovkovou aktivitu.** I v horsi pozici autor stale hledal checks a hrozby.
3. **Nulovy blunder — jen 2 mistakes.** Skore 0/2/6 neni katastrofa, ale v teto hre to nestacilo protoze opponent hral ACPL 16.

### [IM] Jedna vec na zlepseni

Heisman: "Nejmensi chyba prvni." Nd5 (ply 17) — pred skokem na d5 zkontrolovat: "Kdo kryje to pole a kolikrat?"

### [IM] Treninkova doporuceni

- **Téma:** Simple piece counting — "kdo kryje cilove pole?"
- **Puzzle theme:** "Bait-and-capture" — pozice kde jedna strana nabizi jezdce na zjavne ale kryte pole.
- **Otazka k zamyšlení:** "Pred kazdym skokem jezdce — kdo vsechno kryje cilove pole?"

---

## Game 2: G40ssnlG — Italian Two Knights (C56)

### [DATA] Zakladni info

| Metrika | Hodnota |
|---------|---------|
| Strana | Black (autor) |
| Result | 1-0 (autor prohral) |
| Time control | 300+3 (Rapid) |
| ACPL | **45.2** |
| Accuracy | **93.2%** |
| Delka hry | 14 ply (7 moves) — kratka |
| Blundy | 0 |
| Chyby (mistakes) | 2 |
| Nepresnosti | 3 |

### [DATA] Fazovy breakdown

| Faze | Tahu | ACPL | Errors |
|------|------|------|--------|
| Opening (ply 1-20) | 10 | **55.6** | 2 mistakes + 2 inaccuracies |
| Middlegame (ply 21+) | 4 | 19.2 | 1 inaccuracy |
| Endgame | — | — | (hra nesla do koncovky) |

### [DATA] Error klasifikace

**Blunders (0):** None.

**Mistakes (2):**
| Ply | Tah | cp_loss | Faze | Co se stalo |
|-----|-----|---------|------|------------|
| 8 | **Be7** | **246** | op | Eval: 0 → -246. Po Nxe5 a d4 ma bily dominantni centrum. Be7 misto Nxe4 — autor nevyuziva aktivni moznost a hraje pasivni vyvin. |
| 10 | **Nxe4** | **192** | op | Eval: -222 → -414. Pozdni pokus o aktivitu — ale uz je pozice cerneho stisnena. Po d5 od bileho je jezdec na e4 nestabilni. |

**Inaccuracies (3):** Nxe5 (64), Kh8 (53), Ng5 (57)

### [DATA] Pattern detection

Zadny pattern z autorova poolu (O, B, C, J) neni aplikovatelny na tuto hru — je prilis kratka (14 tahu) a nema opakujici se chyby.

### [DATA] Silman imbalance assessment

- **Ply 1-8:** Italian Two Knights — bily obetuje Nxf7 (Knight sacrifice). Autor (cerny) bere figuru Kxf7. Po Bc4+ a d4 ma bily dominantni centrum a vyvin. **Imbalance:** Bily ma vyhodu v centru a vyvoji (2 tempa). Cerny ma figuru navic, ale pasivni pozici.
- **Ply 8 (Be7):** Zde mel autor hrat Nxe4, ne be7. Jezdec na e4 by vyuzil ,ze cerny ma vetsi pocet figur v centru. Misto toho autor hraje pasivni vyvin. **Imbalance se zhorsuje:** Bily dava f3 a cerny ztrati tempo.
- **Ply 10 (Nxe4):** Uz je pozde. Po d5 je jezdec na e4 napaden a nestabilni.

### [IM] Heisman-style error analyza

**Nejkritictejsi error:** Be7 (ply 8, cp_loss=246). Po prijeti obeti na f7 je klicove byt aktivni — hrat Nxe4, ne vyvinout strelce. Be7 je pasivni a dava bilemu cas na konsolidaci. Evaluace skoci z 0 na -246.

**Typ chyby:** **Pozicni** — nepochopeni, ze po obeti f7 je cerny zavazan k aktivite, ne pasivite.

**Time trouble:** Nepravdepodobna — 14 tahu, rapid.

### [IM] Tri veci co autor udelal dobre

1. **Fyzicky vyhral figuru (Nxf7).** V Italian Two Knights je to standardni obet, autor ji korektne prijal.
2. **Vcas resignoval.** Kratka hra bez zbytecneho protahovani — to je disciplinovany pristup.
3. **Zadny blunder.** Skore 0/2/3 — ale 0 blunderu znamena, ze autor nedal opponentovi zadny dar.

### [IM] Jedna vec na zlepseni

Heisman: "Nejmensi chyba prvni." Be7 (ply 8) — po prijeti obeti na f7 musis hrat aktivne. Nxe4 okamzite, ne vyvoj strelce.

### [IM] Treninkova doporuceni

- **Tema:** Post-sacrifice play — jak hrat po prijeti obeti na f7 v Italian.
- **Puzzle theme:** Italian Two Knights defense — "counterattack in the center after Nxf7".
- **Otazka k zamyšlení:** "Po Kxf7 a Bc4+ — co je dulezitejsi: vyvinout strelce nebo utocit na centrum (e4)?"

---

## Game 3: 8jqLVD9c — Trompowsky Attack (A45)

### [DATA] Zakladni info

| Metrika | Hodnota |
|---------|---------|
| Strana | White (autor) |
| Result | 0-1 (autor prohral) |
| Time control | 300+3 (Rapid) |
| ACPL | **48.6** |
| Accuracy | **92.7%** |
| Delka hry | 50 ply (25 moves) |
| Blundy | **1** |
| Chyby (mistakes) | 4 |
| Nepresnosti | 11 |

### [DATA] Fazovy breakdown

| Faze | Tahu | ACPL | Errors |
|------|------|------|--------|
| Opening (ply 1-20) | 10 | 20.3 | 1 inaccuracy |
| Middlegame (ply 21-40) | 18 | **62.6** | 1 blunder + 3 mistakes + 3 inaccuracies |
| Endgame (ply 41+) | 22 | 51.6 | 1 mistake + 5 inaccuracies |

### [DATA] Error klasifikace

**Blunders (1):**
| Ply | Tah | cp_loss | Faze | Co se stalo |
|-----|-----|---------|------|------------|
| 45 | **Qc4** | **333** | mid | Eval: +6 → -319. Dama na c4 s hrozbou Qxf7+, ale po Rf8, Bxe5 a Qxe5 cerny udrzi vyhodu. Spatne umistena dama — bez opory a snadno napadena. |

**Mistakes (4):**
| Ply | Tah | cp_loss | Faze |
|-----|-----|---------|------|
| 43 | Bf2 | 174 | mid |
| 87 | Bd1 | 267 | end |
| 89 | Qe7 | 165 | end |
| 93 | Qf6+ | 185 | end |

**Inaccuracies (11):** e3 (67), Ng5 (63), Qb4 (97), Nxe4 (60), Bb3 (63), Nc5 (87), Rd3 (86), c4 (70), e5 (146), Qf3 (60), Qxa7 (97)

### [DATA] Pattern detection

| Pattern | Konfidence | Postihuje |
|---------|-----------|-----------|
| **C — Attention tunneling** | 85% | ANO |

**Pattern C:** 5 consecutive error v rozmezi ply 43-93, koncentrovanych v mid+end. Autor se zacyklil v midgame a opakovane chyboval.

### [DATA] Silman imbalance assessment

- **Ply 1-20 (opening):** Trompowsky — autor ma prostorovou vyhodu. Cerny je stisneny, ale nema strukturalni slabiny. **Imbalance:** Bily ma prostor + vyvin, ale zadny konkretni prulom.
- **Ply 21-45 (critical):** Autor postraci vyhodu presunem Qc4 (blunder). Po tomto tahu uz cerny dominuje. **Imbalance se otaci:** Z bileho prostorove vyhody na cernou materialni a pozicni dominanci.
- **Ply 45+ (endgame):** Cerny ma figuru vice a autor se snazi o despere counterplay — ale kazdy tah je dalsi chyba (Bf2, Bd1 — 267cp). **Imbalance:** +2 material pro cerneho. Neni c cim bojovat.

### [IM] Heisman-style error analyza

**Nejkritictejsi error:** Qc4 (ply 45, cp_loss=333). Dama na c4 vypada hrozive (hrozi Qxf7#), ale je to iluze — cerny ma Rf8 a po Bxe5 Qxe5 je dama napadena a musi utect. Ztrata tempa i pozice.

**Typ chyby:** **Takticka** — autor prehledl, ze Rf8 kryje f7 a ze po Bxe5 nema dama oporu.

**Consecutive errors:** Od ply 43 do 93 — 8 erroru, z toho 5 v koncovce. To potvrzuje Pattern C — autor se fixoval na "vyhru pres f7" a prehledel vsechno ostatni.

**Time trouble:** 300+3, 25 tahu — minimalni casovy tlak.

### [IM] Tri veci co autor udelal dobre

1. **Slusny opening.** V Trompowskem mel autor vyhodu az do ply 43.
2. **Bojoval v koncovce.** I po ztrate figury autor stale hledal moznosti — i kdyz casto nepresne.
3. **Vice blunderu nez opponent.** Autor 1, opponent 1 — ale opponent mel 4 mistakes a autor jen Qc4 jako jediny zlom.

### [IM] Jedna vec na zlepseni

Heisman: "Nejmensi chyba prvni." Qc4 (ply 45) — pred presunem damy na c4 overit: "Kdo kryje f7? A co se stane po Rf8 a Bxe5?"

### [IM] Treninkova doporuceni

- **Tema:** Queen placement safety — neumistovat damu na pole bez opory.
- **Puzzle theme:** "False mating attack" — pozice kde matova hrozba neni realna a protistrana ma obranu.
- **Otazka k zamyšlení:** "Pred kazdym Qc4 — kdo kryje f7? A muzu byt counterattacked?"

---

## Game 4: Cm02bEZC — Vienna Anderssen (C25)

### [DATA] Zakladni info

| Metrika | Hodnota |
|---------|---------|
| Strana | White (autor) |
| Result | 0-1 (autor prohral) |
| Time control | 300+3 (Rapid) |
| ACPL | **189.0** |
| Accuracy | **85.8%** |
| Delka hry | 68 ply (34 moves) — nejdelsi |
| Blundy | **8** |
| Chyby (mistakes) | 3 |
| Nepresnosti | 12 |

### [DATA] Fazovy breakdown

| Faze | Tahu | ACPL | Errors |
|------|------|------|--------|
| Opening (ply 1-20) | 10 | **28.3** | 2 inaccuracies |
| Middlegame (ply 21-40) | 14 | **38.3** | 1 mistake + 3 inaccuracies |
| Endgame (ply 41+) | 44 | **279.0** | **8 blundery + 2 mistakes + 7 inaccuracies** |

### [DATA] Error klasifikace

**Blunders (8) — VSECHNY v endgame:**
| # | Ply | Tah | cp_loss | Faze | Pattern |
|---|-----|-----|---------|------|---------|
| 1 | 49 | Ne7+ | 169 | mid | — (klasifikovano jako mistake, ale zlomovy) |
| 2 | 57 | **Rxe5** | **486** | end | **B** (Automatic grab) + **R** (Endgame relaxation) |
| 3 | 65 | Bf2 | 185 | end | **J** (Impulsive check block) |
| 4 | 75 | Kf1 | 326 | end | |
| 5 | 111 | Qg5+ | 487 | end | |
| 6 | 119 | **Ke3** | **1772** | end | |
| 7 | 121 | **c5** | **1081** | end | |
| 8 | 123 | **c6** | **4081** | end | |
| 9 | 125 | Ke4 | 223 | end | (klasifikovano mistake) |
| 10 | 127 | Kf3 | 634 | end | |
| 11 | 129 | **Kg4** | **2151** | end | |
| 12 | 131 | Kxg5 | — | end | |

**Mistakes (3):** Ne7+ (169, mid), Bf2 (185, end), Ke4 (223, end)

**Inaccuracies (12):** a5 (106), a4 (72), Bxd4 (72), + 9 dalsich v endgame

### [DATA] Kriticke eval swingy (|delta| > 200cp)

| Ply | Tah | Eval pred | Eval po | Delta |
|-----|-----|-----------|---------|-------|
| 57 | Rxe5 | +X | -Y | (prvni velky) |
| 119 | Ke3 | -2172 | -2733 | -561 |
| 121 | c5 | -1271 | -4926 | -3655 |
| 123 | c6 | -3793 | -4980 | -1187 |
| 125 | Ke4 | -2157 | -4906 | -2749 |
| 129 | Kg4 | -2865 | -5096 | -2231 |
| 133 | Kg4 | -4221 | 0 | +4221 (hra skoncila) |

### [DATA] Pattern detection

| Pattern | Konfidence | Postihuje |
|---------|-----------|-----------|
| **O — Stagnacni panika** | 85% | ANO |
| **B — Automatic grab** | 85% | ANO |
| **C — Attention tunneling** | 85% | ANO |
| **J — Impulsive check block** | 68% | ANO |

Vsechny 4 autorovy detekovane patterny se projevily v teto jedine hre. To je **vzacny pripad kompletniho kolapsu**.

### [DATA] Silman imbalance assessment

**Ply 1-20 (opening):** Vienna Anderssen — rovnocenna pozice. Obe strany vyvinute. **Imbalance:** Minimalni. Hra je otevrena.

**Ply 21-48 (midgame):** Rovnovazna hra s mirnym tlakem tam a zpet. ACPL 38.3 je solidni. Zlom je Ne7+ (ply 49) — neni to blunder (169cp), ale zacina posun.

**Ply 49-57 (endgame začátek):** Rxe5 (ply 57, 486cp) — prvni velky blunder. V koncovce bere vez na e5 a ceka ze vyhraje figuru, ale cerny ma protihrozby. Eval se otaci. **Imbalance:** Z mírne vyhody bileho na vyhodu cerneho.

**Ply 57-75 (endgame kolaps):** 8 blunderu a 3 mistakes v 44 tazich. ACPL endgame 279 — to je daleko pod 1000 ELO urovni. Autor zcela ztratil prehled.

### [IM] Heisman-style error analyza

**Nejkritictejsi error:** Rxe5 (ply 57, cp_loss=486). Prvni velky blunder v endgame. Pattern B (Automatic grab) — autor videl brani a automaticky bral bez vyhodnoceni nasledku. Po tomto blundru se spustil kaskadovy kolaps (Pattern C + O).

**Kaskada:**
1. Rxe5 (486cp, B+R) → Attention tunneling: autor se fixuje na "zisk figury"
2. Bf2 (185cp, J) → zkousi impulsivni block v checku
3. Kf1-Ne7+ (326cp) → kral bloudi
4. Qg5+ (487cp) → panicky presun damy
5. Ke3-c5-c6-Ke4 (1772+1081+4081+223cp) → kompletni endgame kolaps
6. Kf3-Kg4-Kxg5 (634+2151cp) → kral jde napric deskou jako v 400 ELO hre

**Typ chyby:** **Kombinovana** — prvni chyba je takticka (automatic grab), nasledujici jsou pozicni + psychologicke (collapse of calculation).

**Time trouble:** 300+3, 68 tahu — casovy tlak je mozny (34 moves v rapidu je tempo ~1 move/9 sec), ale ne ospravedlnuje 8 blunderu.

### [IM] Tri veci co autor udelal dobre

1. **Prvnich 48 tahu solidnich.** ACPL 38 v opening+mid je na solidni klubove urovni.
2. **Bojoval az do konce.** I po 8 blundrech autor nevzdal — 133 ply jeu.
3. **Vzdor vsemu — zadna resignace.** Kde jini by uz davno resignovali, autor stale zkousel.

### [IM] Jedna vec na zlepseni

Heisman: "Nejmensi chyba prvni." Rxe5 (ply 57) — "Co se stane po Rxe5? Kdo ma hrozby?"

### [IM] Treninkova doporuceni

- **Tema:** Endgame consolidation — kdyz mas vyhodu v koncovce, neforce, konsoliduj.
- **Puzzle theme:** "Endgame blunder prevention" — pozice kde jedna strana ztraci vyhodu kvuli sp_chne nacasovanemu capture.
- **Otazka k zamyšlení:** "Proc jsem hral Rxe5? Co jsem cekal ze se stane? A co jsem mohl hrat misto toho (napr. Be3, Re1)?"

---

## Cross-Game Summary: Author Perspective

### Aggregate

| Metrika | k9a1IXvp | G40ssnlG | 8jqLVD9c | Cm02bEZC | **Autor prumer** | Opponent prumer |
|---------|-----------|----------|----------|----------|-----------------|-----------------|
| ACPL | 32.1 | 45.2 | 48.6 | **189.0** | **78.7** | 26.9 |
| Blunders | 0 | 0 | 1 | **8** | **2.3** | 1.0 |
| Mistakes | 2 | 2 | 4 | 3 | 2.8 | 1.0 |
| Inaccuracies | 6 | 3 | 11 | 12 | 8.0 | 5.0 |

### Detekovane patterny (autor)

| Pattern | Games | Co znamena |
|---------|-------|------------|
| **O — Stagnacni panika** | 2/4 (k9a1IXvp, Cm02bEZC) | Flat eval triggerne forcing — neforce, konsoliduj |
| **B — Automatic grab** | 2/4 (k9a1IXvp, Cm02bEZC) | 5.7% captures fatalnich — 3s pause "A CO ON?" |
| **C — Attention tunneling** | 2/4 (8jqLVD9c, Cm02bEZC) | Fixace na jednu oblast — po prvni chybe zkontroluj jinde |
| **J — Impulsive check block** | 1/4 (Cm02bEZC) | Block misto capture/kral — kdyz check, nejdriv kral |

### Klicovy insight

**Cm02bEZC je outlier — 8 blunderu (ACPL 189) v jedne hre.** Bez ni by byl autor prumer ACPL 42.0 — porad horsi nez opponent (26.9), ale ne katastrofalne. Tato hra obsahuje vsechny 4 autorovy patterny v akci: O → B → C → J.

Zbyvajici 3 hry (ACPL 32-49) ukazuji, ze autor hraje na ~1500-1600 urovni, ale opponent hral jeste lepe (ACPL 16-37). **Autor neprohral kvuli genialnim tahum opponentu — ale kvoli vlastnim chybam, ktere opponent nepotrestal, protoze sam nechyboval.**

### Priorita (Heisman: minimalizuj nejvetsi chybu prvni)

1. **P0 — Pattern B (Automatic grab):** 5.7% captures = blunder. Staci 3s pause pred kazdym capture.
2. **P0 — Pattern O (Stagnacni panika):** Kdyz eval plato 2+ tahy — neforce. Pockej.
3. **P1 — Pattern C (Attention tunneling):** Po prvni chybe — zvedni hlavu, zkontroluj jinde.
4. **P1 — Cm02bEZC endgame:** 8 blunderu v koncovce — to neni nahoda. Endgame technique a konsolidace.

---

*Report generated by coaching report pipeline (depth 12) + IM-level reasoning. 4 games from N2 pool, AUTHOR perspective. Cache: data/game_cache/{game_id}_{color}_d12.json. Patterns from lichess_match_patterns (author perspective, 4 games). Template 1 per CHESS_COACHING_PROMPT_TEMPLATES.md.*
