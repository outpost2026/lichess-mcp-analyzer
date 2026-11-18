# DBCL — Deterministic Blunder Context Layer

**Cross-Audit Artifact | Verze: 1.0 | Datum: 2026-07-24**
**Účel:** Strukturovaný dokument pro cross-validaci jiným LLM. Dokumentuje bottleneck deterministic→probabilistic bridge v MCP chess coach serveru, root cause halucinací, transfer learning z jiných domén, a navrhovanou architekturu DBCL.

---

## 1. Executive Summary

### 1.1 The Problem

LLM-based chess coaching pipelines hallucinate because the probabilistic model (LLM) is asked to perform both **detection** (find errors in a chess game) and **narration** (explain them in natural language). Detection requires exact board-state computation — which LLMs cannot do reliably. Narration is what LLMs excel at. Conflating the two in a single prompt guarantees hallucination.

### 1.2 The Bottleneck

```
deterministic data pool (PGN, FEN, Stockfish eval)
    ↓
[BRIDGE]  ← CURRENT WEAKNESS: unstructured aggregation, no fact sheets
    ↓
probabilistic LLM → narration
```

The bridge currently passes **aggregated statistics** (total ACPL, blunder count, phase averages). It does **not** pass:
- Position-level FEN before/after each blunder
- Whether the player was in check
- Which captures were legal
- Top engine lines ranked by eval
- Pattern match per blunder (not just per game)

### 1.3 The Fix

Replace the aggregated bridge with a **Deterministic Blunder Context Layer (DBCL)** that produces typed `BlunderFactSheet[]` objects. LLM role changes from "analyst who finds and explains errors" to "translator who narrates pre-found errors from structured facts."

---

## 2. System Context

### 2.1 MCP Server Architecture (Current)

```
┌─────────────────────────────────────────────────────────────────┐
│                    lichess-analyzer-mcp                          │
│                                                                  │
│  fetch_games ──→ Stockfish 18 ──→ game_cache.json                │
│       │               │                    │                      │
│       │         pattern_detector.py   match_patterns tool          │
│       │               │                    │                      │
│       └───────────────┴────────────────────┘                      │
│                           │                                       │
│                    aggregated data:                                │
│                    {total_acpl, blunders[], patterns[],            │
│                     phase_stats, leaky_openings}                   │
│                           │                                       │
│                      LLM prompt ←───  HERE BE HALLUCINATIONS      │
│                           │                                       │
│                    coaching narrative                              │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Pipeline Components (Existing)

| Component | Language | Role | Determinisic? |
|-----------|----------|------|---------------|
| `fetch_recent_games` | Python | Stahne hry z Lichess API | ✅ |
| Stockfish 18 (BMI2) | C++ | Evaluace pozic depth 14 | ✅ |
| `game_cache.json` | JSON | Per-ply eval, classification, blunders | ✅ |
| `pgn_cache/` | PGN | Raw game notation | ✅ |
| `pattern_detector.py` | Python | A-Q1 pattern detection (11 patterns) | ✅ |
| `match_patterns` tool | Python | Detects patterns across games | ✅ |
| `analyze_position` tool | Python | Stockfish position eval via MCP | ✅ |
| **LLM prompt (coaching)** | text | Generates narrative coaching | ❌ |

### 2.3 Data Flow Detail

```
PGN ──→ Stockfish ──→ game_cache.json
                         │
                    per-move:
                    {ply, move_san, classification,
                     centipawn_loss, eval_before, eval_after,
                     phase, move_uci}
                         │
                    aggregated into tool output:
                    {total_acpl, blunders[], mistakes[],
                     inaccuracies[], phase_stats}
                         │
                    passed to LLM prompt as text blob
```

---

## 3. Incident Report: kNAMNYUF ply 63 (Rdg1)

### 3.1 What Actually Happened

Source truth from deterministic pipeline:

```
FEN before: r4r1k/1p1b3P/p3p1R1/3p3Q/3N1q2/8/PPP4P/1K1R4 w - - 1 32
Eval before: +823 cp       (decisive advantage)
Move played: Rdg1           (rook d1 → g1)
Eval after:  +45 cp         (nearly equal)
Loss:        950 cp
Phase:       endgame
Was in check: false          ← COMPUTED, NOT GUESSED
Legal moves: 38 total, including Nxe6 (+920), Rg8+ (+901), Qe5+ (+887)
Rank of played: 38/38       ← worst legal move
```

### 3.2 What LLM Generated (Fabrication)

> "Qf4+ dává šach. Místo ústupu králem (Ka1 nebo Kc1) jsi instinktivně zablokoval věží — Rdg1."

Three hallucinations in one sentence:
1. **Qf4+ was not a check** — queen on f4, king on b1: delta +3 ranks, +4 files. Not a diagonal. Not check. (Confidence: 100% — computed from FEN.)
2. **Rdg1 does not block anything** — rook d1→g1 does not change any line or diagonal to the king. No check to block. (Confidence: 100% — verified against board topology.)
3. **Ka1 and Kc1 are not relevant** — king was not in check, no evasion needed. Only Ka1 is a legal king move (not needed). Kc1 is not legal. (Confidence: 100% — legal moves list from python-chess.)

### 3.3 Root Cause Chain

```
LLM prompt contains: {blunders: [{ply:63, move:"Rdg1", loss:950, ...}]}
    ↓
LLM sees "Q on f4" + "K on b1" in FEN string (embedded in some context)
    ↓
Pattern completion: "queen near king = check"
    ↓
Position schema activated: check → response must be block or evade
    ↓
"Rdg1" mapped to "block" (rook interposes... but doesn't)
    ↓
Plausible narrative generated: "Qf4+ check → impulsive block with Rdg1"
    ↓
OUTPUT: 3 hallucinated claims
```

**Root cause: LLM was asked to derive board-state facts from incomplete data.** The FEN was present somewhere in the context but never explicitly parsed. The LLM used heuristics (piece proximity ≈ check) instead of calculation (geometry of attack).

### 3.4 Why Deterministic Part Could Not Prevent This

The game_cache.json and pgn_cache contain ALL data needed to prevent this hallucination:

```json
// In game_cache — available but NOT passed to LLM:
{"ply": 62, "fen": "r4r1k/.../1K1R4 w - - 1 32", "eval": 823}
```

```python
# Computable from PGN but NOT computed before prompt:
board.is_check()  # would return False
[board.san(m) for m in board.legal_moves]  # 38 moves, none block a check
```

The deterministic data exists but is not **extracted, structured, and verified** before LLM injection.

---

## 4. Transfer Learning Matrix

Solutions from other domains that address the same deterministic→probabilistic bridge problem.

### 4.1 Take Take Take (Magnus Carlsen's chess app)

| Attribute | Detail |
|-----------|--------|
| Source | AI Engineer conference 2026 — Anant Dole, Asbjorn Steinskog |
| Domain | Consumer chess coaching app |
| Problem | LLMs can explain but can't play chess; Stockfish plays but can't explain |
| Solution | Detectors extract concepts (forks, pins, skewers, structural themes) → structured signals → LLM translates only |
| Key insight | "Keeping the model as a translator rather than a reasoner is what makes it work at sub-3-second latency." |
| Transfer | Replace "LLM finds errors" with "LLM explains errors found by deterministic detectors." |
| Evidence | Sub-3s latency, Gemini Flash as translator, 16 eval scenarios with LLM-as-judge |
| Adaptability | HIGH — identical problem domain (chess coaching), identical separation pattern |
| Limitation | Proprietary — no public code; described at conference only |

### 4.2 VeNRA — Verifiable Numerical Reasoning Agent (arxiv 2603.04663)

| Attribute | Detail |
|-----------|--------|
| Source | arXiv 2603.04663, Mar 2026 |
| Domain | Financial document analysis |
| Problem | LLMs conflate "Net Income" with "Net Sales" (semantic proximity), arithmetically incompetent |
| Solution | Universal Fact Ledger (UFL): typed variables with Double-Lock Grounding → LLM generates only Python code, never raw numbers |
| Key insight | "By acknowledging that LLMs are fundamentally probabilistic sequence generators, VeNRA surgically removes their responsibility to perform arithmetic." |
| Transfer | Replace "LLM evaluates chess positions" with "LLM generates only narrative from pre-computed facts." |
| Evidence | Double-Lock: character-offset alignment + semantic schema validation. Sentinel SLM audits traces. |
| Adaptability | MEDIUM — financial domain, but the UFL pattern maps directly to BlunderFactSheet |
| Limitation | 3B SLM Sentinel may be overengineered for chess; simpler validator may suffice |

### 4.3 Compiled AI (Deterministic LLM Systems)

| Attribute | Detail |
|-----------|--------|
| Source | dev.to, June 2026 |
| Domain | General software engineering |
| Problem | LLMs produce inconsistent results for same input; no reproducibility |
| Solution | Two-phase: compile time (LLM builds corpus of schemas/templates/code) → runtime (deterministic execution from corpus) |
| Key insight | "Once we trust the corpus, we treat its publication as a release — the same release process traditional software systems use." |
| Transfer | Stockfish analysis = compile time. BlunderFactSheet[] = corpus. LLM generation = runtime. Never invoke LLM without fact sheet. |
| Evidence | Backtrace capability — every runtime element traces to corpus element |
| Adaptability | HIGH — architecture-agnostic pattern |
| Limitation | Requires corpus validation before release (CI/CD integration needed) |

### 4.4 Neural Fact Sheets / Retrieve-Then-Write

| Attribute | Detail |
|-----------|--------|
| Source | TruthVouch, multiple engineering blogs 2024-2026 |
| Domain | Enterprise AI documentation |
| Problem | LLM invents statistics, names, dates not present in source material |
| Solution | Pre-extract facts from sources → LLM writes only against approved fact list → validation pass catches fabrication |
| Key insight | "Extraction is a much easier task than generation. Asking 'is this claim in the text' is close to a lookup." |
| Transfer | Extract blunder facts from PGN/FEN/Stockfish → LLM writes only from these facts → validate output against fact sheet |
| Evidence | Claimed 60-96% hallucination reduction with RAG; validation pass catches residuals |
| Adaptability | VERY HIGH — domain-agnostic pattern, minimal overhead |
| Limitation | Validation pass adds latency; requires structured fact extraction pipeline |

### 4.5 Blunder Tutor (Self-Hosted Chess Trainer)

| Attribute | Detail |
|-----------|--------|
| Source | mrlokans.work, Mar 2026 |
| Domain | Chess training |
| Problem | Naive eval-delta thresholding produces false positives (mate-in-N prolongation classified as blunder) |
| Solution | Pipeline: Stockfish → Move Quality (winning-chances sigmoid) → Phase Detection → Tactical Pattern Detection (python-chess, no engine) → Trap Detection → SQLite. EnginePool for async operations. |
| Key insight | "The PV is the engine's best-play sequence for both sides — it shows what concretely happens after the best move." PV-first explanation: resolve mate → PV analysis (captures, material delta, mate in line) → static fallback. |
| Transfer | Use winning-chances sigmoid (not raw cp) for classification. PV-first explanation structure. Tactical motif detection via python-chess (fork/pin/skewer/discovered attack). |
| Evidence | 600+ test suite, CI golden set, deterministic grounding checks |
| Adaptability | HIGH — same domain, directly applicable code patterns |
| Limitation | Template-based narration (no LLM) — different tradeoff |

### 4.6 Lichess Analysis Architecture (lila)

| Attribute | Detail |
|-----------|--------|
| Source | github.com/lichess-org/lila, open source |
| Domain | Chess platform analysis |
| Problem | Limited server resources for analysis; need deterministic, strong, fast per-move classification |
| Solution | Backwards analysis with hash table chunking. Win% classification via Advice.scala: CpAdvice (centipawn delta thresholds) + MateAdvice (mate sequence classification). Fishnet distributed analysis network. |
| Key insight | "At equal resources used, chunking with overlap can close the gap between fishnet 2.7.0 and sequential backwards-analysis." Hash table priming with overlap improves eval consistency. |
| Transfer | Backwards analysis for faster Stockfish re-eval. Win% classification thresholds (10%/20%/30% for inaccuracy/mistake/blunder). Dead-end position handling (once mate inevitable, only flag dramatic changes). |
| Evidence | Production-proven at scale (millions of games/day). MSE + misprediction rate as quality metrics. |
| Adaptability | HIGH — same domain, open source reference implementation |
| Limitation | No LLM component; classification-only |

---

## 5. Architecture: DBCL (Deterministic Blunder Context Layer)

### 5.1 Principle

**Detection must be deterministic. LLM must be translator, not reasoner.**

```
Current:   Data → LLM → LLM finds errors + LLM explains → narrative
                                              ↑
                                        hallucination zone

Proposed:  Data → Deterministic Detectors → Fact Sheets → LLM translates → narrative
                                                  ↑
                                          no hallucination possible
```

### 5.2 Component Design

#### 5.2.1 eval_delta_threshold.py

```
Input:  game_cache.json (per-move eval data)
Output: list of BlunderWindow objects

Algorithm:
  for each game:
    for each move:
      delta = abs(eval_before - eval_after)
      if delta > THRESHOLD_BLUNDER (300cp):
        mark as blunder window
      if classification == "blunder" or "mistake":
        mark as anomaly
      if consecutive_errors >= 2:
        mark as collapse window
    for each blunder window:
      expand context: ±3 moves
      extract: ply_range, eval_curve, classification_sequence
```

#### 5.2.2 context_extractor.py

```
Input:  BlunderWindow[], PGN file, game_cache.json
Output: BlunderFactSheet[]

For each blunder:
  1. Replay PGN to ply-1
  2. Extract FEN before blunder
  3. Compute: board.is_check()
  4. Classify legal moves:
     - captures (with piece type)
     - king_moves (legal king destinations)
     - blocks (interpositions)
     - checks (moves giving check)
  5. Check: capture_checking_piece_possible?
     - If in check: is there a legal capture of checking piece?
     - If king capture: was it played?
  6. Rank played move: position in legal_moves sorted by eval
  7. Run pattern matcher on this blunder (not whole game):
     - B (automatic grab): capture blunder?
     - J (impulsive block): check + block instead of king move?
     - S (capture aversion): in check + king capture available + not taken?
     - R (endgame relaxation): eval_before > 300 && phase == endgame?
     - C (attention tunneling): consecutive errors?
  8. Return BlunderFactSheet
```

#### 5.2.3 BlunderFactSheet Schema

```json
{
  "$schema": "DBCL v1.0",
  "game_id": "string",
  "ply": "integer",
  "move_played_san": "string",
  "move_played_uci": "string",
  "centipawn_loss": "float",
  "eval_before": "float | null",
  "eval_after": "float | null",
  "fen_before": "string (FEN)",

  "board_state": {
    "was_in_check": "boolean",
    "checking_pieces": ["square", "..."],
    "capture_checking_piece_possible": "boolean",
    "king_capture_possible": "boolean",
    "king_capture_played": "boolean | null"
  },

  "legal_moves": {
    "total": "integer",
    "captures": ["SAN", "..."],
    "king_moves": ["SAN", "..."],
    "blocks": ["SAN", "..."],
    "checks": ["SAN", "..."]
  },

  "engine_lines": [
    {
      "rank": "integer",
      "move_san": "string",
      "eval_cp": "float",
      "pv": ["SAN", "..."]
    }
  ],

  "played_move_rank": "integer",

  "phase": "opening | middlegame | endgame",

  "pattern_matches": [
    {
      "pattern_id": "string (A-Q1 + S)",
      "pattern_name": "string",
      "confidence": "float (0-1)",
      "evidence": "string"
    }
  ],

  "context_window": {
    "moves_before": [
      {"ply": "integer", "move_san": "string", "eval_after": "float"}
    ],
    "moves_after": [
      {"ply": "integer", "move_san": "string", "eval_after": "float"}
    ]
  }
}
```

#### 5.2.4 LLM Prompt Guard (template)

```
=== SYSTEM ===
You are a chess coach translator. You are given DETERMINISTIC BlunderFactSheet
objects. Your ONLY job is to produce natural-language coaching narrative FROM
THESE FACTS. You do not find errors — they are already found.

RULES (violation = hallucination):
1. Every claim about the board state MUST trace to the BlunderFactSheet.
2. If was_in_check=false, DO NOT say the player was in check.
3. If capture_checking_piece_possible=false, DO NOT say a capture was possible.
4. Engine lines are the SOLE source for "what should have been played."
5. Pattern matches are the SOLE source for psychological/behavioral analysis.
6. If a fact sheet field is null, DO NOT guess — write around the gap.
7. NEVER invent a variation, eval, or motive not in the fact sheet.

=== INPUT ===
BlunderFactSheet[]:
<fact sheets here>

=== OUTPUT ===
Coaching narrative. Each section addresses one BlunderFactSheet.
Use field names from fact sheet explicitly.
```

#### 5.2.5 Validator (adversarial)

```
Input:  LLM narrative string + BlunderFactSheet[]
Output: Pass/Fail + list of unsupported claims

Algorithm:
  1. Extract all chess claims from narrative:
     - Piece on square statements (regex: [KQRBN]?[a-h][1-8])
     - Check statements ("gives check", "is check", "+")
     - Capture statements ("takes", "captures", "x")
     - Eval statements (numbers ±)
  2. For each claim:
     - Check existence in ANY BlunderFactSheet in the batch
     - If not found → UNSUPPORTED CLAIM → flag
  3. If any unsupported claim → FAIL (reject output)

Example:
  "Qf4+ dává šach"
    → Qf4 on board? YES (from FEN)
    → gives check? NO (from was_in_check=false)
    → UNSUPPORTED → FAIL
```

### 5.3 Integration into MCP Pipeline

```
                       PGN
                        ↓
                  Stockfish 18
                        ↓
                game_cache.json
                        ↓
         ┌──────────────────────────────┐
         │  eval_delta_threshold.py     │  NEW
         │  → BlunderWindow[]           │
         └──────────────────────────────┘
                        ↓
         ┌──────────────────────────────┐
         │  context_extractor.py        │  NEW
         │  → BlunderFactSheet[]        │
         └──────────────────────────────┘
                        ↓
         ┌──────────────────────────────┐
         │  pattern_matcher (per-fact)  │  MODIFIED
         │  → enriched BlunderFactSheet │
         └──────────────────────────────┘
                        ↓
         ┌──────────────────────────────┐
         │  LLM prompt with guard       │  MODIFIED
         │  → narrative                 │
         └──────────────────────────────┘
                        ↓
         ┌──────────────────────────────┐
         │  validator.py                │  NEW
         │  → pass/fail + reject loop   │
         └──────────────────────────────┘
                        ↓
                  coaching output
```

### 5.4 Verification of the Fix (kNAMNYUF)

With DBCL, the BlunderFactSheet for ply 63 would contain:

```json
{
  "ply": 63,
  "move_played_san": "Rdg1",
  "fen_before": "r4r1k/.../1K1R4 w - - 1 32",
  "board_state": {
    "was_in_check": false,
    "checking_pieces": [],
    "capture_checking_piece_possible": false
  },
  "engine_lines": [
    {"rank": 1, "move_san": "Nxe6", "eval_cp": 920},
    {"rank": 2, "move_san": "Rg8+", "eval_cp": 901},
    {"rank": 38, "move_san": "Rdg1", "eval_cp": 45}
  ],
  "pattern_matches": [
    {"pattern_id": "R", "confidence": 0.7, "evidence": "eval_before=823>300, phase=endgame"},
    {"pattern_id": "C", "confidence": 0.8, "evidence": "consecutive errors"}
  ]
}
```

The prompt guard clause `if was_in_check=false, DO NOT say check` would prevent the fabricated check narrative. The validator would catch it if it slipped through. The output changes from:

> ❌ "Qf4+ dává šach. Místo ústupu králem (Ka1 nebo Kc1) jsi instinktivně zablokoval věží — Rdg1."

To:

> ✅ "Pozice před tahem: bílý má +823 cp, rozhodující výhodu. Místo drtivého Nxe6 (+920) nebo Rg8+ (+901) jsi zahrál pasivní Rdg1 — nejhorší z 38 legálních tahů. Pattern match: endgame relaxation (70%) + attention tunneling (80%)."

---

## 6. Principles of the Deterministic→Probabilistic Bridge

Extracted from all six reference systems. These are generalizable beyond chess.

### P1. Separation of Detection and Narration

**Statement:** The LLM must never perform detection. Detection must be computational/deterministic.

**Evidence:** Take Take Take (Stockfish detectors → LLM translator), VeNRA (UFL → code generator), Blunder Tutor (template-based). In all cases where LLM performs detection, hallucination rate increases.

**Violation cost in our system:** kNAMNYUF hallucination directly caused by LLM performing detection (is this position a check?) without proper tools.

### P2. Fact Sheet as Sole Source of Truth

**Statement:** All data passed to LLM must be pre-verified, structured, and typed. LLM may not introduce facts outside this sheet.

**Evidence:** Neural Fact Sheets (retrieve-then-write), Compiled AI (corpus as release), VeNRA (UFL with Double-Lock Grounding).

**Implementation:** BlunderFactSheet with mandatory fields. Output validator checks every claim back to a fact sheet entry.

### P3. Asymmetric Roles in Adversarial Verification

**Statement:** The agent that writes must not be the agent that verifies. Verification requires a separate, stricter pass.

**Evidence:** VeNRA Sentinel (3B SLM auditor separate from generator), Multi-Agent Systems research 2025-2026 (generator + critic separation), Blunder Tutor CI golden set checks.

**Implementation:** validator.py runs independently after LLM generation. No shared context with generation prompt.

### P4. Contextual Anchoring via Explicit Negation

**Statement:** It is not sufficient to say "only use these facts." Explicitly state what NOT to do based on data state.

**Evidence:** Compiled AI research shows prompt guardrails fail under long context. Explicit negative constraints ("if was_in_check=false, do not say check") outperform positive constraints ("only use facts").

**Implementation:** Prompt guard clauses with conditional structure (if→then→else). Each boolean field in fact sheet has a corresponding guard.

### P5. PV-First Explanation Structure

**Statement:** Explanation of a position should follow the engine's principal variation (PV) as primary structure, not free-form analysis.

**Evidence:** Blunder Tutor resolves explanation in three phases: (1) immediate mate → (2) PV analysis (captures, material delta, mate) → (3) static fallback. This prevents LLM from inventing variations.

**Implementation:** Each BlunderFactSheet includes top 3 engine lines with PV. LLM prompt instructs: "Engine lines ranked 1-N are the only valid 'what should have been played' answers."

### P6. Compile Time vs Runtime Separation

**Statement:** All expensive/deterministic computation happens at compile time. Runtime (LLM) operates only on pre-computed artifacts.

**Evidence:** Compiled AI (corpus release), VeNRA (UFL built before inference), Blunder Tutor (Stockfish analysis written to SQLite before any reading).

**Implementation:** DBCL runs as compile step before any LLM call. Fact sheets are cached and versioned.

---

## 7. Cross-Audit Protocol

### 7.1 How Another LLM Validates This Document

This document is structured for another LLM to read and produce a validation report answering:

1. **Completeness** — Are all architectural components specified? (Yes/No + missing items)
2. **Consistency** — Do the proposed components address the documented root cause? (Yes/No + gap analysis)
3. **Transfer validity** — Are the transfer learning mappings correct? Are the referenced sources accurately characterized?
4. **Testability** — Can the proposed architecture be verified? What test cases would validate it?
5. **Generalizability** — Does the DBCL pattern apply beyond chess? Where would it break?

### 7.2 Audit Inputs

Auditing LLM should have access to:
- This document (DBCL_cross_audit_artifact.md)
- The actual codebase at `_github/lichess-analyzer-mcp/src/`
- The coaching document (evening_coaching_2026-07-24.md)
- The cache files (game_cache/, pgn_cache/)

### 7.3 Audit Output Schema

```json
{
  "audit_timestamp": "ISO8601",
  "auditor_model": "string",
  "document_version": "1.0",
  "findings": [
    {
      "finding_id": "F-001",
      "severity": "critical | high | medium | low | info",
      "section": "string",
      "claim": "string",
      "assessment": "correct | incorrect | insufficient_evidence | unclear",
      "reasoning": "string",
      "recommendation": "string | null"
    }
  ],
  "overall_assessment": "pass | pass_with_concerns | fail",
  "critical_path": ["finding_id", "..."]
}
```

---

## 8. Generalizability

The DBCL pattern (deterministic detectors → typed fact sheets → LLM translator) applies to any domain where:

1. **Ground truth is computable** — There exists a deterministic algorithm that can produce correct answers for a subset of the problem. (Chess: Stockfish. Finance: arithmetic. Medicine: lab values + guidelines.)
2. **Explanation requires natural language** — The end user needs narrative, not just numbers. (Chess: coaching. Finance: audit reports. Medicine: clinical notes.)
3. **Hallucination cost is high** — The domain tolerates near-zero fabrication. (Chess: credibility. Finance: legal liability. Medicine: patient safety.)

### Boundary Conditions

| Condition | DBCL Applicable | Example |
|-----------|----------------|---------|
| Ground truth computable | ✅ | Chess, arithmetic, code generation |
| Ground truth probabilistic | ❌ | Stock market prediction, weather |
| Explanation needed | ✅ | Coaching, auditing, medical reporting |
| Only classification needed | ❌ | Spam filtering, image recognition |
| High hallucination cost | ✅ | Legal, medical, financial |
| Low hallucination cost | ❌ | Creative writing, entertainment |

---

## Appendix A: Source References

| Reference | Type | Relevance |
|-----------|------|-----------|
| Take Take Take (AI Engineer 2026, Anant Dole, Asbjorn Steinskog) | Conference talk | Same domain (chess coaching), same pattern (detection → LLM translator) |
| VeNRA (arXiv 2603.04663, 2026) | Academic paper | Universal Fact Ledger pattern, Double-Lock Grounding, Sentinel SLM |
| Compiled AI (dev.to, June 2026) | Engineering blog | Compile time / runtime separation for deterministic LLM systems |
| Blunder Tutor (mrlokans.work, 2026) | Engineering blog | Same domain, PV-first explanation, EnginePool, winning-chances sigmoid |
| Lichess lila (github.com/lichess-org/lila) | Open source | Advice.scala classification, fishnet architecture, eval cache |
| Neural Fact Sheets (TruthVouch Docs) | Documentation | Retrieve-then-write pattern, fact extraction → validation |
| Blunder Tutor Tactical Detection (mrlokans.work) | Engineering blog | python-chess pattern detection (fork, pin, skewer, discovered attack) |

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| DBCL | Deterministic Blunder Context Layer — proposed architecture layer |
| BlunderFactSheet | Structured, typed JSON object describing one blunder with full context |
| Fact Sheet | Output of deterministic extraction before LLM sees any data |
| PV | Principal Variation — engine's best-play sequence for both sides |
| A-Q1 | Pattern library (11 patterns A through R) for chess behavior detection |
| Transfer learning | Applying principles from one domain (e.g., finance) to another (chess) |
| Double-Lock Grounding | Two independent verification steps: character-offset + semantic schema |
| Compile time | Deterministic computation phase before any LLM inference |
| Runtime | LLM inference phase operating only on pre-compiled fact sheets |
| Winning-chances sigmoid | Mapping of centipawn eval → win probability (-1 to +1 scale) |

---

## Appendix C: Cross-Audit Results (Claude, 2026-07-24)

### C.1 Audit Verdict

| Metrika | Hodnota |
|---|---|
| Auditor | Claude (Anthropic) |
| Celkove hodnoceni | **PASS WITH CONCERNS** |
| Nalezu | 21 (F-001 az F-021) |
| Critical | 3 |
| High | 4 |

### C.2 Critical Path Items (must fix before DBCL v1)

| ID | Finding | Fix |
|---|---|---|
| **F-002/F-003** | FEN se v `game_analyzer.py` pocita a zahazuje; `board.is_check()` se nevola ani jednou | 1 radek: pridat `fen` pole do `MoveAnalysis` + predat ho v konstruktoru |
| **F-007** | Pattern J testuje `"+" in move_san` (tah dava sach) misto `board.is_check()` (pozice byla v sachu) — **aktivni bug v produkci** | Nahradit `"+" in move_san` → `board.is_check()` + overit blok neni capture |
| **F-008** | Dve mista sestaveni promptu (mono + incremental); DBCL pokryva jen `build_coaching_prompt` | Aplikovat guard-clause i na `_build_game_prompt`; explicitni kontrakt mezi vrstvami |
| **F-013** | Validator (§5.2.5) nema mapovani claim-typ → JSON path → operator; neumi negacni tvrzeni | Doplnit 5 kategorii s operatory: existence, rovnost, tolerance, negace, legalita |

### C.3 Key Implementation Corrections

| DBCL navrh | Audit korekce |
|---|---|
| `context_extractor.py` jako samostatny replay PGN | **Sloucit do `_run_analyze_pgn()`** — board uz existuje v cyklu |
| `engine_lines` ranking nova logika | **Volat `engine_client.analyze_position(fen, multipv=3)`** — uz existuje |
| Validator jako `validator.py` | **Pojmenovat `narrative_validator.py`** — konflikt s existujicim `validator.py` |
| Pouze mono prompt builder | **+ incremental `_build_game_prompt`** — dve vetve |

### C.4 Revised BlunderFactSheet v1.1 Schema (delta oproti §5.2.3)

Pridana pole (viz F-010, F-007):

```json
{
  "$schema": "DBCL v1.1",
  "win_prob_before": "float | null",
  "win_prob_after": "float | null",
  "win_prob_delta": "float | null",
  "detector_version": "string"
}
```

Validacni kategorie rozsireny o:
- `piece-on-square` → existence proti `fen_before` (figura + pole)
- `check` → rovnost proti `board_state.was_in_check`
- `capture` → existence v `legal_moves.captures` nebo `engine_lines[].move_san`
- `eval-cislo` → tolerance ±20cp proti `eval_before`/`eval_after`/`engine_lines[].eval_cp`
- **legalita/negace (NOVE)** → negace proti sjednocene mnozine `legal_moves.*`

### C.5 Revidovana implementacni priorita

```
P0: Opravit pattern J semantiku (§6 P1 pty)     ← audit F-007
P0: Propagovat fen_before do MoveAnalysis        ← audit F-002
P1: Napojit existujici analyze_position(multipv=3) ← audit F-005
P1: Inject BlunderFactSheet do obou prompt builderu ← audit F-008
P2: Doplnit win_prob + detector_version do schematu ← audit F-010
P2: Rozsirit validator spec na 5 kategorii s operatory  ← audit F-013
P3: Cross-validace vsech 11 detektoru           ← audit F-007 extrapolace
```

---

*End of DBCL Cross-Audit Artifact v1.0 + v1.1 audit appendix*
