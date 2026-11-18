"""Renderer DOCX z utrudnieniami z prawdziwych kancelarii: papier firmowy, tabele, przypisy, komentarze, zmiany
śledzone, metadane, pola formularza, rozbite runy i podpis jako obraz.

Renderer rysuje WSZYSTKIE elementy podanego `Dokumentu` (wcześniej przyciętego `utrudnienia.przytnij`);
`utrudnienia` steruje wyłącznie formą (gdzie w pakiecie OOXML trafia dana wartość). Zwracana lista `Wartosc` jest
autorytatywna: `miejsce` mówi, gdzie wartość faktycznie leży w pliku (część ZIP), także `obraz` dla logo i podpisu.

Gold obrazów dla zadania 8: `renderuj_docx(...).obrazy` to gotowe `Obraz` (PNG + wartości + ramki w pikselach
obrazu); zadanie 8 dopisuje je do `Dokument.obrazy`. `render_docx` zwraca samą listę wartości (interfejs z planu).

Gdzie co leży: treść/pola/zmiany – `word/document.xml`; nagłówek/stopka (z papierem) – `word/header*.xml`,
`word/footer*.xml`; przypisy – `word/footnotes.xml`; komentarze – `word/comments.xml` (autor także w atrybucie
`w:author`); metadane – `docProps/core.xml` (autor, tytuł, temat) i `docProps/custom.xml` (pozostałe klucze).
Autor komentarza i zmiany śledzonej to atrybut `w:author`, a treść zawiera tylko to, co dopisał (bez autora).
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import io
import random
import re
import zipfile
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

from docx import Document as NowyDocx
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.opc.part import Part
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.text.paragraph import Paragraph
from docx.text.run import Run
from lxml import etree

from ..linearyzacja import ETYKIETY, NAGLOWKI_EMAIL
from ..model import Dokument, Element, Obraz, Wartosc
from ..utrudnienia import NEUTRALNY_AUTOR, UTRUDNIENIA_DOCX, UTRUDNIENIA_POMINIETE
from . import logo, podpis

KROJ = "DejaVu Serif"
KROJ_SANS = "DejaVu Sans"
STRONA = {"pl": "Strona", "en": "Page", "es": "Página", "de": "Seite", "fr": "Page", "uk": "Сторінка"}
CT_FOOTNOTES = "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml"
CT_CUSTOM = "application/vnd.openxmlformats-officedocument.custom-properties+xml"
NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
STALA_DATA_ZIP = (2024, 1, 1, 0, 0, 0)
#: Część wartości (i zwykłych słów) dzielona na runy przy `rozbite_runy`.
UDZIAL_ROZBITYCH = 0.25


@dataclass
class WynikDocx:
    """Wynik renderowania: wartości faktycznie umieszczone w pliku i obrazy z gold (logo, podpisy)."""

    wartosci: list[Wartosc] = field(default_factory=list)
    obrazy: list[Obraz] = field(default_factory=list)


# ----------------------------------------------------------------------------- XML: runy i akapity
def _el(tag: str, **atrybuty: str) -> etree._Element:
    e = OxmlElement(tag)
    for k, v in atrybuty.items():
        e.set(qn(f"w:{k}"), str(v))
    return e


def _rpr(fmt: dict | None) -> etree._Element | None:
    if not fmt:
        return None
    rpr = _el("w:rPr")
    if "font" in fmt:
        rpr.append(_el("w:rFonts", ascii=fmt["font"], hAnsi=fmt["font"], cs=fmt["font"], eastAsia=fmt["font"]))
    if fmt.get("b"):
        rpr.append(_el("w:b"))
    if fmt.get("i"):
        rpr.append(_el("w:i"))
    if "color" in fmt:
        rpr.append(_el("w:color", val=fmt["color"]))
    if "sz" in fmt:
        rpr.append(_el("w:sz", val=fmt["sz"]))
    if fmt.get("u"):
        rpr.append(_el("w:u", val="single"))
    if "vert" in fmt:
        rpr.append(_el("w:vertAlign", val=fmt["vert"]))
    return rpr


def _run(tekst: str, fmt: dict | None = None, usuniety: bool = False, rsid: str | None = None) -> etree._Element:
    r = _el("w:r")
    if rsid:
        r.set(qn("w:rsidR"), rsid)
        r.set(qn("w:rsidRPr"), rsid)
    rpr = _rpr(fmt)
    if rpr is not None:
        r.append(rpr)
    for i, linia in enumerate(tekst.split("\n")):
        if i:
            r.append(_el("w:br"))
        t = _el("w:delText" if usuniety else "w:t")
        t.text = linia
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        r.append(t)
    return r


def _ppr(jc: str | None = None, after: int = 120, before: int = 0, ind_lewy: int | None = None,
         dolna_kreska: bool = False, keep_next: bool = False) -> etree._Element:
    ppr = _el("w:pPr")
    if keep_next:
        ppr.append(_el("w:keepNext"))
    if dolna_kreska:
        bdr = _el("w:pBdr")
        bdr.append(_el("w:bottom", val="single", sz="6", space="1", color="404040"))
        ppr.append(bdr)
    ppr.append(_el("w:spacing", before=before, after=after, line="276", lineRule="auto"))
    if ind_lewy is not None:
        ppr.append(_el("w:ind", left=ind_lewy))
    if jc:
        ppr.append(_el("w:jc", val=jc))
    return ppr


def _p(ppr: etree._Element | None = None, dzieci: list[etree._Element] = ()) -> etree._Element:
    p = _el("w:p")
    if ppr is not None:
        p.append(ppr)
    for d in dzieci:
        p.append(d)
    return p


def _pole_zlozone(instr: str, wynik: str, fmt: dict | None) -> list[etree._Element]:
    """Pole złożone (np. PAGE): begin, instrText, separate, wynik, end."""
    def fld(typ: str) -> etree._Element:
        r = _el("w:r")
        if (rpr := _rpr(fmt)) is not None:
            r.append(rpr)
        r.append(_el("w:fldChar", fldCharType=typ))
        return r
    ins = _el("w:r")
    if (rpr := _rpr(fmt)) is not None:
        ins.append(rpr)
    it = _el("w:instrText")
    it.text = f" {instr} "
    it.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    ins.append(it)
    return [fld("begin"), ins, fld("separate"), _run(wynik, fmt), fld("end")]


# ----------------------------------------------------------------------------- kontekst renderowania
class _Ctx:
    def __init__(self, d: Dokument, utrudnienia: set[str], doc) -> None:
        self.d = d
        self.utr = utrudnienia
        self.doc = doc
        self.rng = random.Random(zlib.crc32(d.id.encode("utf-8")))
        self.wynik = WynikDocx()
        self.rozbite = "rozbite_runy" in utrudnienia
        self.przypisy: list[etree._Element] = []
        self.id_zmiany = 100
        self.sect = doc.element.body.find(qn("w:sectPr"))
        self.pula_rsid = [f"{self.rng.randrange(16 ** 8):08X}" for _ in range(6)]

    def zapisz(self, w: Wartosc, miejsce: str) -> Wartosc:
        z = dataclasses.replace(w, miejsce=miejsce)
        self.wynik.wartosci.append(z)
        return z

    def data_iso(self) -> str:
        r = self.rng
        return f"{r.randint(2023, 2026)}-{r.randint(1, 12):02d}-{r.randint(1, 28):02d}T{r.randint(8, 18):02d}:" \
               f"{r.randint(0, 59):02d}:00Z"

    def dodaj(self, el: etree._Element) -> None:
        """Dopisuje element na końcu treści (przed `w:sectPr`)."""
        self.sect.addprevious(el)

    def rsidy(self, n: int) -> list[str]:
        """`n` identyfikatorów rsid, sąsiednie różne – jedyna różnica między kawałkami rozbitego tekstu."""
        wynik: list[str] = []
        for _ in range(n):
            wynik.append(self.rng.choice([r for r in self.pula_rsid if not wynik or r != wynik[-1]]))
        return wynik

    def ciecia(self, tekst: str, wartosc: bool) -> list[str]:
        """Rozbite runy są NIEWIDOCZNE (to samo formatowanie), różnią się tylko rsid. Dzielimy ok. 25% wartości
        oraz część zwykłych słów – żeby podział nie był znacznikiem danych osobowych."""
        if not self.rozbite:
            return [tekst]
        if wartosc:
            if len(tekst) < 2 or self.rng.random() >= UDZIAL_ROZBITYCH:
                return [tekst]
            n = 2 if len(tekst) < 3 else self.rng.choice((2, 3))
            ciecia = sorted(self.rng.sample(range(1, len(tekst)), n - 1))
            granice = [0, *ciecia, len(tekst)]
            return [tekst[a:b] for a, b in zip(granice, granice[1:])]
        wynik: list[str] = []
        for slowo in re.findall(r"\s+|\S+", tekst):
            if len(slowo) >= 4 and not slowo.isspace() and self.rng.random() < UDZIAL_ROZBITYCH:
                c = self.rng.randrange(1, len(slowo))
                wynik += [slowo[:c], slowo[c:]]
            else:
                wynik.append(slowo)
        return wynik

    def runy(self, fragmenty: list[str | Wartosc], miejsce: str, fmt: dict | None = None,
             usuniety: bool = False) -> list[etree._Element]:
        wynik: list[etree._Element] = []
        for f in fragmenty:
            if isinstance(f, str):
                kawalki = self.ciecia(f, False) if f else []
            elif f.tekst:
                self.zapisz(f, miejsce)
                kawalki = self.ciecia(f.tekst, True)
            else:
                continue
            # kolejne kawałki jednego tekstu: sąsiednie rsid różne; pozostałe runy – rsid bazowy
            wiele = len(kawalki) > 1 and self.rozbite
            rs = self.rsidy(len(kawalki)) if wiele else [None] * len(kawalki)
            wynik.extend(_run(k, fmt, usuniety, r) for k, r in zip(kawalki, rs))
        return wynik

    def obraz(self, png: bytes, w: Wartosc, bbox: tuple[int, int, int, int]) -> Wartosc:
        wobraz = dataclasses.replace(w, id=f"{w.id}@obraz", miejsce="obraz")
        self.wynik.wartosci.append(wobraz)
        self.wynik.obrazy.append(Obraz(f"{self.d.id}-obraz{len(self.wynik.obrazy) + 1}", png, [wobraz],
                                       [(wobraz.id, tuple(bbox))]))
        return wobraz


def _png(img) -> bytes:
    bufor = io.BytesIO()
    img.save(bufor, format="PNG")
    return bufor.getvalue()


# ----------------------------------------------------------------------------- elementy treści
def _bez_autora(e: Element) -> tuple[Wartosc, list[str | Wartosc]]:
    """Autor (fragment `autor_fragment`) i reszta fragmentów bez prefiksu „: ”."""
    i = e.atrybuty.get("autor_fragment", 0)
    autor = e.fragmenty[i]
    reszta = list(e.fragmenty[i + 1:])
    if reszta and isinstance(reszta[0], str) and reszta[0].startswith(": "):
        reszta[0] = reszta[0][2:]
    return autor, reszta


def _akapit_tresci(ctx: _Ctx, e: Element) -> etree._Element:
    fragmenty = e.fragmenty
    tekst = "".join(f if isinstance(f, str) else f.tekst for f in fragmenty)
    if len(fragmenty) == 1 and isinstance(fragmenty[0], str) and tekst.isupper() and len(tekst) <= 90:
        return _p(_ppr("center", after=200, before=240, keep_next=True),
                  ctx.runy(fragmenty, "tresc", {"b": 1, "sz": 26}))
    return _p(_ppr("both" if len(tekst) > 200 else None), ctx.runy(fragmenty, "tresc"))


def _akapit_listu(ctx: _Ctx, e: Element, nagl: bool, miejsce: str, indeks: int) -> etree._Element:
    """Nagłówek/stopka renderowane w treści (bez papieru firmowego)."""
    if nagl:
        fmt = {"b": 1, "sz": 22} if indeks == 0 else {"sz": 17, "color": "595959"}
        return _p(_ppr(after=40), ctx.runy(e.fragmenty, miejsce, fmt))
    return _p(_ppr("center", after=40, before=0), ctx.runy(e.fragmenty, miejsce, {"sz": 16, "color": "595959"}))


def _pole(ctx: _Ctx, e: Element) -> etree._Element:
    etykieta = e.atrybuty.get("etykieta", "")
    sdt = _el("w:sdt")
    pr = _el("w:sdtPr")
    pr.append(_el("w:alias", val=etykieta))
    pr.append(_el("w:tag", val=f"pole{ctx.rng.randint(100, 999)}"))
    pr.append(_el("w:id", val=ctx.rng.randint(10 ** 6, 2 * 10 ** 9)))
    pr.append(_el("w:text"))
    sdt.append(pr)
    tresc = _el("w:sdtContent")
    for r in ctx.runy(e.fragmenty, "pole"):
        tresc.append(r)
    sdt.append(tresc)
    dzieci = ([_run(f"{etykieta}: ", {"b": 1})] if etykieta else []) + [sdt]
    return _p(_ppr(after=80), dzieci)


def _zmiana(ctx: _Ctx, e: Element) -> etree._Element:
    autor, reszta = _bez_autora(e)
    ctx.zapisz(autor, "zmiany")
    usuniety = e.atrybuty.get("typ") == "del"
    znacznik = _el("w:del" if usuniety else "w:ins", id=ctx.id_zmiany, author=autor.tekst, date=ctx.data_iso())
    ctx.id_zmiany += 1
    for r in ctx.runy(reszta, "zmiany", None, usuniety):
        znacznik.append(r)
    return _p(_ppr(), [znacznik])


def _przypis(ctx: _Ctx, e: Element, p: etree._Element) -> None:
    nr = len(ctx.przypisy) + 1
    fn = etree.Element(qn("w:footnote"))
    fn.set(qn("w:id"), str(nr))
    ref = _el("w:r")
    ref.append(_rpr({"vert": "superscript"}))
    ref.append(_el("w:footnoteRef"))
    runy = [ref, _run(" ", {"sz": 18})] + ctx.runy(e.fragmenty, "przypis", {"sz": 18})
    fn.append(_p(_ppr(after=0), runy))
    ctx.przypisy.append(fn)
    znak = _el("w:r")
    znak.append(_rpr({"vert": "superscript"}))
    znak.append(_el("w:footnoteReference", id=nr))
    p.append(znak)


def _komentarz(ctx: _Ctx, e: Element, p: etree._Element) -> None:
    autor, reszta = _bez_autora(e)
    ctx.zapisz(autor, "komentarz")
    runy = [r for r in p.findall(qn("w:r")) if r.find(qn("w:t")) is not None]
    if not runy:
        r = _run(" ")
        p.append(r)
        runy = [r]
    par = Paragraph(p, ctx.doc._body)
    # inicjały neutralne: pochodne od nazwiska byłyby daną osobową poza gold
    c = ctx.doc.add_comment([Run(runy[0], par), Run(runy[-1], par)], text="", author=autor.tekst, initials="")
    c._comment_elm.set(qn("w:date"), ctx.data_iso())
    tp = c.paragraphs[0]._p
    for r in tp.findall(qn("w:r")):
        if r.find(qn("w:t")) is not None:
            tp.remove(r)
    for r in ctx.runy(reszta, "komentarz"):
        tp.append(r)


def _tabela(ctx: _Ctx, komorki: list[Element]) -> None:
    wiersze = max(e.atrybuty["wiersz"] for e in komorki) + 1
    kolumny = max(e.atrybuty["kolumna"] for e in komorki) + 1
    t = ctx.doc.add_table(rows=wiersze, cols=kolumny)
    t.style = ctx.doc.styles["Table Grid"]
    rozmiar = 16 if kolumny >= 6 else 18
    komorki_tabeli = t._cells  # jednorazowo: t.cell() przelicza całą tabelę przy każdym wywołaniu
    uzyte: set[tuple[int, int]] = set()
    for e in komorki:
        w, k = e.atrybuty["wiersz"], e.atrybuty["kolumna"]
        kom = komorki_tabeli[w * kolumny + k]
        par = kom.paragraphs[0] if (w, k) not in uzyte else kom.add_paragraph()
        uzyte.add((w, k))
        naglowek = w == 0 and wiersze > 2
        fmt = {"sz": rozmiar, **({"b": 1} if naglowek else {})}
        p = par._p
        for stary in p.findall(qn("w:pPr")):
            p.remove(stary)
        p.insert(0, _ppr(after=20, before=20))
        for r in ctx.runy(e.fragmenty, "tabela", fmt):
            p.append(r)
        if naglowek:
            tc_pr = kom._tc.get_or_add_tcPr()
            tc_pr.append(_el("w:shd", val="clear", color="auto", fill="E7E6E6"))
    ctx.dodaj(_p(_ppr(after=60)))


def _podpis(ctx: _Ctx, e: Element) -> None:
    wartosci = [f for f in e.fragmenty if isinstance(f, Wartosc)]
    tylko_imie = len(wartosci) == 1 and all(isinstance(f, Wartosc) or not f.strip() for f in e.fragmenty)
    if "podpis" in ctx.utr and tylko_imie and wartosci[0].tekst:
        img, bbox = podpis.generuj(wartosci[0].tekst, ctx.rng)
        ctx.obraz(_png(img), wartosci[0], bbox)
        p = _p(_ppr("right", after=0, before=360, ind_lewy=5200, dolna_kreska=True))
        ctx.dodaj(p)
        Paragraph(p, ctx.doc._body).add_run().add_picture(io.BytesIO(_png(img)), width=Cm(4.5))
        ctx.dodaj(_p(_ppr("right", after=120), ctx.runy(e.fragmenty, "tresc", {"sz": 18})))
    else:
        ctx.dodaj(_p(_ppr("right", after=120, before=480), ctx.runy(e.fragmenty, "tresc")))


# ----------------------------------------------------------------------------- układ dokumentu
def _rozloz(n_akapitow: int, ile: int, przesuniecie: float) -> list[int]:
    return [min(n_akapitow - 1, int((i + przesuniecie) * n_akapitow / (ile + 1) + 0.5)) for i in range(1, ile + 1)]


def _metadane(ctx: _Ctx) -> tuple[list[Element], list[Element], dict[str, str]]:
    """Metadane: nagłówki w treści (początek/koniec) i właściwości pliku; wartości `metadane` idą do core/custom."""
    d = ctx.d
    etykiety = ETYKIETY.get(d.jezyk, {})
    poczatek: list[Element] = []
    koniec: list[Element] = []
    wlasciwosci: dict[str, str] = {}
    naglowki_email = [k for k in NAGLOWKI_EMAIL if k in d.metadane] if d.typ == "email" else []
    kolejnosc = naglowki_email + sorted((k for k in d.metadane if k not in naglowki_email),
                                        key=lambda x: (etykiety.get(x, x), x))
    for k in kolejnosc:
        v = d.metadane[k]
        w_properties = isinstance(v, Wartosc) and v.miejsce == "metadane"
        if w_properties:
            wlasciwosci[k] = ctx.zapisz(v, "metadane").tekst
            if k in naglowki_email:  # blok nagłówka e-maila widoczny też w treści (druga kopia, miejsce „tresc”)
                poczatek.append(Element("akapit", [f"{etykiety.get(k, k)}: ", dataclasses.replace(v, miejsce="tresc")]))
        elif isinstance(v, Wartosc) or k in naglowki_email:
            e = Element("akapit", [f"{etykiety.get(k, k)}: ", v])
            (poczatek if k in naglowki_email else koniec).append(e)
        else:
            wlasciwosci[k] = v
    return poczatek, koniec, wlasciwosci


def _ustaw_styl(doc) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = KROJ
    normal.font.size = Pt(10)
    rf = normal.element.get_or_add_rPr().rFonts
    for a in ("eastAsia", "cs"):
        rf.set(qn(f"w:{a}"), KROJ)
    sek = doc.sections[0]
    sek.page_width, sek.page_height = Cm(21), Cm(29.7)
    sek.left_margin = sek.right_margin = Cm(2.5)
    sek.top_margin, sek.bottom_margin = Cm(2.8), Cm(2.3)
    sek.header_distance = sek.footer_distance = Cm(1.2)


def _papier_firmowy(ctx: _Ctx, naglowki: list[Element], stopki: list[Element]) -> None:
    doc = ctx.doc
    sek = doc.sections[0]
    hdr = sek.header
    hdr.is_linked_to_previous = False
    h = hdr._element
    for stary in list(h):
        h.remove(stary)
    firma = next((f for e in naglowki for f in e.fragmenty if isinstance(f, Wartosc) and f.kategoria == "ORGANIZACJA"),
                 None)
    if firma is not None:
        img, bbox = logo.generuj_z_ramka(firma.tekst, ctx.rng)
        png = _png(img)
        ctx.obraz(png, firma, bbox)
        p = _p(_ppr(after=60))
        h.append(p)
        Paragraph(p, hdr).add_run().add_picture(io.BytesIO(png), height=Cm(1.5))
    for i, e in enumerate(naglowki):
        fmt = {"b": 1, "sz": 20} if i == 0 else {"sz": 16, "color": "595959"}
        h.append(_p(_ppr(after=20, dolna_kreska=i == len(naglowki) - 1), ctx.runy(e.fragmenty, "naglowek", fmt)))
    if not len(h):
        h.append(_p())
    ftr = sek.footer
    ftr.is_linked_to_previous = False
    f = ftr._element
    for stary in list(f):
        f.remove(stary)
    mala = {"sz": 16, "color": "595959"}
    for e in stopki:
        f.append(_p(_ppr("center", after=20), ctx.runy(e.fragmenty, "stopka", mala)))
    f.append(_p(_ppr("center", after=0), [_run(f"{STRONA.get(ctx.d.jezyk, 'Page')} ", mala),
                                          *_pole_zlozone("PAGE", "1", mala)]))


def _czesc(nazwa: str, ct: str, blob: bytes, pakiet) -> Part:
    return Part(PackURI(nazwa), ct, blob, pakiet)


def _zaloz_przypisy(ctx: _Ctx) -> None:
    root = etree.Element(qn("w:footnotes"), nsmap={"w": NS_W})
    for typ, i, tag in (("separator", -1, "w:separator"), ("continuationSeparator", 0, "w:continuationSeparator")):
        fn = etree.SubElement(root, qn("w:footnote"))
        fn.set(qn("w:type"), typ)
        fn.set(qn("w:id"), str(i))
        p = etree.SubElement(fn, qn("w:p"))
        r = etree.SubElement(p, qn("w:r"))
        etree.SubElement(r, qn(tag))
    for fn in ctx.przypisy:
        root.append(fn)
    blob = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    czesc = _czesc("/word/footnotes.xml", CT_FOOTNOTES, blob, ctx.doc.part.package)
    ctx.doc.part.relate_to(czesc, RT.FOOTNOTES)
    ustawienia = ctx.doc.settings.element
    fp = _el("w:footnotePr")
    fp.append(_el("w:footnote", id="-1"))
    fp.append(_el("w:footnote", id="0"))
    compat = ustawienia.find(qn("w:compat"))
    (compat.addprevious if compat is not None else ustawienia.append)(fp)


def _zaloz_custom(ctx: _Ctx, wlasciwosci: dict[str, str]) -> None:
    pozycje = "".join(
        f'<property fmtid="{{D5CDD505-2E9C-101B-9397-08002B2CF9AE}}" pid="{i}" name="{escape(k)}">'
        f"<vt:lpwstr>{escape(v)}</vt:lpwstr></property>" for i, (k, v) in enumerate(sorted(wlasciwosci.items()), 2))
    blob = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/custom-properties" '
            'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            f"{pozycje}</Properties>").encode("utf-8")
    czesc = _czesc("/docProps/custom.xml", CT_CUSTOM, blob, ctx.doc.part.package)
    ctx.doc.part.package.relate_to(czesc, RT.CUSTOM_PROPERTIES)


def _ustaw_core(ctx: _Ctx, wlasciwosci: dict[str, str]) -> None:
    cp = ctx.doc.core_properties
    autor = wlasciwosci.pop("author", NEUTRALNY_AUTOR.get(ctx.d.jezyk, "User"))
    cp.author = cp.last_modified_by = autor
    cp.title = wlasciwosci.pop("title", "")
    cp.subject = wlasciwosci.pop("subject", "")
    cp.comments = cp.keywords = cp.category = ""
    cp.language = ctx.d.jezyk
    cp.revision = 1
    utworzony = dt.datetime(ctx.rng.randint(2022, 2025), ctx.rng.randint(1, 12), ctx.rng.randint(1, 28),
                            ctx.rng.randint(8, 17), ctx.rng.randint(0, 59))
    cp.created = utworzony
    cp.modified = utworzony + dt.timedelta(days=ctx.rng.randint(0, 40), minutes=ctx.rng.randint(1, 600))


def _zapisz_deterministycznie(zrodlo: Path, cel: Path) -> None:
    """Przepakowuje ZIP ze stałymi znacznikami czasu (python-docx zapisuje bieżący czas)."""
    with zipfile.ZipFile(zrodlo) as zin, zipfile.ZipFile(cel, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            zi = zipfile.ZipInfo(info.filename, STALA_DATA_ZIP)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o600 << 16
            zout.writestr(zi, zin.read(info.filename))


def renderuj_docx(d: Dokument, plik: Path, utrudnienia: set[str]) -> WynikDocx:
    """Zapisuje `d` jako DOCX w `plik`; zwraca umieszczone wartości i obrazy z gold (zob. docstring modułu)."""
    nieznane = set(utrudnienia) - UTRUDNIENIA_DOCX - UTRUDNIENIA_POMINIETE
    if nieznane:
        raise ValueError(f"nieznane utrudnienia DOCX: {sorted(nieznane)}")
    plik = Path(plik)
    doc = NowyDocx()
    ctx = _Ctx(d, set(utrudnienia), doc)
    body = doc.element.body
    sect = body.find(qn("w:sectPr"))
    for p in list(body):
        if p is not sect:
            body.remove(p)
    _ustaw_styl(doc)

    papier = "papier_firmowy" in utrudnienia
    naglowki = [e for e in d.elementy if e.rodzaj == "naglowek"]
    stopki = [e for e in d.elementy if e.rodzaj == "stopka"]
    poczatek_meta, koniec_meta, wlasciwosci = _metadane(ctx)

    elementy: list[tuple[str, object]] = [("m", e) for e in poczatek_meta]
    if not papier:
        elementy += [("n", e) for e in naglowki]
    tabele: dict[int, list[Element]] = {}
    for e in d.elementy:
        if e.rodzaj == "akapit":
            elementy.append(("p", e))
        elif e.rodzaj == "komorka":
            nr = e.atrybuty["tabela"]
            if nr not in tabele:
                elementy.append(("t", nr))
            tabele.setdefault(nr, []).append(e)
        elif e.rodzaj == "podpis":
            elementy.append(("sig", e))
    elementy += [("m", e) for e in koniec_meta]
    if not papier:
        elementy += [("s", e) for e in stopki]

    pola = [e for e in d.elementy if e.rodzaj == "pole"]
    przypisy = [e for e in d.elementy if e.rodzaj == "przypis"]
    komentarze = [e for e in d.elementy if e.rodzaj == "komentarz"]
    zmiany = [e for e in d.elementy if e.rodzaj == "zmiany"]
    if (przypisy or komentarze or zmiany) and not any(k in ("p", "m") for k, _ in elementy):
        elementy.insert(0, ("p", Element("akapit", [" "])))
    # pola przed pierwszym podpisem (albo stopką w treści / na końcu)
    miejsce_pol = next((i for i, (k, _) in enumerate(elementy) if k in ("sig", "s")), len(elementy))
    elementy[miejsce_pol:miejsce_pol] = [("pole", e) for e in pola]
    kotwice = [i for i, (k, _) in enumerate(elementy) if k in ("p", "m")]
    doczepy: dict[int, list[tuple[str, Element]]] = {}
    for rodzaj, lista, przes in (("przypis", przypisy, 0.0), ("komentarz", komentarze, 0.5)):
        for e, poz in zip(lista, _rozloz(len(kotwice), len(lista), przes) if kotwice else []):
            doczepy.setdefault(kotwice[poz], []).append((rodzaj, e))
    po: dict[int, list[Element]] = {}
    for e, poz in zip(zmiany, _rozloz(len(kotwice), len(zmiany), 0.25) if kotwice else []):
        po.setdefault(kotwice[poz], []).append(e)

    if papier and (naglowki or stopki):
        _papier_firmowy(ctx, naglowki, stopki)
    indeks_naglowka = 0
    for i, (rodzaj, ob) in enumerate(elementy):
        if rodzaj in ("p", "m"):
            p = _akapit_tresci(ctx, ob)  # type: ignore[arg-type]
            ctx.dodaj(p)
            for r, e in doczepy.get(i, []):
                (_przypis if r == "przypis" else _komentarz)(ctx, e, p)
            for e in po.get(i, []):
                ctx.dodaj(_zmiana(ctx, e))
        elif rodzaj == "n":
            ctx.dodaj(_akapit_listu(ctx, ob, True, "tresc", indeks_naglowka))  # type: ignore[arg-type]
            indeks_naglowka += 1
        elif rodzaj == "s":
            ctx.dodaj(_akapit_listu(ctx, ob, False, "tresc", 0))  # type: ignore[arg-type]
        elif rodzaj == "t":
            _tabela(ctx, tabele[ob])  # type: ignore[index]
        elif rodzaj == "pole":
            ctx.dodaj(_pole(ctx, ob))  # type: ignore[arg-type]
        elif rodzaj == "sig":
            _podpis(ctx, ob)  # type: ignore[arg-type]

    if ctx.przypisy:
        _zaloz_przypisy(ctx)
    if ctx.rozbite:
        rsids = doc.settings.element.find(qn("w:rsids"))
        if rsids is not None:
            for r in ctx.pula_rsid:
                rsids.append(_el("w:rsid", val=r))
    _ustaw_core(ctx, wlasciwosci)
    if wlasciwosci:
        _zaloz_custom(ctx, wlasciwosci)
    plik.parent.mkdir(parents=True, exist_ok=True)
    tmp = plik.with_name(plik.name + ".tmp")
    doc.save(str(tmp))
    _zapisz_deterministycznie(tmp, plik)
    tmp.unlink()
    return ctx.wynik


def render_docx(d: Dokument, plik: Path, utrudnienia: set[str]) -> list[Wartosc]:
    """Jak `renderuj_docx`, ale zwraca tylko listę umieszczonych wartości (z `miejsce`, w tym `obraz`)."""
    return renderuj_docx(d, plik, utrudnienia).wartosci
