> **Historický snapshot (2026-11-16, compact 2.4).** Current contract je
> compact **2.7**; viz `docs/SESSION_HANDOFF_2026-11-17.md`.

# LLM input audit — reálné výstupy `lichess_coaching_single_game` (2026-11-16)

Cíl: ověřit, zda současný JSON výstup obstojí jako **vstupní soubor pro plnohodnotnou
LLM analýzu**, a najít redundance/duplicity, které by vedly k dvojímu počítání
nebo k chybné narraci. Nejde o názor z kódu — východiskem jsou skutečné tool
calls.

## 1. Metoda

8 volání MCP toolu přes adapter
`scripts/mcp_call.py lichess_coaching_single_game`:

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -X utf8 scripts\mcp_call.py lichess_coaching_single_game `
  --args '{"game_id":"WHIbVLXk","color":"black","output_format":"both","use_llm":false}' `
  --out data\reports\audit_mcp_WHIbVLXk_black.json
```

Hry: `WHIbVLXk`, `S23Qm04u`, `1fpJTeYP`, `2ILNc9EN` (vždy `white` + `black`,
celkem 8 payloadů `{"compact", "detailed"}`). `use_llm=false` = offline ETL,
žádné provider volání. Soubory jsou v gitignored `data/reports/`.

Analyzátor: `scripts/audit_single_game_output.py` (read-only) validuje obě
schémata a kontroluje 12 cross-surface invariantů; výstup
`data/reports/output_audit_16.json`.

Poznámka ke kontraktu: tool přijímá `color` pouze `white|black` (D6). `""` =
obě barvy je **CLI režim** (`coach_single.py --color both`), který tool zavolá
dvakrát. Pokus o `color:""` vrátí `INVALID_COLOR` — není to chyba.

## 2. Výsledek měření (před opravou i po opravě)

| Kontrola (8/8 souborů) | Stav |
|---|---|
| `schema_compact` / `schema_detailed` | PASS |
| `same_game_identity`, `color_is_contract`, `depth_mirror` | PASS |
| `coverage_flagged` (`patterns_meta.coverage.flagged == len(flags) == len(flagged_moves)`) | PASS |
| `confidence_dims_count`, `acc_warning_mirror` | PASS |
| `report_present_both`, `cache_hit_mirror` | PASS |
| `pipeline_mirror`, `offline_not_failed` | PASS (po 2.4) |
| `status_triad` | `degraded / degraded / deterministic` — konzistentně pro offline ETL |

Velikosti (compact / detailed, UTF-8 bytes): **2 921–5 412 / 7 672–19 210**.
Počet flagů 2–9, patternů 0–3, clusterů 0–1, unclassified 1–6, délka reportu
1 020–1 115 znaků. Compact je tedy pro LLM pohodlně malý a detailed zůstává
úplný auditní záznam.

## 3. Nálezy a opatření

| ID | Nález | Závažnost | Opatření |
|---|---|---|---|
| **F1** | `WHIbVLXk` black ply 68 `Kc7`: compact měl `game_impact=losing_to_mate`, ale **neobsahoval směr matu** (`mate_after` chyběl, přestože doc tvrdil opak). LLM mohl napsat „matoval soupeře“. | **Vysoká** | **Opraveno v [2.11] / compact 2.4**: `flags[].mate_after` je povinné (nullable), pro `*_to_mate` `for`/`against`. Ověřeno na živém výstupu: `ply 68 … mate_after: "against"`. |
| **F2** | `eval_before == eval_before_mover_cp` a `eval_after == eval_after_mover_cp` v detailed (8/8 souborů; 2 hodnoty na flag). | Info | Ponecháno — D9 kompatibilní alias. Dokumentováno v `COMPACT_JSON_FOR_LLM.md` jako „počítej jednou“. |
| **F3** | `compact.report` není prefix `detailed.report` (8/8; navíc ruční kontrola obsahu); compact zkracuje/přepisuje na 900 znaků, `report_meta` popisuje jen detailed. | Info | Ponecháno záměrně (R2: report je shrnutí). Nová sekce „Aliases and collisions“ to výslovně říká. |
| **F4** | `detailed.cascade_log` (raw telemetrie) duplikuje odvozené `llm.attempts` (8/8). | Info | Ponecháno jako K7 alias; LLM má používat `llm.attempts`. |
| **F5** | **Kolize názvu `flags`**: v detailed 1.2 je `flags` konfigurační objekt, v compact 2.x je `flags` pole flagovaných tahů. | Střední | Žádná změna schématu (rozbila by kontrakt). Nová sekce „Aliases and collisions“ s explicitním „use `detailed.flagged_moves` when you mean moves“. |
| **F6** | `status=degraded` + `llm.status=degraded` + `pipeline.llm_requested=false` u `--no-llm`: dřív nebylo možné odlišit „vypnul jsem LLM“ od „selhala analýza“. | Střední | **Opraveno v [2.11]**: nový `pipeline` blok v obou surfacech, sdílená logika `services/pipeline_status.py`. Offline běh má `analysis=complete`, `coaching=deterministic_fallback`, `llm_requested=false`. |
| **F7** | `llm.status` se liší napříč surface (`degraded` detailed vs `failed` compact) pro stejnou událost. | Nízká | Ponecháno (kompaktní enum), ale kontext je nyní dán `pipeline`; dokumentováno v LLM guide. |

## 4. Verdikt o vhodnosti pro LLM

**Ano, po [2.11] je výstup plnohodnotným LLM inputem.** Každý flag nese SAN,
ply, cp loss, POV evaly (když byly měřeny), `game_impact` **včetně směru matu**,
motiv, FEN. Patternová vrstva nese tři pojmenované dimenze confidence a
explicitní `unclassified` důvody. Obě barvy jsou k dispozici vždy (klíčovaný
soubor nebo dvě volání toolu). Validace schémat a 12 invariantů prošla na
8/8 reálných payloadů.

Co zůstává **vědomým omezením, ne chybou**: aliasy se musí počítat jednou;
`report` je shrnutí, ne zdroj faktů; `pv_played` je engine linie, ne skutečná
odpověď soupeře (tu má jen `game_full` 1.0); kalibrace mechanismů neexistuje
(`behavioral_confidence = null / not_calibrated`); time trouble není měřeno,
dokud neexistuje `%clk` parser (T-16).

## 5. Dopad na další vývoj

Žádný z nálezů nevyžaduje změnu detekční logiky ani `cp_loss`. Všechny opravy
byly aditivní: compact 2.4 je nový artefakt, 2.3 zůstává zmrazený; detailed 1.2
získal jedno nové pole. P0-9 (CI fast/engine split + pinnutý Stockfish) zůstává
dalším krokem fáze 0.
