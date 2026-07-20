# Coaching Report: systeq (Incremental)

**Generated:** 2026-07-20 16:02 UTC  
**Pipeline:** per-game LLM cache + aggregate  
**Games:** 5 (0 new, 5 from LLM cache)  
**Per-game LLM:** 5 cached  
**Aggregate provider:** NVIDIA  
**Aggregate tokens:** 3496  
**Patterns detected:** 6  

---

**1 game with 0 blunders.

Next session focus: maybe work on middlegame tactics and endgame vigilance.

Now produce report in Czech, plain language, no absolutes.

Let's write**Summary**  
V pěti analyzovaných partiích měl hráč průměrnou ztrátu centipawnů (ACPL) 43,3 a celkem 11 blunderů. Nejvíce chyb vzniká v middlegame (ACPL ≈ 44,6, 6 blunderů) a v koncovkách, kdy se hráč často uvolní při materiální výhře. Silnou stránkou je tendence k aktivní obraně a vytváření protihry i v horších pozicích.

**Priority Issues** (seřazeno podle závažnosti × frekvence)  
1. **Barva jako modulátor** – vysoká spolehlivost (95 %), hráč při černé barvě dělá přibližně třikrát více blunderů než při bílé.  
2. **Uvolnění v koncovce** – vysoká spolehlivost (70 %), při materiální výhodě v koncovce hráč často dělá pasivní tahy a ztrácí výhodu.  
3. **Aktivní obrana** – dobrá spolehlivost (80 %), hráč rád hledá protihru, což může vést k rizikovým pozicím, pokud se nejprve nezbaví nepřesností.  
4. **Impulzivní blok šachu** – střední spolehlivost (33 %), při šachu hráč často blokuje figurkou bez posouzení útěku krále.  
5. **Přetrvávající pozornost (attention tunneling)** – střední spolehlivost (40 %), hráč fixuje se na jednu část desky a přehlédne protihráčovu hru jinde.  
6. **Taktická povědomí v přechodech middlegame** – podle slabin reportu je zde nejvyšší ACPL a nejvíce blunderů (6).  

**Training Recommendations** (konkrétní a proveditelné)  
- **Barva a impulzivita**: před každou partií si představ, že hraješ opačnou barvu a že jsi o pěšec méně; toto jednoduché mentální cvičení snižuje rozdíl v chybovosti mezi bílou a černou.  
- **Koncovková bdělost**: před každým tahem v koncovce, kdy vedeš materiálně, nejprve zkontroluj, jaké protihráčovy hrozby existují (kontrola krále, možné šachy, výměnné kombinace). Používej jednoduché koncovkové cvičení (např. král a věž proti králi) s důrazem na aktivní pozici krále.  
- **Reakce na šach**: když jsi v šachu, nejprve prohlédni všechny možné úkryty krále (úkryt, blok, výměna) a teprve až poté zvaž blok figurkou. Trénuj na hádankách zaměřených na odpověď na šach (5–10 denně).  
- **Rozptýlení pozornosti**: nastav si během partie 15‑minutový timer (nebo použij hodiny s přerušovaným signálem) a při každém signálu se zeptej: „Jaká nová hrozba se mohla objevit jinde na desce?“ Toto cvičení pomáhá přerušit fixaci na jednu oblast.  
- **Taktika v middlegame**: věnuj 10–15 minut denně řešení taktických úloh zaměřených na přechody z opening do middlegame (např. výměny, otevření linií, objevené útoky). Po každé partii si poznamenat, kde jsi přehlédl taktickou možnost a proč.  

**Strengths** (vzory dobré hry)  
- **Aktivní obrana / Desperátní gambit** – hráč často odmítá pasivní obranu, hledá protihru a vytváří hrozby i v horších pozicích (vzory Q a Q1). Tato schopnost může přinést výhry, pokud se nejprve eliminují zbytečné nepřesnosti.  
- **Jedna partie bez blunderů** – v partii 9PSKkXvK hráč černými neudělal žádný blunder, což ukazuje, že je schopen hrát přesně, když se soustředí.  

**Next Session Focus**  
Na příštím tréninkovém sezení se soustřeď na kombinaci dvou nejvýznamnějších slabin:  
1. **Barvová rozdílnost a impulzivita** – krátká partie (10–15 minut) kde si hráč vědomě mění perspektivu barvy a před každým tahem v šachu kontroluje úkryt krále.  
2. **Koncovková pozornost** – série koncovkových pozic (král+věž vs král, král+dvě věže vs král) s úkolem najít nejaktivnější plán krále před provedením jakéhokoli jiného tahu.  

Tento zaměřených vzorech a ne na domnělého plánu.  

Tímto zaměřením by měl hráč snížit rozdíl v chybovosti mezi barvami, udržet koncentraci v koncovkách a zároveň rozvíjet svou silnou stránku aktivní obrany. Na konci sezení doporučuji krátkou reflexi: které situace stále vyvolávají impulzivní blok šachu a jaké nové hrozby se objevily jinde na desce po použití 15‑minutového intervalu.