# IM Coaching Report: NktJfZZy — Pirc Defense (B00)

**Datum:** 2026-07-30 | **Perspektiva:** Autor (White)
**Result:** 1-0 (autor vyhral) | **Time control:** 300+3 (Rapid)
**Zdroj:** data/game_cache/NktJfZZy_white_d14.json
**Metodika:** Template 1 — Per-Game Coaching Report — [DATA]/[IM] split, overeno z cache

---

## [DATA] Zakladni info

| Metrika | Hodnota |
|---------|---------|
| Strana | White (autor) |
| Result | **1-0** (autor vyhral) |
| Time control | 300+3 |
| Opening | Pirc Defense (B00) |
| Delka hry | 73 ply (36.5 moves) |
| **ACPL** | **49.4** |
| **Accuracy** | **92.6%** |
| Blundy | **3** |
| Chyby | 0 |
| Nepresnosti | 5 |

## [DATA] Fazovy breakdown

| Faze | Tahu | ACPL | Errors |
|------|------|------|--------|
| Opening (ply 1-20) | 10 | 25.3 | 2 inaccuracies |
| **Middlegame** (ply 21-43) | 12 | **92.4** | **3 blundery + 2 inaccuracies** |
| Endgame (ply 45-73) | 15 | 15.6 | 1 inaccuracy |

## [DATA] Error klasifikace

### Blunders (3) — VSECHNY v midgame

| # | Ply | Tah | cp_loss | Eval pred | Eval po | Co se stalo |
|---|-----|-----|---------|-----------|---------|------------|
| 1 | 33 | **Qd2** | **371** | +146 | -223 | Dama na d2 blokuje vlastni figury, nema oporu. Po Nd5 od cerneho je dama napadena. |
| 2 | 37 | **Ng5** | **469** | +278 | -180 | Jezdec na g5 — hrozba Nxf7, ale cerny ma Re8 a Bf8, jezdec je nestabilni a po Kh8/h6 ztraceny. |
| 3 | 43 | **Qg5** | **300** | -192 | -484 | Dama na g5 — opet nestabilni placement. Po h6 od cerneho musi utect a ztraci tempo |

### Inaccuracies (5)

| Ply | Tah | cp_loss | Faze | Poznamka |
|-----|-----|---------|------|----------|
| 9 | Bxf6 | 82 | op | Vymena strelce za jezdce — dava cernemu par strelcu + tempo |
| 17 | Bb5 | 66 | op | Strelec na b5 muze byt zahnan (a6/c6) |
| 23 | e5 | 68 | mid | Predcasny push — oslabuje d5 |
| 27 | c4 | 76 | mid | Dalsi predcasny push |
| 57 | Rf4 | 53 | end | Vez na f4 bez opory |

### Zadne mistakes (0)

## [DATA] Pattern detection

Zadny pattern detekovan — single game je prilis mala sample. Nicmene **Q2 (Win despite blunder)** by byl relevantni: autor vyhral i pres 3 blundery.

## [DATA] Silman imbalance assessment

### Klicove pozice

**Ply 1-20 (opening):** Pirc Defense. Autor hra Bg5, Bxf6 — vymena strelce za jezdce. **Imbalance:** Material even, ale cerny ma par strelcu + vyvin. Autor ma mirnou prostorovou vyhodu (e5, d4, f4).

**Ply 33 (Qd2 — blunder):** Cerny prave udelal chybu (ply 32, +335 swing), eval skocil z -189 na +146. Autor ma sanci na utok, ale Qd2 je **pasivni — nedava hrozby a blokuje vlastni figury.** Spravne bylo Qe2 nebo Rd1. **Imbalance:** Po Qd2 se situace otaci — cerny ma material even a lepsi figury (par strelcu).

**Ply 37 (Ng5 — blunder):** Autor prave hral Nd5 (ply 35) a ziskal vyhodu (+239). Misto konsolidace hraje Ng5 — jezdec na g5 je napaden (h6) a nema oporu. **Imbalance:** Cerny ma par strelcu + prostorovou vyhodu.

**Ply 64-73 (obrat):** Cerny ma dominantni vyhodu (-547). Pak cerny blunder (ply 64, swing +771) — autor okamzite hraje h6+!, Rf8+, Rxg8+, Qc8+, Qxd8#. **Imbalance:** Zcela obracena — z -547 na mat behem 4 tahu.

## [IM] Heisman-style error analyza

### Nejkritictejsi error: Ng5 (ply 37, cp_loss=469)

Tento blunder je nejhorsi z tri — ztrati vyhodu (+278 → -180) v momente, kdy autor prave ziskal iniciativu (Nd5). Jezdec na g5 visi — po h6 je napaden a po Kh1 nemuze byt branen. Spravne bylo konsolidovat s Be3 nebo Qe2.

**Typ chyby:** **Takticka** — autor spravne citil, ze ma iniciativu, ale vybral si spatny nastroj. Misto Ng5 mel hrat Qe2 (vyvoj damy, hrozba na e6) nebo Be3 (konsolidace). Ng5 je prehnane agresivni — jezdec nema outpost na g5 (nema oporu).

### Qd2 (ply 33, cp_loss=371)

Autor prave dostal dar od cerneho (blunder +335) a mel sanci na rozhodujici utok. Misto toho hraje Qd2 — pasivni, blokujici vlastni figury. Spravne bylo Qe2 (vyvoj, kontrola e6, pripadne Qg4 s hrozbami).

### Qg5 (ply 43, cp_loss=300)

Treti blunder — uz v horsi pozici autor stale force. Qg5 je desperace — dama nema oporu, cerny h6 ji zene. Spravne bylo Qe2 nebo priznat si horsi pozici a konsolidovat.

### Time trouble

300+3, 73 tahu — casovy tlak je mozny (36.5 tahu v rapidu = ~8 sec/tah), ale ne ospravedlnuje 3 blundery.

## [IM] Tri veci co autor udelal dobre

1. **Kapitalizace na opponentove chybe (ply 64-73).** Kdyz cerny blunderl (ply 64, swing +771), autor okamzite hral h6+ a behem 4 tahu dal mat. To je vyborne nacitani critical momentu — zadne vahani, zadna dalsi chyba.

2. **Nd5 (ply 35).** Po Qd2 blundru a opponentove dalsi chybe autor nasel spravny tah — jezdec na d5 aktivni, centralni, s hrozbami.

3. **Endgame technika (ACPL 15.6).** I v horsi pozici (-500 az -650) autor pokracoval — Rf6, Rf4, Rdf1, Rf5, h5. Aktivni obrana. A pak h6+ v pravou chvili.

## [IM] Jedna vec na zlepseni

Heisman: "Nejmensi chyba prvni." **Ng5 (ply 37) — jezdec na g5 bez opory.**

Po Nd5 (+239) mas iniciativu. **Nedavej ji pryc jezdcem bez opory.** Misto Ng5: Qe2 (vyvin) nebo Be3 (konsolidace). Jezdec na g5 je impulzivni — "chci utocit, dam jezdce tam" — ale nema to oporu.

## [IM] Treninkova doporuceni

- **Tema:** Piece placement — jezdec na g5 neni outpost, neni stabilni, je to impulsivni forcing.
- **Puzzle theme:** "Initiative consolidation" — pozice kde mas vyhodu (+1..+2) a musis najit tichy tah (konsolidace), ne forcing.
- **Otazka k zamyšlení:** "Kdyz mam vyhodu v midgame — co je dulezitejsi: nova hrozba nebo konsolidace? A jak poznam, ze je jezdec na g5 stabilni?"

---

## Appendix: Critical moments timeline

| Ply | Barva | Tah | Eval | Co se deje |
|-----|-------|-----|------|-----------|
| 1-20 | W | Bg5, Bxf6 | 50→-38 | Opening — autor ztrati par strelcu |
| 23 | W | e5 | -42→-114 | Inaccuracy — predcasny push |
| 27 | W | c4 | -137→-219 | Inaccuracy — dalsi push |
| **32** | **B** | **(chyba)** | **-189→+146** | **Opponent blunder (+335cp)** |
| **33** | **W** | **Qd2** | **+146→-223** | **Autor nevyuziva sanci — pasivni Qd2 (BLUNDER 371cp)** |
| **34** | **B** | **(chyba)** | **-223→+201** | **Opponent dalsi blunder (+424cp)** |
| 35 | W | Nd5 | +201→+239 | Autor spravne kapitalizuje |
| **37** | **W** | **Ng5** | **+278→-180** | **Impulzivni jezdec (BLUNDER 469cp)** |
| 41 | W | Nxe6 | -167→-212 | Snaha o aktivitu |
| **43** | **W** | **Qg5** | **-192→-484** | **Desperace (BLUNDER 300cp)** |
| 45-63 | W | Rf6,Rf4,Rdf1,Rf5 | -500→-650 | Aktivni obrana v horsi pozici |
| **64** | **B** | **(chyba)** | **-547→+224** | **Opponent fatalni blunder (+771cp)** |
| **65** | **W** | **h6+** | **+224→+530** | **Autor okamzite tresta — h6+!** |
| 67-73 | W | Rf8+, Rxg8+, Qc8+, Qxd8# | →MATE | Ciste dokonceno |

### Zaver

Tato hra je ucebnice **Q2 (Win despite blunder)** — 3 blundery autora, 3 blundery oponenta. Rozdil je v nacasovani: posledni blunder udelal opponent (ply 64), autor ho okamzite potrestal. Hra ukazuje ze **neni dulezite kolik chyb udelas, ale kdy je udelas — a jestli umis potrestat chyby soupere.**

*Report generated by coaching report pipeline (depth 14) + IM-level reasoning. NktJfZZy_white_d14.json. Template 1 per CHESS_COACHING_PROMPT_TEMPLATES.md.*
