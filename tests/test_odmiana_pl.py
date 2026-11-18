"""Testy odmiany polskich imion i nazwisk."""
from __future__ import annotations

import pytest

from pbench.odmiana_pl import PRZYPADKI, odmiana_trudna, odmien


@pytest.mark.parametrize("imie,nazwisko,plec,przypadek,oczekiwane", [
    ("Jan", "Kowalski", "M", "dop", "Jana Kowalskiego"),
    ("Anna", "Nowak", "K", "dop", "Anny Nowak"),
    ("Piotr", "Nowak", "M", "narz", "Piotrem Nowakiem"),
    ("Maria", "Wiśniewska", "K", "cel", "Marii Wiśniewskiej"),
    ("Jan", "Kowalski", "M", "cel", "Janowi Kowalskiemu"),
    ("Jan", "Kowalski", "M", "narz", "Janem Kowalskim"),
    ("Jan", "Kowalski", "M", "msc", "Janie Kowalskim"),
    ("Maria", "Wiśniewska", "K", "bier", "Marię Wiśniewską"),
    ("Maria", "Wiśniewska", "K", "narz", "Marią Wiśniewską"),
    ("Monika", "Sroka", "K", "cel", "Monice Sroce"),
    ("Paweł", "Wróbel", "M", "dop", "Pawła Wróbla"),
    ("Marek", "Mazurek", "M", "narz", "Markiem Mazurkiem"),
    ("Jerzy", "Dudek", "M", "dop", "Jerzego Dudka"),
    ("Anna", "Nowak", "K", "mian", "Anna Nowak"),
    ("Jan", "Kopeć", "M", "dop", "Jana Kopcia"),
    ("Jan", "Siwiec", "M", "dop", "Jana Siwca"),
    ("Jan", "Malec", "M", "dop", "Jana Malca"),
    ("Jan", "Szczygieł", "M", "dop", "Jana Szczygła"),
    ("Jan", "Gołąb", "M", "dop", "Jana Gołębia"),
    ("Ernest", "Nowak", "M", "msc", "Erneście Nowaku"),
    ("Tomasz", "Kowalenko", "M", "dop", "Tomasza Kowalenko"),  # nazwisko na -o nieodmienne
])
def test_odmiana(imie, nazwisko, plec, przypadek, oczekiwane):
    assert odmien(imie, nazwisko, plec, przypadek) == oczekiwane


def test_nieznany_przypadek():
    with pytest.raises(ValueError):
        odmien("Jan", "Kowalski", "M", "woł")


def test_samo_imie_i_samo_nazwisko():
    assert odmien("Jan", "", "M", "dop") == "Jana"
    assert odmien("", "Kowalska", "K", "dop") == "Kowalskiej"


@pytest.mark.parametrize("imie,nazwisko,plec,przypadek,oczekiwane", [
    ("Ołeksandr", "Szewczenko", "M", "dop", "Ołeksandra Szewczenki"),
    ("Ołeksandr", "Szewczenko", "M", "cel", "Ołeksandrowi Szewczence"),
    ("Ołeksandr", "Szewczenko", "M", "bier", "Ołeksandra Szewczenkę"),
    ("Ołeksandr", "Szewczenko", "M", "narz", "Ołeksandrem Szewczenką"),
    ("Ołeksandr", "Szewczenko", "M", "msc", "Ołeksandrze Szewczence"),
    ("Petro", "Marczenko", "M", "dop", "Petra Marczenki"),
    ("Dmytro", "Bondarenko", "M", "narz", "Dmytrem Bondarenką"),
    ("Wasyl", "Bereżnyj", "M", "dop", "Wasyla Bereżnego"),
    ("Jurij", "Kowalski", "M", "cel", "Jurijowi Kowalskiemu"),
    ("Ołena", "Szewczenko", "K", "dop", "Ołeny Szewczenko"),          # nazwisko żeńskie na -o nieodmienne
    ("Tetiana", "Kowalska", "K", "cel", "Tetianie Kowalskiej"),
    ("Iwan", "Melnyczuk", "M", "dop", "Iwana Melnyczuka"),
])
def test_odmiana_ukrainskich_nazwisk_w_transliteracji_polskiej(imie, nazwisko, plec, przypadek, oczekiwane):
    assert odmien(imie, nazwisko, plec, przypadek, ukrainskie=True) == oczekiwane


def test_tryb_ukrainski_nie_zmienia_domyslnej_odmiany():
    assert odmien("Tomasz", "Kowalenko", "M", "dop") == "Tomasza Kowalenko"            # trzon: nazwiska na -o nieodmienne
    assert odmien("Petro", "Marczenko", "M", "dop") == "Petro Marczenko"


@pytest.mark.parametrize("imie,nazwisko,przypadek,oczekiwane", [
    ("Agnieszka", "Hryniewicz", "dop", "Agnieszki Hryniewicz"),
    ("Agnieszka", "Hryniewicz", "cel", "Agnieszce Hryniewicz"),
    ("Agnieszka", "Hryniewicz", "bier", "Agnieszkę Hryniewicz"),
    ("Agnieszka", "Hryniewicz", "narz", "Agnieszką Hryniewicz"),
    ("Agnieszka", "Hryniewicz", "msc", "Agnieszce Hryniewicz"),
    ("Anna", "Pietruszka", "dop", "Anny Pietruszki"),
    ("Anna", "Gruszka", "bier", "Annę Gruszkę"),
    ("Ewa", "Tyszka", "cel", "Ewie Tyszce"),
    ("Ewa", "Beczka", "dop", "Ewy Beczki"),
    ("Agnieszka", "Grodzka", "dop", "Agnieszki Grodzkiej"),         # -dzka zostaje przymiotnikowe
    ("Agnieszka", "Zawadzka", "bier", "Agnieszkę Zawadzką"),
    ("Agnieszka", "Kowalska", "cel", "Agnieszce Kowalskiej"),
])
def test_odmiana_szka_w_warstwie_trudnej(imie, nazwisko, przypadek, oczekiwane):
    """I4 (H6b-fix1): żeńskie -szka/-czka/-żka odmieniane rzeczownikowo w kontekście warstwy trudnej."""
    with odmiana_trudna():
        assert odmien(imie, nazwisko, "K", przypadek) == oczekiwane


def test_odmiana_szka_trzon_bez_zmian():
    """Tryb domyślny (trzon, opublikowane sumy) – znany błąd „Agnieszkiej” zostaje (`metodyka/znane-ograniczenia.md`);
    kontekst nie przecieka poza blok."""
    assert odmien("Agnieszka", "Nowak", "K", "dop") == "Agnieszkiej Nowak"
    assert odmien("Agnieszka", "Nowak", "K", "bier") == "Agnieszką Nowak"
    # mężczyźni i inne końcówki – w kontekście bez zmian względem trybu domyślnego
    inne = (("Jan", "Gruszka", "M"), ("Zofia", "Wiśniewska", "K"), ("Maja", "Czarna", "K"), ("Ewa", "Łabędzka", "K"))
    domyslne = [odmien(i, n, pl, p) for i, n, pl in inne for p in PRZYPADKI]
    with odmiana_trudna():
        assert odmien("Agnieszka", "Nowak", "K", "dop") == "Agnieszki Nowak"
        assert [odmien(i, n, pl, p) for i, n, pl in inne for p in PRZYPADKI] == domyslne
    assert odmien("Agnieszka", "Nowak", "K", "dop") == "Agnieszkiej Nowak"

