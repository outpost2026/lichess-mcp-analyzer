# Coaching Report — diagnosis (Systeq)

**Generated:** 2026-09-01 07:26 UTC
**Pipeline:** deterministic (Stockfish) + LLM cascade
**LLM provider:** NVIDIA
**Games analyzed:** 20

---

## Patterns (8)

| Pattern | Name | Confidence | Frequency | Severity |
|---------|------|------------|-----------|----------|
| O | Stagnační panika | 40.0% | 10 | CRITICAL |
| C | Attention tunneling | 27.0% | 6 | MEDIUM |
| Q2 | Win despite blunder | 27.0% | 6 | LOW |
| R | Endgame relaxation | 20.0% | 5 | HIGH |
| B | Automatic grab | 17.0% | 14 | HIGH |
| Q | Active defense | 14.0% | 3 | LOW |
| Q1 | Desperate Gambit Mode | 4.0% | 1 | LOW |
| N | X-ray pin violation | 4.0% | 1 | HIGH |

## Weakness Report

- Total ACPL: 44.65650969529086
- Blunders: 19
- Mistakes: 38
- Inaccuracies: 114

---

## LLM Report

**Summary**  
Systeq hrál 20 partií s průměrnou chybovostí (ACPL) 44,66, což odpovídá přibližně 1500 ELO úrovni. Nejvíce chyb vzniká v middlegame (ACPL ≈ 52,68) a endgame (ACPL ≈ 50,95), zatímco openingová příprava je slabá zejména ve Vídni hře – Max Lange obrana.  

**Priority Issues** (seřazeno podle severity × frequency)  
1. **B: Automatic grab** (HIGH, frekvence 14) – hráč bere materiál automaticky bez kontroly protihráčovy odpovědi.  
   *Mitigation:* 3‑sekundová pauza + otázka „A CO ON?“ před každým výměnou; nejprve zkontrolovat objevené útoky.  

2. **O: Stagnation panic** (CRITICAL, frekvence 10) – při rovnoměrném evaluačním platě hráč pocítí nutnost vynutit komplikace, které často pozici zhorší.  
   *Mitigation:* Při plochém evaluačním vývoji 2+ tahů se zastavit a zeptat se: „Je to opravdu stagnace, nebo jen pozicní klid?“ – nevynucovat komplikace bez konkrétního cíle.  

3. **R: Endgame relaxation** (HIGH, frekvence 5) – při materiální výhodě v koncovce hráč poleví v koncentraci a zahraje pasivní tahy, které výhodu ztratí.  
   *Mitigation:* Před každým tahem v vyhrávající koncovce nejprve zkontrolovat možnou protihráčovu hru, poté vlastní plán.  

4. **C: Attention tunneling** (MEDIUM, frekvence 6) – hráč fixuje pozornost na jednu oblast desky, přehlédne protihráčovu hru jinde.  
   *Mitigation:* Nastavit 15‑minutový timer během analýzy; po uplynutí času se zeptat: „Objevil se někde jinde nový problém?“  

5. **Q2: Win despite blunder** (LOW, frekvence 6) – hráč často dokáže vyhrát i po velké chybě, což naznačuje odolnost nebo štěstí soupeře.  
   *Mitigation:* Upevnit tuto sílu, ale zároveň rozebrat chyby, aby se zjistilo, zda vítězství pochází z odolnosti nebo štěstí.  

6. **Q: Active defense** (LOW, frekvence 3) – hráč upřednostňuje aktivní protihru před pasivní obranou, což vytváří šance i v horších pozicích.  
   *Mitigation:* Tato silná stránka je užitečná, ale je třeba se snažit nejprve nepropadnout do ztracených pozic.  

7. **N: X‑ray pin violation** (HIGH, frekvence 1) – hráč občas přehlédne, že je jeho figura přišpendlena k vyšší hodnotě za ní.  
   *Mitigation:* Před každým tahem zkontrolovat, zda není figura přišpendlena k králi nebo dámě; pokud ano, ověřit, že tah neodhalí vyšší hodnotu.  

8. **Q1: Desperate Gambit Mode** (LOW, frekvence 1) – v prohraných pozicích hráč přechází do chaotického režimu, odměňuje výměny a vytváří hrozby.  
   *Mitigation:* Při prohrané pozici: odmítnout výměny dámy, udržet figury aktivní, vytvářet šachy a hrozby – soupeř často chybí v časové tísni.  

**Training Recommendations**  
- **Automatické braní:** Před každým výměnou provést 3‑sekundovou kontrolu (hrozba objeveného útoku, protihráčova odpověď). Zapsat si tuto rutinu do tréninkového deníku.  
- **Stagnace vs. klid:** Po každých dvou tazích s téměř nezměněným evaluačním číslem provést krátkou pauzu a položit otázku o povaze pozice. Procvičovat na partiích s rovnoměrnou hrou (např. v otevřených pozicích).  
- **Koncentrace v koncovce:** Před každým tahem v koncovce s materiální výhodou nejprve prohlédnout šachovnici na možné protihráčovy hrozby (šachy, převislé figury, možné výměny).  
- **Rozptýlení pozornosti:** Použít timer (15 min) při analýze partií; po uplynutí času provést rychlý „board scan“ celou šachovnici, aby se odhalily přehlédnuté hrozby.  
- **Odolnost po chybě:** Po partiích s velkou chybou rozebrat, zda vítězství vzniklo díky vlastní hře nebo díky soupeřovým nepřesnostem; zaznamenat poučení do sešitu.  
- **Aktivní obrana:** V tréninkových partiích cíleně hledat aktivní protihru i v horších pozicích, ale současně pracovat na minimalizaci rizika přejít do ztracené pozice (např. přesné výpočty před obětováním materiálu).  
- **X‑ray špendlíky:** Denně řešit 5‑10 taktických cvičení zaměřených na odhalení přišpendlených figur (zejména těch, které chrání vyšší hodnotu).  

**Strengths**  
- **Odolnost po chybě (Q2):** Schopnost vyhrát i po významné chybě ukazuje bojového ducha a schopnost najít kompenzaci.  
- **Aktivní obrana (Q):** Sklon k aktivní protihře často vytváří šance i v nepříznivých pozicích – užitečná zbraň, pokud se kombinuje s lepší přípravou openingů.  
- **Občasná schopnost vytvářet chaos (Q1):** V zoufalých situacích hráč dokáže generovat hrozby, což může soupeře přimět k chybě v časové tísni.  

**Next Session Focus**  
Hlavní důraz na první dvě priority issues:  
1. Eliminovat automatické braní pomocí 3‑sekundové kontroly před každým výměnou.  
2. Rozlišovat skutečnou stagnaci od pouhého pozicního klidu a naučit se nevynucovat komplikace bez jasného cíle.  

Tyto dva body mají nejvyšší kombinaci závažnosti a četnosti a jejich zlepšení by mělo nejvíce snížit celkový počet blunders a zlepšit stabilitu hry v middlegame a endgame.

---

## Provider Cascade

| # | Provider | Status | Tokens | Cost (USD) |
|---|----------|--------|--------|-----------|
| 1 | NVIDIA | OK | 3716 | 0.0 |