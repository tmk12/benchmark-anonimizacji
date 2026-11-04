# Prerejestracja (wersja `prerejestracja-1`)

**Stan: ZAMROŻONY.** Data zamrożenia: 2026-11-04. Zamrożenie potwierdza tag git `prerejestracja-1` (wskazuje commit
zamrożenia). Po zamrożeniu każda zmiana miar, reguł sędziów, kalibracji,
korpusu albo uczestników to nowa wersja opisana w raporcie razem z wynikami obu wersji (pkt 9).

Dokument jest prerejestracją punktacji (`metodyka/punktacja.md`; wagi
`metodyka/wagi_punktow.json`): wszystko, co `punktacja.md` zostawiła na czas po pilocie („Ustalane po pilocie na dev”), oraz
definicje operacyjne miar, reguły sędziów, kalibrację, uczestników, korpus i środowisko oceny zapisuje w brzmieniu obowiązującym
dla przebiegu na splicie test **korpusu**. Sposób liczenia T1, T3, T4, P1 i P3 – pkt 3.2 i 1.1; zakres gold –
`metodyka/zakres-gold.md`, pkt 6.

**Stan splitu test w chwili zamrożenia.** Żaden uczestnik nie został uruchomiony ani oceniony sędzią na splicie test korpusu
(w repozytorium nie ma żadnych wyników: ani surowych, ani ocen); nikt nie zna wyników testu. Surowe przebiegi testu i oceny powstają
dopiero po zamrożeniu; kalibracja (pkt 4) jest wykonana przed nim, wyłącznie na dev. Do punktów wchodzą wyłącznie przebiegi z progami i kodem uczestników z commitu
zamrożenia (dowód: `wersje.json` przebiegu, `prog.json`), ocenione sędzią z commitu zamrożenia.

## 1. Uzupełnienia dozwolone po pilocie

### 1.1. T3 i P3 – które przypadki są punktowane

„Średnia po przypadkach tekstowych” (T3) i „jak T3, sędzia plikowy” (P3) liczy się po przypadkach z funkcji
`pbench.przypadki.przypadki_punktowane(poziom)` – agregacja wybiera przypadki wyłącznie nią (rozkład i uzasadnienie:
`metodyka/przypadki.md`):

- **T3 – 18 przypadków** (`przypadki_punktowane("tekst")`: rejestr bez `POSREDNIE` i bez `TYLKO_PLIK`): `odmiana_nazwisk`,
  `nazwiska_zwykle_slowa`, `zdrobnienia`, `nazwisko_imie`, `parafy`, `liczby_slownie`, `cyrylica_dokument_uk`, `cyrylica_wstawka`,
  `transliteracja`, `homoglify`, `pisownia_rosyjska_imion`, `skroty_po_pelnym`, `granica_okna`, `dlugie_listy_osob`,
  `znaki_zerowej_szerokosci`, `rtl`, `przeniesienia`, `cytowane_watki_vcard`.
- **P3 – 30 przypadków** (`przypadki_punktowane("plik")`): 18 powyższych oraz 12 z trudnością wyłącznie w pliku (`TYLKO_PLIK`):
  `ukryta_docx`, `ukryta_xlsx`, `ukryta_pptx`, `ukryta_pdf`, `ukryta_poczta`, `zepsuty_tounicode`, `dwie_kolumny`,
  `obrocone_strony`, `skan_pieczatki`, `zrzut_ekranu`, `znak_wodny`, `formaty_rtf_odt`.
- **Poza obiema średnimi:** `posrednie_funkcja_firma`, `posrednie_rzadka_choroba`, `posrednie_wiek_miejscowosc`,
  `posrednie_dzialka_gps` – identyfikacja pośrednia, osobna miara opisowa (pkt 3.4).

Przypadek `TYLKO_PLIK` ma wartości przypadku tylko w `gold_plik`/`gold_obrazy`, a tekst poziomu 1 jest zwykłym tekstem
dokumentu – w T3 nie mierzyłby swojej trudności, więc wchodzi tylko do P3.

Wzór: dla przypadku *p* – dokumenty warstwy `trudne` splitu test, które mają *p* w polu manifestu `przypadki` (dokument z kilkoma
przypadkami liczy się w każdym); wynik przypadku = 1 − Σ_{d ∈ przypadek} s(d) / liczba dokumentów przypadku, gdzie s(d) to waga wycieku
dokumentu (pkt 3.2: najwyższa waga kategorii wśród wyciekłych wartości gold dokumentu, podzielona przez 3; fail-closed
s = 1, pkt 3.1). T3 (P3) = średnia arytmetyczna wyników przypadków, każdy przypadek z tą samą wagą. Ukraiński (`uk`) wchodzi jako przypadek; język przetwarzania dokumentu `uk` – reguła języka zastępczego
(`metodyka/uczestnicy.md`, „Język zastępczy”).

### 1.2. `t_ref` i pomiar czasu (T6, P7)

`punktacja.md`: wynik = min(1, `t_ref` / *t*), *t* = mediana s/stronę na maszynie referencyjnej. Wynik ma być **niezależny od
innych uczestników** („dodanie lub usunięcie konkurenta nie zmienia cudzych punktów”), więc `t_ref` jest **stałą** ustaloną przed
jakimkolwiek pomiarem czasu na maszynie referencyjnej (pomiary – `pbench-czas`, po zamrożeniu).

**Wartość: `t_ref` = 1,0 s na stronę obliczeniową, ta sama dla T6 i P7**.

Uzasadnienie:

1. **Kotwica w odczuciu użytkownika, nie w uczestnikach.** Klasyczne progi czasu odpowiedzi (Nielsen, *Usability Engineering*,
   1993, rozdz. 5: 0,1 s / 1 s / 10 s) wskazują 10 s jako granicę utrzymania uwagi na zadaniu. Przy 1 s/stronę typowy
   10-stronicowy dokument kancelarii jest gotowy w ≤ 10 s – prawnik czeka, nie przełącza się do innej pracy. Szybciej niż
   1 s/stronę różnica jest dla użytkownika niezauważalna, więc pełne punkty; wolniej – punkty maleją proporcjonalnie
   (2 s/stronę → 0,5; 10 s/stronę → 0,1; brak progu odcięcia).
2. **Niezależność i brak dopasowania do wyników.** Stała nie zależy od zbioru uczestników ani od ich czasów. Odrzucona
   alternatywa „mediana s/stronę grupy A na pilocie” (≈ 2,5 s/stronę) zależałaby od składu grupy (dodanie wolnego uczestnika
   przesuwa `t_ref` i cudze punkty – sprzeczne z `punktacja.md`), a czasy pilota mierzono na serwerach trafności przy równoległym
   obciążeniu, nie na maszynie referencyjnej. Odrzucona też skala względna (czas najszybszego uczestnika) – z tego samego powodu.
3. **Jedna wartość dla tekstu i plików.** Użytkownik czeka na cały wynik; odczyt pliku, OCR skanu i zapis są kosztem, który
   ponosi. Narzędzia plikowe mają przez to zwykle niższy wynik P7 niż tekstowe T6 – rankingi są rozłączne, więc to nie
   faworyzuje nikogo w obrębie rankingu.
4. **Ograniczony wpływ.** T6 i P7 to po 50 z 1000 pkt; żadna wartość `t_ref` nie zmieni sumy o więcej niż 50 pkt. Aneks
   wrażliwości pokaże dodatkowo (opisowo, bez zmiany punktów) wyniki T6/P7 przy `t_ref` 0,5 i 2,0 s/stronę.

**Strona obliczeniowa** = 1800 znaków tekstu poziomu 1 dokumentu (plik `.txt` z generatora – ten sam tekst dostaje każdy uczestnik
tekstowy; znaki Unicode ze spacjami i znakami nowej linii; polska „strona znormalizowana”). Liczba stron dokumentu
= max(1, znaki / 1800) – ta sama dla wszystkich uczestników i formatów (bez zależności od renderu DOCX/XLSX); dolna granica 1
nie karze krótkich dokumentów (e-maile, ok. 11% dev ma < 1800 znaków) za stały narzut wywołania.

**Maszyna referencyjna: Apple M1** (MacBook Pro 13″ 2020, `MacBookPro17,1`, 8 rdzeni: 4 wydajne + 4
energooszczędne, 8 GB RAM, macOS). Uzasadnienie: fizyczny, niezmienny sprzęt (maszyna wirtualna Windows
Server w chmurze, typ `e2-standard-4`, dostaje przy każdym starcie dowolną platformę CPU – w testach obciążeniowych trafiła na
Xeon Broadwell 2,2 GHz – więc pomiar nie byłby powtarzalny); typowa dla laptopa biurowego ilość pamięci; najwolniejsza maszyna
zestawu (konserwatywnie – nikt nie korzysta z procesora serwerowego); obsługiwana natywnie przez Privatizera (Apple Silicon)
i przez wszystkich uczestników OSS (torch na CPU, macOS arm64). Pozostałe maszyny czasu (Apple M4, Windows Server,
drugi Windows) – czasy raportowane opisowo, bez punktów.

**Ustawienia pomiaru** (implementacja `pbench-czas`, zadanie 18):

- **Próbka:** 60 dokumentów trzonu ze splitu **test korpusu** – PL 30, EN 8, DE 8, ES 7, FR 7; w każdym języku losowanie bez zwracania
  z posortowanych identyfikatorów, `random.Random(20261102)`. Ta sama próbka dla T6 (pliki `.txt`) i P7 (pliki oryginalne);
  lista identyfikatorów publikowana z wynikami. Pomiar czasu nie korzysta z sędziego (nie ocenia trafności).
- **Warunki:** jeden uczestnik naraz, jeden dokument naraz; maszyna na zasilaczu, tryb niskiego zużycia energii wyłączony, bez
  innych obliczeń (potwierdzenie zwolnienia maszyny przed pomiarem), uczestnicy offline
  (`HF_HUB_OFFLINE=1`; modele pobrane wcześniej).
- **Wątki:** każdy uczestnik `--watki 4` (`OMP_NUM_THREADS=4`) – tyle, ile rdzeni wydajnościowych M1 i ile bierze polityka wydania
  Privatizera (połowa wątków logicznych); aplikacja Privatizer – ustawienia domyślne wydania. Wszyscy dostają ten sam budżet
  wątków.
- **Privatizer:** wydanie aplikacji i model jak w pkt 5 (znacznik wersji tam), aplikacja z instalatora macOS tego samego
  tagu; uczestnicy Privatizera wołają to samo API co w przebiegu trafności. Warianty „Maksymalna ochrona” (`privatizer-*-maks`, aneks)
  nie są mierzone czasem.
- **Przebieg:** proces uczestnika uruchomiony i model załadowany przed pomiarem (czas startu i ładowania – raportowany osobno,
  bez punktów); jedno pełne przejście próbki na rozgrzewkę (nieliczone), potem 3 przejścia mierzone. Czas dokumentu = czas
  ścienny orkiestratora od wysłania zapytania do odebrania kompletnego wyniku (tekst – wykrycia; plik – zapisany plik wynikowy),
  *t_dok* = mediana z 3 przejść. Raportowana też szczytowa pamięć (PSS albo `phys_footprint`, patrz niżej).
- **Wynik:** *t* = mediana po dokumentach próbki z *t_dok* / liczba stron. Dokument z błędem, przekroczonym czasem (`timeout_s`
  z `uczestnik.toml`) albo odmową ma *t_dok* = +∞ (fail-closed: awaria nie może być „szybka”); gdy takich jest co najmniej
  połowa (przy dokładnie połowie mediana – średnia dwóch środkowych – też jest +∞), *t* = +∞ i wynik = 0. Dokument nieobsługiwany (`pominiety`) nie wchodzi do próbki uczestnika – pokrycie formatów ocenia P6.
- **Narzędzie** (`pbench-czas`, poprawki z próby na maszynie referencyjnej; realizują protokół, niczego w nim nie zmieniają):
  uczestnicy startują poleceniem `uv run --frozen --no-sync` (środowisko zbudowane wcześniej `uv sync --frozen`, bez sprawdzania
  sieci; `--sprawdz` to weryfikuje); **szczytowa pamięć** to suma PSS drzewa procesów (Linux) albo suma `phys_footprint` z
  `footprint -p` (macOS), próbkowana co 1 s, z podaniem metody w `rss.jsonl` (zapas: RSS z `ps`) – zamiast RSS; `--limit N` służy wyłącznie do prób narzędzia i oznacza wynik jako `proba_niepelna` (nie wchodzi do rankingu);
  `--podsumuj <cel>` składa tabelę (mediana s/stronę, awarie, start, szczyt pamięci) z katalogu wyników.
- **Wejście agregacji** (`pbench-agreguj --czasy`, format w docstringu `pbench/agregacja.py`): JSONL, po linii na uczestnika ×
  poziom × dokument próbki – `{"uczestnik", "poziom", "id", "znaki", "pomiary_s": [3 pomiary], "status": ok|blad|timeout|odmowa|
  pominiety}`. Bez pliku pomiaru T6/P7 nie są liczone, a raport to oznacza (suma bez nich).

## 2. Reguły wycieku

Wartości progowe sędziów (czyta je `pbench.sedzia.tekst.RegulyWycieku.wczytaj` z tego pliku – blok poniżej; `pbench-ocen
--reguly` domyślnie wskazuje ten dokument). Wartości są równe domyślnym z kodu, z którymi przebiegły pilot i kalibracja; lista
`kategorie_id` jest zapisana jawnie, żeby jej późniejsza zmiana w kodzie nie zmieniła cicho oceny.

```yaml
reguly_wycieku:
  min_dl_tokenu: 3
  min_cyfr_id: 4
  ulamek_tokenu: 0.5
  prog_leksykonu: 0.05
  kategorie_id: [CIF, DNI, DOWOD, EIN, IDENTYFIKATOR, IP, KARTA, KOD_POCZTOWY, KRS, KRYPTO, KSIEGA_WIECZYSTA, KVNR, MAC, MBI,
                 MRZ, NHS, NINO, NIP, NIR, NR_ID, NR_PODATKOWY, NR_REJESTRACYJNY, NR_REJESTRU, NUSS, PASZPORT, PESEL,
                 PRAWO_JAZDY, RACHUNEK, REGON, SIREN, SSN, SVNR, SYGNATURA, TELEFON, UUID, VAT]
```

Brzmienie reguł (pełne – docstringi modułów, które są częścią zamrożenia):

- **Sędzia tekstowy** (`pbench/sedzia/tekst.py`, pkt 1–9): ocena pokrycia offsetów tekstu poziomu 1, bez względu na etykietę
  (label-blind); wartość = wszystkie spany o tym samym `wartosc_id`, wycieka raz. Kategorie słowne: token `\w+` ≥ 3 znaki
  jest odsłonięty, gdy ma niepokryty ciąg ≥ max(3, ⌈0,5·długość⌉); w EMAIL/URL nie liczą się schemat, `www`, `mailto` i TLD;
  słowa opisowe nazw organizacji same nie dają wycieku. Identyfikatory (`kategorie_id`): wyciek = odsłonięty ciąg ≥ 4 kolejnych
  znaków alfanumerycznych (krótsza wartość – cała), separatory i etykiety identyfikatorów (`ETYKIETY_ID`) pomijane. Inicjały –
  wszystkie litery odsłonięte. Rodzaj „pelny”/„czesciowy”.
- **Sędzia plikowy** (`pbench/sedzia/plik.py`, `ekstrakcja.py`, `obrazy.py`, `normalizacja.py`, `rtf.py`): skan wszystkich części
  pliku wynikowego (XML w ZIP, strumienie PDF, metadane, OLE, MIME, załączniki, obrazy osadzone, OCR stron) tymi samymi regułami
  tokenów i ciągów; leksykon korpusu (`prog_leksykonu`), wartości niejednoznaczne i niewykrywalne oraz linia bazowa liczone
  wyłącznie z oryginału i gold – wspólne dla wszystkich uczestników. Homoglify (szkielet), transliteracje, inicjały, widoki
  binarne OLE: `metodyka/trudne-sedziowie.md`, `metodyka/miejsca-ukryte.md`.
- **Zakres gold i rozstrzygnięcia po pilocie** (cytowane orzeczenia, miasto w nazwie sądu, etykiety w spanach identyfikatorów,
  słowa opisowe organizacji, kwoty, kody pocztowe): `metodyka/zakres-gold.md`.

## 3. Miary

Zakres danych jak w `punktacja.md`: split **test**; T1, T2, T4, T5, P1, P2, P4–P6 – warstwa `trzon` (800 dokumentów); T3, P3 –
warstwa `trudne` (222 dokumenty); poziom „tekst” – sędzia tekstowy na `.txt`, poziom „plik” – sędzia plikowy na pliku wynikowym.
Rekordy: `wyniki/oceny/<uczestnik>/test/<poziom>.jsonl` (`pbench-ocen`, schemat w docstringu `pbench/ocen.py`). Agregacja:
`pbench/agregacja.py`, wywołanie `uv run pbench-agreguj` – liczy dokładnie poniższe wzory.

### 3.1. Fail-closed, odmowa, błąd sędziego

- **Brak wyniku** (błąd uczestnika, przekroczony czas, pad procesu, plik wynikowy brakujący, nieczytelny albo pusty – flaga
  `brak_wyniku`) i **nieobsługiwany** (`nieobslugiwany`: język/format spoza deklaracji) = dokument z wyciekiem: sędzia ocenia
  wtedy tekst bez wykryć / kopię oryginału (wycieka wszystko, co może wyciec), a w T1/P1/T3/P3/T4 dokument ma wagę wycieku
  s = 1 (najwyższą) niezależnie od liczby wartości. W T2/P2 licznik takiego dokumentu = jego mianownik. Użytkownik wysłałby oryginał.
- **Odmowa** – uczestnik celowo nie przetwarza dokumentu i informuje o tym użytkownika (np. Privatizer: „Wiadomość zawiera
  załączniki…” dla EML z załącznikami w pilocie). Liczona dokładnie jak brak wyniku, a raport pokazuje ją **osobno** (kolumna
  „odmowy” obok „błędy/timeouty/nieobsługiwane”). Rozpoznanie: komunikat produktu w polu `blad` rekordu (dopasowanie podciągiem)
  z listy `uczestnicy/<id>/odmowy.json` (`{"komunikaty": [...]}`, opis w sekcji „Odmowy” `KONFIG.md` uczestnika; ta sama zasada
  dla każdego narzędzia z takim komunikatem). Lista `privatizer-plik` (brzmienie do potwierdzenia dla wersji z pkt 5): „Wiadomość zawiera załączniki – Privatizer nie
  anonimizuje załączników w plikach EML.”
- **Błąd sędziego** (`blad_sedziego` – np. uszkodzony oryginał): rekord liczony fail-closed jak brak wyniku i raportowany osobno;
  `pbench-ocen` kończy się kodem 1. Wyników z błędem sędziego się nie publikuje – przyczynę naprawia się w sędzi, poprawka jest
  nowym uzupełnieniem metodyki, a ocenę powtarza się dla wszystkich uczestników.
- **Odcisk sędziego.** Każdy rekord oceny niesie odcisk sędziego: sumę SHA-256 kodu sędziego i reguł wycieku z tego
  dokumentu, a dla ocen plikowych także skrót `tessdata` i wersje Tesseracta, leptoniki i LibreOffice'a (commit – informacyjnie).
  `pbench-agreguj` przerywa, gdy rekordy uczestników jednego poziomu mają różne odciski albo nie mają odcisku (wyjątek tylko dla
  pilota na dev) – ranking nie może łączyć ocen różnych sędziów ani środowisk.
- **Ranking niekompletny.** Gdy uczestnik rankingu ma test nieliczony, dokumenty bez rekordu oceny albo z błędem sędziego
  (w dowolnej warstwie), albo uczestnik zadeklarowany nie ma ocen – `pbench-agreguj` oznacza ranking jako NIEKOMPLETNY (kod
  wyjścia ≠ 0, lista braków) i takiego rankingu się nie publikuje. Warstwa trudna bez ocen uczestnika liczy się fail-closed
  (T3/P3 = 0).
- Ponowienia: dokument z błędem/timeoutem ponawiany do 2 razy, `pominiety` nigdy – ta sama polityka dla wszystkich (`pbench/uruchom.py`).

### 3.2. Miary punktowane (definicje operacyjne)

| Test | Definicja (rekordy ocen) |
|---|---|
| T1, P1 | **ważone kategorią**: T1 = 1 − Σ_d s(d) / N po dokumentach trzonu test; P1 = to samo na sędzi plikowym (wycieki w dowolnej części pliku wynikowego). **Waga dokumentu z wyciekiem** s(d) = max w(kat) po wartościach gold, które w dokumencie wyciekły (pełnie lub częściowo – rekord `wycieki`), podzielone przez 3 (najwyższa waga kategorii; w(kat) z `wagi_punktow.json`, wagi kategorii 3/2/1, kategoria spoza list – 1); dokument bez wycieku s = 0; dokument fail-closed (`brak_wyniku`, `nieobslugiwany`, `blad_sedziego`, odmowa albo dokument splitu bez rekordu oceny – każdy stan ≠ `ok`) s = 1. **Wagi miejsc nie wchodzą** (ani do T1, ani do P1). Przykłady: kwota i PESEL → 1; sama kwota → 1/3; sama osoba → 2/3 |
| T2 | 1 − Σ w(kat)·[wyciekła] / Σ w(kat) po unikalnych `wartosc_id` z `gold_tekst` dokumentów; kategoria wartości = kategoria jej pierwszego spanu; w(kat) z `wagi_punktow.json` (kategoria spoza list – 1) |
| P2 | pkt 3.3 |
| T3, P3 | pkt 1.1: średnia po przypadkach z (1 − Σ s(d) / liczba dokumentów przypadku), s(d) jak w T1/P1 (T3 – sędzia tekstowy, P3 – plikowy) |
| T4 | min po {pl, en, es, de, fr} wyniku T1 (ważonego, s(d)) w obrębie języka dokumentu |
| T5 | *u* = Σ `fp_znaki` / Σ znaki niebiałe tekstu poza wszystkimi spanami gold; sumy po dokumentach z wynikiem (bez `brak_wyniku`, `nieobslugiwany`); wynik = max(0, 1 − *u* / 0,20). Dokument bez wyniku nie wchodzi do T5 – jest już liczony jako wyciek w T1/T2/T4 i nie może dawać „zera nadmiarowego maskowania”. **Zakres gold:** kody ICD, nazwy leków (z dawką) i opisy przypadłości są poza gold (`metodyka/zakres-gold.md`, pkt 6) – ich zamaskowanie to znaki poza gold, czyli nadmiarowe maskowanie (`fp_znaki`); osoba, której dotyczą, i jej dane są w gold |
| P4 | dla dokumentu: średnia dostępnych składników `integralnosc` – `otwiera_sie` (0/1), `zachowanie_struktury`, `spojnosc`; `None` (nie dotyczy: format zamieniony na odpowiednik, brak encji do oceny spójności) pominięty w średniej; brak wyniku i plik nieczytelny/pusty = 0; nieobsługiwany – poza P4 (ocenia go P6). P4 = średnia po dokumentach |
| P5 | jak T5 na tekście wyekstrahowanym z pliku wynikowego: znaki niebiałe oryginału poza wystąpieniami gold, które w wyniku zostały zamienione albo usunięte, przez wszystkie znaki niebiałe oryginału poza gold; tekst widoczny dokumentu (treść, tabele, nagłówki, stopki, przypisy, slajdy, komórki, treść poczty – bez metadanych, komentarzy i śledzenia zmian, których usunięcie jest krokiem anonimizacji), wyrównanie słów oryginału i wyniku jak w `spojnosc` (difflib na słowach; część z częścią o tej samej nazwie, przy formacie zamienionym na odpowiednik – cały tekst widoczny pliku; strona PDF wyniku bez warstwy tekstowej – OCR tej strony), wystąpienia gold w oryginale – każde wystąpienie tekstu wartości gold (poza narysowanymi na obrazach) odnalezione w słowach oryginału normalizacją sędziego plikowego, także wartości wyłączonych z oceny wycieku (niejednoznaczne, bez liczącego się tokenu) – maskowanie wartości gold nie jest nadmiarowe; skan bez warstwy tekstowej nie wnosi znaków. Kody ICD, leki i opisy przypadłości są poza gold, więc ich zamaskowanie w pliku zwiększa `nadmiarowe.znaki` (zakres gold jak w T5). Implementacja: `pbench.sedzia.plik.nadmiarowe`, pole rekordu `nadmiarowe` `{znaki, poza_gold}` |
| P6 | dokumenty bez `brak_wyniku` i bez `nieobslugiwany` / wszystkie dokumenty trzonu test (odmowa = nieprzetworzony) |
| T6, P7 | pkt 1.2 |

Zamiana formatu (`format_wyj` ≠ format oryginału, np. DOC → DOCX, MSG → TXT) nie jest błędem ani wyciekiem; raport pokazuje ją
w tabeli różnic funkcjonalnych, a w P4 składnik `zachowanie_struktury` jest wtedy „nie dotyczy”.

### 3.3. Mianownik P2 i wycieku ważonego na poziomie plik

W pilocie wyciek ważony na poziomie plik przekroczył 100%, bo mianownik liczono z `gold_tekst`, a sędzia plikowy ocenia
wartości z `gold_plik` i `gold_obrazy` (`sedzia.sanity.wartosci_wpisu`; inne identyfikatory i krotność wartości obrazowych).
Formuła obowiązująca (licznik i mianownik po **tych samych** identyfikatorach):

- zbiór ocenianych wartości dokumentu *O* = linia bazowa sędziego plikowego (`OcenaPliku.bazowe`: wartości odnajdywane w oryginale,
  bez niewykrywalnych i niejednoznacznych – wspólna dla wszystkich uczestników) ∪ identyfikatory z `wycieki` uczestnika
  (wartość, którą uczestnik dopisał w miejscu, gdzie oryginał jej nie pokazywał, szkodzi tylko jemu); |*O*| = `wartosci_ocenione`;
- waga wartości *v* = w(kat(*v*)) · w(miejsce(*v*)): kategoria z gold *v*, miejsce = **największa** waga miejsca wśród wpisów gold
  *v* w `gold_plik`/`gold_obrazy` (identyfikator powtórzony w kilku miejscach, np. treść i metadane, waży jak najmniej widoczne
  z nich) – waga zależy tylko od gold, nie od tego, gdzie wartość wyciekła u uczestnika;
- P2 = 1 − Σ_{v ∈ *O*, wyciekła} waga(*v*) / Σ_{v ∈ *O*} waga(*v*), sumy po wszystkich dokumentach trzonu test (micro); dokument
  bez wyniku/nieobsługiwany – oceniany kopią oryginału, więc wszystkie wartości *O* wyciekają (pkt 3.1);
- **wyciek ważony kategorią na poziomie plik** (miara opisowa, odpowiednik T2 dla plików) – ten sam zbiór *O*, waga = w(kat).

Z konstrukcji licznik ≤ mianownik (wynik ∈ [0, 1]). Rekord oceny poziomu plik ma pole `bazowe` (identyfikatory linii bazowej,
`pbench-ocen`); rekord bez niego (ocena bez linii bazowej) – dla dokumentu bez wyniku linią bazową są wycieki oceny kopii oryginału
(wszystkie wartości linii bazowej wyciekają – test regresji sędziego), dla dokumentu z wynikiem P2 nie jest liczone (ocenę trzeba
powtórzyć). Agregacja: `pbench/agregacja.py` (`pbench-agreguj`), testy `test_p2_licznik_i_mianownik_z_tych_samych_id`
i `test_p2_w_przedziale_dla_przypadku_pilota_ponad_100` (`tests/test_agregacja.py`).

### 3.4. Miary pomocnicze (poza punktami)

- **W deklarowanym zakresie** (`w_zakresie_deklarowanym`, `etykiety.json` uczestnika dla języka dokumentu – `metodyka/zakres-gold.md`
  pkt 4): te same wzory na wartościach kategorii, które uczestnik deklaruje; dokument nieobsługiwany – poza mianownikiem tej miary.
- **W zakresie oficjalnym** (`w_zakresie_oficjalnym`: język dokumentu w `jezyki_oficjalne` uczestnika wg karty/dokumentacji) –
  wiersze tabel tylko z języków oficjalnych; nagłówek liczy wszystkie pięć języków (każdy uczestnik przetwarza wszystkie).
- **Identyfikacja pośrednia** – odsetek kombinacji przerwanych, `pbench.posrednie.agreguj`, z przedziałem ufności
  (`metodyka/posrednie.md`).
- **Poziom encji** – encja wycieka, gdy wycieka którykolwiek jej zapis (cyrylica, transliteracje, homoglify, inicjały; pola
  `wycieki_encji`, `encje_ocenione` – docstring `pbench/ocen.py`).
- **Rozbicia:** per język, format, typ dokumentu, kategoria, miejsce (miejsce gold wartości, jak w pkt 3.3), przypadek trudny;
  ukraiński i przypadki cyrylicy osobno, z zastrzeżeniem, że `uk` jest poza pięcioma językami Privatizera.
- **Aneks techniczny:** `char_f2`, `pokrycie_znakowe`, `fp_spany`, wartości z wyciekiem pełnym/częściowym, liczba timeoutów
  wariantów krzyżowych.
- **Ścisłe F1 na spanach** (spec §6; decyzja 2026-11-02 – miara pomocnicza, poza punktami): trafienie = wykrycie o granicach
  dokładnie równych spanowi gold, bez względu na etykietę; spany unikalne w dokumencie; dokument bez wyniku – bez wykryć; mikro
  po dokumentach trzonu (poziom tekst, z wyników surowych). Punkty liczą wyciek i pokrycie znaków, nie granice spanów.

### 3.5. Niepewność i remis

Bootstrap po dokumentach: 1000 losowań ze zwracaniem, `numpy.random.default_rng(20261031)` (to samo ziarno co
`pbench.posrednie.ZIARNO_BOOTSTRAP`), percentyle 2,5 i 97,5. Losowanie sparowane (te same indeksy dokumentów dla wszystkich
uczestników), osobno w warstwie `trzon` (800) i `trudne` (222); w warstwie trudnej warstwowane po pełnym zestawie
przypadków dokumentu (pole `przypadki`; dokumenty o tym samym zestawie tworzą jedną warstwę – `pbench.agregacja.warstwy_przypadkow`),
dzięki czemu każdy przypadek T3/P3 ma w każdym losowaniu tyle dokumentów co w próbie, także przypadek występujący wyłącznie obok
innego; kolejność losowań: trzon, potem warstwy alfabetycznie (`pbench.agregacja.macierz_losowan`). Suma rankingu liczona
w każdym losowaniu z tych samych indeksów; T6/P7 – stała (osobna próbka czasu, bez bootstrapu). Nakładające się 95% przedziały
sum dwóch uczestników = **remis statystyczny**. Analiza wrażliwości – zestawy `rowne`, `prywatnosc`, `uzytecznosc` z
`wagi_punktow.json`.

## 4. Kalibracja progów (grupa A)

**Kolejność (wiążąca).** Kalibrację wykonano **przed zamrożeniem**, wyłącznie na splicie dev korpusu: zamrożone progi są mocniejszą
gwarancją niż zamrożona sama procedura, a dev nie dotyka testu. Surowe wyniki dev policzono kodem uczestników
z commitu zamrożenia; progi (`prog.json`, pole `commit_sedziego`) wyznaczono sędzią z tego commitu. Wynik (`uczestnicy/<id>/prog.json`,
zebrany w `metodyka/progi.json`) jest częścią commitu zamrożenia; przebiegi testu korzystają z tych progów. Test nie bierze udziału
w kalibracji w żadnym kroku.

Procedura (`pbench/kalibracja.py`, `pbench-kalibruj`; opis w `metodyka/uczestnicy.md`): surowe wyniki dev w trybie podłogi
(`PBENCH_SUROWE=1` – wykrycia z wynikami pewności od 0,01), miara = **średnia `char_f2` dokumentów dev** (200 dokumentów trzonu,
wszystkie języki razem, jeden próg na uczestnika) liczona sędzią tekstowym tą samą funkcją co `pbench-ocen` (sędzia z commitu
zamrożenia), siatka progów **0,01–0,95** (0,01–0,04 co 0,01, potem 0,05–0,95 co 0,05), remis → wyższy próg. Privatizer nie jest
kalibrowany (mierzymy wydanie). Kalibracja korzysta wyłącznie z dev.

| Uczestnik | Próg | char-F2 dev przy progu | char-F2 przy progu domyślnym autorów | Siatka | Uwagi |
|---|---|---|---|---|---|
| `presidio-spacy` | 0,01 | 0,7228 | 0,7228 (autorzy: bez progu) | 0,01–0,95 | optimum na brzegu siatki |
| `presidio-pl-ner` | 0,01 | 0,8491 | 0,8491 (autorzy: bez progu) | 0,01–0,95 | optimum na brzegu siatki; próg dziedziczą plikowi grupy B |
| `presidio-gliner` | 0,15 | 0,8578 | 0,8560 (0,30) | 0,01–0,95 | próg dziedziczy `presidio-lgp` |
| `gliner-nvidia-pii` | 0,01 | 0,8770 | 0,8180 (0,30) | 0,01–0,95 | optimum na brzegu siatki; 7 dokumentów dev przekroczyło limit 600 s (puste wykrycia, jak w ocenie); próg dziedziczy `privatizer-tekst-gliner` |
| `gliner-urchade-pii` | 0,01 | 0,7968 | 0,7444 (0,50) | 0,01–0,95 | optimum na brzegu siatki |
| `gliner-knowledgator-pii` | 0,04 | 0,9151 | 0,8026 (0,30) | 0,01–0,95 | |
| `openai-privacy-filter` | 0,02 | 0,7018 | 0,7018 (autorzy: Viterbi bez progu) | 0,01–0,95 | próg dziedziczy `privatizer-tekst-opf` |
| `stanza` | – | – | – | – | NER bez pewności spanów (wynik 1,0) – próg bez wpływu |

Pełne krzywe F2: `uczestnicy/<id>/prog.json`, zebrane w `metodyka/progi.json`. Próg domyślny autorów „bez progu” odpowiada w trybie
podłogi progowi 0,01 (wykryć poniżej 0,01 tryb surowy nie zwraca), stąd ta sama wartość F2.

**Optimum na brzegu siatki.** Siatki nie rozszerza się poniżej 0,01: próg bliski zera to zwracanie prawie każdego kandydata modelu, a
koszt nadmiarowego maskowania ocenia osobno T5. Jeżeli optimum wypadnie na brzegu (0,01), raport to zaznacza jako ograniczenie siatki;
działa ono na korzyść recall konkurencji. Reguła jest ustalona z góry i nie zależy od wyniku.

**Dziedziczenie progów:** `presidio-lgp` (aneks) – próg końcowy `presidio-gliner`; `privatizer-tekst-gliner` (aneks) –
`gliner-nvidia-pii`; `privatizer-tekst-opf` (aneks) – `openai-privacy-filter`; `presidio-wrapper-plikowy`, `pdf-redactor`,
`presidio-image-redactor` (grupa B) – `presidio-pl-ner`. Grupa B tekstowa (`scrubadub`, `flair`, `ai4privacy`) – domyślne
ustawienia autorów, bez kalibracji.

## 5. Uczestnicy

Szczegóły i uzasadnienia: `metodyka/uczestnicy.md` i `uczestnicy/<id>/KONFIG.md` (rewizje, sumy wag, licencje, odstępstwa).
23 uczestników (grupa A – 8, Privatizer – 3, grupa B – 6, aneks – 6, w tym dwa warianty aneksu w trybie
„Maksymalna ochrona”), te same rewizje modeli i narzędzi OSS. Wszyscy na CPU (`CUDA_VISIBLE_DEVICES=""`), wersje bibliotek z `uczestnicy/<id>/uv.lock`, każdy uczestnik tekstowy na wszystkich
pięciu językach.

| Grupa | Uczestnik | Ranking | Narzędzie / model (rewizja) |
|---|---|---|---|
| A | `presidio-spacy` | tekst | Presidio 2.2.366 + spaCy 3.8.18, `{pl,es,de,fr}_core_news_lg`, `en_core_web_lg` 3.8.0 |
| A | `presidio-pl-ner` | tekst | Presidio + transformers 4.57.6: pl `lexedit/herbert-polish-legal-ner` `3b0f37e5`, en `dslim/bert-large-NER` `6fe43d9e`, es `Davlan/xlm-roberta-large-ner-hrl` `1f929ffa`, de `FacebookAI/xlm-roberta-large-finetuned-conll03-german` `1fbcc7a0`, fr `Jean-Baptiste/camembert-ner` `ef35fe77` |
| A | `presidio-gliner` | tekst | Presidio + GLiNER 0.2.29, `urchade/gliner_multi_pii-v1` `1fcf13e8` |
| A | `gliner-nvidia-pii` | tekst | `nvidia/gliner-PII` `bd23e8ef` |
| A | `gliner-urchade-pii` | tekst | `urchade/gliner_multi_pii-v1` `1fcf13e8` |
| A | `gliner-knowledgator-pii` | tekst | `knowledgator/gliner-pii-large-v1.0` `f847f54f` |
| A | `openai-privacy-filter` | tekst | `openai/privacy-filter` `7ffa9a04` (wyłącznie oficjalne repozytorium), kod `opf` `f7f00ca7` |
| A | `stanza` | tekst | Stanza 1.15.0, pl `nkjp_bert` (HerBERT `50e33e05`), en/es/de/fr – modele wydania |
| Privatizer | `privatizer-model` | tekst | sam model `lgp-1.0-rc` (`Detector.predict`) |
| Privatizer | `privatizer-tekst` | tekst | silnik na tekście (model + reguły + scalanie) |
| Privatizer | `privatizer-plik` | pliki | aplikacja plik → plik (API serwera, ustawienia domyślne wydania) |
| B | `scrubadub` | tekst | scrubadub 2.0.1 (same wyrażenia regularne) |
| B | `flair` | tekst | Flair 0.15.1, `flair/ner-multi` `efbff753` |
| B | `ai4privacy` | tekst | `ai4privacy/llama-ai4privacy-multilingual-categorical-anonymiser-openpii` `83ef30d5` (sam model, potok transformers) |
| B | `presidio-image-redactor` | pliki (skany) | Presidio Image Redactor 0.0.62 + analizator `presidio-pl-ner` |
| B | `pdf-redactor` | pliki (PDF) | `JoshData/pdf-redactor` `12ad5c68` + analizator `presidio-pl-ner` |
| B | `presidio-wrapper-plikowy` | pliki (DOCX/XLSX/PPTX) | **nasz naiwny wrapper** – wzorzec „co zostaje, gdy anonimizuje się tylko tekst” |
| aneks | `privatizer-reguly` | – | same reguły Privatizera (`use_model=False`) |
| aneks | `presidio-lgp` | – | Presidio jak `presidio-gliner`, rozpoznawacz NER = model LGP |
| aneks | `privatizer-tekst-gliner` | – | potok `privatizer-tekst` z modelem `nvidia/gliner-PII` |
| aneks | `privatizer-tekst-opf` | – | potok `privatizer-tekst` z modelem `openai/privacy-filter` |
| aneks | `privatizer-tekst-maks` | – | potok `privatizer-tekst` w trybie „Maksymalna ochrona” (`privacy`, `KWOTA` włączona przez aplikację) |
| aneks | `privatizer-plik-maks` | – | aplikacja plik → plik (`privatizer-plik`) w trybie „Maksymalna ochrona” (jw.) |

**Privatizer:** aplikacja Privatizer by Legal Geek `v1.3.0b24` (commit `6ed25e2`, manifest serial 31), model `lgp-1.0-rc` w wersji paczki `1.0.0rc5`. SHA-256 artefaktów wydania: instalator Windows (exe) `03e78a89bc595dda92de998c61a7fd6894fc1460ffb213c1ac217e1f8e1709ed`, obraz macOS (dmg) `e153ba035dcfecc7da8752ac2095d8a93c1cdc6a568293301f2c539ad67b40c6`. Tryb ustawień: **ranking** – tryb domyślny świeżej instalacji (czułość `balanced`, `KWOTA` wyłączona); **aneks** –
`privatizer-tekst-maks` i `privatizer-plik-maks` w trybie „Maksymalna ochrona” (`privacy`, `KWOTA` włączona przez aplikację: tryb ustawia funkcja
`settings.save`, nie ręczna lista kategorii), poza rankingami; zakres gold wariantów maks obejmuje `KWOTA` (`metodyka/zakres-gold.md`). Pozostałe warunki: kanał test, czułość
`balanced` (ranking), instalacja z drzewa tagu (`git archive`), kod bez zmian. Dowód wersji i sum artefaktów (kontener `.lgm`, wagi
`model.safetensors`, słowniki, twarze, OCR) w `wyniki/surowe/<id>/wersje.json` każdego przebiegu. Komunikat odmowy `privatizer-plik` (`uczestnicy/privatizer-plik/odmowy.json`, pkt 3.1) jest zgodny z brzmieniem tego wydania (`err.file.mail.attachments`).

**Rozważeni i odrzuceni** (powody – `metodyka/uczestnicy.md`): Piiranha (licencja CC-BY-NC-ND 4.0), anonimizator CLARIN-PL (brak
licencji, NER tylko usługami sieciowymi), Liner2 (ogólny NER, nie anonimizator; martwy), pakiet `ai4privacy` z PyPI (bez licencji
otwartej – w benchmarku sam model na MIT), `pdf-redactor` z PyPI (fork – zastąpiony repozytorium autorów). Usługi chmurowe
(Google Cloud Sensitive Data Protection): tylko opisowo, bez pomiaru.

## 6. Korpus

- **Trzon:** 1000 dokumentów syntetycznych, ziarno `20261103` (`pbench.korpus.ZIARNO`), generator: kod z commitu zamrożenia
  (`pbench.korpus`, `pbench.budowa`, `pbench.szablony`). Języki: PL 500, EN/ES/DE/FR po 125; split dev 200 / test
  800, stratyfikowany (test: PL 400, EN/ES/DE/FR po 100). Formaty: docx 302, pdf 200, skan 98, xlsx 98, eml 80, pptx 80, doc 71, msg 71.
  Typy dokumentów: email 151, faktura 108, prezentacja 80, odpis_rejestru 57, pelnomocnictwo 57, cv 56, wyrok 56, pozew 55,
  umowa 55, wezwanie 53, lista_plac 49, notatka 45, protokol 44, med_zaswiadczenie 28, med_wypis 27, umowa_najmu 23,
  pozew_zaplata_osoby 22, umowa_sprzedazy_auta 22, med_skierowanie 12. Sumy SHA-256: `metodyka/SHA256SUMS-trzon` (2002 wpisy: 2000 plików,
  `manifest.jsonl` `5f23adedb58dcaa03b8441e016cc4a602d3126f379fd5a9622b105fe04770d63`, `statystyki.json`; SHA-256 samego pliku sum
  `53f1691f2a26bbf3558f76ea3d952b3ac39e7c62f5b8138886606a518d99e39f`).
- **Dokumenty medyczne i prywatne.** Dokumentów medycznych (`med_wypis`, `med_zaswiadczenie`, `med_skierowanie`) jest **67 z 1000**
  (27 + 28 + 12); **dokumentów prywatnych** (osoby fizyczne jako strony: `umowa_najmu`, `umowa_sprzedazy_auta`, `pozew_zaplata_osoby`)
  także **67 z 1000** (23 + 22 + 22), PL, EN, DE, ES, FR, w formatach jak pozostałe typy. Rozpoznania, kody ICD i leki są poza gold
  (`metodyka/zakres-gold.md`, pkt 6; pkt 3.2).
- **Identyfikatory.** Generatory identyfikatorów, numerów rejestracyjnych i telefonów mają poprawki oparte o źródła pierwotne, a część
  pozycji pozostaje niezweryfikowana – opis i lista: `metodyka/znane-ograniczenia.md` (sekcja „Generatory identyfikatorów”; pkt 8).
- **Warstwa trudna:** 290 dokumentów (split dev 68 / test 222), ziarno `20261104` (`pbench.trudne.ZIARNO_TRUDNE`), rozkład per przypadek
  i uzasadnienie: `metodyka/przypadki.md`; generator: ten sam kod co trzon. Języki: PL 128, DE 41, EN 41, ES 34, FR 34, UK 12 (test:
  PL 72, EN 39, DE 37, FR 34, ES 30, UK 10). Formaty: docx 110, pdf 97, doc 18, eml 12, msg 12, xlsx 12, skan 10, pptx 9, odt 5, rtf 5.
  34 przypadki (dev/test): `cyrylica_dokument_uk` 2/10, `cyrylica_wstawka` 4/15, `cytowane_watki_vcard` 2/8, `formaty_rtf_odt` 2/8,
  `homoglify` 2/10, `transliteracja` 2/8, `ukryta_poczta` 2/8, `ukryta_xlsx` 2/8, a pozostałe 26 po 2/6 (dokument może mieć więcej
  niż jeden przypadek; liczby z pola `przypadki` manifestu). Sumy `metodyka/SHA256SUMS-trudne` (582 wpisy: dokumenty, `.txt`,
  `manifest.jsonl` `e733cc538392c063e31c0c7e66e941a2417430906ab4ff7e84dd6f9463d7c0f2`, `statystyki.json`; SHA-256 samego pliku sum
  `35dff33bd8c45450a1897600c58ea3c0083ddeaeefc1d362c154731c37edfe83`). Odtworzenie wymaga LibreOffice'a 24.2.7.2 (DOC, RTF, ODT) i czcionek
  Liberation (`metodyka/srodowiska.md`). Przypadek `posrednie_rzadka_choroba` nie ma w gold składnika „choroba” (`zakres-gold.md`, pkt 6).
- **Rozdzielność od treningu:** szablony pisane od zera, własne słowniki, kontrola 8-gramów względem danych treningowych modelu
  (poniżej). Zespoły Privatizera nie mają dostępu do splitu testowego; korpus nie służy do treningu ani walidacji modelu.

### 6.1. Kontrola kontaminacji (8-gramy)

Metoda (`pbench/kontaminacja.py`): odsetek **unikalnych** 8-gramów słownych (małe litery, ciągi liter i cyfr, skrót 64-bit; bez
próbkowania) obecnych w danych treningowych modelu: (a) bloki szablonów, (b) wygenerowane teksty korpusu. Frazy formułkowe = 8-gramy
występujące w blokach szablonów co najmniej 3 różnych typów dokumentów (31 takich 8-gramów, 0,23% 8-gramów szablonów); raport podaje
odsetek ogółem i po ich wyłączeniu („poza formułkowymi”). Wewnętrzny cel to **≤ 1%**, liczony na wartościach „poza formułkowymi”.
Zbiór referencyjny: pełna linia treningowa modelu mierzonego (rc5, `lgp-1.0-rc` paczka 1.0.0rc5) = `mmbert-soup-nft-b`, czyli średnia
wag trzech dotrenowań z `mmbert-r06b-lw4-s5` (best, krok 91377): `mmbert-lw4s5-nft-s3` i `mmbert-lw4s5-nft-e1` (mieszanka run-008) oraz
`mmbert-nft1-cyr-s2` (run-010). Zbiór = mieszanki run-006, run-008 i run-010 (train i val) oraz dev run-005; jest **kompletny**
(`zbior_referencyjny.kompletny: true` w obu plikach wyniku) i liczy 84 379 068 unikalnych 8-gramów. Opis linii (składniki, mieszanki, pliki) i
zgodność z `config.json` przebiegów – `metodyka/linia-modelu-rc5.json` oraz pole `linia_modelu` w `metodyka/kontaminacja.json` i
`metodyka/kontaminacja-trudne.json`.
Wynik zawiera wyłącznie liczby (`metodyka/kontaminacja.json`, `metodyka/kontaminacja-trudne.json`).

| Zbiór | Unikalnych 8-gramów | Wspólnych z treningiem (ogółem) | Odsetek ogółem | Odsetek poza formułkowymi | Cel ≤ 1% |
|---|---|---|---|---|---|
| Korpus trzonu (1000 dok.) | 326 863 | 2572 | 0,787% | 0,779% (2546 z 326 832) | **spełniony** |
| Warstwa trudna (290 dok.) | 97 635 | 1534 | 1,571% | 1,545% (1508 z 97 604) | **niespełniony** |
| Szablony (bloki szablonów trzonu) | 13 316 | 1738 | 13,05% | 12,89% (1712 z 13 285) | **niespełniony** |

(Blok „szablony” w obu plikach jest ten sam – nie zależy od korpusu. Liczone po wystąpieniach, a nie po unikalnych 8-gramach, odsetki
są wyższe: korpus trzonu 3,74% ogółem i 3,59% poza formułkowymi, warstwa trudna 2,44% i 2,33%.)

**Interpretacja – uczciwie.** Cel 1% jest spełniony dla korpusu trzonu i **niespełniony** dla szablonów oraz warstwy trudnej. Pomiar nie
potwierdza, że nadwyżka to kwestia „fraz formułkowych” w sensie narzędzia: wyłączenie 31 fraz wspólnych dla ≥ 3 typów obniża szablony
tylko z 13,05% do 12,89%, a warstwę trudną z 1,57% do 1,55%. Diagnostyka narzędzia dzieli wspólne 8-gramy szablonów (poza formułkowymi) na
powołania z cyframi (artykuły, §, lata: 255 z 2465, 10,3%) i słowa bez cyfr (1457 z 10 820, 13,5%) – nadwyżka nie jest więc samymi
powołaniami przepisów. Najprostsze wyjaśnienie, **niezweryfikowane** [HIPOTEZA], to nakładanie się stylu prawnego: szablony są pisane
językiem pism procesowych, umów i orzeczeń, a dane treningowe zawierają polskie i obce teksty prawne, więc stałe zwroty prawnicze
typowe dla danego typu dokumentu (a nie wspólne dla trzech typów, jak frazy formułkowe) pokrywają się z nimi. Szablony nie są kopiami
tych danych (pisane od zera), a w korpusie trzonu, gdzie szablon to tylko część tekstu, a resztę wypełniają losowane dane, odsetek jest
poniżej celu. Raport podaje wszystkie powyższe liczby wprost; żaden wynik uczestnika nie jest korygowany z tytułu kontaminacji.

## 7. Środowisko oceny (zamrożone)

Trafność liczona na CPU serwerów ARM (Ubuntu 24.04, aarch64, NVIDIA GB10, 20 rdzeni; obliczenia wyłącznie na CPU);
sędziowie dają ten sam wynik niezależnie od maszyny przy tym samym środowisku:

- **Tesseract 5.3.4** (leptonica 1.82.0; Ubuntu `tesseract-ocr 5.3.4-1ubuntu0.1~esm1`). Sędzia czyta **wyłącznie** dane z
  `vendor/tessdata` (`--tessdata-dir`, zmienna `PBENCH_TESSDATA` tylko do testów), nie systemowe. Pliki (`eng`, `pol`, `osd` –
  kopie pakietów Ubuntu `tesseract-ocr-{eng,pol,osd} 1:4.1.0-2`, identyczne bajtowo z systemowymi; `spa`, `deu`, `fra`, `ukr` –
  `tessdata_fast`, Apache-2.0):

  | Plik | SHA-256 |
  |---|---|
  | `deu.traineddata` | `19d219bbb6672c869d20a9636c6816a81eb9a71796cb93ebe0cb1530e2cdb22d` |
  | `eng.traineddata` | `7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2` |
  | `fra.traineddata` | `ced037562e8c80c13122dece28dd477d399af80911a28791a66a63ac1e3445ca` |
  | `osd.traineddata` | `9cf5d576fcc47564f11265841e5ca839001e7e6f38ff7f7aacf46d15a96b00ff` |
  | `pol.traineddata` | `c4476cdbc0e33d898d32345122b7be1cbf85ace15f920f06c7714756e1ef79b2` |
  | `spa.traineddata` | `6f2e04d02774a18f01bed44b1111f2cd7f3ba7ac9dc4373cd3f898a40ea6b464` |
  | `ukr.traineddata` | `d59e53e2bded32f4445f124b4b00240fcac7e8044c003ab822ccb94f0b3db59b` |

- **LibreOffice 24.2.7.2** (konwersja DOC → DOCX w sędzi plikowym i budowa DOC/RTF/ODT korpusu).
- **Biblioteki sędziego** (`uv.lock` commitu zamrożenia, Python 3.12): pypdfium2 5.14.0, pikepdf 10.17.0, lxml 6.1.3,
  Pillow 13.0.0, numpy 2.5.4, olefile 0.47, openpyxl 3.1.5, python-docx 1.2.0, python-pptx 1.0.2, PyYAML 6.0.3, reportlab 5.1.0,
  phonenumbers 9.0.42, python-stdnum 2.2, arabic-reshaper 3.0.1, python-bidi 0.6.12 (dev: extract-msg 0.58.0, pdfminer.six
  20260107).
- **Pamięć podręczna OCR** (`PBENCH_OCR_CACHE`, klucz: SHA-256 obrazu/PDF-u, język, wersje odczytu i skrót zawartości
  `tessdata` – `ocr.skrot_tessdata`; bez wersji Tesseracta): inne dane `tessdata` dają nowe odczyty; przy zmianie Tesseracta albo
  maszyny z innym środowiskiem – **czyszczona** przed oceną.
  Przed każdą oceną plikową operator sprawdza obecność i sumy wszystkich siedmiu plików `tessdata` (`sha256sum -c`
  względem tabeli powyżej); brak pliku zapisałby w pamięci podręcznej pusty odczyt jako wynik. Kontrola
  w kodzie: `pbench-ocen --poziom plik` sprawdza obecność i sumy siedmiu plików względem tabeli powyżej oraz wersje Tesseracta
  (z leptoniką) i LibreOffice'a (`pbench/srodowisko.py`, wartości czytane z tego dokumentu) i przy niezgodności przerywa bez oceny (kod 2).
- Wykrywania twarzy sędzia nie ma: korpus nie zawiera zdjęć twarzy (kategoria `TWARZ` bez wartości gold) – ograniczenie badania.

## 8. Znane ograniczenia

`metodyka/znane-ograniczenia.md` (realizm korpusu, warstwa trudna do ręcznej weryfikacji, przegląd pilota, nazwy firm, licencja
modelu Flair, generatory identyfikatorów i telefony), `metodyka/zakres-gold.md` (zakres gold, kwoty, rozpoznania i leki) i sekcje ograniczeń
w `metodyka/uczestnicy.md` (warianty krzyżowe). Najważniejsze dla interpretacji wyników:

- **Generatory identyfikatorów** (PESEL, KRS, dowody, rachunki, tablice, sygnatury i in.) nie są zweryfikowane w źródłach pierwotnych w
  pozycjach wymienionych w `znane-ograniczenia.md`; poprawki mają testy, ale lista „niezweryfikowane” pozostaje.
- **Kody pocztowe GB** zawężono heurystycznie (potwierdzone zakresy dystryktów tylko dla HG, SP, FY, TF; dla pozostałych 1–5), więc kod
  nie musi istnieć.
- **Telefony** są w formatach fikcyjnych (oficjalne pule fikcyjne GB, US, DE, FR; dla PL, ES i UA numery zaczynające się od `00`) i
  nie przechodzą walidacji planów numeracji – jednakowo dla wszystkich uczestników; narzędzia walidujące libphonenumber mogą mieć
  przez to niższą wykrywalność.
- **XLSX:** poziom tekstu (linearyzacja `.txt`) traci etykiety kolumn arkusza.
- **Redaktor obrazów** (`presidio-image-redactor`) – P5 (nadmiarowe maskowanie) jest dla niego n/d (nie dotyczy).
- Brak zdjęć twarzy w korpusie (kategoria `TWARZ` bez wartości gold) – pkt 7.
- Rozpoznania, kody ICD i leki są poza gold (pkt 3.2): ocena ochrony samej diagnozy jest poza zakresem; maskowanie ich liczy się do
  nadmiarowego maskowania.
- Kontaminacja szablonów i warstwy trudnej powyżej celu wewnętrznego (pkt 6.1).

## 9. Zamrożenie

- Data: 2026-11-04; zamrożenie: tag `prerejestracja-1` (commit wskazany przez tag).
- Zamrażane razem: ten dokument (blok `reguly_wycieku`, definicje, `t_ref`, maszyna i ustawienia czasu, procedura kalibracji),
  `punktacja.md` i `metodyka/wagi_punktow.json`, kod sędziów (`pbench/sedzia/*`, `pbench/ocen.py`,
  `pbench/posrednie.py`, `pbench/przypadki.py`), kod agregacji i kontroli środowiska (`pbench/agregacja.py`, `pbench/srodowisko.py`,
  `pbench/ocr.py`), kod kalibracji i pomiaru czasu (`pbench/kalibracja.py`, `pbench/czas.py`), listy odmów (`uczestnicy/*/odmowy.json`),
  `metodyka/SHA256SUMS-trzon`, `metodyka/SHA256SUMS-trudne`, `metodyka/kontaminacja*.json`, progi kalibracji (`uczestnicy/*/prog.json`,
  `metodyka/progi.json`), `metodyka/*.md` przywołane wyżej,
  `uczestnicy/*` (konfiguracje, `uv.lock`; Privatizer w wersji ze znacznika w pkt 5).
- **Nie jest zamrażane tagiem, a powstaje po nim:** wyniki przebiegów.
- Zmiana po zamrożeniu = nowa wersja (np. `prerejestracja-2`) z opisem i wynikami obu wersji w raporcie. Pomiar czasu (`pbench-czas`)
  nie zmienia tych definicji – realizuje je.

## 10. Zmiany po zamrożeniu

Brak. Wpisy dodaje się wyłącznie po zamrożeniu: data, opis, uzasadnienie, odwołanie do wyników obu wersji.
