# Źródła słowników generatorów (pbench/dane/slowniki)

Wszystkie słowniki służą wyłącznie do **generowania danych syntetycznych** (wartości wstawianych do dokumentów
testowych). Nie zawierają danych osobowych żadnej rzeczywistej osoby: imiona i nazwiska to pojedyncze
najczęstsze elementy statystyczne (fakty o języku i populacji, nie dane o osobach), a kombinuje je generator losowo.

## Jak powstały

Celowo **nie pobieraliśmy** żadnych zbiorów z internetu (nic nie trafiło do `vendor/`). Listy **zostały ułożone ręcznie** (z pamięci autora) na podstawie wiedzy o publicznych rejestrach
statystycznych wymienionych niżej, w przybliżonej kolejności częstości (od najczęstszych; generator losuje z wagą
malejącą z pozycją). Nie są to wiernie przepisane tabele ani kopie baz – to własne kompilacje faktów
(nazwy własne, nazwy ulic i miejscowości, kody ICD-10, nazwy międzynarodowe INN leków), które nie podlegają
ochronie prawa autorskiego. Kolejność i rozmiary są orientacyjne; benchmark nie zależy od dokładnego rozkładu.

Zapis w pliku: jedna pozycja na linię. Wyjątki: `miejscowosci.txt` zawiera po znaku `|` pomocnicze pole
(PL: dwie pierwsze cyfry kodu pocztowego; ES: kod prowincji; DE: pierwsze dwie cyfry PLZ; FR: departament;
EN: `Miasto|GB|OBSZAR` albo `Miasto|US|STAN|ZIP3`); `choroby.txt` – `KOD_ICD10 opis w języku dokumentu`.

## Pliki i źródła statystyczne

| Pliki | Źródło wiedzy (publiczne) | Licencja / status |
|---|---|---|
| `pl/imiona_m.txt`, `pl/imiona_k.txt`, `pl/nazwiska.txt` | Rejestr PESEL – liczba osób według imion i nazwisk (dane.gov.pl, Ministerstwo Cyfryzacji / GUS) | Dane publiczne udostępnione na otwartej licencji CC0 1.0 (dane.gov.pl); do słownika trafiła wyłącznie własna, skrócona i przetasowana lista pojedynczych imion/nazwisk |
| `pl/ulice.txt`, `pl/miejscowosci.txt` | TERYT/SIMC/ULIC (GUS) – nazwy najczęstszych ulic i miejscowości | Dane publiczne; własna kompilacja nazw własnych |
| `en/imiona_m.txt`, `en/imiona_k.txt` | Popularne imiona w Wielkiej Brytanii (ONS – „Baby names in England and Wales”, Open Government Licence v3.0) i USA (SSA – „Popular Baby Names”, domena publiczna) | OGL v3.0 / domena publiczna USA; własna kompilacja |
| `en/nazwiska.txt` | Najczęstsze nazwiska USA (U.S. Census Bureau – „Frequently Occurring Surnames”, domena publiczna) uzupełnione o typowe nazwiska brytyjskie | Domena publiczna USA; własna kompilacja |
| `en/ulice.txt`, `en/miejscowosci.txt` | Typowe nazwy ulic GB/USA; największe miasta GB (ONS) i USA (Census Bureau), prefiksy kodów pocztowych (Royal Mail – tylko obszary, nie adresy) i ZIP3 | Fakty geograficzne; własna kompilacja |
| `es/imiona_m.txt`, `es/imiona_k.txt`, `es/nazwiska.txt` | INE (Instituto Nacional de Estadística) – „Nombres y apellidos más frecuentes” | Reutilización de información INE (aviso legal: reutilización permitida z podaniem źródła); własna kompilacja pojedynczych imion/nazwisk |
| `es/ulice.txt`, `es/miejscowosci.txt` | Typowe nazwy ulic (stcallejero) oraz municipios (INE) z kodem prowincji | Fakty; własna kompilacja |
| `de/imiona_m.txt`, `de/imiona_k.txt`, `de/nazwiska.txt` | Statystyki imion i nazwisk w Niemczech (Destatis, GfdS – listy najczęstszych) | Fakty statystyczne; własna kompilacja (bez kopiowania tabel) |
| `de/ulice.txt`, `de/miejscowosci.txt` | Typowe nazwy ulic niemieckich, największe miasta (Destatis) z początkiem PLZ | Fakty; własna kompilacja |
| `fr/imiona_m.txt`, `fr/imiona_k.txt`, `fr/nazwiska.txt` | INSEE – „Fichier des prénoms” i „Fichier des noms de famille” | Licence Ouverte / Open Licence v2.0 (Etalab) – dozwolone ponowne wykorzystanie z podaniem źródła; własna kompilacja pojedynczych pozycji |
| `fr/ulice.txt`, `fr/miejscowosci.txt` | Typowe nazwy ulic (Base Adresse Nationale – wzorce) i communes (INSEE COG) z departamentem | Licence Ouverte v2.0 / fakty; własna kompilacja |
| `*/firmy_rdzenie.txt` | Własne, wymyślone rdzenie nazw firm (bez prawdziwych podmiotów; ewentualne zbieżności są przypadkowe) | Własne dzieło autora benchmarku (CC0) |
| `*/choroby.txt` | ICD-10 (WHO) – kody i krótkie nazwy rozpoznań w tłumaczeniu na język dokumentu (PL: oficjalne tłumaczenie CSIOZ/ICD-10; DE: BfArM/DIMDI ICD-10-GM; FR: ATIH/CIM-10; ES: Ministerio de Sanidad/CIE-10-ES; EN: WHO/ICD-10) | Kody klasyfikacji są faktami; nazwy skrócone i sparafrazowane przez autora |
| `*/leki.txt` | Międzynarodowe nazwy nieopatentowane (INN, WHO) w lokalnej pisowni | Nazwy INN są publicznie dostępne (domena publiczna WHO) |
| słowniki w `pbench/trudne_posrednie.py` (H5) | Choroby rzadkie – wiedza ogólna (choroby z list chorób rzadkich typu Orphanet, nazwy w języku dokumentu); małe miejscowości – nazwy wsi i gmin (fakty geograficzne; pary miejscowość–gmina syntetyczne); funkcje i nazwy szkół bez nazw własnych osób; pary funkcja – forma prawna (wiedza ogólna o prawie spółek PL/DE/FR/ES/UK); obszary lądowe GPS – prostokąty w głębi lądu (wiedza ogólna o położeniu regionów, współrzędne zaokrąglone); prefiksy numerów tytułu HM Land Registry (tylko format, numery syntetyczne) | Fakty / własna kompilacja autora (CC0) |

## Zastrzeżenia

* **Do weryfikacji przed publikacją repozytorium:** nazwy licencji w tabeli podano według wiedzy autora; nie
  sprawdzaliśmy ich online. Ponieważ w repozytorium nie ma kopii żadnego zbioru (tylko własne kompilacje faktów),
  ryzyko jest niskie, ale warunki ponownego wykorzystania warto potwierdzić przy wydaniu publicznym.

* Listy nie są pobraniem ani kopią któregokolwiek ze wskazanych zbiorów – pochodzą z wiedzy autora o tych
  zbiorach. Jeśli ktoś zażąda wglądu w pochodzenie pozycji: zob. wyżej, każda pozycja jest pospolitym imieniem,
  nazwiskiem, nazwą ulicy/miejscowości, kodem ICD-10 lub nazwą INN.
* Zakresy numerów (PESEL, NIP, IBAN, telefony…) generujemy algorytmicznie; opisy w docstringu `pbench/dane/wspolne.py`.

## Słowniki profilowe ES (uzupełnienie)

| Pliki | Źródło wiedzy (publiczne) | Licencja / status |
|---|---|---|
| `es/choroby_cardiologia.txt`, `es/choroby_interna.txt` | CIE-10-ES / ICD-10 (WHO) – podzbiory rozpoznań kardiologicznych i internistycznych, nazwy skrócone i sparafrazowane przez autora | Kody klasyfikacji są faktami; nazwy własne autora benchmarku |
| `es/leki_cardiologia.txt`, `es/leki_interna.txt` | Nazwy INN (DCI w Hiszpanii) leków w pisowni hiszpańskiej wraz z typowymi dawkami (dawki po znaku pionowej kreski i średnikach, przecinek dziesiętny) | Nazwy INN są publicznie dostępne (domena publiczna WHO); dawki – fakty farmakologiczne |

## Słowniki profilowe DE (uzupełnienie)

| Pliki | Źródło wiedzy (publiczne) | Licencja / status |
|---|---|---|
| `de/choroby_kardiologie.txt`, `de/choroby_innere.txt` | ICD-10-GM (BfArM) / ICD-10 (WHO) – podzbiory rozpoznań kardiologicznych i internistycznych (kody 3–4-znakowe), nazwy skrócone i sparafrazowane przez autora | Kody klasyfikacji są faktami; nazwy własne autora benchmarku |
| `de/leki_kardiologie.txt`, `de/leki_innere.txt` | Nazwy INN leków w pisowni niemieckiej wraz z typowymi dawkami w mg (dawki po znaku pionowej kreski i średnikach, przecinek dziesiętny) | Nazwy INN są publicznie dostępne (domena publiczna WHO); dawki – fakty farmakologiczne |

## Słowniki profilowe FR (uzupełnienie)

| Pliki | Źródło wiedzy (publiczne) | Licencja / status |
|---|---|---|
| `fr/choroby_cardiologie.txt`, `fr/choroby_cardiologie_glowne.txt`, `fr/choroby_medecine_interne.txt` | CIM-10 (WHO, wersja francuska) – podzbiory rozpoznań kardiologicznych (główne: niewydolność serca; współistniejące) i internistycznych, nazwy skrócone i sparafrazowane przez autora | Kody klasyfikacji są faktami; nazwy własne autora benchmarku |
| `fr/leki_cardiologie.txt`, `fr/leki_medecine_interne.txt` | Nazwy DCI (INN) leków w pisowni francuskiej wraz z typowymi dawkami w mg (dawki po znaku pionowej kreski i średnikach, przecinek dziesiętny) | Nazwy INN są publicznie dostępne (domena publiczna WHO); dawki – fakty farmakologiczne |

## Słowniki UK – warstwa trudnych przypadków (H1; ukraiński, dane wyłącznie ukraińskie)

Listy ułożone **ręcznie** z wiedzy ogólnej autora (nie skopiowane z żadnego zbioru); **nie użyto** niczego z danych
treningowych modelu (kontaminacja). Nazwiska osób publicznych pominięte
(a pary typu Тарас Шевченко generator odrzuca).

| Pliki | Źródło wiedzy (publiczne) | Licencja / status |
|---|---|---|
| `uk/imiona_m.txt`, `uk/imiona_k.txt`, `uk/imiona_ojcow.txt`, `uk/nazwiska.txt` | Powszechna wiedza o częstych ukraińskich imionach, imionach po ojcu (tabela: ukr. męskie/żeńskie, ros. męskie/żeńskie) i nazwiskach różnych typów (-енко, -ук/-юк, -ський/-цький, -ич, -ак, -ов/-єв, -ець, na -а, nieodmienne). Druga kolumna po `|` to **rosyjska pisownia** tego samego imienia/nazwiska osoby ukraińskiej (dozwolony, oznaczany przypadek `pisownia_rosyjska_imion`) | Fakty językowe; własna kompilacja pojedynczych pozycji |
| `uk/ulice.txt`, `uk/miejscowosci.txt` | Typowe nazwy ulic (bez radzieckich i rosyjskich) oraz miasta z obwodem, dwucyfrowym prefiksem kodu pocztowego i numerem strefowym telefonu (`miasto\|obwód\|prefiks\|strefa`); kody dobrane do obwodu | Fakty geograficzne; własna kompilacja |
| `uk/firmy_rdzenie.txt` | Własne, wymyślone rdzenie nazw firm (ТОВ/ПП/АТ/ФОП) | Dzieło własne (CC0) |
| `uk/choroby.txt`, `uk/choroby_interna.txt`, `uk/leki.txt`, `uk/leki_interna.txt` | МКХ-10 (ICD-10, WHO) – kody i krótkie nazwy po ukraińsku (parafrazowane); nazwy INN leków po ukraińsku z typowymi dawkami w mg | Kody klasyfikacji i nazwy INN są faktami |

Identyfikatory (РНОКПП, ЄДРПОУ, IBAN UA, ID-картка, паспорт) generuje kod z poprawnymi sumami kontrolnymi (testy:
`python-stdnum` `stdnum.ua.rntrc`/`stdnum.ua.edrpou`); dane wyłącznie syntetyczne.

## Dane fikcyjne (wszystkie języki)

Korpus jest syntetyczny. Wszystkie cytowane orzeczenia, numery spraw (sygnatury, RG, Aktenzeichen, Claim No, Rollo…),
oznaczenia publikacji i cytaty w szablonach (PL, EN, ES, DE, FR) są **fikcyjne** – generowane losowo w realistycznym
formacie; nie odnoszą się do rzeczywistych orzeczeń ani spraw. To samo dotyczy osób, firm, adresów i identyfikatorów.

## Renderer DOCX – zasoby graficzne i ograniczenia (Zadanie 5)

* **Logo kancelarii** (`pbench/render/logo.py`): rysowane programowo (formy geometryczne + nazwa firmy), krój DejaVu Sans
  Bold z systemu (licencja Bitstream Vera/DejaVu – dowolne użycie). Bez znaków towarowych, nic nie pobrano.
* **Podpis odręczny** (`pbench/render/podpis.py`): obraz renderowany krojem URW Z003 Medium Italic z systemu
  (`/usr/share/fonts/opentype/urw-base35/`, pakiet fonts-urw-base35, wydanie URW++ na AGPL z wyjątkiem dla fontów, nie OFL).
  Krój nie jest kopiowany ani osadzany w repozytorium ani w korpusie – w plikach są wyłącznie wyrenderowane PNG podpisów.
* **Zdjęcie twarzy w CV (utrudnienie `zdjecie`) – NIE zaimplementowane.** Nie znaleziono (i nie pobierano) źródła
  syntetycznych twarzy z całkowicie pewną licencją CC0/domena publiczna zezwalającą na redystrybucję, a twarze
  prawdziwych osób są wykluczone. Utrudnienie jest pomijane (renderer je przyjmuje bez efektu; nie należy do
  `UTRUDNIENIA_DOCX`) i musi trafić do ograniczeń badania. Decyzja o ewentualnym źródle należy do kontrolera.
