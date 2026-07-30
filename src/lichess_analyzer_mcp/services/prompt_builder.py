"""5 coaching prompt templates + builder function.

Transforms prompts from CHESS_COACHING_PROMPT_TEMPLATES.md into
Python string templates with {placeholder} for pipeline data.
"""

PROMPT_TEMPLATES: dict[int, str] = {
    1: """Vytvoř coaching report pro hru {game_id}.

K DISPOZICI:
- Cache analýza: data/game_cache/{game_id}_{color}_d{depth}.json
  (per-move Stockfish eval, cp_loss, was_in_check, phase)
- Pattern detection: {patterns_json}
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
[IM] Tréninková doporučení: konkrétní puzzle téma, studijní materiál, otázka k zamyšlení""",
    2: """Vytvoř cross-game pattern analysis pro {N} her hráče.

K DISPOZICI:
- Pattern detection: {patterns_json}
  s výsledky: confidence, frequency, severity, affected_games
- Cache všech her: data/game_cache/*.json (ACPL per game, blunder rate)
- BlunderFactSheets pro všechny blundry napříč hrami
- Weakness report: {weakness_json}

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
  {pattern_ranking}
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
  3. Konkrétní tréninková metoda
[IM] Verdikt""",
    3: """Vytvoř opponent pool analysis pro {N} her — analyzováno z OPPONENTOVY perspektivy.

KONTEXT:
- Hry jsou z pohledu OPPONENTA (my = oponent, oni = původní hráč)
- n1 = {n1_počet} her kde OPPONENT prohrál (original: wins)
- n2 = {n2_počet} her kde OPPONENT vyhrál (original: losses)
- Cache: data/game_cache/*.json (dual perspective)

K DISPOZICI:
- Opponent perspective pattern detection: {opponent_patterns_json}
  (detekuje patterny v OPONENTOVĚ hře)
- Author perspective patterns pro srovnání: {author_patterns_json}
- Per-game ACPL srovnání: author_acpl vs opponent_acpl
- BlunderFactSheets z obou perspektiv

PRAVIDLA:
1. Stejná guardrails — ověř každé tvrzení, NEVYMÝŠLEJ, [DATA]/[IM] split.
2. OZNAČ perspektivu: každý pattern/game id uveď "opponent:" nebo "author:" prefix.
3. Pokud n2 < 3 hry: statistika n2 je indikativní, ne průkazná — explicitně uveď.
4. Countermeasures musí být konkrétní a ověřitelné z dat.

STRUKTURA:
[DATA] Opponent aggregate:
  - n1 ACPL = {n1_acpl} ({n1} her), n2 ACPL = {n2_acpl} ({n2} her)
  - Blunder rate: n1 = {n1_blunder_rate}/game, n2 = {n2_blunder_rate}/game
  - Phase breakdown (opponent perspective)
[DATA] Pattern detection — opponent:
  - Ranking patternů co oponenti dělají (frequency, severity)
  - Srovnání: author pattern frequency vs opponent pattern frequency (pattern delta)
[DATA] n1 vs n2 diferenciál:
  - Co dělali oponenti jinak v n2 (když vyhráli) vs n1 (když prohráli)?
  - ACPL difference, blunder difference, phase difference

[IM] Co oponenti dělají špatně:
  - Nejčastější typ chyby (taktická/poziční, fáze, pattern)
  - Kde oponenti systematicky selhávají pod tlakem
[IM] Exploitable patterns:
  - Jaké imbalances oponenti nechápou a lze je exploitovat
  - Konkrétní pozice/plány kde mají oponenti slabiny
[IM] Countermeasures:
  - Co dělat v openingu pro maximalizaci opponent error rate
  - Jaké typy pozic vytvářet (closed/open, tactical/positional, time pressure)
[IM] n2 study — co funguje:
  - V čem se lišily hry kde oponent vyhrál?
  - Jaké chování oponenta vedlo k úspěchu?
  - Dá se to replikovat?""",
    4: """Vytvoř tréninkový plán pro hráče na základě diagnostiky z {N} her.

KONTEXT:
- Rating: {rating}, Time control: {tc}, Available: {hours_week} hodin týdně
- Diagnostics: pattern detection + weakness report
- {questions}

PRAVIDLA:
1. KAŽDÉ doporučení musí vycházet z diagnostických dat — ne generické rady.
2. Pokud data neukazují konkrétní slabinu — neimprovizuj. Napiš "není dostatek dat".
3. [DATA] = co diagnostika ukázala, [IM] = co s tím dělat.
4. Plán musí být realistický na {hours_week} hodin týdně.

K DISPOZICI:
- Weakness report: {weakness_json}
- Pattern detection: {patterns_json}

STRUKTURA:
[DATA] Shrnutí diagnostiky (1-2 věty)
[DATA] Top 3 slabiny dle dopadu na výsledek:
  {top_weaknesses}

[IM] Měsíční plán (4 týdny):
  - Týden 1: cíl — konkrétní cvičení, počet hodin, pomůcky
  - Týden 2: cíl
  - Týden 3: cíl
  - Týden 4: review + test (NOVÝ set her)
[IM] Heisman Four Homeworks rozpis:
  1. Tactical puzzles: téma, počet/týden, zdroj: lichess/chesstempo
  2. Annotated master games: konkrétní kniha/games, počet/týden
  3. Game analysis: vlastní hry, struktura: self-review → engine → coach
  4. Reading: konkrétní kapitola/článek, zaměření
[IM] Měsíční cíl:
  - Co konkrétně chceme dosáhnout
  - Jak změříme úspěch (ACPL, win rate v určité fázi, pattern frequency)
[IM] Co NEDĚLAT:
  - Na co se nesoustředit""",
    5: """Vytvoř opening repertoire report pro hráče z {N} her.

K DISPOZICI:
- Cache: data/game_cache/*.json (každá hra má opening_name, ECO)
- Pattern detection: {patterns_json} (cross-reference s openingem)
- ACPL per game, blunder rate per game

PRAVIDLA:
1. Každé tvrzení o výkonnosti v openingu musí být podloženo minimálně 3 hrami v daném zahájení.
2. Pokud počet her pro opening < 3: uveď "nedostatek dat — indikativní".
3. [DATA]/[IM] split.
4. NEVYMÝŠLEJ teoretické varianty — používej jen data z cache.

STRUKTURA:
[DATA] White openings:
  {white_openings}
[DATA] Black openings:
  {black_openings}
[DATA] Nejhorší openingy (top 3 dle ACPL / win rate):
  {worst_openings}
[DATA] Nejlepší openingy (top 3):
  {best_openings}

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
[IM] Tréninkový tip na tento týden:
  - Konkrétní 1-2 varianty k prostudování
  - Konkrétní zdroj (Lichess study, Chessable, kniha, video)""",
}


def build_prompt(template_id: int, data: dict) -> str:
    return PROMPT_TEMPLATES[template_id].format(**data)
