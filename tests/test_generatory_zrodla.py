"""Generatory identyfikatorów: każdy test losuje N próbek z własnym ziarnem i sprawdza regułę ze źródła
(źródła w komentarzach generatorów i w `metodyka/znane-ograniczenia.md`)."""
from __future__ import annotations

import random
import re

import phonenumbers
import pytest

from pbench.dane import Generator, de, en, fr, pl, uk

N = 4000


def _rng(n: int) -> random.Random:
    return random.Random(990000 + n)


# ----------------------------------------------------------------------------- PL
def test_pwz_nie_zaczyna_sie_od_zera_i_ma_poprawna_sume():
    r = _rng(1)
    for _ in range(N):
        n = pl.pwz(r)
        assert re.fullmatch(r"[1-9]\d{6}", n), n
        assert sum(int(c) * w for c, w in zip(n[1:], range(1, 7))) % 11 == int(n[0])


def test_kody_wydzialow_kw_istnieja_w_zalaczniku():
    assert not {"LU1L", "ZG1Z"} & set(pl._KW_SADY) and {"LU1S", "ZG1E"} <= set(pl._KW_SADY)
    r = _rng(2)
    assert all(pl.ksiega_wieczysta(r).split("/")[0] in pl._KW_SADY for _ in range(N))


def test_tablica_pl_prefiksy_uklady_i_litery():
    zle_prefiksy = {"LL", "KA", "OL", "ZG", "BY", "LD"}
    assert not zle_prefiksy & set(pl._TABLICA_PREFIKSY)
    g = Generator("pl", 990003)
    uklady2 = [r"\d{5}", r"\d{4}[A-Z]", r"\d[A-Z]\d{3}"]
    uklady3 = [r"[A-Z]\d{3}", r"\d{2}[A-Z]{2}", r"\d[A-Z]\d{2}"]
    for _ in range(N):
        pref, suf = g.tablica().split(" ")
        assert pref in pl._TABLICA_PREFIKSY
        assert any(re.fullmatch(u, suf) for u in (uklady2 if len(pref) == 2 else uklady3)), (pref, suf)
        assert not set(suf) & set("BDIOZ") and any(c in "123456789" for c in suf if c.isdigit()), suf


# ----------------------------------------------------------------------------- UA
def test_tablica_ua_kod_regionu_z_listy_dstu():
    g = Generator("uk", 990004)
    assert len(uk._KODY_REGIONOW) == 28 == len(set(uk._KODY_REGIONOW))
    for _ in range(N):
        kod, num, koniec = g.tablica().split(" ")
        assert kod in uk._KODY_REGIONOW and re.fullmatch(r"\d{4}", num) and num != "0000" and len(koniec) == 2


# ----------------------------------------------------------------------------- DE
def test_lanr_kod_grupy_z_anlage_2_i_suma_kontrolna():
    r = _rng(5)
    dozwolone = {f"{n:02d}" for n in (*range(1, 70), 85, 87, 91, 99)}
    for _ in range(N):
        n = de.lanr(r)
        assert re.fullmatch(r"\d{9}", n) and n[7:] in dozwolone, n
        assert (10 - sum(int(c) * (4 if i % 2 == 0 else 9) for i, c in enumerate(n[:6])) % 10) % 10 == int(n[6])


def test_personalausweis_znaki_z_pauswv():
    r = _rng(6)
    for _ in range(N):
        assert re.fullmatch(r"[LMNPRTVWXY][CFGHJKLMNPRTVWXYZ1-9]{8}", de.personalausweis(r))


def test_telefony_de_tylko_pule_bnetza():
    pule = re.compile(r"\+49(30 ?23125|40 ?66969|69 ?90009|89 ?99998|221 ?4710)\d{3}")
    komorki = re.compile(r"\+49(15228817386|15228895456|15254599371|17139200\d\d|1729925904|1729968532|1729973185|"
                         r"1729973186|1729980752|1749091317|1749464308|176040690\d\d)")
    for seed in range(40):
        g = Generator("de", 990100 + seed)
        for _ in range(60):
            o = g.osoba()
            e164 = "+" + re.sub(r"\D", "", phonenumbers.format_number(phonenumbers.parse(o.telefon, "DE"), phonenumbers.PhoneNumberFormat.E164))
            assert pule.fullmatch(e164) or komorki.fullmatch(e164), o.telefon


# ----------------------------------------------------------------------------- FR
RACINES = {"199": "00", "261": "91", "353": "01", "465": "71", "536": "49", "639": "98"}


def test_telefony_fr_tylko_racines_arcep():
    wzor = re.compile(r"\+33(1 ?99 ?00|2 ?61 ?91|3 ?53 ?01|4 ?65 ?71|5 ?36 ?49|6 ?39 ?98)\d{4}")
    for seed in range(40):
        g = Generator("fr", 990200 + seed)
        for _ in range(60):
            t = g.telefon()
            e164 = "+33" + re.sub(r"\D", "", t).removeprefix("33").removeprefix("0")
            assert wzor.fullmatch(e164), t


def test_tablica_fr_bez_ww_i_ss():
    g = Generator("fr", 990201)
    for _ in range(N):
        a, c, b = g.tablica().split("-")
        assert "WW" not in (a, b) and "SS" not in (a, b)


# ----------------------------------------------------------------------------- GB / US
def test_nino_bez_prefiksow_nieprzydzielanych():
    r = _rng(7)
    zle = {"BG", "GB", "KN", "NK", "NT", "TN", "ZZ", "NC", "PY", "PZ"}
    assert all(en.nino(r)[:2] not in zle for _ in range(N * 3))


def test_iban_gb_srlg_ma_sort_code_60():
    g = Generator("en", 990008)
    g.kraj_dok = "GB"
    widziane = 0
    for _ in range(N):
        i = g.iban("GB")
        if i[4:8] == "SRLG":
            widziane += 1
            assert i[8:10] == "60"
    assert widziane > 0


def test_kod_pocztowy_gb_dystrykt_w_zakresie():
    g = Generator("en", 990009)
    g.kraj_dok = "GB"
    for _ in range(N):
        a = g.adres("GB")
        m = re.fullmatch(r"([A-Z]{1,2})(\d{1,2}) \d[A-Z]{2}", a.kod)
        assert m, a.kod
        assert 1 <= int(m.group(2)) <= en._MAKS_DYSTRYKT_GB.get(m.group(1), en._MAKS_DYSTRYKT_GB_DOMYSLNY), a.kod
    assert en._MAKS_DYSTRYKT_GB == {"HG": 5, "SP": 11, "FY": 8, "TF": 13}


def test_tablica_gb_druga_litera_bez_i_q_z():
    g = Generator("en", 990010)
    g.kraj_dok = "GB"
    for _ in range(N):
        t = g.tablica("GB")
        assert re.fullmatch(r"[A-Z]{2}\d{2} [A-Z]{3}", t) and t[1] not in "IQZ" and t[0] not in "IQZ", t


def test_telefony_gb_tylko_pule_ofcom():
    wzor = re.compile(r"\+44(20 ?7946 ?0\d{3}|(161|113|114|115|116|117|118|121|151) ?496 ?0\d{3}|191 ?498 ?0\d{3}|"
                      r"7700 ?900\d{3})")
    for seed in range(40):
        g = Generator("en", 990300 + seed)
        g.kraj_dok = "GB"
        for _ in range(60):
            t = g.telefon("GB")
            e164 = "+44" + re.sub(r"\D", "", t).removeprefix("44").removeprefix("0")
            assert wzor.fullmatch(e164), t


def test_telefony_us_tylko_555_01xx():
    for seed in range(40):
        g = Generator("en", 990400 + seed)
        g.kraj_dok = "US"
        for _ in range(60):
            cyfry = re.sub(r"\D", "", g.telefon("US")).removeprefix("1")
            assert re.fullmatch(r"\d{3}55501\d\d", cyfry), cyfry


# ----------------------------------------------------------------------------- PL, ES, UA: fikcyjny format 00…
def test_telefony_pl_es_ua_zaczynaja_sie_od_00():
    for seed in range(40):
        for jezyk, nowy in (("pl", r"(\+48 )?000 \d{3} \d{3}|\+48000\d{6}"),
                            ("es", r"000 \d{3} \d{3}|\+34 000 \d\d \d\d \d\d|\+34000\d{6}"),
                            ("uk", r"0 00 \d{3} \d\d \d\d|\+380 00 \d{3} \d\d \d\d|\+38000\d{7}")):
            g = Generator(jezyk, 990500 + seed)
            for _ in range(40):
                t = g.telefon()
                assert re.fullmatch(nowy, t), (jezyk, t)
                cyfry = re.sub(r"\D", "", t)
                po_kodzie = {"pl": cyfry.removeprefix("48"), "es": cyfry.removeprefix("34"),
                             "uk": cyfry.removeprefix("380") if t.startswith("+") else cyfry.removeprefix("0")}[jezyk]
                assert po_kodzie.startswith("00") and len(po_kodzie) == (9 if jezyk == "uk" else 9), t
