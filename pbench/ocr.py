"""Tesseract: katalog danych językowych i proste wywołanie OCR (kontrola jakości skanów, sędzia plików – zadanie 10).

Dane `tessdata_fast` (Apache-2.0) dla `spa`, `deu`, `fra`, `ukr` leżą w `vendor/tessdata/` razem z `eng`, `pol` i `osd`
skopiowanymi z systemu; katalog poza gitem (`vendor/`). Zmienna `PBENCH_TESSDATA` wskazuje inny katalog.

Język OCR to klucz `KODY`: język dokumentu (`pl`), `uk` (dokument ukraiński: `ukr+eng` – identyfikatory i adresy
e-mail są łacińskie) albo język dokumentu z ukraińską wstawką `+uk` (`pl+uk` → `pol+ukr`).
"""
from __future__ import annotations

import functools
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

#: Język dokumentu (`Dokument.jezyk`) -> kod danych Tesseracta.
class _Kody(dict):
    """Język OCR -> kod Tesseracta; `<język>+uk` to kod języka dokumentu i `ukr` (dokument z cyrylicą ukraińską)."""

    def __missing__(self, klucz: str) -> str:
        czesci = klucz.split("+")
        if len(czesci) == 2 and czesci[1] == "uk" and czesci[0] in self:
            return f"{self[czesci[0]]}+ukr"
        raise KeyError(klucz)


KODY: dict[str, str] = _Kody({"pl": "pol", "en": "eng", "es": "spa", "de": "deu", "fr": "fra", "uk": "ukr+eng"})
KORZEN = Path(__file__).resolve().parent.parent


def tessdata_dir() -> Path:
    """Katalog z plikami `*.traineddata`: `PBENCH_TESSDATA` albo `vendor/tessdata` w repozytorium."""
    env = os.environ.get("PBENCH_TESSDATA")
    return Path(env) if env else KORZEN / "vendor" / "tessdata"


def skrot_tessdata() -> str:
    """Skrót zawartości katalogu `tessdata_dir()` (12 znaków SHA-256 z nazw i sum SHA-256 wszystkich `*.traineddata`): część
    klucza pamięci podręcznej OCR – inne dane Tesseracta (brak pliku, inna wersja) to nowe odczyty, nie stare z pamięci
    (prerejestracja, pkt 7). Sumy liczone raz na stan plików (nazwa, rozmiar, czas modyfikacji)."""
    katalog = tessdata_dir()
    pliki = sorted(katalog.glob("*.traineddata")) if katalog.is_dir() else []
    return _skrot_plikow(tuple((str(p), p.stat().st_size, p.stat().st_mtime_ns) for p in pliki))


@functools.lru_cache(maxsize=8)
def _skrot_plikow(pliki: tuple[tuple[str, int, int], ...]) -> str:
    h = hashlib.sha256()
    for sciezka, *_ in pliki:
        h.update(f"{Path(sciezka).name}:{hashlib.sha256(Path(sciezka).read_bytes()).hexdigest()}\n".encode())
    return h.hexdigest()[:12]


def dostepny(jezyk: str) -> bool:
    """Czy są dane dla języka (`pl`, `en`, …) i program `tesseract`."""
    return all((tessdata_dir() / f"{kod}.traineddata").exists() for kod in KODY[jezyk].split("+")) and _tesseract() is not None


def _tesseract() -> str | None:
    for katalog in os.environ.get("PATH", "").split(os.pathsep):
        sciezka = Path(katalog) / "tesseract"
        if sciezka.exists():
            return str(sciezka)
    return None


def ocr_obraz(obraz: Image.Image, jezyk: str, psm: int = 3) -> str:
    """Tekst rozpoznany na obrazie (`psm` 3 – strona, 7 – jeden wiersz). Bez zapisu do repozytorium."""
    program = _tesseract()
    if program is None:
        raise FileNotFoundError("brak programu tesseract w PATH")
    with tempfile.TemporaryDirectory(prefix="pbench-ocr-") as tmp:
        wejscie = Path(tmp) / "we.png"
        obraz.convert("RGB").save(wejscie)
        wynik = subprocess.run(
            [program, str(wejscie), "stdout", "-l", KODY[jezyk], "--tessdata-dir", str(tessdata_dir()),
             "--psm", str(psm)],
            capture_output=True, check=True, timeout=300, env={**os.environ, "OMP_THREAD_LIMIT": "1"})
    return wynik.stdout.decode("utf-8", errors="replace")
