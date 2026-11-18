"""Testy generatora wartości ukraińskich: sumy kontrolne liczone NIEZALEŻNIE (python-stdnum: `stdnum.ua.rntrc`,
`stdnum.ua.edrpou`, `stdnum.iban`; wektory z ich dokumentacji), telefony (libphonenumber), adresy, imiona i nazwiska
(wyłącznie ukraińskie, pisownia rosyjska tylko jako oznaczony przypadek), formy prawne i rejestry."""
from __future__ import annotations

import datetime as dt
import random
import re
from pathlib import Path

import phonenumbers
import pytest
from stdnum import iban as stdnum_iban
from stdnum.ua import edrpou as ua_edrpou, rntrc as ua_rntrc

from pbench.budowa import MAPA_KATEGORII
from pbench.dane import Generator
from pbench.dane.uk import (GeneratorUK, OsobaUK, data_z_rnokpp, edrpou, nazwisko_zenskie, plec_z_rnokpp, rnokpp)

SLOWNIKI = Path(__file__).resolve().parents[1] / "pbench" / "dane" / "slowniki" / "uk"
N = 400
#: Litery wyłącznie rosyjskie (nie występują w alfabecie ukraińskim).
ROSYJSKIE = set("ыэёъЫЭЁЪ")
UKRAINSKIE_LITERY = set("АБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯабвгґдеєжзиіїйклмнопрстуфхцчшщьюя’ʼ'-. ")


def _osoby(ziarno: int = 1, n: int = N, p_ru: float = 0.0) -> list[OsobaUK]:
    g = Generator("uk", ziarno)
    g.p_ru = p_ru
    return [g.osoba() for _ in range(n)]


# ----------------------------------------------------------------------------- РНОКПП
def test_rnokpp_wektory_z_dokumentacji_stdnum():
    assert ua_rntrc.is_valid("1759013776") and not ua_rntrc.is_valid("1759013770")
    assert ua_rntrc.calc_check_digit("175901377") == "6"
    assert ua_edrpou.is_valid("32855961")


def test_rnokpp_poprawna_suma_data_i_plec():
    for o in _osoby():
        num = o.ids["RNOKPP"]
        assert len(num) == 10 and ua_rntrc.is_valid(num), num
        assert data_z_rnokpp(num) == o.data_ur, (num, o.data_ur)
        assert plec_z_rnokpp(num) == o.plec
    # dzień pierwszy = 1 stycznia 1900; granice zakresu urodzeń
    assert data_z_rnokpp("0000100000") == dt.date(1900, 1, 1)
    rng = random.Random(1)
    assert rnokpp(rng, dt.date(1900, 1, 1), "M").startswith("00001")


def test_rnokpp_zgodny_z_data_urodzenia_w_roznych_zakresach():
    rng = random.Random(5)
    for rok in (1940, 1971, 1999, 2005):
        for plec in "MK":
            d = dt.date(rok, 3, 9)
            num = rnokpp(rng, d, plec)
            assert ua_rntrc.is_valid(num) and data_z_rnokpp(num) == d and plec_z_rnokpp(num) == plec


# ----------------------------------------------------------------------------- ЄДРПОУ, IBAN, dokumenty
def test_edrpou_stdnum_oba_zakresy_wag():
    rng = random.Random(3)
    liczby = [edrpou(rng) for _ in range(600)]
    assert all(len(x) == 8 and ua_edrpou.is_valid(x) for x in liczby)
    assert any(30_000_000 <= int(x) <= 60_000_000 for x in liczby) and any(int(x) < 30_000_000 for x in liczby)


def test_firmy_formy_prawne_i_rejestry():
    g = Generator("uk", 7)
    firmy = [g.firma() for _ in range(N)]
    formy = {f.forma for f in firmy}
    assert formy == {"ТОВ", "ПП", "АТ", "ФОП"}
    for f in firmy:
        assert f.kraj == "UA"
        if f.forma == "ФОП":
            assert set(f.rejestry) == {"RNOKPP"} and ua_rntrc.is_valid(f.rejestry["RNOKPP"])
            assert f.nazwa.startswith("ФОП ") and "«" not in f.nazwa
        else:
            assert set(f.rejestry) == {"EDRPOU"} and ua_edrpou.is_valid(f.rejestry["EDRPOU"])
            assert f.nazwa.startswith(f"{f.forma} «") and f.nazwa.endswith("»")
        assert stdnum_iban.is_valid(f.rachunek) and f.rachunek.startswith("UA")
    assert all(ua_edrpou.is_valid(g.firma(rodzaj="spolka").rejestry["EDRPOU"]) for _ in range(30))
    assert {g.firma(rodzaj="spolka").forma for _ in range(30)} == {"ТОВ"}
    kanc = [g.firma(rodzaj="kancelaria") for _ in range(30)]
    assert all(f.nazwa.startswith(("Адвокатське об’єднання «", "Адвокатське бюро «")) for f in kanc)
    plac = [g.firma(rodzaj="placowka") for _ in range(30)]
    assert {f.forma for f in plac} <= {"КНП", "ТОВ"}


def test_iban_ua_29_znakow_mfo_i_mod97():
    g = Generator("uk", 2)
    for _ in range(N):
        iban = g.iban()
        assert len(iban) == 29 and iban.startswith("UA") and iban[2:].isdigit()
        assert stdnum_iban.is_valid(iban)
        assert re.fullmatch(r"[3]\d{5}", iban[4:10])            # MFO: sześć cyfr z zakresu 3xxxxx


def test_dowod_i_paszport_formaty():
    for o in _osoby():
        assert re.fullmatch(r"\d{9}", o.ids["DOWOD"])                      # ID-картка: 9 cyfr
        assert re.fullmatch(r"[A-Z]{2}\d{6}", o.ids["PASZPORT"])           # паспорт для виїзду за кордон
    assert MAPA_KATEGORII["RNOKPP"] == "NR_PODATKOWY" and MAPA_KATEGORII["EDRPOU"] == "NR_REJESTRU"
    assert MAPA_KATEGORII["DOWOD"] == "DOWOD" and MAPA_KATEGORII["PASZPORT"] == "PASZPORT"


def test_wartosci_unikalne_i_deterministyczne():
    a, b = _osoby(4, 200), _osoby(4, 200)
    assert a == b
    assert len({o.ids["RNOKPP"] for o in a}) == 200 and len({o.email for o in a}) == 200
    assert _osoby(5, 50) != _osoby(6, 50)


# ----------------------------------------------------------------------------- telefony i adresy
def test_telefony_fikcyjne_z_kodem_operatora_00():
    g = Generator("uk", 3)
    numery = [g.telefon() for _ in range(N)]
    for t in numery:
        assert re.fullmatch(r"(\+380|0) 00 \d{3} \d\d \d\d|\+38000\d{7}", t), t
    assert any(t.startswith("+380") for t in numery) and any(t.startswith("0") for t in numery)


ADRES = re.compile(r"^(вул|просп|бульв|пров|пл)\. [^,]+, буд\. \d+[АБ]?(, (кв|оф)\. \d+)?, м\. [^,]+, (?:[^,]+ обл\., )?\d{5}$")


def test_adresy_w_konwencji_ukrainskiej_kod_zgodny_z_obwodem():
    miasta = {}
    for linia in (SLOWNIKI / "miejscowosci.txt").read_text(encoding="utf-8").splitlines():
        m, obwod, pref, _ = linia.split("|")
        miasta[m] = (obwod, pref)
    g = Generator("uk", 11)
    for _ in range(N):
        a = g.adres()
        assert ADRES.match(a.linia()), a.linia()
        assert a.kraj == "UA" and re.fullmatch(r"\d{5}", a.kod)
        obwod, pref = miasta[a.miejscowosc]
        assert a.region == obwod
        assert a.kod.startswith(pref) or (a.miejscowosc == "Київ" and a.kod[:2] in {"01", "02", "03", "04"})
    assert "Київ" in {g.adres().miejscowosc for _ in range(200)}


def test_numer_sprawy_sad_tablica_kwota_data():
    g = Generator("uk", 1)
    g.styl = {"data": 0, "waluta": 0}
    assert re.fullmatch(r"\d{3}/\d{1,5}/24", g.sygnatura(rok=2024))
    assert "суд" in g.sad() and not (set(g.sad()) & ROSYJSKIE)
    assert re.fullmatch(r"[A-Z]{2} \d{4} [A-Z]{2}", g.tablica())
    assert re.fullmatch(r"\d{1,3}( \d{3})*,\d{2} грн", g.kwota())
    assert re.fullmatch(r"\d{1,2} [а-яіїєґ]+ \d{4} р\.", g.data())
    g.styl = {"data": 1, "waluta": 1}
    assert re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", g.data()) and g.kwota().endswith(" грн") and "UAH" not in g.kwota()
    assert g.formatuj_date(dt.date(2024, 6, 14)) == "14.06.2024"
    g.styl = {"data": 0, "waluta": 0}
    assert g.formatuj_date(dt.date(2024, 6, 14)) == "14 червня 2024 р."


# ----------------------------------------------------------------------------- imiona i nazwiska
def test_slowniki_ukrainskie_pierwsza_kolumna_bez_rosyjskich_liter_i_lacinki():
    for plik in ("imiona_m", "imiona_k", "nazwiska"):
        linie = (SLOWNIKI / f"{plik}.txt").read_text(encoding="utf-8").splitlines()
        assert len(linie) >= 40
        for linia in linie:
            uk, _, ru = linia.partition("|")
            assert set(uk) <= UKRAINSKIE_LITERY, (plik, uk)
            assert not (set(uk) & ROSYJSKIE)
            if ru:
                assert ru != uk and set(ru) <= UKRAINSKIE_LITERY | ROSYJSKIE, (plik, linia)
    for linia in (SLOWNIKI / "imiona_ojcow.txt").read_text(encoding="utf-8").splitlines():
        m, k, mr, kr = linia.split("|")
        assert m.endswith(("ович", "йович", "ич")) and k.endswith(("івна", "ївна")) and not (set(m + k) & ROSYJSKIE)
        assert mr.endswith(("ович", "евич", "ич")) and kr.endswith(("овна", "евна", "ична"))
    for plik in ("miejscowosci", "ulice", "firmy_rdzenie", "choroby", "leki"):
        tekst = (SLOWNIKI / f"{plik}.txt").read_text(encoding="utf-8")
        assert not (set(tekst) & ROSYJSKIE), plik            # dane, adresy, instytucje: wyłącznie ukraińskie


def test_osoby_ukrainskie_pisownia_ukrainska_i_form_zenskie():
    for o in _osoby():
        for czesc in (o.imie, o.nazwisko, o.po_batkovi):
            assert set(czesc) <= UKRAINSKIE_LITERY and not (set(czesc) & ROSYJSKIE), czesc
        assert not o.pisownia_ru and o.ru_czesci == ()
        if o.plec == "M":
            assert o.po_batkovi.endswith(("ович", "йович", "ич")) and not o.nazwisko.endswith(("ська", "цька", "ова", "ева"))
        else:
            assert o.po_batkovi.endswith(("івна", "ївна")) and not o.nazwisko.endswith(("ський", "цький", "ий", "ов", "ев", "єв"))
        assert o.pelne_imie == f"{o.nazwisko} {o.imie} {o.po_batkovi}"
        assert (o.imie, o.nazwisko) not in {("Тарас", "Шевченко"), ("Андрій", "Шевченко")}
    assert nazwisko_zenskie("Підгорний") == "Підгорна" and nazwisko_zenskie("Ковальський") == "Ковальська"
    assert nazwisko_zenskie("Ковальов") == "Ковальова" and nazwisko_zenskie("Шевченко") == "Шевченко"
    assert nazwisko_zenskie("Подгорный", ru=True) == "Подгорная" and nazwisko_zenskie("Ковалёв", ru=True) == "Ковалёва"


def test_pisownia_rosyjska_oznaczona_i_tylko_dla_imion_osob():
    osoby = _osoby(9, 400, p_ru=1.0)
    ru = [o for o in osoby if o.pisownia_ru]
    assert len(ru) > 300                                    # tylko wpisy bez różnicy (Олег Петренко…) nie są oznaczone
    wyrazy = {"imie": set(), "nazwisko": set()}
    for o in ru:
        assert set(o.ru_czesci) <= {"imie", "nazwisko", "po_batkovi"} and o.ru_czesci
        if "imie" in o.ru_czesci:
            wyrazy["imie"].add(o.imie)
    assert {"Александр", "Сергей", "Андрей"} & wyrazy["imie"]
    assert any(o.nazwisko in ("Ковалёв", "Ковалёва") for o in ru)
    # adres, instytucje i identyfikatory zawsze ukraińskie, także dla osób z rosyjską pisownią
    for o in ru:
        assert not (set(o.adres.linia()) & ROSYJSKIE) and o.kraj == "UA" and o.telefon
    assert all(not o.pisownia_ru for o in _osoby(9, 100, p_ru=0.0))


def test_pola_dodatkowe_osoby():
    o = _osoby(1, 1)[0]
    p = o.pola_dodatkowe
    assert p["po_batkovi"] == (o.po_batkovi, "OSOBA") and p["pelne_im"][0] == f"{o.imie} {o.nazwisko}"
    assert p["im_po"][0] == f"{o.imie} {o.po_batkovi}"
    assert re.fullmatch(r"\S+ \S\. \S\.", p["pib_skr"][0]) and re.fullmatch(r"\S\. \S\. \S+", p["skr_pib"][0])


def test_login_email_z_transliteracji_i_domeny_zarezerwowane():
    for o in _osoby(2, 100):
        assert o.login.isascii() and o.email.isascii()
        assert o.email.rsplit("@", 1)[1] in {"example.com", "example.org", "example.net", "poshta.test", "webmail.test",
                                             "skrynka.test"}
    g = Generator("uk", 4)
    assert g.url().startswith("https://") and g.url().isascii()


def test_diagnozy_i_leki_po_ukrainsku():
    g = Generator("uk", 1)
    d = g.diagnozy(3, "interna", "K")
    assert len(set(d)) == 3 and all(re.match(r"[A-Z]\d{2}", x) and not (set(x) & ROSYJSKIE) for x in d)
    leki = g.leki(3, "interna")
    assert all(re.fullmatch(r"[^\d]+ [\d,]+ мг", x) for x in leki) and len(set(leki)) == 3


def test_fabryka_zna_uk_a_jezyki_trzonu_bez_zmian():
    from pbench.dane import JEZYKI, JEZYKI_TRUDNE
    assert JEZYKI == ("pl", "en", "es", "de", "fr") and JEZYKI_TRUDNE == ("uk",)
    assert isinstance(Generator("uk", 1), GeneratorUK)
    with pytest.raises(ValueError):
        Generator("ru", 1)
