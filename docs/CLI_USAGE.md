# CLI usage — samostatné spouštění bez MCP klienta

Nástroj je navržený tak, aby šel použít i mimo IDE (OpenCode, Codex, …).
Oba skripty spouští **aktuální kód z repozitáře v novém procesu** — obcházejí
případný starý běžící MCP server.

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

## 1. Jedna hra: `scripts/coach_single.py`

Standardní single-game pipeline (stejná jako MCP tool
`lichess_coaching_single_game`, kontrakt v1.1), jen z příkazové řádky.

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

Návratové kódy: `0` = ok nebo degraded, `2` = partial (některé plyny
neanalyzované), `1` = chyba.

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

## 3. Determinismus a cache

- Engine politika: `Threads=1`, `Limit(depth, nodes)`, `Clear Hash` před každým
  top-level callem, cloud eval jen opt-in.
- Cache klíč obsahuje politiku: `data\game_cache\{game}_{color}_d{depth}n{nodes}.json`.
  Staré soubory bez `n…` suffixu se pro novou politiku nepoužijí.
- Stejná hra + stejné parametry ⇒ stejné ACPL, stejná množina vlajkovaných
  tahů, stejný report (ověřeno dvěma cold běhy na `NxKgE4l8` a `lxO3gwd3`).
- Čísla z reportů před zavedením politiky nejsou s novými srovnatelná.

## 4. Řešení potíží

| Symptom | Příčina | Řešení |
|---|---|---|
| `tools_total: 18` neodpovídá | starý proces / jiná větev | spusť z kořene repa, zkontroluj `git log -1` |
| JSON má na začátku BOM nebo je rozbitý | `>` redirect v PowerShellu | použij `--out` |
| `status=partial`, `exit=2` | vyčerpaný budget / timeout enginu | `--mode deep`, případně `--no-cache` |
| `engine … error` | Stockfish se nepodařilo spustit | `stockfish\stockfish-bmi2.exe` + `STOCKFISH_PATH` |
| report je „degraded“ | LLM providery nedostupné | očekávané; report je deterministický |
| proces visí po dokončení | starý skript bez `close_engine()` | použij `coach_single.py` / `mcp_call.py` |
