# 02 Coaching Exemplars — reprezentativní reporty a katalog nálezů

**Datum:** 2026-11-18 | **Autor:** LLM agent (opencode), extrakce z W2 trimmingu | **Status:** AKTIVNÍ
**Účel:** Nahradit 23 `coaching_report_*.md` + 4 opponent dokumenty + 3 pipeline logy (234 KB) jedním souborem (~28 KB) se zachováním všech unikátních technik a měření.

> **DATA-FABRICATION-001 (AGENTS.md §6):** Zdroj pravdy je deterministická vrstva — `data/reports/*.json` a `data/game_cache/{game_id}_{color}_d{...}.json`. Každá `.md` narace níže je **odvozená**. Konkrétní číslo používej jen s ověřením proti JSON/cache. Ostatních ~30 reportů je v `_ARCHIVE/` (P84–P89 soft-delete přes `git mv`).
> **Historické `data/` cesty níže:** `data/` je gitignored a regenerovatelné; některé soubory v working tree po trimu 2026-11-18 chybí. Chápej je jako provenance (game_id + depth), ne jako živý odkaz.

---

## A. Exemplář 1 — deterministický single-game formát (bez LLM)

Plně vloženo z `coaching_report_single_game_HmUBpeoJ_DSV4F.md` (před archivací). Jediný report s čistým [DATA]/[IM] splitem, explicitní data-limitation poznámkou a žádným LLM cascade (tedy bez rizika fabrikace ani leaknutého CoT).

---

# Coaching Report — HmUBpeoJ [DSV4F]

**Typ:** vlastní report (deterministická data, bez LLM cascade)
**Generováno:** 2026-08-02
**Zdroj dat:** `lichess_coaching_single_game` (depth 14, cache Stockfish)

---

## [DATA] Základní info

| Atribut | Hodnota |
|---------|---------|
| Game ID | HmUBpeoJ |
| Výsledek | 1-0 (výhra bílých) |
| Barva | white |
| Zahájení | Borg Defense |
| Celková ACPL | 41.7 |
| Přesnost | ~58.3 % |

## [DATA] Fázový breakdown

| Fáze | ACPL | Chyby |
|------|------|-------|
| Opening | 54.0 | 6 (1 mistake + 5 nepřesností) |
| Middlegame | 0.7 | 0 |
| Endgame | — | data nedostupná (žádné zaznamenané tahy) |

## [DATA] Error klasifikace

- **Blunders:** žádné
- **Mistakes:** 1
  - Ply 17, tah **Ba2** (c4a2)
  - Centipawn loss: **161**
  - Eval: +0.67 → −0.86
  - Win prob: 0.595 → 0.379 (Δ −0.216)
  - Fáze: opening
- **Inaccuracies:** 5 (detaily nejsou v sadě dat)

## [DATA] Pattern detection

Žádné shody (prázdné pole).

## [DATA] BlunderFactSheet — ply 17 (Ba2)

- **Engine linie (top 3):**
  1. Bxd5 Qxd5 — eval −108 cp, win prob 0.349
  2. Ba2 (hraná) — eval −92 cp, win prob 0.371
  3. Ba2 (alternativní) — eval −61 cp, win prob 0.413
- **Legal moves:** 36 celkem
  - Captures: Nxa7, Bxd5, Bxg5
  - King moves: Kd2, Kf1, O-O
  - Checks: Nc7+, Nd6+
- **Board state:** nebyl v šachu; žádné šachující bílé kusy; capture šachujícího kusu možná (Bxd5); king capture možná ani hrána

---

## [IM] Heisman-style analýza

Nejkritičtější chyba: **Ba2 na ply 17** — jediná mistake, Δ eval −161 cp, Δ win prob −0.216.
Typ: taktické přehlédnutí. Engine ukazuje, že výměna **Bxd5** byla dostupná a výrazně lepší (zisk materiálu, evaluace bílým výhodná); tah na a2 střelcem stahuje bílou hru. Časová tíseň: nelze posoudit (data nedostupná).

## [IM] Tři věci, co hráč udělal dobře

1. Middlegame bezchybný — ACPL 0.7, 0 chyb.
2. Žádný blunder za celou partii.
3. Přes slabý opening (ACPL 54) partii dotáhl do výhry 1-0.

## [IM] Jedna věc na zlepšení

V openingu volit rozvíjející/exchange tahy s materiálovým ziskem (Bxd5) místo odtažení střelce na okraj desky (Ba2) — vyhnout se pasivním tahům střelce v Borg Defense struktuře.

## [IM] Tréninková doporučení

1. Taktika: vyhledávání výměn (Bxd5 vs. …d5) a materiálových zisků v otevřených strukturách.
2. Studium typických plánů Borg Defense pro bílého — reakce na …e5 + …Nf6.
3. Engine review vlastních openingových partií (prvních 15–20 tahů), identifikace opakujících se nepřesných tahů střelcem.

---

*Data limitace: inaccuracy detaily, endgame a časové informace nebyly v datové sadě k dispozici.*

---

## A2. Exemplář 2 — dual-perspective hSNR (obě barvy)

Plně vloženo z `coaching_report_NktJfZZy.md` (před archivací). Jediný report, který porovnává obě perspektivy téže partie a ukazuje „blunder timing" jako rozhodující faktor.

---

# IM Coaching Report: NktJfZZy — Pirc Defense (B00) [hSNR dual]

**Datum:** 2026-07-30 | **Perspektiva:** Dual (White+Black)
**Result:** 1-0 (autor vyhral) | **Time control:** 300+3 (Rapid)
**Zdroje:** data/game_cache/NktJfZZy_white_d14.json, NktJfZZy_black_d14.json
**Metodika:** Template 1 — hSNR dual-perspective extension (dual_cache commit ea19336)

---

## [DATA] Dual-perspective comparison

| Metrika | White (autor) | Black (opponent) | Rozdil |
|---------|:-------------:|:----------------:|:------:|
| ACPL | **49.4** | **63.1** | autor lepsi o 13.7 |
| Accuracy | 92.6% | 90.6% | +2.0% |
| Blundy | 3 | 3 | 0 |
| Chyby | 0 | 0 | 0 |
| Nepresnosti | 5 | 4 | +1 |
| Tahu | 37 | 36 | +1 |
| **Avg cp_loss pri chybe** | **380** | **514** | o 134cp horsi opponent |
| **Max cp_loss** | **469** | **700** | opponent ma horsi peak |

### Fazovy breakdown — dual

| Faze | White tahu | White ACPL | White errors | Black tahu | Black ACPL | Black errors | hSNR |
|------|:----------:|:----------:|:------------:|:----------:|:----------:|:------------:|:----:|
| Opening | 10 | 25.3 | 2 inacc | 10 | 17.4 | 0 errors | cerny lepsi |
| **Middlegame** | **12** | **92.4** | **3 bl + 2 inacc** | **10** | **69.8** | **2 bl + 1 inacc** | **cerny lepsi** |
| Endgame | 15 | 15.6 | 1 inacc | 16 | 95.6 | 1 bl + 3 inacc | autor dominant |

**hSNR insight:** Autor vyhral, pritom prohral **obe prvni dve faze** (opening ACPL 25.3 vs 17.4; middlegame 92.4 vs 69.8). Rozhodlo se az v endgame, kde opponent totalne zkolaboval (ACPL 95.6) a autor drzel kvalitu (ACPL 15.6).

---

## [DATA] White blunders (autor, 3)

| # | Ply | Tah | cp_loss | Eval pred | Eval po | Fen |
|---|-----|-----|---------|-----------|---------|-----|
| 1 | 33 | **Qd2** | **371** | +146 | -223 | 2bq1rk1/4nppp/p3p3/1rp1P1N1/5n2/1BP5/PP1BQ1PP/R4RK1 w - - 1 17 |
| 2 | 37 | **Ng5** | **469** | +278 | -180 | r1b1r1k1/2qn1p1p/pp2pp2/1BpnN1p1/7N/3B4/PPP2PPP/R2Q1RK1 w - - 1 19 |
| 3 | 43 | **Qg5** | **300** | -192 | -484 | r1b2rk1/3n1p1p/pp2pn2/q3N1pQ/3N4/1B6/PPP2PPP/R4RK1 w - - 1 22 |

### Pattern: "Piece placement — dama/jezdec bez opory"
Vsechny tri autorské blundery maji stejnou strukturu: figura jde na pole bez opory. Qd2 blokuje vlastni figury. Ng5 nema outpost (h6 ho zene). Qg5 je desperace. **Neni to nahoda — autor v midgame systematicky preceňuje stabilitu svych figur.**

---

## [DATA] Black blunders (opponent, 3)

| # | Ply | Tah | cp_loss | Eval pred | Eval po | Fen |
|---|-----|-----|---------|-----------|---------|-----|
| 1 | **32** | **Bxe5** | **343** | -189 | +146 | 2bq1rk1/4nppp/p3p3/1rp1b1N1/5n2/1BP5/PP1BQ1PP/R4RK1 b - - 0 16 |
| 2 | **34** | **Rad8** | **498** | -223 | +201 | 2bqr1k1/4nppp/p3p3/1rp1P1N1/1n6/1BP5/PP1BQ1PP/R4RK1 b - - 2 17 |
| 3 | **64** | **Rd6** | **700** | -547 | +224 | 5rk1/3P4/p2R4/1p6/8/nP1R4/P3r1PP/7K b - - 1 32 |

### hSNR point: blunder timing

| Poradi | Blunder | cp_loss | Kdo | Eval kontext |
|--------|---------|---------|:---:|:-----------:|
| 1 | ply 32 Bxe5 | 343 | OPP | otaci hru z -189 → +146 ve prospěch autora |
| 2 | ply 33 Qd2 | 371 | AUT | okamzite vracia dar zpet |
| 3 | ply 34 Rad8 | 498 | OPP | znova dava autorovi sancu |
| 4 | ply 37 Ng5 | 469 | AUT | zase nevyuziva |
| 5 | ply 43 Qg5 | 300 | AUT | treti chyba v rade, jde do -484 |
| 6 | **ply 64 Rd6** | **700** | **OPP** | **fatalni — autor matuje do 4 tahu** |

**hSNR key insight:** Autor i opponent dali po 3 blunderech, ale rozhodlo poradi. Opponent udelal **posledni** blunder (ply 64, nejvetsi — 700cp). Autor uz zadny blunder nepridal a okamzite trestal. V hSNR terminologii: **opponent mel posledni error v chain of mistakes.**

---

## [DATA] Cross-phase hSNR analysis

### Sekvence: ply 32-43 (6 blunderu v 12 tazich)

```
ply 32: OPP blunder (+343) → autor +146
ply 33: AUT blunder (-371) → autor -223
ply 34: OPP blunder (+498) → autor +201
ply 35: AUT good (Nd5)    → autor +239
ply 37: AUT blunder (-469) → autor -180
ply 43: AUT blunder (-300) → autor -484
```

Tato sekvence je **IM typicka**: autor dostane sanci (opponent chyba), pak ji okamzite vrati vlastni chybou. Tento "ping-pong" se opakuje trikrat. Kdyby autor alespon jednou zkonsolidoval misto force, mohl hru rozhodnout driv.

---

## [IM] Heisman-style: chybovy chain

### Critical pattern: "Middlegame impulsivity"

| Problem | Dukaz |
|---------|-------|
| Opening ACPL 25.3 | solidni, zadny velky problem |
| **Middlegame ACPL 92.4** | **kriticky — 2.5x horsi nez opponent (69.8)** |
| Endgame ACPL 15.6 | excelentni — opponent 95.6 |

**Heisman:** "Tva nejvetsi slabina je midgame decision-making s iniciativou." Kdyz mas vyhodu (+1..+2), misto konzolidace volis forcing tahy (Ng5, Qg5). Kdyz mas nevyhodu, neumis jeste rozpoznat, ze je cas na obranu.

### Konkretni pattern: "Blocking queen" (Qd2 ply 33)

**Pozice:** +146, dama na d1, strelec na b3, jezdec na g5. Spravne: Qe2 (vyvoj + hrozba na e6) nebo prep. Qg4 (utok na g7). Realita: Qd2 — blokuje vlastni figury.

### Konkretni pattern: "Floating knight" (Ng5 ply 37)

**Pozice:** +278, jezdec na f3, dama na e2, vez na e1. Spravne: konsolidace (g3/Be3). Realita: Ng5 — jezdec bez opory na g5, po h6 napaden.

### Proč autor vyhral, kdyz hral horsi midgame?

Odpoved: **Opponent zkolaboval driv.** Autor mel ACPL 49.4 (solidni), opponent 63.1 (horsi). I kdyz middlegame autora byl 92.4, opponent v endgame dal 95.6 — a autor uz nechyboval. V hSNR terminologii: **autor mel lepsi "error resistance" v critical momentu (ply 64+).**

---

## [IM] Treninkova doporuceni — dual perspective

1. **Midgame konsolidace** (nejdulezitejsi): Vsechny 3 blundery jsou "figure placement without support" — dama/jezdec na pole bez opory. **Puzzle theme:** "When ahead — consolidate, don't force."

2. **Blunder chain detection**: 3x autor dostal sanc a 3x ji vratil. Trenink: **po opponentove chybe — pause 5 sec, check jestli tah neni chyba.** Heisman: "After opponent's mistake, assume you're still losing."

3. **Endgame conversion** (co jiz funguje): ACPL 15.6 je vyborny. Pokracovat v treninku endgame techniky, protoze prave zde se rozhoduje.

4. **hSNR awareness**: Author nema problem s kvalitou samotnou (ACPL 49.4 je slusny). Ma problem s **reakci na opponentovy chyby** — impulzivni odpovedi misto konsolidace. **Trenink:** V pozici +eval hledej nejprve "tichy tah", az pote forcing.

---

## Appendix: Critical moments timeline — dual

| Ply | Kdo | Tah | Eval swing | Kumulativni dopad |
|-----|:---:|-----|:----------:|:----------------:|
| 1-20 | W | Bg5, Bxf6 | -88 | autori opening ACPL 25.3 vs cerni 17.4 |
| 23 | W | e5 (inacc) | -72 | push |
| 27 | W | c4 (inacc) | -82 | push |
| **32** | **B** | **Bxe5 (BL 343)** | **+335** | **prvni velka sance** |
| **33** | **W** | **Qd2 (BL 371)** | **-369** | **sance zahozena** |
| **34** | **B** | **Rad8 (BL 498)** | **+424** | **druha sance** |
| 35 | W | Nd5 | +38 | spravna reakce |
| **37** | **W** | **Ng5 (BL 469)** | **-458** | **druha sance zahozena** |
| **43** | **W** | **Qg5 (BL 300)** | **-292** | **desperace** |
| **64** | **B** | **Rd6 (BL 700)** | **+771** | **posledni chyba — rozhoduje** |
| **65** | **W** | **h6+** | **+306** | **okamzita kapitalizace** |
| 67-73 | W | Rf8+, Rxg8+, Qc8+, Qxd8# | →MATE | ciste dokonceno |

---

### Zaver — hSNR

Tato hra je ucebnice chain-of-mistakes timing. Autor i opponent dali po 3 blunderech. Opponent mel vetsi peak cp_loss (700 vs 469) a **jeho blunder prisel jako posledni.** Autor v rozhodujicim momentu nechyboval. hSNR pouceni: **Neni dulezite kolik chyb udelas, ale jestli tva posledni chyba prijde driv nez souperova — a jestli umis potrestat tu jeho.**

*Report generated by coaching report pipeline (dual cache, depth 14) + IM-level reasoning. Zdroje: NktJfZZy_white_d14.json, NktJfZZy_black_d14.json. Template 1 — hSNR dual extension.*

---

## B. Další techniky — 1 odstavec + odkaz na deterministický zdroj

| Technika | Reprezentativní zdroj (před archivací) | Deterministický zdroj pravdy |
|---|---|---|
| **Autorova perspektiva + per-game→aggregate** (4 prohry; `Cm02bEZC` 8 koncovkových blunderů, c6 4081 cp, Kg4 2151 cp, Ke3 1772 cp; autor průměr ACPL 78.7 vs opponent 26.9; Silman imbalance, P0–P1 priority) | `coaching_report_author_4losses.md` | `data/game_cache/{k9a1IXvp,G40ssnlG,8jqLVD9c,Cm02bEZC}_*_d12.json` |
| **Cross-game N=20 + diagnosis** (Systeq ACPL 44.66, 19/38/114, O 40 %/10, B 17 %/14, fáze 25.86/52.68/50.95; severity×frequency ranking, Vienna Max Lange leak) | `coaching_report_cross_game_Systeq_20260901_072548.md`, `coaching_report_diagnosis_Systeq_20260901_072636.md` | `data/reports/cross_game_Systeq_20260901_072548.json` |
| **Cross-game N=20 (amatér)** (sladekkule ACPL 64.98, 27/53/122, B 19/20, fáze 44.07/80.09/63.87; 9 detekovaných patternů) | `coaching_report_cross_game_sladekkule_20260901_075718.md` | `data/reports/cross_game_sladekkule_20260901_075718.json` |
| **A/B Variant B (N=20 vs N=20)** (ACPL 44.7 vs 65.0 = +45 %; opening 25.86 vs 44.07; B ratio 0.085 vs 0.141; depth drift −8.0; PATTERN_CONF_DROP O 85→40 / B 88→17; TIME_PRESSURE 4/7; „pattern structure skill-invariant") | `coaching_report_Systeq_VariantB_20games_20260901_092817.md`, `coaching_report_sladekkule_VariantB_20games_20260901_100000.md`, `comparison_Systeq_vs_sladekkule_20260901_100000.md` | `data/reports/cross_game_*.json`, `pipeline_Systeq_20260901_091825.log` (v archivu) |
| **Opponent pool + n1/n2 profiling** (N=73: 12W/61L 16,4 %; opponent ACPL 50.1; n2 ACPL 29.4 vs n1 54.2; 6/12 vítězů bez blunderu; O 60 % vs 29 %, C 23 % vs 5 %) | `coaching_report_opponent_pool_73.md` | `data/reports/opponent_pool_pool_101_*.json` (pro N=101) |
| **Anonymous pool** (N=33: G Color as modulator 92 %, 2,75× více blunderů jako White, ACPL 32.5; N=35: A Anonymous effect 85 %, 1,7×, ACPL 32.9, endgame ACPL 39.2) | `coaching_report_anonymous_session_33.md`, `coaching_report_anonymous_session_35.md` | ručně psané, **bez JSON protějšku** — čísla platí jen s N a datem; dvě nezávislé hypotézy, **neslučovat** |

---

## C. Findings catalogue (číslo + zdroj)

| # | Nález | Zdroj |
|---|---|---|
| 1 | `yBgAmaI7` **ACPL 18.92**, accuracy 97.2, 0/1/2, fáze 11.4/25.2/0.0, Bd2 ply29 176 cp. **Autoritativní** — sedí na cache. Ostatní dvě generace (21.3) jsou stale. | `data/game_cache/yBgAmaI7_white_d14.json`; `coaching_report_single_game_yBgAmaI7_20260905_144837.md` |
| 2 | `HmUBpeoJ` Ba2 ply17 161 cp, win prob 0.595→0.379, dostupné Bxd5 | §A výše (DSV4F) |
| 3 | `Cm02bEZC` 8 endgame blunderů, c6 4081 cp; autor ACPL 78.7 vs opp 26.9 | `coaching_report_author_4losses.md` L245–382 |
| 4 | Dual hSNR `NktJfZZy`: 49.4 vs 63.1 ACPL; endgame 15.6 vs 95.6; Rd6 700 cp ply64 → mate do 4 | §A2 výše |
| 5 | Cross-game N=20 Systeq: ACPL 44.66, 19/38/114, O 40 %/10, phase 25.86/52.68/50.95 | `data/reports/cross_game_Systeq_20260901_072548.json` |
| 6 | Cross-game N=20 sladekkule: ACPL 64.98, 27/53/122, B 19/20, phase 44.07/80.09/63.87 | `data/reports/cross_game_sladekkule_20260901_075718.json` |
| 7 | A/B: ACPL 44.7 vs 65.0 (+45 %), opening 25.86 vs 44.07, B ratio 0.085 vs 0.141, flags 4/7 vs 0/7 | `comparison_Systeq_vs_sladekkule_20260901_100000.md` L5–25 |
| 8 | Anomalie: mean 43.3 / stdev 14.6, `PIuXqVx4` 78.4 z+2.41, depth drift −8.0, PATTERN_CONF_DROP O85→40 / B88→17 | `pipeline_Systeq_20260901_091825.log`; `coaching_report_Systeq_VariantB_20games_20260901_092817.md` L26–38 |
| 9 | Opponent pool: n2 ACPL 29.4 vs n1 54.2, 6/12 zero-blunder, O 60 % vs 29 %, C 23 % vs 5 % | `coaching_report_opponent_pool_73.md` L50–59, L105–115 |
| 10 | Anonymous: G 92 %/2,75× White (N=33) vs A 85 %/1,7× (N=35); O 12/33 vs 19/35; endgame 39.2 | `coaching_report_anonymous_session_33.md` L55–86; `_35.md` L16–47, L65–86 |
| 11 | „Winners don't blunder" invariance napříč N=33 / N=73 / N=101 (0 blunderů u vítězů v N=33 i N=73) | `opponent_countermeasures_N2.md`; `coaching_report_opponent_pool_73.md` |

---

## D. Anti-patterny (co se do nových reportů nesmí dostat)

| Anti-pattern | Příklad z archivu |
|---|---|
| Leakovaný chain-of-thought | `coaching_report_single_game_HmUBpeoJ_20260801_222903.md:15–29` — „We need to produce a coaching report…", „Make sure not to invent…" (~45 řádků) |
| Fallback / data dump bez narace | `coaching_report_single_game_6ERH4PMw_20260831_093715.md` — „LLM provider: fallback (data dump)", „No patterns detected.", „LLM unavailable after cascade." + echo promptu |
| Placeholder narace | `coaching_report_cross_game_sladekkule_20260901_075718.md`, `...cross_game_Systeq_072548.md`, `...diagnosis_sladekkule_075725.md` — „Hra ? v zahájení ?, ACPL ?.", „Žádný blunder — chyby jsou nepřesnosti" přestože report uvádí 27/19 blunderů |
| Stale čísla oproti cache | `yBgAmaI7` 21.3 ve dvou generacích vs cache 18.923 |
| „Žádná data" výplň | `pool_101` ×2 („Rozdělení podle fáze … není k dispozici"), `nsMOkOhc`, `bbJRWReS` |
| Sebepochvala místo důkazu | „Strengths: Report postaven na Stockfish … bez halucinace" |

---

*Komprese: 31 zdrojových souborů / 234 KB → tento soubor. Ponechané techniky: deterministický [DATA]/[IM] formát, dual hSNR, autorova perspektiva, cross-game N=20, A/B Variant B, opponent_pool, anonymous pool. Vše ostatní v `_ARCHIVE/`.*
