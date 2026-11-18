"""Obrazy syntetyczne warstwy trudnych przypadków H4a: pieczątka firmy, zrzut ekranu poczty i znak wodny (PIL).

Każda funkcja rysuje WYŁĄCZNIE wartości z `Wartosc.tekst` (po ewentualnym zamaskowaniu przez uczestnika „idealnego”) i
zwraca PNG oraz ramki wartości w pikselach obrazu (po obrocie i szumie): pieczątka – okrągła albo prostokątna, z lekkim
obrotem i szumem tuszu; zrzut – okno poczty (pasek tytułu, foldery, nagłówek wiadomości, podpis); znak wodny – napis
poziomy (obraz osadzony w PDF jest ustawiany ukośnie macierzą strony, więc OCR czyta go poziomo). Krój: DejaVu Sans z
systemu, rysunek własny – bez znaków towarowych.
"""
from __future__ import annotations

import io
import math
import random
import textwrap

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .model import Wartosc
from .render.skan import obroc_punkt

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
Ramka = tuple[int, int, int, int]
#: Napisy interfejsu zrzutu ekranu (bez danych) wg języka dokumentu.
INTERFEJS: dict[str, dict[str, str]] = {
    "pl": {"tytul": "Poczta – Odebrane", "foldery": "Odebrane|Wysłane|Wersje robocze|Archiwum|Kosz", "od": "Od", "do": "Do",
           "temat": "Temat", "adresat": "biuro@kancelaria.example", "dotyczy": "W sprawie dokumentów",
           "tresc": "Dzień dobry, w załączeniu przesyłam dokumenty. Proszę o kontakt w sprawie terminu.",
           "pozdrawiam": "Pozdrawiam"},
    "en": {"tytul": "Mail – Inbox", "foldery": "Inbox|Sent|Drafts|Archive|Trash", "od": "From", "do": "To",
           "temat": "Subject", "adresat": "office@firm.example", "dotyczy": "Regarding the documents",
           "tresc": "Hello, please find the documents attached. Please contact me about the date.",
           "pozdrawiam": "Kind regards"},
    "es": {"tytul": "Correo – Recibidos", "foldery": "Recibidos|Enviados|Borradores|Archivo|Papelera", "od": "De",
           "do": "Para", "temat": "Asunto", "adresat": "oficina@despacho.example", "dotyczy": "Sobre los documentos",
           "tresc": "Buenos días, adjunto los documentos. Le ruego que me contacte sobre la fecha.",
           "pozdrawiam": "Saludos cordiales"},
    "de": {"tytul": "Post – Posteingang", "foldery": "Posteingang|Gesendet|Entwürfe|Archiv|Papierkorb", "od": "Von",
           "do": "An", "temat": "Betreff", "adresat": "buero@kanzlei.example", "dotyczy": "Betreffend die Unterlagen",
           "tresc": "Guten Tag, anbei die Unterlagen. Bitte melden Sie sich wegen des Termins.",
           "pozdrawiam": "Mit freundlichen Grüßen"},
    "fr": {"tytul": "Courrier – Réception", "foldery": "Réception|Envoyés|Brouillons|Archives|Corbeille", "od": "De",
           "do": "À", "temat": "Objet", "adresat": "bureau@cabinet.example", "dotyczy": "Au sujet des documents",
           "tresc": "Bonjour, veuillez trouver les documents ci-joints. Merci de me contacter pour la date.",
           "pozdrawiam": "Cordialement"},
}


def _png(obraz: Image.Image) -> bytes:
    bufor = io.BytesIO()
    obraz.save(bufor, format="PNG")
    return bufor.getvalue()


def obroc_ramke(ramka: Ramka, kat: float, przed: tuple[int, int], po: tuple[int, int]) -> Ramka:
    """Ramka po `Image.rotate(kat, expand=True)` (kąt w stopniach, przeciwnie do ruchu wskazówek zegara, oś y w dół):
    obwiednia czterech obróconych rogów, przycięta do obrazu."""
    x0, y0, x1, y1 = ramka
    rogi = [obroc_punkt(x, y, kat, przed[0], przed[1], po[0], po[1]) for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
    xs, ys = [r[0] for r in rogi], [r[1] for r in rogi]
    return (max(0, math.floor(min(xs))), max(0, math.floor(min(ys))), min(po[0], math.ceil(max(xs))),
            min(po[1], math.ceil(max(ys))))


def _etykieta(w: Wartosc) -> str:
    """Etykieta zastępcza z kategorii (gdy wywołujący nie podał etykiet w języku dokumentu)."""
    return {"NIP": "NIP", "REGON": "REGON", "KRS": "KRS"}.get(w.kategoria, w.kategoria.replace("_", " "))


def _unia(a: Ramka | None, b: Ramka) -> Ramka:
    return b if a is None else (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


# ----------------------------------------------------------------------------- pieczątka
def pieczatka(wartosci: list[Wartosc], ksztalt: str, kat: float, ziarno: int,
              etykiety: list[str] | None = None) -> tuple[bytes, dict[str, Ramka]]:
    """Pieczątka firmy (`okragla` | `prostokatna`) z wartościami po kolei: nazwa (pierwsza), a potem adres/identyfikatory
    (etykieta przed wartością: `etykiety[i]` w języku dokumentu – „NIP”, „USt-IdNr.”, „SIRET”…, pusta = bez etykiety;
    bez `etykiety` – z kategorii). Zwraca (PNG, id wartości -> ramka)."""
    rng = random.Random(f"pieczatka:{ziarno}")
    tusz = (rng.choice((30, 40, 55)), rng.choice((50, 60, 90)), rng.choice((150, 170, 190)))
    okragla = ksztalt == "okragla"
    bok_x, bok_y = (440, 440) if okragla else (600, 380)
    obraz = Image.new("RGBA", (bok_x, bok_y), (255, 255, 255, 0))
    rys = ImageDraw.Draw(obraz)
    # linie: (wartość, tekst widoczny, czy nazwa)
    wiersze: list[tuple[Wartosc, list[str], bool]] = []
    for i, w in enumerate(wartosci):
        if i == 0:
            wiersze.append((w, textwrap.wrap(w.tekst, 20 if okragla else 30, break_long_words=True) or [w.tekst], True))
        else:
            etykieta = _etykieta(w) if etykiety is None else etykiety[i]
            wiersze.append((w, textwrap.wrap(w.tekst, 36, break_long_words=True) or [w.tekst] if w.kategoria == "ADRES"
                            else [f"{etykieta} {w.tekst}" if etykieta else w.tekst], False))
    rozmiar = 28 if okragla else 30
    f_n = ImageFont.truetype(FONT_B, rozmiar)
    f_m = ImageFont.truetype(FONT_B, rozmiar - 8)
    wys_linii = [(f_n if nazwa else f_m).getbbox("Ag")[3] + 8 for _, linie, nazwa in wiersze for _ in linie]
    razem = sum(wys_linii)
    y = (bok_y - razem) // 2
    ramki: dict[str, Ramka] = {}
    for w, linie, nazwa in wiersze:
        f = f_n if nazwa else f_m
        ramka_w: Ramka | None = None
        for linia in linie:
            szer = int(rys.textlength(linia, font=f))
            x = (bok_x - szer) // 2
            rys.text((x, y), linia, font=f, fill=tusz + (255,))
            # ramka samej wartości (bez etykiety przed nią)
            pref = linia[: len(linia) - len(w.tekst)] if linia.endswith(w.tekst) else ""
            x0 = x + int(rys.textlength(pref, font=f)) if pref else x
            bb = f.getbbox(w.tekst if linia.endswith(w.tekst) else linia)
            ramka_w = _unia(ramka_w, (x0, y + bb[1], x0 + (bb[2] - bb[0] if linia.endswith(w.tekst) else szer), y + bb[3]))
            y += f.getbbox("Ag")[3] + 8
        assert ramka_w is not None
        ramki[w.id] = ramka_w
    grub = 5
    if okragla:
        rys.ellipse((4, 4, bok_x - 5, bok_y - 5), outline=tusz + (255,), width=grub)
        rys.ellipse((24, 24, bok_x - 25, bok_y - 25), outline=tusz + (255,), width=2)
    else:
        rys.rectangle((4, 4, bok_x - 5, bok_y - 5), outline=tusz + (255,), width=grub)
        rys.rectangle((16, 16, bok_x - 17, bok_y - 17), outline=tusz + (255,), width=2)
    # lekki obrót i szum tuszu (przetarcia = losowe przezroczyste plamki)
    obrocony = obraz.rotate(kat, resample=Image.BICUBIC, expand=True, fillcolor=(255, 255, 255, 0))
    szum = ImageDraw.Draw(obrocony)
    for _ in range(260):
        x, y2 = rng.randrange(obrocony.width), rng.randrange(obrocony.height)
        r = rng.choice((1, 1, 2))
        szum.ellipse((x - r, y2 - r, x + r, y2 + r), fill=(255, 255, 255, 0))
    tlo = Image.new("RGB", obrocony.size, (255, 255, 255))
    tlo.paste(obrocony, mask=obrocony.getchannel("A"))
    tlo = tlo.filter(ImageFilter.GaussianBlur(0.5))
    po = tlo.size
    return _png(tlo), {wid: obroc_ramke(r, kat, (bok_x, bok_y), po) for wid, r in ramki.items()}


# ----------------------------------------------------------------------------- zrzut ekranu
def zrzut_ekranu(jezyk: str, wartosci: list[Wartosc], ziarno: int) -> tuple[bytes, dict[str, Ramka]]:
    """Zrzut okna poczty. `wartosci` po kolei: nadawca (OSOBA), jego e-mail, osoba z podpisu, jej telefon.
    Zwraca (PNG, id wartości -> ramka)."""
    rng = random.Random(f"zrzut:{ziarno}")
    t = INTERFEJS.get(jezyk, INTERFEJS["en"])
    nadawca, email, podpis, telefon = wartosci
    szer, wys = 1180, 700
    obraz = Image.new("RGB", (szer, wys), (246, 247, 249))
    rys = ImageDraw.Draw(obraz)
    f = ImageFont.truetype(FONT, 22)
    f_b = ImageFont.truetype(FONT_B, 22)
    f_m = ImageFont.truetype(FONT, 19)
    rys.rectangle((0, 0, szer, 52), fill=(52, 58, 72))
    for i, kolor in enumerate(((235, 96, 90), (240, 190, 70), (90, 195, 100))):
        rys.ellipse((18 + i * 30, 17, 36 + i * 30, 35), fill=kolor)
    rys.text((140, 12), t["tytul"], font=f_b, fill=(240, 240, 240))
    rys.rectangle((0, 52, 250, wys), fill=(228, 231, 237))
    for i, folder in enumerate(t["foldery"].split("|")):
        if i == 0:
            rys.rectangle((0, 70, 250, 112), fill=(205, 214, 235))
        rys.text((28, 78 + i * 46), folder, font=f_b if i == 0 else f, fill=(35, 40, 55))
    # lista wiadomości (neutralne wiersze)
    rys.rectangle((251, 52, 640, wys), fill=(255, 255, 255))
    for i in range(6):
        y = 70 + i * 100
        rys.line((251, y + 92, 640, y + 92), fill=(225, 228, 233), width=2)
        rys.rectangle((270, y + 6, 270 + rng.randrange(140, 260), y + 24), fill=(205, 208, 215))
        rys.rectangle((270, y + 38, 270 + rng.randrange(180, 330), y + 52), fill=(228, 230, 235))
    rys.rectangle((251, 70, 640, 160), outline=(120, 150, 215), width=2)
    # okno wiadomości
    x = 668
    ramki: dict[str, Ramka] = {}
    y = 80
    for etykieta, wartosc, rodzaj in ((t["od"], nadawca, "osoba"), ("", email, "email")):
        if etykieta:
            rys.text((x, y), f"{etykieta}:", font=f_b, fill=(60, 66, 80))
            x0 = x + int(rys.textlength(f"{etykieta}: ", font=f_b)) + 6
        else:
            x0 = x + int(rys.textlength(f"{t['od']}: ", font=f_b)) + 6
            y += 36
        bb = f.getbbox(wartosc.tekst)
        rys.text((x0, y), wartosc.tekst, font=f, fill=(20, 24, 36))
        ramki[wartosc.id] = (x0 + bb[0], y + bb[1], x0 + bb[2], y + bb[3])
        y += 36
    rys.text((x, y), f"{t['do']}: {t['adresat']}", font=f, fill=(60, 66, 80))
    y += 36
    rys.text((x, y), f"{t['temat']}: {t['dotyczy']}", font=f_b, fill=(20, 24, 36))
    y += 46
    rys.line((x, y, szer - 30, y), fill=(210, 213, 220), width=2)
    y += 22
    for linia in textwrap.wrap(t["tresc"], 38):
        rys.text((x, y), linia, font=f_m, fill=(30, 34, 46))
        y += 30
    y += 24
    rys.text((x, y), f"{t['pozdrawiam']},", font=f_m, fill=(30, 34, 46))
    y += 34
    for wartosc in (podpis, telefon):
        bb = f.getbbox(wartosc.tekst)
        rys.text((x, y), wartosc.tekst, font=f, fill=(20, 24, 36))
        ramki[wartosc.id] = (x + bb[0], y + bb[1], x + bb[2], y + bb[3])
        y += 34
    obraz = obraz.filter(ImageFilter.GaussianBlur(0.4))
    return _png(obraz), ramki


# ----------------------------------------------------------------------------- znak wodny
def znak_wodny(w: Wartosc) -> tuple[bytes, Ramka]:
    """Poziomy napis szary na przezroczystym tle (RGB pod przezroczystością jest biały, więc po wyciągnięciu obrazu z PDF
    – bez kanału alfa – OCR widzi szary tekst na białym tle). Zwraca (PNG RGBA, ramka tekstu)."""
    f = ImageFont.truetype(FONT_B, 92)
    miara = ImageDraw.Draw(Image.new("RGB", (4, 4)))
    bb = miara.textbbox((0, 0), w.tekst, font=f)
    szer, wys = bb[2] - bb[0] + 60, bb[3] - bb[1] + 60
    maska = Image.new("L", (szer, wys), 0)
    ImageDraw.Draw(maska).text((30 - bb[0], 30 - bb[1]), w.tekst, font=f, fill=255)
    obraz = Image.new("RGBA", (szer, wys), (255, 255, 255, 0))
    obraz.paste(Image.new("RGBA", (szer, wys), (96, 96, 96, 255)), mask=maska)
    return _png(obraz), (30, 30, 30 + bb[2] - bb[0], 30 + bb[3] - bb[1])
