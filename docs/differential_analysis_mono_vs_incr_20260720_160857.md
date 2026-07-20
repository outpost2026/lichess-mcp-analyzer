# Differential Analysis: Monolithic vs Incremental Pipeline

**Generated:** 2026-07-20 16:08 UTC  
**Games:** 5 (same data)  
**Reference monolithic:** NVIDIA, 2597 tokens  
**Incremental provider (R1):** NVIDIA  
**Incremental provider (R2):** NVIDIA  

---

## Metrics Comparison

| Metric | Monolithic | Incremental R1 (cold) | Incremental R2 (warm) |
|---|---|---|---|
| Provider | NVIDIA | NVIDIA | NVIDIA |
| Total tokens | 2597 | 10530 (6323 per-game + 4207 agg) | 3806 (0 per-game + 3806 agg) |
| LLM cost | $0.0000 | $0.0000 | $0.0000 |
| Pipeline time | 17.4s | 39.0s | 22.5s |
| Report length | 39 lines | 48 lines | 53 lines |
| Deterministic | N/A (single run) | Run1 baseline | NO |

## Per-Game LLM Cache (cold run)

| Game | Tokens | Cost | Time |
|---|---|---|---|
| MtEGzuvx | 1379 | $0.000000 | 0.0s |
| qmodxzNF | 1246 | $0.000000 | 0.0s |
| BAEXAHoW | 1210 | $0.000000 | 0.0s |
| AczKbLug | 1259 | $0.000000 | 0.0s |
| 9PSKkXvK | 1229 | $0.000000 | 0.0s |
| **Total** | **6323** | **$0.000000** | **0.0s** |

## Cost/Time Projection

| Scenario | Monolithic | Incremental |
|---|---|---|
| 50 games (initial) | 129,850 tok, ~$0.0000 | 73,157 tok, ~$0.0000 |
| +10 new games | 155,820 tok (re-run 60) | 86,947 tok (10 per-game + aggregate) |
| Token savings on +10 | baseline | **68,873 tok saved** (44%) |

## Report Quality

**Reports differ between runs** (non-deterministic LLM output).

### Incremental Run 1 (first 20 lines)

```
**1. Shrnutí**  
V pěti analyzovaných partiích dosáhl hráč průměrnou ztrátu centipawnů (ACPL) 43,3 a udělal 11 blatných chyb (blunders) spolu s 30 nepřesnostmi. Nejvíce chyb vzniklo v middlegame (6 blunders, ACPL ≈ 44,6), zatímco v zahájení a koncovce byly chyb méně, ale koncovka vykazovala nejvyšší ACPL (≈ 48,9). Hráč černými figurami dělá výrazně více chyb než bílými (9 vs. 2 blunders), což odpovídá detekovanému vzoru „barva jako modulátor“.

**2. Prioritní problémy (seřazeno podle závažnosti × frekvence)**  

| Pořadí vzhlediska | Frekvence | Poznámka (z)  
---|---|---|---|---  
**G: Barva jako modulátor** (vysoká důvěra 95 %, frekvence 3) | Data ukazují, že v černých partiích hráč udělal 9 z 11 blunders, zatímco v bílých jen 2. To naznačuje tendenci k větší chybovosti při hře černými. |  
**R: Uvolnění v koncovce** (vysoká důvěra 70 %, frekvence 2) | ACPL v koncovce je nejvyšší ze všech fází (≈ 48,9) a došlo k 2 blunders, i když celkový počet je nízký. To může signalizovat sníženou koncentraci při výhodné materiální pozici. |  
**C: Tunelová pozornost** (střední důvěra 40 %, frekvence 2) | Dvě instance naznačují, že hráč může fixovat pozornost na jednu část desky a přehlédnout protihru jinde. |  
**J: Impulzivní blok šachu** (vysoká důvěra 33 %, frekvence 1) | Jedna pozorovaná situace, kdy hráč zřejmě blokoval šach bez hodnocení bezpečnosti krále. |  
**Q: Aktivní obrana** (nízká důvěra 80 %, frekvence 2) | Dva případy naznačují, že hráč rád hraje aktivně i v horších pozicích, což může vytvářet protihru. |  
**Q1: Rezolutní gambitový režim** (nízká důvěra 70 %, frekvence 1) | Jedna situace, kdy hráč v prohrané pozici odměnil výměny a snažil se vytvořit nebezpečí, pravděpodobně aby vyvolal chybu soupeře v časové tísni. |  

*Poznámka: Hodnocení „závažnosti“ je odvozeno z úrovně důvěry pattern detection (vysoká = 3, střední = 2, nízká = 1) násobené frekvencí výskytu. Jedná se o orientační pořadí, nikoli o definitivní důkaz.*

**3. Doporučení pro trénink**  

- **Barva jako modulátor**  
  - Při přípravě na partie černými figurami vědomě zpomalte tempo a před každým tahem se zeptejte: „Jaká je nejhorší odpověď soupeře?“  
```

### Incremental Run 2 (first 20 lines)

```
**1. Shrnutí**  
V pěti analyzovaných partiích jste dosáhli průměrné ztráty 43,3 cp (ACPL) a udělali 11 blundrů. Nejvíce chyb vzniká v middlegame, kde je ACPL nejvyšší (44,6 blundrů, a při hře černými děláte až trojnásobně více blundrů než při hře bílými. Naopak projevujete aktivní obranu a schopnost vytvářet protihru i v horších pozicích.

**2. Prioritní problémy (seřazeno podle závažnosti × frekvence)**  

| Pořadí | Problém (zdroj) | Závažnost | Frekvence | Proč je důležité |
|-------|-----------------|-----------|-----------|------------------|
| 1 | **Barva jako modulátor** (Pattern G) | HIGH (3) | 3 | Při hře černými děláte 3× více blundrů → hlavní zdroj ztrát. |
| 2 | **Uvolnění v koncovce** (Pattern R) | HIGH (3) | 2 | Když máte materiální výhodu, polevíte koncentrací a ztrácíte výhodu pasivními tahy. |
| 3 | **Taktická povědomost v middlegame** (Weakness Report) | – (z dat: nejvyšší ACPL 44,57 a 6 blundrů) | – | Middlegame přináší nejvíce chyb; zlepšení zde sníží celkový ACPL. |
| 4 | **Pozornostní tunel** (Pattern C) | MEDIUM (2) | 2 | Fixujete se na jednu část desky a přehlédnete protihráčovu hrozbu jinde. |
| 5 | **Impulzivní blok šachu** (Pattern J) | HIGH (3) | 1 | V šachu často blokujete figurkou bez zkoumání útěku krále, což může vytvořit novou slabost. |
| 6 | **Desperátní gambitový režim** (Pattern Q1) | LOW (1) | 1 | V prohraných pozicích přecházíte do chaotické hry; může vytvořit šance, ale často prohlubuje ztrátu. |

**3. Tréninková doporučení (konkrétní a proveditelné)**  

- **Hra černými**  
  - Před každou partií černými si představte, že hrajete bílými a že jste o pěšce méně – tato mentální kompenzace snižuje impulzivitu (mitigace z Pattern G).  
  - Trénujte partie pouze s černými figurkami proti engine nebo sparring partnerovi a zaměřte se na snížení blundrů na polovinu svého současného průměru (cíl ≤ 0,5 blundu/partii).  

```
