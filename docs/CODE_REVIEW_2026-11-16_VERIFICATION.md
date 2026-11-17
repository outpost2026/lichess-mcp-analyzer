> **Historický snapshot (2026-11-16, compact 2.4).** Current contract je
> compact **2.7**; viz `docs/SESSION_HANDOFF_2026-11-17.md`.

# Verifikace generálního code review 3. LLM (2026-11-16)

Vstup: `lichess_opencode_handoff_2026-11-16.md` (1205 řádků, auditní HEAD
`e136fee`, tedy **před** [2.9]). Audit proběhl čtením GitHub `main`, ne během
lokálního checkoutu; opakoval jsem proto každé konkrétní tvrzení proti zdrojovému
kódu a testům na lokálním HEAD `b2134a4`.

Rozdělení: **Potvrzeno** (defekt), **Stale** (pravdivé v auditním HEAD, dnes
vyřešené), **Návrh** (pravdivý popis stavu, ale nejde o chybu; patří do další
fáze), **Neplatné** (tvrzení neodpovídá kódu).

## 1. Stale vůči [2.9]

| Audit | Ověřený stav |
|---|---|
| Phase 0 úkol „Close P0-4: separate pattern confidence dimensions“ | **Stale — hotovo v [2.9]** (D37): `detection_strength`, `evidence_support`, `behavioral_confidence = null` + důvod, `confidence_kind`, compact 2.3 |
| §13 „Keep detailed 1.2 and compact 2.2 stable“ | **Stale**: 2.2 zůstává zmrazený soubor, ale current artefakt je compact **2.3** (`schemas/single_game_v2_compact_2.3.json`) |
| §2.1 „pytest 505 passed, mypy 71 files“ | **Stale, ne chyba**: platilo pro `e136fee`; na `b2134a4` je 513 fast + 2 nové testy = **515 passed**, mypy **72 souborů** |

Auditem deklarovaný HEAD je tedy nutné považovat za vstupní snapshot, ne za
současný stav. Žádné z těchto tvrzení není chybou auditu.

## 2. Potvrzené defekty — opravené v [2.10]

| ID | Nález a důkaz | Oprava |
|---|---|---|
| **P-03** | `coaching_training_plan.py:37` i dalších 5 toolů uváděly v docstringu `max_games (5-50)`, zatímco clamp je `max(5, min(999, max_games))` (např. `:45`). API kontrakt neodpovídal validaci. | Docstringy 6 toolů sjednoceny na `(5-999; 999 is a hard clamp, not a recommendation)`; `persist_report` je průchozí a zdokumentován stejně. Nový `tests/test_tool_param_contract.py` porovnává doc range s clampem (2 testy). |
| **P-04** | `services/srs_engine.py:1-5` tvrdil FSRS, 3parametrický model a gradient descent. Skutečnost: `review_card()` je `2.5 - 0.1*(5-quality)` násobič (SM-2-like), `models/srs_card.py` má `stability`/`difficulty` jen jako pole. Žádný gradient descent, žádná kalibrace. | Docstring přepsán na „SM-2-like … prototype, not FSRS“, včetně známých limit JSON souboru; README už neříká „FSRS/SM-2 engine“. |
| **§9.2 README drift** | `README.md:7` uváděl `263 fast + 15 real engine` a `v4: 7ce7f61`, strom `:400` `254 fast`. Reálně 515 fast a 11 engine testů. | Statusní řádek má datum 2026-11-16, aktuální počty a seznam schémat; strom `:400` opraven; historická poznámka `:508-513` označena jako historická k 11. 11. |

## 3. Potvrzená zjištění, která nejsou defekty

| ID | Verdikt | Proč to není chyba teď |
|---|---|---|
| **D-01** `game_full` není joint coaching kontext | **Návrh — platí** | `services/timeline.py::build_full_game` skládá jen merge vrstvu (ply, game, source); `docs/GAME_FULL_1.0.md` to výslovně říká. Joint kontext je Phase 2, ne změna 1.0. Chybějící testy pro chybějící `game.id` / policy mismatch v `tests/test_game_full.py` jsou reálná testovací mezera — odložit s Phase 0/2. |
| **D-02** `run_id` není DB identita běhu | **Návrh — platí a je záměr** | `services/eval_provenance.py::run_id` je policy fingerprint; D36 ho tak pojmenovává a výslovně vyčleňuje engine identitu. Do Phase 1 ho v DB označit jako `policy_fingerprint` a přidat samostatný `analysis_run_id`. |
| **D-03** `status` míchá analýzu a naraci | **Návrh — platí** | `coaching_single_game.py` dává `status="degraded"` i při kompletní analýze bez LLM. Změna pole by porušila kontrakt 1.2; oddělené statusy patří do nového DTO ve Phase 2. |
| **D-04** eval metriky oddělené | **Platí** | `accuracy_method = internal_cp_linear`, `accuracy_warning`, `eval_provenance`. Doporučení uchovávat raw data v DB je v souladu s Phase 1. |
| **L-01** `narrative_validator` není zapojen do provider cascade | **Potvrzeno, mimo rozsah** | `coaching_base.safe_llm_call` kontroluje jen délku/echo (`len < 50`), `narrative_validator.validate_narrative` se nikde mimo svůj modul nevolá. Phase 2 (strukturovaný output + evidence refs). |
| **L-02** ořez kontextu | **Potvrzeno** | `_move_lines(..., limit=10)` a `bfs_json = ...[:2000]` v `coaching_single_game.py`. Deterministický report už ořezán není; LLM prompt ano. Phase 2. |
| **L-03** deterministický fallback z promptu | **Potvrzeno** | `ide_fallback.py` extrahuje ply/SAN/cp z textu. Funguje, ale není strukturovaný pedagogický fallback. Phase 2. |
| **L-04** prompt v kódu | **Potvrzeno** | `services/prompt_builder.py` drží runtime šablony, docs je design reference. Verzované `prompts/` + `prompt_hash` je Phase 2. |
| **L-05** provider metadata | **Částečně** | `llm.attempts`, `llm_skipped`/`llm_skip_reason`, `report_meta.source` už existují; chybí rozlišení „unusable output“ vs „unsupported claims“ vs „low quality“. Phase 2. |
| **P-01/P-02** plán vs aspirace | **Potvrzeno** | `coaching_training_plan.py` je jednorázový LLM report; doména `player_goal` / `intervention` / `outcome_measure` neexistuje. Phase 3. |
| **P-04 (zbytek)** SRS jako soubor | **Potvrzeno** | `SRS_FILE = data/srs_cards.json`, celý soubor se přepisuje, `_load` tiše ignoruje poškozený JSON. Záměrně ponecháno jako prototyp; DB + transakce až Phase 1/3. |
| **DB-01/DB-02** chybí relační paměť | **Potvrzeno** | Žádný SQLite modul ani migrace. `report_persister` je exportér. Phase 1 (a auditův Sprint 1). |
| **P0-9** jeden CI job | **Potvrzeno** | `.github/workflows/test.yml` má jediný job `test`, `pytest tests/` bez splitu a bez pinnutého buildu. **Další krok.** |

## 4. Co z auditu nepřijímám jako pokyn pro tento krok

- Žádný nový pattern ID z `unclassified` (D4 trvá, audit to také zakazuje).
- Žádný rewrite `game_analyzer.py` ani změna `cp_loss` (D12/D30).
- Žádné slučování White/Black do jednoho cohortu (D8).
- Žádný Streamlit/frontend, dokud není SQLite source of truth (auditův vlastní §12).
- Žádné tvrzení, že `strength`/`conf` je pravděpodobnost — P0-4/D37 právě říká opak.

## 5. Dopad na P0-9

Audit nezpochybňuje samotný cíl P0-9, ale doplňuje jeho acceptance: fast a engine
joby musí být oddělené, engine build identifikovatelný (UCI `id name` + hash),
žádné tiché deselektování a README musí být pravdivé. Poslední bod je splněn
[2.10]; zbývají dva první. Audit také potvrzuje, že po P0-9 následuje Phase 1
(SQLite), ne frontend.
