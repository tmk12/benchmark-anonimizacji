import json

import pytest

from pbench.model import Dokument, Element, Obraz, Wartosc, Wykrycie


def _dokument() -> Dokument:
    imie = Wartosc("w1", "OSOBA", "Jan Kowalski", "pl", "tresc", "osoba:1")
    pesel = Wartosc("w2", "PESEL", "44051401359", "pl", "tabela", "osoba:1")
    meta = Wartosc("w3", "ORGANIZACJA", "Alfa sp. z o.o.", "pl", "metadane", "firma:1")
    na_obrazie = Wartosc("w4", "TELEFON", "+48 600 100 200", "pl", "obraz", "osoba:1")
    return Dokument(
        id="d1",
        jezyk="pl",
        typ="umowa",
        format="docx",
        elementy=[
            Element("akapit", ["Strona: ", imie, "."], {"styl": "Normalny"}),
            Element("komorka", [pesel], {"wiersz": 1, "kolumna": 2}),
        ],
        metadane={"tytul": "Umowa", "autor": meta},
        obrazy=[Obraz("o1", b"\x89PNG\r\n", [na_obrazie], [("w4", (1, 2, 30, 40))])],
    )


def test_wartosc_roundtrip_json():
    dok = _dokument()
    tekst = dok.to_json()
    json.loads(tekst)  # poprawny JSON
    assert Dokument.from_json(tekst) == dok


def test_wartosc_odrzuca_nieznana_kategorie():
    with pytest.raises(ValueError):
        Wartosc("w1", "NIE_MA_TAKIEJ", "x", "pl", "tresc", "k")


def test_wartosc_odrzuca_nieznane_miejsce():
    with pytest.raises(ValueError):
        Wartosc("w1", "OSOBA", "x", "pl", "gdzies", "k")


def test_wykrycie_start_mniejszy_od_end():
    assert Wykrycie(0, 3, "OSOBA", 0.9).end == 3
    assert Wykrycie(0, 3, "OSOBA", None).wynik is None
    with pytest.raises(ValueError):
        Wykrycie(3, 3, "OSOBA", None)
    with pytest.raises(ValueError):
        Wykrycie(5, 2, "OSOBA", None)
