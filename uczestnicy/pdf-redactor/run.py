"""Uczestnik `pdf-redactor`: pdf-redactor (JoshData) na PDF-ach z warstwą tekstu, poziom plik.

pdf-redactor zamienia tekst w strumieniach treści stron wyrażeniami regularnymi (`content_filters`), czyści metadane
(słownik Info, XMP) i adnotacje tekstowe; obrazów nie dotyka. Sam niczego nie wykrywa, więc wyrażenia budujemy z wykryć
analizatora w konfiguracji `presidio-pl-ner` (`../_wspolne/presidio_plikowe.py`) na tekście stron. Kolejność kroków
jak w README autorów: rozpakowanie strumieni (qpdf – tu jego biblioteka przez pikepdf), redakcja, ponowna kompresja
i linearyzacja. Konfiguracja i uzasadnienie: KONFIG.md."""
from __future__ import annotations

import io
import re
import sys
import tempfile
from pathlib import Path

KATALOG = Path(__file__).resolve().parent
sys.path.insert(0, str(KATALOG.parent / "_wspolne"))

import presidio_plikowe as pp  # noqa: E402
import presidio_wspolne as pw  # noqa: E402
import protokol_uczestnika as pu  # noqa: E402

MIN_ZNAKOW = 2                       # wartości z mniej niż 2 znakami alfanumerycznymi pomijamy (wzorzec zamieniłby je wszędzie)


def wzorzec_wartosci(wartosc: str) -> str | None:
    """Wyrażenie dla wykrytej wartości: części między białymi znakami dosłownie, odstępy jako `\\s*` (warstwa tekstu
    pdf-redactora skleja wiersze bez separatora, a wartość z pdfium może je mieć)."""
    if sum(ch.isalnum() for ch in wartosc) < MIN_ZNAKOW:
        return None
    return r"\s*".join(re.escape(cz) for cz in wartosc.split())


def wzorzec_dokumentu(wartosci: set[str]) -> re.Pattern | None:
    """Jedno wyrażenie-alternatywa ze wszystkich wartości, dłuższe najpierw (alternatywa bierze pierwszą pasującą)."""
    czesci = [w for w in (wzorzec_wartosci(v) for v in sorted(wartosci, key=lambda v: (-len(v), v))) if w]
    return re.compile("|".join(dict.fromkeys(czesci))) if czesci else None


def main() -> None:
    pu.ustaw_watki()
    import pdf_redactor
    import pikepdf
    import pypdfium2 as pdfium

    analizator = pp.AnalizatorPlNer()

    def tekst_stron(plik: Path) -> str:
        dokument = pdfium.PdfDocument(str(plik))
        try:
            return "\n".join(strona.get_textpage().get_text_range() for strona in dokument)
        finally:
            dokument.close()

    def przetworz(plik_wej: Path, plik_wyj: Path, jezyk: str) -> Path:
        tekst = tekst_stron(plik_wej)
        wartosci = {tekst[s:e] for s, e, _, _ in analizator.analizuj(tekst, jezyk)}
        wzorzec = wzorzec_dokumentu(wartosci)
        cel = plik_wyj.with_suffix(".pdf")
        with tempfile.TemporaryDirectory(prefix="pbench-pdfr-") as tmp:
            rozpakowany = Path(tmp) / "rozpakowany.pdf"
            with pikepdf.open(plik_wej) as pdf:          # `qpdf --stream-data=uncompress` (pdfrw nie zna strumieni obiektów)
                pdf.save(rozpakowany, compress_streams=False, stream_decode_level=pikepdf.StreamDecodeLevel.generalized,
                         object_stream_mode=pikepdf.ObjectStreamMode.disable)
            opcje = pdf_redactor.RedactorOptions()
            # jak w example.py autorów: metadane Info i XMP wyczyszczone, wartości zastąpione literami X
            opcje.metadata_filters = {"DEFAULT": [lambda wartosc: None]}
            opcje.xmp_filters = [lambda xml: None]
            opcje.content_filters = [(wzorzec, lambda m: "X" * len(m.group(0)))] if wzorzec else []
            wyjscie = io.BytesIO()
            with open(rozpakowany, "rb") as wej:
                opcje.input_stream, opcje.output_stream = wej, wyjscie
                pdf_redactor.redactor(opcje)
            with pikepdf.open(io.BytesIO(wyjscie.getvalue())) as pdf:     # `qpdf --linearize`
                pdf.save(cel, linearize=True)
        return cel

    wersje = {**analizator.wersje(), "pdf-redactor": pw.wersja("pdf-redactor"), "pdfrw": pw.wersja("pdfrw"),
              "pikepdf": pw.wersja("pikepdf"), "pypdfium2": pw.wersja("pypdfium2"),
              "pdf-redactor_rewizja": "JoshData/pdf-redactor@12ad5c68ab4174ccf579d43be005ac90b28d7d5f"}
    pp.petla_plikowa(wersje, przetworz)


if __name__ == "__main__":
    main()
