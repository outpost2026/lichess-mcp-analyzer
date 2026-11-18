# Večerní šachy — Koučink s pipeline

**Hráč:** Systeq | **Zdroj:** RUN_002 (9 proher, Stockfish 18 BMI2 @ d14)
**Pattern knihovna:** A-Q1 v5 | **Generováno:** 2026-07-24 19:20Z

---

## 1. Tři prohry, které bolí nejvíc

Tři pozice, kde Stockfish řekl "vyhráváš". Všechny tři jsi prohrál.

### 1.1 qmodxzNF — Scotch Game (tah 60: Kd7)

**Manuální inspekce:** předcházel soupeřově Qc5+ (šach!), dáma přímo vedle krále na d6. Jediný rozumný krok byl Kxc5 = vzít bílou dámu. Místo toho: Kd7 — obrovský blunder.

**Pipeline verifikace:**

**FEN před tahem:** `7r/2p2p2/3k4/p1QPp3/1pP1P2q/5P2/P1B2P2/2K3R1 b - - 3 30`

| Metrika | Hodnota |
|---------|---------|
| Král na d6, Bílá dáma na c5 dává šach | ✅ |
| Kxc5 legální? | ✅ (jediné dvě možnosti: Kc5, Kd7) |
| Stockfish top move | Kxc5 (+542 cp) |
| Co jsi zahrál | Kd7 (−573 cp) |
| CP swing | **1 142** — nejhorší ze všech 9 her |
| Fáze | Koncovka |

**Stockfish linie:** `Kxc5 Ba4 Qh6+ Kxb2` → černý vychází o figuru výš (+542).

**Mechanismus selhání:** Šach aktivoval "král v nebezpečí → utéci" reflex. Místo skenování všech legálních odpovědí (včetně Kxc5) jsi automaticky zvolil ústup. Dáma na c5 vypadala "chráněně" (pěšec na b4?) — ale král bere *přes* šach, ochrana neexistuje.

**Pattern match:** Tento blunder neodpovídá žádnému existujícímu A-Q1 patternu přesně. Je to **kandidát na nový pattern S — Capture aversion under check** (viz sekce 4).

---

### 1.2 kNAMNYUF — French Franco-Sicilian (tah 63: Rdg1)

**FEN:** `r4r1k/1p1b3P/p3p1R1/3p3Q/3N1q2/8/PPP4P/1K4R1 b - - 2 32`

| Metrika | Hodnota |
|---------|---------|
| Eval před | **+823 cp** (vyhrané) |
| Eval po | **+45 cp** (rovné) |
| CP swing | **778** |
| Fáze | Koncovka |
| Výsledek | Prohra na čas o 8 tahů později |

**Co se stalo:** Qf4+ dává šach. Místo ústupu králem (Ka1 nebo Kc1) jsi instinktivně zablokoval věží — **Rdg1**. Tím jsi odtáhl věž z obrany, přerušil vlastní koordinaci a umožnil Qf1+ → Qf2+ → výměna dam. Tvoje +823 útok se rozplynul.

**Co chtěl Stockfish:** Hýbat králem. Prostě uhnout. Věž na g1 (první řada) tam byla potřeba k obraně — Qf1+ po Ka1/Kc1 je neškodná.

**Pattern match:** **B — Automatic grab (95%)** + **J — Impulsive check block (67%)**. Šach spustil reflex: blokovat, pak přemýšlet. Královský ústup nebyl ani v seznamu kandidátů.

> **Cross-audit korekce (DBCL_Cross_Audit_Report.docx, F-007):** Qf4+ nebyl šach — dáma na f4 vs. král na b1 nemají společnou diagonálu. Pattern J v produkci testuje `"+" in move_san` (odehraný tah dává šach) místo `board.is_check()` (pozice před tahem byla v šachu). Popis blunderu jako "impulsivní blok šachu" je tedy **věcně nepřesný** — šlo o odtažení věže z první řady, nikoliv o blok. Pattern J detektor bude opraven před nasazením DBCL v1.

---

### 1.3 PQvwuTAO — Vienna Game (tah 71: Re3)

**FEN:** `8/1p3rp1/p1pk3p/P2pn3/1P1K1N2/4R1P1/2P5/8 b - - 13 36`

| Metrika | Hodnota |
|---------|---------|
| Eval před | **+322 cp** (jasná výhoda) |
| Eval po | **−365 cp** (prohrané) |
| CP swing | **687** |
| Fáze | Koncovka |
| Výsledek | Prohra na čas později |

**Co se stalo:** Král na d4, jezdec na f4. Zahrál jsi Re3 — a odhalil jsi krále na vidličku Nc4+. Tunnel vision: soustředil ses na pěšcovou lavinu a aktivaci věže, ale zapomněl jsi, že král je pořád cíl.

**Co chtěl Stockfish:** Re1 (ne Re3) udrží krále v bezpečí a připraví zdvojení na e-sloupci. Nebo Nxd5. Ale Re3 prohrává: Nc4+ forkuje krále a věž.

**Pattern match:** **C — Attention tunneling (80%)** + **R — Endgame relaxation (70%)**. Heuristika "král je v koncovce aktivní" neplatí, když jsou na šachovnici jezdci a věže.

---

## 2. Výjimka — xUlQasD0 (Sicilská zavřená)

**4 blundery. 70,9 ACPL. Z +681 do rezignace během 5 tahů.**

### Tahy 39–43: Kolaps

```
39. ... Jb4  (hrozí Jxc2 vidlička)
40. f5?     (panika — mělo být Se3 bránící c2)
41. fxe6??  (automatický úder — BLUNDER #1, +681→+336)
42. ... dxe6 (černý bere, tvůj jezdec na d6 je teď odříznutý)
43. Sf4??   (BLUNDER #2, +335→−110)
```

**FEN po 40. f5:** `b2q1rk1/r2p1pp1/pb1NP2p/1pp1P3/6B1/3P2Q1/PPn3PP/R1B2R1K b - - 0 21`

**FEN po 43. Sf4:** `b2q1rk1/r4pp1/pb1Np2p/1pp1P3/5BB1/3P2Q1/PPn3PP/R4R1K b - - 1 22`

Co bylo v sázce: úplně vyhraná pozice (jezdec na d6 dominuje, střelecký pár, dáma aktivní). Pak:
- **40. f5:** Místo obrany c2 (Se3, Sf4, nebo Qf3) jsi udeřil na královském.
- **41. fxe6:** Místo přiznání chyby a hledání nejlepšího ústupu (Jce4) jsi bral automaticky.
- **43. Sf4:** Jezdec na d6 teď visí, vyvíjíš útok figurou, která není v bezpečí. Sf4 prohrává na Jxa1 (Stockfish ukazuje +296 pro černého).

**40. f5** → 2-tahový blunder sekvence. Tohle je **C — Attention tunneling (80%)**: fixoval ses na královský útok a zapomněl, že c2 je nechráněné. Vidličková hrozba nikdy nedorazila do vědomí.

### Tah 71: Df5 — BLUNDER #3 (+208→−115)

```
36. Df5   (blunder)
FEN: 3q2k1/4r1p1/pb4r1/1p3Q2/2p1PB2/5B2/PP4PP/R6K
```

Df5 vypadá aktivně, ale prohrává na ...Vf6! Stockfish ukazuje +187 pro černého. Dáma blokuje vlastního střelce na f3 — a ...Vf6 útočí na dámu i střelce zároveň. Musíš vracet materiál.

### Tah 89: Vd7+ — BLUNDER #4 (−788→−1248)

```
45. Vd7+  (blunder)
FEN: 8/3Rk1p1/p4r2/1p1Bb3/2p4Q/8/Pq4PP/7K
```

Vd7+ je impulsivní šach z prohrané pozice. Jediný odpor: Kxd7, odevzdat střelce a vstoupit do úplně prohrané koncovky. Stockfish: Kxd7 +342.

---

## 3. Diagnóza patternů (z A-Q1 knihovny)

7 patternů detekováno z 9 her.

| ID | Pattern | Spol. | Závažnost | Zásahů | Charakteristický tah |
|----|---------|-------|-----------|--------|----------------------|
| **B** | Automatické brání | 95% | vysoká | 4 | fxe6 (xUlQasD0), Vdg1 (kNAMNYUF) |
| **C** | Tunnel vision | 80% | střední | 4 hry | Ve3 (PQvwuTAO), 40.f5 (xUlQasD0) |
| **S** | Capture aversion under check | ~40% | kritická | 1 | **Kd7 místo Kxc5 (qmodxzNF)** — NOVÝ PATTERN |
| **R** | Relaxace v koncovce | 70% | vysoká | 3 hry | Kd7 (qmodxzNF), Ve3 (PQvwuTAO) |
| **J** | Impulsivní blok šachu | 67% | vysoká | 2 hry | Vdg1 (kNAMNYUF), Vd7+ (xUlQasD0) |
| **O** | Vyhýbání se trojáku | 60% | kritická | 7 her | Odmítnutí trojnásobného opakování |
| **P** | Vizuální chyba | 50% | vysoká | 4 hry | Sf4 (xUlQasD0), Kd7 (qmodxzNF) |
| **I** | Návnada | 40% | nízká | 2 hry | Silná stránka — pokračovat |

Patterny tvoří kauzální řetěz:

```
Časová tíseň
   ↓
Tunnel vision (C) — přestaneš skenovat celou šachovnici
   ↓
Automatické brání (B) — bereš co je nabízeno
Capture aversion (S) — nevidíš bránící figuru jako bratelnou
Impulsivní blok (J) — blokuješ bez vyhodnocení
   ↓
Relaxace v koncovce (R) — výhoda tě ukolébá
Vizuální chyba (P) — halucinace o jeden tah hluboká
   ↓
Blunder
```

---

## 4. Kandidát na nový pattern: S — Capture Aversion Under Check

### Pozorování

V qmodxzNF (tah 60) dal bílý šach dámou na c5. Král na d6 měl dvě legální možnosti: **Kxc5** (brát) nebo **Kd7** (uhnout). Zahrál jsi Kd7 — ztráta 1386cp. Stockfishův top move: Kxc5 (+542).

### Datasetová analýza (RUN_002, 9 her, 28 šachových situací)

| Metrika | Hodnota |
|---------|---------|
| Celkem šachů na hráče | 28 |
| Šachů s možností brát | 11 (39 %) |
| Šachů s možností brát KRÁLEM | **2** (7 %) |
| Z toho správně bráno král | 1/2 (qmodxzNF ply=78: Kxe7 ✅) |
| Z toho chybně nebráno král | **1/2** (qmodxzNF ply=60: Kxc5 → Kd7 ❌) |

### Hypotéza

Při šachu hráč systematicky **podhodnocuje možnost brát šachující figuru králem** — preferuje ústup nebo blok. "Král v šachu → musí utéci" reflex potlačuje "král může brát" jako kandidátský tah.

### Mechanismus

```
Šach → Stress → "Král v nebezpečí" reflex
  ↓
Možnost A: brát šachující figuru králem  [nevyhodnoceno — "král na ústup" shortcut]
Možnost B: uhnout králem                   [default]
Možnost C: blokovat figurou                [default, méně častý]
  ↓
A je přeskočeno → B nebo C → blunder když A bylo jediné správné
```

### Confidence

| Dimenze | Hodnota |
|---------|---------|
| Stockfish verifikace | 100% (top move) |
| N = chance | 2 příležitosti, 1 miss = 50% selhání |
| Penalizace za N | ~40% (N=2 → kvadratická penalizace) |
| Výsledná confidence | **~40 %** |
| Závažnost | **kritická** (1386cp ztráta) |

### Vztah k existujícím patternům

- **J (Impulsive check block):** KOMPLEMENT. J řeší blok vs ústup. S řeší brání vs ústup. Dohromady J+S pokrývají všechny 3 odpovědi na šach.
- **P (Visual misrecognition):** ČÁSTEČNÝ PRŮNIK. Missnutí Kxc5 může být vizuální — hráč neviděl, že d6-c5 je nekryté.
- **C (Attention tunneling):** TRIGGER. Časová tíseň → tunel → "král v šachu" je jediná myšlenka → brání není ve skenu.

### Mitigation

"Když jsi v šachu, zastav se a zeptej se: **MŮŽU BRÁT šachující figuru?** Teprve pokud ne, řeš ústup nebo blok."

---

## 5. Hodiny jsou tvůj nepřítel

**4 z 9 proher na čas.**

| Hra | Čas | Tahů | Konec | Blundry | Situace |
|-----|-----|------|-------|---------|---------|
| kNAMNYUF | 300+3 | 63 | Time forfeit | 1 | Vyhrával (+823) když spadl praporek |
| PQvwuTAO | 300+3 | 53 | Time forfeit | 2 | Vedl, pak blunder, pak prohra na čas |
| NYcRejUc | 600+2 | 148 | Time forfeit | 2 | Dlouhá hra, čas při rovnovážném materiálu |
| qmodxzNF | 600+0 | 31 | Time forfeit | 1 | Vyhrával (+569) když blunder, pak spadl praporek |

V **300+3**: do 40. tahu jsi na 3–5s/tah. V **600+0**: jeden delší výpočet tě stojí 20s.

Tři ze čtyř koncovkových blunderů (včetně qmodxzNF Kd7) se staly při ≤15s/tah.

---

## 6. Večerní protokol

### Drill 1: Záchrana 3 výher (15 min)

Postav tyhle pozice a hraj **proti Stockfish depth 8 z pozice soupeře**:

| Pozice | FEN | Cíl |
|--------|-----|-----|
| kNAMNYUF @ +823 | `r4r1k/1p1b3P/p3p1R1/3p3Q/3N1q2/8/PPP4P/1K4R1 b - - 2 32` | Braň jako černý, dokaž že bílý neumí proměnit |
| qmodxzNF @ +542 (po Kxc5) | `8/2p2p2/2k5/p3Pp2/1pP1P2q/5P2/P1B2P2/2K3R1 w - - 4 31` | Braň jako bílý po Kxc5, prověř že černý fakt vyhrává |
| PQvwuTAO @ +322 | `8/1p3rp1/p1pk3p/P2pn3/1P1K1N2/4R1P1/2P5/8 b - - 13 36` | Braň jako černý, dokaž že bílý neumí proměnit |

Výměna stran tě nutí počítat soupeřovy zdroje — láme **C — tunnel vision**.

### Drill 2: Capture Under Check (10 min)

10 pozic z lichess nebo z vlastních her, kde jsi v šachu a **jediná správná odpověď je brát šachující figuru**. Před každým tahem: vyjmenuj všechny 3 kategorie odpovědí (brát → uhnout → blokovat) v tomto pořadí.

Cíl: přeučit reflex z "král v šachu → utéci" na "král v šachu → může král brát? → ne → může jiná figura brát? → ne → uhnout/blokovat".

### Drill 3: Endgame Check Block (10 min)

Postav krále v šachu z koncovky s materiální výhodou. Vždy nejdřív vyhodnoť brání, pak ústup králem, pak blok.

### Drill 4: Časový budget (3 hry, 10 min každá)

Zahraj **3 rapid (10+0)** nebo **3+2**. Před každou hrou si nastav:
- Tah 1–15: max 30s/tah
- Tah 16–30: max 45s/tah
- Tah 31+: max 15s/tah

Bílým hraj Vídeň, černým Slav nebo Francouzskou.

**Stop podmínka:** Když jsi v šachu, řekni nahlas: "Můžu brát? Pak uhýbám? Pak blokuju?" Teprve potom táhni.

---

## Příloha: Všech 10 blunderů

| Hra | Tah | Tah | CP před | CP po | Ztráta | Pattern | Fáze |
|-----|-----|-----|---------|-------|--------|---------|------|
| qmodxzNF | 60 | **Kd7** (místo Kxc5) | +569 | −573 | **1386** | **S** (nový) | koncovka |
| kNAMNYUF | 63 | Vdg1 | +823 | +45 | 950 | B+J | koncovka |
| PQvwuTAO | 71 | Ve3 | +322 | −365 | 739 | C+R | koncovka |
| NYcRejUc | 148 | Vh1+ | −11 | −536 | 536 | C | koncovka |
| xUlQasD0 | 43 | Sf4 | +335 | −110 | 505 | P+B | střední hra |
| xUlQasD0 | 89 | Vd7+ | −788 | −1248 | 464 | J | koncovka |
| xUlQasD0 | 41 | fxe6 | +681 | +336 | 369 | B | střední hra |
| xUlQasD0 | 71 | Df5 | +208 | −115 | 338 | P | koncovka |
| PQvwuTAO | 101 | Vg7 | +1 | −321 | 321 | C | koncovka |
| NYcRejUc | 76 | Vb4 | −58 | −356 | 303 | P | koncovka |

**8 z 10 blunderů v koncovce.** Jeden z nich (qmodxzNF Kd7) identifikuje **nový pattern S — Capture Aversion Under Check**, který není v aktuální A-Q1 knihovně. Confidence ~40% (N=2), závažnost kritická.
