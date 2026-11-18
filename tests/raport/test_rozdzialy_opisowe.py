"""Testy rozdziałów opisowych (metodyka, punktacja, przykłady, wdrożenie, ograniczenia, aneksy): tabela przykładów z podświetleniem wycieku,
narzędzie zakresów przykładów, stałe opisowe i kontaminacja z repozytorium, podsumowanie czasu, treść rozdziałów na danych rzeczywistych
(env PBENCH_RAPORT_WYNIKI) i brak treści zakazanych w źródłach."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest

from raport import buduj, dane, kontrola, tabele
from raport.dane import Raport, wczytaj

FIKSTURY = Path(__file__).parent / "fixtures"
KORZEN = Path(__file__).resolve().parents[2]
ROZDZIALY_OPISOWE = ["30-metodyka.md", "35-punktacja.md", "50-przyklady.md", "60-wdrozenie.md", "70-ograniczenia.md", "95-aneks-ujawnienia.md", "96-aneks-odtworzenie.md"]


def _przyklad(**kw) -> dict:
    p = {"uczestnik": "privatizer-tekst", "id": "pl-t-0001", "jezyk": "pl", "przed": "Klient: Jan Kowalski & Co, ul. Testowa 1.",
         "po": "Klient: [OSOBA] & Co, ul. [ADRES].", "wyciek": ["k.nazwa#1", "ORGANIZACJA", "naglowek", "czesciowy"]}
    p.update(kw)
    return p


def _raport(*przyklady: dict) -> Raport:
    r = Raport()
    r.przyklady = list(przyklady)
    return r


# ------------------------------------------------------------------ przykłady

def test_przyklady_podswietlenie_nie_tylko_kolorem(monkeypatch):
    monkeypatch.setattr(tabele, "zakresy_przykladow", lambda: {"pl-t-0001|k.nazwa#1": {"od": 21, "do": 27, "tekst": "& Co, "}})
    html = tabele.przyklady(_raport(_przyklad()), "tekst")
    assert '<mark class="wyciek">&amp; Co, </mark>' in html          # wartość wzorcowa, zmieniona na bezpieczny HTML
    assert '<span class="maska">[OSOBA]</span>' in html               # oznaczenie maski uczestnika w ramce
    assert "ORGANIZACJA" in html and "nagłówek, częściowy" in html     # kategoria, miejsce i rodzaj po polsku
    css = (buduj.SZABLON / "druk.css").read_text(encoding="utf-8")
    reguła = re.search(r"mark\.wyciek\s*\{([^}]*)\}", css).group(1)
    assert "underline" in reguła and "font-weight" in reguła           # podkreślenie i pogrubienie, nie sam kolor


def test_przyklady_zly_offset_nie_podswietla(monkeypatch):
    monkeypatch.setattr(tabele, "zakresy_przykladow", lambda: {"pl-t-0001|k.nazwa#1": {"od": 0, "do": 3, "tekst": "inny"}})
    assert "<mark" not in tabele.przyklady(_raport(_przyklad()), "tekst")
    monkeypatch.setattr(tabele, "zakresy_przykladow", lambda: {})
    assert "<mark" not in tabele.przyklady(_raport(_przyklad()), "tekst")


def test_przyklady_fikstura_z_wyciekiem_logicznym_i_pusty_zbior():
    r = wczytaj(FIKSTURY / "zbiorcze", FIKSTURY / "czas-m1")
    html = tabele.przyklady(r, "tekst")
    assert html.lstrip().startswith("<table") and "None" not in html
    assert "n/d (brak danych)" in tabele.przyklady(_raport(), "tekst")


def test_przyklady_kolejnosc_miejsc_rankingu():
    r = _raport(_przyklad(uczestnik="b"), _przyklad(uczestnik="a"))
    from raport.dane import Wiersz
    r.rankingi["tekst"] = [Wiersz("a", 2, [], 1.0, (0.0, 2.0), {}), Wiersz("b", 1, [], 2.0, (1.0, 3.0), {})]
    html = tabele.przyklady(r, "tekst")
    assert html.index("<td>b<br>") < html.index("<td>a<br>")      # miejsce 1 przed miejscem 2, nie alfabetycznie


# ------------------------------------------------------------------ narzędzie zakresów

def _korpus(tmp_path: Path, tekst: str, spany: list[dict]) -> Path:
    (tmp_path / "d1.txt").write_text(tekst, encoding="utf-8")
    (tmp_path / "manifest.jsonl").write_text(json.dumps({"id": "d1", "plik_txt": "d1.txt", "gold_tekst": spany}) + "\n", encoding="utf-8")
    return tmp_path


def test_zakresy_przykladow_odtwarza_offsety(tmp_path):
    sys.path.insert(0, str(KORZEN))
    from narzedzia import zakresy_przykladow as z
    tekst = "x" * 100 + "Jan Kowalski" + "y" * 100
    korpus = _korpus(tmp_path, tekst, [{"start": 100, "end": 112, "wartosc_id": "o#1", "tekst": "Jan Kowalski"}])
    a, b = 20, 192
    wynik = z.zakresy([{"id": "d1", "przed": tekst[a:b], "wyciek": ["o#1", "OSOBA", "tresc", "pelny"]}], korpus)
    assert wynik == {"d1|o#1": {"od": 80, "do": 92, "tekst": "Jan Kowalski"}}
    assert tekst[a:b][80:92] == "Jan Kowalski"


def test_zakresy_przykladow_krotkie_okno_na_poczatku_i_niezgodnosc(tmp_path):
    sys.path.insert(0, str(KORZEN))
    from narzedzia import zakresy_przykladow as z
    korpus = _korpus(tmp_path, "Jan Kowalski mieszka tu.", [{"start": 0, "end": 12, "wartosc_id": "o#1", "tekst": "Jan Kowalski"}])
    przyklad = {"id": "d1", "przed": "Jan Kowalski mieszka tu.", "wyciek": ["o#1", "OSOBA", "tresc", "pelny"]}
    assert z.zakresy([przyklad], korpus)["d1|o#1"] == {"od": 0, "do": 12, "tekst": "Jan Kowalski"}
    with pytest.raises(SystemExit):
        z.zakresy([{**przyklad, "przed": "inny tekst"}], korpus)


def test_zakresy_w_repozytorium_zgodne_z_przykladami_rzeczywistymi():
    wyniki = os.environ.get("PBENCH_RAPORT_WYNIKI")
    if not wyniki:
        pytest.skip("brak PBENCH_RAPORT_WYNIKI")
    r = wczytaj(Path(wyniki))
    zakresy = dane.zakresy_przykladow()
    assert zakresy, "brak raport/dane/przyklady_zakresy.json"
    for p in r.przyklady:
        z = zakresy[f'{p["id"]}|{p["wyciek"][0]}']
        assert p["przed"][z["od"]:z["do"]] == z["tekst"]


# ------------------------------------------------------------------ dane opisowe

def test_liczby_opisowe_i_kontaminacja_z_repozytorium():
    m = dane.liczby_opisowe()
    assert m["korpus"]["trzon_test"] + m["korpus"]["trzon_dev"] == m["korpus"]["trzon_dokumentow"]
    assert m["korpus"]["trudne_test"] + m["korpus"]["trudne_dev"] == m["korpus"]["trudne_dokumentow"]
    assert m["czas"]["proba_dokumentow"] == sum(m["czas"][f"proba_{j}"] for j in ("pl", "en", "de", "es", "fr"))
    k = dane.kontaminacja()
    assert set(k) == {"trzon", "trudne"}
    assert k["trzon"]["korpus"]["dokumentow"] == m["korpus"]["trzon_dokumentow"]
    assert k["trudne"]["korpus"]["dokumentow"] == m["korpus"]["trudne_dokumentow"]
    w = dane.wagi_punktow()
    assert w["progi"]["bootstrap_powtorzen"] == 1000


def test_podsumowanie_czasu_i_pamiec_wysoka(tmp_path):
    czas = tmp_path / "czas-m1"
    czas.mkdir()
    (czas / "wersje.json").write_text("{}", encoding="utf-8")
    (czas / "podsumowanie.txt").write_text(
        "| uczestnik | poziom | dok. | mediana s/stronę | awarie | start [s] | szczyt pamięci [MB] | metoda pamięci |\n|---|---|---|---|---|---|---|---|\n"
        "| a | tekst | 60 | 0.5000 | 0 | 4.1 | 350 | phys_footprint |\n| b | plik | 7 | 0.2000 | 1 | 15.6 | 7909 | phys_footprint |\n| zepsuty | tekst | x | y | | | | |\n",
        encoding="utf-8")
    r = wczytaj(FIKSTURY / "zbiorcze", czas)
    assert [x["uczestnik"] for x in r.czas_podsumowanie] == ["a", "b", "zepsuty"]  # nieczytelny wiersz nie ginie: jawne None („n/d”), nie 0
    assert r.czas_podsumowanie[2] == {"uczestnik": "zepsuty", "poziom": "tekst", "dokumenty": None, "s_na_strone": None, "awarie": None, "start_s": None, "szczyt_mb": None, "metoda": ""}
    assert [x["uczestnik"] for x in dane.czas_podsumowanie_wg_pamieci(r)] == ["b", "a", "zepsuty"]  # wiersz bez pomiaru na końcu
    assert r.czas_podsumowanie[1] == {"uczestnik": "b", "poziom": "plik", "dokumenty": 7, "s_na_strone": 0.2, "awarie": 1, "start_s": 15.6, "szczyt_mb": 7909, "metoda": "phys_footprint"}
    assert [x["uczestnik"] for x in dane.pamiec_wysoka(r)] == ["b"]
    assert dane.pamiec_wysoka(Raport()) == []


def test_format_zmieniony_wczytany():
    r = wczytaj(FIKSTURY / "zbiorcze")
    assert all(w.format_zmieniony is None or isinstance(w.format_zmieniony, int) for rk in r.rankingi.values() for w in rk)


def test_przyklady_bez_zakresu_ma_to_samo_wielokropek(monkeypatch):
    monkeypatch.setattr(tabele, "zakresy_przykladow", lambda: {})
    html = tabele.przyklady(_raport(_przyklad()), "tekst")
    assert "ul. Testowa 1.…" in html                                   # jak w wariancie z podświetleniem


def test_zakresy_przykladow_brak_wartosci_w_manifescie_to_czytelny_blad(tmp_path):
    sys.path.insert(0, str(KORZEN))
    from narzedzia.zakresy_przykladow import zakresy
    (tmp_path / "manifest.jsonl").write_text(json.dumps({"id": "pl-t-0001", "plik_txt": "a.txt", "gold_tekst": []}) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="pl-t-0001"):
        zakresy([_przyklad()], tmp_path)


# ------------------------------------------------------------------ identyfikacja pośrednia

def _wiersz_pom(u, **kw):
    x = {"ranking": "tekst", "uczestnik": u, "posrednie_kombinacje": 36, "posrednie_przerwane": 30, "posrednie_odsetek": 0.833333,
         "posrednie_ci_dol": 0.72973, "posrednie_ci_gora": 0.939394}
    x.update(kw)
    return x


def _raport_posrednie(*wiersze):
    r = wczytaj(FIKSTURY / "zbiorcze", FIKSTURY / "czas-m1")
    r.pomocnicze = list(wiersze)
    return r


def test_posrednie_miara_przedzial_i_aneks_na_koncu():
    r = _raport_posrednie(_wiersz_pom("privatizer-tekst"))
    html = tabele.posrednie(r, "tekst")
    tekst = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))
    assert "83,3%" in tekst and "[73,0%" in tekst.replace("–", " ").replace("  ", " ") or "73,0" in tekst
    assert "30" in tekst and "36" in tekst and "poza punktami" in tekst


def test_posrednie_brak_danych_to_nd():
    r = _raport_posrednie()
    html = tabele.posrednie(r, "tekst")
    assert "n/d" in html and not re.search(r"\bnan\b|\bNone\b", html)
    assert tabele.posrednie(Raport(), "tekst").count("n/d") >= 1            # brak rankingu: pojedynczy wiersz z komunikatem
    # wartość brakująca w jednym wierszu: przedział też „n/d”, nie „0%”
    r2 = _raport_posrednie(_wiersz_pom("privatizer-tekst", posrednie_odsetek=None, posrednie_ci_dol=None, posrednie_ci_gora=None))
    assert "n/d" in tabele.posrednie(r2, "tekst")


def test_posrednie_zero_to_zero_a_nie_nd():
    r = _raport_posrednie(_wiersz_pom("privatizer-tekst", posrednie_przerwane=0, posrednie_odsetek=0.0, posrednie_ci_dol=0.0, posrednie_ci_gora=0.0))
    html = tabele.posrednie(r, "tekst")
    assert "0,0%" in html


def test_rozdzial_wyniki_ma_sekcje_posrednie_i_uwage_interpretacyjna(tmp_path):
    zrodlo = (buduj.ROZDZIALY / "40-wyniki.md").read_text(encoding="utf-8")
    assert "## Identyfikacja pośrednia" in zrodlo and "tabela('posrednie', 'tekst')" in zrodlo and "tabela('posrednie', 'pliki')" in zrodlo
    assert "warunek konieczny ochrony, nie wystarczający" in zrodlo
    sekcja = zrodlo[zrodlo.index("## Identyfikacja pośrednia"):zrodlo.index("## Rozbicia")]
    (tmp_path / "40-wyniki.md").write_text(sekcja, encoding="utf-8")
    html = buduj.zloz_html(wczytaj(FIKSTURY / "zbiorcze", FIKSTURY / "czas-m1"), tmp_path)   # dane bez miary: sekcja degraduje się do „n/d”
    assert 'id="identyfikacja-posrednia"' in html and "n/d" in html and "None" not in re.sub(r"<[^>]+>", "", html)


# ------------------------------------------------------------------ repozytorium, identyfikatory modeli, osobność zdania

def test_repozytorium_ze_stalej_a_nie_literalu():
    assert dane.REPOZYTORIUM == "https://github.com/tmk12/benchmark-anonimizacji"
    zrodlo = (buduj.ROZDZIALY / "96-aneks-odtworzenie.md").read_text(encoding="utf-8")
    assert "{{ repozytorium }}" in zrodlo and "github.com" not in zrodlo


def test_pelne_identyfikatory_modeli_w_metodyce():
    zrodlo = (buduj.ROZDZIALY / "30-metodyka.md").read_text(encoding="utf-8")
    for idm in ("urchade/gliner_multi_pii-v1", "knowledgator/gliner-pii-large-v1.0"):
        assert idm in zrodlo
    assert kontrola.kontroluj_zrodla(buduj.ROZDZIALY) == []


def test_zdanie_o_rozdzielnosci_stoi_samo_w_punkcie():
    zrodlo = (buduj.ROZDZIALY / "30-metodyka.md").read_text(encoding="utf-8")
    zdanie = "Zespoły Privatizera nie mają dostępu do splitu testowego; korpus nie służy do treningu ani walidacji modelu."
    punkt = [l for l in zrodlo.splitlines() if zdanie in l]
    assert len(punkt) == 1 and punkt[0].strip() == f"- **Rozdzielność od treningu:** {zdanie}"


def test_daty_i_wersje_srodowiska_ze_stalych_opisowych():
    for nazwa in ("30-metodyka.md", "95-aneks-ujawnienia.md", "96-aneks-odtworzenie.md"):
        zrodlo = (buduj.ROZDZIALY / nazwa).read_text(encoding="utf-8")
        assert not re.search(r"\b2026-11-\d\d\b|5\.3\.4|1\.83\.1|Python w wersji 3\.12", zrodlo), nazwa
    m = dane.liczby_opisowe()
    assert m["daty"]["zamrozenie"] and m["srodowisko"]["python"] == "3.12" and m["swap"]["wrapper_limit_gb"] == 4


# ------------------------------------------------------------------ rozdziały

def test_rozdzialy_opisowe_istnieja_i_przechodza_kontrole(tmp_path):
    for nazwa in ROZDZIALY_OPISOWE:
        assert (buduj.ROZDZIALY / nazwa).is_file(), nazwa
        (tmp_path / nazwa).write_text((buduj.ROZDZIALY / nazwa).read_text(encoding="utf-8"), encoding="utf-8")
    assert kontrola.kontroluj_zrodla(buduj.ROZDZIALY) == []
    assert kontrola.kontroluj_zrodla(buduj.ANEKS) == [] and kontrola.kontroluj_zrodla(buduj.ANEKS, publikacja=True) == []
    # bez [NIEZWERYFIKOWANE]/[HIPOTEZA]; rozdział „Dlaczego to ważne” ma je świadomie (blokada publikacji – test_zrodla.py)
    assert kontrola.kontroluj_zrodla(tmp_path, publikacja=True) == []


def test_jedyne_zdanie_o_rozdzielnosci_i_brak_tresci_zakazanych_w_zrodlach():
    tekst = "\n".join((buduj.ROZDZIALY / n).read_text(encoding="utf-8") for n in ROZDZIALY_OPISOWE)
    zdanie = "Zespoły Privatizera nie mają dostępu do splitu testowego; korpus nie służy do treningu ani walidacji modelu."
    assert tekst.count(zdanie) == 1
    for zakazane in ("/home/", "/Users/"):
        assert zakazane not in tekst, zakazane


WYNIKI = os.environ.get("PBENCH_RAPORT_WYNIKI")


@pytest.fixture(scope="module")
def html_rzeczywisty():
    return buduj.zloz_html(wczytaj(Path(WYNIKI)))


@pytest.mark.skipif(not WYNIKI, reason="brak PBENCH_RAPORT_WYNIKI (katalog zbiorczy z wynikami)")
def test_dane_rzeczywiste_rozdzialy_opisowe(html_rzeczywisty):
    tekst = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html_rzeczywisty))
    for naglowek in ("Metodyka", "Punktacja", "Przykłady", "Wdrożenie", "Ograniczenia", "Aneks ujawnień", "Aneks odtworzenia"):
        assert f">{naglowek}</h1>" in html_rzeczywisty, naglowek
    assert not re.search(r"\bnan\b|\bNone\b|Undefined", tekst)
    assert '<mark class="wyciek">' in html_rzeczywisty and 'class="maska"' in html_rzeczywisty
    assert "1.3.0b24" in tekst and "1.0.0rc5" in tekst
    # kontaminacja z danych: trzon poza formułkowymi, cel niespełniony dla warstwy trudnej i szablonów
    assert "0,78%" in tekst and "cel jest niespełniony" in tekst
    # identyfikacja pośrednia: tabele z danych i uwaga interpretacyjna; swap osobno dla tekstu i plików
    assert 'id="identyfikacja-posrednia"' in html_rzeczywisty and "36" in tekst and "warunek konieczny ochrony" in tekst
    assert "uczestników tekstowych" in tekst and "uczestników plikowych" in tekst and "3,19 GB z 4 GB" in tekst
    # ograniczenia testu domen i odsyłacz z rozdziału Wyniki
    assert "korekty na wielokrotne porównania" in tekst and "aneks ujawnień (akapit o domenach" in tekst
    # akapity ujawnień (po jednym na okoliczność)
    for fragment in ("Kontaminacja korpusu", "Domeny example.* w danych treningowych", "Poprawka warstwy MoE", "Przeniesienie przebiegu flair",
                     "Pamięć maszyny referencyjnej i swap", "Wersja Tesseracta", "Błąd przenośności narzędzia", "mierzony w dwóch sesjach",
                     "Test P5 dla presidio-image-redactor", "Wiadomości EML z załącznikami", "Zmiana formatu pliku wynikowego"):
        assert fragment in tekst, fragment
    # chmura tylko opisowo; odrzuceni z metodyki
    assert "Google Cloud Sensitive Data Protection" in tekst and "Piiranha" in tekst and "CLARIN-PL" in tekst
    assert kontrola._zakazy(tekst, "html:", kontrola.ZAKAZY) == []
