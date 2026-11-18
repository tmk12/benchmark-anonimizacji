"""Testy kontroli domen zarezerwowanych w raporcie: wczytanie wyniku (`kontrola-domen/`), tabele (n/d, kolejność, sygnał), decyzje szablonu
z danych (przewaga w rodzinie Privatizera → ranking główny z wariantem w rozdziale) i degradacja bez pliku wyniku (sekcje pomijane)."""
from __future__ import annotations

import csv
import json
import re
import shutil
from pathlib import Path

import pytest

from raport import buduj, kontrola, tabele
from raport.dane import przedzial_procent, przewaga_domen, roznica_pp, sygnaly_domen, wczytaj, zmiana_rankingu

FIKSTURY = Path(__file__).parent / "fixtures"
KOLUMNY = ["ranking", "uczestnik", "aneks", "kategoria", "inna_n", "example_n", "example_wyciek_n", "example_odsetek", "example_ci_dol",
           "example_ci_gora", "test_n", "test_wyciek_n", "test_odsetek", "test_ci_dol", "test_ci_gora", "roznica", "roznica_ci_dol",
           "roznica_ci_gora", "pozostalych", "mediana_pozostalych", "mediana_ci_dol", "mediana_ci_gora", "kierunek", "sygnal"]


def _wiersz(ranking, u, kat, ex, te, sygnal, kierunek="nierozróżnialna", aneks=False, nd=False):
    roznica = te - ex
    w = dict.fromkeys(KOLUMNY, "")
    w.update(ranking=ranking, uczestnik=u, aneks=aneks, kategoria=kat, inna_n=0, example_n=100, test_n=80, pozostalych=3)
    if nd:
        return w
    w.update(example_odsetek=ex, example_ci_dol=max(0, ex - .05), example_ci_gora=ex + .05, example_wyciek_n=int(ex * 100),
             test_odsetek=te, test_ci_dol=max(0, te - .05), test_ci_gora=te + .05, test_wyciek_n=int(te * 80), roznica=roznica,
             roznica_ci_dol=roznica - .08, roznica_ci_gora=roznica + .08, mediana_pozostalych=0.0, mediana_ci_dol=0.0, mediana_ci_gora=0.01,
             kierunek=kierunek, sygnal=sygnal)
    return w


def _zapisz(katalog: Path, przewaga_privatizera: bool) -> None:
    katalog.mkdir(parents=True)
    wiersze = []
    for kat in ("EMAIL", "URL"):
        wiersze += [_wiersz("tekst", "privatizer-tekst", kat, 0.0, 0.0, "nie"),
                    _wiersz("tekst", "beta", kat, 0.4, 0.2, "nie", "mniejsza"),
                    _wiersz("tekst", "gamma", kat, 0.0, 0.8, "tak", "większa"),
                    _wiersz("tekst", "delta", kat, 0, 0, None, "", nd=True),
                    _wiersz("tekst", "privatizer-tekst-maks", kat, 0.0, 0.0, "nie", aneks=True),
                    _wiersz("pliki", "privatizer-plik", kat, 0.1, 0.4 if przewaga_privatizera else 0.1, "tak" if przewaga_privatizera else "nie",
                            "większa" if przewaga_privatizera else "nierozróżnialna"),
                    _wiersz("pliki", "plik-b", kat, 0.1, 0.1, "nie")]
    with (katalog / "kontrola_domen.csv").open("w", encoding="utf-8", newline="") as f:
        pis = csv.DictWriter(f, fieldnames=KOLUMNY)
        pis.writeheader()
        pis.writerows(wiersze)
    with (katalog / "ranking_bez_example.csv").open("w", encoding="utf-8", newline="") as f:
        pis = csv.writer(f)
        pis.writerow(["ranking", "uczestnik", "aneks", "miejsce", "remis_z", "suma", "suma_ci_dol", "suma_ci_gora"])
        for rk, u, m, suma in [("tekst", "privatizer-tekst", 1, 770.0), ("tekst", "beta", 2, 701.5), ("tekst", "gamma", 3, 650.0), ("tekst", "delta", 4, 500.0),
                               ("tekst", "epsilon", 5, 499.0), ("tekst", "zeta", 6, 498.0), ("tekst", "privatizer-tekst-maks", "", 900.0),
                               ("pliki", "privatizer-plik", 1, 590.0), ("pliki", "plik-b", 2, 151.0)]:
            pis.writerow([rk, u, u.endswith("maks"), m, "", suma, suma - 5, suma + 5])
    (katalog / "meta.json").write_text(json.dumps({"powtorzenia": 1000, "wartosci_inna_domena_trzon": {"EMAIL": 0, "URL": 0}}), encoding="utf-8")


@pytest.fixture()
def zbiorcze(tmp_path):
    kat = tmp_path / "zbiorcze"
    shutil.copytree(FIKSTURY / "wykresy", kat)
    return kat


def _sekcje(katalog: Path) -> Path:
    """Rozdział złożony wyłącznie z sekcji kontroli domen (z rozdziału Wyniki i z aneksu): fikstura nie ma pełnych danych reszty rozdziałów."""
    katalog.mkdir()
    wyniki = (buduj.ROZDZIALY / "40-wyniki.md").read_text(encoding="utf-8")
    aneks = (buduj.ANEKS / "90-aneksy-liczbowe.md").read_text(encoding="utf-8")
    (katalog / "40.md").write_text(wyniki[wyniki.index("{% if przewaga_domen(r) is not none %}"):], encoding="utf-8")
    (katalog / "90.md").write_text(aneks[aneks.index("{% if r.ranking_bez_example %}"):aneks.index("## Rankingi niekompletne")], encoding="utf-8")
    return katalog


def test_brak_wyniku_kontroli_domen_to_puste_dane_i_pominiete_sekcje(zbiorcze):
    r = wczytaj(zbiorcze, FIKSTURY / "czas-m1")
    assert r.kontrola_domen == [] and r.ranking_bez_example == {} and r.kontrola_domen_meta == {}
    assert przewaga_domen(r) is None and zmiana_rankingu(r, "tekst") is None
    html = buduj.zloz_html(r, _sekcje(zbiorcze.parent / "sekcje"))
    assert "Kontrola domen zarezerwowanych" not in html and "bez wartości example" not in html
    for rk in ("tekst", "pliki"):
        for t in (tabele.kontrola_domen(r, rk, "EMAIL"), tabele.ranking_bez_example(r, rk)):
            assert "n/d" in t and "nan" not in t.lower()


def test_wczytanie_i_przewaga_w_rodzinie_privatizera(zbiorcze):
    _zapisz(zbiorcze / "kontrola-domen", przewaga_privatizera=False)
    r = wczytaj(zbiorcze, FIKSTURY / "czas-m1")
    assert len(r.kontrola_domen) == 14 and r.kontrola_domen_meta["powtorzenia"] == 1000
    assert [w.uczestnik for w in r.ranking_bez_example["tekst"]][:2] == ["privatizer-tekst", "beta"]    # aneks poza rankingiem
    assert [x["uczestnik"] for x in sygnaly_domen(r, "tekst")] == ["gamma", "gamma"]
    assert przewaga_domen(r) is False                                                                      # sygnał tylko u uczestnika spoza rodziny
    _zapisz_ponownie(zbiorcze, True)
    assert przewaga_domen(wczytaj(zbiorcze, FIKSTURY / "czas-m1")) is True


def _zapisz_ponownie(zbiorcze: Path, przewaga: bool) -> None:
    shutil.rmtree(zbiorcze / "kontrola-domen")
    _zapisz(zbiorcze / "kontrola-domen", przewaga)


def test_tabela_kontroli_domen_kolejnosc_nd_i_bez_aneksu(zbiorcze):
    _zapisz(zbiorcze / "kontrola-domen", False)
    r = wczytaj(zbiorcze, FIKSTURY / "czas-m1")
    html = tabele.kontrola_domen(r, "tekst", "EMAIL")
    wiersze = re.findall(r"<tr>.*?</tr>", html, re.S)
    nazwy = [re.sub(r"<[^>]+>", "", w.split("</td>")[0]).replace("-", "") for w in wiersze[1:]]
    assert nazwy == ["privatizertekst", "beta", "gamma", "delta"]                    # kolejność miejsc, bez wariantu z aneksu
    assert "−" in wiersze[2] and "mniejsza" in wiersze[2]                       # kierunek odwrotny pokazany, nie ukryty
    assert wiersze[3].count(">tak<") == 1
    assert wiersze[4].count("n/d") >= 5 and "nan" not in html.lower()               # brak policzonych wartości = n/d


def test_formatery_roznicy():
    assert roznica_pp(-0.151) == "−15,1 p.p." and roznica_pp(0.0) == "0,0 p.p." and roznica_pp(-0.0001) == "0,0 p.p."
    assert roznica_pp(None) == "n/d" and przedzial_procent(None, 0.1) == "n/d"
    assert przedzial_procent(-0.183, -0.122) == "[−18,3; −12,2]"  # ujemne krańce: średnik, nie „–−”
    assert przedzial_procent(-0.05, 0.12) == "[−5,0; 12,0]" and przedzial_procent(0.099, 0.14) == "[9,9–14,0]"


def test_przewaga_privatizera_pokazuje_ranking_glowny_z_wariantem(zbiorcze):
    _zapisz(zbiorcze / "kontrola-domen", True)
    r = wczytaj(zbiorcze, FIKSTURY / "czas-m1")
    z = zmiana_rankingu(r, "tekst")
    assert z["lider_wariant"] == "privatizer-tekst" and z["to_samo_top3"] and z["zmienione_miejsca"] == 0
    assert z["najwieksza_zmiana"] == pytest.approx(2.4) and z["uczestnik_najwiekszej_zmiany"] == "privatizer-tekst"
    html = buduj.zloz_html(r, _sekcje(zbiorcze.parent / "sekcje"))
    assert "Sygnał przewagi wystąpił w rodzinie Privatizera" in html and "Ranking główny i wariant bez wartości" in html
    assert "Ranking bez wartości example.*" in html                                                     # aneks zawsze, gdy jest wariant
    assert not re.search(r"\bnan\b|\bNone\b", re.sub(r"<[^>]+>", " ", html))


def test_bez_przewagi_privatizera_wariant_tylko_w_aneksie(zbiorcze):
    _zapisz(zbiorcze / "kontrola-domen", False)
    html = buduj.zloz_html(wczytaj(zbiorcze, FIKSTURY / "czas-m1"), _sekcje(zbiorcze.parent / "sekcje"))
    assert "Żaden uczestnik rankingu z rodziny Privatizera nie ma sygnału przewagi" in html
    assert "Ranking główny i wariant bez wartości" not in html and "Ranking bez wartości example.*" in html
