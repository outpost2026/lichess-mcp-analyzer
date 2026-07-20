# Coaching Report: systeq (Cerebras)

**Model:** gpt-oss-120b  
**Tokens:** 2938  
**Cost:** $0.000000  

---

**Shrnutí**  
Analýza pěti partií ukazuje, že hlavní slabiny hráče systeq jsou spojeny s hrou s černými figurami a s nedostatečnou taktickou pozorností v přechodu do střední hry. Dále se objevují problémy s koncentrací v koncovkách a s impulzivními reakcemi na šach.

---

### Prioritní problémy  

| # | Problém (důležitost × frekvence) | Hodnocení | Frekvence | Poznámka |
|---|-----------------------------------|-----------|-----------|----------|
| 1 | **Barva jako modulátor (G)** – výrazně vyšší počet chyb při hře s černými figurami (3‑násobek chyb) | VYSOKÁ (95 %) | 3 partie | Vliv na celkový počet blunderů (6 v middlegame). |
| 2 | **Taktická nepozornost v middlegame** – 6 blunderů, ACPL ≈ 44,5 | VYSOKÁ (z weakness report) | 5 partií | Přechod z otevření do střední hry je kritický. |
| 3 | **Uvolnění v koncovce (R)** – ztráta výhody při materiálním převýšení | VYSOKÁ (70 %) | 2 partie | Přispívá k vysokému ACPL v koncovce (≈ 48,9). |
| 4 | **Impulzivní blokování šachu (J)** – reflexní blok bez ohledu na bezpečnost krále | STŘEDNÍ (33 %) | 1 partie | Jednorázové, ale potenciálně rozhodující. |
| 5 | **Tunelování pozornosti (C)** – zaměření na jedno pole a přehlédnutí protihry | STŘEDNÍ (40 %) | 2 partie | Může vést k sekundárním chybám. |

---

### Doporučený trénink  

1. **Práce s černými figurami**  
   - **Cílené partie:** hraj alespoň 5 her s černými figurami denně, zaměř se na bezpečnost krále a vyhýbání se zbytečným taktickým chybám.  
   - **Analýza:** po každé partii si projdi všechny tahy, kde došlo k blunderu, a zkus najít, co tě odvedlo od správného řešení.  
   - **Otvírací repertoár:** posilni otevření, kde máš nejvíce chyb (Scotch, Trompowsky, Sicilská – uzavřená). Nauč se typické plány a typické taktické motivy.

2. **Taktické cvičení pro střední hru**  
   - **Puzzle:** 15 minut denně řeš taktická cvičení zaměřená na střední hru (např. „middle‑game tactics“ v lichess, Chess.com).  
   - **Tematické tréninky:** zaměř se na kombinace, které vznikají po výměně střelců a koní, protože právě v těchto pozicích se u tebe objevují chyby.  

3. **Koncovky – udržení koncentrace**  
   - **Endgame drills:** 10 minut denně hraj jednoduché koncovky (král + pěšec vs král, věžové koncovky) a před každým tahem si polož otázku „Jaký je největší protihodící tah soupeře?“  
   - **Kontrolní checklist:** před každým tahem v koncovce si rychle projdi: 1) protiútok, 2) aktivita krále, 3) potenciální pasáž.  

4. **Reakce na šach**  
   - **Check‑response puzzle:** najdi sadu úloh, kde je hlavní úkolem najít nejlepší únikový tah (ne blok). Trénuj alespoň 5 úloh týdně.  
   - **„Stop‑and‑think“ metoda:** při každém šachu si dej 5 sekund na rychlé zhodnocení „kde může král uniknout?“ před tím, než uvažuješ o bloku.  

5. **Prevence tunelování**  
   - **Timer‑trénink:** během analýzy partií si nastav 15‑minutový limit na jeden tah a po uplynutí času se zamysli, zda jsi nevynechal jiné relevantní figury či pole.  
   - **„Zpětný pohled“:** po každém tahu si krátce projdi celý šachovnici a zkus najít, zda se neobjevily nové hrozby mimo oblast, na kterou jsi se soustředil.  

---

### Silné stránky  

- **Aktivní obrana (Q)** – máš tendenci vytvářet dynamické protiútoky i v nepříznivých pozicích, což často vede k komplikacím a možnostem soupeře udělat chybu.  
- **„Desperate Gambit Mode“ (Q1)** – v ztracených partiích dokážeš udržet napětí, odmítat výměny a hledat taktická řešení, což může soupeře přimět k časovým chybám.  
- **Základní otevření** – v Alapinově variantě se ti daří bez výrazných chyb, což ukazuje na solidní znalost základních principů.  

---

### Fokus na další tréninkovou seanci  

1. **Hra s černými figurami** – zaměř se na konkrétní otevření, kde máš nejvíce chyb, a procvičuj typické taktické motivy.  
2. **Taktické cvičení pro střední hru** – řeš úlohy, kde je potřeba najít kombinace po výměně střelců a koní.  
3. **Endgame checklist** – během koncovky si zvykej kontrolovat protihodící tahy soupeře před tím, než provedeš svůj plán.  

Tyto tři oblasti by měly přinést největší zlepšení v průměrném hodnocení chyb a pomoci ti stabilizovat hru jak s bílými, tak s černými figurami. Hodně štěstí!