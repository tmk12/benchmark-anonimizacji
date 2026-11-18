# privatizer-tekst-maks

**Wariant aneksu (poza rankingami)**: `privatizer-tekst` w trybie „**Maksymalna ochrona**”. Założenie testu: ranking mierzy
tryb domyślny (`privatizer-tekst`: `balanced`, `KWOTA` wyłączona), ten wariant pokazuje, co zmienia tryb najsilniejszej ochrony.
Wszystko poza trybem – model (`lgp-1.0-rc`, kontener `.lgm`), paczki (słowniki, twarze, OCR), serwer, sprawa na dokument,
odczyt znaczników z podglądu zadania,
wersja wydania (ta sama co pierwowzór) – opisane w
[`../privatizer-tekst/KONFIG.md`](../privatizer-tekst/KONFIG.md) i **niezmienione**. `run.py` nie kopiuje potoku: ładuje `run.py` pierwowzoru
i woła `main(tryb="privacy")`.

## Co robi tryb (v1.3.0b24, `6ed25e2`; odwołania do tagu)

Tryb = `settings.sensitivity = "privacy"` (`settings.py`, `TRYBY`). Uczestnik ustawia go **funkcją aplikacji**
`settings.save({"sensitivity": "privacy"})` (`pw.ustaw_tryb`) w świeżym `LGP_DATA_DIR` **przed startem serwera** – tą samą, którą woła
ekran Ustawień; kategorii nie edytuje ręcznie. Skutki w wydaniu:

- **`KWOTA` włączona** – `settings.save` → `kwota_wg_trybu` (`settings.py`): wejście w `privacy` dopisuje `KWOTA` do
  kategorii i ustawia flagę `kwota_wg_trybu` (`settings.py`). Funkcja jest od `v1.3.0b22` (wydanie sprzed b22 jej nie ma – wariant przerywa wtedy
  start, zamiast mierzyć „Maksymalną ochronę” bez kwot).
- **Niższe progi modelu** – `engine.py` (`det.thresholds("privacy")`): `MmbertBioDetector.thresholds` (`detect/backends.py`) przycina
  progi z profilu `thresholds-privacy.json` taksonomii do przedziału `BIO_FLOOR/BIO_CAP` (`backends.py`, kopia `GLINER2_FLOOR/CAP`:
  dla `privacy` próg w [0,15; 0,60] zamiast [0,30; 0,90]); okno inicjałów 60 zamiast 40 (`detect/inicjaly.py`).
- **Inne reguły silnika** – lista wyjątków (`engine.py`, flaga trybu w `_Wyjatki`), tablice rejestracyjne bez słowa o pojeździe (D26),
  klauzula jurysdykcji (D11) **nie** zachowuje miejscowości/regionu/państwa, strony umowy, rzadkie słowa
  maskowane w strefach pewnych, kotwice marek CamelCase.
- **Polski: „między”/„pomiędzy”** nie wchodzi w osobę (`maks_ochrona` w `engine.py`; `detect/komparycja.py`).
- **Niepełnosprawność i rehabilitacja (D39)** – `ZDROWIE` jest w wydaniu domyślnie wyłączona w każdym trybie (`categories.py`, migracja 38),
  ale przy wyłączonej kategorii tryb `privacy` maskuje samą frazę o niepełnosprawności lub rehabilitacji (`zdrowie_maks` w `engine.py`:
  reguła i przepuszczenie przez filtr kategorii; `detect/niepelnosprawnosc.py`). Kody ICD-10, leki i rozpoznania zostają jawne.
  Zachowanie wynika z `Options.sensitivity`, nie z listy kategorii, więc opcje zadania nie wymagają dopisku.
- Ponowna analiza w przeglądzie idzie za trybem tak samo (`jobs.py`); uczestnik nie zmienia trybu w trakcie.

## Kategorie w opcjach zadania

Aplikacja bierze kategorie z **opcji zadania**, jeśli je podano (`server.py`: `{**settings.load(), **body}`). Uczestnicy
wysyłają kategorie jawnie (profil języka, `settings.profilowe_domyslne`), więc sama zmiana trybu w ustawieniach nie włączyłaby `KWOTA` w
zadaniu. `pw.opcje_jezyka` dokłada więc `KWOTA` do kategorii profilu języka **wtedy i tylko wtedy**, gdy ustawienia mają `KWOTA` włączoną
przez tryb (`kwota_wg_trybu`); w trybie domyślnym opcje są bez zmian. Pozostałe kategorie – dokładnie jak w pierwowzorze (domyślne
wydania dla języka dokumentu); `ZDROWIE` nie należy do nich w żadnym trybie (test: `tests/test_uczestnicy_maks.py`).

## Zakres gold

`etykiety.json` = pierwowzór + `"KWOTA": ["KWOTA"]` + `"ZDROWIE": ["ZDROWIE"]`: w konfiguracji wariantu `KWOTA` jest włączona, więc **jest w zakresie oceny**
(reguła J2, `metodyka/zakres-gold.md`; u pierwowzoru jako kategoria wyłączona – poza zakresem). `MAC`, `UUID` pozostają wyłączone,
`INICJALY` jak u pierwowzoru (przez model, pod `OSOBA`).
`etykiety.json` = pierwowzór + `ZDROWIE` (spany D39 w trybie privacy; korpus nie ma wartości gold tej kategorii, `metodyka/zakres-gold.md` sekcja 6), więc
frazy o niepełnosprawności maskowane trybem (D39) są dla sędziego nadmiarowym maskowaniem poza gold, nie wyciekiem ani błędem zakresu.

## Dowód w `wersje.json`

Jak u pierwowzoru, oraz: `czulosc` = `privacy` (odczyt ustawień po starcie serwera), `kategorie_ustawien` (kategorie aktywne w ustawieniach po
zmianie trybu, profil języka ustawień; per język idą kategorie profilu + `KWOTA`) i `kwota_wg_trybu` = `true`.

## Czas i wersja

Wariant nie jest mierzony czasem (`pbench-czas` – tylko tryb domyślny). Środowisko jak pierwowzór (ten sam tag wydania).
