"""Rejestry szablonów warstwy trudnych przypadków (poza `SZABLONY` trzonu, żeby plan trzonu pozostał bez zmian).

* `SZABLONY_UK[typ]` – dokumenty w całości po ukraińsku (`pbench/szablony/uk/<typ>.py`);
* `SZABLONY_WSTAWKI[(język, typ)]` – dokumenty PL/EN/DE z osobami/adresami/identyfikatorami z Ukrainy
  (`pbench/szablony/wstawki/<język>/<typ>.py`), pisane od zera dla warstwy trudnej; gniazda `:t_s1…t_s3` wybierają
  zapis (cyrylica albo transliteracja) wg przypisania budowy przypadku; polskie mają `Szablon.przyimki` („ze”/„we”).
"""
from __future__ import annotations

import dataclasses
import importlib
import pkgutil

from ..budowa import Szablon


def _zbierz(pakiet_nazwa: str) -> dict[str, Szablon]:
    pakiet = importlib.import_module(pakiet_nazwa)
    wynik: dict[str, Szablon] = {}
    for info in pkgutil.iter_modules(pakiet.__path__):
        if info.name.startswith("_"):
            continue
        szablon = importlib.import_module(f"{pakiet_nazwa}.{info.name}").SZABLON
        if szablon.typ != info.name:
            raise ValueError(f"szablon {pakiet_nazwa}.{info.name} ma typ {szablon.typ}")
        wynik[info.name] = szablon
    return wynik


def _wstawki() -> dict[tuple[str, str], Szablon]:
    wynik: dict[tuple[str, str], Szablon] = {}
    for jezyk in ("pl", "en", "de"):
        for typ, szablon in _zbierz(f"{__package__}.wstawki.{jezyk}").items():
            if szablon.jezyk != jezyk:
                raise ValueError(f"wstawka {jezyk}/{typ} ma język {szablon.jezyk}")
            wynik[(jezyk, typ)] = dataclasses.replace(szablon, przyimki=True) if jezyk == "pl" else szablon
    return wynik


SZABLONY_UK: dict[str, Szablon] = _zbierz(f"{__package__}.uk")
SZABLONY_WSTAWKI: dict[tuple[str, str], Szablon] = _wstawki()
