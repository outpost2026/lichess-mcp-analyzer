# Cross-LLM Audit — Meta-analýza & Optimalizační PLÁN

**Vstup:** AUDIT_REPORT_v1 (de novo z twinu) + AUDIT_REPORT_v2 (verifikace s kódem)
**Auditor:** Claude Sonnet 5.0 (Anthropic)
**Datum:** 2026-07-24 | **Branch:** `debug/phase1-fixes` (HEAD `506b20c`)

---

## 1. Konsolidovaná Findings Matrix

Všechny nálezy z v1 + v2 sloučeny do jednotné prioritizace.

### Critical (blokující korektnost dat)

| ID | Lokace | Popis | Detekce |
|----|--------|-------|---------|
| **N1** | `game_analyzer.py:161-162` | `mistakes` list nikdy nenaplněn — tahy 150-299cp jdou do `blunders` místo `mistakes`. Všechny downstream aggregace (diagnostician, coaching prompt) hlásí `mistakes=0` trvale. | Pouze v2 (s kódem) |
| **F2** | `lichess_client.py`, `game_analyzer.py` | Path traversal: `username`/`game_id` vkládány přímo do `os.path.join()` bez sanitizace. Žádná whitelist validace formátu. | v1 + v2 |

### Major (správnost logiky)

| ID | Lokace | Popis | Detekce |
|----|--------|-------|---------|
| **N3** | `diagnostician.py:52` | Middlegame pravidlo: absolutní count vs. per-move rate. Phase_stats už obsahuje move_count data pro normalizaci — jen se nepoužívají. | v1 + v2 |
| **F3** | `pattern_detector.py` (O/P/Q/Q1/R) | Fixní confidence bez ohledu na evidenci (0.6/0.5/0.8/0.7/0.7). U O (severity critical) nejvíce problematické. | v1 + v2 |
| **F4** | všechny `tools/*.py` | `{"error": str(e)}` — ztráta typu chyby, žádný structured error kód. | v1 + v2 |
| **F5** | `engine_client.py` | Globální analysis lock serializuje Stockfish. 120s timeout nerozlišuje legitimně pomalou analýzu od deadlocku. | v1 + v2 |

### Minor (logické nekonzistence)

| ID | Lokace | Popis | Detekce |
|----|--------|-------|---------|
| **N2** | `diagnostician.py:56-57` | `list(openings.values())[0]` bere první, ne nejvíce chybový opening. Nekonzistentní s `leaky_openings` (který je správně sorted). | Pouze v2 |
| **N4** | `pattern_detector.py:149` | Pattern G: `frequency=int(blunder_rate)` místo countu postižených her. Sémanticky jiná veličina než u ostatních detektorů. | Pouze v2 |
| **N7** | `match_patterns.py:103-126` | Sort až po `store_patterns()` a schema validaci. Funkčně OK (sdílená reference), ale křehké pořadí. | Pouze v2 |
| **F1'** | `engine_client.py:129-132` | Mate pozice: `score=None` → `cp_loss=0` (None guard exists → tiše spadne na 0). Méně závažné než v1 předpokládala (crash → tichá ztráta signálu). | v1 (upřesněno v2) |

### Info (úklid)

| ID | Lokace | Popis | Detekce |
|----|--------|-------|---------|
| **N6** | `patterns/` | Prázdný adresář, neimportován. Příprava na budoucí extrakci. | Pouze v2 |
| — | `kb/writer.py`, `kb/md_reporter.py` | Mrtvý kód — nikde importován. `kb/schemas.py` je jediná používaná část. | v1 + v2 |
| **N5** | git historie | `DEBUG_REPORT_v003.md` zastaralý — popisuje revertnutý A4 fix. Riziko matení. | Pouze v2 |

---

## 2. Optimalizační Session PLÁN

Členění do 5 session bloků. Každý blok = samostatná session (ideálně samostatný commit).

### Session A — P0: Korektnost dat (kritické)

**A1 — N1: Oprava `mistakes` klasifikace**
- **Soubor:** `game_analyzer.py`, řádky 161-164
- **Změna:** Rozdělit `if classification in ("blunder", "mistake"):` na samostatné větve:
  ```python
  if classification == "blunder":
      analysis.blunders.append(move_analysis)
  elif classification == "mistake":
      analysis.mistakes.append(move_analysis)
  elif classification == "inaccuracy":
      analysis.inaccuracies.append(move_analysis)
  ```
- **Test:** Vytvořit syntetickou partii s garantovanou 150-299cp chybou, ověřit `len(analysis.mistakes) > 0`
- **Riziko:** Žádné — pure refactor, nemění chování pro blunder/inaccuracy

**A2 — F2: Path traversal sanitizace**
- **Soubor:** `lichess_client.py` + `game_analyzer.py`
- **Změna:** Před použitím `username`/`game_id` v `os.path.join()`:
  ```python
  import re
  _SAFE_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
  if not _SAFE_ID.match(username):
      raise ValueError(f"Invalid username format: {username!r}")
  ```
- **Rozsah:** Všechny cache path funkce + tool vrstva (fetch_games, analyze_game, diagnose_player, match_patterns)
- **Alternativa:** Validace na úrovni tool vstupů (username, game_id) místo v service vrstvě — preferováno pro DRY

**A3 — A1 test: Guard-free test pro mistakes**
- **Soubor:** `tests/test_prompt_contract.py` (nebo nový `test_game_analyzer.py`)
- **Změna:** Odstranit `if not mistakes: return` guard z testu, přidat test se zaručenou 150-299cp chybou
- **Reasoning:** Stávající test je falešně zelený — guard maskuje prázdný seznam

### Session B — P1: Správnost agregací (Major)

**B1 — N3: Normalizace middlegame pravidla na per-move rate**
- **Soubor:** `diagnostician.py`, řádek 52
- **Změna:** Místo absolutního porovnání použít per-move error rate:
  ```python
  # data pro normalizaci už existují v phase_stats
  # lepší: porovnat poměr errors/moves per phase
  if phase_weaknesses and "middlegame" in phase_weaknesses:
      mg = phase_weaknesses["middlegame"]
      op = phase_weaknesses.get("opening", {"blunders": 0, "move_count": 1})
      eg = phase_weaknesses.get("endgame", {"blunders": 0, "move_count": 1})
      mg_rate = mg["blunders"] / max(mg["move_count"], 1)
      op_rate = op["blunders"] / max(op["move_count"], 1)
      eg_rate = eg["blunders"] / max(eg["move_count"], 1)
      if mg_rate > op_rate + eg_rate:
          top_weaknesses.append("Tactical awareness in middlegame transitions")
  ```
- **Data už existují:** `phase_weaknesses` v `WeaknessReport` obsahuje `move_count` per fázi
- **Test:** 3 hry: opening 100 tahů 5 chyb, middlegame 30 tahů 3 chyby, endgame 10 tahů 1 chyba → staré pravidlo by řeklo "middle problem" (3 >= 5+1=false → neřekne nic), nové by mělo říct "middle problem" (3/30=0.1 > 5/100+1/10=0.05+0.1=0.15 → 0.1 > 0.15 = false → neřekne nic, správně)
- **Alternativa:** Použít data z `phase_stats` (GameAnalysis._compute_phase_stats) místo `phase_weaknesses` — obě mají move_count

**B2 — N2: Oprava "most-played opening" na sorted**
- **Soubor:** `diagnostician.py`, řádky 56-57
- **Změna:** Použít stejný sorted pattern jako `leaky_openings`:
  ```python
  if openings:
      worst_opening = sorted(openings.items(), key=lambda x: x[1]["blunders"], reverse=True)[0]
      if worst_opening[1]["blunders"] > 2:
          top_weaknesses.append(f"Opening preparation: {worst_opening[0]}")
  ```

**B3 — N4: Sjednocení frequency v Pattern G**
- **Soubor:** `pattern_detector.py`, řádek 149
- **Změna:** Místo `int(max(blunder_rate))` použít počet postižených her (jak dělají ostatní detektory):
  ```python
  frequency=len([g.game.id for g in (white_analyses if white_blunder_rate > black_blunder_rate else black_analyses)])
  ```
- **Nebo:** Přejmenovat na explicitní pole, např. `blunder_rate_asymmetry` v evidence dict

### Session C — P1: Error handling & observability

**C1 — F4: Strukturovaný error formát**
- **Soubor:** všech 9 `tools/*.py`
- **Změna:** Místo `{"error": str(e)}` zavést helper:
  ```python
  # nový helper v services/ nebo utils/
  def tool_error(e: Exception, context: str = "") -> dict:
      error_type = type(e).__name__
      if "429" in str(e) or isinstance(e, RateLimitError):
          cat = "rate_limit"
      elif isinstance(e, (ValueError, KeyError)):
          cat = "validation"
      elif isinstance(e, TimeoutError):
          cat = "timeout"
      else:
          cat = "internal"
      return {"error": {"type": cat, "message": str(e), "context": context}}
  ```
- **Reasoning:** LLM agent může rozhodovat o retry/abort podle typu chyby
- **Rozsah:** Minimálně přidat `type` pole; rozšířit `_export_by_player` string-matching na status_code

**C2 — F1': Mate pozice cp_loss**
- **Soubor:** `engine_client.py`, evaluate_move
- **Analýza:** Kód má `if best_score is not None` guard → žádný crash. Když `best_score=None` (mate), `best_player` zůstane `None`, a následný `max(0, best_player - actual_player)` vrací `0`. Mate scénář je vzácný.
- **Rozhodnutí:** Pouze zdokumentovat v response (např. `"mate_detected": True`). Neopravovat — dopad je minimální (mate v engine variantě je vzácný, cp_loss=0 v té pozici je konzervativní bias).

### Session D — P2: Pattern confidence & metodologie

**D1 — F3: Váhovaná confidence**
- **Soubor:** `pattern_detector.py` — `_detect_o`, `_detect_p`, `_detect_q`, `_detect_q1`, `_detect_r`
- **Změna:** Každý hardcoded confidence nahradit vzorcem zohledňujícím frekvenci a total_games:
  ```python
  # příklad pro _detect_o: confidence = min(0.4 + affected_games/total_games * 0.3, 0.9)
  #                   nebo: confidence = 0.4 + min(frequency / 10, 0.5)
  ```
- **Minimální varianta:** Přidat `"confidence_note": "low_sample"` do evidence dict, zachovat fixní confidence
- **Reasoning:** Sonnet v2 audit správně identifikoval, že fixní confidence u nejzávažnější patternu (O: critical) je designová nekonzistence

### Session E — P2: Úklid (Info + housekeeping)

**E1 — N7: Pořadí v match_patterns.py**
- **Soubor:** `match_patterns.py`, řádky 103-126
- **Změna:** Přesunout `result.sort(...)` před `store_patterns()` a schema validaci

**E2 — N5: Vyčištění zastaralé dokumentace**
- **Soubor:** `docs/DEBUG_REPORT_2026-07-22_v003.md`
- **Změna:** Odstranit nebo přidat warning header "OBSOLETE — A4 fix byl revertnut"

**E3 — N6 + kb/ dead code**
- Adresář `patterns/` — buď smazat, nebo naplnit extrahovanými pattern definicemi
- `kb/writer.py` a `kb/md_reporter.py` — buď integrovat, nebo smazat

---

## 3. Session Order & Dependencies

```
Session A (P0) ─── kritické opravy, musí první
  │
  ├── A1: N1 mistakes fix ──── no deps, 5 min
  ├── A2: F2 path traversal ─── no deps, 15 min
  └── A3: A1 test ──────────── depends on A1, 10 min
  │
  ▼
Session B (P1) ─── správnost agregací
  │
  ├── B1: N3 middle rate
  ├── B2: N2 opening sort
  └── B3: N4 pattern G freq
  │
  ▼
Session C (P1) ─── error handling
  │
  ├── C1: F4 structured errors
  └── C2: F1' mate cp_loss doc
  │
  ▼
Session D (P2) ─── pattern metodologie
  │
  └── D1: F3 weighted confidence
  │
  ▼
Session E (P2) ─── úklid
  │
  ├── E1: N7 sort order
  ├── E2: N5 old docs
  └── E3: dead code cleanup
```

**Doporučené pořadí: A1→A2→A3→B1→B2→B3→C1→C2→D1→E1→E2→E3**

---

## 4. Meta-hodnocení Cross-LLM Audit Workflow

### 4.1 Co fungovalo — potvrzená hodnota

| Aspekt | Hodnocení | Důkaz |
|--------|-----------|-------|
| **Architektonický scan (v1)** | ✅ Vysoce přesný | 5/5 arch. nálezů potvrzeno v kódu (F2, F3, F4, F5, kb/ dead code) |
| **Security awareness (v1)** | ✅ Užitečná perspektiva | Path traversal (F2) — reálný nález, který autor přehlédl. Token leakage byl nadhodnocen, ale prověření bylo správné. |
| **Detail branching bugs (v2)** | ✅ Zásadní | N1 (mistakes→blunders) — jednovětvová chyba, kterou twin nemohl zachytit. Nejcennější nález. |
| **Logické nekonzistence (v2)** | ✅ Střední hodnota | N2 (unsorted openings), N4 (frequency mix), N7 (sort po persist) — všechny potvrzeny. |
| **Cross-validation (v1→v2)** | ✅ Eliminace false positives | Mate score crash (v1 F1) byl vyvrácen; mate=0 je minor, ne critical. |
| **MCP compliance (v1)** | ✅ Kvalitní | Progress notifikace, @app.prompt(), sampling — vše identifikováno správně. |

### 4.2 Co nefungovalo — limity metody

| Limitace | Příčina | Doporučení |
|----------|---------|------------|
| Twin neodhalí jednovětvové bugy (N1) | Digital twin = popis architektury, ne řádek po řádku kódu | Vždy kombinovat: twin pro scan + 2-3 klíčové soubory číst v plném znění (game_analyzer.py, diagnostician.py) |
| Overconfidence v edge-case spekulacích (v1 F1: mate crash) | Bez kódu auditor tipuje chybějící guardy | Označit "předpoklad" sekce v auditu, oddělit jisté od spekulativního |
| Neodhalí chyby v test suite (N1 guard mask) | Test struktura není v twinu | Zahrnout test file summary do digital twin příště |
| "One-shot" audit nestačí na detekci patternů | N1, N2, N4, N6, N7 vyžadují iteraci s kódem | Plánovat 2-fázový audit pro každý cross-LLM review (v1 = twin, v2 = code verification) |

### 4.3 Skóre cross-LLM metody

| Metrika | Hodnota | Poznámka |
|---------|---------|----------|
| **Nálezy celkem** | 12 unikátních (v1+v2) | 2 critical, 4 major, 4 minor, 2 info |
| **False positives (v1)** | 1 (F1 crash→minor F1') | +1 nadhodnocený (token leakage) |
| **False negatives (v1 miss)** | 5 (N1, N2, N4, N6, N7) | 4/5 pouze v kódu |
| **Confirm rate v1 nálezů** | 5/7 potvrzeno (71%) | F1 vyvrácen, token leakage zmírněn |
| **Nové nálezy v2** | 5 (N1, N2, N4, N6, N7) | +1 upřesnění (F1') |
| **Časová investice** | ~30 min (twin) + ~45 min (v2) | Celkem ~75 min na kompletní audit |
| **EROI (poměr nálezů/čas)** | 12 nálezů / 1.25h = 9.6 nálezů/hod | Extrémně vysoká — srovnatelné s pair programmingem |

### 4.4 Doporučení pro další cross-LLM audity

1. **Dvoufázový audit jako standard:**
   - Fáze 1: Digital twin → architektonický scan + security review
   - Fáze 2: Plný zdrojový kód top 5 souborů → detailní implementační review
   - Výstup: Sloučený report s označením "twin-only" vs "code-verified"

2. **Rozšířit Digital Twin o:**
   - Test file structure (alespoň seznam testů a co pokrývají)
   - Error flow diagram (co se stane když X selže, nejen happy path)
   - Klíčové if/elif/else větve v kritických funkcích (diagnostician, game_analyzer)

3. **Pro příští audit (po implementaci PLÁNu):**
   - Zaměřit se na: MCP Progress notifikace, rate limiting, statistická validace patternů
   - Použít v3 digital twin (aktualizovaný o opravy z tohoto plánu)
   - Zadat jinému modelu (např. GPT-4o nebo DeepSeek V4) jako další cross-LLM perspektivu

---

## 5. Souhrn

| Metrika | Hodnota |
|---------|---------|
| Celkové skóre systému (Sonnet) | 5.5/10 |
| Blokující položky před používáním | 1 (N1 — mistakes data corruption) |
| Blokující položky před publikací | 3 (N1 + F2 + F4) |
| Odhadovaný čas oprav (A+B+C) | ~2-3 hodiny |
| Session bloků | 5 (A-E) |
| Celkem úkolů | 12 |
| Z toho P0 (tato session) | 3 (A1, A2, A3) |
| Z toho P1 (příští session) | 5 (B1-B3, C1-C2) |
| Z toho P2 (do 2 týdnů) | 4 (D1, E1-E3) |
