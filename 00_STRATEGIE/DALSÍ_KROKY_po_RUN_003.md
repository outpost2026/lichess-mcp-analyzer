# Návrh dalších kroků po RUN_003 + CPM korelace

**Datum:** 2026-07-27 | **Verze:** 2.0 (CPM korelovaná)
**Kontext:** DBCL v1.1 implementována, RUN_003 dokončen, CPM v1.0 dokument analyzován
**Princip:** Vše auditovatelné, zpětně rekonstruovatelné, žádná black box logika. Vývoj MCP serveru je současně vzdělávací proces.

---

## 0. Korelační zjištění: CPM vs Realita

### Co CPM přináší nového (oproti v1.0 plánu)

| CPM koncept | V DALSÍ_KROKY v1? | Dopad na plán |
|-------------|-------------------|---------------|
| **K0 jako samostatný kanál** (orákulum) | ❌ Chybí | Build plan má jen K1/K2/K3. K0 (Stockfish kvalita, depth konzistence) ovlivňuje všechny downstream výsledky. Musí být explicitně řízen. |
| **CR = N / (C_impl + C_udrz)** | ❌ Chybí | Každý pattern by měl mít měřitelný kompresní poměr. Bez něj nelze rozhodnout, zda se pattern vyplatí udržovat. |
| **Pattern typy** (author_error, mechanism, ...) | ❌ Chybí | Typ patternu určuje prioritu opravy a mitigaci. author_error > mechanism > recovery. |
| **it_analogy pole** | ❌ Chybí | Každý pattern musí mít IT analogii pro generalizaci. Chybí v `PatternDef` modelu. |
| **7 typů evidence** | ⚠️ Částečně | Evidence format standard je v CPM definován, v kódu nekonzistentní (AUD-08). |
| **6-fázový lifecycle** | ⚠️ Implicitně | Build plan sleduje lifecycle, ale nepojmenovává ho. Explicitní lifecycle zlepší audit trail. |

### Co CPM potvrzuje

| Naše rozhodnutí | CPM verdikt |
|----------------|-------------|
| P0-2 audit před implementací | ✅ **Správně.** Audit je fáze 3 lifecycle. Bez auditu je pattern v observační fázi. |
| Anti-blackbox přístup | ✅ **Korektní.** CPM §8 explicitně vyžaduje interpretabilitu, falsifikovatelnost, auditovatelnost. |
| Per-blunder pattern matching | ✅ **Správně.** CPM říká: pattern je hypotéza o generativním procesu. Per-blunder = jedna instance. Cross-game = agregace. |
| narrative_validator jako K2 řešení | ✅ **Správně.** CPM potvrzuje K2 jako samostatný noise channel. |
| Depth=12 pro rychlý run | ⚠️ **K0 kompromis.** Nižší depth = nižší SNR v K0. ACPL čísla nejsou přímo srovnatelná s depth=14 runy. |

---

## 1. Korekce build planu: K0 channel

### Současný stav (3 channels)
```
K1 (detektor) → K2 (kontrakt) → K3 (dekodér)
```

### Navrhovaný stav (4 channels) — dle CPM
```
K0 (orákulum) → K1 (detektor) → K2 (kontrakt) → K3 (dekodér)
```

### Co se mění

| Aspekt | Před korelací | Po korelaci |
|--------|---------------|-------------|
| Depth policy | "depth=12 pro rychlost" | **Explicitní K0 metrika:** každý run reportuje K0 quality (depth, engine version, nps, timing) |
| Srovnatelnost runů | Předpokládá se | **K0 variance se měří:** RUN_002 depth 12-14 vs RUN_003 depth 12 → ACPL rozdíl může být částečně K0 noise |
| Cache refresh | "smazat a znovu" | **K0 audit před refresh:** ověřit, že engine verze/thready/depth jsou konzistentní napříč cache |
| INC-A/B/C verifikace | Chybí | **K0 ground truth:** BFS eval_before/eval_after musí být ověřitelné proti Stockfish depth=14 (ne depth=12) |

---

## 2. Revidovaný plán: 10 kroků + 3 nové

### Priorita 0 (NOVÁ): Stabilizovat K0

**K0-1: Zdokumentovat Stockfish konfiguraci pro každý run**

| Atribut | Hodnota |
|---------|---------|
| **Problém** | Každý run používá Stockfish, ale nikde není zaznamenáno: binary verze, Threads, Hash, depth per-game, časová omezení. RUN_002 měl 7/9 @ d14, RUN_003 je 100% @ d12. |
| **Řešení** | Vytvořit `data/runs/RUN_004_config.json` template, který se vyplní při každém runu. Povinná pole: engine_version, binary, Threads, Hash, depth, nps_benchmark, total_time_seconds. |
| **Binární MVP** | Každý run report v `data/runs/` obsahuje K0 sekci. |
| **Edukace** | K0 je "měřicí přístroj". Bez znalosti jeho přesnosti jsou všechny hodnoty relativní. |

**K0-2: Ověřit depth konzistenci napříč cache**

| Atribut | Hodnota |
|---------|---------|
| **Problém** | Současná cache obsahuje depth=12 i depth=14. Při načítání s `use_cache=True` se použije nejbližší depth, ne nutně konzistentní. |
| **Řešení** | Rozšířit `_load_cached_analysis()` o logování depth mismatchů. Při mixed depth cache: warning do loggeru. |
| **Binární MVP** | Pipeline log obsahuje "K0 WARNING: depth mismatch" pokud jsou data nekonzistentní. |

**K0-3: INC-A/B/C re-fetch na depth=14**

| Atribut | Hodnota |
|---------|---------|
| **Problém** | kNAMNYUF, xUlQasD0, qmodxzNF byly smazány s cache. Jsou to jediné hry s manuálně verifikovanými halucinacemi (SRC-3). Bez nich nelze otestovat DBCL guard-clause ani narrative validator. |
| **Řešení** | Explicitně stáhnout PGN pro tyto 3 hry a analyzovat depth=14 (ne 12). Porovnat eval_before/eval_after s referenčními hodnotami z unity doc. |
| **Binární MVP** | Tři cache soubory s BFS, ověřené proti unity doc §2. |
| **Edukace** | Ground truth není abstraktní — je to konkrétní číslo z konkrétního běhu Stockfish na konkrétní FEN. |

### Priorita 1 (REVIDOVANÁ): Uzavřít K1 (detektor)

**Pořadí oprav se mění podle CPM typologie:**

| Pořadí | Pattern | Typ (CPM) | Důvod priority |
|--------|---------|-----------|----------------|
| **1a** | B (Automatic grab) | author_error | Nejjednodušší oprava (AUD-01), vysoký dopad na confidence |
| **1b** | J (Impulsive check block) | author_error | Již částečně opraven (F-007), zbývá per-blunder konzistence |
| **1c** | O (Repetition avoidance) | author_error → mechanism | Nejtěžší oprava (AUD-04), ale 0/15 true detekcí je kritické |
| **1d** | I (Bait trap → Opponent's grab) | strategy → author_error | Přejmenování + hypothesis fix (AUD-03/11) |
| **1e** | Q+Q2 merge | recovery | Sloučení duplicit (AUD-05) |
| **1f** | S (Capture aversion) | author_error | Nový pattern z INC-B, do produkce (AUD-10) |

**Každá oprava musí splňovat CPM evidence standard (AUD-08):**
- evidence NESMÍ být jen `{"affected_games": N}`
- MUSÍ obsahovat: konkrétní hodnoty, thresholdy, podmínky detekce
- Formát: `{"field": value, "condition": "string", "threshold": float}`

### Priorita 2 (REVIDOVANÁ): Uzavřít K3 (dekodér)

**2a: Reject loop pro narrative validator** (beze změny oproti v1)

**2b (NOVÉ): Přidat it_analogy do PatternDef a guard clause**

| Atribut | Hodnota |
|---------|---------|
| **CPM mapping** | §4.1: `it_analogy: str` je povinné pole každého patternu |
| **Současný stav** | `PatternDef` v `models/pattern.py` toto pole nemá. Guard-clause neobsahuje IT analogie. |
| **Řešení** | Přidat `it_analogy: str = ""` do PatternDef. Při sestavování promptu: zahrnout it_analogy do popisu patternu. |
| **Příklad** | Pattern B (Automatic grab): it_analogy = "git push --force bez review" |
| **Edukace** | IT analogie je most pro transfer patternu do jiné domény. Bez něj je pattern vázaný na šachy. |

### Priorita 3 (REVIDOVANÁ): Uzavřít K2 (kontrakt)

**3a: P0-5 K2 protokol** (beze změny oproti v1)

**3b (NOVÉ): Přidat compression_ratio metriku do pattern reportu**

| Atribut | Hodnota |
|---------|---------|
| **CPM mapping** | §4.3: CR = N_detected / (C_impl + C_udrz) normalizováno na stovky řádků |
| **Implementace** | Do `PatternMatch` přidat `compression_ratio: Optional[float]`. Počítat při `detect_all()`: `CR = len(affected_games) / max(1, (detector_lines / 100))`. Logovat patterns s CR < 1 jako WARNING. |
| **Očekávané hodnoty** | Pattern B: ~12/0.7 ≈ 17. Pattern J: ~3/0.7 ≈ 4. Pattern C: ~9/0.7 ≈ 13. Všechny > 1. |
| **Edukace** | Kompresní poměr je ekonomické kritérium: "stojí tento pattern za údržbu?" |

### Priorita 4 (NOVÁ): Měřit K0 noise

**4a: Depth srovnávací test**

| Atribut | Hodnota |
|---------|---------|
| **Cíl** | Zjistit, jak moc se liší ACPL, blunder count a pattern detekce mezi depth=12 a depth=14 na stejných hrách |
| **Metoda** | Vybrat 5 her z RUN_003, analyzovat depth=14 (zatímco depth=12 cache existuje). Porovnat per-move eval rozdíly. |
| **Očekávání** | Depth 14 by měl mít nižší ACPL (přesnější eval → menší cp_loss). Očekávaný rozdíl: 3-10% ACPL. |
| **Binární MVP** | Report: "Na N hrách je průměrný rozdíl ACPL mezi d12 a d14 = X%" |

---

## 3. CPM lifecycle mapování

Každý krok je explicitně mapován na CPM lifecycle fázi:

```
Fáze 0 (Observace):   INC-A/B/C incidenty → RUN_001/002/003 data
Fáze 1 (Hypotéza):    PatternDef v models/pattern.py (existuje pro A-Q2, chybí pro S)
Fáze 2 (Implementace): _detect_X() v pattern_detector.py
Fáze 3 (Audit):       P0-2 audit matrix (HOTOVO pro 11 patternů)
                      → NÁSLEDUJE: opravy podle AUD-01 až AUD-11
Fáze 4 (Kalibrace):   Threshold ladění + confidence vzorce
                      → NÁSLEDUJE: po opravách
Fáze 5 (Produkce):    detect_all() v pipeline
                      → NÁSLEDUJE: RUN_004
Fáze 6 (Re-kalibrace): Každých +50% dat
```

### Stav jednotlivých patternů v lifecycle

| Pattern | Fáze 0 | Fáze 1 | Fáze 2 | Fáze 3 | Fáze 4 | Fáze 5 | Fáze 6 |
|---------|--------|--------|--------|--------|--------|--------|--------|
| A | ✅ | ✅ | ✅ | ✅ PASS | ✅ | ✅ | ⏳ |
| B | ✅ | ✅ | ✅ | ⚠️ AUD-01 | ⏳ blokováno | ✅ | ⏳ |
| C | ✅ | ✅ | ✅ | ⚠️ AUD-02 | ⏳ blokováno | ✅ | ⏳ |
| G | ✅ | ✅ | ✅ | ✅ PASS | ✅ | ✅ | ⏳ |
| I | ✅ | ✅ | ✅ | ❌ AUD-03 | ⏳ blokováno | ✅ | ⏳ |
| J | ✅ | ✅ | ✅ | ✅ FIXED (P0-1) | ✅ | ✅ | ⏳ |
| O | ✅ | ✅ | ✅ | ❌ AUD-04 | ⏳ blokováno | ✅ | ⏳ |
| P | ✅ | ✅ | ✅ | ⚠️ AUD-06 | ⏳ blokováno | ✅ | ⏳ |
| Q | ✅ | ✅ | ✅ | ❌ AUD-05 | ⏳ blokováno | ✅ | ⏳ |
| Q1 | ✅ | ✅ | ✅ | ✅ PASS | ✅ | ✅ | ⏳ |
| Q2 | ✅ | ✅ | ✅ | ✅ PASS | ✅ | ✅ | ⏳ |
| R | ✅ | ✅ | ✅ | ✅ PASS | ✅ | ✅ | ⏳ |
| **S** | ✅ | ⏳ | ❌ | ❌ | ❌ | ❌ | ❌ |
| N | ✅ | ✅ | ✅ | ✅ PASS | ✅ | ✅ | ⏳ |

Legenda: ✅ hotovo | ⚠️ částečně/audit pass s výhradami | ❌ neprošlo | ⏳ pending

---

## 4. Revidovaný commit checklist

1. `[K0-3] feat: INC-A/B/C re-fetch depth=14` — ground truth pro DBCL testování
2. `[K0-1] docs: RUN_config template s K0 metrikami`
3. `[AUD-01] fix: B total_captures scope` — přesunout counter mimo blunder podmínku
4. `[AUD-03/11] fix: I rename + hypothesis` — "Opponent's grab exploit"
5. `[AUD-04] fix: O real repetition detection` — parsovat board history
6. `[AUD-05] fix: Q + Q2 merge` — odstranit duplicitní detekci
7. `[AUD-10] feat: S capture aversion under check` — do produkce
8. `[AUD-08] fix: evidence format standard` — structured dict místo string
9. `[CPM] feat: it_analogy do PatternDef + prompt` — generalizační most
10. `[CPM] feat: compression_ratio do PatternMatch + WARNING pri CR<1`
11. `[P1-4] feat: reject loop v LLM pipeline` — integrovat narrative validator
12. `[P1-5] feat: SRSCard konzument BFS`
13. `[P0-5] feat: K2 kontrakt per-game/aggregate`
14. `[K0-2] feat: depth mismatch warning v cache load`
15. `[RUN_004] data: fresh pipeline run depth=14` — finální verifikace

---

## 5. Vzdělávací momenty (pro deva)

### Z CPM §8 — Anti-blackbox

> "Proč ne ML black-box? Protože ML nedokáže odpovědět na otázku 'proč se pattern spustil?' Náš detektor ano — je to explicitní podmínka v kódu."

Toto je klíčový rozdíl mezi "predikcí" (ML) a "porozuměním" (CPM). Všechny naše patterny jsou otevřené modely — každý řádek detektoru je falsifikovatelný. Pattern O je ukázkový příklad: díky otevřenosti jsme zjistili, že 0/15 detekcí je skutečná repetition avoidance. U ML black-boxu bychom to nezjistili nikdy.

### Z K0 — Měřicí přístroj

Stejně jako nelze měřit délku bez znalosti přesnosti metru, nelze měřit ACPL bez znalosti depth Stockfish. RUN_003 ACPL = 39.4 při depth=12. Pokud bychom zítra spustili depth=14 a dostali ACPL = 37.0, není to zlepšení hráče — je to K0 noise.

### Z compression_ratio — Ekonomie patternů

Pattern s CR < 1 stojí víc, než ušetří. To je ekonomický argument pro "neimplementovat všechno." Pattern S (capture aversion) má N=2 → CR ~ 2/0.6 ≈ 3.3, takže se vyplatí. Ale kdyby měl N=1, CR by bylo ~ 1.7 — stále > 1, ale těsně. To je důvod, proč je S v P3 (dlouhodobé) v build planu.

---

## 6. Shrnutí změn oproti v1.0

| Sekce | v1.0 | v2.0 (CPM korelovaná) |
|-------|------|----------------------|
| Priorita 0 | Neexistuje | **K0: Stabilizovat orákulum** (3 nové kroky) |
| Priorita 1 | 5 kroků (AUD fixy) | **6 kroků** (přidán S, změněno pořadí dle typologie) |
| Priorita 2 | 1 krok (reject loop) | **2 kroky** (přidáno it_analogy) |
| Priorita 3 | pending opposite-color | **3 kroky** (přidán CR metric, K2 protokol) |
| Priorita 4 | Neexistuje | **K0 noise měření** (depth srovnání) |
| Commit checklist | 10 commitů | **15 commitů** (přidány K0, CPM, evidence standard) |
| Pattern lifecycle | Implicitní | **Explicitní: 6 fází CPM** se stavem per-pattern |
| Vzdělávací momenty | 0 | **3 sekce** z CPM pro deva |

---

*Navrženo 2026-07-27. Korelace s COMPRESSION_PATTERN_METHOD_v1.0.md provedena. Žádný kód nebyl editován.*
