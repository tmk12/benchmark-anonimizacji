"""Testy tabel raportu (`raport.tabele`): kolejność i remisy, „n/d” zamiast nan/0/pustej komórki, aneks osobno, rozbicia, przewagi,
wersje bez pól środowiska, układ w PDF (bez wylewania poza blok A4) i test na danych rzeczywistych (env PBENCH_RAPORT_WYNIKI)."""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from raport import buduj, kontrola, tabele
from raport.dane import wczytaj

FIKSTURY = Path(__file__).parent / "fixtures"
WSZYSTKIE = [("ranking", ("tekst",)), ("ranking", ("pliki",)), ("aneks_x1", ("tekst",)), ("aneks_x1", ("pliki",)),
             ("per", ("jezyk", "tekst")), ("per", ("format", "tekst")), ("per", ("typ", "tekst")), ("per", ("kategoria", "tekst")),
             ("per", ("miejsce", "tekst")), ("per", ("przypadek", "tekst")), ("szybkosc", ("tekst",)), ("szybkosc", ("pliki",)),
             ("wrazliwosc", ("tekst",)), ("wrazliwosc", ("pliki",)), ("tryby", ("tekst",)), ("tryby", ("pliki",)), ("wersje", ()), ("odcisk", ()),
             ("trudne_przypadki", ("tekst",)), ("w_zakresie", ("tekst",)), ("posrednie", ("tekst",)), ("posrednie", ("pliki",)), ("aplikacja_vs_modele", ("tekst",)),
             ("przegrywa", ("test", "tekst")), ("przegrywa", ("jezyk", "tekst")), ("przegrywa", ("szybkosc", "tekst")),
             ("przegrywa", ("kategoria", "tekst")), ("przegrywa", ("format", "pliki")),
             ("kontrola_domen", ("tekst", "EMAIL")), ("kontrola_domen", ("pliki", "URL")), ("ranking_bez_example", ("tekst",)), ("ranking_bez_example", ("pliki",)),
             ("przyklady", ("tekst",))]


@pytest.fixture(scope="module")
def raport():
    return wczytaj(FIKSTURY / "wykresy", FIKSTURY / "czas-m1")


def _wiersze(html: str) -> list[str]:
    return re.findall(r"<tr>.*?</tr>", html, re.S)


def _tekst(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def test_wszystkie_tabele_zarejestrowane():
    for nazwa in ("ranking", "per", "szybkosc", "wrazliwosc", "tryby", "aneks_x1", "wersje", "odcisk", "trudne_przypadki", "w_zakresie",
                  "aplikacja_vs_modele", "przegrywa"):
        assert nazwa in buduj.TABELE


@pytest.mark.parametrize("nazwa,args", WSZYSTKIE)
def test_brak_nan_i_pustych_komorek(raport, nazwa, args):
    """Review Focus 1: wartość nieliczona to „n/d”/„–”, nigdy `nan`, `None` ani pusta komórka."""
    html = buduj.TABELE[nazwa](raport, *args)
    assert html.lstrip().startswith("<table")
    assert not re.search(r"\bnan\b|\bNone\b|\binf\b", _tekst(html), re.I)
    assert not re.search(r"<td[^>]*>\s*</td>", html)


@pytest.mark.parametrize("nazwa,args", WSZYSTKIE)
def test_deterministyczne(raport, nazwa, args):
    assert buduj.TABELE[nazwa](raport, *args) == buduj.TABELE[nazwa](raport, *args)


def test_ranking_kolejnosc_miejsc_i_aneks_osobno(raport):
    html = buduj.TABELE["ranking"](raport, "tekst")
    kolejnosc = [re.sub(r"<[^>]+>", "", re.findall(r"<td[^>]*>(.*?)</td>", w, re.S)[1]) for w in _wiersze(html)[1:]]
    assert kolejnosc[:3] == ["privatizer-tekst", "beta", "gamma"]
    assert "tekst-<wbr>maks" not in html  # privatizer-tekst-maks jest w aneksie
    assert "privatizer-tekst-maks" in re.sub(r"<[^>]+>", "", buduj.TABELE["aneks_x1"](raport, "tekst"))
    assert "<strong>privatizer-<wbr>tekst</strong>" in html  # Privatizer wyróżniony pogrubieniem, nie kolorem


def test_ranking_remis_trzech_ma_etykiete_zakresu(raport):
    html = buduj.TABELE["ranking"](raport, "tekst")
    assert html.count("4–6<br><small>remis</small>") == 3  # delta, epsilon, zeta – remis łączy trzech uczestników


def test_ranking_liczby_po_polsku_i_przedzial(raport):
    t = _tekst(buduj.TABELE["ranking"](raport, "tekst"))
    assert "772,4" in t and "772.4" not in t
    assert re.search(r"\[\d+–\d+\]", t)


def test_ranking_pliki_p5_nd_i_uwaga_prerejestracja(raport):
    html = buduj.TABELE["ranking"](raport, "pliki")
    wiersz = next(w for w in _wiersze(html) if "plik-<wbr>b" in w)
    komorki = re.findall(r"<td[^>]*>(.*?)</td>", wiersz, re.S)
    assert "n/d" in komorki  # P5 nieliczony
    assert "P5: nie dotyczy" in wiersz and "prerejestracj" not in wiersz  # krótka uwaga w komórce (bez łamania „(prerejestracja )”), wyjaśnienie w przypisie
    assert "test P5 nie dotyczy uczestnika wg prerejestracji" in html
    assert "P5: nie dotyczy" not in next(w for w in _wiersze(html) if "<strong>privatizer-<wbr>plik</strong>" in w)


def test_ranking_bledy_odmowy_nieobslugiwane(raport):
    html = buduj.TABELE["ranking"](raport, "pliki")
    assert "1 / 3 / n/d" in _tekst(html)  # privatizer-plik: błędy 1, odmowy 3, nieobsługiwane brak w danych
    assert "n/d / n/d / 7" in _tekst(html)


def test_ranking_naglowki_z_maksimum_punktow(raport):
    t = _tekst(buduj.TABELE["ranking"](raport, "tekst"))
    assert "T1 /350" in t and "T6 /50" in t


def test_nieznany_ranking_to_tabela_n_d(raport):
    assert "n/d" in buduj.TABELE["ranking"](raport, "nie-ma")
    assert "n/d" in buduj.TABELE["per"](raport, "nie-ma", "tekst")


def test_per_jezyk_nd_i_kolejnosc_jezykow(raport):
    html = buduj.TABELE["per"](raport, "jezyk", "tekst")
    wiersze = _wiersze(html)[1:]
    assert [re.sub(r"<[^>]+>", "", w.split("</td>")[0]) for w in wiersze] == ["pl", "en", "es", "de", "fr"]
    assert "n/d" in wiersze[-1]  # delta/fr bez wartości
    assert "<strong>privatizer-<wbr>tekst</strong>" in html and 'class="num obrot"' in html


def test_per_przypadek_poza_punktacja_i_nd(raport):
    t = _tekst(buduj.TABELE["per"](raport, "przypadek", "tekst"))
    assert "rtl (poza punktacją)" in t and "homoglify (poza punktacją)" not in t
    assert "n/d" in t  # gamma bez wartości


def test_szybkosc_nd_dla_braku_pomiaru(raport):
    wiersz = next(w for w in _wiersze(buduj.TABELE["szybkosc"](raport, "tekst")) if "delta" in w)
    assert wiersz.count("n/d") >= 4
    assert "0,68" in _tekst(buduj.TABELE["szybkosc"](raport, "tekst"))


def test_tryby_uklad_zatwierdzony(raport):
    t = _tekst(buduj.TABELE["tryby"](raport, "tekst"))
    for etykieta in ("Tryb domyślny", "Maksymalna ochrona", "w tym kwoty", "Wyciek bez kwot", "Dokumenty z wyciekiem"):
        assert etykieta in t


def test_wersje_tylko_aplikacja_i_model(raport):
    t = _tekst(buduj.TABELE["wersje"](raport))
    assert "9.8.7b6" in t and "lgp-test" in t and "0.0.1rc2" in t
    assert "8765" not in t and "pro" not in re.sub(r"[A-Za-zĄąĘęŁłŃńÓóŚśŹźŻż]*pro[a-z]*", "", t)  # port i plan nie trafiają do raportu


def test_odcisk_hash_i_kreski(raport):
    html = buduj.TABELE["odcisk"](raport)
    assert 'class="hash">aa<' in html and "n/d" in html  # commit „None” → n/d
    assert "–" in html  # leptonica itd. nie dotyczą poziomu tekst


def test_przewagi_z_danych(raport):
    # fikstura: wszyscy mają te same punkty testów; przewaga tylko w szybkości (zeta 0,03 s < Privatizer 0,68 s)
    assert [x["wycinek"] for x in tabele.przewagi(raport, "test", "tekst")] == []
    szybkosc = tabele.przewagi(raport, "szybkosc", "tekst")
    assert len(szybkosc) == 1 and szybkosc[0]["inny"] == "zeta" and szybkosc[0]["privatizer"] == 0.68
    # po zmianie danych (beta bije Privatizera w T5) wycinek pojawia się, z kierunkiem „więcej = lepiej”
    beta = next(w for w in raport.rankingi["tekst"] if w.uczestnik == "beta")
    stare = beta.testy["T5"].pkt
    beta.testy["T5"].pkt = 999.0
    try:
        x = tabele.przewagi(raport, "test", "tekst")
        assert x[0]["wycinek"] == "T5" and x[0]["inny"] == "beta" and x[0]["roznica"] == pytest.approx(999.0 - raport.rankingi["tekst"][0].testy["T5"].pkt)
    finally:
        beta.testy["T5"].pkt = stare


def test_przewagi_pomija_warianty_privatizera_i_nieliczone(raport):
    inni = {x["inny"] for wymiar in ("test", "jezyk", "szybkosc", "kategoria", "typ") for x in tabele.przewagi(raport, wymiar, "tekst")}
    assert not any(u.startswith("privatizer") for u in inni)
    # kategoria: gamma/KWOTA nieliczona, więc nie jest „najlepsza”; beta ma lepszy odsetek wycieków? nie – Privatizer wyciekł mniej
    assert tabele.przewagi(raport, "kategoria", "tekst") == []


def test_przewagi_kierunek_mniej_lepiej_dla_wyciekow(raport):
    wiersze = [x for x in raport.per["kategoria"] if x["ranking"] == "tekst" and x["uczestnik"] == "beta" and x["kategoria"] == "ADRES"]
    stare = [x["odsetek_wyciekow"] for x in wiersze]
    for x in wiersze:
        x["odsetek_wyciekow"] = 0.01  # Privatizer ma 0,10 → beta lepsza (mniej wycieków)
    try:
        x = tabele.przewagi(raport, "kategoria", "tekst")
        assert [(y["wycinek"], y["inny"]) for y in x] == [("ADRES", "beta")]
    finally:
        for x, v in zip(wiersze, stare):
            x["odsetek_wyciekow"] = v


def test_przegrywa_brak_wierszy_to_informacja(raport):
    html = buduj.TABELE["przegrywa"](raport, "test", "tekst")
    assert "Brak wycinków, w których inny uczestnik ma lepszy wynik" in html


def test_aplikacja_vs_modele_suma_bez_t6_i_opisy(raport):
    # w fikstury nie ma uczestników z listy poza privatizer-tekst: tabela ma tylko jego wiersz, suma bez T6 = suma − pkt T6
    html = buduj.TABELE["aplikacja_vs_modele"](raport, "tekst")
    w = raport.rankingi["tekst"][0]
    assert tabele.suma_bez_szybkosci(w) == pytest.approx(w.suma - w.testy["T6"].pkt)
    assert "Suma bez T6" in html and "Silnik Privatizera" in html and "nie mają pomiaru czasu" in html


def test_html_escapuje_nazwy(raport):
    assert tabele._nazwa("<b>x&y") == "&lt;b&gt;x&amp;y"


def _wylewajace_sie(raport, tmp_path) -> list[str]:
    """Skład wszystkich tabel w Chromium przy szerokości bloku tekstu A4 (174 mm = 658 px): lista tabel i komórek, które wystają albo są ucięte."""
    pw = pytest.importorskip("playwright.sync_api")
    rozdz = tmp_path / "r"
    rozdz.mkdir()
    (rozdz / "10-test.md").write_text("# Test\n\n" + "\n\n".join(
        "{{ tabela('%s'%s) }}" % (n, "".join(", " + repr(a) for a in args)) for n, args in WSZYSTKIE) + "\n", encoding="utf-8")
    html = buduj.zloz_html(raport, rozdz)
    with pw.sync_playwright() as p:
        try:
            b = p.chromium.launch(executable_path=buduj._chromium(p), args=["--no-sandbox"])
        except Exception as e:  # brak Chromium – nie błąd testu
            pytest.skip(f"brak Chromium: {e}")
        try:
            strona = b.new_page(viewport={"width": 658, "height": 900})
            strona.set_content(html, wait_until="load")
            strona.emulate_media(media="print")
            return strona.evaluate("""() => [...document.querySelectorAll('main table')].flatMap((t, i) => {
                const w = [];
                if (t.getBoundingClientRect().right > 660) w.push('tabela ' + i + ' wylewa się: ' + t.getBoundingClientRect().right);
                t.querySelectorAll('th, td').forEach(c => { if (c.scrollWidth > c.clientWidth + 1) w.push('tabela ' + i + ' komórka ucięta: ' + c.textContent.slice(0, 30)); });
                return w; })""")
        finally:
            b.close()


def test_chromium_uklad_tabel_nie_wylewa_sie(raport, tmp_path):
    """Review Focus 3: szerokie tabele (13 kolumn, długie nazwy) mieszczą się w bloku tekstu A4 i nie ucinają komórek."""
    assert _wylewajace_sie(raport, tmp_path) == []


def test_rozdzialy_wynikow_przechodza_kontrole_zrodel():
    assert kontrola.kontroluj_zrodla(buduj.ROZDZIALY) == []
    assert kontrola.kontroluj_zrodla(buduj.ANEKS) == []


# ------------------------------------------------------------------ dane rzeczywiste

WYNIKI = os.environ.get("PBENCH_RAPORT_WYNIKI")


@pytest.mark.skipif(not WYNIKI, reason="brak PBENCH_RAPORT_WYNIKI (katalog zbiorczy z wynikami)")
def test_dane_rzeczywiste_miejsca_i_niezaleznosc_od_p5(tmp_path_factory):
    r = wczytaj(Path(WYNIKI))
    assert r.rankingi["tekst"][0].uczestnik == "privatizer-tekst" or min(r.rankingi["tekst"], key=lambda w: w.miejsce).uczestnik == "privatizer-tekst"
    pliki = {w.miejsce: w for w in r.rankingi["pliki"]}
    assert pliki[1].uczestnik == "privatizer-plik"
    # miejsca 3 i 4 nie zależą od P5: różnica sum > 100 (maks. P5 = 100 pkt, więc nieliczony P5 u miejsca 4 niczego nie odwraca)
    assert pliki[3].suma - pliki[4].suma > 100
    for nazwa, args in WSZYSTKIE:
        html = buduj.TABELE[nazwa](r, *args)
        assert not re.search(r"\bnan\b|\bNone\b", _tekst(html), re.I)
    html = buduj.TABELE["aplikacja_vs_modele"](r, "tekst")
    assert len(_wiersze(html)) == 1 + len(tabele.APLIKACJA_VS_MODELE)
    assert _wylewajace_sie(r, tmp_path_factory.mktemp("uklad")) == []
    tresc = buduj.zloz_html(r)
    assert not re.search(r"\bnan\b|\bNone\b", _tekst(re.sub(r"<style.*?</style>", "", tresc, flags=re.S)), re.I)


def test_liczba_przewag_brak_danych_to_none(raport):
    assert tabele.liczba_przewag(raport, "typ", "pliki") is None  # fikstura: per_typ tylko dla tekstu
    assert tabele.liczba_przewag(raport, "typ", "tekst") == 1  # beta ma lepszy typ „umowa”
    assert tabele.liczba_przewag(raport, "szybkosc", "tekst") == 1
