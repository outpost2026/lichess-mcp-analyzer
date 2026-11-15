---
title: Integrace handoffu v1.2 -> v1.3 (11 her) do projektu refaktoru
date: 2026-11-15
status: ROZHODNUTÍ + PLÁN
navaznost: HANDOFF_AGENT_lichess-analyzer-mcp.md, docs/AUDIT_INTEGRATION_2026-11-13.md
---

# Integrace handoffu v1.2 -> v1.3

## 0. Metoda a provenience

Ověřeno na `HEAD 942dd35` proti `src/` a `data/game_cache/*_d14n150000.json`.
Značky: `[M]` měřeno, `[Č]` čteno z kódu, `[O]` odvozeno.

Handoff míchá dvě datové vrstvy:

| Vrstva | Stav | Důsledek |
|---|---|---|
| Cache (`data/game_cache`) | **aktuální**, `cp_loss`/evaly/in_check sedí na korunu | čísla v tabulkách P0-1..P0-3 jsou pravá |
| Compact JSON samples ("22 JSON samples") | **stale, compact 2.0** | P0-4, P0-5, P1-4 popisují stav před 2.1 |

Důkaz stálosti: handoff tvrdí "Compact 2.0 default"; kód má `SCHEMA_V = "2.1"` (`compact_serializer.py:64`). Handoff tvrdí, že `patterns_meta` v compactu chybí; v 2.1 je `patterns_meta` **povinný** (`_REQUIRED_TOP`, řádek 454; schema `required`). Handoff tvrdí, že FEN chybí pro `Qe3` (9465); kód má `FEN_CP_THRESHOLD = 100` a cache pro ten tah `fen` **má**.

**Verdikt:** datová část handoffu je silná, ale dva ze šesti P0 "blockerů" porušují vlastní kontrakty projektu (D4, D11) a tři popisují již opravený compact 2.0.

---

## 1. Preserve - kontrola

| Tvrzení | Stav | Kód / data |
|---|---|---|
| `cp_loss = best_eval_mover_cp - eval_after_mover_cp`, 100% consistent, FIX-023 resolved | **částečně nepravda** | Rovnice je tautologie z konstrukce (`engine_client.py:373,379,383`). FIX-023 (eval_before vs cp_loss) **není** vyřešen: `eval_before=767`, `cp_loss=687`, divergence 91 > tolerance 50 (`eval_consistency.py:16`). |
| Mate score: `eval_cp: null` + `mate_in: N` | **nepravda v eval_cp** | `mate_in` sedí. `eval_cp` se publikuje jako `0` a `win_prob=0.5` (`game_analyzer.py:833` + `_win_prob_from_cp(None)`), tedy nerozlišitelné od vyrovnané pozice. To je T-06. |
| Weakest phase sort + "Čisté fáze:" | **platí** | `coaching_single_game.py:246-261`, `ide_fallback.py:136-141`. |
| `phase_stats` + `segment_stats` + `chess_phase_stats` | **platí ve full** | `models/game.py:241-246`. V compact summary je jen `phase_stats` (`compact_serializer.py:349`). |
| `pattern_status` + `unclassified_reason` + `patterns_meta.coverage` | **platí v 2.1** | `_REQUIRED_TOP` + `_REQUIRED_PATTERNS_META`; schema required. |
| `accuracy_method: internal_cp_linear` | **platí** | `models/game.py` konstanta; schema enum. |
| Compact 2.0 default | **nepravda** | `SCHEMA_V = "2.1"`. |
| CAND-E per-flag `patterns[]` | **platí** | `pattern_ids` v `_single_game_candidate`. |
| CAND-F `clusters[]` | **platí** | `compact_serializer.py:437`. |
| `username` preserves API case | **platí [O]** | FIX-026; neověřoval jsem proti API, jen proti cache. |
| Endgame null policy `endgame: [null, 0]` | **platí v compactu** | `_phase()` vrací `[None, 0]` pro chybějící fázi; full klíč vynechá. |

---

## 2. P0 - kontrola a překlasifikace

| ID | Data | Diagnóza | Návrh handoffu | Verdikt |
|---|---|---|---|---|
| P0-1 | `Qe3` 9465, `Qd3` 347, `Qg4` 152 `[M]` | `quiet_positional` opravdu pokrývá i matové blundery | nový pattern `Q1` "Quiet positional drift" | **ODMÍTNUTO jako pattern.** `Q1` už existuje = "Desperate Gambit Mode" (`pattern_detector.py:525`). D4 zakazuje nová ID. Navíc predikát `cp>200 + class in (mistake, blunder)` je jen přejmenování existující klasifikace, ne nová detekce. |
| P0-2 | `Kf3` 9197, `Ke6` 234, `Kf1` 123 `[M]` | king retreat v šachu propadne | rozšířit J, nebo nový `Q2` | **ODMÍTNUTO obojí.** `Q2` už existuje = "Win despite blunder" (`:559`). J má explicitní kontrakt "king move is an escape, never a block" (`is_piece_block`, `:52`) = D11. Rozšíření J by ten kontrakt rozbilo. |
| P0-3 | `Bxg2+` 338 (420->58), `Bf2+` 9328 (9992->666), `Qe3` 9465 (-548->-9999) `[M]` | cosmetic vs fatal blunder nerozlišitelné | `game_impact` enum | **PŘIJATO**, aditivní pole. Enum ale musí umět mat: `losing_to_losing` pro -9999 je špatně, má být `losing_to_mate` (nebo `mate_after: true`). |
| P0-4 | `Qe3` nemá FEN v compactu | FEN jen pro cp>100 | FEN pro cp>200 nebo blunder/mistake | **STALE.** `FEN_CP_THRESHOLD=100`; v cache má `Qe3` `fen=Y`. V 2.0 to byl reálný gap, v 2.1 ne. |
| P0-5 | PV délka 0-2 | PV nestačí pro naraci | retry 15 s / 64 MB + `pv_truncated` | **STALE / UŽ HOTOVO.** `pv_recovery.py` má přesně 15 s a 64 MB; `pv_unavailable` už existuje se 6 důvody (`compact_serializer.py:68`). V cache mají všechny citované flagged tahy `pv=3` (vyjma best tahů, kde je PV 0 záměrně). |
| P0-6 | report 1987.4 vs chess_phase 1656.2 `[M]` | report míchá dvě fáze | přepnout report na `segment_stats` | **PŘIJATO jen jako štítek.** `phase_stats` **není** deprecated; je to `effective_phase` a je autoritativní (`models/game.py:168-169`). Dnes se rovná `segment_stats`, protože `phase_method` nikdy není `material`. Přepnutí by jen schovalo T-08. |

---

## 3. P1 / P2 - kontrola

| ID | Verdikt |
|---|---|
| P1-1 `strength == confidence` | **Alias, ne defekt.** `confidence` je deprecated property = `strength` (`models/pattern.py:100`); `coaching_base.py:152` ho publikuje jako `strength*100`, `pattern_detector.py:959` jako `strength` (0-1). To není duplicita, to je **rozdílná jednotka** - viz N-02. |
| P1-2 `eval_before == eval_before_mover_cp` | **Alias 1.2 kompatibility.** Obě z `m.get("eval_before")` (`coaching_single_game.py:112,118`). D12 přidal `*_mover_cp`; 1.2 jméno zůstává. Nemazat. |
| P1-3 `accuracy == internal_accuracy_score` | **Alias, dokumentovaný v kódu.** `accuracy` je 1.2 kompatibilní alias (`models/game.py:236-238`). Nemazat v 1.2. |
| P1-4 `patterns_meta` chybí v compactu | **NEPRAVDA v 2.1.** Povinný (`_REQUIRED_TOP`). Stale sample. |
| P1-5 `endgame` tvar | **Reálné, nízká hodnota.** Compact má `[null,0]` vždy; full klíč vynechá. Aditivní `not_reached` do full je OK. |
| P1-6 Pattern C false positive | **Překrývá T-10.** Změna `frequency >= 2` je změna predikátu = `DETECTOR_VERSION` + fixture + rozhodnutí. Neřešit samostatně. |
| P2-1 definice clusteru | **Dokumentační**, pokud v `COMPACT_JSON_FOR_LLM` chybí. |
| P2-2 `time_control` + `clock` | `time_control` **už je** (`GameSummary`, compact `tc`). `%clk` **nikde neparsuje** - viz N-01. |
| P2-3 `opening_deviation` | **Odložit.** "Joke opening" nemá měřitelnou definici; bez ní je to názor, ne pole. |
| P2-4 median ACPL | **Přijato, nízká priorita.** Aditivní report-only pole při `max/median > 10`. |

---

## 4. Nové nálezy (nejsou v žádném handoffu)

**N-01 `%clk` je deklarovaný, ale neimplementovaný `[Č]`.**
`prompt_builder.py:30,48` zakazuje LLM soudit time trouble bez `%clk`, ale v `src/` neexistuje parser `%clk` ani pole `clock` na `MoveAnalysis`. Výstup je tedy **vždy** `clock_data_unavailable`. D10a přitom říká "jen PGN `%clk`" - rozhodnutí existuje, implementace ne. Produktová mezera, ne drift.

**N-02 `confidence` má dvě jednotky `[Č]`.**
`pattern_detector.py:959` = 0-1; `coaching_base.py:152` a `match_patterns.py:169` = 0-100; schema vyžaduje 0-100 (`schemas.py:30`). `report_persister.py:99` tiskne `{confidence}%` a `:156` dělí 100. Pokud single-game pattern (0-1) dojde do `persist_report`, vyjde `0.8%` místo `80%`. Ověřit testem, pak sjednotit.

**N-03 D12 anchor chybí u 97,8 % tahů `[M]`.**
318 souborů, 9 412 analyzovaných tahů, z toho 9 208 bez `best_eval` (297 souborů úplně). Invariant `cp_loss == best_eval - eval_after` je ověřitelný jen na 2,2 % korpusu. "100% consistent" v handoffu platí pro 23 flagů, které anchor mají - ne pro korpus.

**N-04 `phase_stats` změní význam tichým přechodem `[Č]`.**
Dnes `phase_stats == segment_stats` (ověřeno na `GUhKY0rm`: 1987.4 vs 1987.4). Ale `phase_stats` je `effective_phase`; jakmile T-08 zapne `material`, report změní čísla, aniž by se změnil jeho kód. T-08 musí rozhodnout zdroj reportu **před** implementací.

**N-05 vysoké ACPL jsou matový pseudo-cp, ne šum `[M]`.**
`a4bflvVZ_black`: 9422 (ea 575), 9091 (ea 901), ACPL 828.0. `v6O0wNa7_white`: 9750 (ea -9998), ACPL 784.8. Aritmetika přesně `9997-575` a `-248-(-9998)`. T-01 je tím P0 s přímým důkazem, ne hypotéza.

**N-06 `unclassified_reason` je enum v schema `[Č]`.**
`schemas/single_game_v2_compact.json` má uzavřený enum (`why`). Přidání `quiet_blunder` / `check_escape` je aditivní, ale mění enum kontrakt; validator i schema musí jít spolu. Precedent T2 (aditivní pole bez bumpu verze) to dovoluje.

---

## 5. Rozhodnutí D13-D23

| ID | Rozhodnutí | Dopad |
|---|---|---|
| **D13** | P0-1 **není** nový pattern. `quiet_positional` dostane sémantické rozlišení: při `cp>200` a bez motivu se publikuje `why=quiet_blunder` (aditivní enum) + `game_impact`. Žádné nové pattern ID. | LLM dostane signál "tohle nebyl tichý posun, byl to blunder"; Q1 zůstává "Desperate Gambit Mode". |
| **D14** | P0-2 **není** rozšíření J. J zůstává "block, nikdy king move" (D11). King escape v šachu dostane `why=check_escape` (aditivní enum); kandidát na pattern se zapíše do metodologie pro příští D4 gate. | Žádná změna J; žádný nový pattern; mezera je pojmenovaná, ne zametená. |
| **D15** | `game_impact` **přijato** jako aditivní pole detailed 1.2. Enum obsahuje matové stavy (`winning_to_mate`, `losing_to_mate`) nebo `mate_after: true`. Práh ±100 cp je dokumentovaný, ne implicitní. | LLM rozliší kosmetický a fatální blunder; žádná změna schématu (1.2 nemá `additionalProperties:false`). |
| **D16** | P0-4, P0-5, P1-4 **zamítnuty jako stale** (compact 2.0). Každý review sample musí nést `generated_by_commit` + `schema_v`; bez toho se analýza nepřijímá. | Žádný kód se nemění; zabrání se opakovanému review starého výstupu. |
| **D17** | P0-6 **přijato jako štítek, ne přepnutí.** Report publikuje oba řezy s vyznačením (`segment` vs `chess_phase`) nebo explicitně řekne `effective_phase`. Závisí na T-08. | Odstraní se ambiguous "Fázově nejslabší"; čísla zůstanou. |
| **D18** | P1-1/2/3 **jen dokumentace aliasů**; jediná kódová změna je N-02 (jednotka `confidence`). Žádné odebírání polí v 1.2. | 1.2 kompatibilita zůstává; 100x chyba zmizí. |
| **D19** | P1-5 **přijato** (full emituje `not_reached`), priorita P3. | Konzistence full vs compact. |
| **D20** | P1-6 **fold do T-10**; žádná samostatná změna prahu C. | Jeden predikát C, jeden bump, jedna fixture. |
| **D21** | P2-4 **přijato** (median ACPL při `max/median > 10`), report-only, P3. | Fáze dominovaná jedním blunderem nezkreslí mean. |
| **D22** | P2-3 **odloženo** do doby, kdy existuje měřitelná definice "non-standard opening". | Žádné pole bez pravidla. |
| **D23** | N-01 **přijato jako produktový úkol** (T-16): parser `%clk` + `clock` per move podle D10a. Do té doby prompt zůstává `clock_data_unavailable`. | Time trouble se stane měřitelným, ne deklarovaným. |

---

## 6. Integrace do task listu

| Task | Vychází z | Priorita | Gate |
|---|---|---|---|
| T-16 `%clk` parser + `clock` per move | N-01 / D23 | P2 | none (D10a rozhodnuto) |
| T-17 `confidence` jedna jednotka | N-02 / D18 | P1 | none |
| T-18 `game_impact` | P0-3 / D15 | P1 | none |
| T-19 `why=quiet_blunder` | P0-1 / D13 | P1 | none |
| T-20 `why=check_escape` | P0-2 / D14 | P1 | none |
| T-21 report phase label | P0-6 / D17 | P2 | depends T-08 |
| T-22 full `endgame.not_reached` | P1-5 / D19 | P3 | none |
| T-23 median ACPL | P2-4 / D21 | P3 | none |

Mapování na starý plán:

| Starý task | Co pokrývá z nového handoffu |
|---|---|
| T-01 | N-05 (matový pseudo-cp má přímý důkaz); "Do NOT touch cp_loss" je **neplatné** |
| T-02 | N-03 (provenience; 97,8 % bez anchoru) |
| T-07 | Preserve #1 (tautologie; FIX-023 není vyřešen) |
| T-08 | N-04 (fáze; blokuje T-21) |
| T-10 | P1-6 (jeden predikát C) |
| T-15 | D16 (provenience review samples) + stale "Compact 2.0" |

---

## 7. Pořadí práce

```
T-13 -> T-02 -> T-01 -> T-03 -> T-04 -> T-07 -> T-06 -> T-05
     -> T-10 -> T-11 -> T-14 -> T-17 -> T-18 -> T-19/T-20
     -> T-12 -> T-16 -> T-21 -> T-22 -> T-23 -> T-15
```

T-17 před T-18, protože `game_impact` půjde do stejného payloadu a jednotka `confidence` musí být vyřešena dřív, než se payload rozšíří.

---

## 8. Co opravit v dokumentaci

1. `CHANGELOG` [2.4]: žádná zmínka o "Compact 2.0"; všude 2.1.
2. `COMPACT_JSON_FOR_LLM`: doplnit, že `patterns_meta` je povinný a `pv_unavailable` je ekvivalent navrhovaného `pv_truncated`.
3. `AUDIT_INTEGRATION` §12: D13-D23 (tento dokument je detail).
4. `PATTERN_DISCOVERY_METHODOLOGY`: zaznamenat kandidáty `quiet_blunder` a `check_escape` jako **candidate patterns** pro příští D4 gate, ne jako hotové.
5. Každý review sample: hlavička `generated_by_commit`, `schema_v`, `detector_version`.

---

## 9. Stav implementace (2026-11-15, [2.5])

Hotovo v této iteraci (kód + test, gate zelený):

| Položka | Změna | Test |
|---|---|---|
| **D18 / N-02** | `scan_single_game` publikuje `confidence` 0–100; `strength` zůstává 0–1 | `tests/test_confidence_unit.py` |
| **D25** | detailed `flagged_moves[].fen_before` | `tests/test_output_enrichment.py` |
| **D25** | detailed `game` blok; `Anonymous`/`?`/`-` → `""`, rating `0` → `null` | `tests/test_output_enrichment.py` |
| **D24** | `--color ""` = obě barvy, klíčovaný JSON; `coach_single.py --format both` default | `tests/test_coach_cli.py` |
| **D24** | chyba pipeline = stderr + exit 1, nikdy prázdný JSON | `tests/test_output_enrichment.py` |

Zbývá (v pořadí z §7): T-13, T-02, T-01, T-03, T-04, T-07, T-06, T-05, T-10, T-11, T-14, T-18, T-19/T-20, T-12, T-16, T-21, T-22, T-23, T-15.

Ověřeno na korpusu 2026-11-15:

- `iAIWvqPo` (pojmenovaná hra): White `Heinzlinus` 1942 vs `Systeq` 1898 — jména i ratingy se parsují správně z PGN hlaviček.
- `quOLOThu`, `nB5FdIFo`, `GUhKY0rm`, `rgQlsl0s` (anonymní): `player_name`/`opponent_name` = `""`, rating = `null` — placeholder se nikdy nepublikuje.
- `coach_single.py quOLOThu` bez `--color`: 1 JSON, klíče `white`/`black`, 9 + 4 flagy, FEN u všech flagů v detailed a u 7 (White) + 2 (Black) v compactu (`cp > 100`).
