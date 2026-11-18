"""Testy transliteracji ukraińskiego (siedem systemów). Wektory: przykłady z tablicy Postanowienia KMU nr 55 z 27.01.2010
(`kmu2010`: Алушта, Борщагівка, Вишгород, Згорани, Гадяч, Єнакієве, Їжакевич, Кадиївка, Мар’їне, Йосипівка, Стрий…), tablica
ISO 9:1995 (Шевченко → Ševčenko, Київ → Kiïv), tablica rosyjskich paszportów ICAO 9303 (Щербаков → SHCHERBAKOV, Юлия → IULIIA,
Яковлев → IAKOVLEV) oraz powszechna praktyka polska (Ołeksandr, Łesia, Zełenski), niemiecka (Schewtschenko) i francuska
(Chevtchenko)."""
from __future__ import annotations

import random
import unicodedata

import pytest

from pbench.translit import SYSTEMY, ma_cyrylice, transliteruj


@pytest.mark.parametrize("cyr,lac", [
    ("Алушта", "Alushta"), ("Борщагівка", "Borshchahivka"), ("Вишгород", "Vyshhorod"), ("Згорани", "Zghorany"),
    ("Гадяч", "Hadiach"), ("Єнакієве", "Yenakiieve"), ("Їжакевич", "Yizhakevych"), ("Кадиївка", "Kadyivka"),
    ("Мар’їне", "Marine"), ("Йосипівка", "Yosypivka"), ("Стрий", "Stryi"), ("Крюківщина", "Kriukivshchyna"),
    ("Запоріжжя", "Zaporizhzhia"), ("Юрій", "Yurii"), ("Ярошенко", "Yaroshenko"), ("Олексій", "Oleksii"),
    ("Тетяна", "Tetiana"), ("Гребінка", "Hrebinka"), ("Щербак", "Shcherbak"), ("Шевченко", "Shevchenko"),
    ("Олександр", "Oleksandr"), ("Юлія", "Yuliia"), ("Ґанок", "Ganok"), ("Ковальський", "Kovalskyi"),
    ("Розгін", "Rozghin"),                                  # „зг” → „zgh” także w środku wyrazu
    ("Мар'яна", "Mariana"), ("Мар’яна", "Mariana"), ("Мар'їна", "Marina"),   # apostrof (obie odmiany) pomijany
    ("Ясинська", "Yasynska"),                              # я na początku → Ya, ь pominięty
])
def test_kmu2010(cyr, lac):
    assert transliteruj(cyr, "kmu2010") == lac


def test_kmu2010_pozycyjne_je_ji_j_ju_ja():
    assert [transliteruj(x, "kmu2010") for x in ("Єва", "Тієї", "Їжак", "Мої", "Йосип", "Мій", "Юра", "Тюра", "Яна", "Мая")] == [
        "Yeva", "Tiiei", "Yizhak", "Moi", "Yosyp", "Mii", "Yura", "Tiura", "Yana", "Maia"]


def test_kmu2010_wielkosc_liter_i_znaki_spoza_cyrylicy():
    assert transliteruj("ШЕВЧЕНКО", "kmu2010") == "SHEVCHENKO"
    assert transliteruj("Щука", "kmu2010") == "Shchuka"
    assert transliteruj("ЗГОРАНИ", "kmu2010") == "ZGHORANY"
    assert transliteruj("вул. Соборна, 12, кв. 3, 79000", "kmu2010") == "vul. Soborna, 12, kv. 3, 79000"
    assert transliteruj("Anna Nowak", "kmu2010") == "Anna Nowak"
    assert transliteruj("Мельник-Кравчук", "kmu2010") == "Melnyk-Kravchuk"


@pytest.mark.parametrize("cyr,lac", [
    ("Шевченко", "Szewczenko"), ("Олександр", "Ołeksandr"), ("Юрій", "Jurij"), ("Григорій", "Hryhorij"),
    ("Леся", "Łesia"), ("Василь", "Wasyl"), ("Іван", "Iwan"), ("Ковальський", "Kowalski"), ("Зеленський", "Zełenski"),
    ("Щербак", "Szczerbak"), ("Жук", "Żuk"), ("Ганна", "Hanna"), ("Чорновіл", "Czornowił"), ("Тетяна", "Tetiana"),
    ("Юлія", "Julija"), ("Мар’яна", "Marjana"), ("Харківська", "Charkiwska"), ("Дзюба", "Dziuba"), ("Лисенко", "Łysenko"),
])
def test_polski(cyr, lac):
    assert transliteruj(cyr, "polski") == lac


@pytest.mark.parametrize("cyr,lac", [
    ("Шевченко", "Schewtschenko"), ("Щербак", "Schtscherbak"), ("Жук", "Shuk"), ("Чорний", "Tschornyj"),
    ("Володимир", "Wolodymyr"), ("Юрій", "Jurij"), ("Хмельницький", "Chmelnyzkyj"),
])
def test_niemiecki(cyr, lac):
    assert transliteruj(cyr, "niemiecki") == lac


@pytest.mark.parametrize("cyr,lac", [
    ("Шевченко", "Chevtchenko"), ("Щербак", "Chtcherbak"), ("Жук", "Jouk"), ("Чорний", "Tchornyi"),
    ("Хмельницький", "Khmelnytskyi"), ("Юрій", "Iourii"),
])
def test_francuski(cyr, lac):
    assert transliteruj(cyr, "francuski") == lac


@pytest.mark.parametrize("cyr,lac", [
    ("Шевченко", "Ševčenko"), ("Київ", "Kiïv"), ("Кіїв", "Kìïv"), ("Юрій", "Ûrìj"), ("Щербак", "Ŝerbak"), ("Олександр", "Oleksandr"),
    ("Єва", "Êva"), ("Жук", "Žuk"), ("Григорій", "Grigorìj"), ("Ґанок", "G̀anok"), ("Яна", "Âna"),
    ("Чайка", "Čajka"), ("ШЕВЧЕНКО", "ŠEVČENKO"),
])
def test_iso9(cyr, lac):
    wynik = transliteruj(cyr, "iso9")
    assert wynik == unicodedata.normalize("NFC", lac)
    assert unicodedata.is_normalized("NFC", wynik)


@pytest.mark.parametrize("cyr,lac", [
    ("Щербаков", "SHCHERBAKOV"), ("Юлия", "IULIIA"), ("Яковлев", "IAKOVLEV"), ("Шевченко", "SHEVCHENKO"),
    ("Юлія", "IULIIA"), ("Григорій", "GRIGORII"), ("Хмельницький", "KHMELNITSKII"), ("Ковалёв", "KOVALEV"),
    ("Чернов", "CHERNOV"), ("Цибуля", "TSIBULIA"),
])
def test_paszport_zsrr(cyr, lac):
    assert transliteruj(cyr, "paszport_zsrr") == lac


def test_pisownia_rosyjska_odczyt_rosyjski():
    """Rosyjska pisownia imion osób ukraińskich: litery czytane po rosyjsku (Александр → Aleksandr, Игорь → Igor)."""
    assert transliteruj("Александр", "kmu2010", rosyjska=True) == "Aleksandr"
    assert transliteruj("Сергей", "kmu2010", rosyjska=True) == "Sergei"
    assert transliteruj("Ковалёв", "kmu2010", rosyjska=True) == "Kovalev"
    assert transliteruj("Игорь", "kmu2010", rosyjska=True) == "Igor"
    assert transliteruj("Александр Ковалёв", "polski", rosyjska=True) == "Aleksandr Kowalew"
    # bez flagi: odczyt ukraiński (inne litery, inny wynik)
    assert transliteruj("Игорь", "kmu2010") == "Yhor"


def test_ascii_dorazne_niespojne_ale_ascii():
    zapisy = {transliteruj("Олександр Шевченко", "ascii_dorazne", random.Random(i)) for i in range(200)}
    assert len(zapisy) >= 8
    assert "Oleksandr Shevchenko" in zapisy and any(z.startswith("Olex") for z in zapisy)
    assert all(z.isascii() for z in zapisy)
    # domyślnie deterministyczne dla tekstu
    assert transliteruj("Олександр Шевченко", "ascii_dorazne") == transliteruj("Олександр Шевченко", "ascii_dorazne")


@pytest.mark.parametrize("system", SYSTEMY)
def test_system_nie_zostawia_cyrylicy_i_zachowuje_poczatek_wyrazu(system):
    for slowo in ("Шевченко", "Олександр", "Єнакієве", "Мельничук", "Їжак", "Щука", "Сергієнко", "Ґандзя"):
        wynik = transliteruj(slowo, system)
        assert wynik and not ma_cyrylice(wynik), (system, slowo, wynik)
        assert wynik[0].isupper(), (system, slowo, wynik)


def test_nieznany_system():
    with pytest.raises(ValueError):
        transliteruj("Іван", "nieistniejacy")
    assert not ma_cyrylice("Kowalski") and ma_cyrylice("Kоwalski")      # druga: cyrylicka „о”
