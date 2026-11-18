"""Skrót do pisania szablonów: role bloku wynikają z jego gniazd, sekcje domyślnie używają wszystkich bloków."""
from __future__ import annotations

import dataclasses
import re

from ..budowa import Blok, Sekcja, Szablon

_ROLA = re.compile(r"\{([a-z_][a-z0-9_]*)\.")


def blok(tekst: str, wariant: str = "") -> Blok:
    """Blok, którego `wymagane_role` to role użytych gniazd (bez wbudowanej roli `ctx`)."""
    return Blok(tekst, set(_ROLA.findall(tekst)) - {"ctx"}, wariant)


class W(str):
    """Tekst bloku, który wchodzi do dokumentu tylko w wariancie `wariant` szablonu: `W("rejonowy", "…")`."""

    wariant: str

    def __new__(cls, wariant: str, tekst: str) -> "W":
        o = super().__new__(cls, tekst)
        o.wariant = wariant
        return o


def sekcja(nazwa: str, rodzaj: str, *teksty: str, min: int | None = None, max: int | None = None) -> Sekcja:
    """Sekcja z blokami z `teksty`; bez `min`/`max` zawsze wszystkie bloki (dostępne w wariancie), w kolejności."""
    n = len(teksty)
    return Sekcja(nazwa, rodzaj, [blok(t, getattr(t, "wariant", "")) for t in teksty],
                  n if min is None else min, n if max is None else max)


def z_zamianami(szablon: Szablon, zamiany: dict[str, str]) -> Szablon:
    """Kopia szablonu z podmienionymi fragmentami tekstu bloków – wariant warstwy trudnej `SZABLON_ZGODNA_PLEC` (formy zgodne
    z płcią osoby, np. `{autor.rodzaj:Sporządził|Sporządziła}`); trzon używa niezmienionego `SZABLON`. Zamiana, która nie
    trafia w żaden blok, to błąd (szablon się zmienił)."""
    uzyte: set[str] = set()

    def zamien(b: Blok) -> Blok:
        tekst = b.tekst_z_gniazdami
        for stary, nowy in zamiany.items():
            if stary in tekst:
                tekst, _ = tekst.replace(stary, nowy), uzyte.add(stary)
        return blok(tekst, b.wariant)

    sekcje = [Sekcja(s.nazwa, s.rodzaj_elementu, [zamien(b) for b in s.bloki], s.min, s.max) for s in szablon.sekcje]
    if brak := set(zamiany) - uzyte:
        raise ValueError(f"zamiany bez trafienia w szablonie {szablon.jezyk}/{szablon.typ}: {sorted(brak)}")
    return dataclasses.replace(szablon, sekcje=sekcje)
