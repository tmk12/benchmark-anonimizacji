"""Wstrzykiwanie treści ukrytej do PDF (warstwa trudnych przypadków H4a, spec §11 pkt 1 – część PDF).

Dopisuje na końcu pliku wyrenderowanego przez `render.pdf` dwa rodzaje stron z `Dokument.ukryte` (rodzaje `pdf.*`):

* `pdf.zaczernienie` – aneks, w którym czarny prostokąt jest narysowany NAD tekstem wartości, a tekst pod spodem zostaje
  w strumieniu treści strony (do zaznaczenia i skopiowania) – klasyczne błędne „zaczernienie” bez usunięcia tekstu;
* `pdf.warstwa_ocr` – skan strony (obraz z pustymi polami formularza) z niewidoczną warstwą tekstową (tryb renderowania 3,
  jak warstwa OCR), w której stoją dane NIEOBECNE na obrazie (inne niż to, co widać).

Mapowanie element -> miejsce gold: `metodyka/miejsca-ukryte.md` (oba: `metadane` – niewidoczne dla czytelnika).
Linie elementu rozdziela `ROZDZIELACZ`; w linii napisy to etykieta, a `Wartosc` – wartość.
"""
from __future__ import annotations

import io
import random
import zlib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics

from .model import Element, Wartosc
from .obrazy_trudne import FONT
from .pliki_pdf import bez_a85, dolacz_strony, nowy_canvas
from .render.pdf import MARGINES
from .ukryta_pakiet import ROZDZIELACZ

SZER_OBRAZU_PX = 900
SZER_OBRAZU_PT = 470.0


def linie(e: Element) -> list[tuple[str, str]]:
    """Linie elementu jako (etykieta, wartość): napisy to etykieta, `Wartosc` – wartość (jedna na linię)."""
    wynik: list[tuple[str, str]] = []
    etykieta, wartosc = "", ""
    for f in e.fragmenty:
        if f == ROZDZIELACZ:
            wynik.append((etykieta, wartosc))
            etykieta, wartosc = "", ""
        elif isinstance(f, Wartosc):
            wartosc += f.tekst
        else:
            etykieta += f
    wynik.append((etykieta, wartosc))
    return wynik


def _zaczernienia(c, elementy: list[Element], tytul: str, y: float) -> None:
    c.setFont("DejaVuSerif-Bold", 13)
    c.drawString(MARGINES, y, tytul)
    y -= 36
    for e in elementy:
        for etykieta, wartosc in linie(e):
            if y < MARGINES + 20:                                         # koniec strony: dalsze linie na następnej
                c.showPage()
                y = A4[1] - 90
            c.setFont("DejaVuSerif", 10.5)
            c.setFillGray(0)
            c.drawString(MARGINES, y, etykieta)
            x = MARGINES + pdfmetrics.stringWidth(etykieta, "DejaVuSerif", 10.5)
            c.drawString(x, y, wartosc)                                   # tekst zostaje w strumieniu treści…
            szer = pdfmetrics.stringWidth(wartosc, "DejaVuSerif", 10.5)
            c.rect(x - 2, y - 3, szer + 4, 14, fill=1, stroke=0)          # …a czarny prostokąt leży NAD nim
            y -= 24
        y -= 18


def _formularz(e: Element, rng: random.Random) -> tuple[bytes, list[tuple[float, float]]]:
    """Obraz skanu: etykiety pól i puste linie na wartości; zwraca (JPEG, położenie początku pola w pikselach: x, y linii
    bazowej) dla każdej linii elementu."""
    etykiety = [et for et, _ in linie(e)]
    f = ImageFont.truetype(FONT, 30)
    wys = 130 + 100 * len(etykiety)
    obraz = Image.new("L", (SZER_OBRAZU_PX, wys), 250)
    rys = ImageDraw.Draw(obraz)
    polozenia = []
    for i, et in enumerate(etykiety):
        y = 90 + 100 * i
        rys.text((40, y), et, font=f, fill=25)
        x = 40 + int(rys.textlength(et, font=f)) + 8
        rys.line((x, y + 40, SZER_OBRAZU_PX - 40, y + 40), fill=60, width=2)
        polozenia.append((float(x + 6), float(y + 34)))
    for _ in range(900):                                                  # ziarno skanera
        x, y = rng.randrange(SZER_OBRAZU_PX), rng.randrange(wys)
        rys.point((x, y), fill=rng.randrange(150, 235))
    obraz = obraz.filter(ImageFilter.GaussianBlur(0.6))
    bufor = io.BytesIO()
    obraz.save(bufor, format="JPEG", quality=80)
    return bufor.getvalue(), polozenia


def _warstwa_ocr(c, e: Element, tytul: str, rng: random.Random) -> None:
    c.setFont("DejaVuSerif-Bold", 13)
    c.setFillGray(0)
    c.drawString(MARGINES, A4[1] - 90, tytul)
    jpeg, polozenia = _formularz(e, rng)
    skala = SZER_OBRAZU_PT / SZER_OBRAZU_PX
    wys_pt = Image.open(io.BytesIO(jpeg)).height * skala
    y0 = A4[1] - 120 - wys_pt
    c.drawImage(ImageReader(io.BytesIO(jpeg)), MARGINES, y0, SZER_OBRAZU_PT, wys_pt)
    for (x, y), (_, wartosc) in zip(polozenia, linie(e)):
        t = c.beginText(MARGINES + x * skala, y0 + wys_pt - y * skala)
        t.setFont("DejaVuSans", 11)
        t.setTextRenderMode(3)                                            # niewidoczny, jak warstwa OCR
        t.textOut(wartosc)
        c.drawText(t)


def wstrzyknij_pdf(plik: Path, elementy: list[Element], ziarno: str = "") -> None:
    """Dopisuje strony elementów `pdf.*` na końcu `plik` (nadpisuje go, deterministycznie). `ziarno` (np. id dokumentu) różnicuje
    szum skanu między dokumentami."""
    zaczernione = [e for e in elementy if e.rodzaj == "pdf.zaczernienie"]
    ocr = [e for e in elementy if e.rodzaj == "pdf.warstwa_ocr"]
    nieznane = [e.rodzaj for e in elementy if e.rodzaj not in ("pdf.zaczernienie", "pdf.warstwa_ocr")]
    if nieznane:
        raise ValueError(f"treść ukryta PDF: nieznane rodzaje {nieznane}")
    with bez_a85():
        bufor, c = nowy_canvas()
        if zaczernione:
            _zaczernienia(c, zaczernione, zaczernione[0].atrybuty["tytul"], A4[1] - 90)
            c.showPage()
        for e in ocr:
            _warstwa_ocr(c, e, e.atrybuty["tytul"], random.Random(zlib.crc32(f"{ziarno}|{e.atrybuty['tytul']}".encode()) ^ 0x0C12))
            c.showPage()
        c.save()
    dolacz_strony(plik, bufor.getvalue())
