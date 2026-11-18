# Zakres gold i reguły sędziów (J1, J2, J3)

Reguły sędziów i zakres gold obowiązujące w korpusie, wypracowane w przeglądzie ręcznym pilota na dev (S1–S7 uczestników OSS, A–E
Privatizera) i w sanity warstwy trudnej. Gold trzonu korpusu (pliki i manifest – sumy kontrolne są publiczne w prerejestracji) i wagi
punktów (`wagi_punktow.json`) są zamrożone; reguły są zapisane wyłącznie w sędziach (`pbench/sedzia/tekst.py`, `pbench/sedzia/plik.py`), oceny (`pbench/ocen.py`) i opisu metodyki. Te same reguły
obowiązują wszystkich uczestników. Żadna z poprawek nie ukrywa prawdziwego wycieku: odsłonięty numer rachunku czy sygnatury
nadal wycieka (pełny albo częściowy według progów sędziów; jedyne ograniczenie – reguła krotności części opisowych sygnatury
w sędzi plikowym przy cytacie innej sprawy, pkt 2).

## 1. Własna sprawa a cytowane orzeczenia (S2, S3)

Konwencja właściciela (2026-10-23): **nazwy spraw w cytatach orzeczeń nie są danymi osobowymi do anonimizacji.**

| Element | Własna sprawa dokumentu | Cytowane orzeczenie (inna sprawa) |
|---|---|---|
| strony (osoby, firmy) | gold (`OSOBA`, `ORGANIZACJA`) | nie gold |
| daty (rozprawy, wyroku, doręczenia, zdarzeń) | gold (`DATA`) | nie gold (data wydania cytowanego orzeczenia) |
| sygnatura / numer sprawy | gold (`SYGNATURA`) | nie gold (np. „XI ZR 46/17”, „[2017] UKSC 33”, „pourvoi n° 21-18.680”) |
| miasto w nazwie sądu lub rejestru | nie gold (konwencja: „Sąd Rejonowy w Gdańsku”, „RCS Reims”) | nie gold |

Maskowanie elementów cytowanego orzeczenia (np. „Lewandowski” w „(w sprawie Strzelecki przeciwko Lewandowski)”, data
„23.06.2020 r.” cytowanego wyroku) jest **nadmiarowym maskowaniem** – liczy się do FP. Uzasadnienie: orzeczenia są publikowane,
a cytat w piśmie identyfikuje precedens, nie stronę obsługiwanej sprawy; prawnik wysyłający pismo do modelu potrzebuje cytatu
w brzmieniu oryginalnym. Wszystkie cytowane orzeczenia w korpusie są fikcyjne (`README.md`, „Dane fikcyjne”).

Data własnej sprawy i data cytowanego orzeczenia mogą wyglądać tak samo („14.09.2020”); sędzia ocenia offsety, więc rozstrzyga
kontekst – ta sama reguła dla wszystkich uczestników.

**Kontrola (J1, próba 24 dokumentów trzonu – po 4 wyroki i 4 pozwy PL, po 2 wyroki i 2 pozwy EN/ES/DE/FR, ziarno 20261101):**
dla każdej wartości gold `OSOBA`/`ORGANIZACJA` szukano wszystkich wystąpień jej słów (≥ 4 znaki, wielka litera) w tekście
dokumentu poza spanami gold. Wynik: **0 wystąpień stron własnej sprawy poza gold**, także w dokumentach z cytatami orzeczeń
z nazwami stron (wyroki PL „przeciwko”, EN „Holt v Brewer [2017] UKSC 33”) i z cytatami bez nazw (DE „BGH, Urteil vom …”, FR
„Cass. 1re civ.”, ES „STS …”). Jedyne trafienia poza gold (5, `es-wyrok-0008`): „Valencia” w nazwie sądu („Juzgado de Primera
Instancia n.º 24 de Valencia”, „Audiencia Provincial de Valencia”) – miasto sądu, poza gold zgodnie z konwencją, a nie strona.
W próbie żadne słowo nazwy strony własnej sprawy nie wystąpiło w cytacie (ani nigdzie indziej poza gold).

## 2. Etykiety w spanach gold identyfikatorów (S1, A)

Gold rachunku i sygnatury bywa zapisany razem z etykietą: EN „Routing No. 015757092, Account No. 60431799632”, „Claim No.
QB-2020-014548”, „Case No. 2:21-cv-01234-JSR”, ES „Procedimiento Ordinario n.º 123/2024”, FR „RG n° 21/01234”. Słowa etykiety
nie identyfikują wartości. Lista etykiet (per kategoria i język, z komentarzem): `pbench.sedzia.tekst.ETYKIETY_ID`
(RACHUNEK: „Nr rachunku”, „Routing No.”, „Account No.”, „Kontonummer”, „N.º de cuenta”, „N° de compte”, „IBAN”…; SYGNATURA:
„Sygn. akt”, „Claim No.”, „Case No.”, „Az.”, „n.º”, „Autos”, „RG”, „N° RG”…). Etykieta pasuje tylko całymi słowami, bez
rozróżniania wielkości liter. Na liście są **wyłącznie czyste etykiety** – oznaczenia stałe, takie same w każdej wartości
(orzeczenie kontrolera J1-fix1, I1 wariant a). „RG” (répertoire général) jest jedną literą rejestru, wspólną dla każdego numeru
sprawy francuskiej, i częścią etykiety „N° RG” – nie odróżnia spraw; „Autos” (akta) odpowiada polskiemu „Sygn. akt”.

- **Sędzia tekstowy:** reguła ciągu alfanumerycznego (`min_cyfr_id` = 4) obejmuje znaki spanu spoza etykiet – etykiety są
  pomijane jak separatory. Oba numery zamaskowane, etykiety zostają → brak wycieku; numer routingu odsłonięty → częściowy;
  całość odsłonięta (także same numery przy zamaskowanych etykietach) → pełny. Jak przy każdym separatorze, ciąg **łączy się
  ponad etykietą**: odsłonięte 2 ostatnie cyfry numeru routingu i 2 pierwsze cyfry numeru konta dają razem ciąg 4 znaków →
  wyciek częściowy, choć żaden z numerów nie ma 4 kolejnych odsłoniętych znaków (reguła wyłącznie zaostrza ocenę).
- **Fragment poniżej progu nie jest wyciekiem** – zgodnie z zamrożonym progiem `min_cyfr_id`, tak samo jak dla numeru bez
  etykiety: „Claim No. QB-···········” (odsłonięty prefiks wydziału „QB”, 2 znaki) czy 3-cyfrowy numer kolejny przy
  zamaskowanym roku nie wyciekają: ciąg nie obejmuje liter etykiety.
  „Wszystkie identyfikujące znaki zamaskowane” znaczy w tej metodyce: nie zostaje odsłonięty ciąg ≥ progu.
- **Sędzia plikowy** (bez offsetów): obok pełnej wartości szukane są jej **części** – ciągi alfanumeryczne między etykietami
  (łącznie ≥ 6 znaków; szukanie samych całości z etykietami przepuszczałoby odsłonięty sam numer routingu). Sygnatura – z etykietą i bez niej – dzieli się dalej na **części opisowe i numer** (`plik._opis_i_numer`, ta sama
  reguła w każdym języku): numer zaczyna się od ostatniego tokenu (słowa rozdzielone białymi znakami) z cyfrą; to, co przed nim,
  jest częścią opisową („VII Ca”, „12 C”, „32 O”, „Juicio Verbal”, „WR.XII”), a litery na początku tokenu numeru oddzielone od
  cyfr separatorem – drugą częścią opisową („NS-REJ.KRS” z „NS-REJ.KRS/033655/20”, „QB” z „QB-2020-014548”); ciąg bez cyfry jest
  w całości opisowy. Rodzaj: wszystkie części → „pelny” (także gdy etykiety zamieniono); odsłonięta część o długości ≥ progu →
  „czesciowy”. Próg części sygnatury (opisowej i numeru) to `min_cyfr_id` = 4 – **ten sam co w sędzi tekstowym** (J1-fix3, m1);
  części rachunku z etykietą – 6 (są to całe numery, dłuższe niż próg tekstowy). Skutek – oba sędziowie zgodnie:
  „12 C 345/24” z odsłoniętym „12 C” (3 znaki) – brak wycieku, z odsłoniętym samym „345/24” (5 znaków) – częściowy; „32 O 264/24”
  – tak samo; „WR.XII NS-REJ.KRS/033655/20” z zamaskowanymi „WR.XII” i „033655/20” – częściowy („NS-REJ.KRS”, 8 znaków); „I C”
  i „QB” (2 znaki) odsłonięte same – brak wycieku.
  - **Część wspólna** z inną wartością gold (cała część występuje w tekście innej wartości, z granicami – nie wystarczy podciąg:
    „32 O” nie jest wspólne z „Hauptstraße 32 Ost”; J1-fix3, m2) jest pomijana – jej odsłonięcia nie da się przypisać, jak przy
    wartościach niejednoznacznych; część pominięta nie wchodzi do „wszystkich części”, więc odsłonięcie reszty przy zamaskowanej
    części wspólnej daje „pelny” (zaostrzenie).
  - **Cytat innej sprawy** (J1-fix3, I1 – orzeczenie kontrolera): wyroki cytują orzeczenia tego samego wydziału („VII Ca
    6470/18” obok własnej „VII Ca 1554/21”), a cytaty nie są gold (pkt 1). Część **opisowa** sygnatury (wydział, repertorium, rodzaj postępowania – nie numer ani część rachunku; J1-fix4, m1), którą oryginał ma także **poza
    wystąpieniami wartości gold**, liczy się jako trafienie tylko wtedy, gdy wynik ma ją **częściej**, niż oryginał ma jej
    wystąpień poza gold – ta sama reguła krotności co dla wartości niejednoznacznych (`plik.niejednoznaczne`). Wystąpienia
    liczone są tokenami po przejściu, w którym wystąpienie całej wartości gold „zabiera” swoje części (`plik._krotnosc_fraz`);
    w oryginale – mniejsza z dwóch miar (przejście albo wszystkie wystąpienia minus wystąpienia w wpisach gold), więc OCR, który
    przeczyta wartość gold z błędem, a jej część poprawnie, nie zawyża liczby i nie ukrywa wycieku. Skutek: własna sygnatura
    zamaskowana wszędzie, cytat zostawiony – brak wycieku (w sędzi plikowym i tekstowym); własne „VII Ca”
    odsłonięte przy zamaskowanym numerze – „czesciowy”; odsłonięty sam numer przy zostawionym cytacie – „czesciowy” (część
    opisowa z cytatu nie dopełnia go do „pelny”); własny numer odsłonięty przy zamaskowanym cytacie z tym samym numerem – wyciek
    (numer nie podlega regule krotności, jak w sędzi tekstowym). Sędzia tekstowy ocenia offsety, więc cytatu w ogóle nie widzi. Ograniczenie
    (wspólne dla wszystkich uczestników plikowych, wynik braku offsetów): uczestnik, który zamaskuje cytat, a własną część
    opisową zostawi najwyżej tyle razy, ile było cytatów, nie ma wycieku plikowego.
  - W OCR – także po złożeniu znaków mylonych, częściowy z potwierdzeniem innym odczytem jak token.
  - **Pozostała różnica wobec sędziego tekstowego:** sędzia plikowy szuka całych części. Część odsłonięta tylko w kawałku
    („Verbal” z zamaskowanym „Juicio”, połowa numeru konta „0157·····”) nie jest wyciekiem plikowym (w tekstowym jest, gdy
    zostaje ≥ 4 kolejnych znaków), a IBAN bez etykiety wycieka wyłącznie „pelny”. Reguła jest ta sama dla wszystkich uczestników.
- **Nie są etykietami** opisowe części oznaczenia sprawy – w każdym języku tak samo: polski wydział i repertorium („VII Ca
  1234/21”, „NS-REJ.KRS”), hiszpański rodzaj postępowania („Procedimiento Ordinario”, „Juicio Verbal”, „Rollo de Apelación”,
  „Procedimiento Monitorio”…), niemieckie „C”/„O” w Aktenzeichen, angielskie prefiksy wydziału („QB”, „KB”) i „CV”/„cv” w
  numerach amerykańskich; także litery tablicy rejestracyjnej i kod kraju IBAN. Liczą się jako identyfikujące: odsłonięte „VII Ca”
  albo „Juicio Verbal” przy zamaskowanym numerze daje wyciek częściowy (5 i 12 znaków) – w obu sędziach jednakowo, z etykietą
  i bez niej (sędzia plikowy: części opisowe, zob. wyżej).

## 3. Słowa opisowe nazw organizacji (D)

Rodzaj kancelarii i forma prawna („Kancelaria”, „Radców Prawnych”, „Adwokacka”, „Wspólnicy”, „Rechtsanwälte”, „PartG mbB”,
„Partnerschaft”, „Abogados”, „Despacho”, „Bufete”, „SELARL”, „Avocats”, „Cabinet”, „LLP”, „Solicitors”…) – lista z komentarzem:
`pbench.sedzia.tekst.SLOWA_OPISOWE_ORGANIZACJI` – nie dają **same** wycieku częściowego nazwy organizacji: „Kancelaria Radców
Prawnych Ziemba i Wspólnicy sp.k.” z zamaskowanym „Ziemba” nie wycieka. Nazwa odsłonięta w całości nadal wycieka („pelny”),
także złożona z samych słów opisowych. Sędzia tekstowy stosuje listę w kategorii `ORGANIZACJA`; sędzia plikowy – jako słowa
zastrzeżone leksykonu (`plik.SLOWA_ZASTRZEZONE`: pojedynczy token nie dowodzi wycieku, pełna wartość – tak). Na listę nie trafiają
słowa, które bywają nazwiskami albo rdzeniem nazwy („Law”, „Chambers”, „Lex”). Sędzia plikowy stosuje leksykon we wszystkich
kategoriach (tekstowy – tylko w `ORGANIZACJA`), a jego lista zastrzeżona ma od dawna także „law” i „group”; różnica nie wpływa na
wynik, dopóki żadne z tych słów nie jest imieniem, nazwiskiem, ulicą ani miejscowością korpusu – pilnuje tego test
(`tests/test_j1.py`: słowa zastrzeżone i opisowe poza słownikami osób, ulic i miejscowości oraz nazwiskami-słowami warstwy
trudnej, H2). Uwaga: słownik rdzeni firm hiszpańskich
(`dane/slowniki/es/firmy_rdzenie.txt`) zawiera rdzeń „Abogados Asociados” złożony wyłącznie ze słów opisowych – taka nazwa
wycieka tylko w całości.

## 4. Kwoty i miara „w deklarowanym zakresie” (S4, C)

Kwoty (`KWOTA`) zostają w gold z wagą 1 (`wagi_punktow.json`); dominują liczbę wycieków uczestników, którzy z założenia
kwot nie maskują (listy płac: ok. 200 kwot na dokument). Obok miary głównej każda ocena (`pbench-ocen`, oba poziomy) ma pole
pomocnicze `w_zakresie_deklarowanym` (poza punktami): wycieki i oceniane wartości tylko z kategorii, które uczestnik deklaruje
w `uczestnicy/<id>/etykiety.json` **dla języka dokumentu** (J1-fix3, I2 – niżej), a poziom tekst także pokrycie znakowe
i char-F2 w tym zakresie (FP – bez zmian, względem całego gold). Agregacja (zadanie 17) liczy z niego `w_zakresie.csv`.

Zakres wynika wyłącznie z `etykiety.json` (etykieta uczestnika → kategorie gold). **Reguła deklaracji (J2, ta sama dla
wszystkich uczestników):** deklaracja = kategorie, które narzędzie maskuje w konfiguracji używanej w benchmarku (domyślnej).

1. Liczy się tylko etykieta, którą uczestnik w tej konfiguracji faktycznie zwraca: typ zadany modelowi (GLiNER – lista
   `ETYKIETY` w `run.py`), encja rozpoznawacza zarejestrowanego dla języka (Presidio), typ przekazywany dalej (Stanza, mapowanie
   NER), kategoria włączona w ustawieniach domyślnych wydania (Privatizer, `categories.py` tagu – `KWOTA`, `MAC`, `UUID`,
   `INICJALY` są wyłączone; wyjątek: warianty aneksu `privatizer-tekst-maks` i `privatizer-plik-maks` pracują w trybie „Maksymalna
   ochrona”, który sama aplikacja włącza `KWOTA` – ta kategoria jest wtedy w ich konfiguracji, więc w ich zakresie). Wariant-komponent deklaruje tylko to, co zwraca ten komponent: `privatizer-model` – kategorie
   etykiet taksonomii modelu (`detect/backends.py`), `privatizer-reguly` – kategorie reguł (bez `ZDROWIE`: kategoria jest w wydaniu
   domyślnie wyłączona w każdym trybie, a reguła ICD-10 działa tylko przy włączonej ręcznie i zwraca sam kod, fragment wartości gold – pkt 2). Wariant krzyżowy (aneks, `metodyka/uczestnicy.md`) deklaruje sumę
   składników: potok Privatizera z obcym modelem – kategorie reguł i kategorie, które obejmują etykiety modelu w mapowaniu
   uczestnika (`KATEGORIE` w `detektor.py`); `presidio-lgp` – encje rozpoznawaczy Presidio i kategorie `privatizer-model`.
2. Etykieta obejmuje kategorię gold, gdy **wartość tej kategorii w całości** mieści się w definicji etykiety (karta modelu,
   dokumentacja rozpoznawacza, taksonomia). Etykieta węższa od kategorii (podtyp, odpowiednik krajowy) obejmuje ją: „blood_type”
   → `ZDROWIE`, „ssn” → numery ubezpieczenia społecznego innych krajów (`SVNR`, `NUSS`, `NINO`, `NIR`), „person initials”
   Privatizera (inicjały zwracane pod `OSOBA`, kategoria domyślnie włączona) → `INICJALY`. Nie obejmuje kategorii, której
   wartość jest dla etykiety tylko fragmentem albo czymś innym: miejsce/lokalizacja z NER (spaCy, Stanza) ≠ adres pocztowy
   (`ADRES`), „address” ≠ samodzielna miejscowość/region/państwo, „date of birth” ≠ inne daty (`DATA`), „national id number”
   ≠ numer prawa wykonywania zawodu lekarza (`NR_ID` w gold: PWZ, GMC, NPI, LANR, colegiado, RPPS – obejmują go
   „certificate_license_number”, `MEDICAL_LICENSE`/`US_NPI`/`DE_LANR` Presidio, „professional licence number” Privatizera),
   „certificate_license_number” ≠ numer rejestru spółki (`NR_REJESTRU`).
3. Gdy dokumentacja etykiety nie podaje definicji (OpenAI Privacy Filter: „account_number”), zostaje mapowanie autora
   integracji z `KONFIG.md` uczestnika.
4. **Zakres jest liczony per język dokumentu** (J1-fix3, I2; język z manifestu, `wpis["jezyk"]`): kategoria jest w zakresie
   dokumentu tylko wtedy, gdy uczestnik ma etykietę, która ją obejmuje, **w języku tego dokumentu**. Format `etykiety.json`
   (jeden dla wszystkich): wartość etykiety to lista kategorii – etykieta zwracana w każdym języku – albo słownik język → lista
   kategorii – etykieta zwracana tylko w wymienionych językach (klucz `*` – w każdym; `pbench.ocen.zakres_deklarowany`). Granica
   jest strukturalna, nie jakościowa: język „nie działa”, gdy komponent w tym języku nie jest uruchomiony albo nie ma danego typu
   (rozpoznawacz zarejestrowany tylko dla jednego języka, model NER języka bez tego typu); model wielojęzyczny zadany tą samą
   listą etykiet w każdym języku (GLiNER, OpenAI Privacy Filter, model Privatizera) i reguły Privatizera, które działają w
   komplecie w każdym profilu języka (`jezyki.profil_wykrywania` tagu, D21), deklarują etykiety w każdym języku – także poza
   językami oficjalnymi (te ocenia osobna miara „w zakresie oficjalnym”). Sumowanie po językach zawyżało zakres uczestników
   z komponentami jednojęzycznymi (np. kwoty i daty Stanzy z modeli EN/PL liczone w dokumentach DE/ES/FR).

| uczestnik | etykieta (komponent) | języki |
|---|---|---|
| presidio-spacy, presidio-gliner, presidio-pl-ner, presidio-lgp | `PL_*` (`PlPeselRecognizer`; presidio-pl-ner także `rozpoznawacze_pl`) | pl |
| jw. | `US_*`, `UK_*`, `MEDICAL_LICENSE` (`presidio_wspolne.KRAJOWE["en"]`) | en |
| jw. | `ES_*` | es |
| jw. | `DE_*` | de |
| presidio-pl-ner | `ID`, `MEDICAL_CONDITION`, `LOCATION` → `ADRES` (lexedit – model NER polskiego; w en/es/de/fr NER CoNLL bez tych klas) | pl |
| stanza | `DATE` (NKJP `date`, OntoNotes `DATE`; CoNLL02, GermEval2014, WikiNER – bez dat) | pl, en |
| stanza | `MONEY` (tylko OntoNotes) | en |
| pozostałe etykiety wszystkich uczestników | rozpoznawacze wzorcowe Presidio (`OGOLNE`, telefon), NER każdego języka (osoby, organizacje, miejsca), modele wielojęzyczne, Privatizer | każdy |

Deklaracja wpływa wyłącznie na miarę pomocniczą `w_zakresie_deklarowanym`; miara główna i punkty – bez zmian. Zmiany deklaracji
J2 (przed → po, źródło) – raport zadania J1-fix1 i `KONFIG.md` uczestników:

| uczestnik | usunięte | dodane |
|---|---|---|
| privatizer-tekst, privatizer-plik | KWOTA, MAC, UUID, ZDROWIE (domyślnie wyłączone) | – |
| privatizer-tekst-maks, privatizer-plik-maks (aneks) | MAC, UUID (wyłączone także w trybie „Maksymalna ochrona”) | KWOTA (włączona trybem: `settings.kwota_wg_trybu`, od v1.3.0b22), ZDROWIE (spany D39 w trybie privacy; poza gold, więc nadmiarowe maskowanie) – zakres = `privatizer-tekst` / `privatizer-plik` + `KWOTA` + `ZDROWIE` |
| privatizer-reguly | KWOTA, MAC, UUID, INICJALY (wyłączone), ZDROWIE (brak reguły) | – |
| privatizer-model | KWOTA, MAC, UUID, ZDROWIE (wyłączone), KRYPTO, MRZ (żadna etykieta modelu ich nie definiuje) | – |
| gliner-knowledgator-pii | NR_ID | NINO |
| gliner-nvidia-pii | NR_REJESTRU | NINO, NIR |
| gliner-urchade-pii | DATA, MIEJSCOWOSC, REGION, KRAJ, MIEJSCE_UR, NR_ID | NINO |
| openai-privacy-filter | MIEJSCOWOSC, REGION, KRAJ, MIEJSCE_UR, KOD_POCZTOWY, IP, LOGIN | – |
| presidio-gliner | MIEJSCOWOSC, REGION, KRAJ, MIEJSCE_UR | – |
| presidio-spacy | ADRES | NR_ID |
| presidio-pl-ner | – | NR_ID, SYGNATURA |
| stanza | – | – |

Zmiany J1-fix3 (tylko miara pomocnicza; zakres per język – tabela wyżej):

| uczestnik | zmiana | źródło |
|---|---|---|
| privatizer-model | + KVNR, NHS, MBI (pod `IDENTYFIKATOR`) | taksonomia etykiet modelu w tagu: „contract or account reference” = „a client, contract, policy, order, membership or account number identifying a named party’s relationship” – numer ubezpieczonego to numer polisy/członkostwa; w pilocie model maskuje je też pod `DOWOD`/`NR_ID` (m4) |
| presidio-spacy, presidio-pl-ner (i `_wspolne/etykiety_presidio.json`) | − CIF (z `ES_NIF`) | `EsNifRecognizer` 2.2.366: `\b[0-9]?[0-9]{7}[-]?[A-Z]\b` z sumą kontrolną DNI – CIF zaczyna się literą („B04324430”) (m3) |
| presidio-gliner | `ES_NIF` bez CIF; CIF w zakresie zostaje (GLiNER „tax identification number” → `TAX_ID`) | jw. |

## 5. Reguły sędziego plikowego wynikające z sanity warstwy trudnej (J3)

Trzy reguły sędziego plikowego zapewniają spójność oceny oryginału i uczestnika idealnego w całej warstwie trudnej (sanity:
oryginał i uczestnik idealny, sędzia plikowy z OCR). Są symetryczne – te same dla każdego uczestnika, języka i warstwy (także
trzonu); gold i pliki korpusu od nich nie zależą, `punktacja.md` ich nie dotyczy.

1. **Inicjały i wartości krótkie w binarnych strumieniach DOC** (`plik.MAKS_ALNUM_KROTKIEJ`, `ekstrakcja.Czesc.binarna`). Sędzia
   plikowy czyta strumienie OLE pliku DOC także jako surowe bajty (cp1250, UTF-16). Dwuliterowe inicjały („tb”) trafiają tam
   przypadkowo w bajty strumienia `Data` (np. wyniku idealnego `h-pf-en-pismo_z_parafami-0001` – w bajtach oryginału ich nie
   ma); trafienie zależy od bajtów wyniku, więc dotykałoby losowo uczestników zachowujących `.doc`, a nigdy tych, którzy zamieniają
   DOC na DOCX. Dlatego inicjały i wartości o ≤ 3 znakach alfanumerycznych nie są szukane w widokach binarnych strumieni DOC
   (wszystkie poza `SummaryInformation`/`DocumentSummaryInformation`), tylko w tekście dokumentu (konwersja LibreOffice),
   właściwościach i pozostałych częściach; dłuższe wartości są szukane wszędzie. Ryzyko resztkowe: krótka wartość obecna wyłącznie w bajtach DOC, których
   LibreOffice nie pokazuje (np. tekst po szybkim zapisie poza tabelą fragmentów), nie jest wykrywana – jednakowo dla wszystkich.
2. **Wykrywalność w OCR = warunki wycieku.** Wyciek z OCR wymaga potwierdzenia (drugi odczyt albo słowo dokładne; obrazy
   osadzone – inny tryb albo skala), więc sama „wykrywalność” w jednym odczycie oryginału (także samym trafieniem rozmytym)
   nie wystarcza: nazwa firmy z pieczątki `h-sp-de-cv-0001` byłaby oceniana, choć nie wycieka nawet z kopii oryginału. Grupa
   wartości obrazowych, której linia bazowa (te same reguły i odczyty co ocena wyniku) w oryginale nie odnajduje, jest
   `niewykrywalna` – poza mianownikiem i bez OCR obrazów wyniku – dla wszystkich uczestników (`obrazy.wykrywalne_obrazy`).
3. **Kod pocztowy jak identyfikator** (`KOD_POCZTOWY` w `tekst.KATEGORIE_ID`; sędzia plikowy od `plik.MIN_DL_KODU` = 5 znaków).
   Kod nie jest ciągiem tokenów słownych (polski „28-333” miałby tokeny „28” i „333” krótsze niż `min_cyfr_id` i w sędzi plikowym
   nie mógłby wyciec, a pięciocyfrowe kody DE/ES/FR – tak). W każdym języku kod wycieka, gdy jego ciąg znaków alfanumerycznych
   występuje z granicami, z separatorem albo bez („28-333”, „28333”, „28 333”); sędzia tekstowy – regułą ciągu identyfikatora
   (pkt 4 reguł: ≥ `min_cyfr_id` kolejnych odsłoniętych znaków).

Reguła oczekiwana (bez wyjątku): kwota krótsza niż `MIN_CYFR_KWOTY` = 5 znaków alfanumerycznych („10,00 €” – cztery cyfry,
`h-os-fr-protokol-0001`) nie może wyciec w sędzi plikowym (reguła 2b – słabe tokeny kwot trafiają w liczby z metadanych i tabel);
sanity raportuje takie wartości jako niewyciekające z kopii oryginału. Obejmuje to wszystkich uczestników jednakowo.

## 6. Rozpoznania, kody ICD i leki poza gold

Obowiązuje w korpusie (ziarna trzonu 20261103 i warstwy trudnej 20261104):

* **Poza gold:** wartości kategorii `ZDROWIE` pochodzące z rozpoznań (pola `*.diagnoza*` – kod ICD i nazwa rozpoznania) oraz z leków
  (pola `*.lek*` – nazwa z dawką). Tekst rozpoznań i leków **zostaje w dokumencie** (w pliku i w `.txt`), ale nie jest wartością gold
  w `gold_tekst`, `gold_plik` ani `gold_obrazy`. Mapowanie: `pbench/budowa.py` (`_KATEGORIE_POL`, pola `diagnoza`/`lek` → zwykły
  tekst). W korpusie nie ma żadnej wartości gold kategorii `ZDROWIE`; kategoria zostaje w taksonomii (`KATEGORIE`, wagi).
* **W gold zostaje** pacjent i jego dane (imię i nazwisko, data urodzenia, adres, telefon, PESEL, numer ubezpieczenia), lekarz,
  placówka, daty wizyt itd.
* **Zamaskowanie rozpoznania lub leku to nadmiarowe maskowanie** (T5/P5): znaki poza gold, `fp_znaki` > 0 w sędzi tekstowym
  (`ocen_tekst`) i `nadmiarowe.znaki` > 0 w sędzi plikowym; brak wycieku. Logika sędziów bez zmian
  (`tests/test_korpus_sklad.py`). Nieosłonięcie rozpoznania lub leku nie jest wyciekiem.
* **Warstwa trudna:** składnik `choroba` przypadku `posrednie_rzadka_choroba` przestaje być gold (`posrednie.md`); pozostałe przypadki
  nie używały `ZDROWIE`.
* **Domyślna konfiguracja wydania a `ZDROWIE`:** kategoria jest w `v1.3.0b24` domyślnie wyłączona w każdym trybie i profilu (`categories.py`),
  więc warianty rankingowe Privatizera (tryb domyślny) jej nie deklarują (reguła J2; ani model, ani reguły jej nie zwracają).
  Warianty aneksu `privatizer-tekst-maks` i `privatizer-plik-maks` ją deklarują: w trybie „Maksymalna ochrona” aplikacja maskuje frazy
  o niepełnosprawności i rehabilitacji także przy wyłączonej kategorii (D39) i zwraca je jako `ZDROWIE`. Wartości gold `ZDROWIE` nie ma,
  więc deklaracja nie zmienia żadnej miary; zamaskowane frazy są poza gold i sędzia liczy je jako nadmiarowe maskowanie (znaki poza gold,
  jak rozpoznania), nie jako wyciek ani etykietę nieznaną (sędzia nie rozróżnia kategorii wykrycia, kategoria wchodzi tylko do zakresu).
