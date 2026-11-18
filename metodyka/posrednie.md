# Identyfikacja pośrednia – osobna miara opisowa (warstwa trudnych przypadków, spec §11 pkt 4)

Identyfikacja pośrednia jest **poza punktami** (`punktacja.md`: „Identyfikacja pośrednia (`posrednie`) – poza punktami, osobna
miara opisowa”). Raport pokazuje ją obok rankingów, z przedziałem ufności, bez wpływu na T1–T6 i P1–P7. Dokumenty przypadków
`posrednie_*` nie są przypadkami T3/P3 (średnia po przypadkach trudnych liczy się bez nich); ich zwykłe gold (osoby nazwane,
firmy, daty…) jest oceniane jak w każdym dokumencie warstwy trudnej. Agregacja punktów wybiera przypadki średniej T3/P3
wyłącznie funkcją `pbench.przypadki.przypadki_punktowane()` (rejestr bez `posrednie_*`; pilnuje test).

## Przypadki (zadanie H5, `pbench/trudne_posrednie.py`)

Dokument opisuje osobę-cel, która **nie jest nazwana nigdzie w dokumencie** (ani imieniem, ani nazwiskiem, ani inicjałami –
sprawdza generator i test), ale da się ją wskazać z połączenia kilku informacji – **kombinacji**. Inne osoby dokumentu (autor
notatki, rozmówca, lekarz, świadek, sąsiad) są nazwane i są zwykłym gold.

| Przypadek | Typ dokumentu | Kombinacja (składniki; *gold*, pozostałe spoza gold) |
|---|---|---|
| `posrednie_funkcja_firma` | notatka kancelarii o kontrahentach (`notatka_kontrahent`) | dwie na dokument: funkcja + *firma* (Prezes Zarządu …, główna księgowa w spółce …, jedyny wspólnik …, komplementariusz …; Chief Financial Officer of …, Geschäftsführer der …, administrador único de …, gérant de …, président de …) albo kierownik budowy + *adres inwestycji*; forma prawna firmy zawsze dopuszczalna dla funkcji (niżej) |
| `posrednie_rzadka_choroba` | wniosek kadrowy (`wniosek_kadrowy`), notatka zespołu szkolnego (`notatka_szkolna`) | *choroba rzadka* + *pracodawca* + *miejscowość zakładu* albo rocznik; *choroba ucznia* + szkoła + *miejscowość* |
| `posrednie_wiek_miejscowosc` | notatka ze zdarzenia drogowego (`notatka_zdarzenie`) | wiek („47-letni”, „82-year-old”, „47-jähriger”, „82 años”, „âgé de 47 ans”) + *mała miejscowość* (wieś, village, Ortsteil, pedanía, hameau); gmina obok to zwykłe gold MIEJSCOWOSC poza kombinacją |
| `posrednie_dzialka_gps` | protokół oględzin domu (`protokol_ogledzin`) | **dwie kombinacje jednoskładnikowe**: oznaczenie działki (numer z obrębem, Flur/Flurstück, section cadastrale, polígono/parcela; EN – numer tytułu HM Land Registry) oraz współrzędne wejścia do domu (dziesiętne albo stopnie-minuty-sekundy) – każde z nich samo wskazuje dom osoby-celu, więc zamaskowanie jednego nie chroni drugiego; żadne nie jest gold. W połowie dokumentów nieruchomość wskazuje też zwykłe gold miary głównej – *księga wieczysta* (PL) albo *adres* – w drugiej połowie tylko miejscowość |

Języki: wszystkie cztery przypadki w PL, EN, ES, DE i FR (każdy ma sens w każdym z pięciu języków; EN = Wielka Brytania).
Formaty: DOCX, PDF i DOC (`trudne.formaty_dla`), zawsze z tekstem poziomu 1 (`.txt`).

Słowniki są w module generatora: choroby rzadkie (wiedza ogólna – choroby z list chorób rzadkich typu Orphanet; eponimy nie mogą
pokrywać się z nazwiskami osób dokumentu), małe miejscowości (własna kompilacja nazw – nazwy miejscowości nie są danymi
osobowymi; pary miejscowość–gmina są syntetyczne; żadna nie jest w słowniku miast generatora), funkcje i szkoły (bez nazw własnych
osób). Nic z danych treningowych modelu; firmy fikcyjne z generatora trzonu.

**Realizm prawny** (`_FUNKCJE` w generatorze): firma jest losowana z generatora trzonu tak długo, aż jej forma prawna pasuje do
funkcji – PL: prezes zarządu – sp. z o.o./S.A./P.S.A., jedyny wspólnik – sp. z o.o., komplementariusz – sp.k./S.K.A.; DE:
Geschäftsführer i Alleingesellschafter – GmbH/UG, Finanzvorstand – AG; FR: gérant – SARL/EURL, président – SAS/SASU, associé
unique – EURL/SASU; ES: administrador único – S.L./S.A./S.L.U., socio único – S.L.U.; EN: dyrektorzy – Ltd/Limited/PLC, sole
shareholder – Ltd/Limited; księgowość i finanse – formy spółek, w których te stanowiska istnieją. FR: elizja przed nazwą firmy
od samogłoski („gérante d'Étoile SARL”); PL: kierowca w bierniku („kierowanego przez Tadeusza Kwiatkowskiego”). EN – Anglia nie
ma numerów działek ewidencyjnych: nieruchomość wskazuje numer tytułu księgi HM Land Registry („title number WK123456”; prefiks
z listy prefiksów hrabstw, numer syntetyczny).

**GPS**: punkt losowany z prostokątów w głębi lądu kraju dokumentu (`OBSZARY_LADOWE`: po kilka na kraj, z dala od wybrzeża
i granic – wiedza ogólna, współrzędne zaokrąglone), więc leży na lądzie w kraju dokumentu; NIE odpowiada miejscowości ani
adresowi z dokumentu (dane syntetyczne – sędziowie nie geokodują, uczestnicy też nie).

## Gold i struktura w manifeście

* **Bez nowych kategorii** – wagi zamrożone (`wagi_punktow.json`). Składnik, który jest kategorią gold trzonu
  (ORGANIZACJA, MIEJSCOWOSC, ADRES), zostaje zwykłym gold, oznaczonym jak w trzonie.
* **Choroba nie jest gold.** Rozpoznania (nazwa choroby, kod ICD) i leki nie należą do gold (`zakres-gold.md`, pkt 6), więc
  składnik `choroba` przypadku `posrednie_rzadka_choroba` jest składnikiem spoza gold (`wartosc_id` = null). Nazwa choroby zostaje
  w tekście jako kontekst identyfikujący (kombinacja: choroba + pracodawca + miejscowość albo rocznik; choroba + szkoła + miejscowość)
  i jest oceniana regułą tokenów słów (`posrednie.KATEGORIA_SLOWNA`) jak funkcja. Pozostałe składniki kombinacji (firma, miejscowość,
  rocznik, szkoła) bez zmian, więc żaden przypadek nie traci sensu (każda kombinacja ma nadal ≥ 2 składniki).
* Składniki **spoza kategorii** (funkcja, wiek, rocznik, choroba, szkoła, numer działki, współrzędne GPS) NIE są gold miary głównej:
  uczestnik, który ich nie zamaskuje, nie ma wycieku. Zapisuje się je wyłącznie w polu `posrednie`.
* Pole `posrednie` wpisu manifestu (`pbench/posrednie.py`, walidacja `posrednie.sprawdz` przy generacji):

```json
[{"id": "k1", "rodzaj": "posrednie_rzadka_choroba",
  "skladniki": [{"id": "k1.firma", "rola": "firma", "tekst": "Delta sp. z o.o.", "miejsce": "tresc",
                 "wartosc_id": "pracodawca.nazwa#1", "rdzen": ["Delta sp. z o.o."]},
                {"id": "k1.rok_urodzenia", "rola": "rok_urodzenia", "tekst": "rocznik 1979", "miejsce": "tresc",
                 "wartosc_id": null, "rdzen": ["1979"]},
                {"id": "k1.choroba", "rola": "choroba", "tekst": "choroba Fabry'ego", "miejsce": "tresc",
                 "wartosc_id": null, "rdzen": ["Fabry'ego"]}]}]
```

  `wartosc_id` – identyfikator wartości `gold_tekst` (ten sam tekst; `miejsce` = miejsce tej wartości po przycięciu do formatu);
  null – składnik spoza gold (zawsze w akapicie treści). `rdzen` – **rdzeń identyfikujący** składnika: fragmenty jego tekstu
  w kolejności (wiek – liczba „47”, rok – rok, szkoła – numer albo nazwa szkoły, działka – numer i identyfikator obrębu
  [„82/26”, „0021”], GPS – liczby współrzędnych bez liter półkul i symboli [„50”, „10”, „32.3”, „11”, „21”, „27.1”], choroba –
  nazwa bez słów rodzajowych „choroba/zespół/disease/Morbus/-Syndrom…”, funkcja, firma, miejscowość, adres – cały tekst).
  Kombinacja ma co najmniej dwa składniki; jedyny wyjątek to role `dzialka` i `gps` (`posrednie.ROLE_JEDNOSKLADNIKOWE`) –
  kombinacje jednoskładnikowe. Tekst każdego składnika występuje w dokumencie **dokładnie raz** (bez
  rozróżniania wielkości liter) – inaczej zamaskowanie jednego wystąpienia nie przerywałoby kombinacji, a sędzia nie odróżniłby
  wystąpień. W pozostałych przypadkach warstwy trudnej pole jest pustą listą; wpisy trzonu go nie mają (trzon bajtowo bez zmian).

## Miara: odsetek kombinacji przerwanych

Kombinacja jest **przerwana** u uczestnika, gdy **co najmniej jeden** jej składnik NIE jest widoczny w wyniku (zamaskowany,
usunięty albo zmieniony). Widoczny = **pełny wyciek RDZENIA** składnika regułą sędziego – tą samą co dla gold. Liczy się tylko
rdzeń: zamaskowanie samej etykiety („-letni”, „rocznik”, „obręb”, „title number”, „Szkoła Podstawowa”, litery półkuli „E”,
symbolu „°”, słowa „choroba”) NIE przerywa kombinacji – reszta nadal wskazuje osobę; zamaskowanie liczby (albo jej cyfry) –
przerywa:

* **tekst** (`sedzia/tekst.py`, pkt 9): fragmenty rdzenia są spanami (rodzaj „pelny” – wszystkie liczące się jednostki
  fragmentów odsłonięte w całości); składnik gold – w spanie jego `wartosc_id`, z kategorią wartości; składnik spoza gold –
  w każdym wystąpieniu tekstu osobno, widoczny, gdy w którymś rdzeń jest w całości odsłonięty;
* **pliki** (`sedzia/plik.py`, „Identyfikacja pośrednia”): składnik to osobna wartość oceniana tymi samymi regułami i widokami
  co gold (wszystkie części pliku, obrazy osadzone i OCR stron z drugim/trzecim odczytem), widoczny = trafienie „pelny” całego
  tekstu ALBO wszystkich odcinków rdzenia (`posrednie.odcinki_rdzenia`: fragmenty rozdzielone tylko znakami niealfanumerycznymi
  tworzą jeden odcinek – „50°10′32.3”). **Ograniczenie sędziego plikowego:** bez offsetów odcinek da się szukać tylko wtedy, gdy
  sam może wyciec (liczba ≥ 4 cyfr, identyfikator ≥ 6 znaków, słowo ≥ 3 znaków), jego pełna wartość jest w tekście oryginału
  dokładnie raz i jest widoczny w oryginale (wspólnie dla wszystkich uczestników). Tak jest dla współrzędnych w obu zapisach,
  numeru tytułu, roku, nazwy szkoły (poza PL) i nazwy choroby; krótkie rdzenie (wiek „47”, numer szkoły PL, krótkie numery
  działki „82/26”, „0021”, „Flur 12”) sędzia plikowy szuka całym tekstem składnika – tam zamaskowanie samej etykiety przerywa
  kombinację na poziomie plików (sędzia tekstowy ocenia rdzeń zawsze).

Kategoria reguły składnika spoza gold (`posrednie.kategoria_reguly`): role `wiek`, `rok_urodzenia`, `szkola`, `dzialka`, `gps` –
reguła identyfikatora (ciąg znaków alfanumerycznych rdzenia; zamaskowany choćby jeden znak liczby przerywa składnik, separatory
i symbole się nie liczą); `funkcja` – reguła tokenów słów (jak nazwy). To wybór reguły, nie kategoria gold i nie waga.

**Przeformatowanie składnika = przerwanie.** Miara mierzy, czy **zapis z dokumentu** pozostał w wyniku, nie czy pozostała
informacja: GPS zamieniony z DMS na stopnie dziesiętne albo zaokrąglony („52.2762” zamiast „52.276167”, dokładność nadal
ok. 10 m), wiek zapisany słownie („czterdziestosiedmioletni”) – liczą się jako przerwanie kombinacji, choć informacja zostaje.
To samo ograniczenie ma miara główna (gold w innym zapisie nie jest wyciekiem); realne narzędzia anonimizacji maskują albo
zostawiają zapis, a nie go przeliczają, więc wpływ praktyczny jest mały – ale wynik „przerwana” nie dowodzi usunięcia informacji. Składnik, który regułą nie może wyciec (brak liczącej się jednostki), albo – w plikach –
nie jest widoczny w ORYGINALE (linia bazowa składników, wspólna dla wszystkich uczestników), czyni kombinację **nieocenioną**
(`przerwana` = null, poza mianownikiem; liczba w `nieocenione`).

Wynik (`posrednie.agreguj`, rekordy `pbench.ocen`): odsetek kombinacji przerwanych per uczestnik (osobno poziom tekst i pliki),
per rodzaj (przypadek), per rola kombinacji jednoskładnikowej (`podrodzaje`: w `posrednie_dzialka_gps` osobno działka i GPS –
rekord kombinacji jednoskładnikowej ma pole `rola`; narzędzie chroniące tylko jedno z nich ma dwie różne liczby zamiast wspólnych
50%) i per język, z przedziałem ufności 95% – bootstrap po dokumentach (1000 powtórzeń, percentylowy; dokument
wchodzi jako całość, bo kombinacje jednego dokumentu nie są niezależne), jak przy innych miarach. Dokument bez wyniku uczestnika
(błąd, timeout, plik nieczytelny, format nieobsługiwany) sędziowie oceniają jak kopię oryginału – **żadna jego kombinacja nie jest
przerwana** (fail-closed). Błąd samego sędziego na dokumencie (`blad_sedziego` w rekordzie) – tak samo: `pbench.ocen` zapisuje
wszystkie kombinacje dokumentu jako nieprzerwane (`posrednie.nieprzerwane`), więc zostają w mianowniku i nie poprawiają wyniku
(zgodnie z `punktacja.md`: dokument z błędem = z wyciekiem) – z wyjątkiem kombinacji nieocenionych na kopii oryginału (`None`
u wszystkich uczestników): te zostają nieocenione także u uczestnika z błędem sędziego, poza mianownikiem (`pbench.ocen` ocenia
wtedy kopię oryginału; gdy i ta ocena się nie uda, wszystkie są w mianowniku); `agreguj` podaje też liczbę rekordów z błędem
sędziego (`bledy_sedziego` – wszystkich, także bez kombinacji).

Uwaga interpretacyjna dla raportu: „przerwana” to warunek konieczny ochrony, nie wystarczający – zamaskowanie samej funkcji przy
nazwie firmy przerywa kombinację, choć czytelnik może domyślić się reszty z kontekstu. Miara mierzy, czy narzędzie w ogóle rusza
informacje pośrednio identyfikujące; uczestnik maskujący tylko kategorie gold przerywa dokładnie kombinacje ze składnikiem gold
(sprawdzone testem `tests/test_h5.py`), a kombinacje działki i GPS (spoza gold) zostawia nietknięte.

## Nadmiarowe maskowanie

Zamaskowanie składnika spoza gold (funkcja, wiek, rocznik, szkoła, działka, GPS) **nie jest nadmiarowym maskowaniem**: sędzia
tekstowy wyłącza wystąpienia tych składników z `fp_znaki`/`fp_spany` (i z precyzji char-F2) – tylko w dokumentach z kombinacjami
(`ocen_tekst(posrednie=…)`). Teksty do wyłączenia dla miary na pliku (P5, tekst wyekstrahowany z wyniku) to te same teksty
składników z pola `posrednie`. T5/P5 liczą się na warstwie `trzon`, więc wyłączenie dotyczy surowych miar FP dokumentów warstwy
trudnej (aneks), nie punktów.
