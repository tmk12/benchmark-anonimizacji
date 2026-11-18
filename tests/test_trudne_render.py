"""Renderery i OCR dla cyrylicy ukraińskiej: każdy format (DOCX, PDF, skan, XLSX, PPTX, EML, MSG, DOC) musi zawierać
wartości gold z cyrylicą (w tym litery ґ є і ї i apostrof) dokładnie tak, jak w gold – sprawdzane NIEZALEŻNYMI czytnikami
z testów rendererów (zip+XML, pypdfium2, openpyxl, python-pptx, email, olefile) – oraz mieć glify czcionek i OCR `ukr`."""
from __future__ import annotations

import random
from pathlib import Path

import pytest
from reportlab.pdfbase.ttfonts import TTFont
from test_render_docx import WSZYSTKIE, _teksty_miejsc
from test_render_inne import (WSZYSTKIE_DOC, WSZYSTKIE_EML, WSZYSTKIE_MSG, WSZYSTKIE_PPTX, WSZYSTKIE_XLSX, _blob_doc,
                              _sprawdz_wartosci_eml, _sprawdz_wartosci_msg, _teksty_pptx, _teksty_xlsx, _w_blobie)
from test_render_pdf import _bez_spacji, _odzyskana, _ocr_strony, _sprawdz_miejsca

from pbench import ocr
from pbench.budowa import zbuduj_z_kontekstem
from pbench.dane import Generator
from pbench.dane.wspolne import SLOWNIKI
from pbench.model import Dokument, Wartosc
from pbench.render import podpis
from pbench.render.doc import renderuj_doc
from pbench.render.docx import render_docx
from pbench.render.eml import render_eml
from pbench.render.msg import render_msg
from pbench.render.pdf import FONTY, render_pdf
from pbench.render.pptx import render_pptx
from pbench.render.skan import UTRUDNIENIA_SKAN, renderuj_skan
from pbench.render.xlsx import render_xlsx
from pbench.szablony import SZABLONY
from pbench.szablony.trudne import SZABLONY_UK, SZABLONY_WSTAWKI
from pbench.translit import ma_cyrylice
from pbench.trudne import NATURALNY, z_homoglifami
from pbench.utrudnienia import UTRUDNIENIA_DOCX, UTRUDNIENIA_PDF, przytnij, przytnij_dla

ALFABET_UK = "АБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯабвгґдеєжзиіїйклмнопрстуфхцчшщьюя’ʼ№«»—"
DOCX_ZAL = {"papier_firmowy", "tabele", "przypisy", "komentarze", "metadane"}


def _uk(typ: str, seed: int) -> Dokument:
    d = zbuduj_z_kontekstem(SZABLONY_UK[typ], Generator("uk", seed), random.Random(seed)).dokument
    d.id, d.format = f"h-test-uk-{typ}", "docx"
    return d


def _wstawka(jezyk: str, typ: str, seed: int, wariant: str = "cw") -> Dokument:
    gen = Generator(jezyk, seed)
    gen.systemy_translit = {"s1": NATURALNY[jezyk], "s2": "cyr", "s3": "kmu2010", "s4": "iso9"}
    d = zbuduj_z_kontekstem(SZABLONY_WSTAWKI[(jezyk, typ)], gen, random.Random(seed), wariant).dokument
    d.id, d.format = f"h-test-{jezyk}-{typ}", "docx"
    return d


def _homoglify(jezyk: str, typ: str, seed: int) -> Dokument:
    d = zbuduj_z_kontekstem(z_homoglifami(SZABLONY[(jezyk, typ)], 1.0), Generator(jezyk, seed), random.Random(seed)).dokument
    d.id, d.format = f"h-test-{jezyk}-{typ}", "docx"
    return d


def _wartosci_dok(d: Dokument) -> list[Wartosc]:
    return [f for e in d.elementy for f in e.fragmenty if isinstance(f, Wartosc)]


DOKUMENTY = {
    "uk-umowa": lambda: _uk("umowa", 3), "uk-notatka": lambda: _uk("notatka", 4),
    "uk-pelnomocnictwo": lambda: _uk("pelnomocnictwo", 5), "pl-wstawka-umowa": lambda: _wstawka("pl", "umowa", 6, "tr"),
    "en-wstawka-notatka": lambda: _wstawka("en", "notatka", 7), "pl-homoglify": lambda: _homoglify("pl", "umowa", 8),
}


def _cyrylica_w_gold(d: Dokument) -> list[Wartosc]:
    ws = [w for w in _wartosci_dok(d) if ma_cyrylice(w.tekst)]
    assert ws
    return ws


@pytest.mark.parametrize("nazwa", DOKUMENTY)
def test_docx_cyrylica(tmp_path, nazwa):
    pelny = DOKUMENTY[nazwa]()
    d = przytnij(pelny, WSZYSTKIE)
    plik = tmp_path / "a.docx"
    wartosci = render_docx(d, plik, WSZYSTKIE)
    assert _cyrylica_w_gold(d)
    import zipfile
    with zipfile.ZipFile(plik) as zf:
        teksty = _teksty_miejsc(zf)
        for w in wartosci:
            if w.miejsce != "obraz":
                assert w.tekst in teksty[w.miejsce], (w.id, w.tekst, w.miejsce)
        assert any(ma_cyrylice(w.tekst) for w in wartosci if w.miejsce != "obraz")


@pytest.mark.parametrize("nazwa", DOKUMENTY)
def test_pdf_cyrylica(tmp_path, nazwa):
    d = przytnij(DOKUMENTY[nazwa](), UTRUDNIENIA_PDF)
    plik = tmp_path / "a.pdf"
    wartosci = render_pdf(d, plik, set(UTRUDNIENIA_PDF))
    assert any(ma_cyrylice(w.tekst) for w in wartosci)
    _sprawdz_miejsca(plik, wartosci)


@pytest.mark.parametrize("nazwa", ["uk-umowa", "pl-wstawka-umowa", "pl-homoglify"])
def test_xlsx_cyrylica(tmp_path, nazwa):
    d = przytnij_dla("xlsx", DOKUMENTY[nazwa](), WSZYSTKIE_XLSX)
    plik = tmp_path / "a.xlsx"
    wartosci = render_xlsx(d, plik, WSZYSTKIE_XLSX)
    teksty = _teksty_xlsx(plik)
    assert any(ma_cyrylice(w.tekst) for w in wartosci)
    for w in wartosci:
        assert w.tekst in teksty[w.miejsce], (w.id, w.tekst, w.miejsce)


@pytest.mark.parametrize("nazwa", ["uk-notatka", "en-wstawka-notatka", "pl-homoglify"])
def test_pptx_cyrylica(tmp_path, nazwa):
    d = przytnij_dla("pptx", DOKUMENTY[nazwa](), WSZYSTKIE_PPTX)
    plik = tmp_path / "a.pptx"
    wartosci = render_pptx(d, plik, WSZYSTKIE_PPTX)
    teksty = _teksty_pptx(plik)
    assert any(ma_cyrylice(w.tekst) for w in wartosci)
    for w in wartosci:
        if w.miejsce == "obraz":
            continue
        zbior = teksty["tresc"] + teksty["naglowek"] if w.miejsce == "naglowek" else teksty[w.miejsce]
        assert w.tekst in zbior, (w.id, w.tekst, w.miejsce)


def _poczta(typ_zal: str = "notatka"):
    """E-mail ukraiński + załącznik DOCX tego samego zdarzenia (wspólny kontekst), jak w korpusie."""
    gen = Generator("uk", 11)
    mail = zbuduj_z_kontekstem(SZABLONY_UK["email"], gen, random.Random(11))
    zal = zbuduj_z_kontekstem(SZABLONY_UK[typ_zal], gen, random.Random(12), wspolne=mail)
    zal.dokument.id, zal.dokument.format = "h-test-zal", "docx"
    return mail.dokument, przytnij_dla("docx", zal.dokument, DOCX_ZAL)


@pytest.mark.parametrize("utrudnienia", [set(), WSZYSTKIE_EML])
def test_eml_cyrylica(tmp_path, utrudnienia):
    mail, zal = _poczta()
    d = przytnij_dla("eml", mail, utrudnienia)
    plik = tmp_path / "a.eml"
    wartosci = render_eml(d, plik, utrudnienia, zal, DOCX_ZAL)
    assert any(ma_cyrylice(w.tekst) for w in wartosci)
    _sprawdz_wartosci_eml(plik, wartosci)


@pytest.mark.parametrize("utrudnienia", [set(), WSZYSTKIE_MSG])
def test_msg_cyrylica(tmp_path, utrudnienia):
    mail, zal = _poczta()
    d = przytnij_dla("msg", mail, utrudnienia)
    plik = tmp_path / "a.msg"
    wartosci = render_msg(d, plik, utrudnienia, zal, DOCX_ZAL)
    assert any(ma_cyrylice(w.tekst) for w in wartosci)
    _sprawdz_wartosci_msg(plik, wartosci)


@pytest.mark.parametrize("nazwa", ["uk-pelnomocnictwo", "pl-wstawka-umowa"])
def test_doc_cyrylica(tmp_path, nazwa):
    d = przytnij_dla("doc", DOKUMENTY[nazwa](), WSZYSTKIE_DOC)
    plik = tmp_path / "a.doc"
    wynik = renderuj_doc(d, plik, WSZYSTKIE_DOC)
    assert wynik.ostrzezenia == [] and any(ma_cyrylice(w.tekst) for w in wynik.wartosci)
    blob = _blob_doc(plik)
    for w in wynik.wartosci:
        if w.miejsce != "obraz":
            assert _w_blobie(w.tekst, blob), (w.id, w.tekst, w.miejsce)


# ----------------------------------------------------------------------------- skan i OCR (ukr)
@pytest.mark.parametrize("nazwa,jezyk_ocr", [("uk-umowa", "uk"), ("pl-wstawka-umowa", "pl+uk")])
def test_skan_ocr_ukr_odzyskuje_wiekszosc_cyrylicy(tmp_path, nazwa, jezyk_ocr):
    if not ocr.dostepny(jezyk_ocr):
        pytest.skip("brak ukr.traineddata (vendor/tessdata)")
    d = przytnij(DOKUMENTY[nazwa](), UTRUDNIENIA_SKAN)
    plik = tmp_path / "s.pdf"
    wynik = renderuj_skan(d, plik, random.Random(1), set(UTRUDNIENIA_SKAN))
    tekst = _bez_spacji(" ".join(t for _, t in _ocr_strony(plik, jezyk_ocr))).casefold()
    cyr = [w for w in wynik.wartosci if ma_cyrylice(w.tekst) and len(_bez_spacji(w.tekst)) >= 4 and w.miejsce == "obraz"
           and not w.id.endswith("@obraz")]
    assert len(cyr) >= 2
    odzyskane = sum(_odzyskana(_bez_spacji(w.tekst).casefold(), tekst, prog=0.8) for w in cyr)
    assert odzyskane / len(cyr) >= 0.80, (odzyskane, len(cyr))


def test_ocr_jezyki_dla_cyrylicy():
    assert ocr.KODY["uk"] == "ukr+eng" and ocr.KODY["pl+uk"] == "pol+ukr" and ocr.KODY["de+uk"] == "deu+ukr"
    with pytest.raises(KeyError):
        ocr.KODY["xx+uk"]
    assert (ocr.tessdata_dir() / "ukr.traineddata").exists() or not ocr.dostepny("uk")


def test_jezyk_ocr_sedziego_dla_cyrylicy():
    from pbench.sedzia.plik import jezyk_ocr
    pl = Wartosc("a#1", "OSOBA", "Jan", "pl", "tresc", "OSOBA")
    cyr = Wartosc("a#2", "OSOBA", "Іван", "pl", "tresc", "OSOBA")
    uk = Wartosc("a#3", "OSOBA", "Іван", "uk", "tresc", "OSOBA")
    assert jezyk_ocr([pl], "pl") == "pl" and jezyk_ocr([pl, cyr], "pl") == "pl+uk" and jezyk_ocr([uk], "uk") == "uk"
    assert jezyk_ocr([cyr], "pl+uk") == "pl+uk"


# ----------------------------------------------------------------------------- czcionki
@pytest.mark.parametrize("plik", ["DejaVuSerif.ttf", "DejaVuSerif-Bold.ttf", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf"])
def test_czcionki_pdf_i_logo_maja_wszystkie_litery_ukrainskie(plik):
    face = TTFont("x", f"{FONTY}/{plik}").face
    brak = [c for c in ALFABET_UK if ord(c) not in face.charToGlyph]
    assert not brak, (plik, brak)


def test_podpis_z_cyrylica_rysowany_czcionka_z_cyrylica():
    from PIL import ImageFont
    font = ImageFont.truetype(podpis.CZCIONKA_CYRYLICA, 40)
    maska = font.getmask("Їжак")
    assert maska.getbbox() is not None
    rng = random.Random(1)
    obraz, ramka = podpis.generuj("Олександр Шевченко", rng)
    assert obraz.size[0] > 200 and ramka[2] - ramka[0] > 150
    # czcionka łacińska bez cyrylicy (Z003) nie jest używana dla tekstu z cyrylicą
    obraz_lac, _ = podpis.generuj("Oleksandr Shevchenko", random.Random(1))
    assert obraz_lac.size != obraz.size
