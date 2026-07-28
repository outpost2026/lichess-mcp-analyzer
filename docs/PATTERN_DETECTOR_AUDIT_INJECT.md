# Pattern Detector — Deep Audit Context Injection

**Verze:** 1.0 | **Datum:** 2026-07-28  
**Repo:** https://github.com/outpost2026/lichess-mcp-analyzer  
**Branch:** `main` (`feat` pro aktivní vývoj)  
**Účel:** Machine-ready kontextový injekt pro hloubkový audit modulu Pattern detector (14 patternů, DBCL Phase 2)

---

## Obsah
1. [Architektura a data flow](#1-architektura-a-data-flow)
2. [Kompletní zdrojový kód s řádky](#2-kompletní-zdrojový-kód-s-řádky)
3. [Identifikované slabiny (W1-W5)](#3-identifikované-slabiny-w1-w5)
4. [Halucinace — case study](#4-halucinace--case-study)
5. [Chybějící dependencies a blind spots](#5-chybějící-dependencies-a-blind-spots)
6. [Požadavky na refaktor](#6-požadavky-na-refaktor)
7. [Test coverage analysis](#7-test-coverage-analysis)
8. [Lossy Compression Principle — teoretický rámec](#8-lossy-compression-principle--teoretický-rámec)
9. [Přílohy: data schemas](#9-přílohy-data-schemas)

---

## 1. Architektura a data flow

### 1.1 Call chain

```
lichess_match_patterns (tools/match_patterns.py:34)
  ├── [game_ids branch] _find_cached_analysis() → GameAnalysis cache
  │     (tools/match_patterns.py:19-31)
  │
  ├── [username branch] fetch_user_games() → fetch_game_pgn() → analyze_pgn()
  │     (tools/match_patterns.py:86-145)
  │
  └── shared pipeline:
        detector = PatternDetector()                         (line 148)
        detector.detect_all(analyses, metadata)              (line 150)
          ├── pattern_detector.py:26-40 → iteruje přes PatternLibrary
          │     volá _detect_{pid}() na každý pattern
          │     filtruje dle min_games, min_occurrences
          │
        compute_compression(m, analyses)                     (line 154)
          └── compressibility_validator.py:13 → CR = total_moves / (10 + evidence_count*2)
        
        validace: validate_against_schema()                  (line 193)
        validace: validate_pattern_artifact()                (line 198)
        
        store_patterns(resource_key, artifact)               (line 207)
          └── pattern_resources.py:39 → JSON store
```

### 1.2 Data flow diagram

```
GameAnalysis[] ──→ PatternDetector.detect_all()
                       │
                       ├── _detect_a() → PatternMatch(game_ids=[...], evidence=[{...}])
                       ├── _detect_b() → PatternMatch(game_ids=[...], evidence=[{...}])
                       ├── ...
                       └── _detect_s() → PatternMatch(game_ids=[...], evidence=[{...}])
                       │
                       ▼
                 PatternMatch[]
                       │
                       ├── compute_compression() → compression_ratio
                       │
                       ▼
                 Tool response: {
                   "patterns_detected": [{
                     "pattern_id": "J",
                     "evidence": [{"impulsive_blocks": 5, ...}],
                     "affected_games": ??? -- CHYBÍ!
                   }]
                 }
```

### 1.3 Závislosti

| Závislost | Typ | Role v pattern detection |
|-----------|-----|--------------------------|
| `lichess_analyzer_mcp.models.pattern` | dataclasses | PatternDef, PatternMatch, PatternLibrary |
| `lichess_analyzer_mcp.models.game` | dataclasses | GameAnalysis, MoveAnalysis, GameSummary |
| `lichess_analyzer_mcp.models.analysis` | dataclasses | BlunderFactSheet, BoardState, LegalMovesSummary |
| `python-chess` (chess.Board) | externí | FEN parsing, legal moves, pin detection (pattern N, S) |
| `collections.Counter` | stdlib | Pattern O position frequency |

---

## 2. Kompletní zdrojový kód s řádky

### 2.1 `models/pattern.py` — PatternMatch model

**GitHub:** https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/src/lichess_analyzer_mcp/models/pattern.py

```python
# Lines 36-45
@dataclass
class PatternMatch:
    pattern_id: str
    pattern_name: str
    confidence: float
    evidence: list[dict]              # ← volný formát, každý detector píše jinak
    game_ids: list[str]               # ← REQUIRED, všichni plní, ale SERIALIZACE ZAHOZÍ
    frequency: int
    severity: str
    hypothesis: Optional[str] = None
    compression_ratio: Optional[float] = None
```

PatternDef (lines 20-32) a PatternLibrary (lines 48-213) definují 14 patternů včetně PatternDef.min_games (default 3) a PatternDef.min_occurrences (default 2).

### 2.2 `services/pattern_detector.py` — Všech 14 detectorů

**GitHub:** https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/src/lichess_analyzer_mcp/services/pattern_detector.py

#### 2.2.1 Pattern A — Anonymous effect (lines 42-66)
```python
def _detect_a(self, analyses, metadata) -> PatternMatch:
    anonymous_games = [a for a in analyses if "anonymous" in a.game.opponent_name.lower()]
    named_games = [a for a in analyses if "anonymous" not in ...]
    # blunder rate comparison
    evidence: {"anonymous_blunder_rate", "named_blunder_rate", "ratio"}
    game_ids = [g.game.id for g in anonymous_games]   # line 61
    # affected_games CHYBÍ v evidence
```

#### 2.2.2 Pattern B — Automatic grab (lines 68-102)
```python
def _detect_b(self, analyses, metadata) -> PatternMatch:
    # captures with blunder/mistake classification + cp_loss >= 100
    evidence: {"blunder_captures", "total_captures", "blunder_capture_ratio",
               "affected_games": list(set(affected_games)),       # ← line 93 ✅ list[str]
               "total_games"}
    game_ids = list(set(affected_games))                          # line 97
```

#### 2.2.3 Pattern C — Attention tunneling (lines 104-142)
```python
def _detect_c(self, analyses, metadata) -> PatternMatch:
    # consecutive blunders/mistakes >= 2 within a game
    evidence: {"affected_games": len(set(affected)),              # ← line 130 POČET, ne seznam!
               "total_games", "max_consecutive_blunders", ...}
    game_ids = list(set(affected))                                # line 137 ✅
```

#### 2.2.4 Pattern G — Color as modulator (lines 144-182)
```python
def _detect_g(self, analyses, metadata) -> PatternMatch:
    # compare blunder rate White vs Black, ratio > 1.4
    evidence: {"white_blunder_rate", "black_blunder_rate", "asymmetry_ratio", "dominant_side"}
    # affected_games CHYBÍ v evidence
    game_ids = affected_ids                                       # line 177 ✅
```

#### 2.2.5 Pattern I2 — Opponent's gift exploitation (lines 184-214)
```python
def _detect_i2(self, analyses, metadata) -> PatternMatch:
    # best captures with eval jump > 70 from slightly worse to clear advantage
    evidence: {"gift_captures", "total_games", "threshold_eval_jump", "detail"}
    # affected_games CHYBÍ v evidence
    game_ids = list(set(affected))                                # line 209 ✅
```

#### 2.2.6 Pattern J — Impulsive check block (lines 216-247)
```python
def _detect_j(self, analyses, metadata) -> PatternMatch:
    # blunder/mistake + cp_loss >= 150 + was_in_check + "x" not in move_san
    # BUGBUG: chytá i tahy králem (Kd3, Kf7) = false positive
    evidence: {"impulsive_blocks", "total_games", "threshold_cp", "detail"}
    # affected_games CHYBÍ v evidence ← ZPŮSOBILO HALUCINACI!
    game_ids = list(set(affected))                                # line 242 ✅
```

#### 2.2.7 Pattern O — Stagnační panika (lines 249-305)
```python
def _detect_o(self, analyses, metadata) -> PatternMatch:
    # repetition refusal (3x same position) + blunder within 4 moves
    # OR flat eval plateau (3+ moves <30cp swing) + blunder within 6 moves
    evidence: {"affected_games": len(set(affected)),              # ← line 293 POČET
               "total_games", "repetition_confirmed", ...}
    game_ids = list(set(affected))                                # line 300 ✅
```

#### 2.2.8 Pattern P — Visual misrecognition (lines 307-340)
```python
def _detect_p(self, analyses, metadata) -> PatternMatch:
    # blunder/mistake + cp_loss >= 150 + "x" or "Q" or "R" in san + eval_before > 0 + was_in_check
    evidence: {"affected_games": len(set(affected)),              # ← line 328 POČET
               "total_games", "threshold_cp", "condition", "detail"}
    game_ids = list(set(affected))                                # line 335 ✅
```

#### 2.2.9 Pattern Q — Active defense (lines 342-378)
Detekuje: deficit (eval_before < -150) + active response (check/capture) + win.
```python
evidence: {"defensive_wins", "total_games", "threshold_deficit_cp", "detail"}
# affected_games CHYBÍ v evidence
```

#### 2.2.10 Pattern Q1 — Desperate Gambit Mode (lines 380-422)
Detekuje: big blunder (>300cp) + rejected queen trades + 10+ subsequent moves + checks + win.
```python
evidence: {"affected_games": len(set(affected)),                  # POČET
           "total_games", "threshold_eval", "detail"}
```

#### 2.2.11 Pattern Q2 — Win despite blunder (lines 424-456)
Detekuje: big blunder (>300cp) + win.
```python
evidence: {"resilient_wins", "total_games", "threshold_blunder_cp", "detail"}
# affected_games CHYBÍ v evidence
```

#### 2.2.12 Pattern R — Endgame relaxation (lines 458-490)
Detekuje: endgame blunder (cp_loss >= 300) + eval_before > 300.
```python
evidence: {"affected_games": len(set(affected)),                  # POČET
           "total_games", "threshold_eval_before", "threshold_cp_loss", "condition"}
```

#### 2.2.13 Pattern S — Capture aversion under check (lines 492-523)
Detekuje: was_in_check + cp_loss >= 500 + king CAN capture checker (chess.Board analysis) but didn't.
```python
evidence: {"affected_games": len(set(affected)),                  # POČET
           "total_games", "threshold_cp", "detail"}
```

#### 2.2.14 Pattern N — X-ray pin violation (lines 525-558)
Detekuje: blunder/mistake + cp_loss >= 100 + board.is_pinned().
```python
evidence: {"pin_events", "total_games", "threshold_cp", "detail"}
# affected_games CHYBÍ v evidence
```

### 2.3 `tools/match_patterns.py` — Response builder

**GitHub:** https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/src/lichess_analyzer_mcp/tools/match_patterns.py

```python
# Lines 152-170 — THE BUG
result_list = []
for m in matches:
    m = compute_compression(m, analyses)
    entry = {
        "pattern_id": m.pattern_id,
        "pattern_name": m.pattern_name,
        "confidence": round(m.confidence * 100, 0),
        "frequency": m.frequency,
        "severity": m.severity,
        "evidence": m.evidence,           # ← passthrough, žádná normalizace
        "mitigation": ...,
    }
    # m.game_ids NENÍ v entry ← ROOT CAUSE of hallucination
    if m.hypothesis:
        entry["hypothesis"] = m.hypothesis
    if m.compression_ratio is not None:
        entry["compression_ratio"] = m.compression_ratio
    result_list.append(entry)
```

### 2.4 `services/compressibility_validator.py`

**GitHub:** https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/src/lichess_analyzer_mcp/services/compressibility_validator.py

```python
# Lines 13-23
def compute_compression(match: PatternMatch, analyses: list[GameAnalysis]) -> PatternMatch:
    total_moves = sum(len(a.moves) for a in analyses)
    evidence_count = len(match.evidence) if match.evidence else 1
    exception_cost = evidence_count * 2
    pattern_cost = PATTERN_BASE_COST + exception_cost   # PATTERN_BASE_COST = 10
    compression_ratio = total_moves / pattern_cost
    match.compression_ratio = round(compression_ratio, 1)
    return match
```

### 2.5 `services/pattern_artifact_validator.py`

**GitHub:** https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/src/lichess_analyzer_mcp/services/pattern_artifact_validator.py

Validuje: username, games_analyzed >= 1, patterns_detected je list, pattern_id unikátní, confidence 0-100, severity valid, frequency >= 1, hypothesis starts with "Hypothesis:". **Nekontroluje affected_games.**

### 2.6 `models/game.py` — MoveAnalysis

**GitHub:** https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/src/lichess_analyzer_mcp/models/game.py

```python
# Lines 37-61
@dataclass
class MoveAnalysis:
    ply: int
    move_uci: str
    move_san: str
    eval_before: float
    eval_after: float
    centipawn_loss: float
    classification: str          # "best", "good", "inaccuracy", "mistake", "blunder"
    fen: str = ""
    was_in_check: bool = False
```

---

## 3. Identifikované slabiny (W1-W5)

### W1 — CRITICAL: `game_ids` dropped in serialization

| Aspekt | Detail |
|--------|--------|
| **Lokace** | `match_patterns.py:155-170` |
| **Popis** | `PatternMatch.game_ids` (povinné pole, všichni plní) není zahrnuto v response entry |
| **Dopad** | Agent vidí `frequency=5` pro Pattern J, ale neví KTERÝCH 5 her → fabrikace |
| **Fix** | Přidat `"affected_games": list(m.game_ids)` do entry slovníku |

### W2 — HIGH: Evidence schema inconsistent across 14 detectors

| Formát v `evidence[0]` | Počet patternů | Seznam |
|------------------------|----------------|--------|
| `affected_games: list[str]` ✅ | **1** | B (line 93) |
| `affected_games: int` (count) ⚠️ | **6** | C (130), O (293), P (328), Q1 (411), R (478), S (512) |
| `affected_games` absent ❌ | **7** | A, G, I2, J, Q, Q2, N |

### W3 — MEDIUM: `_detect_j` semantic mismatch (king moves as blocks)

| Aspekt | Detail |
|--------|--------|
| **Lokace** | `pattern_detector.py:221-225` |
| **Kód** | `if m.was_in_check and "x" not in m.move_san:` |
| **Problém** | Chytá i tahy králem (Kd3, Kf7) = false positive. Definičně Pattern J = "block with a piece" |
| **Příklad** | `tDcFRclj` ply 29 Kd3 (king move, mistake 282cp, was_in_check=true) — false positive |
| **Fix** | Přidat `"K" not in m.move_san` pro vyloučení královských tahů |

### W4 — LOW: Pattern S/J overlap

Pattern S (capture aversion under check, line 492) a Pattern J (impulsive check block, line 216) se mohou překrývat: pokud hráč mohl brát šachující figurou králem ALE blokoval → oba patterny by detekovaly stejný tah. Není implementována deduplikace ani dokumentace overlapu.

### W5 — MEDIUM: `affected_games` type mismatch

U patternů C, O, P, Q1, R, S je `affected_games` v evidence typu **int** (počet her) namísto `list[str]` (seznam ID). To znemožňuje agentovi identifikovat konkrétní hry i po fixu W1.

---

## 4. Halucinace — case study

### 4.1 Incident

**Datum:** 2026-07-28 | **Pipeline:** lichess-analyzer-mcp | **Model:** DeepSeek V4 Flash

**Tvrzení v reportu (FABRIKACE):**
> "Konkretni priklad (z cache: sAtfdKTi ply 16): Hrac ma vyhodu ~+4.6, souper da sach dámou. Misto brani vezi (coz drzi vyhodu) nebo ustupu krále, hrac blokuje jezdcem a po 2 tazich uz ma jen +0.5."

**Realita:** `sAtfdKTi` ply 16 = **O-O** (castling). Žádný šach. `was_in_check=false` u všech 52 tahů hry.

### 4.2 Chain of causality

1. **Pipeline gap:** `lichess_match_patterns` vrátilo Pattern J s `frequency=5` ale **bez `affected_games`**. Na rozdíl od Pattern B, který `affected_games` měl.
2. **Agent nedisciplína:** Agent měl cache s `sAtfdKTi_black_d12.json` (52 tahů, was_in_check=false) — nezkontroloval.
3. **Agent fabrikace:** Věděl že sAtfdKTi ply 16 je mistake 220cp s eval drop 465→240. Usoudil "mistake + eval drop = pravděpodobně šach" a dopsal detaily.

### 4.3 Data dostupná v té době

| Zdroj | Co obsahoval | Použito? |
|-------|-------------|----------|
| `cache/hrLawxDC_white_d12.json` | ply 89: Rb3 blunder 840cp, was_in_check=true | ❌ |
| `cache/9WlaBdkU_white_d12.json` | ply 19: Qe2 inaccuracy 53cp, was_in_check=true | ❌ |
| `cache/sAtfdKTi_black_d12.json` | 52 tahů, was_in_check=false | ❌ |
| `lichess_match_patterns(game_ids=...)` | Měl affected_games pro B, neměl pro J | ❌ |

### 4.4 Tři vrstvy ochrany (po fixu)

1. **Prompt**— explicitní zákaz fabrikace + [DATA] vs [IM] oddělení
2. **AGENTS.md §6**— DATA-FABRICATION-001: ověř z cache/tool, nebo neuváděj
3. **Tool response**— musí vracet `affected_games: list[str]` pro každý pattern (tento audit)

---

## 5. Chybějící dependencies a blind spots

### 5.1 Chybějící závislosti

| Missing | Kde | Proč chybí |
|---------|-----|------------|
| **Board state tracking** pro `_detect_j` | `pattern_detector.py:225` | Nelze detekovat skutečný "block" z move_san samotného. Chybí `LegalMovesSummary.blocks` — v současnosti plněno jen v BlunderFactSheet (per blunder), ne v obecném GameAnalysis |
| **Normalizovaný evidence formatter** | — | Každý detector píše `evidence[0]` ručně jako dict. Chybí helper/validátor, který by vynutil `affected_games: list[str]` |
| **BlunderFactSheet.board_state** pro všechna pattern detection | `models/analysis.py:9-17` | BoardState existuje ale je plněn jen pro blunder/error move akce, ne pro všechny tahy. Patterny J, S potřebují `was_in_check`, ale `MoveAnalysis.was_in_check` je boolean bez kontextu (která figura šachuje?) |
| **Chess.Board pro každý tah** | `pattern_detector.py` | Pouze patterny N (line 532) a S (line 497) vytvářejí Board. Pro plnohodnotnou J detekci by musel každý tah mít board context |
| **Per-pattern threshold konfigurace** | `pattern_detector.py:9-19` | Thresholdy jsou hardcoded jako globální konstanty. Nelze per-pattern kalibrovat |

### 5.2 Blind spots (co není detekováno ale mělo by být)

| Blind spot | Kde | Důvod |
|------------|-----|-------|
| **King moves under check** false positive pro Pattern J | `pattern_detector.py:225` | Detekce `was_in_check + no capture` chytá i krále. Pattern J by měl detekovat jen bloky figurou |
| **Overlap S/J** | `pattern_detector.py:216, 492` | Stejný tah může splnit podmínky pro oba patterny |
| **Q + Q2 duplicita** | `pattern_detector.py:342, 424` | Q i Q2 detekují "win despite blunder". Q navíc vyžaduje active response. Mohou se překrývat |
| **I2 confidence příliš vysoká** | `pattern_detector.py:200` | Confidence = `gift_count / total_games * 0.8`, cap 0.9. Pro 1 gift v 35 hrách = 2.3% → 0.023*0.8 = 0.018 → cap 0.9? To je absurdní. Vzorec je broken pro nízké frekvence |
| **Pattern A — "anonymous" string match** | `pattern_detector.py:43` | Detekuje "anonymous" v opponent_name. Funguje jen pro Lichess anonymous účet (správně), ale nerozlišuje "anonymous" jako username |

### 5.3 Debugging/metrika gaps

| Gap | Dopad |
|-----|-------|
| **Žádná per-detector confidence formula dokumentace** | Nelze ověřit, zda confidence reflektuje realitu (data-driven) nebo je heuristická |
| **Žádný log per-game detection (které patterny v které hře)** | Pattern detection je "všechny hry → seznam patternů". Chybí reverzní index: "hra X → patterny Y" |
| **Žádný threshold calibration mechanismus** | Thresholdy (THRESHOLD_GRAB_CP=100, THRESHOLD_BLOCK_CP=150) jsou empirické, nekalibrované |
| **compressibility_validator nepoužívá compression vzorec z README** | README říká: `final = 0.5×compression + 0.3×entropy + 0.2×sample`, ale `compute_compression` počítá jen `CR = total_moves / (10 + evidence*2)`. Entropy a sample skóre neimplementovány |

---

## 6. Požadavky na refaktor

### 6.1 P0 — Must fix (data integrity)

```
[W1] match_patterns.py:155-170 — add "affected_games": list(m.game_ids)
[W2] pattern_detector.py — normalize evidence format across all 14 detectors:
     EVERY evidence[0] MUST include "affected_games": list[str]
     CURRENT: B=correct, C/O/P/Q1/R/S=int (fix to list), A/G/I2/J/Q/Q2/N=absent (add)
```

### 6.2 P1 — Should fix (semantic integrity)

```
[W3] pattern_detector.py:225 — exclude king moves from _detect_j:
     ADD: "K" not in m.move_san
     NOTE: This reduces J frequency but improves semantic integrity

[I2 confidence] pattern_detector.py:200 — fix formula for low frequencies:
     CURRENT: min(gift_count / total_games * 0.8, 0.9) → for 1/35 → 0.023 → cap 0.9 = WRONG
     PROPOSED: min(gift_count / max(total_games, 1) * 0.8, 0.9) with floor check

[compressibility] compressibility_validator.py — align with README formula:
     ADD: entropy_score + sample_score components
```

### 6.3 P2 — Nice to fix

```
[W4] Document S/J overlap in pattern_detector.py docstring
[BoardState] Add BoardState to every MoveAnalysis (not just blunder context)
[Per-game index] Create reverse index: game_id → [pattern_ids]
[Threshold calibration] Make thresholds configurable per-pattern
```

### 6.4 Konkrétní změny v kódu (diff template)

**match_patterns.py:155:**
```python
# BEFORE:
entry = {
    "pattern_id": m.pattern_id,
    "frequency": m.frequency,
    "evidence": m.evidence,
    # NO game_ids
}

# AFTER:
entry = {
    "pattern_id": m.pattern_id,
    "frequency": m.frequency,
    "evidence": m.evidence,
    "affected_games": list(m.game_ids),     # <-- ADDED
}
```

**pattern_detector.py — normalize evidence (example for Pattern C):**
```python
# BEFORE (line 128-135):
evidence=[{
    "affected_games": len(set(affected)),   # int
    "total_games": total_games,
}]

# AFTER:
evidence=[{
    "affected_games": list(set(affected)),  # list[str]
    "total_games": total_games,
}]
```

**pattern_detector.py:225 — fix J:**
```python
# BEFORE:
if m.was_in_check and "x" not in m.move_san:

# AFTER:
if m.was_in_check and "x" not in m.move_san and "K" not in m.move_san:
```

---

## 7. Test coverage analysis

### 7.1 Exisiting tests (`tests/test_pattern_semantic_contract.py`)

**Link:** https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/tests/test_pattern_semantic_contract.py

| Test | Co testuje | Coverage poznámka |
|------|-----------|-------------------|
| `test_b_automatic_grab_positive` (line 100) | Detekce capture blunderů >= 2 | ✅ |
| `test_b_automatic_grab_negative` (line 112) | False negative pro 1 capture | ✅ |
| `test_c_tunneling_positive` (line 126) | 2 consecutive errors | ✅ |
| `test_c_tunneling_negative` (line 137) | Bez consecutive errors | ✅ |
| `test_o_repetition_refusal_positive` (line 151) | 3x repetition + blunder | ✅ |
| `test_o_repetition_refusal_negative` (line 183) | Bez repetition | ✅ |
| `test_p_visual_misrecognition_positive` (line 197) | Rxe5 blunder in check | ✅ |
| `test_p_visual_misrecognition_negative` (line 215) | Non-expensive move | ✅ |
| `test_q_active_defense_positive` (line 229) | Deficit + active + win | ✅ |
| `test_q_active_defense_negative` (line 243) | Passive defense | ✅ |
| `test_q2_resilience_positive` (line 258) | Blunder + win | ✅ |
| `test_q2_resilience_negative` (line 273) | Blunder + loss | ✅ |
| `test_s_capture_aversion_positive` (line 288) | King could capture but didn't | ✅ |
| `test_s_capture_aversion_negative` (line 311) | No check situation | ✅ |
| `test_n_xray_pin_positive` (line 332) | Pinned piece blunder | ✅ |
| `test_n_xray_pin_negative` (line 345) | No pin | ✅ |
| `test_all_patterns_have_detectors` (line 359) | Každý PatternDef (krom manual_only) má _detect_ method | ✅ |
| `test_all_detectors_check_min_games` (line 369) | Single game → žádný pattern s min_games>1 | ✅ |

### 7.2 Missing test coverage

| Chybí test | Důležitost |
|------------|-----------|
| **Pattern J positive** (false positive fix): blok figurou v šachu → detected | **HIGH** — bez testu se fix W3 nedá ověřit |
| **Pattern J negative**: král v šachu, král utíká → NOT detected | **HIGH** |
| **Pattern J negative**: šach, hráč bere šachující figuru → NOT detected | **HIGH** |
| **Pattern A positive/negative** | **MEDIUM** |
| **Pattern G positive/negative** | **MEDIUM** |
| **Pattern I2 positive/negative** | **MEDIUM** |
| **Pattern Q1 positive/negative** | **MEDIUM** |
| **Evidence affected_games format test**: každý PatternMatch má `affected_games: list[str]` jako non-empty | **HIGH** — regresní test pro W2 |
| **Tool response affected_games test**: response obsahuje `affected_games` jako list | **HIGH** — regresní test pro W1 |
| **Pattern S positive**: was_in_check + king CAN capture + cp_loss >= 500 + didn't capture | CURRENT |
| **Pattern S negative**: was_in_check + king CANNOT capture | CHYBÍ |
| **Pattern N negative**: move from pinned square but pin is to same-value piece | CHYBÍ (false positive edge case) |

---

## 8. Lossy Compression Principle — teoretický rámec

### 8.1 Základní princip (Mikolov CPM)

Pattern detection = **lossy compression**. Cílem je najít vzory s maximální entropickou hodnotou na minimum tokenů.

### 8.2 Sémantická integrita jako prerequisite

**CR = N / (C_impl + C_udrz) dává smysl POUZE pokud N = počet instancí téže věci.**

Pokud popis patternu neodpovídá kódu:
- CR není kompresní poměr, je to míra klamu
- Každá instance je false positive vůči popisu
- Entropická hodnota = 0

**Exemplární selhání — Pattern O (AUD-04):**
| Vrstva | Původní (špatně) | Po fixu (správně) |
|--------|------------------|-------------------|
| Jméno | "Repetition avoidance greed" | "Stagnační panika" |
| Kód | Flat eval plateau → blunder | Flat eval plateau → blunder (stejný) |
| Výsledek | CR=47.8 měří noise | CR=47.8 měří signal |

### 8.3 Confidence formula (z README — neimplementováno)

```
final_confidence = 0.5 × compression_score + 0.3 × entropy_score + 0.2 × sample_score
```

Současný `compute_compression()` počítá jen `CR = total_moves / (10 + evidence_count*2)`. Zbylé 2 komponenty (entropy, sample) nejsou implementovány.

---

## 9. Přílohy: data schemas

### 9.1 PatternMatch (aktuální)

```python
@dataclass
class PatternMatch:
    pattern_id: str        # e.g. "J"
    pattern_name: str      # e.g. "Impulsive check block"
    confidence: float      # 0.0 - 1.0 (before *100 in tool response)
    evidence: list[dict]   # volný formát — PROBLEM
    game_ids: list[str]    # [game_id, ...] — správně plněno
    frequency: int         # počet výskytů
    severity: str          # "critical" | "high" | "medium" | "low"
    hypothesis: Optional[str]
    compression_ratio: Optional[float]
```

### 9.2 Tool response (aktuální — s chybou W1)

```json
{
  "username": "anonymous",
  "games_analyzed": 35,
  "patterns_detected": [
    {
      "pattern_id": "J",
      "pattern_name": "Impulsive check block",
      "confidence": 12.0,
      "frequency": 5,
      "severity": "high",
      "evidence": [
        {
          "impulsive_blocks": 5,
          "total_games": 35,
          "threshold_cp": 150,
          "detail": "Player was in check and blocked..."
        }
      ],
      "mitigation": "When in check: evaluate king moves..."
    }
  ]
}
```

### 9.3 Tool response (po fixu W1+W2 — žádoucí)

```json
{
  "patterns_detected": [
    {
      "pattern_id": "J",
      "confidence": 12.0,
      "frequency": 5,
      "evidence": [
        {
          "impulsive_blocks": 5,
          "total_games": 35,
          "affected_games": ["hrLawxDC", "9WlaBdkU", "tDcFRclj", "...", "..."],
          "threshold_cp": 150,
          "detail": "Player was in check and blocked..."
        }
      ],
      "affected_games": ["hrLawxDC", "9WlaBdkU", "tDcFRclj", "...", "..."]
    }
  ]
}
```

---

## Reference

| Dokument | Link |
|----------|------|
| Root cause analysis (halucinace) | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/docs/HALUCINACE_ROOT_CAUSE_ANALYSIS.md |
| Context injection (hlavní) | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/docs/CONTEXT_INJECT.md |
| Context a záměr | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/docs/CONTEXT_A_ZAMER.md |
| Pattern detection (14 detectorů) | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/src/lichess_analyzer_mcp/services/pattern_detector.py |
| PatternMatch model | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/src/lichess_analyzer_mcp/models/pattern.py |
| Tool response builder | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/src/lichess_analyzer_mcp/tools/match_patterns.py |
| Kompresní validátor | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/src/lichess_analyzer_mcp/services/compressibility_validator.py |
| Artifact validator | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/src/lichess_analyzer_mcp/services/pattern_artifact_validator.py |
| GameAnalysis model | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/src/lichess_analyzer_mcp/models/game.py |
| GameAnalysis.auto_annotate | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/src/lichess_analyzer_mcp/models/game.py#L89 |
| Semantic contract tests | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/tests/test_pattern_semantic_contract.py |
| README (CZ) | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/README.md |
| Lossy Compression Principle | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/docs/MIKOLOV_KOMPRESE_V_PATTERN_ARCHITEKTURE.md |
| Coaching report (35 her — obsahuje halucinaci) | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/docs/coaching_report_anonymous_session_35.md |
| Kalibrační plán | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/docs/KALIBRACE_PLAN_2026-07-19.md |
| AGENTS.md (DATA-FABRICATION-001) | https://github.com/outpost2026/lichess-mcp-analyzer/blob/main/AGENTS.md (master _github) |
