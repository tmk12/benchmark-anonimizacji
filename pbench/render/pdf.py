"""Renderer PDF z tekstem (reportlab) z utrudnieniami: papier firmowy, tabele, przypisy, komentarze, metadane, pola
formularza i podpis jako obraz.

Kontrakt jak w DOCX (`pbench.render.docx`): renderer rysuje WSZYSTKIE elementy podanego `Dokumentu` (wcześniej przyciętego
`utrudnienia.przytnij_pdf`); `utrudnienia` steruje wyłącznie formą. Zwracana lista `Wartosc` jest autorytatywna:
`miejsce` mówi, gdzie wartość faktycznie leży w pliku, także `obraz` dla logo i podpisu. Zmiany śledzone w PDF nie
występują – dokument z elementami `zmiany` jest błędem (`ValueError`).

Gdzie co leży: treść/tabele/nagłówek/stopka/przypisy – tekst stron (`naglowek` i `stopka` powtarzają się na każdej
stronie przy `papier_firmowy`, w gold liczą się raz; przypisy u dołu strony, na której stoi odnośnik); komentarze –
adnotacje `/Annot /Text` (`/T` = autor, `/Contents` = treść); pola – widgety AcroForm (`/V` = `/DV` = wartość, wygląd
`/AP` z osadzoną czcionką DejaVu Sans, więc znaki diakrytyczne są widoczne); metadane – słownik
`/Info` (Author, Title, Subject, pozostałe klucze jako własne) **i** XMP (dc:creator, dc:title, dc:description, własne
klucze w przestrzeni `pdfx`). Wartość wieloczłonowa może łamać się na granicy wiersza jak w zwykłym PDF – ekstraktory
tekstu podają wtedy znak końca wiersza zamiast spacji.

Plik jest deterministyczny: stałe daty tworzenia (z ziarna dokumentu), stałe `/ID`, tryb `invariant` reportlaba.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import io
import random
import re
import unicodedata
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape, unescape

import pikepdf
from reportlab.lib.colors import Color, black, white
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, KeepTogether, PageTemplate, Paragraph, Spacer, Table,
                                TableStyle)

from ..model import Dokument, Element, Obraz, Wartosc
from ..utrudnienia import NEUTRALNY_AUTOR, UTRUDNIENIA_PDF, UTRUDNIENIA_POMINIETE
from . import bez_a85, logo, podpis
from .docx import STRONA, _bez_autora, _metadane, _png, _rozloz

FONTY = "/usr/share/fonts/truetype/dejavu"
SZER, WYS = A4
MARGINES = 70.9  # 2,5 cm z lewej i prawej
SZER_TEKSTU = SZER - 2 * MARGINES
SZARY = Color(0.25, 0.25, 0.25)
MAX_PRZEBIEGOW = 6
WYS_LOGO = 39.7  # 1,4 cm
SZER_PODPISU = 127.6  # 4,5 cm

#: Umiejscowienie obrazu na stronie: (id wartości obrazowej, numer strony od 1, ramka w pt: x0, y0, x1, y1; początek
#: układu w lewym dolnym rogu strony) – używane przez skan do wyznaczenia ramek logo i podpisu.
Umiejscowienie = tuple[str, int, tuple[float, float, float, float]]


def _zarejestruj_czcionki() -> None:
    for nazwa, plik in (("DejaVuSerif", "DejaVuSerif.ttf"), ("DejaVuSerif-Bold", "DejaVuSerif-Bold.ttf"),
                        ("DejaVuSans", "DejaVuSans.ttf"), ("DejaVuSans-Bold", "DejaVuSans-Bold.ttf")):
        if nazwa not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(nazwa, f"{FONTY}/{plik}"))
    pdfmetrics.registerFontFamily("DejaVuSerif", normal="DejaVuSerif", bold="DejaVuSerif-Bold",
                                  italic="DejaVuSerif", boldItalic="DejaVuSerif-Bold")  # kursywy brak w systemie


_zarejestruj_czcionki()

#: Pisma RTL (hebrajski, arabski), których nie ma w kroju DejaVu Serif: tekst w tych zakresach jest składany kroiem DejaVu
#: Sans (warstwa trudnych przypadków H4a, `rtl`); poza nimi znaki zostają bez zmian – trzon korpusu się nie zmienia.
#: Zakres obejmuje formy prezentacyjne arabskiego (U+FB50–FDFF, U+FE70–FEFC), które powstają przy kształtowaniu liter.
_RTL = re.compile("[\u0590-\u08ff\ufb1d-\ufdff\ufe70-\ufefc]+")
#: Znaki sterujące bidi (osadzenia, nadpisania, izolacje): w PDF nie mają glifu, ich skutek jest już w kolejności wizualnej.
_STEROWANIE_BIDI = re.compile("[\u202a-\u202e\u2066-\u2069]")
_ZNACZNIK = re.compile(r"(<[^>]*>)")


def _kolejnosc_wizualna(tekst: str) -> str:
    """Tekst logiczny -> tekst do narysowania: kształtowanie liter arabskich (formy początkowe/środkowe/końcowe, ligatury) i
    porządek wizualny wg algorytmu bidi (akapit LTR). Tak zapisuje glify prawdziwy program (Word, LibreOffice): w strumieniu
    PDF jest kolejność wizualna, a mapa ToUnicode oddaje znaki z kształtowania."""
    from arabic_reshaper import reshape
    from bidi import get_display
    return _STEROWANIE_BIDI.sub("", get_display(reshape(tekst), base_dir="L"))


def _nadpisanie_po(fragment: str, nadpisanie: bool) -> bool:
    """Stan nadpisania kierunku (RLO/LRO do PDF) po tekście `fragment`."""
    for znak in fragment:
        if znak in "\u202d\u202e":
            nadpisanie = True
        elif znak == "\u202c":
            nadpisanie = False
    return nadpisanie


def _zastepcze(znaczniki: str) -> str:
    """Znaczniki akapitu z tekstem RTL w kolejności wizualnej (`_kolejnosc_wizualna`) i krojem DejaVu Sans dla pism RTL;
    bez RTL i znaków bidi akapit zostaje bez zmian."""
    if not (_RTL.search(znaczniki) or _STEROWANIE_BIDI.search(znaczniki)):
        return znaczniki
    kawalki = _ZNACZNIK.split(znaczniki)
    for i in range(0, len(kawalki), 2):               # parzyste: tekst między znacznikami (`<br/>` rozdziela wiersze)
        if _RTL.search(kawalki[i]) or _STEROWANIE_BIDI.search(kawalki[i]):
            kawalki[i] = escape(_kolejnosc_wizualna(unescape(kawalki[i])))
    return _RTL.sub(lambda m: f'<font name="DejaVuSans">{m.group(0)}</font>', "".join(kawalki))


STYL = ParagraphStyle("tresc", fontName="DejaVuSerif", fontSize=10, leading=13.8, spaceAfter=6, alignment=TA_LEFT,
                      allowWidows=1, allowOrphans=1)
STYL_JUSTOWANY = ParagraphStyle("justowany", parent=STYL, alignment=TA_JUSTIFY)
STYL_TYTUL = ParagraphStyle("tytul", parent=STYL, fontName="DejaVuSerif-Bold", fontSize=13, leading=17,
                            alignment=TA_CENTER, spaceBefore=12, spaceAfter=10, keepWithNext=1)
STYL_NAGL1 = ParagraphStyle("nagl1", parent=STYL, fontName="DejaVuSans-Bold", fontSize=10, leading=12.5, spaceAfter=1)
STYL_NAGL = ParagraphStyle("nagl", parent=STYL, fontName="DejaVuSans", fontSize=8.5, leading=10.8, spaceAfter=1,
                           textColor=SZARY)
STYL_STOPKA = ParagraphStyle("stopka", parent=STYL_NAGL, alignment=TA_CENTER)
STYL_PRZYPIS = ParagraphStyle("przypis", parent=STYL, fontSize=8, leading=10.5, spaceAfter=1)
STYL_PODPIS = ParagraphStyle("podpis", parent=STYL, alignment=TA_RIGHT, fontSize=9, spaceAfter=6)


@dataclass
class WynikPdf:
    """Wynik renderowania: wartości faktycznie umieszczone w pliku, obrazy z gold (logo, podpisy) i ich położenie."""

    wartosci: list[Wartosc] = field(default_factory=list)
    obrazy: list[Obraz] = field(default_factory=list)
    #: Położenie obrazów na stronach (logo na każdej stronie, podpis raz) – dla skanu.
    umiejscowienie: list[Umiejscowienie] = field(default_factory=list)
    #: Strefy stron w pt (od dołu): nagłówek powyżej `WYS - gora`, stopka poniżej `dol`, przypisy do `dol + rezerwa`.
    gora: float = 0.0
    dol: float = 0.0
    rezerwy: dict[int, float] = field(default_factory=dict)
    strony: int = 0
    #: Tylko z `geometria=True` (skan): (wartość, strona od 1, ramka w pt) – pozycje zapisane przy rysowaniu.
    ramki: list[tuple[Wartosc, int, tuple[float, float, float, float]]] = field(default_factory=list)


class _Znacznik(Flowable):
    """Element o zerowych wymiarach: przy rysowaniu wywołuje `funkcja(canvas, strona, x, y)` (pozycja bezwzględna)."""

    def __init__(self, funkcja) -> None:
        super().__init__()
        self.funkcja = funkcja

    def wrap(self, aw: float, ah: float) -> tuple[float, float]:
        return 0, 0

    def draw(self) -> None:
        x, y = self.canv.absolutePosition(0, 0)
        self.funkcja(self.canv, self.canv.getPageNumber(), x, y)


class _Pole(Flowable):
    """Pole formularza: etykieta tekstem i widget AcroForm z wartością w `/V`."""

    WYSOKOSC = 22

    def __init__(self, ctx: _Ctx, etykieta: str, wartosc: str, nazwa: str) -> None:
        super().__init__()
        self.ctx, self.etykieta, self.wartosc, self.nazwa = ctx, etykieta, wartosc, nazwa

    def wrap(self, aw: float, ah: float) -> tuple[float, float]:
        self.aw = aw
        return aw, self.WYSOKOSC

    def draw(self) -> None:
        etykieta = f"{self.etykieta}:" if self.etykieta else ""
        self.canv.setFont("DejaVuSans-Bold", 9)
        self.canv.setFillColor(black)
        self.canv.drawString(0, 7, etykieta)
        przesuniecie = pdfmetrics.stringWidth(etykieta, "DejaVuSans-Bold", 9) + 8 if etykieta else 0
        szer = min(self.aw - przesuniecie, max(150.0, pdfmetrics.stringWidth(self.wartosc, "DejaVuSans", 9) + 14))
        x, y = self.canv.absolutePosition(przesuniecie, 1)
        # wartość i wygląd (/V, /AP z osadzoną czcionką DejaVu) dopisuje `_dokoncz` – reportlab zna tylko Helveticę
        self.canv.acroForm.textfield(value="", name=self.nazwa, x=x, y=y, width=szer, height=16,
                                     fontName="Helvetica", fontSize=9, borderWidth=0.5, borderColor=black,
                                     fillColor=white, textColor=black, forceBorder=True, fieldFlags="",
                                     annotationFlags="print")


class _ObrazPodpisu(Flowable):
    """Podpis jako obraz przy prawym marginesie nad linią; zapisuje położenie obrazu na stronie."""

    def __init__(self, ctx: _Ctx, png: bytes, bbox: tuple[int, int, int, int], wid: str) -> None:
        super().__init__()
        self.ctx, self.png, self.bbox, self.wid = ctx, png, bbox, wid
        self.czytnik = ImageReader(io.BytesIO(png))
        iw, ih = self.czytnik.getSize()
        self.iw, self.ih = iw, ih
        self.szer = SZER_PODPISU
        self.wys = SZER_PODPISU * ih / iw

    def wrap(self, aw: float, ah: float) -> tuple[float, float]:
        self.aw = aw
        return aw, self.wys + 14

    def draw(self) -> None:
        x = self.aw - self.szer
        self.canv.drawImage(self.czytnik, x, 8, self.szer, self.wys, mask="auto")
        self.canv.setStrokeColor(Color(0.25, 0.25, 0.25))
        self.canv.setLineWidth(0.6)
        self.canv.line(x - 10, 6, self.aw, 6)
        ax, ay = self.canv.absolutePosition(x, 8)
        self.ctx.umiejscowienie.append((self.wid, self.canv.getPageNumber(),
                                        ramka_pt(self.bbox, ax, ay, self.szer, self.wys, self.iw, self.ih)))


def ramka_pt(bbox: tuple[int, int, int, int], ax: float, ay: float, szer: float, wys: float, iw: int,
              ih: int) -> tuple[float, float, float, float]:
    """Ramka w pikselach obrazu -> pt strony, gdy obraz o lewym dolnym rogu (ax, ay) ma rozmiar szer x wys."""
    bx0, by0, bx1, by1 = bbox
    return (ax + bx0 * szer / iw, ay + wys - by1 * wys / ih, ax + bx1 * szer / iw, ay + wys - by0 * wys / ih)


# ----------------------------------------------------------------------------- kontekst renderowania
class _Ctx:
    def __init__(self, d: Dokument, utrudnienia: set[str], rezerwy: dict[int, float], geometria: bool = False) -> None:
        self.d = d
        self.geo = geometria
        #: indeks znacznika -> (wartość z gold, numer wystąpienia); pozycje znaczników zapisane przy rysowaniu
        self.kawalki: list[tuple[Wartosc, int, str]] = []
        self.pozycje: dict[int, list[tuple[str, int, float, float, float, str]]] = {}
        self.wystapienia = 0
        self.utr = utrudnienia
        self.rng = random.Random(zlib.crc32(d.id.encode("utf-8")))
        self.wynik = WynikPdf()
        self.rezerwy = rezerwy
        self.potrzebne: dict[int, float] = {}
        self.notki: dict[int, list[tuple[int, str]]] = {}
        self.komentarze: list[tuple[str, str]] = []
        self.pola: list[tuple[str, str]] = []
        self.umiejscowienie = self.wynik.umiejscowienie
        self.nr_przypisu = 0
        self.papier = "papier_firmowy" in utrudnienia
        self.wlasciwosci: dict[str, str] = {}

    def zapisz(self, w: Wartosc, miejsce: str) -> Wartosc:
        z = dataclasses.replace(w, miejsce=miejsce)
        self.wynik.wartosci.append(z)
        return z

    def tekst(self, fragmenty: list[str | Wartosc], miejsce: str) -> str:
        """Znaczniki akapitu reportlaba z fragmentów; wartości trafiają do gold z miejscem `miejsce`."""
        czesci: list[str] = []
        nadpisanie = False       # za U+202E (RLO) i przed U+202C: wartość jest rysowana w odwrotnej kolejności znaków
        for f in fragmenty:
            if isinstance(f, str):
                czesci.append(escape(f).replace("\n", "<br/>"))
                nadpisanie = _nadpisanie_po(f, nadpisanie)
            elif f.tekst:
                # PDF zapisuje glify w kolejności wizualnej: wartość pod RLO leży w strumieniu odwrócona względem zapisu
                # logicznego (zob. `_kolejnosc_wizualna`), a gold ma być tym, co jest w pliku
                z = self.zapisz(dataclasses.replace(f, tekst=f.tekst[::-1]) if nadpisanie else f, miejsce)
                if not self.geo:
                    czesci.append(escape(f.tekst).replace("\n", "<br/>"))
                    continue
                self.wystapienia += 1
                for token in re.findall(r"\s+|\S+", f.tekst):
                    if token.isspace():
                        czesci.append(escape(token).replace("\n", "<br/>"))
                        continue
                    self.kawalki.append((z, self.wystapienia, token))
                    n = len(self.kawalki) - 1
                    czesci.append(f'<onDraw name="pbench" label="{n}:s"/>{escape(token)}'
                                  f'<onDraw name="pbench" label="{n}:e"/>')
        return _zastepcze("".join(czesci))

    def znacz(self, canv, rodzaj: str, etykieta: str) -> None:
        """Wywołanie znacznika `<onDraw>`: zapisuje pozycję bezwzględną (pt) początku/końca słowa wartości."""
        n, k = etykieta.split(":")
        info = canv._curr_tx_info
        x, y = canv.absolutePosition(info["cur_x"], info["cur_y"])
        fs = info["tx"]._fontsize or info["xs"].style.fontSize
        self.pozycje.setdefault(int(n), []).append((k, canv.getPageNumber(), x, y, fs, info["xs"].style.fontName))

    def ramki(self) -> list[tuple[Wartosc, int, tuple[float, float, float, float]]]:
        """Ramki wartości (pt, lewy dolny róg strony): jedna na wiersz i stronę, z pozycji zapisanych przy rysowaniu."""
        poz: dict[tuple[int, int], list[tuple[float, float, float, float]]] = {}
        wartosc: dict[int, Wartosc] = {}
        for n, lista in sorted(self.pozycje.items()):
            z, wyst, token = self.kawalki[n]
            starty = [p for p in lista if p[0] == "s"]
            konce = [p for p in lista if p[0] == "e"]
            for (_, st, x0, y0, fs, font), (_, _, x1, y1, _, _) in zip(starty, konce):
                wartosc[wyst] = z
                dol, gora = -0.2 * fs, 0.82 * fs
                if abs(y0 - y1) < 0.5 * fs:
                    poz.setdefault((wyst, st), []).append((x0, y0 + dol, x1, y0 + gora))
                else:  # znacznik początku został na końcu poprzedniego wiersza: słowo w całości w następnym
                    poz.setdefault((wyst, st), []).append(
                        (x1 - pdfmetrics.stringWidth(token, font, fs), y1 + dol, x1, y1 + gora))
        wynik = []
        for (wyst, strona), pudelka in poz.items():
            wiersze: list[list[float]] = []
            for b in pudelka:
                if wiersze and abs(wiersze[-1][1] - b[1]) < 1.0 and b[0] >= wiersze[-1][0]:
                    wiersze[-1][2] = max(wiersze[-1][2], b[2])
                else:
                    wiersze.append(list(b))
            wynik += [(wartosc[wyst], strona, tuple(w)) for w in wiersze]  # type: ignore[misc]
        return wynik

    def obraz(self, png: bytes, w: Wartosc, bbox: tuple[int, int, int, int]) -> Wartosc:
        wobraz = dataclasses.replace(w, id=f"{w.id}@obraz", miejsce="obraz")
        self.wynik.wartosci.append(wobraz)
        self.wynik.obrazy.append(Obraz(f"{self.d.id}-obraz{len(self.wynik.obrazy) + 1}", png, [wobraz],
                                       [(wobraz.id, tuple(bbox))]))
        return wobraz

    def data_iso(self) -> dt.datetime:
        r = self.rng
        return dt.datetime(r.randint(2022, 2025), r.randint(1, 12), r.randint(1, 28), r.randint(8, 17),
                           r.randint(0, 59))


# ----------------------------------------------------------------------------- elementy treści
def _akapit(ctx: _Ctx, e: Element, dodatek: str = "") -> Paragraph:
    fragmenty = e.fragmenty
    tekst = "".join(f if isinstance(f, str) else f.tekst for f in fragmenty)
    if len(fragmenty) == 1 and isinstance(fragmenty[0], str) and tekst.isupper() and len(tekst) <= 90:
        return Paragraph(ctx.tekst(fragmenty, "tresc") + dodatek, STYL_TYTUL)
    # w trybie geometrii (skan) bez justowania: pozycje słów w wierszu są wtedy dokładne
    return Paragraph(ctx.tekst(fragmenty, "tresc") + dodatek,
                     STYL_JUSTOWANY if len(tekst) > 200 and not ctx.geo else STYL)


def _akapit_listu(ctx: _Ctx, e: Element, nagl: bool, indeks: int) -> Paragraph:
    """Nagłówek/stopka renderowane w treści (bez papieru firmowego)."""
    styl = (STYL_NAGL1 if indeks == 0 else STYL_NAGL) if nagl else STYL_STOPKA
    return Paragraph(ctx.tekst(e.fragmenty, "tresc"), styl)


def _tabela(ctx: _Ctx, komorki: list[Element], szer_dostepna: float = SZER_TEKSTU) -> Table:
    wiersze = max(e.atrybuty["wiersz"] for e in komorki) + 1
    kolumny = max(e.atrybuty["kolumna"] for e in komorki) + 1
    naglowek = wiersze > 2
    teksty = [[[] for _ in range(kolumny)] for _ in range(wiersze)]
    for e in sorted(komorki, key=lambda x: (x.atrybuty["wiersz"], x.atrybuty["kolumna"])):
        teksty[e.atrybuty["wiersz"]][e.atrybuty["kolumna"]].append(e)
    # kolumny: najszersze nierozdzielne słowo wyznacza minimum; nadwyżkę dzielimy wg długości tekstu
    rozmiar = 9.0
    while True:
        minima, waga = [], []
        for k in range(kolumny):
            slowa = [s for w in range(wiersze) for e in teksty[w][k]
                     for s in "".join(f if isinstance(f, str) else f.tekst for f in e.fragmenty).split()]
            minima.append(max([pdfmetrics.stringWidth(s, "DejaVuSerif-Bold", rozmiar) for s in slowa] + [8]) + 7)
            waga.append(max(sum(len(s) + 1 for s in slowa), 4))
        if sum(minima) <= szer_dostepna or rozmiar <= 5.5:
            break
        rozmiar -= 0.5
    nadwyzka = max(szer_dostepna - sum(minima), 0)
    szer = [m + nadwyzka * wg / sum(waga) for m, wg in zip(minima, waga)]
    styl = ParagraphStyle("kom", parent=STYL, fontSize=rozmiar, leading=rozmiar * 1.3, spaceAfter=0)
    styl_n = ParagraphStyle("komn", parent=styl, fontName="DejaVuSerif-Bold")
    dane = [[[Paragraph(ctx.tekst(e.fragmenty, "tabela"), styl_n if naglowek and w == 0 else styl)
              for e in teksty[w][k]] or [Paragraph("", styl)] for k in range(kolumny)] for w in range(wiersze)]
    ts = [("GRID", (0, 0), (-1, -1), 0.5, Color(0.2, 0.2, 0.2)), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
          ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
    if naglowek:
        ts.append(("BACKGROUND", (0, 0), (-1, 0), Color(0.9, 0.9, 0.9)))
    return Table(dane, colWidths=szer, repeatRows=1 if naglowek else 0, style=TableStyle(ts), hAlign="LEFT")


def _pole(ctx: _Ctx, e: Element) -> _Pole:
    wartosci = [f for f in e.fragmenty if isinstance(f, Wartosc)]
    tekst = "".join(f if isinstance(f, str) else f.tekst for f in e.fragmenty)
    for w in wartosci:
        ctx.zapisz(w, "pole")
    nazwa = f"pole{len(ctx.pola) + 1}"
    ctx.pola.append((nazwa, tekst))
    return _Pole(ctx, e.atrybuty.get("etykieta", ""), tekst, nazwa)


def _komentarz(ctx: _Ctx, e: Element) -> _Znacznik:
    autor, reszta = _bez_autora(e)
    ctx.zapisz(autor, "komentarz")
    tresc = "".join(f if isinstance(f, str) else ctx.zapisz(f, "komentarz").tekst for f in reszta)
    nr = len(ctx.komentarze)
    ctx.komentarze.append((autor.tekst, tresc))

    def rysuj(canv, strona: int, x: float, y: float) -> None:
        canv.textAnnotation(f"@@C{nr}@@", Rect=(SZER - MARGINES + 8, y - 4, SZER - MARGINES + 22, y + 10),
                            T=f"@@A{nr}@@", name=f"komentarz{nr}")

    return _Znacznik(rysuj)


def _przypis(ctx: _Ctx, e: Element) -> tuple[str, _Znacznik]:
    """Znak odnośnika (dopisywany do akapitu) i znacznik rejestrujący przypis na stronie, gdzie kończy się akapit."""
    ctx.nr_przypisu += 1
    nr = ctx.nr_przypisu
    tresc = ctx.tekst(e.fragmenty, "przypis")

    def rysuj(canv, strona: int, x: float, y: float) -> None:
        ctx.notki.setdefault(strona, []).append((nr, tresc))

    return f"<super>{nr}</super>", _Znacznik(rysuj)


def _podpis(ctx: _Ctx, e: Element) -> list[Flowable]:
    wartosci = [f for f in e.fragmenty if isinstance(f, Wartosc)]
    tylko_imie = len(wartosci) == 1 and all(isinstance(f, Wartosc) or not f.strip() for f in e.fragmenty)
    if "podpis" in ctx.utr and tylko_imie and wartosci[0].tekst:
        img, bbox = podpis.generuj(wartosci[0].tekst, ctx.rng)
        png = _png(img)
        wobraz = ctx.obraz(png, wartosci[0], bbox)
        return [Spacer(1, 18), _ObrazPodpisu(ctx, png, bbox, wobraz.id),
                Paragraph(ctx.tekst(e.fragmenty, "tresc"), STYL_PODPIS)]
    return [Spacer(1, 22), Paragraph(ctx.tekst(e.fragmenty, "tresc"), STYL_PODPIS)]


# ----------------------------------------------------------------------------- układ strony
class _Uklad:
    """Nagłówek i stopka (papier firmowy) liczone raz; rysowane na każdej stronie."""

    def __init__(self, ctx: _Ctx, naglowki: list[Element], stopki: list[Element]) -> None:
        self.ctx = ctx
        self.logo = None
        self.glowa: list[Paragraph] = []
        self.stopka: list[Paragraph] = []
        if ctx.papier:
            firma = next((f for e in naglowki for f in e.fragmenty
                          if isinstance(f, Wartosc) and f.kategoria == "ORGANIZACJA"), None)
            if firma is not None:
                img, bbox = logo.generuj_z_ramka(firma.tekst, ctx.rng)
                png = _png(img)
                wobraz = ctx.obraz(png, firma, bbox)
                self.logo = (ImageReader(io.BytesIO(png)), bbox, wobraz.id, img.width, img.height)
            self.glowa = [Paragraph(ctx.tekst(e.fragmenty, "naglowek"), STYL_NAGL1 if i == 0 else STYL_NAGL)
                          for i, e in enumerate(naglowki)]
            self.stopka = [Paragraph(ctx.tekst(e.fragmenty, "stopka"), STYL_STOPKA) for e in stopki]
            wys_g = sum(p.wrap(SZER_TEKSTU, 1000)[1] for p in self.glowa)
            wys_s = sum(p.wrap(SZER_TEKSTU, 1000)[1] for p in self.stopka)
            self.gora = 24 + (WYS_LOGO + 5 if self.logo else 0) + wys_g + 20
            self.dol = 22 + 12 + wys_s + 14
        else:
            self.gora = self.dol = 56.7
        ctx.wynik.gora, ctx.wynik.dol = self.gora, self.dol

    def strona(self, canv, doc) -> None:
        ctx = self.ctx
        strona = canv.getPageNumber()
        rez = ctx.rezerwy.get(strona, 0.0)
        for ramka in doc.pageTemplate.frames:        # jedna ramka albo kolumny (`dwie_kolumny`)
            ramka.y1, ramka.height = self.dol + rez, WYS - self.gora - self.dol - rez
        canv.setNamedCB("pbench", ctx.znacz)
        if not ctx.papier:
            return
        y = WYS - 24
        if self.logo:
            czytnik, bbox, wid, iw, ih = self.logo
            szer = WYS_LOGO * iw / ih
            canv.drawImage(czytnik, MARGINES, y - WYS_LOGO, szer, WYS_LOGO)
            ctx.umiejscowienie.append((wid, strona, ramka_pt(bbox, MARGINES, y - WYS_LOGO, szer, WYS_LOGO, iw, ih)))
            y -= WYS_LOGO + 5
        for p in self.glowa:
            w, h = p.wrap(SZER_TEKSTU, 1000)
            p.drawOn(canv, MARGINES, y - h)
            y -= h
        canv.setStrokeColor(Color(0.25, 0.25, 0.25))
        canv.setLineWidth(0.5)
        canv.line(MARGINES, y - 5, SZER - MARGINES, y - 5)
        # stopka: numer strony na samym dole, nad nim wiersze stopki
        canv.setFont("DejaVuSans", 8.5)
        canv.setFillColor(SZARY)
        canv.drawCentredString(SZER / 2, 22, f"{STRONA.get(ctx.d.jezyk, 'Page')} {strona}")
        y = 34
        for p in reversed(self.stopka):
            w, h = p.wrap(SZER_TEKSTU, 1000)
            p.drawOn(canv, MARGINES, y)
            y += h
        canv.line(MARGINES, y + 3, SZER - MARGINES, y + 3)

    def koniec_strony(self, canv, doc) -> None:
        """Przypisy u dołu strony (nad stopką); zapisuje, ile miejsca potrzeba, do następnego przebiegu."""
        strona = canv.getPageNumber()
        notki = self.ctx.notki.get(strona, [])
        if not notki:
            return
        akapity = [Paragraph(f"<super>{nr}</super> {tresc}", STYL_PRZYPIS) for nr, tresc in notki]
        wysokosci = [p.wrap(SZER_TEKSTU, 1000)[1] for p in akapity]
        potrzeba = sum(wysokosci) + 10
        self.ctx.potrzebne[strona] = potrzeba
        y = self.dol + potrzeba - 6
        canv.setStrokeColor(black)
        canv.setLineWidth(0.4)
        canv.line(MARGINES, y, MARGINES + SZER_TEKSTU * 0.3, y)
        y -= 3
        for p, h in zip(akapity, wysokosci):
            p.drawOn(canv, MARGINES, y - h)
            y -= h


#: Odstęp między kolumnami układu `kolumny=2` (pt).
ODSTEP_KOLUMN = 18.0


def _przebieg(d: Dokument, utrudnienia: set[str], rezerwy: dict[int, float],
              geometria: bool, kolumny: int = 1) -> tuple[bytes, _Ctx]:
    ctx = _Ctx(d, utrudnienia, rezerwy, geometria)
    naglowki = [e for e in d.elementy if e.rodzaj == "naglowek"]
    stopki = [e for e in d.elementy if e.rodzaj == "stopka"]
    poczatek_meta, koniec_meta, ctx.wlasciwosci = _metadane(ctx)
    uklad = _Uklad(ctx, naglowki, stopki)

    elementy: list[tuple[str, object]] = [("m", e) for e in poczatek_meta]
    if not ctx.papier:
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
    if not ctx.papier:
        elementy += [("s", e) for e in stopki]

    pola = [e for e in d.elementy if e.rodzaj == "pole"]
    przypisy = [e for e in d.elementy if e.rodzaj == "przypis"]
    komentarze = [e for e in d.elementy if e.rodzaj == "komentarz"]
    if (przypisy or komentarze) and not any(k in ("p", "m") for k, _ in elementy):
        elementy.insert(0, ("p", Element("akapit", [" "])))
    miejsce_pol = next((i for i, (k, _) in enumerate(elementy) if k in ("sig", "s")), len(elementy))
    elementy[miejsce_pol:miejsce_pol] = [("pole", e) for e in pola]
    kotwice = [i for i, (k, _) in enumerate(elementy) if k in ("p", "m")]
    doczepy: dict[int, list[tuple[str, Element]]] = {}
    for rodzaj, lista, przes in (("przypis", przypisy, 0.0), ("komentarz", komentarze, 0.5)):
        for e, poz in zip(lista, _rozloz(len(kotwice), len(lista), przes) if kotwice else []):
            doczepy.setdefault(kotwice[poz], []).append((rodzaj, e))

    szer_kolumny = (SZER_TEKSTU - ODSTEP_KOLUMN * (kolumny - 1)) / kolumny
    story: list[Flowable] = []
    indeks_naglowka = 0
    for i, (rodzaj, ob) in enumerate(elementy):
        if rodzaj in ("p", "m"):
            znaczniki: list[Flowable] = []
            dodatek = ""
            for r, e in doczepy.get(i, []):
                if r == "przypis":
                    znak, zn = _przypis(ctx, e)
                    dodatek += znak
                else:
                    zn = _komentarz(ctx, e)
                znaczniki.append(zn)
            if kolumny > 1:      # akapit (a z nim wartość) nie dzieli się między kolumny
                story.append(KeepTogether([_akapit(ctx, ob, dodatek), *znaczniki]))  # type: ignore[arg-type]
            else:
                story.append(_akapit(ctx, ob, dodatek))  # type: ignore[arg-type]
                story += znaczniki
        elif rodzaj == "n":
            story.append(_akapit_listu(ctx, ob, True, indeks_naglowka))  # type: ignore[arg-type]
            indeks_naglowka += 1
        elif rodzaj == "s":
            story.append(_akapit_listu(ctx, ob, False, 0))  # type: ignore[arg-type]
        elif rodzaj == "t":
            story += [_tabela(ctx, tabele[ob], szer_kolumny), Spacer(1, 8)]  # type: ignore[index]
        elif rodzaj == "pole":
            story.append(_pole(ctx, ob))  # type: ignore[arg-type]
        elif rodzaj == "sig":
            story += _podpis(ctx, ob)  # type: ignore[arg-type]
    if not story:
        story.append(Spacer(1, 1))

    bufor = io.BytesIO()
    doc = BaseDocTemplate(bufor, pagesize=A4, invariant=1, pageCompression=1, title="", author="", subject="",
                          creator="", producer="", leftMargin=MARGINES, rightMargin=MARGINES)
    ramki = [Frame(MARGINES + k * (szer_kolumny + ODSTEP_KOLUMN), uklad.dol, szer_kolumny, WYS - uklad.gora - uklad.dol,
                   leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id="glowna" if k == 0 else f"kolumna{k + 1}")
             for k in range(kolumny)]
    doc.addPageTemplates([PageTemplate("strona", ramki, onPage=uklad.strona, onPageEnd=uklad.koniec_strony)])
    with bez_a85():                    # strumienie bez ASCII85 – bajty niezależne od flag ustawionych w procesie
        doc.build(story)
    ctx.wynik.strony = doc.page
    if geometria:
        ctx.wynik.ramki = ctx.ramki()
    ctx.wynik.rezerwy = dict(rezerwy)
    return bufor.getvalue(), ctx


# ----------------------------------------------------------------------------- metadane i adnotacje (pikepdf)
def _data_pdf(t: dt.datetime) -> str:
    return t.strftime("D:%Y%m%d%H%M%S+00'00'")


def _xmp(autor: str, tytul: str, temat: str, dodatkowe: dict[str, str], utworzono: dt.datetime,
         zmieniono: dt.datetime, narzedzie: str) -> bytes:
    def alt(wartosc: str) -> str:
        return f'<rdf:Alt><rdf:li xml:lang="x-default">{escape(wartosc)}</rdf:li></rdf:Alt>'

    wlasne = "".join(f"<pdfx:{_nazwa_xml(k)}>{escape(v)}</pdfx:{_nazwa_xml(k)}>" for k, v in sorted(dodatkowe.items()))
    opis = (f'<rdf:Description rdf:about="" xmlns:dc="http://purl.org/dc/elements/1.1/" '
            f'xmlns:xmp="http://ns.adobe.com/xap/1.0/" xmlns:pdf="http://ns.adobe.com/pdf/1.3/" '
            f'xmlns:pdfx="http://ns.adobe.com/pdfx/1.3/">'
            + (f"<dc:creator><rdf:Seq><rdf:li>{escape(autor)}</rdf:li></rdf:Seq></dc:creator>" if autor else "")
            + (f"<dc:title>{alt(tytul)}</dc:title>" if tytul else "")
            + (f"<dc:description>{alt(temat)}</dc:description>" if temat else "")
            + f"<xmp:CreatorTool>{escape(narzedzie)}</xmp:CreatorTool>"
              f"<xmp:CreateDate>{utworzono.isoformat()}Z</xmp:CreateDate>"
              f"<xmp:ModifyDate>{zmieniono.isoformat()}Z</xmp:ModifyDate>"
              f"<pdf:Producer>{escape(narzedzie)}</pdf:Producer>{wlasne}</rdf:Description>")
    xml = ('<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>'
           '<x:xmpmeta xmlns:x="adobe:ns:meta/"><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
           f'{opis}</rdf:RDF></x:xmpmeta><?xpacket end="w"?>')
    return xml.encode("utf-8")


def _nazwa_xml(klucz: str) -> str:
    nazwa = "".join(x.capitalize() for x in re.split(r"\W+", klucz) if x)
    return nazwa if nazwa and nazwa[0].isalpha() else f"K{nazwa}"


def zapisz_metadane(pdf: pikepdf.Pdf, info: dict[str, str], xmp: bytes) -> None:
    """Zastępuje `/Info` i XMP dokumentu (wartości Unicode zapisuje pikepdf jako UTF-16BE)."""
    pdf.trailer["/Info"] = pdf.make_indirect(pikepdf.Dictionary({"/" + k: pikepdf.String(v)
                                                                  for k, v in info.items()}))
    strumien = pdf.make_stream(xmp)
    strumien.Type = pikepdf.Name.Metadata
    strumien.Subtype = pikepdf.Name.XML
    pdf.Root.Metadata = strumien


def _czcionka_formularza(pdf: pikepdf.Pdf, znaki: set[str]) -> pikepdf.Object:
    """Pełna czcionka DejaVu Sans (Type0, Identity-H) do wyglądu pól – znaki diakrytyczne zostają w `/AP`."""
    face = pdfmetrics.getFont("DejaVuSans").face
    dane = Path(f"{FONTY}/DejaVuSans.ttf").read_bytes()
    plik = pdf.make_stream(dane)
    plik.Length1 = len(dane)
    jednostka = 1000 / face.unitsPerEm
    szerokosci = pikepdf.Array()
    for gid in sorted({face.charToGlyph.get(ord(c), 0) for c in znaki}):
        szerokosci.append(gid)
        szerokosci.append(pikepdf.Array([round(face.hmetrics[gid][0] * jednostka)]))
    opis = pikepdf.Dictionary(Type=pikepdf.Name.FontDescriptor, FontName=pikepdf.Name.DejaVuSans, Flags=32,
                              FontBBox=[round(v * jednostka) for v in face.bbox], ItalicAngle=0,
                              Ascent=round(face.ascent * jednostka), Descent=round(face.descent * jednostka),
                              CapHeight=round(face.capHeight * jednostka), StemV=87, FontFile2=plik)
    cid = pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.CIDFontType2,
                             BaseFont=pikepdf.Name.DejaVuSans, FontDescriptor=opis, CIDToGIDMap=pikepdf.Name.Identity,
                             DW=600, W=szerokosci,
                             CIDSystemInfo=pikepdf.Dictionary(Registry=pikepdf.String("Adobe"),
                                                              Ordering=pikepdf.String("Identity"), Supplement=0))
    return pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.Font, Subtype=pikepdf.Name.Type0,
                                                BaseFont=pikepdf.Name.DejaVuSans, Encoding=pikepdf.Name("/Identity-H"),
                                                DescendantFonts=pikepdf.Array([cid])))


def _wypelnij_pole(pdf: pikepdf.Pdf, a: pikepdf.Dictionary, wartosc: str, czcionka: pikepdf.Object) -> None:
    """`/V` = `/DV` = wartość, wygląd `/AP` z czcionką DejaVu (znaki diakrytyczne widoczne tak jak w `/V`)."""
    face = pdfmetrics.getFont("DejaVuSans").face
    x0, y0, x1, y1 = (float(v) for v in a.Rect)
    w, h = x1 - x0, y1 - y0
    hex_ = "".join(f"{face.charToGlyph.get(ord(c), 0):04X}" for c in wartosc)
    tresc = (f"q 1 g 0 0 {w:.2f} {h:.2f} re f 0 G 0.5 w 0.25 0.25 {w - 0.5:.2f} {h - 0.5:.2f} re S Q "
             f"/Tx BMC q BT /F0 9 Tf 0 g 3 {(h - 9) / 2 + 2:.2f} Td <{hex_}> Tj ET Q EMC").encode("ascii")
    ap = pdf.make_stream(tresc)
    ap.Type, ap.Subtype = pikepdf.Name.XObject, pikepdf.Name.Form
    ap.BBox = [0, 0, w, h]
    ap.Resources = pikepdf.Dictionary(Font=pikepdf.Dictionary(F0=czcionka))
    a.AP = pikepdf.Dictionary(N=ap)
    a.DA = pikepdf.String("/F0 9 Tf 0 g")
    a.V = pikepdf.String(wartosc)
    a.DV = pikepdf.String(wartosc)


def _dokoncz(bajty: bytes, ctx: _Ctx) -> bytes:
    """Podmienia znaczniki adnotacji i pól na wartości Unicode, zapisuje `/Info` i XMP; deterministyczny zapis."""
    wl = dict(ctx.wlasciwosci)
    autor = wl.pop("author", NEUTRALNY_AUTOR.get(ctx.d.jezyk, "User"))
    tytul, temat = wl.pop("title", ""), wl.pop("subject", "")
    utworzono = ctx.data_iso()
    zmieniono = utworzono + dt.timedelta(days=ctx.rng.randint(0, 40), minutes=ctx.rng.randint(1, 600))
    narzedzie = "Writer"
    info = {"Author": autor, "Title": tytul, "Subject": temat, "Creator": narzedzie, "Producer": narzedzie,
            "CreationDate": _data_pdf(utworzono), "ModDate": _data_pdf(zmieniono)}
    for k, v in sorted(wl.items()):
        info[_nazwa_xml(k)] = v
    with pikepdf.open(io.BytesIO(bajty)) as pdf:
        pola = dict(ctx.pola)
        czcionka = _czcionka_formularza(pdf, {c for _, v in ctx.pola for c in v}) if pola else None
        for strona in pdf.pages:
            for a in strona.get("/Annots", []):
                if a.get("/Subtype") == "/Text":
                    m = re.fullmatch(r"@@C(\d+)@@", str(a.Contents))
                    nr = int(m.group(1))
                    a.T = pikepdf.String(ctx.komentarze[nr][0])
                    a.Contents = pikepdf.String(ctx.komentarze[nr][1])
                    a.Subtype = pikepdf.Name.Text
                    a.Name = pikepdf.Name.Comment
                elif a.get("/Subtype") == "/Widget":
                    _wypelnij_pole(pdf, a, pola[str(a.T)], czcionka)
        if czcionka is not None:
            pdf.Root.AcroForm.DR = pikepdf.Dictionary(Font=pikepdf.Dictionary(F0=czcionka))
            pdf.Root.AcroForm.DA = pikepdf.String("/F0 9 Tf 0 g")
        zapisz_metadane(pdf, info, _xmp(autor, tytul, temat, wl, utworzono, zmieniono, narzedzie))
        wyjscie = io.BytesIO()
        pdf.save(wyjscie, deterministic_id=True, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.disable)
    return wyjscie.getvalue()


def zbuduj_pdf(d: Dokument, utrudnienia: set[str], geometria: bool = False,
               kolumny: int = 1) -> tuple[bytes, WynikPdf]:
    """PDF jako bajty i `WynikPdf`; powtarza przebieg, aż rezerwy miejsca na przypisy wystarczą na każdej stronie.
    `kolumny` > 1: tekst w kolumnach (warstwa trudnych przypadków; akapity nie dzielą się między kolumny)."""
    nieznane = set(utrudnienia) - UTRUDNIENIA_PDF - UTRUDNIENIA_POMINIETE
    if nieznane:
        raise ValueError(f"nieznane utrudnienia PDF: {sorted(nieznane)}")
    if any(e.rodzaj == "zmiany" for e in d.elementy):
        raise ValueError("zmiany śledzone nie występują w PDF – przytnij dokument przez `przytnij_pdf`")
    rezerwy: dict[int, float] = {}
    for _ in range(MAX_PRZEBIEGOW):
        bajty, ctx = _przebieg(d, set(utrudnienia), rezerwy, geometria, kolumny)
        if all(h <= rezerwy.get(p, 0.0) + 0.01 for p, h in ctx.potrzebne.items()):
            break
        rezerwy = {**rezerwy, **{p: max(h, rezerwy.get(p, 0.0)) for p, h in ctx.potrzebne.items()}}
    return _dokoncz(bajty, ctx), ctx.wynik


def renderuj_pdf(d: Dokument, plik: Path, utrudnienia: set[str], kolumny: int = 1) -> WynikPdf:
    """Zapisuje `d` jako PDF w `plik`; zwraca umieszczone wartości i obrazy z gold (zob. docstring modułu)."""
    bajty, wynik = zbuduj_pdf(d, utrudnienia, kolumny=kolumny)
    plik = Path(plik)
    plik.parent.mkdir(parents=True, exist_ok=True)
    plik.write_bytes(bajty)
    return wynik


def render_pdf(d: Dokument, plik: Path, utrudnienia: set[str]) -> list[Wartosc]:
    """Jak `renderuj_pdf`, ale zwraca tylko listę umieszczonych wartości (z `miejsce`, w tym `obraz`)."""
    return renderuj_pdf(d, plik, utrudnienia).wartosci
