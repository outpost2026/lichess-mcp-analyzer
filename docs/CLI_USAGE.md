# CLI usage — samostatné spouštění bez MCP klienta

Nástroj je navržený tak, aby šel použít i mimo IDE (OpenCode, Codex, …).
Všechny skripty spouští **aktuální kód z repozitáře v novém procesu** — obcházejí
případný starý běžící MCP server.

Primární vstup je `scripts/coach.py` (jedna hra, PGN, dávka). Starší skripty
`coach_single.py`, `pgn_to_compact.py`, `analyze_single_game.py` a
`run_single_game_offline.py` zůstávají funkční, ale tisknou deprecation warning.

Všechny příkazy se spouští z kořene repozitáře:

```powershell
cd C:\Users\PC\Documents\Repozitar_Dev\_github\lichess-analyzer-mcp
```

## Předpoklady

| Co | Kontrola |
|---|---|
| Virtuální prostředí | `.\.venv\Scripts\python.exe -V` → Python 3.12.x |
| Stockfish | `stockfish\stockfish-bmi2.exe` existuje |
| Lichess token | v `.env` (`LICHESS_TOKEN=...`); skripty `.env` načtou samy |
| LLM providery | volitelné; bez nich je report deterministický (`report_source=deterministic`) |

Ověření, že server i tools jsou dostupné:

```powershell
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_workspace_info
```

`tools_total` musí být `18`.

## 1. Jednotný CLI: `scripts/coach.py`

Jeden vstupní bod pro všechny reálné workflow. **Výchozí výstup je compact
JSON 2.0** (schema `schemas/single_game_v2_compact.json`); schema 1.1 je
opt-in přes `--format detailed`.

```powershell
# jedna hra -> compact 2.0 (výchozí)
.\.venv\Scripts\python.exe -X utf8 scripts\coach.py --game-id FVhqtv1S --username systeq --no-llm --out data\reports\FVhqtv1S.json

# explicitně schema 1.1 (debugging / cross-game)
.\.venv\Scripts\python.exe -X utf8 scripts\coach.py --game-id lxO3gwd3 --format detailed --out detailed.json

# oba tvary v jednom payloadu
.\.venv\Scripts\python.exe -X utf8 scripts\coach.py --game-id lxO3gwd3 --format both --out both.json

# lokální PGN, plně offline
.\.venv\Scripts\python.exe -X utf8 scripts\coach.py --pgn-file data\runs\game.pgn --color black --no-llm --out out.json

# posledních N her hráče -> pole compact her
.\.venv\Scripts\python.exe -X utf8 scripts\coach.py --username systeq --batch 3 --no-llm --out data\runs\batch.json

# totéž jako NDJSON (jeden JSON na řádek)
.\.venv\Scripts\python.exe -X utf8 scripts\coach.py --username systeq --batch 3 --ndjson --out data\runs\batch.ndjson
```

| Parametr | Význam |
|---|---|
| `--game-id ID` | Lichess ID (8 znaků) |
| `--pgn-file PATH` | alternativa k `--game-id`; lokální PGN |
| `--username NAME` | Lichess nick; určí barvu automaticky |
| `--color white\|black\|both` | `both` analyzuje obě strany (vrací pole) |
| `--batch N` | posledních N her z `--username`; jen s `--format compact` |
| `--depth N` | výchozí 14 |
| `--mode fast\|deep` | `fast` = 60 s deadline, `deep` = 120 s |
| `--format compact\|detailed\|both\|full` | `compact` výchozí; `full` = deprecated alias pro `detailed` |
| `--no-llm` | žádný LLM provider; report je deterministický |
| `--no-cache` | vynutí cold analýzu |
| `--nodes-cap N` | přepíše `NODE_CAPS[depth]` jen v tomto procesu |
| `--out PATH` | JSON do souboru (výchozí stdout) |
| `--ndjson` | jen pro `--batch`: jeden JSON na řádek |
| `--quiet` | potlačí progress a agregát na stderr |

Exit kódy: **0** ok, **1** validační chyba (argumenty / neplatné PGN), **2**
I/O chyba, **3** engine chyba (Stockfish chybí nebo timeout), **4** síťová
chyba. JSON jde na stdout nebo do `--out`; progress a agregáty jdou na stderr,
takže `coach.py ... | jq` funguje.

Batch na konci vypíše agregát na stderr:

```text
aggregate: {"games": 3, "mean_acpl": 191.4, "flags": {"blunder": 2, "mistake": 6, "inaccuracy": 24}, "patterns": {"B": 2, "T": 2}}
```

### Starší varianta: `scripts/coach_single.py` (deprecated)

Standardní single-game pipeline (kontrakt v1.1), jen z příkazové řádky. Stále
funguje, ale nové příkazy piš přes `coach.py`.

```powershell
# základní: hra podle ID, barva se určí z username
.\.venv\Scripts\python.exe -X utf8 scripts\coach_single.py lxO3gwd3 --username systeq

# bez username, barva explicitně
.\.venv\Scripts\python.exe -X utf8 scripts\coach_single.py lxO3gwd3 --color black

# hlubší režim + výstup na konkrétní cestu
.\.venv\Scripts\python.exe -X utf8 scripts\coach_single.py lxO3gwd3 --color black --mode deep --out data\reports\lxO3gwd3.json

# z lokálního PGN (bez Lichess API)
.\.venv\Scripts\python.exe -X utf8 scripts\coach_single.py --pgn data\reports\game.pgn --color black

# vynutit cold běh (ignorovat cache)
.\.venv\Scripts\python.exe -X utf8 scripts\coach_single.py lxO3gwd3 --color black --no-cache

# jen souhrn, bez těla reportu
.\.venv\Scripts\python.exe -X utf8 scripts\coach_single.py lxO3gwd3 --color black --quiet
```

| Parametr | Význam |
|---|---|
| `game_id` | Lichess ID (8 znaků) |
| `--pgn PATH` | alternativa k `game_id`; cesta relativně k repozitáři |
| `--username` | tvůj Lichess nick; určí barvu automaticky |
| `--color white\|black` | fallback, když není username |
| `--depth N` | výchozí `14` (auto politika: 12/14/16/18) |
| `--mode fast\|deep` | `fast` = 60 s deadline, `deep` = 120 s |
| `--out PATH` | výchozí `data\reports\single_game_{id}_{ts}.json` |
| `--no-cache` | vynutí nový výpočet |
| `--quiet` | nevypisuje markdown report |

Návratové kódy staršího skriptu: `0` = ok nebo degraded, `2` = partial
(některé plyny neanalyzované), `1` = chyba. Nový `coach.py` používá jednotné
kódy 0–4 viz výše.

Výstupní JSON obsahuje `analysis.acpl`, `analysis.accuracy`, `flagged_moves`,
`patterns`, `report`, `engine` (politika) a `timings`.

## 2. Libovolný tool: `scripts/mcp_call.py`

Tool se volá přímo jako Python funkce. Argumenty se předávají jako **jeden JSON
objekt v jednoduchých uvozovkách**; uvnitř JSONu jen dvojité uvozovky.

```powershell
# seznam dostupných toolů a jejich signatur
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py --list

# výsledek do souboru místo na stdout
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_player_profile --args '{"username":"systeq"}' --out data\reports\profile.json
```

### Pravidla quotingu (PowerShell)

- Celý JSON do `'…'` (single quotes) — PowerShell uvnitř nic neinterpoluje.
- Uvnitř jen `"…"` (double quotes), nikdy escapované `\"`.
- Cesta s mezerami do `"…"`.
- Nepoužívej `>` pro JSON výstup — používej `--out` (redirect míchá encoding
  a u dlouhých běhů zdržuje ukončení procesu).

### Příklady pro všech 18 toolů

```powershell
# 1. profil hráče
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_player_profile --args '{"username":"systeq"}'

# 2. stažení partií
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_fetch_games --args '{"username":"systeq","max_games":10}'

# 3. cache index her
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_games_index --args '{"username":"systeq"}'

# 4. analýza jedné hry (bez coaching reportu)
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_analyze_game --args '{"game_id":"lxO3gwd3","username":"systeq"}'

# 5. analýza pozice (FEN)
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_analyze_position --args '{"fen":"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1","depth":14}'

# 6. opening explorer
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_opening_explorer --args '{"fen":"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1","source":"lichess"}'

# 7. diagnostika slabin
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_diagnose_player --args '{"username":"systeq","max_games":20}'

# 8. patterny
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_match_patterns --args '{"username":"systeq","max_games":20}'

# 9. pending analýza
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_analyze_pending --args '{"username":"systeq","max_games":5}'

# 10. anonymní session
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_analyze_anonymous_session --args '{"game_ids":"lxO3gwd3"}'

# 11. import PGN
$pgn = Get-Content data\reports\game.pgn -Raw
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_import_pgn --args (@{pgn=$pgn;color="black"} | ConvertTo-Json -Compress)

# 12. workspace info
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_workspace_info

# 13. single game coaching
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_coaching_single_game --args '{"game_id":"lxO3gwd3","username":"systeq","mode":"fast"}' --out data\reports\single.json

# 14. cross-game coaching
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_coaching_cross_game --args '{"username":"systeq","max_games":20}'

# 15. opening report
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_coaching_opening_report --args '{"username":"systeq","max_games":20}'

# 16. pool soupeřů
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_coaching_opponent_pool --args '{"game_ids":"lxO3gwd3,NxKgE4l8","username":"systeq"}'

# 17. tréninkový plán
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_coaching_training_plan --args '{"username":"systeq","max_games":20,"hours_per_week":5}'

# 18. uložení reportu na disk
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_persist_report --args '{"kind":"single_game","game_id":"lxO3gwd3","username":"systeq","format":"both"}'
```

Poznámky k jednotlivým toolům:

- `lichess_analyze_game` vrací strukturovanou analýzu, ne markdown report.
  Pro report použij `lichess_coaching_single_game` nebo `scripts\coach_single.py`.
- `lichess_persist_report` umí `kind`: `single_game`, `cross_game`,
  `opponent_pool`, `training_plan`, `opening_report`, `diagnosis`.
  `target="kb"` zapisuje i do B2B-Knowledge-Base.
- `ctx` parametr (MCP sampling) nemá v CLI smysl; nechává se `None`, takže
  report vzniká z deterministického fallbacku, pokud nejsou LLM API klíče.
- `lichess_import_pgn` s dlouhým PGN: použij `ConvertTo-Json -Compress` jako
  v příkladu výše, ať zůstane platný JSON.

## 3. Kompaktní JSON 2.0 (ETL bez LLM)

Compact 2.0 je **výchozí** výstup `coach.py`. Sekce výše pokrývá všechny
případy; zde jen minimální příklady a rozdíly.

```powershell
# hra podle ID
.\.venv\Scripts\python.exe -X utf8 scripts\coach.py --game-id Sl1s8KmU --username systeq --no-llm --out data\reports\compact_Sl1s8KmU.json

# lokální PGN
.\.venv\Scripts\python.exe -X utf8 scripts\coach.py --pgn-file data\reports\game.pgn --color white --no-llm --out out.json

# jiný strop uzlů (mění i cache klíč)
.\.venv\Scripts\python.exe -X utf8 scripts\coach.py --game-id Sl1s8KmU --color white --nodes-cap 200000 --out out.json
```

`scripts/pgn_to_compact.py` je deprecated shim nad `coach.py`; argumenty
`--game-id`, `--pgn-file`, `--color`, `--depth`, `--nodes-cap`, `--mode`,
`--out`, `--no-cache` zůstávají. Nové skripty piš proti `coach.py`.

Výstup se validuje proti `schemas/single_game_v2_compact.json`. Detaily,
null/omission politika a prompt pro LLM: `docs/COMPACT_JSON_FOR_LLM.md`.

MCP tool `lichess_coaching_single_game` umí totéž přes `output_format`:
`compact` (výchozí, 2.0), `detailed` (kontrakt 1.1), `both`;
`full` je deprecated alias pro `detailed`.

## 4. Determinismus a cache

- Engine politika: `Threads=1`, `Limit(depth, nodes)`, `Clear Hash` před každým
  top-level callem, cloud eval jen opt-in.
- Cache klíč obsahuje politiku: `data\game_cache\{game}_{color}_d{depth}n{nodes}.json`.
  Staré soubory bez `n…` suffixu se pro novou politiku nepoužijí.
- Stejná hra + stejné parametry ⇒ stejné ACPL, stejná množina vlajkovaných
  tahů, stejný report (ověřeno dvěma cold běhy na `NxKgE4l8` a `lxO3gwd3`).
- Čísla z reportů před zavedením politiky nejsou s novými srovnatelná.

## 5. Řešení potíží

| Symptom | Příčina | Řešení |
|---|---|---|
| `tools_total: 18` neodpovídá | starý proces / jiná větev | spusť z kořene repa, zkontroluj `git log -1` |
| JSON má na začátku BOM nebo je rozbitý | `>` redirect v PowerShellu | použij `--out` |
| `status=partial` (starší skript) | vyčerpaný budget / timeout enginu | `--mode deep`, případně `--no-cache` |
| `engine … error` | Stockfish se nepodařilo spustit | `stockfish\stockfish-bmi2.exe` + `STOCKFISH_PATH` |
| report je „degraded“ | LLM providery nedostupné | očekávané; report je deterministický |
| `pv_unavailable` v compact JSON | blunder/mistake bez engine line i po retry | explicitní mezera; nepředstírej, že pozice je jednoduchá |
| proces visí po dokončení | starý skript bez `close_engine()` | použij `coach.py` / `mcp_call.py` |
