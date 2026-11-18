"""Kontrola treści raportu: źródła rozdziałów (`*.md`) i tekst gotowego PDF.

Zakazy (ścieżki domowe, a gdy jest moduł wewnętrzny – także hosty i historia prac) obowiązują zawsze; liczby w prozie poza wstawkami `{{ … }}` to błąd
(każda liczba z wyników pochodzi z danych); znaczniki `[NIEZWERYFIKOWANE]`/`[HIPOTEZA]` są błędem tylko w trybie publikacji."""
from __future__ import annotations

import re
from pathlib import Path

# (wzorzec, opis) – dopasowanie bez rozróżniania wielkości liter. Reguły ogólne; lista wzorców wewnętrznych (hosty, sesje, historia
# prac) jest w opcjonalnym module `raport.zakazy_wewnetrzne` (poza wersją publiczną).
ZAKAZY = [
    (r"/home/", "ścieżka /home/"),
    (r"/Users/", "ścieżka /Users/"),
]
SESJE: tuple[str, str] | None = None
SESJE_PDF: tuple[str, str] | None = None
try:
    from raport.zakazy_wewnetrzne import SESJE, SESJE_PDF, ZAKAZY_WEWNETRZNE
    ZAKAZY = ZAKAZY + ZAKAZY_WEWNETRZNE
except ImportError:  # wersja publiczna: tylko reguły ogólne
    pass
# Rejestr źródeł używa krótkiej formy „[NIEZWERYFIKOWANE]” (test_zrodla.py): długi wariant z myślnikiem i opisem mógłby w komórce tabeli PDF
# zawinąć się na dwa wiersze i umknąć kontroli tekstu PDF.
# Także pełne warianty statusów z protokołu źródeł, np. „[NIEZWERYFIKOWANE — MCP niedostępny / brak wyniku]”, „[HIPOTEZA — DO SPRAWDZENIA]”.
ZNACZNIKI = (r"\[(?:NIEZWERYFIKOWANE|HIPOTEZA)\b[^\]\n]*\]", "znacznik weryfikacji w wersji do publikacji")

_JINJA = re.compile(r"\{\{.*?\}\}|\{%.*?%\}|\{#.*?#\}", re.S)
_KOMENTARZ = re.compile(r"<!--.*?-->", re.S)
# Wyjątki od reguły liczb: lata, „art./ust./pkt/poz./motyw N” (także zakres „art. 44–49”), numery aktów (2016/679), daty ISO i dotted,
# numeracja listy oraz identyfikatory prawne z rozdziału o przepisach: data aktu lub stosowania słownie z rokiem i „r.”
# („z dnia 26 maja 1982 r.”), sygnatura sprawy TSUE/Sądu („C-413/23 P”), numer CELEX, publikator „Dz.Urz. UE L 119 z 4.5.2016, s. 1”.
_MIESIACE = "stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia"
_WYJATKI = re.compile(
    r"\b(?:art|ust|pkt|lit|motyw(?:u|y|ie|ów)?)\.?\s*\d+[a-z]?[–‑-]\d+[a-z]?"
    r"|\b(?:art|ust|pkt|poz|lit|rozdz|motyw(?:u|y|ie|ów)?|sekcja|tabela|rysunek|wykres)\.?\s*\d+[a-z]?"
    r"|\b\d{4}/\d+\b|\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}\.\d{1,2}\.\d{4}\b|\b20(?:2\d|30)\b|^\s*\d+[.)]\s|https?://\S+"
    rf"|\b\d{{1,2}}\s+(?:{_MIESIACE})\s+\d{{4}}\s*r\."
    r"|\b(?-i:[CT])[-‑]\d+/\d{2}(?:\s+P)?\b|\bCELEX:?\s*\d{5}[A-Z]{1,2}\d{4}\b"
    r"|\bDz\.\s?Urz\.\s?UE\s+L\s+\d+\s+z\s+\d{1,2}\.\d{1,2}\.\d{4}(?:,\s*s(?:tr)?\.\s*\d+)?",
    re.I | re.M)
_LICZBY = [
    (re.compile(r"\d+,\d+"), "liczba z przecinkiem dziesiętnym w prozie"),
    (re.compile(r"\d\s*%"), "procent w prozie"),
    (re.compile(r"(?<![\w.,-])\d{2,}(?![\w.,]*\d)"), "liczba ≥ 10 w prozie"),
]


def _zakazy(tekst: str, miejsce: str, wzorce: list[tuple[str, str]]) -> list[str]:
    bledy = []
    for nr, linia in enumerate(tekst.splitlines(), 1):
        for wzorzec, opis in wzorce:
            if re.search(wzorzec, linia, re.I):
                bledy.append(f"{miejsce}{nr}: {opis}")
    return bledy


def kontroluj_zrodla(katalog: Path, publikacja: bool = False) -> list[str]:
    """Błędy w `katalog/*.md`, każdy jako „plik.md:wiersz: opis”. `publikacja=True` dodaje znaczniki weryfikacji jako błędy."""
    bledy: list[str] = []
    wzorce = ZAKAZY + ([SESJE] if SESJE else []) + ([ZNACZNIKI] if publikacja else [])
    for plik in sorted(Path(katalog).glob("*.md")):
        surowy = plik.read_text(encoding="utf-8")
        # Wstawki zastępujemy spacjami tej samej długości liczby wierszy – numeracja wierszy zostaje.
        bez_jinja = _JINJA.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), surowy)
        bez_kom = _KOMENTARZ.sub(lambda m: re.sub(r"[^\n]", " ", m.group()), bez_jinja)
        bledy += _zakazy(bez_jinja, f"{plik.name}:", wzorce)
        proza = _WYJATKI.sub(lambda m: " " * len(m.group()), bez_kom)
        for nr, linia in enumerate(proza.splitlines(), 1):
            for wzorzec, opis in _LICZBY:
                if wzorzec.search(linia):
                    bledy.append(f"{plik.name}:{nr}: {opis}")
                    break
    return bledy


def znaczniki_zrodel(katalog: Path) -> list[str]:
    """Wiersze ze znacznikami `[NIEZWERYFIKOWANE]`/`[HIPOTEZA]` (ostrzeżenia poza trybem publikacji)."""
    bledy: list[str] = []
    for plik in sorted(Path(katalog).glob("*.md")):
        bledy += _zakazy(plik.read_text(encoding="utf-8"), f"{plik.name}:", [ZNACZNIKI])
    return bledy


def tekst_pdf(pdf: Path) -> str:
    from pdfminer.high_level import extract_text
    return extract_text(str(pdf))


def kontroluj_pdf(pdf: Path, publikacja: bool = False) -> list[str]:
    """Zakazy na tekście wyciągniętym z PDF (łapie wycieki przez dane, nie tylko przez prozę); bez reguły liczb; nazwy sesji – w module wewnętrznym (liczba zwykła w tabelach)."""
    wzorce = ZAKAZY + ([SESJE_PDF] if SESJE_PDF else []) + ([ZNACZNIKI] if publikacja else [])
    return _zakazy(tekst_pdf(pdf), f"{Path(pdf).name}:", wzorce)
