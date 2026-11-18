"""Testy szablonów treści: komplet typów × języków, gęstość danych, rozwiązywalność gniazd, wymogi per typ.

`GOTOWE_JEZYKI` rosła z każdą wysyłką (EN, ES, DE, FR); testy dla języków jeszcze nienapisanych są `xfail(strict)`
– po dopisaniu szablonów język trzeba dodać do listy, inaczej `XPASS` wywali test. Wszystkie języki są gotowe.
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import random
import re

import pytest

from pbench.budowa import Szablon, zbuduj, zbuduj_z_kontekstem
from pbench.dane import Generator
from pbench.linearyzacja import linearyzuj_z_wartosciami
from pbench.model import KATEGORIE
from pbench.szablony import JEZYKI, SZABLONY, TYPY, TYPY_DODATKOWE, TYPY_PRYWATNE

GOTOWE_JEZYKI = ["pl", "en", "es", "de", "fr"]

PARY = [(j, t) for j in JEZYKI for t in (*TYPY, *TYPY_DODATKOWE.get(j, ()))]
#: Pisma i umowy: papier firmowy (nagłówek), stopka kancelarii/nadawcy i podpis.
PISMA = ("umowa", "pozew", "pelnomocnictwo", "wezwanie", "protokol", "notatka")
SLOT = re.compile(r"\{([a-z_][a-z0-9_]*)\.([a-z0-9_]+)(?:/\d+)?(?::[a-z]+|:[^{}|]*\|[^{}]*)?\}")
NIEMIANOWNIK_MIN = 0.30


def _pary(jezyki=None):
    wynik = []
    for j, t in PARY:
        if jezyki is not None and j not in jezyki:
            continue
        marki = [] if j in GOTOWE_JEZYKI else [pytest.mark.xfail(strict=True, reason=f"szablony {j} jeszcze nie napisane")]
        wynik.append(pytest.param(j, t, marks=marki, id=f"{j}-{t}"))
    return wynik


def _szablon(j: str, t: str) -> Szablon:
    return SZABLONY[(j, t)]


def _liczba_blokow(s: Szablon) -> int:
    return sum(len(sek.bloki) for sek in s.sekcje)


def _wszystkie_bloki(s: Szablon) -> Szablon:
    """Wariant szablonu, który zawsze używa wszystkich bloków każdej sekcji (sprawdza każde gniazdo)."""
    return dataclasses.replace(s, sekcje=[dataclasses.replace(sek, min=len(sek.bloki), max=len(sek.bloki))
                                          for sek in s.sekcje])


def _buduj(s: Szablon, ziarno: int, wariant: str | None = None):
    return zbuduj(s, Generator(s.jezyk, ziarno), random.Random(ziarno), wariant)


def _buduj_ctx(s: Szablon, ziarno: int, wariant: str | None = None):
    return zbuduj_z_kontekstem(s, Generator(s.jezyk, ziarno), random.Random(ziarno), wariant)


# ------------------------------------------------------------------------------------------ rejestr
def test_rejestr_klucze_zgodne_z_modulami():
    assert JEZYKI == ("pl", "en", "es", "de", "fr")
    assert len(TYPY) == 15 and len(set(TYPY)) == 15
    assert TYPY_DODATKOWE == {"pl": ("med_skierowanie",)}
    for (j, t), s in SZABLONY.items():
        assert (s.jezyk, s.typ) == (j, t)
        assert j in JEZYKI and (t in TYPY or t in TYPY_DODATKOWE.get(j, ()) or t in TYPY_PRYWATNE)


@pytest.mark.parametrize("jezyk,typ", _pary())
def test_kazdy_typ_kazdy_jezyk_istnieje(jezyk, typ):
    assert (jezyk, typ) in SZABLONY


@pytest.mark.parametrize("jezyk,typ", _pary())
def test_min_8_blokow_na_szablon(jezyk, typ):
    assert _liczba_blokow(_szablon(jezyk, typ)) >= 8


@pytest.mark.parametrize("typ", [t for j, t in PARY if j == "pl"])
def test_pl_min_12_blokow_na_szablon(typ):
    assert _liczba_blokow(_szablon("pl", typ)) >= 12


# ------------------------------------------------------------------------------------------ gniazda
@pytest.mark.parametrize("jezyk,typ", _pary())
def test_gniazda_rozwiazywalne(jezyk, typ):
    """Każde gniazdo każdego bloku (nie tylko wylosowanych) buduje się i wymaga dokładnie ról, których używa."""
    s = _szablon(jezyk, typ)
    for sek in s.sekcje:
        for b in sek.bloki:
            uzyte = {m.group(1) for m in SLOT.finditer(b.tekst_z_gniazdami)} - {"ctx"}   # ctx: rola wbudowana
            assert uzyte == b.wymagane_role, (sek.nazwa, b.tekst_z_gniazdami[:60])
            assert uzyte <= set(s.role)
    for wariant in s.warianty or (None,):
        for ziarno in range(3):
            _buduj(_wszystkie_bloki(s), ziarno, wariant)  # ValueError przy nieznanej roli/polu/przypadku


@pytest.mark.parametrize("jezyk,typ", _pary())
def test_role_szablonu_sa_uzywane(jezyk, typ):
    s = _szablon(jezyk, typ)
    uzyte = {r for sek in s.sekcje for b in sek.bloki for r in b.wymagane_role}
    uzyte |= {m.group(1) for v in s.metadane.values() for m in SLOT.finditer(v)} - {"ctx"}
    assert uzyte == set(s.role)


@pytest.mark.parametrize("jezyk,typ", _pary())
def test_kategorie_gniazd_znane(jezyk, typ):
    """Wszystkie wartości z maksymalnej budowy mają kategorię z modelu (konstruktor `Wartosc` to sprawdza)."""
    _, spany, wartosci = linearyzuj_z_wartosciami(_buduj(_wszystkie_bloki(_szablon(jezyk, typ)), 7))
    assert len(spany) == len(wartosci) > 0
    assert all(w.kategoria in KATEGORIE for w in wartosci)


# ------------------------------------------------------------------------------------------ gęstość
@pytest.mark.parametrize("jezyk,typ", _pary())
def test_dokument_ma_ge_6_wartosci_i_ge_3_kategorie(jezyk, typ):
    s = _szablon(jezyk, typ)
    n = 15 if typ == "lista_plac" else 60
    for i in range(n):
        _, spany, _ = linearyzuj_z_wartosciami(_buduj(s, 1000 + i))
        assert len(spany) >= 6, (i, len(spany))
        assert len({sp.kategoria for sp in spany}) >= 3, (i, {sp.kategoria for sp in spany})


@pytest.mark.parametrize("jezyk,typ", _pary())
def test_budowa_deterministyczna(jezyk, typ):
    s = _szablon(jezyk, typ)
    assert _buduj(s, 5).to_json() == _buduj(s, 5).to_json()
    assert _buduj(s, 5).to_json() != _buduj(s, 6).to_json()


@pytest.mark.parametrize("jezyk,typ", _pary())
def test_bloki_szumu_bez_danych_osobowych(jezyk, typ):
    """Każdy typ (każdy język) ma bloki bez gniazd osób/firm – realny „szum” prawniczy (ustawy, organy, terminy)."""
    s = _szablon(jezyk, typ)
    bez = [b for sek in s.sekcje for b in sek.bloki if not b.wymagane_role]
    assert len(bez) >= 2, (jezyk, typ)


# ------------------------------------------------------------------------------------------ odmiana PL
def test_pl_proza_co_najmniej_30_proc_osob_poza_mianownikiem():
    """Agregat typów prozatorskich (bez tabelarycznych lista_plac i odpis_rejestru; 200 budów): >= 30% wystąpień
    osób w formie innej niż mianownik. Wartości poniżej 30% dla pojedynczych typów są dopuszczalne (ustalenie
    kontrolera) – próg dotyczy sumy."""
    typy = [t for j, t in PARY if j == "pl" and t not in ("lista_plac", "odpis_rejestru")]
    razem = inna = 0
    for i in range(200):
        w = _buduj_ctx(_szablon("pl", typy[i % len(typy)]), i)
        _, _, wartosci = linearyzuj_z_wartosciami(w.dokument)
        for x in wartosci:
            if x.kategoria != "OSOBA":
                continue
            o = w.osoby[x.id.split(".", 1)[0]]
            razem += 1
            inna += x.tekst not in {o.imie, o.nazwisko, o.pelne_imie}
    assert razem > 300
    assert inna / razem >= NIEMIANOWNIK_MIN, (inna, razem)


# ------------------------------------------------------------------------------------------ wymogi per typ
@pytest.mark.parametrize("jezyk,typ", _pary())
def test_pisma_maja_naglowek_stopke_i_podpis(jezyk, typ):
    if typ not in PISMA:
        pytest.skip("nie pismo")
    rodzaje = {sek.rodzaj_elementu for sek in _szablon(jezyk, typ).sekcje}
    assert {"naglowek", "stopka", "podpis"} <= rodzaje
    _, _, wartosci = linearyzuj_z_wartosciami(_buduj(_szablon(jezyk, typ), 3))
    miejsca = {w.miejsce for w in wartosci}
    assert {"naglowek", "stopka"} <= miejsca


def _komorki(d):
    return [e for e in d.elementy if e.rodzaj == "komorka"]


@pytest.mark.parametrize("jezyk", [pytest.param(j, marks=[] if j in GOTOWE_JEZYKI else
                                                [pytest.mark.xfail(strict=True)], id=j) for j in JEZYKI])
def test_lista_plac_min_200_wierszy(jezyk):
    for ziarno in range(3):
        d = _buduj(_szablon(jezyk, "lista_plac"), ziarno)
        wiersze = {(e.atrybuty["tabela"], e.atrybuty["wiersz"]) for e in _komorki(d)}
        assert len(wiersze) >= 200


@pytest.mark.parametrize("jezyk,typ", [p for p in _pary() if p.values[1] in ("faktura", "protokol", "odpis_rejestru")])
def test_typy_tabelaryczne_maja_tabele(jezyk, typ):
    for ziarno in range(5):
        assert len(_komorki(_buduj(_szablon(jezyk, typ), ziarno))) >= 8


@pytest.mark.parametrize("jezyk", [pytest.param(j, marks=[] if j in GOTOWE_JEZYKI else
                                                [pytest.mark.xfail(strict=True)], id=j) for j in JEZYKI])
def test_odpis_rejestru_zarzad_z_identyfikatorami(jezyk):
    _, _, wartosci = linearyzuj_z_wartosciami(_buduj(_szablon(jezyk, "odpis_rejestru"), 2))
    tabela = [w for w in wartosci if w.miejsce == "tabela"]
    assert {"OSOBA", "DATA_UR"} <= {w.kategoria for w in tabela}
    if jezyk not in ("de", "fr"):      # DE, FR: prawdziwe odpisy (Handelsregister, Kbis) nie zawierają ID osób
        assert any(w.kategoria in ("PESEL", "DOWOD", "NR_PODATKOWY", "SSN", "NINO", "DNI", "NIR", "SVNR")
                   for w in tabela)


@pytest.mark.parametrize("jezyk", [pytest.param(j, marks=[] if j in GOTOWE_JEZYKI else
                                                [pytest.mark.xfail(strict=True)], id=j) for j in JEZYKI])
def test_email_ma_naglowki_w_metadanych(jezyk):
    s = _szablon(jezyk, "email")
    assert {"from", "to", "cc"} <= set(s.metadane)
    d = _buduj(s, 1)
    assert all(not isinstance(d.metadane[k], str) for k in ("from", "to", "cc"))
    assert any(e.rodzaj == "stopka" for e in d.elementy)


@pytest.mark.parametrize("jezyk", [pytest.param(j, marks=[] if j in GOTOWE_JEZYKI else
                                                [pytest.mark.xfail(strict=True)], id=j) for j in JEZYKI])
def test_wyrok_cytaty_sygnatura_i_sklad(jezyk):
    s = _szablon(jezyk, "wyrok")
    cytaty = {r for r, k in s.role.items() if k == "cytat"}
    assert 2 <= len(cytaty) <= 4
    sedziowie = {r for r, k in s.role.items() if k == "osoba" and r.startswith(("sedzia", "judge", "juez", "richter",
                                                                              "juge"))}
    assert len(sedziowie) >= 2
    for ziarno in range(5):
        d = _buduj(s, ziarno)
        _, spany, wartosci = linearyzuj_z_wartosciami(d)
        assert any(w.kategoria == "SYGNATURA" and w.id.startswith("sad.") for w in wartosci)
        assert {w.id.split(".", 1)[0] for w in wartosci} & sedziowie
        assert not any(w.id.startswith(tuple(cytaty)) for w in wartosci)  # cytaty to zwykły tekst


@pytest.mark.parametrize("jezyk,typ", [p for p in _pary() if p.values[1].startswith("med_")])
def test_med_ma_rozpoznanie_leki_i_strony(jezyk, typ):
    s = _szablon(jezyk, typ)
    assert {"pacjent", "lekarz"} <= {k for k in s.role.values()}
    kategorie = set()
    for ziarno in range(10):
        _, spany, _ = linearyzuj_z_wartosciami(_buduj(s, ziarno))
        kategorie |= {sp.kategoria for sp in spany}
    assert {"OSOBA", "DATA_UR"} <= kategorie
    assert "ZDROWIE" not in kategorie       # rozpoznania (ICD) i leki są tekstem dokumentu, nie gold
    if jezyk == "pl":
        assert "NR_ID" in kategorie  # numer PWZ lekarza


@pytest.mark.parametrize("jezyk,typ", [p for p in _pary() if p.values[1] == "prezentacja"])
def test_prezentacja_krotkie_bloki_i_tabela(jezyk, typ):
    s = _szablon(jezyk, typ)
    akapity = [b for sek in s.sekcje if sek.rodzaj_elementu in ("akapit", "naglowek") for b in sek.bloki]
    assert sum(len(b.tekst_z_gniazdami) <= 220 for b in akapity) >= len(akapity) * 0.8
    assert any(sek.rodzaj_elementu == "komorka" for sek in s.sekcje)


# ------------------------------------------------------------------------------------------ spójność kontekstu
MIESIACE = {m: i for i, m in enumerate(("stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca",
                                         "sierpnia", "września", "października", "listopada", "grudnia"), 1)}
ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")


def _data(tekst: str) -> dt.date:
    """Polski zapis daty z „r.” na końcu: „12 marca 2024 r.” albo „12.03.2024 r.”."""
    m = re.fullmatch(r"(\d{1,2}) (\w+) (\d{4}) r\.", tekst)
    if m:
        return dt.date(int(m.group(3)), MIESIACE[m.group(2)], int(m.group(1)))
    m = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4}) r\.", tekst)
    assert m, f"zły zapis daty: {tekst!r}"
    return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))


def _grosze(tekst: str) -> int:
    m = re.fullmatch(r"(\d{1,3}(?: \d{3})*),(\d{2}) (?:zł|PLN)", tekst)
    assert m, f"zły zapis kwoty: {tekst!r}"
    return int(m.group(1).replace(" ", "")) * 100 + int(m.group(2))


def _pole(wartosci, nazwa: str, nr: int = 1) -> str:
    """Tekst `nr`-tego wystąpienia pola kontekstu `ctx.<nazwa>` w dokumencie."""
    return next(w.tekst for w in wartosci if w.id == f"ctx.{nazwa}#{nr}")


def _zbuduj_pl(typ: str, n: int = 200, warianty=None):
    s = _szablon("pl", typ)
    for i in range(n):
        wariant = None if warianty is None else warianty[i % len(warianty)]
        w = _buduj_ctx(s, 5000 + i, wariant)
        yield w, linearyzuj_z_wartosciami(w.dokument)


def test_pl_daty_polskie_bez_iso_i_bez_podwojnej_kropki():
    """W polskiej prozie daty zawsze z „r.” (nigdy ISO), bez „r..”, jeden styl zapisu w dokumencie."""
    typy = [t for j, t in PARY if j == "pl"]
    for i in range(200):
        w = _buduj_ctx(_szablon("pl", typy[i % len(typy)]), i)
        tekst, _, wartosci = linearyzuj_z_wartosciami(w.dokument)
        assert not ISO.search(tekst), (w.dokument.typ, ISO.search(tekst).group())
        assert "r.." not in tekst and ". r." not in tekst, w.dokument.typ
        daty = [x.tekst for x in wartosci if x.kategoria == "DATA"]
        assert all(x.endswith(" r.") for x in daty), daty
        for x in daty:
            _data(x)                                       # parsuje się
        assert len({bool(re.fullmatch(r"\d{2}\.\d{2}\.\d{4} r\.", x)) for x in daty}) <= 1, daty   # jeden styl


def test_pl_kwoty_jeden_symbol_waluty_w_dokumencie():
    for typ in ("wyrok", "faktura", "wezwanie"):
        for w, (tekst, _, wartosci) in _zbuduj_pl(typ, 40):
            symbole = {x.tekst.rsplit(" ", 1)[1] for x in wartosci if x.kategoria == "KWOTA"}
            assert len(symbole) == 1, (typ, symbole)


def test_wyrok_daty_kwoty_sygnatura_i_sklad():
    for i, (w, (tekst, _, wartosci)) in enumerate(_zbuduj_pl("wyrok", 200, ["rejonowy", "apelacyjny"])):
        k, d = w.kontekst, w.kontekst.daty
        apel = k.wariant == "apelacyjny"
        lancuch = ["umowa", "termin_platnosci", "wezwanie", "termin_wezwania", "pozew", "rozprawa", "wyrok"]
        lancuch += ["apelacja", "rozprawa_apel", "wyrok_apel"] if apel else []
        assert all(d[a] < d[b] for a, b in zip(lancuch, lancuch[1:])) or all(d[a] <= d[b] for a, b in zip(lancuch, lancuch[1:])), i
        assert d["rozprawa"] <= d["wyrok"] and d["rozprawa_koncowa"] <= d["wyrok_koncowy"]
        assert _data(_pole(wartosci, "wyrok_koncowy")) == d["wyrok_koncowy"]
        assert _data(_pole(wartosci, "rozprawa_koncowa")) <= _data(_pole(wartosci, "wyrok_koncowy"))
        # sygnatura: rok wpływu sprawy, nie późniejszy niż orzeczenie
        sygn = next(x.tekst for x in wartosci if x.id == "sad.sygnatura#1")
        assert sygn.endswith(f"/{k.sygn_rok % 100:02d}") and k.sygn_rok <= d["wyrok_koncowy"].year
        assert (" Ca " in sygn) == apel
        # kwoty
        kw = k.kwoty
        assert kw["zasadzona"] < kw["glowna"] and kw["koszty_procesu"] < kw["glowna"]
        assert kw["koszty_procesu"] == kw["koszty_zast"] + kw["oplata_pozwu"] + 17_00 and kw["oplata_nieuisz"] < kw["oplata_pozwu"]
        assert kw["glowna"] <= 100_000_00
        if not apel:
            assert _grosze(_pole(wartosci, "zasadzona")) < _grosze(_pole(wartosci, "glowna"))
            assert _grosze(_pole(wartosci, "koszty_procesu")) > _grosze(_pole(wartosci, "koszty_zast"))
        # skład: pierwsza instancja – jeden sędzia w sądzie rejonowym; apelacja – trzech w okręgowym
        sedziowie = {x.id.split(".")[0] for x in wartosci if x.id.startswith("sedzia")}
        assert sedziowie == ({"sedzia1", "sedzia2", "sedzia3"} if apel else {"sedzia1"}), (i, sedziowie)
        assert ("Sąd Okręgowy" if apel else "Sąd Rejonowy") in tekst.split("\n")[4], tekst.split("\n")[4]


def test_pozew_daty_kwoty_i_poziom_sadu():
    for i, (w, (tekst, _, wartosci)) in enumerate(_zbuduj_pl("pozew", 200)):
        k, d = w.kontekst, w.kontekst.daty
        assert d["umowa"] < d["termin_platnosci"] < d["wezwanie"] < d["termin_wezwania"] < d["pozew"]
        assert _data(_pole(wartosci, "pozew")) == d["pozew"]
        assert all(_data(x.tekst) <= d["pozew"] for x in wartosci if x.kategoria == "DATA"), i
        assert all(int(x.tekst[-2:]) <= d["pozew"].year % 100 for x in wartosci if x.kategoria == "SYGNATURA"), i
        assert k.kwoty["oplata_pozwu"] == round(k.kwoty["glowna"] * 0.05)
        assert _grosze(_pole(wartosci, "oplata_pozwu")) < _grosze(_pole(wartosci, "glowna"))
        okr = k.kwoty["glowna"] > 100_000_00
        assert (k.wariant == "okregowy") == okr and (k.wariant == "rejonowy") == (not okr)
        assert ("Sąd Okręgowy" if okr else "Sąd Rejonowy") in tekst


def test_wezwanie_daty_i_suma_zobowiazan():
    for i, (w, (tekst, _, wartosci)) in enumerate(_zbuduj_pl("wezwanie", 200)):
        d = w.kontekst.daty
        assert d["umowa"] < d["termin_platnosci"] < d["wezwanie"] < d["termin_wezwania"]
        assert _data(_pole(wartosci, "wezwanie")) == d["wezwanie"]
        assert _data(_pole(wartosci, "termin_wezwania")) > _data(_pole(wartosci, "wezwanie"))
        suma = sum(_grosze(_pole(wartosci, n)) for n in ("glowna", "odsetki", "koszty_wind"))
        assert _grosze(_pole(wartosci, "razem_wez")) == suma, i
        assert w.kontekst.kwoty["ugoda_rata"] < w.kontekst.kwoty["glowna"]


def test_faktura_i_lista_plac_sumy_sie_zgadzaja():
    for w, (_, _, wartosci) in _zbuduj_pl("faktura", 60):
        netto = sum(_grosze(_pole(wartosci, n)) for n in ("kf1", "kf2", "kf3"))
        assert _grosze(_pole(wartosci, "netto")) == netto
        assert _grosze(_pole(wartosci, "brutto")) == netto + _grosze(_pole(wartosci, "vat"))
        assert abs(_grosze(_pole(wartosci, "vat")) - netto * 0.23) <= 1
        assert _data(_pole(wartosci, "dok_sprzedaz")) <= _data(_pole(wartosci, "dok")) <= _data(_pole(wartosci, "dok_termin_fv"))
    for w, (_, _, wartosci) in _zbuduj_pl("lista_plac", 5):
        wiersze = [_grosze(x.tekst) for x in wartosci if x.id.startswith("ctx.brutto_")]
        assert len(wiersze) >= 200
        assert _grosze(_pole(wartosci, "suma_212")) == sum(wiersze[:212])


def test_med_wypis_kolejnosc_dat():
    for i, (w, (_, _, wartosci)) in enumerate(_zbuduj_pl("med_wypis", 200)):
        przyjecie, wypis = _data(_pole(wartosci, "przyjecie")), _data(_pole(wartosci, "wypis"))
        assert przyjecie < wypis < _data(_pole(wartosci, "kontrola")), i
        assert wypis <= _data(_pole(wartosci, "zwolnienie_do")), i
        urodzenie = _data(next(x.tekst for x in wartosci if x.kategoria == "DATA_UR"))
        assert urodzenie < przyjecie


def test_med_skierowanie_i_zaswiadczenie_kolejnosc_dat():
    for w, (_, _, wartosci) in _zbuduj_pl("med_skierowanie", 60):
        assert _data(_pole(wartosci, "dok")) < _data(_pole(wartosci, "dok_termin"))
    for w, (_, _, wartosci) in _zbuduj_pl("med_zaswiadczenie", 60):
        od, wyst, rozprawa, do = (_data(_pole(wartosci, n)) for n in ("zas_od", "zas_wystaw", "rozprawa", "zas_do"))
        assert od < wyst < rozprawa < do
        sygn = next(x.tekst for x in wartosci if x.kategoria == "SYGNATURA")
        assert int(sygn[-2:]) <= wyst.year % 100


def test_odpis_rejestru_daty_kapital_i_sygnatura_rejestrowa():
    for i, (w, (_, _, wartosci)) in enumerate(_zbuduj_pl("odpis_rejestru", 200)):
        rej, wpis, odpis = (_data(_pole(wartosci, n)) for n in ("kr_rejestracja", "kr_wpis", "dok"))
        assert rej <= wpis <= odpis, i
        kapital = _grosze(_pole(wartosci, "kapital2"))
        assert kapital >= 5_000_00 and kapital % 50_00 == 0, kapital
        sygn = _pole(wartosci, "sygn_rej")
        assert re.fullmatch(r"[A-Z]{2}\.[IVX]+ NS-REJ\.KRS/\d{6}/\d{2}", sygn), sygn
        assert sygn.endswith(f"/{wpis.year % 100:02d}")
        assert not any(" Gc " in x.tekst or " Ga " in x.tekst for x in wartosci if x.kategoria == "SYGNATURA")


def test_protokol_kapital_zgodny_z_udzialami():
    for w, (_, _, wartosci) in _zbuduj_pl("protokol", 60):
        u = w.kontekst.liczby
        assert w.kontekst.kwoty["kapital3"] == (u["udzialy1"] + u["udzialy2"] + u["udzialy3"]) * 50_00 >= 5_000_00
        assert _data(_pole(wartosci, "dok")) < _data(_pole(wartosci, "dok_pozniej"))


def test_cv_kolejnosc_dat():
    for w, (_, _, wartosci) in _zbuduj_pl("cv", 60):
        s, o2, d2, o1 = (_data(_pole(wartosci, n)) for n in ("cv_studia", "cv_od2", "cv_do2", "cv_od1"))
        assert s < o2 < d2 <= o1


def test_wszystkie_daty_nie_pozniej_niz_dzis():
    dzis = dt.date(2026, 10, 29)
    for typ in [t for j, t in PARY if j == "pl"]:
        for w, (_, _, wartosci) in _zbuduj_pl(typ, 30):
            assert all(_data(x.tekst) <= dzis + dt.timedelta(days=400) for x in wartosci if x.kategoria == "DATA"), typ
            assert max(w.kontekst.daty[n] for n in ("umowa", "wyrok_apel", "rozprawa", "pozew")) <= dzis


# ------------------------------------------------------------------------------------------ zgodność rodzaju PL
MESKIE_ROLE = {   # rola -> formy męskie rzeczownika roli, które nie mogą stać przy kobiecie
    "pozwany": r"[Pp]ozwan(?:y|ego|emu|ym)", "powod": r"[Pp]owod(?:a|owi|em)|[Pp]owód",
    "sedzia1": r"[Pp]rzewodniczący", "biegly": r"biegłego",
    "pacjent": r"[Pp]acjent(?:a|owi|em)?|wymieniony pacjent", "dluznik": r"[Dd]łużnik(?:a|owi|iem)?",
    "mocodawca": r"[Mm]ocodawc(?:a|y|ę|ą|om)",
}
ZAKAZANE_ROLE_PL = {"wyrok": ("pozwany", "powod", "sedzia1", "biegly"), "pozew": ("pozwany", "powod"),
                    "wezwanie": ("dluznik",), "pelnomocnictwo": ("mocodawca",),
                    "med_wypis": ("pacjent",), "med_skierowanie": ("pacjent",), "med_zaswiadczenie": ("pacjent",)}


@pytest.mark.parametrize("typ", sorted(ZAKAZANE_ROLE_PL))
def test_pl_kobieta_nie_wystepuje_z_meskim_rzeczownikiem_roli(typ):
    """Zgodność rodzaju: gdy strona jest kobietą, jej rola nie pojawia się w formie męskiej (200 budów)."""
    s = _szablon("pl", typ)
    widziane = set()
    for i in range(200):
        w = _buduj_ctx(s, 9000 + i, ["rejonowy", "apelacyjny"][i % 2] if typ == "wyrok" else None)
        tekst, _, _ = linearyzuj_z_wartosciami(w.dokument)
        for rola in ZAKAZANE_ROLE_PL[typ]:
            if rola in w.osoby and w.osoby[rola].plec == "K":
                widziane.add(rola)
                m = re.search(rf"\b(?:{MESKIE_ROLE[rola]})\b", tekst)
                assert m is None, (typ, rola, m and tekst[max(0, m.start() - 40):m.end() + 40])
    assert widziane == set(ZAKAZANE_ROLE_PL[typ]) & set(s.role)


# ------------------------------------------------------------------------------------------ medycyna
PULE = {"med_wypis": "kardiologia", "med_zaswiadczenie": "interna", "med_skierowanie": "interna"}


@pytest.mark.parametrize("typ", sorted(PULE))
def test_pl_rozpoznania_zgodne_z_profilem_i_plcia(typ):
    """Rozpoznania i leki z puli profilu szablonu (kardiologia/interna), różne, zgodne z płcią pacjenta."""
    from pbench.dane.wspolne import kod_icd_plec, slownik
    profil = PULE[typ]
    assert _szablon("pl", typ).profil == profil
    choroby, leki = set(slownik("pl", f"choroby_{profil}")), {x.split("|")[0] for x in slownik("pl", f"leki_{profil}")}
    plcie = set()
    for w, (tekst, _, wartosci) in _zbuduj_pl(typ, 200):
        plec = w.osoby["pacjent"].plec
        plcie.add(plec)
        diag = [d for d in w.encje["pacjent"].diagnozy if d in tekst]
        meds = [d for d in w.encje["pacjent"].leki if d in tekst]
        assert diag and meds
        assert all(d in choroby and kod_icd_plec(d) in (None, plec) for d in diag), diag
        assert all(m.rsplit(" ", 2)[0] in leki for m in meds), meds
        assert len(set(diag)) == len(diag) and len(set(meds)) == len(meds)
    assert plcie == {"M", "K"}


@pytest.mark.parametrize("typ", [t for j, t in PARY if j == "pl" and t.startswith("med_")])
def test_pl_bez_fantomowych_pacjentow(typ):
    """Jedna encja pacjenta na dokument; dodatkowe rozpoznania i leki to jej pola (`diagnoza2`, `lek3`…)."""
    assert sum(k == "pacjent" for k in _szablon("pl", typ).role.values()) == 1
    assert sum(k == "placowka" for k in _szablon("pl", typ).role.values()) >= 1


# ------------------------------------------------------------------------------------------ etykiety metadanych
def test_pl_linearyzacja_bez_zmian_wzgledem_migawki():
    """Wynik linearyzacji PL (96 dokumentów: 16 typów × 6 ziaren) zgodny co do bajtu z migawką sum SHA-256
    (linearyzacja bez kanonicznych kluczy metadanych). Wyjątek: wpisy
    `email` przeliczone po przeniesieniu nagłówków e-maila na początek dokumentu (decyzja kontrolera). Drugi świadomy wyjątek (poprawka 1 ES): wpisy typów z `Szablon.dorosli` (odpis_rejestru, protokol,
    umowa, pelnomocnictwo) przeliczone po ograniczeniu dat urodzenia osób pełniących funkcje do >= 18 lat. Trzeci świadomy wyjątek (poprawka 1 DE,
    decyzja kontrolera): wszystkie daty kontekstu w dni robocze, wyrok po rozprawie, daty cytowanych orzeczeń w szablonie
    `wyrok` – baseline PL przeliczony raz celowo (71 z 96 wpisów). Czwarty świadomy wyjątek: poprawki generatorów
    identyfikatorów (telefony 000…, numery rejestracyjne, PWZ, kody KW) zmieniają wartości, więc baseline przeliczony ponownie."""
    import hashlib
    import json
    from pathlib import Path
    wzorzec = json.loads((Path(__file__).parent / "dane_testowe" / "pl_linearyzacja_migawka.json").read_text())
    assert len(wzorzec) == 96
    for klucz, (suma, n) in wzorzec.items():
        typ, ziarno = klucz.split(":")
        tekst, spany, _ = linearyzuj_z_wartosciami(_buduj(_szablon("pl", typ), int(ziarno)))
        assert (hashlib.sha256(tekst.encode()).hexdigest(), len(spany)) == (suma, n), klucz


POLSKIE_ETYKIETY = re.compile(r"^(?:Autor|Temat|Od|Do|DW|Sprawa|Numer KRS|Tytul|Podmiot): ", re.M)


@pytest.mark.parametrize("jezyk,typ", [p for p in _pary(["en"])])
def test_en_tekst_bez_polskich_etykiet_metadanych(jezyk, typ):
    for i in range(10):
        tekst, _, _ = linearyzuj_z_wartosciami(_buduj(_szablon(jezyk, typ), 40 + i))
        assert POLSKIE_ETYKIETY.search(tekst) is None, (typ, POLSKIE_ETYKIETY.search(tekst).group())
        assert re.search(r"^(?:Author|Subject|Case|Entity|From): ", tekst, re.M)


def test_en_email_naglowki_na_poczatku():
    tekst, _, _ = linearyzuj_z_wartosciami(_buduj(_szablon("en", "email"), 3))
    assert re.match(r"From: .+\nTo: .+\nCc: .+\nSubject: .+\n", tekst)
    tekst, _, _ = linearyzuj_z_wartosciami(_buduj(_szablon("pl", "email"), 3))
    assert re.match(r"Od: .+\nDo: .+\nDW: .+\nTemat: .+\n", tekst)
