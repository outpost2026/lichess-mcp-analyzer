# Phase 2 — Build Plan

**Datum:** 2026-07-25 | **Verze:** 2.0 **Navazuje na:** DBCL\_cross\_audit\_artifact.md (v1.0 + audit appendix v1.1), DBCL\_Cross\_Audit\_Report.docx **Status:** 🟡 Phase 2 (detectors done, DBCL designed+audited, ready to implement)


## Current State (2026-07-25 baseline)

| Komponenta | Stav |
| - | - |
| Stockfish 18 BMI2 (Threads=6, Hash=512) | ✅ +24.7% NPS |
| 11 pattern detectoru (A-R) + S kandidat | ✅ vsechny implementovany |
| Pattern J semantika | ⚠️ **BUG** — testuje "+" in move\_san, ma byt board.is\_check() (viz F-007) |
| Analyzovane partie | 22 (RUN\_001 + RUN\_002, depth 12-14) |
| LLM pipeline (NVIDIA/Cerebras/DeepSeek) | ✅ 3 provider, mono + incremental |
| DBCL architektura | ✅ navrzena + auditem verifikovana (PASS WITH CONCERNS) |
| Cross-audit releasu | 21 nalezu, 3 critical, 4 high |
| Tests | 33/33 pass |
| Branch | `debug/phase1-fixes` (commit `c1b095b` + pending changes) |



## P0 — Critical fixes (DBCL blocker, must do first)

Priorita: **NEJVYSSI** — aktivni bug + jednoradkove opravy, ktere jinak znehodnoti DBCL.

### Tasks

- [ ] 

- **F-007: Opravit pattern J semantiku**

  - `pattern\_detector.py:\_detect\_j()`: nahradit podminku `"+" in m.move\_san` → kontrola, zda `board.is\_check()` v pozici pred tahem

  - Overit, ze blok neni zaroven capture (kdyz hrac bere sachujici figuru, neni to "impulsivni blok")

  - Vysvetlivka: soucasna implementace testuje, zda *odehrany tah* dava sach (`+` v SAN), coz je jina promenna nez "hrac byl v sachu a zablokoval"

  - Upravit hypothesis v PatternDef J v `models/pattern.py` pokud nutno

- [ ] 

- **F-002: Propagovat fen\_before do MoveAnalysis**

  - `models/game.py:MoveAnalysis`: pridat pole `fen: str = ""`

  - `services/game\_analyzer.py:\_run\_analyze\_pgn()`: predat `fen\_before = board.fen()` do konstruktoru

  - TOTO umozni DBCL context\_extractoru cist FEN z cache, ne replayovat PGN

- [ ] 

- **F-003: Pridat board.is\_check() do pipeline**

  - Ve stejne smycce `\_run\_analyze\_pgn()`, kde existuje `board`, volat `board.is\_check()` po kazdem tahu

  - Ulozit do MoveAnalysis jako pole `was\_in\_check: bool = False`


## P1 — DBCL core implementation

Priorita: **HIGH** — po P0 je to hlavni prinos teto phase.

### Tasks

- [ ] 

- **Vyuzit existujici analyze\_position(multipv=3) pro engine\_lines**

  - BlunderFactSheet engine\_lines\[\] ziskat volanim `engine\_client.analyze\_position(fen\_before, depth=14, multipv=3)`

  - Existujici kod uz vraci: `rank, score\_cp, mate, pv, pv\_san` — prakticky identicke schema

  - Nepsat novou logiku (viz F-005)

- [ ] 

- **Sloucit eval\_delta\_threshold + context\_extractor do jedneho pruchodu**

  - Nepisat `context\_extractor.py` jako samostatny replay PGN (viz F-004)

  - Misto: v `\_run\_analyze\_pgn()` inline:

    1. Detekovat blunder window (delta \> 300cp || classification == blunder/mistake)

    2. Extrahovat: FEN, is\_check, legal\_moves klasifikovane (captures/king\_moves/blocks/checks)

    3. Zavolat analyze\_position(multipv=3)

    4. Zavolat per-blunder pattern matcher (B, J, S, R, C)

    5. Sestavit BlunderFactSheet

  - Ulozit BlunderFactSheet\[\] jako soucast game\_cache (novy klic `"dbcl\_fact\_sheets"`)

- [ ] 

- **Inject BlunderFactSheet do obou prompt builderu**

  - `llm\_client.py:build\_coaching\_prompt()` — vlozit BlunderFactSheet\[\] misto agregovaneho blobu

  - `game\_llm\_cache.py:\_build\_game\_prompt()` — stejna zmena

  - Pridat guard clause template z DBCL §5.2.4 do obou system promptu

  - Pridat explicitni kontrakt: per-game vrstva nesmi predavat halucinovana data do agregacni

- [ ] 

- **Implementovat narrative\_validator.py**

  - Nazev: `narrative\_validator.py` (NE `validator.py` — konflikt s existujicim, viz F-011)

  - 5 kategorii claimu s operatory (viz Appendix C.4):

    1. piece-on-square → existence v fen\_before

    2. check → rovnost proti was\_in\_check

    3. capture → existence v legal\_moves.captures nebo engine\_lines

    4. eval-cislo → tolerance ±20cp

    5. legalita/negace → negace proti legal\_moves.\*

  - Reject loop: pokud validator fail, zopakovat LLM call s prislusnym guard clause


## P2 — Schema completion & consistency

Priorita: **MEDIUM** — doplnit mezery z auditu, zlepsit kvalitu dat.

### Tasks

- [ ] 

- **Doplnit win\_prob do BlunderFactSheet**

  - `models/game.py:MoveAnalysis` ma pole `win\_prob\_before` a `win\_prob\_after` (aktualne hardcoded 0.0)

  - Implementovat winning-chances sigmoid (DBCL §4.6 transfer z lila: 10/20/30% prahy)

  - Pridat `win\_prob\_delta` do schematu

  - Prepnout klasifikaci z plocheho cp prahu na win% delta

- [ ] 

- **Pridat detector\_version do BlunderFactSheet**

  - Umoznuje odlisit fact sheets vznikle pred/po oprave patternu (viz F-007)

  - Verze = commit hash + timestamp buildu

- [ ] 

- **Integrovat BlunderFactSheet do cache konvence**

  - Resit: `game\_cache.json` jmenuje soubory `\{game\_id\}\_\{color\}\_d\{depth\}.json`

  - `\_load\_cached\_analysis()` ma logiku priblizne shody hloubky

  - BlunderFactSheet\[\] ulozit pod klic `"dbcl\_fact\_sheets"` ve stejnem JSON, ne jako samostatny cache mechanismus

- [ ] 

- **Cross-validace vsech 11 detektoru**

  - Pro kazdy pattern overit: detection\_method odpovida pattern\_name/mechanism

  - F-007 ukazuje, ze pattern J testuje jinou velicinu nez tvrdi hypothesis

  - Pridat contract test: `test\_pattern\_semantic\_contract.py` s 1 pozitivnim + 1 negativnim pripadem na detector


## P3 — Pattern S + Dlouhodobe

Priorita: **LOW** — az po P0-P2.

### Tasks

- [ ] 

- **Pattern S — Capture aversion under check**

  - `models/pattern.py`: pridat `PatternDef(id="S", ...)`

  - Detektor: `centipawn\_loss \> 500 && in\_check && king\_capture\_possible && not king\_capture\_played`

  - Confidence: ~40% (N=2), severity: critical

- [ ] 

- **Cross-audit artifact — predat druhemu LLM k validaci**

  - DBCL\_Cross\_Audit\_Report.docx (Claude) uz existuje

  - Dalsi kolo: predat tentyz artifact dalsimu modelu (DeepSeek?)

- [ ] 

- **FSRS integration**

  - Nahradit SM-2 formuli za `fsrs.Card` + `fsrs.Scheduler`

  - Prvni realny konzument BlunderFactSheet muze byt SRSCard (pole `fen` uz existuje, viz F-009)

- [ ] 

- **Structured logging (P19)**

  - `logger.warning()` per-failed-game

  - `skipped` counter na konci kazdeho batch toolu


## Dependencies & Blockers

| Blocker | Kdo resi | Stav |
| - | - | - |
| Pattern J bug (F-007) | P0 | ULTIAN — blokuje DBCL |
| FEN propagace (F-002) | P0 | 1 radek, bezny |
| Oba prompt buildery (F-008) | P1 | Nutne soubezne |
| Validator spec (F-013) | P1 | Nutno doplnit mapovani |


## Key Files Reference

| Cesta | Ucel |
| - | - |
| `00\_STRATEGIE/DBCL\_cross\_audit\_artifact.md` | Zdrojova architektura + audit appendix |
| `00\_STRATEGIE/DBCL\_Cross\_Audit\_Report.docx` | Claude audit (21 nalezu) |
| `00\_STRATEGIE/evening\_coaching\_2026-07-24.md` | Coaching doc v2 s korekcni poznamkou |
| `src/lichess\_analyzer\_mcp/services/pattern\_detector.py` | 11 detektoru (J bug zde) |
| `src/lichess\_analyzer\_mcp/services/game\_analyzer.py` | \_run\_analyze\_pgn — FEN propagace sem |
| `src/lichess\_analyzer\_mcp/services/engine\_client.py` | analyze\_position(multipv=3) — existujici |
| `src/lichess\_analyzer\_mcp/models/game.py` | MoveAnalysis — pridat fen, was\_in\_check |
| `src/lichess\_analyzer\_mcp/models/pattern.py` | PatternDef + PatternLibrary |
| `src/lichess\_analyzer\_mcp/services/llm\_client.py` | build\_coaching\_prompt — mono vetev |
| `src/lichess\_analyzer\_mcp/services/game\_llm\_cache.py` | \_build\_game\_prompt — incremental vetev |


