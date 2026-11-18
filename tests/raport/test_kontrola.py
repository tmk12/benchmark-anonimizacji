"""Testy kontroli treści raportu (`raport.kontrola`): lista zakazów, reguła liczb w prozie, znaczniki weryfikacji, kontrola tekstu PDF."""
from __future__ import annotations

from pathlib import Path

import pytest

from raport.kontrola import kontroluj_pdf, kontroluj_zrodla


def _md(tmp_path: Path, tresc: str) -> Path:
    (tmp_path / "01-test.md").write_text(tresc, encoding="utf-8")
    return tmp_path


def test_liczba_dziesietna_z_procentem_to_jeden_blad(tmp_path):
    assert len(kontroluj_zrodla(_md(tmp_path, "# T\n\nwynik 72,4%\n"))) == 1


def test_wstawka_jinja_nie_jest_bledem(tmp_path):
    assert kontroluj_zrodla(_md(tmp_path, "# T\n\nwynik {{ procent(x) }} i {{ liczba(1234.5) }}\n")) == []


def test_liczba_calkowita_ponad_10_i_ulamek_to_bledy(tmp_path):
    assert kontroluj_zrodla(_md(tmp_path, "# T\n\nmamy 150 dokumentów\n"))
    assert kontroluj_zrodla(_md(tmp_path, "# T\n\nmamy 3,5 punktu\n"))
    assert kontroluj_zrodla(_md(tmp_path, "# T\n\nudział 5%\n"))


@pytest.mark.parametrize("zdanie", [
    "art. 32 ust. 1 RODO", "pkt 15 lit. a", "w roku 2026", "rozporządzenie 2016/679", "dyrektywa 2022/2555",
    "dziewięć testów i 7 kategorii",
])
def test_wyjatki_liczbowe(tmp_path, zdanie):
    assert kontroluj_zrodla(_md(tmp_path, f"# T\n\n{zdanie}\n")) == []


@pytest.mark.parametrize("zakazane", ["/home/ktos/x", "/Users/ktos"])
def test_zakazane_sciezki_domowe(tmp_path, zakazane):
    assert kontroluj_zrodla(_md(tmp_path, f"# T\n\ntekst {zakazane} koniec\n")), zakazane


def test_znaczniki_weryfikacji_tylko_w_publikacji(tmp_path):
    kat = _md(tmp_path, "# T\n\nprzepis [NIEZWERYFIKOWANE]\n\nteza [HIPOTEZA]\n")
    assert kontroluj_zrodla(kat) == []
    assert len(kontroluj_zrodla(kat, publikacja=True)) == 2


def test_blad_zawiera_plik_i_wiersz(tmp_path):
    blad = kontroluj_zrodla(_md(tmp_path, "# T\n\nwynik 72,4%\n"))[0]
    assert "01-test.md:3" in blad


def test_kontroluj_pdf_znajduje_sciezke(tmp_path, monkeypatch):
    import raport.kontrola as k
    monkeypatch.setattr(k, "tekst_pdf", lambda pdf: "Wynik ... /home/ktos/dev/x ... koniec")
    assert kontroluj_pdf(tmp_path / "a.pdf")
    monkeypatch.setattr(k, "tekst_pdf", lambda pdf: "Wynik 72,4% w tekście pdf – liczby w PDF są dozwolone")
    assert kontroluj_pdf(tmp_path / "a.pdf") == []


# ------------------------------------------------------------------ rozdział o przepisach: identyfikatory prawne i publikacja

@pytest.mark.parametrize("zdanie", [
    "motyw 26 RODO", "według motywu 26", "motywy 26–27", "art. 44–49 RODO", "art. 28-30 DORA", "pkt 75–77 wyroku", "art. 3 ust. 3–5 ustawy",
    "wyrok w sprawie C-413/23 P", "sprawa T‑557/20", "wyrok z dnia 4 września 2025 r.", "ustawa z dnia 26 maja 1982 r.",
    "stosuje się od 11 grudnia 2027 r.", "CELEX 32016R0679", "CELEX: 62023CJ0413", "Dz.Urz. UE L 119 z 4.5.2016, s. 1",
    "Dz. Urz. UE L 333 z 27.12.2022, s. 80", "Dz.U. z 2024 r. poz. 1564",
])
def test_wyjatki_identyfikatorow_prawnych(tmp_path, zdanie):
    assert kontroluj_zrodla(_md(tmp_path, f"# T\n\n{zdanie}\n")) == []


@pytest.mark.parametrize("zdanie", [
    "w ciągu 24 godzin", "mamy 150 dokumentów w maju", "do 12 maja", "motyw 26 i 150 dokumentów", "art. 28 i 150 stron",
    "C-413 to nie sygnatura, a 150 to liczba", "L 119 bez nazwy dziennika",
    "zgodnie z art. 33 – 72 godziny", "tabela 3 – 150 dokumentów", "pkt 5 - 99 przypadków", "art. 12a – 150 osób",
    "sprawa c-413/23 i 150 osób", "Dz.Urz. UE L 119 i 150 osób",
])
def test_wyjatki_prawne_nie_oslabiaja_reguly_liczb(tmp_path, zdanie):
    assert kontroluj_zrodla(_md(tmp_path, f"# T\n\n{zdanie}\n")), zdanie


def test_niezweryfikowane_blokuje_publikacje(tmp_path):
    kat = _md(tmp_path, "# T\n\nOrgan nadzoru rynku nie jest ustalony [NIEZWERYFIKOWANE].\n")
    assert kontroluj_zrodla(kat) == []
    bledy = kontroluj_zrodla(kat, publikacja=True)
    assert len(bledy) == 1 and "01-test.md:3" in bledy[0]


@pytest.mark.parametrize("znacznik", ["[NIEZWERYFIKOWANE — MCP niedostępny / brak wyniku]", "[HIPOTEZA — DO SPRAWDZENIA]"])
def test_pelne_warianty_znacznikow_tez_blokuja(tmp_path, znacznik, monkeypatch):
    kat = _md(tmp_path, f"# T\n\nteza {znacznik}\n")
    assert kontroluj_zrodla(kat) == [] and len(kontroluj_zrodla(kat, publikacja=True)) == 1
    import raport.kontrola as k
    monkeypatch.setattr(k, "tekst_pdf", lambda pdf: f"tabela źródeł {znacznik}")
    assert kontroluj_pdf(tmp_path / "a.pdf") == [] and kontroluj_pdf(tmp_path / "a.pdf", publikacja=True)


def test_status_zweryfikowane_nie_jest_znacznikiem(tmp_path):
    kat = _md(tmp_path, "# T\n\nstatus [ZWERYFIKOWANE: EUR-Lex, dostęp: 2026-11-13]\n")
    assert kontroluj_zrodla(kat, publikacja=True) == []
