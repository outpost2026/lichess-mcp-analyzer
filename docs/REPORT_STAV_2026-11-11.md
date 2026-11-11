# Stav vývoje a optimalizace — Feynmanovský report

- **Datum:** 2026-11-11
- **HEAD:** `b9401da` (kód na úrovni `7ce7f61` + dokumentace)
- **Navazující dokument:** `docs/REFACTOR_PLAN_2026-11-11.md` (detailní audit a plán)
- **Metoda:** vysvětlit bez žargonu, každé tvrzení doložit, každý odhad označit nejistotou

---

## 1. Co ten systém vlastně dělá

Vezme šachovou partii, pustí na každý tah Stockfish a z čísel udělá tréninkový report.

Jsou na to tři kroky:

1. **Změřit.** Stockfish ohodnotí pozici před tahem a po tahu. Rozdíl se převede na `cp_loss` — kolik setin pěšce hráč ztratil proti nejlepšímu tahu.
2. **Pojmenovat.** Z čísla se stane `blunder` / `mistake` / `inaccuracy` a případně behaviorální pattern („automatické braní“, „panika pod šachem“).
3. **Vyprávět.** Compact JSON 2.0 nebo detailed 1.1; z toho deterministický report, volitelně LLM komentář.

Nejtěžší část není Stockfish. Ten měří dobře. Nejtěžší je, aby stejné číslo znamenalo totéž na začátku, uprostřed a na konci řetězu. A aby se dalo dokázat, že dvě měření jsou srovnatelná.

---

## 2. Diagnóza v jedné větě

> Pipeline umí hru změřit. Ne vždy umí říct, co to které číslo znamená. A neumí vždy dokázat, že stejné zadání dá stejný výsledek.

To není katastrofa. Je to normální stav systému, který vyrostl z prototypu do nástroje. Ale je to přesně ten stav, kdy se nemá stavět SQLite a GUI, dokud se štítky nespraví.

---

## 3. Co funguje a čím to víme

| Vrstva | Stav | Důkaz |
|---|---|---|
| Měření tahem | Funguje | Stockfish 18, depth policy, cache; 18 MCP toolů |
| Klasifikace | Funguje mechanicky | 193/193 fast testů, 7,2 s |
| Compact výstup | Funguje | 2,0 je default; 2,3-4,4 tis. znaků na hru |
| Deterministický report | Funguje | `status`, `partial`, `errors`, `unanalyzed_plies` |
| Pattern library | Existuje | 14 definovaných patternů, 13 aktivních detektorů |
| Reprodukovatelnost | Neúplná | cache klíč `d14n150000` nezná build, hash, threads |
| Význam čísel | Neúplný | phase, confidence, accuracy, king capture |
| Ověření engine vrstvy | Rozbité | 27/28 testů, 1 RED; CI ho maskuje mypy gate |

**Co to znamená prakticky:** analytical core je použitelný. Slabé místo je překlad mezi měřením a významem, ne samotné měření.

---

## 4. Osm děr, které dnes brzdí další vývoj

### 4.1 King capture — pattern S říká něco jiného, než si myslíme

Kód se ptá: „Byl hráč v šachu a obsahuje SAN písmeno `x`?“ To znamená „něco sebral“. Ne „sebral králem“.

Příklad: `Qxd4` v šachu nastaví `king_capture_played = true`, i když král netáhl. Pattern S se pak neaktivuje, protože si myslí, že hráč králem bral.

Horší je, že stejný pattern má druhou implementaci v `pattern_detector.py`, která to dělá správně přes typ figury. Dvě části pipeline tedy mohou o stejné pozici tvrdit opak.

**Náročnost:** S (1-2 dny). **Důsledek:** jedna pravda pro BFS i compact; méně falešných negativů patternu S.

### 4.2 Fáze hry — „endgame“ je jen pořadové číslo

`_detect_phase(ply)` vrátí `endgame` od 51. půltahu. Pozice se 14 figurami na desce je tak „endgame“, protože přišla pozdě.

To není jen kosmetika: pattern R („endgame relaxation“) na tom čísle závisí. Změna definice fáze tedy mění detekci, ne jen popisek.

**Náročnost:** M (3-5 dní včetně testů a dual-runu). **Důsledek:** report bude říkat, jak fázi určil; material-based `chess_phase` bude věcně správná.

### 4.3 Confidence — jedno slovo, čtyři významy

Dnes `confidence` znamená nejméně čtyři různé věci:

- síla rule matchu u jednoho tahu (`cp / 500`),
- podíl her, ve kterých se pattern objevil,
- kompozitní skóre z compressibility validátoru,
- rozptyl cp_loss u opakovaného měření.

Compact z něj navíc odvozuje `sev` (critical/high/medium/low). LLM agent tedy dostane jedno číslo a nemá jak vědět, co znamená.

**Náročnost:** M (3-5 dní). **Důsledek:** tři pojmenované dimenze + kompatibilní alias; `sev` přestane záviset na nejednoznačném čísle.

### 4.4 Accuracy — jmenuje se jako Lichess, ale není to Lichess

Vzorec je `mean(max(0, 100 - cp_loss * 0.15))`. Je to rozumná lokální heuristika. S Lichess accuracy (win-probability based) nemá společného nic než rozsah 0-100.

**Náročnost:** S (1 den na přejmenování a reporty). **Důsledek:** žádné falešné srovnání s Lichess; `accuracy_method` v payloadu.

### 4.5 Quiet blunder — 43 % blunderů nemá pattern

Změřeno na 224 cache souborech s aktuálním detektorem: z 228 blunderů jich 98 (43 %) nemá motiv ani pattern, medián `cp_loss` 384.

Není to náhoda. `_single_game_candidate` umí jen braní, šach, endgame, předchozí chybu nebo taktický motiv. Tichý poziční blunder (Bf4, g3, Na6) neprojde žádnou větví. Detektor je klíč, který má zuby jen na šest konkrétních tvarů.

**Náročnost:** S (1-2 dny na `unclassified` stav) + M/L (2-3 týdny na skutečný pattern s mechanismem). **Důsledek:** LLM dostane explicitní „nevím, proč“ místo prázdna; nový pattern vznikne až s důkazem.

### 4.6 Eval provenance — dvě pravdy vedle sebe

`cp_loss` se počítá jako `best_player - actual_player` z re-searchu nejlepšího tahu. `eval_before` je evaluace rodiče. Invariant `eval_before - eval_after ≈ cp_loss` platí jen tehdy, když `eval_before ≈ best_player`. Právě tam vzniká rozdíl.

Naměřeno: 101/7231 tahů (1,4 %) porušuje invariant; u flagovaných tahů 101/2010 (5,0 %). `FVhqtv1S` ply 89: cached cp 237, fresh cp 168 při stejném depth.

FIX-023 to řeší jen v compactu (eval pole vynechá). Detailed dál publikuje raw dvojici. To je obhajitelný containment, ne root fix.

**Náročnost:** M (3-4 dny na explicitní provenance) + L (součást SQLite). **Důsledek:** žádná „oprava znaménka“, která by byla chybná; každé číslo bude mít uvedený původ.

### 4.7 Ověření — zelené číslo, které nic neříká o srdci pipeline

Fast suite: 193/193. Engine suite: 28 testů, 27 prošlo, 1 selhal.

Selhává `TestIDGameQh4::test_analyze_position_qh4_rank1`: čeká `f2c2`, Stockfish 18 při `multipv=1` vrací `b1h7`; při `multipv=3` je `f2c2` první linie. Test tedy tvrdí konkrétní tah závislý na buildu a režimu, ne na skutečnosti.

A je maskovaný dvakrát: lokálně `--ignore`, v CI je pytest krok za RED mypy gate (77 chyb/16 souborů).

**Náročnost:** S (1-2 dny). **Důsledek:** důvěryhodné CI; engine vrstva má vlastní job s pinnutým buildem.

### 4.8 Compact patterns_meta — prázdný list bez důvodu

Detailed 1.1 má `patterns_meta` povinné. Compact 2.0 ho neumí (`additionalProperties: false`). Když jsou patterny prázdné, LLM nepozná, zda žádné nejsou, nebo byly potlačeny.

**Náročnost:** S (1 den). **Důsledek:** každý prázdný list má reason; kontrakt 2.1.

---

## 5. Náročnost a důsledky navrhovaných kroků

Škála: **S** = 0,5-2 dny, **M** = 3-10 dní, **L** = 2-4 týdny, **XL** = měsíc a víc. Odhady jsou pro jednoho vývojáře, bez regresí, s testy průběžně; nejistota ±40 %, u L a XL nižší confidence.

| Krok | Co se změní | Náročnost | Čas | Důsledek při provedení | Důsledek při odkladu |
|---|---|---|---|---|---|
| A. Opravit engine test + split CI | stale expectation pryč, fast/engine joby | S | 1-2 dny | CI znovu něco dokazuje | každé „zelené“ číslo je neúplné |
| B. Board facts + dedup patternů | jedna implementace S/B/J/R | M | 3-5 dní | BFS a compact si neodporují | dva výstupy, dvě pravdy |
| C. `unclassified` blunder | pattern_status + reason | S | 1-2 dny | LLM ví, co neví | 43 % chyb bez vysvětlení |
| D. Fáze, confidence, accuracy | `phase_method`, dimenze, `heuristic_score` | M | 5-7 dní | štítky odpovídají obsahu | sémantický dluh roste s každým konzumentem |
| E. Eval provenance | `cp_loss_basis`, `eval_source`, `analysis_run_id` | M | 3-4 dny | žádná falešná narativa | 5 % flagů s rozpornými čísly |
| F. Compact 2.1 | `patterns_meta`, `phase_method`, `unclassified` | S | 1 den | prázdný list má důvod | LLM hádá |
| G. SQLite + verzované runy | games, runs, evaluations, occurrences | L | 3-4 týdny | reprodukovatelnost a srovnání | storage zamrazí současné nejasnosti |
| H. GUI read-only | Streamlit nad service vrstvou | L | 3-4 týdny | použitelnost bez duplikace logiky | ruční CLI workflow |
| I. LLM strategie | provider chain, budget, validace, fallback | M | 8-12 dní | výpadek providera není výpadek produktu | křehká závislost |
| J. Pattern lifecycle | candidate → validated s kritérii | M/L | 2-3 týdny + ongoing | patterny jsou důkazy, ne dojmy | kvantita bez kvality |

**Kumulativně:** Fáze 0 (A-F) cca 7-9 dní. Do použitelného GUI cca 2-2,5 měsíce. Odhady nezahrnují placené LLM experimenty ani lidské značení vzorku.

---

## 6. Proč právě v tomto pořadí

Každý krok snižuje nejistotu pro krok následující:

1. **A** vrací důvěru v měření. Bez ní nelze poznat, zda zlepšení není jen flake.
2. **B + C** zavádějí jednu pravdu a explicitní mezery. Nejdražší chyba je mlčet, když detektor neví.
3. **D + E** dávají číslům význam a původ. Teprve teď má smysl je ukládat.
4. **F** dokončuje kontrakt pro LLM.
5. **G** ukládá až ověřenou sémantiku. SQLite je multiplikátor: správná data zrychlí, špatná zamrazí.
6. **H** staví GUI nad hotovou service vrstvou, ne nad kopií logiky.
7. **I** řeší výpadky a náklady, až když je výstup sám důvěryhodný.
8. **J** kalibruje patterny proti ground truth, ne proti dojmu.

---

## 7. Tři věci, které bych udělal hned

1. **Opravit engine test a rozdělit CI** (S, 1-2 dny). Je to nejrychlejší způsob, jak získat zpět pravdivé „zelené“.
2. **Board facts + dedup + `unclassified`** (M, 4-6 dní). Nejvyšší poměr přínosu k námaze: odstraní dvě pravdy a dá LLM čestnou odpověď „nevím“.
3. **Potvrdit rozhodnutí D1-D6** (hodina). Odblokuje 5-7 dní práce, která by jinak čekala.

---

## 8. Co vědomě nedělat

- **Nezačínat SQLite a GUI před Fází 0.** Uloží a zobrazí současné nejasnosti.
- **Neopravovat FIX-023 převrácením znaménka.** Diagnóza „sign flip“ je nepřesná; zavedlo by to novou chybu.
- **Nevymýšlet pattern pro quiet blunder.** Bez mechanismu je to jen nový název pro neznámou věc.
- **Neslibovat Lichess parity accuracy.** Dokud není implementovaná a kalibrovaná.
- **Nepřidávat LLM funkce, dokud není health check a fallback.** Aktuální stav providerů je neověřený.
- **Neoptimalizovat náklady na úkor správnosti.** Levný špatný report je dražší než žádný.

---

## 9. Jak poznáme, že to funguje

Bez metrik a bez pocitu:

1. Každé číslo má jeden význam a payload to říká.
2. Každý blunder má pattern, nebo explicitní `unclassified_reason`.
3. Prázdný pattern list má v compactu důvod.
4. Eval pár, který porušuje invariant, není publikován bez `eval_consistency=false`.
5. Stejný PGN + stejný engine build + stejná konfigurace = stejný `run_fingerprint`.
6. CI má dva joby: fast bez engine a engine s pinnutým buildem; žádný test není tiše vyloučen.
7. GUI je read-only a nevolá engine.
8. Výpadek LLM providera vrátí deterministický report s `status=degraded`, ne prázdno.

---

## 10. Otevřená rozhodnutí

| ID | Otázka | Doporučení | Cena odkladu |
|---|---|---|---|
| D1 | `phase` = segment, nebo chess phase? | obojí: `segment` + `chess_phase` + `phase_method` | pattern R a phase_stats zůstávají nejednoznačné |
| D2 | `confidence` alias, nebo dimenze? | tři dimenze + `confidence_kind`, alias do 3.0 | LLM dál hádá, co `conf` znamená |
| D3 | `accuracy` rename? | `heuristic_score` + `accuracy_method` | riziko falešného srovnání s Lichess |
| D4 | Quiet blunder = pattern, nebo event? | nejdřív `unclassified` event | 43 % chyb zůstává bez popisu |
| D5 | Compact 2.1? | ano, additive | prázdné patterny bez důvodu |
| D6 | Real engine v CI? | samostatný job s pinnutým buildem | CI dál maskuje RED test |

---

## 11. Bottom line

Systém není rozbitý. Je v mnoha místech neoznačený.

To je dobrá zpráva: neoznačené věci se dají označit levněji než přepsat. A špatná zpráva: každý měsíc, kdy se na neoznačená čísla navěsí storage, GUI a LLM, se cena opravy zvyšuje.

Nejlepší investice teď není další feature. Je to **důvěra v čísla**: opravit testy, sjednotit predikáty, pojmenovat významy a přiznat mezery. Teprve pak má smysl stavět SQLite, GUI a pattern lifecycle.
