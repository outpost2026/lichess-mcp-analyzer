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
