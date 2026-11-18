"""Fikcyjne logo kancelarii: abstrakcyjny kształt + nazwa firmy jako tekst na obrazie.

Wyłącznie rysunek własny (formy geometryczne i krój DejaVu Sans Bold z systemu) – bez znaków towarowych.
Nazwa firmy na obrazie jest wartością wzorcową poziomu obrazów (miejsce „obraz”), dlatego razem z obrazem
zwracamy ramkę tekstu (piksele obrazu).
"""
from __future__ import annotations

import random
import textwrap

from PIL import Image, ImageDraw, ImageFont

CZCIONKA = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
#: Palety (ciemny, jasny) – stonowane barwy kancelaryjne.
PALETY: tuple[tuple[str, str], ...] = (("#1F3864", "#8FAADC"), ("#7B1E1E", "#E0A8A8"), ("#1E5B3A", "#9FD4B3"),
                                       ("#3B2F63", "#B9AEE0"), ("#2F4F4F", "#A9C7C7"))
WYSOKOSC = 140
MAX_ZNAKOW_LINII = 24


def _ksztalt(rys: ImageDraw.ImageDraw, rng: random.Random, ciemny: str, jasny: str, rozmiar: int) -> None:
    wariant = rng.randrange(4)
    p = 10
    if wariant == 0:  # dwa przesunięte kwadraty
        rys.rectangle((p, p, rozmiar - 30, rozmiar - 30), fill=jasny)
        rys.rectangle((p + 22, p + 22, rozmiar - p, rozmiar - p), fill=ciemny)
    elif wariant == 1:  # koło z pierścieniem
        rys.ellipse((p, p, rozmiar - p, rozmiar - p), fill=ciemny)
        rys.ellipse((p + 28, p + 28, rozmiar - p - 28, rozmiar - p - 28), fill=jasny)
    elif wariant == 2:  # trójkąty
        rys.polygon([(p, rozmiar - p), (rozmiar // 2, p), (rozmiar - p, rozmiar - p)], fill=ciemny)
        rys.polygon([(p + 30, rozmiar - p), (rozmiar // 2, p + 40), (rozmiar - p - 30, rozmiar - p)], fill=jasny)
    else:  # trzy pionowe słupy (kolumny)
        szer = (rozmiar - 2 * p) // 5
        for i in range(3):
            x = p + i * 2 * szer
            rys.rectangle((x, p, x + szer, rozmiar - p), fill=ciemny if i != 1 else jasny)


def generuj_z_ramka(firma: str, rng: random.Random) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """Logo i ramka tekstu nazwy (x0, y0, x1, y1) w pikselach obrazu; deterministyczne dla ziarna `rng`."""
    ciemny, jasny = PALETY[rng.randrange(len(PALETY))]
    czcionka = ImageFont.truetype(CZCIONKA, 32)
    linie = textwrap.wrap(firma, MAX_ZNAKOW_LINII, break_long_words=False) or [firma]
    tekst = "\n".join(linie)
    miara = Image.new("RGB", (4, 4))
    bb = ImageDraw.Draw(miara).multiline_textbbox((0, 0), tekst, font=czcionka, spacing=8)
    szer_tekstu, wys_tekstu = bb[2] - bb[0], bb[3] - bb[1]
    ksztalt = WYSOKOSC
    obraz = Image.new("RGB", (ksztalt + 24 + szer_tekstu + 20, WYSOKOSC), "white")
    rys = ImageDraw.Draw(obraz)
    _ksztalt(rys, rng, ciemny, jasny, ksztalt)
    x0, y0 = ksztalt + 24, (WYSOKOSC - wys_tekstu) // 2
    rys.multiline_text((x0 - bb[0], y0 - bb[1]), tekst, font=czcionka, fill=ciemny, spacing=8)
    return obraz, (x0, y0, x0 + szer_tekstu, y0 + wys_tekstu)


def generuj(firma: str, rng: random.Random) -> Image.Image:
    """Fikcyjne logo z nazwą firmy jako tekstem (bez ramki; zob. `generuj_z_ramka`)."""
    return generuj_z_ramka(firma, rng)[0]
