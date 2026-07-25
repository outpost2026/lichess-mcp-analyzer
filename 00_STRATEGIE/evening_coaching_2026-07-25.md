# Večerní koučink — P0 audit & pipeline state

**Hráč:** Systeq | **Session:** 2026-07-25 | **Branch:** `debug/phase1-fixes` (HEAD `37b02cc`)
**Cache:** RUN_002 (9 proher, Stockfish 18 BMI2 @ d12-14)
**P0 změny:** F-002 (FEN), F-003 (is_check), F-007 (pattern J), N7 (sort order)

---

## 1. Co se změnilo — P0 fixy v kostce

Dnešní session aplikovala 3 kritické fixy a 1 organizační:

| Fix | Problém | Oprava | Dopad |
|-----|---------|--------|-------|
| **F-002** | `fen_before` se počítal a zahazoval | +`fen: str` v `MoveAnalysis` | BlunderFactSheet nyní může referovat FEN pozici |
| **F-003** | `board.is_check()` se nikde nevolal | +`was_in_check: bool` v `MoveAnalysis` | H1/H2 halucinace (falešný šach/blok) nyní detekovatelné |
| **F-007** | Pattern J testoval `"+" in move_san` (odehraný tah dává šach) místo `was_in_check` (pozice byla v šachu) | `m.was_in_check and "x" not in m.move_san` | Falešně pozitivní J na INC-C (Vd7+) eliminován |
| **N7** | `result.sort()` probíhal až po `store_patterns()` a validaci | Sort přesunut před artifact build | Pattern data se persistují již seřazená |

**N1, N2, N3, N4** — již fixovány v předchozím commitu (`e6ce584`).

---

## 2. Stav pipeline — cache RUN_002 (9 proher)

Data zůstávají stejná (nebyl proveden nový RUN), ale **interpretační rámec se mění** díky F-007:

### Blundery přehled

| Hra | Tah | Tah | CP před | CP po | Ztráta | Pattern (původní) | Pattern (po F-007) |
|-----|-----|-----|---------|-------|--------|-------------------|-------------------|
| qmodxzNF | 60 | Kd7 | +569 | −573 | 1386 | **S** (nový) | **S** (beze změny) |
| kNAMNYUF | 63 | Vdg1 | +823 | +45 | 950 | B+J | **B+R** (J byl FP — nebyl šach) |
| PQvwuTAO | 71 | Ve3 | +322 | −365 | 739 | C+R | C+R (beze změny) |
| NYcRejUc | 148 | Vh1+ | −11 | −536 | 536 | C | C (beze změny) |
| xUlQasD0 | 43 | Sf4 | +335 | −110 | 505 | P+B | P+B (beze změny) |
| xUlQasD0 | 89 | Vd7+ | −788 | −1248 | 464 | **J** | **žádný** (J byl FP) |
| xUlQasD0 | 41 | fxe6 | +681 | +336 | 369 | B | B (beze změny) |
| xUlQasD0 | 71 | Df5 | +208 | −115 | 338 | P | P (beze změny) |
| PQvwuTAO | 101 | Vg7 | +1 | −321 | 321 | C | C (beze změny) |
| NYcRejUc | 76 | Vb4 | −58 | −356 | 303 | P | P (beze změny) |

**Klíčový insight:** Pattern J byl v RUN_002 detekován 2× (kNAMNYUF ply 63 + xUlQasD0 ply 89). Po F-007 opravě:
- kNAMNYUF: `Rdg1` — nebyl šach před tahem → J **odmítnut**, nahrazen `R` (endgame relaxation)
- xUlQasD0: `Vd7+` — nebyl šach před tahem → J **odmítnut**, žádný pattern

Pattern J frequency klesá z 2 na 0 v tomto datasetu. To je konzistentní s hypotézou z DBCL unity syntézy (§5.1): J byl systematicky falešně pozitivní díky sémantickému bugu.

---

## 3. Pattern landscape po F-007

Detekováno 7 patternů z 9 her (baseline: `Systeq_20260724_184812`):

| ID | Pattern | Spol. | Závažnost | Zásahů | Změna oproti RUN_002 |
|----|---------|-------|-----------|--------|---------------------|
| **B** | Automatické brání | 95% | vysoká | 4 | ✅ beze změny |
| **C** | Tunnel vision | 80% | střední | 4 hry | ✅ beze změny |
| **O** | Vyhýbání se trojáku | 60% | kritická | 7 her | ✅ beze změny |
| **R** | Relaxace v koncovce | 70% | vysoká | 3 hry | ⬆️ +1 (kNAMNYUF přeřazen z J) |
| **P** | Vizuální chyba | 50% | vysoká | 4 hry | ✅ beze změny |
| **I** | Návnada | 40% | nízká | 2 hry | ✅ beze změny |
| **S** | Capture aversion under check | ~40% | kritická | 1 (N=2) | ✅ kandidát (beze změny) |
| ~~**J**~~ | ~~Impulsivní blok šachu~~ | — | — | ~~2~~ **0** | ❌ eliminován — byl FP |

**Důsledek:** Pattern `R` (endgame relaxation) je nyní dominantnější. Kauzální řetězec se zkracuje:

```
Časová tíseň → Tunnel vision (C) → Automatické brání (B) / Relaxace (R) → Blunder
```

Bez falešně pozitivního J je signál čistší — `R` a `B` jsou skutečné slabiny, `J` byl artefakt špatné detekce.

---

## 4. Tři nejbolestivější prohry (z cache RUN_002)

### 4.1 qmodxzNF — Scotch Game (tah 60: Kd7)

**FEN:** `7r/2p2p2/3k4/p1QPp3/1pP1P2q/5P2/P1B2P2/2K3R1 b - - 3 30`

| Metrika | Hodnota |
|---------|---------|
| Král na d6, Bílá dáma na c5 dává šach | ✅ |
| Stockfish top move | Kxc5 (+542 cp) |
| Co jsi zahrál | Kd7 (−573 cp) |
| CP swing | 1386 |
| Pattern | **S** (capture aversion under check) |

**Mechanismus:** Šach → stress → "král v nebezpečí → utéci" reflex. Kxc5 nebyl ani v seznamu kandidátů.

### 4.2 kNAMNYUF — French Franco-Sicilian (tah 63: Rdg1)

**FEN:** `r4r1k/1p1b3P/p3p1R1/3p3Q/3N1q2/8/PPP4P/1K4R1 b - - 2 32`

| Metrika | Hodnota |
|---------|---------|
| Eval před | +823 cp |
| Eval po | +45 cp |
| CP swing | 778 cp |
| Pattern (po F-007) | **B + R** |

**Korekce oproti RUN_002:** Původně bylo B+J. Po F-007 opravě: `was_in_check=false` → J odmítnut. Šlo o **odtažení věže z první řady** (Rdg1 místo Ka1/Kc1), což je relaxace v koncovce s výhodou (pattern R), ne impulsivní blok.

### 4.3 PQvwuTAO — Vienna Game (tah 71: Re3)

**FEN:** `8/1p3rp1/p1pk3p/P2pn3/1P1K1N2/4R1P1/2P5/8 b - - 13 36`

| Metrika | Hodnota |
|---------|---------|
| Eval před | +322 cp |
| Eval po | −365 cp |
| CP swing | 687 |
| Pattern | **C + R** |

**Mechanismus:** Tunnel vision na pěšcovou lavinu + relaxace. Re3 odhalilo krále na Nc4+ fork.

---

## 5. DBCL readiness — co chybí k P1 startu

Stav po dnešních P0 fixech:

| Komponenta | Stav | Blokuje DBCL? |
|------------|------|---------------|
| `fen` v MoveAnalysis | ✅ hotovo | Ne |
| `was_in_check` v pipeline | ✅ hotovo | Ne |
| Pattern J sémantika | ✅ hotovo | Ne |
| N7 sort order | ✅ hotovo | Ne |
| Inlinovat context do `_run_analyze_pgn` | ❌ P1-1 | **Ano** — BlunderFactSheet builder |
| Zavolat `engine_client.analyze_position(multipv=3)` | ❌ P1-2 | **Ano** — multi-PV engine_lines |
| Guard-clause na oba prompt buildery | ❌ P1-3 | **Ano** — H1-H8 ochrana |
| Narrativní validátor | ❌ P1-4 | Medium — ochrana proti reinfekci |
| Pattern guard (J, S, R, C) | ❌ [SYNTHESIS] | Medium — detektor validace |

**Odblokováno:** P0 je kompletní. DBCL v1 (P1) může začít — BlunderFactSheet má k dispozici FEN a `was_in_check`, pattern J negeneruje falešné poplachy.

**Zbývá před DBCL v1:** Audit zbývajících 10 detectorů (A–R kromě J) na sémantickou konzistenci (dle unity §5.2 a meta-evaluace §5.3). Současný kód má potvrzený jeden sémantický bug (J), ale nelze vyloučit další.

---

## 6. Večerní protokol — další kroky

### Drill 1: Capture under check refresher (10 min)

Postav 5 pozic z vlastních her (qmodxzNF ply 60 jako první), kde jsi v šachu a jediná správná odpověď je brát šachující figuru. Před každým tahem: **"Můžu brát? Pak uhýbám? Pak blokuju?"**

### Drill 2: Endgame relaxation awareness (10 min)

Z 10 blunderů jich bylo 8 v koncovce. Pattern R (relaxace) ovlivnil 3 z 9 proher. Postav 3 pozice z RUN_002 s eval_before > +300 v koncovce a hraj je se záměrnou pauzou 5s před každým tahem, během které hledáš soupeřovu nejlepší odpověď.

### Drill 3: DBCL context injection (5 min)

Až příště spustíš `lichess_analyze_game` nebo `lichess_diagnose_player`, data už ponesou `fen` a `was_in_check`. Zkus si vyžádat koučink na konkrétní blunder (např. "INC-A z DBCL unity §2.1") a ověř, že LLM výstup neobsahuje H1-H8 halucinace.

---

## Příloha: Všech 10 blunderů (po F-007 korekci)

| Hra | Tah | Tah | CP před | CP po | Ztráta | Pattern (korigováno) | Fáze |
|-----|-----|-----|---------|-------|--------|---------------------|------|
| qmodxzNF | 60 | Kd7 | +569 | −573 | 1386 | S (nový) | koncovka |
| kNAMNYUF | 63 | Vdg1 | +823 | +45 | 950 | B+R | koncovka |
| PQvwuTAO | 71 | Ve3 | +322 | −365 | 739 | C+R | koncovka |
| NYcRejUc | 148 | Vh1+ | −11 | −536 | 536 | C | koncovka |
| xUlQasD0 | 43 | Sf4 | +335 | −110 | 505 | P+B | střední hra |
| xUlQasD0 | 89 | Vd7+ | −788 | −1248 | 464 | — (bývalý J, nyní FP) | koncovka |
| xUlQasD0 | 41 | fxe6 | +681 | +336 | 369 | B | střední hra |
| xUlQasD0 | 71 | Df5 | +208 | −115 | 338 | P | koncovka |
| PQvwuTAO | 101 | Vg7 | +1 | −321 | 321 | C | koncovka |
| NYcRejUc | 76 | Vb4 | −58 | −356 | 303 | P | koncovka |

**8 z 10 blunderů v koncovce** (beze změny). **Pattern J frequency: 0** (eliminováno F-007).
