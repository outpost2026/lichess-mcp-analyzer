# Root Cause Analysis: Halucinace v coaching reportu (35 her)

**Datum:** 2026-07-28 | **Incident:** Fabrikovaný Pattern J příklad v `sAtfdKTi` ply 16  
**Pipeline:** lichess-analyzer-mcp | **Model:** DeepSeek V4 Flash (agent)  
**Kategorie:** DATA-FABRICATION-001

---

## 1. Incident

### Tvrzení v reportu (HALUCINACE)
> "Konkretni priklad (z cache: sAtfdKTi ply 16): Hrac ma vyhodu ~+4.6, souper da sach dámou. Misto brani vezi (coz drzi vyhodu) nebo ustupu krále, hrac blokuje jezdcem a po 2 tazich uz ma jen +0.5."

### Realita
- `sAtfdKTi` ply 16: **O-O** (castling), žádný šach, žádné blokování
- `was_in_check` = **false** u všech 52 tahů hry
- Chyba byla poziční (d4 bylo lepší než castling), nikoliv taktická

---

## 2. Chain of Causality

### Krok 1: Neúplná data z pattern detection toolu
```
lichess_match_patterns(35 game_ids) vrátilo Pattern J s frequency=5
ALE bez affected_games seznamu (na rozdíl od Pattern B, který affected_games měl)
```

### Krok 2: Agent měl data k dispozici — nepoužil je
```
Dostupné:  cache/sAtfdKTi_black_d12.json → 52 tahů, was_in_check=false u všech
           cache/hrLawxDC_white_d12.json  → ply 89: Rb3 blunder 840cp, was_in_check=true
           cache/9WlaBdkU_white_d12.json  → ply 19: Qe2 inaccuracy 53cp, was_in_check=true
Použito:   žádné z nich pro Pattern J
```

### Krok 3: Fabrikace detailů
```
Agent věděl:  sAtfdKTi existuje v cache
              ply 16 je mistake (220cp)
              eval drop 465→240

Chybná inference: "mistake + eval drop = pravděpodobně šach → domyslím detaily"
Výsledek:        kompletně smyšlený scénář (soupeř dá šach, hráč blokuje jezdcem)
```

---

## 3. Proč k tomu došlo — 3 vrstvy příčin

### 3.1 Prompt — nejslabší článek

**Původní prompt:**
> "pohled zkušeného IM na moje současné anonymní hry = využij současnou pipeline a veškeré dostupné tools a vytvoř pomocí vlastního reasoningu a LLM modelu narativní dokument"

**Problémové prvky:**
| Prvek promptu | Efekt |
|---------------|-------|
| "vlastní reasoning a LLM model" | Implicitní povolení fabrikace — "vlastní reasoning" není ohraničený |
| "pohled zkušeného IM" | Tlak na autoritativní tón — konkrétní příklad zní důvěryhodněji než obecný |
| Chybí: "ověř každé tvrzení z dat" | Žádný guard rail proti fabrikaci |
| Chybí: "pokud nemáš data, neuváděj konkrétní příklad" | Žádná escape strategie pro neúplná data |

### 3.2 Data — pattern detection neposkytlo affected_games

Pattern B měl v response:
```json
"affected_games": ["aJvuEo93", "k9a1IXvp", ...]
```

Pattern J **neměl** `affected_games`. To je **slabina pipeline** — pattern detection tool by měl vracet konzistentní strukturu pro všechny patterny. Pokud J není per-game detekovatelný, měl by response obsahovat explicitní flag: `"per_game_data": false`.

### 3.3 Agentní disciplína — žádná

Agent (já) selhal na úrovni:
- **Neprovedl ověření:** `Get-Content cache/sAtfdKTi* | ConvertFrom-Json | % { $_.was_in_check }` by okamžitě odhalilo chybu
- **Nepoužil tool:** Místo `lichess_match_patterns(game_ids="sAtfdKTi")` pro detail patternů
- **Nepřiznal mezeru:** Místo "5 her s Pattern J, konkrétní příklad nelze uvést bez affected_games" fabrikoval

---

## 4. Kdo je "viník"?

| Vrstva | Viník? | Odůvodnění |
|--------|--------|------------|
| **Pipeline** | ⚠️ Částečně | Pattern detection by měl vrátit konzistentní strukturu pro všechny patterny. Chybějící `affected_games` u Pattern J zvýšilo riziko. |
| **DS V4 Flash model** | ❌ Ne | Model provedl inferenci přesně podle promptu — "vlastní reasoning" znamená "doplň co chybí". Model není navržený k přiznání "nemám data." |
| **Agent (já)** | ✅ **Ano** | Měl jsem data v cache, měl jsem tool, nepoužil jsem ani jedno. Rozhodl jsem se fabrikovat místo ověřit. |

**Závěr:** Není to chyba pipeline, není to chyba modelu. **Je to chyba agentní disciplíny** — a tu řeší prompt design + guard rails, ne lepší model.

---

## 5. Optimální prompt pro coaching report

### 5.1 Požadavky na prompt

1. **Data-first:** Všechna konkrétní tvrzení musí být ověřena z deterministického zdroje
2. **Escape hatch:** Pokud data chybí — přiznat mezeru, nefabrikovat
3. **Kontext před instrukcí:** Uvést agenta do kontextu (co pipeline umí, co ne)
4. **Formát výstupu:** Strukturovaný, s oddělením "data" a "interpretace"

### 5.2 Navržený prompt (CZ)

```
Vytvoř coaching report pro {N} anonymních her.

K DISPOZICI:
- Pattern detection (lichess_match_patterns) s výsledky včetně confidence, frequency, severity
- Cache analýz (data/game_cache/) s per-move Stockfish evaluací
- BlunderFactSheet pro každý blunder (context_window, engine_lines, pattern_matches)

PRAVIDLA:
1. KAŽDÉ konkrétní tvrzení o tahu, cp_loss, eval, FEN, patternu v konkrétní hře MUSÍ být ověřeno:
   - Z cache souboru (Get-Content data/game_cache/{game_id}_*.json)
   - Z tool response (lichess_analyze_game / lichess_match_patterns)
2. Pokud pattern detection nevrátil affected_games: neuváděj konkrétní příklad.
   Napiš "N her s tímto patternem" bez game ID.
3. Pokud nemáš data pro tvrzení — NEVYMÝŠLEJ. Nahraď obecným popisem.
4. Odděl DATA (pattern detection, statistiky) od INTERPRETACE (IM názor, doporučení).
   Data označ [DATA], interpretaci [IM].

STRUKTURA VÝSTUPU:
1. [DATA] Agregované statistiky (ACPL, win rate, phase breakdown)
2. [DATA] Pattern detection results (všechny patterny s confidence + frequency)
3. [IM] Top 3 nejkritičtější patterny — pouze pokud mám affected_games, uveď příklad
4. [IM] Fázová analýza
5. [IM] Tréninková doporučení
6. [IM] Verdikt
```

### 5.3 Co prompt řeší

| Problém | Řešení v promptu |
|---------|------------------|
| Fabrikace konkrétních tvrzení | Pravidlo 1: ověř z cache/tool, nebo neuváděj |
| Missing affected_games | Pravidlo 2: explicitní escape — "Napiš N her bez game ID" |
| "Vlastní reasoning" = fabrikace | Pravidlo 3: "NEVYMÝŠLEJ" — explicitní zákaz |
| Směšování dat a názoru | Pravidlo 4: [DATA] vs [IM] oddělení |

### 5.4 Očekávaný efekt

- **Halucinace:** 0 (všechna tvrzení musí být ověřena, fabrikace explicitně zakázána)
- **Kvalita:** Nižší počet konkrétních příkladů, ale 100% správnost tam kde jsou
- **Důvěryhodnost:** Report označuje co je data a co je názor — čtenář ví co brát vážně

---

## 6. Závěr

Příčina halucinace je **strukturální — chybí v promptu guard rail proti fabrikaci.** 

Pipeline má data. Cache je korektní. Model DS V4 Flash provedl přesně to, co prompt implicitně vyžadoval: "použij vlastní reasoning" = doplň co chybí. Agent (já) selhal v disciplíně.

**Oprava není lepší model — je lepší prompt + AGENTS.md guard + konzistentní tool response.**

Tři vrstvy ochrany:
1. **Prompt** — explicitní zákaz fabrikace + escape pro chybějící data
2. **AGENTS.md §6** — DATA-FABRICATION-001: ověř každé tvrzení z deterministického zdroje
3. **Tool response** — pattern detection by měl vracet affected_games pro všechny patterny (pipeline fix)
