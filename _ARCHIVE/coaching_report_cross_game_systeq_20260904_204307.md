# Coaching Report — cross_game (systeq)

**Generated:** 2026-09-04 20:43 UTC
**Pipeline:** deterministic (Stockfish) + LLM cascade
**LLM provider:** NVIDIA
**Games analyzed:** 20

---

## Patterns (9)

| Pattern | Name | Confidence | Frequency | Severity |
|---------|------|------------|-----------|----------|
| O | Stagnační panika | 40.0% | 10 | CRITICAL |
| S | Capture aversion under check | 2.0% | 1 | CRITICAL |
| R | Endgame relaxation | 24.0% | 6 | HIGH |
| Q | Active defense | 22.0% | 5 | LOW |
| C | Attention tunneling | 18.0% | 4 | MEDIUM |
| Q2 | Win despite blunder | 18.0% | 4 | LOW |
| B | Automatic grab | 13.0% | 10 | HIGH |
| J | Impulsive check block | 5.0% | 1 | HIGH |
| Q1 | Desperate Gambit Mode | 4.0% | 1 | LOW |

## Weakness Report

- Total ACPL: 43.314473684210526
- Blunders: 11
- Mistakes: 36
- Inaccuracies: 159

---

## LLM Report

[DATA] Agregované statistiky:
- Celkový počet her: 20
- Průměrná ACPL (všech her): 43.31
- Celkový počet blunderů: 11 → průměrně 0.55 blunderu na hru
- Celkový počet mistake: 36 → průměrně 1.8 mistake na hru
- Celkový počet nepřesností: 159 → průměrně 7.95 nepřesnosti na hru
- Výsledky (W/L/D) a rozdělení dle barvy nejsou v poskytnutých datech uvedeny → data nejsou k dispozici.
- ACPL trend (první polovina her vs druhá) není v datech uveden → data nejsou k dispozici.

[DATA] Phase breakdown (z weakness report):
- Opening: ACPL 24.05, blunders 3 z 196 tahů (≈1.5 % chyb)
- Middlegame: ACPL 53.63, blunders 22 z 268 tahů (≈8.2 % chyb)
- Endgame: ACPL 46.73, blunders 22 z 296 tahů (≈7.4 % chyb)

[DATA] Pattern ranking (sestupně dle závažnosti a frekvence; závažnost: critical > high > medium > low):
1. Stagnační panika – frequency = 10, severity = critical, confidence = 40 %
2. Capture aversion under check – frequency = 1, severity = critical, confidence = 2 %
3. Automatic grab – frequency = 10, severity = high, confidence = 13 %
4. Endgame relaxation – frequency = 6, severity = high, confidence = 24 %
5. Impulsive check block – frequency = 1, severity = high, confidence = 5 %
6. Attention tunneling – frequency = 4, severity = medium, confidence = 18 %
7. Active defense – frequency = 5, severity = low, confidence = 22 %
8. Win despite blunder – frequency = 4, severity = low, confidence = 18 %
9. Desperate Gambit Mode – frequency = 1, severity = low, confidence = 4 %

[DATA] Error distribution:
- Rozdělení chyb na taktické vs. positionální není v poskytnutých datech uvedeno → data nejsou k dispozici.

[IM] Heisman-style diagnostika:
- Nejkritičtější pattern z hlediska dopadu na výsledek se jeví **Stagnační panika** – vyskytuje se v polovině her (10/20) a je označena jako critical; její hypotéza popisuje, že hráč v klidných pozicích nutně vytváří komplikace, které vedou k ztrátě výhody.
- Největší ztráty ELO pravděpodobně pocházejí ze **middlegame**, kde je ACPL nejvyšší (53.63) a relativně největší podíl blunderů (22/268 ≈ 8 %). Endgame také ukazuje vysokou ACPL, ale middlegame má horší poměr chyb k počtu tahů.

[IM] Silman-style assessment:
- Na základě detekovaných patternů hráč systematicky přehlíží:
  - **Bezpečnost krále při šachu** (Capture aversion under check, Impulsive check block) – tendence blokovat nebo utíkat místo přímého zachycení.
  - **Materiální rovnováhu při captures** (Automatic grab) – sklon k automatickému zachycení bez kontroly protihráčovy odpovědi.
  - **Pozicní klid** (Stagnační panika) – vnímá rovnou evaluaci jako nebezpečnou a nutí nepřiměřené komplikace.
  - **Koncentraci ve výhodných endgame** (Endgame relaxation) – po získání materiální výhody snižuje pozornost, což umožňuje soupeři kontrapraktiku.
- Hráč se naopak zdá excelovat v **aktivní obraně** (Active defense) a **odolnosti po velkých chybách** (Win despite blunder, Desperate Gambit Mode), kdy dokáže vytvářet hrozby i z horších pozic.

[IM] Top 3 doporučení (Heisman: nejprve eliminovat největší chybu):
1. **Eliminovat Stagnantní paniku** – při rovné evaluaci (≤30cp změna přes 3+ tahy) vědomě zastavit, položit si otázku „Je to opravdu stagnace, nebo jen pozicní klid?“ a vyhnout se vynuceným komplikacím bez konkrétního cíle.
2. **Zlepšit middlegame techniku** – před každým zachycením provést 3‑sekundovou pauzu a zeptat se „A CO ON?“ (zkontrolovat objevené útoky, protihráčovu odpověď); tím se sníží frekvence automatických grabů.
3. **Posílit endgame koncentraci** – v výhodných endgame před každým tahem nejprve zkontrolovat soupeřovy možnosti kontrapraktiky, teprve potom realizovat vlastní plán; využít jednoduchý kontrolní seznam (aktivita krále, pěšcová struktura, případné protihráčovy hrozby).

[IM] Verdikt:
Hráč vykazuje silnou schopnost aktivní hry a odolnosti po chybách, ale jeho největší slabiny pramení z tendence nutit komplikace v klidných pozicích, nepřiměřeného spěchu při zachycováních a poklesu koncentrace v výhodných endgame. Zaměřením se na uvedené tři oblasti lze očekávat snížení průměrné ACPL a zvýšení konverze výhodných pozic ve výhrách.

---

## Provider Cascade

| # | Provider | Status | Tokens | Cost (USD) |
|---|----------|--------|--------|-----------|
| 1 | NVIDIA | OK | 6637 | 0.0 |