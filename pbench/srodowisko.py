"""Kontrola środowiska oceny przed `pbench-ocen` na poziomie plik (prerejestracja, pkt 7 „Środowisko oceny (zamrożone)”).

Sędzia plikowy czyta OCR wyłącznie z `ocr.tessdata_dir()` (`vendor/tessdata`), a stare formaty konwertuje LibreOffice'em. Brak
pliku `*.traineddata` dałby pusty odczyt zapisany w pamięci podręcznej jako wynik (recenzja H6b, m4), inna wersja danych albo
programów – inne odczyty niż w zamrożonym środowisku. Dlatego przed oceną:

* każdy plik z tabeli sum w `metodyka/prerejestracja.md` (wiersze ``| `xxx.traineddata` | `<sha256>` |``) musi być w katalogu
  danych i mieć tę sumę;
* `tesseract --version` i `soffice --version` muszą podać wersje zapisane w prerejestracji (``**Tesseract X** (leptonica Z``,
  ``**LibreOffice Y**``) – także wersję leptoniki, z którą zbudowano Tesseracta.

Niezgodność = lista problemów; `pbench-ocen --poziom plik` kończy się wtedy kodem 2, nic nie oceniając. Tabela i wersje są
czytane z prerejestracji (jedno źródło – zmiana środowiska to nowa wersja prerejestracji). Klucz pamięci podręcznej OCR zawiera
skrót danych (`ocr.skrot_tessdata`), więc zmiana `tessdata` daje nowe odczyty.

**Odcisk sędziego** (`odcisk_sedziego`) – pole `odcisk_sedziego` każdego rekordu `pbench-ocen`: suma SHA-256 kodu oceny
(`PLIKI_SEDZIEGO`: `pbench/sedzia/*.py`, `pbench/ocr.py`, `pbench/ocen.py`) i reguł wycieku wczytanych z prerejestracji, a na
poziomie plik także skrót `tessdata` i wersje Tesseracta, leptoniki i LibreOffice'a (sędzia tekstowy ich nie używa). Commit
repozytorium (`commit`, z dopiskiem `+zmiany`, gdy pliki sędziego różnią się od commitu) jest informacyjny – porównuje się
pozostałe pola (`klucz_odcisku`). `pbench-agreguj` przerywa, gdy rekordy uczestników jednego poziomu mają różne odciski.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

from . import ocr

PREREJESTRACJA = ocr.KORZEN / "metodyka" / "prerejestracja.md"
_WIERSZ_SUMY = re.compile(r"^\s*\|\s*`([\w.]+\.traineddata)`\s*\|\s*`([0-9a-f]{64})`\s*\|", re.MULTILINE)
_WERSJA_TESSERACTA = re.compile(r"\*\*Tesseract ([\d.]+)\*\*")
_WERSJA_LEPTONIKI = re.compile(r"\*\*Tesseract [\d.]+\*\* \(leptonica ([\d.]+)")
_WERSJA_LIBREOFFICE = re.compile(r"\*\*LibreOffice ([\d.]+)\*\*")


def sumy_tessdata(prerejestracja: Path = PREREJESTRACJA) -> dict[str, str]:
    """Plik `*.traineddata` -> SHA-256 z tabeli prerejestracji."""
    return dict(_WIERSZ_SUMY.findall(Path(prerejestracja).read_text(encoding="utf-8")))


def wersje_oczekiwane(prerejestracja: Path = PREREJESTRACJA) -> dict[str, str]:
    """Wersje Tesseracta, leptoniki i LibreOffice'a zapisane w prerejestracji (`{"tesseract", "leptonica", "libreoffice"}`)."""
    tekst = Path(prerejestracja).read_text(encoding="utf-8")
    wynik = {}
    for klucz, wzor in (("tesseract", _WERSJA_TESSERACTA), ("leptonica", _WERSJA_LEPTONIKI),
                        ("libreoffice", _WERSJA_LIBREOFFICE)):
        if m := wzor.search(tekst):
            wynik[klucz] = m.group(1)
    return wynik


def sprawdz_tessdata(katalog: Path, oczekiwane: dict[str, str]) -> list[str]:
    """Problemy z danymi Tesseracta w `katalog` względem `oczekiwane` (plik -> SHA-256); pusta lista – zgodne."""
    problemy = []
    for nazwa, suma in sorted(oczekiwane.items()):
        p = Path(katalog) / nazwa
        if not p.is_file():
            problemy.append(f"tessdata: brak pliku {nazwa} w {katalog}")
        elif (jest := hashlib.sha256(p.read_bytes()).hexdigest()) != suma:
            problemy.append(f"tessdata: {nazwa} – suma SHA-256 {jest[:12]}… inna niż w prerejestracji ({suma[:12]}…)")
    return problemy


def _wersja(polecenie: list[str], wzor: str) -> str | None:
    if shutil.which(polecenie[0]) is None:
        return None
    try:
        wynik = subprocess.run(polecenie, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    m = re.search(wzor, wynik.stdout + wynik.stderr)
    return m.group(1) if m else None


def wersja_tesseracta() -> str | None:
    return _wersja(["tesseract", "--version"], r"tesseract ([\d.]+)")


def wersja_leptoniki() -> str | None:
    return _wersja(["tesseract", "--version"], r"leptonica-([\d.]+)")


def wersja_libreoffice() -> str | None:
    from .render.doc import _soffice
    try:
        program = _soffice()
    except RuntimeError:
        return None
    return _wersja([program, "--version"], r"LibreOffice ([\d.]+)")


def kontrola_srodowiska(prerejestracja: Path = PREREJESTRACJA) -> list[str]:
    """Wszystkie niezgodności środowiska oceny plikowej z prerejestracją (pusta lista – można oceniać)."""
    oczekiwane = sumy_tessdata(prerejestracja)
    if not oczekiwane:
        return [f"brak tabeli sum tessdata w {prerejestracja}"]
    problemy = sprawdz_tessdata(ocr.tessdata_dir(), oczekiwane)
    wersje = wersje_oczekiwane(prerejestracja)
    for klucz, jest in (("tesseract", wersja_tesseracta()), ("leptonica", wersja_leptoniki()),
                        ("libreoffice", wersja_libreoffice())):
        if klucz not in wersje:
            problemy.append(f"{klucz}: brak wersji w {prerejestracja}")
        elif jest != wersje[klucz]:
            problemy.append(f"{klucz}: wersja {jest or 'nieznana (brak programu)'}, oczekiwana {wersje[klucz]}")
    return problemy


# ----------------------------------------------------------------------------- odcisk sędziego
#: Kod oceny objęty odciskiem (ścieżki względem korzenia repozytorium; wzorce glob).
PLIKI_SEDZIEGO = ("pbench/sedzia/*.py", "pbench/ocr.py", "pbench/ocen.py")


def suma_kodu_sedziego(korzen: Path = ocr.KORZEN) -> str:
    """SHA-256 z nazw i sum SHA-256 plików `PLIKI_SEDZIEGO` (kolejność alfabetyczna ścieżek)."""
    h = hashlib.sha256()
    for p in sorted({p for wzor in PLIKI_SEDZIEGO for p in Path(korzen).glob(wzor)}):
        h.update(f"{p.relative_to(korzen).as_posix()}:{hashlib.sha256(p.read_bytes()).hexdigest()}\n".encode())
    return h.hexdigest()


def suma_regul(reguly: Path) -> str:
    """SHA-256 reguł wycieku tak, jak je wczytuje sędzia (`RegulyWycieku.wczytaj` – brak pliku = domyślne)."""
    from .sedzia.tekst import RegulyWycieku
    d = {k: sorted(v) if isinstance(v, frozenset) else v
         for k, v in dataclasses.asdict(RegulyWycieku.wczytaj(reguly)).items()}
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()


def commit_sedziego(korzen: Path = ocr.KORZEN) -> str | None:
    """Commit repozytorium (informacyjnie); `+zmiany`, gdy pliki sędziego różnią się od niego; None – poza gitem."""
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=korzen, capture_output=True, text=True, timeout=30)
        zmiany = subprocess.run(["git", "status", "--porcelain", "--", *PLIKI_SEDZIEGO], cwd=korzen, capture_output=True,
                                text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if commit.returncode != 0:
        return None
    return commit.stdout.strip() + ("+zmiany" if zmiany.stdout.strip() else "")


def odcisk_sedziego(poziom: str, reguly: Path) -> dict[str, str | None]:
    """Odcisk sędziego i środowiska oceny dla rekordów `pbench-ocen` (docstring modułu)."""
    odcisk: dict[str, str | None] = {"kod": suma_kodu_sedziego(), "reguly": suma_regul(reguly)}
    if poziom == "plik":
        odcisk.update(tessdata=ocr.skrot_tessdata(), tesseract=wersja_tesseracta(), leptonica=wersja_leptoniki(),
                      libreoffice=wersja_libreoffice())
    odcisk["commit"] = commit_sedziego()
    return odcisk


def klucz_odcisku(odcisk: dict) -> tuple:
    """Pola odcisku porównywane między uczestnikami (bez informacyjnego `commit`)."""
    return tuple(sorted((k, v) for k, v in odcisk.items() if k != "commit"))
