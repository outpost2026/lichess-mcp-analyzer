---
title: Mikolovova komprese v pattern architektuře
date: 2026-07-19
ucel: Analyza Mikolovovy filozofie redukce entropie aplikovane na chess pattern artifact
verze: 1.0
navaznost: KALIBRACE_PLAN_2026-07-19.md → v2.2
status: IMPLEMENTOVANO v KALIBRACE_PLAN v2.2
---

## 1. Problemy soucasne baseliny

**Tvrzeni autora:** Soucasny chess pattern artifact (17 patternu A-Q1) vzniknul z N < 25 her, tedy:
- nema statistickou autoritu pro tvrzeni "pattern s high confidence"
- je prototypem — nema korektne identifikovat vetsinu patterns
- patterns s P > 0.5 mohou byt korigovany nebo rozsireny — oboje validni

**Toto je relevantni problem.** Standardni statisticky pristup by rekl: "s N=9 nelze nic tvrdit s confidence > 0.8". Ale Mikolovuv kompresni ramec nabizi alternativu.

---

## 2. Teze: Komprese jako alternativa ke statistice

**Klíčová otázka:** Je pattern validní, když se objeví v 9 hrách, ale vysvětluje pozorované chování lépe než surová data?

### 2.1 Standardní statistický přístup (SOUČASNÝ)

```
confidence = f(N_vzorku, konzistence)
Problem: pri N=9 je i konzistentni pattern "low confidence"
Ale: co kdyz pattern opravdu existuje, jen jsme ho jeste nemerili dost?
```

### 2.2 Kompresní přístup (Mikolov — NAVRHOVANÝ)

```
Pattern je validní, pokud:
  L(pattern + exceptions) < L(raw_data)
  kde L = delka popisu v bitech (MDL)

To znamena: pattern komprimuje data lepe nez surova data sama
```

**Klicovy posun:** 
- Statistika: "Jak je pravdepodobne, ze pattern je nahodny?" → vyzaduje N > 30
- Komprese: "Popisuje pattern data efektivneji nez bez nej?" → funguje i pri N = 1 (ale nizsi conf)

### 2.3 Prakticky priklad

Surova data (9 her, ~1000 tahu):
- Popis: 1000 tahu × 5 atributu = ~5000 tokenu

Pattern Q (aktivni obrana, 4 vyskpty):
- Popis patternu: "Pattern Q: v obranne pozici voli utocny tah" = ~10 tokenu
- Vyjimky: "tah 26.Bh5, tah 48.Qg5, tah 37.Re3, tah 62.c3" = ~12 tokenu  
- Uspora: 5000 - 22 = 4978 tokenu usporenych
- Kompresni pomer: 5000/22 = 227:1

**Zaver:** Pattern Q je EXTREMNE KOMPRIMUJICI (pomer 227:1), i kdyz N = 9.

---

## 3. Mikolovova filozofie v kontextu chess pattern

### 3.1 Redukce entropie

> "Transformace dat do reprezentace s nižší informační náročností."

Pattern artifact transformuje ~5000 tokenu surovych dat na ~50 tokenu strukturovaneho profilu. To je **99% komprese**. Kazdy pattern, ktery se udrzi v teto kompresi, je entropicky relevantni.

**Implementace:** Kazdy pattern v artifactu nese implicitni kompresni pomer. Pattern s pomerem < 2:1 je podezrely (hluk). Pattern s pomerem > 10:1 je silny signal.

### 3.2 Kompresni model reality

> "Reprezentace reality minimalizujici komplexitu, predikcni chybu a vypocetni naklady."

Chess pattern artifact je **kompresni model hrace**: minimalizuje komplexitu (17 patternu namisto 1000 tahu), predikcni chybu (Stochastic cp_loss jako ground truth) a vypocetni naklady (2s cached runtime).

**Jak overit:**
- MSE zprava: Predikce tahu na zaklade patternu vs realita
- Pokud MSE(pattern) < MSE(prumer), model je validni
- Pokud MSE(pattern) ≈ MSE(prumer), pattern je noise

### 3.3 Ztratova komprese

> "Odstraneni informace s nizkou prediktivni hodnotou."

To je presne to, co pattern library dela: ignoruje jednotlive tahy (sum) a extrahuje behavioralni vzory (signal). Ztratova komprese v chess kontextu = minut detaily (presna hodnota cp_loss) chytit vzor (hra preferuje X).

**Pravidlo:** Pattern je dobry, pokud:
- zachycuje chovani (signal)
- odstranuje jednotlive chyby (sum)
- neodstranuje strukturu (trendy, fazove slabiny)

### 3.4 Occamova britva

> "Preferovani nejjednodussiho dostatecne presneho modelu."

Kompresni pomer = meritko Occamovy britvy. Ze dvou patternu, ktere stejne dobre vysvetluji data, je ten s vyssim kompresnim pomerem spravnejsi.

**Prakticky problem:** Pattern H (Matematicka neznalost) a Pattern I (Material before initiative) se mohou prekryvat. Occam pres kompresi rekne:
- Ktery ma vyssi kompresni pomer?
- Ktery vyzaduje mene vyjimek pro stejne vysvetleni?

---

## 4. VERDIKT: PASS

**Kompresni filozofie Tomase Mikolova je plne kompatibilni s existujici architekturou a resi jeji klicovy problem (small-N authority).**

### Zdovodneni:

| Aspekt | Bez komprese | S kompresi | Zlepseni |
|--------|-------------|------------|----------|
| Validace patternu pri N<25 | Neni mozna (low conf) | Mozna pri compression_ratio > 2:1 | **Prulomove** |
| Confidence metrika | Pouze sample size + consistency | compression_ratio × entropy_reduction | **Presnejsi** |
| Occamova britva | Implicitni | Explicitni (meritelna) | **Overitelna** |
| Ztratova komprese | Neuvedomena | Formalizovana | **Riditelná** |

### Dusledky:
1. Soucasny pattern artifact NENI nevalidni jen kvuli N<25 — pokud komprimuje, je relevantni
2. Confidence musi byt prepocitana na compression_ratio (ne na N)
3. Patterns s nizkou kompresi (= potrebuji mnoho vyjimek) = spise noise
4. Patterns s vysokou kompresi (= par vyjimek na mnoho dat) = spise signal

---

## 5. Implementace v architekture

### 5.1 Novy koncept: CompressibilityValidator

Vrstva 4.5 (mezi layer 4 analyzator a layer 5 pattern):

```
Analyzed games → Pattern detector → Candidate patterns
                                        │
                                        ▼
                               CompressibilityValidator
                                        │
                              ┌─────────┴─────────┐
                              ▼                   ▼
                    compression_ratio        entropy_reduction
                    > 1.5 = PASS            > 20% = PASS
                              │                   │
                              └─────────┬─────────┘
                                        ▼
                                Pattern artifact
```

**Formula pro confidence:**
```
compression_score = compression_ratio / max_compression_ratio
entropy_score = entropy_reduction / original_entropy
sample_score = min(games_with_pattern / min_games, 1.0)

final_confidence = 0.5 × compression_score 
                + 0.3 × entropy_score 
                + 0.2 × sample_score
```
Kde: compression_score ma nejvyssi vahu — pattern, ktery komprimuje, je validni i pri malem N.

### 5.2 Schema zmena v PatternMatch

```json
{
  "pattern_id": "Q",
  "pattern_name": "Active Defense",
  "confidence": 0.72,
  "confidence_breakdown": {
    "compression_ratio": 227.3,
    "entropy_reduction": 0.58,
    "compression_score": 0.85,
    "entropy_score": 0.58,
    "sample_score": 0.44
  },
  "severity": "low",
  "games_analyzed": 9,
  "occurrences": 4,
  "avg_cp_loss": 108,
  "evidence": [...],
  "hypothesis": "...",
  "trend": "stable",
  "first_seen": "2026-07-18",
  "last_seen": "2026-07-19"
}
```

### 5.3 Kompresni kalkulace v praxi

**Pro kazdy kandidatni pattern (during detection):**

```
1. raw_cost = sum(L(move_data) for all analyzed games)
   kde move_data = {phase, cp_loss, eval, piece, move_type}
   L(x) = 8 + log2(unique_values) — informacni obsah

2. pattern_cost = L(pattern_definition) + sum(L(exceptions))
   L(pattern_definition) = 8 + len(conditions) + 8 + len(label)
   L(exception) = 8 + ply + uci

3. if raw_cost / pattern_cost > 1.5 → pattern je kompresne relevantni
   if > 5.0 → pattern je silny signal
   if < 1.0 → pattern je noise (popis je delsi nez data)
```

### 5.4 Phase 1 — rozsireni

Pridat do Phase 1 novy task:

| Task | Co | Soubor | Odhad | Dopad |
|------|----|--------|-------|-------|
| **K8.1** | CompressibilityValidator | `src/services/compressibility_validator.py` (novy) | 1 hod | confidence recalibration + small-N robustness |

Napr. pattern Q s compression_ratio 227:1 a N=9 games ziska confidence ~0.76 (pattern je kompresne extremne silny), pattern s compression_ratio 1.2:1 a N=50 ziska confidence ~0.45 (pattern je slaby signal).

---

## 6. Zaver

**Mikolovova kompresni filozofie zachranuje chess pattern artifact pred "statistickou irelevanci".**

Bez ni: "s N=9 nemuzeme nic tvrdit." S ni: "pattern Q komprimuje data 227:1, proto je relevantni i pri N=9."

Architekturni dusledky:
1. **CompressibilityValidator** jako nova komponenta (vrstva 4.5)
2. **Confidence = 0.5 × compression + 0.3 × entropy + 0.2 × sample** — vzorec respektujici kompresi
3. **Pattern s compression_ratio < 1.5 = automaticky noise** — nezavisly na N
4. **Pattern s compression_ratio > 10 = silny signal** — i pri N < 10

Tato implementace je konzistentni s existujicimi principy:
- Determinismus (compression_ratio je deterministicka metrika)
- Filtrace sumu (high compression = signal, low compression = noise)
- Call to action (kazdy pattern nese informaci o sve relevanci)
- EROI (CompressibilityValidator ma vysoky prinos pri nizkych nakladech)
