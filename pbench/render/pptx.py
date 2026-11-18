"""Renderer PPTX: slajd tytułowy z logo, slajdy z blokami tekstu, slajdy z tabelą, notatki prelegenta, komentarze
(starszy format `ppt/comments`) i właściwości dokumentu.

Wejście to `Dokument` przycięty przez `przytnij_dla("pptx", …)`; renderer rysuje WSZYSTKIE jego elementy, a
`utrudnienia` (`UTRUDNIENIA_PPTX`) steruje formą. Zwracana lista `Wartosc` jest autorytatywna (`miejsce` = gdzie
wartość faktycznie leży), z obrazami z gold jak w DOCX: `renderuj_pptx(...).obrazy` (logo z ramką nazwy firmy).

Układ: slajd 1 – nagłówek pierwszy jako tytuł (pozostałe nagłówki jako podtytuł; w typie „prezentacja” kolejne nagłówki
są tytułami slajdów treści), z logo (`logo`); slajdy treści – akapity porcjami, podpis i (bez `logo`) stopka na ostatnim
slajdzie; po pierwszym slajdzie treści – slajdy z tabelą (`tabele`, po 10 wierszy, nagłówek kolumn powtórzony, o ile nie
zawiera wartości). Tytuły slajdów bez własnego nagłówka są neutralne („Treść 2”, „Tabela 1”).

Gdzie co leży: tytuły i bloki – `ppt/slides/slideN.xml` („tresc”; nagłówki z `logo` – „naglowek”); stopka z `logo` –
pole stopki na każdym slajdzie („stopka”; gold ma jedną wartość o tym samym id na każde wystąpienie); tabela – `a:tbl` w slajdzie („tabela”); notatki
prelegenta – `ppt/notesSlides/notesSlideN.xml` (miejsce „przypis” – PPTX nie ma przypisów, notatki są jego odpowiednikiem);
komentarze – `ppt/comments/commentN.xml` (treść) i `ppt/commentAuthors.xml` (autor), miejsce „komentarz”; właściwości –
`docProps/core.xml` (autor, tytuł, temat), `docProps/custom.xml` (pozostałe klucze) i `docProps/app.xml` (`<Company>` –
kopia nazwy firmy z nagłówka), miejsce „metadane”. Komentarze zapisujemy w starszym formacie (`p:cmLst`); nowsze
komentarze wątkowe (`ppt/comments/modernComment*.xml`) mają tę samą treść, inne tagi i nie są generowane.
"""
from __future__ import annotations

import dataclasses
import io
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.enum.text import PP_ALIGN
from pptx.opc.constants import CONTENT_TYPE as CT
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.opc.package import Part
from pptx.opc.packuri import PackURI
from pptx.util import Inches, Pt

from ..model import Dokument, Element, Obraz, Wartosc
from ..utrudnienia import UTRUDNIENIA_POMINIETE, UTRUDNIENIA_PPTX
from . import logo, wspolne

TRESC = {"pl": "Treść", "en": "Content", "es": "Contenido", "de": "Inhalt", "fr": "Contenu", "uk": "Зміст"}
TABELA = {"pl": "Tabela", "en": "Table", "es": "Tabla", "de": "Tabelle", "fr": "Tableau", "uk": "Таблиця"}
TYTUL = {"pl": "Prezentacja", "en": "Presentation", "es": "Presentación", "de": "Präsentation", "fr": "Présentation", "uk": "Презентація"}
LIMIT_ZNAKOW_SLAJDU = 800
WIERSZY_NA_SLAJD = 10
SZARY = RGBColor(0x59, 0x59, 0x59)


@dataclass
class WynikPptx:
    """Wynik renderowania: wartości umieszczone w pliku i obrazy z gold (logo)."""

    wartosci: list[Wartosc] = field(default_factory=list)
    obrazy: list[Obraz] = field(default_factory=list)


class _Ctx:
    def __init__(self, d: Dokument) -> None:
        self.d = d
        self.rng = wspolne.rng_dokumentu(d)
        self.wynik = WynikPptx()
        self.daty = wspolne.data_pliku(self.rng)  # (utworzony, zmodyfikowany): też daty komentarzy

    def zapisz(self, w: Wartosc, miejsce: str) -> Wartosc:
        z = wspolne.zapisz_jako(w, miejsce)
        self.wynik.wartosci.append(z)
        return z

    def tekst(self, fragmenty: list[str | Wartosc], miejsce: str) -> str:
        return "".join(f if isinstance(f, str) else self.zapisz(f, miejsce).tekst for f in fragmenty)

    def obraz(self, png: bytes, w: Wartosc, bbox: tuple[int, int, int, int]) -> None:
        wobraz = dataclasses.replace(w, id=f"{w.id}@obraz", miejsce="obraz")
        self.wynik.wartosci.append(wobraz)
        self.wynik.obrazy.append(Obraz(f"{self.d.id}-obraz{len(self.wynik.obrazy) + 1}", png, [wobraz],
                                       [(wobraz.id, tuple(bbox))]))


def _usun(shape) -> None:
    shape._element.getparent().remove(shape._element)


def _ustaw_tekst(tf, akapity: list[str], rozmiar: int, wyrownanie=None, kolor: RGBColor | None = None,
                 bez_punktora: bool = False) -> None:
    tf.word_wrap = True
    for i, t in enumerate(akapity):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        r = p.add_run()
        r.text = t
        r.font.size = Pt(rozmiar)
        if kolor is not None:
            r.font.color.rgb = kolor
        if wyrownanie is not None:
            p.alignment = wyrownanie
        if bez_punktora:  # bez punktora i wcięcia, jak zwykły akapit
            ppr = p._p.get_or_add_pPr()
            ppr.set("marL", "0")
            ppr.set("indent", "0")
            ppr.insert(0, ppr.makeelement("{http://schemas.openxmlformats.org/drawingml/2006/main}buNone", {}))


def _rozmiar(znaki: int) -> int:
    return 16 if znaki <= 500 else 14 if znaki <= 800 else 12


def _porcje(akapity: list[str], liczba: int | None) -> list[list[str]]:
    """Dzieli akapity na kolejne porcje: `liczba` równych albo wg budżetu znaków slajdu."""
    if liczba:
        baza, reszta = divmod(len(akapity), liczba)
        wynik, i = [], 0
        for k in range(liczba):
            n = baza + (1 if k < reszta else 0)
            wynik.append(akapity[i:i + n])
            i += n
        return wynik
    wynik, biezaca, suma = [], [], 0
    for a in akapity:
        if biezaca and suma + len(a) > LIMIT_ZNAKOW_SLAJDU:
            wynik.append(biezaca)
            biezaca, suma = [], 0
        biezaca.append(a)
        suma += len(a)
    if biezaca:
        wynik.append(biezaca)
    return wynik


def _tabela(ctx: _Ctx, prs, slajd, wiersze: list[list[str]]) -> None:
    kolumn = max(len(w) for w in wiersze)
    szer = prs.slide_width - Inches(1.0)
    gt = slajd.shapes.add_table(len(wiersze), kolumn, Inches(0.5), Inches(1.6), szer, Inches(0.4) * len(wiersze))
    rozmiar = 8 if kolumn >= 7 else 10
    for i, w in enumerate(wiersze):
        for k in range(kolumn):
            kom = gt.table.cell(i, k)
            kom.text_frame.text = ""
            r = kom.text_frame.paragraphs[0].add_run()
            r.text = w[k] if k < len(w) else ""
            r.font.size = Pt(rozmiar)


def _tytul_slajdu(slajd, tekst: str) -> None:
    slajd.shapes.title.text_frame.text = ""
    r = slajd.shapes.title.text_frame.paragraphs[0].add_run()
    r.text = tekst
    r.font.size = Pt(28 if len(tekst) <= 50 else 22)


def _stopka_pola(slajd, uklad, tekst: str) -> None:
    for ph in uklad.placeholders:
        if ph.placeholder_format.type == PP_PLACEHOLDER.FOOTER:
            slajd.shapes.clone_placeholder(ph)
    for sh in slajd.placeholders:
        if sh.placeholder_format.type == PP_PLACEHOLDER.FOOTER:
            sh.text_frame.text = ""
            r = sh.text_frame.paragraphs[0].add_run()
            r.text = tekst
            r.font.size = Pt(10)
            return


def _komentarze(ctx: _Ctx, prs, slajdy: list, komentarze: list[Element]) -> None:
    """Komentarze w starszym formacie: `commentAuthors.xml` i `comments/commentN.xml` na slajdach."""
    autorzy: dict[str, int] = {}
    wpisy: dict[int, list[tuple[int, str]]] = {}
    n = len(komentarze)
    for i, e in enumerate(komentarze):
        indeks = e.atrybuty.get("autor_fragment", 0)
        autor = ctx.zapisz(e.fragmenty[indeks], "komentarz").tekst
        reszta = list(e.fragmenty[indeks + 1:])
        if reszta and isinstance(reszta[0], str) and reszta[0].startswith(": "):
            reszta[0] = reszta[0][2:]
        a = autorzy.setdefault(autor, len(autorzy))
        wpisy.setdefault(min(len(slajdy) - 1, int((i + 0.5) * len(slajdy) / n)), []).append(
            (a, ctx.tekst(reszta, "komentarz")))
    ns = 'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
    ostatni = {a: 0 for a in autorzy.values()}
    pakiet = prs.part.package
    nr = 0
    for s, lista in sorted(wpisy.items()):
        nr += 1
        cm = []
        for j, (a, tekst) in enumerate(lista):
            ostatni[a] += 1
            cm.append(f'<p:cm authorId="{a}" dt="{_data(ctx)}" idx="{ostatni[a]}"><p:pos x="{10 + 40 * j}" y="{10 + 40 * j}"/>'
                      f"<p:text>{escape(tekst)}</p:text></p:cm>")
        blob = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                f"<p:cmLst {ns}>{''.join(cm)}</p:cmLst>").encode("utf-8")
        czesc = Part(PackURI(f"/ppt/comments/comment{nr}.xml"), CT.PML_COMMENTS, pakiet, blob)
        slajdy[s].part.relate_to(czesc, RT.COMMENTS)
    lista_autorow = "".join(
        f'<p:cmAuthor id="{i}" name="{escape(nazwa)}" initials="" lastIdx="{ostatni[i]}" clrIdx="{i}"/>'
        for nazwa, i in autorzy.items())
    blob = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f"<p:cmAuthorLst {ns}>{lista_autorow}</p:cmAuthorLst>").encode("utf-8")
    prs.part.relate_to(Part(PackURI("/ppt/commentAuthors.xml"), CT.PML_COMMENT_AUTHORS, pakiet, blob),
                       RT.COMMENT_AUTHORS)


def _data(ctx: _Ctx) -> str:
    """Data komentarza między utworzeniem a modyfikacją pliku."""
    utworzony, zmodyfikowany = ctx.daty
    kiedy = utworzony + (zmodyfikowany - utworzony) * ctx.rng.random()
    return kiedy.strftime("%Y-%m-%dT%H:%M:%S.000")


def renderuj_pptx(d: Dokument, plik: Path, utrudnienia: set[str]) -> WynikPptx:
    """Zapisuje `d` jako PPTX w `plik`; zwraca umieszczone wartości i obrazy z gold (zob. docstring modułu)."""
    nieznane = set(utrudnienia) - UTRUDNIENIA_PPTX - UTRUDNIENIA_POMINIETE
    if nieznane:
        raise ValueError(f"nieznane utrudnienia PPTX: {sorted(nieznane)}")
    plik = Path(plik)
    ctx = _Ctx(d)
    jez = d.jezyk
    z_logo = "logo" in utrudnienia
    m_nag, m_stopka = ("naglowek", "stopka") if z_logo else ("tresc", "tresc")
    prs = Presentation()
    uklad_tytulowy, uklad_tresci, uklad_tabeli = prs.slide_layouts[0], prs.slide_layouts[1], prs.slide_layouts[5]

    meta_poczatek, meta_koniec = wspolne.metadane_w_tresci(d)
    naglowki = [e for e in d.elementy if e.rodzaj == "naglowek"]
    akapity_el = meta_poczatek + [e for e in d.elementy if e.rodzaj == "akapit"] + meta_koniec
    podpisy = [e for e in d.elementy if e.rodzaj == "podpis"]
    stopki = [e for e in d.elementy if e.rodzaj == "stopka"]
    przypisy = [e for e in d.elementy if e.rodzaj == "przypis"]
    komentarze = [e for e in d.elementy if e.rodzaj == "komentarz"]
    tabele: dict[int, dict[int, dict[int, list[Element]]]] = {}
    for e in d.elementy:
        if e.rodzaj == "komorka":
            a = e.atrybuty
            tabele.setdefault(a["tabela"], {}).setdefault(a["wiersz"], {}).setdefault(a["kolumna"], []).append(e)

    # --- teksty (kolejność zapisu = kolejność w dokumencie: nagłówki, akapity, podpisy, tabele, stopka)
    teksty_nag = [ctx.tekst(e.fragmenty, m_nag) for e in naglowki]
    akapity = [ctx.tekst(e.fragmenty, "tresc") for e in akapity_el]
    tytul_prezentacji = teksty_nag[0] if teksty_nag else (
        akapity.pop(0) if akapity and len(akapity[0]) <= 90 and akapity[0].isupper() else TYTUL.get(jez, "Presentation"))
    reszta_nag = teksty_nag[1:]
    tytuly_slajdow = reszta_nag if d.typ == "prezentacja" and reszta_nag else []
    podtytul = [] if tytuly_slajdow else reszta_nag
    teksty_podpis = [ctx.tekst(e.fragmenty, "tresc") for e in podpisy]
    tabele_tekst: list[list[list[str]]] = []
    for nr in sorted(tabele):
        w = tabele[nr]
        tabele_tekst.append([[("\n".join(ctx.tekst(e.fragmenty, "tabela") for e in w[i][k]) if k in w[i] else "")
                              for k in range(max(max(r) for r in w.values()) + 1)] for i in sorted(w)])
    naglowek_kolumn = [
        all(isinstance(f, str) for k in tabele[nr].get(0, {}).values() for e in k for f in e.fragmenty)
        for nr in sorted(tabele)]
    teksty_stopki = [ctx.tekst(e.fragmenty, m_stopka) for e in stopki]

    # --- slajd tytułowy
    slajdy: list = []
    s0 = prs.slides.add_slide(uklad_tytulowy)
    slajdy.append(s0)
    s0.shapes.title.text_frame.text = ""
    r = s0.shapes.title.text_frame.paragraphs[0].add_run()
    r.text = tytul_prezentacji
    r.font.size = Pt(34 if len(tytul_prezentacji) <= 50 else 26)
    podtyt = s0.placeholders[1]
    if podtytul:
        _ustaw_tekst(podtyt.text_frame, podtytul, 16, kolor=SZARY)
    else:
        _usun(podtyt)
    if z_logo:
        firma = next((f for e in naglowki for f in e.fragmenty if isinstance(f, Wartosc) and f.kategoria == "ORGANIZACJA"),
                     None)
        if firma is not None:
            obraz, bbox = logo.generuj_z_ramka(firma.tekst, ctx.rng)
            bufor = io.BytesIO()
            obraz.save(bufor, format="PNG")
            png = bufor.getvalue()
            s0.shapes.add_picture(io.BytesIO(png), Inches(0.4), Inches(0.3), height=Inches(1.0))
            ctx.obraz(png, firma, bbox)

    # --- slajdy treści
    porcje = _porcje(akapity, len(tytuly_slajdow) or None) if (akapity or tytuly_slajdow) else []
    if (podpisy or stopki and not z_logo) and not porcje:
        porcje = [[]]
    tresci: list[tuple] = []  # (slajd, porcja)
    for i, porcja in enumerate(porcje):
        s = prs.slides.add_slide(uklad_tresci)
        _tytul_slajdu(s, tytuly_slajdow[i] if tytuly_slajdow else f"{TRESC.get(jez, 'Content')} {i + 1}")
        tresci.append((s, porcja))
    for i, (s, porcja) in enumerate(tresci):
        ostatni = i == len(tresci) - 1
        akap = list(porcja)
        if ostatni:
            akap += teksty_podpis
            if not z_logo:
                akap += teksty_stopki
        cialo = s.placeholders[1]
        if akap:
            _ustaw_tekst(cialo.text_frame, akap, _rozmiar(sum(map(len, akap))), bez_punktora=True)
            if ostatni and teksty_podpis:  # podpis wyrównany do prawej
                n_pod = len(teksty_podpis) + (0 if z_logo else len(teksty_stopki))
                for p in cialo.text_frame.paragraphs[len(akap) - n_pod:len(akap) - (0 if z_logo else len(teksty_stopki))]:
                    p.alignment = PP_ALIGN.RIGHT
        else:
            _usun(cialo)

    # --- slajdy z tabelą (po pierwszym slajdzie treści)
    tabele_slajdy: list = []
    for nr, wiersze in enumerate(tabele_tekst):
        naglowek = wiersze[0] if naglowek_kolumn[nr] and len(wiersze) > 2 else None
        dane = wiersze[1:] if naglowek else wiersze
        for j in range(0, len(dane), WIERSZY_NA_SLAJD):
            s = prs.slides.add_slide(uklad_tabeli)
            _tytul_slajdu(s, f"{TABELA.get(jez, 'Table')} {len(tabele_slajdy) + 1}")
            _tabela(ctx, prs, s, ([naglowek] if naglowek else []) + dane[j:j + WIERSZY_NA_SLAJD])
            tabele_slajdy.append(s)
    # przesunięcie slajdów tabel za pierwszy slajd treści
    if tabele_slajdy:
        lista = prs.slides._sldIdLst
        ids = list(lista)
        n_tr = 1 + len(tresci)
        po = ids[:min(2, n_tr)]
        tab = ids[n_tr:]
        reszta = ids[min(2, n_tr):n_tr]
        for el in ids:
            lista.remove(el)
        for el in po + tab + reszta:
            lista.append(el)
    wszystkie = list(prs.slides)
    zawartosc = wszystkie[1:] or wszystkie

    # --- stopka jako pole stopki na każdym slajdzie (zapisana raz)
    if z_logo and teksty_stopki:
        tekst_stopki = " | ".join(teksty_stopki)
        for i, s in enumerate(wszystkie):
            _stopka_pola(s, s.slide_layout, tekst_stopki)
            if i:  # każde wystąpienie stopki to osobna wartość w gold (to samo id)
                for e in stopki:
                    ctx.tekst(e.fragmenty, m_stopka)

    # --- notatki prelegenta i komentarze
    if przypisy:
        n = len(przypisy)
        grupy: dict[int, list[str]] = {}
        for i, e in enumerate(przypisy):
            idx = min(len(zawartosc) - 1, int(i * len(zawartosc) / n))
            grupy.setdefault(idx, []).append(ctx.tekst(e.fragmenty, "przypis"))
        for idx, lista in grupy.items():
            zawartosc[idx].notes_slide.notes_text_frame.text = "\n".join(lista)
    if komentarze:
        _komentarze(ctx, prs, zawartosc, komentarze)

    # --- metadane
    core, wlasne = wspolne.rozdziel_metadane(d, ctx.zapisz)
    firma_meta = None
    if "metadane" in utrudnienia:
        firma = next((f for e in naglowki for f in e.fragmenty if isinstance(f, Wartosc) and f.kategoria == "ORGANIZACJA"),
                     None)
        firma_meta = ctx.zapisz(firma, "metadane").tekst if firma else None
    p = prs.core_properties
    p.author = p.last_modified_by = core["author"]
    p.title, p.subject = core.get("title", ""), core.get("subject", "")
    p.comments = p.keywords = p.category = ""
    p.language = jez
    p.revision = 1
    p.created, p.modified = ctx.daty
    if wlasne:
        prs.part.package.relate_to(Part(PackURI("/docProps/custom.xml"), wspolne.CT_CUSTOM, prs.part.package,
                                        wspolne.custom_xml(wlasne)), RT.CUSTOM_PROPERTIES)

    plik.parent.mkdir(parents=True, exist_ok=True)
    bufor = io.BytesIO()
    prs.save(bufor)
    podmiany = {"docProps/app.xml": lambda x: wspolne.wstaw_firme(x, firma_meta)} if firma_meta else {}
    plik.write_bytes(wspolne.przepakuj(bufor.getvalue(), podmiany))
    return ctx.wynik


def render_pptx(d: Dokument, plik: Path, utrudnienia: set[str]) -> list[Wartosc]:
    """Jak `renderuj_pptx`, ale zwraca tylko listę umieszczonych wartości (z `miejsce`, w tym `obraz`)."""
    return renderuj_pptx(d, plik, utrudnienia).wartosci
