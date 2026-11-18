# Srovnani Systeq (1935 rapid) vs sladekkule (1185 blitz) — Variant B

**Metodika:** Stejny pipeline N=20, Stockfish d12, diagnose+match_patterns, Python anomaly log. Srovnatelny pocet her, rozdil TC: Systeq rapid 10+0, sladekkule blitz 3+0 (rapid fallback neuplatnen — recent 20 = blitz).

| Metrika | Systeq | sladekkule | Delta | Interpretace |
|---|---|---|---|---|
| Rating | 1935 rapid | 1185 blitz / 1530 rapid | -350/-750 | Experienced vs amater |
| Rekord 20h | 13W7L 65% | 7W13L 35% | -30% | Winrate koreluje s ACPL |
| ACPL total | 44.7 | 65.0 | +20.3 (+45%) | Hlavni gap |
| Blundry/mistakes/inacc | 19/38/114 | 27/53/122 | +42%/+39%/+7% | Chyby exponencialne |
| Opening ACPL | 25.86 | 44.07 | +18.2 (+70%) | Nejvetsi kvalitativni rozdil |
| Middlegame ACPL | 52.67 | 80.09 | +27.4 (+52%) | Obe slabe, amater katastrofa |
| Endgame ACPL | 50.95 | 63.87 | +12.9 | Mene koncovek u sladek (125 vs 248 tahu) |
| Nejlepsi hra | 12.5 (KZX6) | 31.7 (eAyN) | +19 | Strop experta vyssi |
| Nejhorsi hra | 78.4 (PIuX) | 118.9 (BJUK) | +40 | Variance amatéra vetsi |
| Leaky opening | Vienna 16/3h | King's Pawn 28/5h (Head 11, Vienna 11, Damiano 9) | — | Oba 1.e4, jina veta |
| O panika | 85% 10/20 | 88% 12/20 | +2 | Univerzalni |
| B grab ratio | 0.085 (14/164) | 0.141 (19/135) | +65% | Amater bere slepe casteji |
| B freq | 14/20 | 19/20 | +5 | Takmer kazda partie |
| C tunneling | 71% 6/20 | 74% 7/20 | +1 | Stejne |
| Q+Q2 resilience | 6+3=9 her | 5+5=10 her | +1 | Oba houzevnati |
| Nove patterny | — | J impulsive block, I2 gift | — | Jen u amatéra (<1300) |
| Cas | 4/7 flag (57%) | 0/7 flag, 8x mate | — | Blitz konci matem, rapid casem |

**Zaver:** Chybova struktura je **kvalitativne stejna** (O,B,C,R,Q/Q2) pres 750 bodu rozdilu — rozdil je **kvantitativni**. Amatér navic pridava J/I2 a ma derave zahajeni (44 vs 25 ACPL). Oba potrebuji stejnou terapii (3s pauza, flat eval alarm), ale sladekkule navic repertoar zuzeni a check-response drill. Dokazuje ze patterny jsou skill-invariantni, jen mirě se meni.

**Doporučeni:** Spolecny trenink: 15min O/B drill, pak rozdelit — Systeq Vienna, sladekkule Damiano+King's Head.
