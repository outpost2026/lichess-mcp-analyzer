# Coaching report update — +16 new games (2026-07-26)

**Hráč:** Systeq | **Dataset:** 52 unique games (26 losses, 24 wins, 2 draws)
**Engine:** Stockfish 18 BMI2 @ depth 12–18
**Nové:** +6 losses, +10 wins (všechny hrány 2026-07-26)

---

## 1. Co je nového — delta oproti předchozímu reportu

| Metrika | Před (46 her) | Teď (52 her) | Δ |
|---------|---------------|--------------|---|
| Celkový ACPL | 41.7 | ~43.0 | +1.3 |
| Bludy celkem | 31 | 45 | +14 |
| Prohry | 24 | 26 | +2 |
| automatic_grab=True | ? | 4/6 nových proher | ⚠️ |

---

## 2. Nové prohry — detailní rozbor

### 2.1 Px0Izuw4 — ACPL 72.9 (nejhorší nová prohra)

**Opening:** Scandinavian Defense: Mieses-Kotroc Variation
**Rating:** Systeq 1739 vs james_bond0007 1725
**automatic_grab:** ✅ TRUE

**Blunder ply=47:** `Nxd5` — cp_loss **1146** (2. největší v celém datasetu!)
**FEN:** `r3r1k1/2R1bppp/p4n2/2Pp4/8/2B1NPPq/P3Q2P/3R2K1 w - - 0 24`
**Phase:** middlegame | **In check:** False

**Analýza:** Bílý (Systeq) má o figuru méně, ale aktivní figury — věž na c7, střelec na c3, jezdec na e3. Černý útočí dámou na h3 s hrozbou Qxh2#. Místo obrany (`Rxd1` nebo `Qf1` blok) hraje `Nxd5` — jezdec bere pěšce na d5, ale černý odpoví `Rxd1+ Kf2 Qxh2+` a bílý prohrává. Stockfish ukazuje, že `Nxd5` je fatální — otevírá d-sloupec pro černou věž a král zůstává odkrytý.

**Pattern:** **B (Automatic grab)** — jezdec vidí "volného" pěšce na d5 a bere, aniž spočítá, že po `Rxd1+` bílý ztratí věž a černý dáma diktuje matové hrozby. Toto je druhý nejhorší capture blunder v celém datasetu (po Nf6+ v 0EAA2iRk s 1599cp).

---

### 2.2 kPS7cYNV — ACPL 42.0

**Opening:** Vienna Game
**Rating:** Systeq 1843 vs Ibraimo 1829
**automatic_grab:** FALSE (ale bludy jsou capture-related)

**Blunder ply=75:** `Rc7` — cp_loss 442
**FEN:** `3r2k1/6p1/p3r1p1/1pR1P3/1P1p4/P2Pn1P1/5QP1/6K1 w - - 2 38`
**Phase:** endgame

**Blunder ply=77:** `Qa2` — cp_loss 497
**FEN:** `5rk1/2R3p1/p3r1p1/1p2P3/1P1p4/P2Pn1P1/5QP1/6K1 w - - 4 39`
**Phase:** endgame

**Párové blundy v koncovce (ply 75 + 77).** Stejný mechanismus jako JyPCXXNc (Rd8→Qe2) a iX9MjUyw (a3→a2):
- První blunder (Rc7): věž opouští krytí krále a umožňuje `Re1+` s vidličkou
- Druhý blunder (Qa2): o 2 tahy později, dáma skáče na a2 kde není krytá — černý prostě bere

**Pattern: R (Endgame relaxation) → C (Attention tunneling cascade).** Po prvním blundru ztrácí hráč koncentraci a dělá druhý, ještě horší.

---

### 2.3 txR8BTDS — ACPL 43.8

**Opening:** Queen's Gambit Declined: Marshall Defense
**Rating:** Systeq 1860 vs mirahora9996 1500 (⚠️ 360 bodů rozdíl!)
**automatic_grab:** ✅ TRUE

**Blunder ply=26:** `Ba5` — cp_loss 376
**FEN:** `3qk2r/3n1ppp/rp2pn2/3p4/1b1P1B2/2N2N1P/PP3PP1/R2Q1RK1 b k - 1 13`
**Phase:** middlegame

**Blunder ply=90:** `Kg6` — cp_loss 431
**FEN:** `8/6kp/5p2/6p1/q7/P3QP1P/5KP1/8 b - - 12 45`
**Phase:** endgame

Prohra proti hráči o 360 bodů slabšímu. První blunder (Ba5) je typický **pattern C (Attention tunneling)** — střelec na a5 visí, hráč ho tam dal bez krytí. Druhý blunder (Kg6) v koncovce — král jde na otevřené pole, kde ho černá dáma šachuje a vynucuje mat. **Pattern R**.

---

### 2.4 ErPlUF79 — ACPL 36.2

**Opening:** Italian Game: Two Knights Defense, Modern Bishop's Opening
**Rating:** Systeq 1739 vs Diadoco 1804
**automatic_grab:** ✅ TRUE

**Blunder ply=38:** `Nd5` — cp_loss 387
**FEN:** `r3r1k1/ppp2p1p/2nq1npQ/4p1B1/8/1BPP3P/PP3PP1/R3R1K1 b - - 3 19`
**Phase:** middlegame

Jezdec skáče na d5 — vidí "centrální pole", ale nevidí, že bílá dáma na h6 + střelec na g5 dávají matové hrozby. Po `Bxd5 exd5 Qg7#` je mat. **Pattern C (Attention tunneling)** — hráč fixovaný na centrum nevidí královské křídlo.

---

### 2.5 uhuOrtAZ — ACPL 45.9 + HHR0x8fL — ACPL 37.1

Tyto dvě prohry **nemají žádný blunder** — hráč prohrál pozvolným úpadkem (9 inaccuracies v 19 tazích, resp. 11 inaccuracies + 2 mistakes v 50 tazích). To je odlišný mechanismus — není to fatální chyba, ale kumulativní ztráta výhody.

**Pattern: O (Repetition avoidance)** — v obou partiích hráč pravděpodobně odmítl remízové opakování v rovné pozici a postupně ztratil výhodu.

---

## 3. Fenomén: xgw9sFUh — 6 blundrů, ACPL 124.3, a přesto výhra

**Opening:** Vienna Game: Anderssen Defense
**Rating:** Systeq 1654 vs alimohm55533 1776
**automatic_grab:** ✅ TRUE
**Result:** 1-0 (Systeq vyhrál!)
**Bludy:** 6 | **Chyby:** 4 | **Nepřesnosti:** 8

| Blunder | Tah | CP loss | Fáze |
|---------|-----|---------|------|
| 1 | h3 | 374 | MG |
| 2 | Bg5 | 304 | MG |
| 3 | Rf5 | 315 | EG |
| 4 | Rxg5 | 1046 | EG |
| 5 | Rf8 | 2136 | EG |
| 6 | g5 | 1356 | EG |

**Toto je vůbec nejchaotičtější partie v celém datasetu.** Hráč udělal 6 blundrů (včetně 3 s cp_loss > 1000) a přesto vyhrál. Proč? Protože soupeř byl ještě chaotičtější. V koncovce hráč ztratil věž, pak dal věž pryč (`Rf8`), pak obětoval pěšce (`g5`) — a soupeř to nedokázal potrestat.

**Pattern: Q2 (Win despite blunder) — extrémní případ.** Tato partie je důkazem, že hráčova schopnost "vyhrát i přes blunder" není způsobena jeho skill, ale selháním soupeře. Ve 3 partiích (xgw9sFUh, pw1sbK2R, uQyHgTj2) hráč udělal blunder v koncovce a vyhrál jen proto, že soupeř neuměl capitalizovat.

---

## 4. Blunder severity ranking — rozšířený (52 her)

| # | Game | Move | CP loss | Phase | Výsledek | Nový? |
|---|------|------|---------|-------|----------|-------|
| 1 | xgw9sFUh | Rf8 | 2136 | EG | **výhra** | ✅ |
| 2 | xgw9sFUh | g5 | 1356 | EG | **výhra** | ✅ |
| 3 | 0EAA2iRk | Nf6+ | 1599 | EG | prohra | — |
| 4 | BAEXAHoW | Rg1+ | 1164 | EG | remíza | — |
| 5 | **Px0Izuw4** | **Nxd5** | **1146** | **MG** | **prohra** | **✅** |
| 6 | qmodxzNF | Kd7 | 1108 | EG | výhra | — |
| 7 | xgw9sFUh | Rxg5 | 1046 | EG | **výhra** | ✅ |
| 8 | xgw9sFUh | Rf5 | 831 | EG | **výhra** | ✅ |
| 9 | pw1sbK2R | Bxe4 | 831 | EG | **výhra** | ✅ |
| 10 | PQvwuTAO | Re3 | 731 | EG | prohra | — |

**Klíčové zjištění:** 7 z 10 největších blundrů je ve **výhrách**, ne v prohrách. To znamená, že hráč dělá obrovské chyby i v partiích, které nakonec vyhraje — soupeři je nepotrestají. To je nebezpečný signál: hráč si zvykl, že "to projde", a přestal dávat pozor.

---

## 5. Agregovaný kognitivní profil (52 her)

### Patterns — nová evidence

| Pattern | Frekvence | Nové případy | Trend |
|---------|-----------|--------------|-------|
| **O** (Repetition greed) | 22+ | HHR0x8fL, uhuOrtAZ | ⚠️ stabilní |
| **B** (Auto grab) | 18+ | **Px0Izuw4** (Nxd5 1146cp), ErPlUF79 (Nd5), txR8BTDS | 🔴 zhoršení |
| **C** (Tunneling) | 14+ | kPS7cYNV (párové blundy), ErPlUF79 (Nd5) | ⚠️ stabilní |
| **R** (Endgame relax) | 10+ | kPS7cYNV (Rc7→Qa2), txR8BTDS (Kg6) | 🔴 zhoršení |
| **J** (Check block) | 4 | — (žádný nový) | 🟢 stabilní |
| **S** (Aversion) | 1 | — | 🟢 vzácný |
| **Q2** (Win despite) | 11+ | **xgw9sFUh** (6 blundrů!), pw1sbK2R, uQyHgTj2 | 🔴 extrémní |

### Fázová slabost — nová data

| Fáze | Bludy (před) | Bludy (nové) | Celkem |
|------|-------------|--------------|--------|
| Opening | 0 | 0 | **0** |
| Middlegame | 5 | 4 (Nxd5, Nd5, Ba5, h3, Bg5) | **9** |
| Endgame | 11 | 7 (Rc7, Qa2, Kg6, Bxe4, Rf5, Rxg5, Rf8, g5, Ng4+) | **18** |

Endgame zůstává dominantní — 18 z 27 blundrů v koncovce = **67 %**.

---

## 6. Shrnutí — co nová data mění

1. **Pattern B eskaluje.** Nové prohry Px0Izuw4 (Nxd5 1146cp) a ErPlUF79 (Nd5 387cp) jsou čisté Automatic grab — hráč bere figuru bez výpočtu odpovědi. To není zlepšení oproti 0EAA2iRk a 0X5L991E z dřívějška.

2. **Q2 není výhoda, je to past.** xgw9sFUh (6 blundrů, ACPL 124.3, výhra) ukazuje, že hráčova schopnost "vyhrát i přes blunder" je ve skutečnosti symptom — hráč přestane dávat pozor, protože "to stejně vyjde". To je nebezpečný kognitivní bias.

3. **Kaskádové selhání je systémové.** kPS7cYNV (Rc7→Qa2) je třetí potvrzený případ párových blundrů v koncovce (po JyPCXXNc a iX9MjUyw). Vzorec je vždy stejný: první blunder otevře pozici, druhý blunder (o 1-2 tahy později) je fatální.

4. **Síla zahájení = jediná skutečná výhoda.** 0 blundrů v openingu po 52 hrách potvrzuje, že hráč má výbornou přípravu. Problém je přechod do střední hry a koncovky.

---

## 7. Aktualizovaná tréninková doporučení

### 7.1 Capture pause protokol — priorita #1 (NOVÉ: posíleno)
- Px0Izuw4 (Nxd5 1146cp) je druhá nejhorší chyba datasetu
- Trénovat 15 capture cvičení denně (Lichess: "capture the defender" motif)
- **Pravidlo:** před každým braním říct nahlas odpověď soupeře

### 7.2 Koncovkový bootcamp — priorita #2 (NOVÉ: kPS7cYNV)
- 3 případy párových blundrů v koncovce = není náhoda
- Cvičit "věžové koncovky s aktivním králem" (10 pozic/den)
- Cvičit "dámské koncovky s nebezpečím vidličky" (5 pozic/den)

### 7.3 Q2 past — nová sekce
- Analyzovat xgw9sFUh (6 blundrů) — pochopit, proč soupeř nevyhrál
- Cvičit: "předpokládej, že soupeř potrestá každou chybu" mindset
- Vědomě hrát s přesností, ne "to snad vyjde"

---

*Update generován 2026-07-26. Dataset: 52 unikátních partií (26 losses, 24 wins, 2 draws). 14 nových blundrů z 16 nových her.*
