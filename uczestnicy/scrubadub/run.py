"""Uczestnik `scrubadub`: scrubadub 2.0.1 w konfiguracji domyślnej autorów (`Scrubber(locale=...)`), poziom tekst.

Punkt odniesienia „same regexy”: `Scrubber` ładuje detektory z `autoload = True` obsługujące locale dokumentu (wzorce
e-mail, URL, telefon przez `phonenumbers`, karta, dane logowania, Twitter; dla `en_US` także SSN). Detektorów nazwisk i
adresów (spaCy, Stanford, TextBlob, sklearn) autorzy nie ładują domyślnie – zostają wyłączone. Bez okien (wzorce działają
na całym tekście) i bez progu (filth nie ma pewności – wynik 1.0). Konfiguracja i uzasadnienie: KONFIG.md."""
from __future__ import annotations

import sys
from importlib import metadata
from pathlib import Path

KATALOG = Path(__file__).resolve().parent
sys.path.insert(0, str(KATALOG.parent / "_wspolne"))

import protokol_uczestnika as pu  # noqa: E402

# Locale dokumentu wg języka (format scrubadub `xx_YY`); `en` → `en_US` – domyślne locale autorów (`Scrubber()`).
LOCALE = {"pl": "pl_PL", "en": "en_US", "es": "es_ES", "de": "de_DE", "fr": "fr_FR"}


def main() -> None:
    import scrubadub

    scrubbery = {j: scrubadub.Scrubber(locale=loc) for j, loc in LOCALE.items()}

    def analizuj(tekst: str, jezyk: str) -> list:
        wyniki = []
        for filth in scrubbery[jezyk].iter_filth(tekst):
            # MergedFilth (nakładające się wykrycia różnych detektorów) – każde z osobna, z własnym zakresem
            for f in getattr(filth, "filths", None) or [filth]:
                if f.end > f.beg:
                    wyniki.append((f.beg, f.end, f.type, 1.0))
        return sorted(set(wyniki))

    wersje = {"scrubadub": metadata.version("scrubadub"), "phonenumbers": metadata.version("phonenumbers"),
              **{f"detektory:{j}": ",".join(sorted(s._detectors)) for j, s in scrubbery.items()}}
    pu.petla(wersje, analizuj)


if __name__ == "__main__":
    main()
