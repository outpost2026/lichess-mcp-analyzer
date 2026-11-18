# Implementační plán: Single-Game Pattern Discovery & Library Calibration

**Verze:** 1.0 | **Datum:** 2026-08-02 | **Status:** plán k realizaci
**Návaznost:** DEEP_DIVE_SINGLE_GAME_PATTERNS_2026-08-02.md (§2 root cause, §3 deflekce, §5 confidence)
**Cíl:** mechanismus, který z analýzy single game (obě strany) identifikuje kandidátní patterny (conf>0.7 / TOT 0.3–0.6) a kalibruje knihovnu A-Q1 z jednotlivých her.

---

## 0. Architektura (3 vrstvy)

```
┌─────────────────────────────────────────────────────────────┐
│ Vrstva 1 — Motif engine (NOVÝ modul)                        │
│   services/motif_detector.py: taktické motivy na hraném     │
│   i best tahu (fork, pin, skewer, deflection, decoy…)       │
│   → vyplní stub is_tactical_motif/motif_type                │
├─────────────────────────────────────────────────────────────┤
│ Vrstva 2 — Single-game candidates (ÚPRAVA existujícího)     │
│   detect_all(min_games_override) → per-move detektory       │
│   → PatternMatch s TOT flag + candidate registry            │
├─────────────────────────────────────────────────────────────┤
│ Vrstva 3 — Kalibrace z N her (ÚPRAVA + backlog)             │
│   candidate registry → N≥3 → rekalibrace kompresí → promoce │
│   backlog: Declare4Py pilot (declarative discovery)         │
└─────────────────────────────────────────────────────────────┘
```

**Princip:** neměnit gate anti-noise (K5.1), ale parametrizovat kontext. Single game = kandidát (TOT), nikdy promovaný pattern. Promoce jen při replikaci.

---

## Fáze 1 — Fixy (předpoklad, ~0.5 dne)

| # | Úkol | Soubor | Detail |
|---|------|--------|--------|
| F1.1 | **Fix W9** — mistakes se ukládají do `blunders` | `services/game_analyzer.py:359-364` | Rozdělit `elif classification == "mistake"` do `analysis.mistakes`. Dnes je `mistakes` vždy prázdný → kalibrace chybových statistik je zkreslená |
| F1.2 | **Parametrizace gate** | `services/pattern_detector.py:34-48` | `detect_all(analyses, metadata, min_games_override=None)`; v loopu: `min_games = min_games_override if min_games_override is not None else pdef.min_games`. Default chování beze změny (A-Q1 multi-game). |
| F1.3 | **Parametrizace min_occurrences** | `services/pattern_detector.py:45-46` | Stejný vzor: `min_occ = occ_override if occ_override is not None else pdef.min_occurrences`. Single-game režim → 1 |
| F1.4 | Test existence gates | `tests/test_pattern_semantic_contract.py:369-389` | Ověřit, že testy `test_all_detectors_check_min_games` zůstávají zelené (default nezměněn) |

**Verifikace F1:** `pytest tests/` — celá sada zelená.

---

## Fáze 2 — Motif engine (nový modul, ~2–3 dny)

### 2.1 Nový soubor `services/motif_detector.py`

```python
# Rozhraní (návrh)
@dataclass
class MotifHit:
    motif: str                  # "deflection", "fork", "pin", "skewer", ...
    side: str                   # "played" | "missed" (best move)
    ply: int
    move_uci: str
    material_gain_cp: int       # engine-ověřený zisk
    win_prob_delta: float
    confidence: float           # 0-1
    evidence: dict              # FEN, sekvence, engine lines

def detect_motifs(
    board_before: chess.Board,
    move: chess.Move,
    best_move: chess.Move,
    engine_confirm_cp: int,     # ověření z analyze_position / per-move eval
    win_prob_delta: float,
) -> list[MotifHit]:
    """Detekce motivů na hraném tahu (played) i best tahu (missed)."""
```

### 2.2 Taxonomie motivů (v1 — 8 detektorů)

| Motif | Detekce (python-chess) | Zdroj |
|-------|------------------------|-------|
| `deflection` | oběť (material≥3 vs zisk≥5 do 2 ply) + vynucující (check/capture) + engine potvrzení | Lichess theme, §3.2 HmUBpeoJ |
| `decoy` | tažení figury na pole, odkud nemůže bránit | Lichess theme |
| `fork` | hraný/best tah útočí na ≥2 figury ≥jezdec | chess-detect |
| `pin` | x-ray linie přes figuru ke králi/dámě | chess-detect |
| `skewer` | x-ray s vyšší hodnotou vpředu | chess-detect |
| `discovered_attack` | figurkou z krytí linie útočí figura za ní | chess-detect |
| `hanging_piece` | figura nechráněná, napadnutelná | Lichess theme |
| `removing_defender` | výměna/oběť na obránce | chess-detect |

### 2.3 Integrace do analyzy

- `services/game_analyzer.py:353-354` — nahradit `is_tactical_motif=False, motif_type=None` voláním `detect_motifs()` na **hraném tahu** → vyplní `motif_type`/`is_tactical_motif`
- **Missed tactic**: best tah hráčovy strany s `classification in ("blunder","mistake")` + `motif_type(best) is not None` → uložit do `MoveAnalysis.best_move_motif` (nové pole, model `models/game.py:37-53`)
- **Deflekce jako flagship kandidát**: `deflection` detekce na best tahu = missed deflection (HmUBpeoJ ply 17 ekvivalent), na hraném tahu = exploit (ply 25 Bxf7+)

### 2.4 Poznámka k reuse

chess-detect (PyPI 0.2.1, MIT) má architekturu `BaseDetector`+`MoveContext` — **nepřidávat dependency**, implementovat vlastní ~150 řádků na python-chess (již v requirements). Vzor detektoru převzít z chess-detect (MIT, atribuce do docstringu).

**Verifikace F2:**
- `tests/test_motif_detector.py` — FEN fixture: fork, pin, skewer, deflection (HmUBpeoJ ply 25: `r1b1k1nr/pp3pb1/7p/q5p1/1n1p4/2NP4/B1P1NPPP/R1BQK2R w KQkq - 0 13`, tah a2f7 → `deflection`, gain ≥300cp, forcing)
- HmUBpeoJ re-analýza → cache má `motif_type` non-null na ply 25

---

## Fáze 3 — Single-game candidates (Vrstva 2, ~1–2 dny)

### 3.1 Rozšíření `collect_patterns_for_games` (`services/coaching_base.py:32-56`)

```python
def collect_patterns_for_games(analyses, username, mode="multi"):
    # mode="single" → min_games_override=1, min_occ_override=1
    # A, G detektory: v single režimu skipnout (sémanticky nemožné, §2.2 deep dive)
```

- Strukturální skip: `_detect_a`/`_detect_g` vracejí `None` při `len(analyses)==1` (dnes samy ošetřují, ale projít ř. 51-54/154-157)
- Všechny detektory B, C, I, I2, J, N, O, P, Q, Q1, Q2, R, S fungují per-move → **v single režimu projdou automaticky**
- `evidence`/`frequency` sémantika: u single hry `frequency` = počet událostí, ne her (B, J, I2, N takto už počítají)

### 3.2 Candidate registry (nový soubor `services/candidate_registry.py`)

```python
# data/resource_store/candidates_store.json
{
  "<game_id>_<pid>": {
    "pattern_id": "T", "game_id": "HmUBpeoJ",
    "confidence": 0.60, "tot": true,          # TOT flag 0.3-0.6
    "evidence": [...], "game_ids": ["HmUBpeoJ"],
    "motifs": ["deflection@ply25", "missed_deflection@ply17"],
    "ts": "..."
  }
}
```

- Zápis analogicky k `store_patterns` (`resources/pattern_resources.py:39-45`)
- **Promoční pravidlo:** stejný `(pattern_id, signature)` ve ≥3 hrách → přepočítat conf kompresí (`compute_compression`, `compressibility_validator.py:15-26`) → promovat do pattern_store.json

### 3.3 Confidence single-game (upřesnění vzorce)

`compressibility_validator.py` — pro single režim přidat výpočet, který **nezávisí na délce hry** (dnes krátká hra = pod 0.7):
- `final = 0.5*cs + 0.3*es + 0.2*ss` zůstává jako multi-game standard
- Single-game: `conf_single = min(0.5 + 0.15*verified_events, 0.95)`, kde `verified_events` = počet engine-ověřených motif hitů (deterministický fakt, ne délka hry)
- HmUBpeoJ: 1 ověřený hit (ply 25) → 0.65 → TOT; 2 hity (missed + exploit) → 0.8 > 0.7 → **plný kandidát**
- Formule do `KALIBRACE_PLAN` jako doplněk k §2.5

**Verifikace F3:**
- `tests/test_single_game_patterns.py` — detektory B/C/J na single hře vrací match s conf, A/G vrací None
- Regresní test: multi-game mode nemění výstup stávajících testů

---

## Fáze 4 — Dual-side coaching (obě strany, ~0.5–1 den)

| Úkol | Soubor |
|------|--------|
| `collect_single_game` rozšířit o `analyze_pgn(pgn, other_color, ...)` (vzor `tools/analyze_game.py:64-69`) | `services/coaching_base.py:19-29` |
| Vrácení obou analýz + patterns pro obě strany | `collect_patterns_for_games([white, black], "lichess", mode="single")` |
| Prompt 1: přidat `patterns_opponent_json` + `opponent_acpl` | `services/prompt_builder.py:7-44`, `tools/coaching_single_game.py:63-77` |

→ Full analýza partie obě strany = přesně autorova historická metoda (21 her ručně → obě strany).

**Verifikace F4:** HmUBpeoJ volání `lichess_coaching_single_game` vrací patterns neprázdné (kandidát T) + data obou stran v cache.

---

## Fáze 5 — Pattern T (Deflekce) do knihovny (~1 den)

`models/pattern.py:52` `load_baseline()` — přidat:

```python
PatternDef(
    id="T",
    name="Deflection Blindspot",
    pattern_type="author_error",
    mechanism="Player misses or fails to see deflection/decoy sequences "
              "(sacrifice forcing a piece off its defensive duty, e.g. Bxf7+ Kxf7 Rxa5)",
    it_analogy="Opening a trap door under a load-bearing wall instead of checking what it supports",
    detection_method="deflection_motif",
    severity="high",
    mitigation="...",
    detection_rules={
        "motif": "deflection|decoy",
        "sacrifice_floor": 3,     # oběť materiálu (body)
        "gain_floor": 5,          # zisk do 2 ply
        "forcing": True,          # check/capture sekvence
        "engine_confirm_cp": 300,
        "win_prob_delta": 0.15,
    },
    min_games=3,
    min_occurrences=2,
)
```

Detektor `_detect_t` v `pattern_detector.py`: iteruje `moves`, vybírá tahy s `motif_type in ("deflection","decoy")` + `classification in ("blunder","mistake")` (missed) nebo exploit s `eval_after - eval_before > 0`; evidence = MotifHit list.

**Verifikace F5:** `tests/test_pattern_semantic_contract.py` — přidat T do kontraktu (mechanism ↔ detection_rules ↔ kód), `test_all_detectors_check_min_games` pokrývá T automaticky.

---

## Fáze 6 — Kalibrační loop + dokumentace (~1–2 dny)

| Úkol | Detail |
|------|--------|
| Promoční pipeline | script `scripts/promote_candidates.py` (pattern storage → `PatternLibrary` YAML/JSON export + candidate review) |
| Kalibrace z historie | Re-analýza existujících her v cache (153 souborů / ~54 her s dual cache) → first calibration run → report |
| Dokumentace | `KALIBRACE_PLAN` dodatek: single-game confidence vzorec, promoční pravidla, TOT semantika |
| Backlog (ne v v1.0) | Declare4Py pilot: vyjádřit B/C/O jako DECLARE constrainty, discovery na 21 historických hrách (§7.1 deep dive) |

---

## Testovací strategie

| Test | Obsah |
|------|-------|
| `test_motif_detector.py` (nový) | 8 motivů × FEN fixture; deflekce = HmUBpeoJ ply 25 pozice |
| `test_single_game_patterns.py` (nový) | single-mode detekce, A/G skip, TOT conf, kandidát registry |
| `test_candidate_registry.py` (nový) | zápis/čtení, promoční pravidlo ≥3 hry |
| `test_pattern_semantic_contract.py` (úprava) | T pattern kontrakt, min_games default nezměněn |
| End-to-end | HmUBpeoJ: coaching → patterns=[T kandidát], dual cache, konzistence s lichess_analyze_position d18 |

## Acceptance criteria (v1.0)

1. `lichess_coaching_single_game` na HmUBpeoJ vrací `patterns` neprázdné — kandidát T (deflekce) s conf reportovanou (≥0.65, TOT flag)
2. Full analýza partie: obě strany v cache + patterns obou stran v reportu
3. Všechna data deterministická z cache/engine — žádná LLM fabrikace (DATA-FABRICATION-001)
4. Multi-game mode (match_patterns) beze změny chování — stávající testy zelené
5. Pattern z 1 hry je VŽDY kandidát (TOT), promoce až při N≥3

## Rizika

| Riziko | Mitigace |
|--------|----------|
| False-positive motivů (deflekce je fuzzy pojem) | engine_confirm_cp + win_prob_delta jako povinné prahy; TOT flag; promoční replikace |
| Short-game bias confidence vzorce | nový single-game vzorec založený na verified_events, ne délce hry |
| Změna detect_all rozbije stávající tool | min_games_override má default None = beze změny; regresní testy |
| Fabrikace game_id v LLM reportu | evidence nese game_ids z deterministické vrstvy; prompt pravidlo zůstává |
| W9 fix změní čísla v historických reportech | fix je datový (mistakes ≠ blunders), audit vzorová hra před/po |

---

# Amendment v1.1 — Mapování výzkumných nástrojů na epistemologii

**Datum:** 2026-08-02 | **Status:** doplněk k v1.0 (systémová odpověď na deep dive §7)

## A1. Nástroje z deep dive — zařazení

| Nástroj | Stav v plánu | Role (epistemologická) | Řešení |
|---------|--------------|------------------------|--------|
| chess-detect (MIT) | ✅ v plánu (F2.4) | **Dekompozice** — taktické motivy na hraném i best tahu | Reference architektury (`BaseDetector`+`MoveContext`), port 6 motivů, vlastní deflection/decoy; **oracle test**: srovnání s chess-detect na stejném PGN |
| Declare4Py / PM4Py | ✅ backlog (F6) | **Komprese na úrovni constraintů** — constraint zkracuje popis trace | PM4Py NEbrat (těžké). Declare4Py volitelná dependency: B/C/O jako DECLARE constrainty → conformance na cache hrách (54 dual) → support tabulka → audit knihovny |
| SPMF / PrefixSpan | ❌ vyřazen (epistemologický konflikt) | **Mechanické sekvenční čtení** — frekvence ≠ root cause (knižní tahy jsou časté, ale nejsou pattern) | In-house event counter (~30 řádků, dict) na úrovni `(phase, classification, motif)` — 90 % hodnoty, 0 dependency. Revize při korpusu >100 her |
| Rokach & Shapira 2026 | ❌ jako model; ✅ jako taxonomie | **Dekompozice chyb** — immediate (taktické) vs non-immediate (strategické) | `blunder_subtype` pole v motif layer (F2); per-fáze THRESHOLD_* legitimizace (AUC 0.80/0.766/0.835); citace v docs (F5) |

## A2. Kompresní epistemika — formální rámec (Mikolov/CPM + MDL)

Repo deklaruje Lossy Compression Core (`models/pattern.py:1-14`). V1.0 plán je konzistentní, ale chybí formální doménově agnostická opora — **MDL pattern mining**:

- **Krimp** (Siebes et al.) / **SIRIUS, ROCK** (Vreeken): "vzor je validní, pokud zahrnutí do modelu zlepšuje kompresi databáze" — přesná formalizace kompresní epistemiky
- **Vazba na repo:** `compressibility_validator.py` = zjednodušený MDL (compression_ratio = total_moves/pattern_cost). MDL literatura poskytuje: výběr vzorů podle kompresního zisku (ne frekvence), anti-redundanci, formální confidence. Doplnit do F6 jako referenční aparát.

**Čtyři operace pattern discovery (místo sekvenčního čtení):**

```
1. DEKOMPOZICE   hra → layered event streams (motivy, chyby, fáze, materiál)
2. KOMPRESE      pattern = struktura, která zkracuje popis vrstvy (MDL)
3. CLUSTER       podobné komprimované kontexty napříč hrami (FEN/motiv similarity) → kandidát
4. PROMOCE       replikace N≥3 → rekalibrace kompresí → knihovna
```

## A3. Změny proti v1.0

| Změna | Fáze | Popis |
|-------|------|-------|
| `blunder_subtype` (immediate/non-immediate) | F2.2 | nové pole v MoveAnalysis; immediate = taktický motiv, non-immediate = strategický |
| Oracle test chess-detect | F2.4 | fixture PGN → výstup vs chess-detect (externí, dev-only) |
| Declare4Py pilot rozšířen | F6 | support tabulka B/C/O constraintů + srovnání s detektory; výstup = audit knihovny |
| Event counter nahrazuje PrefixSpan | F3 | in-house, bez dependency |
| MDL reference (Krimp/SIRIUS/ROCK) | F6 | dokumentace kompresního rámce |
| Acceptance 6 | v1.0 | `blunder_subtype` vyplněn na chybách HmUBpeoJ (ply 17 Ba2 = non-immediate/strategická, ply 25 = immediate/deflection) |
