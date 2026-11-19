# 00 Docs Contract — navigace a autorita dokumentace

**Datum:** 2026-11-18 | **Autor:** LLM agent (opencode), W3 trimmingu | **Status:** AKTIVNÍ
**Účel:** Jediný vstupní bod pro orientaci v dokumentaci. Definuje, který soubor je pro co zdroj pravdy, v jakém pořadí číst a co považovat za historii.

---

## 1. Read order (nová session)

1. `README.md` (root) — rychlý přehled, proč a jak, 18 toolů, CLI příklady.
2. `docs/SESSION_HANDOFF_2026-11-17.md` — **current state**: kontrakty, příkazy, validační vzorek, otevřené položky, pravidla pro agenta.
3. `docs/COMPACT_JSON_FOR_LLM.md` — **runtime kontrakt** compact 2.9 + Appendix A (`game_full` 1.0). Číst vždy před prací s payloadem.
4. `docs/CLI_USAGE.md` — konkrétní volání 18 MCP toolů, PowerShell quoting, exit codes.
5. `docs/AUDIT_INTEGRATION_2026-11-13.md` — **závazná rozhodnutí D1–D40** (při rozhodování o změně kontraktu).
6. `docs/PATTERN_DISCOVERY_METHODOLOGY.md` — **závazná metodologie v1.7** (při práci s patterny).
7. `docs/01_EVIDENCE_DIGEST.md` — historická evidence, root causes a decision provenance. **Číst jen pro pochopení, proč věci jsou jak jsou** — nikdy jako aktuální kontrakt.
8. `docs/02_COACHING_EXEMPLARS.md` — reprezentativní výstupy a katalog nálezů.

`CHANGELOG.md` (root) = autoritativní historie releasů [2.1]–[2.16].

---

## 2. Autorita (zdroj pravdy)

| Oblast | Kanonický zdroj | Poznámka |
|---|---|---|
| Current stav projektu | `SESSION_HANDOFF_2026-11-17.md` | Jediný „CURRENT STATE" artefakt |
| Kontrakt compact 2.9 / game_full 1.0 | `COMPACT_JSON_FOR_LLM.md` + `schemas/` | `schemas/single_game_v2_compact_2.9.json`, `game_full_v1.0.json` |
| Kontrakt detailed 1.2 | `schemas/single_game_v1.2.json` | kód: `coaching_single_game.py` |
| Cross-game 1.4 | inline v `src/lichess_analyzer_mcp/kb/schemas.py` | žádný samostatný schema soubor |
| Depth policy | `src/lichess_analyzer_mcp/config/depth.py` | runtime; `DEPTH_POLICY.md` je v `_ARCHIVE/` |
| Engine identity | `config/engine_identity.json` | pin pro CI |
| Prompt text | `src/lichess_analyzer_mcp/services/prompt_builder.py` | `CHESS_COACHING_PROMPT_TEMPLATES.md` v archivu |
| Závazná rozhodnutí | `AUDIT_INTEGRATION_2026-11-13.md` | §14 = D38–D40 |
| Metodologie patternů | `PATTERN_DISCOVERY_METHODOLOGY.md` | v1.7 |
| Antifabrikace | `_github/AGENTS.md` §6 (DATA-FABRICATION-001) | deterministická data > narace |
| Root causes / měření (historická) | `01_EVIDENCE_DIGEST.md` | vždy s bannerem „dated evidence" |
| Coaching data | `data/reports/*.json`, `data/game_cache/` | gitignored, deterministická vrstva |

---

## 3. Pravidla

- **P1 — jeden zdroj pravdy.** Nový fakt patří do existujícího kanonického souboru, ne do nového. Kopie se nahrazuje odkazem.
- **P2 — procesní artefakty ven.** Deníky, per-iterační audity, handoffy a jednorázové plány patří do `_ARCHIVE/`, ne mezi aktivní docs. Test: „bude to smysluplné za 6 měsíců bez kontextu iterace?"
- **P3 — banner povinný.** Každé historické číslo v `01_EVIDENCE_DIGEST.md` má zdrojový anchor a označení „historické měření pro HEAD/verzi X, ne aktuální kontrakt".
- **P4 — dated snapshoty.** Nová generace ⇒ starší do `_ARCHIVE/`; kanon = poslední datum.
- **P5 — drift check.** Seznam aktivních souborů výše musí sedět s `git ls-files docs`. Změna → aktualizuj tento soubor a `SESSION_HANDOFF` §6.
- **P84–P89 — gate.** Žádné mazání bez echo-back (cesta + počet + souhlas); soft-delete přes `git mv`; po operaci integrity snapshot (count + bytes); selhání/lock = STOP bez nové autorizace.
- **ASCII názvy** `[A-Za-z0-9._-]` (GT-080); obsah UTF-8, bez emoji; `python -X utf8`, `$env:PYTHONIOENCODING='utf-8'`.
- **Verze v názvu souboru/seksi musí sedět s obsahem.** Zjištěné drift opraveny ve W1 (2.3→2.7, 2.1→2.7, D35 2.7→2.2, `eval_before_mover_cp` 2.7→2.6, U/V).

---

## 4. Archiv

`_ARCHIVE/` obsahuje 72+ souborů z trimmingu 2026-11-18 (původní `docs/`, `00_STRATEGIE/`, část `scripts/` a `schemas/`). Není to aktivní navigace; slouží výhradně jako git-historie a zdroj pro `01_EVIDENCE_DIGEST.md`. Odkazovat na něj lze jen jako na „původní znění před W3", nikoli jako na platný kontrakt.

Archivace provedena: checkpoint `6f2694d` → W1 `f6eaa98` → W2 `4eb9741` → W3 (tento commit).
