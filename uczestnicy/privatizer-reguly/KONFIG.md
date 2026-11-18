# privatizer-reguly

Reguły deterministyczne Privatizera **bez modelu**: wzorce i sumy kontrolne (PESEL, NIP, REGON, IBAN, karty, e-mail,
telefon, sygnatury…), pola i etykiety formularzy, tytuły i zwroty grzecznościowe, słowniki imion, komparycja, lista
wyjątków i rozchodzenie powtórzeń po dokumencie. Poziom: **tekst**, w procesie (bez serwera). Wariant ablacyjny – w **aneksie, poza
rankingami** (`aneks = true` w `uczestnik.toml`, `metodyka/punktacja.md`).

Działa jak zadanie tekstowe aplikacji (`POST /api/jobs/text`) bez modelu: `jobs.MemoryText` dzieli tekst na wiersze
(`\r\n` → `\n`), a `engine.detect(segmenty, Options(use_model=False, language=jezyk, …))` zwraca fragmenty; offsety wracają do
tekstu wejściowego (przeliczenie `\r\n`). Sugestie rzadkich słów (`Span.sugestia`), które aplikacja tylko podświetla, nie są
wykryciami. Licencji nie potrzeba (reguły nie wymagają modelu), więc nie ma serwera.

## Wersja i dowód, co zmierzono

Wydanie **v1.3.0b24** (commit `6ed25e2ea415a02a4a93c000ee630bda34f19f3b`)
repozytorium Privatizera. Pakiet `legalgeek-privatizer` jest instalowany **z rozpakowanego drzewa tagu**
(`git archive` tagu; w trybie edytowalnym), a nie ze zbudowanego koła z `git+file://` – zbudowane koło
tego wydania nie zawiera plików danych podpakietu `detect/uk_names/data` i pakiet nie importuje się (błąd pakietu tego wydania). Tak Privatizer uruchamia też własne testy obciążeniowe („wersja niespakowana”). Kodu Privatizera
nie zmieniamy ani nie łatamy.

Linia `gotowy` uczestnika niesie `wersje` zapisywane do `wyniki/surowe/<id>/wersje.json`: `lgprivatizer` (wersja pakietu),
`tag`, `commit`, `zrodla_sha` (skrót git katalogu `lgprivatizer/` liczony z działających plików i porównywany z `git rev-parse <tag>:lgprivatizer`; start przerwany przy rozbieżności), `torch`, `transformers`, `numpy`. Biblioteki ML mają wersje z `uv.lock` tego wydania
(`torch==2.14.0` z indeksu CPU, `transformers==4.57.6`).

## Paczki danych (jak domyślna instalacja)

Domyślna instalacja pobiera razem z modelem obowiązkowe paczki (`wybor_pobierania.wszystko()`): **słowniki imion i nazwisk**
(`slowniki-osob`, bez nich reguły OSOBA tracą wzorzec „Imię Nazwisko”, a detektor rzadkich słów jest wyłączony), **model
twarzy** (`yunet-face-2026may`, zaczernianie twarzy w obrazach) i **OCR** (`rapidocr-pp-ocrv6-small`). Uczestnik instaluje je
tym samym źródłem co aplikacja: z kanału aktualizacji aplikacji, wg podpisanego
manifestu kanału (weryfikowanego kodem aplikacji, `aktualizacje.zweryfikuj`; obecnie serial 25: słowniki 1.3.0, twarze 1.0.0,
OCR 1.0.0), z weryfikacją SHA-256 każdego pliku. Pliki (poza repozytorium) są dowiązane do katalogu modeli procesu. Mierzymy WYŁĄCZNIE z paczkami
(domyślne wydania); `wersje` niesie `slowniki_wersja`, `slowniki_sha256` (suma zbiorcza „ścieżka sha256” plików), analogicznie
`twarze_*`, `ocr_*` i `manifest_serial`. Start jest przerywany, gdy aplikacja nie widzi paczki w tej wersji.
Lista paczek, wersje i sumy pochodzą z podpisanego manifestu kanału test o serialu wydania (serial 31), nie z bieżącego stanu kanału; inny serial przerywa start.

Ten wariant instaluje tylko słowniki (reguły nie używają OCR ani twarzy). Sugestie rzadkich słów (`Span.sugestia`) wymagają leksykonu ze słowników; wariant w procesie odrzuca sugestię, której tekst (małymi literami) nie występuje w wykryciu niebędącym sugestią – aplikacja porównuje tokeny (po odmianie), więc odmieniona forma sugestii o „pewnym” lemacie bywa tu odrzucona, a w aplikacji zamieniona (różnica rzadka).

## Ustawienia: domyślne wydania

Niczego nie dostrajamy. Świeży katalog danych (`LGP_DATA_DIR`) na proces, tryb czułości **`balanced`** („Zrównoważony”,
`settings.DEFAULTS`), `expand_repeats` i `inflection` włączone, tryb zamiany `token`, czyszczenie metadanych włączone, OCR
włączony (paczka OCR – zob. „Paczki danych”). Jedyne ustawienie ruszone przez uczestnika to `autodownload=false`
(bez sieci; modele są lokalne), akceptacja warunków (`statystyki=false`) i aktywacja licencji.

**Język i kategorie.** Opcje zadania niosą `language` = `jezyk` dokumentu (profil wykrywania `pl/en/es/de/fr`). Kategorie i
lista wyjątków to to, co dostaje świeża instalacja w tym języku: `settings.profilowe_domyslne(jezyk)` (ta sama funkcja, którą
aplikacja wypełnia ustawienia przy pierwszym zapisie) – dla polskiego dokładnie `DEFAULT_ENABLED`, dla pozostałych języków
dodatkowo identyfikatory krajowe tego profilu (np. SSN, NINO, SVNR, NIR, DNI…). Rozstrzygnięcie integratora: bez tego
dokument angielski analizowany ustawieniami polskiej instalacji nie dostawałby krajowych identyfikatorów.

**Etykiety.** Uczestnik zwraca klucze kategorii Privatizera (`OSOBA`, `PESEL`…) – te same, co w gold; `etykiety.json` to
mapowanie tożsamościowe kategorii, które dają reguły, włączonych w ustawieniach domyślnych wydania (bez `WLASNE` i `TWARZ`;
bez domyślnie wyłączonych `KWOTA`, `MAC`, `UUID`, `INICJALY` i bez `ZDROWIE` – zakres deklarowany wg reguły
`metodyka/zakres-gold.md` pkt 4 (J2)). `ZDROWIE` jest w wydaniu domyślnie wyłączona w każdym trybie (migracja 38), więc reguły kodów ICD-10 (D35, `detect/icd10.py`)
i niepełnosprawności (D39, `detect/niepelnosprawnosc.py`) w konfiguracji benchmarku `ZDROWIE` nie zwracają (D39 działa tylko w trybie
„Maksymalna ochrona” – warianty aneksu `-maks`). Gdyby reguła ICD-10 działała, zwracałaby sam kod z kontekstem („I25.1”), a wartość
gold `ZDROWIE` to nazwa choroby albo kod z nazwą – kod byłby jej fragmentem (J2 pkt 2); `ZDROWIE` zostaje poza deklaracją.
Próg: Privatizer nie ma progu do kalibracji – próg modelu wynika z trybu
czułości wydania, więc `prog.json` nie obowiązuje i `PBENCH_SUROWE` nie zmienia wyniku; `wynik` = pewność fragmentu
(reguły 0,90–1,00, model: pewność adaptera).

## Języki

Oficjalnie pl, en, es, de, fr (profile językowe Privatizera); dokument ukraiński dostaje w aplikacji profil `uk`
automatycznie (`jezyki.jezyk_analizy`), korpus go nie zawiera. Ruling R37: wszystkie 5.
