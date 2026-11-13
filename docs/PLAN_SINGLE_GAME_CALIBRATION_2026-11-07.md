# Plan kalibrace a optimalizace single-game pipeline

> **Stav 2026-11-13:** dokument je **implementovaný a jeho kontrakt je zmražený**.
> Detailed 1.2 a compact 2.1 jsou závazné a nemění se; nové požadavky jdou aditivně
> (viz `AUDIT_INTEGRATION_2026-11-13.md`, D7/D9). Poznámky ke dvěma známým
> nejasnostem tohoto dokumentu jsou v sekci „Poznámky k příkladům“ níže.
> Roadmapu single-game větve už neřídí tento plán, ale `AUDIT_INTEGRATION_2026-11-13.md` §6.

**Verze:** 1.0 (DRAFT) | **Datum:** 2026-11-07 | **Status:** implementováno, kontrakt 1.2 zmražen
**Rozsah:** `lichess_coaching_single_game` a služby, které přímo volá
**Baseline:** HEAD `9738250` (2026-10-09), měření n=3 ze dne 2026-11-07
**Mimo rozsah:** cross-game a batch pipeline, KB writer, tréninkové plány, změny `max_time_dual`

---

## Poznámky k příkladům v tomto dokumentu (2026-11-13)

Dvě místa v příkladech jsou historicky správná, ale dnešní čtenář je může vyložit špatně:

1. **`moves_total` v příkladu (§5) znamená počet rozhodnutí analyzovaného hráče**, ne počet půltahů partie. Pole dnes počítá `len(moves)`, a `moves` obsahuje jen tahy vybrané barvy. Aditivní rozdělení (`player_moves_total`, `game_plies_total`, `opponent_moves_total`) je Tier 2.2 v `AUDIT_INTEGRATION_2026-11-13.md`; do té doby se `moves_total` nesmí číst jako délka partie.
2. **`eval_before` / `eval_after` jsou z pohledu hráče, který táhl** (mover POV), v celé pipeline. `eval_after` není POV soupeře. Definitivní názvy `eval_before_mover_cp` / `eval_after_mover_cp` a White POV pro timeline řeší D9 a Tier 2.1.

---

## 0. Účel dokumentu

Repo má 128 commitů a 141 zelených testů, ale tři po sobě jdoucí produkční analýzy vykazují stejné
tři mezery: prázdné `patterns`, šablonu vydávanou za LLM a žádné `timings`. Cílem tohoto plánu není
přepsat pipeline. Cílem je **uzavřít produktový kontrakt** tak, aby každý výstup nesl důkaz o tom,
co bylo spočítáno, co nebylo a proč.

Pořadí priorit je záměrně jiné než v prvních dvou analýzách:

1. **Důvěryhodnost** — výstup nesmí lhát (P0).
2. **Vysvětlitelnost** — každá vlajkovaná chyba má důvod (P0).
3. **Rychlost** — až poté, co výstup není prázdný (P1).

Důvod: devět minut v analýze #1 nezpůsobil motor, ale rozhraní. Nástroj vrací český narativ, a tak
agent sáhl po osmi ručních voláních `analyze_position`. Zrychlení enginu bez opravy kontraktu jen
zrychlí prázdný report.

---

## 1. Změřený stav (baseline, n=3)

| | #1 `wC3fgDiQ` | #2 `mHgzFNl4` | #3 `KkAkq59s` |
|---|---|---|---|
| Cesta | obchvat pipeline | 1× single-game | 1× single-game |
| Barva / ply / tahů hráče | black / 5 / 2 | black / 68 / 34 | white / 63 / 31 |
| Cold (audit) | 92,4 s MCP (8 volání) | **21,735 s** | **37,843 s** |
| Warm (cache) | — | 1,609 s | 1,843 s |
| s / tah hráče (cold) | — | 0,64 | **1,22** |
| ACPL | — | 29,1 | 21,3 |
| `evaluation_errors` | 2 tiché `[]` | 0 | 0 |
| `patterns` | — | `[]` | `[]` |
| LLM | nevoláno | 404 / 402 / 402 → šablona | 404 / 402 / 402 → šablona |

**Co z toho plyne pro plán:**

- Cold cena není stabilní (0,64 vs 1,22 s/tah při stejném depth 14) → depth není časová záruka.
- Warm cena je konstantní 1,6–1,9 s → cache je nejrychlejší páka, ale jen pro opakování.
- Kvalita výstupu je konzistentně slabá napříč třemi hrami → není to náhoda ani konkrétní pozice.

**Známé, ale neopravené (`.ai_state.json`):** CR-B16 (tiché `cp_loss=0`), CR-B5 (timeout zabíjí
sdílený engine), REVIEW-F1 (0× asyncio v `src/`), CR-B113, BLIND-SPOT-3, mypy 42 chyb.
Tyto položky nejsou novým objevem; jsou to dluhy, které je třeba spálit, ne znovu analyzovat.

---

## 2. Cílový kontrakt

### 2.1 Principy

| # | Pravidlo | Vynucení |
|---|---|---|
| K1 | Žádná degradace nesmí být vydávána za plný výstup | `llm.status`, `report.source`, `status` |
| K2 | Žádná chyba nesmí být reprezentována nulou | `centipawn_loss: null` + `analyzed: false` |
| K3 | Každá response nese časy po etapách | `timings` (povinné) |
| K4 | Každá vlajkovaná chyba má vysvětlení nebo explicitní `explanation_source: "none"` | `flagged_moves[]` |
| K5 | Prázdný pattern list musí mít důvod | `patterns_meta.reason` |
| K6 | Hard deadline je závazný; překročení = `partial`, ne tichá nula | `timings.budget_used`, `errors[]` |
| K7 | Nová pole jsou aditivní; staré klíče zůstávají po dobu jednoho vydání | `schema_version` |

### 2.2 Response schema (v1.1)

Ukázka je vyplněná reálnými hodnotami z analýzy #3 (`KkAkq59s`) tam, kde jsou k dispozici.

```json
{
  "schema_version": "1.1",
  "game_id": "KkAkq59s",
  "username": "systeq",
  "color": "white",
  "mode": "fast",
  "depth": 14,
  "status": "degraded",
  "partial": false,

  "errors": [],
  "unanalyzed_plies": [],

  "timings": {
    "io_s": 0.4,
    "engine_s": 34.2,
    "llm_s": 0.1,
    "overhead_s": 3.1,
    "total_s": 37.8,
    "deadline_s": 60.0,
    "budget_used": 0.63,
    "engine_calls": 64,
    "engine_timeouts": 0
  },

  "engine": {
    "limit": "depth+nodes",
    "depth": 14,
    "nodes_cap": null,
    "hash_mb": 128,
    "threads": 4
  },

  "cache": { "hit": false, "layer": "none", "key": null },

  "analysis": {
    "acpl": 21.3,
    "accuracy": 96.8,
    "moves_analyzed": 31,
    "moves_total": 31,
    "evaluation_errors": 0,
    "phase_stats": {
      "opening":    { "acpl": 29.3, "move_count": 10, "flagged": 3 },
      "middlegame": { "acpl": 9.3,  "move_count": 15, "flagged": 1 },
      "endgame":    { "acpl": 35.6, "move_count": 7,  "flagged": 1 }
    }
  },

  "flagged_moves": [
    {
      "ply": 59,
      "san": "Rh4",
      "uci": "h5h4",
      "classification": "mistake",
      "cp_loss": 214,
      "eval_before": -0.04,
      "eval_after": -2.19,
      "win_prob_before": 0.494,
      "win_prob_after": 0.221,
      "phase": "endgame",
      "best_move_san": "Rhg1",
      "played_rank": 4,
      "engine_lines": [
        { "rank": 1, "san": "Rhg1", "eval_cp": -7, "pv": ["Rhg1", "..."] },
        { "rank": 2, "san": "c4",   "eval_cp": -147, "pv": ["c4", "..."] },
        { "rank": 3, "san": "Rf4",  "eval_cp": -160, "pv": ["Rf4", "..."] }
      ],
      "motif": null,
      "explanation": "Věž opouští g-file; po ...Rg5 se h5 stává terčem.",
      "explanation_source": "deterministic"
    }
  ],

  "patterns": [
    {
      "pattern_id": "C",
      "pattern_name": "Attention tunneling",
      "confidence": 0.62,
      "frequency": 1,
      "severity": "medium",
      "scope": "single_game",
      "evidence": [{ "ply": 59, "cp_loss": 214 }],
      "affected_games": ["KkAkq59s"]
    }
  ],
  "patterns_meta": {
    "scope": "single_game",
    "cross_game_suppressed": true,
    "reason": "Cross-game detectors require >=3 games (pattern_detector.py:39).",
    "detector_version": "..."
  },

  "llm": {
    "status": "degraded",
    "provider": "none",
    "degraded": true,
    "reason": "all_providers_failed",
    "attempts": [
      { "provider": "NVIDIA",   "http_status": 404, "retryable": false },
      { "provider": "Cerebras", "http_status": 402, "retryable": false },
      { "provider": "DeepSeek", "http_status": 402, "retryable": false }
    ],
    "timeout_s": 10.0,
    "tokens": { "input": 0, "output": 0 }
  },

  "report": {
    "source": "deterministic",
    "format": "markdown",
    "text": "# Coaching Report ...",
    "chars": 3883
  },

  "cascade_log": [],
  "flags": {
    "cloud_eval": "disabled",
    "bfs_scope": "blunder+mistake+inaccuracy"
  }
}
```

**Semantika `status`:**

| Hodnota | Podmínka |
|---|---|
| `ok` | všechny etapy v rozpočtu, `errors=[]`, LLM reálný |
| `degraded` | výstup použitelný, ale některá komponenta substituována (LLM → deterministický souhrn) |
| `partial` | část tahů neanalyzována v deadline; `unanalyzed_plies` neprázdné |
| `error` | žádná použitelná analýza; `report.source="none"` |

`degraded` a `partial` se nevylučují: response může být obojí, `status` je pak `partial`
(horší stav vyhrává), ale obě skutečnosti zůstávají ve `llm.status` a `unanalyzed_plies`.

### 2.3 SLO

SLO je rozdělené na fázi P0 (bez změny počtu analýz) a P1 (po optimalizaci enginu).
Fáze se nesmí zaměňovat: P0 neslibuje rychlost, kterou současný engine neumí.

| Režim | Fáze | p50 | p95 | Hard deadline |
|---|---:|---:|---:|---:|
| `fast` (≤80 ply, d12–14) | P0 | 35 s | 50 s | **60 s** |
| `fast` | P1 | 12 s | 20 s | **30 s** |
| `deep` (≤80 ply, d16–18 + LLM) | P1 | 50 s | 80 s | **120 s** |
| warm (cache hit) | P0 | 2 s | 5 s | **8 s** |
| `analyze_position` (1 FEN) | P0 | 1 s | 3 s | **5 s** |

`analyze_position` dnes default depth 18 = 7,7 s (měřeno) → nesplňuje ani p95.
V P0 se default snižuje na 14 a zavádí `nodes` strop (viz 3.2).

### 2.4 Zpětná kompatibilita

- `report` (string) zůstává po jedno vydání jako alias `report.text`; nový kód čte objekt.
- `patterns` zůstává pole; mění se pouze obsah (single-game scope) a přibývá `patterns_meta`.
- `cascade_log` zůstává.
- Nové klíče: `schema_version`, `status`, `partial`, `errors`, `unanalyzed_plies`, `timings`,
  `engine`, `cache`, `flagged_moves`, `llm`, `report.{source,chars}`, `flags`.
- Konzumenti k aktualizaci: `report_persister.py`, `tools/persist_report.py`, testy
  `test_coaching_*`, případně KB writer (jen čtení `report`).

---

## 3. Etapové deadliney

### 3.1 Model rozpočtu

Rozpočet se odečítá z **jednoho monotónního deadline na hru**, ne z pevného limitu na jeden
engine call. Tím zmizí třída chyb „15 s × N".

```
Budget(total_s):
    deadline = monotonic() + total_s
    remaining() = max(0, deadline - monotonic())

stage_cap = min(stage_budget, remaining() - reserve)
```

Alokace (konfigurovatelné v `config/depth.py`, nová sekce `budgets`):

| Režim | total | engine | llm | io | reserve |
|---|---:|---:|---:|---:|---:|
| `fast` | 60 s | 40 s | 10 s | 5 s | 5 s |
| `deep` | 120 s | 85 s | 25 s | 5 s | 5 s |
| `position` | 5 s | 4 s | 0 s | 1 s | 0 s |

`reserve` je záměrně oddělený: pokrývá serializaci, zápis cache a režii Pythonu. Bez něj se
response začne vyrábět po deadline a SLO padne na posledních 200 ms.

### 3.2 Engine limit: depth + nodes

Depth zůstává kvalitativní parametr. Časovou záruku dává `nodes` strop:

```python
Limit(depth=depth, nodes=nodes_cap)
```

Engine se zastaví podle toho, co nastane dřív. `nodes_cap` se **nekalibruje odhadem** — v P0.1
se změří na třech golden hrách a uloží do configu jako tabulka `NODE_CAPS[depth]`. Výchozí
hodnota do té doby `None` (žádný strop), aby se nezměnilo chování před kalibrací.

**Proč ne jen snížit depth:** měření ukázalo, že d12 a d14 jsou si cenou blízko
(0,84 vs 0,96 s/tah u `evaluate_move`). Snížení depth je tedy slabá páka. Skutečná páka je
počet analýz na pozici (P1.1), ne hloubka.

### 3.3 Algoritmus běhu

```
analyze_game(pgn, deadline):
    budget = Budget(deadline)
    pgn = fetch_pgn(timeout=min(5, budget.remaining()))

    moves = list_of_player_moves(pgn)
    per_move = budget.remaining(engine) / max(1, len(moves))

    for i, move in enumerate(moves):
        if budget.remaining(engine) < MIN_USEFUL (0.15 s):
            mark remaining moves unanalyzed   # cp_loss=null, analyzed=false
            break
        call_cap = min(per_move * 0.9, budget.remaining(engine))
        result = engine.evaluate(position_i, cap=call_cap)
        if result.error:
            record errors[]; mark unanalyzed; continue   # NIKDY cp_loss=0
        ...
    if unanalyzed: status = partial
```

Pravidla, která se nesmí obejít:

1. `call_cap` se počítá z **zbývajícího** rozpočtu, ne z konstanty 15 s.
2. Timeout engine callu znamená `analyzed=false`, nikoli `cp_loss=0`.
3. `total_acpl` se počítá pouze z `analyzed=true` tahů; jinak je metrika optimistická.
4. `_run_engine_call` dostane `timeout_s` parametr; globální konstanta zůstává jen jako
   fallback pro volání bez budgetu (batch, testy).
5. Při `partial` se do `errors[]` zapíše každý neanalyzovaný tah nebo souhrnný kód
   `BUDGET_EXHAUSTED` s počtem.

### 3.4 Změny v kódu

| Soubor | Změna |
|---|---|
| `config/depth.py` | nová sekce `budgets`, `NODE_CAPS` (kalibrace v P0.1) |
| `services/budget.py` (nový) | `Budget`, `StageBudget`, `remaining()`, `checkpoint()` |
| `services/engine_client.py` | `evaluate_move(..., timeout_s=None)`, `analyze_position(..., timeout_s=None)`; návrat `{"error": ...}` bez nuly |
| `services/game_analyzer.py` | budget-aware smyčka, `analyzed` flag, `unanalyzed_plies`, stage timings |
| `models/game.py` | `MoveAnalysis.centipawn_loss: float \| None`, `MoveAnalysis.analyzed: bool` |
| `tools/coaching_single_game.py` | `mode` parametr, sestavení `timings`, `status`, `errors` |

### 3.5 Feynman: proč rozpočet na hru a ne na tah

Představ si taxík, který má na celou jízdu 60 sekund. Když dáš řidiči 15 sekund na každou
zastávku a zastávek je deset, může jet 150 sekund — a ty se to dozvíš až na konci. Přesně to
dnes děláme: engine má 15 s na jeden call, ale jeden call obsahuje tři analýzy, a herních tahů
je třicet. Rozpočet na hru znamená, že se ptáme „kolik mi zbývá?", ne „kolik mi patří na tuhle
zastávku". Když peníze dojdou, taxík zastaví a **řekne, kam dojel** — místo aby jel na dluh a
pak tvrdil, že cesta stála nula.

---

## 4. Golden regression

### 4.1 Fixtury

Tři hry, které už máme změřené. PGN se uloží do `tests/fixtures/pgn/` (veřejná data, žádná síť
v testu). Očekávané hodnoty do `tests/fixtures/golden/`.

| ID | Barva | Depth | Cold baseline | ACPL | Vlajkové tahy |
|---|---|---|---:|---:|---|
| `mHgzFNl4` | black | 14 | 21,735 s | 29,1 | 1× mistake `18...Bd6` 195 cp, 7× inaccuracy |
| `KkAkq59s` | white | 14 | 37,843 s | 21,3 | 1× mistake `30.Rh4` 214 cp, 4× inaccuracy |
| `wC3fgDiQ` | black | 12 | (error path) | — | 2× tichý `[]` v původním běhu → negativní fixture |

`wC3fgDiQ` slouží primárně jako **negativní test**: injektovaný engine timeout musí vést k
`status=partial`, `analyzed=false`, `cp_loss=null`, `errors[]` neprázdné. Nikdy k `[]` nebo k nule.

### 4.2 Aserce

| # | Aserce | Tolerance |
|---|---|---|
| A1 | `analysis.acpl` proti fixture | ±10 % (hash nondeterminismus) |
| A2 | počet flagged moves ≥ fixture − 1 | deterministické prahy |
| A3 | `evaluation_errors == 0` a `unanalyzed_plies == []` na čistém běhu | přesně |
| A4 | `timings.total_s <= deadline_s` | přesně |
| A5 | `timings` obsahuje všechny etapy a `engine_calls > 0` | přesně |
| A6 | `llm.status != "ok"` ⇒ `report.source != "llm"` | přesně |
| A7 | `patterns` neprázdné, pokud existuje ≥1 flagged move s motivem; jinak `patterns_meta.reason` neprázdný | přesně |
| A8 | každý flagged move má `explanation` nebo `explanation_source="none"` | přesně |
| A9 | response validuje proti JSON schématu `schemas/single_game_v1.1.json` | přesně |
| A10 | warm běh (`cache.hit=true`) ≤ 5 s | přesně |

A1–A10 tvoří **ship gate**. Bez zeleného golden runu se P0 nepovažuje za hotové.

### 4.3 Negativní testy

| Test | Injektáž | Očekávání |
|---|---|---|
| N1 | engine call vyhodí timeout | `partial`, `errors[]`, žádná nula |
| N2 | všechny LLM providery 402 | `llm.status="degraded"`, `report.source="deterministic"`, text neobsahuje „LLM" |
| N3 | neplatný PGN | `status="error"`, `report.source="none"`, HTTP-level úspěch (MCP tool nesmí spadnout) |
| N4 | deadline 2 s na 60 ply | `partial`, `unanalyzed_plies` neprázdné, návrat ≤ 3 s |
| N5 | cache obsahuje starý formát | migrace nebo miss, nikdy výjimka |

### 4.4 Feynman: proč golden regression

V dílně máš tři kalibrační závaží. Když seřídíš stroj, zvážíš je znovu a porovnáš. Bez nich
každá úprava vypadá jako zlepšení, protože nemáš s čím srovnávat — a přesně to se stalo:
tři různé hry, tři různé subjektivní dojmy, žádná společná míra. Golden regression je stejná
míra před i po. Není to test, že kód „něco dělá". Je to test, že **dělá totéž nebo líp**.

---

## 5. Pořadí prací

### 5.1 P0 — důvěryhodnost (ship blocker)

#### P0.0 — Ověřit, že server běží HEAD

**Co:** porovnat verzi kódu v běžícím MCP procesu s `9738250`; restartovat server; znovu změřit
jeden warm běh.

**Proč:** `.ai_state.json` uvádí jako blocker „MCP server session bezi se starym kodem — restart
procesu potrebny pro nove fixy". Pokud to platí, měříme minulost a všechny závěry jsou posunuté.

**Feynman:** Než začneš měřit, ujisti se, že měříš dnešní auto a ne včerejší. Jinak opravíš
závadu, která už v garáži není, a ta skutečná zůstane.

**Acceptance:** `tools/version` nebo log při startu obsahuje commit SHA; warm běh odpovídá
aktuálnímu kódu.

---

#### P0.1 — Kontrakt, `timings`, `status`, `errors`

**Co:** zavést JSON schéma `schemas/single_game_v1.1.json`; instrumentovat etapy
(`io`, `engine`, `llm`, `overhead`) přes `time.perf_counter()`; do response přidat `status`,
`partial`, `errors`, `unanalyzed_plies`, `engine`, `cache`, `flags`.

**Kde:** `tools/coaching_single_game.py`, `services/coaching_base.py`, `services/audit.py`
(stage-level pole v JSONL), nový `services/response.py` (sestavení a validace).

**Proč:** dnes jediná observability je `audit.jsonl` s `duration_s` na úrovni toolu. Neumíme
říct, kolik z 37,8 s byl engine, kolik LLM a kolik síť. Bez toho nelze optimalizovat — jen hádat.

**Feynman:** Je to palubní deska. Auto jede, ale nevíš, jestli je pomalé kvůli motoru, nebo
protože jsi jel oklikou. Přidáním tachometru a teploměru zjistíš, že „pomalé" je ve skutečnosti
„motor v pořádku, ale zastavovali jsme na každé vesnici".

**Riziko:** změna návratového typu rozbije `report_persister` a testy. **Mitigace:** aditivní
klíče + alias `report`, aktualizace konzumentů ve stejném commitu.

**Acceptance:** A5, A9; audit obsahuje `stage_durations`.

---

#### P0.2 — Deadline orchestrátor a konec tichých nul

**Co:** `services/budget.py`; `evaluate_move`/`analyze_position` přijímají `timeout_s`;
`MoveAnalysis.centipawn_loss` je `float | None` + `analyzed: bool`; timeout → `errors[]`,
`unanalyzed_plies`, `status=partial`; ACPL jen z analyzovaných tahů.

**Kde:** `services/engine_client.py:122–157, 195–198, 262–270`,
`services/game_analyzer.py:415–425, 461–463`, `models/game.py:64–89`.

**Proč:** dva defekty mají stejnou příčinu — chyba je reprezentována nulou. `analyze_position`
vrací `[]` při timeoutu (`engine_client.py:196–198`), `evaluate_move` vrací `cp_loss=0`
(`:263–270`), `game_analyzer` inkrementuje `evaluation_errors` a pokračuje (`:425`). Čítač se
nikde nevrací, takže konzument vidí „0 chyb, ACPL 0".

**Feynman:** Když se pokazí váha, nesmíš zapsat „0 kg". Zapiš „neměřeno". Nula je platná
hmotnost — a v ACPL znamená „perfektní tah". Právě proto dvě z osmi pozic v analýze #1 vypadaly
jako bezchybné: motor je nestihl, ale výsledek tvrdil nulu.

**Riziko:** `None` prosakuje do `_compute_phase_stats`, `_compute_accuracy`, JSON výstupů a testů.
**Mitigace:** centrální helper `mean_over_analyzed()`; migrační test N5; dočasný `analyzed` flag
umožní starým konzumentům číst `centipawn_loss=0` bez změny chování, pokud explicitně nezvolí nové.

**Acceptance:** N1, N4; A3, A4.

---

#### P0.3 — Pravdivý LLM status

**Co:**
1. Přejmenovat `IDE (Muse Spark)` na `deterministic` a **nepočítat** ho do
   `is_llm_available()` / `get_llm_status().available`.
2. `safe_llm_call` vrací čtvrtou hodnotu `source` (`provider name` | `deterministic` |
   `data_dump`); `cascade_exhausted=True` i při deterministické náhradě.
3. `llm.status` v response: `ok` | `degraded` | `disabled`; `reason`, `attempts[]`.
4. Provider health: discovery přes `GET {base_url}/models` při startu (GT-051 / P36),
   negativní cache na 401/402/404 s TTL 10 min; mrtvý provider se přeskočí bez HTTP callu.
5. Report text nesmí obsahovat „LLM", pokud `source="deterministic"`.

**Kde:** `services/ide_fallback.py:28–127`, `services/coaching_base.py:204–271`,
`services/llm_client.py:426–549`, `services/llm_client.py:75–116`.

**Proč:** dnes je šablona validní výstup (`_is_valid_coaching_content`), takže kaskáda ji přijme
a vrátí `cascade_exhausted=False`. Všechny tři providery jsou 404/402, ale response tvrdí
`ok=true`. To není jen kosmetika: **čtenář nemá jak poznat, že text není od LLM.**

**Feynman:** Když nepřijde překladatel, nesmíš vydat strojový překlad s jeho podpisem. Text
může být užitečný, ale podpis musí odpovídat skutečnosti. A když víš, že obchod má zavřeno,
nepokoušíš kliku pokaždé, když jdeš kolem — zapamatuješ si to na deset minut.

**Riziko:** bez platných klíčů nelze ověřit `status="ok"`. **Mitigace:** P0.3 je plně
testovatelná bez klíčů (N2); získání kreditů je samostatný ops úkol, který blokuje jen „plný"
stav, ne pravdivost.

**Acceptance:** N2; A6; `get_llm_status()` už nikdy nevrátí IDE jako providera.

---

#### P0.4 — Single-game pattern surface

**Co:** nová funkce `detect_single_game(analysis: GameAnalysis) -> list[dict]`, která používá
**jen** signály dostupné z jedné hry: `is_tactical_motif`, `motif_type`, `was_in_check`,
`classification`, `phase`, `cp_loss`, plus `_per_blunder_patterns()` z `game_analyzer.py`.
Cross-game detektory (A, B, …) se **nespouštějí**; `patterns_meta.cross_game_suppressed=true`
s důvodem.

**Kde:** `services/pattern_detector.py` (nová metoda), `tools/coaching_single_game.py:54`.

**Proč (důležité — mění původní plán z 2026-08-02):**
Původní dokument navrhoval `min_games_override`. To je **nebezpečné a nestačí**:

1. `collect_patterns_for_games([analysis])` dostává **dict** (`analysis.to_dict()`), ale detektory
   očekávají `GameAnalysis` (`a.game.opponent_name`). Dnes to nekryje nic jiného než gate
   `1 < 3`; po jeho vypnutí by první detektor spadl na `AttributeError`.
2. Většina detektorů jsou **skupinové statistiky** (A: anonym vs. jmenovaný, B: míra grabů
   napříč hrami). Na jedné hře nemají definovaný jmenovatel. I kdyby nespadly, vrátí nesmysl.
3. `min_occurrences=2` by výsledek stejně odfiltroval (`frequency` = počet her).

Správné řešení je tedy **druhý, poctivý výstup**, ne odemčení skupinového.

**Feynman:** Patterny A–S odpovídají na otázku „hraješ hůř proti anonymům než proti známým?".
Na jedné hře to změřit nelze — jako když chceš průměrnou výšku populace a máš jednoho člověka.
Ale jiné vzorce jsou vidět na jednom tahu: „vzal jsi pěšce a ztratil 200 cp", „ignoroval jsi
šach". Ty vytáhneme. Neodemkneme skupinovou statistiku; přidáme druhý, správně označený výstup.

**Riziko:** nová detekce může produkovat falešné patterny. **Mitigace:** žádná nová inference —
pouze recyklace již existujících deterministických signálů; každý pattern nese `evidence` s ply.

**Acceptance:** A7; u #2 a #3 je `patterns` neprázdné (minimálně C / motiv), u hry bez chyb
je `patterns_meta.reason` neprázdný.

---

#### P0.5 — Vysvětlení pro každý vlajkovaný tah

**Co:** rozšířit BFS scope z `classification in ("blunder","mistake") and cp_loss >= 150`
na **všechny** flagged moves (blunder/mistake/inaccuracy). Pro inaccuracy stačí lehká verze:
`best_move_san`, `played_rank`, top-3 `engine_lines`, `explanation_source`.

**Kde:** `services/game_analyzer.py:464–509`.

**Proč:** dnes má 7 z 8 chyb v #2 a 4 z 5 v #3 pouze číslo. Coaching hodnota je nulová:
„ztratil jsi 60 cp" není vysvětlení. Motivační příklad: #3 `30.Rh4` má BFS, protože je to
mistake; `24.h5` (57 cp) nemá nic, přestože je to tatáž otázka.

**Feynman:** Říct pacientovi „máš teplotu 38" a nic víc není diagnóza. U jedné chyby už
pipeline umí říct „tady byl lepší tah a tady je důvod". Rozšíříme to na všechny vlajkované
tahy. Je to levné, protože motor tu pozici už jednou viděl — jen se ho zeptáme na top-3.

**Riziko:** +1 až +10 volání `analyze_position` na hru. **Mitigace:** jen pro flagged moves
(typicky ≤10), s `multipv=3` a deadline; při nedostatku rozpočtu `explanation_source="none"`.

**Acceptance:** A8; počet `analyze_position` callů na hru ≤ 10.

---

#### P0.6 — Golden regression harness

**Co:** `scripts/run_golden_single_game.py` + `tests/test_golden_single_game.py` (marker `slow`,
bez sítě), fixtury dle §4, JSON schéma, CI job volitelný (manuální gate).

**Proč:** 141 testů zelených a přesto tři produkční běhy selhaly na kontrakt. Testy chrání
interní chování, ne slib.

**Feynman:** Viz §4.4 — kalibrační závaží.

**Acceptance:** 3/3 her zelených, N1–N5 zelených.

---

### 5.2 P1 — výkon (až po P0)

#### P1.1 — Jedna analýza na pozici

**Co:** nahradit 3 analýzy v `evaluate_move` schématem „1 analýza na pozici":

```
eval[i]      = skóre pozice před tahem i (perspektiva hráče na tahu)
best[i]      = první tah PV z eval[i]
eval_after[i] = -eval[i+1]        # pozice po tahu i = pozice před tahem i+1, obrácené znaménko
cp_loss[i]    = max(0, eval[i] - eval_after[i])
```

Celkem `N+1` analýz místo `3N` na hru. `best_move` zůstává z `eval[i]`; `played_rank` se
počítá jen pro flagged moves z `multipv=3` (P0.5).

**Proč:** `evaluate_move` dělá `eval_before`, `best_res` a `actual_res` (`engine_client.py:241–260`).
Třetí analýza je zbytečná: hodnocení pozice po tvém tahu je totéž jako hodnocení pozice před
souperovým tahem, jen s opačným znaménkem. To je standardní přístup (jeden eval na pozici).

**Feynman:** Měříš výšku na túře. Nepotřebuješ tři výškoměry na každý krok — stačí jeden na
každém bodě a rozdíl sousedů ti dá stoupání. Dnes měříme každý bod třikrát a stejně použijeme
jen rozdíl.

**Riziko:** ACPL se může mírně změnit (jiný search pro `after`). **Mitigace:** golden test A1
s tolerancí ±10 %; pokud delta > 10 %, použít 1 analýzu jen pro `inaccuracy` a 3 pro
`mistake/blunder` (hybrid).

**Očekávaný dopad:** cold #3 z 37,8 s na ~13 s; #2 z 21,7 s na ~8 s. Odhad P~0.7, ověří golden.

---

#### P1.2 — Position cache

**Co:** `data/position_cache.sqlite`, klíč `(fen, depth, nodes_cap, multipv)`, hodnota
`{score_cp, mate, pv, depth_reached, ts}`. Použít v `evaluate_move` i `analyze_position`.

**Proč:** warm game cache je 1,6 s, ale jakákoli nová hra nebo jiná hra se stejnou pozicí
počítá znovu. Zahájení se opakují; BFS volá stejnou pozici jako hlavní analýza.

**Feynman:** Když se na stejnou věc ptáš podruhé, odpověď už znáš. Dnes se ptáme znovu a
platíme plnou cenu.

**Acceptance:** druhá hra se stejným zahájením ≥30 % hit rate; warm ≤ 5 s.

---

#### P1.3 — Cloud eval: default off, negativní cache

**Co:** `use_cloud=False` default v `analyze_position`; `CHESS_API_CLOUD` už nezapíná per-call
volání bez možnosti vypnout; 404 se cachingem 1 h; timeout 1 s.

**Proč:** v logu 7× `cloud_eval failed: HTTP 404` za jednu session. Každé volání je zbytečný
round-trip a 10 s timeout.

**Feynman:** Posíláš dopis na adresu, která neexistuje, a děláš to znovu u každé další pozice.
Když si zapamatuješ „tam nikdo nebydlí", ušetříš cestu.

**Acceptance:** v logu 0 cloud 404 při default běhu.

---

#### P1.4 — Async offload a engine pool

**Co:** všechna blokující volání (`engine.analyse`, `httpx.post`, file I/O) přes
`asyncio.to_thread`; pool 2 engine instancí pro paralelní hry; `_analysis_lock` jen kolem
jednoho engine, ne globálně.

**Proč:** F1 v `.ai_state.json`: 0× asyncio v `src/`. Jeden běh blokuje event loop, takže
paralelní tool cally se serializují. To je přesně scénář z #1, kdy agent volal 8× za sebou.

**Feynman:** Obsluha je jedna a obsluhuje jednoho zákazníka. Když první čeká 30 s na motor,
druhý se nedostane na řadu. Přesuneme čekání do vedlejší místnosti, aby obsluha mohla
odpovídat ostatním.

**Acceptance:** dva paralelní `coaching_single_game` na různých hrách doběhnou za
`max(t1,t2) + 20 %`, ne za `t1+t2`.

---

### 5.3 P2 — architektura

| # | Co | Proč | Feynman |
|---|---|---|---|
| P2.1 | Submit + poll (`job_id`, `search_status`) pro `deep` režim, dle GT-087 / P13 | Dlouhá analýza nesmí držet tool call 120 s | „Objednávka dostane číslo a stav. Nemusíš držet telefon pět minut." |
| P2.2 | Paralelní analýza tahů (2–4 workery, deterministické pořadí) | Další 2–3× zrychlení po P1.1 | „Čtyři kuchaři připravují čtyři talíře, ne jeden po druhém." |
| P2.3 | Stage-level audit a metriky (`engine_s`, `llm_s` v JSONL) | Udržet observability po zavedení deadline | „Palubní deska se nesmí vypnout, když se zrychlí motor." |

P2 se nespouští, dokud P0 a P1 nejsou zelené na golden regression.

---

## 6. Co záměrně neděláme

| Vyloučeno | Důvod |
|---|---|
| Nová pattern inference z LLM | Porušuje DATA-FABRICATION-001; patterny musí být deterministické |
| Odemčení `min_games` pro single game | Skupinové statistiky nedávají na 1 hře smysl a kód by spadl na dict vstupu |
| Změna batch/cross-game pipeline | Mimo rozsah; riziko regrese 20-game reportů |
| Změna KB writeru | Jen konzumuje `report`; stačí alias |
| Ladění Stockfish binárky, hash, threads nad rámec node caps | Není to páka; cena je v počtu analýz |
| Redesign textu reportu | Řešíme pravdivost zdroje, ne styl |
| `max_time_dual` a batch budgety | Jiný produktový povrch |

---

## 7. Předpoklady a rizika

| # | Riziko | P | Dopad | Mitigace |
|---|---|---:|---|---|
| R1 | Běžící server není HEAD | 0,6 | měříme minulost | P0.0 před vším |
| R2 | LLM klíče/kredity nedostupné | 0,9 | nelze ověřit `llm.status="ok"` | P0.3 testuje jen degradaci; „ok" je ops úkol |
| R3 | 1 analýza/pozici změní ACPL > 10 % | 0,3 | golden A1 padne | hybrid: 3 analýzy pro mistake/blunder |
| R4 | `None` v `centipawn_loss` rozbije konzumenty | 0,7 | testy/CI | `analyzed` flag + migrační test N5 + grep konzumentů |
| R5 | Stockfish nondeterminismus | 0,8 | flaky golden | ±10 % tolerance, pevný hash, 4 thready |
| R6 | mypy 42 chyb blokuje CI | 0,9 | nový kód nemusí projít | nové moduly typované; gate řešit samostatně |
| R7 | `evaluate_move_with_confidence` (3 runs) zůstane | 0,5 | zdvojení práce v deep | použít jen na explicitní `confidence=true` |

---

## 8. Implementační pořadí, odhady, exit gate

Odhady jsou pracovní, nikoli závazné termíny (P~0.5).

| Milník | Obsah | Odhad | Exit gate |
|---|---|---:|---|
| M0 | P0.0 verifikace + restart | 0,5 h | běží HEAD, warm běh změřen |
| M1 | P0.1–P0.3 kontrakt + deadline + LLM | 8 h | N1, N2, N4; A3–A6, A9 |
| M2 | P0.4–P0.5 patterny + vysvětlení | 6 h | A7, A8 |
| M3 | P0.6 golden harness | 4 h | 3/3 hry, N1–N5 |
| M4 | P1.1–P1.3 výkon | 12 h | fast p50 ≤ 15 s, warm ≤ 5 s, 0 cloud 404 |
| M5 | P1.4 async + pool | 6 h | paralelní běh dle A11 |
| M6 | P2.1–P2.3 architektura | 16 h | job API, stage audit |

**Ship gate po P0:** všechny tři golden hry zelené, response obsahuje `timings`, `status`,
`llm`, `patterns_meta`, žádná nula za chybu, žádné `[]` bez důvodu.

**Ship gate po P1:** SLO z §2.3 splněno na golden sadě.

---

## 9. Schvalovací checklist

Před implementací potvrdit:

- [ ] Kontrakt v §2.2 je závazný (zejména `status`, `llm.status`, `centipawn_loss: null`).
- [ ] SLO v §2.3 je přijatelné (P0: fast p50 35 s / hard 60 s; P1: p50 12 s / hard 30 s).
- [ ] P0.4 mění původní plán `min_games_override` na samostatný single-game surface.
- [ ] P1.1 smí změnit ACPL do ±10 %; jinak hybrid.
- [ ] Golden sada = 3 hry výše; `wC3fgDiQ` jen jako negativní fixture.
- [ ] P0.3 nevyžaduje nové kredity; „ok" stav je samostatný ops úkol.
- [ ] Commity: jeden logický celek na položku P0.x, zpráva `[PLAN]` / `[COACHING]` dle konvence.

---

## 10. Poznámky k provenience

- Měření: `logs/audit_202611.jsonl` (tool-level), `logs/lichess_mcp_202611.log`, vlastní
  benchmark `.venv` (4 thready, hash 128 MB), 2026-11-07.
- Cache: `data/game_cache/{game_id}_{color}_d{depth}.json` (`mHgzFNl4_black_d14.json`,
  `KkAkq59s_white_d14.json`) — ověřeno `total_acpl`, `evaluation_errors`, `phase_stats`.
- Historie rozhodnutí: commity `a536845`, `4348b04`, `3d3f26f`, `00776f0`, `f9f60b5`,
  `17dd5fb`, `a5e9dad`; dokumenty `CODE_REVIEW_2026-08-01.md`, `DEPTH_POLICY.md`,
  `DEEP_DIVE_SINGLE_GAME_PATTERNS_2026-08-02.md`, `.ai_state.json`.
- GT: GT-051 / P36 (model ID discovery), GT-057 / P42 (cascade resilience),
  GT-087 / P13 (long-running operations).

---

## 11. Nález z testu #5 (anonymní hra NxKgE4l8, 2026-11-08)

První běh na nové hře odhalil defekt, který plán nepředjímal:

| Symptom | Root cause | Fix |
|---|---|---|
| `status=partial`, 12/25 tahů, 13× `ENGINE_ERROR: engine event loop dead` | `evaluate_move()` předával vlastní referenci do `_run_engine_call()`; timeout engine zabil, ale `_engine` zůstal ukazovat na mrtvý proces → všech 13 následujících tahů selhalo | `_run_engine_call()` čistí `_engine`, kdykoli zabil sdílený engine; `reset_engine()` + jeden retry tahu v `game_analyzer` |
| timeout na ply 25 už při 3 s | `evaluate_move` = až 3 analýzy (before/best/played); cap `per_move_s × 1.2` byl pod reálnou potřebou | floor 6 s na tah (BFS lines floor 5 s), vždy omezeno zbytkem budgetu |
| vlajkovaný tah bez vysvětlení (BFS timeout) | vysvětlení se stavělo jen z multi-PV linií | fallback: SAN z `best_move_uci` + naměřený cp_loss → `explanation_source=deterministic` |
| částečný výsledek se uložil do cache | `_save_cached_analysis()` bez kontroly `unanalyzed_plies` | partial se necachuje (jinak by se mezera replikovala navždy) |

Měření po opravě (stejná hra, cold/warm): 25/25 tahů, 0 timeoutů, 7 vlajkovaných tahů,
všechny s vysvětlením, 28,7 s / 2,5 s.

**Otevřený nález (nedeterminismus):** dva cold běhy stejné hry daly ACPL 47,6 a 41,6
a jinou množinu vlajkovaných tahů (5 vs 7). Příčina: `Threads=4` + transposition table
se mezi tahy nečistí (clear jen na konci hry). Reprodukovatelnost by vyžadovala
`Threads=1` + `Clear Hash` před každým tahem; to je kalibrační rozhodnutí, ne bug —
zatím nezvoleno.

**Defekt nalezený v hotovém reportu (2026-11-09):** deterministický report tvrdil
„Žádný blunder“, i když data obsahovala 1 blunder (ply 41 Qf5+, 308 cp). Příčina:
parser hledal v promptu literál `Blundry:`, šablona však používá `Blundry (s detaily):`
→ hodnota byla vždy prázdná. Fix: `_bullet_value()` (prefix labelu + pokračovací řádky),
křížová kontrola přes `Počet chyb`, ořez na hranici pole místo uprostřed slova.
Testy: `tests/test_deterministic_report.py` (5). Jde o přesně ten typ vady, který plán
řadí do P0: čísla jsou správná, ale tvrzení o nich je nepravdivé.

**Kosmetika (neopraveno):** šablona promptu generuje „1 blunderů / 2 chyb“; je to
gramatika, ne datová vada — mimo rozsah této kalibrace.

---

## 12. Determinismus a uzavření handoffu FIX-001..FIX-010 (2026-11-09)

Cíl: stejná hra + stejný vstup ⇒ stejná čísla, stejná množina vlajkovaných tahů,
stejný report. Bez wall-clock závislosti a bez externího evaluátoru. Řešení musí
zůstat jednoduché — nástroj slouží k rychlému opakovanému hodnocení vlastních her.

### 12.1 Zvolená politika (FIX-003)

| Prvek | Hodnota | Důvod |
|---|---|---|
| `ENGINE_THREADS` | `1` | více vláken = výsledek závisí na plánování vláken (ACPL 47.6 vs 41.6) |
| limit | `Limit(depth=…, nodes=…)` | oba jsou search counters, žádný wall clock; `depth` rozhoduje v klidných pozicích, `nodes` jen zastropuje patologické |
| `Clear Hash` | před každým top-level voláním (`evaluate_move`, `analyze_position_ex`) | žádné carry-over z předchozích tahů |
| cloud eval (`chess-api.com`) | `use_cloud=False` default, jen opt-in | vzdálený engine = nekontrolovaná verze a hloubka |
| `LLM_TEMPERATURE` | `0.0` (bylo 0.3) | deterministický text, když je LLM dostupné |

`NODE_CAPS = {12: 80_000, 14: 150_000, 16: 400_000, 18: 1_000_000}`.
Měřeno na `r1bqk2r/...`: 150k = 0.43 s (depth 17), 250k = 0.65 s (depth 20);
depth 14 s 1 vláknem = 0.10 s / 47.6k nodes. Strop tedy neovlivňuje klidné pozice,
ale drží worst case na ~0.4 s na jeden engine call.

Politika je součástí cache klíče: `{game}_{color}_d{depth}n{nodes}.json`
(např. `NxKgE4l8_white_d14n150000.json`). Staré cache bez suffixu se pro novou
politiku nepoužijí — první běh hry je cold. Batch/legacy volající mají prázdný
suffix, takže jejich cache zůstává platná.

### 12.2 Měřené ověření

| Hra | Běh 1 | Běh 2 | Shoda |
|---|---|---|---|
| `NxKgE4l8` (25 tahů, white) | ACPL 29.6, acc 95.6, 6 flagů, pattern T 0.48 | ACPL 29.6, acc 95.6, 6 flagů, pattern T 0.48 | flagged set + report byte-identical |
| `lxO3gwd3` (34 tahů, black) | ACPL 18.2, acc 97.3, 4 flagy, pattern T 0.16 | ACPL 18.2, acc 97.3, 4 flagy, pattern T 0.16 | flagged set + report identical |

Oba běhy byly cold (cache přesunuta). Engine 11.4–19.2 s, celkem 14.6–23.5 s
podle délky hry. LLM cascade je nedostupná (402/404), report je deterministický
(`report_source=deterministic`), takže běh nevisí na síti.

**Důsledek pro interpretaci:** ACPL 43.3 → 29.6 na `NxKgE4l8` není zlepšení
algoritmu. Staré číslo vzniklo s `Threads=4` a remote cloud eval; čísla z reportů
před touto změnou nejsou s novými srovnatelná. Nové reporty mají v `engine`
bloku `limit=depth+nodes`, `nodes_cap`, `threads=1`.

### 12.3 Ostatní FIX položky

| FIX | Stav | Řešení |
|---|---|---|
| FIX-001 | hotovo | report odvozuje počet blunderů z `flagged_moves`, parser `_bullet_value()`; testy `test_deterministic_report.py` |
| FIX-002 | hotovo | `check` = hraný tah dává šach (odpovídá `motif=check`); předchozí stav je `in_check_before`; schema 1.1 rozšířena |
| FIX-003 | hotovo | viz 12.1 |
| FIX-004 | hotovo | jeden retry BFS top-3 linií při timeoutu; žádný exponential backoff ani fallback z předchozího ply |
| FIX-005 | odloženo | `color=both` by vyžadoval schema 1.2 a 2× náklady; pro hodnocení vlastních her stačí jeden color |
| FIX-006 | pokryto | deterministický report už uvádí konkrétní ply/SAN/cp_loss/best/rank/FEN; strukturování by nic nepřidalo |
| FIX-007/008/010 | odloženo (P2) | ACPL→ELO heuristika by fabrikovala přesnost; ostatní je DX |
| FIX-009 | hotovo | `scripts/coach_single.py` + `scripts/mcp_call.py`, viz `docs/CLI_USAGE.md` |

### 12.4 Zbylé riziko

- `tests/test_engine_client.py` zůstává závislé na sdíleném Stockfish procesu
  a v suite se přeskakuje; politika je pokryta mockovanými testy v
  `tests/test_determinism.py`.
- Starý MCP server proces (spuštěný před změnou) vrací starou politiku, dokud
  se nerestartuje. CLI skripty spouští vždy aktuální kód v novém procesu.
