"""Obraz odręcznego podpisu: imię i nazwisko skryptową czcionką URW Z003 (system, nie jest redystrybuowana)."""
from __future__ import annotations

import random

from PIL import Image, ImageDraw, ImageFont

CZCIONKA = "/usr/share/fonts/opentype/urw-base35/Z003-MediumItalic.otf"
#: Z003 nie ma cyrylicy – podpisy z cyrylicą rysujemy kursywą Liberation Serif (pełna cyrylica, w tym litery ukraińskie)
CZCIONKA_CYRYLICA = "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf"
KOLORY = ((20, 40, 140), (10, 10, 60), (30, 30, 30))


def generuj(imie_nazwisko: str, rng: random.Random) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """Podpis (RGBA, przezroczyste tło) i ramka napisu (piksele obrazu); lekki obrót i podkreślenie jak z długopisu."""
    cyrylica = any("\u0400" <= c <= "\u04ff" for c in imie_nazwisko)
    czcionka = ImageFont.truetype(CZCIONKA_CYRYLICA if cyrylica else CZCIONKA, rng.choice((72, 80, 88)))
    kolor = KOLORY[rng.randrange(len(KOLORY))]
    miara = ImageDraw.Draw(Image.new("L", (4, 4)))
    bb = miara.textbbox((0, 0), imie_nazwisko, font=czcionka)
    szer, wys = bb[2] - bb[0] + 60, bb[3] - bb[1] + 60
    plotno = Image.new("RGBA", (szer, wys), (0, 0, 0, 0))
    rys = ImageDraw.Draw(plotno)
    rys.text((30 - bb[0], 30 - bb[1]), imie_nazwisko, font=czcionka, fill=kolor + (255,))
    y = wys - 22 + rng.randrange(-4, 5)
    rys.line((30, y, szer - 30, y - rng.randrange(0, 14)), fill=kolor + (255,), width=3)
    obraz = plotno.rotate(rng.uniform(-4, 4), resample=Image.BICUBIC, expand=True)
    ramka = obraz.getchannel("A").getbbox()
    # ramka tekstu = ramka wszystkich zamalowanych pikseli (napis + podkreślenie)
    return obraz, tuple(ramka)  # type: ignore[return-value]
