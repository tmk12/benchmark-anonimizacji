"""Skan: PDF z tekstem -> obrazy 200 dpi -> szum, obrót, niejednorodna jasność, JPEG -> PDF bez warstwy tekstu.

Skan niesie tylko to, co widać na kartce: obsługuje `UTRUDNIENIA_SKAN` (papier firmowy, tabele, przypisy, podpis);
komentarze, pola i metadane nie mają w skanie odpowiednika, więc `renderuj_skan` sam przycina dokument
(`utrudnienia.przytnij`) do tych utrudnień. Wszystkie wartości skanu mają `miejsce="obraz"`, a dla każdej strony
powstaje `Obraz` (bez PNG – stroną jest JPEG w pliku) z ramkami wartości w pikselach strony (200 dpi, po obrocie).

Ramki: tekst PDF jest najpierw układany jak zwykły PDF (`pbench.render.pdf`, tryb geometrii), a pozycje słów każdej
wartości zapisują znaczniki `<onDraw>` w chwili rysowania (współrzędne bezwzględne w pt) – zwykły tekst o tym samym
brzmieniu ani podciąg dłuższego słowa nie zajmują cudzej ramki. Ramki przechodzą tę samą transformację obrotu co obraz;
wartość złamana między wierszami ma po jednej ramce na wiersz. W trybie geometrii akapity nie są justowane.
Metadane skanu są neutralne („Scanner”, data) – bez danych osobowych.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import io
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pikepdf
import pypdfium2 as pdfium
from PIL import Image, ImageFilter
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from ..model import Dokument, Obraz, Wartosc
from ..utrudnienia import UTRUDNIENIA_POMINIETE, przytnij
from . import bez_a85
from .pdf import _data_pdf, _xmp, zapisz_metadane, zbuduj_pdf

#: Utrudnienia, które mają widoczny odpowiednik na zeskanowanej kartce.
UTRUDNIENIA_SKAN: frozenset[str] = frozenset({"papier_firmowy", "tabele", "przypisy", "podpis"})
DPI = 200
SKALA = DPI / 72
MAX_OBROT = 1.5
JAKOSC_JPEG = 75
#: Margines ramki w pikselach (rozmycie i obrót nie powinny obcinać liter).
LUZ_RAMKI = 1


@dataclass
class WynikSkan:
    """Wynik renderowania skanu: wszystkie wartości z `miejsce="obraz"` i po jednym `Obraz` z ramkami na stronę."""

    wartosci: list[Wartosc] = field(default_factory=list)
    obrazy: list[Obraz] = field(default_factory=list)
    #: Wartości, dla których nie znaleziono trafienia w tekście strony (powinno być puste).
    nieznalezione: list[Wartosc] = field(default_factory=list)


def obroc_punkt(x: float, y: float, kat: float, szer: int, wys: int, szer_po: int | None = None,
                wys_po: int | None = None) -> tuple[float, float]:
    """Położenie piksela (x, y) po `Image.rotate(kat, center=(szer/2, wys/2))` (kąt w stopniach, przeciwnie do ruchu
    wskazówek zegara, oś y w dół). Z `szer_po` x `wys_po` – po `rotate(…, expand=True)` (obraz wynikowy o tym rozmiarze)."""
    t = math.radians(kat)
    dx, dy = x - szer / 2, y - wys / 2
    cx, cy = (szer if szer_po is None else szer_po) / 2, (wys if wys_po is None else wys_po) / 2
    return (cx + dx * math.cos(t) + dy * math.sin(t), cy - dx * math.sin(t) + dy * math.cos(t))


def _ramka_px(ramka_pt: tuple[float, float, float, float], wys_pt: float, kat: float, szer: int, wys: int,
              skala_x: float, skala_y: float) -> tuple[int, int, int, int]:
    """Ramka (pt, początek w lewym dolnym rogu) -> ramka w pikselach obróconego obrazu (obwiednia czterech rogów)."""
    x0, y0, x1, y1 = ramka_pt
    rogi = [obroc_punkt(x * skala_x, (wys_pt - y) * skala_y, kat, szer, wys) for x in (x0, x1) for y in (y0, y1)]
    xs, ys = [r[0] for r in rogi], [r[1] for r in rogi]
    return (max(0, math.floor(min(xs)) - LUZ_RAMKI), max(0, math.floor(min(ys)) - LUZ_RAMKI),
            min(szer, math.ceil(max(xs)) + LUZ_RAMKI), min(wys, math.ceil(max(ys)) + LUZ_RAMKI))


def _zeskanuj(obraz: Image.Image, kat: float, rng: np.random.Generator) -> bytes:
    """Obrót, lekkie rozmycie, niejednorodna jasność i szum -> JPEG (q75)."""
    obr = obraz.rotate(kat, resample=Image.BICUBIC, center=(obraz.width / 2, obraz.height / 2),
                       fillcolor=(255, 255, 255)).filter(ImageFilter.GaussianBlur(0.6))
    a = np.asarray(obr, dtype=np.float32) / 255.0
    # niejednorodność jasności: gładkie pole z małej losowej siatki (cień od zgięcia, nierówne oświetlenie)
    siatka = (rng.random((4, 3)) * 255).astype(np.uint8)
    pole = np.asarray(Image.fromarray(siatka).resize((obraz.width, obraz.height), Image.BICUBIC), dtype=np.float32) / 255
    a *= (0.90 + 0.08 * pole)[..., None]
    a += rng.normal(0.0, 0.022, a.shape[:2])[..., None]  # ziarno skanera (jednakowe w kanałach)
    plamki = rng.random(a.shape[:2]) > 0.99985  # pojedyncze ciemne punkty
    a[plamki] *= 0.45
    bufor = io.BytesIO()
    Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)).save(bufor, format="JPEG", quality=JAKOSC_JPEG)
    return bufor.getvalue()


def _zloz_pdf(jpegi: list[bytes], rng: random.Random) -> bytes:
    bufor = io.BytesIO()
    with bez_a85():                    # JPEG w PDF bez dodatkowego kodowania ASCII85
        c = canvas.Canvas(bufor, pagesize=A4, invariant=1, pageCompression=1)
        for jpeg in jpegi:
            c.drawImage(ImageReader(io.BytesIO(jpeg)), 0, 0, A4[0], A4[1])
            c.showPage()
        c.save()
    utworzono = dt.datetime(rng.randint(2022, 2025), rng.randint(1, 12), rng.randint(1, 28), rng.randint(8, 17),
                            rng.randint(0, 59))
    info = {"Title": "Skan", "Creator": "Scanner", "Producer": "Scanner", "CreationDate": _data_pdf(utworzono),
            "ModDate": _data_pdf(utworzono)}
    with pikepdf.open(io.BytesIO(bufor.getvalue())) as pdf:
        for strona in pdf.pages:  # reportlab dopisuje nieużywaną czcionkę F1 i „BT /F1 12 Tf ET” – skan ich nie ma
            if "/Font" in strona.Resources:
                del strona.Resources["/Font"]
            operacje = [(o, op) for o, op in pikepdf.parse_content_stream(strona)
                        if str(op) not in ("BT", "ET", "Tf", "TL")]
            strona.Contents = pdf.make_stream(pikepdf.unparse_content_stream(operacje))
        zapisz_metadane(pdf, info, _xmp("", "Skan", "", {}, utworzono, utworzono, "Scanner"))
        wyjscie = io.BytesIO()
        pdf.save(wyjscie, deterministic_id=True, compress_streams=True,
                 object_stream_mode=pikepdf.ObjectStreamMode.disable)
    return wyjscie.getvalue()


def renderuj_skan(d: Dokument, plik: Path, rng: random.Random, utrudnienia: set[str] | None = None) -> WynikSkan:
    """Zapisuje `d` jako skan (PDF z samymi obrazami) w `plik`; `utrudnienia` domyślnie `UTRUDNIENIA_SKAN`."""
    utr = set(UTRUDNIENIA_SKAN if utrudnienia is None else utrudnienia)
    nieznane = utr - UTRUDNIENIA_SKAN - UTRUDNIENIA_POMINIETE
    if nieznane:
        raise ValueError(f"nieznane utrudnienia skanu: {sorted(nieznane)}")
    dp = przytnij(d, utr)
    bajty, wp = zbuduj_pdf(dp, utr, geometria=True)
    nrng = np.random.default_rng(rng.getrandbits(63))
    pdf = pdfium.PdfDocument(bajty)
    wynik = WynikSkan()
    try:
        strony = [pdf[i] for i in range(len(pdf))]
        wys_pt = strony[0].get_height()
        jpegi: list[bytes] = []
        for n, strona in enumerate(strony):
            bm = strona.render(scale=SKALA).to_pil().convert("RGB")
            kat = rng.uniform(-MAX_OBROT, MAX_OBROT)
            sx, sy = bm.width / strona.get_width(), bm.height / wys_pt
            jpegi.append(_zeskanuj(bm, kat, nrng))
            ob = Obraz(f"{d.id}-strona{n + 1}", None)
            ramki_pt = [(dataclasses.replace(w, miejsce="obraz"), r) for w, nr, r in wp.ramki if nr == n + 1]
            ramki_pt += [(next(w for w in wp.wartosci if w.id == wid), r) for wid, nr, r in wp.umiejscowienie
                         if nr == n + 1]
            for wo, r in ramki_pt:
                if wo not in ob.wartosci:
                    ob.wartosci.append(wo)
                ob.ramki.append((wo.id, _ramka_px(r, wys_pt, kat, bm.width, bm.height, sx, sy)))
            wynik.obrazy.append(ob)
    finally:
        pdf.close()
    wynik.wartosci = [dataclasses.replace(w, miejsce="obraz") for w in wp.wartosci]
    umieszczone = {id(w) for w, _, _ in wp.ramki}
    wynik.nieznalezione = [w for w in wp.wartosci if w.miejsce != "obraz" and w.tekst.strip()
                           and id(w) not in umieszczone]
    plik = Path(plik)
    plik.parent.mkdir(parents=True, exist_ok=True)
    plik.write_bytes(_zloz_pdf(jpegi, rng))
    return wynik


def render_skan(d: Dokument, plik: Path, rng: random.Random, utrudnienia: set[str] | None = None) -> list[Wartosc]:
    """Jak `renderuj_skan`, ale zwraca tylko listę wartości (wszystkie z `miejsce="obraz"`)."""
    return renderuj_skan(d, plik, rng, utrudnienia).wartosci
