"""Testy podsumowania, okładki i składu całego PDF: wiersze podsumowania (pierwsza piątka + Privatizer spoza niej), tabela i wykres, okładka,
a na danych rzeczywistych (env PBENCH_RAPORT_WYNIKI) treść podsumowania i geometria PDF (żaden blok nie wychodzi poza obszar strony, Review Focus 3)."""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from raport import buduj, dane, tabele, wykresy
from raport.dane import Raport, Test, Wiersz, wczytaj

FIKSTURY = Path(__file__).parent / "fixtures"
WYNIKI = os.environ.get("PBENCH_RAPORT_WYNIKI")
MM = 72 / 25.4
MARGINES_BOCZNY = 16 * MM  # `@page` w druk.css


def _w(nazwa: str, miejsce: int | None, suma: float, remis: list[str] | None = None) -> Wiersz:
    return Wiersz(uczestnik=nazwa, miejsce=miejsce, remis_z=remis or [], suma=suma, suma_ci=(suma - 5, suma + 5), testy={}, dokumenty=800, z_wyciekiem=100)


def _raport() -> Raport:
    r = Raport()
    r.rankingi["tekst"] = [_w(f"narzedzie-{i}", i, 900 - 50 * i) for i in range(1, 6)] + [_w("narzedzie-6", 6, 600), _w("privatizer-tekst", 7, 500), _w("narzedzie-8", 8, 400)]
    r.rankingi["pliki"] = [_w("privatizer-plik", 1, 700), _w("plik-b", 2, 300)]
    return r


def test_wiersze_podsumowania_piatka_i_privatizer_spoza_niej():
    r = _raport()
    assert [w.uczestnik for w in dane.wiersze_podsumowania(r, "tekst")] == [f"narzedzie-{i}" for i in range(1, 6)] + ["privatizer-tekst"]
    assert [w.uczestnik for w in dane.wiersze_podsumowania(r, "pliki")] == ["privatizer-plik", "plik-b"]
    assert dane.wiersze_podsumowania(r, "brak") == []


def test_tabela_i_wykres_podsumowania_maja_te_same_wiersze():
    r = _raport()
    html, svg = tabele.podsumowanie(r), wykresy.podsumowanie(r)
    for nazwa in ("narzedzie-5", "privatizer-tekst", "privatizer-plik", "plik-b"):
        assert nazwa.replace("-", "-<wbr>") in html and nazwa in svg
    assert "narzedzie-6" not in html and "narzedzie-8" not in html and "nan" not in html.lower().replace("narzedzie", "")


def test_podsumowanie_bez_danych_nie_pada():
    assert "n/d" in wykresy.podsumowanie(Raport())
    assert "n/d" in tabele.podsumowanie(Raport())


def test_okladka_ma_tylko_logo_tytul_metodyke_i_date(tmp_path):
    (tmp_path / "01-x.md").write_text("# X\n\nTreść.\n", encoding="utf-8")
    html = buduj.zloz_html(wczytaj(FIKSTURY / "zbiorcze", FIKSTURY / "czas-m1"), tmp_path)
    okladka = re.search(r'<section class="okladka">(.*?)</section>', html, re.S).group(1)
    m = dane.liczby_opisowe()["daty"]
    tekst = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<svg.*?</svg>", "", okladka, flags=re.S))).strip()
    assert "<svg" in okladka
    assert tekst == f"Raport porównawczy anonimizacji Wersja metodyki: prerejestracja-1 (zamrożona {m['zamrozenie']}) Data raportu: {m['raport']}"
    assert not re.search(r"\bv[12]\b", tekst)


# ------------------------------------------------------------------ dane rzeczywiste

@pytest.fixture(scope="module")
def pdf_rzeczywisty(tmp_path_factory):
    cel = tmp_path_factory.mktemp("pdf-rzeczywisty") / "raport.pdf"
    buduj.buduj(Path(WYNIKI), cel)
    return cel


@pytest.fixture(scope="module")
def pdf_aneks_rzeczywisty(tmp_path_factory):
    cel = tmp_path_factory.mktemp("pdf-aneks-rzeczywisty") / "aneks.pdf"
    buduj.buduj(Path(WYNIKI), cel, rozdzialy=buduj.ANEKS, tytul=buduj.TYTUL_ANEKSU, towarzyszy=buduj.TYTUL_RAPORTU)
    return cel


@pytest.mark.skipif(not WYNIKI, reason="brak PBENCH_RAPORT_WYNIKI (katalog zbiorczy z wynikami)")
def test_podsumowanie_dane_rzeczywiste():
    html = buduj.zloz_html(wczytaj(Path(WYNIKI)))
    sekcja = html[html.index(">Podsumowanie</h1>"):html.index(">Dlaczego to ważne</h1>")]
    tekst = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", sekcja))
    assert not re.search(r"\bnan\b|\bNone\b|Undefined|\{\{", tekst)
    assert "1.3.0b24" in tekst and "1.0.0rc5" in tekst and "2026-11-04" in tekst
    assert sekcja.count("<table") == 1 and sekcja.count("<svg") == 1 and sekcja.count("<li>") == 3
    assert not re.search(r"najlepsz|bezkonkurenc|niedościgł", tekst, re.I)
    assert "Okładka" not in tekst and html.index('class="okladka"') < html.index('id="spis"') < html.index(">Podsumowanie</h1>")


@pytest.mark.skipif(not WYNIKI, reason="brak PBENCH_RAPORT_WYNIKI (katalog zbiorczy z wynikami)")
@pytest.mark.parametrize("dokument", ["pdf_rzeczywisty", "pdf_aneks_rzeczywisty"])
def test_pdf_zadna_tresc_nie_wychodzi_poza_obszar_strony(dokument, request):
    """Review Focus 3: tabele (komórki, linie, tła) i wykresy mieszczą się w bloku tekstu A4; okładka (strona 1) ma własne marginesy."""
    pdf_rzeczywisty = request.getfixturevalue(dokument)
    from pdfminer.high_level import extract_pages
    from pdfminer.layout import LTChar, LTCurve, LTFigure, LTImage, LTLine, LTRect, LTTextContainer

    def elementy(obiekt):
        for x in obiekt:
            yield x
            if hasattr(x, "__iter__") and not isinstance(x, LTTextContainer):
                yield from elementy(x)

    wykroczenia = []
    for nr, strona in enumerate(extract_pages(str(pdf_rzeczywisty)), 1):
        if nr == 1:
            continue
        lewo, prawo = MARGINES_BOCZNY - 2, strona.width - MARGINES_BOCZNY + 2
        for x in elementy(strona):
            if isinstance(x, (LTChar, LTRect, LTLine, LTCurve, LTImage, LTFigure)) and (x.x0 < lewo or x.x1 > prawo):
                wykroczenia.append(f"s. {nr}: {type(x).__name__} x0={x.x0:.0f} x1={x.x1:.0f}")
    assert not wykroczenia, "\n".join(wykroczenia[:10])


@pytest.mark.skipif(not WYNIKI, reason="brak PBENCH_RAPORT_WYNIKI (katalog zbiorczy z wynikami)")
@pytest.mark.parametrize("dokument", ["pdf_rzeczywisty", "pdf_aneks_rzeczywisty"])
def test_pdf_bez_nan_niewypelnionych_wstawek_i_pustych_stron(dokument, request):
    pdf_rzeczywisty = request.getfixturevalue(dokument)
    from pdfminer.high_level import extract_pages, extract_text
    tekst = extract_text(str(pdf_rzeczywisty))
    assert not re.search(r"\bnan\b|\bNone\b|Undefined|\{\{|\}\}|\{%", tekst)
    for nr, strona in enumerate(extract_pages(str(pdf_rzeczywisty)), 1):
        assert sum(1 for _ in strona) > 1, f"pusta strona {nr}"


def test_okladka_aneksu_ma_tytul_aneksu_i_wskazuje_raport(tmp_path):
    (tmp_path / "01-x.md").write_text("# X\n\nTreść.\n", encoding="utf-8")
    html = buduj.zloz_html(wczytaj(FIKSTURY / "zbiorcze", FIKSTURY / "czas-m1"), tmp_path, buduj.TYTUL_ANEKSU, buduj.TYTUL_RAPORTU)
    okladka = re.search(r'<section class="okladka">(.*?)</section>', html, re.S).group(1)
    tekst = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<svg.*?</svg>", "", okladka, flags=re.S))).strip()
    m = dane.liczby_opisowe()["daty"]
    assert tekst == (f"Aneks liczbowy Dokument towarzyszący raportowi „Raport porównawczy anonimizacji” "
                     f"Wersja metodyki: prerejestracja-1 (zamrożona {m['zamrozenie']}) Data raportu: {m['raport']}")
    assert "Privatizer by Legal Geek – Aneks liczbowy · s." in html and "<title>Privatizer by Legal Geek – Aneks liczbowy</title>" in html


# ------------------------------------------------------------------ Privatizer nie jest pierwszy

def _html_podsumowania(r: Raport, tmp_path: Path) -> str:
    (tmp_path / "10-podsumowanie.md").write_text((buduj.ROZDZIALY / "10-podsumowanie.md").read_text(encoding="utf-8"), encoding="utf-8")
    html = buduj.zloz_html(r, tmp_path)
    sekcja = html[html.index(">Podsumowanie</h1>"):]
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", sekcja))


def _raport_privatizer_drugi() -> Raport:
    """Fikstury z `privatizer-tekst` na miejscu 2. i 1. miejscem innego uczestnika (oraz `privatizer-model`, którego fikstury nie mają)."""
    r = wczytaj(FIKSTURY / "zbiorcze", FIKSTURY / "czas-m1")
    t = {w.uczestnik: w for w in r.rankingi["tekst"]}
    t["privatizer-tekst"].miejsce, t["privatizer-tekst"].suma, t["privatizer-tekst"].suma_ci = 2, 700.0, (690.0, 710.0)
    t["beta"].miejsce, t["beta"].suma, t["beta"].suma_ci = 1, 780.7, (770.0, 790.0)
    model = Wiersz("privatizer-model", 9, [], 500.0, (490.0, 510.0), dict(t["beta"].testy), dokumenty=800, z_wyciekiem=700)
    r.rankingi["tekst"].append(model)
    return r


def test_podsumowanie_privatizer_drugi_nie_drukuje_ujemnej_roznicy(tmp_path):
    tekst = _html_podsumowania(_raport_privatizer_drugi(), tmp_path)
    assert "Privatizer ma o 80,7 pkt mniej" in tekst and "pierwszy w kolejności" in tekst and "zajmuje miejsce 2" in tekst
    assert not re.search(r"[-−]\s?\d[\d\s,]*pkt", tekst)  # nigdy „-80,7 pkt”
    assert "drugi w kolejności" not in tekst.split("Silnik na tekście")[0].split("Ranking tekstu")[1].split("Ranking plików")[0]


def test_podsumowanie_privatizer_pierwszy_pisze_wiecej(tmp_path):
    r = _raport_privatizer_drugi()
    t = {w.uczestnik: w for w in r.rankingi["tekst"]}
    t["privatizer-tekst"].miejsce, t["privatizer-tekst"].suma, t["privatizer-tekst"].suma_ci = 1, 900.0, (890.0, 910.0)
    t["beta"].miejsce = 2
    tekst = _html_podsumowania(r, tmp_path)
    assert "Privatizer ma o 119,3 pkt więcej" in tekst and "drugi w kolejności" in tekst and "nie nachodzą na siebie" in tekst
