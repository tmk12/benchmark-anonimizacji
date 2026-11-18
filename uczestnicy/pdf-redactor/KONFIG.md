# pdf-redactor

**pdf-redactor** (Joshua Tauberer, Antoine McGrath; <https://github.com/JoshData/pdf-redactor>) – redakcja warstwy tekstu PDF
wyrażeniami regularnymi, w czystym Pythonie (pdfrw). Grupa B (bez kalibracji). Poziom: **plik**; format: pdf (z warstwą tekstu).
Skany są poza zakresem narzędzia (README: „Graphical elements, images … are not touched”) – zajmuje się nimi
`presidio-image-redactor`.

## Wersje i źródło (przypięte, `uv.lock` w repo)

| Składnik | Wersja / rewizja | Licencja |
|---|---|---|
| pdf-redactor | **oficjalne repozytorium** `JoshData/pdf-redactor`, commit `12ad5c68ab4174ccf579d43be005ac90b28d7d5f` (2019-05-31, ostatni na gałęzi `primary`), instalacja `git+https` z przypiętym commitem | CC0-1.0 |
| pdfrw / defusedxml | 0.4 / 0.7.1 | MIT / PSF-2.0 |
| pikepdf (biblioteka qpdf) | 10.17.0 | MPL-2.0 |
| pypdfium2 (PDFium) | 5.14.0 | BSD-3-Clause / Apache-2.0 |
| analizator | jak `presidio-pl-ner` (te same wersje i modele – test `test_plikowi_maja_wersje_presidio_pl_ner`) | zob. `../presidio-pl-ner/KONFIG.md` |

Pakiet `pdf-redactor` 0.0.1 z PyPI **nie jest** używany: opublikował go fork `vitalbeats/pdf-redactor` (adres projektu w metadanych
PyPI), nie autorzy – instalujemy kod z repozytorium autorów.

## Konfiguracja („regex + wykrycia `presidio-pl-ner`”)

pdf-redactor niczego sam nie wykrywa – przyjmuje listę `content_filters` (wyrażenie regularne → funkcja zamiany), stosowaną do
tekstu wszystkich stron sklejonego w jeden ciąg (oraz do adnotacji tekstowych). Wykrycia daje analizator w konfiguracji
`presidio-pl-ner` (kod ładowany z `../presidio-pl-ner/run.py` przez `../_wspolne/presidio_plikowe.py`):

1. Tekst do wykrywania: strony z PDFium (`pypdfium2`, `get_text_range`), połączone znakiem nowego wiersza. Nie bierzemy tekstu
   z warstwy pdf-redactora (sposób z jego `pdftotext.py`), bo skleja wiersze bez separatora („Marcin DąbrowskiAplikant”) i psuje NER.
2. Każda wykryta wartość → wzorzec: części między białymi znakami dosłownie (`re.escape`), odstępy jako `\s*` (w warstwie
   pdf-redactora odstępu na końcu wiersza nie ma). Wartości z mniej niż 2 znakami alfanumerycznymi pomijamy (wzorzec zamieniłby
   je w całym dokumencie). Wszystkie wzorce w jednej alternatywie, dłuższe najpierw.
3. Zamiana jak w `example.py` autorów: dopasowanie → tyle samo liter `X` (pdf-redactor sam podstawia znaki obecne w czcionce,
   `content_replacement_glyphs`). Zamiana dotyczy każdego wystąpienia wartości w dokumencie.
4. Metadane jak w `example.py`: słownik Info wyczyszczony (`metadata_filters = {"DEFAULT": [lambda v: None]}`), XMP usunięte
   (`xmp_filters = [lambda xml: None]`). Adresów linków (`link_filters`) nie zmieniamy (przykład autorów podmienia je na stały
   adres – to demonstracja, nie anonimizacja).
5. Kolejność z README autorów („Content stream compression”): rozpakowanie strumieni przed redakcją i kompresja + linearyzacja po
   niej – README podaje `qpdf --stream-data=uncompress …` i `qpdf --linearize …`; robimy to biblioteką qpdf przez pikepdf
   (`stream_decode_level=generalized`, `compress_streams=False`, `object_stream_mode=disable` – pdfrw nie czyta strumieni obiektów;
   potem `save(linearize=True)`), bo programu `qpdf` nie ma na maszynach pomiarowych.

`etykiety.json` = jak w `presidio-pl-ner` (redagowane jest wszystko, co analizator wykryje).

## Ograniczenia narzędzia (z README, istotne dla wyników)

Bez zmian zostają: obrazy (w tym skany i logotypy z tekstem), pola formularzy, adnotacje z tekstem sformatowanym, osadzone pliki,
podpisy cyfrowe, nazwy obiektów; czcionki z nietypowym mapowaniem glifów mogą nie dać się dopasować. Wartość rozbita w PDF-ie
między operatory tekstu jest dopasowywana (pdf-redactor mapuje sklejony tekst na tokeny strumienia), ale wartość z przeniesieniem
(„Kowal-\nski”) – nie. Błąd parsowania pdfrw = `blad` (dla sędziego brak pliku wynikowego).

## Format wyniku (R42)

PDF; uczestnik zwraca rzeczywistą ścieżkę zapisanego pliku.

## Języki, próg

Jak `presidio-pl-ner` (5 języków, R37; próg z `presidio-pl-ner/prog.json`, gdy istnieje, inaczej domyślny autorów).

**Wyjątek od „bez kalibracji” (grupa B):** próg jest dziedziczony z konfiguracji bazowej `presidio-pl-ner` także po jej kalibracji
(zob. `metodyka/uczestnicy.md`, sekcja grupy B).
