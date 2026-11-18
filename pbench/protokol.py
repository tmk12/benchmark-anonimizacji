"""Protokół uczestnika: JSON-lines na stdin/stdout.

Wejście (linia): {"id","jezyk","tekst"} albo {"id","jezyk","plik_wej","plik_wyj"}.
Wyjście (czyta je `czytaj_wyjscie`): {"id","wykrycia":[[start,end,etykieta,wynik],...]} albo {"id","plik_wyj"}
albo {"id","blad":str}. Pierwsza linia wyjścia uczestnika: {"gotowy":true,"wersje":{pakiet: wersja}}.
"""
from __future__ import annotations

import json
from typing import IO, Any, Iterator


def czytaj_wejscie(stream: IO[str]) -> Iterator[dict[str, Any]]:
    """Czyta linie JSON ze strumienia (puste pomija); linia bez `id` lub nie-JSON → ValueError."""
    for nr, linia in enumerate(stream, 1):
        linia = linia.strip()
        if not linia:
            continue
        try:
            obj = json.loads(linia)
        except json.JSONDecodeError as e:
            raise ValueError(f"linia {nr}: niepoprawny JSON") from e
        if not isinstance(obj, dict) or "id" not in obj:
            raise ValueError(f"linia {nr}: brak pola 'id'")
        yield obj


def parsuj_wyjscie(linia: str, nr: int = 1) -> dict[str, Any]:
    """Jedna linia wyjścia uczestnika: obiekt z `id` albo linia `{"gotowy": true, "wersje": {...}}` (bez `id`).

    Niepoprawny JSON, brak `id` (poza linią `gotowy`) albo `wersje` niebędące słownikiem → ValueError."""
    try:
        obj = json.loads(linia)
    except json.JSONDecodeError as e:
        raise ValueError(f"linia {nr}: niepoprawny JSON") from e
    if not isinstance(obj, dict):
        raise ValueError(f"linia {nr}: oczekiwano obiektu JSON")
    if obj.get("gotowy") is True and "id" not in obj:
        if not isinstance(obj.get("wersje", {}), dict):
            raise ValueError(f"linia {nr}: 'wersje' musi być słownikiem")
        return obj
    if "id" not in obj:
        raise ValueError(f"linia {nr}: brak pola 'id'")
    return obj


def czytaj_wyjscie(stream: IO[str]) -> Iterator[dict[str, Any]]:
    """Czyta wyjście uczestnika (puste linie pomija). Pierwsza linia może być `gotowy` (bez `id`); `gotowy` w dalszej
    części strumienia lub linia bez `id` → ValueError."""
    pierwsza = True
    for nr, linia in enumerate(stream, 1):
        linia = linia.strip()
        if not linia:
            continue
        obj = parsuj_wyjscie(linia, nr)
        if "gotowy" in obj and "id" not in obj and not pierwsza:
            raise ValueError(f"linia {nr}: 'gotowy' dozwolone tylko jako pierwsza linia")
        pierwsza = False
        yield obj


def wyslij(stream: IO[str], obj: dict[str, Any]) -> None:
    """Zapisuje jedną linię JSON i opróżnia bufor (uczestnik czeka na odpowiedź w potoku)."""
    stream.write(json.dumps(obj, ensure_ascii=False) + "\n")
    stream.flush()
