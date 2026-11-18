# Coaching Report — opponent_pool (pool_101)

**Generated:** 2026-08-02 18:52 UTC
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
- Blunder rate: n1 = 2,70 chyb/hra, n2 = 2,53 chyb/hra
- Rozdělení podle fáze hry (opening/middlegame/endgame) není v předložených datech k dispozici.

[DATA] Pattern detection — opponent:
Seznam detekovaných patternů (opponent perspektiva) seřazený podle frekvence a závažnosti:

| Pattern ID | Pattern name (opponent:) | Confidence | Frequency | Severity | Poznámka |
|------------|--------------------------|------------|-----------|----------|----------|
| opponent:O | Stagnant panic           | 48,0 %     | 60        | critical | Flat eval plateau → nucená prohrávající tah do 6 tahů |
| opponent:B | Automatic grab           | 16,0 %     | 50        | high     | Automatické braní bez hodnocení protihráčovy odpovědi |
| opponent:C | Attention tunneling      | 24,0 %     | 27        | medium   | Více po sobě jdoucích chyb → výpadek pozornosti |
| opponent:R | Endgame relaxation       | 11,0 %     | 14        | high     | Vítězné koncovky → pasivní tahy, ztráta výhody |
| opponent:J | Impulsive check block    | 10,0 %     | 11        | high     | Blokování šachu místo úniku/výměny → materiálová ztráta |
| opponent:N | X‑ray pin violation      | 3,0 %      | 4         | high     | Tah figurou, která je x‑ray připnutá k vyšší hodnotě |
| opponent:P | Visual misrecognition    | 2,0 %      | 3         | high     | Špatné čtení taktiky s výhodou → přehlédnutí protihráčovy hrozby |
| opponent:Q2| Win despite blunder      | 6,0 %      | 7         | low      | Výhra i po velké chybě (>300 cp) |
| opponent:Q1| Desperate Gambit Mode    | 4,0 %      | 5         | low      | V prohrané pozici odměna výměn, aktivní hra → výhra |
| opponent:Q | Active defense           | 3,0 %      | 3         | low      | Aktivní obrana při materiálovém deficitu → výhra |

Protože v datech autorovy perspektivy nejsou zaznamenány žádné patterny (author perspective patterns = []), je frekvence autorových patternů rovna 0. Proto pattern delta (opponent – author) odpovídá výše uvedené frekvenci opponent patternů.

[DATA] n1 vs n2 diferenciál:
- ACPL se zlepšil o 19,4 bodů (54,0 → 34,6) v hrách, kde oponent vyhrál.
- Blunder rate se snížil o 0,17 chyb/hry (2,70 → 2,53) ve vítězných hrách.
- Konkrétní rozdíly ve frekvenci jednotlivých patternů mezi n1 a n2 nejsou v datech uvedeny, proto nelze tvrdit, které patterny se konkrétně snížily nebo zvýšily.

[IM] Co oponenti dělají špatně:
- Nejčastější typ chyby je **psychologicko‑pozicní** – pattern **opponent:O (Stagnant panic)** se vyskytuje v 60 z 101 her (≈59 %) a je označen jako critical. Naznačuje, že při dlouhodobě rovnoměrné evaluaci (flat eval plateau) oponent často propadne panice a vynutí si zhoršující tah.
- Druhá nejčastější chyba je **taktická** – pattern **opponent:B (Automatic grab)** se objevuje v 50 hrách (≈50 %) a má high severity. Oponent často bere materiál bez kontroly protihráčovy odpovědi (objeví se objevený útok, přehlédnutá hrozba atd.).
- Třetí významná oblast je **porucha pozornosti** – pattern **opponent:C (Attention tunneling)** v 27 hrách (≈27 %) signalizuje, že po sérii chyb oponent ztrácí globální přehled a opravuje jednu chybu tím, že vytvoří další.
- V koncovkách s materiální výhodou se projevuje pattern **opponent:R (Endgame relaxation)** (14 her, high), kdy oponent snižuje koncentraci a dělá pasivní tahy, které ztrácejí výhodu.
- Další taktické slepé body zahrnují impulzivní blok šachu (opponent:J), přehlédnuté x‑ray připnutí (opponent:N) a vizuální chybu při čtení složitých výměn (opponent:P).

Celkově lze říci, že oponenti systematicky selhávají v situacích s nízkou napětím (flat eval) a v okamžicích, kdy mají materiální výhodu – buď propadají panice, nebo příliš rychle využívají příležitost k braní bez hlubší analýzy.

[IM] Exploitable patterns:
- **Vytvoření rovnoměrné pozice** (např. uzavřená struktura s výměnami) může vyvolat flat eval plateau a tím spustit pattern **opponent:O** – oponent pak často vynutí si riskantní pokračování do 6 tahů.
- **Nastavení taktických pastí**, kde je materiál zdánlivě volný (např. nabídnutí pěšce s skrytým objeveným útokem), zvyšuje šanci, že oponent spustí pattern **opponent:B** (automatické braní).
- **Opakované šachy** nebo hrozby šachu v krátkém sledu mohou vyvolat pattern **opponent:J** (impulsivní blok), protože oponent často blokuje místo úniku nebo výměny.
- **Výhoda v koncovce** (např. věžová koncovka s pěšcem navíc) může aktivovat pattern **opponent:R** – oponent má tendenci „odpočinout“ a hrát pasivně, což dává příležitost k přesnému technickému postupu.
- **Komplikované výměnové sekvence** s více kusy (např. obětování kvality za iniciativu) mohou způsobit pattern **opponent:P** (vizualní chyba), protože oponent často přehlédne skrytou protihráčovu hrozbu.

[IM] Countermeasures:
- V **openingu** usilujte o pozice s malým napětím a rovnoměrnou strukturou (např. symetrické struktury, výměny centrálních pěšců), aby se zvýšila pravděpodobnost výskytu flat eval plateau a tím i patternu **opponent:O**.
- Po dosažení rovnoměrné pozice **nechte soupeře na tahu** a pozorujte, zda začne vynucovat komplikace – pokud ano, připravte přesné protihráčovy odpovědi (např. mezihra, která trestá nucený tah).
- V **middlegame** vytvářejte zdánlivě volné materiální nabídky (např. nabídnutí pěšce s skrytým objeveným útokem na královou linii) – to aktivuje pattern **opponent:B**. Po přijetí nabídky okamžitě zahajte kombinaci, která využívá přehlédnutou hrozbu.
- Pokud získáte materiální výhodu, **udržujte tlak** (např. aktivní figurální hrozby, neumožňujte soupeři jednoduché výměny), aby se omezila šance na pattern **opponent:R** (endgame relaxation).
- V situacích šachu **nabízejte více možností bloku** (např. šach jezdeckým skokem, kde blokování vede k ztrátě figury) – to zvyšuje pravděpodobnost, že souvolí pattern **opponent:J** (impulsivní blok) a vy získáte materiál.
- Pro trénink vizuální přesnosti používejte cvičení na rozpoznání x‑ray připnutí a složitých výměn – to přímo čelí patternům **opponent:N** a **opponent:P**.

[IM] n2 study — co funguje:
- V 15 hrách, kde oponent vyhrál (n2), byl průměrný ACPL **34,6** a blunder rate **2,53/hra**, což je výrazné zlepšení oproti prohraným hrám (ACPL 54,0, blunder rate 2,70).
- Tato data naznačují, že vítězných her se oponent **méně často dopouštěl velkých chyb** a **lépe udržoval koncentraci** po celou partii.
- Konkrétní změny ve frekvenci jednotlivých patternů mezi n1 a n2 nejsou v datech uvedeny, proto nelze tvrdit, které konkrétní návyky se změnily; nicméně nižší ACPL a nižší blunder rate naznačují celkově **lepší rozhodování**, méně panických reakcí (opatření proti patternu **opponent:O**) a přesnější taktické hodnocení (méně výskytů patternů **opponent:B**, **opponent:J**, **opponent:N**, **opponent:P**).
- Tyto indicie naznačují, že pokud se podaří oponenta dostat do situací, kde musí přemýšlet nad rovnoměrnou pozicí nebo kde je vystaven taktickým pastím, jeho šance na chybu rostou – což je přesně to, co lze využít v přípravě proti němu.

---

## Provider Cascade

| 1 | NVIDIA | OK |