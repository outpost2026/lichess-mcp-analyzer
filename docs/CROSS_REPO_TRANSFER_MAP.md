---
title: Cross-repo transfer map - ML_Ops_edukace a mcp-retrieval
date: 2026-11-12
verze: 1.0
status: ANALYTICKÝ ARTEFAKT (návrh transferu, nic neimplementováno)
účel: Vyhodnotit, které kontrakty, metriky a implementace z pracovního prostředí autora jsou přenositelné do lichess pattern discovery, a v jakém pořadí.
navaznost: PATTERN_DISCOVERY_METHODOLOGY.md, CANDIDATE_PATTERNS_2026-11-12.md
---

## 0. TL;DR

1. Oba repozitáře jsou **relevantní a přenositelné**, ale ne jako hotový pattern engine. Jsou to **reference implementace tří kontraktů**, které lichess pipeline právě postrádá: abstention, data identity a drift guard.
2. Nejsilnější transfer není algoritmus. Je to **měřicí disciplína**: každé číslo s dataset hash + commit + `n` + before/after, a žádný tichý fallback.
3. `mcp-retrieval` je produkční reference pro BM25 + RRF + abstention + freshness + drift (MIT, malé moduly). `ML_Ops_edukace` je výzkumná laboratoř pro evaluaci na malém korpusu, kompresi a negativní výsledky.
4. **Nepřebírat:** dense embeddings (jejich vlastní měření: MRR 0,26-0,31 vs 0,70 BM25), MMR pro ranking (0,5987 vs 0,7067), LLM v detection path.
5. Tři konkrétní návrhy s nejvyšším poměrem hodnota/úsilí: **T1 provenance blok**, **T2 skutečná komprese**, **T3 drift guard pattern knihovny**. Teprve pak T4 (RRF pro řazení lekcí) a T5 (`pattern_search` MCP tool).

---

## 1. Metoda a rozsah

Prošel jsem oba repozitáře na úrovni README, dokumentace, skriptů, výsledků a klíčových modulů. Čísla přebírám z jejich `results/` a dokumentace; **neověřoval jsem je vlastním během** (P~0,8 o jejich platnosti v jejich kontextu). Návrhy transferu jsou moje, s uvedenou úrovní jistoty.

Co jsem nehodnotil: instalační závislosti, výkon na Windows, licenční kompatibilitu při přímém copy-paste (MIT vs tento repo).

---

## 2. Inventura

### 2.1 ML_Ops_edukace

| Vrstva | Co obsahuje | Stav |
|---|---|---|
| Dataset | 121 GT entries, 106 pravidel, JSONL + JSON Schema + SHA-256 | produkční disciplína |
| Retrieval | BM25, TF-IDF, SVD, query expansion, RRF, MMR, Word2Vec/GloVe | experimenty s měřením |
| Evaluace | MRR, Hits@5, Prec@3, Recall@5, 50 dotazů CZ/EN | reprodukovatelné s hashem |
| Komprese | JSONL vs markdown: -49,7 % bytes, -49,1 % tokens | měřeno na 22/108 entries |
| Dokumentace | bottleneck analýza B1-B5, P0 proposal, glosář | vysoké SNR |
| Negativní výsledky | Word2Vec 0,3107; GloVe 0,2607; MMR 0,5987; SVD 0,5413 | cenné |

### 2.2 mcp-retrieval

| Vrstva | Co obsahuje | Stav |
|---|---|---|
| Engine | `BM25` + `SequenceMatcher` + `RRF(k=60)` | produkce, 51 testů |
| Abstention | `matched:false` + `reason` při nulovém lexikálním překryvu | produkce |
| Freshness | reload při změně `(mtime_ns, size)` | produkce |
| Identita dat | `data_version` = entries + rules + source_version + SHA-256 | produkce |
| Drift guard | JSONL ↔ meta ↔ kanon ↔ README ↔ skill markery | produkce, test v pytest |
| MCP surface | 5 toolů, jednotný response kontrakt | produkce |

---

## 3. Transfer matrix

| # | Aktivum | Potřeba v lichess pipeline | Typ transferu | Úsilí | Riziko |
|---|---|---|---|---|---|
| A1 | Abstention kontrakt (`matched/reason/count/results`) | `unclassified` už existuje, ale nemá jednotný response shape | **kontrakt 1:1** | nízké | nízké |
| A2 | `data_version` + SHA-256 | měření patternů nemá hash datasetu ani knihovny | **kontrakt 1:1** | nízké | nízké |
| A3 | Drift guard | ID v kódu vs docs vs schema vs testy se rozcházejí | **vzor + test** | střední | nízké |
| A4 | Freshness guard | pattern store / cache může být stale | **vzor** | nízké | nízké |
| A5 | Měřená komprese (bytes/tokens + hash) | `compressibility_validator` je falešný MDL | **metodika** | střední | střední |
| A6 | MRR/Prec@3/Recall@5 + qrels | chybí external validity patternů (E4) | **metodika** | vysoké | střední |
| A7 | RRF fúze | řazení lekcí z více evidenčních kanálů | **algoritmus** | střední | střední |
| A8 | BM25 nad popisy patternů | agent-facing `pattern_search` | **algoritmus + kontrakt** | střední | nízké |
| A9 | MMR diverzita | složení reportu (top-3 distinct lekce) | **algoritmus, jen po měření** | nízké | střední |
| A10 | Malý korpus B1-B5 | CI, shrinkage, tokenizace, RRF k | **metodika** | nízké | nízké |
| A11 | Dense embeddings | sémantické hledání patternů | **NEPŘEBÍRAT** | - | vysoké |
| A12 | LLM v detection path | vysvětlení | **NEPŘEBÍRAT** | - | vysoké |

---

## 4. Tři kontrakty, které se mají převzít doslova

### 4.1 Abstention

`mcp-retrieval` vrací při nulovém překryvu:

```json
{"matched": false, "reason": "no_token_overlap", "count": 0, "results": []}
```

a v README explicitně popisuje předchozí chybu: „dřív vracel GT-001, GT-002, GT-003 se skóre ~0,032 — tedy sebevědomě vypadající šum.“

To je **identický failure mode** jako nekalibrovaná `confidence` v pattern_detectoru. Lichess `unclassified` je správná myšlenka, ale nemá jednotný strojový kontrakt. Návrh: sjednotit na

```json
{
  "status": "matched" | "unclassified",
  "reason": null | "quiet_positional" | "forcing" | "capture" | "evidence_gap",
  "pattern_id": null | "K5",
  "strength": 0.0,
  "evidence": [],
  "data_version": {"dataset_sha256": "...", "pattern_lib_sha256": "..."}
}
```

**Přínos:** LLM agent nemůže omylem citovat pattern, který není matched. To je přesně ten typ guardu, který `mcp-retrieval` už řeší.

### 4.2 Data identity

`gt_stats().data_version` vrací `entries`, `rules`, `source_version`, `dataset_sha256`, `rules_sha256`, `loaded_at`. README říká: „Každé měřené číslo v tomto repu má být uváděno s tímto hashem.“

Lichess měření dnes uvádí „259 dedup her, 2137 flagged tahů“, ale bez hashe cache a bez verze pattern knihovny. Návrh: každý measurement JSON a každý coaching report nese

```json
{
  "dataset_sha256": "...",
  "pattern_lib_sha256": "...",
  "code_commit": "...",
  "n_games": 259,
  "n_moves": 2137,
  "metric": {"matched": 375, "unclassified": 1762}
}
```

**Přínos:** reprodukovatelnost a možnost říct „toto číslo platí pro tento snapshot“, ne „někdy dřív to bylo 17,5 %“.

### 4.3 Drift guard

`mcp-retrieval` má `python -m mcp_retrieval.drift` a `tests/test_drift.py`, které porovnávají JSONL, meta, kanonický dokument, README a skill markery. Selhání = exit != 0.

Lichess má přesně tento problém: baseline knihovna definuje 15 ID, `PatternDetector` má 14 detektorů (`I` je `manual_only`), dokumentace mluvila o 17 patternech. Bez drift guardu se tato čísla rozcházejí tiše.

Návrh `python -m lichess_analyzer_mcp.drift`:

| Kontrola | Zdroj A | Zdroj B |
|---|---|---|
| ID množina | `PatternLibrary.load_baseline()` | `docs/CANDIDATE_PATTERNS_*.md` |
| ID množina | `PatternLibrary.load_baseline()` | `schemas/*.json` enumy |
| Detektory | `_detect_*` metody | ID v knihovně |
| Verze | `COMPACT_JSON_FOR_LLM.md` | `schemas/single_game_v2_compact.json` |
| Čísla | README | `results/*.json` |

**Přínos:** eliminuje třídu chyb, kterou jsem našel při psaní metodologie, a je to levné (jeden test + jeden CLI modul).

---

## 5. Konkrétní návrhy

### T1 — Provenance blok (P1, nízké úsilí)

Převzít `data_version` shape. Acceptance: každý `PatternMatch` a každý measurement JSON má `dataset_sha256`, `pattern_lib_sha256`, `code_commit`, `n`. Test: report bez těchto polí neprojde schema validací.

### T2 — Skutečná komprese místo proxy (P1, střední úsilí)

Současné `compression_ratio = total_moves / (10 + 2*evidence)` saturuje. Převzít **měřicí disciplínu** z `compression_comparison.json`: změřit bytes a tokeny před/po na fixním datasetu s hashem.

Dvě možnosti:

- **Minimální:** přejmenovat na `coverage_score`, odstranit z `confidence`.
- **Správná:** dvoučlenná MDL na pattern eventech:
  ```
  L_total = L(model) + L(data | model)
  L(model) = tokeny definice patternu + tokeny výjimek
  L(data | model) = -sum log2 P(event | model)
  ```
  Reportovat `bits_per_event` a `compression_ratio` s `dataset_sha256`.

Acceptance: žádný report netvrdí „confidence“ z proxy; komprese je měřená, ne odvozená z počtu tahů.

### T3 — Drift guard + freshness (P2, střední úsilí)

Zavést `drift` modul a `tests/test_drift.py`. Freshness pro pattern store: reload při změně `(mtime_ns, size)` jako v `mcp-retrieval/retrieval.py:243-264`.

Acceptance: `python -m lichess_analyzer_mcp.drift` exit 0 na konzistentním repu; test padá při přidání ID jen do kódu nebo jen do docs.

### T4 — RRF pro řazení lekcí (P2, střední úsilí)

Použít RRF **jen na ranking**, nikdy na admission. Kanály:

1. rank podle `lift`
2. rank podle `cp_loss`
3. rank podle `frequency` / `N`
4. rank podle `recency` / `drift`

Jejich měření: `k=60` je pro malé N příliš ploché; `k=20` dá +2-3 % MRR. Pro naše N≈15 patternů je rozumné `k ∈ {5, 10, 20}` a grid search na validační sadě.

Acceptance: top-3 lekce v reportu mají vyšší Prec@3 než baseline řazení podle confidence; jinak RRF nezavádět.

### T5 — `pattern_search` MCP tool (P3, střední úsilí)

Agent-facing retrieval nad pattern library a coaching reporty:

```python
pattern_search(query: str, top_k: int = 5) -> {
  "matched": bool, "reason": str | None,
  "count": int, "results": [...],
  "data_version": {...}
}
```

BM25 nad `pattern_name + mechanism + mitigation + evidence`, abstention při nulovém překryvu. To je přímá adaptace `gt_search` na chess doménu a dává LLM agentovi kalibrovaný způsob, jak se ptát „jaká lekce platí pro tuto pozici?“.

Acceptance: na 30 ručně kurátorovaných dotazech MRR ≥ 0,65 a žádný výsledek při `matched:false`.

### T6 — qrels pro patterny (P3, vysoké úsilí)

Nejdražší, ale jediný skutečný test E4. Pro 30-50 her označit graded relevanci 0-2: které patterny se na tah vztahují. Poté měřit MRR, Prec@3, Recall@5 stejně jako v `ML_Ops_edukace`.

Acceptance: report má `precision/recall` na held-out hrách, ne jen coverage na trénovacích.

### T7 — Kanonický event tokenizer (P4, střední úsilí)

Před PrefixSpan je nutné sjednotit tokeny. Inspirace B3: `kalibrace/kalibraci` fragmentovalo BM25; v chessu to jsou `SAN` vs `UCI`, `O-O` vs `e1g1`, promoce, en passant.

```
event_token = (pattern_id, phase, color, cp_bucket, is_capture, is_check, piece_type)
```

Acceptance: stejný tah z různých zdrojů (cache, PGN, engine line) dá stejný token; test na 100 tazích.

---

## 6. Co NEPŘEBÍRAT (negativní výsledky)

| Věc | Jejich měření | Proč to nepřenášet |
|---|---|---|
| Word2Vec z nuly | MRR 0,3107 vs 0,7067 | malý korpus, 44,9 % OOV; chess SAN je ještě horší |
| GloVe pre-trained | MRR 0,2607 | doménová slovní zásoba chybí |
| TF-IDF + SVD | MRR 0,5413 | agresivní pro malý korpus |
| MMR λ=0,7 | MRR 0,5987 | diverzita zhoršila ranking; použít jen po měření na report composition |
| LLM v detection path | - | porušuje determinismus (REFACTOR_PLAN) |

**Meta-lekce:** jejich nejsilnější výsledek vznikl z **jednoduchého BM25 + RRF + abstention**, ne z embeddings. To je argument pro naši strategii „deterministické pravidlo + kontrast“, ne pro neuronové rozšíření.

---

## 7. Dopad na metodologii

### 7.1 Originalita

Tyto repozitáře **nezávisle dospěly ke stejnému kontraktu** (abstention + data identity + drift), který v lichess pipeline navrhuji jako `unclassified`. To je silný argument, že nejde o idiosynkrazii, ale o **obecný informačně-vědní pattern**.

Důsledek pro tvrzení o originalitě: `unclassified` **není originální v informační vědě**. Originální je jeho aplikace na chess pattern discovery s FP stropem na dobrých tazích. To je přesnější a obhajitelnější formulace než „unikátní metodologie“.

### 7.2 Efektivita

Jejich výsledky ukazují, že **jednoduché deterministické jádro + poctivá evaluace** poráží složitější modely na malém korpusu. To podporuje naši strategii: nepřidávat patterny, ale zlepšit důkaz. Zároveň varují před dvěma chybami, které máme:

1. **Window truncation** (B2): jejich `content[:4000]` ořezával signál. Náš `context_window` obsahuje jen tahy analyzovaného hráče — stejná bias. Řešení: doplnit tahy soupeře a reportovat coverage.
2. **Malý korpus** (B1/B4): 10 dotazů = 10% swing. Naše N=30 pro admission je na hraně; Wilson CI a shrinkage nejsou volitelné.

---

## 8. Závěr a pořadí

| Priorita | Akce | Proč |
|---|---|---|
| 1 | T1 provenance blok | bez něj jsou všechna čísla neporovnatelná |
| 2 | T2 skutečná komprese | odstraňuje falešné tvrzení v confidence |
| 3 | T3 drift guard | eliminuje tichý rozchod kódu a dokumentace |
| 4 | T4 RRF ranking | zlepšuje report bez zásahu do detekce |
| 5 | T5 `pattern_search` | agent-facing vrstva, přímá adaptace `gt_search` |
| 6 | T6 qrels | jediný skutečný test generalizace |
| 7 | T7 tokenizer | předpoklad pro sekvenční discovery |

**Verdikt:** ano, oba repozitáře jsou vhodný zdroj — ale jako **reference kontraktů a evaluační disciplíny**, ne jako hotové řešení pattern discovery. Nejcennější transfer je levný (T1-T3) a nejdražší (T6) je zároveň ten, který rozhodne o produktovém tvrzení.
