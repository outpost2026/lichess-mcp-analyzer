# game_full 1.0 - merged timeline obou barev

**Verze:** 1.0 | **Datum:** 2026-11-14 | **Status:** implementováno
**Kód:** `src/lichess_analyzer_mcp/services/timeline.py`
**Schéma:** `schemas/game_full_v1.0.json`
**Rozhodnutí:** D7a (`AUDIT_INTEGRATION_2026-11-13.md`) - název `game_full`, verze `1.0`
**CLI:** `scripts/coach.py --format game-full`

---

## 1. Co to je

`game_full` je **merge vrstva**, ne nová analýza. Dual cache už dnes měří každý
půltah právě jednou: bílý běh měří tahy Bílého, černý běh tahy Černého. Merge
z těchto dvou `GameAnalysis` postaví jednu časovou osu, kde

- každý půltah (`ply`) je tam **právě jednou**,
- všechna eval pole jsou **White POV**,
- `cp_loss` zůstává **velikost ztráty** (nikdy se nepřeklápí),
- co nebylo změřeno, je `null` - nikdy nula a nikdy odhad.

Merge **nesmí** spustit engine. Když chybí jeden pohled, výsledek je
`status="partial"` a díra je pojmenovaná; dopočítat ji by znamenalo druhý běh,
což je jiný produkt.

## 2. Tvar payloadu

```json
{
  "schema": "game_full",
  "v": "1.0",
  "pov": "white",
  "game": {"id": "...", "white": "...", "black": "...", "result": "1-0",
           "opening": "...", "eco": "...", "time_control": "600+0",
           "date": "...", "url": "..."},
  "status": "complete",
  "plies_total": 78,
  "missing_plies": [],
  "unanalyzed_plies": [],
  "coverage": {"white_plies": 39, "black_plies": 39, "merged_plies": 78,
               "expected_plies": 78, "missing_colours": []},
  "source": {
    "white": {"available": true, "mode": "fast", "acpl": 24.1, "moves_measured": 39},
    "black": {"available": true, "mode": "fast", "acpl": 31.7, "moves_measured": 39}
  },
  "plies": [
    {"ply": 1, "mover_color": "white", "san": "e4", "uci": "e2e4",
     "class": "best", "cp_loss": 0.0,
     "eval_before_mover_cp": 20.0, "eval_after_mover_cp": 18.0,
     "eval_before_white_cp": 20.0, "eval_after_white_cp": 18.0,
     "win_prob_white_before": 0.53, "win_prob_white_after": 0.52,
     "fen_before": "...", "best": "d4", "rank": 1, "analyzed": true}
  ]
}
```

| Pole | Význam |
|---|---|
| `pov` | vždy `white`; jiná hodnota je validační chyba |
| `status` | `complete` jen při známém `plies_total`, všech plies, žádném unmeasured a obou barvách |
| `plies_total` | počet půltahů z průchodu PGN; `null` u legacy cache bez pole (T2.2) - nikdy odhad |
| `missing_plies` | plies v `1..plies_total`, které nemá žádná analýza; prázdné, když je `plies_total` neznámý |
| `unanalyzed_plies` | plies přítomné v payloadu, ale explicitně nezměřené (engine timeout/budget) |
| `coverage` | počty po barvách + `missing_colours` (barvy bez jakékoli analýzy) |
| `source` | vždy obě barvy; `available=false` znamená "nemáme analýzu" a nesmí nést čísla |
| `plies[].mover_color` | `white` pro lichý ply, `black` pro sudý - jinak chyba |
| `plies[].eval_*_mover_cp` | měřená hodnota z pohledu toho, kdo táhl |
| `plies[].eval_*_white_cp` | totéž ve White POV: pro Bílého stejné, pro Černého negované |
| `plies[].win_prob_white_*` | pravděpodobnost ve White POV: pro Černého `1 - p` (pravděpodobnost se nepřeklápí znaménkem) |
| `plies[].cp_loss` | velikost ztráty tahu, `>= 0`; `null` právě když `analyzed=false` |

## 3. Invarianty (validace)

`validate_game_full()` kontroluje vše, co JSON Schema neumí:

1. `schema`/`v`/`pov` jsou konstanty; `status` je `complete|partial`.
2. Plies jsou striktně rostoucí, bez duplicit, v rozsahu `1..plies_total`.
3. `mover_color` odpovídá paritě ply.
4. `eval_*_white_cp == ±eval_*_mover_cp` (přesně, s tolerancí 1e-6).
5. `cp_loss >= 0` a je `null` právě u nezměřeného tahu.
6. `unanalyzed_plies` obsahuje přesně nezměřené plies.
7. `status="complete"` nepřipouští díru, nezměřený tah, neznámý `plies_total`
   ani chybějící barvu.
8. `missing_plies` a `plies` se nesmí překrývat.
9. `source` má obě barvy; `available=false` nesmí publikovat měření.

Testy: `tests/test_game_full.py` (14 testů, včetně validace proti JSON Schema
souboru a determinismu merge).

## 4. Partial kontrakt (T3.4)

| Situace | `status` | Co to říká |
|---|---|---|
| obě cache, plné pokrytí | `complete` | timeline je použitelná jako celek |
| jen jedna barva | `partial` | `missing_plies` = plies druhé barvy, `missing_colours` = chybějící barva |
| legacy cache bez `game_plies_total` | `partial` | `plies_total=null`, `missing_plies=[]` - rozsah neznáme, nevymýšlíme |
| engine timeout u některého ply | `partial` | ply je v `plies` s `analyzed=false` a `unanalyzed_plies` |

## 5. Determinismus

- Merge jen čte cache; žádné wall-clock, žádné LLM, žádné nové engine volání.
- Pořadí je dáno `ply`, ne pořadím vstupů.
- Dva běhy na stejných cache dávají identický JSON (test
  `test_merge_is_deterministic`).
- Cache policy je stejná jako u coachingu (`_policy_token`), takže
  `lichess_analyze_game` a `coach.py` sdílí záznamy (T3.0).

## 6. Co tento artefakt NEDĚLÁ

- **Není to náhrada compact 2.1 ani detailed 1.2.** Ty zůstávají
  jednoperspektivní a jejich kontrakty se nemění.
- **Nemá `interaction` events.** T3.3 by vyžadoval měřenou definici interakce
  (tah soupeře, který vytvoří hrozbu, a hráč ji neřeší) a kalibraci FP. Bez
  toho by šlo o nový pattern ID mimo D4 gate. Stav: **čeká na measurement
  spec**, nic se netvrdí.
- **Nedopočítává chybějící plies.** Chybějící data zůstávají chybějící.
