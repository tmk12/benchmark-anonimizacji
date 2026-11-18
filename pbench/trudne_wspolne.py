"""Wspólne pomocniki generatorów H2 (warstwa trudnych przypadków, punkty 2 i 5 spec §11): kontekst dokumentu, osoby,
wartości gold osoby, inicjały."""
from __future__ import annotations

import dataclasses
import datetime as dt
import random
from typing import Callable

from .budowa import MAPA_KATEGORII, Kontekst
from .dane import Generator
from .dane.wspolne import BazowyGenerator, Osoba
from .model import Dokument, Wartosc
from .sedzia.normalizacja import ile_inicjalow, normalizuj, wzor_inicjalow
from .skladacz import G

#: Klucz `Osoba.ids` wybierany jako „identyfikator osoby” wg języka dokumentu (kraj dokumentu: GB dla EN).
KLUCZ_ID = {"pl": "PESEL", "en": "NINO", "es": "DNI", "de": "STEUER_ID", "fr": "NIR"}
JEZYKI = ("pl", "en", "es", "de", "fr")

#: Pary (imię, nazwisko), których generatory H2 nie zwracają (osoby publiczne, także o nazwiskach będących słowami
#: pospolitymi: Lis, Mróz, Wood, Fox, Koch, Wolf…). Imię jest losowane z generatora, więc blokada obejmuje wszystkie
#: znane pary dla nazwisk z pul H2.
ZABLOKOWANE: frozenset[tuple[str, str]] = frozenset({
    ("william", "smith"), ("will", "smith"), ("matt", "smith"), ("sam", "smith"), ("maggie", "smith"), ("adam", "smith"),
    ("michael", "fox"), ("megan", "fox"), ("james", "fox"), ("edward", "fox"),
    ("tom", "baker"), ("danny", "baker"), ("timothy", "cook"), ("tim", "cook"), ("peter", "cook"), ("alastair", "cook"),
    ("james", "cook"), ("robin", "cook"), ("elijah", "wood"), ("ronnie", "wood"), ("tom", "hunter"), ("larry", "bird"),
    ("brad", "bird"), ("james", "mason"), ("nick", "mason"),
    ("thomas", "müller"), ("gerd", "müller"), ("christa", "wolf"), ("markus", "wolf"), ("robert", "koch"),
    ("roland", "koch"), ("helene", "fischer"), ("joschka", "fischer"), ("klaus", "fuchs"), ("hans-jochen", "vogel"),
    ("michel", "berger"), ("georges", "boulanger"), ("maurice", "chevalier"),
    ("josé", "zapatero"), ("luis", "zapatero"),
    ("tomasz", "lis"), ("remigiusz", "mróz"),
})


def bez_blokady(o: Osoba) -> bool:
    """Prawda, gdy para (imię, nazwisko) nie jest na liście osób publicznych `ZABLOKOWANE`."""
    return (o.imie.lower(), o.nazwisko.lower()) not in ZABLOKOWANE


def nowy_kontekst(jezyk: str, seed: int) -> tuple[BazowyGenerator, Kontekst]:
    """Generator i kontekst dat/kwot dokumentu (jak budowa trzonu: jeden styl zapisu, jeden kraj; EN = Wielka Brytania)."""
    gen = Generator(jezyk, seed)
    gen.styl = {"data": gen.rng.randrange(2), "waluta": gen.rng.randrange(2)}
    if jezyk == "en":
        gen.kraj_dok = "GB"
    ctx = Kontekst(gen, "", gen.kraj_dok or gen.kraje[0])
    return gen, ctx


def osoba(gen: BazowyGenerator, ctx: Kontekst, plec: str | None = None, warunek=None) -> Osoba:
    """Dorosła osoba (>= 18 lat w najwcześniejszej dacie kontekstu) wskazanej płci i spełniająca `warunek(osoba)`.
    Zawsze spoza listy osób publicznych (`ZABLOKOWANE`); w ES z DNI (nie NIE) – identyfikator osoby ma format DNI."""
    gen.max_ur = ctx.najpozniejsze_urodzenie()
    try:
        for _ in range(2000):
            o = gen.osoba()
            if (plec is None or o.plec == plec) and bez_blokady(o) and ("DNI" in o.ids or "NIE" not in o.ids) \
                    and (warunek is None or warunek(o)):
                return o
    finally:
        gen.max_ur = None
    raise RuntimeError("nie udało się wylosować osoby spełniającej warunek")   # pragma: no cover


def zmien(o: Osoba, imie: str | None = None, nazwisko: str | None = None) -> Osoba:
    """Osoba z podmienionym imieniem/nazwiskiem (adres, identyfikatory i data urodzenia bez zmian; e-mail i login
    pochodzą ze starego imienia – dokumenty H2 ich w takim przypadku nie używają)."""
    return dataclasses.replace(o, imie=imie or o.imie, nazwisko=nazwisko or o.nazwisko)


class Os:
    """Osoba dokumentu pod nazwą roli (`rola`): fabryka wartości gold z kluczem `rola.pole` i encją `rola`."""

    def __init__(self, rola: str, o: Osoba, jezyk: str) -> None:
        self.rola, self.o, self.jezyk = rola, o, jezyk

    def g(self, pole: str, tekst: str, kategoria: str = "OSOBA", cechy: tuple[str, ...] = ()) -> G:
        return G(tekst, kategoria, f"{self.rola}.{pole}", self.rola, cechy)

    @property
    def pelne(self) -> G:
        return self.g("pelne", self.o.pelne_imie)

    @property
    def nazwisko(self) -> G:
        return self.g("nazwisko", self.o.nazwisko)

    @property
    def imie(self) -> G:
        return self.g("imie", self.o.imie)

    @property
    def adres(self) -> G:
        return self.g("adres", self.o.adres.linia(), "ADRES")

    @property
    def telefon(self) -> G:
        return self.g("telefon", self.o.telefon, "TELEFON")

    @property
    def email(self) -> G:
        return self.g("email", self.o.email, "EMAIL")

    @property
    def rachunek(self) -> G:
        return self.g("rachunek", self.o.rachunek, "RACHUNEK")

    @property
    def id(self) -> G:
        k = KLUCZ_ID[self.jezyk]
        return self.g(k.lower(), self.o.ids[k], MAPA_KATEGORII[k])

    @property
    def inicjaly_pelne(self) -> str:
        return inicjaly(self.o)


def inicjaly(o: Osoba, kropki: bool = False, male: bool = False) -> str:
    """Inicjały osoby: pierwsza litera imienia i pierwsza litera nazwiska („JK”, z kropkami „J.K.”)."""
    i, n = o.imie[0], o.nazwisko.split()[0][0]
    if kropki:
        return f"{i}.{n}."
    return (i + n).lower() if male else i + n


def data_gold(ctx: Kontekst, nazwa: str, klucz: str = "ctx.data") -> G:
    tekst, kat = ctx.pole(nazwa)
    return G(tekst, kat or "DATA", f"{klucz}.{nazwa}")


def dzien_roboczy(d: dt.date) -> bool:
    return d.weekday() < 5


def rng_h2(seed: int, *czesci: object) -> random.Random:
    return random.Random(":".join(["pbench-h2", str(seed), *map(str, czesci)]))


#: Ile prób (kolejne ziarna) ma generator z inicjałami na dokument z inicjałami jednoznacznymi (`inicjaly_jednoznaczne`).
PROBY_INICJALOW = 50


def inicjaly_jednoznaczne(d: Dokument) -> bool:
    """Czy inicjały dokumentu da się ocenić wzorcem sędziego plikowego (`normalizacja.wzor_inicjalow`, orzeczenie kontrolera do
    H2): wzorzec żadnej wartości INICJALY nie występuje w tekście dokumentu POZA spanami gold (np. „C.” w „k.c.”, „ak” w słowie
    „ak” zdania), w CAŁYM tekście (z gold) trafia nie częściej niż w tekstach wartości gold – ta sama miara co reguła
    niejednoznaczności sędziego (`normalizacja.ile_inicjalow`, `plik.niejednoznaczne`; poprawka H6a I1: honoryfikat spoza gold
    i inicjał gold – FR „M. L.”, ES „D. G.” – trafiają wzorzec „M.L.”/„D.G.” innej wartości) – a inicjały różnych encji nie
    trafiają się nawzajem („K.” osoby b w „J.K.” osoby a, dwie osoby „JK”)."""
    ini: list[Wartosc] = []
    gold: list[str] = []
    linie, pelne = [], []
    for e in d.elementy:
        czesci, caly = [], []
        for f in e.fragmenty:
            if isinstance(f, str):
                czesci.append(f)
                caly.append(f)
            else:
                czesci.append("\n")              # span gold wycięty (granica: znak spoza liter i cyfr)
                caly.append(f.tekst)
                gold.append(normalizuj(f.tekst))
                if f.kategoria == "INICJALY":
                    ini.append(f)
        linie.append("".join(czesci))
        pelne.append("".join(caly))
    if not ini:
        return True
    poza = normalizuj("\n".join(linie))
    pelny = normalizuj("\n".join(pelne))
    wzorce = [(w, wzor_inicjalow(w.tekst)) for w in ini]
    if any(wz.search(poza) or ile_inicjalow(wz, [pelny]) > ile_inicjalow(wz, gold) for _, wz in wzorce):
        return False
    return not any(a.encja != b.encja and wz.search(normalizuj(b.tekst)) for a, wz in wzorce for b in ini)


def z_inicjalami_jednoznacznymi(budowa: Callable[[str, str, int], tuple]) -> Callable[[str, str, int], tuple]:
    """Generator dokumentu z inicjałami: kolejne ziarna (`seed + 7919·próba`; próba 0 = ziarno dokumentu) do pierwszego dokumentu
    z inicjałami jednoznacznymi (`inicjaly_jednoznaczne`)."""
    def generator(jezyk: str, typ: str, seed: int) -> tuple:
        for proba in range(PROBY_INICJALOW):
            wynik = budowa(jezyk, typ, seed + 7919 * proba)
            if inicjaly_jednoznaczne(wynik[0].dokument):
                return wynik
        raise RuntimeError(f"nie udało się złożyć dokumentu z jednoznacznymi inicjałami ({jezyk}, {typ}, {seed})")  # pragma: no cover
    generator.__name__ = budowa.__name__
    generator.__doc__ = budowa.__doc__
    return generator
