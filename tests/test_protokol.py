import io

import pytest

from pbench import protokol


def test_protokol_odrzuca_linie_bez_id():
    with pytest.raises(ValueError):
        list(protokol.czytaj_wejscie(io.StringIO('{"jezyk": "pl", "tekst": "x"}\n')))


def test_protokol_odrzuca_niepoprawny_json():
    with pytest.raises(ValueError):
        list(protokol.czytaj_wejscie(io.StringIO("to nie json\n")))


def test_protokol_roundtrip_pomija_puste_linie():
    wyj = io.StringIO()
    protokol.wyslij(wyj, {"id": "a", "jezyk": "pl", "tekst": "zażółć"})
    protokol.wyslij(wyj, {"id": "b", "jezyk": "en", "plik_wej": "i", "plik_wyj": "o"})
    wej = io.StringIO(wyj.getvalue() + "\n")
    assert list(protokol.czytaj_wejscie(wej)) == [
        {"id": "a", "jezyk": "pl", "tekst": "zażółć"},
        {"id": "b", "jezyk": "en", "plik_wej": "i", "plik_wyj": "o"},
    ]
    assert wyj.getvalue().count("\n") == 2


def test_czytaj_wyjscie_pierwsza_linia_gotowy_bez_id():
    wyj = io.StringIO()
    protokol.wyslij(wyj, {"gotowy": True, "wersje": {"pakiet": "1.0"}})
    protokol.wyslij(wyj, {"id": "a", "wykrycia": [[0, 3, "OSOBA", 0.9]]})
    wyj.seek(0)
    odp = list(protokol.czytaj_wyjscie(wyj))
    assert odp[0] == {"gotowy": True, "wersje": {"pakiet": "1.0"}}
    assert odp[1]["id"] == "a"


def test_czytaj_wyjscie_odrzuca_gotowy_poza_pierwsza_linia_i_brak_id():
    with pytest.raises(ValueError):
        list(protokol.czytaj_wyjscie(io.StringIO('{"id": "a", "blad": "x"}\n{"gotowy": true}\n')))
    with pytest.raises(ValueError):
        list(protokol.czytaj_wyjscie(io.StringIO('{"wykrycia": []}\n')))
    with pytest.raises(ValueError):
        list(protokol.czytaj_wyjscie(io.StringIO('{"gotowy": true, "wersje": 5}\n')))
