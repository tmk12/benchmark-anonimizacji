"""Testy składu HTML → PDF (`raport.buduj`): rozdziały + Jinja2, rejestry tabel/wykresów, PDF z Chromium, stopka, CLI i kontrola."""
from __future__ import annotations

from pathlib import Path

import re

import pytest

from raport import buduj
from raport.dane import wczytaj

FIKSTURY = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def raport():
    return wczytaj(FIKSTURY / "zbiorcze", FIKSTURY / "czas-m1")


@pytest.fixture(scope="module")
def szkielet(tmp_path_factory):
    """Sam rozdział szkieletowy: skład sprawdza się na nim, a nie na rozdziałach z wynikami (te wymagają pełnych danych)."""
    katalog = tmp_path_factory.mktemp("szkielet")
    (katalog / "00-szkielet.md").write_text(
        "# Szkielet raportu\n\nRozdział tymczasowy: sprawdza skład PDF (polskie znaki ąęłńóśźż, stopka, spis treści).\n", encoding="utf-8")
    return katalog


def test_zloz_html_rozdzial_szkieletowy(raport, szkielet):
    html = buduj.zloz_html(raport, szkielet)
    assert "Privatizer by Legal Geek" in html
    assert 'id="spis"' in html
    assert "<h1" in html and "ąęłńóśźż" in html


def test_nieznana_tabela_i_wykres_to_blad(raport, tmp_path):
    for fn in ("tabela", "wykres"):
        (tmp_path / "01-x.md").write_text(f"# X\n\n{{{{ {fn}('nie-ma') }}}}\n", encoding="utf-8")
        with pytest.raises(KeyError, match="nie-ma"):
            buduj.zloz_html(raport, tmp_path)


def test_tabela_i_wykres_przekazuja_argumenty(raport, tmp_path, monkeypatch):
    monkeypatch.setitem(buduj.TABELE, "t", lambda r, a, b=0: f"<table><tr><td>t{a}{b}</td></tr></table>")
    monkeypatch.setitem(buduj.WYKRESY, "w", lambda r, *a, **kw: f'<svg id="w{a[0]}{kw["k"]}"></svg>')
    (tmp_path / "01-x.md").write_text("# X\n\n{{ tabela('t', 5, b=7) }}\n\n{{ wykres('w', 1, k='z') }}\n", encoding="utf-8")
    html = buduj.zloz_html(raport, tmp_path)
    assert "<td>t57</td>" in html and '<svg id="w1z">' in html


def test_rozdzialy_w_kolejnosci_nazw(raport, tmp_path):
    (tmp_path / "02-b.md").write_text("# Drugi\n", encoding="utf-8")
    (tmp_path / "01-a.md").write_text("# Pierwszy\n", encoding="utf-8")
    html = buduj.zloz_html(raport, tmp_path)
    assert html.index("Pierwszy") < html.index("Drugi")


def test_kontrola_zrodel_blokuje_build(raport, tmp_path):
    (tmp_path / "01-x.md").write_text("# X\n\nwynik 72,4%\n", encoding="utf-8")
    with pytest.raises(buduj.BladKontroli):
        buduj.buduj(FIKSTURY / "zbiorcze", tmp_path / "r.pdf", rozdzialy=tmp_path)


@pytest.fixture(scope="module")
def pdf(tmp_path_factory, szkielet):
    cel = tmp_path_factory.mktemp("pdf") / "raport.pdf"
    html = cel.with_suffix(".html")
    buduj.buduj(FIKSTURY / "zbiorcze", cel, html=html, czas=FIKSTURY / "czas-m1", rozdzialy=szkielet)
    return cel


def test_pdf_powstaje_ze_stopka_i_polskimi_znakami(pdf):
    from pdfminer.high_level import extract_pages, extract_text
    assert pdf.is_file() and sum(1 for _ in extract_pages(str(pdf))) >= 1
    tekst = extract_text(str(pdf))
    assert "Privatizer by Legal Geek" in tekst
    assert "ąęłńóśźż" in tekst
    assert "Raport porównawczy anonimizacji" in tekst and re.search(r"· s\. \d+", tekst)
    assert pdf.with_suffix(".html").is_file()


def test_cli_publikacja_odrzuca_znaczniki(tmp_path):
    (tmp_path / "01-x.md").write_text("# X\n\nprzepis [HIPOTEZA]\n", encoding="utf-8")
    with pytest.raises(buduj.BladKontroli):
        buduj.buduj(FIKSTURY / "zbiorcze", tmp_path / "r.pdf", rozdzialy=tmp_path, publikacja=True)


def test_nieudana_kontrola_pdf_nie_nadpisuje_poprzedniego_pliku(raport, szkielet, tmp_path, monkeypatch):
    cel = tmp_path / "raport.pdf"
    cel.write_bytes(b"poprzedni dobry PDF")
    monkeypatch.setattr(buduj, "drukuj_pdf", lambda html, plik: Path(plik).write_bytes(b"nowy PDF"))
    monkeypatch.setattr(buduj, "kontroluj_pdf", lambda plik, publikacja=False: [f"{Path(plik).name}:1: zakaz"])
    with pytest.raises(buduj.BladKontroli) as e:
        buduj.buduj(FIKSTURY / "zbiorcze", cel, czas=FIKSTURY / "czas-m1", rozdzialy=szkielet)
    assert cel.read_bytes() == b"poprzedni dobry PDF"
    assert "raport.pdf:1" in str(e.value)
    assert [p.name for p in tmp_path.iterdir()] == ["raport.pdf"]  # po błędzie nie zostaje plik tymczasowy


def test_udana_kontrola_pdf_podmienia_plik(raport, szkielet, tmp_path, monkeypatch):
    cel = tmp_path / "raport.pdf"
    cel.write_bytes(b"stary")
    monkeypatch.setattr(buduj, "drukuj_pdf", lambda html, plik: Path(plik).write_bytes(b"nowy PDF"))
    monkeypatch.setattr(buduj, "kontroluj_pdf", lambda plik, publikacja=False: [])
    buduj.buduj(FIKSTURY / "zbiorcze", cel, czas=FIKSTURY / "czas-m1", rozdzialy=szkielet)
    assert cel.read_bytes() == b"nowy PDF"
    assert [p.name for p in tmp_path.iterdir()] == ["raport.pdf"]


@pytest.fixture()
def katalog_aneksu(tmp_path):
    katalog = tmp_path / "aneks"
    katalog.mkdir()
    (katalog / "00-aneks.md").write_text("# Aneks liczbowy\n\nTreść aneksu: ąęłńóśźż.\n", encoding="utf-8")
    return katalog


def test_cli_cel_aneks_daje_dwa_pdf(szkielet, katalog_aneksu, tmp_path, monkeypatch):
    from pdfminer.high_level import extract_text
    monkeypatch.setattr(buduj, "ANEKS", katalog_aneksu)
    monkeypatch.setattr(buduj, "ROZDZIALY", szkielet)
    glowny, aneks = tmp_path / "raport.pdf", tmp_path / "aneks.pdf"
    kod = buduj.main(["--wyniki", str(FIKSTURY / "zbiorcze"), "--czas", str(FIKSTURY / "czas-m1"),
                      "--cel", str(glowny), "--cel-aneks", str(aneks), "--html-aneks", str(tmp_path / "aneks.html")])
    assert kod == 0 and glowny.is_file() and aneks.is_file() and (tmp_path / "aneks.html").is_file()
    t_glowny, t_aneks = extract_text(str(glowny)), extract_text(str(aneks))
    assert "Raport porównawczy anonimizacji" in t_glowny and "Aneks liczbowy" not in t_glowny
    assert t_aneks.lstrip().startswith("Aneks liczbowy") and "Dokument towarzyszący raportowi" in t_aneks
    assert "Privatizer by Legal Geek – Aneks liczbowy · s." in t_aneks


def test_nieudana_kontrola_aneksu_nie_nadpisuje_poprzedniego_pliku(katalog_aneksu, tmp_path, monkeypatch):
    cel = tmp_path / "aneks.pdf"
    cel.write_bytes(b"poprzedni dobry aneks")
    monkeypatch.setattr(buduj, "drukuj_pdf", lambda html, plik: Path(plik).write_bytes(b"nowy PDF"))
    monkeypatch.setattr(buduj, "kontroluj_pdf", lambda plik, publikacja=False: [f"{Path(plik).name}:1: zakaz"])
    with pytest.raises(buduj.BladKontroli) as e:
        buduj.buduj(FIKSTURY / "zbiorcze", cel, czas=FIKSTURY / "czas-m1", rozdzialy=katalog_aneksu, tytul=buduj.TYTUL_ANEKSU, towarzyszy=buduj.TYTUL_RAPORTU)
    assert cel.read_bytes() == b"poprzedni dobry aneks" and "aneks.pdf:1" in str(e.value)
    assert [p.name for p in tmp_path.iterdir() if p.is_file()] == ["aneks.pdf"]


def test_kontrola_zrodel_aneksu_blokuje_build(katalog_aneksu, tmp_path):
    (katalog_aneksu / "01-x.md").write_text("# X\n\nwynik 72,4%\n", encoding="utf-8")
    with pytest.raises(buduj.BladKontroli):
        buduj.buduj(FIKSTURY / "zbiorcze", tmp_path / "aneks.pdf", rozdzialy=katalog_aneksu, tytul=buduj.TYTUL_ANEKSU)
