"""Zapis kontenera OLE/CFB (Compound File Binary) – olefile potrafi tylko czytać.

Własna implementacja (wzór: fikstury testowe Privatizera, przepisane): sektory 512 B (wersja 3), jedna lista sektorów
FAT w nagłówku (do 109 sektorów FAT, ok. 7 MB danych), mini-strumień dla strumieni krótszych niż 4096 B, drzewo
rodzeństwa katalogu zrównoważone. Zapis jest deterministyczny (czasy w katalogu zerowe, brak identyfikatorów CLSID).
"""
from __future__ import annotations

import struct
from pathlib import Path

SECTOR, MINI_SECTOR, CUTOFF = 512, 64, 4096
FREE, END, FATSECT, NOSTREAM = 0xFFFFFFFF, 0xFFFFFFFE, 0xFFFFFFFD, 0xFFFFFFFF
DIR_PER_SECTOR, FAT_PER_SECTOR = SECTOR // 128, SECTOR // 4
MAX_SEKTOROW_FAT = 109

#: Drzewo kontenera: nazwa -> bajty (strumień) albo zagnieżdżony słownik (storage).
Drzewo = dict[str, "bytes | Drzewo"]


def _porzadek(nazwa: str) -> tuple[int, str]:
    """Porządek rodzeństwa w katalogu CFB: najpierw długość nazwy, potem wersja wielkimi literami."""
    return len(nazwa), nazwa.upper()


def _rodzenstwo(wpisy: list[dict], dzieci: list[int]) -> int:
    """Zrównoważone drzewo rodzeństwa; zwraca identyfikator korzenia."""
    dzieci = sorted(dzieci, key=lambda i: _porzadek(wpisy[i]["name"]))

    def buduj(lo: int, hi: int) -> int:
        if lo >= hi:
            return NOSTREAM
        mid = (lo + hi) // 2
        wpisy[dzieci[mid]]["left"] = buduj(lo, mid)
        wpisy[dzieci[mid]]["right"] = buduj(mid + 1, hi)
        return dzieci[mid]

    return buduj(0, len(dzieci))


def _katalog(drzewo: Drzewo) -> list[dict]:
    """Wpisy katalogu: 0 = „Root Entry”, dalej storage'e (typ 1) i strumienie (typ 2)."""
    wpisy: list[dict] = [{"name": "Root Entry", "type": 5, "data": None}]

    def dodaj(wezel: Drzewo, rodzic: int) -> None:
        dzieci = []
        for nazwa, wartosc in wezel.items():
            dzieci.append(idx := len(wpisy))
            if isinstance(wartosc, dict):
                wpisy.append({"name": nazwa, "type": 1, "data": None})
                dodaj(wartosc, idx)
            else:
                wpisy.append({"name": nazwa, "type": 2, "data": wartosc})
        wpisy[rodzic]["child"] = _rodzenstwo(wpisy, dzieci)

    dodaj(drzewo, 0)
    return wpisy


def _wpis(e: dict) -> bytes:
    raw = bytearray(128)
    nazwa = e["name"].encode("utf-16-le") + b"\0\0"
    assert len(nazwa) <= 64, e["name"]
    raw[0:len(nazwa)] = nazwa
    struct.pack_into("<H", raw, 64, len(nazwa))
    raw[66], raw[67] = e["type"], 1  # typ obiektu, kolor „czarny”
    struct.pack_into("<III", raw, 68, e.get("left", NOSTREAM), e.get("right", NOSTREAM), e.get("child", NOSTREAM))
    struct.pack_into("<I", raw, 116, e["start"])
    struct.pack_into("<Q", raw, 120, e["size"])
    return bytes(raw)


def _pusty_wpis() -> bytes:
    raw = bytearray(128)
    struct.pack_into("<III", raw, 68, NOSTREAM, NOSTREAM, NOSTREAM)
    return bytes(raw)


def _sektory(dlugosc: int, jednostka: int = SECTOR) -> int:
    return -(-dlugosc // jednostka)


def zapisz_cfb(plik: Path, drzewo: Drzewo) -> None:
    """Zapisuje kontener OLE z `drzewo` (zob. `Drzewo`)."""
    wpisy = _katalog(drzewo)
    mini = bytearray()
    minifat: list[int] = []
    duze: list[tuple[dict, bytes]] = []
    for e in wpisy:
        dane = e.pop("data")
        if dane is None:                       # Root Entry albo storage
            e["start"], e["size"] = 0, 0
        elif not dane:                         # strumień pusty – bez przydziału sektorów
            e["start"], e["size"] = END, 0
        elif len(dane) < CUTOFF:               # mini-strumień
            pierwszy, ile = len(mini) // MINI_SECTOR, _sektory(len(dane), MINI_SECTOR)
            mini += dane.ljust(ile * MINI_SECTOR, b"\0")
            minifat += [pierwszy + k + 1 for k in range(ile - 1)] + [END]
            e["start"], e["size"] = pierwszy, len(dane)
        else:
            e["start"], e["size"] = 0, len(dane)
            duze.append((e, dane))
    wpisy[0]["size"] = len(mini)

    # Kolejność sektorów: tablice FAT, katalog, mini-FAT, mini-strumień, duże strumienie.
    minifat += [FREE] * (-len(minifat) % FAT_PER_SECTOR)
    liczby = [_sektory(len(wpisy), DIR_PER_SECTOR), _sektory(len(minifat) * 4), _sektory(len(mini))] + [
        _sektory(len(d)) for _e, d in duze]
    razem = sum(liczby)
    n_fat = 1
    while FAT_PER_SECTOR * n_fat < razem + n_fat:
        n_fat += 1
    if n_fat > MAX_SEKTOROW_FAT:
        raise ValueError("kontener za duży na jedną tablicę FAT w nagłówku (ok. 7 MB)")

    fat, starty, nast = [FATSECT] * n_fat, [], n_fat
    for ile in liczby:
        starty.append(nast if ile else END)
        fat += [nast + k + 1 for k in range(ile - 1)] + ([END] if ile else [])
        nast += ile
    fat += [FREE] * (FAT_PER_SECTOR * n_fat - len(fat))

    start_katalogu, start_minifat, start_mini = starty[0], starty[1], starty[2]
    wpisy[0]["start"] = start_mini
    for (e, _dane), start in zip(duze, starty[3:]):
        e["start"] = start

    naglowek = bytearray(SECTOR)
    naglowek[0:8] = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    struct.pack_into("<HHHHH", naglowek, 24, 0x003E, 3, 0xFFFE, 9, 6)
    struct.pack_into("<IIIIIII", naglowek, 40, 0, n_fat, start_katalogu, 0, CUTOFF, start_minifat, liczby[1])
    struct.pack_into("<II", naglowek, 68, END, 0)
    struct.pack_into("<109I", naglowek, 76, *(list(range(n_fat)) + [FREE] * (109 - n_fat)))

    dane_sektorow = [b"".join(_wpis(e) for e in wpisy) + _pusty_wpis() * (-len(wpisy) % DIR_PER_SECTOR),
                     struct.pack(f"<{len(minifat)}I", *minifat), bytes(mini)] + [d for _e, d in duze]
    wyjscie = bytearray(naglowek)
    wyjscie += struct.pack(f"<{len(fat)}I", *fat)
    for dane, ile in zip(dane_sektorow, liczby):
        wyjscie += dane.ljust(ile * SECTOR, b"\0")
    Path(plik).write_bytes(bytes(wyjscie))
