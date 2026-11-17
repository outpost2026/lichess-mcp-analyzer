# Handoff 2.5 — verifikace P0/P1 (2026-11-17)

Zdroj: externí handoff „Schema 2.4 → 2.5“. Ověřeno proti kódu a **čerstvým
cold re-runům** 4 her (`zOk3TnoC`, `QxL4Tr8u`, `PbOhjKa8`, `WHIbVLXk`, obě
barvy, `--no-cache`). Původní cache zálohována v gitignored
`data/_backup_handoff_20261117/`.

## P0 — opravy

| ID | Změna (soubor) | Test | Důkaz z re-runu | Odchylka |
|---|---|---|---|---|
| **P0-3** | `game_analyzer._align_engine_lines_with_anchor()`: `engine_lines[0].eval_cp` = D12 anchor (i přesun ranku); `best_move_san` z anchor UCI; když anchor == sehráno, `cp_loss=0` a `best_eval=eval_after`. Vzorec `best_eval − eval_after` nezměněn. | `test_game_analyzer.py::test_best_eval_matches_engine_lines` + 2 helper testy | 60/61 flagů má `|best_eval − engine_lines[0]| ≤ 10` (98,4 %). `QxL4Tr8u` black 58 už nemá `san==best_move_san` s `cp_loss 131` — čerstvý search dal `best=Re7` vs `Rxd6`, `cp_loss=131` je legitimní. | `zOk3TnoC` white 41 `Qb5`: engine nevrátil `best_move_uci`, takže anchor nelze přiřadit (gap 16). Zbylé pole zůstává měřené, ne odhadnuté. |
| **P0-1** | `pattern_detector.scan_single_game()`: run 3+ flagovaných vlastních tahů (ply krok 2) → agregovaný pattern C se `strength=min(total_cp/1000,1)`, `severity=high` nad 500; coverage mapa se synchronizuje. | `tests/test_pattern_detector.py::test_cluster_based_attention_tunneling` (+ medium cases) | C přítomen: `zOk3TnoC` white (0.623), `PbOhjKa8` white (0.958), `QxL4Tr8u` black (0.566), `WHIbVLXk` white/black (0.546 / 1.0). | Žádná. |
| **P0-2** | Nový pattern **U** „unseen_threat_quiet_blunder“ (Q1/Q2 jsou obsazené D13): tichý `mistake/blunder`, cp ≥ 100, bez motivu, ne v šachu; `severity=critical` nad 500. `DETECTOR_VERSION` → `DBCL-20261117-dev`, přidány cross-game detektory `_detect_u`/`_detect_v`. | `tests/test_pattern_detector.py::test_quiet_blunder_pattern` | `zOk3TnoC` white 41 `Qb5` → U `strength 1.0 / critical`; tiché blundery v ostatních hrách → U `high`. | Žádné; D4 podmínka (mechanismus + test) splněna, LP fixture `NxK1MuwN`/`rgQlsl0s`/`nB5FdIFo` nebyly lokálně dostupné — pokryto jednotkovým testem. |
| **P0-4** | `eval_provenance.configured_eval_source()` + `GameAnalysis.engine_hash_mb/nodes_cap/policy_run_id`; `cache.hit` už_nevrací `hash_mb: null`, pokud cache metadata mají hash. | `test_eval_provenance.py::test_eval_provenance_contains_config` | `eval_source` např. `stockfish_d14_n150000_h128_live`, `..._cache_run_<id>`; žádný `unknown` v čerstvých bězích (předtím `WHIbVLXk {unknown:35}`). | Hash je **adaptivní** (`h128`/`h256`, existující `choose_adaptive_hash`), ne pevné `h512` z příkladu handoffu. Konfigurace je přesto plně pojmenovaná; Stockfish nastavení se nezměnilo. |

## P1 — konzistence

| ID | Stav | Důkaz |
|---|---|---|
| **P1-1** | Opraveno | `acc_warning` nyní `contains_mate_level_outlier` / `contains_blunder` / `contains_mistake`. `zOk3TnoC` black má `contains_mistake` (dříve `null` u accuracy 97,3). |
| **P1-2** | Opraveno | Compact 2.5 už neemituje `eval_before`/`eval_after`; `validate_compact` přijímá i 2.4 s aliasy (backward reader). Schéma `single_game_v2_compact_2.5.json`. |
| **P1-3** | **Nezměněno (odchylka)** | `internal_accuracy_score` zůstává v detailed 1.2. Odstranění by vyžadovalo nový detailed kontrakt 1.3; handoff povoluje bump pouze compactu. Ponechán jako zdokumentovaný alias. |
| **P1-4** | Opraveno | Nový pattern **V** „wrong_check_response“ (in check, cp > 100, bez motivu). Přítomen v `QxL4Tr8u` white/black a `WHIbVLXk` black (critical). |
| **P1-5** | Již fungovalo | `QxL4Tr8u` black 86/88 mají `pv_played_unavailable=no_engine_lines` a strukturované `best_move_san: Nc2` / `Na3` v detailed flagu. Žádná změna kódu. |
| **P1-6** | Opraveno | `provider_health`: 410 → 24 h, 402 → 1 h, 5xx → 60 s. `tests/test_provider_health.py`. |

## P2

P2-1 (FEN > 100) a P2-3 (tichý cp > 100) jsou pokryty stávajícím chováním a
novým patternem U. P2-2 (medián ACPL) nebyl v tomto sprintu implementován —
je to report-only polish, neblokuje LLM narativ.

## Compact size delta (UTF-8 bytes, compact surface)

| Hra / barva | 2.4 | 2.5 | Δ |
|---|---:|---:|---:|
| zOk3TnoC white | 6456 | 5948 | −508 |
| zOk3TnoC black | 3359 | 3356 | −3 |
| QxL4Tr8u white | 4674 | 4764 | **+90** |
| QxL4Tr8u black | 6995 | 6638 | −357 |
| PbOhjKa8 white | 5367 | 5217 | −150 |
| PbOhjKa8 black | 3982 | 3981 | −1 |
| WHIbVLXk white | 5331 | 5219 | −112 |
| WHIbVLXk black | 5697 | 5641 | −56 |

Maximální nárůst +90 B (limit +200 B). Všechny payloady validují proti
`single_game_v2_compact_2.5.json` a `single_game_v1.2.json`.

## Gates

`pytest` **531 passed** (bez `test_engine_client.py`), Ruff clean, mypy
**73 souborů** clean.
