"""Przecieki polskich elementów do dokumentów obcojęzycznych oraz pełnoletność osób pełniących funkcje."""
from __future__ import annotations

import random
import re

import pytest

from pbench.budowa import zbuduj_z_kontekstem
from pbench.dane import Generator
from pbench.dane.wspolne import DOMENY_EMAIL_JEZYK
from pbench.linearyzacja import linearyzuj_z_wartosciami
from pbench.szablony import SZABLONY, TYPY

NIEPL = ["en", "es", "de", "fr"]
POLSKIE_ZNAKI = re.compile("[ąćęłńśźż]", re.I)
POLSKIE_SLOWA = re.compile(r"\b(?:umowa|biuro|poczta|pozew|spółka|przeciwko|wezwanie|pełnomocnictwo)\b", re.I)
FUNKCJE = ("odpis_rejestru", "protokol", "umowa", "pelnomocnictwo")


def test_domeny_email_zarezerwowane_i_bez_polskich_slow_poza_pl():
    for j, domeny in DOMENY_EMAIL_JEZYK.items():
        assert all(d.endswith((".test", "example.com", "example.org", "example.net")) for d in domeny)
        if j != "pl":
            assert not any(re.search(r"poczta|biuro|kontakt", d) for d in domeny), j


@pytest.mark.parametrize("jezyk", NIEPL)
def test_brak_polskich_znakow_i_slow_w_dokumentach_nie_pl(jezyk):
    for typ in TYPY:
        if (jezyk, typ) not in SZABLONY:
            continue
        for i in range(100 if typ != "lista_plac" else 5):
            w = zbuduj_z_kontekstem(SZABLONY[(jezyk, typ)], Generator(jezyk, 8000 + i), random.Random(8000 + i))
            tekst = linearyzuj_z_wartosciami(w.dokument)[0]
            # Wartości (e-maile, URL) i proza: żadnych polskich liter ani słów-przecieków.
            assert not POLSKIE_ZNAKI.search(tekst), (jezyk, typ, POLSKIE_ZNAKI.search(tekst).group())
            zle = POLSKIE_SLOWA.search(tekst)
            assert zle is None, (jezyk, typ, zle.group())


@pytest.mark.parametrize("jezyk", NIEPL)
def test_emaile_firm_i_osob_bez_polskich_czesci(jezyk):
    g = Generator(jezyk, 3)
    for _ in range(100):
        for adres in (g.osoba().email, g.firma().email, g.url()):
            assert not re.search(r"biuro|poczta|umowa", adres), (jezyk, adres)


def test_slug_firmy_nie_tnie_slowa():
    g = Generator("es", 1)
    assert g._slug_firmy("Despacho Gutiérrez Abogados") == "despachogutierrez"
    assert g._slug_firmy("Aurora") == "aurora"
    assert len(g._slug_firmy("Supercalifragilisticoespialidosoextraordinario")) == 24


@pytest.mark.parametrize("jezyk", ["pl", "en", "es", "de", "fr"])
def test_osoby_pelniace_funkcje_pelnoletnie_w_najwczesniejszym_dniu(jezyk):
    for typ in FUNKCJE:
        for i in range(300 // len(FUNKCJE)):
            w = zbuduj_z_kontekstem(SZABLONY[(jezyk, typ)], Generator(jezyk, 9000 + i), random.Random(9000 + i))
            najwczesniej = min(w.kontekst.daty.values())
            for rola, o in w.osoby.items():
                wiek = najwczesniej.year - o.data_ur.year - ((najwczesniej.month, najwczesniej.day) < (o.data_ur.month, o.data_ur.day))
                assert wiek >= 18, (jezyk, typ, rola, o.data_ur, najwczesniej)
