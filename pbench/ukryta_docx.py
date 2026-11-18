"""Wstrzykiwanie treści ukrytej do DOCX (warstwa trudnych przypadków H3, spec §11 pkt 1).

Dopisuje do pliku wyrenderowanego przez `render.docx` elementy z `Dokument.ukryte` (rodzaje `docx.*`), przy czym treść
leży tam, gdzie zwykły użytkownik jej nie ogląda: tekst `w:vanish`, kody pól, pole tekstowe (`w:txbxContent` w `wps`
z wersją VML), alt text obrazu, nazwa zakładki, część `customXml/`, wykres (`word/charts`), obiekt osadzony (XLSX),
nagłówek pierwszej strony i przypis końcowy (`word/endnotes.xml`). Mapowanie element -> miejsce gold:
`metodyka/miejsca-ukryte.md`. Teksty wartości pobierane są z fragmentów elementu (po ewentualnym zamaskowaniu).
"""
from __future__ import annotations

import io
from collections.abc import Callable
from pathlib import Path

from lxml import etree
from openpyxl import Workbook

from .model import Element
from .render.wspolne import przepakuj, tekst_fragmentow, ustaw_modified
from .ukryta_pakiet import NS, ROZDZIELACZ, Pakiet, czesci, png_bajty, tekst

W = f"{{{NS['w']}}}"
CT = "application/vnd.openxmlformats-officedocument."
KOLEJNOSC_SECT_PO_TITLEPG = ("textDirection", "bidi", "rtlGutter", "docGrid", "printerSettings", "sectPrChange")


class Ctx:
    def __init__(self, pak: Pakiet) -> None:
        self.pak = pak
        self.doc = pak.xml("word/document.xml")
        self.body = self.doc.find(f"{W}body")
        self.sect = self.body.find(f"{W}sectPr")
        self.nr = 7000            # identyfikatory zakładek i `wp:docPr` (powyżej tych z renderera)
        self.przypisy: etree._Element | None = None

    def id(self) -> int:
        self.nr += 1
        return self.nr

    def dodaj(self, xml: str, *prefiksy: str) -> None:
        for el in self.pak.fragment(xml, "w", *prefiksy):
            if self.sect is not None:
                self.sect.addprevious(el)
            else:
                self.body.append(el)

    def obraz(self) -> str:
        """Dodaje obraz PNG (bez tekstu) i zwraca `rId` w `document.xml.rels`."""
        nazwa = self.pak.wolna_nazwa("word/media/hidden{}.png")
        self.pak.czesci[nazwa] = png_bajty(48, self.nr)
        self.pak.typ_domyslny("png", "image/png")
        return self.pak.dodaj_relacje("word/document.xml", "image", nazwa)


def _etykieta(e: Element) -> str:
    return e.atrybuty.get("etykieta", "")


def _akapit_ukryty(ctx: Ctx, e: Element) -> None:
    ctx.dodaj(f'<w:p><w:r><w:rPr><w:vanish/></w:rPr><w:t xml:space="preserve">{tekst(tekst_fragmentow(e.fragmenty))}</w:t></w:r></w:p>')


def _pole(ctx: Ctx, e: Element) -> None:
    """Pole złożone: instrukcja z PII (AUTHOR / MERGEFIELD / DOCPROPERTY) i wynik z tą samą wartością."""
    wartosc = tekst(tekst_fragmentow(e.fragmenty))
    instr = {"AUTHOR": f' AUTHOR "{wartosc}" ', "MERGEFIELD": f' MERGEFIELD "{wartosc}" \\* MERGEFORMAT ',
             "DOCPROPERTY": f' DOCPROPERTY "{wartosc}" \\* MERGEFORMAT '}[e.rodzaj.split("_", 1)[1].upper()]
    ctx.dodaj(
        f'<w:p><w:r><w:t xml:space="preserve">{tekst(_etykieta(e))}: </w:t></w:r>'
        '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        f'<w:r><w:instrText xml:space="preserve">{instr}</w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        f'<w:r><w:t xml:space="preserve">{wartosc}</w:t></w:r>'
        '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')


def _pole_tekstowe(ctx: Ctx, e: Element) -> None:
    akapity = "".join(f'<w:p><w:r><w:t xml:space="preserve">{tekst(a)}</w:t></w:r></w:p>' for a in czesci(e))
    n = ctx.id()
    ctx.dodaj(
        f'<w:p><w:r><mc:AlternateContent xmlns:wps="{NS['wps']}"><mc:Choice Requires="wps"><w:drawing>'
        '<wp:anchor distT="0" distB="0" distL="0" distR="0" simplePos="0" relativeHeight="251659264" behindDoc="0" '
        'locked="0" layoutInCell="1" allowOverlap="1"><wp:simplePos x="0" y="0"/>'
        '<wp:positionH relativeFrom="column"><wp:posOffset>0</wp:posOffset></wp:positionH>'
        '<wp:positionV relativeFrom="paragraph"><wp:posOffset>0</wp:posOffset></wp:positionV>'
        '<wp:extent cx="3600000" cy="720000"/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapSquare wrapText="bothSides"/>'
        f'<wp:docPr id="{n}" name="Pole tekstowe {n}"/><wp:cNvGraphicFramePr/>'
        '<a:graphic><a:graphicData uri="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"><wps:wsp>'
        '<wps:cNvSpPr txBox="1"/><wps:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="3600000" cy="720000"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></wps:spPr>'
        f'<wps:txbx><w:txbxContent>{akapity}</w:txbxContent></wps:txbx><wps:bodyPr/></wps:wsp></a:graphicData></a:graphic>'
        '</wp:anchor></w:drawing></mc:Choice><mc:Fallback><w:pict>'
        f'<v:shape id="pole{n}" style="position:absolute;width:283pt;height:57pt" stroked="t"><v:textbox>'
        f'<w:txbxContent>{akapity}</w:txbxContent></v:textbox></v:shape></w:pict></mc:Fallback></mc:AlternateContent>'
        '</w:r></w:p>', "mc", "wps", "wp", "a", "v")


def _alt_text(ctx: Ctx, e: Element) -> None:
    opis, *tytul = czesci(e)
    rid = ctx.obraz()
    n = ctx.id()
    ctx.dodaj(
        '<w:p><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="540000" cy="540000"/>'
        f'<wp:docPr id="{n}" name="Obraz {n}" descr="{tekst(opis)}" title="{tekst(tytul[0] if tytul else "")}"/>'
        '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>'
        f'<pic:nvPicPr><pic:cNvPr id="{n}" name="hidden{n}.png"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="540000" cy="540000"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
        '</wp:inline></w:drawing></w:r></w:p>', "wp", "a", "pic", "r")


def _zakladka(ctx: Ctx, e: Element) -> None:
    n = ctx.id()
    ctx.dodaj(f'<w:p><w:bookmarkStart w:id="{n}" w:name="{tekst(tekst_fragmentow(e.fragmenty))}"/>'
              f'<w:r><w:t xml:space="preserve">{tekst(_etykieta(e))}</w:t></w:r><w:bookmarkEnd w:id="{n}"/></w:p>')


def _custom_xml(ctx: Ctx, e: Element) -> None:
    """Część `customXml/itemN.xml` (dane klienta) + `itemPropsN.xml` i relacje (jak w plikach z systemów DMS)."""
    pak = ctx.pak
    pola = czesci(e)
    nazwa = pak.wolna_nazwa("customXml/item{}.xml")
    n = int(nazwa.removeprefix("customXml/item").removesuffix(".xml"))
    ns = f"urn:pbench:klient:{n}"
    etykiety = e.atrybuty["pola"]
    tresc = "".join(f"<{k}>{tekst(v)}</{k}>" for k, v in zip(etykiety, pola))
    pak.czesci[nazwa] = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<klient xmlns="{ns}">{tresc}</klient>'.encode()
    props = f"customXml/itemProps{n}.xml"
    pak.czesci[props] = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<ds:datastoreItem ds:itemID="{{7A1C0F2E-5B3D-4C8A-9E11-{n:012d}}}" '
                         f'xmlns:ds="http://schemas.openxmlformats.org/officeDocument/2006/customXml"><ds:schemaRefs><ds:schemaRef ds:uri="{ns}"/>'
                         '</ds:schemaRefs></ds:datastoreItem>').encode()
    pak.typ(props, CT + "customXmlProperties+xml")
    pak.dodaj_relacje(nazwa, "customXmlProps", props)
    pak.dodaj_relacje("word/document.xml", "customXml", nazwa)


def _wykres(ctx: Ctx, e: Element) -> None:
    pak = ctx.pak
    seria, *kategorie = czesci(e)
    nazwa = pak.wolna_nazwa("word/charts/chart{}.xml")
    pt = lambda i, v: f'<c:pt idx="{i}"><c:v>{tekst(v)}</c:v></c:pt>'   # noqa: E731
    k = len(kategorie)
    pak.czesci[nazwa] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        f'<c:chartSpace xmlns:c="{NS["c"]}" xmlns:a="{NS["a"]}" xmlns:r="{NS["r"]}"><c:chart><c:autoTitleDeleted val="1"/>'
        '<c:plotArea><c:layout/><c:barChart><c:barDir val="col"/><c:grouping val="clustered"/><c:varyColors val="0"/>'
        '<c:ser><c:idx val="0"/><c:order val="0"/>'
        f'<c:tx><c:strRef><c:f>Arkusz1!$B$1</c:f><c:strCache><c:ptCount val="1"/>{pt(0, seria)}</c:strCache></c:strRef></c:tx>'
        f'<c:cat><c:strRef><c:f>Arkusz1!$A$2:$A${k + 1}</c:f><c:strCache><c:ptCount val="{k}"/>'
        f'{"".join(pt(i, v) for i, v in enumerate(kategorie))}</c:strCache></c:strRef></c:cat>'
        f'<c:val><c:numRef><c:f>Arkusz1!$B$2:$B${k + 1}</c:f><c:numCache><c:formatCode>General</c:formatCode>'
        f'<c:ptCount val="{k}"/>{"".join(pt(i, str(10 + 7 * i)) for i in range(k))}</c:numCache></c:numRef></c:val></c:ser>'
        '<c:axId val="50010"/><c:axId val="50020"/></c:barChart>'
        '<c:catAx><c:axId val="50010"/><c:scaling><c:orientation val="minMax"/></c:scaling><c:delete val="0"/>'
        '<c:axPos val="b"/><c:crossAx val="50020"/></c:catAx>'
        '<c:valAx><c:axId val="50020"/><c:scaling><c:orientation val="minMax"/></c:scaling><c:delete val="0"/>'
        '<c:axPos val="l"/><c:crossAx val="50010"/></c:valAx></c:plotArea><c:plotVisOnly val="1"/></c:chart></c:chartSpace>').encode()
    pak.typ(nazwa, CT + "drawingml.chart+xml")
    rid = pak.dodaj_relacje("word/document.xml", "chart", nazwa)
    n = ctx.id()
    ctx.dodaj(
        '<w:p><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="4320000" cy="2160000"/>'
        f'<wp:docPr id="{n}" name="Wykres {n}"/><wp:cNvGraphicFramePr/>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/chart">'
        f'<c:chart xmlns:c="{NS["c"]}" r:id="{rid}"/></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>',
        "wp", "a", "r")


def skoroszyt_osadzony(wiersze: list[tuple[str, str]]) -> bytes:
    """Mały XLSX (deterministyczny) z wierszami (etykieta, wartość) – obiekt osadzony w DOCX."""
    import datetime as dt
    wb = Workbook()
    ws = wb.active
    ws.title = "Arkusz1"
    for w in wiersze:
        ws.append(list(w))
    wb.properties.creator = "pbench"
    wb.properties.created = wb.properties.modified = dt.datetime(2024, 1, 1)
    bufor = io.BytesIO()
    wb.save(bufor)
    # openpyxl wpisuje do `dcterms:modified` czas zapisu – bez podmiany bajty DOCX zależą od chwili budowy (H6b)
    return przepakuj(bufor.getvalue(), {"docProps/core.xml": lambda x: ustaw_modified(x, dt.datetime(2024, 1, 1))})


#: Standardowy `v:shapetype` obrazu (jak w DOCX z Worda z osadzonym obiektem); `v:shape type="#_x0000_t75"` odwołuje się do niego.
SHAPETYPE_T75 = (
    '<v:shapetype id="_x0000_t75" coordsize="21600,21600" o:spt="75" o:preferrelative="t" '
    'path="m@4@5l@4@11@9@11@9@5xe" filled="f" stroked="f"><v:stroke joinstyle="miter"/><v:formulas>'
    '<v:f eqn="if lineDrawn pixelLineWidth 0"/><v:f eqn="sum @0 1 0"/><v:f eqn="sum 0 0 @1"/><v:f eqn="prod @2 1 2"/>'
    '<v:f eqn="prod @3 21600 pixelWidth"/><v:f eqn="prod @3 21600 pixelHeight"/><v:f eqn="sum @0 0 1"/>'
    '<v:f eqn="prod @6 1 2"/><v:f eqn="prod @7 21600 pixelWidth"/><v:f eqn="sum @8 21600 0"/>'
    '<v:f eqn="prod @7 21600 pixelHeight"/><v:f eqn="sum @10 21600 0"/></v:formulas>'
    '<v:path o:extrusionok="f" gradientshapeok="t" o:connecttype="rect"/><o:lock v:ext="edit" aspectratio="t"/></v:shapetype>')


def _obiekt(ctx: Ctx, e: Element) -> None:
    pak = ctx.pak
    wartosci = czesci(e)
    etykiety = e.atrybuty["pola"]
    nazwa = pak.wolna_nazwa("word/embeddings/Microsoft_Excel_Sheet{}.xlsx")
    pak.czesci[nazwa] = skoroszyt_osadzony(list(zip(etykiety, wartosci)))
    pak.typ_domyslny("xlsx", CT + "spreadsheetml.sheet")
    rid_obiektu = pak.dodaj_relacje("word/document.xml", "package", nazwa)
    rid_ikony = ctx.obraz()
    n = ctx.id()
    ctx.dodaj(
        f'<w:p><w:r><w:object w:dxaOrig="1440" w:dyaOrig="720">{SHAPETYPE_T75}<v:shape id="_x0000_i{n}" type="#_x0000_t75" '
        f'style="width:72pt;height:36pt" o:ole=""><v:imagedata r:id="{rid_ikony}" o:title=""/></v:shape>'
        f'<o:OLEObject Type="Embed" ProgID="Excel.Sheet.12" ShapeID="_x0000_i{n}" DrawAspect="Icon" ObjectID="_{n}" r:id="{rid_obiektu}"/>'
        '</w:object></w:r></w:p>', "v", "o", "r")


def _naglowek_pierwszej_strony(ctx: Ctx, e: Element) -> None:
    pak = ctx.pak
    if any(r.get(f"{W}type") == "first" for r in ctx.sect.findall(f"{W}headerReference")):
        raise ValueError("docx.naglowek_pierwszej_strony: sectPr ma już headerReference type=\"first\" (dwa byłyby błędem Worda)")
    nazwa = pak.wolna_nazwa("word/header{}.xml")
    pak.czesci[nazwa] = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:hdr xmlns:w="{NS["w"]}" xmlns:r="{NS["r"]}">'
                         f'<w:p><w:r><w:t xml:space="preserve">{tekst(tekst_fragmentow(e.fragmenty))}</w:t></w:r></w:p></w:hdr>').encode()
    pak.typ(nazwa, CT + "wordprocessingml.header+xml")
    rid = pak.dodaj_relacje("word/document.xml", "header", nazwa)
    sect = ctx.sect
    ref = etree.Element(f"{W}headerReference")
    ref.set(f"{W}type", "first")
    ref.set(f"{{{NS['r']}}}id", rid)
    sect.insert(0, ref)
    if sect.find(f"{W}titlePg") is None:
        tp = etree.Element(f"{W}titlePg")
        for nastepny in KOLEJNOSC_SECT_PO_TITLEPG:
            n = sect.find(f"{W}{nastepny}")
            if n is not None:
                n.addprevious(tp)
                break
        else:
            sect.append(tp)


def _przypis_koncowy(ctx: Ctx, e: Element) -> None:
    pak = ctx.pak
    if ctx.przypisy is None:
        nazwa = "word/endnotes.xml"
        if nazwa in pak.czesci:
            raise ValueError("docx.przypis_koncowy: renderer dodał już word/endnotes.xml – nie nadpisujemy istniejącej części")
        sep = '<w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:r><w:{}/></w:r></w:p>'
        ctx.przypisy = etree.fromstring(
            f'<w:endnotes xmlns:w="{NS["w"]}"><w:endnote w:type="separator" w:id="-1">{sep.format("separator")}</w:endnote>'
            f'<w:endnote w:type="continuationSeparator" w:id="0">{sep.format("continuationSeparator")}</w:endnote></w:endnotes>')
        pak.typ(nazwa, CT + "wordprocessingml.endnotes+xml")
        pak.dodaj_relacje("word/document.xml", "endnotes", nazwa)
        if "word/settings.xml" in pak.czesci:
            ust = pak.xml("word/settings.xml")
            if ust.find(f"{W}endnotePr") is None:
                pr = pak.fragment('<w:endnotePr><w:endnote w:id="-1"/><w:endnote w:id="0"/></w:endnotePr>', "w")[0]
                zgodnosc = ust.find(f"{W}compat")
                (zgodnosc.addprevious(pr) if zgodnosc is not None else ust.append(pr))
                pak.zapisz_xml("word/settings.xml", ust)
    numer = len(ctx.przypisy.findall(f"{W}endnote")) - 1
    ctx.przypisy.append(pak.fragment(
        f'<w:endnote w:id="{numer}"><w:p><w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:endnoteRef/></w:r>'
        f'<w:r><w:t xml:space="preserve"> {tekst(tekst_fragmentow(e.fragmenty))}</w:t></w:r></w:p></w:endnote>', "w")[0])
    ctx.dodaj(f'<w:p><w:r><w:t xml:space="preserve">{tekst(_etykieta(e))}</w:t></w:r>'
              f'<w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:endnoteReference w:id="{numer}"/></w:r></w:p>')


OBSLUGA: dict[str, Callable[[Ctx, Element], None]] = {
    "docx.vanish": _akapit_ukryty, "docx.pole_author": _pole, "docx.pole_mergefield": _pole,
    "docx.pole_docproperty": _pole, "docx.pole_tekstowe": _pole_tekstowe, "docx.alt_text": _alt_text,
    "docx.zakladka": _zakladka, "docx.custom_xml": _custom_xml, "docx.wykres": _wykres, "docx.obiekt": _obiekt,
    "docx.naglowek_pierwszej_strony": _naglowek_pierwszej_strony, "docx.przypis_koncowy": _przypis_koncowy,
}


def wstrzyknij_docx(plik: Path, elementy: list[Element]) -> None:
    """Dopisuje `elementy` (rodzaje `docx.*`) do pliku DOCX `plik` (nadpisuje go, deterministycznie)."""
    pak = Pakiet(Path(plik).read_bytes())
    ctx = Ctx(pak)
    for e in elementy:
        OBSLUGA[e.rodzaj](ctx, e)
    pak.zapisz_xml("word/document.xml", ctx.doc)
    if ctx.przypisy is not None:
        pak.zapisz_xml("word/endnotes.xml", ctx.przypisy)
    Path(plik).write_bytes(pak.bajty())
