"""Odmiana polskich imion i nazwisk przez przypadki (do gniazd szablonów `{klient.pelne:dop}`).

Zakres: imiona i nazwiska ze słowników generatora (`pbench/dane/slowniki/pl`). Reguły ogólne + niewielka
tablica wyjątków dla alternacji tematu (Paweł, Wróbel, Mróz…). Nazwiska żeńskie na spółgłoskę i nazwiska
na -o/-e są nieodmienne. Funkcja jest deterministyczna i bez efektów ubocznych.

Tryb `ukrainskie=True` (warstwa trudnych przypadków; transliteracja polska osoby z Ukrainy): męskie nazwiska na -o/-ko
odmieniają się jak rzeczowniki żeńskie na -a (Szewczenko → Szewczenki, Szewczence, Szewczenkę, Szewczenką), męskie imiona
na -o jak rzeczowniki męskie (Petro → Petra, Petrowi), nazwiska na -yj jak przymiotniki (Bereżnyj → Bereżnego).
Nazwiska żeńskie na -o pozostają nieodmienne (Jana Szewczenko). Dalsze reguły wyłącznie tego trybu: żeńskie nazwiska
przymiotnikowe (Bereżna, Biła, Podhorna – formy żeńskie męskich na -yj ze słownika generatora – oraz na -owa/-ewa/-ina/-yna:
Kowalowa) odmieniają się jak przymiotniki (Bereżnej, Bereżną); męskie na -eć (Kraweć) tracą -e- (Krawcia, Krawciowi);
żeńskie na -sia/-cia/-zia (Łesia, Orysia) mają dopełniacz, celownik i miejscownik równy tematowi (Łesi). Domyślny tryb
nie zmienia się (także jego znane błędy, np. „Czarniej” zamiast „Czarnej”, „Basii” zamiast „Basi”, „Agnieszkiej” zamiast
„Agnieszki” – zob. `metodyka/znane-ograniczenia.md`: poprawka zmieniłaby opublikowane sumy kontrolne trzonu korpusu).

Kontekst `odmiana_trudna()` (warstwa trudnych przypadków, H6b-fix1; włącza `trudne.generuj_dokument_trudny`): żeńskie imiona
i nazwiska na -szka/-czka/-żka (Agnieszka, Gruszka, Pietruszka, Tyszka) odmieniają się rzeczownikowo (Agnieszki, Agnieszce,
Agnieszkę, Agnieszką), a nie przymiotnikowo jak -ska/-cka/-dzka („Agnieszkiej”, biernik „Agnieszką” – błąd trybu domyślnego).
"""
from __future__ import annotations

import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache

PRZYPADKI: tuple[str, ...] = ("mian", "dop", "cel", "bier", "narz", "msc")

_SAMOGLOSKI = "aąeęioóuy"

# Alternacje tematu (forma podstawowa -> temat przed końcówkami „a/owi/em”).
_TEMATY = {
    "Wróbel": "Wróbl", "Mróz": "Mroz", "Stępień": "Stępni", "Gołąb": "Gołębi", "Kozioł": "Kozł",
    "Kopeć": "Kopci", "Szczygieł": "Szczygł",
    "Sylwester": "Sylwestr", "Kacper": "Kacpr",
}

# Pełne wyjątki (forma podstawowa -> przypadek -> forma).
_WYJATKI = {
    "Paweł": {"dop": "Pawła", "cel": "Pawłowi", "bier": "Pawła", "narz": "Pawłem", "msc": "Pawle"},
}

# Nazwiska żeńskie przymiotnikowe nie kończące się na -ska/-cka/-dzka.
_ZENSKIE_PRZYMIOTNIKOWE = {"Czarna", "Dolna", "Górna", "Wolna", "Konieczna", "Mała"}

#: Warstwa trudna: poprawki odmiany zmieniające tekst (zob. docstring modułu). Domyślnie wyłączone – trzon korpusu ma
#: opublikowane sumy kontrolne i nie może się zmienić.
ODMIANA_TRUDNA: ContextVar[bool] = ContextVar("pbench_odmiana_trudna", default=False)
#: Końcówki rzeczownikowe, które tryb domyślny bierze za przymiotnikowe (-zka jak -dzka): Agnieszka, Gruszka, Beczka.
_RZECZOWNIKOWE_ZKA = ("szka", "czka", "żka")


@contextmanager
def odmiana_trudna() -> Iterator[None]:
    """Kontekst warstwy trudnej: `ODMIANA_TRUDNA` włączone (zob. docstring modułu)."""
    znacznik = ODMIANA_TRUDNA.set(True)
    try:
        yield
    finally:
        ODMIANA_TRUDNA.reset(znacznik)


def _zenskie_a(s: str, przyp: str) -> str:
    """Deklinacja rzeczownikowa na -a (Anna, Monika, Maria, Sroka); także męskie nazwiska na -a."""
    k = s[:-1]
    if przyp == "bier":
        return k + "ę"
    if przyp == "narz":
        return k + "ą"
    ost = k[-1:]
    if k.endswith("j") and len(k) > 1 and k[-2] in _SAMOGLOSKI:  # Maja -> Mai
        return k[:-1] + "i"
    if k.endswith("i") or ost == "j":  # Maria -> Marii, Alicja -> Alicji
        return k + "i"
    if przyp == "dop":
        if ost in "kg":
            return k + "i"
        if ost == "l":
            return k + "i"  # Kamila -> Kamili
        return k + "y"
    # celownik i miejscownik
    if ost == "k":
        return k[:-1] + "ce"
    if ost == "g":
        return k[:-1] + "dze"
    if ost == "t":
        return k[:-1] + "cie"
    if ost == "d":
        return k[:-1] + "dzie"
    if ost == "r":
        return k + "ze"
    if ost == "l":
        return k + "i"
    if ost == "ł":
        return k[:-1] + "le"
    if k.endswith(("sz", "cz", "rz", "dz")) or ost in "żc":
        return k + "y"
    if ost in "ćśźń":
        return k + "i"
    return k + "ie"


def _meskie_msc(t: str) -> str:
    if t.endswith("ch"):
        return t + "u"
    if t.endswith(("sz", "cz", "rz", "dz")) or t[-1:] in "żźśćńjckglu":
        return t + "u"
    if t.endswith("ł"):
        return t[:-1] + "le"
    if t.endswith("r"):
        return t + "ze"
    if t.endswith("st"):
        return t[:-2] + "ście"  # Ernest -> Erneście
    if t.endswith("t"):
        return t[:-1] + "cie"
    if t.endswith("d"):
        return t[:-1] + "dzie"
    if t[-1:] in "nmwszbpf":
        return t + "ie"
    return t + "u"


def _meskie(s: str, przyp: str) -> str:
    if s in _WYJATKI:
        return _WYJATKI[s][przyp]
    t = _TEMATY.get(s)
    if t is None:
        t = s
        if s.endswith("ek") and len(s) > 4:
            t = s[:-2] + "k"
        elif s.endswith("iec") and len(s) > 5:  # Siwiec -> Siwca (ruchome e)
            t = s[:-3] + "c"
        elif s.endswith("ec") and len(s) > 4:  # Malec -> Malca
            t = s[:-2] + "c"
    if przyp in ("dop", "bier"):
        return t + "a"
    if przyp == "cel":
        return t + "owi"
    if przyp == "narz":
        return t + ("iem" if t[-1] in "kg" else "em")
    return _meskie_msc(t)


def _przymiotnikowe(s: str, przyp: str, plec: str) -> str:
    """Nazwiska/imiona na -ski/-cki/-dzki/-y/-i (męskie) oraz -ska/-cka/-dzka (żeńskie)."""
    if plec == "K":
        t = s[:-1]
        return t + ("ą" if przyp in ("bier", "narz") else "iej")
    t = s[:-1]
    miekkie = s.endswith("i")  # -ski: „-skiego”, -y: „-ego”
    if przyp in ("dop", "bier"):
        return t + ("iego" if miekkie else "ego")
    if przyp == "cel":
        return t + ("iemu" if miekkie else "emu")
    return t + ("im" if miekkie else "ym")  # narz, msc


@lru_cache(maxsize=1)
def _zenskie_przymiotnikowe_ukr() -> frozenset[str]:
    """Polskie zapisy żeńskich nazwisk od męskich na -ий ze słownika generatora (Biła, Bereżna, Podhorna)."""
    from .odmiana_uk import _zenskie_od_ij
    from .translit import transliteruj
    return frozenset(transliteruj(n, "polski") for n in _zenskie_od_ij())


def _slowo_ukr_zenskie(s: str, przyp: str, ukr: str) -> str | None:
    """Odmiana żeńskich imion/nazwisk ukraińskich, które wymagają reguł trybu ukraińskiego (None = zwykła ścieżka)."""
    if ukr == "nazwisko" and s.endswith("aja") and len(s) > 4:
        # rosyjska pisownia żeńskich nazwisk przymiotnikowych (Бережная → Bereżnaja): po polsku odmiana przymiotnikowa,
        # Tołstaja – Tołstej – Tołstą (nie „Bereżnai”)
        t = s[:-3]
        return t + ("ą" if przyp in ("bier", "narz") else "iej" if t[-1:] in "kg" else "ej")
    if ukr == "nazwisko" and (s.endswith(("owa", "ewa", "ina", "yna")) or s in _zenskie_przymiotnikowe_ukr()):
        t = s[:-1]
        return t + ("ą" if przyp in ("bier", "narz") else "iej" if t[-1:] in "kg" else "ej")
    if s.endswith(("sia", "cia", "zia")) and przyp in ("dop", "cel", "msc"):
        return s[:-1]
    return None


def _slowo(s: str, plec: str, przyp: str, ukr: str | None = None) -> str:
    """`ukr` – `imie`/`nazwisko` w trybie ukraińskim (zob. docstring modułu), inaczej None."""
    if przyp == "mian" or not s:
        return s
    if ukr and plec == "K":
        forma = _slowo_ukr_zenskie(s, przyp, ukr)
        if forma is not None:
            return forma
    if ukr == "nazwisko" and plec == "M" and s.endswith("eć") and len(s) > 4:    # Kraweć → Krawcia
        t = s[:-2] + "ci"
        return t + {"dop": "a", "bier": "a", "cel": "owi", "narz": "em", "msc": "u"}[przyp]
    if ukr and plec == "M":
        if s.endswith("o") and s not in _WYJATKI:
            return _meskie(s[:-1], przyp) if ukr == "imie" else _zenskie_a(s[:-1] + "a", przyp)
        if ukr == "nazwisko" and s.endswith("yj") and len(s) > 3:
            return _przymiotnikowe(s[:-1], przyp, "M")
    if plec == "K":
        if (s.endswith(("ska", "cka", "dzka", "zka")) or s in _ZENSKIE_PRZYMIOTNIKOWE) \
                and not (s.endswith(_RZECZOWNIKOWE_ZKA) and ODMIANA_TRUDNA.get()):
            return _przymiotnikowe(s, przyp, "K")
        if s.endswith("a"):
            return _zenskie_a(s, przyp)
        return s  # żeńskie na spółgłoskę/-o/-e – nieodmienne
    if s.endswith("a"):  # Kuba, Sikora, Sroka
        return _zenskie_a(s, przyp)
    if s.endswith(("i", "y")):
        return _przymiotnikowe(s, przyp, "M")
    if s[-1] in "oeuóęą" and s not in _WYJATKI:
        return s  # nieodmienne (np. Kowalenko)
    return _meskie(s, przyp)


def _czlony(tekst: str, plec: str, przyp: str, ukr: str | None = None) -> str:
    """Odmienia każdy człon (spacje i łączniki zostają)."""
    wynik: list[str] = []
    for spacja in tekst.split(" "):
        wynik.append("-".join(_slowo(c, plec, przyp, ukr) for c in spacja.split("-")))
    return " ".join(wynik)


def odmien(imie: str, nazwisko: str, plec: str, przypadek: str, ukrainskie: bool = False) -> str:
    """Imię i nazwisko w żądanym przypadku (`mian|dop|cel|bier|narz|msc`); `plec` to „M” lub „K”.

    Puste imię albo nazwisko jest pomijane (pozwala odmieniać samo imię lub samo nazwisko). `ukrainskie` – imię i
    nazwisko osoby z Ukrainy w transliteracji polskiej (zob. docstring modułu).
    """
    if przypadek not in PRZYPADKI:
        raise ValueError(f"nieznany przypadek: {przypadek!r} (dozwolone: {', '.join(PRZYPADKI)})")
    if plec not in ("M", "K"):
        raise ValueError(f"nieznana płeć: {plec!r}")
    czesci = [_czlony(c, plec, przypadek, ("imie", "nazwisko")[i] if ukrainskie else None)
              for i, c in enumerate((imie, nazwisko)) if c]
    return " ".join(czesci)


# ----------------------------------------------------------------------------- przyimki z/ze, w/we (warstwa trudna)
_SAMOGLOSKI_PL = "aąeęioóuy"
#: Przyimek polski przed wartością z gniazda: „z” -> „ze” przed s/z/ś/ź/ż/sz/rz + spółgłoska (ze Zbigniewem, ze Stępniem,
#: ze Szczepańskimi; z Zofią, z Szymonem), „w” -> „we” przed w/f + spółgłoska (we Wrocławiu, we Włoszczowie; w Warszawie).
_PRZYIMKI_PL: dict[str, tuple[tuple[str, ...], str]] = {"z": (("sz", "rz", "s", "z", "ś", "ź", "ż"), "ze"),
                                                        "w": (("w", "f"), "we")}


def przyimek_pl(przyimek: str, wyraz: str) -> str:
    """Forma przyimka `z`/`w` (wielkość pierwszej litery zachowana) przed `wyraz` wg reguły `_PRZYIMKI_PL`; inne – bez zmian."""
    regula = _PRZYIMKI_PL.get(przyimek.lower())
    if regula is None:
        return przyimek
    w = wyraz.lower()
    poczatek = next((p for p in regula[0] if w.startswith(p)), None)
    if poczatek is None or len(w) <= len(poczatek) or not w[len(poczatek)].isalpha() \
            or w[len(poczatek)] in _SAMOGLOSKI_PL:
        return przyimek
    return przyimek[0] + regula[1][1:]


_PRZYIMEK_NA_KONCU = re.compile(r"(?:^|(?<=[\s(„]))([zZwW]) $")


def przyimek_przed(tekst: str, wyraz: str) -> str | None:
    """`tekst` kończący się przyimkiem „z ”/„w ” z formą „ze ”/„we ” wymaganą przez następny `wyraz` (`przyimek_pl`); None –
    bez zmiany. Używają tego budowa warstwy trudnej (`Skladacz`, szablony z `Szablon.przyimki`); trzon – nie."""
    m = _PRZYIMEK_NA_KONCU.search(tekst)
    if m and (forma := przyimek_pl(m.group(1), wyraz)) != m.group(1):
        return tekst[:m.start(1)] + forma + " "
    return None
