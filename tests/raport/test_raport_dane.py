"""Testy modelu danych raportu PDF (`raport.dane`): formatery PL, wczytanie fikstur zbiorczych (n/d, remisy, aneks),
brak opcjonalnych plików i porównanie trybu domyślnego z „Maksymalną ochroną”. Fikstury: małe syntetyczne wycinki w formacie agregacji."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from raport import dane

from raport.dane import Test, Wiersz, etykieta_miejsca, liczba, porownanie_trybow, przedzial, procent, wczytaj

FIKSTURY = Path(__file__).parent / "fixtures"
NBSP = " "


@pytest.fixture(scope="module")
def raport():
    return wczytaj(FIKSTURY / "zbiorcze")


def test_liczba_format_pl():
    assert liczba(772.4) == "772,4"
    assert liczba(12345.6) == f"12{NBSP}345,6"
    assert liczba(None) == "n/d"
    assert liczba(3.0, 0) == "3"


def test_procent_i_przedzial():
    assert procent(0.1234) == "12,3%"
    assert procent(None) == "n/d"
    assert przedzial((766.2, 777.9)) == "[766–778]"
    assert przedzial(None) == "n/d"


def test_nieliczony_test_to_none(raport):
    w = next(x for x in raport.rankingi["pliki"] if x.uczestnik == "plik-b")
    assert w.testy["P5"].wartosc is None
    assert w.testy["P5"].pkt is None and w.testy["P5"].ci is None
    assert w.testy["P4"].wartosc is not None
    assert isinstance(w.testy["P4"], Test)


def test_wiersz_glowny(raport):
    w = raport.rankingi["tekst"][0]
    assert (w.uczestnik, w.miejsce, w.remis_z) == ("privatizer-tekst", 1, [])
    assert w.suma == pytest.approx(772.4) and w.suma_ci == (766.2, 777.9)
    assert w.testy["T1"].ci[0] < w.testy["T1"].wartosc < w.testy["T1"].ci[1]
    assert w.testy["P1"].wartosc is None  # pusta komórka = nieliczony


def test_aneks_osobno_od_rankingu(raport):
    assert [w.uczestnik for w in raport.aneks["tekst"]] == ["privatizer-tekst-maks"]
    assert all(w.miejsce is not None for r in raport.rankingi.values() for w in r)
    assert raport.aneks["tekst"][0].miejsce is None
    assert "privatizer-tekst-maks" not in {w.uczestnik for w in raport.rankingi["tekst"]}


def test_remis_trzech_uczestnikow(raport):
    wiersze = raport.rankingi["tekst"]
    etykiety = {w.uczestnik: etykieta_miejsca(w, wiersze) for w in wiersze}
    assert etykiety["delta"] == etykiety["epsilon"] == etykiety["zeta"] == "4–6 (remis)"
    assert etykiety["privatizer-tekst"] == "1" and etykiety["gamma"] == "3"


def test_etykieta_aneks_bez_miejsca(raport):
    w = raport.aneks["tekst"][0]
    assert etykieta_miejsca(w, raport.aneks["tekst"]) == "–"


def test_remis_dwoch_z_roznymi_miejscami():
    a = Wiersz("a", 12, ["b"], 1.0, (0.0, 2.0), {})
    b = Wiersz("b", 13, ["a"], 1.0, (0.0, 2.0), {})
    assert etykieta_miejsca(a, [a, b]) == etykieta_miejsca(b, [a, b]) == "12–13 (remis)"


def test_brak_czas_csv_daje_pusta_liste(raport):
    assert raport.czas == []


def test_dodatkowe_tabele(raport):
    assert raport.per["format"][0]["format"] == "docx" and raport.per["format"][0]["dokumenty"] == 10
    assert raport.per["jezyk"] == [] and raport.per["typ"] == []  # brak pliku => []
    assert raport.wrazliwosc[0]["suma"] == pytest.approx(800.1)
    assert raport.pomocnicze and raport.w_zakresie
    assert raport.niekompletne == [{"ranking": "pliki", "uczestnik": "plik-b", "powod": "P5 nieliczony"}]
    assert raport.odcisk[0]["poziom"] == "tekst"
    assert len(raport.przyklady) == 2 and raport.przyklady[0]["id"] == "pl-t-0001"


def test_wersje_z_czas_m1(raport):
    # domyślnie: katalog sąsiedni `czas-m1` (w fiksturach nie istnieje obok `zbiorcze`? – tu istnieje)
    assert raport.wersje["privatizer-tekst/tekst"]["wersje"]["narzedzie"] == "1.0"


def test_wersje_bez_katalogu_czas(tmp_path):
    shutil.copytree(FIKSTURY / "zbiorcze", tmp_path / "zbiorcze")
    r = wczytaj(tmp_path / "zbiorcze")
    assert r.wersje == {}
    r2 = wczytaj(tmp_path / "zbiorcze", czas=FIKSTURY / "czas-m1")
    assert "privatizer-tekst/tekst" in r2.wersje


def test_porownanie_trybow(raport):
    w = porownanie_trybow(raport)
    def v(rank, etykieta):
        return next(x for x in w if x["ranking"] == rank and x["wiersz"] == etykieta)
    t = v("tekst", "Wyciekłe wartości")
    assert (t["domyslny"], t["maks"]) == (140, 10)
    assert (v("tekst", "w tym kwoty")["domyslny"], v("tekst", "w tym kwoty")["maks"]) == (40, 0)
    assert (v("tekst", "Wyciek bez kwot")["domyslny"], v("tekst", "Wyciek bez kwot")["maks"]) == (100, 10)
    assert v("tekst", "Dokumenty z wyciekiem")["domyslny"] == 12
    assert v("tekst", "Dokumenty z wyciekiem")["maks"] == 2
    assert v("pliki", "Wyciek bez kwot")["domyslny"] == 60 and v("pliki", "Wyciek bez kwot")["maks"] == 20


def test_porownanie_trybow_brak_kategorii_to_none_nie_zero(tmp_path):
    """Uczestnik bez wiersza KWOTA (albo z pustą liczbą wyciekłych) ma „n/d”, nie 0 – brak pomiaru to nie brak wycieku."""
    shutil.copytree(FIKSTURY / "zbiorcze", tmp_path / "z")
    plik = tmp_path / "z" / "per_kategoria.csv"
    linie = [l for l in plik.read_text(encoding="utf-8").splitlines() if not l.startswith("tekst,privatizer-tekst-maks,KWOTA")]
    plik.write_text("\n".join(linie) + "\n", encoding="utf-8")
    w = porownanie_trybow(wczytaj(tmp_path / "z"))
    v = {(x["ranking"], x["wiersz"]): x for x in w}
    assert v[("tekst", "w tym kwoty")]["maks"] is None and v[("tekst", "w tym kwoty")]["domyslny"] == 40
    assert v[("tekst", "Wyciek bez kwot")]["maks"] == 10  # reszta kategorii policzona
    assert v[("tekst", "Wyciekłe wartości")]["maks"] == 10


def test_porownanie_trybow_pusta_wartosc_kategorii_to_none(tmp_path):
    shutil.copytree(FIKSTURY / "zbiorcze", tmp_path / "z")
    plik = tmp_path / "z" / "per_kategoria.csv"
    tekst = plik.read_text(encoding="utf-8").replace("tekst,privatizer-tekst-maks,ADRES,1000,10,", "tekst,privatizer-tekst-maks,ADRES,1000,,")
    plik.write_text(tekst, encoding="utf-8")
    v = {(x["ranking"], x["wiersz"]): x for x in porownanie_trybow(wczytaj(tmp_path / "z"))}
    assert v[("tekst", "Wyciek bez kwot")]["maks"] is None
    assert v[("tekst", "Wyciekłe wartości")]["maks"] is None
    assert v[("tekst", "w tym kwoty")]["maks"] == 0


def test_kategorie_trybow_wspolny_pomocnik(raport):
    from raport.dane import kategorie_trybow
    kat = kategorie_trybow(raport, "tekst")
    assert set(kat) == {"privatizer-tekst", "privatizer-tekst-maks"}
    assert kat["privatizer-tekst"]["KWOTA"]["wyciekle"] == 40
    assert kategorie_trybow(raport, "nie-ma") == {}


def test_wiersz_ma_bledy_odmowy_nieobslugiwane_i_uwagi():
    r = wczytaj(FIKSTURY / "wykresy")
    plik = {w.uczestnik: w for w in r.rankingi["pliki"]}
    assert (plik["privatizer-plik"].bledy, plik["privatizer-plik"].odmowy) == (1, 3)
    assert plik["plik-b"].nieobslugiwane == 7 and plik["plik-b"].bledy is None
    assert plik["plik-b"].uwagi == ""


def test_wagi_testow_z_metodyki():
    from raport.dane import wagi_testow
    w = wagi_testow()
    assert w["T1"] == 350 and w["P7"] == 50 and w["T6"] == 50


def test_odmiana_i_ile():
    from raport.dane import ile, odmiana
    f = ("teście", "testach", "testach")
    assert [odmiana(n, *f) for n in (1, 2, 4, 5, 12, 14, 22, 0)] == ["teście", "testach", "testach", "testach", "testach", "testach", "testach", "testach"]
    assert odmiana(1, "język", "języki", "języków") == "język" and odmiana(3, "język", "języki", "języków") == "języki"
    assert odmiana(12, "język", "języki", "języków") == "języków" and odmiana(22, "język", "języki", "języków") == "języki"
    assert ile(1, "teście", "testach", "testach") == "1 teście" and ile(None, "a", "b", "c") == "n/d"


def test_sekundy_jedna_funkcja_dla_malych_wartosci():
    assert dane.sekundy(None) == "n/d" and dane.sekundy(2.345) == "2,35" and dane.sekundy(0.0123) == "0,012"
    assert dane.sekundy(0.00055) == "0,00055" and dane.sekundy(0.0005) == "0,00050"


def test_wykres_i_tabela_szybkosci_pokazuja_te_sama_mala_wartosc():
    from raport import tabele, wykresy
    r = dane.Raport()
    r.rankingi["tekst"] = [dane.Wiersz("scrubadub", 1, [], 1.0, (1.0, 1.0), {})]
    r.czas = [{"ranking": "tekst", "uczestnik": "scrubadub", "s_na_strone": 0.00055, "dokumenty_proby": 3, "awarie": 0}]
    assert "0,00055" in tabele.szybkosc(r, "tekst") and "0,00055" in wykresy.szybkosc(r, "tekst")


def test_ujemne_roznice_i_przedzialy_z_minusem_typograficznym():
    assert dane.roznica(-12.26) == "−12,3" and dane.roznica(-0.01) == "0,0" and dane.roznica(None) == "n/d" and dane.roznica(3.0) == "3,0"
    assert dane.przedzial((-18.3, -12.2), 1) == "[−18,3; −12,2]" and dane.przedzial((766, 778)) == "[766–778]" and dane.przedzial((-1.0, 2.0), 0) == "[−1; 2]"
    assert dane.przedzial(None) == "n/d" and dane.przedzial((None, 1.0)) == "n/d"


def test_pozycja_szybkosci_i_n_d_bez_pomiaru():
    r = dane.Raport()
    r.rankingi["pliki"] = [dane.Wiersz(u, i, [], 1.0, (1.0, 1.0), {"P7": dane.Test(None, 7.5, None)}) for i, u in enumerate(("a", "b", "c"), 1)]
    r.czas = [{"ranking": "pliki", "uczestnik": "a", "s_na_strone": 6.4}, {"ranking": "pliki", "uczestnik": "b", "s_na_strone": 0.2}, {"ranking": "pliki", "uczestnik": "c", "s_na_strone": None}]
    p = dane.pozycja_szybkosci(r, "pliki", "a")
    assert (p["miejsce"], p["z"], p["s_na_strone"], p["pkt"], p["maks"]) == (2, 2, 6.4, 7.5, dane.wagi_testow()["P7"])
    assert dane.pozycja_szybkosci(r, "pliki", "c") is None and dane.pozycja_szybkosci(r, "pliki", "nie-ma") is None


def test_zmiana_rankingu_zauwaza_zmiany_remisu():
    def w(u, m, remis=()):
        return dane.Wiersz(u, m, list(remis), 100.0 - m, (0.0, 1.0), {})
    r = dane.Raport()
    r.rankingi["tekst"] = [w("a", 1), w("b", 2), w("c", 3), w("d", 4, ["e"]), w("e", 5, ["d"])]
    r.ranking_bez_example["tekst"] = [w("a", 1), w("b", 2), w("c", 3, ["d"]), w("d", 4, ["c"]), w("e", 5)]
    z = dane.zmiana_rankingu(r, "tekst")
    assert z["zmienione_miejsca"] == 0  # numery miejsc te same
    assert [(e["uczestnik"], e["glowny"], e["wariant"]) for e in z["zmiany_etykiet"]] == [
        ("c", "3", "3–4 (remis)"), ("d", "4–5 (remis)", "3–4 (remis)"), ("e", "4–5 (remis)", "5")]
    assert z["zmienione_etykiety"] == 3


def test_przegrywa_ma_wymiar_miejsca_w_dokumencie():
    from raport import tabele
    def w(u, m):
        return dane.Wiersz(u, m, [], 1.0, (1.0, 1.0), {})
    r = dane.Raport()
    r.rankingi["tekst"] = [w("privatizer-tekst", 1), w("inny", 2)]
    r.per["miejsce"] = [
        {"ranking": "tekst", "uczestnik": "privatizer-tekst", "miejsce": "naglowek", "wartosci": 40, "wyciekle": 10, "odsetek_wyciekow": 0.25},
        {"ranking": "tekst", "uczestnik": "inny", "miejsce": "naglowek", "wartosci": 40, "wyciekle": 4, "odsetek_wyciekow": 0.10},
        {"ranking": "tekst", "uczestnik": "privatizer-tekst", "miejsce": "tabela", "wartosci": 30, "wyciekle": 1, "odsetek_wyciekow": 0.03},
        {"ranking": "tekst", "uczestnik": "inny", "miejsce": "tabela", "wartosci": 30, "wyciekle": 3, "odsetek_wyciekow": 0.10}]
    assert [x["wycinek"] for x in tabele.przewagi(r, "miejsce", "tekst")] == ["naglowek"]
    assert tabele.liczba_przewag(r, "miejsce", "tekst") == 1 and tabele.liczba_przewag(r, "miejsce", "pliki") is None
    html = tabele.przegrywa(r, "miejsce", "tekst")
    assert "Miejsce w dokumencie" in html and "nagłówek" in html and "25,0%" in html and "15,0&nbsp;p.p." in html
