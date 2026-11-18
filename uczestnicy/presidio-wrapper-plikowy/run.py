"""Uczestnik `presidio-wrapper-plikowy`: NASZ naiwny wrapper plikowy (nie produkt) – Presidio w konfiguracji
`presidio-pl-ner` + podmiana tekstu w DOCX/XLSX/PPTX typowymi bibliotekami, poziom plik.

Tak, jak robi to typowy integrator (źródła wzorca w KONFIG.md): python-docx – akapity treści głównej i komórki tabel,
openpyxl – komórki tekstowe arkuszy, python-pptx – akapity kształtów z ramką tekstu. Tekst akapitu/komórki →
`presidio-analyzer` (konfiguracja `presidio-pl-ner`, `../_wspolne/presidio_plikowe.py`) → `presidio-anonymizer`
(operator domyślny: `<TYP_ENCJI>`) → tekst wpisany z powrotem. Nagłówków, stopek, przypisów, komentarzy, śledzonych zmian,
pól, notatek, metadanych itp. wrapper nie dotyka – to wzorzec „co zostaje, gdy anonimizuje się tylko tekst”.
Konfiguracja i uzasadnienie: KONFIG.md."""
from __future__ import annotations

import sys
from pathlib import Path

KATALOG = Path(__file__).resolve().parent
sys.path.insert(0, str(KATALOG.parent / "_wspolne"))

import presidio_plikowe as pp  # noqa: E402
import presidio_wspolne as pw  # noqa: E402
import protokol_uczestnika as pu  # noqa: E402


def main() -> None:
    pu.ustaw_watki()
    import docx
    import openpyxl
    import pptx
    from presidio_anonymizer import AnonymizerEngine

    analizator = pp.AnalizatorPlNer()
    anonimizator = AnonymizerEngine()

    def anonimizuj(tekst: str, jezyk: str) -> str | None:
        """Tekst po anonimizacji albo None, gdy nic nie wykryto (element zostaje nietknięty)."""
        if not tekst.strip():
            return None
        wyniki = analizator.wyniki_presidio(tekst, jezyk)
        return anonimizator.anonymize(text=tekst, analyzer_results=wyniki).text if wyniki else None

    def docx_(plik_wej: Path, cel: Path, jezyk: str) -> None:
        dokument = docx.Document(str(plik_wej))
        for akapit in dokument.paragraphs:
            nowy = anonimizuj(akapit.text, jezyk)
            if nowy is not None:                  # stare przebiegi usunięte, nowy tekst w jednym przebiegu
                akapit.clear()
                akapit.add_run(nowy)
        for tabela in dokument.tables:
            widziane = set()
            for wiersz in tabela.rows:
                for komorka in wiersz.cells:
                    if id(komorka._tc) in widziane:   # komórka scalona występuje w `cells` kilka razy
                        continue
                    widziane.add(id(komorka._tc))
                    nowy = anonimizuj(komorka.text, jezyk)
                    if nowy is not None:
                        komorka.text = nowy
        dokument.save(str(cel))

    def xlsx_(plik_wej: Path, cel: Path, jezyk: str) -> None:
        skoroszyt = openpyxl.load_workbook(plik_wej)
        for arkusz in skoroszyt.worksheets:
            for wiersz in arkusz.iter_rows():
                for komorka in wiersz:
                    if komorka.data_type == "s" and isinstance(komorka.value, str):
                        nowy = anonimizuj(komorka.value, jezyk)
                        if nowy is not None:
                            komorka.value = nowy
        skoroszyt.save(cel)

    def pptx_(plik_wej: Path, cel: Path, jezyk: str) -> None:
        prezentacja = pptx.Presentation(str(plik_wej))
        for slajd in prezentacja.slides:
            for ksztalt in slajd.shapes:
                if not ksztalt.has_text_frame:
                    continue
                for akapit in ksztalt.text_frame.paragraphs:
                    nowy = anonimizuj(akapit.text, jezyk)
                    if nowy is not None:          # setter `text` zastępuje przebiegi jednym
                        akapit.text = nowy
        prezentacja.save(str(cel))

    obslugi = {".docx": docx_, ".xlsx": xlsx_, ".pptx": pptx_}

    def przetworz(plik_wej: Path, plik_wyj: Path, jezyk: str) -> Path:
        rozszerzenie = plik_wej.suffix.lower()
        if rozszerzenie not in obslugi:
            raise ValueError(f"nieobsługiwany format {rozszerzenie}")
        cel = plik_wyj.with_suffix(rozszerzenie)
        obslugi[rozszerzenie](plik_wej, cel, jezyk)
        return cel

    wersje = {**analizator.wersje(), "presidio-anonymizer": pw.wersja("presidio-anonymizer"),
              "python-docx": pw.wersja("python-docx"), "openpyxl": pw.wersja("openpyxl"),
              "python-pptx": pw.wersja("python-pptx")}
    pp.petla_plikowa(wersje, przetworz)


if __name__ == "__main__":
    main()
