# Coaching Report: systeq (NVIDIA)

**Generated:** 2026-07-20 14:51 UTC  
**Provider:** NVIDIA  
**Model:** nvidia/nemotron-3-super-120b-a12b  
**Tokens:** 2667  
**Cost:** $0.000000  
**Time:** 21.3s  

---

**Summary**  
Analýza pěti partií hráče systeq ukazuje celkovou ACPL 43,3 s nejvíce chyb ve střední hře a koncovce. Nejvýraznější tendencí je výrazně vyšší chybovost při hře černými figurami a tendence k uvolnění pozornosti v výhodných koncovkách. Zároveň hráč projevuje aktivní obranu a schopnost vytvářet hrozby i v horších pozicích.

**Priority Issues** (seřazeno podle závažnosti × frekvence)  
1. **G: Barva jako modulátor** – VYSOKÁ závažnost, frekvence 3 (černé figuríny vedou k 3× více chyb).  
2. **R: Uvolnění v koncovce** – VYSOKÁ závažnost, frekvence 2 (při materiální výhodě dochází k pasivním tahům, které ztrácí výhodu).  
3. **C: Tunelová pozornost** – STŘEDNÍ závažnost, frekvence 2 (fixace na jednu oblast desky, přehlédnutí protihráčovy hry).  
4. **J: Impulzivní blok šachu** – VYSOKÁ závažnost, frekvence 1 (v šachu často blokuje figurkou bez posouzení útěku krále).  
5. **Q: Aktivní obrana** – NÍZKÁ závažnost, frekvence 2 (silná stránka – hráč rád hledá protiútok i v horších pozicích).  
6. **Q1: Režim zoufalého gambitu** – NÍZKÁ závažnost, frekvence 1 (v prohraných pozicích odměňuje výměny a vytváří hrozby, aby využil časového tlaku soupeře).

**Training Recommendations** (konkrétní a proveditelné)  
- **Barva jako modulátor**: Před partií černými figurami si představ, že jsi o pěšec méně; hraj s větší opatrností a věnuj zvláštní pozornost taktickým hrozbám soupeře. Trénuj partie, kde začínáš černými, a po každém tahu se zeptej: „Jaká hrozba by mohla vzniknout na druhé straně desky?“  
- **Uvolnění v koncovce**: Před každým tahem v výhodné koncovce proveď rychlou kontrolu: „Jaké protihráčovy figury mohou vytvořit nebezpečí?“ Používej cvičení na přesné výpočty v koncovkách (např. král a pěšec proti králi) a nastav si časový limit, abys udržel koncentraci.  
- **Tunelová pozornost**: Nastav si během partie 15‑minutový interval (např. pomocí hodin) a po jeho uplynutí proveď krátkou inventářskou kontrolu celé desky – hledej nejen své plány, ale i možné protihráčovy odpovědi.  
- **Impulzivní blok šachu**: Při šachu nejprve zvaž všechny možné úkryty krále (útěk, blok, výměna) a teprve poté rozhodni o bloku. Řeš pravidelně hádanky zaměřené na reakce na šach (např. 5‑10 denně).  
- **Aktivní obrana** (posílit): V tréninkových partiích vědomě hledej protiútok i když jsi materiálně horší, ale zároveň si stanov limit, kdy je nutné přejít do pevnější obrany, aby ses vyhnul zbytečným rizikům.  
- **Režim zoufalého gambitu** (využít): V prohraných pozicích cvič odmítání výměn královny, udržuj aktivitu figur a vytvářej šachy či hrozby, které soupeře nutí přemýšlet o času.

**Strengths** (vzory dobré hry)  
- Aktivní obrana a schopnost vytvářet hrozby i v horších pozicích (vzory Q a Q1) naznačují bojovného hráče, který se nevzdává snadno.  
- V úvodní fázi je ACPL relativně nízká (34,16) a pouze jedna partie v úvodu obsahuje blunders, což naznačuje solidní přípravu úvodů.

**Next Session Focus**  
Nejbližší trénink se zaměří na dvě nejvyšší priority: (1) eliminaci rozdílu v chybovosti mezi bílými a černými figurami prostřednictvím cílených partií a mentální kompenzace, a (2) udržení koncentrace v výhodných koncovkách pomocí kontrolních bodů a konkrétních koncovkových cvičení. Současně bude zařazeno krátké cvičení na reakce na šach, aby se snížila impulzivita blokování. Tyto aktivity jsou přímo odvozeny z zaznamenaných vzorů a nevyžadují žádné dodatečné předpoklady mimo poskytnutá data.