"""Składacz dokumentów warstwy trudnych przypadków (H2): dokument budowany kodem, nie szablonem.

Przypadki H2 (odmiana nazwisk, zdrobnienia, parafy, liczby słownie, długie dokumenty i listy) wymagają formy wartości,
której silnik szablonów nie umie wytworzyć (liczba mnoga nazwisk, „KOWALSKI Jan”, inicjały z nazwiska osoby, wartość
na zadanej pozycji tekstu płaskiego). `Skladacz` składa więc `Dokument` z akapitów zapisanych jako szablon tekstu z
gniazdami `{nazwa}`; wartość gold to `G` (tekst, kategoria, klucz, encja, cechy), tekst niebędący gold – zwykły napis,
a „pułapka” (słowo pospolite o brzmieniu nazwiska) – `Pulapka`. Identyfikator wartości to `<klucz>#<n>` (n – kolejny
numer użycia klucza w dokumencie), jak w silniku szablonów; `Wartosc.encja` jest ustawiane dla każdej wartości osoby.
Składnik kombinacji identyfikacji pośredniej (H5) to `Skladnik`: wartość gold (`G`) albo zwykły tekst spoza kategorii gold;
oba są zapamiętywane w `Skladacz.skladniki` (do pola manifestu `posrednie`) razem z rdzeniem identyfikującym (`rdzen`).
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from .budowa import MIEJSCE_ELEMENTU, Wynik
from .model import Dokument, Element, Wartosc
from .odmiana_pl import przyimek_przed

_GNIAZDO = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


@dataclass(frozen=True)
class G:
    """Wartość gold do wstawienia w gniazdo: tekst, kategoria, klucz identyfikatora (`rola.pole`), encja i cechy."""

    tekst: str
    kategoria: str
    klucz: str
    encja: str | None = None
    cechy: tuple[str, ...] = ()


@dataclass(frozen=True)
class Pulapka:
    """Słowo pospolite o brzmieniu nazwiska osoby z dokumentu: NIE jest gold (mierzy nadmiarowe maskowanie)."""

    tekst: str
    encja: str | None = None


@dataclass(frozen=True)
class Skladnik:
    """Składnik kombinacji identyfikacji pośredniej (H5): `wartosc` – `G` (składnik będący zwykłą kategorią gold, oznaczony
    jak w trzonie) albo napis (składnik spoza kategorii – funkcja, wiek, numer działki, GPS: zwykły tekst, NIE gold). `rdzen` –
    rdzeń identyfikujący: fragmenty tekstu składnika w kolejności (liczba wieku, numer działki z obrębem, liczby współrzędnych;
    pusta krotka = cały tekst; `pbench.posrednie`)."""

    kombinacja: str
    rola: str
    wartosc: str | G
    rdzen: tuple[str, ...] = ()


@dataclass
class SkladnikWTekscie:
    """Składnik zapamiętany przy składaniu: tekst, miejsce elementu i identyfikator wartości gold (None – spoza gold)."""

    kombinacja: str
    rola: str
    tekst: str
    miejsce: str
    wartosc_id: str | None
    rdzen: tuple[str, ...] = ()


@dataclass
class PulapkaWTekscie:
    """Pułapka zapamiętana przy składaniu: akapit (cały tekst linii), przesunięcie i długość w akapicie."""

    akapit: str
    przesuniecie: int
    tekst: str
    encja: str | None


@dataclass
class Skladacz:
    jezyk: str
    elementy: list[Element] = field(default_factory=list)
    pulapki: list[PulapkaWTekscie] = field(default_factory=list)
    skladniki: list[SkladnikWTekscie] = field(default_factory=list)
    _licznik: Counter = field(default_factory=Counter)
    _dlugosc: int = 0     # długość tekstu płaskiego dotychczasowych elementów (bez separatora po ostatnim)

    # ----- gniazda
    def wartosc(self, g: G, miejsce: str) -> Wartosc:
        self._licznik[g.klucz] += 1
        return Wartosc(f"{g.klucz}#{self._licznik[g.klucz]}", g.kategoria, g.tekst, self.jezyk, miejsce, g.kategoria,
                       None, g.encja, list(g.cechy))

    def fragmenty(self, szablon: str, sloty: dict[str, object], miejsce: str) -> list[str | Wartosc]:
        """Rozwija `{nazwa}`; slot: napis, `G` (gold), `Pulapka` albo `Skladnik`. Nieznane gniazdo / niezamknięte `{`:
        ValueError; składnik spoza gold poza treścią (miejsce inne niż `tresc`) też – jego miejsce nie zmienia się przy przycinaniu."""
        wynik: list[str | Wartosc] = []
        poz = 0
        pulapki: list[tuple[int, Pulapka]] = []
        przesuniecie = 0

        def dodaj(t: str) -> None:
            nonlocal przesuniecie
            if (t.startswith(".") and wynik and isinstance(wynik[-1], Wartosc) and wynik[-1].kategoria == "DATA"
                    and wynik[-1].tekst.endswith("r.")):
                t = t[1:]      # „2024 r.” kończy już zdanie – bez podwójnej kropki (jak w silniku szablonów)
            if t:
                if wynik and isinstance(wynik[-1], str):
                    wynik[-1] += t
                else:
                    wynik.append(t)
                przesuniecie += len(t)

        for m in _GNIAZDO.finditer(szablon):
            dodaj(szablon[poz:m.start()])
            if m.group(1) not in sloty:
                raise ValueError(f"brak slotu {m.group(1)!r} w szablonie {szablon!r}")
            s = sloty[m.group(1)]
            tekst_slotu = s.tekst if isinstance(s, (G, Pulapka)) else (
                (s.wartosc.tekst if isinstance(s.wartosc, G) else s.wartosc) if isinstance(s, Skladnik) else str(s))
            if (nowy := self._przyimek(wynik, tekst_slotu)) is not None:
                przesuniecie += len(nowy) - len(wynik[-1])
                wynik[-1] = nowy
            if isinstance(s, G):
                w = self.wartosc(s, miejsce)
                wynik.append(w)
                przesuniecie += len(w.tekst)
            elif isinstance(s, Pulapka):
                pulapki.append((przesuniecie, s))
                dodaj(s.tekst)
            elif isinstance(s, Skladnik):
                if isinstance(s.wartosc, G):
                    w = self.wartosc(s.wartosc, miejsce)
                    wynik.append(w)
                    przesuniecie += len(w.tekst)
                    self.skladniki.append(SkladnikWTekscie(s.kombinacja, s.rola, w.tekst, miejsce, w.id,
                                                            s.rdzen or (w.tekst,)))
                else:
                    if miejsce != "tresc":
                        raise ValueError(f"składnik spoza gold {s.wartosc!r} poza treścią ({miejsce})")
                    self.skladniki.append(SkladnikWTekscie(s.kombinacja, s.rola, s.wartosc, miejsce, None,
                                                            s.rdzen or (s.wartosc,)))
                    dodaj(s.wartosc)
            else:
                dodaj(str(s))
            poz = m.end()
        dodaj(szablon[poz:])
        if any(c in "{}" for f in wynik if isinstance(f, str) for c in f):
            raise ValueError(f"niezamknięte gniazdo w szablonie {szablon!r}")
        self._ostatnie_pulapki = pulapki
        return wynik

    def _przyimek(self, wynik: list[str | Wartosc], wyraz: str) -> str | None:
        """Polski: tekst poprzedzający gniazdo z „z ”/„w ” na końcu zamienionym na „ze ”/„we ”, gdy wymaga tego wartość
        gniazda (`odmiana_pl.przyimek_pl`); None – bez zmiany."""
        if self.jezyk != "pl" or not wynik or not isinstance(wynik[-1], str):
            return None
        return przyimek_przed(wynik[-1], wyraz)

    def _dodaj(self, rodzaj: str, fragmenty: list[str | Wartosc], atrybuty: dict | None = None) -> Element:
        e = Element(rodzaj, fragmenty, atrybuty or {})
        tekst = "".join(f if isinstance(f, str) else f.tekst for f in fragmenty)
        for przes, p in getattr(self, "_ostatnie_pulapki", []):
            self.pulapki.append(PulapkaWTekscie(tekst, przes, p.tekst, p.encja))
        self._ostatnie_pulapki = []
        self._dlugosc += len(tekst) + (1 if self.elementy else 0)
        self.elementy.append(e)
        return e

    def element(self, rodzaj: str, szablon: str, **sloty: object) -> Element:
        return self._dodaj(rodzaj, self.fragmenty(szablon, sloty, MIEJSCE_ELEMENTU[rodzaj]))

    def akapit(self, szablon: str, **sloty: object) -> Element:
        return self.element("akapit", szablon, **sloty)

    def naglowek(self, szablon: str, **sloty: object) -> Element:
        return self.element("naglowek", szablon, **sloty)

    def stopka(self, szablon: str, **sloty: object) -> Element:
        return self.element("stopka", szablon, **sloty)

    def komorka(self, tabela: int, wiersz: int, kolumna: int, szablon: str, **sloty: object) -> Element:
        return self._dodaj("komorka", self.fragmenty(szablon, sloty, "tabela"),
                           {"tabela": tabela, "wiersz": wiersz, "kolumna": kolumna})

    @property
    def start_nastepnego(self) -> int:
        """Położenie w tekście płaskim, od którego zacznie się następny element (po separatorze `\\n`).
        Dotyczy dokumentów złożonych z jednego nagłówka (pierwszy element) i akapitów (kolejność linearyzacji
        = kolejność dodawania)."""
        return self._dlugosc + (1 if self.elementy else 0)

    def wynik(self, typ: str, kontekst=None) -> Wynik:
        d = Dokument(f"{typ}-h2", self.jezyk, typ, "txt")
        d.elementy = list(self.elementy)
        return Wynik(d, {}, kontekst, {})
