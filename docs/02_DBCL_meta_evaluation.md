# DBCL — Meta-Hodnocení (3. pohled, de novo)

**Verze:** 1.0
**Datum:** 2026-07-25
**Autor pohledu:** Tento dokument není rozšířením DBCL, ani kontrolou auditu, ani reprodukcí evening coaching. Je to **třetí nezávislá perspektiva**, která se ptá na rámec, v němž se celá diskuse odehrává.
**Prameny:** Všechny tři artify čteny vcelku, nikoliv pro potvrzení předem dané teze. Závěry, které zde zazní, jsou formulovány jako **rámcové úvahy**, nikoliv jako doporučení k implementaci — k tomu slouží `01_DBCL_unity_synthesis.md`.

> **Poznámka pro čtenáře:** Tento text je záměrně esejistický, ne inženýrský. Pokud hledáte konkrétní implementační kroky, jděte do `01_DBCL_unity_synthesis.md` §8. Tady jde o **proč** a **v jakém rámci**, ne o **co dělat**.

---

## 0. Tři pohledy, tři rámce

Než začnu, je důležité si uvědomit, že tři artify, které mám k dispozici, neleží v jednom epistemologickém rámci — a **jejich vzájemné neporozumění je strukturální, ne obsahové**.

| Artefakt | Rámec | Co je „fakt" | Co je „chyba" |
|----------|-------|-------------|--------------|
| **SRC-1 (DBCL návrh)** | inženýrský | Deterministic data + jejich strukturovaná projekce | Halucinace LLM |
| **SRC-2 (Claude audit)** | inženýrsko-kontrolní | Co je v kódu (řádek po řádku) | Co chybí v kódu, sémantické bugy, neúplnost |
| **SRC-3 (evening coaching)** | didaktický | Stockfish eval + pattern match | Blunder = odchylka od nejlepšího tahu |

Tato různorodost sama o sobě není chyba — je to **odraz skutečnosti, že se v projektu pohybujeme přes tři různé abstrakční vrstvy**: výpočet (Stockfish), kód (Python), jazyk (LLM). Každá vrstva má svou vlastní ontologii.

---

## 1. Axiomata — co musíme přijmout, aby celá diskuse měla smysl

Než se pustím do vlastní analýzy, chci explicitně formulovat **čtyři axiomata**, která podle mého čtení všichni tři autoři (autor DBCL, auditor Claude, autor evening coaching) sdílejí, i když je nikde nezmiňují. Když se tato axiomata zpochybní, celá řeč o halucinacích a DBCL ztrácí půdu pod nohama.

### Axiom 1: Determinismus je epistemologicky primární

**Tvrzení:** Některé výroky o šachové pozici jsou pravdivé nezávisle na tom, kdo nebo co je vysloví. „Krále na d6 dává šach dáma na c5" je buď pravda, nebo ne — Stockfish ji nezkonstruoval, pouze ověřil.

**Důsledek:** Jakákoliv narrace, která tvrdí opak, je chybná. LLM, který řekne „Qf4+ dává šach", lže. Neinterpretuje, lže.

**Problém s axiomem:** Tvrzení „král na d6 je v šachu" je v matematice triviální, ale v **přirozeném jazyce** je to performativní akt — vyslovením věty „X je v šachu" současně tvrdíme, že jsme provedli geometrický výpočet. LLM tento výpočet neprovedl. Tudíž **nevyslovil lež, ale vygeneroval text, jehož sémantická struktura implikuje výpočet, který neproběhl**. To je jemný, ale důležitý rozdíl: nejde o lež, jde o **selhání inference**.

### Axiom 2: Deterministický výpočet a probabilistická inference jsou **různé operace**, ne totéž v různé přesnosti

**Tvrzení:** Výpočet (deterministický) dává stejnou odpověď pro stejný vstup. Inference (probabilistická) dává **nejpravděpodobnější odpověď pro daný kontext**. Tyto dvě operace **nelze zaměňovat**, a to ani v případě, že inference „vypadá" správně.

**Důsledek:** LLM, který správně uhodne, že `Qf4` nedává šach (protože „král je daleko"), nedělal totéž co Stockfish, který to **vypočítal**. Uhodnutí a výpočet jsou různé epistemologické akty.

**Důsledek pro DBCL:** DBCL je pokus o vytvoření **hranice mezi těmito operacemi** — deterministická data na jedné straně, inferenční narrace na druhé. Validátor je kontrola, že inferenční narrace **nepřekročila** hranici zpět do deterministického prostoru.

### Axiom 3: Pravda musí být trasovatelná

**Tvrzení (z autorovy pozice):** Výrok, jehož pravdivost nelze rekonstruovat ze zdrojových dat, **není pravdivý výrok** — je to hypotéza. Autor DBCL toto vyjadřuje odporem k black-box LLM thinking.

**Důsledek:** Pokud LLM řekne „hráč měl vzít Kxc5", nestačí, že to dává smysl. Musí existovat **cesta od výroku zpět k FEN a legal_moves**, kde se ověří, že Kxc5 byl skutečně v seznamu legálních tahů. Tato cesta se v auditu (SRC-2) nazývá „adversarial verification", v DBCL (SRC-1) „Double-Lock Grounding" podle VeNRA. **Jde o totéž: pravda jako trasovatelnost, ne pravda jako konzistence.**

### Axiom 4: Šum je strukturální, ne náhodný

**Tvrzení:** Chyby v systému (detektoru, promptu, LLM) nejsou gaussovské fluktuace kolem správné odpovědi. Mají **systémovou strukturu** — pattern J vždycky selže na `+` v SAN (ne náhodně, ale strukturálně), LLM vždycky inferuje z blízkosti (ne náhodně, ale strukturálně). Strukturovaný šum **nelze eliminovat statistikou**, lze jej **pouze detekovat a blokovat** jeho cestu do výstupu.

**Důsledek:** „Lepší LLM" (Gemini Flash, Claude Opus, GPT-5 Mini) **neřeší** strukturální šum. Řeší statistickou přesnost, což je jiná veličina. F-007 (pattern J) bude existovat i s lepším LLM, protože bug je v detektoru, ne v LLM. Lepší LLM bude **věrněji** narrativizovat chybný pattern J output — což je ironický obrat: **zlepšení LLM může zvýšit důvěryhodnost chybných faktů**.

---

## 2. Kategorický omyl: proč „RAG" není správný label

Tady se zastavím u jednoho aspektu, který považuji za **strukturálně důležitý pro celou diskusi**.

V SRC-3 se autor přiznává, že označení „RAG" je pracovní a možná ne korektní. Má pravdu — a to víc, než tuší. Pojďme rozebrat proč.

### Co je RAG (Retrieval-Augmented Generation)?

Klasická definice:
1. Máte **velkou bázi znalostí** (dokumenty, web, databáze).
2. Na dotaz **vyhledáte** relevantní pasáže (top-k retrieval).
3. LLM **generuje** odpověď s těmito pasážemi jako kontextem.

RAG je tedy **trojice**: báze + retrieval + generování. Klíčová složka je **retrieval** — vyhledání z velké množiny.

### Co se děje v DBCL?

1. Máte **PGN hru** a **Stockfish evaluace**.
2. Deterministické detektory **extrahují** strukturovaná fakta (FEN, is_check, legal_moves, engine_lines, pattern_matches).
3. LLM **generuje** narraci z těchto fakt.

Tady **neprobíhá retrieval**. Co probíhá je **structured fact extraction (SFE)** — deterministické computace produkují strukturovaný JSON. LLM pak narrativizuje tento JSON.

### Proč na záleží

RAG a SFE se liší v **typu neurčitosti**:
- V RAG je neurčitost v **retrieval** (který pasáž je relevantní?).
- V SFE je neurčitost v **generování** (jak převést JSON na narraci?).

V RAG může být LLM „tvůrčí" v tom smyslu, že **hledá** informace, které pak spojuje. V SFE je LLM „překladatel", ne „hledač". Pokud tvrdíme, že LLM „hledá" (RAG rétorika), otevíráme mu prostor pro **inferenční chybu** typu „tahle pasáž je relevantní, i když v ní není" — což je přesně halucinace, kterou pozorujeme.

Když DBCL říká „LLM je překladatel, ne detektor", říká vlastně totéž. Ale to **není** RAG. Je to **překlad ze strukturované reprezentace do přirozeného jazyka**, nikoliv z vyhledané báze.

### Doporučení `[DE-NOVO]`

Přejmenovat „RAG vrstvu" na **SFE vrstvu** (Structured Fact Extraction → Narration) nebo **DBN** (Deterministic Bridge Narration). Tím se:
1. Odstraní RAG rétorika, která matoucím způsobem implikuje retrieval.
2. Zpřesní očekávání: SFE nemá fázi „hledání", má fázi „strukturování".
3. Zpřesní kritéria kvality: SFE selhává na inferenčních chybách v překladu, ne na retrieval miss.

Toto je **doporučení k terminologii, ne k implementaci**. Ale terminologie není neutrální — formuje, jak přemýšlíme o problému. Rétorika RAG vede k řešením typu „větší báze, lepší embedding, více retrieval". Rétorika SFE vede k řešením typu „přesnější schéma, lepší validátor, silnější guard". Druhá skupina řešení je relevantní k problému, první nikoliv.

---

## 3. Informačně-teoretická dekompozice: tři kanály šumu

Tohle je jádro mé analýzy. Vezmu celý systém a podívám se na něj **jako na komunikační kanál** se třemi zdroji šumu.

### 3.1 Klasický pohled

Klasická představa z SRC-1 §1.2 vypadá takto:

```
deterministic data pool
    ↓
[BRIDGE]  ← jedna „hluchá" zóna
    ↓
probabilistic LLM → narration
```

Tento diagram má **jeden box označený jako problém**. Z toho plynou dvě omezení:
- Řeší se jen to, co se dá do boxu vložit (detector + fact sheet).
- Co je **mimo box** (např. detektor samotný), je mimo scope.

### 3.2 Rozšířený pohled: tři kanály

Ve skutečnosti máme **tři oddělené kanály**, každý se svým šumem:

```
                    ┌───────────────┐
                    │   DETEKTOR    │  Šum kanálu 1: sémantické bugy
                    │  (determin.)  │  Příklad: F-007 pattern J
                    └───────┬───────┘
                            │ BlunderFactSheet (strukturovaná fakta)
                            ↓
                    ┌───────────────┐
                    │  KONTRAKT     │  Šum kanálu 2: přenos mezi
                    │  (per-game ↔  │  per-game a aggregate
                    │   aggregate)  │  Příklad: F-008
                    └───────┬───────┘
                            │ finální prompt
                            ↓
                    ┌───────────────┐
                    │   DEKODÉR     │  Šum kanálu 3: inference
                    │    (LLM)      │  Příklad: INC-A halucinace
                    └───────────────┘
                            │
                            ↓
                       narrace
```

### 3.3 Každý kanál má jiný charakter šumu

**Kanál 1 — Detektor (deterministický, ale chybný):**
- Šum je **binární a opakovatelný**: pattern J vždycky selže na `+` v SAN.
- Opravitelný: stačí přepsat podmínku (F-007).
- **Není detekovatelný validátorem na výstupu** (validátor ověřuje narraci, ne fakt, na kterém je narrace postavena).

**Kanál 2 — Kontrakt mezi per-game a aggregate (organizační):**
- Šum je **strukturální a skrytý**: per-game LLM halucinoval, parsování JSONu prošlo, aggregate LLM to cituje jako fakt.
- Opravitelný: explicitní kontrakt, ne důvěra v JSON parse.
- **Není viditelný z jednoho místa** — per-game LLM a aggregate LLM jsou dvě různé inference instance, každá má svůj kontext.

**Kanál 3 — Dekodér (LLM, inferenční):**
- Šum je **statistický a kontextový**: LLM inferuje z proximity, ne z výpočtu.
- Částečně opravitelný: guard-clauses, fact sheet, validátor.
- **Jediný kanál, na který DBCL cílí přímo** (P1 princip).

### 3.4 Co z toho plyne `[DE-NOVO]`

DBCL pokrývá kanál 3 důkladně (P1–P6, BlunderFactSheet, validátor). Audit (SRC-2) doplnil kanál 1 (F-002, F-003, F-007). Ale **kanál 2 (kontrakt per-game ↔ aggregate) zůstává v auditovaném návrhu poddimenzovaný** — F-008 se o něm zmiňuje, ale neobsahuje specifikaci, jak kontrakt navrhnout.

Toto je **3. pohled, který v SRC-1 chybí a SRC-2 jen naťukne**: kanál 2 je **organizační problém**, ne technický. Řešení není v kódu, je v **definici** — co smí per-game LLM produkovat, aby aggregate LLM mohl bezpečně inferovat? Jaký je **informační protokol** mezi těmito dvěma inferenčními agenty?

Bez explicitního protokolu bude každá implementace DBCL v1 obsahovat tuto **skrytou zranitelnost**: per-game halucinace se bude maskovat jako fakt v aggregate. Validátor na výstupu aggregate to nechytí, protože validátor nezná per-game kontext.

### 3.5 Jak by takový protokol mohl vypadat (nástin)

```
PER-GAME LLM OUTPUT CONTRACT (návrh):

Output: JSON object s povinnými poli:
  - critical_moments[]: pole objektů, každý MUSÍ obsahovat:
    - ply: integer
    - blunder_fact_sheet_id: string (reference na BlunderFactSheet v per-game scope)
    - claim_type: enum {descriptive|explanatory|prescriptive}
    - claim_text: string
  - summary: string (samo o sobě NESMÍ obsahovat chess claims,
                    které nejsou v critical_moments[])

VALIDACE per-game výstupu:
  - Každý claim v critical_moments[].claim_text MUSÍ projít
    narrative validatorem (§7 unity doc).
  - summary NESMÍ obsahovat piece-on-square ani check claims.
  - Pokud per-game validace selže, per-game output je ZAMÍTNUT
    a aggregate dostane fallback na raw BlunderFactSheet.

KONTRAKT s aggregate:
  - Aggregate LLM dostane per-game critical_moments[] JAKO
    BlunderFactSheet extension (ne jako text).
  - Aggregate LLM NESMÍ inferovat z critical_moments[].claim_text
    přímo; musí projít zpět přes BlunderFactSheet[].
```

Toto je `[DE-NOVO]` návrh, ne `[SYNTHESIS]`. Vychází z F-008 a z mé analýzy kanálu 2, ale **není ve SRC-1, ani v SRC-2**. Berte to jako hypotézu k další iteraci.

---

## 4. Epistemologie ground truth v deterministickém systému

Tohle je **obecnější úvaha**, kterou považuji za důležitou pro dlouhodobou práci na projektu.

### 4.1 Stockfish není ground truth

V SRC-1 §3.1 se píše „Eval before: +823 cp" jako o faktu. Ale tohle číslo je:
- Výsledek **konkrétní konfigurace**: Stockfish 18 BMI2 @ d14, multipv=1 (dle SRC-3).
- **Změnilo by se** při multipv=3, depth=20, nebo při použití jiného enginu (např. Leela Zero s neuronovou sítí).
- Je to **důkaz v bayesovském smyslu**: s vysokou pravděpodobností je pozice pro bílého vyhraná, ale není to *jistota* (i když v praxi je jistota tak vysoká, že se chová jako fakt).

### 4.2 Tři úrovně „pravdy" v systému

Rozlišuji tři úrovně, které se v datech směšují:

| Úroveň | Co to je | Příklad | Jak s ní zacházet |
|--------|---------|---------|------------------|
| **Pravda-1: Matematická** | Geometricky ověřitelné | Král na d6, Q na c5, společná diagonála → šach | Berte jako fakt, nevyžaduje kontext |
| **Pravda-2: Empirická** | Silný důkaz, ale ne nutně | Stockfish +823 = vyhrané | Berte jako silný důvod, ne jako jistotu |
| **Pravda-3: Inferenční** | Odvozeno z kontextu | Pattern R (endgame relaxation) | Berte jako hypotézu s evidencí |

SRC-3 v noze často směšuje Pravdu-2 a Pravdu-3: „+823 znamená jistou výhru → hráč relaxoval → pattern R". Ale **přechod z Pravdy-2 na Pravdu-3 není deterministický**. Stockfish vám řekne, že pozice je vyhraná; neřekne vám, **proč ji hráč prohrál**. Ten přechod je inferenční, a tudíž zahrnuje pattern matching — což je přesně to, co detektor dělá, a co může selhat (F-007).

### 4.3 Co to znamená pro DBCL

BlunderFactSheet by měl **explicitně rozlišovat** tři úrovně:
- `board_state.*` = Pravda-1 (geometrická)
- `eval_*, win_prob_*` = Pravda-2 (empirická, engine-specific)
- `pattern_matches[]` = Pravda-3 (inferenční, s evidencí)

A guard-clause by měl **zakázat inferenční přechody**, které nejsou v BlunderFactSheetu evidovány. Tj.:

```
Pravidlo: Každý inferenční skok z Pravdy-2 na Pravdu-3
          (např. "eval +823 → hráč relaxoval → pattern R")
          MUSÍ mít pattern_match záznam s evidence řetězcem
          odkazujícím na konkrétní Pravdu-2 hodnotu.

Příklad správné evidence:
  pattern_id=R, evidence="eval_before=823>300 AND phase=endgame"

Příklad NESPRÁVNÉ evidence (generická):
  pattern_id=R, evidence="hráč byl v koncovce s výhodou"
  (Toto nesplňuje podmínku: chybí explicitní prahová hodnota.)
```

Toto opět není `[SYNTHESIS]` — je to můj vlastní návrh. Ale vychází z logiky, kterou považuji za důležitou: **inferenční skoky musí být explicitní, aby mohly být auditovány**.

---

## 5. Tři pohledy na halucinaci

V SRC-1 se halucinace definuje prakticky: „výstup, jehož tvrzení nejsou v BlunderFactSheetu". V SRC-2 se definuje z hlediska auditu: „nepodložený claim". V SRC-3 se definuje z hlediska uživatele: „výstup, který lže o hře".

Přidám **čtvrtý pohled**, informačně-teoretický:

### 5.1 Halucinace jako entropie v inferenčním kanálu

LLM je v podstatě **generativní model** s určitou entropií. Při inference z kontextu C produkuje výstup s rozdělením pravděpodobnosti P(output|C). Halucinace nastává, když:

> P(output|C) je vysoká pro výstupy, které **nejsou v C obsaženy**, ale **kontextově vypadají koherentně**.

To znamená: halucinace není selhání LLM. Je to **selhání inference** v situaci, kdy kontext C je **příliš slabý** na to, aby určil jednoznačný výstup. Pokud je C = „Q na f4, K na b1, hráč zahrál Rdg1, ztráta 950cp", je inferenční prostor pro „Qf4+ dává šach" obrovský, protože **kontext neobsahuje explicitní tvrzení o šachu**. LLM tedy musí „uhodnout", a jeho nejlepší guess je dán naučenými korelacemi (queen blízko = check, velká ztráta = blbý tah, blbý tah po šachu = blok).

Toto je **jádro problému**: kontext C, který DBCL nyní poskytuje, **je příliš slabý na to, aby inference byla jednoznačná**. Přidáním `board_state.was_in_check` se inference prostor **zúží** natolik, že správná odpověď se stane dominantní. Validátor je **druhý bezpečnostní pás**: i kdyby inference selhala, výstup se zachytí.

### 5.2 Z toho plyne důležitý důsledek

**Čím slabší kontext, tím víc halucinací.** Čím silnější kontext, tím méně. Neexistuje žádná „úroveň kontextu", pod kterou by se halucinace zcela zastavily — ale existuje prahová hodnota, nad kterou jsou **výjimečné a odchylitelné**.

DBCL cílí na **dosažení prahové hodnoty**. Ale to **závisí na inferenčních charakteristikách konkrétního LLM**. To, co funguje pro Gemini Flash, nemusí fungovat pro Claude Opus. Empirická kalibrace prahové hodnoty (kolik polí BlunderFactSheetu je potřeba k potlačení halucinací pod X %) je **klíčový budoucí experiment**, který v SRC-1 není specifikován a v SRC-2 není zmíněn.

### 5.3 Halucinace v jiném kanálu

Co je halucinace v kanálu 1 (detektor)? Dle mé definice: **výstup deterministického kódu, jehož propositionální obsah neodpovídá board state**. Přesně toto je F-007: pattern J říká „impulsive check block" (propositionální obsah), ale testuje `+` v SAN (jiný propositionální obsah). To je **detektor halucinace** — a je strukturálně nebezpečnější, protože:
1. Věříme mu, protože je „deterministický".
2. Guard-clause ho nekontroluje.
3. Validátor ho nekontroluje (kontroluje jen narraci).

### 5.4 Co z toho plyne

**Dvě třídy halucinací, dva různé léky:**

| Třída | Příčina | Dostupný lék |
|-------|---------|--------------|
| Inference halucinace | Slabý kontext + inferenční entropie LLM | Silnější kontext (fact sheet), guard-clauses, validátor |
| Detektor halucinace | Sémantický bug v kódu | Audit kódu, pattern guard (unity doc §5.3), `detector_version` |

**Chyba, kterou DBCL v1 může udělat: soustředit se jen na inference halucinace, protože ta je hlasitější (viditelná v narraci), a přehlédnout detektor halucinace, protože je tichá (detector `+` v SAN vypadá legitimně).** SRC-2 F-007 je přesně toto — a můj 3. pohled říká: **toto je pravděpodobně systematičtější problém, než audit sám naznačuje**, protože F-007 je jeden diagnostikovaný případ z 11 detektorů, z nichž žádný jiný nebyl auditován.

---

## 6. Black-box odpor jako epistemologický princip

Tohle je **osobní poznámka** k postoji autora DBCL, kterou považuji za důležitou artikulovat.

### 6.1 Co je to black-box LLM thinking

V kontextu tohoto projektu: black-box LLM thinking = situace, kdy LLM **vyprodukuje výstup**, jehož **propozicionální obsah nemůžeme rekonstruovat** ze vstupních dat. Tj. nemůžeme říct „tahle inference použila tato data a tuto logiku".

### 6.2 Tradiční inženýrský pohled

Tradiční inženýr by řekl: „Pokud LLM funguje (output je správný v 95 % případů), je to dost dobré. Nech mě to použít." Toto je **pragmatický** přístup.

### 6.3 Autorův axiom: determinismus jako epistemologický základ

Autor DBCL říká něco jiného: **„ne, nestačí, že to funguje, musí to být rekonstruovatelné."** Toto je **epistemologický**, ne pragmatický postoj. Říká: „Věda nestojí na empirické shodě, stojí na vysvětlitelnosti. Systém, jehož výstupy neumím vysvětlit, není znalostní systém, je to orákulum."

### 6.4 Proč je to důležité

Tento postoj **mění celou architekturu**. Pragmatik by řešil halucinace statisticky (fine-tune, větší model, lepší prompt). Epistemolog řeší halucinace **strukturálně** (přesunutím inference mimo LLM tam, kde to jde, deterministickým výpočtem tam, kde to jde, a inferencí jen tam, kde to **nutně** musí být).

DBCL je **důsledek epistemologického postoje**, ne pragmatického rozhodnutí. Pokud by autor přijal pragmatický přístup, navrhl by fine-tune nebo RAG s větší bází. On navrhl **strukturální přestavbu mostu**. To je důsledek axiomu determinismu.

### 6.5 Co z toho plyne pro audit a implementaci

Pokud se autor ptá „je DBCL správně?", pragmatická odpověď je: „ano, audit potvrdil principy, implementace je proveditelná". Epistemologická odpověď je: „**DBCL je nutný, ale nestačí** — protože nekontroluje detektor halucinace, a to je systematičtější riziko, než inference halucinace".

**Mé doporučení `[DE-NOVO]`:** Při každé iteraci DBCL se ptejte ne „funguje to?", ale **„mohu rekonstruovat, proč to funguje?"**. Pokud ano, je to znalost. Pokud ne, je to empirická shoda — a ta se může zítra zlomit.

---

## 7. Pattern jako komprese — co se ztrácí, když komprimujeme

Tohle je další **obecnější úvaha**, kterou považuji za důležitou.

### 7.1 Co je pattern?

Pattern (v tomto projektu) je **komprimovaná narrace** opakujícího se jevu. Pattern R = „hráč relaxuje v koncovce s výhodou" je **popis** stavů, ve kterých eval_before > 300 AND phase = endgame AND došlo k chybě.

### 7.2 Komprese ztrácí informaci

Když řeknu „pattern R", ztratím:
- **Které konkrétní tahy** vedly k chybě (bylo to kvůli oslabení, nebo ztrátě soustředění, nebo časové tísni?).
- **Jak dlouho** hráč měl výhodu před chybou (krátce, dlouho?).
- **Co se dělo** v okolních tazích (byla to izolovaná chyba, nebo součást kolapsu?).
- **Jakou fázi koncovky** to bylo (pěšcová, figurální, dáma?).

Pattern R všechny tyto informace **zahodí** ve prospěch jednoduché, zapamatovatelné narrace. To je **účel patternů** — generalizace, přenositelnost, zapamatovatelnost. Ale to je **také jejich limit**: pattern nikdy neřekne plnou pravdu o incidentu.

### 7.3 Důsledek: každý pattern je aproximace

Když pattern detektor řekne „pattern R s confidence 0.7", znamená to „pravděpodobně relaxace", ne **„určitě relaxace"**. Zbývajících 30 % jsou **alternativní vysvětlení**, která pattern zahodil.

V DBCL v1 by **guard-clause neměl brát pattern_match jako fakt**. Měl by brát pattern_match jako **hypotézu s evidencí**, která musí být konzistentní s BlunderFactSheetem. A pokud je pattern match v rozporu s board_state, **pattern by měl být odmítnut**, ne narrativizován.

Toto je v podstatě **návrh na pattern guard**, který jsem v unity doc §5.3 naznačil. Ale zde to formuluji obecněji: **každý pattern je inferenční skok z Pravdy-2 na Pravdu-3, a proto musí být auditovatelný**.

### 7.4 Z toho plyne otázka: kolik patternů je správně?

SRC-3 navrhuje nový pattern S (capture aversion under check). SRC-2 audit varuje, že 11 detektorů A–S nebylo auditováno. Co když některé z 11 detektorů jsou **falešně pozitivní** jako F-007? Co když confidence uvedená v SRC-3 (~40 % pro S, 70 % pro R) je systematicky nadhodnocená?

Toto jsou otázky, na které **SRC-1 neodpovídá** a **SRC-2 jen naznačuje**. Doporučuji (v unity doc §10) audit všech 11 detektorů jako P0. Zde bych dodal: **v tomto auditu nestačí ověřit, že detektor testuje správnou podmínku. Je třeba ověřit, že pattern skutečně generalizuje** — tj. že popisuje jev, který se vyskytuje v datech častěji, než by se vysvětlil náhodou.

Toto je **empirická otázka**, ne teoretická. Odpověď vyžaduje **labeled dataset** chyb hráčů s různými pattern anotacemi, a metriku jako **inter-annotator agreement** (jestli dva nezávislí anotátoři dají stejný pattern na stejnou pozici). Bez tohoto je každá confidence number v SRC-3 **heuristická**, ne statistická.

---

## 8. Halucinace jako referenční odpoutání — fenomenologická vs strukturální

Chci nabídnout ještě jeden pohled, který považuji za užitečný pro pochopení toho, co se vlastně děje.

### 8.1 Dvě třídy halucinace

**Třída A — Strukturální (kanál 3, LLM):**
LLM má kontext C a generuje výstup. Výstup obsahuje výrok V, který není v C. Strukturálně je to **přeskočení** — inference šla z C do V, aniž by V bylo v C obsaženo.

Příklad: C obsahuje „Qf4, Kb1". LLM generuje „Qf4+ dává šach". Inference šla z proximity (Q blízko K) k tvrzení o šachu, bez kontroly geometrie. Toto je **referenční odpoutání** — slovo `+` (které v SAN znamená šach) bylo použito **mimo kontext SAN**, jen na základě asociace.

**Třída B — Sémantická (kanál 1, detektor):**
Detektor testuje podmínku P, ale pattern name tvrdí, že detekuje Q, kde Q ≠ P. Toto je **referenční odpoutání na úrovni kódu** — název patternu (slovní popis) referuje na jiný jev, než podmínka (kód).

Příklad: pattern J tvrdí „impulsive check block" (Q), ale testuje `+` v SAN (P). Q ≠ P. Když se `+` vyskytne, detektor řekne „impulsive check block", ačkoliv jde o tah dávající šach, ne o reakci na šach.

### 8.2 Společný rys: ztráta reference

V obou třídách **slovo ztratilo svůj referent**. V třídě A: `+` ztratil referenci na geometrický šach a odkazuje na jazykovou konvenci. V třídě B: „impulsive check block" ztratil referenci na board state a odkazuje na syntaktickou vlastnost SAN.

**Toto je klíčové**: halucinace není o LLM, je o **referenčním odpoutání**, ke kterému může dojít v **jakékoliv vrstvě systému**, která zprostředkovává mezi syntaktickou reprezentací a sémantickým obsahem.

### 8.3 Důsledek: validátor nestačí

Validátor v DBCL kontroluje **výstup LLM** (třída A). Nekontroluje **detektor** (třída B). Pokud chceme systém bez referenčního odpoutání, musíme kontrolovat **obě** třídy.

Toto je **3. pohled, který považuji za nejdůležitější**: halucinace není vlastnost LLM, je to vlastnost **každé zprostředkující vrstvy**. Prevence halucinací vyžaduje **validaci každé zprostředkující vrstvy**, ne jen té poslední.

### 8.4 Praktický implikát

Pokud DBCL v1 implementuje pouze LLM-level validaci, bude **strukturně neúplný**. Doporučuji `[DE-NOVO]`:

1. **Detektor validace** — pro každý detektor ověřit, že **název patternu** odpovídá **testované podmínce**. Toto je audit, ne runtime kontrola, ale měl by se opakovat při každé změně detektoru.

2. **Kontrakt validace** — mezi per-game a aggregate LLM, jak je naznačeno v §3.5.

3. **LLM validace** — stávající validátor, kontrola výstupu aggregate.

Tyto tři validace pokrývají **všechny tři kanály** a **všechny dvě třídy halucinace**. Validace na jedné úrovni nestačí.

---

## 9. DBCL jako symptom vs řešení

Tohle je **nejvíce spekulativní část** tohoto textu. Chci nabídnout jednu meta-úvahu, kterou považuji za důležitou artikulovat, i když nemám definitivní odpověď.

### 9.1 Teze

DBCL je **řešení** problému halucinací v MCP. Ale je **také symptomem** hlubšího problému v návrhu MCP: **představy, že LLM může být univerzální „inteligence"**, která integruje různé zdroje dat.

### 9.2 Argument

Kdyby MCP bylo navrženo s **jasně oddělenými rolemi** od začátku (detector → fact → narrator), nebyla by potřeba DBCL jako reaktivní oprava. DBCL je **návrat k modularitě**, která byla buď opuštěna z pohodlnosti, nebo nikdy nebyla plně implementována.

To není kritika autorů — je to **kontextualizace**. Vývoj softwaru s LLM komponenty v letech 2024–2026 procházel fází, kdy se **předpokládalo, že LLM nahradí tradiční logiku**. Toto se ukázalo jako chybné pro vysoké-stakes domény (šach, finance, medicína, právo). DBCL je jeden z projevů **korekce tohoto předpokladu**.

### 9.3 Důsledek: cyklická povaha korekce

Pokud je DBCL symptom větší korekce, můžeme očekávat **další korekce** v budoucnu. Například:
- Per-game vs aggregate problém (F-008) může vést k **přehodnocení dvou-režimové architektury** úplně.
- Pattern library revize může vést k **přehodnocení konceptu pattern match** úplně (místo patternů, plné feature vektory + ML klasifikace).
- Validátor může vést k **větší automatizaci** a méně LLM v pipeline.

Toto neříkám jako kritiku, ale jako **kontextualizaci**: DBCL není konec příběhu, je **iterace v cyklu korekcí**. Každá iterace řeší problémy předešlé a otevírá nové.

### 9.4 Otázka k zamyšlení

Kdyby se MCP navrhoval dnes od nuly, s poučením z DBCL, jak by vypadal? Pravděpodobně:
- Deterministické moduly **bez LLM** (Stockfish, pattern detector, fact sheet builder).
- **Jeden LLM** pro narraci, ne dva (žádný per-game vs aggregate problém).
- Validátor **integrovaný do LLM pipeline**, ne jako post-processing.
- **Žádná přímá data ingestion do LLM** — všechno přes fact sheets.

Toto je **idea**, ne návrh. Ale je užitečné si ji artikulovat, protože ukazuje **směr**, kterým by se DBCL v2 mohl ubírat.

---

## 10. Závěrečná syntéza — co si z tohoto pohledu odnést

Tento dokument nabídl **třetí perspektivu** — pohled zvenčí, informačně-teoretický, epistemologický. Kde stojí vůči SRC-1 a SRC-2?

### 10.1 Co potvrzuji

1. **P1 princip je správný** — detekce musí být deterministická, LLM musí být překladatel.
2. **F-007 je kritický** — pattern J (a potenciálně další) je sémantický bug, který DBCL guard-clause neřeší.
3. **F-008 je kritický** — dvě prompt místa jsou strukturální zranitelnost.
4. **F-013 je kritický** — validátor bez mapování claim→field je neúplný.
5. **Směr DBCL** (BlunderFactSheet, guard-clauses, validátor) je správný.

### 10.2 Co doplňuji `[DE-NOVO]`

1. **Terminologie**: „RAG" je špatný label, navrhuji SFE (Structured Fact Extraction) nebo DBN (Deterministic Bridge Narration).
2. **Tři kanály šumu**: detektor, kontrakt, dekódování. DBCL pokrývá hlavně dekódování; kanál 2 (kontrakt) je poddimenzovaný.
3. **Dvě třídy halucinace**: strukturální (LLM) a sémantická (detektor). Druhá třída je systematičtější a méně viditelná.
4. **Pattern jako komprese**: každý pattern je inferenční skok z Pravdy-2 na Pravdu-3, musí být auditovatelný.
5. **Epistemologie ground truth**: Stockfish není ground truth, je to silný důkaz. Pattern match je inferenční, ne deterministický.
6. **Validace na třech úrovních**: detektor, kontrakt, LLM. Nestačí jedna.
7. **Cyklická korekce**: DBCL je iterace, ne konec. Směřuje k menšímu zapojení LLM, ne většímu.

### 10.3 Co zpochybňuji (otevřeně)

1. **Confidence čísla** v SRC-3 (40 % pro S, 70 % pro R) jsou heuristická, ne statistická. Vyžadují labeled dataset a inter-annotator agreement.
2. **Pattern S** (capture aversion under check) je slibný, ale **bez širšího datasetu nelze říct, zda jde o skutečný pattern nebo o šum**. INC-B (N=1 miss) je příliš malý vzorek.
3. **Doporučení DBCL „zapojit existující multi-PV engine_lines"** je technicky správné, ale **neřeší kanál 1 (detektor halucinace)**. Může se stát, že po implementaci DBCL v1 bude system fungovat lépe, ale **systematická chyba v detektorech** zůstane.
4. **Audit F-007** je varování, ale **není diagnóza**. Nemáme audit dalších 10 detektorů. Můj 3. pohled říká: **dokud nebude audit kompletní, DBCL v1 je experiment, ne řešení**.

### 10.4 Co nechávám otevřené

- Zda je „RAG" rhetorika v SRC-3 nevinná pracovní zkratka, nebo symptom hlubšího záměny pojmu.
- Zda pattern S je skutečně nový, nebo varianta již existujícího patternu (např. B automatic grab).
- Zda kontrakt mezi per-game a aggregate má smysl řešit explicitně, nebo zda je efektivnější zrušit per-game režim.
- Zda validátor by měl být LLM-as-judge, deterministický, nebo hybrid.

Toto jsou otázky, na které odpoví **další iterace**, ne tento dokument. Můj záměr zde byl nabídnout **rámec**, ne odpovědi. Pokud tento rámec pomůže autorovi DBCL formulovat lepší otázky v další iteraci, splnil svůj účel.

---

## Dodatek: O tomto dokumentu

Tento text je **záměrně neinženýrský**. Neobsahuje tabulky incidentů, schémata BlunderFactSheetu, implementační sekvence — to vše je v `01_DBCL_unity_synthesis.md`. Tady jde o **kontextualizaci, rámec, epistemologii**. Pokud čtete oba dokumenty popořadě, doporučuji:

1. Nejdřív `01_DBCL_unity_synthesis.md` — konkrétní data, konkrétní akce.
2. Pak `02_DBCL_meta_evaluation.md` — rámec, ve kterém ty akce dávají smysl.

Pokud čtete jen tento dokument, ztratíte **konkrétní akční plán**. Pokud čtete jen unity syntézu, ztratíte **kontext, proč je ten plán takový, jaký je**.

Cíle těchto dvou dokumentů jsou různé:
- **Unity syntéza** = „co dělat".
- **Meta-hodnocení** = „proč to dělat a v jakém rámci".

Společně tvoří **pragmatický + epistemologický** pár. Dva pohledy na stejný problém, záměrně nestejné, aby pokryly víc prostoru, než jeden může.

---

*End of Meta-Evaluation v1.0*
*Připraveno 2026-07-25 07:58Z*
*Tento dokument nemá implementační sekci. Má interpretační.*
