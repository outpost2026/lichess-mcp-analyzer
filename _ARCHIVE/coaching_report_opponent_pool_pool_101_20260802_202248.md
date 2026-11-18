# Coaching Report — opponent_pool (pool_101)

**Generated:** 2026-08-02 20:22 UTC
**Pipeline:** deterministic (Stockfish) + LLM cascade
**Perspective:** OPPONENT (deterministické barvy z anonymous_batch reportu)
**Games analyzed:** 101
**n1 (opponent prohrál):** 86 | **n2 (opponent vyhrál):** 15

---

## Opponent Patterns

| Pattern | Name | Confidence | Frequency | Severity |
|---------|------|------------|-----------|----------|
| O | Stagnační panika | 48.0% | 60 | CRITICAL |
| C | Attention tunneling | 24.0% | 27 | MEDIUM |
| B | Automatic grab | 16.0% | 50 | HIGH |
| R | Endgame relaxation | 11.0% | 14 | HIGH |
| J | Impulsive check block | 10.0% | 11 | HIGH |
| Q2 | Win despite blunder | 6.0% | 7 | LOW |
| Q1 | Desperate Gambit Mode | 4.0% | 5 | LOW |
| Q | Active defense | 3.0% | 3 | LOW |
| N | X-ray pin violation | 3.0% | 4 | HIGH |
| P | Visual misrecognition | 2.0% | 3 | HIGH |

---

## LLM Report

[DATA] Opponent aggregate:
- n1 (proher oponenta) = 86 her, průměrný ACPL = 54.0  
- n2 (výher oponenta) = 15 her, průměrný ACPL = 34.6  
- Blunder rate: n1 = 2,70 blundru/hra, n2 = 2,53 blundru/hra  
- Rozdělení podle fáze hry (opening/middlegame/endgame) není v předložených datech k dispozici → nelze přesně určit.

[DATA] Pattern detection — opponent (všechny patterny jsou z perspektivy oponenta):
| Pattern ID | Pattern name (opponent:) | Frekvence | Severita | Confidence | Poznámka |
|------------|--------------------------|-----------|----------|------------|----------|
| opponent:O | Stagnant panic           | 60        | critical | 48 %       | Nejčastější vzor – hráč vynutí komplikace při rovnoměrném evaluačním plateu. |
| opponent:B | Automatic grab           | 50        | high     | 16 %       | Četné chybné zachyty bez vyhodnocení protihráčovy odpovědi. |
| opponent:C | Attention tunneling      | 27        | medium   | 24 %       | Série po sobě jdoucích chyb naznačuje úzké zaměření na jednu část desky. |
| opponent:R | Endgame relaxation       | 14        | high     | 11 %       | V výherních koncovkách hráč poleví a ztrácí výhodu. |
| opponent:J | Impulsive check block    | 11        | high     | 10 %       | Blok šachu místo úkrytu nebo výměny vede k materiálové ztrátě. |
| opponent:N | X‑ray pin violation      | 4         | high     | 3 %        | Tah odhalí vyšší hodnotu figurky kvůli přehlédnutému pinu. |
| opponent:P | Visual misrecognition    | 3         | high     | 2 %        | Chybné čtení taktiky při výhodné pozici. |
| opponent:Q2| Win despite blunder      | 7         | low      | 6 %        | Hráč dokáže vyhrát i po velké chybě (>300 cp). |
| opponent:Q1| Desperate Gambit Mode    | 5         | low      | 4 %        | Při ztracené pozici hráč odměňuje výměny a vytváří hrozby. |
| opponent:Q | Active defense           | 3         | low      | 3 %        | Aktivní obrana místo pasivní vede k výhře i při materiálovém deficitu. |

*Pattern delta (opponent – author):* autorovy patterny nejsou v datech uvedeny, proto předpokládáme nulovou frekvenci; delta odpovídá frekvenci výše.

[DATA] n1 vs n2 diferenciál:
- ACPL se zlepšil o **19,4 bodů** (54,0 → 34,6) v hrách, kde oponent vyhrál.  
- Blunder rate klesl o **0,17 blundru/hra** (2,70 → 2,53).  
- Konkrétní rozdíly ve fázi hry, typu chyb nebo v konkrétních patternech mezi n1 a n2 nejsou v datech rozvedeny → nelze přesněji specifikovat.

[IM] Co oponenti dělají špatně:
- Nejčastější chyba je **Stagnant panic** (opponent:O) – v 60 z 101 her hráč vynutí komplikace při rovnoměrném evaluačním plateu, což často vede k rychlé ztrátě.  
- Druhá nejčastější je **Automatic grab** (opponent:B) – 50 případů chybného zachytu bez vyhodnocení protihráčovy odpovědi (poměr blunder‑captures / total captures = 0,081).  
- Třetí je **Attention tunneling** (opponent:C) – série po sobě jdoucích chyb naznačuje úzké zaměření na jednu oblast desky.  
- V koncovkách se projevuje **Endgame relaxation** (opponent:R) – hráč poleví, když je materiálně nahoře, a ztrácí výhodu.  
- Další systematické slabiny: přehlížení **X‑ray pinů** (opponent:N), **vizualní chybné rozpoznání** (opponent:P) a impulzivní **blok šachu** (opponent:J).  

[IM] Exploitable patterns:
- Oponent často chytá materiál bez vyhodnocení protihráčovy odpovědi → lze připravit pasti, kde se zdánlivě volný materiál skrývá objevený útok nebo protiútok.  
- V pozicích s dlouhým rovnoměrným evaluačním plateu (méně než 30 cp posun na 3+ tahy) oponent často propadne panice a vynutí rizikové pokračování → v takových pozicích lze zvýšit tlak a čekat na jeho nepřesný tah.  
- Oponent má tendenci k **attention tunneling** → při vytváření více současných hrozeb (např. dvojitý útok, křížová šachová hrozba) je pravděpodobné, že přehlédne jednu z nich.  
- V výherních koncovkách oponent často poleví → lze udržet napětí i při materiální výhodě a čekat na nepřesnost.  
- Časté přehlížení **X‑ray pinů** a **vizualních iluzí** naznačuje, že kombinace s pinem nebo zdánlivě nuceným obětováním může být účinná.  

[IM] Countermeasures (co dělat my – autor – pro maximalizaci chyb oponenta):
- V openingové fázi usilujte o pozice s rovnoměrným evaluačním po delší dobu (např. uzavřené struktury, symetrické struktury), aby se zvýšila pravděpodobnost spuštění patternu **Stagnant panic**.  
- Po každém svém tahu, který vypadá jako volný materiál, připravte skrytý protiútok (objevený útok, šach, nebo past na král) – tím využijete vzor **Automatic grab**.  
- Vytvářejte více současných hrozeb (např. dvojútok, křížová šachová hrozba, hrozba na více frontách) – to zatíží **Attention tunneling** a zvyšuje šanci na přehlédnutí jedné z nich.  
- V koncovkách, kdy jste materiálně nahoře, udržujte aktivitu a neumožněte soupeři „odpočinout“ – tím potlačíte **Endgame relaxation**.  
- Hledejte pozice, kde je vaše figura X‑ray připnutá k vyšší hodnotě figurky soupeře – při tahu soupeře tuto pinovou vazbu využijte k zisku materiálu.  
- Používejte taktické sekvence, které vypadají jako nucené (např. obětování figury s následným šachem), ale ve skutečnosti mají alternativní obranu – tím prověříte **Visual misrecognition** a **Impulsive check block**.  

[IM] n2 study — co funguje (15 her, kde oponent vyhrál):
- V těchto hrách oponent dosáhl nižšího ACPL (34,6 proti 54,0) a mírně nižší blunder rate (2,53 vs 2,70/hra).  
- Konkrétní chování, které vedlo k tomuto zlepšení (např. méně časté automatické zachyty, lepší zvládnutí rovnoměrných pozic, větší obezřetnost v koncovkách) není v datech rozvedeno → nelze určit, které konkrétní změny byly rozhodující.  
- Z důvodu nízkého počtu her (n2 = 15) je jakákoliv statistika o n2 pouze indikativní, ne průkazná; jakékoliv závěry o tom, „co funguje“, je třeba brát s rezervou a ověřovat dalším vzorkem her.

---

## Provider Cascade

| 1 | NVIDIA | OK |