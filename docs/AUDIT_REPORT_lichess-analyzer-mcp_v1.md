# Nezávislý audit — lichess-analyzer-mcp v0.1.0

**Auditor:** Claude (Anthropic) — cross-LLM audit, de novo
**Datum:** 2026-07-24
**Zdroj:** DIGITAL_TWIN_v1.0.md (kompletní disekce, bez přístupu ke skutečnému zdrojovému kódu)
**Metodologická poznámka:** Tento audit vychází výhradně z popisu v digital twinu. Nejde o statickou analýzu skutečného kódu (ten jsem neviděl) — jde o architektonický a logický review specifikace chování systému tak, jak je zdokumentována. Tam, kde závěr závisí na detailu, který twin neuvádí (přesné pořadí řádků kódu, konkrétní implementace regexů apod.), to explicitně označuji jako předpoklad.

---

## Section 1: Executive Summary

Systém je funkčně bohatý prototyp (9 nástrojů, 11 detektorů vzorů, 3-poskytovatelová LLM kaskáda, 4vrstvá cache) postavený rychlým tempem jedním vývojářem. Architektura je čitelná a dobře vrstvená (tools → services → models), ale nese typické stopy v0.1.0 softwaru: univerzální `{"error": str(e)}` handling, netestované edge-case aritmetiky (zejména v `evaluate_move`), heuristické pattern-detektory bez statistické validace a bezpečnostní mezery typické pro lokální nástroj, který nebyl navržen s vědomím, že bude vystaven autonomnímu LLM agentovi. Nejzávažnější riziko není žádná jednotlivá chyba, ale to, že celá pipeline nemá vrstvu, která by explicitně komunikovala nejistotu výsledků (Stockfish confidence, cache staleness, low-sample pattern matches) směrem k LLM agentovi, který na datech staví koučovací doporučení.

- **Nálezy dle závažnosti:** Critical: 2 | Major: 5 | Minor: 6 | Info: 4
- **Odhadovaná úroveň zralosti:** 4/10 (funkční proof-of-concept s reálnou hodnotou, ale bez production hardeningu)

---

## Section 2: Architecture Assessment

**Modulární separace:** Rozdělení `tools/ → services/ → models/ → resources/` je čisté a konvenční pro MCP servery. Tools jsou tenké wrappery (správně — obsahují jen argument validaci a volání služby), veškerá logika žije v `services/`. To je zdravý vzor. Mírná výjimka: `kb/` modul (schemas, writer, md_reporter) má nejasnou roli — je importován, ale dle poznámky v promptu jeho užití je "omezené na validaci". To naznačuje buď neúplnou integraci, nebo mrtvý kód (viz Section 8, kb/ modul).

**Data flow:** Pipeline je převážně lineární a kompozitní (T6/T7 skládají T1+T2 do agregace), bez cyklických závislostí — services na sebe nevolají navzájem kruhově, volání jde vždy směrem tools→services→(engine/API). Jediné tangle-riziko je v `pattern_detector.py`: 11 nezávislých detektorů běží nad stejnou sadou `GameAnalysis` bez sdíleného kontextu ("no cross-detector communication, no state persists"). To je architektonicky čisté (žádné vedlejší efekty), ale prakticky to znamená, že detektory se mohou navzájem kontradiktorně "přetahovat" o stejná data (např. pattern O "repetition avoidance greed" a pattern R "endgame relaxation" mohou klasifikovat tutéž sekvenci tahů odlišně), aniž by o tom systém věděl.

**MCP compliance:** Server používá Tools i Resources korektně — L2 Resources (`lichess://analysis/{key}`, `lichess://patterns/{key}`) jsou vhodné pro perzistentní, adresovatelné výstupy, zatímco Tools vrací přímé odpovědi. Chybí ale využití MCP **Progress** notifikací — u operací jako T6/T7 (20 her × Stockfish analýza při hloubce 12-18) může běh trvat desítky sekund až minuty bez jakékoli zpětné vazby klientovi, což je anti-pattern pro dlouho běžící MCP tooly. Také chybí **Prompts** primitivy — coaching prompt template v `llm_client.py` je natvrdo v kódu služby, zatímco MCP specifikace nabízí `@app.prompt()` právě pro tento účel (umožnilo by to klientovi/uživateli šablonu vidět a upravovat). Sampling capability (LLM by mohl žádat MCP klienta o dokončení namísto vlastní HTTP kaskády) není využita vůbec — server implementuje vlastní paralelní LLM klienta místo delegace na `sampling/createMessage`, což je legitimní volba, ale znamená to, že server nese vlastní API klíče a náklady místo přenesení této odpovědnosti na hostitelského klienta.

**Extensibilita:** Přidání nového tool je snadné (kopie existujícího tenkého wrapperu + `@app.tool()`). Přidání nového pattern detektoru vyžaduje: (1) novou `PatternDef` v `load_baseline()`, (2) metodu `_detect_{id}()` konvencí name-mangling přes `getattr` — to je fragilní vzor (typo v ID rozbije lookup tiše, žádná chyba za běhu, detektor se prostě nikdy nespustí). Přidání cache vrstvy by vyžadovalo úpravy na více místech najednou (game_analyzer.py pro L2, lichess_client.py pro L0/L1) — cache logika není abstrahována do společného rozhraní, každá vrstva má vlastní ad-hoc implementaci s podobným, ale ne identickým kódem (TTL vs. content-hash vs. no-TTL).

---

## Section 3: Correctness Analysis

**Data acquisition (`lichess_client.py`):** Retry logika `sleep(2^(attempt+1))` na HTTP 429 je rozumná, ale kontrola `"429" in str(e)` a `"404" in str(e)` je string-matching na text výjimky, nikoli na status kód — pokud `berserk`/`httpx` mění formát chybové zprávy mezi verzemi, tato detekce potichu selže a přejde do větve `raise`, což změní chování (žádný retry, žádný graceful empty list) bez zjevné příčiny. Toto je křehké a mělo by testovat `e.response.status_code` pokud je dostupné.

**Stockfish analýza — korektnost perspektivy v `evaluate_move`:** Toto je nejdůležitější technický detail k prověření. Podle popisu:
```
best_player = -best_score   # negace pozice PO tahu best_move (kde je na tahu soupeř)
actual_player = -actual_score  # negace pozice PO skutečném tahu (kde je na tahu soupeř)
cp_loss = max(0, best_player - actual_player)
```
Logika negace je **koncepčně správná** — `score.relative` je vždy z pohledu hráče na tahu v dané pozici, a jelikož po tahu hráče je na tahu soupeř, je nutné skóre negovat zpět na perspektivu původního hráče. Nicméně zde je riziko: `eval_before` (skóre PŘED tahem, tj. `info_before["score"].relative.score()`) **není** negováno, protože je to skóre z pohledu hráče, který se chystá táhnout — to je konzistentní. Otázka, kterou twin nezodpovídá: je `eval_before` a `eval_after` v `MoveAnalysis` ukládáno konzistentně ve stejné perspektivě (vždy "hráč na tahu" nebo vždy "bílý")? Pokud se perspektiva mění řádek od řádku (jednou "hráč", jednou "bílý"), downstream agregace v `diagnostician.py` (phase_stats, ACPL per phase) by mohly tiše mísit znaménka. **Doporučuji explicitní unit test**, který ověří `cp_loss` na známé pozici s ručně spočítaným Stockfish výstupem pro obě barvy.

**Mate scóre edge case:** `info_before["score"].relative.score()` vrací `None`, pokud je na desce mat/matový vektor (python-chess `PovScore.score()` vrací `None` pro `Mate` skóre, pokud není předán `mate_score` parametr). Twin neuvádí, že by `evaluate_move()` explicitně řešil `mate_in` větev — pokud kód volá `.score()` bez `mate_score=...`, `eval_before`/`eval_after` mohou být `None`, což by způsobilo `TypeError` při `best_player - actual_player` (odečítání `None`). To je pravděpodobný **Critical bug** v jakékoliv hře, kde je ve variantě engine mat.

**Cache depth aproximace:** `_load_cached_analysis` bere "glob {id}_{color}_d*.json → take highest depth" — to je rozumné (vyšší hloubka je vždy alespoň tak přesná jako nižší), ale znamená to, že pokud uživatel zavolá analýzu s `depth=14` a v cache je uložený výsledek s `depth=24`, vrátí se `depth=24` výsledek beze změny — funkce **nikdy nevrátí přesně požadovanou hloubku**, což může matoucím způsobem měnit reprodukovatelnost (dva volání se stejným `depth=14` argumentem mohou vracet různé ACPL, pokud mezitím proběhla hlubší analýza). To by mělo být zdokumentováno v návratové hodnotě (např. pole `actual_depth_used`).

**Klasifikační prahy:** Standardní chess.com/lichess-like thresholdy (300/150/50/20 cp) jsou rozumné aproximace, ale jsou **necitlivé na fázi hry a eval magnitude** — ztráta 300cp v pozici, kde je hráč již -800cp (prohraná pozice), je kvalitativně jiná chyba než 300cp ztráta v vyrovnané pozici. Systém to nerozlišuje (kromě patternu Q "Active defense", který je specifický pro tento kontext, ale není to obecná korekce klasifikace).

**Pattern detection — heuristiky:** Většina detektorů má rozumnou logiku, ale trpí malými vzorky a metodologicky slabou "confidence" metrikou:
- **Pattern A/G** (anonymous effect, color asymmetry): poměrové prahy (1.3x, 1.4x) nad malým počtem her (min 3) mají velký rozptyl — s 3-5 hrami je poměr blunder rate snadno zkreslen jednou hrou. Žádná zmínka o statistické signifikanci (např. binomický test) — confidence je čistě odvozena z poměru, ne z pravděpodobnosti, že jev je náhodný.
- **Pattern O** ("repetition avoidance greed", severity critical, min_games=3): confidence je **hardcoded na 0.6** bez ohledu na počet nalezených instancí — to je podezřelé, protože všechny ostatní detektory škálují confidence s frekvencí/poměrem. Fixní confidence u nejzávažnějšího patternu je nekonzistentní designové rozhodnutí.
- **False positive potenciál:** Pattern J ("impulsive check block" — blunder/mistake obsahující `+`/`#` v SAN) bude mít vysokou false-positive míru, protože šach/mat je v mnoha silných tazích přítomen běžně; korelace "blunder measured AND move gives check" neimplikuje kauzální "impulzivitu" — je to slabá proxy.

**Diagnostician — hardcoded pravidla:** Pravidlo "pokud middlegame blunders > opening+endgame" nezohledňuje **počet tahů v každé fázi** (middlegame typicky obsahuje výrazně více tahů než opening, takže absolutní počet chyb bude přirozeně vyšší i bez skutečné slabiny) — mělo by být normalizováno na per-move rate, ne na absolutní count. To je pravděpodobně systematicky zkreslené pravidlo, ne edge-case bug.

---

## Section 4: Security & Threat Model

**Token leakage:** `.env` je čten do `os.environ` a health-check tiskne "found keys" do stderr — pokud tisk zahrnuje jen *přítomnost* klíče (boolean), je to bezpečné; pokud by omylem vypsal hodnotu (i částečnou), jde o leak do logů/konzole. Twin uvádí "print found keys" — nejednoznačné, zda jde o názvy proměnných nebo hodnoty. **Doporučení: ověřit, že se loguje jen `{provider}: configured` bez hodnoty tokenu.** Dále: `.env` obsahuje `LICHESS_TOKEN` (read-only token dle poznámky, což je dobré) i tři placené/free LLM API klíče v plaintextu bez `.gitignore` zmínky v twinu — pokud repozitář (`outpost2026`) je nebo bude veřejný na GitHubu, real riziko commitnutí `.env` je vysoké. Toto je nejčastější reálná příčina úniku klíčů u sólo vývojářů.

**SSRF / path traversal:** `fen: str` a `pgn: str` argumenty jdou přímo do `python-chess` parseru — pokud `chess.pgn.read_game()` nebo FEN parser striktně validují formát (což standardně dělají), injection risk je nízký. Reálnější riziko: `game_id` a `username` se používají přímo ve **jménech souborů** (`{game_id}_{color}_d{depth}.json`, `{username}_games.json`). Twin neuvádí žádnou sanitizaci těchto řetězců před použitím jako cesty k souboru. Pokud `username` nebo `game_id` pochází z argumentu volaného LLM agentem (a agent je řízen třetí stranou nebo halucinuje), hodnota jako `../../../etc/passwd` nebo obsahující `..\` by teoreticky mohla vést k **path traversal při zápisu cache souboru** — záleží na tom, zda Lichess username/game_id validace probíhá před sestavením cesty. Toto je nejkonkrétnější a nejsnáze opravitelný bezpečnostní nález (viz F2 níže).

**Resource exhaustion:** Toto je reálné a systémové riziko:
- Stockfish je compute-bound; s `depth` až 24 a `max_games` až 50 (T6/T7), teoretický worst-case je 50 her × ~desítky tahů × hluboká analýza = řádově desítky minut CPU jedním voláním nástroje. LLM agent (např. autonomní smyčka) může snadno spustit více takových volání za sebou nebo paralelně (pokud FastMCP transport umožňuje souběžná volání) — bez rate limitingu na úrovni MCP tool to je snadný self-inflicted DoS na lokální stroj.
- Threading lock s 120s timeoutem **serializuje veškerou Stockfish práci** napříč všemi současně běžícími tool voláními (viz Section 5) — to paradoxně *chrání* proti resource exhaustion (jen jedna analýza běží najednou), ale za cenu, že souběžní klienti čekají v řadě až 2 minuty, než dostanou zombie-recovery.
- LLM kaskáda: DeepSeek fallback je placený ($0.14/$0.28 na 1M tokenů) — bez per-user/per-session rate limitu nebo budget capu by opakovaná volání T6/T7 s LLM cascade mohly generovat neomezené náklady, pokud NVIDIA/Cerebras free tier vyprší nebo selže (fallback na placený tier proběhne automaticky a tiše).

**Input validace:** `depth` a `max_games` mají explicitní rozsahy (dobré). `fen`/`pgn` se spoléhají na parser knihovny (přiměřené). `username`/`game_id`/`color`/`source` **nejsou explicitně validovány proti enum hodnotám** v popisu (kromě `source` a `color`, kde twin zmiňuje "must be" — nejasné, zda je to vynucováno kódem nebo jen dokumentací tool signatury). Pokud `color` není striktně `"white"|"black"`, `evaluate_move`/`phase` logika by mohla selhat nečekaně.

**Denial of service — extrémní parametry:** `depth=24` + `max_games=50` na T6/T7 je legitimní vstup dle deklarovaného rozsahu, ale ekonomicky/výpočetně nejdražší možná kombinace. Server nemá zjevný guard proti kombinaci vysoký-depth × vysoký-max_games (např. omezení součinu, nebo varování). To je jednoduchá a levná ochrana k přidání.

---

## Section 5: Performance Evaluation

**Stockfish bottleneck:** Při ~3.5s/hra (dle poznámky v promptu, hloubka ~16) by batch analýza 50 her trvala řádově ~3 minuty čistého Stockfish času — to je zvládnutelné pro dávkový skript (`batch_analyze_all.py`), ale **nepřijatelné pro interaktivní MCP tool call**, kde LLM agent očekává odpověď v řádu sekund. T6/T7 s `max_games=50` bez cache by tedy typicky way přesáhly rozumný timeout MCP klienta (pokud existuje) a bez Progress notifikací (viz Section 2) klient nemá signál, že se něco děje.

**Cache efektivita:** L0/L1/L2 cache výrazně sníží latenci u opakovaných dotazů — ale L2 depth-aproximace (Section 3) znamená, že *první* volání s vyšší hloubkou "znečistí" cache pro všechna budoucí volání s nižší hloubkou (což je funkčně v pořádku pro přesnost, ale matoucí pro reprodukovatelnost a benchmarking výkonu — testeři si mohou myslet, že jejich `depth=12` volání je rychlé díky cache, zatímco ve skutečnosti dostávají starý `depth=18` výsledek).

**Analysis lock — vliv na souběžnost:** Ano, jednoduchý globální `threading.Lock` **plně serializuje veškerou Stockfish analýzu** napříč všemi tool voláními, bez ohledu na to, kolik MCP klientů/agentů je připojeno. To je záměrně bezpečné (jeden proces enginu, žádné race conditions v UCI komunikaci), ale prakticky to znamená, že server je **single-tenant** ve výkonu, i kdyby MCP transport teoreticky podporoval více souběžných volajících. 120s timeout + zombie recovery je rozumná pojistka proti deadlocku, ale restart enginu uprostřed něčí analýzy pravděpodobně způsobí, že **čekající volání dostane chybu nebo neúplný výsledek** — twin neuvádí, jak se in-flight analýza chová při force-restartu (ztratí se, nebo se zopakuje na nový engine?).

**Serializační overhead:** `GameAnalysis.to_dict()/from_dict()` na každém cache read/write je pro JSON-serializovatelné dataclassy s desítkami `MoveAnalysis` položek na hru neefektivní jen mírně (JSON (de)serializace je rychlá ve srovnání se Stockfish časem) — toto pravděpodobně **není** reálný bottleneck, spíš kosmetická neefektivita. Bagatelizuji tento bod oproti Stockfish/LLM latenci.

---

## Section 6: Reliability & Error Handling

**Univerzální `{"error": str(e)}`:** Toto je skutečný anti-pattern pro MCP servery z několika důvodů: (1) ztrácí se typ chyby (network vs. validation vs. engine crash) — LLM agent nemůže rozumně rozhodnout, zda má retry, změnit parametry, nebo se vzdát; (2) `str(e)` může uniknout interní detaily (cesty k souborům, verze knihoven) do LLM kontextu, což je menší, ale reálné information-disclosure riziko; (3) chybí strukturovaný error kód/kategorie, který by MCP klient mohl programově zpracovat. Doporučené řešení: alespoň `{"error": {"type": "RateLimitError"|"EngineTimeout"|"ValidationError"|"Unknown", "message": str(e)}}`.

**Zombie recovery (120s):** Časový limit je rozumný kompromis (dost dlouhý na hlubokou analýzu, dost krátký na to, aby uživatel nečekal věčně), ale bez znalosti skutečné distribuce trvání analýz (`depth=24` na dlouhé partii může legitimně trvat přes 120s) riskuje **false positive zombie detekci** — legitimní dlouhá analýza je zabita a restartována, což ztratí práci a vrátí buď chybu, nebo neúplný výsledek volajícímu, jehož požadavek byl ve skutečnosti v pořádku, jen pomalý.

**Graceful degradation:**
- LLM kaskáda: `_fallback_report()` (raw data dump) je dobrý design — systém nikdy úplně neselže, i když všichni 3 poskytovatelé jsou nedostupní.
- Chybějící Stockfish: twin neuvádí explicitní fallback — pokud `STOCKFISH_PATH` resolution selže na všech 4 úrovních, pravděpodobně vyhodí výjimku zachycenou univerzálním handlerem → `{"error": "..."}`. Funkčně to "degraduje" celý T2/T3/T6/T7/T9 (vše, co potřebuje engine) na chybu bez alternativy — to není opravdu "graceful", je to hard-fail se zachytáváním.
- Lichess API výpadek: retry (3x na 429) a graceful 404→[] existuje, ale obecný network timeout/500 chování není zmíněno — pravděpodobně padá do univerzálního `raise` → error.

**Silent failures:** Explicitně zmíněné v twinu: "Disk writes: silent on OSError" — to je designové riziko. Pokud zápis cache selže (např. disk plný, permission chyba), operace **tiše pokračuje**, jako by cache byla zapsána, ale při dalším čtení cache prostě chybí (opětovný výpočet) — funkčně neškodné, ale znamená to ztrátu observability nad stavem disku/cache vrstvy bez jakéhokoli varování v logu.

---

## Section 7: Code Quality Assessment

*Pozn.: Hodnocení vychází z popisu chování a struktury v digital twinu, nikoli z přímého čtení zdrojového kódu — jde o odhad na základě zdokumentovaných vzorů.*

| Module | Readability | Testability | Robustness | Error Handling |
|--------|:-----------:|:------------:|:-----------:|:----------------:|
| server.py | 4 | 2 | 3 | 2 |
| lichess_client.py | 4 | 3 | 3 | 3 |
| engine_client.py | 3 | 2 | 3 | 3 |
| game_analyzer.py | 4 | 3 | 3 | 2 |
| diagnostician.py | 4 | 4 | 3 | 2 |
| pattern_detector.py | 3 | 2 | 2 | 2 |
| llm_client.py | 4 | 3 | 4 | 4 |
| tools/* | 5 | 4 | 3 | 2 |

**Zdůvodnění výběrových bodů:**
- **server.py — Testability: 2:** Startup sekvence je monolitický skript se side-effecty (import triggeruje registraci dekorátorů, env loading má fallback logiku) — těžko testovatelné bez mockování celého procesu spuštění.
- **pattern_detector.py — Testability/Robustness: 2:** 11 samostatných `_detect_*` metod s name-mangling přes `getattr(self, f"_detect_{pid.lower()}")` — typo v `PatternDef.id` tiše vynechá detektor bez chyby; to je špatně testovatelný a fragilní vzor (chybí explicitní registrace/mapping, který by selhal nahlas).
- **llm_client.py — Error Handling: 4:** Nejlépe ošetřený modul v celém systému — explicitní kódy (401/402/429), fallback kaskáda, `_fallback_report()` jako poslední záchrana. Kontrast oproti zbytku kódu je nápadný.
- **tools/* — Readability: 5, Error Handling: 2:** Tenké wrappery jsou snadno čitelné právě proto, že veškerá komplexita je delegována — ale to znamená, že jediný error-handling vzor (`try/except → {"error": str(e)}`) je opakován 9×, což je duplicitní a nekonzistentní s bohatším handlingem v `llm_client.py`.

---

## Section 8: Top 5 Findings

| ID | Severity | Location | Description | Impact |
|----|----------|----------|--------------|--------|
| F1 | Critical | `engine_client.py` — `evaluate_move()` | Pokud `python-chess` `PovScore.score()` vrátí `None` u pozic vedoucích k matu (bez `mate_score` parametru), aritmetika `best_player - actual_player` selže na `TypeError` u jakékoli partie obsahující matovou variantu v enginem navrhované linii. | Analýza her s taktickými/matovými sekvencemi (běžné u blunderů — např. mat v X tahů po chybě) může tvrdě padat nebo tiše vracet nesprávné `cp_loss`, což zkresluje veškeré downstream statistiky (ACPL, klasifikace, pattern detekce). |
| F2 | Critical | `lichess_client.py`, `game_analyzer.py` — cache file naming | `username`/`game_id` vstupy jsou pravděpodobně použity přímo ve jménech cache souborů bez zjevné sanitizace proti path traversal (`../`) nebo neplatným znakům pro souborový systém. | Škodlivý nebo halucinovaný vstup od LLM agenta (`username="../../x"`) by mohl vést k zápisu/čtení souborů mimo zamýšlený `data/` adresář. |
| F3 | Major | `pattern_detector.py` — confidence metriky | Confidence hodnoty jsou heuristické poměry bez statistické váhy na velikost vzorku (min_games 1-3 her); Pattern O má dokonce fixní confidence=0.6 bez ohledu na evidenci. | Uživatel (skrz LLM coaching report) může dostat "critical severity" nález postavený na 1-3 hrách s falešnou jistotou v %, což podkopává důvěryhodnost celého coaching výstupu. |
| F4 | Major | server-wide — `{"error": str(e)}` pattern | Žádná strukturovaná kategorizace chyb (network/validation/timeout/engine) napříč všemi 9 tools. | LLM agent nemůže inteligentně reagovat na chybu (retry vs. abort vs. změna parametrů), degraduje UX i spolehlivost automatizovaných workflow. |
| F5 | Major | `engine_client.py` — analysis lock | Globální lock plně serializuje Stockfish napříč všemi současnými voláními; 120s zombie-recovery nerozlišuje mezi "legitimně pomalá analýza" (depth=24) a skutečně zaseknutým procesem. | Při vyšších hloubkách nebo souběžných klientech riziko zbytečného restartu enginu uprostřed platné práce → ztráta výsledku, matoucí chybové chování. |

---

## Section 9: Recommendations

**Immediate (bugy, které mohou dnes produkovat špatné výsledky):**
- Ověřit a opravit `None`-handling pro matová skóre v `evaluate_move()` (přidat `mate_score` parametr do `.score()` volání nebo explicitní větev pro `Mate` typ).
- Sanitizovat `username`/`game_id` před použitím v cestách k souborům (whitelist regex, např. `^[a-zA-Z0-9_-]+$`).
- Normalizovat diagnostician pravidlo "middlegame > opening+endgame" na per-move rate, ne absolutní count.

**Short-term (stabilita a korektnost):**
- Nahradit string-matching (`"429" in str(e)`) za typovanou kontrolu HTTP status kódu, pokud je dostupná přes `httpx`/`berserk` exception objekt.
- Zavést strukturovaný error formát (`{"error": {"type": ..., "message": ...}}`) napříč všemi tools.
- Přidat statistickou váhu (např. Wilsonův interval nebo prostě explicitní "low sample size" flag) k pattern confidence hodnotám u detektorů s min_games ≤ 3.
- Zdokumentovat/vrátit `actual_depth_used` v odpovědi T2/T6/T7, aby bylo jasné, když cache vrátila hlubší analýzu než požadováno.
- Ověřit chování in-flight analýzy během zombie-recovery restartu (zajistit, že volající dostane jasnou chybu, ne tichý částečný výsledek).

**Medium-term (architektonická vylepšení):**
- Zvážit MCP Progress notifikace pro dlouho běžící tools (T6/T7 s vysokým `max_games`/`depth`).
- Přesunout coaching prompt template do MCP `@app.prompt()` primitivy místo hardcoded stringu v `llm_client.py`, případně zvážit delegaci na MCP `sampling` capability namísto vlastní HTTP LLM kaskády (přenesení nákladů/klíčů na hostitelského klienta).
- Zavést explicitní registraci pattern detektorů (mapping dict místo `getattr` name-mangling), aby typo v ID selhalo nahlas při startu, ne tiše za běhu.
- Vyjasnit a buď dokončit, nebo odstranit `kb/` modul — pokud je použití "omezené na validaci", zvážit sloučení jeho funkcionality přímo do `validator.py` a odstranění samostatného modulu.
- Zvážit rate-limiting/budget cap na LLM kaskádu, zejména na placenou DeepSeek větev.

---

## Section 10: Summary Assessment

- **Celkové skóre:** 5/10 — funkčně ambiciózní a dobře strukturovaný pro rané stádium, ale s několika potenciálně tichými korektnostními bugy (F1, F3) a bezpečnostní mezerou (F2), které by měly být adresovány před jakýmkoli veřejným nebo víceuživatelským nasazením.
- **Největší síla:** Čistá vrstvená architektura (tools/services/models/resources) s konzistentním cache diagram a robustním fallback chováním v `llm_client.py` — LLM kaskáda je nejlépe odladěná část celého systému.
- **Největší slabina:** Nedostatečná explicitní komunikace nejistoty směrem k LLM agentovi — jak ve formě chyb (ztráta typu chyby), tak ve formě pattern-detekce (fixní/neváhovaná confidence u malých vzorků), tak v samotné Stockfish aritmetice (potenciální `None`-related crash u matových pozic).
- **Production-ready pro osobní použití?** Ano, s výhradou — pro jednoho důvěryhodného uživatele na lokálním stroji je riziko F2 (path traversal) prakticky irelevantní a F1 (mate score bug) je spíš otravný než nebezpečný. Doporučuji opravit F1 před dalším používáním, protože přímo ovlivňuje kvalitu analytických dat.
- **Production-ready pro veřejné MCP publikování?** Ne. F1, F2 a F4 by měly být vyřešeny jako předpoklad; F3 (confidence metodologie) by měla být adresována, pokud má coaching výstup sloužit reálným hráčům jako důvěryhodný zdroj — jinak riskuje šíření falešně sebejistých "critical" nálezů nad statisticky nevýznamnými vzorky.
