# Handoff 2.7 — vlna 1, validace (2026-11-17)

Vzorek: 5 her × 2 barvy (`RhkEoVUT`, `WxfSvX4y`, `0yeUi5EO`, `yXmiCYss`,
`hJjXxxvq`), tool `lichess_coaching_single_game(use_llm=false, output_format=both)`.

| Fix | Změna | Test | Důkaz |
|---|---|---|---|
| §4.7 `src` | `compact_serializer._summary_src()` | `test_summary_src_and_rank_unknown` | `summary.src = d14n150k_hash_unknown_cache` u 10/10 souborů |
| §4.9 `rank_unknown` | `pv_played_unavailable` pro `rank null/0` | stejný test | `yXmiCYss` white 79/87/93/125, black 120; `hJjXxxvq` black 58/60/62 |
| §4.10/4.11 `alts` | 1 rank-2 SAN pro `rank ≥ 4` | `test_all_flags_preserved_in_ply_order`, `test_summary_src...` | `RhkEoVUT` white 25/37, `hJjXxxvq` white 55 (`alts` přítomno) |
| §4.1 `piece_reads` | `services/piece_reads.py`, top-level mapa, max 1 flag | `tests/test_piece_reads.py` (3 testy) | 8/10 souborů má 1 read; např. `hJjXxxvq` white 55 → `th=Rxe4` z PV |
| N-2 konzistence | reason i pro matched rank≥4 | `test_summary_src...` + live | `missing_un` kleslo z 10/10 na 0/10 souborů |

## Size delta

+50 až +232 znaků oproti 2.6 (limit +300). Největší: `0yeUi5EO` black +232,
`hJjXxxvq` black +232.

## Odchylky

- `piece_reads` publikuje jen forcing figurku obsaženou v engine PV, ne plnou
  šachovou analýzu pozice. Uživatelský příklad „Rf1 je monstrum" (`hJjXxxvq`
  55) není v PV jako forcing tah, proto se nepublikuje — místo toho `Rxe4`.
- Nový engine call proplayed-move PV rank-4 nebyl přidán; zůstává
  `rank_not_in_engine_lines`. Tím je §4.11 částečně pokryt (alternativy ano,
  PV sehraného tahu ne).
- `alts` omezeno na 1 SAN a `piece_reads` na 1 ply kvůli size budgetu.

## Cross-game validace

Žádný nový behaviorální pattern nebyl přidán — wave 1 jsou jen datové pole.
Cross-game validace Q3/Q4 a paired_blunder je nutná před wave 2.

## Gates

`pytest` 536 passed, Ruff clean, mypy 74 souborů, 10/10 payloadů validuje
proti 2.7 + 1.2.
