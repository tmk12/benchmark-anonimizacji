"""Homoglify: litery łacińskie i cyrylicy o (prawie) identycznym kształcie, wmieszane w jeden wyraz.

Przykład: łacińskie „Kowalski” z cyrylicznymi „К” i „о” wygląda tak samo, ale ma inne punkty kodowe. Gold to zapis
dokładnie taki, jaki jest w dokumencie (z wmieszanymi znakami); NFKC ich nie scala. Tablice: pary jednoznaczne wizualnie
(a e o p c x y i oraz wielkie A B C E H I K M O P T X Y) – w obu kierunkach (łacina → cyrylica, cyrylica → łacina).
"""
from __future__ import annotations

import random
import re

LAC_NA_CYR: dict[str, str] = {
    "a": "а", "c": "с", "e": "е", "o": "о", "p": "р", "x": "х", "y": "у", "i": "і",
    "A": "А", "B": "В", "C": "С", "E": "Е", "H": "Н", "I": "І", "K": "К", "M": "М", "O": "О", "P": "Р", "T": "Т",
    "X": "Х", "Y": "У",
}
CYR_NA_LAC: dict[str, str] = {v: k for k, v in LAC_NA_CYR.items()}
_SLOWO = re.compile(r"[^\W\d_]+")


def _jest_cyrylica(c: str) -> bool:
    return "Ѐ" <= c <= "ӿ"


def _jest_lacina(c: str) -> bool:
    return c.isalpha() and "A" <= c.upper() <= "Z" or c.isalpha() and "À" <= c <= "ɏ"


def mieszane(tekst: str) -> bool:
    """Czy któryś wyraz tekstu zawiera litery obu pism (łacina i cyrylica) naraz."""
    return any(any(_jest_cyrylica(c) for c in w) and any(_jest_lacina(c) for c in w) for w in _SLOWO.findall(tekst))


def homoglify(tekst: str, rng: random.Random | None = None, udzial: float = 0.35) -> str:
    """Zamienia część liter (min. jedną w każdym wyrazie, który ma co zamienić) na odpowiedniki z drugiego pisma.

    Kierunek wynika z wyrazu: wyraz łaciński dostaje cyrylicę, cyrylicki – łacinę. `rng` domyślnie wyznacza tekst."""
    rng = rng or random.Random(f"homoglify:{tekst}")

    def zamien(m: re.Match[str]) -> str:
        w = m.group(0)
        tab = CYR_NA_LAC if any(_jest_cyrylica(c) for c in w) else LAC_NA_CYR
        kandydaci = [i for i, c in enumerate(w) if c in tab]
        if not kandydaci:
            return w
        ile = max(1, round(udzial * len(kandydaci)))
        wybrane = set(rng.sample(kandydaci, ile))
        return "".join(tab[c] if i in wybrane else c for i, c in enumerate(w))

    return _SLOWO.sub(zamien, tekst)
