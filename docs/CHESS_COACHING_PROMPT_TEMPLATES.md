# LLM Prompt Templates for Chess Coaching Reports

**Datum:** 2026-07-29
**Účel:** 5 reusable prompt template pro generování coaching reportů z lichess-analyzer-mcp pipeline
**Metodologický základ:** Heisman (Novice Nook), Silman (imbalances), AICoachess, DecodeChess, Caissa (GM Prasanna), ChessMentor AI
**Guardrails:** §5.2 HALUCINACE_ROOT_CAUSE_ANALYSIS — [DATA]/[IM] separation, NEVYMÝŠLEJ, ověř každé tvrzení

---

## Semantická analýza — co funguje v existujících zdrojích

| Zdroj | Klíčová metodika | Co přináší do promptu |
|-------|------------------|-----------------------|
| **Heisman** | Sokratovská metoda, "minimalizuj největší chyby první", The Four Homeworks, Looking for Trouble | Error prioritization, thought process emphasis, tactical safety checklist |
| **Silman** | 7 imbalances: minor piece, pawn structure, space, material, key file/square, development, initiative | Positional assessment framework, fantasy position thinking, side-of-board planning |
| **AICoachess** | Phase grading (opening/middlegame/endgame), tactical radar, critical moment ID | Phase-structured reporting, per-phase accuracy scores, "what vs why" distinction |
| **DecodeChess** | XAI — 5 dimensions: threats, good moves, plans, piece functionality, concepts | Structured position breakdown, explanatory AI layer |
| **Caissa** | GM-embedded methodology, 3 pillars (GM + AI + peer), psychology training | Long-term improvement planning, emotional regulation, mindset |
| **ChessMentor AI** | 18 pattern types, cross-game detection, opening stats, coach chat | Multi-game pattern aggregation, opening-specific diagnostics |
| **Industry consensus** | Self-analyze first → engine verify → classify errors → find patterns → create plan | Workflow structure: blunder/mistake/inaccuracy classification by cp thresholds |

---

## Template 1: Per-Game Coaching Report

**Účel:** Detailní analýza jedné hry — fázový breakdown, kritické momenty, tréninková doporučení.
**Vstup:** 1 game_id, cached analysis (_white_d{depth} / _black_d{depth})
**Metodika:** Heisman error prioritization + AICoachess phase grading + Silman imbalances

POZNAMKA K DEPTH:
- Standardni analyza: d=14 (single game), d=12 (batch)
- Cache soubory: {game_id}_{color}_d{depth}.json
- Pro detailni endgame/positional analyze: pouzij d=18
- Depth neni tool parametr — MCP tool pouzije default podle profilu hry

```
Vytvoř coaching report pro hru {game_id}.

K DISPOZICI:
- Cache analýza: data/game_cache/{game_id}_{color}_d{depth}.json
  (per-move Stockfish eval, cp_loss, was_in_check, phase)
- Pattern detection: lichess_match_patterns(game_ids="{game_id}", depth=14)
- BlunderFactSheet: každý blunder s context_window a engine_lines

PRAVIDLA:
1. KAŽDÉ konkrétní tvrzení o tahu, cp_loss, eval, FEN, patternu MUSÍ být ověřeno z cache nebo tool response.
2. Pokud tool nevrátí affected_games pro pattern — neuváděj konkrétní game_id. Napiš "N her s tímto patternem".
3. Pokud nemáš data — NEVYMÝŠLEJ. Nahraď obecným popisem.
4. [DATA] a [IM] oddělené sekce.

STRUKTURA:
[DATA] Základní info: výsledek, barva, time control, celková ACPL, accuracy %
[DATA] Fazovy breakdown:
  - Opening (ply 1-15): ACPL, hlavní chyby
  - Middlegame (ply 16-40): ACPL, kritické momenty (kde eval skočil >200cp)
  - Endgame (ply 41+): ACPL, konverze/obrana
[DATA] Error klasifikace:
  - Blunders (>200cp): počet, seznam, každý s ply, cp_loss, popis
  - Mistakes (100-200cp): počet, seznam
  - Inaccuracies (50-100cp): počet (bez detailu pokud >3)
[DATA] Pattern detection výsledky pro tuto hru
[DATA] Silman imbalance assessment v klíčových pozicích (minor piece, pawn structure, space, king safety)

[IM] Heisman-style error analýza:
  - Která chyba byla nejkritičtější (největší cp_loss, nejhorší načasování)
  - Šlo o taktickou chybu (patterns, přehlédnutí) nebo poziční (plán, struktura)?
  - Byl hráč v time trouble? (časová značka pokud dostupná)
[IM] Tři věci co hráč udělal dobře
[IM] Jedna věc na zlepšení do příště (Heisman: minimalizuj největší chybu první)
[IM] Tréninková doporučení: konkrétní puzzle téma, studijní materiál, otázka k zamyšlení
```

---

## Template 2: Cross-Game Pattern Analysis (Aggregate N Games)

**Účel:** Agregace N her — detekce recurring patternů, ranking dle frequency/severity, diagnostika slabin.
**Vstup:** N game_ids + pattern detection results
**Metodika:** ChessMentor AI (18 pattern types) + Heisman (prioritizace) + vlastní pipeline

```
Vytvoř cross-game pattern analysis pro {N} her hráče.

K DISPOZICI:
- Pattern detection: lichess_match_patterns(username="{username}", max_games={N})
  s výsledky: confidence, frequency, severity, affected_games
- Cache všech her: data/game_cache/*.json (ACPL per game, blunder rate)
- BlunderFactSheets pro všechny blundry napříč hrami

PRAVIDLA:
1. Každé tvrzení o pattern frekvenci, ACPL, blunder rate musí být ověřeno z cache/tool.
2. Pokud pattern nemá affected_games — uveď "N her s tímto patternem", NE game_id.
3. [DATA] = ověřitelná fakta, [IM] = interpretace a doporučení.
4. NEVYMÝŠLEJ příklady — pokud nemáš affected_games, nepoužívej konkrétní herní scénáře.

STRUKTURA:
[DATA] Agregované statistiky:
  - Celkový počet her, výsledky (W/L/D), průměrná ACPL
  - Rozložení dle barvy (bílý/černý ACPL, win rate)
  - Průměrný počet blunderů/mistakes/inaccuracies na hru
  - ACPL trend (první polovina her vs druhá)
[DATA] Pattern ranking (sestupně dle composite_score = frequency * severity):
  1. {pattern_name} — frequency={X}%, severity={Y}/10, confidence={Z}%
     affected_games: [id1, id2, ...]
  2. ...
[DATA] Phase breakdown:
  - Opening ACPL, % errors in opening
  - Middlegame ACPL, % errors in middlegame
  - Endgame ACPL, % errors in endgame
[DATA] Error distribution:
  - Tactical errors (forks, pins, skewers, discovered attacks) vs positional errors
  - Poměr: kolik % chyb je taktických

[IM] Heisman-style diagnostika:
  - Který pattern je nejkritičtější (ne podle frequency, ale podle dopadu na výsledek)
  - Kde hráč ztrácí nejvíc ELO (např. "endgame conversion" pokud 60% proher pochází z vyhraných endgame)
[IM] Silman-style assessment:
  - Jaké imbalances hráč systematicky přehlíží? (např. "nikdy nebere v úvahu bishop pair")
  - V jakých typech pozic hráč exceluje a kde selhává?
[IM] Top 3 doporučení (Heisman: minimalizuj největší chybu první):
  1. Konkrétní pattern k odstranění
  2. Konkrétní fáze k posílení
  3. Konkrétní tréninková metoda (puzzles, studie, otázka k myšlenkovému procesu)
[IM] Verdikt: "Hráč je {typ} — nejsilnější v {X}, nejslabší v {Y}. Očekávaný improvement: {Z} ELO za {N} měsíců při {frekvence} tréninku."
```

---

## Template 3: Opponent Pool Analysis

**Účel:** Analyzovat pool her z perspektivy oponenta — co oponenti dělají špatně, exploitable patterns, countermeasures.
**Vstup:** N game_ids s flipped perspective (opponent = "us"), včetně n1 (losses) vs n2 (wins) groups.
**Metodika:** Vlastní dual-perspective pipeline + Silman (exploiting imbalances) + AICoachess (critical moments)

```
Vytvoř opponent pool analysis pro {N} her — analyzováno z OPPONENTOVY perspektivy.

KONTEXT:
- Hry jsou z pohledu OPPONENTA (my = oponent, oni = původní hráč)
- n1 = {n1_počet} her kde OPPONENT prohrál (original: wins)
- n2 = {n2_počet} her kde OPPONENT vyhrál (original: losses)
- Cache: data/game_cache/*_black_d{depth}.json a *_white_d{depth}.json (dual perspective)

K DISPOZICI:
- Opponent perspective pattern detection: lichess_match_patterns(game_ids="{ids}")
  (detekuje patterny v OPONENTOVĚ hře)
- Author perspective patterns pro srovnání: z předchozího běhu
- Per-game ACPL srovnání: author_acpl vs opponent_acpl
- BlunderFactSheets z obou perspektiv

PRAVIDLA:
1. Stejná guardrails jako Template 1+2 — ověř každé tvrzení, NEVYMÝŠLEJ, [DATA]/[IM] split.
2. OZNAČ perspektivu: každý pattern/game id uveď "opponent:" nebo "author:" prefix.
3. Pokud n2 < 3 hry: statistika n2 je indikativní, ne průkazná — explicitně uveď.
4. Countermeasures musí být konkrétní a ověřitelné z dat.

STRUKTURA:
[DATA] Opponent aggregate:
  - n1 ACPL = {X} ({n1} her), n2 ACPL = {Y} ({n2} her)
  - Blunder rate: n1 = {X}/game, n2 = {Y}/game
  - Phase breakdown (opponent perspective)
[DATA] Pattern detection — opponent:
  - Ranking patternů co oponenti dělají (frequency, severity)
  - Srovnání: author pattern frequency vs opponent pattern frequency (pattern delta)
[DATA] n1 vs n2 diferenciál:
  - Co dělali oponenti jinak v n2 (když vyhráli) vs n1 (když prohráli)?
  - ACPL difference, blunder difference, phase difference
[DATA] Zero-blunder games (pokud existují):
  - Které hry měly 0 blunderů z opponent perspektivy
  - Společné znaky těchto her

[IM] Co oponenti dělají špatně (Heisman-style):
  - Nejčastější typ chyby (taktická/poziční, fáze, pattern)
  - Kde oponenti systematicky selhávají pod tlakem
[IM] Exploitable patterns (Silman-style):
  - Jaké imbalances oponenti nechápou a lze je exploitovat
  - Konkrétní pozice/plány kde mají oponenti slabiny
[IM] Countermeasures:
  - Co dělat v openingu pro maximalizaci opponent error rate
  - Jaké typy pozic vytvářet (closed/open, tactical/positional, time pressure)
[IM] n2 study — co funguje:
  - V čem se lišily hry kde oponent vyhrál?
  - Jaké chování oponenta vedlo k úspěchu?
  - Dá se to replikovat?
```

---

## Template 4: Training Plan Generator

**Účel:** Z cross-game diagnostiky vygenerovat konkrétní, časově ohraničený tréninkový plán.
**Vstup:** Výstup z Template 2 + znalost hráčova ratingu, time control preference, dostupného času.
**Metodika:** Heisman (Four Homeworks) + Caissa (structured curriculum) + Chessodoro (monthly focus)

```
Vytvoř tréninkový plán pro hráče na základě diagnostiky z {N} her.

KONTEXT:
- Rating: {rating}, Time control: {tc}, Available: {hours/week} hodin týdně
- Diagnostics: Template 2 output (error types, phases, patterns)
- Otevřené otázky k zodpovězení: {questions}

PRAVIDLA:
1. KAŽDÉ doporučení musí vycházet z diagnostických dat — ne generické rady.
2. Pokud data neukazují konkrétní slabinu — neimprovizuj. Napiš "není dostatek dat".
3. [DATA] = co diagnostika ukázala, [IM] = co s tím dělat.
4. Plán musí být realistický na {hours/week} hodin týdně.

STRUKTURA:
[DATA] Shrnutí diagnostiky (1-2 věty)
[DATA] Top 3 slabiny dle dopadu na výsledek:
  1. {slabina} — ztráta ~{X} ELO (odhad)
  2. ...
  3. ...

[IM] Měsíční plán (4 týdny):
  - Týden 1: {cíl} — konkrétní cvičení, počet hodin, pomůcky
  - Týden 2: {cíl} — ...
  - Týden 3: {cíl} — ...
  - Týden 4: {cíl} — review + test (NOVÝ set her)
[IM] Heisman Four Homeworks rozpis:
  1. Tactical puzzles: {téma}, {počet}/týden, zdroj: {lichess/chesstempo}
  2. Annotated master games: {konkrétní kniha/games}, {počet}/týden
  3. Game analysis: {vlastní hry}, struktura: self-review → engine → coach
  4. Reading: {konkrétní kapitola/článek}, zaměření
[IM] Měsíční cíl:
  - Co konkrétně chceme dosáhnout (např. "snížit blunder rate z 1.2/game na 0.6/game")
  - Jak změříme úspěch (ACPL, win rate v určité fázi, pattern frequency)
[IM] Co NEDĚLAT:
  - Na co se nesoustředit (Heisman: "opravy vzácných chyb nepomohou tolik jako oprava častých")
```

---

## Template 5: Opening Repertoire Report

**Účel:** Analyzovat výkonnost dle zahájení — kde se vyplácí příprava, kde hráč ztrácí body.
**Vstup:** N game_ids + opening klasifikace z cache (ECO code, opening name)
**Metodika:** ChessMentor AI (opening stats) + vlastní pipeline (ACPL per opening)

```
Vytvoř opening repertoire report pro hráče z {N} her.

K DISPOZICI:
- Cache: data/game_cache/*.json (každá hra má opening_name, ECO)
- Pattern detection: lichess_match_patterns (cross-reference s openingem)
- ACPL per game, blunder rate per game

PRAVIDLA:
1. Každé tvrzení o výkonnosti v openingu musí být podloženo minimálně 3 hrami v daném zahájení.
2. Pokud počet her pro opening < 3: uveď "nedostatek dat — indikativní".
3. [DATA]/[IM] split.
4. NEVYMÝŠLEJ teoretické varianty — používej jen data z cache.

STRUKTURA:
[DATA] White openings:
  - {opening} ({počet} her): {win_rate}%, ACPL {X}, blunder rate {Y}
  - Seřazeno dle performance (win rate * games played)
[DATA] Black openings:
  - {opening}: stejná struktura
[DATA] Nejhorší openingy (top 3 dle ACPL / win rate):
  - {opening}: ACPL {X}, prohrané pozice v ply {Y}-{Z} (typické problémy)
[DATA] Nejlepší openingy (top 3):

[IM] Kde hráč ztrácí body v openingu:
  - Memory issue? (opouští teorii brzy a je v problémových pozicích)
  - Conceptual issue? (rozumí myšlence za variantou?)
  - Tactical issue? (dělá chyby v konkrétních taktických motivacích)
[IM] Repertoire doporučení:
  - Co ponechat (funguje, nízká ACPL)
  - Co posílit (funguje částečně, chybí znalost konkrétních linií)
  - Co zvážit výměnu (vysoká ACPL, nízká win rate)
[IM] Prioritizace:
  - Který opening má nejvyšší ROI na hodinu studia?
  - (zvaž: frekvence výskytu * current ACPL * potenciál zlepšení)
[IM] Tréninkový tip na tento týden:
  - Konkrétní 1-2 varianty k prostudování
  - Konkrétní zdroj (Lichess study, Chessable, kniha, video)
```

---

## Metodologické poznámky k použití

### Ranking errorů dle Heismana
1. **Blunder** (>200cp nebo ztráta figury/mat): studovat KAŽDÝ — "one understood blunder is a permanent upgrade"
2. **Mistake** (100-200cp): studovat v prohraných hrách — obvykle kde hra začala klouzat
3. **Inaccuracy** (50-100cp): skimmovat, ignorovat pod 1800 ELO — "perfekcionismus o inaccuracies je prokrastinace o blunderech"

### Klasifikace errorů — taktický vs poziční
| Typ | Charakteristika | Oprava |
|-----|----------------|--------|
| **Taktický** | Přehlédnutí forku, pinu, skeweru, deflekce | Puzzle training (CCTV: Checks, Captures, Threats, Vulnerable pieces) |
| **Poziční** | Špatný plán, struktura, piece activity, imbalance misread | Silman imbalances study, annotated GM games |

### Silmanových 7 imbalances pro assessment
1. Superior minor piece (knight vs bishop, aktivní vs pasivní)
2. Pawn structure (islolated, doubled, holes, passed pawns)
3. Space (who controls more squares on opponent's side)
4. Material (up/down)
5. Control of key file or square (outpost, open file)
6. Lead in development (tempo, initiative)
7. King safety (castled vs exposed, attacking chances)

### Escape hatch konvence
Když tool nevrátí `affected_games` pro pattern:
```
[DATA] Pattern J: frequency=33%, confidence=0.72
  affected_games: (nedostupné — per-game data nejsou k dispozici)
[IM] Tento pattern se vyskytuje v ~1/3 her.
Konkrétní příklad nelze uvést bez per-game dat.
Nejčastější projev: [obecný popis patternu bez game ID].
```
