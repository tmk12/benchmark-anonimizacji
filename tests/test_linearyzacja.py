"""Testy drzewa dokumentu: linearyzacja, offsety gold, budowa z szablonu."""
from __future__ import annotations

import random

import pytest
from szablon_testowy import szablon_pl

from pbench.budowa import MAPA_KATEGORII, Blok, encja, Sekcja, Szablon, zbuduj
from pbench.dane import Generator
from pbench.linearyzacja import GoldSpan, linearyzuj, linearyzuj_z_wartosciami
from pbench.model import KATEGORIE, Dokument, Element, Obraz, Wartosc


def _zbuduj(szablon: Szablon, ziarno: int = 1) -> Dokument:
    return zbuduj(szablon, Generator(szablon.jezyk, ziarno), random.Random(ziarno))


def _szablon(jezyk: str, role: dict[str, str], rodzaj: str, *bloki: str) -> Szablon:
    return Szablon(jezyk, "t", role, [Sekcja("s", rodzaj, [Blok(b, set(role)) for b in bloki], 1, 1)])


def _w(i: str, tekst: str, miejsce: str = "tresc", kat: str = "OSOBA") -> Wartosc:
    return Wartosc(i, kat, tekst, "pl", miejsce, kat)


# ----------------------------------------------------------------------------- brief
@pytest.mark.parametrize("ziarno", range(8))
def test_offsety_gold_wskazuja_wartosc(ziarno):
    d = _zbuduj(szablon_pl(), ziarno)
    tekst, spany = linearyzuj(d)
    _, spany2, wartosci = linearyzuj_z_wartosciami(d)
    assert spany == spany2 and len(spany) == len(wartosci) > 5
    for s, w in zip(spany, wartosci):
        assert tekst[s.start:s.end] == w.tekst
        assert (s.wartosc_id, s.kategoria, s.miejsce) == (w.id, w.kategoria, w.miejsce)
    assert all(a.end <= b.start for a, b in zip(spany, spany[1:]))  # bez nakładania, rosnąco


def test_wartosc_rozbita_na_komorki_jest_jednym_wpisem_gold():
    d = Dokument("d", "pl", "t", "txt", [
        Element("komorka", [_w("klient.pelne#1", "Jan", "tabela")], {"tabela": 0, "wiersz": 0, "kolumna": 0}),
        Element("komorka", [_w("klient.pelne#1", "Kowalski", "tabela")], {"tabela": 0, "wiersz": 0, "kolumna": 1}),
    ])
    tekst, spany = linearyzuj(d)
    assert tekst == "Jan\tKowalski"
    assert [(s.start, s.end, s.wartosc_id) for s in spany] == [(0, 3, "klient.pelne#1"), (4, 12, "klient.pelne#1")]


def test_rozbicie_na_komorki_z_szablonu():
    d = _zbuduj(_szablon("pl", {"klient": "osoba"}, "komorka", "{klient.pelne/1} | {klient.pelne/2}"))
    tekst, spany = linearyzuj(d)
    assert len(spany) == 2 and spany[0].wartosc_id == spany[1].wartosc_id
    assert "\t" in tekst and {s.kategoria for s in spany} == {"OSOBA"}
    assert all(s.miejsce == "tabela" for s in spany)


def test_cytat_orzeczenia_nie_jest_gold():
    d = _zbuduj(szablon_pl(), 3)
    _, spany = linearyzuj(d)
    ids = {s.wartosc_id.split("#")[0] for s in spany}
    assert not ids & {"cytat.sprawa", "cytat.sygnatura", "sad.nazwa"}
    assert all(not isinstance(f, Wartosc) or not f.id.startswith(("cytat.", "sad.nazwa"))
               for e in d.elementy for f in e.fragmenty)


def test_cytat_i_sad_to_zwykly_tekst():
    d = _zbuduj(_szablon("pl", {"sad": "sad", "cytat": "cytat"}, "akapit",
                         "{cytat.sprawa} {cytat.sygnatura} {sad.nazwa} {sad.sygnatura}"))
    tekst, spany = linearyzuj(d)
    assert [s.wartosc_id.split("#")[0] for s in spany] == ["sad.sygnatura"]
    assert spany[0].kategoria == "SYGNATURA"
    assert len(tekst) > spany[0].end - spany[0].start + 10


def test_linearyzacja_deterministyczna():
    a, b = _zbuduj(szablon_pl(), 5), _zbuduj(szablon_pl(), 5)
    assert a.to_json() == b.to_json()
    assert linearyzuj(a) == linearyzuj(b)
    assert linearyzuj(_zbuduj(szablon_pl(), 6)) != linearyzuj(a)


# ----------------------------------------------------------------------------- kolejność i układ
def test_tresc_obrazow_i_metadane_gold():
    d = Dokument("d", "pl", "t", "txt", [Element("akapit", ["x"])],
                 {"subject": "T", "author": _w("a#1", "Jan Nowak", "metadane")},
                 [Obraz("o1", None, [_w("x#1", "NIEWIDOCZNY", "obraz")])])
    tekst, spany = linearyzuj(d)
    assert tekst == "x\nAutor: Jan Nowak\nTemat: T"
    assert len(spany) == 1 and tekst[spany[0].start:spany[0].end] == "Jan Nowak"
    assert spany[0].miejsce == "metadane"


def test_kolejnosc_grup_i_tabela():
    d = Dokument("d", "pl", "t", "txt", [
        Element("stopka", ["stopka"]), Element("pole", ["pole"]),
        Element("zmiany", ["zm", " usunięty"], {"typ": "del"}), Element("komentarz", ["kom"]),
        Element("przypis", ["przypis"]),
        Element("komorka", ["a"], {"tabela": 0, "wiersz": 0, "kolumna": 0}),
        Element("komorka", ["b"], {"tabela": 0, "wiersz": 0, "kolumna": 1}),
        Element("komorka", ["c"], {"tabela": 0, "wiersz": 1, "kolumna": 0}),
        Element("akapit", ["akapit"]), Element("podpis", ["podpis"]), Element("naglowek", ["nagłówek"]),
    ], {"subject": "T", "author": "A"})
    tekst, _ = linearyzuj(d)
    assert tekst == "nagłówek\na\tb\nc\nakapit\npodpis\nprzypis\nkom\nzm usunięty\npole\nstopka\nAutor: A\nTemat: T"


def test_nieznany_rodzaj_to_blad():
    with pytest.raises(ValueError):
        linearyzuj(Dokument("d", "pl", "t", "txt", [Element("dziwny", ["x"])]))


# ----------------------------------------------------------------------------- budowa
def test_atrybuty_to_czysty_json_i_roundtrip():
    d = _zbuduj(szablon_pl(), 2)
    assert Dokument.from_json(d.to_json()).to_json() == d.to_json()
    rodzaje = {e.rodzaj for e in d.elementy}
    assert rodzaje == {"naglowek", "akapit", "komorka", "przypis", "komentarz", "zmiany", "pole", "stopka", "podpis"}
    kom = next(e for e in d.elementy if e.rodzaj == "komentarz")
    assert kom.atrybuty == {"autor_fragment": 0} and isinstance(kom.fragmenty[0], Wartosc)
    zm = next(e for e in d.elementy if e.rodzaj == "zmiany")
    assert zm.atrybuty == {"autor_fragment": 0, "typ": "del"} and zm.fragmenty[0].kategoria == "OSOBA"
    kom_tab = [e for e in d.elementy if e.rodzaj == "komorka"]
    assert [e.atrybuty for e in kom_tab] == [{"tabela": 0, "wiersz": r, "kolumna": c} for r in (0, 1) for c in (0, 1)]


def test_identyfikatory_wartosci_i_wagi():
    d = _zbuduj(szablon_pl(), 4)
    _, _, wartosci = linearyzuj_z_wartosciami(d)
    for w in wartosci:
        assert "." in w.id and "#" in w.id and w.waga_klucz == w.kategoria and w.jezyk == "pl"
    ids = [w.id for w in wartosci]
    # numer wystąpienia rośnie dla kolejnych użyć tego samego pola
    pelne = [w.id for w in wartosci if w.id.startswith("pelnomocnik.pelne#")]
    assert len(pelne) >= 2 and len(set(pelne)) >= 2


def test_miejsca_zgodne_z_rodzajem_elementu():
    d = _zbuduj(szablon_pl(), 1)
    oczekiwane = {"naglowek": "naglowek", "akapit": "tresc", "komorka": "tabela", "przypis": "przypis",
                  "komentarz": "komentarz", "zmiany": "zmiany", "pole": "pole", "stopka": "stopka", "podpis": "tresc"}
    for e in d.elementy:
        for f in e.fragmenty:
            if isinstance(f, Wartosc):
                assert f.miejsce == oczekiwane[e.rodzaj]
    assert all(w.miejsce == "metadane" for w in d.metadane.values() if isinstance(w, Wartosc))
    assert isinstance(d.metadane["author"], Wartosc) and d.metadane["subject"] == "Pismo"


def test_odmiana_w_gniezdzie():
    from pbench.odmiana_pl import odmien
    d = _zbuduj(_szablon("pl", {"klient": "osoba"}, "akapit", "Przeciwko {klient.pelne:dop}, {klient.pelne}."))
    tekst, spany = linearyzuj(d)
    _, _, w = linearyzuj_z_wartosciami(d)
    assert len(spany) == 2 and w[0].tekst != w[1].tekst
    imie, nazwisko = w[1].tekst.split(" ", 1)
    plec = "K" if w[1].tekst.split()[0] in Generator("pl", 1)._s("imiona_k") else "M"
    assert w[0].tekst == odmien(imie, nazwisko, plec, "dop")
    assert tekst[spany[0].start:spany[0].end] == w[0].tekst


@pytest.mark.parametrize("jezyk,role,blok", [
    ("en", {"k": "osoba"}, "{k.pelne:dop}"),            # odmiana tylko w polskim
    ("pl", {"k": "osoba"}, "{k.nieistnieje}"),          # nieistniejące pole
    ("pl", {"k": "osoba"}, "{k.pesel:xyz}"),            # nieznany przypadek
    ("pl", {"k": "osoba"}, "{k.pesel:dop}"),            # przypadek tylko dla imienia/nazwiska
    ("pl", {"k": "osoba"}, "{inna.pelne}"),             # rola spoza szablonu
    ("pl", {"k": "osoba"}, "{k.pelne/2}"),              # część bez części 1
])
def test_bledne_gniazda(jezyk, role, blok):
    with pytest.raises(ValueError) as e:
        _zbuduj(_szablon(jezyk, role, "akapit", blok))
    assert "{" in str(e.value)  # komunikat zawiera nazwę gniazda


def test_gniazda_wszystkich_jezykow():
    pola = {"pl": "{k.pesel} {k.nip} {k.dowod}", "en": "{k.ssn}", "es": "{k.dni_nie} {k.nuss}",
            "de": "{k.steuer_id} {k.svnr}", "fr": "{k.nir}"}
    for jezyk, blok in pola.items():
        role = {"k": "osoba"}
        if jezyk == "en":  # ssn tylko dla US – ziarno dobieramy tak, by osoba była z USA
            for z in range(50):
                try:
                    d = _zbuduj(_szablon(jezyk, role, "akapit", blok), z)
                    break
                except ValueError:
                    continue
        else:
            d = _zbuduj(_szablon(jezyk, role, "akapit", blok))
        assert all(s.kategoria in KATEGORIE for s in linearyzuj(d)[1])


def test_mapa_kategorii_pokrywa_klucze_generatora():
    for jezyk in ("pl", "en", "es", "de", "fr"):
        g = Generator(jezyk, 9)
        for _ in range(60):
            for klucz in g.osoba().ids:
                assert klucz in MAPA_KATEGORII, (jezyk, klucz)
            for klucz in g.firma().rejestry:
                assert klucz in MAPA_KATEGORII, (jezyk, klucz)
    assert set(MAPA_KATEGORII.values()) <= KATEGORIE
    assert MAPA_KATEGORII["STEUER_ID"] == "NR_PODATKOWY" and MAPA_KATEGORII["NIE"] == "DNI"
    assert MAPA_KATEGORII["SIRET"] == "SIREN" and MAPA_KATEGORII["HRB"] == "NR_REJESTRU"


def test_liczba_blokow_miedzy_min_a_max_i_wlasnosci_rng():
    sz = szablon_pl()
    liczby = {sum(1 for e in _zbuduj(sz, z).elementy if e.rodzaj == "akapit") for z in range(30)}
    assert liczby <= {3, 4} and len(liczby) == 2


def test_bledy_budowy_szablonu():
    with pytest.raises(ValueError):
        _zbuduj(_szablon("pl", {"k": "dziwna"}, "akapit", "{k.pelne}"))
    with pytest.raises(ValueError):
        _zbuduj(_szablon("pl", {"k": "osoba"}, "dziwny", "x"))


def test_cytat_rozlaczny_z_gold():
    sz = Szablon("pl", "t", {"klient": "osoba", "p": "pacjent", "k": "kancelaria", "c": "cytat"}, [
        Sekcja("s", "akapit", [Blok("{klient.pelne:dop} {p.pelne} {k.nazwa} {klient.nazwisko}"),
                               Blok("{c.sprawa}")], 2, 2)])
    for z in range(500):
        d = _zbuduj(sz, z)
        gold = {t.strip(".,").casefold() for e in d.elementy for f in e.fragmenty if isinstance(f, Wartosc)
                for t in f.tekst.split()}
        cytat = [f for e in d.elementy for f in e.fragmenty if isinstance(f, str) and "przeciwko" in f]
        assert len(cytat) == 1
        tokeny = {t.casefold() for t in cytat[0].split()} - {"przeciwko"}
        assert tokeny and not tokeny & gold, (z, tokeny & gold)


def test_encja_to_rola_z_id():
    assert encja("klient.pelne#1") == encja("klient.nazwisko#2") == "klient"
    assert encja("pelnomocnik.pelne#3") == "pelnomocnik"


def test_nieznany_klucz_generatora_ma_jasny_blad(monkeypatch):
    import pbench.budowa as b
    monkeypatch.delitem(b.MAPA_KATEGORII, "PESEL")
    with pytest.raises(RuntimeError, match="PESEL"):
        _zbuduj(_szablon("pl", {"k": "osoba"}, "akapit", "{k.pesel}"))


def test_etykiety_metadanych_wg_jezyka_i_naglowki_emaila_na_poczatku():
    meta = {"subject": "S", "author": "A", "from": "x@example.com", "to": "y@example.com", "cc": "z@example.com"}
    en = Dokument("d", "en", "umowa", "txt", [Element("akapit", ["body"])], dict(meta))
    assert linearyzuj(en)[0] == "body\nAuthor: A\nCc: z@example.com\nFrom: x@example.com\nSubject: S\nTo: y@example.com"
    mail = Dokument("d", "en", "email", "txt", [Element("akapit", ["body"])], dict(meta))
    assert linearyzuj(mail)[0] == ("From: x@example.com\nTo: y@example.com\nCc: z@example.com\nSubject: S\n"
                                   "body\nAuthor: A")
    pl = Dokument("d", "pl", "email", "txt", [Element("akapit", ["body"])], dict(meta))
    assert linearyzuj(pl)[0] == "Od: x@example.com\nDo: y@example.com\nDW: z@example.com\nTemat: S\nbody\nAutor: A"
    pl_umowa = Dokument("d", "pl", "umowa", "txt", [Element("akapit", ["body"])], dict(meta))
    assert linearyzuj(pl_umowa)[0] == "body\nAutor: A\nDW: z@example.com\nDo: y@example.com\nOd: x@example.com\nTemat: S"
    for jezyk, etykieta in (("es", "Asunto: S"), ("de", "Betreff: S"), ("fr", "Objet: S")):
        d = Dokument("d", jezyk, "umowa", "txt", [Element("akapit", ["b"])], {"subject": "S"})
        assert linearyzuj(d)[0] == f"b\n{etykieta}"
