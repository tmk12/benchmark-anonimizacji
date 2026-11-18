"""Uczestnik `presidio-image-redactor`: Microsoft Presidio Image Redactor na skanach PDF, poziom plik.

Każda strona skanu → obraz (pypdfium2, 300 dpi) → `ImageRedactorEngine.redact` (OCR Tesseract + analizator tekstu,
czarne prostokąty na słowach wykrytych encji) → strony z powrotem w jeden PDF (PIL). Analizator tekstu to konfiguracja
`presidio-pl-ner` (`../_wspolne/presidio_plikowe.py`; okna tokenowe – tekst strony z OCR bywa dłuższy niż limit modelu).
Konfiguracja i uzasadnienie: KONFIG.md."""
from __future__ import annotations

import os
import sys
from pathlib import Path

KATALOG = Path(__file__).resolve().parent
KORZEN = KATALOG.parent.parent
sys.path.insert(0, str(KATALOG.parent / "_wspolne"))

import presidio_plikowe as pp  # noqa: E402
import presidio_wspolne as pw  # noqa: E402
import protokol_uczestnika as pu  # noqa: E402

DPI = 300                                   # zalecenie Tesseracta dla OCR; skany korpusu mają 200 dpi
WYPELNIENIE = (0, 0, 0)                     # domyślne `fill` w `ImageRedactorEngine.redact`
JEZYK_OCR = {"pl": "pol", "en": "eng", "es": "spa", "de": "deu", "fr": "fra"}
# dane Tesseracta z `vendor/tessdata` (systemowy Tesseract na serwerach trafności ma tylko eng/osd/pol – `metodyka/srodowiska.md`)
TESSDATA = KORZEN / "vendor" / "tessdata"


class AnalizatorOknami:
    """Analizator dla `ImageAnalyzerEngine` (wywołuje `analyze(text=..., language=...)` na całym tekście strony z OCR):
    to samo co `AnalyzerEngine.analyze`, ale oknami tokenowymi `presidio-pl-ner` (bez nich model NER ucina tekst strony)."""

    def __init__(self, analizator: pp.AnalizatorPlNer) -> None:
        self.analizator = analizator

    def analyze(self, text: str, language: str, **_):
        return self.analizator.wyniki_presidio(text, language)


def main() -> None:
    pu.ustaw_watki()
    if TESSDATA.is_dir() and "TESSDATA_PREFIX" not in os.environ:
        os.environ["TESSDATA_PREFIX"] = str(TESSDATA)
    import pypdfium2 as pdfium
    import pytesseract
    from presidio_image_redactor import ImageAnalyzerEngine, ImageRedactorEngine, TesseractOCR

    analizator = pp.AnalizatorPlNer()
    silnik = ImageRedactorEngine(image_analyzer_engine=ImageAnalyzerEngine(
        analyzer_engine=AnalizatorOknami(analizator), ocr=TesseractOCR()))

    def przetworz(plik_wej: Path, plik_wyj: Path, jezyk: str) -> Path:
        dokument = pdfium.PdfDocument(str(plik_wej))
        try:
            strony = []
            for strona in dokument:
                obraz = strona.render(scale=DPI / 72).to_pil().convert("RGB")
                strony.append(silnik.redact(obraz, fill=WYPELNIENIE, ocr_kwargs={"lang": JEZYK_OCR[jezyk]},
                                            language=jezyk))
        finally:
            dokument.close()
        if not strony:
            raise ValueError("PDF bez stron")
        cel = plik_wyj.with_suffix(".pdf")
        strony[0].save(cel, "PDF", resolution=DPI, save_all=True, append_images=strony[1:])
        return cel

    wersje = {**analizator.wersje(), "presidio-image-redactor": pw.wersja("presidio-image-redactor"),
              "pypdfium2": pw.wersja("pypdfium2"), "tesseract": str(pytesseract.get_tesseract_version()), "dpi": str(DPI)}
    pp.petla_plikowa(wersje, przetworz)


if __name__ == "__main__":
    main()
