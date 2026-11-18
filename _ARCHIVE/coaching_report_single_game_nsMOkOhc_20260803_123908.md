# Coaching Report — single_game (nsMOkOhc)

**Generated:** 2026-08-03 12:39 UTC
**Pipeline:** deterministic (Stockfish) + LLM cascade
**LLM provider:** NVIDIA

---

*No patterns detected.*

---

## LLM Report

[DATA] Základní info: Výsledek 1-0, barva white, zahájení Philidor Defense, celková ACPL 33,9.  
[DATA] Fazovy breakdown:  
  - Opening: ACPL 31,0 (údaje o chybách v této fázi nejsou v souladu s celkovým počtem chyb – viz poznámku níže).  
  - Middlegame: ACPL 43,7 (údaje o 1 chybě v této fázi rovněž nejsou v souladu s celkovým počtem chyb).  
  - Endgame: data nejsou k dispozici.  
[DATA] Error klasifikace:  
  - Blunders: žádné.  
  - Mistakes: celkový počet udán jako 0, ale fázový breakdown uvádí chyby v opening (2) a middlegame (1) – tento rozpor nelze z dostupných dat vyřešit, proto uvádíme, že přesná klasifikace chyb není k dispozici.  
  - Inaccuracies: 3 (konkrétní detaily jako tah, cp_loss nebo FEN nejsou poskytnuty).  
[DATA] Pattern detection výsledky pro tuto hru: žádné vzory nebyly detekovány.  
[DATA] BlunderFactSheet: žádné podrobnosti nejsou k dispozici (žádné blundry k analýze).  

[IM] Heisman-style error analýza: Protože v datech nejsou zaznamenány žádné blundry ani chyby, nelze určit jednu „nejkritičtější“ chybu. Tři zaznamenané nepřesnosti pravděpodobně přispěly k vyšší ACPL ve střední hře (43,7), ale bez konkrétních údajů nelze říci, zda byly taktické, poziční nebo související s časovým tlakem.  
[IM] Tři věci co hráč udělal dobře:  
  1. Vyhrál partii (1-0).  
  2. Udržel nízkou celkovou ACPL (33,9), což svědčí o solidní celkové hře.  
  3. V zahájení dosáhl velmi nízké ACPL (31,0), což naznačuje dobré zvládnutí úvodní fáze.  
[IM] Jedna věc na zlepšení do příště: Snížit počet nepřesností, zejména ve střední hře kde se ACPL zvýšil na 43,7; přesnější hře v této fázi by mohlo dále snížit riziko ztráty výhody.  
[IM] Tréninková doporučení:  
  - Pravidelně řešit taktické úlohy zaměřené na hledání přesných pokračování a minimalizaci zbytečných ztrát materiálu nebo pozice.  
  - Analyzovat své partie s důrazem na střední hru, identifikovat momenty, kde došlo k nepřesnostem, a porovnat je s engineovými návrhy.  
  - Hrát tréninkové partie s časovou kontrolou podobnou turnajové, aby se zvyklo na udržování přesnosti i při časovém tlaku.  
  - Po partiích využít engine k revizi nepřesností a pochopit, jaké alternativní tahy by vedly k nižší cp_loss.

---

## Provider Cascade

| # | Provider | Status | Tokens | Cost (USD) |
|---|----------|--------|--------|-----------|
| 1 | NVIDIA | OK | 2645 | 0.0 |