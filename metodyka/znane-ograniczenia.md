# Znane ograniczenia realizmu trzonu korpusu

Trzon korpusu (1000 dokumentów, ziarno 20261103) ma **opublikowane sumy SHA-256** w prerejestracji
(`metodyka/SHA256SUMS-trzon`), więc jego zawartość nie może się zmienić ani o bajt. Poniższe błędy realizmu językowego trzonu są świadomie **niepoprawiane**; warstwa
trudnych przypadków (`warstwa = "trudne"`) ich nie powtarza (tryb ukraiński odmiany polskiej ma własne reguły).
Test `tests/test_trudne.py::test_trzon_*` pilnuje niezmienności trzonu.

## Odmiana polska: żeńskie nazwiska przymiotnikowe na -iej

`pbench/odmiana_pl.py::_przymiotnikowe` dla płci żeńskiej zawsze dopisuje „-iej”. Dla nazwisk z listy
`_ZENSKIE_PRZYMIOTNIKOWE` (Czarna, Dolna, Górna, Wolna, Konieczna, Mała) daje to formy błędne w dopełniaczu, celowniku i
miejscowniku: „Anny **Czarniej**”, „**Małiej**”, „**Górniej**”, „**Dolniej**”, „**Wolniej**”, „**Konieczniej**”
(poprawnie: Czarnej, Małej, Górnej, Dolnej, Wolnej, Koniecznej; „-iej” jest prawidłowe tylko po k/g, np. Kowalskiej).

- **Liczba wystąpień w trzonie** (zliczone w tekstach `.txt` wszystkich 1000 dokumentów): **1 dokument, 1 wystąpienie**
  („Górniej”; pozostałe formy się nie pojawiają).
- Wpływ na pomiar: wartość gold ma tę samą (błędną) formę co tekst, więc ocena wycieków jest poprawna; zaniżony jest tylko
  realizm języka dwóch dokumentów trzonu.
- Poprawka (`t + ("iej" if t[-1] in "kg" else "ej")`) zmieniłaby te dwa dokumenty i sumy kontrolne trzonu – nie wolno jej
  wprowadzać do domyślnego trybu; tryb ukraiński (`ukrainskie=True`) stosuje już poprawną końcówkę.

## Odmiana polska: żeńskie imiona i nazwiska na -szka/-czka

Warunek przymiotnikowy w `pbench/odmiana_pl.py::_slowo` (końcówki „-ska/-cka/-dzka/-zka”) łapie też rzeczowniki na
„-szka”/„-czka”, więc żeńskie „Agnieszka”, „Gruszka”, „Pietruszka”, „Tyszka” odmieniają się jak „Kowalska”: dopełniacz,
celownik i miejscownik „**Agnieszkiej**” (poprawnie: Agnieszki, Agnieszce), biernik „**Agnieszką**”, „**Gruszką**” (poprawnie:
Agnieszkę, Gruszkę); narzędnik „Agnieszką” jest poprawny.

- **Liczba wystąpień w trzonie** (zliczone w tekstach `.txt` wszystkich 1000 dokumentów): formy błędne w dopełniaczu, celowniku
  i miejscowniku – **35 wystąpień w 21 dokumentach** („Agnieszkiej” 29, „Pietruszkiej” 5, „Gruszkiej” 1). Biernik „Agnieszką”
  występuje 4 razy w 4 dokumentach; formy tej samej postaci w narzędniku są poprawne, więc liczba błędnych bierników nie została
  rozdzielona (nie wchodzi do sumy 35).
- Wpływ na pomiar: wartość gold ma tę samą (błędną) formę co tekst, więc ocena wycieków jest poprawna; zaniżony jest realizm
  języka (forma, której model NER może nie znać jako imienia).
- Warstwa trudna ma poprawkę: `generuj_dokument_trudny` włącza `odmiana_pl.odmiana_trudna()` (odmiana rzeczownikowa „-szka/
  -czka/-żka”; „-dzka”, np. Grodzka, Zawadzka, zostaje przymiotnikowa). Tryb domyślny – bez zmian (sumy kontrolne trzonu).

## Odmiana polska: -sia/-cia/-zia po stronie żeńskiej

`_zenskie_a` odmienia imiona na -sia/-cia/-zia jak -ia po samogłosce („Basia → Basii”, poprawnie: Basi). Słownik polski
trzonu nie zawiera takich imion, więc w trzonie nie występuje (0 wystąpień; imię „Stefania” z końcówką -nia ma poprawne
„Stefanii”). Błąd jest naprawiony wyłącznie w trybie ukraińskim (Łesi, Orysi), dla spójności z innymi poprawkami tego trybu.

## Warstwa trudna: dane do ręcznej weryfikacji

- Kody sądów w numerach spraw ukraińskich (`pbench/dane/uk.py`: 761 Шевченківський район Києва, 910 Господарський суд
  м. Києва itd.) wpisano z wiedzy ogólnej, bez sprawdzenia w rejestrze court.gov.ua; to dane syntetyczne, ale kod ma być
  wiarygodny.
- ISO 9:1995: apostrof zapisywany jest jako ʼ (U+02BC); brak pewnego źródła normy co do znaku w wyniku (U+2019 albo
  U+02BC), więc wybór pozostawiono (opis w docstringu `translit._iso9`).
- Notarialne poświadczenie nie podaje okręgu notarialnego („Київського міського нотаріального округу”): wymagałoby
  przymiotnikowej formy nazwy miasta w słowniku miejscowości.

## Znane ograniczenia korpusu (przegląd ręczny, J1)

Liczby zliczone w korpusie; trzon bez zmian (sumy kontrolne), wpływ na pomiar opisany przy każdym punkcie.
Reguły sędziów i polityka gold: `metodyka/zakres-gold.md`.

- **Płeć imienia i nazwiska (S5).** Polski słownik nazwisk (`dane/slowniki/pl/nazwiska.txt`) zawiera żeńską formę „Sadowska”,
  którą generator daje też mężczyznom („Andrzej Sadowska”): w trzonie **3 wystąpienia w 3 dokumentach**. Polska lista płac
  przypisuje stanowiska cyklicznie, a „Księgowa” ma tylko formę żeńską („Krystian Górny … Księgowa”): **222 wiersze w 25 listach
  płac** trzonu (imię męskie ze słownika `imiona_m.txt`). Wpływ: gold ma tę samą formę co tekst, więc ocena wycieków jest poprawna; zaniżony jest realizm (model NER może
  reagować inaczej niż na prawdziwe dane). Warstwa trudna (nie zamrożona) ma poprawkę: `generuj_dokument_trudny` włącza
  `dane.zgodna_plec()` (mężczyzna dostaje formę męską nazwiska – ten sam ciąg losowań), a szablony warstwy trudnej
  (`szablony.SZABLONY_TRUDNE`) mają w polskiej liście płac stanowisko zgodne z płcią osoby (`{pNNN.rodzaj:Księgowy|Księgowa}`).
- **Zdublowana etykieta sygnatury (B).** Angielski szablon pozwu ma „Claim No. {court.sygnatura}”, a sygnatura brytyjska już
  zawiera „Claim No.”, więc tekst brzmi „Claim No. Claim No. QB-2020-014548”: **2 dokumenty** (`en-pozew-0001`, `en-pozew-0006` – oba
  split test). Gold obejmuje jedną etykietę z numerem; druga etykieta jest poza gold, a słowa etykiet sędziowie
  pomijają (`zakres-gold.md`, pkt 2) – bez wpływu na wyciek; jej zamaskowanie liczy się do FP (kilka znaków).
- **Zakres ZDROWIE (E).** W korpusie rozpoznania (nazwa choroby, kod ICD) i leki **nie są gold** (`zakres-gold.md`, pkt 6): ich tekst
  jest w dokumencie, a zamaskowanie liczy się jako nadmiarowe maskowanie (FP / P5). Tak samo nie są gold listy wykonanych badań
  w polskich wypisach ani cel skierowania w polskim skierowaniu. Wpływ: uczestnik maskujący dane o zdrowiu ma wyższy FP; wyciek bez zmian.
  Dane o zdrowiu pacjenta (kto i na co choruje) pozostają w tekście – ocena ochrony samej diagnozy jest poza zakresem.
- **Dokumenty prywatne.** Trzy nowe typy (`umowa_najmu`, `umowa_sprzedazy_auta`, `pozew_zaplata_osoby`, 67 dokumentów) mają strony
  będące osobami fizycznymi. Ograniczenia: (a) liczność typów prywatnych rozkłada się na języki proporcjonalnie do udziału zwolnionych
  miejsc medycznych (PL ok. 39, pozostałe języki po 7–8), nie równo; (b) numer VIN i numer księgi wieczystej nie istnieją w generatorach
  (kategoria `KSIEGA_WIECZYSTA` występuje w warstwie trudnej, ale nie jest polem encji), więc umowy auta i najmu ich nie zawierają;
  samochód identyfikuje numer rejestracyjny, lokal – adres; (c) lokal najmu jest identyfikowany adresem dotychczasowego mieszkańca
  (osoba z generatora, której adres jest adresem lokalu); (d) teksty prawne (przepisy o najmie, sprzedaży, powództwie) są streszczone
  w jednym akapicie i nie zastępują poradnika prawnego – syntetyczne.
- **Kwoty (C, S4).** `KWOTA` (waga 1) dominuje liczbę wycieków uczestników, którzy z założenia nie maskują kwot (listy płac: ok.
  200 kwot na dokument; Privatizer ma kategorię domyślnie wyłączoną). Wagi kategorii: `wagi_punktow.json`; obok miary głównej
  raportowana jest miara pomocnicza „w deklarowanym zakresie” (`zakres-gold.md`, pkt 4).

## Decyzje właściciela przed prerejestracją (2026-11-02)

- **Nazwy firm – „Skanska Projekt”.** Polski słownik rdzeni nazw firm trzonu (`pbench/dane/slowniki/pl/firmy_rdzenie.txt`)
  zawiera rdzeń „Skanska Projekt”, podobny do nazwy istniejącej marki: w trzonie **8 dokumentów, 19 wartości gold**
  (`ORGANIZACJA`; `gold_tekst` manifestu). Wszystkie nazwy firm w korpusie są fikcyjne, a podobieństwo do istniejących podmiotów jest przypadkowe – nazwa
  nie odnosi się do żadnej rzeczywistej spółki ani jej danych. Trzon zostaje bez zmian (zmiana zmieniłaby opublikowane sumy
  kontrolne), adnotacja trafia do raportu i do opisu korpusu.
- **Licencja modelu `flair/ner-multi`.** Karta modelu na Hugging Face nie ma pola licencji (biblioteka Flair – MIT). Model zostaje
  w benchmarku (uczestnik `flair`, grupa B) z adnotacją w raporcie: karta bez licencji, model pobierany przez użytkownika z
  oficjalnego repozytorium (rewizja i suma wag w `uczestnicy/flair/KONFIG.md`), **wagi nie są redystrybuowane** – benchmark
  publikuje tylko wyniki i kod uruchamiający.

## Punktacja

T1/P1/T3/P3/T4 są ważone kategorią (waga dokumentu = najwyższa waga wyciekłej kategorii / 3;
`metodyka/punktacja.md`, wagi w `metodyka/wagi_punktow.json`). Wagi kategorii (3/2/1) i punktów testów są zapisane w
prerejestracji.

## Generatory identyfikatorów: poprawki, telefony i pozycje niezweryfikowane

Weryfikacja generatorów w źródłach dała poprawki: PL – numer PWZ nie
zaczyna się od 0 (NIL), kody wydziałów KW LU1S i ZG1E (zał. 1 do rozp. MS, Dz.U. 2024 poz. 1583), numery rejestracyjne wg zał. 13 i
§ 30–31 rozp. MI (Dz.U. 2024 poz. 1709: tylko prefiksy z załącznika, bez liter B, D, I, O, Z, układy dozwolone dla długości
prefiksu, część cyfrowa niezerowa); UA – kod regionu tablicy z listy ДСТУ 4278:2004; DE – SVNR (obszary wg VKVV), kod grupy LANR
(01–69, 85, 87, 91, 99; KBV Anlage 2), Personalausweis (cyfry 1–9); FR – tablice bez WW i SS; GB – NINO bez NC, PY, PZ (HMRC
NIM39110), IBAN SRLG z sort code 60, druga litera tablicy bez I, Q, Z (DVLA INF104), kody pocztowe z ograniczonym numerem dystryktu.
Każda poprawka ma test z N próbkami (`tests/test_generatory_zrodla.py`).

**Telefony.** Wszystkie telefony są wyraźnie fikcyjne i NIE muszą przechodzić walidacji libphonenumber:

* GB – pule Ofcom „Numbers for drama” (w tym komórkowe 07700 900000–900999); US – tylko 555-0100–0199; DE – pule Bundesnetzagentur
  „Drama Numbers” (030 23125, 040 66969, 069 90009, 089 99998, 0221 4710 oraz zarezerwowane numery komórkowe z listy BNetzA); FR – sześć
  racines ARCEP (decyzja 2018-0881): 01 99 00, 02 61 91, 03 53 01, 04 65 71, 05 36 49, 06 39 98.
* PL, ES, UA – oficjalnej puli fikcyjnej nie ma (UKE, CNMC, NKRZI), więc przyjęto regułę (wybór właściciela): numer krajowy zaczyna się od `00`,
  a długość i grupowanie są jak w realnym formacie kraju. PL: `+48 000 123 456` / `000 123 456`; ES: `+34 000 12 34 56` /
  `000 123 456`; UA: `+380 00 123 45 67` / `0 00 123 45 67` (kod operatora 00). Taki prefiks nie istnieje w żadnym z tych planów.
* **Wpływ na pomiar:** część narzędzi może nie rozpoznać takich numerów jako telefonów (zwłaszcza walidujących libphonenumber), co może
  obniżyć ich wykrywalność. Dotyczy to wszystkich uczestników jednakowo. W pozostałych krajach numery pochodzą z oficjalnych pul fikcyjnych.

**Rachunki bankowe** zostają bez zmian: numery IBAN mają poprawne cyfry kontrolne i długości, ale kody banków/oddziałów i numery kont są
losowe, więc mogą przypadkiem odpowiadać istniejącym rachunkom (DE: 27 realnych BLZ z Bundesbank, losowe konto; ES: kody banków
z rejestru BdE 2018, z historycznymi 0075/0030/0487; FR: cztery kody banków niepotwierdzone; PL i UA: kody banków niepotwierdzone).

**Kody pocztowe GB.** Raport C nie wskazał źródła maksimów dystryktów: potwierdzone zakresy dotyczą tylko HG (1–5), SP (1–11), FY (1–8),
TF (1–13); dla pozostałych obszarów zawężono dystrykt do 1–5, co nie gwarantuje istnienia kodu (np. brak dystryktów 1–10 w LL, NP).

**Pozycje NIEZWERYFIKOWANE (bez zmian; szczegóły i źródła w tej sekcji):**

* PL/UA (A): KRS (format), dowód osobisty (zakres liter serii), prefiksy banków PL, sygnatury sądowe PL, kody pocztowe PL; UA: ID-картка,
  paszport zagraniczny (zbiór liter serii), IBAN UA i kody MFO, kody sądów i numery spraw, indeksy pocztowe UA (brak dostępu do zakon.rada.gov.ua,
  bank.gov.ua, reyestr.court.gov.ua, ewib.nbp.pl).
* DE/FR (B): kody pocztowe DE i FR, tablice DE (zakazane pary NS, SS, SA, HJ, KZ, SD – do potwierdzenia), Aktenzeichen DE, klucz RIB, kody
  banków FR (30006, 10278, 18206, 16798), RG/pourvoi FR; Steuernummer – bez cyfry kontrolnej landowej; KVNR, TVA FR, NIR, USt-IdNr – algorytmy
  potwierdzone tylko źródłami wtórnymi.
* GB/US/ES (C): VAT GB (algorytm), ZIP US, sygnatury i cytaty GB/US (wzorce poglądowe), NUSS (algorytm kontrolny), numer colegiado (format),
  kody pocztowe ES, ECLI/STS, tablice ES; ograniczenie pierwszej cyfry NHS (4/6/7) i GMC (1–7) oraz obszaru SSN (1–772) to podzbiory ważnych wartości.
