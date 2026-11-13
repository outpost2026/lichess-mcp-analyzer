# Kandidátní patterny pro pattern detection — naměřená taxonomie

**Datum:** 2026-11-12 | **Status:** PODKLAD PRO ROZHODNUTÍ D4 — žádná implementace
**Rámec:** `docs/REFACTOR_PLAN_2026-11-11.md` §355 (taxonomie dříve než pattern),
D4 (quiet blunder = nejdřív `unclassified` event), §337–340 (runtime
deterministický; LLM = jen offline hypotézy).
**Autor analýzy:** LLM offline nad cache (sémantické čtení digestu); všechna
číla jsou měřená z `data/game_cache`, každé tvrzení je reprodukovatelné.

## 1. Reprodukce a univerza čísel

```
uv run python -X utf8 scripts/aggregate_candidate_moves.py --top 40
```

Sekce skriptu: A inventář · B profily quiet skupin · C proxy mechanismů
(FEN, bez engine) · D sémantický digest kritických momentů · E FP strop
+ mapa fází.

Univerza (aby se čísla nemíchala). Názvy jsou **obsahové**; indexové zkratky jsou jen historické aliasy z prvního měření a v nových artefaktech se nepoužívají:

| Univerzum | Alias | Definice | Velikost |
|---|---|---|---|
| `cache_analyses_raw` | U0 | všech 282 analýz v cache (s duplicitami hloubek) | 8 873 tahů |
| `flagged_factsheets_dedup` | U1 | fact sheets dedup dle `game_id+barva+ply` (hlubší vyhrává) | 880 sheetů (z 943) |
| `all_moves_dedup` | U2 | tahy dedup dle hry+barva (nejhlubší analýza na hru) | 8 109 tahů |
| `good_moves_control` | — | `all_moves_dedup` omezené na `classification == "best"` | 4 721 tahů |

`good_moves_control` je jediný platný jmenovatel FP stropu; `all_moves_dedup` je jmenovatel supportu. Každé číslo v tomto dokumentu musí být doprovázeno `n_moves`, `n_games` a `dataset_sha256` (`services/provenance.py`).

## 2. Naměřená data

### 2.1 Inventář (`cache_analyses_raw`, `flagged_factsheets_dedup`)

- 282 analýz: 204× d12, 58× d14, 16× d14n150000, 3× d18, 1× d8.
- Klasifikace tahů: best 5 194, inaccuracy 1 568, good 1 369, mistake 497,
  blunder 245 → **742 kritických momentů** (blunder+mistake) v `cache_analyses_raw`.
- Fact sheets: 943 → po dedupu **880** (63 duplicit). Covered 311 / quiet 569
  = **64,7 % sheetů bez `pattern_matches`**.

| Třída sheetů | celkem | covered | quiet | % quiet |
|---|---|---|---|---|
| blunder | 222 | 125 | **97** | 43,7 % |
| mistake | 460 | 150 | 310 | 67,4 % |
| inaccuracy | 198 | 36 | 162 | 81,8 % |

Pozn.: v `cache_analyses_raw` má každý blunder (245/245) i každý mistake (497/497) sheet;
inaccuracy sheet má jen 201/1 568 (legacy formát). Unikátních kritických
pozic ve `flagged_factsheets_dedup` je **682** (digest jich zobrazuje 40).

### 2.2 Profily: čím se tichý blunder liší (`flagged_factsheets_dedup`)

| Rys | quiet blunder (n=97) | covered blunder (n=125) |
|---|---|---|
| SAN bez sebrání i šachu | 86 (88,7 %) | 61 (48,8 %) |
| SAN sebrání | **0** | 51 (40,8 %) |
| SAN šach | 11 (11,3 %) | 13 |
| hráč byl před tahem v šachu | **0** | 23 (18,4 %) |
| rank odehraného tahu = 4 (mimo top-3) | 88 (90,7 %) | 96 (76,8 %) |
| fáze (segment) | mid 65 / end 26 / open 6 | end 73 / mid 43 / open 9 |
| cp 300–399 (těsně nad prahem) | 50 (51,5 %) | 41 (32,8 %) |
| motiv (taktický tvar) | 0 | 11 |

Tichý blunder je tedy **strukturálně netaktický tah hráče, který není pod
tlakem šachu, mimo engine top-3, a často těsně nad prahem 300 cp**.

### 2.3 FP strop proxy (`good_moves_control` — jak často by vystřelily na dobrých tazích)

| Tahy | n | hang % | free % |
|---|---|---|---|
| best | 4 721 | 7,4 | 17,6 |
| good | 1 251 | 5,6 | 16,1 |
| inaccuracy | 1 463 | 6,6 | 18,6 |
| mistake | 454 | 11,0 | 30,0 |
| blunder | 220 | **7,7** | **37,3** |

- `hanging_piece`: blunder 7,7 % vs best 7,4 % → **lift 1,04 = bez
  diskriminační síly** (viz §7 — původní invertovaná verze dávala 41,1 %).
- `free_capture_after`: 37,3 % vs 17,6 % → **lift 2,12** (poměr šancí 2,79)
  = jediný silný signál.
- Základna „engine best je capture" (L1) u flagged sheetů: blunder 23,6 %,
  mistake 22,9 %, inaccuracy 22,7 % — **plochá, ~23 %**.

**FP strop se čte pouze z řádku `best`.** Ostatní řádky jsou kontext pro
kontrast, ne FP: `good`/`inaccuracy`/`mistake`/`blunder` nejsou kontrolní
sada a jejich použití jako jmenovatele by FP uměle snížilo.

Podmnožiny podle tvaru tahu (`all_moves_dedup`):

| skupina | tvar | n | hang % | free % |
|---|---|---|---|---|
| best | šach | 258 | 1,9 | 1,9 |
| flagged | šach | 104 | 5,8 | 5,8 |
| best | sebrání | 1 097 | 24,6 | 36,6 |
| flagged | sebrání | 315 | 30,2 | 49,2 |
| best | quiet | 3 206 | 0,6 | 11,5 |
| flagged | quiet | 1 683 | 2,7 | 18,4 |
| flagged | šach+sebrání | 35 | 48,6 | 54,3 |

Klíčové: **šach, po kterém zůstává volný tah soupeře, je na best tazích vzácný
(1,9 %) a na flagged trojnásobný (5,8 %)** — ale malé n. Sebrání mají vysokou
základnu všude (36,6 % na best) — proto „capture + free" je slabý kandidát.

### 2.4 Kde v partii jsou kritické momenty (`all_moves_dedup`, mapování fází)

| fáze (segment) | tahů | podíl | blunder | mistake | crit rate |
|---|---|---|---|---|---|
| opening | 2 519 | 31,1 % | 15 (0,6 %) | 79 | **3,7 %** |
| middlegame | 3 198 | 39,4 % | 106 (3,3 %) | 229 | **10,5 %** |
| endgame | 2 392 | 29,5 % | 99 (4,1 %) | 146 | **10,2 %** |

Kritické momenty se soustředí v middlegame+endgame (2,8× vyšší míra než
v openingu); **nejvyšší míra blunderů je v koncovce (4,1 %)**.

Dopad (|win_prob_delta|, 682 unikátních kritických sheetů):
0,60+ = 39 · 0,30–0,59 = 193 · 0,10–0,29 = 314 · 0,00–0,09 = 136.
Pásma ply: 0–19 = 81 · 20–49 = 345 · 50+ = 256.
Fáze sheetů: blunder mid 108 / end 99 / open 15; mistake mid 233 / end 148 /
open 79. **22/682 sheetů nemá vůbec engine linie** (rank 0 — budget/deadline).

## 3. Sémantická analýza kritických momentů (digest, top 40 dle |wpd|)

Metoda: čtení engine linek L1–L3 (SAN, cp, PV), kontextového okna a proxy
u 40 největších dopadů (wpd −0,935 … −0,592; **všech 40 je class=blunder**).
Přiřazení „primární rodiny" je soudcem LLM offline — jde o interpretační
vrstvu, ne o naměřený fakt; číslo `[n]` odkazuje na výstup digestu
(reprodukcí příkazu výše).

**Upozornění na okno:** `context_window.moves_before/after` obsahují **jen
tahy analyzovaného hráče** (parita ply), tahy soupeře jsou skryté — některé
závěry o „okamžité ztrátě figury" jsou z toho důvodu inference (označeno).

| Rodina | Počet /40 | Příklady (soubor, ply) | Kritérium čtení |
|---|---|---|---|
| F1 volná/uvolněná figura | 7 | zXNIPcPi b50 Ne3; JIup0fyD w71 Rg2; lN4K3mtt w63 Nd4 | tah následovaný ztrátou odehrané figury / free+hang proxy |
| F2 nevyužitý engine best jako sebrání | 8 | qmodxzNF b60 Kd7 (L1 Kxc5); GvX6dBi6 b76 Kb6 (L1 Rxd8); zNo9vhO0 w81 Bg5 (L1 Bxf7+) | L1 = capture, odehráno něco jiného (missed_capture) |
| F3 pseudo-forcing šach | 5 | juc5Yoyf w41 Qe5+; w7o2GAbg w51 Nh6+ (L1 fxg6 recapture); BJUKoLPf w33 Qd2+ (L1 c3+) | odehraný šach, který neřeší hrozbu ani recapturu |
| F4 materiální grab / špatná volba sebrání | 9 | KWfWzjAz b42 Qxa3 (L1 Rhe8); a6UstoSV w43 Bxd3; Px0Izuw4 w47 Nxd5 | capture odehrán, L1 klidný/velký jiný tah |
| F5 jiný tahající kus ve stejném obchodu | 2 | bjI0Hl7E b42 Bg6 vs L1 Qg6 (stejné g6); piZsN15I w41 Rxe5 vs L1 dxe5 (stejné e5) | oba capture, stejný cíl, jiný kus |
| F6 tah místo vyřešení napětí | 1 | rgQlsl0s w21 g3 (L1 Rc1; sebrání až v 23) | quiet tah, zatímco napětí nevyřešeno |
| F7 „správný tah na špatném místě" (nevysvětleno) | 6 | NktJfZZy b64 Rd6; NnHdTc8h w77 Kb1 (L1 Kb2); yQ9wX7eX b48 b5; YkNJF8zt b42 Re3 | oba quiet, žádný proxy, čistě pozicionální ztráta |
| F8 kluz (jiný kus na zamýšlené pole) | 1 | tuHR2dh1 b12 c6 vs L1 N8c6 (stejné c6) | stejný cíl, jiný kus, bez sebrání |
| Z důkazní mezera / anomálie | 1 | Q9xROOT1 w99 Re2 (rank 0, žádné linie) | nelze ohodnotit |

Anomálie k prošetření: `[23] dA9VZuIz w31 Qxf7` — rank 2 (tah je v L2!)
při cp_loss 588, ale L2 eval_cp = −75 → **nesoulad znaménka/ranku vs cp_loss**
(u `[12] JIup0fyD w71 Rg2` podobně rank 2 vs cp 762). Než se z toho stane
pattern, musí se vyřešit FIX-023 provenience.

## 4. Taxonomie mechanismů (výsledek §355)

1. **F1 — uvolněná figura po tichém tahu** (tah neadresuje útok, figura
   vzítelná; někdy se ztratí okamžitě — skrytý tah soupeře v okně).
2. **F2 — nevyužitý engine best jako sebrání** (best byl capture/„recapture",
   hráč tahal jinam; zahrnuje „král mohl brát a nebral").
3. **F3 — pseudo-forcing šach** (šach jako iluze iniciativy místo obrany/
   recaptury; tah po šachu stále dovoluje volný tah soupeře).
4. **F4 — materiální grab** (sebrání salientního materiálu, zatímco engine
   chtěl klidný tah / jiné, větší sebrání).
5. **F5 — špatný tahající kus ve stejném obchodu** (stejný cíl, jiný kus —
   „vzal dámou místo pěšcem, tj. jiný výsledek výměny").
6. **F6 — odložené vyřešení napětí** (tah místo nutného sebrání/bránění).
7. **F7 — pozicionální ztráta bez identifikovaného mechanismu** (to, co
   zbývá; **jádro `unclassified` stavu D4**).
8. **F8 — kluz záměru** (zamýšlený tah jiným kusem na stejné pole).
9. **Z — důkazní mezera** (bez engine linek, anomálie znaménka).

Pokrytí proxy ve `flagged_factsheets_dedup` (součty se překrývají, tah může mít více):

| skupina | free_capture_after | missed_capture | hanging_piece | žádný proxy |
|---|---|---|---|---|
| quiet blunder (97) | 32 (33,0 %) | 19 (19,6 %) | 6 (6,2 %) | **51 (52,6 %)** |
| quiet mistake+inacc (472) | 103 (21,8 %) | 93 (19,7 %) | 14 (3,0 %) | 298 (63,1 %) |
| covered blunder (125) | 50 (40,0 %) | 19 (15,2 %) | 11 (8,8 %) | 62 (49,6 %) |

**Přes polovinu tichých blunderů nemá žádný proxy** — to je měřený objem
zbytku, který D4 říká ponechat jako `unclassified`, ne vymýšlet pattern narychlo.

## 5. Kandidáti (D4 — všichni ve stavu „kandidát", nic není implementováno)

### K1 `loose_piece` (F1) — ZAMÍTNUT měřením FP stropu
- Spec: po odehraném tahu je naše figura na cílovém poli napadena soupeřem
  a nebráněna.
- Důkaz: hang na blunder 7,7 % vs na best 7,4 % (`good_moves_control`) → lift 1,04.
- Verdikt: jako trigger/klasifikátor **nepoužitelný**. Zůstává jen možný
  kvalifikátor už flagged tahů, a to až v kombinaci s K1′/K2.

### K1′ `quiet_move_free_capture` (F1′ odvozený z F4/free) — kandidát
- Spec: flagged tah + SAN bez sebrání (quiet, případně i šach) +
  `free_capture_after` na pozici po tahu.
- Důkaz: quiet blunder 32/97 (33,0 %) vs základna best-quiet 11,5 % (`good_moves_control`)
  → lift 2,87.
- FP testy (plánované): (a) negativní sada = best/good quiet tahy, kde
  `free_capture_after` fire (369/3 206) — musí existovat podmínka, která je
  oddělí (např. hodnota volného materiálu ≥ 300 cp, tj. SEE-like podmínka);
  (b) 10 fixture z cache: pozice, kde je „volný tah" ve skutečnosti past
  (po sebrání následuje fork/pin) — očekávání: pattern NESMÍ fire;
  (c) na nových snapshotch: podíl fire na win/draw vs loss tahy.

### K2 `missed_win_capture` (F2) — kandidát na EXPLANAČNÍ label, ne na diskriminátor
- Spec: na flagged tahu je L1 (`best_san_of` = `move.best_move_san`, jinak
  L1 z `engine_lines`) capture a odehraný tah capture není.
- Důkaz: quiet blunder 19/97 (19,6 %) vs covered 19/125 (15,2 %); ale
  základna „L1 = capture" u flagged je ~23 % → **lift pod základnou**.
- Verdikt: jako detektor slabý; jako **kvalita vysvětlení v reportu** dobrý
  (v top-40 jde o 8/40 největších dopadů: Kxc5, Rxd8, Kxe2, Bxf7+, Qxd4+,
  gxf5, Bxc3, fxg6).
- FP test: manuální kontrola 20 náhodných výskytů z digestu — že sebrání
  bylo podle engine materiálně rozhodující (ne jen „best se tak jako tak
  bral"), + deterministická podmínka `L1 eval − eval po tahu ≥ 300`.

### K3 `unaddressed_check` (F3) — kandidát s dobrým liftem, malým n
- Spec: flagged tah = šach (SAN `+`/`#`) + po šachu má soupeř
  `free_capture_after` nebo je naše figura visící + L1 řeší jinak
  (recapture/obrana, ideálně bez šachu).
- Důkaz: šach-forem na best 1,9 % free/hang vs flagged 5,8 % (lift ~3);
  v top-40 rodina 5/40; quiet blunder šachy 11/97.
- FP testy: (a) fixture „šach, který skutečně řeší hrozbu" (musí NEfire);
  (b) změřit podmnožinu „šach na best tazích" kompletně (n=258, 5 případů)
  jako negativní sadu; (c) rozšířit n přes mistake třídu (šachů je málo →
  před implementací zvážit sloučení s K1′).

### K4 `material_grab_over_threat` (F4) — kandidát, nutná podmínka hodnoty
- Spec: flagged + odehraný capture + L1 quiet (nebo jiný, větší capture) +
  `free_capture_after`.
- Důkaz: rodina 9/40 v top-40; ALE základna „capture + free" na best
  sebráních = 36,6 % → **naivní forma má 36,6 % FP strop, zamítnuta**.
- nutná podmínka: hodnota volného materiálu soupeře > hodnota námi
  sebraného materiálu (SEE-podobná nerovnost; deterministické z python-chess
  bez engine).
- FP test: (a) negativní sada = best captures s free (402/1 097) — musí je
  podmínka hodnoty oddělit; (b) fixture z cache, kde grab je korektní
  protiútokem (musí NEfire).

### K5 `wrong_recapture` (F5) — kandidát, nejčistší mechanika
- Spec: flagged + odehraný capture + L1 capture + **stejný cílový pole**
  (`uci[-2:]` shoda) + jiný tahající kus.
- Důkaz: 24 pozic ve `flagged_factsheets_dedup` (bulk měření); v top-40: [9] Bg6 vs Qg6,
  [11] Rxe5 vs dxe5.
- FP testy: (a) manuální kontrola 10/24, že rozdíl je v materiálu
  (jiný výsledek výměně), ne jen v pořadí preferencí; (b) fixture, kde je
  jiný tahající kus rovnocenný (obě varianty ±30 cp — musí NEfire, tj.
  podmínka `cp_loss ≥ 300` už existuje, ověřit na hraničních 300–399).

### K8 `intention_slip` (F8) — zatím event, ne pattern
- Spec k eventu: flagged + L1 a odehraný tah mají stejné cílové pole,
  jiný tahající kus, aniž by šlo o capture (kluz záměru).
- Důkaz: 1/40 (c6 vs N8c6). Příliš vzácný na pattern; chování odpovídá
  pohybové/chybové glebě (viz §6), ne šachovému mechanismu.
- FP test: shoda cílového pole může být i legitimní alternativa — fixture
  „stejné pole, rovnocenné varianty" musí NEfiret.

### Kandidáti NE — co zůstává `unclassified` (D4)
- **F7 (6/40)** a **51/97 tichých blunderů bez jakéhokoli proxy** → stav
  `unclassified` (FIX-029), žádný pattern bez nového engine-side měření
  (např. SEE, obranná hloubka, kontinuační hrozby — to je až P-kolo po D4).
- **F6 (1/40)** — příliš málo podpory pro cokoli než event.
- **Z** — nejdřív vyřešit znaménkovou anomálii a pokrytí engine liniemi
  (22/682 bez linek), jinak by pattern měl vstup bez důkazu.

## 6. Behaviorální / psychologické hypotézy (LLM offline — NE data, NE runtime)

Každá hypotéza je testovatelná a zatím nepotvrzená; nic z toho se
v detektorech neimplementuje (§337–340).

| Hypotéza | Rodina | Předpoklad chování | Jak ověřit |
|---|---|---|---|
| Předpojatost ke šachu („šach musí být dobrý") | F3 | hráči dávají přednost šachu před recapturou/obranou | poměr šachů u flagged vs best (naměřeno 5,8 % vs 1,9 % — směr sedí, n malé) |
| Materiální salience (grab bias) | F4 | sebrání je nejsnazší volba, „lepší" tah se přehlédne | korelace s game-level tagem `automatic_grab` (true u 113/282 analýz; `bait_trap` vždy false, `metacognition` vždy prázdné — políčka existují, ale nevyužitá) |
| Selhání update mapy („nechal jsem něco viset") | F1/K1′ | po vlastním tahu chybí kontrola bezpečnosti vlastních figur | F1/K1′ fire rate vs `was_in_check` a vs fází |
| Kluz záměru (nesprávný kus, zamýšlené pole) | F8 | shoda cílového pole + jiný kus = překlep, ne výpočet | sběr: četnost stejného cíle u best tahů (zatím nezměřeno) |
| Vyhýbání se napětí (tension avoidance) | F6 | místo sebrání/bránění volba klidného tahu | poměr „recapture existovala a nehrála se" u flagged |
| Vada rozumného tahu (sensible-move flaw) | F7 | první „slušně vypadající" tah bez konkrétního výpočtu | zbývá po vyčerpání F1–F6; jediná cesta = engine-side kontinua (SEE, hloubka obrany) |

Poznámka: `automatic_grab` je game-level pole (113/282 analýz true) —
existující koncept, který se F4 přímo dotýká; před novým patternem nejprve
zjistit, jak se tag počítá (nedařilo se zde dohledat jeho tvůrce — viz
§8), aby se ne duplicitoval.

## 7. Auditní nálezy z měření (opraveno během tvorby tohoto dokumentu)

1. **Invertovaný `hanging_piece`** — po `board.push` je `board.turn` = soupeř,
   původní podmínka měřila „napadeno NÁMI". FP strop to odhalil: 41,1 % na
   best tazích (nemožné). Po opravě 7,4 %. Bez měření by detektor prošel.
2. **Dedup bez barvy** — klíč `game_id+ply` slučoval obě barvy stejné hry
   (`bRBSphxo_white` + `_black` existují); `all_moves_dedup` vzrostlo
   z 6 477 na **8 109** po opravě na `(game_id, barva, ply)` / `(gid, barva)`.
3. **`best_move_san` jen u 282/943 sheetů** — proxy `missed_capture` byl
   nefunkční (1 výstřel). Fallback na L1 z `engine_lines` (897/943;
   při průniku 0 nesouladů) zvedl počet na 19/97 quiet blunder.
4. **`ignored_threat` proxy byl strukturálně nesmyslný** — best move je tah
   NAŠÍ barvy; po našem tahu je pro soupeře ilegální vždy (naměřeno 0,0).
   Vyřazen z definice proxy.
5. **Duplicitní hloubky** — 63 sheetů stejné (hra, barva, ply) ve více
   hloubkách; digest před dedupem obsahoval 2 dvojice d12/d14.

## 8. Další kroky (v pořadí)

**Metodologický rámec:** `docs/PATTERN_DISCOVERY_METHODOLOGY.md` (2026-11-12)
— evidence hierarchie E0-E5, discovery loop, cross-domain srovnání,
originalita a roadmapa P1-P7. Tento dokument je závazný pro každý nový
pattern; zdejší taxonomie F1-F8/Z je jeho measurement appendix.

1. **D4**: ROZHODNUTO 2026-11-12 (P0-7) — quiet blunder dostává explicitní
   `unclassified` event s důvodem, žádný nový pattern. Měření pokrytí viz §9.
2. **FP testy K1′, K2, K3, K4, K5** podle plánů v §5 (fixture z cache +
   negativní sady z `good_moves_control`) — až pak implementace patternů.
3. Prošetřit **znaménkovou anomálii** (rank 2 vs cp_loss; L2 eval −75) —
   souvisí s FIX-023 provenience.
4. **Pokrytí engine liniemi**: 22/682 kritických sheetů bez linek —
   bez nich je K2/K5 nevyhodnotitelný.
5. Doplnit do okna `context_window` **tahy soupeře** (nyní jen tahy
   analyzovaného hráče) — jinak F1 nelze deterministicky potvrdit z okna.
6. Pravidelný běh digestu po každé dávce snapshotů (cadence): stejný příkaz,
   tabulky §2–§3 se přepočtou; změny v procentech = regrese/posun.
7. `automatic_grab`/`metacognition` — dohledat tvůrce pole, než se navrhne
   korelace (§6).

## 9. P0-7 měření pokrytí (2026-11-12)

Zdroj: `scripts/measure_pattern_coverage.py` (stejná cache, dedup
`game_id+color`, nejhlubší analýza, bez engine/sítě). Na rozdíl od §2 se
neměří proxy, ale **výstup produkčního detektoru**: `scan_single_game()`
(per-move patterny B/J/R/S/C/T) vs explicitní `unclassified` důvod.

| Metrika | Hodnota |
|---|---|
| soubory / hry po dedupu | 282 / 259 |
| flagged tahy | 2137 (blunder 220, mistake 454, inaccuracy 1463) |
| matched patternem | 375 (17,5 %) |
| unclassified | 1762 (82,5 %) |
| blunder matched | 124/220 (56,4 %) |
| mistake matched | 148/454 (32,6 %) |
| inaccuracy matched | 103/1463 (7,0 %) |
| `quiet_positional` | 1523 (86,4 % unclassified) |
| `forcing_move_unexplained` | 148 (8,4 %) |
| `capture_unexplained` | 91 (5,2 %) |
| flagged s `best_move_san` | 276/2137 (12,9 %) |

Dva nálezy:

1. **Pokrytí je dáno prahy, ne chybějícími daty.** Většina unclassified tahů
   je tichá poziční chyba (`quiet_positional`), tedy přesně objem, který D4
   nechává jako event — ne důkaz pro nový pattern.
2. **Absence PV je globální, ne per-tah.** `engine_lines`/`played_rank` nese
   jen 11 % flagged tahů v cache (jsou uložené ve fact sheets, ne v
   `MoveAnalysis`). Proto `evidence_gap` není první větev klasifikace: jinak
   by 88 % důvodů bylo „nemáme důkaz" a tvar tahu by se ztratil. Kvalita
   podkladu se reportuje zvlášť (`patterns_meta`) a je zapsaná jako
   `CACHE-PV-FIDELITY` v `.ai_state.json`.

---
*Všechna čísla: `scripts/aggregate_candidate_moves.py`, běh 2026-11-12,
cache 282 analýz. Cache je gitignored — bez ní nelze čísla reprodukovat,
souřadnice her (id+ply) jsou v digestu pro ruční dohledání. Pokrytí v §9:
`scripts/measure_pattern_coverage.py`, stejný běh/cache.*
