# Środowiska uruchomieniowe benchmarku

Maszyny, ścieżki i zależności środowiska pomiarów. Wersja wydania Privatizera i modelu – wyłącznie według prerejestracji
(`metodyka/prerejestracja.md`, pkt 5); stan maszyn (selftest, wolne miejsce, wersje Pythona i uv) potwierdza się przed przebiegiem
i zapisuje w `srodowisko.json` / `wersje.json` przebiegu.

## Maszyny

| Rola | OS | CPU | Rdzenie | RAM | Tesseract (systemowy) |
|---|---|---|---|---|---|
| Serwery trafności: 3 × Linux aarch64, NVIDIA GB10, 20 rdzeni, CPU bez GPU | Ubuntu 24.04, Linux aarch64 | NVIDIA GB10 (Cortex-X925 + A725) | 20 | ok. 120 GiB | 5.3.4; języki: eng, osd, pol |
| Maszyna referencyjna czasu: Apple M1, 8 GB RAM, macOS (T6/P7, `prerejestracja.md` pkt 1.2) | macOS, arm64 | Apple M1 | 8 | 8 GB | – |

Obliczenia trafności wyłącznie na CPU. Gdy serwery trafności były zajęte innymi obliczeniami, kroki benchmarku uruchamiano
z `nice -n 19`.

## Ścieżki (względem katalogu repozytorium)

| Co | Ścieżka |
|---|---|
| Kod harnessu | katalog repozytorium (środowisko: `.venv`, `uv sync --python 3.12`; bez torcha) |
| Korpus syntetyczny | `korpus/` i `korpus-trudne/` (tylko na serwerach trafności) |
| Dane Tesseracta (pol, eng, spa, deu, fra, ukr, osd – tessdata_fast; `ukr` do warstwy trudnej H1) | `vendor/tessdata/` (uruchamiać z `TESSDATA_PREFIX` na ten katalog; systemowy Tesseract serwerów trafności ma tylko eng, osd, pol; sumy plików – `prerejestracja.md`) |
| Privatizer – wydanie z prerejestracji | wydanie `v1.3.0b24` (`prerejestracja.md`, pkt 5); adaptery Privatizera nie są publiczne (`README.md`) |

## Uwagi

- **Torch:** uczestnicy z torchem instalują go z indeksu `pytorch-cpu` także na aarch64; bez pakietów `nvidia-*`,
  `torch.version.cuda = None`. Projekt harnessu nie ma zależności od torcha.
- **Tesseract – `ukr` (H1, warstwa trudnych przypadków):** OCR sędziego dla dokumentów z cyrylicą ukraińską czyta danymi `ukr`
  (`uk` → `ukr+eng`, dokument PL/EN/DE z ukraińską wstawką → np. `pol+ukr`). `ukr.traineddata` (tessdata_fast, Apache-2.0;
  `https://github.com/tesseract-ocr/tessdata_fast/raw/main/ukr.traineddata`, 3,8 MB) leży w `vendor/tessdata/` jak
  pozostałe języki; systemowy Tesseract serwerów trafności nie ma `ukr`.
- **Tesseract:** na serwerach trafności systemowy 5.3.4 z samymi eng/osd/pol, brakujące języki z `vendor/tessdata`.
- **Czcionka podpisów z cyrylicą (H1):** `pbench/render/podpis.py` rysuje podpisy z cyrylicą kursywą Liberation Serif
  z zapisaną na stałe ścieżką `/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf` (bez zastępstwa – Z003 nie ma
  cyrylicy). Generowanie warstwy trudnej wymaga więc pakietu `fonts-liberation` (Ubuntu: `sudo apt install fonts-liberation`); na
  maszynach bez niego renderer podpisu zgłosi brak pliku czcionki.

## Zależności generatora PDF z tekstem RTL (H4a, poprawki 1)

Kolejność wizualna i kształtowanie liter w PDF-ach przypadku `rtl` (`pbench/render/pdf.py`): `arabic-reshaper` 3.0.1 (licencja MIT)
i `python-bidi` 0.6.12 (nakładka na crate `unicode-bidi`; licencja LGPL-3.0-or-later, pliki `COPYING`/`COPYING.LESSER` w pakiecie).
Kod harnessu jest na Apache-2.0: biblioteka LGPL jest tu zwykłą zależnością instalowaną z PyPI (dynamicznie importowaną, bez
kopiowania jej kodu do repozytorium i bez modyfikacji), co licencja LGPL-3.0 dopuszcza także dla kodu na Apache-2.0 (Apache-2.0 jest
zgodna z GPLv3/LGPLv3). Pliki korpusu (wynik działania generatora) nie są dziełem zależnym od biblioteki. Do testów dochodzi
`pdfminer.six` (MIT) w grupie `dev` – drugi niezależny parser PDF.

## Konwersje RTF i ODT (H4b)

Przypadek `formaty_rtf_odt` konwertuje DOCX do RTF i ODT LibreOffice'em (`soffice --headless --convert-to rtf|odt`, sprawdzone na
LibreOffice 24.2.7.2) – tym samym, którym generator robi DOC (licencja MPL-2.0; program zewnętrzny wywoływany jako proces, bez
kopiowania kodu). Bez nowych zależności Pythona: vCard zapisuje i czyta własny kod, RTF czyta własny parser sędziego
(`pbench/sedzia/rtf.py`), ODT – `zipfile` i `lxml`. Bajty RTF/ODT są powtarzalne dopiero po normalizacji (`render/rtf.py`,
`render/odt.py` – zob. ich docstringi); inna wersja LibreOffice'a może dać inne bajty (sumy kontrolne korpusu trudnego wymagają
tej samej wersji).
