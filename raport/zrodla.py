"""Rejestr źródeł prawnych (`raport/zrodla.md`) dla rozdziału „Dlaczego to ważne”: wczytanie tabeli rejestru i oznaczenia aktów cytowanych w tekście.

Oznaczenie aktu to numer aktu UE („2016/679”), sygnatura sprawy TSUE/Sądu („C-413/23”) albo publikator aktu polskiego („Dz.U. 2024 poz. 1564”);
test pilnuje, żeby każde oznaczenie z rozdziału miało wiersz w rejestrze. Tabela zasila też aneks „Źródła prawne” (`tabele.zrodla_prawne`)."""
from __future__ import annotations

import re
from pathlib import Path

REJESTR = Path(__file__).resolve().parent / "zrodla.md"
KOLUMNY = ["Akt / źródło", "Publikator i wersja", "Jednostki redakcyjne", "Stan na", "Źródło", "URL", "Status", "Uwagi"]
# Statusy z protokołu źródeł (`lg-protokol-zrodel`); pełne warianty z dopiskiem po dwukropku lub myślniku.
STATUS = re.compile(r"\[(?:ZWERYFIKOWANE: [^\]]+|NIEZWERYFIKOWANE[^\]]*|HIPOTEZA[^\]]*|NIE DOTYCZY)\]")

_AKT_UE = re.compile(r"(?<![\d/])((?:19|20)\d{2}/\d{2,4})(?![\d/])")
_SPRAWA = re.compile(r"\b([CT])[-‑](\d+/\d{2})\b")
_DZU = re.compile(r"\bDz\.\s?U\.\s+z\s+(\d{4})\s+r\.\s+poz\.\s+(\d+)")


def wczytaj_rejestr(plik: Path = REJESTR) -> list[dict[str, str]]:
    """Wiersze pierwszej tabeli Markdown w pliku (nagłówek = `KOLUMNY`), jako słowniki kolumna → tekst komórki."""
    linie = [l.strip() for l in Path(plik).read_text(encoding="utf-8").splitlines() if l.strip().startswith("|")]
    if not linie:
        return []
    komorki = lambda l: [k.strip() for k in l.strip("|").split("|")]
    naglowek = komorki(linie[0])
    if naglowek != KOLUMNY:
        raise ValueError(f"Nagłówek rejestru {naglowek} ≠ {KOLUMNY}")
    return [dict(zip(naglowek, komorki(l))) for l in linie[1:] if not re.fullmatch(r"\|[\s|:-]+\|", l)]


def oznaczenia(tekst: str) -> set[str]:
    """Oznaczenia aktów w tekście: numery aktów UE, sygnatury spraw (bez dopisku „P”), publikatory „Dz.U. RRRR poz. N” (tylko z „z RRRR r.”)."""
    wynik = {m.group(1) for m in _AKT_UE.finditer(tekst)}
    wynik |= {f"{m.group(1).upper()}-{m.group(2)}" for m in _SPRAWA.finditer(tekst)}
    wynik |= {f"Dz.U. {m.group(1)} poz. {m.group(2)}" for m in _DZU.finditer(tekst)}
    return wynik


def oznaczenia_rejestru(wiersze: list[dict[str, str]]) -> set[str]:
    """Oznaczenia z kolumn „Akt / źródło” i „Publikator i wersja” (publikator „Dz.U. z RRRR r. poz. A, B” rozwinięty na każdą pozycję)."""
    wynik: set[str] = set()
    for w in wiersze:
        tekst = f'{w["Akt / źródło"]} {w["Publikator i wersja"]}'
        wynik |= oznaczenia(tekst)
        # „z 2026 r. poz. 370, 846, 1290” – kolejne pozycje tego samego rocznika
        for m in re.finditer(r"z\s+(\d{4})\s+r\.\s+poz\.\s+([\d,\s]+)", tekst):
            wynik |= {f"Dz.U. {m.group(1)} poz. {p}" for p in re.findall(r"\d+", m.group(2))}
    return wynik
