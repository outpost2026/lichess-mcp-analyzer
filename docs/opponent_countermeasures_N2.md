# Opponent Countermeasures: N=2 Discrete Player Generalization

**Datum:** 2026-07-28
**Zdroj:** 33 anonymnich her, dual-perspektiva (autor + opponent), depth 12 Stockfish
**Pool:** N=33 her jako jeden diskretni hrac → n1 = 27 proher, n2 = 6 vyher (18.2% win rate opponentu)
**Cil:** Zjistit co delaji oponenti, kteri porazeji autora, a inferovat protiakci pro zvyseni P vyhry v dalsich hrach

---

## [DATA] Autor v losses (n=6) vs Autor v wins (n=27)

### Hruby obraz

| Metrika | Autor v prohrach (n=6) | Autor v vyhrach (n=27) | Delta |
|---------|----------------------|----------------------|-------|
| ACPL | **35.5** | 32.5 | +3.0 cp |
| Blunders/game | **0.33** | 0.39 | -0.06 (lepsi) |
| Mistakes/game | 1.33 | 0.97 | +0.36 |
| Inaccuracies/game | **5.67** | 3.64 | **+2.03** |
| Best move rate | 59.1% | ~65% | -6 pp |
| Avg game length | **32.2** | 22.8 | +41% (delsi) |
| Best move rate | 59.1% | ~65% | -6% |
| Win rate as white | 75% (15/20) | — | — |
| Win rate as black | 92% (12/13) | — | — |

### Klicove zjisteni

> **Autor nehraje v prohrach vyrazne hur (35.5 vs 32.5 ACPL). Rozdil je v tom, ze opponent neblundruje vubec.** V 6 prohrach ma opponent 0 blunderu, autor ma 2. V 27 vyhrach ma opponent 21 blunderu — to je 0.78 blunderu na hru.

Autor prohrava proto, ze **opponent prestane delat fatalni chyby**, ne proto, ze by autor najednou zapomnel hrat sach.

---

## [DATA] Detail 6 n2 her (opponenti, kteri porazili autora)

### Per-game breakdown

| Hra | Zahajeni | Autor barva | AC-A | B-A | M-A | I-A | AC-O | B-O | M-O | I-O | Tahu | Rozhodujici chyba autora |
|-----|----------|------------|------|-----|-----|-----|------|-----|-----|-----|------|-------------------------|
| k9a1IXvp | Pirc Defense | W | 32.1 | 0 | 2 | 6 | **16.1** | **0** | 0 | 3 | 31 | ply 59 Rxe1 (174cp, endgame) |
| tDcFRclj | QGD Semi-Tarrasch | W | 45.2 | **2** | 2 | 4 | 34.8 | **0** | 3 | 6 | 40 | ply 19 Bd6 (459cp, opening) |
| LpJ8wgDG | Semi-Slav Normal | B | **24.4** | 0 | 0 | 1 | 50.4 | **0** | 3 | 4 | 20 | ply 23 Bd2 (173cp, middlegame) |
| wrYUwz6A | Scandinavian Nimzo | W | **19.5** | 0 | 0 | 3 | 32.4 | **0** | 0 | 3 | 23 | positional squeeze, zadna chyba |
| 8jqLVD9c | Trompowsky | W | 48.6 | 1 | 4 | 11 | 37.1 | **0** | 4 | 5 | 50 | ply 87 Bd1 (267cp, endgame) |
| 4gOcfuaY | Caro-Kann Advance | W | 43.4 | 0 | 2 | 10 | 44.3 | **0** | 1 | 4 | 29 | ply 37 Nd4 (164cp, middlegame) |

**Legenda:**
- AC = ACPL | B = Blunders | M = Mistakes | I = Inaccuracies
- A = Autor | O = Opponent
- W = White | B = Black
- **B-O je vzdy 0** — opponent v zadne vyhre neudelal blunder
- Zelene = exceptionalni (autor ACPL < 25), oranzova = podprumer (autor ACPL > 40)

### Dva typy proher

**Typ 1 — "Better player won" (4/6 her):**
k9a1IXvp, LpJ8wgDG, wrYUwz6A, 4gOcfuaY
- Autor ACPL: 19.5–43.4 (v prumeru ~30)
- Opponent ACPL: 16.1–50.4 (v prumeru ~36)
- 0–2 blunderu autora, 0 blunderu opponentu
- Jedna chyba autora stala — ply 23, ply 37, ply 59
- **Autor neprohral proto, ze by hral katastrofalne. Prohral proto, ze opponent hral "dost dobre na to, aby pockal na autorovu jedinou chybu."**

**Typ 2 — "Self-destruction" (2/6 her):**
tDcFRclj, 8jqLVD9c
- Autor ACPL: 45.2–48.6
- Opponent ACPL: 34.8–37.1
- Konkretni takticka chyba (ply 19 Bd6 v QGD) nebo akumulace nepresnosti (11 I v 50 tazich v Trompowskem)
- **Autor si prohral sam — opponent jen neudelal chybu, aby ho zachranil.**

---

## [IM] Proc opponent v n2 neblundruje?

### Data: blunder rate napric grupami

| Skupina | Blunders/game | Vztah |
|---------|--------------|-------|
| Autor v wins (n=27) | 0.39 | baseline |
| Autor v losses (n=6) | 0.33 | stejny jako baseline |
| Opponent v n1 (n=27, losses) | **0.70** | 1.8× vice nez autor |
| Opponent v n2 (n=6, wins) | **0.00** | **0×** |

### Inferencni model

Opponenti v n2 (18.2% poolu) jsou **odhad ~1800-1900 Lichess**. Na teto urovni:
- Blunder rate klesa pod 0.5/game
- Hraci nevyhravaji diky "trapum" ale diky **konzistenci**
- Jejich systemove chyby (patterns O, J, B) stale existuji, ale jsou **mene fatalni** — nedelaji je v kriticich momentech

**Porovnej:**
- n1 opponent (ACPL 57.0) → blundruje kazdou 1.4 hru → autor tresta
- n2 opponent (ACPL 29.4) → neblundruje vubec → autor nema "free win"
- Autor (ACPL 32.5) → blundruje kazdou 2.6 hru → n2 opponent nepotrebuje, autor si obcas "pomuze sam"

---

## [CM] Countermeasures — co delat pro zvyseni P vyhry

### CM1: Opravit konkretni openingove linie (nejvyssi P vyhry)

**Kriticke pozice:**

| Game | Linie | Chyba | Fix |
|------|-------|-------|-----|
| tDcFRclj ply 19 | QGD Semi-Tarrasch | Bd6 (459cp) | Misto 19.Bd6? hrat 19.Ne5 nebo 19.Rad1. Bd6 blokuje dame diagonalu a vystavuje strelce. |
| LpJ8wgDG ply 23 | Semi-Slav Normal (cerna) | Bd2 (173cp) | Misto 23.Bd2? Zkontrolovat 23...Rfd8 nebo 23...a5. Bd2 je pasivni — opponent ziskal initiative. |
| 4gOcfuaY ply 37 | Caro-Kann Advance (bila) | Nd4 (164cp) | Misto 37.Nd4? Zkusit 37.Rc1 nebo 37.Kf1. Nd4 vytvari slabinu na c3. |

**Doporuceni:** Analyzovat techto 5 pozic s engine na depth 22-24. Zapsat do osobni opening book (cena: 15 minut).

### CM2: Rizeni inaccuracy v dlouhych hrach (stredni P vyhry)

V losses ma autor 5.67 I/game, v wins 3.64 I/game (o 56% vice). Prvni 3-4 nepresnosti jsou "free" — nerozhoduji hru. Dale:
- 5.-7. nepresnost: vytvari pozicni tlak
- 8.+ nepresnost: rozhoduje hru

**Mechanismus:** Autor nehraje v losses hur. Jeho ACPL je 35.5 (porad dobre proti opponentovi 35.8). Problem je, ze **kumulace malych nepresnosti v dlouhe hre vytvari rozhodujici momentum pro opponent.**

**Akce:**
1. Po tahu 25 pridelit +10s na kazdy dalsi tah (casovka na koncentraci)
2. Kazdych 5 tahu si polozi otazku: "Je nejaka ma figura spatne postavena?" (capture avoidance)
3. V komplexnich pozicich (2+ variant v kalkulaci) vzdy zkontrolovat "nejjednodussi" odpoved soupere
4. Studovat 3-5 prikladu "positional squeeze defense" od Caruany nebo Kramnika

### CM3: Resit color asymmetry (stredni P vyhry)

| Barva | Win rate | Losses/games |
|-------|----------|-------------|
| Bila | **75%** (15W/5L) | 5/6 vsech proher |
| Cerna | **92%** (12W/1L) | 1/6 proher |

5/6 proher je jako bila. To muze byt:
(a) Nahoda (p=~0.1, Fishers exact test na N=33 by byl borderline)
(b) Repertoarovy problem — autor ma slabsí bilou opening book
(c) Stylovy problem — autor preferuje counterplay z cernych pozic

**Akce:**
- Zkontrolovat: je autoruv white win rate 75% signifikantne nizsi nez 50% baseline? ANO
- Porovnat white ACPL vs black ACPL v coachingu (Pattern G = 92% confidence — color asymmetry je real)
- **Pokud bilá ACPL je vyrazne horsi nez cerna:** upravit bilou opening book na vice aggressive (e4 misto d4, nebo vice konkretni varianty)

### CM4: Pozicni tlak, ne takticke pasti (stredni P vyhry)

**n2 opponent nema blunder.** Takticke pasti (bait traps) funguji na n1, kde opponent blundruje v kazde 1.4 hre. Proti n2:

- **Nedelat "bait traps," ktere oslabuji vlastni pozici** — opponent je nevidi, nebo vidi a ignoruje
- Misto toho: **vytvaret pozicni tlak v plochych pozicich.** Proc? Protoze opponent ma pattern O (stagnacni panika) ve 44% her.
  - Pokud opponent panikari v ploche pozici, autor musi byt ten, kdo **zklidni hru a pocka**
  - Nezahlcovat variantami — hrat principialni tahy, cekat na opponentovu chybu
- **5-second rule pred kazdym capturem:** Proti n2 je capture greed mensi problem (4-5%, stejne jako autor), ale porad existuje. Kontrola "A CO ON?" pred captures.

### CM5: Endgame preparedness (nizka P vyhry, vysoka hodnota)

2/6 proher se rozhodly v endgame (ply 59, ply 87). Objektivne:
- k9a1IXvp: opponent mel ACPL 16.1 v endgame — proste lepsi
- 8jqLVD9c: autor mel 11 inaccuracy v dlouhe 50-tahove hre

**Akce:**
- Specificky: prostudovat pozici po 50 tazich v Trompowskem (8jqLVD9c). Byla to prohra na "slow positional squeeze" nebo konkretni technical error?
- Obecne: pridat 5 endgame study session (rooke+pesec, dama+pesec, strelec rozdilne barvy)
- **Nejvetsi prinos:** studovat technical conversion v +0.5 az +1.5 pozicich

### CM6: Accept the 20% ceiling (mentální nastaveni)

Nektere prohry (wrYUwz6A: autor ACPL 19.5 — nejlepsi hra session, porad prohra) jsou proste proto, ze opponent byl silnejsi.

- wrYUwz6A: autor hral ACPL 19.5 s 0 blundery — to je 1900+ level. Opponent hral ACPL 32.4 s 0 blundery — to je ~1800 level. Autor hral lepe, ale opponent "vydrzel"
- **Lesson:** Nekdy 1 chyba v dlouhe hre rozhodne. Autor musi:
  1. Snizit tu 1 chybu na 0 (ale to je extremne tezke)
  2. Nebo vytvorit vice prílezitosti, kde opponent udela chybu prvni

---

## [IM] Shrnuti: Prototyp silneho opponentu (n2) a protiakce

### Profil n2 opponent

```
Elo:    ~1800-1900 Lichess (odhad)
ACPL:   35.8 (pri vyhre nad autorem)
Blunder rate: 0.00 (v techto hrach)
Silna stranka: konzistence, nechybuje fatalne
Slaba stranka: stagnacni panika (O ~44%), impulse check block (J ~16%)
Proti autorovi: vyhrava "cirkave" — ne dominanci, ale vydrzi dele
```

### Protiakce — prioritizovano

| # | Akce | Odhad P zvyseni | Casova narocnost |
|---|------|----------------|-----------------|
| 1 | Opravit 5 konkretnich opening pozic (QGD ply 19, Semi-Slav ply 23, Caro-Kann ply 37) | +8-12% | 15 min |
| 2 | Po 25. tahu +10s checking rule (redukce inaccuracy driftu) | +5-8% | 0 min (zvyk) |
| 3 | Color asymmetry — analyzovat proc 5/6 proher jako bila | +3-5% | 10 min |
| 4 | Zmenit strategii: misto bait traps → positional grind + cekani na O pattern | +3-5% | mindset |
| 5 | Studovat technical conversion (rook+pawn, opposite bishops) | +2-3% | 20 min/session |
| 6 | Accept 20% ceiling — nekazit si hlavu prohrami kde autor hral 19.5 ACPL | — | mental |

### Celkovy potencial

Z 18.2% win rate opponentu (6/33) na ~10-12% (3-4/33) — tedy **zvyseni author win rate z 81.8% na ~88-90%** proti anonymnimu poolu ~1600-1900 Lichess.

Realne: autor uz ted porazi 80% poolu. Proti top 20% je treba:
- Fixnout 2-3 konkretni chyby v openingu (cena 15 minut)
- Pridat 1 endurance mechanismus (cena: zvyk)
- Mentalne akceptovat, ze nekdy je opponent proste lepsi

**To je vse. Neni treba prekopavat cely sachovy repertoire — staci 5 konkretnich oprav a 1 novy zvyk.**

---

*Data: Stockfish BMI2 dev-20260609 depth 12, 33 anonymnich her, dual-perspektivni analyza. Patterny: 8 detekovanych (O 44%, J 16%, Q2 14%, C 11%, B 8%, Q 8%, P 4%, Q1 2%). Finalni N=2 generalizace.*
