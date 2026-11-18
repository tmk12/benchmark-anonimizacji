"""Edycja pakietu OOXML (ZIP) dla warstwy trudnych przypadków H3: części, typy zawartości, relacje, zapis ze stałymi
znacznikami czasu. Używa go wstrzykiwanie treści ukrytej (`ukryta_docx/xlsx/pptx`); dodaje części do pliku
wyrenderowanego przez zwykły renderer, więc plik pozostaje w całości zgodny z OOXML (ZIP + `[Content_Types].xml` +
relacje spójne)."""
from __future__ import annotations

import io
import posixpath
import zipfile
from xml.sax.saxutils import escape

from lxml import etree

from .model import Element
from .render.wspolne import STALA_DATA_ZIP, tekst_fragmentow

NS_CT = "http://schemas.openxmlformats.org/package/2006/content-types"
NS_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
    "c": "http://schemas.openxmlformats.org/drawingml/2006/chart",
    "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
    "mc": "http://schemas.openxmlformats.org/markup-compatibility/2006",
    "v": "urn:schemas-microsoft-com:vml",
    "o": "urn:schemas-microsoft-com:office:office",
    "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "x": "urn:schemas-microsoft-com:office:excel",
}
RT = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
#: Znacznik rozdzielający teksty fragmentów jednego elementu ukrytego (np. opis i tytuł alt textu).
ROZDZIELACZ = "\x1f"


def czesci(e: Element) -> list[str]:
    """Teksty fragmentów elementu rozdzielone znacznikiem `ROZDZIELACZ`."""
    return tekst_fragmentow(e.fragmenty).split(ROZDZIELACZ)


def xml_do_bajtow(root: etree._Element) -> bytes:
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def ns_deklaracje(*prefiksy: str) -> str:
    return " ".join(f'xmlns:{p}="{NS[p]}"' for p in prefiksy)


def tekst(s: str) -> str:
    """Tekst bezpieczny w treści i atrybucie XML (cudzysłów też)."""
    return escape(s, {'"': "&quot;"})


class Pakiet:
    """Pakiet OOXML w pamięci: `czesci` (nazwa -> bajty, w kolejności ZIP), operacje na typach i relacjach."""

    def __init__(self, bajty: bytes) -> None:
        with zipfile.ZipFile(io.BytesIO(bajty)) as z:
            self.czesci: dict[str, bytes] = {i.filename: z.read(i) for i in z.infolist() if not i.filename.endswith("/")}

    # ----- XML
    def xml(self, nazwa: str) -> etree._Element:
        return etree.fromstring(self.czesci[nazwa], etree.XMLParser(resolve_entities=False, huge_tree=True))

    def zapisz_xml(self, nazwa: str, root: etree._Element) -> None:
        self.czesci[nazwa] = xml_do_bajtow(root)

    def fragment(self, xml: str, *prefiksy: str) -> list[etree._Element]:
        """Elementy z napisu XML (przestrzenie nazw `prefiksy` zadeklarowane w osłonie)."""
        oslona = etree.fromstring(f"<oslona {ns_deklaracje(*prefiksy)}>{xml}</oslona>")
        wynik = list(oslona)
        for e in wynik:
            oslona.remove(e)
        return wynik

    # ----- nazwy
    def wolna_nazwa(self, wzor: str) -> str:
        """Pierwsza niezajęta nazwa części z `wzor` zawierającego `{}` (numer od 1)."""
        n = 1
        while wzor.format(n) in self.czesci:
            n += 1
        return wzor.format(n)

    # ----- [Content_Types].xml
    def typ_domyslny(self, rozszerzenie: str, typ: str) -> None:
        root = self.xml("[Content_Types].xml")
        if not any(e.get("Extension", "").lower() == rozszerzenie.lower() for e in root.findall(f"{{{NS_CT}}}Default")):
            d = etree.Element(f"{{{NS_CT}}}Default", Extension=rozszerzenie, ContentType=typ)
            root.insert(0, d)
            self.zapisz_xml("[Content_Types].xml", root)

    def typ(self, nazwa: str, typ: str) -> None:
        root = self.xml("[Content_Types].xml")
        pn = "/" + nazwa
        for e in root.findall(f"{{{NS_CT}}}Override"):
            if e.get("PartName") == pn:
                e.set("ContentType", typ)
                self.zapisz_xml("[Content_Types].xml", root)
                return
        etree.SubElement(root, f"{{{NS_CT}}}Override", PartName=pn, ContentType=typ)
        self.zapisz_xml("[Content_Types].xml", root)

    # ----- relacje
    @staticmethod
    def czesc_relacji(zrodlo: str) -> str:
        katalog, plik = posixpath.split(zrodlo)
        return posixpath.join(katalog, "_rels", plik + ".rels")

    def relacje(self, zrodlo: str) -> etree._Element:
        nazwa = self.czesc_relacji(zrodlo)
        if nazwa in self.czesci:
            return self.xml(nazwa)
        return etree.Element(f"{{{NS_REL}}}Relationships", nsmap={None: NS_REL})

    def dodaj_relacje(self, zrodlo: str, rodzaj: str, cel: str, tryb: str | None = None) -> str:
        """Dodaje relację części `zrodlo` do części `cel` (ścieżka w pakiecie, bezwzględna wobec korzenia) i zwraca jej `Id`."""
        root = self.relacje(zrodlo)
        zajete = {e.get("Id") for e in root}
        n = 1
        while f"rId{n}" in zajete:
            n += 1
        rid = f"rId{n}"
        wzgl = posixpath.relpath(cel, posixpath.dirname(zrodlo) or ".")
        e = etree.SubElement(root, f"{{{NS_REL}}}Relationship", Id=rid, Type=rodzaj if rodzaj.startswith("http") else RT + rodzaj,
                             Target=wzgl)
        if tryb:
            e.set("TargetMode", tryb)
        self.zapisz_xml(self.czesc_relacji(zrodlo), root)
        return rid

    # ----- zapis
    def bajty(self) -> bytes:
        wyjscie = io.BytesIO()
        with zipfile.ZipFile(wyjscie, "w", zipfile.ZIP_DEFLATED) as zout:
            for nazwa, dane in self.czesci.items():
                zi = zipfile.ZipInfo(nazwa, STALA_DATA_ZIP)
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = 0o600 << 16
                zout.writestr(zi, dane)
        return wyjscie.getvalue()


def png_bajty(rozmiar: int = 48, ziarno: int = 0) -> bytes:
    """Mały deterministyczny obraz PNG bez tekstu (szary gradient) – nośnik alt textu i miniatura obiektu."""
    from PIL import Image
    obraz = Image.new("RGB", (rozmiar, rozmiar))
    px = obraz.load()
    for y in range(rozmiar):
        for x in range(rozmiar):
            g = 170 + (x + y + ziarno) % 60
            px[x, y] = (g, g, 200)
    bufor = io.BytesIO()
    obraz.save(bufor, "PNG")
    return bufor.getvalue()
