"""Generatory wartości syntetycznych dla PL/EN/ES/DE/FR.

Użycie: `g = Generator("pl", 42); osoba = g.osoba(); firma = g.firma()`.
"""
from __future__ import annotations

from .wspolne import Adres, BazowyGenerator, Firma, Osoba, zgodna_plec

JEZYKI = ("pl", "en", "es", "de", "fr")
#: Języki tylko warstwy trudnych przypadków (poza planem trzonu korpusu).
JEZYKI_TRUDNE = ("uk",)


def Generator(jezyk: str, ziarno: int = 0) -> BazowyGenerator:
    """Fabryka generatora dla języka dokumentu (`pl|en|es|de|fr`, w warstwie trudnej też `uk`); wynik deterministyczny dla `ziarno`."""
    if jezyk == "pl":
        from .pl import GeneratorPL as klasa
    elif jezyk == "en":
        from .en import GeneratorEN as klasa
    elif jezyk == "es":
        from .es import GeneratorES as klasa
    elif jezyk == "de":
        from .de import GeneratorDE as klasa
    elif jezyk == "fr":
        from .fr import GeneratorFR as klasa
    elif jezyk == "uk":
        from .uk import GeneratorUK as klasa
    else:
        raise ValueError(f"nieznany język: {jezyk!r} (dozwolone: {', '.join(JEZYKI + JEZYKI_TRUDNE)})")
    return klasa(jezyk, ziarno)


__all__ = ["Generator", "JEZYKI", "JEZYKI_TRUDNE", "Adres", "Firma", "Osoba", "zgodna_plec"]
