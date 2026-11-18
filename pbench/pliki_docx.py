"""Operacje na gotowych plikach DOCX warstwy trudnych przypadków H4a (pakiet OOXML przez `ukryta_pakiet.Pakiet`): układ w
dwóch kolumnach (`w:cols`), znak wodny (WordArt VML w nagłówku, jak „Znak wodny” w Wordzie) i obraz osadzony na końcu
dokumentu (pieczątka, zrzut ekranu). Zapis deterministyczny."""
from __future__ import annotations

from pathlib import Path

from lxml import etree

from .ukryta_pakiet import NS, Pakiet, tekst

W = f"{{{NS['w']}}}"
CT = "application/vnd.openxmlformats-officedocument."
#: Elementy `w:sectPr`, przed którymi (wg schematu) stoi `w:cols`.
PO_COLS = ("formProt", "vAlign", "noEndnote", "titlePg", "textDirection", "bidi", "rtlGutter", "docGrid",
           "printerSettings", "sectPrChange")
#: Typ kształtu WordArt „tekst na ścieżce” (znak wodny Worda) – standardowa definicja VML.
_SHAPETYPE = (
    '<v:shapetype id="_x0000_t136" coordsize="21600,21600" o:spt="136" adj="10800" path="m@7,l@8,m@5,21600l@6,21600e">'
    '<v:formulas><v:f eqn="sum #0 0 10800"/><v:f eqn="prod #0 2 1"/><v:f eqn="sum 21600 0 @1"/><v:f eqn="sum 0 0 @2"/>'
    '<v:f eqn="sum 21600 0 @3"/><v:f eqn="if @0 @3 0"/><v:f eqn="if @0 21600 @1"/><v:f eqn="if @0 0 @2"/>'
    '<v:f eqn="if @0 @4 21600"/><v:f eqn="mid @5 @6"/><v:f eqn="mid @8 @5"/><v:f eqn="mid @7 @8"/><v:f eqn="mid @6 @7"/>'
    '<v:f eqn="sum @6 0 @5"/></v:formulas><v:path textpathok="t" o:connecttype="custom" '
    'o:connectlocs="@9,0;@10,10800;@11,21600;@12,10800" o:connectangles="270,180,90,0"/><v:textpath on="t" fitshape="t"/>'
    '<v:handles><v:h position="#0,bottomRight" xrange="6629,14971"/></v:handles><o:lock v:ext="edit" text="t" '
    'shapetype="t"/></v:shapetype>')


def _sekcja(pak: Pakiet) -> tuple[etree._Element, etree._Element]:
    doc = pak.xml("word/document.xml")
    sect = doc.find(f"{W}body").find(f"{W}sectPr")
    if sect is None:
        raise ValueError("DOCX bez w:sectPr w treści – nie ma gdzie ustawić układu")
    return doc, sect


def kolumny(plik: Path, liczba: int = 2, odstep_twips: int = 567) -> None:
    """Ustawia układ sekcji w `liczba` kolumnach (`w:cols`); kolejność dzieci `w:sectPr` zgodna ze schematem."""
    plik = Path(plik)
    pak = Pakiet(plik.read_bytes())
    doc, sect = _sekcja(pak)
    cols = sect.find(f"{W}cols")
    if cols is None:
        cols = etree.Element(f"{W}cols")
        for nastepny in PO_COLS:
            n = sect.find(f"{W}{nastepny}")
            if n is not None:
                n.addprevious(cols)
                break
        else:
            sect.append(cols)
    cols.set(f"{W}num", str(liczba))
    cols.set(f"{W}space", str(odstep_twips))
    pak.zapisz_xml("word/document.xml", doc)
    plik.write_bytes(pak.bajty())


def znak_wodny(plik: Path, napis: str) -> None:
    """Dodaje znak wodny (WordArt, srebrny, ukośny, półprzezroczysty) z napisem `napis` do nagłówka domyślnego sekcji;
    gdy sekcja nie ma nagłówka – tworzy go."""
    plik = Path(plik)
    pak = Pakiet(plik.read_bytes())
    doc, sect = _sekcja(pak)
    ref = next((r for r in sect.findall(f"{W}headerReference") if r.get(f"{W}type") == "default"), None)
    znak = (f'<w:r><w:rPr><w:noProof/></w:rPr><w:pict>{_SHAPETYPE}'
            '<v:shape id="PowerPlusWaterMarkObject1" o:spid="_x0000_s2049" type="#_x0000_t136" '
            'style="position:absolute;margin-left:0;margin-top:0;width:468pt;height:117pt;rotation:315;z-index:-251658752;'
            'mso-position-horizontal:center;mso-position-horizontal-relative:margin;mso-position-vertical:center;'
            'mso-position-vertical-relative:margin" o:allowincell="f" fillcolor="silver" stroked="f"><v:fill opacity=".5"/>'
            f'<v:textpath style="font-family:&quot;Calibri&quot;;font-size:1pt" string="{tekst(napis)}"/></v:shape>'
            '</w:pict></w:r>')
    if ref is None:
        nazwa = pak.wolna_nazwa("word/header{}.xml")
        pak.czesci[nazwa] = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:hdr xmlns:w="{NS["w"]}" '
                             f'xmlns:r="{NS["r"]}" xmlns:v="{NS["v"]}" xmlns:o="{NS["o"]}"><w:p>{znak}</w:p></w:hdr>').encode()
        pak.typ(nazwa, CT + "wordprocessingml.header+xml")
        rid = pak.dodaj_relacje("word/document.xml", "header", nazwa)
        ref = etree.Element(f"{W}headerReference")
        ref.set(f"{W}type", "default")
        ref.set(f"{{{NS['r']}}}id", rid)
        sect.insert(0, ref)
    else:
        cel = pak.relacje("word/document.xml")
        rel = next(e for e in cel if e.get("Id") == ref.get(f"{{{NS['r']}}}id"))
        nazwa = "word/" + rel.get("Target").removeprefix("/word/").removeprefix("word/")
        hdr = pak.xml(nazwa)
        akapit = hdr.find(f"{W}p")
        if akapit is None:
            akapit = etree.SubElement(hdr, f"{W}p")
        for el in pak.fragment(znak, "w", "v", "o"):
            akapit.append(el)
        pak.zapisz_xml(nazwa, hdr)
        pak.zapisz_xml("word/document.xml", doc)
        plik.write_bytes(pak.bajty())
        return
    pak.zapisz_xml("word/document.xml", doc)
    plik.write_bytes(pak.bajty())


def obraz_na_koncu(plik: Path, png: bytes, szer_cm: float, tytul: str, opis: str = "") -> None:
    """Dopisuje na końcu treści akapit z tytułem (od nowej strony) i akapit z obrazem PNG (`szer_cm` cm, proporcje zachowane)."""
    from PIL import Image
    import io
    plik = Path(plik)
    pak = Pakiet(plik.read_bytes())
    doc, sect = _sekcja(pak)
    with Image.open(io.BytesIO(png)) as im:
        iw, ih = im.size
    cx = int(szer_cm * 360000)
    cy = int(cx * ih / iw)
    nazwa = pak.wolna_nazwa("word/media/h4_obraz{}.png")
    pak.czesci[nazwa] = png
    pak.typ_domyslny("png", "image/png")
    rid = pak.dodaj_relacje("word/document.xml", "image", nazwa)
    identyfikatory = [int(e.get("id")) for e in doc.iter("{%s}docPr" % NS["wp"]) if (e.get("id") or "").isdigit()]
    n = max([8000, *identyfikatory]) + 1
    xml = (f'<w:p><w:r><w:br w:type="page"/></w:r><w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">{tekst(tytul)}</w:t></w:r></w:p>'
           '<w:p><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
           f'<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{n}" name="Obraz {n}" descr="{tekst(opis)}"/>'
           '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
           '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>'
           f'<pic:nvPicPr><pic:cNvPr id="{n}" name="h4_obraz{n}.png"/><pic:cNvPicPr/></pic:nvPicPr>'
           f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
           f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
           '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
           '</wp:inline></w:drawing></w:r></w:p>')
    for el in pak.fragment(xml, "w", "wp", "a", "pic", "r"):
        sect.addprevious(el)
    pak.zapisz_xml("word/document.xml", doc)
    plik.write_bytes(pak.bajty())
