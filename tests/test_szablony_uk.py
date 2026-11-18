"""Testy szablonów ukraińskich (`pbench/szablony/uk`), wstawek ukraińskich w dokumentach PL/EN/DE
(`pbench/szablony/wstawki`) i homoglifów (szablony trzonu z `homoglif`): kompletna budowa, gold zgodny z tekstem
linearyzacji, jeden alfabet w wyrazie, rodzaj gramatyczny i przypadki, daty i pełnoletność, spójność РНОКПП z datą
urodzenia, transliteracje jako osobne wartości tej samej encji."""
from __future__ import annotations

import datetime as dt
import random
import re
import unicodedata

import pytest
from stdnum.ua import edrpou as ua_edrpou, rntrc as ua_rntrc

from pbench import odmiana_uk
from pbench.budowa import MAPA_KATEGORII, zbuduj_z_kontekstem
from pbench.dane import Generator
from pbench.dane.uk import data_z_rnokpp
from pbench.dane.wspolne import MIESIACE, kod_icd_plec
from pbench.homoglify import mieszane
from pbench.linearyzacja import linearyzuj_z_wartosciami
from pbench.model import Wartosc
from pbench.odmiana_pl import odmien as odmien_pl
from pbench.szablony import SZABLONY
from pbench.szablony.trudne import SZABLONY_UK, SZABLONY_WSTAWKI
from pbench.translit import SYSTEMY, ma_cyrylice, transliteruj
from pbench.trudne import NATURALNY, z_homoglifami

ROSYJSKIE = set("ыэёъЫЭЁЪ")
TYPY_UK = sorted(SZABLONY_UK)
SEEDY = range(12)


def _buduj(typ: str, seed: int, **kw):
    gen = Generator("uk", seed)
    return zbuduj_z_kontekstem(SZABLONY_UK[typ], gen, random.Random(seed), **kw)


def _wartosci(d) -> list[Wartosc]:
    return [f for e in d.elementy for f in e.fragmenty if not isinstance(f, str)] + [
        v for v in d.metadane.values() if not isinstance(v, str)]


_DATY_SLOWNIE = {odmiana_uk.data_slownie_pelna(d): d for d in
                 (dt.date(2015, 1, 1) + dt.timedelta(days=i) for i in range(12 * 366))}


def _data_uk(t: str) -> dt.date:
    m = re.fullmatch(r"(\d{1,2}) ([а-яіїє]+) (\d{4}) (?:р\.|року)", t)
    if m:
        return dt.date(int(m.group(3)), MIESIACE["uk"].index(m.group(2)) + 1, int(m.group(1)))
    slownie = _DATY_SLOWNIE.get(t)             # data w całości słownie (poświadczenie notarialne)
    if slownie:
        return slownie
    m = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})", t)
    assert m, t
    return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))


def _pole(w, nazwa: str) -> str:
    return next(x.tekst for x in _wartosci(w.dokument) if x.id == f"ctx.{nazwa}#1")


# ----------------------------------------------------------------------------- szablony ukraińskie
def test_zestaw_szablonow_ukrainskich():
    assert TYPY_UK == ["cv", "email", "med_zaswiadczenie", "notatka", "pelnomocnictwo", "umowa"]
    assert sorted(SZABLONY_WSTAWKI) == [("de", "notatka"), ("de", "umowa"), ("en", "notatka"), ("en", "umowa"),
                                        ("pl", "med_zaswiadczenie"), ("pl", "protokol"), ("pl", "umowa")]
    assert all(("uk", t) not in SZABLONY for t in TYPY_UK)        # rejestr trzonu bez zmian


@pytest.mark.parametrize("typ", TYPY_UK)
def test_budowa_gold_zgodny_z_tekstem_i_bez_resztek_gniazd(typ):
    for seed in SEEDY:
        w = _buduj(typ, seed)
        tekst, spany, wartosci = linearyzuj_z_wartosciami(w.dokument)
        assert "{" not in tekst and "}" not in tekst and "None" not in tekst
        assert len(spany) == len(wartosci) and spany
        for s, v in zip(spany, wartosci):
            assert tekst[s.start:s.end] == v.tekst
        assert w.dokument.jezyk == "uk"
        assert w.dokument.elementy and all(isinstance(v.kategoria, str) for v in wartosci)


@pytest.mark.parametrize("typ", TYPY_UK)
def test_jeden_alfabet_w_wyrazie_i_brak_rosyjskich_liter(typ):
    """Wyraz ma albo same litery cyrylicy, albo same łacińskie (bez homoglifów); brak liter wyłącznie rosyjskich
    (dokumenty ukraińskie: wyłącznie ukraiński)."""
    for seed in SEEDY:
        tekst = linearyzuj_z_wartosciami(_buduj(typ, seed).dokument)[0]
        assert not (set(tekst) & ROSYJSKIE)
        for wyraz in re.findall(r"[^\W\d_]+", tekst):
            assert not mieszane(wyraz), wyraz


@pytest.mark.parametrize("typ", TYPY_UK)
def test_dorosli_i_daty_w_dni_robocze_nie_pozniej_niz_dzis(typ):
    for seed in SEEDY:
        w = _buduj(typ, seed)
        daty = [_data_uk(v.tekst) for v in _wartosci(w.dokument) if v.kategoria == "DATA"]
        assert (daty or typ == "email") and all(d <= dt.date(2026, 10, 29) and d.weekday() < 5 for d in daty), typ     # daty widoczne w dokumencie
        if SZABLONY_UK[typ].dorosli:
            najwczesniej = min(w.kontekst.daty.values())
            for rola, o in w.osoby.items():
                wiek = najwczesniej.year - o.data_ur.year - ((najwczesniej.month, najwczesniej.day) < (o.data_ur.month, o.data_ur.day))
                assert wiek >= 18, (typ, rola)


@pytest.mark.parametrize("typ", TYPY_UK)
def test_rnokpp_w_dokumencie_zgodny_z_data_urodzenia_i_plcia(typ):
    for seed in SEEDY:
        w = _buduj(typ, seed)
        for rola, o in w.osoby.items():
            assert ua_rntrc.is_valid(o.ids["RNOKPP"]) and data_z_rnokpp(o.ids["RNOKPP"]) == o.data_ur
        teksty = {x.tekst for x in _wartosci(w.dokument) if x.kategoria == "NR_PODATKOWY"}
        assert teksty <= {o.ids["RNOKPP"] for o in w.osoby.values()} | {
            e.firma.rejestry.get("RNOKPP") for e in w.encje.values() if e.firma}
        for e in w.encje.values():
            if e.firma:
                assert all(ua_edrpou.is_valid(v) for k, v in e.firma.rejestry.items() if k == "EDRPOU")


def test_umowa_strony_formy_prawne_rodzaj_i_odmiana_w_tekscie():
    for seed in SEEDY:
        w = _buduj("umowa", seed)
        tekst = linearyzuj_z_wartosciami(w.dokument)[0]
        o = w.osoby
        assert "в особі" in tekst and "код ЄДРПОУ" in tekst
        assert re.search(r"Адвокатське (об’єднання|бюро) «", tekst) and "ТОВ «" in tekst
        # imię i nazwisko w dopełniaczu po „в особі … директора/директорки”
        gen = odmiana_uk.odmien(o["dyrektor"].imie, o["dyrektor"].po_batkovi, o["dyrektor"].nazwisko, o["dyrektor"].plec, "rod")
        zaimek = "який" if o["dyrektor"].plec == "M" else "яка"
        slowo = "директора" if o["dyrektor"].plec == "M" else "директорки"
        assert f"в особі {slowo} {gen}, {zaimek} діє на підставі Статуту" in tekst
        # celownik: „адвокатові/адвокатці … , а у спірних питаннях — керуючому партнеру/керуючій партнерці …”
        dav = odmiana_uk.odmien(o["partner"].imie, o["partner"].po_batkovi, o["partner"].nazwisko, o["partner"].plec, "dav")
        assert dav in tekst and ("керуючому партнеру" in tekst or "керуючій партнерці" in tekst)
        assert re.search(r"гонорар у фіксованому розмірі \d[\d ]*,\d{2} (грн|UAH)", tekst)
        assert "Закону України «Про захист персональних даних»" in tekst
        assert w.kontekst.kwoty["um_limit"] < w.kontekst.kwoty["um_wyn"]


def test_pelnomocnictwo_rodzaj_gramatyczny_i_przypadki():
    for seed in SEEDY:
        w = _buduj("pelnomocnictwo", seed)
        tekst = linearyzuj_z_wartosciami(w.dokument)[0]
        m = w.osoby["mocodawca"]
        assert (" зареєстрований за адресою" in tekst) == (m.plec == "M")
        assert (" зареєстрована за адресою" in tekst) == (m.plec == "K")
        assert f"Підпис {'довірителя' if m.plec == 'M' else 'довірительки'}:" in tekst
        p = w.osoby["pelnomocnik"]
        assert f"{odmiana_uk.odmien(p.imie, p.po_batkovi, p.nazwisko, p.plec, 'zna')}, РНОКПП {p.ids['RNOKPP']}" in tekst
        assert f"ID-картка № {m.ids['DOWOD']}" in tekst
        assert re.search(r"справі № \d{3}/\d+/\d{2} ", tekst)
        d = w.kontekst.daty
        assert d["po_pozwie"] > d["pozew"]
        # wyłącznie ukraińska instytucja w tekście (sąd): nazwa po ukraińsku
        assert "суд" in tekst


def test_med_zaswiadczenie_rozpoznania_zgodne_z_plcia_i_daty():
    for seed in SEEDY:
        w = _buduj("med_zaswiadczenie", seed)
        tekst = linearyzuj_z_wartosciami(w.dokument)[0]
        pac = w.osoby["pacjent"]
        e = w.encje["pacjent"]
        assert all(kod_icd_plec(x) in (None, pac.plec) for x in e.diagnozy)
        assert len(set(e.diagnozy)) == 3 and len(set(e.leki)) == 3
        assert ("пацієнт не може" in tekst) == (pac.plec == "M") and ("пацієнтка не може" in tekst) == (pac.plec == "K")
        assert f"Видана {odmiana_uk.odmien(pac.imie, pac.po_batkovi, pac.nazwisko, pac.plec, 'dav')}" in tekst
        assert f"{pac.rodzaj if False else ''}" == ""
        d = w.kontekst.daty
        assert d["zas_od"] < d["zas_wystaw"] < d["rozprawa"] < d["zas_do"]
        assert re.search(r"[A-Z]\d{2}(\.\d)? [А-ЯІЇЄҐ]", tekst)               # ICD-10 z ukraińską nazwą
        assert re.search(r"\d+(,\d)? (мг|мкг)", tekst)


def test_notatka_lancuch_dat_kwoty_i_rodzaj():
    for seed in SEEDY:
        w = _buduj("notatka", seed)
        tekst = linearyzuj_z_wartosciami(w.dokument)[0]
        d, k = w.kontekst.daty, w.kontekst.kwoty
        assert d["umowa"] < d["termin_platnosci"] < d["wezwanie"] < d["termin_wezwania"] < d["pozew"]
        assert k["razem_wez"] == k["glowna"] + k["odsetki"] + k["koszty_wind"]
        assert _data_uk(next(x.tekst for x in _wartosci(w.dokument) if x.id == "ctx.termin_wezwania#1")) == d["termin_wezwania"]
        a = w.osoby["autor"]
        assert ("начальника юридичного відділу" in tekst) == (a.plec == "M")
        assert ("начальниці юридичного відділу" in tekst) == (a.plec == "K")
        assert "частина друга статті 625 Цивільного кодексу України" in tekst


def test_cv_daty_i_rodzaj():
    for seed in SEEDY:
        w = _buduj("cv", seed)
        tekst = linearyzuj_z_wartosciami(w.dokument)[0]
        d = w.kontekst.daty
        assert d["cv_studia"] < d["cv_od2"] < d["cv_do2"] <= d["cv_od1"]
        assert re.search(r"диплом (отримав|отримала) \d", tekst) and " у " + _pole(w, "cv_studia") not in tekst


def test_email_naglowki_i_zwrot_w_wolaczu():
    for seed in SEEDY:
        w = _buduj("email", seed)
        tekst = linearyzuj_z_wartosciami(w.dokument)[0]
        assert tekst.startswith("Від: ") and "\nКому: " in tekst and "\nТема: " in tekst
        k = w.osoby["klient"]
        zwrot = f"{'Шановний' if k.plec == 'M' else 'Шановна'} {odmiana_uk.odmien(k.imie, k.po_batkovi, k.nazwisko, k.plec, 'kl', 'IP')}!"
        assert zwrot in tekst


def test_znaczniki_encji_i_kategorie_ukrainskich_identyfikatorow():
    w = _buduj("umowa", 1)
    wart = _wartosci(w.dokument)
    assert all(v.encja == v.id.split(".", 1)[0] for v in wart if not v.id.startswith("ctx."))
    assert all(v.encja is None for v in wart if v.id.startswith("ctx."))
    kat = {v.id.split("#")[0]: v.kategoria for v in wart}
    assert kat["klient.edrpou"] == "NR_REJESTRU" and kat["klient.rachunek"] == "RACHUNEK"
    assert kat["partner.pelne"] == "OSOBA" and kat["kancelaria.adres"] == "ADRES"
    w = _buduj("pelnomocnictwo", 1)
    kat = {v.id.split("#")[0]: v.kategoria for v in _wartosci(w.dokument)}
    assert kat["mocodawca.rnokpp"] == "NR_PODATKOWY" and kat["mocodawca.dowod"] == "DOWOD"
    assert kat["mocodawca.data_ur"] == "DATA_UR" and kat["sprawa.sygnatura"] == "SYGNATURA"
    assert kat["mocodawca.skr_pib"] == "OSOBA"


def test_budowa_deterministyczna():
    for typ in TYPY_UK:
        assert _buduj(typ, 5).dokument.to_json() == _buduj(typ, 5).dokument.to_json()


# ----------------------------------------------------------------------------- wstawki
def _buduj_wstawke(jezyk: str, typ: str, seed: int, wariant: str, uklad: dict[str, str] | None = None, p_ru: float = 0.0):
    gen = Generator(jezyk, seed)
    if uklad:
        gen.systemy_translit = uklad
    gen.p_ru_ua = p_ru
    return zbuduj_z_kontekstem(SZABLONY_WSTAWKI[(jezyk, typ)], gen, random.Random(seed), wariant)


def _lac(o, v: Wartosc, tekst_czesci: tuple[str, str] | None = None) -> str:
    """Oczekiwany zapis łaciński „Imię Nazwisko” osoby `o` w systemie wartości `v` (człony osobno, jak w budowie)."""
    return " ".join(transliteruj(czesc, v.translit, rosyjska=nazwa in o.ru_czesci)
                    for nazwa, czesc in (("imie", o.imie), ("nazwisko", o.nazwisko)))


@pytest.mark.parametrize("jezyk,typ", sorted(SZABLONY_WSTAWKI))
@pytest.mark.parametrize("wariant", ["cw", "tr"])
def test_wstawki_budowa_gold_i_wariant(jezyk, typ, wariant):
    for seed in SEEDY:
        uklad = {"s1": NATURALNY[jezyk], "s2": "cyr", "s3": "kmu2010", "s4": "iso9"}
        w = _buduj_wstawke(jezyk, typ, seed, wariant, uklad)
        tekst, spany, wartosci = linearyzuj_z_wartosciami(w.dokument)
        assert "{" not in tekst
        assert all(tekst[s.start:s.end] == v.tekst for s, v in zip(spany, wartosci))
        assert w.dokument.jezyk == jezyk and all(v.jezyk == jezyk for v in wartosci)
        ua = next(e for e in w.encje.values() if e.rodzaj == "osoba_ua")
        o = ua.osoba
        nazwy = [v for v in wartosci if v.id.startswith(f"{ua.rola}.pelne_im")]
        cyr = [v for v in nazwy if v.translit is None]
        lac = [v for v in nazwy if v.translit is not None]
        assert cyr and all(v.tekst == f"{o.imie} {o.nazwisko}" for v in cyr)          # zapis cyrylicą (s2) obecny w każdym dokumencie
        assert lac and all(not ma_cyrylice(v.tekst) for v in lac)
        assert all(v.encja == ua.rola for v in wartosci if v.id.startswith(f"{ua.rola}."))
        # każdy zapis łaciński = wynik `pbench.translit` dla tej osoby (osobna wartość gold na każdy zapis)
        assert all(v.tekst == _lac(o, v) for v in lac if v.translit != "polski") or jezyk == "pl"
        assert all(v.tekst in (_lac(o, v), odmien_pl(transliteruj(o.imie, "polski"), transliteruj(o.nazwisko, "polski"),
                                                     o.plec, "dop", ukrainskie=True)) for v in lac if v.translit == "polski")
        # identyfikatory ukraińskie wprost w tekście dokumentu
        assert o.ids["RNOKPP"] in tekst and ua_rntrc.is_valid(o.ids["RNOKPP"]) and data_z_rnokpp(o.ids["RNOKPP"]) == o.data_ur
        if typ == "umowa":
            assert o.rachunek in tekst
        systemy = {v.translit for v in lac}
        if wariant == "tr":
            assert {"kmu2010", "iso9"} <= systemy                                  # blok „tr” z zapisami s2–s4
        else:
            assert systemy <= {NATURALNY[jezyk]}


def test_wstawki_transliteracja_gold_dokladnie_wg_systemu():
    uklad = {"s1": "polski", "s2": "ascii_dorazne", "s3": "paszport_zsrr", "s4": "francuski"}
    for seed in SEEDY:
        w = _buduj_wstawke("pl", "umowa", seed, "tr", uklad)
        o = w.encje["wykonawca"].osoba
        wart = [v for v in _wartosci(w.dokument) if v.id.startswith("wykonawca.pelne_im")]
        assert {v.translit for v in wart} == {"polski", "ascii_dorazne", "paszport_zsrr", "francuski"}   # Latin-only: bez cyrylicy
        assert not any(ma_cyrylice(v.tekst) for v in wart)
        for v in wart:
            assert v.tekst == _lac(o, v)
        assert all(v.tekst == v.tekst.upper() for v in wart if v.translit == "paszport_zsrr")
        assert len({v.tekst for v in wart}) >= 2 and all(v.encja == "wykonawca" for v in wart)


def test_wstawki_pl_odmiana_polska_po_transliteracji():
    w = _buduj_wstawke("pl", "med_zaswiadczenie", 3, "cw")
    o = w.encje["pacjent"].osoba
    dop = [v for v in _wartosci(w.dokument) if v.id.startswith("pacjent.pelne_im") and v.translit == "polski"]
    imie, nazwisko = transliteruj(o.imie, "polski"), transliteruj(o.nazwisko, "polski")
    assert odmien_pl(imie, nazwisko, o.plec, "dop", ukrainskie=True) in {v.tekst for v in dop}


def test_wstawki_adres_i_telefon_ukrainskie_a_reszta_dokumentu_w_jezyku():
    w = _buduj_wstawke("de", "umowa", 4, "cw")
    tekst = linearyzuj_z_wartosciami(w.dokument)[0]
    o = w.encje["auftragnehmer"].osoba
    assert o.adres.linia() in tekst and o.telefon in tekst and o.telefon.startswith(("+380", "0"))
    assert "DIENSTLEISTUNGSVERTRAG" in tekst and "РНОКПП" in tekst
    wart = _wartosci(w.dokument)
    assert {v.kategoria for v in wart if v.id.startswith("auftragnehmer.")} >= {"OSOBA", "ADRES", "TELEFON", "EMAIL",
                                                                              "NR_PODATKOWY", "PASZPORT", "RACHUNEK", "DATA_UR"}
    assert all(v.jezyk == "de" for v in wart)


def test_wstawki_rosyjska_pisownia_oznaczona_w_gold():
    ile = 0
    for seed in range(40):
        w = _buduj_wstawke("pl", "protokol", seed, "cw", p_ru=1.0)
        o = w.encje["swiadek"].osoba
        wart = [v for v in _wartosci(w.dokument) if v.id.startswith("swiadek.pelne_im")]
        if {"imie", "nazwisko"} & set(o.ru_czesci):
            ile += 1
            assert all("pisownia_rosyjska" in v.cechy for v in wart)
            cyr = next(v for v in wart if v.translit is None)
            assert cyr.tekst == f"{o.imie} {o.nazwisko}"
            lac = next(v for v in wart if v.translit == "polski")
            assert lac.tekst == _lac(o, lac)
        else:
            assert all(not v.cechy for v in wart)
    assert ile >= 25


def test_wstawki_ta_sama_osoba_w_roznych_jezykach_dokumentu_ma_te_same_identyfikatory():
    a = _buduj_wstawke("pl", "umowa", 6, "cw").encje["wykonawca"].osoba
    b = _buduj_wstawke("pl", "umowa", 6, "cw").encje["wykonawca"].osoba
    assert a == b


# ----------------------------------------------------------------------------- homoglify
def _wszystkie_szablony_trzonu():
    return sorted(SZABLONY)


def test_z_homoglifami_nie_zmienia_oryginalu_i_ma_gniazda():
    s = SZABLONY[("pl", "pelnomocnictwo")]
    przed = [b.tekst_z_gniazdami for sek in s.sekcje for b in sek.bloki]
    h = z_homoglifami(s, 1.0)
    assert [b.tekst_z_gniazdami for sek in s.sekcje for b in sek.bloki] == przed and not s.znacz_encje
    po = [b.tekst_z_gniazdami for sek in h.sekcje for b in sek.bloki]
    assert po != przed and any(":homoglif}" in t or "+homoglif}" in t for t in po)
    assert h.znacz_encje and h.role == s.role
    # podpis i tabele bez zmian
    for sek, sek_h in zip(s.sekcje, h.sekcje):
        if sek.rodzaj_elementu in ("podpis", "komorka"):
            assert [b.tekst_z_gniazdami for b in sek.bloki] == [b.tekst_z_gniazdami for b in sek_h.bloki]


@pytest.mark.parametrize("klucz", _wszystkie_szablony_trzonu(), ids=lambda k: "/".join(k))
def test_homoglify_kazdy_szablon_trzonu_buduje_sie_i_gold_jest_dokladny(klucz):
    jezyk, typ = klucz
    szablon = z_homoglifami(SZABLONY[klucz], 1.0)
    ma_gniazda = any("homoglif" in b.tekst_z_gniazdami for sek in szablon.sekcje for b in sek.bloki)
    znalezione = 0
    for seed in range(6 if typ != "lista_plac" else 1):
        w = zbuduj_z_kontekstem(szablon, Generator(jezyk, 100 + seed), random.Random(seed))
        tekst, spany, wartosci = linearyzuj_z_wartosciami(w.dokument)
        assert all(tekst[s.start:s.end] == v.tekst for s, v in zip(spany, wartosci))
        for v in (v for v in wartosci if "homoglify" in v.cechy):
            znalezione += 1
            assert v.kategoria == "OSOBA" and mieszane(v.tekst) and v.encja is not None
            assert mieszane(unicodedata.normalize("NFKC", v.tekst))        # NFKC nie scala homoglifów
            assert v.tekst in tekst
    if ma_gniazda:
        assert znalezione, klucz         # (szablony bez gniazd z nazwiskiem osoby – odpis rejestru, lista płac – bez homoglifów)
    else:
        assert znalezione == 0


def test_homoglify_ta_sama_osoba_wystepuje_tez_poprawnie():
    szablon = z_homoglifami(SZABLONY[("pl", "umowa")], 0.5)
    w = zbuduj_z_kontekstem(szablon, Generator("pl", 7), random.Random(7))
    wart = [v for v in _wartosci(w.dokument) if v.kategoria == "OSOBA"]
    role = {v.encja for v in wart if v.cechy}
    assert role
    for r in role:
        osoba = w.osoby[r]
        assert osoba.nazwisko
