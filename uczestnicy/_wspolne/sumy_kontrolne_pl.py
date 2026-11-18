"""Algorytmy sum kontrolnych polskich identyfikatorów (NIP, REGON, numer dowodu) – czysty Python, bez Presidio."""
from __future__ import annotations

import re


def _cyfry(tekst: str) -> str:
    return re.sub(r"\D", "", tekst)


def nip_poprawny(tekst: str) -> bool:
    c = _cyfry(tekst)
    if len(c) != 10:
        return False
    s = sum(int(d) * w for d, w in zip(c[:9], (6, 5, 7, 2, 3, 4, 5, 6, 7))) % 11
    return s != 10 and s == int(c[9])


def regon_poprawny(tekst: str) -> bool:
    c = _cyfry(tekst)
    if len(c) == 9:
        return sum(int(d) * w for d, w in zip(c[:8], (8, 9, 2, 3, 4, 5, 6, 7))) % 11 % 10 == int(c[8])
    if len(c) == 14:
        return (regon_poprawny(c[:9])
                and sum(int(d) * w for d, w in zip(c[:13], (2, 4, 8, 5, 0, 9, 7, 3, 6, 1, 2, 4, 8))) % 11 % 10
                == int(c[13]))
    return False


def dowod_poprawny(tekst: str) -> bool:
    z = re.sub(r"\s", "", tekst).upper()
    if not re.fullmatch(r"[A-Z]{3}\d{6}", z):
        return False
    wartosci = [ord(ch) - 55 for ch in z[:3]] + [int(ch) for ch in z[3:]]       # A=10 … Z=35
    wagi = (7, 3, 1, 0, 7, 3, 1, 7, 3)
    return sum(v * w for v, w in zip(wartosci, wagi)) % 10 == int(z[3])
