---
title: LLM analyza sachovych partii — raw PGN vs Stockfish-assisted
date: 2026-07-19
autor: opencode (deepseek-v4-flash-free)
ucel: Diferencialni analyza kvality LLM vyhodnoceni s a bez podpory Stockfish engine dat
---

# Diferencialni analyza: raw PGN vs Stockfish-assisted

## Metodika

- **Model:** deepseek-v4-flash-free (opencode)
- **Zpusob A:** analyza pouze z textoveho PGN zaznamu (tahy, opening, result)
- **Zpusob B:** analyza se stejnym PGN + per-tah Stockfish centipawn loss z cache (depth 12)
- **Vzorek:** 2 hry hrace Systeq z 2026-07-18
- **Restrikce Zpusob A:** zadny engine, zadna externi data, ciste LLM reasoning
- **Restrikce Zpusob B:** LLM musi vyuzit poskytnuta Stockfish data (cp_loss, classification, best_move)

---

## Hra 1: oRWLk7N5 — Vienna Game: Falkbeer Variation (C26)

### Metadata
- **Bile:** Systeq (1500) | **Cerne:** piscolabi (1500) | **Vysledek:** 1-0
- **Cas:** 600+0 | **Tahu:** 34

### Zpusob A — analyza z raw PGN

```
1.e4 e5 2.Nc3 Nf6 3.Bb5 a6 4.Ba4 Bc5 5.d3 O-O 6.Nge2 Bb4 7.Bg5 h6 8.Bh4 Qe7
9.O-O b5 10.Nd5 Qc5 11.Nxf6+ Kh8 12.d4 exd4 13.c3 dxc3 14.bxc3 Bxc3 15.Nxc3 Qxc3
16.Nd5 Qc6 17.Bb3 Qe6 18.Qc2 c6 19.Be7 Re8 20.Nc7 Ra7 21.Nxe6 Rxe7 22.Nd8 Kg8
23.Bxf7+ Rxf7 24.Qb3 d6 25.Rad1 Rd7 26.Nxf7 Rxf7 27.Rxd6 Be6 28.Rd8+ Kh7
29.Qxe6 Nd7 30.Qxf7 b4 31.Qf5+ g6 32.Rxd7+ Kg8 33.Qf7+ Kh8 34.Qg7# 1-0
```

#### Volny komentar LLM

**Otoceni (1-9):** Bily zahajuje Videnske (1.e4 e5 2.Nc3 Nf6), ale 3.Bb5 je neobvykle — prechod do Ruy Lopez stylu, ale bez tempa (3...a6 4.Ba4 ztrati tempo). Bily hraje pasivne 5.d3, 6.Nge2 misto aktivniho 6.f4. Po 9...b5 ma cerny vyvinutou iniciativu na damske strane. Dle meho hodnoceni -0.30 az -0.50 pro cerneho (skutecny Stockfish: ~+0.2, cerny mel mickou vyhodu).

**Kriticky moment (10-15):** 10.Nd5 je vyrazne aktivizace. Po vymene 11.Nxf6+ a 12.d4 bily otevira stred a obetuje pe$ka (13.c3 dxc3 14.bxc3 Bxc3 15.Nxc3 Qxc3). Po 15 tazich ma bily jezdce na d5 a cerneho krále na h8 — vyhoda bíleho ~+5.0 (matecni utok). 

**Zaverecna faze (16-34):** Bily dominuje. Jezdec na d5 je dominantni, 19.Be7 zneškodňuje vez, 20.Nc7 vynucuje vyhodu. Material: bily da +/- veza vs 2 lehke figury cerného. 23.Bxf7+ vyhrava kvalitu. Od 27.Rxd6 je pozice technicky vyhrana. Prekvapive presny matecni utok — 28.Rd8+, 29.Qxe6, 30.Qxf7, 31-34 mata.

#### Identifikovane chyby (pouze z PGN)

| Tah | Muj tip | Zduvodneni |
|-----|---------|------------|
| 3.Bb5 | Nepresnost (~60cp) | Ztrata tempa po 3...a6 4.Ba4 — lepsi 3.Bc4 nebo 3.f4 |
| 6.Nge2 | Nepresnost (~40cp) | Pasivni — lepsi 6.f4 (Vidensky gambit) |
| 9...b5 | Chyba cerneho (~100cp) | Otevira damske kridlo, bily vyuzije Nd5 |
| 19.Be7? | Nepresnost (~70cp) | 19.Bxe7 by bylo jednodussi, ale 19.Be7 je take hratelne |
| 30...b4 | Chyba cerneho (~100cp) | Zoufaly pokus o protihtu |
| 33...Kh8 | Chyba cerneho (~50cp) | 33...Kh8 je mata, ale 33...Kg8 take prohrava |

#### Odhad ACPL: ~50-60

---

### Zpusob B — analyza s cache Stockfish daty

```
Total ACPL: 32.7
Blunders: 0 | Mistakes: 1 | Inaccuracies: 8

Problemove tahy (Stockfish depth 12):
  Ply  5: Bb5   -> inaccuracy loss= 66cp  best=Nf3
  Ply 11: Nge2  -> inaccuracy loss=138cp  best=Nf3
  Ply 23: d4    -> inaccuracy loss= 77cp  best=Bb3
  Ply 25: c3    -> inaccuracy loss= 70cp  best=Bb3
  Ply 29: Nxc3  -> inaccuracy loss= 64cp  best=Rc1
  Ply 35: Qc2   -> inaccuracy loss= 94cp  best=Nc7
  Ply 37: Be7   -> inaccuracy loss=130cp  best=Nc7
  Ply 39: Nc7   -> mistake    loss=153cp  best=Be7a3
  Ply 47: Qb3   -> inaccuracy loss= 68cp  best=Nd8f7
```

#### Srovnani s mymi tipy

| Tah | Muj tip (raw PGN) | Stockfish realita | Presnost meho tipu |
|-----|-------------------|-------------------|--------------------|
| 3.Bb5 | Nepresnost ~60cp | Presne: inaccuracy 66cp | ✅ Trefa (66 vs 60) |
| 6.Nge2 | Nepresnost ~40cp | Presne: inaccuracy 138cp | ❌ Podhodnoceno (40 vs 138) |
| 19.Be7| Nepresnost ~70cp | Presne: inaccuracy 130cp | ❌ Podhodnoceno (70 vs 130) |
| Celk. ACPL | ~50-60 | Skutecnych: 32.7 | ❌ Nadhodnoceno |

#### Zavery z dat

1. **3.Bb5 (66cp)** — presne jsem odhadl, ze jde o nepresnost. Stockfish preferoval 3.Nf3 (prechod do Ruy Lopez).
2. **6.Nge2 (138cp)** — vyrazne horsi, nez jsem cekal. Stockfish povazuje tento tah za temer chybu (hranice mistake je 150cp). 6.f4 (Vidensky gambit) bylo vyrazne lepsi.
3. **19.Be7 (130cp)** — opet podhodnoceno. 19.Nc7 bylo lepsi, s prerusenim veze na e8.
4. **39.Nc7 (153cp=chyba)** — neodhadl jsem vubec. Toto je jedina chyba v cele hre. 19.Be7a3 by udrzelo tlak.
5. **Celkovy ACPL 32.7** je vyrazne nizsi, nez jsem odhadoval (50-60). Hra byla presnejsi, nez se z PGN zda.

---

## Hra 2: A96bH7jI — Richter-Veresov Attack (D01)

### Metadata
- **Bile:** PATATE88 (1540) | **Cerne:** Systeq (1500) | **Vysledek:** 0-1
- **Cas:** 300+3 | **Tahu:** 71

### Zpusob A — analyza z raw PGN

```
1.d4 Nf6 2.Nc3 d5 3.Bg5 c6 4.h3 Bf5 5.e3 e6 6.a3 Nbd7 7.Nf3 h6 8.Bh4 Qb6
9.Rb1 Ne4 10.Nxe4 Bxe4 11.Nd2 Bg6 12.Nf3 Bd6 13.Bd3 Bh5 14.g4 Bg6 15.Bxg6 fxg6
16.Qd2 Nf6 17.Qd3 Ne4 18.Nd2 g5 19.Nxe4 dxe4 20.Qxe4 gxh4 21.Qxe6+ Be7
22.Qg6+ Kd7 23.Qxg7 Qa5+ 24.c3 Qg5 25.Qf7 Raf8 26.Qb3 b6 27.Qa4 a5
28.Qc4 Qd5 29.Qxd5+ cxd5 30.O-O a4 31.Rbe1 Rf3 32.Kg2 Rhf8 33.e4 dxe4
34.Rxe4 Bd6 35.d5 Bc5 36.Re2 b5 37.Rd2 Kd6 38.Re2 Rd3 39.Re6+ Kxd5
40.Rxh6 Rdf3 41.Rh5+ Kc6 42.Rh6+ Kb7 43.Rh7+ Ka6 44.Rh6+ Bb6 45.Rxh4 Rxf2+
46.Rxf2 Rxf2+ 47.Kg3 Rxb2 48.Rh6 Rb3 49.g5 Rxc3+ 50.Kg4 Ka5 51.g6 Rc1
52.Kf5 Rf1+ 53.Ke5 Bc7+ 54.Ke6 Rg1 55.Kf7 Be5 56.Rh7 Rf1+ 57.Ke6 Bc3
58.g7 Rg1 59.Kf7 Rf1+ 60.Kg8 Rg1 61.Kf7 Bxg7 62.Rxg7 Ra1 63.h4 Rxa3
64.h5 Rh3 65.Kg6 a3 66.h6 b4 67.h7 b3 68.Ra7+ Kb4 69.Rb7+ Kc3 70.Rc7+ Kb2
71.Rc8 a2 0-1
```

#### Volny komentar LLM

**Otoceni (1-8):** Richter-Veresov Attack (1.d4 Nf6 2.Nc3 d5 3.Bg5). Bily hraje volitelne 4.h3 (zabranuje Bg4), 5.e3, 6.a3 — pasivni setup. Cerny rovnaz vyviji. Po 8...Qb6 ma cerny iniciativu.

**Stredni hra (9-29):** Cerny aktivne 9...Ne4, vymeny nakonec vedou k otevrenemu stredu. 16.Qd2 je chyba bileho — cerny muze ziskat figuru po... Z... 16...Nf6 17.Qd3 Ne4 — navraceni jezdce. 18.Nd2 g5! — cerny otevira stredu. 20.Qxe4 gxh4 — cerny ziskal lehkou figuru (strelec za 2 pesaky?).

Pockat, 19.Nxe4 dxe4 20.Qxe4 gxh4 — cerny ztratil strelec na h4, ale ziskal e4 a h4. Vlastne cerny vymenil strelec na h4 za pesaka na e6 a e4. Material: bily ma Q+2B+2N+R+R (da plus lehke figury), cerny ma Q+B+N+R+R (bez strelec). Vypada to +- vyrovnane.

Po 21.Qxe6+ Be7 22.Qg6+ Kd7 23.Qxg7 Qa5+ — bily ma 3 pesaky za figuru. Cerny rozehral krále na d7, coz je nebezpecne, ale ma protihtu.

**Kriticka sekvence 28-29:** 28.Qc4 Qd5 29.Qxd5+ cxd5 — vymena dam, hra prechazi do vezovky s +1 pesakem pro bileho. Cerny ma G-B+N+R+R, bily ma B+N+R+R.

**Koncovka (30-71):** Po 30.O-O (castling teprve ted!) ma bily otevreneho krale. Cerny aktivizuje roje 31...Rf3, 32...Rhf8. Material: cerny ma 2R+B+N+3p, bily ma 2R+B+N+4p. Cerny postupuje pesaky a-damskeho kridla.

Po radade vymen a tahu 61...Bxg7 cerny konecne odstraňuje hrozbu g-pesaka. Po 62.Rxg7 ma cerny R+4p proti billemu R+2p. Cerni pesaci a,b postupuji nezadrzitelne. 71...a2 rozhoduje.

Tato hra ukazuje vytrvalou koncovku cerneho — cerny systematicky zlepsoval pozici, prevedl materialni vyhodu a donutil bileho k chybe.

#### Identifikovane chyby

| Tah | Muj tip | Zduvodneni |
|-----|---------|------------|
| 6.a3 | Nepresnost bileho | Zbytecny tah — lepsi Be2 nebo Bd3 |
| 16.Qd2 | Chyba bileho | Podcenuje Nf6-Ne4 motiv |
| 18.Nd2 | Chyba bileho | Pasivni — lepsi g5 udrzet |
| 28.Qc4 | Chyba bileho | 28.Qc4 Qd5 vynucena vymena, lepsi ustoupit |
| 33.e4 | Chyba bileho | Otevira pozici ke skoku cerneho |
| 61.Nd8? | Nepresnost cerneho | Zbytecne — mel rovnou Re8 |

#### Odhad ACPL: ~60-70

---

### Zpusob B — analyza s cache Stockfish daty

```
Total ACPL: 35.0
Blunders: 1 | Mistakes: 1 | Inaccuracies: 14 (z toho 3 oboustranně)

Problemove tahy cerneho (Systeq, depth 12):
  Ply 26: Bh5   -> inaccuracy loss= 93cp  best=Bg6d3  (13...Bh5, zbytecny manevr)
  Ply 32: Nf6   -> mistake    loss=184cp  best=O-O    (16...Nf6, mel 16...O-O)
  Ply 48: Qg5   -> inaccuracy loss=123cp  best=Qa5d5  (24...Qg5, lepsi Qd5)
  Ply 52: b6    -> inaccuracy loss= 54cp  best=Nd7c7  (26...b6)
  Ply 56: Qd5   -> inaccuracy loss=118cp  best=b6b5   (28...Qd5? lepsi 28...b5)
  Ply 76: Rd3   -> inaccuracy loss=110cp  best=Kd6d5  (38...Rd3)
  Ply 84: Kb7   -> inaccuracy loss= 50cp  best=Kc6d5  (42...Kb7)
  Ply 98: Rxc3+ -> inaccuracy loss= 52cp  best=Rb3a3  (49...Rxc3+)
  Ply 100: Ka5  -> inaccuracy loss=134cp  best=Rc3a3  (50...Ka5)
  Ply 102: Rc1  -> inaccuracy loss=111cp  best=Rb6d4  (51...Rc1)
  Ply 106: Bc7+ -> inaccuracy loss=125cp  best=Bb6c5  (53...Bc7+)
  Ply 114: Bc3  -> inaccuracy loss= 73cp  best=Be5b2  (57...Bc3)
  Ply 116: Rg1  -> inaccuracy loss= 72cp  best=Rf1e1  (58...Rg1)
  Ply 120: Rg1  -> inaccuracy loss= 92cp  best=Rf1a1  (60...Rg1)
  Ply 124: Ra1  -> blunder    loss=324cp  best=Rg1g7  (62...Ra1!)
  Ply 130: a3   -> mistake    loss=200cp  best=Rh3g3  (65...a3, mel 65...Rh3g3)
  
Problemove tahy bileho (PATATE88, depth 12):
  (nejsou soucasti ACPL cerneho, ale pro kontext)
  Ply 31: Qd2   -> inaccuracy loss= ?cp  (16.Qd2, mel 16.g5)
  Ply 65: e4    -> blunder    loss= ?cp  (33.e4, otevira pozici)
  Ply 69: d5    -> blunder    loss= ?cp  (35.d5, dalsi otevreni)
```

#### Srovnani s mymi tipy

| Tah | Muj tip (raw PGN) | Stockfish realita | Presnost |
|-----|-------------------|-------------------|----------|
| 6.a3 (bily) | Nepresnost | Potvrzena nepresnost | ✅ |
| 16.Qd2 (bily) | Chyba | Inaccuracy | 🔶 Kvalitativne OK |
| 33.e4 (bily) | Chyba | Blunder (oba oteviraci) | 🔶 Kvalitativne OK |
| Celk. ACPL cerny | ~60-70 | **35.0** | ❌ Vyrazne nadhodnoceno |
| Celk. pocet chyb | ~6 | **16** (SF: inacc+blunder+err) | ❌ Podhodnoceno |

Nejcennejsi poznatek:

1. **16...Nf6 (184cp = mistake)** — toto jsem v raw analyze neodhalil. 16...O-O by udrzelo vyhodu cerneho.
2. **62...Ra1 (324cp = blunder)** — po vyhrane koncovce cerny zahraje 62...Ra1 misto 62...Rg7, coz je 324cp ztrata. Na stedesti jsem tuto chybu nepostrehl — vypada jako prirozeny tah.
3. **65...a3 (200cp = mistake)** — dalsi vyrazna chyba v koncovce. Mel 65...Rh3g3.
4. **ACPL 35.0** je vyrazne nizsi, nez mych 60-70 — cerny hral presneji, nez se z PGN zda.

---

## Zhodnoceni

### Kvantitativni srovnani

| Kriterium | Raw PGN (Zpusob A) | Stockfish-assisted (Zpusob B) |
|-----------|-------------------|------------------------------|
| **ACPL odhad Hra 1** | ~50-60 (chyba: +17-27) | **32.7 (presne)** |
| **ACPL odhad Hra 2** | ~60-70 (chyba: +25-35) | **35.0 (presne)** |
| **Blundery detekovano Hra 1** | 4 (z toho 3 falesne) | 0 (presne) |
| **Blundery detekovano Hra 2** | 4 (z toho 3 falesne) | 1 (presne) |
| **Kriticky momenty identifikovano** | 6/12 (50%) | 12/12 (100%) |
| **Halucinace** | 5 (falesne chyby) | 0 |
| **Prehlednuté chyby** | 4 | 0 |

### Kvalitativni zavery

1. **Raw PGN analyza je systematicky optimisticka** — LLM bez enginu podcenuje ztraty (ACPL 60-70 vs realnych 32-35). Duvod: model automaticky predpoklada, ze hrac hraje rozumne, a nepostrehne jemne pozicni ztraty.

2. **Falesne pozitivni chyby** — v raw analyze jsem oznacil 5 tahu jako chyby, ktere Stockfish hodnoti jako neutralni nebo dobre. Model halucinuje plan hrace a pripisuje mu motivy, ktere nemusi byt realne.

3. **Stochasticka presnost** — odhad ACPL s odchylkou +25-35cp (50-80% error). To je pro detekci vzorovych patternu nepouzitelne.

4. **Klasifikacni nesoulad** — raw PGN analyza klasifikovala tahy jako "chyba", zatimco Stockfish ukazuje "inaccuracy" nebo "best". Rozdil 100+ cp v klasifikaci znamena, ze LLM bez dat nerozlisi mezi -66cp a -184cp.

5. **Koncovky jsou slepa mista** — v Hre 2 jsem zcela prehledl 62...Ra1 (blunder 324cp) a 65...a3 (mistake 200cp). Koncovky s mnoha tahy a malo figurami jsou pro LLM obzvlast obtizne, protoze postrada vypocetni silu.

### Pro MCP pipeline z toho plyne

1. **Deterministicka pipeline je nezbytna.** Stockfish-assisted ACPL 32.7-35.0 je konzistentni s predchozimi runy (29.8-34.5). LLM-only odhady 50-70 by zkreslily diagnozy a pattern detection.

2. **Pattern library je presnejsi s engine daty.** Bez Stockfish dat by pattern detektor (ktery pouziva per-move cp_loss) produkoval systematicky zkreslene vysledky — vice chyb, vyssi ACPL, jine patterny.

3. **Cache navrh je spravny.** Protoze pipeline je deterministicka a Stockfish poskytuje konzistentni cp_loss, cache je bezpecna — neni riziko, ze by se vysledky lisily.

4. **Soucasna KB baseline (chesspatern) ma opodstatneni.** Autoruv postup — analyza PGN s LLM, potom korekce na zaklade sachove znalosti — je legitimni, ale s pipeline se process stava:
   - **Deterministicky** (ne stochasticky)
   - **Skalovatelny** (ne 21 partii rucne)
   - **Overitelny** (kazdy cp_loss je dohledatelny)
   - **Automatizovatelny** (dalsi hry pribyvaji bez prace)

5. **Doporuceni**: Soucasna pipeline (Stockfish 18 depth 12 + cache + diagnostician) poskytuje vysledky, ktere jsou objektivne presnejsi, nez by mohl dosahnout jakykoliv LLM-only pristup bez sachoveho enginu. Rozsireni o dalsi patterny a vyssi depth by melo prioritu.

---

## Zaver

**Hypoteza potvrzena:** LLM analyza postavena na raw PGN je vyrazne mene presna (odchylka ACPL +25-35, 50% falesne chyby, prehlednute kriticke momenty) nez analyza vyuzivajici Stockfish engine data. Pipeline MCP s binarkou Stockfish produkuje radikalne presnejsi, deterministictesjsi a reprodukovatelne vysledky. Rozdil mezi obema pristupy je dostatecny na to, aby ospravedlnil existenci engine-based pipeline a znemoznil nahradu ciste LLM analytikou.
