"""Linearyzacja drzewa dokumentu do tekstu z offsetami wartości wzorcowych (gold).

Kolejność w tekście: nagłówek, treść (akapity, komórki tabel i podpis w kolejności dokumentu), przypisy,
komentarze, zmiany śledzone (tekst usunięty także), pola formularzy, stopka, metadane. Każdy element to jedna
linia (`\\n`); kolejne komórki tej samej tabeli sklejamy: komórki `\\t`, wiersze `\\n`. Metadane to linie
`<etykieta>: <wartość>` w kolejności posortowanych etykiet, na samym końcu (wyjątek: e-mail we wszystkich językach –
nagłówki `from, to, cc, subject` na samym początku, jak w wiadomości). Klucze metadanych w szablonach są
kanoniczne (`author, subject, from, to, cc, case, …`); etykietę w tekście wybiera tabela `ETYKIETY` wg języka dokumentu. Treść obrazów (`Dokument.obrazy`)
**nie** wchodzi do tekstu – to osobny poziom pomiaru.

Gold = każdy fragment `Wartosc` w kolejności linearyzacji. Wartość rozbita na części (komórki, runy) to kilka
obiektów `Wartosc` z tym samym `id` – każda część daje osobny `GoldSpan` z tym samym `wartosc_id`.
"""
from __future__ import annotations

from dataclasses import dataclass

from .model import Dokument, Element, Wartosc

#: Kolejność grup rodzajów elementów w tekście (elementy jednej grupy – w kolejności dokumentu).
GRUPY: tuple[tuple[str, ...], ...] = (
    ("naglowek",), ("akapit", "komorka", "podpis"), ("przypis",), ("komentarz",), ("zmiany",), ("pole",),
    ("stopka",),
)
RODZAJE: frozenset[str] = frozenset(r for g in GRUPY for r in g)


#: Etykiety metadanych w tekście wg języka dokumentu (PL: bez zmian względem pierwotnych kluczy polskich).
ETYKIETY: dict[str, dict[str, str]] = {
    "pl": {"author": "Autor", "subject": "Temat", "from": "Od", "to": "Do", "cc": "DW", "case": "Sprawa",
           "registry_no": "Numer KRS", "title": "Tytul", "entity": "Podmiot"},
    "en": {"author": "Author", "subject": "Subject", "from": "From", "to": "To", "cc": "Cc", "case": "Case",
           "registry_no": "Registry number", "title": "Title", "entity": "Entity"},
    "es": {"author": "Autor", "subject": "Asunto", "from": "De", "to": "Para", "cc": "CC", "case": "Asunto judicial",
           "registry_no": "Número de registro", "title": "Título", "entity": "Entidad"},
    "de": {"author": "Autor", "subject": "Betreff", "from": "Von", "to": "An", "cc": "Cc", "case": "Verfahren",
           "registry_no": "Registernummer", "title": "Titel", "entity": "Unternehmen"},
    "fr": {"author": "Auteur", "subject": "Objet", "from": "De", "to": "À", "cc": "Cc", "case": "Affaire",
           "registry_no": "Numéro de registre", "title": "Titre", "entity": "Entité"},
    "uk": {"author": "Автор", "subject": "Тема", "from": "Від", "to": "Кому", "cc": "Копія", "case": "Справа",
           "registry_no": "Реєстраційний номер", "title": "Назва", "entity": "Суб’єкт"},
}
#: Kolejność nagłówków e-maila (poza PL) umieszczonych na początku dokumentu.
NAGLOWKI_EMAIL = ("from", "to", "cc", "subject")


@dataclass(frozen=True)
class GoldSpan:
    """Zakres [start, end) wartości wzorcowej w tekście zlinearyzowanym."""

    start: int
    end: int
    wartosc_id: str
    kategoria: str
    miejsce: str


def _kolejnosc(d: Dokument) -> list[Element]:
    for e in d.elementy:
        if e.rodzaj not in RODZAJE:
            raise ValueError(f"nieznany rodzaj elementu: {e.rodzaj!r}")
    return [e for grupa in GRUPY for e in d.elementy if e.rodzaj in grupa]


def linearyzuj_z_wartosciami(d: Dokument) -> tuple[str, list[GoldSpan], list[Wartosc]]:
    """Jak `linearyzuj`, ale dodatkowo zwraca obiekty `Wartosc` równolegle do `GoldSpan` (1:1, ta sama kolejność)."""
    kawalki: list[str] = []
    spany: list[GoldSpan] = []
    wartosci: list[Wartosc] = []
    pos = 0

    def dodaj(f: str | Wartosc) -> None:
        nonlocal pos
        if isinstance(f, str):
            kawalki.append(f)
            pos += len(f)
            return
        if f.tekst:
            spany.append(GoldSpan(pos, pos + len(f.tekst), f.id, f.kategoria, f.miejsce))
            wartosci.append(f)
        kawalki.append(f.tekst)
        pos += len(f.tekst)

    def separator(s: str) -> None:
        nonlocal pos
        kawalki.append(s)
        pos += len(s)

    etykiety = ETYKIETY.get(d.jezyk, {})
    poprzedni: Element | None = None

    def metadane(klucze: list[str]) -> None:
        nonlocal poprzedni
        for klucz in klucze:
            if poprzedni is not None:
                separator("\n")
            dodaj(f"{etykiety.get(klucz, klucz)}: ")
            dodaj(d.metadane[klucz])
            poprzedni = Element("metadane", [])

    naglowki_na_poczatku = d.typ == "email"
    if naglowki_na_poczatku:
        metadane([k for k in NAGLOWKI_EMAIL if k in d.metadane])
    for e in _kolejnosc(d):
        if poprzedni is not None:
            sklejone = (e.rodzaj == "komorka" and poprzedni.rodzaj == "komorka"
                        and e.atrybuty.get("tabela") == poprzedni.atrybuty.get("tabela"))
            separator("\t" if sklejone and e.atrybuty.get("wiersz") == poprzedni.atrybuty.get("wiersz") else "\n")
        for f in e.fragmenty:
            dodaj(f)
        poprzedni = e
    metadane(sorted((k for k in d.metadane if not (naglowki_na_poczatku and k in NAGLOWKI_EMAIL)),
                    key=lambda k: (etykiety.get(k, k), k)))
    return "".join(kawalki), spany, wartosci


def linearyzuj(d: Dokument) -> tuple[str, list[GoldSpan]]:
    """Tekst dokumentu i wzorzec: lista `GoldSpan` (rosnąco po `start`, bez nakładania)."""
    tekst, spany, _ = linearyzuj_z_wartosciami(d)
    return tekst, spany
