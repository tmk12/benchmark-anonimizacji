"""Wstrzykiwanie treści ukrytej do XLSX (warstwa trudnych przypadków H3, spec §11 pkt 1).

Dopisuje do pliku wyrenderowanego przez `render.xlsx` elementy z `Dokument.ukryte` (rodzaje `xlsx.*`): ukryty wiersz i
kolumnę, arkusze `hidden` i `veryHidden`, `pivotCache` (definicja + rekordy), nazwę zdefiniowaną ze stałą, listę
walidacji danych z nazwiskami, formułę ze stałymi (z wartością wyliczoną w `<v>`) i komentarz komórki. Wszystkie
komórki zapisuje jako `inlineStr` (jak renderer). Mapowanie element -> miejsce gold: `metodyka/miejsca-ukryte.md`.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from lxml import etree
from openpyxl.utils import column_index_from_string, get_column_letter
from openpyxl.utils.cell import coordinate_from_string

from .model import Element
from .render.wspolne import tekst_fragmentow
from .ukryta_pakiet import NS, Pakiet, czesci, tekst

S = f"{{{NS['s']}}}"
R = f"{{{NS['r']}}}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
CT = "application/vnd.openxmlformats-officedocument.spreadsheetml."
#: Kolejność elementów `worksheet` (CT_Worksheet) – do wstawiania nowych w poprawne miejsce.
KOLEJNOSC = ("sheetPr", "dimension", "sheetViews", "sheetFormatPr", "cols", "sheetData", "sheetCalcPr", "sheetProtection",
             "protectedRanges", "scenarios", "autoFilter", "sortState", "dataConsolidate", "customSheetViews", "mergeCells",
             "phoneticPr", "conditionalFormatting", "dataValidations", "hyperlinks", "printOptions", "pageMargins", "pageSetup",
             "headerFooter", "rowBreaks", "colBreaks", "customProperties", "cellWatches", "ignoredErrors", "smartTags",
             "drawing", "legacyDrawing", "legacyDrawingHF", "drawingHF", "picture", "oleObjects", "controls",
             "webPublishItems", "tableParts", "extLst")


def _lok(el: etree._Element) -> str:
    return etree.QName(el).localname


def wstaw(root: etree._Element, nowy: etree._Element) -> None:
    """Wstawia `nowy` do `worksheet` w kolejności schematu (przed pierwszym elementem, który ma następować po nim)."""
    idx = KOLEJNOSC.index(_lok(nowy))
    for ch in root:
        if isinstance(ch.tag, str) and _lok(ch) in KOLEJNOSC and KOLEJNOSC.index(_lok(ch)) > idx:
            ch.addprevious(nowy)
            return
    root.append(nowy)


def komorka(ref: str, tresc: str) -> etree._Element:
    c = etree.Element(f"{S}c", r=ref, t="inlineStr")
    t = etree.SubElement(etree.SubElement(c, f"{S}is"), f"{S}t")
    t.text = tresc
    t.set(XML_SPACE, "preserve")
    return c


class Arkusz:
    """Część arkusza: korzeń XML i operacje na wierszach/kolumnach."""

    def __init__(self, nazwa: str, root: etree._Element) -> None:
        self.nazwa, self.root = nazwa, root
        self.dane = root.find(f"{S}sheetData")

    @property
    def max_wiersz(self) -> int:
        return max((int(r.get("r")) for r in self.dane.findall(f"{S}row")), default=0)

    @property
    def max_kolumna(self) -> int:
        return max((column_index_from_string(coordinate_from_string(c.get("r"))[0])
                    for c in self.dane.iter(f"{S}c")), default=0)

    def wiersz(self, nr: int, ukryty: bool = False) -> etree._Element:
        for r in self.dane.findall(f"{S}row"):
            if int(r.get("r")) == nr:
                return r
        nowy = etree.SubElement(self.dane, f"{S}row", r=str(nr))
        if ukryty:
            nowy.set("hidden", "1")
        return nowy

    def aktualizuj_wymiar(self) -> None:
        wym = self.root.find(f"{S}dimension")
        if wym is not None:
            wym.set("ref", f"A1:{get_column_letter(max(1, self.max_kolumna))}{max(1, self.max_wiersz)}")


class Ctx:
    def __init__(self, pak: Pakiet) -> None:
        self.pak = pak
        self.wb = pak.xml("xl/workbook.xml")
        rel = pak.xml("xl/_rels/workbook.xml.rels")
        cele = {e.get("Id"): e.get("Target") for e in rel}
        pierwszy = self.wb.find(f"{S}sheets")[0]
        cel = cele[pierwszy.get(f"{R}id")]
        self.pierwsza = "xl/" + cel.lstrip("/").removeprefix("xl/") if not cel.startswith("/") else cel.lstrip("/")
        self.arkusze: dict[str, Arkusz] = {self.pierwsza: Arkusz(pierwszy.get("name"), pak.xml(self.pierwsza))}

    @property
    def pierwszy(self) -> Arkusz:
        return self.arkusze[self.pierwsza]

    def nowy_arkusz(self, nazwa: str, stan: str, wiersze: list[list[str]]) -> str:
        """Dodaje arkusz o stanie `stan` (visible/hidden/veryHidden) z komórkami tekstowymi; zwraca nazwę części."""
        pak = self.pak
        czesc = pak.wolna_nazwa("xl/worksheets/sheet{}.xml")
        root = etree.Element(f"{S}worksheet", nsmap={None: NS["s"]})
        etree.SubElement(root, f"{S}dimension", ref=f"A1:{get_column_letter(max(len(w) for w in wiersze))}{len(wiersze)}")
        dane = etree.SubElement(root, f"{S}sheetData")
        for i, w in enumerate(wiersze, 1):
            r = etree.SubElement(dane, f"{S}row", r=str(i))
            for j, t in enumerate(w, 1):
                r.append(komorka(f"{get_column_letter(j)}{i}", t))
        pak.zapisz_xml(czesc, root)
        pak.typ(czesc, CT + "worksheet+xml")
        rid = pak.dodaj_relacje("xl/workbook.xml", "worksheet", czesc)
        arkusze = self.wb.find(f"{S}sheets")
        nr = max(int(s.get("sheetId")) for s in arkusze) + 1
        s = etree.SubElement(arkusze, f"{S}sheet", name=nazwa, sheetId=str(nr))
        if stan != "visible":
            s.set("state", stan)
        s.set(f"{R}id", rid)
        return czesc


def _wiersz_ukryty(ctx: Ctx, e: Element) -> None:
    a = ctx.pierwszy
    nr = a.max_wiersz + 3
    w = a.wiersz(nr, ukryty=True)
    for j, t in enumerate(czesci(e)):
        w.append(komorka(f"{get_column_letter(j + 1)}{nr}", t))
    a.aktualizuj_wymiar()


def _kolumna_ukryta(ctx: Ctx, e: Element) -> None:
    a = ctx.pierwszy
    k = a.max_kolumna + 2
    lit = get_column_letter(k)
    for nr, t in enumerate(czesci(e), 1):
        a.wiersz(nr).append(komorka(f"{lit}{nr}", t))
    kolumny = a.root.find(f"{S}cols")
    if kolumny is None:
        kolumny = etree.Element(f"{S}cols")
        wstaw(a.root, kolumny)
    etree.SubElement(kolumny, f"{S}col", min=str(k), max=str(k), width="20", hidden="1", customWidth="1")
    a.aktualizuj_wymiar()


def _arkusz(ctx: Ctx, e: Element) -> None:
    etykieta, *wartosci = czesci(e)
    stan = "veryHidden" if e.rodzaj.endswith("veryhidden") else "hidden"
    ctx.nowy_arkusz(e.atrybuty["nazwa"], stan, [[etykieta], wartosci])


def _pivot(ctx: Ctx, e: Element) -> None:
    pak = ctx.pak
    w1, w2, w3, w4 = czesci(e)
    n = int(pak.wolna_nazwa("xl/pivotCache/pivotCacheDefinition{}.xml").removeprefix("xl/pivotCache/pivotCacheDefinition")
            .removesuffix(".xml"))
    definicja, rekordy = f"xl/pivotCache/pivotCacheDefinition{n}.xml", f"xl/pivotCache/pivotCacheRecords{n}.xml"
    # zakres źródłowy z nagłówkami = nazwy pól cache (ukryty arkusz bez wartości gold – dane siedzą tylko w cache)
    nazwa_zrodla = "Zrodlo_pivot"
    ctx.nowy_arkusz(nazwa_zrodla, "veryHidden", [["Klient", "Rachunek"], ["-", "-"], ["-", "-"]])
    pak.czesci[rekordy] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<pivotCacheRecords xmlns="{NS["s"]}" xmlns:r="{NS["r"]}" count="2">'
        f'<r><x v="0"/><s v="{tekst(w3)}"/></r><r><x v="1"/><s v="{tekst(w4)}"/></r></pivotCacheRecords>').encode()
    rid_rekordow = pak.dodaj_relacje(definicja, "pivotCacheRecords", rekordy)
    pak.czesci[definicja] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<pivotCacheDefinition xmlns="{NS["s"]}" xmlns:r="{NS["r"]}" r:id="{rid_rekordow}" refreshedBy="pbench" '
        'refreshedDate="45292" createdVersion="6" refreshedVersion="6" minRefreshableVersion="3" recordCount="2">'
        f'<cacheSource type="worksheet"><worksheetSource ref="A1:B3" sheet="{tekst(nazwa_zrodla)}"/></cacheSource>'
        '<cacheFields count="2">'
        f'<cacheField name="Klient" numFmtId="0"><sharedItems count="2"><s v="{tekst(w1)}"/><s v="{tekst(w2)}"/></sharedItems></cacheField>'
        '<cacheField name="Rachunek" numFmtId="0"><sharedItems/></cacheField></cacheFields></pivotCacheDefinition>').encode()
    pak.typ(definicja, CT + "pivotCacheDefinition+xml")
    pak.typ(rekordy, CT + "pivotCacheRecords+xml")
    rid = pak.dodaj_relacje("xl/workbook.xml", "pivotCacheDefinition", definicja)
    kontener = ctx.wb.find(f"{S}pivotCaches")
    if kontener is None:
        kontener = etree.Element(f"{S}pivotCaches")
        po = ctx.wb.find(f"{S}calcPr")
        if po is None:
            po = ctx.wb.find(f"{S}definedNames")
        if po is None:
            po = ctx.wb.find(f"{S}sheets")
        po.addnext(kontener)
    etree.SubElement(kontener, f"{S}pivotCache", cacheId=str(len(kontener) + 1)).set(f"{R}id", rid)


def _nazwa(ctx: Ctx, e: Element) -> None:
    nazwy = ctx.wb.find(f"{S}definedNames")
    if nazwy is None:
        nazwy = etree.Element(f"{S}definedNames")
        ctx.wb.find(f"{S}sheets").addnext(nazwy)
    d = etree.SubElement(nazwy, f"{S}definedName", name=e.atrybuty["nazwa"])
    d.text = '"' + tekst_fragmentow(e.fragmenty).replace('"', '""') + '"'


def _walidacja(ctx: Ctx, e: Element) -> None:
    a = ctx.pierwszy
    kontener = a.root.find(f"{S}dataValidations")
    if kontener is None:
        kontener = etree.Element(f"{S}dataValidations", count="0")
        wstaw(a.root, kontener)
    ref = f"A{a.max_wiersz + 5}"
    dv = etree.SubElement(kontener, f"{S}dataValidation", type="list", allowBlank="1", showInputMessage="1",
                          showErrorMessage="1", sqref=ref)
    etree.SubElement(dv, f"{S}formula1").text = '"' + ",".join(czesci(e)) + '"'
    kontener.set("count", str(len(kontener)))


def _formula(ctx: Ctx, e: Element) -> None:
    a = ctx.pierwszy
    wartosc = tekst_fragmentow(e.fragmenty)
    nr = a.max_wiersz + 7
    q = lambda s: '"' + s.replace('"', '""') + '"'   # noqa: E731
    if " " in wartosc:
        l, p = wartosc.split(" ", 1)
        formula = f'{q(l + " ")}&{q(p)}'
    else:
        formula = q(wartosc)
    c = etree.Element(f"{S}c", r=f"A{nr}", t="str")
    etree.SubElement(c, f"{S}f").text = formula
    etree.SubElement(c, f"{S}v").text = wartosc
    a.wiersz(nr).append(c)
    a.aktualizuj_wymiar()


VML = ('<xml xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office" '
       'xmlns:x="urn:schemas-microsoft-com:office:excel"><o:shapelayout v:ext="edit"><o:idmap v:ext="edit" data="1"/></o:shapelayout>'
       '<v:shapetype id="_x0000_t202" coordsize="21600,21600" o:spt="202" path="m,l,21600r21600,l21600,xe">'
       '<v:stroke joinstyle="miter"/><v:path gradientshapeok="t" o:connecttype="rect"/></v:shapetype>'
       '<v:shape id="_x0000_s1025" type="#_x0000_t202" style="position:absolute;margin-left:59.25pt;margin-top:1.5pt;'
       'width:108pt;height:59.25pt;z-index:1;visibility:hidden" fillcolor="#ffffe1" o:insetmode="auto">'
       '<v:fill color2="#ffffe1"/><v:shadow on="t" color="black" obscured="t"/><v:path o:connecttype="none"/>'
       '<v:textbox style="mso-direction-alt:auto"><div style="text-align:left"></div></v:textbox>'
       '<x:ClientData ObjectType="Note"><x:MoveWithCells/><x:SizeWithCells/><x:Anchor>1, 15, 0, 2, 3, 15, 3, 16</x:Anchor>'
       '<x:AutoFill>False</x:AutoFill><x:Row>0</x:Row><x:Column>0</x:Column></x:ClientData></v:shape></xml>')


def _komentarz(ctx: Ctx, e: Element) -> None:
    """Nowy widoczny arkusz „Notatki” z jedną komórką i komentarzem (starszy format: `commentsN.xml` + `vmlDrawing`)."""
    pak = ctx.pak
    czesc = ctx.nowy_arkusz(e.atrybuty["nazwa"], "visible", [[e.atrybuty["tytul"]]])
    komentarze = pak.wolna_nazwa("xl/comments{}.xml")
    pak.czesci[komentarze] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<comments xmlns="{NS["s"]}"><authors><author>{tekst(e.atrybuty["autor"])}</author></authors><commentList>'
        f'<comment ref="A1" authorId="0"><text><r><t xml:space="preserve">{tekst(tekst_fragmentow(e.fragmenty))}</t></r></text>'
        '</comment></commentList></comments>').encode()
    pak.typ(komentarze, CT + "comments+xml")
    rysunek = pak.wolna_nazwa("xl/drawings/vmlDrawing{}.vml")
    pak.czesci[rysunek] = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + VML).encode()
    pak.typ_domyslny("vml", "application/vnd.openxmlformats-officedocument.vmlDrawing")
    pak.dodaj_relacje(czesc, "comments", komentarze)
    rid = pak.dodaj_relacje(czesc, "vmlDrawing", rysunek)
    root = pak.xml(czesc)
    etree.SubElement(root, f"{S}legacyDrawing").set(f"{R}id", rid)
    pak.zapisz_xml(czesc, root)


OBSLUGA: dict[str, Callable[[Ctx, Element], None]] = {
    "xlsx.wiersz_ukryty": _wiersz_ukryty, "xlsx.kolumna_ukryta": _kolumna_ukryta, "xlsx.arkusz_hidden": _arkusz, "xlsx.arkusz_veryhidden": _arkusz,
    "xlsx.pivot": _pivot, "xlsx.nazwa": _nazwa, "xlsx.walidacja": _walidacja, "xlsx.formula": _formula,
    "xlsx.komentarz": _komentarz,
}


def wstrzyknij_xlsx(plik: Path, elementy: list[Element]) -> None:
    """Dopisuje `elementy` (rodzaje `xlsx.*`) do pliku XLSX `plik` (nadpisuje go, deterministycznie)."""
    pak = Pakiet(Path(plik).read_bytes())
    ctx = Ctx(pak)
    for e in elementy:
        OBSLUGA[e.rodzaj](ctx, e)
    pak.zapisz_xml("xl/workbook.xml", ctx.wb)
    for nazwa, a in ctx.arkusze.items():
        pak.zapisz_xml(nazwa, a.root)
    Path(plik).write_bytes(pak.bajty())
