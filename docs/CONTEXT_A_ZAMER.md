# Context a zamer — lichess-analyzer-mcp

**Datum:** 2026-07-18 | **Autor:** Ondrej Sousek (outpost2026)
**Verze:** 1.0 | **Status:** Phase 1 complete (repo init + tools + services)
**Repo:** `_github/lichess-analyzer-mcp/`

---

## 1. Zamer projektu

Tento repozitar vznika se **dvojakym ucelem**:

### 1.1 Ucel A — Analyza a trenink sachove hry

Personalizovany MCP server, ktery:

- Stahuje a analyzuje partie z Lichess pres berserk API
- Vyhodnocuje kazdy tah pomoci Stockfish engine (centipawn loss, klasifikace)
- Detekuje **17 vzorovych patternu (A-Q1)** importovanych z `chess_pattern_v5.json`
- Aplikuje **spaced repetition (FSRS/SM-2)** na osobni chyby — karty s FEN pozici a spravnym tahem
- Diagnostikuje fazove slabiny (opening / middlegame / endgame), unikajici otvoreni a takticke blind spots
- Vysledky perzistentne uklada do **B2B-Knowledge-Base** pro casovou trace a long-term analyzu

### 1.2 Ucel B — Adaptace nove IT dovednosti: MCP ekosystem

Tento projekt je zaroven **vyukovy use-case** pro mastering MCP (Model Context Protocol) ekosystemu:

- Tvorba MCP serveru od nuly: architektura, tool design, transport, error handling
- Prakticke overeni konceptu na **realnych kazustikach** (sachove partie nejsou dummy data)
- Agentni workflow orchestrace: LLM + MCP tools + Stockfish + Lichess API = heterogenni pipeline
- Cross-repo patterny: co se osvedcilo v `mcp-local-server`, `linkedin-mcp-custom`, `MCP-Jobs`
- B2B-Knowledge-Base jako centralni znalostni vrstva pro MCP ekosystem

**Klíčové tvrzení:** Dovednosti ziskane stavbou tohoto serveru jsou **prime prenositelne** na jine doménové oblasti (CNC, HR, finance, zdravotnictvi) v Q3-Q4/2026 a dale.

---

## 2. Souvislosti a pozadi

### 2.1 O autorovi (relevantni fragmenty)

- **IT profil:** 20+ let zkusenosti (CISO, infrastructure, security), aktualne deep-dive do AI/LLM ekosystemu
- **Sachovy profil:** ~1800-2000 ELO (Lichess/Chess.com), aktivni hrac s metakognitivnim pristupem
- **MCP zkusenost:** 3 hotove MCP servery v workspace (dole)
- **Filozofie:** "Build tools for yourself first. If they solve a real problem, they solve a general one."

### 2.2 Vychozi data — chess_pattern_v5.json

Analyza 21 partii (2023-2026) odhalila:

| Metrika | Hodnota |
|---------|---------|
| Celkem partii | 21 |
| Vyhry | 19 (90.5%) |
| Patternu identifikovano | 17 (A-Q1) |
| Autorovych blunderu | 10 |
| Metacognition ON prum. ELO | ~1975 |
| Metacognition OFF prum. ELO | ~1675 |
| **Rozdil = ~300 ELO** | **Nejvetsi paka pro zlepseni** |

**Klicove insighty:**
- Pattern **B** (Automatic grab) — 3x, nejcastejsi autor error
- Pattern **O** (Repetition avoidance greed) — jedina prohra v datasetu
- Pattern **I** (Bait trap) — 3x, nejsilnejsi zbran
- White/Black asymetrie: jako White 8 blunderu vs Black 2 blundery
- Metakognice neni aplikovana pod tlakem — casem nebo v casual modu

### 2.3 Proc automatizace?

Predchozi analyza probehla **rucne** — LLM + manualni zapis 21 partii. To je:
- **Casove:** ~hodiny prace na 21 partich (neskaluje na 100+)
- **Nepresne:** subjektivni ELO odhady, chybi Stockfish centipawn loss
- **Bez trace:** snapshot bez historie, neni mozny long-term trend
- **Bez treninku:** chybi SRS system pro uceni se z vlastnich chyb

MCP server resi vsechny 4 problemy jednim deploymentem.

---

## 3. Soucasny MCP stack ve workspace

Ve `_github/` existuji 3 aktivni MCP servery + tento novy:

| Server | Ucel | Tech stack | Toolu | Testu | Status |
|--------|------|------------|-------|-------|--------|
| **cnc-tools** (mcp-local-server) | CNC pipeline: FS, git, VCF analyza, KB search | Python 3.11, `mcp[cli]`, uv, pytest | 20 | 67 | ✅ aktivni |
| **linkedin-analyzer** (linkedin-mcp-custom) | LinkedIn saved jobs EROI scoring + KB write | Python 3.12, FastMCP, Patchright | 8 | 25 | ✅ aktivni |
| **mcp-jobs** (MCP-Jobs) | CZ job portal scraping + boolean match | Python 3.11, FastMCP, BS4 | 5 | 97 | ✅ aktivni |
| **lichess-analyzer-mcp** (tento) | Chess analysis + pattern detekce + SRS | Python 3.12, `mcp`, berserk, python-chess | 7 | 13 | 🆕 Phase 1 |

**Dulezite:** Vsechny 3 aktivni servery pouzivaji **stdio transport** a jsou registrovany v `opencode.jsonc` jako local servery. Tento server se pripoji jako ctvrty.

### 3.1 Lekce z existujicich serveru

**Z cnc-tools:**
- Rozsahla knihovna toolu (20) demonstruje komplexitu MCP serveru
- Tools-of-tools pattern: VCF analyza, ACI lookup, KB search
- Session state management (`.ai_state.json`) pro cross-session perzistenci
- Cachovani (TTLCache + `@cached` dekorator)
- Audit log pro vsechny operace

**Z linkedin-analyzer:**
- FastMCP framework (jednodussi nez nizkourovny `mcp[cli]`)
- EROI scoring model = transferovatelny na dalsi domeny
- Browser-based scraping (Patchright) — anti-bot techniky
- KB write-back pattern (analyza -> 02_ANALYZY/)

**Z MCP-Jobs:**
- Boolean AST matcher (AND/OR/NOT) — pouzitelny pro jine domeny
- Multi-portal scraping architektura (BaseScraper + implementace)
- YAML config pipeline
- L2 (Resources) + L3 (Prompts) maturity

### 3.2 Architektonicke rozhodnuti

Po resersi 10+ existujicich chess MCP serveru (viz sekce 4) bylo rozhodnuto:

| Rozhodnuti | Dusledek |
|------------|----------|
| **FastMCP** (ne nizkourovny mcp[cli]) | Jednodussi API, ale nizsi kontrola nad transportem; zvolen `mcp>=1.0.0` kvuli kompatibilite s ostatnimi servery |
| **Berserk** (ne raw HTTP) | Lichess API wrapper, spravuje auth + rate limiting |
| **python-chess** (ne Stockfish CLI) | PGN/FEN parsing + UCI wrappery + game tree navigace |
| **py-fsrs** (ne SM-2) | FSRS je moderni standard, lepsi retention pri mene opakovani; rozhodnuti ceka na potvrzeni |
| **KB persistence** | Vysledky se zapisuji do B2B-Knowledge-Base /02_ANALYZY/02_chess/ a /04_KNOWLEDGE_BASE/02_chess/ |
| **Bez cache v MVP** | Vsechno real-time z Lichess + Stockfish; cache prijde v Phase 2 |

---

## 4. Reserse github portfolii — zdroje

### 4.1 Metodika vyberu TOP 4 kandidatu

Prohledano 10+ chess MCP serveru na GitHubu. Hledana kriteria:
1. **Funkcnost:** Stahuje partie, analyzuje Stockfishem, vraci strukturovane vysledky
2. **Architektura:** Cista, modularni, maintainovana
3. **Unikatnost:** Neceho se uci (ne jen wrapper okolo Lichess API)
4. **Kompatibilita:** Python, stdio transport

#### TOP 4 kandidati

| # | Repozitar | Hvezdy | Stack | Focus | Nase odlisnost |
|---|-----------|--------|-------|-------|----------------|
| 1 | **chess-coach-mcp** | ~50 | Python + FastMCP + Stockfish | Analyza partii, trenink | Chybi SRS, chybi pattern library, single-game |
| 2 | **chessagine-mcp** | ~30 | Python + FastMCP + Stockfish + multiple engines | Multi-engine analyza | Chybi personalizace, chybi KB trace |
| 3 | **chess-rocket** | ~80 | Python + SM-2 SRS + Stockfish | Spaced repetition na sachu | SM-2 (ne FSRS), chybi pattern detekce |
| 4 | **chess-com-lichess-org-mcp** | ~120 | Python + 54 toolu | Siroky wrapper (lichess + chess.com) | Prilis obecny, chybi diagnostika |

**Zaver reserse:** Zadny existujici MCP server nekombinuje:
1. Pattern detection library (17 A-Q1 patternu z vlastni analyzy)
2. FSRS spaced repetition na osobni chyby
3. Diagnostiku napric vice partiemi (fazove slabiny, leaky openings)
4. KB persistence s timeline

**Proto vznika tento projekt.**

### 4.2 Zdroje mimo GitHub

- **Lichess API dokumentace** — berserk pytoni wrapper, REST API, streaming
- **Stockfish UCI protokol** — `python-chess` engine wrapper
- **FSRS paper** — "A Stochastic Shortest Path Algorithm for Optimizing Spaced Repetition"
- **FastMCP / MCP SDK specifikace** — oficialni dokumentace Anthropic/opencode

---

## 5. Navrh reseni

### 5.1 Architektura (aktuální — Phase 1)

```
LLM klient (opencode/Claude)
    │
    ▼ JSON-RPC 2.0 (stdio)
    │
lichess-analyzer-mcp (FastMCP)
    │
    ├── 7 toolu ─────────────────────► interakce s LLM
    │
    ├── src/services/lichess_client.py ──► berserk ──► lichess.org
    ├── src/services/engine_client.py ───► Stockfish (UCI, python-chess)
    ├── src/services/game_analyzer.py ───► per-move evaluace + klasifikace
    ├── src/services/diagnostician.py ───► cross-game weakness report
    ├── src/services/pattern_detector.py ► 17 patternu A-Q1
    └── src/services/srs_engine.py ─────► FSRS/SM-2 spaced repetition
    │
    ▼
B2B-Knowledge-Base/
    ├── 02_ANALYZY/02_chess/       ← analyzy, diagnozy
    └── 04_KNOWLEDGE_BASE/02_chess/ ← pattern knihovna, SRS karty
```

### 5.2 Toolset (7 toolu, vse implementovano)

| Tool | Vstup | Vystup | Stav |
|------|-------|--------|------|
| `lichess_fetch_games` | username, max_games, source | Seznam her s metadaty | ✅ |
| `lichess_analyze_game` | game_id/PGN, color, depth | Per-move analyza + ACPL | ✅ |
| `lichess_analyze_position` | FEN, depth, use_cloud | Stockfish eval + PV lines | ✅ |
| `lichess_opening_explorer` | FEN, source (lichess/masters) | Statistiky otvoreni | ✅ |
| `lichess_player_profile` | username | Ratingy, statistiky | ✅ |
| `lichess_diagnose_player` | username, max_games, depth | Cross-game slabiny, leaky openings | ✅ |
| `lichess_match_patterns` | username, max_games, depth | Detekce patternu A-Q1 | ✅ |

### 5.3 Pattern detection engine (17 patternu A-Q1)

Implementovano 6 detectoru (A, B, G, O, P, Q) v `src/services/pattern_detector.py`.
Zbylych 11 (C, D, E, F, H, I, J, K, L, M, N, Q1) prijde v Phase 2-3.

Kazdy pattern ma:
- **id** (A-Q1) + nazev
- **mechanismus** — proc k chybe dochazi
- **IT analogie** — preklenuti do IT sveta
- **detekcni metoda** — Stockfish eval + move classification
- **mitigace** — konkretni ritual nebo pravidlo
- **severity** — critical > high > medium > low

### 5.4 SRS engine (FSRS/SM-2)

Aktualni implementace v `src/services/srs_engine.py` pouziva **zjednoduseny SM-2** (SM-2 formula: `interval * (2.5 - 0.1*(5-quality))`). 

Pro Phase 2 se zvyazuje upgrade na **py-fsrs** (knihovna `py-fsrs>=0.1.0` v dependencies).

**Porovnani SM-2 vs FSRS:**

| Kriterium | SM-2 | FSRS |
|-----------|------|------|
| Parametry | 1 (easiness factor) | 3 (stability, difficulty, retrievability) |
| Personalizace | Globalni EF na vsechny karty | Per-card adaptace |
| Kalibrace | ~10 review | ~20 review |
| Retention efficiency | ~70-75% | ~85-90% (o 30% mene opakovani) |
| Implementace | Jednoducha, ~20 radek | Knihovna (py-fsrs), ~bez prace |

**Rozhodnuti:** ceka na potvrzeni autora.

### 5.5 Struktura repozitare

```
lichess-analyzer-mcp/
├── pyproject.toml           ← Python project config
├── .python-version          ← Python 3.12
├── .gitignore
├── src/
│   ├── server.py            ← FastMCP entry + registrace toolu
│   ├── __init__.py
│   ├── models/              ← Datove modely (dataclasses)
│   │   ├── game.py          ← GameSummary, MoveAnalysis, GameAnalysis
│   │   ├── analysis.py      ← PositionAnalysis, WeaknessReport
│   │   ├── pattern.py       ← PatternDef, PatternMatch, PatternLibrary
│   │   ├── srs_card.py      ← SRSCard, FSRSState
│   │   └── player_profile.py ← PlayerProfile, OpeningStats
│   ├── services/            ← Sluzby
│   │   ├── lichess_client.py   ← berserk wrapper
│   │   ├── engine_client.py    ← Stockfish UCI wrapper
│   │   ├── game_analyzer.py    ← per-move analyza + klasifikace
│   │   ├── diagnostician.py    ← cross-game weakness report
│   │   ├── pattern_detector.py ← 6/17 pattern detectoru
│   │   └── srs_engine.py       ← SM-2 spaced repetition
│   ├── tools/               ← Implementace MCP toolu
│   │   ├── fetch_games.py
│   │   ├── analyze_game.py
│   │   ├── analyze_position.py
│   │   ├── opening_explorer.py
│   │   ├── player_profile.py
│   │   ├── diagnose_player.py
│   │   └── match_patterns.py
│   ├── kb/
│   │   └── writer.py        ← KB persistence layer
│   └── patterns/
│       └── __init__.py
├── tests/
│   └── test_services.py     ← 9 unit testu
├── scripts/
│   └── run_pipeline.py      ← CLI batch pipeline
└── docs/
    └── CONTEXT_A_ZAMER.md   ← tento soubor
```

---

## 6. Odůvodnění vzniku — dualita ucelu

### 6.1 Proc neni resenim pouhych 50 radku Pythonu s berserkem?

Lichess API ma jednoduchy REST endpoint `GET /games/export/{username}`. Proc stavi cely MCP server?

Protoze cilem neni **stahnout par partii**, ale vybudovat **ekosystem**:

1. **Agentni workflow:** LLM neni jen dotazovaci rozhrani — orchestrator, ktery rozhoduje *kdy* a *proc* spustit jaky tool
2. **Pattern library:** 17 vzoru neni nahodnych, vznikly analyzou 21 partii s LLM-asistovanou metakognici
3. **Spaced repetition:** Drill blunderu bez SRS = zbytecna prace (Ebbinghaus krivka zapominani)
4. **KB trace:** Diagnoza dnes je snapshot, diagnoza za mesic je trend. Bez KB nevidis progres.
5. **Transfer:** Pokud umim postavit chess analyzer MCP server, umim postavit:
   - MCP server pro analyzu CNC vyrobku na zaklade VCF dat
   - MCP server pro screning LinkedIn inzeratu s EROI scoringem
   - MCP server pro real-time monitoring infrastruktury s alertingem
   - **Obecne:** libovolny MCP server, ktery kombinuje externi API + lokalni engine + KB persistence

### 6.2 Přenositelnost na Q3-Q4/2026 a dále

| Dovednost | Ziskana z | Kam se prenasi |
|-----------|-----------|----------------|
| MCP architektura (stdio transport, tool design) | Tento + 3 dalsi MCP servery | Libovolny MCP-based ekosystem |
| Agentni orchestrace (LLM decides tool call) | Kazdy den prace s opencode | AI-native aplikace |
| Multi-API pipeline (Lichess + Stockfish + KB) | Tento projekt | Heterogenni data pipelines |
| Boolean matching + scoring | MCP-Jobs + linkedin-analyzer | Filtrovacich systemy (job boards, e-shopy) |
| Pattern detection over time series | Tento projekt (sachove partie = time series evaluaci) | Monitoring, anomaly detection |
| Spaced repetition na real data | Tento projekt (FSRS na blundery) | Vzdelavaci platformy, skill management |
| KB jako znalostni vrstva MCP ekosystemu | Vsechny 4 MCP servery + B2B-Knowledge-Base | Enterprise knowledge management |
| FastMCP framework | linkedin-analyzer + MCP-Jobs + tento | Vsechny dalsi MCP projekty |

### 6.3 EROI scoring (zhodnoceni investice)

| Kriterium | Vaha | Skore | Zduvodneni |
|-----------|------|-------|------------|
| Domenova znalost (sachy + Lichess API) | 35% | 9/10 | Znam sachy, znam Lichess API, berserk pouzivan |
| Technologie (FastMCP + Python + Stockfish) | 25% | 9/10 | Overeny stack, vsechny knihovny zname |
| Role (MCP expert v ekosystemu) | 20% | 8/10 | 3 servery za sebou, dalsi posiluje expertizu |
| Ruzst / unikatnost (pattern library + SRS) | 10% | 7/10 | Zadny existujici MCP server nema pattern library |
| Formal (MIT + dokumentace) | 5% | 6/10 | Standard, neni potreba vyssi |
| Lokace (100% local) | 5% | 10/10 | Stockfish lokalne, Lichess API pres internet |
| **Celkem** | **100%** | **8.5/10** | **Doporucono k realizaci** |

---

## 7. Aktualni stav (Phase 1 — hotovo)

### Co je implementovano

| Komponenta | Stav | Poznamka |
|------------|------|----------|
| Repo struktura | ✅ | `git init` committed (33 files, 1581 lines) |
| Vsechny modely (5) | ✅ | Game, Analysis, Pattern, SRSCard, PlayerProfile |
| Vsechny services (6) | ✅ | lichess/engine client, game_analyzer, diagnostician, pattern_detector, srs_engine |
| Vsechny tools (7) | ✅ | fetch, analyze, position, explorer, profile, diagnose, match |
| KB writer | ✅ | Zapis do /02_ANALYZY/02_chess/ a /04_KNOWLEDGE_BASE/02_chess/ |
| CLI pipeline | ✅ | `scripts/run_pipeline.py` — batch analyza + KB write |
| Testy (9) | ✅ | Unit testy modelu |
| Dokumentace | ✅ | Tento soubor |

### Co chybi k behu (blockery)

1. **Stockfish binary** — `engine_client.py` hleda v PATH + `C:\Program Files\Stockfish\stockfish.exe`. Neni nainstalovan.
2. **LICHESS_TOKEN** — token vytvoren (`MCP-analyser` s full scope), neni nasazen jako env var.
3. **`uv sync`** — dependencies neinstalovany (berserk, python-chess, mcp, httpx, py-fsrs).
4. **FSRS vs SM-2** — ceka na rozhodnuti autora.
5. **open code registrace** — server neni pridan do `opencode.jsonc`.

### Dalsi kroky (Phase 2-4)

```
Phase 2 — FSRS upgrade + cache
├── py-fsrs integrace
├── SRS card creation z blunder analysis
├── Lichess cloud eval cache (TTL)
└── Due cards tool

Phase 3 — Plna pattern detekce
├── Zbylych 11 detectoru (C, D, E, F, H, I, J, K, L, M, N, Q1)
├── Ritual effectiveness tracking
├── ELO trend + metacognition ratio
└── Vizualizace (graf pokroku)

Phase 4 — KB pipeline + EROI
├── Automaticka analyza kazdy tyden
├── EROI scoring pro kazdou analyzu
├── Cross-player comparison (friendly)
└── Open source publikace (pokud povoli)
```

---

## 8. Dodatky

### 8.1 Klicove principy

1. **Bilingualni** — EN v kodu a logech, CZ v KB vystupech a dokumentaci
2. **Fail fast** — pri chybe API / engine vrat chybu, nepadni cely server
3. **Minimalni dependencies** — cim mene knihoven, tim lepsi udrzitelnost
4. **Test first** — Phase 1 ma 9 testu, Phase 2 ciluje na 30+
5. **KB je zdroj pravdy** — vysledky se ukladaji, nikdy nemizi

### 8.2 Co neni v scope (Phase 1)

- Frontend / GUI
- Chess.com API (jen Lichess v MVP)
- Multi-player analyza
- Turnajova priprava
- Opening explorer nad vlastnimi partiemi
- Cross-platform deployment (pouze Windows 11 v tuto chvili)

### 8.3 Odkazy

- Repo: `_github/lichess-analyzer-mcp/` → `https://github.com/outpost2026/lichess-mcp-analyzer`
- KB baseline: `_github/B2B-Knowledge-Base/02_ANALYZY/02_chess/chess_self_analysis_baseline_2026-04.md`
- Pattern library: `_github/B2B-Knowledge-Base/04_KNOWLEDGE_BASE/02_chess/player_pattern_library_v1.json`
- Strategy doc: `_github/B2B-Knowledge-Base/00_STRATEGIE/02_chess/chess_mcp_strategy_v1.md`
- Zdrojova data: `_github/Source_raw/Json/chess_pattern_v5.json`
- opencode config: `C:\Users\PC\.config\opencode\opencode.jsonc`
