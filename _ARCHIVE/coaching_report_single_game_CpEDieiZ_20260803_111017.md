# Coaching Report — single_game (CpEDieiZ)

**Generated:** 2026-08-03 11:10 UTC
**Pipeline:** deterministic (Stockfish) + LLM cascade
**LLM provider:** NVIDIA

---

*No patterns detected.*

---

## LLM Report

[DATA] Základní info: Výsledek 1-0, barva white, zahájení Sicilian Defense: Smith-Morra Gambit Accepted, celková ACPL 72,0.  
[DATA] Fazovy breakdown:  
  - Opening: ACPL 32,2, 2 chyb.  
  - Middlegame: ACPL 102,5, 6 chyb.  
  - Endgame: data nejsou k dispozici.  
[DATA] Error klasifikace:  
  - Blunders: ply 45, tah Qh4, ztráta 936 cp, fáze middlegame.  
  - Mistakes: žádné.  
  - Inaccuracies: 7.  
[DATA] Pattern detection výsledky pro tuto hru: žádné patterny detekovány.  
[DATA] BlunderFactSheet (ply 45, Qh4):  
  - engine_lines top3:  
    1. Qh4, eval_cp 259, win_prob 0,8162  
    2. Qh4, eval_cp 466, win_prob 0,9360  
    3. Qh4, eval_cp 496, win_prob 0,9456  
  - legal_moves: celkem 37; captures: Qxf7+, Bxh7+; king_moves: Kh1; blocks: žádné; checks: Qxf7+, Bxh7+.  
  - board_state: was_in_check false; checking_pieces prázdné; capture_checking_piece_possible true; king_capture_possible false; king_capture_played false.  

[IM] Heisman-style error analýza:  
  - Nejkritičtější chyba byla blunder Qh4 v ply 45 se ztrátou 936 cp v middlegame.  
  - Podle dostupných dat se jedná o taktickou příležitost (v pozici byly dostupné šachové a zachytávací tahy Qxf7+ a Bxh7+, které hráč nezahrál).  
  - Informace o časové tísni nejsou k dispozici.  
[IM] Tři věci co hráč udělal dobře:  
  - Vyhrál hru (výsledek 1-0).  
  - V opening fázi udržel nízkou ACPL (32,2) a pouze 2 chyb.  
  - Před blunderem měl výraznou výhodu (eval_before 1032 cp, win_prob_before ~0,997).  
[IM] Jedna věc na zlepšení do příště:  
  - V middlegame věnovat větší pozornost taktickým možnostem, zejména šachům a zachytávkám (např. Qxf7+ nebo Bxh7+), aby se vyhnul velkým ztrátám materiálu.  
[IM] Tréninková doporučení:  
  - Pravidelně řešit taktické hádanky zaměřené na identifikaci šachů a zachytávok v střední hře.  
  - Studovat typické pozice a plány v Smith-Morra Gambitu (obě strany) aby se lépe rozeznávaly kritické okamžiky.  
  - Po partiích provádět rozbor s enginem a porovnávat své tahy s nejlepšími liniemi, zvláště v middlegame, aby se zachytily přehlédnuté taktické hrozby.

---

## Provider Cascade

| # | Provider | Status | Tokens | Cost (USD) |
|---|----------|--------|--------|-----------|
| 1 | NVIDIA | OK | 3829 | 0.0 |