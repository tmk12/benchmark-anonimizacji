"""Wstrzykiwanie treści ukrytej do PPTX (warstwa trudnych przypadków H3, spec §11 pkt 1).

Dopisuje do pliku wyrenderowanego przez `render.pptx` elementy z `Dokument.ukryte` (rodzaje `pptx.*`): notatki
prelegenta, slajd ukryty (`show="0"`), kształt poza obszarem slajdu, alt text obrazu i komentarze (starszy format
`commentAuthors.xml` + `comments/commentN.xml`). Mapowanie element -> miejsce gold: `metodyka/miejsca-ukryte.md`.
"""
from __future__ import annotations

import io
from collections.abc import Callable
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.opc.constants import CONTENT_TYPE as CT, RELATIONSHIP_TYPE as RT
from pptx.opc.package import Part
from pptx.opc.packuri import PackURI
from pptx.util import Cm

from .model import Element
from .render.wspolne import przepakuj, tekst_fragmentow
from .ukryta_pakiet import ROZDZIELACZ, czesci, png_bajty

NS_P = "http://schemas.openxmlformats.org/presentationml/2006/main"


class Ctx:
    def __init__(self, prs) -> None:
        self.prs = prs
        self.komentarze: list[tuple[int, str, str]] = []       # (indeks slajdu, autor, tekst)

    def slajd(self, indeks: int):
        s = list(self.prs.slides)
        return s[min(indeks, len(s) - 1)]


def _notatki(ctx: Ctx, e: Element) -> None:
    ctx.slajd(e.atrybuty["slajd"]).notes_slide.notes_text_frame.text = tekst_fragmentow(e.fragmenty).replace(ROZDZIELACZ, "\n")


def _slajd_ukryty(ctx: Ctx, e: Element) -> None:
    prs = ctx.prs
    s = prs.slides.add_slide(prs.slide_layouts[1])
    tytul, *reszta = czesci(e)
    s.shapes.title.text_frame.text = tytul
    s.placeholders[1].text_frame.text = "\n".join(reszta)
    s._element.set("show", "0")


def _poza_slajdem(ctx: Ctx, e: Element) -> None:
    s = ctx.slajd(e.atrybuty["slajd"])
    ramka = s.shapes.add_textbox(ctx.prs.slide_width + Cm(3), Cm(3), Cm(10), Cm(3))
    ramka.text_frame.text = "\n".join(czesci(e))
    ramka.name = "Notatka robocza"


def _alt_text(ctx: Ctx, e: Element) -> None:
    s = ctx.slajd(e.atrybuty["slajd"])
    obraz = s.shapes.add_picture(io.BytesIO(png_bajty(48, 5)), Cm(1), Cm(1), Cm(1.2), Cm(1.2))
    cnv = obraz._element.nvPicPr.cNvPr
    opis, *tytul = czesci(e)
    cnv.set("descr", opis)
    if tytul:
        cnv.set("title", tytul[0])


def _komentarz(ctx: Ctx, e: Element) -> None:
    ctx.komentarze.append((e.atrybuty["slajd"], e.atrybuty["autor"], tekst_fragmentow(e.fragmenty)))


def _zapisz_komentarze(ctx: Ctx) -> None:
    prs = ctx.prs
    pakiet = prs.part.package
    autorzy: dict[str, int] = {}
    stary = next((r.target_part for r in prs.part.rels.values() if r.reltype == RT.COMMENT_AUTHORS), None)
    lista = etree.fromstring(stary.blob) if stary is not None else etree.fromstring(f'<p:cmAuthorLst xmlns:p="{NS_P}"/>')
    for a in lista:
        autorzy[a.get("name")] = int(a.get("id"))
    for _, autor, _ in ctx.komentarze:
        if autor not in autorzy:
            autorzy[autor] = max(autorzy.values(), default=-1) + 1
            etree.SubElement(lista, f"{{{NS_P}}}cmAuthor", id=str(autorzy[autor]), name=autor, initials="R",
                             lastIdx="0", clrIdx=str(autorzy[autor]))
    ostatni = {int(a.get("id")): int(a.get("lastIdx")) for a in lista}
    slajdy = list(prs.slides)
    nr = sum(1 for p in pakiet.iter_parts() if str(p.partname).startswith("/ppt/comments/comment"))
    for indeks in sorted({i for i, _, _ in ctx.komentarze}):
        slajd = slajdy[min(indeks, len(slajdy) - 1)]
        istniejacy = next((r.target_part for r in slajd.part.rels.values() if r.reltype == RT.COMMENTS), None)
        cm = etree.fromstring(istniejacy.blob) if istniejacy is not None else etree.fromstring(f'<p:cmLst xmlns:p="{NS_P}"/>')
        for i, autor, tresc in ctx.komentarze:
            if min(i, len(slajdy) - 1) != min(indeks, len(slajdy) - 1):
                continue
            a = autorzy[autor]
            ostatni[a] = ostatni.get(a, 0) + 1
            k = etree.SubElement(cm, f"{{{NS_P}}}cm", authorId=str(a), dt="2024-01-15T10:00:00.000", idx=str(ostatni[a]))
            etree.SubElement(k, f"{{{NS_P}}}pos", x="10", y=str(10 + 40 * len(cm)))
            etree.SubElement(k, f"{{{NS_P}}}text").text = tresc
        blob = etree.tostring(cm, xml_declaration=True, encoding="UTF-8", standalone=True)
        if istniejacy is not None:
            istniejacy._blob = blob
        else:
            nr += 1
            slajd.part.relate_to(Part(PackURI(f"/ppt/comments/comment{nr}.xml"), CT.PML_COMMENTS, pakiet, blob), RT.COMMENTS)
    for a in lista:
        a.set("lastIdx", str(ostatni.get(int(a.get("id")), 0)))
    blob = etree.tostring(lista, xml_declaration=True, encoding="UTF-8", standalone=True)
    if stary is not None:
        stary._blob = blob
    else:
        prs.part.relate_to(Part(PackURI("/ppt/commentAuthors.xml"), CT.PML_COMMENT_AUTHORS, pakiet, blob), RT.COMMENT_AUTHORS)


OBSLUGA: dict[str, Callable[[Ctx, Element], None]] = {
    "pptx.notatki": _notatki, "pptx.slajd_ukryty": _slajd_ukryty, "pptx.poza_slajdem": _poza_slajdem,
    "pptx.alt_text": _alt_text, "pptx.komentarz": _komentarz,
}


def wstrzyknij_pptx(plik: Path, elementy: list[Element]) -> None:
    """Dopisuje `elementy` (rodzaje `pptx.*`) do pliku PPTX `plik` (nadpisuje go, deterministycznie)."""
    prs = Presentation(str(plik))
    ctx = Ctx(prs)
    for e in elementy:
        OBSLUGA[e.rodzaj](ctx, e)
    if ctx.komentarze:
        _zapisz_komentarze(ctx)
    bufor = io.BytesIO()
    prs.save(bufor)
    Path(plik).write_bytes(przepakuj(bufor.getvalue()))
