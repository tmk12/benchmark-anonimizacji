"""Renderer DOC (Word 97-2003): DOCX z `renderuj_docx` przekonwertowany LibreOffice'em (`soffice --headless
--convert-to doc`) – LibreOffice wolno używać w generatorze korpusu (nie w Privatizerze). Utrudnienia i wejście jak w
DOCX (`UTRUDNIENIA_DOC` = `UTRUDNIENIA_DOCX`, `przytnij_dla("doc", …)` = `przytnij`).

Gold = wartości DOCX po sprawdzeniu pliku DOC: DOC jest odczytywany z powrotem (LibreOffice DOC -> DOCX) i każda
wartość musi występować w tekście swojego miejsca (komentarze, nagłówek, przypisy, treść, właściwości…) jako całe
słowa (granice słów – krótka wartość nie jest „potwierdzona” fragmentem dłuższego wyrazu); obraz – jako bajty PNG w
strumieniu `Data` pliku DOC (`olefile`). To, czego konwersja nie zachowała, jest usuwane z gold z ostrzeżeniem w
`WynikDoc.ostrzezenia`. (Tekst Worda leży w `WordDocument` w cp1252 albo UTF-16LE, właściwości w UTF-8 –
`ZAKODOWANIA_TEKSTU` do wyszukiwań w surowych strumieniach, np. w testach.)

Zbadane (LibreOffice 24.2): konwersja zachowuje komentarze (z autorem), zmiany śledzone (autor, tekst usunięty także),
przypisy, nagłówek i stopkę, pola formularza (jako tekst), tabele, obrazy (PNG bez zmian), właściwości podstawowe
(autor, tytuł, temat) i własne; rozbite runy łączy w jeden. Niedeterministyczność: brak – kolejne konwersje tego samego
DOCX dają identyczne bajty (daty plików ustala renderer DOCX, a LibreOffice nie dopisuje bieżącego czasu); każde
wywołanie używa osobnego, tymczasowego profilu LibreOffice (równoległe konwersje się nie blokują).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import olefile
from lxml import etree

from ..model import Dokument, Obraz, Wartosc
from ..utrudnienia import UTRUDNIENIA_DOC, UTRUDNIENIA_POMINIETE
from .docx import renderuj_docx

#: Kodowania, w których tekst może leżeć w strumieniach DOC (tekst Worda 8-bitowy / UTF-16LE, właściwości UTF-8).
ZAKODOWANIA_TEKSTU: tuple[str, ...] = ("utf-16-le", "cp1252", "cp1250", "utf-8")
CZAS_KONWERSJI_S = 180


@dataclass
class WynikDoc:
    """Wynik renderowania: wartości i obrazy z gold zachowane w DOC oraz ostrzeżenia o tym, co konwersja zgubiła."""

    wartosci: list[Wartosc] = field(default_factory=list)
    obrazy: list[Obraz] = field(default_factory=list)
    ostrzezenia: list[str] = field(default_factory=list)


def _soffice() -> str:
    sciezka = os.environ.get("PBENCH_SOFFICE") or shutil.which("soffice")
    if not sciezka:
        raise RuntimeError("brak LibreOffice (`soffice`) – ustaw PBENCH_SOFFICE albo dodaj go do PATH")
    return sciezka


def konwertuj(wejscie: Path, wyjscie: Path, format_docelowy: str) -> None:
    """Konwersja LibreOffice'em (`doc:MS Word 97` albo `docx`) do `wyjscie` (jedna próba ponowiona, gdy brak pliku)."""
    rozszerzenie = format_docelowy.split(":")[0]
    with tempfile.TemporaryDirectory(prefix="pbench-soffice-") as tmp:
        katalog = Path(tmp)
        for _proba in range(2):
            subprocess.run([_soffice(), "--headless", "--norestore", f"-env:UserInstallation=file://{katalog / 'profil'}",
                            "--convert-to", format_docelowy, "--outdir", str(katalog / "out"), str(wejscie)],
                           capture_output=True, timeout=CZAS_KONWERSJI_S)
            wynik = katalog / "out" / (wejscie.stem + "." + rozszerzenie)
            if wynik.exists():
                shutil.copyfile(wynik, wyjscie)
                return
        raise RuntimeError(f"LibreOffice nie przekonwertował {wejscie.name} do {rozszerzenie}")


def konwertuj_do_doc(docx: Path, wyjscie: Path) -> None:
    """DOCX -> DOC w `wyjscie`."""
    konwertuj(docx, wyjscie, "doc:MS Word 97")


_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_CZESCI_MIEJSC: dict[str, tuple[str, ...]] = {
    "tresc": ("word/document.xml",), "tabela": ("word/document.xml",), "pole": ("word/document.xml",),
    "zmiany": ("word/document.xml",), "naglowek": ("word/header",), "stopka": ("word/footer",),
    "przypis": ("word/footnotes.xml",), "komentarz": ("word/comments.xml",),
    "metadane": ("docProps/core.xml", "docProps/custom.xml", "docProps/app.xml"),
}


def teksty_miejsc_docx(docx: Path) -> dict[str, str]:
    """Tekst części DOCX wg miejsca wartości (akapity z `w:t`/`w:delText`, atrybuty – autorzy, i tekst innych elementów)."""
    wynik: dict[str, str] = {}
    with zipfile.ZipFile(docx) as zf:
        for miejsce, prefiksy in _CZESCI_MIEJSC.items():
            kawalki = []
            for nazwa in zf.namelist():
                if nazwa.endswith(".xml") and any(nazwa.startswith(p) for p in prefiksy):
                    root = etree.fromstring(zf.read(nazwa))
                    kawalki += ["".join(t.text or "" for t in p.iter(f"{{{_W}}}t", f"{{{_W}}}delText"))
                                for p in root.iter(f"{{{_W}}}p")]
                    kawalki += [v for e in root.iter() for v in e.attrib.values()] + list(root.itertext())
            wynik[miejsce] = "\n".join(kawalki)
    return wynik


def _jest_w_tekscie(tekst: str, korpus: str) -> bool:
    """Wartość jako całe słowa/fraza (granice słów), nie jako fragment dłuższego wyrazu."""
    return re.search(rf"(?<!\w){re.escape(tekst)}(?!\w)", korpus) is not None


def _strumienie(plik: Path) -> bytes:
    ole = olefile.OleFileIO(str(plik))
    try:
        return b"\0".join(ole.openstream(s).read() for s in ole.listdir())
    finally:
        ole.close()


def odfiltruj_zachowane(wartosci: list[Wartosc], obrazy: list[Obraz], teksty: dict[str, str],
                        blob: bytes) -> tuple[list[Wartosc], list[Obraz], list[str]]:
    """Zostawia wartości obecne (z granicami słów) w tekście DOC dla swojego miejsca i obrazy, których PNG jest w `blob`.

    `teksty` to tekst DOC wg miejsca (`teksty_miejsc_docx` z odczytu zwrotnego LibreOffice), `blob` – strumienie OLE
    (tylko do obrazów). Wartości obrazu (`…@obraz`) idą za swoim obrazem; reszta -> ostrzeżenia (tylko id i miejsce).
    """
    ostrzezenia: list[str] = []
    zgubione_obrazy = [o for o in obrazy if not o.png or o.png not in blob]
    wartosci_obrazow = {w.id for o in zgubione_obrazy for w in o.wartosci}
    for o in zgubione_obrazy:
        ostrzezenia.append(f"obraz {o.id}: konwersja DOC go nie zachowała")
    ok: list[Wartosc] = []
    for w in wartosci:
        if w.miejsce == "obraz":
            if w.id not in wartosci_obrazow:
                ok.append(w)
        elif _jest_w_tekscie(w.tekst, teksty.get(w.miejsce, "")):
            ok.append(w)
        else:
            ostrzezenia.append(f"{w.id} ({w.miejsce}): konwersja DOC nie zachowała wartości")
    return ok, [o for o in obrazy if o not in zgubione_obrazy], ostrzezenia


def renderuj_doc(d: Dokument, plik: Path, utrudnienia: set[str]) -> WynikDoc:
    """Zapisuje `d` jako DOC w `plik`; zwraca wartości i obrazy faktycznie obecne w pliku oraz ostrzeżenia."""
    nieznane = set(utrudnienia) - UTRUDNIENIA_DOC - UTRUDNIENIA_POMINIETE
    if nieznane:
        raise ValueError(f"nieznane utrudnienia DOC: {sorted(nieznane)}")
    plik = Path(plik)
    plik.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pbench-doc-") as tmp:
        docx = Path(tmp) / "dokument.docx"
        wynik = renderuj_docx(d, docx, set(utrudnienia))
        konwertuj_do_doc(docx, plik)
        zwrot = Path(tmp) / "zwrot" / "dokument.docx"  # odczyt DOC niezależny od zapisu: DOC -> DOCX
        zwrot.parent.mkdir()
        konwertuj(plik, zwrot, "docx")
        teksty = teksty_miejsc_docx(zwrot)
    wartosci, obrazy, ostrzezenia = odfiltruj_zachowane(wynik.wartosci, wynik.obrazy, teksty, _strumienie(plik))
    return WynikDoc(wartosci, obrazy, ostrzezenia)


def render_doc(d: Dokument, plik: Path, utrudnienia: set[str]) -> list[Wartosc]:
    """Jak `renderuj_doc`, ale zwraca tylko listę umieszczonych wartości (z `miejsce`, w tym `obraz`)."""
    return renderuj_doc(d, plik, utrudnienia).wartosci
