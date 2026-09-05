# Coaching Report — single_game (yBgAmaI7)

**Generated:** 2026-09-05 14:48 UTC
**Pipeline:** deterministic (Stockfish) + LLM cascade
**LLM provider:** NVIDIA

---

*No patterns detected.*

---

## LLM Report

[DATA] Základní info: výsledek 1-0, barva white, zahájení Sicilian Defense: Closed, Traditional, celková ACPL 18.9  
[DATA] Fazový breakdown:  
  - Opening: ACPL 11.4, 0 chyb  
  - Middlegame: ACPL 25.2, 3 chyb (1 chyba, 2 nepřesnosti)  
  - Endgame: ACPL 0.0, 0 chyb  
[DATA] Error klasifikace:  
  - Blunders: žádné  
  - Chyby:  
    * ply 29: Bd2 (SAN: Bd2, cp_loss 176, fáze middlegame, FEN před tahem: 1r3rk1/p3ppb1/b1pp2pn/q1p3N1/4P2Q/2NP4/PPP3PP/1RB2RK1 w - - 4 15, motif None, check False, taktická/poziční: podle dat taktická=False → klasifikováno jako poziční)  
  - Nepřesnosti:  
    * ply 21: Rb1 (cp_loss 62, fáze middlegame, check False, motif není uveden → klasifikace nejistá, pravděpodobně poziční)  
    * ply 25: Ng5 (cp_loss 78, fáze middlegame, check False, motif není uveden → klasifikace nejistá, pravděpodobně poziční)  
[DATA] Pattern detection výsledky pro tuto hru: [] (žádné detekované vzory)  
[DATA] BlunderFactSheet (pro chybu na ply 29):  
  - engine_lines top3:  
    1. Nh3 (eval_cp 311)  
    2. Nf3 (eval_cp 293)  
    3. Ne6 (eval_cp 231)  
  - legal_moves: celkem 41; captures: Nxf7, Qxh6, Rxf7; king_moves: Kf2, Kh1; blocks: []; checks: []  
  - board_state: was_in_check false, checking_pieces [], capture_checking_piece_possible true, king_capture_possible false, king_capture_played false  

[IM] Heisman-style error analýza:  
  - Nejkritičtější chyba byla Bd2 na ply 29 (cp_loss 176 × win_prob_delta 0,162 ≈ 28,5), což je nejvyšší zaznamenaná hodnota v partii.  
  - Tato chyba je poziční (motif None, check False, engine_lines naznačují lepší vývojové tahy jako Nh3, Nf3, Ne6 spíše než taktický úder).  
  - Time trouble: partie se hrála na 600+0 (10 minut každý). Přibližně polovina partie byla odehrána, není žádný přímý důkaz časové tísně; chyba se pravděpodobně nestala kvůli nedostatku času.  

[IM] Tři věci co hráč udělal dobře:  
  1. V zahájení neudělal žádné chyby (ACPL 11,4, 0 chyb).  
  2. V koncovce hrál bezchybně (ACPL 0,0, 0 chyb).  
  3. Přestože udělal jednu významnou chybu ve střední hře, nakonec partii vyhrál.  

[IM] Jedna věc na zlepšení do příště:  
  - Snížit počet pozičních nepřesností ve střední hře, zejména zlepšit volbu tahů jako Bd2 na pozici, kde engine doporučuje aktivnější vývoj koní (Nh3, Nf3, Ne6).  

[IM] Tréninková doporučení (specifická pro nalezené chyby):  
  - Studovat typické plány ve Sicilské obraně Closed/Traditional – zaměřit se na vhodné pozice pro bílého střelce (např. vývoj na e3 nebo f4) a alternativní skoky koní (Nh3, Nf3, Ne6) místo pasivního Bd2.  
  - Řešit poziční cvičení ze sbírek partií s podobnými strukturami (pevný střed, výměna na d4) a procvičovat hodnocení výměn a manévrování figur bez nutnosti taktického úderu.  
  - Hrát partie s delší časovou kontrolou (např. 15+10) a po partii porovnávat své tahy s engine linkami, aby se zvyklo hledat aktivnější možnosti v klidných pozicích.  
  - Pravidelně kontrolovat vlastní partie na výskyt podobných pozičních nepřesností a zapisovat alternativní tahy, které engine považuje za lepší, aby se vytvořil návyk volit je v partii.

---

## Provider Cascade

| # | Provider | Status | Tokens | Cost (USD) |
|---|----------|--------|--------|-----------|
| 1 | NVIDIA | OK | 4380 | 0.0 |