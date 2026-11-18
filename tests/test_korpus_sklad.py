"""Testy składu korpusu: ICD i leki poza gold (tekst zostaje w dokumencie), dokumenty prywatne (3 typy × 5 języków),
rozkład 67 medycznych / 67 prywatnych na 1000, nadmiarowe maskowanie diagnozy i leku w sędziach (T5/P5)."""
from __future__ import annotations

import json
import random
import re
from collections import Counter
from pathlib import Path

import pytest
from stdnum import iban as _iban
from stdnum.es import dni as _dni, nie as _nie
from stdnum.fr import nir as _nir
from stdnum.pl import pesel as _pesel

from pbench import korpus
from pbench.budowa import zbuduj_z_kontekstem
from pbench.dane import Generator
from pbench.linearyzacja import GoldSpan, linearyzuj_z_wartosciami
from pbench.model import Wartosc, Wykrycie
from pbench.sedzia.normalizacja import normalizuj  # noqa: F401  (import sprawdza, że sędzia się ładuje)
from pbench.sedzia.plik import Czesc, Wydobycie, nadmiarowe
from pbench.sedzia.tekst import RegulyWycieku, ocen_tekst
from pbench.szablony import JEZYKI, SZABLONY, TYPY_PRYWATNE

SLOT = re.compile(r"\{([a-z_][a-z0-9_]*)\.([a-z0-9_]+)(?:/\d+)?(?::[a-z]+|:[^{}|]*\|[^{}]*)?\}")
MED = ("med_wypis", "med_zaswiadczenie", "med_skierowanie")
PARY = [(j, t) for j in JEZYKI for t in TYPY_PRYWATNE]


def _buduj(j: str, typ: str, ziarno: int, wariant: str | None = None):
    s = SZABLONY[(j, typ)]
    w = zbuduj_z_kontekstem(s, Generator(j, ziarno), random.Random(ziarno), wariant)
    return w, linearyzuj_z_wartosciami(w.dokument)


# ----------------------------------------------------------------------------- ICD i leki poza gold
def _med_pozycje():
    return [p for p in korpus.zaplanuj(korpus.ZIARNO) if p.typ in MED]


def test_zdrowie_z_diagnoz_i_lekow_nie_ma_w_gold_a_tekst_jest_w_dokumencie():
    plan = _med_pozycje()
    assert len(plan) == 67
    for p in plan:
        seed = korpus.ziarno_dokumentu(korpus.ZIARNO, p.id)
        w = zbuduj_z_kontekstem(SZABLONY[(p.jezyk, p.typ)], Generator(p.jezyk, seed),
                                random.Random(f"pbench-korpus:{seed}"))
        tekst, spany, wartosci = linearyzuj_z_wartosciami(w.dokument)
        assert not any(x.kategoria == "ZDROWIE" for x in wartosci) and not any(s.kategoria == "ZDROWIE" for s in spany), p.id
        assert not any(".diagnoza" in x.id or ".lek" in x.id for x in wartosci), p.id
        pac = next(e for r, e in w.encje.items() if e.rodzaj == "pacjent")
        assert any(d in tekst for d in pac.diagnozy) and any(m in tekst for m in pac.leki), p.id
        assert any(x.kategoria == "OSOBA" and x.id.startswith(f"{next(r for r, e in w.encje.items() if e.rodzaj == 'pacjent')}.")
                   for x in wartosci), p.id         # pacjent i jego dane zostają w gold


def test_manifest_i_txt_med_wypis_bez_zdrowia_w_gold(tmp_path):
    p = next(p for p in _med_pozycje() if p.format == "docx" and p.typ == "med_wypis")
    wpis = korpus.generuj_dokument(p, korpus.ZIARNO, "test", tmp_path)
    assert wpis["gold_tekst"] and not any(g["kategoria"] == "ZDROWIE" for g in wpis["gold_tekst"] + wpis["gold_plik"])
    seed = korpus.ziarno_dokumentu(korpus.ZIARNO, p.id)
    w = zbuduj_z_kontekstem(SZABLONY[(p.jezyk, p.typ)], Generator(p.jezyk, seed), random.Random(f"pbench-korpus:{seed}"))
    txt = (tmp_path / wpis["plik_txt"]).read_text(encoding="utf-8")
    pac = next(e for e in w.encje.values() if e.rodzaj == "pacjent")
    assert any(d in txt for d in pac.diagnozy) and any(m in txt for m in pac.leki)


def test_sedzia_tekstowy_zamaskowany_lek_to_nadmiarowe_maskowanie_bez_wycieku():
    t = "Pacjent Jan Kowalski leczony: Amlodypina 5 mg, rozpoznanie I10 Nadciśnienie tętnicze."
    i = t.index("Jan Kowalski")
    gold = [GoldSpan(i, i + len("Jan Kowalski"), "pacjent.pelne#1", "OSOBA", "tresc")]    # lek i ICD nie są gold
    R = RegulyWycieku()
    bez = ocen_tekst(gold, [Wykrycie(i, i + len("Jan Kowalski"), "OSOBA")], t, R)
    assert bez.wycieki == [] and bez.fp_znaki == 0
    j = t.index("Amlodypina 5 mg")
    k = t.index("I10 Nadciśnienie tętnicze")
    z = ocen_tekst(gold, [Wykrycie(i, i + len("Jan Kowalski"), "OSOBA"), Wykrycie(j, j + len("Amlodypina 5 mg"), "ZDROWIE"),
                          Wykrycie(k, k + len("I10 Nadciśnienie tętnicze"), "ZDROWIE")], t, R)
    assert z.wycieki == []                                      # brak wycieku
    assert z.fp_znaki >= len("Amlodypina5mg") + len("I10Nadciśnienietętnicze") and z.fp_spany == 2


def test_sedzia_plikowy_zamaskowany_lek_to_nadmiarowe_maskowanie_bez_wycieku():
    orig = Wydobycie(rodzaj="docx", czesci=[Czesc("word/document.xml", ["Jan Kowalski przyjmuje Amlodypina 5 mg."], tresc=True)])
    maska = Wydobycie(rodzaj="docx", czesci=[Czesc("word/document.xml", ["[OSOBA_1] przyjmuje [LEK_1] ."], tresc=True)])
    gold = [Wartosc("pacjent.pelne#1", "OSOBA", "Jan Kowalski", "pl", "tresc", "OSOBA")]
    n = nadmiarowe(orig, maska, gold)
    assert n["znaki"] > 0 and n["znaki"] <= n["poza_gold"]
    tylko_gold = Wydobycie(rodzaj="docx", czesci=[Czesc("word/document.xml", ["[OSOBA_1] przyjmuje Amlodypina 5 mg."], tresc=True)])
    assert nadmiarowe(orig, tylko_gold, gold)["znaki"] == 0


# ----------------------------------------------------------------------------- rozkład typów
def test_rozklad_typow_trzonu_67_medycznych_67_prywatnych_na_1000():
    plan = korpus.zaplanuj(korpus.ZIARNO)
    licz = Counter(p.typ for p in plan)
    assert len(plan) == 1000 and korpus.ZIARNO == 20261103
    assert sum(licz[t] for t in MED) == 67 and sum(licz[t] for t in TYPY_PRYWATNE) == 67
    assert [licz[t] for t in MED] == [27, 28, 12]
    assert sorted(licz[t] for t in TYPY_PRYWATNE) == [22, 22, 23]


def test_ziarno_warstwy_trudnej():
    from pbench import trudne
    assert trudne.ZIARNO_TRUDNE == 20261104


# ----------------------------------------------------------------------------- nowe szablony prywatne
@pytest.mark.parametrize("jezyk,typ", PARY)
def test_szablon_prywatny_gniazda_role_i_liczba_blokow(jezyk, typ):
    s = SZABLONY[(jezyk, typ)]
    assert (s.jezyk, s.typ) == (jezyk, typ) and s.dorosli
    bloki = [b for sek in s.sekcje for b in sek.bloki]
    assert len(bloki) >= (12 if jezyk == "pl" else 8)
    uzyte = set()
    for b in bloki:
        r = {m.group(1) for m in SLOT.finditer(b.tekst_z_gniazdami)} - {"ctx"}
        assert r == b.wymagane_role and r <= set(s.role)
        uzyte |= r
    uzyte |= {m.group(1) for v in s.metadane.values() for m in SLOT.finditer(v)} - {"ctx"}
    assert uzyte == set(s.role)
    for wariant in s.warianty or (None,):
        for ziarno in range(5):
            _buduj(jezyk, typ, ziarno, wariant)


@pytest.mark.parametrize("jezyk,typ", PARY)
def test_dokument_prywatny_gesty_w_dane_osobowe_strony_to_osoby_fizyczne(jezyk, typ):
    for ziarno in range(6):
        w, (tekst, spany, wartosci) = _buduj(jezyk, typ, 100 + ziarno)
        kat = Counter(x.kategoria for x in wartosci)
        assert len(wartosci) >= 24, (jezyk, typ, len(wartosci))
        assert kat["OSOBA"] >= 6 and kat["ADRES"] >= 2 and kat["TELEFON"] >= 2 and kat["RACHUNEK"] >= 1, (jezyk, typ, kat)
        assert not any(x.kategoria in ("ORGANIZACJA", "ZDROWIE") for x in wartosci)      # strony to osoby fizyczne
        assert all(o.data_ur < min(w.kontekst.daty.values()) for o in w.osoby.values())
        if typ == "umowa_sprzedazy_auta":
            assert kat["NR_REJESTRACYJNY"] >= 2, (jezyk, kat)
            assert not re.search(r"\bVIN\b", tekst)
        assert not [s for s in spany if s.kategoria == "ZDROWIE"]


def test_identyfikatory_w_dokumentach_prywatnych_maja_poprawne_sumy_kontrolne():
    for ziarno in range(4):
        for typ in TYPY_PRYWATNE:
            _, (_, _, w) = _buduj("pl", typ, 300 + ziarno)
            assert all(_pesel.is_valid(x.tekst) for x in w if x.kategoria == "PESEL")
            assert all(_iban.is_valid(x.tekst) for x in w if x.kategoria == "RACHUNEK")
            _, (_, _, w) = _buduj("es", typ, 300 + ziarno)
            assert all((_nie if x.tekst[0] in "XYZ" else _dni).is_valid(x.tekst) for x in w if x.kategoria == "DNI")
            assert all(_iban.is_valid(x.tekst) for x in w if x.kategoria == "RACHUNEK")
            _, (_, _, w) = _buduj("fr", typ, 300 + ziarno)
            assert all(_nir.is_valid(x.tekst.replace(" ", "")) for x in w if x.kategoria == "NIR")
            assert all(_iban.is_valid(x.tekst) for x in w if x.kategoria == "RACHUNEK")
            for j in ("de",):
                _, (_, _, w) = _buduj(j, typ, 300 + ziarno)
                assert all(_iban.is_valid(x.tekst) for x in w if x.kategoria == "RACHUNEK")


@pytest.mark.parametrize("jezyk,typ", PARY)
def test_dokumenty_prywatne_renderuja_sie_w_formatach_dokumentowych(jezyk, typ, tmp_path):
    from pbench.korpus import Pozycja
    for fmt in ("docx", "pdf", "skan", "doc"):
        if fmt == "doc" and jezyk != "pl":
            continue
        p = Pozycja(f"{jezyk}-{typ}-9999", jezyk, typ, fmt)
        wpis = korpus.generuj_dokument(p, korpus.ZIARNO, "dev", tmp_path)
        assert (tmp_path / wpis["plik"]).stat().st_size > 0 and wpis["gold_tekst" if fmt != "skan" else "gold_tekst"]
        assert not wpis["ostrzezenia"] or fmt == "doc", wpis["ostrzezenia"]


# ----------------------------------------------------------------------------- SVNR: Bereichsnummern wg VKVV
BEREICHE_VKVV = ({f"{n:02d}" for n in (2, 3, 4, 8, 9, *range(10, 22), 23, 24, 25, 26, 28, 29)}
                 | {f"{n:02d}" for n in (42, 43, 44, 48, 49, *range(50, 62), 63, 64, 65, 66, 68, 69)}
                 | {"38", "39", "80", "81", "82", "89"})


def test_svnr_ma_obszar_z_tabeli_vkvv():
    import datetime as dt
    from pbench.dane import de
    assert set(de._BEREICHE) == BEREICHE_VKVV and "40" not in de._BEREICHE
    rng = random.Random(5)
    widziane = set()
    for i in range(3000):
        n = de.svnr(rng, dt.date(1950 + i % 50, 1 + i % 12, 1 + i % 28), "M" if i % 2 else "K", "Müller")
        assert re.fullmatch(r"\d{2}\d{6}[A-Z]\d{2}\d", n) and n[:2] in BEREICHE_VKVV, n
        widziane.add(n[:2])
    assert widziane == BEREICHE_VKVV
    g = Generator("de", 11)
    for _ in range(200):
        assert g.osoba().ids["SVNR"][:2] in BEREICHE_VKVV
