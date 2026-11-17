# Kalibrace compact 2.6 — první vlna C-1 + C-2 (2026-11-17)

Vstup: 3 hry × 2 barvy (`RhkEoVUT`, `WxfSvX4y`, `0yeUi5EO`), 6 tool callů
`lichess_coaching_single_game(use_llm=false, output_format=both)`.

## Před opravou

- R-1: `eval_before − eval_after ≠ cp` u 10 flagů, mezery 1–28 cp.
- R-2: `patterns[]` neslo jen `id`/`conf`/`freq`/`sev`/`plie`/`support`; U, B, T
  byly pro LLM holé identifikátory bez názvu a mitigace.
- R-3: `eval_source` jen v detailed.

## Po opravě (2.6)

| Kontrola | Výsledek |
|---|---|
| `cp == bcp − eval_after_mover_cp` | **7/7** flagů, delta 0 cp |
| `flags[].eval_before_mover_cp` | odstraněn; `bcp` povinný (nullable) |
| `patterns[].nm` / `mit` | přítomny u všech patternů; `mit` ≤ 50 znaků |
| Schémata | 6/6 payloadů validuje proti 2.6 + 1.2 |
| Delta compactu | **+74 až +177 znaků** (limit +200) |

Příklad: `RhkEoVUT` white 37 má `bcp=388`, `eval_after_mover_cp=124`,
`cp=264` → 388 − 124 = 264. Pattern U nese `nm=unseen_threat` a
`mit=Zkontroluj hrozby pred tichym tahem`.

## Odložené nálezy

C-3 (`src`), C-4 (`ph`), C-5 (`pv_played_unavailable`), C-6/C-7/C-8 a
N-1/N-2/N-4 zůstávají pro další vlnu; žádný z nich neblokuje aritmetiku ani
koučinkový signál patterns.
