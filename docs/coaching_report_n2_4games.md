# IM Coaching Report: N2 Opponent Wins — 4 Games Detail

**Datum:** 2026-07-29 | **Perspektiva:** Opponent (oponent je "my")
**Vyber:** 4 hry z N2 poolu (12 opponent wins, 73-game report)
**Rozsah:** k9a1IXvp (zero-blunder, 16.1 ACPL), G40ssnlG (zero-blunder, 18.2 ACPL), 8jqLVD9c (1 blunder, 37.1 ACPL), Cm02bEZC (3 blundery, 36.0 ACPL)
**Zdroj:** data/game_cache/*_d12.json | lichess_match_patterns(game_ids=4)
**Metodika:** Template 1 — Per-Game Coaching Report (Heisman + Silman + [DATA]/[IM] split)

---

## Game 1: k9a1IXvp — Pirc Defense (B00)

### [DATA] Zakladni info

| Metrika | Hodnota |
|---------|---------|
| Strana | Black (opponent) |
| Result | 0-1 (opponent won) |
| Time control | 300+3 (Rapid) |
| ACPL | **16.1** |
| Accuracy | **97.6%** |
| Delka hry | 31 ply (15.5 moves) |
| Blundy | 0 |
| Chyby | 0 |
| Nepresnosti | 3 |

### [DATA] Fazovy breakdown

| Faze | Tahu | ACPL | Accuracy | Errors |
|------|------|------|----------|--------|
| Opening (ply 1-20) | 10 | **8.4** | 98.7% | 0 |
| Middlegame (ply 21-40) | 15 | **8.0** | 98.8% | 1 (inaccuracy) |
| Endgame (ply 41+) | 6 | 49.0 | 92.6% | 2 (inaccuracies) |

### [DATA] Error klasifikace

**Blunders (0):** None.

**Mistakes (0):** None.

**Inaccuracies (3):**
| Ply | Tah | cp_loss | Faze | Poznamka |
|-----|-----|---------|------|----------|
| 44 | Rb8 | 60 | mid | Rb8 slabsi nez Qxg5 — pasivni presun veze |
| 56 | Bb5+ | 111 | end | Bb5+ namiesto Qd4 — darovani tempa v koncovce |
| 58 | Qxe1+ | 147 | end | Qxe1+ namiesto Qa2 — zbytecna vymena dam v koncovce |

### [DATA] Pattern detection

Zadny pattern detekovan pro tuto hru samostatne. Pool detection (4 games) ukazuje C (Attention tunneling) a Q1 (Desperate Gambit) — ani jeden pro k9a1IXvp.

### [DATA] Silman imbalance assessment

**Klicove pozice:**

- **Ply 14-18 (opening → middlegame):** Bily da Qa4+ a Nc3-d5 — vytvari tlak na cerneho. Opak ma mirne horsi strukturu (izolovany pesec na d4 po exd4), ale ma aktivni figury. **Imbalance:** Bily ma mirkou vyhodu v prostoru a vyvoji, cerny ma lepsi strukturu (zadne slabiny).

- **Ply 22-26 (critical):** Bily exchange na c6 (dxc6), cerny ma Bg5 pinned, bily Qxc6+ a cerny Bd7. Po O-O a Re8+ ma cerny iniciativu. **Imbalance:** Material vyrovnan. Cerny ma iniciativa + lepsi figury. Bily ma oslabeny kral (po O-O, ale F1 je otevrene).

- **Ply 32-36 (decision):** Cerny Bf6-Bxb2-Bf6 — aktivni hra, bere pesce na b2, ale vraci ho na f6. Neni to nejlepsi, ale udrzuje tlak. **Imbalance:** Material vyrovnan. Cerny ma dominantniho strelce na dlouhe diagonale.

- **Ply 40+ (endgame):** Cerny vyhral figuru (Rxb3). Koncovka je technicka — cerny ma kvalitu navic. **Imbalance:** Material +1 (quality). Cerny dominuje.

### [IM] Heisman-style error analyza

**Nejkritictejsi error:** Qxe1+ (ply 58, cp_loss=147). V koncovce s kvalitou navic a pasivnim bilym kralem je Qxe1+ zbytecna vymena. Spravne bylo Qa2 — udrzet damy na desce, tvorit hrozby. Po vymene ma cerny technickou koncovku, ale bez dam je postup pomalejsi.

**Typ chyby:** **Pozicni** — nejedna se o takticke prehlednuti, ale o spatne vyhodnoceni koncovky. Cerny mel vyhodu a chtel ji zjednodusit, ale vymena dam nebyla nutna.

**Time trouble:** S 300+3 casem a jen 31 tazich je time trouble nepravdepodobna. Chyby jsou zpusobene "endgame relaxation" — po vyhrani kvality opponent povolil.

### [IM] Tri veci co opponent udelal dobre

1. **Solidni opening bez chyb (0 errors v prvnich 20 tazich).** Pirc Defense brany korektne — zadne experimenty, zadne zbytecne oslabeni.
2. **Trpeliva hra pod tlakem (ply 14-26).** Po Qa4+ a Nd5 opponent nezpanikaril, udrzel figury v pohromade a vyuzil Bg5 pin k aktivite.
3. **Korektni konverze vyhody.** Po vyhrani kvality (ply 46) hral cisty endgame — zadne zbytecne riskovani.

### [IM] Jedna vec na zlepseni

Heisman: "Nejmensi chyba prvni." Inaccuracy Qxe1+ (ply 58) — v koncovce s vyhodou nesp_chat do zjednoduseni, udrzet damy na desce.

### [IM] Treninkova doporuceni

- **Tema:** Endgame technique — queen trade evaluation. Kdy vymenit damy a kdy ne.
- **Puzzle theme:** Queen endgame conversion. Lichess: "Queen vs Rook" endgame puzzles.
- **Otazka k zamyšlení:** "Kdyz mam vyhodu +2 a souper nema protihru — proc bych vymenoval damy?"

---

## Game 2: G40ssnlG — Italian Two Knights (C56)

### [DATA] Zakladni info

| Metrika | Hodnota |
|---------|---------|
| Strana | White (opponent) |
| Result | 1-0 (opponent won) |
| Time control | 300+3 (Rapid) |
| ACPL | **18.2** |
| Accuracy | **97.3%** |
| Delka hry | 15 ply (7.5 moves = resigned) |
| Blundy | 0 |
| Chyby | 0 |
| Nepresnosti | 2 |

### [DATA] Fazovy breakdown

| Faze | Tahu | ACPL | Accuracy | Errors |
|------|------|------|----------|--------|
| Opening (ply 1-13) | 10 | 25.1 | 96.2% | 2 (inaccuracies) |
| Middlegame (ply 14-15) | 5 | **4.4** | 99.3% | 0 |
| Endgame | — | — | — | — (hra skoncila v mid) |

### [DATA] Error klasifikace

**Blunders (0):** None.

**Mistakes (0):** None.

**Inaccuracies (2):**
| Ply | Tah | cp_loss | Faze | Poznamka |
|-----|-----|---------|------|----------|
| 15 | Nxf7 | 59 | op | Nxf7 misi nez exd4 (drobna tactical imprecision) |
| 19 | Qf3 | **117** | op | Qf3 misio cxd5 — vyhodnoceni centra |

**Komentar k ply 19:** Po Nxf7 Kxf7 je bily kral exponovany. Qf3 misto cxd5 je ztrata tempa — cerny ma cas na vyvin. Po cxd5 by bily oteviral centrum a zvysoval tlak.

### [DATA] Pattern detection

Zadny pattern detekovan pro tuto hru samostatne. Hra je prilis kratka (15 ply) na pattern detection.

### [DATA] Silman imbalance assessment

- **Ply 1-10 (opening):** Italian Two Knights — klasicky vyvin. **Imbalance:** Mirna vyhoda bileho v prostoru (center), ale cerny ma vyvinutu a harmonickou pozici.

- **Ply 13-15 (critical — rozhodnuti):** Nxf7 je hladajici takticka akce. Po Kxf7 a Bc4+ ma cerny kryti, ale neni to konec sveta. **Imbalance:** Material even, ale bily kral je exponovany.

- **Ply 19 (hra skoncila):** Autor (cerny) zrejme resignoval po Qf3. Neni jasne proc — pozice neni prohrana. Pravdepodobne se jedna o Pattern O (Stagnacni panika) z autorovy strany.

### [IM] Heisman-style error analyza

**Nejkritictejsi error:** Qf3 (ply 19, cp_loss=117). Pochybny tah, ktery nedava smysl v kontextu Italian — bily by mel hrat na centrum (cxd5). Qf3 ukazuje na nepochopeni pozicnich pozadavku.

**Typ chyby:** **Pozicni** — nespravne vyhodnoceni priority (centrum vs attack).

**Time trouble:** S 15 ply kratkou hrou a resignaci je mozne, ze autor (cerny) spachil pattern O (panika).

### [IM] Tri veci co opponent udelal dobre

1. **Aggresivni opening.** Italian Two Knights — hned od zacatku aktivni hra.
2. **Rychla dominance.** Po prvnich nepresnostech bileho autor (+ cerny) zrejme spachil paniku a resignoval.
3. **Nulovy blunder.** Bez chyb — opponent vyhral ciste.

### [IM] Jedna vec na zlepseni

Heisman: "Minimalizuj nejvetsi chybu prvni." Qf3 ply 19 — nesp_chat z centra do pasivniho presunu damy. Misto toho cxd5.

### [IM] Treninkova doporuceni

- **Tema:** Italian Two Knights — central control after Nxf7 sacrifice.
- **Puzzle theme:** Sacrifice assessment — when Nxf7 works and when it doesn't.
- **Otazka k zamyšlení:** "Po obeti na f7 je bily kral exponovany — co je dulezitejsi: centrum nebo attack na krale?"

---

## Game 3: 8jqLVD9c — Trompowsky Attack (A45)

### [DATA] Zakladni info

| Metrika | Hodnota |
|---------|---------|
| Strana | Black (opponent) |
| Result | 0-1 (opponent won) |
| Time control | 300+3 (Rapid) |
| ACPL | **37.1** |
| Accuracy | **94.4%** |
| Delka hry | 50 ply (25 moves) |
| Blundy | 1 |
| Chyby | 4 |
| Nepresnosti | 5 |

### [DATA] Fazovy breakdown

| Faze | Tahu | ACPL | Errors |
|------|------|------|--------|
| Opening (ply 1-20) | 10 | **14.3** | 1 inaccuracy |
| Middlegame (ply 21-40) | 18 | **67.7** | 1 blunder + 3 mistakes + 2 inaccuracies |
| Endgame (ply 41-50) | 22 | 27.8 | 1 mistake + 1 inaccuracy |

### [DATA] Error klasifikace

**Blunders (1):**
| Ply | Tah | cp_loss | Faze | Detail |
|-----|-----|---------|------|--------|
| 46 | **Ne5** | **368** | mid | Eval: +374 → +13. Critical positional error — jezdec na e5 nema oporu |

**Mistakes (4):**
| Ply | Tah | cp_loss | Faze |
|-----|-----|---------|------|
| 28 | Re8 | 155 | mid | Pasivni presun veze |
| 38 | c6 | 191 | mid | Oslabeni struktury |
| 72 | Qe7 | 155 | end | Spatne umisteni damy |
| 88 | Bg4 | 299 | end | Chybny presun strelce |

**Inaccuracies (5):** g6 (69), Bxb2 (112), Qe7 (147), Rd7 (79), d2 (79)

### [DATA] Pattern detection

- **Pattern C — Attention tunneling** (confidence 85%): Detekovan pro tuto hru + Cm02bEZC. Max 5 consecutive errors threshold breached.

### [DATA] Silman imbalance assessment

**Critical positions:**

- **Ply 28 (Re8, 155cp):** Priprava na central push bez dostatecne opory. **Imbalance:** Bily ma vyhodu v centru (prostor), cerny je pasivni.

- **Ply 46 (Ne5, 368cp — blunder):** Jezdec se presune na e5, kde nema oporu a blokuje vlastniho strelce. Po c6-d5 a Bg4 je jezdec ztracen. **Imbalance:** Po tomto blundru bily dominuje — prostor, struktura, piece activity.

- **Ply 72-88 (endgame):** Cerny se snazi aktivovat figury, ale dela dalsi chyby. Eval skace +210 → +73 → +554. **Imbalance:** Material a pozice na strane bileho.

### [IM] Heisman-style error analyza

**Nejkritictejsi error:** Ne5 (ply 46, cp_loss=368). Jezdec na e5 nema oporu, blokuje vlastniho strelce na c3, a po Bg4 je napaden. Neni jasny plan za timto tahem.

**Typ chyby:** **Pozicni** — spatne vyhodnoceni piece placement. Jezdec neni na e5 stabilni (nema f6 pawn break, nema outpost support).

**Consecutive errors:** Od ply 28 do 88 — 5 errors v ruznych fazich. To potvrzuje Pattern C (Attention tunneling): opponent se fixoval na jednu oblast (presuny figur) a prehlizel strukturu.

**Time trouble:** S 300+3 casem a 25 tahy minimalni. Spis "stagnacni panika" (Pattern O) — opponent citil tlak a delal chyby v rozhodnutich.

### [IM] Tri veci co opponent udelal dobre

1. **Slusna obrana v koncovce.** Po ztrate vyhody v mid se opponent nevzdal, bojoval dalsich 20 ply v koncovce.
2. **Aktivni figury i zpasobem.** I v horsi pozici opponent stale hledal aktivni moznosti (i kdyz casto nepresne).
3. **Jedna vyhra.** I s 1 blunderem a 4 chybami — opponent vyhral. Autor (cerny) zrejme udelal jeste horsi chyby.

### [IM] Jedna vec na zlepseni

Heisman: "Nejmensi chyba prvni." Ne5 (ply 46, 368cp) — jezdec na e5 bez opory. Predm_yšlet piece placement — neumistovat figuru na pole, kde nema oporu.

### [IM] Treninkova doporuceni

- **Tema:** Piece stability — kdy je outpost bezpecny a kdy neni.
- **Puzzle theme:** Positional — overprotected knight vs hanging knight.
- **Otazka k zamy_sleni:** "Kdyz dávám jezdce na e5 — co se stane po Bg4? A kdo kryje e5 po f6?"

---

## Game 4: Cm02bEZC — Vienna Anderssen (C25)

### [DATA] Zakladni info

| Metrika | Hodnota |
|---------|---------|
| Strana | Black (opponent) |
| Result | 0-1 (opponent won) |
| Time control | 300+3 (Rapid) |
| ACPL | **36.0** |
| Accuracy | **94.6%** |
| Delka hry | 67 ply (33.5 moves) |
| Blundy | **3** |
| Chyby | 0 |
| Nepresnosti | 10 |

### [DATA] Fazovy breakdown

| Faze | Tahu | ACPL | Errors |
|------|------|------|--------|
| Opening (ply 1-20) | 10 | 28.3 | 2 inaccuracies |
| Middlegame (ply 21-40) | 14 | 28.3 | 3 inaccuracies |
| Endgame (ply 41-67) | 33 | **40.6** | **3 blundery + 5 inaccuracies** |

### [DATA] Error klasifikace

**Blunders (3) — vsechny v endgame, behem 4 tahu (ply 54-58):**
| Ply | Tah | cp_loss | Eval pred | Eval po | Faze |
|-----|-----|---------|-----------|---------|------|
| 54 | **d5** | **385** | +357 | -34 | end |
| 56 | **Qd6** | **315** | -25 | -340 | end |
| 58 | **Ra1+** | **347** | +106 | -234 | end |

**Mistakes (0):** None.

**Inaccuracies (10):** a5 (106), a4 (72), Bxd4 (72), + 7 dalsich v endgame.

### [DATA] Pattern detection

| Pattern | Confidence | Detail |
|---------|-----------|--------|
| **R — Endgame relaxation** | 57% | Blunder d5 (ply 54) — v koncovce s vyhodou (+357) opponent relaxuje |
| **C — Attention tunneling** | 85% | 3 consecutive blundery v 4 tazich (ply 54-58) — fixace na jednu oblast |
| **Q1 — Desperate Gambit** | 68% | Po eval <-3.0 opponent (autor) odmital exchange dam, vytvarel hrozby |

### [DATA] Silman imbalance assessment

**Ply 54 (d5 — blunder 385cp):** Opponent ma vyhodu +357. Tah d5 ma byt central push, ale po Qe5+ sach a dxe5 cerny ziska figuru. **Imbalance ZRUCENA behem 1 tahu** — z +357 na -34.

**Ply 56-58 (Qd6, Ra1+ — consecutive blundery):** Po d5 je opponent v soku. Qd6 je spatne — nema oporu. Ra1+ je desperace — da sach krali, ale vez je ztracena. **3 blundery v 4 tazich** — typicky Pattern C (attention tunneling).

**Konec hry:** Po techto blundrech ma cerny (autor) dominantni vyhodu. Opponent (bily) se snazi o desperate counterplay (Q1), ale bez uspechu.

### Critical eval swings

| Ply | Tah | Eval swing | Typ |
|-----|-----|-----------|-----|
| 54 | d5 | **391cp** (357 → -34) | Blunder |
| 56 | Qd6 | **315cp** (-25 → -340) | Blunder |
| 58 | Ra1+ | **340cp** (106 → -234) | Blunder |

### [IM] Heisman-style error analyza

**Nejkritictejsi error:** d5 (ply 54, cp_loss=385). S vyhodou +357 a aktivnimi figurami neni duvod k centralnimu pushi bez opory. Po Qe5+ sachu ztrati opponent figuru.

**Typ chyby:** **Takticka i pozicni.** Takticky: opponent prehledl Qe5+ sach. Pozicni: v koncovce s vyhodou neni duvod pushovat centrum — staci konsolidace.

**Consecutive blunder syndrome (Pattern C):** 3 blundery v 4 tazich. To je klasicky "collapse" — po prvnim velkem blundru se opponent psychicky sesype a dela dalsi.

**Pattern R (Endgame relaxation):** Prvni blunder (d5) je typicky endgame relaxation — opponent mel vyhodu, citil se komfortne, prestal pocitat.

**Pattern Q1 (Desperate Gambit):** Po ztrate vyhody opponent (autor) prehazel na chaos mode — odmital vyhodne exchange, vytvaret hrozby. To je v koncovce spravny reflex — ale melo prijit driv.

### [IM] Tri veci co opponent udelal dobre

1. **Slusne na konci.** I po 3 blundrech a ztrate vyhody se opponent (bily) snazil o despere counterplay (Q1). Neni to krasne, ale je to lepsi nez pasivni cekani.
2. **Bojoval az do konce.** 67 ply — nejdelsi hra ze 4. Vzdor catastrophic collapse se opponent nevzdal.
3. **V koncovce hledal aktivitu.** I v horsi pozici stale hledal hrozby a checks.

### [IM] Jedna vec na zlepseni

Heisman: "Nejmensi chyba prvni." d5 (ply 54, 385cp). V koncovce s vyhodou (+357) neni duvod k riziku. Konsolidace, ne central push.

### [IM] Treninkova doporuceni

- **Tema:** Endgame consolidation — jak prevest vyhodu na vyhru bez rizika.
- **Puzzle theme:** "Convert a winning endgame" — positions where one side has +3 advantage and must find the safe path.
- **Otazka k zamy_sleni:** "Proc jsem hral d5? Co jsem cekal, ze se stane? A co jsem mel hrat misto toho?"

---

## Cross-Game Summary (4 N2 games)

### Aggregate

| Metrika | k9a1IXvp | G40ssnlG | 8jqLVD9c | Cm02bEZC | Avg |
|---------|-----------|----------|----------|----------|-----|
| ACPL | 16.1 | 18.2 | 37.1 | 36.0 | **26.9** |
| Blunders | 0 | 0 | 1 | 3 | 1.0 |
| Mistakes | 0 | 0 | 4 | 0 | 1.0 |
| Inaccuracies | 3 | 2 | 5 | 10 | 5.0 |

### Pozorovani

1. **Zero-blunder hry (k9a1IXvp, G40ssnlG) maji ACPL < 20** — opponent hraje ciste, autor nema sanci.
2. **Hry s blundry (8jqLVD9c, Cm02bEZC) maji ACPL 36-37** — opponent dela chyby, ale autor dela jeste vice.
3. **Cm02bEZC je priklad catastrophic collapse — 3 blundery v 4 tazich** (ply 54-58). Vsechny v endgame. To je Pattern R (Endgame relaxation) → C (Attention tunneling).
4. **8jqLVD9c ukazuje pozvolnejsi kolaps** — 5 erroru rozlozenych pres 60 tahu. Pattern C dominantni.

### Zaver pro autora

Tyto 4 hry potvrzuji insight z 73-game reportu: **n2 opponents nevyhravaji genialitou, ale absenci chyb.** Dve hry s nulovym blunderem (ACPL 16-18) ukazuji, ze staci hrat ciste a autor udela chybu sam. Dve hry s blundry ukazuji, ze i s chybami opponent vyhraje, pokud autor dela vic.

---

*Report generated by coaching report pipeline (depth 12) + IM-level reasoning. 4 games from N2 opponent pool. Cache: data/game_cache/{game_id}_{color}_d12.json. Patterns from lichess_match_patterns. New prompt structure per CHESS_COACHING_PROMPT_TEMPLATES.md — Template 1 (Per-Game).*
