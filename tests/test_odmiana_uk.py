"""Testy odmiany ukraińskich imion, imion po ojcu i nazwisk (podręcznikowe wzorce deklinacji ukraińskiej)."""
from __future__ import annotations

from pathlib import Path

import pytest

from pbench.odmiana_uk import PRZYPADKI, odmien, odmien_slowo

SLOWNIKI = Path(__file__).resolve().parents[1] / "pbench" / "dane" / "slowniki" / "uk"


@pytest.mark.parametrize("slowo,rodzaj,plec,formy", [
    # imiona męskie: rod, dav, zna, oru, mis, kl
    ("Іван", "imie", "M", ["Івана", "Івану", "Івана", "Іваном", "Івану", "Іване"]),
    ("Петро", "imie", "M", ["Петра", "Петру", "Петра", "Петром", "Петру", "Петре"]),
    ("Андрій", "imie", "M", ["Андрія", "Андрію", "Андрія", "Андрієм", "Андрію", "Андрію"]),
    ("Василь", "imie", "M", ["Василя", "Василю", "Василя", "Василем", "Василю", "Василю"]),
    ("Микола", "imie", "M", ["Миколи", "Миколі", "Миколу", "Миколою", "Миколі", "Миколо"]),
    ("Ігор", "imie", "M", ["Ігоря", "Ігорю", "Ігоря", "Ігорем", "Ігорю", "Ігорю"]),
    ("Федір", "imie", "M", ["Федора", "Федору", "Федора", "Федором", "Федору", "Федоре"]),
    ("Михайло", "imie", "M", ["Михайла", "Михайлу", "Михайла", "Михайлом", "Михайлу", "Михайле"]),
    # imiona żeńskie
    ("Олена", "imie", "K", ["Олени", "Олені", "Олену", "Оленою", "Олені", "Олено"]),
    ("Наталія", "imie", "K", ["Наталії", "Наталії", "Наталію", "Наталією", "Наталії", "Наталіє"]),
    ("Ольга", "imie", "K", ["Ольги", "Ользі", "Ольгу", "Ольгою", "Ользі", "Ольго"]),
    ("Зоя", "imie", "K", ["Зої", "Зої", "Зою", "Зоєю", "Зої", "Зоє"]),
    ("Леся", "imie", "K", ["Лесі", "Лесі", "Лесю", "Лесею", "Лесі", "Лесю"]),
    ("Анна", "imie", "K", ["Анни", "Анні", "Анну", "Анною", "Анні", "Анно"]),
    # imiona po ojcu
    ("Петрович", "po_batkovi", "M", ["Петровича", "Петровичу", "Петровича", "Петровичем", "Петровичу", "Петровичу"]),
    ("Олексійович", "po_batkovi", "M", ["Олексійовича", "Олексійовичу", "Олексійовича", "Олексійовичем", "Олексійовичу", "Олексійовичу"]),
    ("Петрівна", "po_batkovi", "K", ["Петрівни", "Петрівні", "Петрівну", "Петрівною", "Петрівні", "Петрівно"]),
    # nazwiska męskie
    ("Шевченко", "nazwisko", "M", ["Шевченка", "Шевченку", "Шевченка", "Шевченком", "Шевченку", "Шевченку"]),
    ("Мельник", "nazwisko", "M", ["Мельника", "Мельнику", "Мельника", "Мельником", "Мельнику", "Мельнику"]),
    ("Мельничук", "nazwisko", "M", ["Мельничука", "Мельничуку", "Мельничука", "Мельничуком", "Мельничуку", "Мельничуку"]),
    ("Ковальський", "nazwisko", "M", ["Ковальського", "Ковальському", "Ковальського", "Ковальським", "Ковальському", "Ковальський"]),
    ("Білий", "nazwisko", "M", ["Білого", "Білому", "Білого", "Білим", "Білому", "Білий"]),
    ("Кравець", "nazwisko", "M", ["Кравця", "Кравцю", "Кравця", "Кравцем", "Кравцю", "Кравче"]),
    ("Ковальов", "nazwisko", "M", ["Ковальова", "Ковальову", "Ковальова", "Ковальовим", "Ковальову", "Ковальове"]),
    ("Коваль", "nazwisko", "M", ["Коваля", "Ковалю", "Коваля", "Ковалем", "Ковалю", "Ковалю"]),
    ("Мартинович", "nazwisko", "M", ["Мартиновича", "Мартиновичу", "Мартиновича", "Мартиновичем", "Мартиновичу", "Мартиновичу"]),
    ("Сорока", "nazwisko", "M", ["Сороки", "Сороці", "Сороку", "Сорокою", "Сороці", "Сороко"]),
    ("Цибуля", "nazwisko", "M", ["Цибулі", "Цибулі", "Цибулю", "Цибулею", "Цибулі", "Цибулю"]),
    # nazwiska żeńskie: przymiotnikowe i na -а odmieniane, reszta nieodmienna
    ("Ковальська", "nazwisko", "K", ["Ковальської", "Ковальській", "Ковальську", "Ковальською", "Ковальській", "Ковальська"]),
    ("Ковальова", "nazwisko", "K", ["Ковальової", "Ковальовій", "Ковальову", "Ковальовою", "Ковальовій", "Ковальова"]),
    ("Шевченко", "nazwisko", "K", ["Шевченко"] * 6),
    ("Мельничук", "nazwisko", "K", ["Мельничук"] * 6),
    ("Кравець", "nazwisko", "K", ["Кравець"] * 6),
    ("Сорока", "nazwisko", "K", ["Сороки", "Сороці", "Сороку", "Сорокою", "Сороці", "Сороко"]),
])
def test_odmiana_slowa(slowo, rodzaj, plec, formy):
    assert [odmien_slowo(slowo, rodzaj, plec, p) for p in PRZYPADKI[1:]] == formy
    assert odmien_slowo(slowo, rodzaj, plec, "mian") == slowo


def test_pib_w_przypadkach():
    assert odmien("Іван", "Петрович", "Шевченко", "M", "rod") == "Шевченка Івана Петровича"
    assert odmien("Іван", "Петрович", "Шевченко", "M", "dav") == "Шевченку Івану Петровичу"
    assert odmien("Іван", "Петрович", "Шевченко", "M", "oru") == "Шевченком Іваном Петровичем"
    assert odmien("Олена", "Петрівна", "Шевченко", "K", "zna") == "Шевченко Олену Петрівну"
    assert odmien("Іван", "Петрович", "Шевченко", "M", "mian") == "Шевченко Іван Петрович"
    assert odmien("Іван", "Петрович", "Шевченко", "M", "rod", "IN") == "Івана Шевченка"
    assert odmien("Іван", "Петрович", "Шевченко", "M", "kl", "IP") == "Іване Петровичу"
    assert odmien("Іван", "", "Шевченко", "M", "rod") == "Шевченка Івана"                # puste człony pomijane
    assert odmien("Іван", "Петрович", "Мельник-Кравчук", "M", "rod") == "Мельника-Кравчука Івана Петровича"


def test_odmiana_bledne_argumenty():
    with pytest.raises(ValueError):
        odmien("Іван", "Петрович", "Шевченко", "M", "woł")
    with pytest.raises(ValueError):
        odmien("Іван", "Петрович", "Шевченко", "X", "rod")
    with pytest.raises(ValueError):
        odmien("Іван", "Петрович", "Шевченко", "M", "rod", "XYZ")


def test_cala_pula_slownikow_odmienia_sie_poprawnie_ksztaltowo():
    """Każde imię, imię po ojcu i nazwisko z puli daje w 6 przypadkach niepuste formy; formy nie zawierają liter spoza
    cyrylicy i nie gubią początku wyrazu (rdzeń, poza wymianą głosek i wypadaniem samogłoski)."""
    for plik, rodzaj, plec in (("imiona_m", "imie", "M"), ("imiona_k", "imie", "K"), ("nazwiska", "nazwisko", "M"),
                               ("nazwiska", "nazwisko", "K")):
        for linia in (SLOWNIKI / f"{plik}.txt").read_text(encoding="utf-8").splitlines():
            slowo = linia.split("|")[0]
            if plec == "K" and rodzaj == "nazwisko":
                from pbench.dane.uk import nazwisko_zenskie
                slowo = nazwisko_zenskie(slowo)
            for p in PRZYPADKI:
                forma = odmien_slowo(slowo, rodzaj, plec, p)
                assert forma and forma[:2].lower() == slowo[:2].lower() or p == "mian", (slowo, p, forma)
                assert not any("a" <= c.lower() <= "z" for c in forma), (slowo, p, forma)
    for linia in (SLOWNIKI / "imiona_ojcow.txt").read_text(encoding="utf-8").splitlines():
        m, k, *_ = linia.split("|")
        assert odmien_slowo(m, "po_batkovi", "M", "oru").endswith("ичем"), m
        assert odmien_slowo(k, "po_batkovi", "K", "oru").endswith("ною"), k
