# privatizer-tekst

**Pełny potok tekstowy** Privatizera przez serwer aplikacji: model + reguły + pola + wyjątki + rozchodzenie powtórzeń +
dopracowanie. Poziom: **tekst**.

Jeden serwer (`python -m lgprivatizer --no-open`, port wolny, token sesji) na proces uczestnika, wspólny dla dokumentów,
zamykany SIGTERM-em przy wyjściu (z `SIGKILL` po 60 s). Start: serwer → `POST /api/settings`
(`autodownload=false`) → `POST /api/legal/accept` → `POST /api/license/activate` → `POST /api/models/lgp-1.0-rc/load`
i oczekiwanie na załadowanie. Dokument: `POST /api/jobs/text` → odpytywanie `GET /api/jobs/{id}` do stanu `review` →
`GET /api/jobs/{id}/entities` (flagi sugestii) i `GET /api/jobs/{id}/preview/{plik}` (znaczniki `s`/`e` w tekście podglądu,
który musi być równy tekstowi wejściowemu po `\r\n` → `\n`) → `DELETE`. Zadanie bez modelu (`model` ≠ `lgp-1.0-rc`),
podgląd ucięty (>150 000 znaków; korpus ma dokumenty do ~23 tys.) albo niezgodny tekst podglądu to `blad`, nie wynik.

## Model

Domyślny model wydania: **`lgp-1.0-rc`** („Legal Geek Privatizer (RC)”), paczka `1.0.0rc5`, adapter `MmbertBioDetector`
(klasyfikator tokenów BIO), jeden model dla wszystkich języków. Wydanie ładuje go jako **kontener `.lgm`** (podpisany
i zaszyfrowany; wagi, konfiguracja, tokenizer i progi są w środku). Uczestnik ładuje model ścieżką kodu wydania – tą samą co
zainstalowana aplikacja – bez kopiowania ani zmieniania kontenera; brak modelu przerywa start (bez cichej degradacji do reguł).
Sposób dostarczenia modelu i licencji w przebiegu pomiarowym nie jest częścią repozytorium publicznego (adaptery Privatizera
nie są publikowane – `README.md`).

Dowód tożsamości modelu (w `wersje`): `kontener_sha256` (`a5c954f1…35611d`, zgodny z sumą w rejestrze aplikacji –
`kontener_zgodny_z_rejestrem`), `wagi_model_safetensors_sha256` (`5d73972d…ce76b`; suma wag z nagłówka kontenera, sprawdzana
przez aplikację po odszyfrowaniu), `folder_modelu`, `paczka_modelu`.

## Wersja i dowód, co zmierzono

Wydanie **v1.3.0b24** (commit `6ed25e2ea415a02a4a93c000ee630bda34f19f3b`)
repozytorium Privatizera. Pakiet `legalgeek-privatizer` jest instalowany **z rozpakowanego drzewa tagu**
(`git archive` tagu; w trybie edytowalnym), a nie ze zbudowanego koła z `git+file://` – zbudowane koło
tego wydania nie zawiera plików danych podpakietu `detect/uk_names/data` i pakiet nie importuje się (błąd pakietu tego wydania). Tak Privatizer uruchamia też własne testy obciążeniowe („wersja niespakowana”). Kodu Privatizera
nie zmieniamy ani nie łatamy.

Model w v1.3.0b24: `lgp-1.0-rc`, paczka `1.0.0rc5`, suma kontenera w rejestrze aplikacji (`models.py` tagu). Kategoria
`ZDROWIE` jest w tym wydaniu domyślnie wyłączona w każdym trybie i profilu (`categories.py`, migracja 38 w `settings.py`);
`etykiety.json` jej nie deklaruje (reguła J2: zakres = kategorie włączone w ustawieniach domyślnych wydania; `metodyka/zakres-gold.md`, sekcja 6).

Linia `gotowy` uczestnika niesie `wersje` zapisywane do `wyniki/surowe/<id>/wersje.json`: `lgprivatizer` (wersja pakietu),
`tag`, `commit`, `zrodla_sha` (skrót git katalogu `lgprivatizer/` liczony z działających plików i porównywany z `git rev-parse <tag>:lgprivatizer`; start przerwany przy rozbieżności), `torch`, `transformers`, `numpy`. Biblioteki ML mają wersje z `uv.lock` tego wydania
(`torch==2.14.0` z indeksu CPU, `transformers==4.57.6`).

**Sprawa.** Jeden dokument = jedna świeża sprawa (`POST /api/cases` przed, `DELETE /api/cases/{id}` po dokumencie); serwer jest wspólny dla dokumentów procesu. Skarbiec spraw nie rośnie między dokumentami, a numeracja tokenów nie zależy od kolejności.

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

Wariant instaluje słowniki, twarze i OCR (komplet domyślnej instalacji); dla tekstu liczą się słowniki.

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
mapowanie tożsamościowe kategorii włączonych w ustawieniach domyślnych wydania (bez `WLASNE` i `TWARZ`; bez domyślnie
wyłączonych `KWOTA`, `MAC`, `UUID`, `INICJALY` – `categories.py` tagu); `OSOBA` obejmuje też `INICJALY`, bo inicjały znalezione
przez model (etykieta „person initials”) idą pod `OSOBA` – zakres deklarowany wg reguły
`metodyka/zakres-gold.md` pkt 4 (J2).
Próg: Privatizer nie ma progu do kalibracji – próg modelu wynika z trybu
czułości wydania, więc `prog.json` nie obowiązuje i `PBENCH_SUROWE` nie zmienia wyniku; `wynik` = pewność fragmentu
(reguły 0,90–1,00, model: pewność adaptera).

## Języki

Oficjalnie pl, en, es, de, fr. Ruling R37: wszystkie 5.
