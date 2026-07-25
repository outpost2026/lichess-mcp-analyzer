# Lichess Analyzer MCP — User Guide

Cil: aby nekdo, kdo nevi, jak presne MCP tooly funguji, dokazal pomoci tohoto serveru analyzovat sve sachove partie.

Nemas vedet, ze existuje neco jako `lichess\_diagnose\_player`. Staci, ze vis, co chces vedet.


## Jak to funguje

Pises do chatu (opencode) prirozene otazky. AI za tebou vola MCP tooly, ktere:

1. Stahnou partie z Lichess

2. Analyzuji je Stockfishem (lokalni engine)

3. Detekuji vzorove chyby (pattern library A-Q1)

4. Diagnostikuji fazove slabiny

5. Vraci vysledky do chatu


## Priklady — co pises a co se stane

### "Kdo je outpost2026?"

Staci napsat:

> Zjisti profil hrace outpost2026, stahni jeho poslednich 5 partii a analyzuj je. Zajima me: jake ma ratingy, jake zahajeni hraje, jaka je jeho prumerna ACPL a kde dela nejvic chyb.

AI za tebou:

1. Zavola `lichess\_player\_profile("outpost2026")` — ratingy, pocet her

2. Zavola `lichess\_fetch\_games("outpost2026", 5)` — seznam partii

3. Pro kazdou partii zavola `lichess\_analyze\_game(id, username="outpost2026")`

4. Sestavi souhrn


### "Proc jsem prohral?"

> Analyzuj partii [https://lichess.org/abc12345](https://lichess.org/abc12345). Hral jsem bilymi. Kde jsem udelal nejvetsi chyby? Kdy jsem mel sanci vyhrat?

AI:

1. Ziska game ID z URL (`abc12345`)

2. Zavola `lichess\_analyze\_game("abc12345", username="outpost2026", depth=18)`

3. Vrati: ACPL 62.3, blunder v 28. tahu (Nxe5, ztrata 450cp), missed win v 22. tahu (Bxf7+)


### "Srovnej me se souperem"

> Stahni 5 partii hrace `souper123` a 5 partii `outpost2026`. Kdo ma nizsi ACPL? Jake maji rozdily ve fazove slabine? Kdo dela vic blunderu v koncovce?

AI:

1. Zavola `lichess\_fetch\_games("souper123", 5)` a `lichess\_fetch\_games("outpost2026", 5)`

2. Analyzuje kazdou partii

3. `lichess\_diagnose\_player` pro oba (vyuzije cache z analyzy)

4. Vrati srovnani: outpost2026 ma ACPL 55, souper123 ma ACPL 82. Rozdil je hlavne v middle game (45 vs 98).


### "Co mam trenovat?"

> Analyzuj mych poslednich 20 her, proved diagnostiku slabin a pattern detection. Chci priorizovany seznam: co resit jako prvni, druhe, treti. A konkretni cviceni.

AI:

1. `lichess\_fetch\_games("outpost2026", 20)`

2. `lichess\_analyze\_game(...)` na kazdou (pokud uz nejsou v cache)

3. `lichess\_diagnose\_player("outpost2026", 20)` — fazove slabiny, leaky otvoreni

4. `lichess\_match\_patterns("outpost2026", 20)` — vzorove chyby A-Q1

5. Vrati report:

   - **1. resit:** pattern B (Automatic grab), conf 85% — delas neuvazene brane. Reseni: 3s pauza pred kazdym branim.

   - **2. resit:** koncovka ACPL 95 — chybi ti praxe. Reseni: 10 koncovek denne.

   - **3. resit:** Sicilksa obrana (1.e4 c5) — prohravas v 60% partii. Reseni: prestudovat main lines.


### "Importuj partii z jinyho serveru"

> Tuhle partii jsem hral na Chess.com. Importuj ji a analyzuj:

```
\[Event "Chess.com"\]  
\[Site "Chess.com"\]  
\[White "outpost2026"\]  
\[Black "souper"\]  
\[Result "0-1"\]  
...
```

AI:

1. Zavola `lichess\_import\_pgn(pgn="...", color="white")`

2. Analyza projde stejnym pipeline jako lichess partie

3. Vrati kompletni analyzu (kazdy tah, cp\_loss, klasifikace)


### "Analyza pozice — co ted hrat?"

> Mam na desce r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4. Co mam hrat? Dej mi top 3 tahy a hlavni variantu na 5 tahu.

AI:

1. Zavola `lichess\_analyze\_position(fen="...", depth=20)`

2. Vrati: 1. Bxc6 (sance 45%), 2. 0-0 (32%), 3. d3 (23%)


### "Co hrajou souperi v mem otvoreni?"

> Zjisti statistiku otevreni z teble pozice: "rnbqkb1r/pppp1ppp/5n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq - 2 3". Co nejcasteji hraji? Jake maji winrate?

AI:

1. Zavola `lichess\_opening\_explorer(fen="...", source="lichess")`

2. Vrati: d5 (42% her, 52% white), d6 (28%, 55% white), Be7 (12%, 48% white)


## Dulezite: jak to optimalizovat

**Cachovani:** Kdyz uz jednou analyzujes partii, dalsi diagnozy a pattern detection probehnou instantne (pouziji cached vysledky).

Dobre:

> Analyzuj 20 partii a proved kompletni diagnostiku.

Zbytecne:

> Analyzuj 20 partii. ... Ted proved diagnostiku. ... A ted pattern detection.

(Tech druhejch dvou se pta najednou — AI pouzije cache.)

**Ruzna hloubka:** Analyza jedne partie (depth 18 je presnejsi, depth 14 je 4x rychlejsi. Pro diagnostiku pres 20 her staci depth 12. Pro konkretni blunder v konkretni partii pouzij depth 18.


## Toolbox (pro zvidave)

Kdyz chces presne vedet, co mas k dispozici:

| Chces-li | Pouzij |
| - | - |
| Stahnout partie | `lichess\_fetch\_games` |
| Analyzovat partii | `lichess\_analyze\_game` |
| Analyzovat pozici | `lichess\_analyze\_position` |
| Statistika otvoreni | `lichess\_opening\_explorer` |
| Profil hrace | `lichess\_player\_profile` |
| Diagnostika slabin | `lichess\_diagnose\_player` |
| Pattern detection | `lichess\_match\_patterns` |
| Workspace info | `lichess\_workspace\_info` |
| Import PGN | `lichess\_import\_pgn` |


Ale nemusis si to pamatovat. Staci rict, co chces.


## Appendix — Co se chysta

V dalsich fazich pribude:

- **FSRS karty** — blunder se stane treninkovou kartou, system ti ji predhodi k opakovani za 1 den, 3 dny, 7 dni

- **Nove patterny** — detektory C, D, E, F, H, I, J, K, L, M, N, Q1 (ted je 7 z 18)

- **LLM coaching report** — AI ti napise treninkovy plan na tyden v MD souboru

- **Sledovani progresu** — kazdy tyden stejna diagnostika, vidis, jestli se ACPL snizuje

- **Automaticke timeouty** — kdyz Stockfish zamrzne, server to odchyti

- **Health check** — overeni, ze Lichess API, Stockfish a LLM provideri funguji


*Generovano: 2026-07-22*

