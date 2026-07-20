# Coaching Report: systeq (NVIDIA)

**Generated:** 2026-07-20 15:00 UTC  
**Provider:** NVIDIA  
**Model:** nvidia/nemotron-3-super-120b-a12b  
**Tokens:** 2590  
**Cost:** $0.000000  
**Time:** 17.4s  

---

**Souhrn**  
Analýza pěti partií hráče systeq ukazuje celkovou průměrnou chybovost (ACPL) 43,3, přičemž nejvíce chyb vzniká v middlegame a koncovce. Nejvýraznější tendence jsou spojené s barvou (černá strana vede k třikrát více blunderům), s tendencí k „uklidnění“ v výhodných koncovkách a s úzkým fokusem na jednu část desky, který přehlédne protihru jinde.  

**Prioritní problémy** (seřazeno podle závažnosti × frekvence)  
1. **G: Barva jako modulátor** – HIGH (3) × frekvence 3 = 9 → černá strana má výrazně vyšší počet blunderů.  
2. **R: Endgame relaxation** – HIGH (3) × frekvence 2 = 6 → v výhodných koncovkách hráč polevuje v koncentraci a dělá pasivní tahy.  
3. **C: Attention tunneling** – MEDIUM (2) × frekvence 2 = 4 → hráč se fixuje na jednu oblast desky a přehlédne protihru jinde.  
4. **J: Impulsivní blok šachu** – HIGH (3) × frekvence 1 = 3 → v šachu často blokuje figurkou bez posouzení bezpečí krále.  
5. **Q: Aktivní obrana** – LOW (1) × frekvence 2 = 2 → hráč rád hledá aktivní protiútok, i když je pozice horší.  
6. **Q1: Desperátní gambitový režim** – LOW (1) × frekvence 1 = 1 → v ztracených pozicích přechází do chaotické hry, aby vyvolal chyby soupeře.  

**Tréninková doporučení** (konkrétní a proveditelné)  
- **Barva a impulzivita**: Před každou partií černými si představ, že hraješ o pěšce méně; vědomě zpomaluj tempo a po každém tahu se zeptej, zda se neobjevila nová hrozba jinde na desce.  
- **Koncovka**: Před každým tahem v výhodné koncovce proveď rychlou kontrolu: „Jaké má soupeř možnosti protihry?“ Teprve poté zvaž svůj vlastní plán.  
- **Pozornost tunnelu**: Nastav si 15‑minutový interval (např. pomocí kuchyňského času) během partie; po uplynutí času se zastav a explicitně zkontroluj všechny čtyři strany desky, než pokračuješ v původním plánu.  
- **Reakce na šach**: Vytvoř si sadu 10‑15 hádanek, kde je nutné nejprve zvážit únik krále, teprve poté blok nebo výměnu. Trénuj je denně 5‑10 minut.  
- **Aktivní obrana**: Udržuj tuto silnou stránku, ale přidej krátkou sekvenci „záchranných tahů“ (např. výměna nejméně aktivní figury) předtím, než se pustíš do rizikového protiútoku, aby ses vyhnul zbytečnému zhoršení pozice.  

**Silné stránky** (vzory, které ukazují dobrou hru)  
- **Aktivní obrana (Q)** a **Desperátní gambitový režim (Q1)** svědčí o bojovném duchu a schopnosti vytvářet hrozby i v horších pozicích – tato vlastnost může být základem pro záchranu partií.  
- Nulový počet „mistakes“ v souhrnu naznačuje, že hráč se vyhýbá větším strategickým přešlapům a většina chyb je spíše taktického charakteru, což je lépe trénovatelné.  

**Zaměření na další sezení**  
Soustředit se na kombinaci dvou nejvýše postavených problémů:  
1. **Barva‑závislá impulzivita** – praktikovat partie černými s vědomým zpomalením a kontrolou protihry po každém tahu.  
2. **Koncová relaxace** – hrát koncovkové výukové pozice (např. král a pěšec proti králi) s povinnou předtahovou kontrolou soupeřových možností.  

Tímto způsobem se pracuje na nejčastějších a nejvážnějších chybách, zatímco se zachovává a rozvíjí hráčova přirozená bojovnost.