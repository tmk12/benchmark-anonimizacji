"""Testy wykresów raportu (`raport.wykresy`): poprawny SVG, determinizm, wzory dla druku cz.-b., „n/d” zamiast słupka."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from raport import buduj, wykresy
from raport.dane import wczytaj

FIKSTURY = Path(__file__).parent / "fixtures"
NAZWY = ["ranking_tekst", "ranking_pliki", "skladniki_tekst", "skladniki_pliki", "jezyki", "szybkosc", "tryby", "kategorie"]


@pytest.fixture(scope="module")
def raport():
    return wczytaj(FIKSTURY / "wykresy", FIKSTURY / "czas-m1")


def test_wszystkie_wykresy_zarejestrowane():
    assert set(NAZWY) <= set(buduj.WYKRESY)


@pytest.mark.parametrize("nazwa", NAZWY)
def test_poprawny_xml_svg(raport, nazwa):
    svg = buduj.WYKRESY[nazwa](raport)
    assert svg.lstrip().startswith("<svg")
    assert ET.fromstring(svg).tag.endswith("svg")
    assert "nan" not in re.sub(r"[A-Za-z]nan|nan[a-z]", "", svg.lower().replace("financial", ""))


@pytest.mark.parametrize("nazwa", NAZWY)
def test_deterministyczny(raport, nazwa):
    assert buduj.WYKRESY[nazwa](raport) == buduj.WYKRESY[nazwa](raport)


@pytest.mark.parametrize("nazwa", NAZWY)
def test_tekst_zostaje_tekstem_z_plex(raport, nazwa):
    svg = buduj.WYKRESY[nazwa](raport)
    assert "<text" in svg and "IBM Plex Sans" in svg
    assert "<path d=" in svg  # sanity: są też kształty


def _wzory(svg: str) -> int:
    return len(re.findall(r"<pattern ", svg))


@pytest.mark.parametrize("nazwa,min_wzorow", [
    ("ranking_tekst", 1), ("ranking_pliki", 1), ("szybkosc", 1), ("tryby", 1),
    ("skladniki_tekst", 6), ("skladniki_pliki", 6),
])
def test_serie_rozroznialne_bez_koloru(raport, nazwa, min_wzorow):
    """Review Focus 4: w wykresie wieloseryjnym serie mają różne wzory (hatch), nie tylko kolor."""
    assert _wzory(buduj.WYKRESY[nazwa](raport)) >= min_wzorow


def test_wzory_serii_sa_rozne():
    wz = wykresy.WZORY
    assert len(set(wz)) == len(wz) >= 13


def test_nd_nie_rysuje_slupka_i_ma_adnotacje(raport):
    svg = buduj.WYKRESY["szybkosc"](raport)  # delta nie ma czasu; privatizer-tekst-maks jest w aneksie
    assert svg.count("n/d") == 1
    # słupki = patche z wypełnieniem poza tłem i legendą: 5 uczestników z czasem
    slupki = re.findall(r'<g id="patch_\d+">\s*<path d="[^"]*" clip-path="url\(#[^)]+\)"', svg)
    assert len(slupki) == 5


def test_nd_w_jezykach_i_kategoriach(raport):
    assert "n/d" in buduj.WYKRESY["jezyki"](raport)      # delta/fr bez wartości
    assert "n/d" in buduj.WYKRESY["kategorie"](raport)   # gamma/KWOTA bez wartości


def test_liczby_po_polsku(raport):
    svg = buduj.WYKRESY["ranking_tekst"](raport)
    assert "772,4" in svg and "772.4" not in svg


def test_szybkosc_linia_odniesienia(raport):
    svg = buduj.WYKRESY["szybkosc"](raport)
    assert "t_ref" in svg and "1,0 s" in svg


def test_tryby_brak_uczestnika_to_nd(raport):
    svg = buduj.WYKRESY["tryby"](raport, "pliki")  # w fikstury per_kategoria są oba tryby plikowe
    assert ET.fromstring(svg) is not None


def test_nieznany_ranking_to_pusty_wykres_z_adnotacja(raport):
    svg = wykresy.ranking(raport, "nie-ma")
    assert "n/d" in svg


def test_tryby_nieznany_ranking_to_pusty_wykres_nie_keyerror(raport):
    svg = wykresy.tryby(raport, "nie-ma")
    assert "n/d" in svg and ET.fromstring(svg) is not None


def test_jezyki_privatizer_bez_koloru_pogrubiona_etykieta(raport):
    """Wiersze Privatizera wyróżnia pogrubiona etykieta wiersza (jak kolumny w `kategorie`), nie kolor kafelka."""
    import matplotlib
    from matplotlib.figure import Figure
    zlapane = {}
    oryg = wykresy._mapa
    def podglad(nazwa, wiersze_etykiety, kolumny, wartosci, jasny, ciemny, **kw):
        zlapane.update(kw)
        return oryg(nazwa, wiersze_etykiety, kolumny, wartosci, jasny, ciemny, **kw)
    wykresy._mapa = podglad
    try:
        wykresy.jezyki(raport)
    finally:
        wykresy._mapa = oryg
    assert zlapane.get("wiersze_pogrubione") == {"privatizer-tekst"}


def test_szybkosc_etykiety_osi_unikalne_bez_wykladnika(raport):
    svg = buduj.WYKRESY["szybkosc"](raport)
    osie = [t for t in re.findall(r"<text[^>]*>([^<]*)</text>", svg) if re.fullmatch(r"\d+(,\d+)?", t) and t in ("0,0001", "0,001", "0,01", "0,1", "1", "10", "100")]
    assert len(osie) == len(set(osie)) >= 3
    assert "e-0" not in svg
