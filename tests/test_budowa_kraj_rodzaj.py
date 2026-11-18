"""Testy budowy: gniazdo rodzaju gramatycznego `{rola.rodzaj:m|k[|n]}`, jeden kraj na dokument (EN: GB albo US),
dopasowanie bloków do wariantu/kraju oraz sygnatury i sądy EN wg poziomu."""
from __future__ import annotations

import random
import re

import pytest

from pbench.budowa import Blok, Sekcja, Szablon, zbuduj, zbuduj_z_kontekstem
from pbench.dane import Generator
from pbench.linearyzacja import linearyzuj_z_wartosciami


def _szablon(jezyk: str, tekst: str, role: dict[str, str], warianty=(), bloki=None) -> Szablon:
    bloki = bloki or [Blok(tekst, set(role))]
    return Szablon(jezyk=jezyk, typ="test", role=role, sekcje=[Sekcja("a", "akapit", bloki, len(bloki), len(bloki))],
                   warianty=warianty)


def _buduj(s: Szablon, ziarno: int, wariant=None):
    return zbuduj_z_kontekstem(s, Generator(s.jezyk, ziarno), random.Random(ziarno), wariant)


# ------------------------------------------------------------------------------------------ rodzaj gramatyczny
def test_rodzaj_dwie_formy_wg_plci_osoby():
    s = _szablon("pl", "{p.pelne}: {p.rodzaj:pozwanego|pozwanej}.", {"p": "osoba"})
    plcie = set()
    for i in range(60):
        w = _buduj(s, i)
        plec = w.osoby["p"].plec
        plcie.add(plec)
        tekst, _, wartosci = linearyzuj_z_wartosciami(w.dokument)
        assert tekst.endswith(": pozwanego." if plec == "M" else ": pozwanej."), tekst
        assert [x.kategoria for x in wartosci] == ["OSOBA"]          # forma rodzaju to zwykły tekst, nie gold
    assert plcie == {"M", "K"}


def test_rodzaj_trzy_formy_firma_neutralna():
    s = _szablon("pl", "{o.rodzaj:m|k|n} {f.rodzaj:m|k|n} {f.nazwa}", {"o": "osoba", "f": "firma"})
    for i in range(30):
        w = _buduj(s, i)
        tekst, _, _ = linearyzuj_z_wartosciami(w.dokument)
        assert tekst.split(" ")[:2] == ["m" if w.osoby["o"].plec == "M" else "k", "n"]


def test_rodzaj_dwie_formy_firma_bierze_pierwsza():
    s = _szablon("pl", "{f.rodzaj:powód|powódka} {f.nazwa}", {"f": "firma"})
    assert linearyzuj_z_wartosciami(_buduj(s, 1).dokument)[0].startswith("powód ")


@pytest.mark.parametrize("gniazdo", ["{p.rodzaj:a}", "{p.rodzaj:a|b|c|d}", "{p.rodzaj}", "{x.rodzaj:a|b}",
                                     "{s.rodzaj:a|b}"])
def test_rodzaj_bledne_gniazdo_to_valueerror(gniazdo):
    s = _szablon("pl", gniazdo, {"p": "osoba", "s": "sprawa"})
    with pytest.raises(ValueError):
        _buduj(s, 1)


def test_rodzaj_dziala_w_innych_jezykach():
    s = _szablon("en", "{p.rodzaj:Mr|Ms} {p.nazwisko}", {"p": "osoba"})
    for i in range(20):
        w = _buduj(s, i)
        assert linearyzuj_z_wartosciami(w.dokument)[0].startswith("Mr " if w.osoby["p"].plec == "M" else "Ms ")


# ------------------------------------------------------------------------------------------ jeden kraj na dokument
SZABLON_EN = _szablon("en", "{a.pelne} {a.adres} {a.telefon} {f.nazwa} {f.adres} {f.rachunek} {ctx.glowna} {ctx.dok} "
                      "{b.data_ur} {l.pelne} {l.adres} {p.pelne}",
                      {"a": "osoba", "b": "osoba", "l": "lekarz", "p": "pacjent", "f": "firma"})


def test_en_jeden_kraj_na_dokument_i_oba_kraje_wystepuja():
    kraje = []
    for i in range(200):
        w = _buduj(SZABLON_EN, i)
        k = w.kontekst.kraj
        kraje.append(k)
        assert {o.kraj for o in w.osoby.values()} == {k}
        _, _, wartosci = linearyzuj_z_wartosciami(w.dokument)
        glowna = next(x.tekst for x in wartosci if x.id == "ctx.glowna#1")
        assert glowna.startswith("£" if k == "GB" else "$"), glowna
        adres = next(x.tekst for x in wartosci if x.id == "f.adres#1")
        assert (re.search(r"\b[A-Z]{1,2}\d{1,2}[A-Z]? \d[A-Z]{2}$", adres) is not None) == (k == "GB"), adres
    assert 70 <= kraje.count("GB") <= 130 and set(kraje) == {"GB", "US"}


def test_en_ten_sam_styl_daty_w_dokumencie():
    s = _szablon("en", "{ctx.umowa} {ctx.wezwanie} {ctx.pozew} {ctx.dok} {a.data_ur}", {"a": "osoba"})
    for i in range(80):
        w = _buduj(s, i)
        _, _, wartosci = linearyzuj_z_wartosciami(w.dokument)
        gb = w.kontekst.kraj == "GB"
        formy = {bool(re.fullmatch(r"\d{2}/\d{2}/\d{4}", x.tekst)) for x in wartosci if x.kategoria in ("DATA", "DATA_UR")}
        assert len(formy) == 1, [x.tekst for x in wartosci]
        for x in wartosci:
            assert re.fullmatch(r"\d{1,2} [A-Z][a-z]+ \d{4}|\d{2}/\d{2}/\d{4}" if gb else
                                r"[A-Z][a-z]+ \d{1,2}, \d{4}|\d{2}/\d{2}/\d{4}", x.tekst), (gb, x.tekst)


def test_jednokrajowy_jezyk_nie_wybiera_kraju():
    """PL: wybór kraju nie zużywa losowości (wyniki PL bez zmian względem wersji sprzed zmiany)."""
    s = _szablon("pl", "{a.pelne}", {"a": "osoba"})
    assert _buduj(s, 3).kontekst.kraj == "PL"


# ------------------------------------------------------------------------------------------ bloki wg wariantu i kraju
def test_blok_z_prefiksem_wariantu_i_kraju():
    bloki = [Blok("ZAWSZE", set()), Blok("TYLKO-GB", set(), "gb"), Blok("TYLKO-US", set(), "us"),
             Blok("COUNTY", set(), "gb_county"), Blok("FEDERAL", set(), "us_federal")]
    s = _szablon("en", "", {}, warianty=("gb_county", "gb_high", "us_federal", "us_state"), bloki=bloki)
    zobaczone = set()
    for i in range(120):
        w = _buduj(s, i)
        tekst = linearyzuj_z_wartosciami(w.dokument)[0].split("\n")
        zobaczone.add((w.kontekst.wariant, tuple(tekst)))
        assert w.kontekst.wariant.split("_")[0] == w.kontekst.kraj.lower()
    assert {"gb_county", "gb_high", "us_federal", "us_state"} == {v for v, _ in zobaczone}
    for v, t in zobaczone:
        assert ("TYLKO-GB" in t) == v.startswith("gb") and ("TYLKO-US" in t) == v.startswith("us")
        assert ("COUNTY" in t) == (v == "gb_county") and ("FEDERAL" in t) == (v == "us_federal")


def test_wymuszony_wariant_wymusza_kraj():
    s = _szablon("en", "{ctx.glowna}", {}, warianty=("gb_county", "us_state"))
    for i in range(10):
        assert _buduj(s, i, "us_state").kontekst.kraj == "US"
        assert _buduj(s, i, "gb_county").kontekst.kraj == "GB"


# ------------------------------------------------------------------------------------------ sygnatury i sądy EN
def test_en_sygnatury_wg_rodzaju_i_roku():
    g = Generator("en", 3)
    for _ in range(60):
        assert re.fullmatch(r"Claim No\. [A-Z]\d[A-Z]{2}\d{4}", g.sygnatura("GB", "county", 2024))
        assert re.fullmatch(r"Claim No\. KB-2024-\d{6}", g.sygnatura("GB", "high", 2024))
        assert re.fullmatch(r"Claim No\. QB-2021-\d{6}", g.sygnatura("GB", "high", 2021))
        assert re.fullmatch(r"Case No\. CA-2024-\d{6}", g.sygnatura("GB", "appeal", 2024))
        assert re.fullmatch(r"Case No\. \d:24-cv-\d{5}-[A-Z]{3}", g.sygnatura("US", "federal", 2024))
        assert re.fullmatch(r"Case No\. (?:24-CV-\d{6}|[A-Z]{3}-24-\d{6}|24[A-Z]{2}CV\d{5})", g.sygnatura("US", "state", 2024))
        assert re.fullmatch(r"No\. 24-\d{4,5}", g.sygnatura("US", "appeal", 2024))
    with pytest.raises(ValueError):
        g.sygnatura("GB", "nieznany", 2024)


def test_en_sad_wg_poziomu():
    g = Generator("en", 4)
    for _ in range(60):
        assert g.sad("GB", "county").startswith("County Court at ")
        assert "High Court" in g.sad("GB", "high")
        assert g.sad("GB", "appeal") == "Court of Appeal (Civil Division)"
        assert g.sad("US", "federal").startswith("United States District Court for the ")
        s = g.sad("US", "state")
        assert "Court" in s and not s.startswith("United States")
        assert g.sad("US", "appeal").startswith("United States Court of Appeals for the ")
    with pytest.raises(ValueError):
        g.sad("GB", "nieznany")


def test_en_cytat_to_brytyjskie_albo_amerykanskie_oznaczenie_orzeczenia():
    g = Generator("en", 5)
    for _ in range(40):
        assert re.fullmatch(r"\[(?:19|20)\d{2}\] [\dA-Za-z ()]+", g.sygnatura_cytatu("GB"))
        assert re.fullmatch(r"\d{1,3} (?:U\.S\.|F\.(?:2d|3d|4th)|F\. Supp\. [23]d) \d{1,4} \([A-Za-z0-9. ]*(?:19|20)\d{2}\)",
                            g.sygnatura_cytatu("US")), g.sygnatura_cytatu("US")
