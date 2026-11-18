"""Okna tekstu dla uczestników z limitem długości wejścia modelu (znakowe i tokenowe) oraz scalanie wykryć.

Offsety są zawsze znakowe (indeksy napisu Pythona w oryginalnym tekście), nie bajtowe ani tokenowe. Okna mają zakładkę
>= 10% rozmiaru i są tnione na granicach białych znaków, a wykrycie dotykające sztucznej krawędzi okna (obciętej
wartości) jest odrzucane – kompletną wartość widzi sąsiednie okno (zakładka jest dłuższa od każdej wartości)."""
from __future__ import annotations

import math
import re
from typing import Any, Callable, Sequence

Wykrycie = tuple[int, int, str, float]   # start, koniec (znaki), etykieta, wynik


def okna_znakowe(tekst: str, rozmiar: int, zakladka_ulamek: float = 0.10) -> list[tuple[int, int]]:
    """Okna [start, koniec) po co najwyżej `rozmiar` znaków, zakładka >= `zakladka_ulamek` * rozmiar, cięcia na białych znakach."""
    n = len(tekst)
    if n <= rozmiar:
        return [(0, n)]
    zakladka = max(1, math.ceil(rozmiar * zakladka_ulamek))
    if rozmiar < 4 * zakladka:
        raise ValueError("rozmiar okna za mały w stosunku do zakładki")
    okna: list[tuple[int, int]] = []
    s = 0
    while True:
        e = min(s + rozmiar, n)
        if e < n:                                     # koniec okna: ostatni biały znak w ostatniej ćwiartce okna
            cel = s + rozmiar
            k = cel
            while k > cel - rozmiar // 4 and not tekst[k - 1].isspace():
                k -= 1
            e = k if k > cel - rozmiar // 4 else cel
        okna.append((s, e))
        if e >= n:
            return okna
        nowy = e - zakladka                           # zakładka >= `zakladka`: start po ostatnim białym znaku <= e - zakladka
        k = nowy
        while k > s + 1 and not tekst[k - 1].isspace():
            k -= 1
        s = k if k > s + 1 and tekst[k - 1].isspace() else nowy


def okna_tokenowe(tekst: str, tokenizer: Any, max_tokenow: int, zakladka_ulamek: float = 0.12) -> list[tuple[int, int]]:
    """Okna znakowe zawierające co najwyżej `max_tokenow` tokenów (szybki tokenizer HF z `offset_mapping`).

    `max_tokenow` = limit modelu minus tokeny specjalne i zapas na różnice retokenizacji podłańcucha. Krawędzie okien
    przesuwane są na granice białych znaków (w obrębie zapasu), by nie ciąć słów."""
    n = len(tekst)
    if not tekst.strip():
        return [(0, n)]
    kodowanie = tokenizer(tekst, add_special_tokens=False, return_offsets_mapping=True, truncation=False,
                          verbose=False)
    ofs = [(a, b) for a, b in kodowanie["offset_mapping"] if b > a]
    if len(ofs) <= max_tokenow:
        return [(0, n)]
    zakladka = max(1, math.ceil(max_tokenow * zakladka_ulamek))
    krok = max_tokenow - zakladka
    okna: list[tuple[int, int]] = []
    i = 0
    while True:
        j = min(i + max_tokenow, len(ofs))
        s, e = ofs[i][0], ofs[j - 1][1]
        if i > 0:                                     # cofnij początek na granicę słowa
            while s > 0 and not tekst[s - 1].isspace() and s > ofs[max(i - zakladka // 2, 0)][0]:
                s -= 1
            if s > 0 and not tekst[s - 1].isspace():
                s = ofs[i][0]
        if j < len(ofs):                              # skróć koniec do granicy słowa
            while e > s and e < n and not tekst[e].isspace() and e > ofs[max(j - zakladka // 2, 0)][1]:
                e -= 1
            if e < n and not tekst[e].isspace():
                e = ofs[j - 1][1]
        okna.append((s, e))
        if j >= len(ofs):
            return okna
        i += krok


def okna_indeksowe(n: int, rozmiar: int, zakladka_ulamek: float = 0.125) -> list[tuple[int, int]]:
    """Okna [start, koniec) po indeksach (np. tokenów) dla `n` elementów: co najwyżej `rozmiar`, zakładka dokładnie
    max(2, ceil(`zakladka_ulamek` * rozmiar)) (>= 10% okna), ostatnie okno może być krótsze."""
    if n <= rozmiar:
        return [(0, n)]
    zakladka = max(2, math.ceil(rozmiar * zakladka_ulamek))
    if rozmiar <= 2 * zakladka:
        raise ValueError("rozmiar okna za mały w stosunku do zakładki")
    krok = rozmiar - zakladka
    okna = []
    s = 0
    while True:
        e = min(s + rozmiar, n)
        okna.append((s, e))
        if e >= n:
            return okna
        s += krok


def zakresy_wlasne(okna_idx: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Dla okien z `okna_indeksowe`: zakres indeksów „własny” każdego okna – środek zakładki dzieli sąsiadów, więc element
    bierze wynik z okna, w którym leży dalej od sztucznej krawędzi. Zakresy układają się bez dziur i nakładek."""
    wynik = []
    for k, (a, b) in enumerate(okna_idx):
        od = a if k == 0 else a + (okna_idx[k - 1][1] - a) // 2
        do = b if k == len(okna_idx) - 1 else okna_idx[k + 1][0] + (b - okna_idx[k + 1][0]) // 2
        wynik.append((od, do))
    return wynik


class TokenizerGliner:
    """Licznik tokenów GLiNER dla `okna_tokenowe`: ten sam podział co `WhitespaceTokenSplitter` biblioteki gliner
    (słowo z łącznikami/podkreśleniami albo pojedynczy znak niebiały – interpunkcja to osobny token), zwracany jak
    `offset_mapping` szybkiego tokenizera HF. Limit `max_len` modelu GLiNER dotyczy właśnie tych tokenów, nie znaków."""

    WZORZEC = re.compile(r"\w+(?:[-_]\w+)*|\S")

    def __call__(self, tekst: str, **_: Any) -> dict:
        return {"offset_mapping": [(m.start(), m.end()) for m in self.WZORZEC.finditer(tekst)]}


def scal(n: int, okna: Sequence[tuple[int, int]], wyniki: Sequence[Sequence[Wykrycie]]) -> list[Wykrycie]:
    """Scala wykrycia z okien (offsety względem okna) do offsetów całego tekstu o długości `n`.

    Odrzuca wykrycia dotykające sztucznej krawędzi okna (poza początkiem i końcem tekstu); identyczne (start, koniec,
    etykieta) z różnych okien dają jedno wykrycie z najwyższym wynikiem."""
    najlepsze: dict[tuple[int, int, str], float] = {}
    for (os_, oe), wyk in zip(okna, wyniki):
        for s, e, et, sc in wyk:
            if (s == 0 and os_ > 0) or (os_ + e == oe and oe < n):
                continue
            klucz = (os_ + s, os_ + e, et)
            if sc > najlepsze.get(klucz, -1.0):
                najlepsze[klucz] = sc
    return sorted(((s, e, et, sc) for (s, e, et), sc in najlepsze.items()), key=lambda w: (w[0], w[1], w[2]))


def analizuj_oknami(tekst: str, okna: Sequence[tuple[int, int]],
                    analiza: Callable[[str], Sequence[Wykrycie]]) -> list[Wykrycie]:
    """Uruchamia `analiza(podtekst)` na każdym oknie i scala wyniki (offsety znakowe oryginału)."""
    if len(okna) == 1:
        return sorted(analiza(tekst), key=lambda w: (w[0], w[1], w[2]))
    return scal(len(tekst), okna, [analiza(tekst[s:e]) for s, e in okna])
