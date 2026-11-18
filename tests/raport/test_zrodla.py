"""Testy rejestru źródeł prawnych (`raport/zrodla.md`, `raport.zrodla`) i rozdziału „Dlaczego to ważne”: każdy akt cytowany w rozdziale ma wiersz
w rejestrze, statusy z protokołu źródeł, aneks „Źródła prawne” bez notatek weryfikacyjnych, odesłania z rozdziału „Wdrożenie”, blokada publikacji."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from raport import buduj, kontrola, tabele
from raport.dane import Raport
from raport.zrodla import KOLUMNY, STATUS, oznaczenia, oznaczenia_rejestru, wczytaj_rejestr

ROZDZIAL = buduj.ROZDZIALY / "20-dlaczego.md"


def _rejestr(tmp_path: Path, *wiersze: list[str]) -> Path:
    plik = tmp_path / "zrodla.md"
    linie = ["# R", "", "| " + " | ".join(KOLUMNY) + " |", "|" + "---|" * len(KOLUMNY)] + ["| " + " | ".join(w) + " |" for w in wiersze]
    plik.write_text("\n".join(linie) + "\n", encoding="utf-8")
    return plik


def _wiersz(akt: str, publikator: str, status: str = "[ZWERYFIKOWANE: EUR-Lex, dostęp: 2026-11-13]") -> list[str]:
    return [akt, publikator, "art. 1", "2026-11-13", "EUR-Lex", "https://eur-lex.europa.eu/x", status, "notatka"]


# ------------------------------------------------------------------ oznaczenia aktów

def test_oznaczenia_akty_ue_sprawy_i_publikatory():
    tekst = ("art. 5 rozporządzenia (UE) 2016/679, dyrektywa (UE) 2022/2555, wyrok w sprawie C-413/23 P i T‑557/20, "
             "ustawa (Dz.U. z 2024 r. poz. 1564 ze zm.), data 4.5.2016, dzień 2026-11-13")
    assert oznaczenia(tekst) == {"2016/679", "2022/2555", "C-413/23", "T-557/20", "Dz.U. 2024 poz. 1564"}


def test_oznaczenia_rejestru_rozwija_pozycje_rocznika(tmp_path):
    w = wczytaj_rejestr(_rejestr(tmp_path, _wiersz("Ustawa X", "t.j. Dz.U. z 2024 r. poz. 1564, ze zm.: Dz.U. z 2026 r. poz. 370, 846, 1290")))
    assert {"Dz.U. 2024 poz. 1564", "Dz.U. 2026 poz. 370", "Dz.U. 2026 poz. 846", "Dz.U. 2026 poz. 1290"} <= oznaczenia_rejestru(w)


def test_wczytaj_rejestr_pomija_separator_i_sprawdza_naglowek(tmp_path):
    w = wczytaj_rejestr(_rejestr(tmp_path, _wiersz("Rozporządzenie (UE) 2016/679", "Dz.Urz. UE L 119")))
    assert len(w) == 1 and w[0]["Akt / źródło"] == "Rozporządzenie (UE) 2016/679" and w[0]["Uwagi"] == "notatka"
    zly = tmp_path / "zly.md"
    zly.write_text("| Akt | Status |\n|---|---|\n| a | b |\n", encoding="utf-8")
    with pytest.raises(ValueError):
        wczytaj_rejestr(zly)


# ------------------------------------------------------------------ rejestr w repozytorium vs rozdział

def test_kazdy_akt_z_rozdzialu_ma_wiersz_w_rejestrze():
    cytowane = oznaczenia(ROZDZIAL.read_text(encoding="utf-8"))
    assert {"2016/679", "2022/2554", "2022/2555", "2024/2847", "2024/1689", "C-413/23"} <= cytowane   # parser widzi akty z zakresu rozdziału
    assert cytowane - oznaczenia_rejestru(wczytaj_rejestr()) == set()


def test_brak_wiersza_w_rejestrze_jest_wykryty(tmp_path):
    w = wczytaj_rejestr(_rejestr(tmp_path, _wiersz("Rozporządzenie (UE) 2016/679", "Dz.Urz. UE L 119")))
    assert oznaczenia("art. 21 dyrektywy (UE) 2022/2555 i RODO 2016/679") - oznaczenia_rejestru(w) == {"2022/2555"}


def test_wiersze_rejestru_kompletne_ze_statusem_z_protokolu():
    wiersze = wczytaj_rejestr()
    assert wiersze
    for w in wiersze:
        assert all(w[k] for k in KOLUMNY), w["Akt / źródło"]
        assert STATUS.fullmatch(w["Status"]), w["Status"]
        assert w["URL"] == "–" or w["URL"].startswith("https://"), w["URL"]
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", w["Stan na"])
        assert "/home/" not in w["Uwagi"] and "/Users/" not in w["Uwagi"]


def test_rozdzial_ma_tylko_proste_znaczniki_rozpoznawane_przez_kontrole():
    tekst = ROZDZIAL.read_text(encoding="utf-8")
    for znacznik in re.findall(r"\[[A-ZĄĆĘŁŃÓŚŹŻ ]{6,}[^\]]*\]", tekst):
        assert re.search(kontrola.ZNACZNIKI[0], znacznik), znacznik


# ------------------------------------------------------------------ aneks i publikacja

def test_aneks_zrodel_bez_uwag_z_odnosnikami(monkeypatch, tmp_path):
    plik = _rejestr(tmp_path, _wiersz("Rozporządzenie (UE) 2016/679", "Dz.Urz. UE L 119"),
                    ["Dokument producenta", "20 października 2026 r.", "pkt 1", "2026-11-13", "dokument producenta", "–", "[NIE DOTYCZY]", "notatka"])
    monkeypatch.setattr(tabele, "wczytaj_rejestr", lambda: wczytaj_rejestr(plik))
    html = tabele.zrodla_prawne(Raport())
    assert html.lstrip().startswith("<table") and "notatka" not in html
    assert '<a href="https://eur-lex.europa.eu/x">EUR-Lex</a>' in html and "dokument producenta" in html and "<a href=\"–\"" not in html


def test_niezweryfikowany_wiersz_rejestru_blokuje_publikacje_pdf(monkeypatch, tmp_path):
    plik = _rejestr(tmp_path, _wiersz("Ustawa X", "Dz.U. z 2026 r. poz. 1", "[NIEZWERYFIKOWANE]"))
    monkeypatch.setattr(tabele, "wczytaj_rejestr", lambda: wczytaj_rejestr(plik))
    tekst = re.sub(r"<[^>]+>", " ", tabele.zrodla_prawne(Raport()))
    monkeypatch.setattr(kontrola, "tekst_pdf", lambda pdf: tekst)
    assert kontrola.kontroluj_pdf(tmp_path / "a.pdf") == []
    assert kontrola.kontroluj_pdf(tmp_path / "a.pdf", publikacja=True)


def test_rozdzialy_przechodza_kontrole_publikacyjna():
    # raport i aneks bez znaczników weryfikacji – wersja do publikacji
    assert kontrola.kontroluj_zrodla(buduj.ROZDZIALY, publikacja=True) == []
    assert kontrola.kontroluj_zrodla(buduj.ANEKS, publikacja=True) == []
    assert kontrola.kontroluj_zrodla(buduj.ROZDZIALY) == []
    assert kontrola.kontroluj_zrodla(buduj.ANEKS) == []


def test_wdrozenie_odsyla_do_rozdzialu_dlaczego():
    wdrozenie = (buduj.ROZDZIALY / "60-wdrozenie.md").read_text(encoding="utf-8")
    assert "rozdział o przepisach" not in wdrozenie and wdrozenie.count("rozdział „Dlaczego to ważne”") == 2
    assert ROZDZIAL.read_text(encoding="utf-8").startswith("# Dlaczego to ważne\n")


def test_rozdzial_dlaczego_nazwy_i_zakres():
    tekst = ROZDZIAL.read_text(encoding="utf-8")
    # Privatizer tylko w sekcji CRA; pełna nazwa przy pierwszym użyciu; bez porównań z innymi narzędziami i bez art. 16 u.z.n.k.
    sekcje = re.split(r"^## ", tekst, flags=re.M)
    assert [s.split("\n", 1)[0] for s in sekcje if "Privatizer" in s] == ["CRA: bezpieczeństwo samego narzędzia"]
    assert tekst.index("Privatizer by Legal Geek") == tekst.index("Privatizer")
    assert "art. 16" not in tekst


def test_rejestr_uzywa_krotkiej_formy_znacznika():
    """Długi wariant („[NIEZWERYFIKOWANE — …]”) mógłby w komórce tabeli PDF zawinąć się na dwa wiersze i umknąć kontroli."""
    tekst = (buduj.ROZDZIALY.parent / "zrodla.md").read_text(encoding="utf-8")
    znaczniki = re.findall(r"\[(?:NIEZWERYFIKOWANE|HIPOTEZA)[^\]\n]*\]", tekst)
    assert znaczniki and all(z in ("[NIEZWERYFIKOWANE]", "[HIPOTEZA]") for z in znaczniki), znaczniki
