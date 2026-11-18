"""Wspólne dla języków: daty kontekstu w dni robocze, cytowane orzeczenia sprzed daty dokumentu (rok sygnatury wcześniejszy
niż rok orzeczenia tam, gdzie sygnatura nosi rok wniesienia) oraz Senat BGH wg przedmiotu sporu (DE)."""
from __future__ import annotations

import datetime as dt
import random
import re

import pytest

from pbench.budowa import zbuduj_z_kontekstem
from pbench.dane import Generator
from pbench.dane.wspolne import MIESIACE
from pbench.linearyzacja import linearyzuj_z_wartosciami
from pbench.szablony import SZABLONY, TYPY

JEZYKI = ["pl", "en", "es", "de", "fr"]


def _buduj(j: str, typ: str, ziarno: int, wariant: str | None = None):
    w = zbuduj_z_kontekstem(SZABLONY[(j, typ)], Generator(j, ziarno), random.Random(ziarno), wariant)
    return w, linearyzuj_z_wartosciami(w.dokument)[0]


def _miesiac(j: str, nazwa: str) -> int:
    nazwy = [m.lower() for m in MIESIACE[j]]
    return nazwy.index(nazwa.lower()) + 1


@pytest.mark.parametrize("jezyk", JEZYKI)
def test_wszystkie_daty_kontekstu_w_dni_robocze(jezyk):
    for typ in TYPY:
        for i in range(25):
            w, _ = _buduj(jezyk, typ, 11000 + i)
            zle = {k: v for k, v in w.kontekst.daty.items() if v.weekday() >= 5}
            assert not zle, (jezyk, typ, zle)


def test_data_orzeczenia_po_rozprawie_w_kazdym_jezyku():
    for jezyk in JEZYKI:
        for i in range(80):
            w, _ = _buduj(jezyk, "wyrok", 11500 + i)
            d = w.kontekst.daty
            assert d["rozprawa"] < d["wyrok"] and d["rozprawa_apel"] < d["wyrok_apel"]


@pytest.mark.parametrize("jezyk", JEZYKI)
def test_daty_cytowanych_orzeczen_w_dni_robocze(jezyk):
    """200 budów wyroku: data każdej roli `cytat` przypada w dzień roboczy."""
    for i in range(200):
        # daty cytatów liczy `_Encja`; sprawdzamy je przez ponowną budowę encji z tego samego dokumentu
        from pbench.budowa import _Budowa
        b = _Budowa(SZABLONY[(jezyk, "wyrok")], Generator(jezyk, 14000 + i), random.Random(14000 + i))
        cyt = [e for e in b.encje.values() if e.rodzaj == "cytat"]
        assert len(cyt) >= 2
        for e in cyt:
            d = e._data_cytatu()
            assert d.weekday() < 5 and d < b.ctx.daty["wyrok_koncowy"], (jezyk, d)


def _cytaty_pl(tekst: str):
    for m in re.finditer(r"z dnia (\d{1,2}) (\w+) (\d{4}) r\.?, (?:sygn\. )?[IVX]+ [A-Za-z]+ \d+/(\d{2})", tekst):
        yield dt.date(int(m.group(3)), _miesiac("pl", m.group(2)), int(m.group(1))), 2000 + int(m.group(4))
    for m in re.finditer(r"z dnia (\d{2})\.(\d{2})\.(\d{4}) r\.?, (?:sygn\. )?[IVX]+ [A-Za-z]+ \d+/(\d{2})", tekst):
        yield dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1))), 2000 + int(m.group(4))


def _cytaty_de(tekst: str):
    for m in re.finditer(r"BGH, (?:Urt\. v\. |Beschl\. v\. )(\d{1,2})\.(\d{1,2})\.(\d{4}) – ([IVX]+) ZR \d+/(\d{2})", tekst):
        yield dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1))), 2000 + int(m.group(5))
    for m in re.finditer(r"BGH, Urteil vom (\d{1,2})\. (\w+) (\d{4}) – ([IVX]+) ZR \d+/(\d{2})", tekst):
        yield dt.date(int(m.group(3)), _miesiac("de", m.group(2)), int(m.group(1))), 2000 + int(m.group(5))


def _cytaty_es(tekst: str):
    for m in re.finditer(r"STS \d+/(\d{4}), de (\d{1,2}) de (\w+)", tekst):
        yield dt.date(int(m.group(1)), _miesiac("es", m.group(3)), int(m.group(2))), None


def _cytaty_fr(tekst: str):
    for m in re.finditer(r"(?:Cass\. civ\. 1re|Cass\. 1re civ\.|Civ\. 1re), (1er|\d{1,2}) ([a-zéû]+) (\d{4}), "
                         r"(?:pourvoi )?n° (\d{2})-\d{2}\.\d{3}", tekst):
        yield dt.date(int(m.group(3)), _miesiac("fr", m.group(2)), 1 if m.group(1) == "1er" else int(m.group(1))), 2000 + int(m.group(4))


@pytest.mark.parametrize("jezyk,wyciag,oczekiwane", [("pl", _cytaty_pl, 2), ("de", _cytaty_de, 3), ("es", _cytaty_es, 3),
                                                     ("fr", _cytaty_fr, 3)])
def test_cytowane_orzeczenia_sprzed_daty_dokumentu(jezyk, wyciag, oczekiwane):
    """200 budów wyroku: data każdego cytatu < data orzeczenia dokumentu (rok <=), rok sygnatury < rok orzeczenia."""
    warianty = {"pl": ("rejonowy", "apelacyjny"), "de": ("de_amtsgericht", "de_landgericht", "de_einzelrichter",
                                                                    "de_berufung"),
                "es": ("es_primera", "es_apelacion"), "fr": ("fr_tj_unique", "fr_tj_collegiale", "fr_appel")}[jezyk]
    for i in range(200):
        w, tekst = _buduj(jezyk, "wyrok", 12000 + i, warianty[i % len(warianty)])
        doc = w.kontekst.daty["wyrok_koncowy"]
        cytaty = list(wyciag(tekst))
        assert len(cytaty) >= oczekiwane, (jezyk, tekst[-1200:])
        for data, rok_az in cytaty:
            assert data < doc and data.year <= doc.year, (jezyk, data, doc)
            assert (data >= doc - dt.timedelta(days=1100)), (jezyk, data, doc)
            if rok_az is not None:
                assert rok_az < data.year, (jezyk, data, rok_az)


def test_cytowane_orzeczenia_en_sprzed_daty_dokumentu():
    for i in range(200):
        w, tekst = _buduj("en", "wyrok", 12500 + i)
        doc = w.kontekst.daty["wyrok_koncowy"]
        lata = [int(m) for m in re.findall(r"\[((?:19|20)\d{2})\]", tekst)]
        lata += [int(m) for m in re.findall(r"(?:U\.S\. \d+|\d+ F\.(?:\dd|4th) \d+|\d+ F\. Supp\. (?:2d|3d) \d+) \([^()]*?((?:19|20)\d{2})\)", tekst)]
        assert lata, tekst[-800:]
        assert all(rok <= doc.year for rok in lata), (lata, doc)
        assert all(rok >= doc.year - 3 for rok in lata), (lata, doc)


def test_senat_bgh_wg_przedmiotu_sporu():
    g = Generator("de", 5)
    for przedmiot, senat in (("darlehen", "XI"), ("kauf", "VIII"), ("miete", "VIII"), ("delikt", "VI"), ("werk", "VII")):
        for _ in range(40):
            s = g.sygnatura_cytatu(data=dt.date(2024, 5, 6), przedmiot=przedmiot)
            m = re.search(r" – ([IVX]+) ZR \d+/(\d{2})$", s)
            assert m and m.group(1) == senat and int(m.group(2)) in (22, 23), s
    for i in range(100):                            # szablon wyroku DE dotyczy pożyczki -> XI ZR
        _, tekst = _buduj("de", "wyrok", 13000 + i)
        assert SZABLONY[("de", "wyrok")].przedmiot == "darlehen"
        assert all(s == "XI" for s in re.findall(r" – ([IVX]+) ZR ", tekst)) and " ZR " in tekst
