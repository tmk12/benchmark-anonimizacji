# presidio-image-redactor

**Microsoft Presidio Image Redactor** (<https://github.com/microsoft/presidio/tree/main/presidio-image-redactor>) – OCR obrazu (Tesseract),
wykrywanie w tekście z OCR analizatorem Presidio i zamalowanie prostokątami słów wykrytych encji. Grupa B (bez kalibracji).
Poziom: **plik**; format: skan (PDF ze stronami-obrazami). PDF-y z warstwą tekstu – poza zakresem (narzędzie pracuje na obrazach;
tekst zamalowany na obrazie strony zostałby w warstwie tekstu) – to zakres `pdf-redactor`.

## Wersje (przypięte, `uv.lock` w repo)

| Składnik | Wersja | Licencja |
|---|---|---|
| presidio-image-redactor | 0.0.62 | MIT |
| pytesseract / Tesseract (systemowy) | 0.3.13 / 5.3.4 (wersja w `wersje`) | Apache-2.0 / Apache-2.0 |
| dane Tesseracta | `vendor/tessdata` (tessdata_fast: pol, eng, spa, deu, fra – `metodyka/srodowiska.md`) | Apache-2.0 |
| pypdfium2 (PDFium) / Pillow | 5.14.0 / 13.0.0 | BSD-3-Clause, Apache-2.0 / MIT-CMU |
| zależności pakietu (pydicom, python-gdcm, opencv-python, azure-ai-formrecognizer, matplotlib) | wg `uv.lock`; nieużywane w tej ścieżce | MIT / BSD / Apache-2.0 / MIT / PSF |
| analizator | jak `presidio-pl-ner` (test `test_plikowi_maja_wersje_presidio_pl_ner`) | zob. `../presidio-pl-ner/KONFIG.md` |

## Konfiguracja

Wg dokumentacji autorów (opis pakietu 0.0.62, <https://pypi.org/project/presidio-image-redactor/0.0.62/>, „Getting started
(standard image types)”): `ImageRedactorEngine().redact(image, fill)` (domyślnie czarne wypełnienie); własny analizator i OCR
przez konstruktory `ImageRedactorEngine(image_analyzer_engine=ImageAnalyzerEngine(analyzer_engine=…, ocr=TesseractOCR()))`
(parametry pakietu). Domyślny `AnalyzerEngine()` zna tylko angielski (spaCy `en_core_web_lg`), więc dla 5 języków korpusu
podstawiamy analizator `presidio-pl-ner`.

* **Strony → obrazy:** Presidio nie czyta PDF-ów, więc integrator renderuje strony; tu PDFium (`pypdfium2`) w **300 dpi**
  (zalecenie Tesseracta; skany korpusu mają 200 dpi), RGB. Wynik: strony po redakcji zapisane jako jeden PDF (Pillow,
  `resolution=300` – rozmiar strony jak w oryginale).
* **OCR:** `TesseractOCR` z `ocr_kwargs={"lang": <pol|eng|spa|deu|fra>}` wg języka dokumentu; `TESSDATA_PREFIX` = `vendor/tessdata`,
  jeśli nie ustawiono (systemowy Tesseract na serwerach trafności ma tylko eng/osd/pol). Wstępne przetwarzanie obrazu i progi OCR – domyślne pakietu.
* **Analizator tekstu:** konfiguracja `presidio-pl-ner` (kod z `../presidio-pl-ner/run.py` przez `../_wspolne/presidio_plikowe.py`),
  `language` = język dokumentu. `ImageAnalyzerEngine` woła `analyze(text=…, language=…)` na całym tekście strony; nasza nakładka
  (`AnalizatorOknami` w `run.py`) robi to oknami tokenowymi `presidio-pl-ner` (bez nich model NER ucina długi tekst strony) i
  zwraca `RecognizerResult` – mapowanie wykryć na ramki słów robi pakiet (`map_analyzer_results_to_bounding_boxes`).
* **Zamalowanie:** `fill=(0, 0, 0)` – domyślne pakietu (czarne prostokąty).

`etykiety.json` = jak w `presidio-pl-ner` (zamalowywane jest wszystko, co analizator wykryje w tekście z OCR).

## Ograniczenia narzędzia istotne dla wyników

Wynik zależy od OCR (słowo źle odczytane nie zostanie wykryte ani zamalowane); prostokąty obejmują ramki słów Tesseracta.
Wynikowy PDF nie ma warstwy tekstu (strony to obrazy). Błąd renderowania/OCR = `blad`.

## Format wyniku (R42)

PDF (strony-obrazy); uczestnik zwraca rzeczywistą ścieżkę zapisanego pliku.

## Języki, próg

Jak `presidio-pl-ner` (5 języków, R37; Tesseract ma dane dla wszystkich pięciu). Próg z `presidio-pl-ner/prog.json`, gdy istnieje,
inaczej domyślny autorów.

**Wyjątek od „bez kalibracji” (grupa B):** próg jest dziedziczony z konfiguracji bazowej `presidio-pl-ner` także po jej kalibracji
(zob. `metodyka/uczestnicy.md`, sekcja grupy B).
