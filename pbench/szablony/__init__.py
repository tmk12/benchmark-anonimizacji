"""Rejestr szablonów treści: `SZABLONY[(język, typ)]`.

Moduły `pbench/szablony/<język>/<typ>.py` eksportują `SZABLON: Szablon`; rejestr zbiera je automatycznie (język
bez katalogu jest po prostu pusty). Nazwa modułu musi równać się typowi szablonu, a katalog – jego językowi.
Szablony pisane od zera (bez korpusu treningowego Privatizera), w realiach kraju języka.
"""
from __future__ import annotations

import dataclasses
import importlib
import pkgutil

from ..budowa import Szablon

JEZYKI: tuple[str, ...] = ("pl", "en", "es", "de", "fr")
TYPY: tuple[str, ...] = ("umowa", "pozew", "pelnomocnictwo", "wezwanie", "protokol", "notatka", "email", "faktura",
                         "lista_plac", "prezentacja", "odpis_rejestru", "cv", "wyrok", "med_wypis",
                         "med_zaswiadczenie")
#: Typy tylko w wybranych językach.
TYPY_DODATKOWE: dict[str, tuple[str, ...]] = {"pl": ("med_skierowanie",)}
#: Dokumenty prywatne: umowy i pozew osób fizycznych, we wszystkich językach. Nie wchodzą do `TYPY` – planuje je
#: osobno `pbench.korpus.zaplanuj` (zajmują miejsca zwolnione po dokumentach medycznych).
TYPY_PRYWATNE: tuple[str, ...] = ("umowa_najmu", "umowa_sprzedazy_auta", "pozew_zaplata_osoby")


def _zbierz(trudne: bool = False) -> dict[tuple[str, str], Szablon]:
    """Szablony wg (język, typ); `trudne` – wariant warstwy trudnej (`SZABLON_ZGODNA_PLEC`, gdy moduł go ma; polskie
    z `przyimki`; bez `TYPY_PRYWATNE`)."""
    wynik: dict[tuple[str, str], Szablon] = {}
    for jezyk in JEZYKI:
        try:
            pakiet = importlib.import_module(f"{__name__}.{jezyk}")
        except ModuleNotFoundError as e:
            if e.name != f"{__name__}.{jezyk}":
                raise
            continue
        for info in pkgutil.iter_modules(pakiet.__path__):
            if info.name.startswith("_") or (trudne and info.name in TYPY_PRYWATNE):
                continue        # warstwa trudna: te same przypadki i typy co w trzonie (typy prywatne tylko w trzonie)
            modul = importlib.import_module(f"{pakiet.__name__}.{info.name}")
            szablon = getattr(modul, "SZABLON_ZGODNA_PLEC", modul.SZABLON) if trudne else modul.SZABLON
            if trudne and jezyk == "pl":            # warstwa trudna: „ze”/„we” przed wartością, gdy wymaga tego wymowa
                szablon = dataclasses.replace(szablon, przyimki=True)
            if (szablon.jezyk, szablon.typ) != (jezyk, info.name):
                raise ValueError(f"szablon {pakiet.__name__}.{info.name} ma język/typ {szablon.jezyk}/{szablon.typ}")
            wynik[(jezyk, info.name)] = szablon
    return wynik


SZABLONY: dict[tuple[str, str], Szablon] = _zbierz()
#: Szablony warstwy trudnej (J1, S5): jak `SZABLONY`, ale z wariantem `SZABLON_ZGODNA_PLEC` modułu, gdy go ma (polska lista
#: płac, notatka i prezentacja: formy zgodne z płcią osoby; H6b), a polskie – z `Szablon.przyimki` („ze”/„we”). Trzon używa `SZABLONY` – jego teksty i sumy kontrolne się nie zmieniają.
SZABLONY_TRUDNE: dict[tuple[str, str], Szablon] = _zbierz(trudne=True)
