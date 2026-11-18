"""Operacje na gotowych plikach PDF warstwy trudnych przypadków H4a (pikepdf + reportlab): zepsuta mapa ToUnicode,
obrócone strony (`/Rotate`) i skany obrócone fizycznie, strony dopisywane na końcu (załącznik z obrazem, aneks), znak
wodny nakładany na każdą stronę. Zapis deterministyczny (stałe `/ID`, bez strumieni obiektów), jak renderer PDF.
Renderer (`pbench.render.pdf`) importujemy dla rejestracji czcionek DejaVu w reportlabie."""
from __future__ import annotations

import io
import math
import re
import zlib
from pathlib import Path

import pikepdf
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .render import bez_a85
from .render import pdf as _render_pdf  # noqa: F401 - rejestruje czcionki DejaVu
from .render.pdf import MARGINES, SZER

#: Tryby zepsutej mapy ToUnicode: kody -> znaki z obszaru prywatnego (śmieci), kody -> znak o 1 dalej (wiarygodnie wyglądający
#: bełkot), brak mapy (przeglądarka zgaduje z kodowania: znaki spoza ASCII stają się kodami sterującymi).
TRYBY_TOUNICODE = ("pua", "przesuniecie", "usuniete")
_BFCHAR = re.compile(r"<([0-9A-Fa-f]{2,4})>\s*<([0-9A-Fa-f]{4})>")


def zapisz(pdf: pikepdf.Pdf) -> bytes:
    wyjscie = io.BytesIO()
    pdf.save(wyjscie, deterministic_id=True, compress_streams=True, object_stream_mode=pikepdf.ObjectStreamMode.disable)
    return wyjscie.getvalue()


def _czcionki_stron(pdf: pikepdf.Pdf) -> list[pikepdf.Object]:
    wynik, widziane = [], set()
    for strona in pdf.pages:
        fonty = strona.get("/Resources", {}).get("/Font", {})
        for _, f in fonty.items():
            if f.objgen not in widziane:
                widziane.add(f.objgen)
                wynik.append(f)
    return wynik


def zepsuj_tounicode(plik: Path, tryb: str) -> int:
    """Psuje mapy ToUnicode wszystkich czcionek stron (tekst wygląda poprawnie, kopiowanie daje śmieci); zwraca liczbę
    zmienionych czcionek. Rysowanie (kody znaków i glify) bez zmian."""
    if tryb not in TRYBY_TOUNICODE:
        raise ValueError(f"nieznany tryb zepsucia ToUnicode: {tryb!r}")
    plik = Path(plik)
    zmienione = 0
    with pikepdf.open(plik) as pdf:
        for f in _czcionki_stron(pdf):
            if "/ToUnicode" not in f:
                continue
            if tryb == "usuniete":
                del f["/ToUnicode"]
            else:
                cmap = f.ToUnicode.read_bytes().decode("latin-1")

                def zamien(m: re.Match[str]) -> str:
                    kod, znak = m.group(1), int(m.group(2), 16)
                    if znak == 0:
                        return m.group(0)
                    nowy = 0xE000 + int(kod, 16) if tryb == "pua" else znak + 1
                    return f"<{kod}> <{nowy:04X}>"
                f.ToUnicode = pdf.make_stream(_BFCHAR.sub(zamien, cmap).encode("latin-1"))
            zmienione += 1
        plik.write_bytes(zapisz(pdf))
    return zmienione


def obroc_strony(plik: Path, katy: list[int]) -> None:
    """Ustawia `/Rotate` stron (kąt wg listy, powtarzany cyklicznie); treść strony bez zmian."""
    plik = Path(plik)
    with pikepdf.open(plik) as pdf:
        for i, strona in enumerate(pdf.pages):
            strona.Rotate = katy[i % len(katy)]
        plik.write_bytes(zapisz(pdf))


def _punkt_po_obrocie(x: float, y: float, kat: int, szer: int, wys: int) -> tuple[float, float]:
    """Piksel (x, y) obrazu `szer` x `wys` po obrocie o `kat` stopni przeciwnie do ruchu wskazówek zegara (90/180/270)."""
    if kat == 90:
        return y, szer - x
    if kat == 180:
        return szer - x, wys - y
    if kat == 270:
        return wys - y, x
    return x, y


def obroc_skan(plik: Path, katy: list[int], gold_obrazy: list[dict]) -> list[dict]:
    """Skan obrócony fizycznie: obraz każdej strony jest obracany (90/180/270 stopni przeciwnie do ruchu wskazówek zegara,
    wg `katy` cyklicznie), strona o obróconym rozmiarze (dla 90/270 pozioma), `/Rotate` bez zmian – tak wygląda skan włożony
    do podajnika bokiem. Zwraca `gold_obrazy` z ramkami przeliczonymi na obrócone piksele."""
    plik = Path(plik)
    wynik = [dict(o) for o in gold_obrazy]
    with pikepdf.open(plik) as pdf:
        for i, strona in enumerate(pdf.pages):
            kat = katy[i % len(katy)]
            if not kat:
                continue
            nazwa, obraz = next((n, o) for n, o in strona.Resources.XObject.items() if o.get("/Subtype") == "/Image")
            with Image.open(io.BytesIO(obraz.read_raw_bytes())) as im:
                im.load()
                szer, wys = im.size
                obrocony = im.transpose({90: Image.ROTATE_90, 180: Image.ROTATE_180, 270: Image.ROTATE_270}[kat])
            bufor = io.BytesIO()
            obrocony.save(bufor, format="JPEG", quality=75)
            obraz.write(bufor.getvalue(), filter=pikepdf.Name.DCTDecode)
            obraz.Width, obraz.Height = obrocony.size
            a, b = float(strona.MediaBox[2]), float(strona.MediaBox[3])
            nowa = (b, a) if kat in (90, 270) else (a, b)
            strona.MediaBox = [0, 0, nowa[0], nowa[1]]
            if "/CropBox" in strona:
                del strona["/CropBox"]
            strona.Contents = pdf.make_stream(f"q {nowa[0]:.2f} 0 0 {nowa[1]:.2f} 0 0 cm {nazwa} Do Q".encode("ascii"))
            for o in wynik:
                if o.get("strona") == i + 1:
                    ramki = []
                    for wid, (x0, y0, x1, y1) in o["ramki"]:
                        rogi = [_punkt_po_obrocie(x, y, kat, szer, wys) for x in (x0, x1) for y in (y0, y1)]
                        xs, ys = [r[0] for r in rogi], [r[1] for r in rogi]
                        ramki.append([wid, [round(min(xs)), round(min(ys)), round(max(xs)), round(max(ys))]])
                    o["ramki"] = ramki
        plik.write_bytes(zapisz(pdf))
    return wynik


def dolacz_strony(plik: Path, strony: bytes) -> int:
    """Dopisuje strony z PDF `strony` na końcu `plik`; zwraca numer (od 1) pierwszej dopisanej strony."""
    plik = Path(plik)
    with pikepdf.open(plik) as pdf, pikepdf.open(io.BytesIO(strony)) as src:
        pierwsza = len(pdf.pages) + 1
        pdf.pages.extend(src.pages)
        plik.write_bytes(zapisz(pdf))
    return pierwsza


def nowy_canvas() -> tuple[io.BytesIO, canvas.Canvas]:
    bufor = io.BytesIO()
    return bufor, canvas.Canvas(bufor, pagesize=A4, invariant=1, pageCompression=1)


def strona_zalacznika(tytul: str, png: bytes, szer_pt: float = SZER - 2 * MARGINES) -> tuple[bytes, tuple[float, float, float, float]]:
    """Strona A4: tytuł i obraz pod nim (szerokość `szer_pt`, proporcje zachowane). Zwraca (PDF, prostokąt obrazu w pt od
    lewego dolnego rogu: x, y, szerokość, wysokość)."""
    with bez_a85():
        bufor, c = nowy_canvas()
        wys_strony = A4[1]
        c.setFont("DejaVuSerif-Bold", 13)
        c.drawString(MARGINES, wys_strony - 90, tytul)
        czytnik = ImageReader(io.BytesIO(png))
        iw, ih = czytnik.getSize()
        szer = min(szer_pt, SZER - 2 * MARGINES)
        wys = szer * ih / iw
        x, y = MARGINES, wys_strony - 120 - wys
        c.drawImage(czytnik, x, y, szer, wys)
        c.showPage()
        c.save()
    return bufor.getvalue(), (x, y, szer, wys)


def naloz_znak_wodny(plik: Path, png: bytes, kat: float = 35.0, alfa: float = 0.3,
                     szer_pt: float = 430.0) -> list[tuple[int, tuple[float, float, float, float]]]:
    """Nakłada obraz (poziomy napis, PNG; kanał alfa spłaszczony na biel) na KAŻDĄ stronę pod kątem `kat` stopni,
    półprzezroczysty (`alfa`, mieszanie `Multiply`, więc biel obrazu jest niewidoczna), środkiem strony. Obraz jest osadzony
    RAZ (jeden obiekt na cały plik) i poziomy – OCR czyta go bez obracania; ukośnie ustawia go macierz strony. Zwraca (numer
    strony, obwiednia obróconego obrazu w pt) dla każdej strony."""
    plik = Path(plik)
    with Image.open(io.BytesIO(png)) as im:
        rgba = im.convert("RGBA")
        tlo = Image.new("RGB", rgba.size, "white")
        tlo.paste(rgba, mask=rgba.getchannel("A"))
    iw, ih = tlo.size
    wys = szer_pt * ih / iw
    t = math.radians(kat)
    c, s_ = math.cos(t), math.sin(t)
    polozenia = []
    with pikepdf.open(plik) as pdf:
        obraz = pdf.make_stream(zlib.compress(tlo.tobytes()))
        obraz.Type, obraz.Subtype = pikepdf.Name.XObject, pikepdf.Name.Image
        obraz.Width, obraz.Height, obraz.BitsPerComponent = iw, ih, 8
        obraz.ColorSpace, obraz.Filter = pikepdf.Name.DeviceRGB, pikepdf.Name.FlateDecode
        stan = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.ExtGState, ca=alfa, BM=pikepdf.Name.Multiply))
        for i, strona in enumerate(pdf.pages):
            a, b = float(strona.MediaBox[2]), float(strona.MediaBox[3])
            zasoby = strona.Resources
            for rodzaj, nazwa, obiekt in (("/XObject", "/PbZnak", obraz), ("/ExtGState", "/PbZnakGs", stan)):
                if rodzaj not in zasoby:
                    zasoby[rodzaj] = pikepdf.Dictionary()
                zasoby[rodzaj][nazwa] = obiekt
            ox = a / 2 - (szer_pt * c - wys * s_) / 2
            oy = b / 2 - (szer_pt * s_ + wys * c) / 2
            strona.contents_add(pdf.make_stream(b"q\n"), prepend=True)       # stan grafiki treści strony nie może wyciec
            strona.contents_add(pdf.make_stream(
                (f"Q\nq /PbZnakGs gs {szer_pt * c:.4f} {szer_pt * s_:.4f} {-wys * s_:.4f} {wys * c:.4f} {ox:.2f} {oy:.2f} cm "
                 "/PbZnak Do Q\n").encode("ascii")), prepend=False)
            polowa_x = (szer_pt * abs(c) + wys * abs(s_)) / 2
            polowa_y = (szer_pt * abs(s_) + wys * abs(c)) / 2
            polozenia.append((i + 1, (a / 2 - polowa_x, b / 2 - polowa_y, a / 2 + polowa_x, b / 2 + polowa_y)))
        plik.write_bytes(zapisz(pdf))
    return polozenia
