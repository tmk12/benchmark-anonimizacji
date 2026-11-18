"""Utrudnienia formatu DOCX i przycinanie `Dokument` do tego, co dane utrudnienie faktycznie obejmuje.

Szablony zawsze mogą produkować komentarze, zmiany śledzone, przypisy, pola formularzy, tabele i metadane
z danymi osobowymi. Zadanie korpusu wybiera podzbiór utrudnień dla pliku; `przytnij` usuwa (albo spłaszcza)
elementy, których wybrane utrudnienia nie obejmują, ZANIM dokument trafi do renderera i do linearyzacji –
dzięki temu plik i tekst poziomu 1 pochodzą z tego samego `Dokumentu`.
"""
from __future__ import annotations

import dataclasses

from .model import Dokument, Element, Wartosc

#: Utrudnienia zaimplementowane w rendererze DOCX (`pbench.render.docx`).
UTRUDNIENIA_DOCX: frozenset[str] = frozenset({
    "papier_firmowy", "tabele", "przypisy", "komentarze", "zmiany", "metadane", "pola", "rozbite_runy", "podpis",
})
#: Utrudnienia zaimplementowane w rendererze PDF z tekstem (`pbench.render.pdf`). Brak `zmiany` (PDF nie ma zmian
#: śledzonych) i `rozbite_runy` (to cecha OOXML); komentarze to adnotacje `/Text`, pola to widgety AcroForm.
UTRUDNIENIA_PDF: frozenset[str] = frozenset({
    "papier_firmowy", "tabele", "przypisy", "komentarze", "metadane", "pola", "podpis",
})
#: Utrudnienia z briefu, których świadomie nie realizujemy (brak źródła syntetycznych twarzy z pewną licencją –
#: `pbench/dane/slowniki/ZRODLA.md`). Renderer je przyjmuje i pomija; nie wchodzą do `UTRUDNIENIA_DOCX`.
UTRUDNIENIA_POMINIETE: frozenset[str] = frozenset({"zdjecie"})

#: Autor metadanych, gdy plik nie ma utrudnienia `metadane` (neutralny, bez danych osobowych).
NEUTRALNY_AUTOR: dict[str, str] = {"pl": "Użytkownik", "en": "User", "es": "Usuario", "de": "Benutzer",
                                   "fr": "Utilisateur", "uk": "Користувач"}
#: Nagłówki e-maila renderowane w treści (zob. `linearyzacja.NAGLOWKI_EMAIL`).
_NAGLOWKI_EMAIL = ("from", "to", "cc")


def _na_tresc(f: str | Wartosc) -> str | Wartosc:
    return f if isinstance(f, str) else dataclasses.replace(f, miejsce="tresc")


def _akapit(fragmenty: list[str | Wartosc]) -> Element:
    return Element("akapit", [_na_tresc(f) for f in fragmenty])


def _tekst(e: Element) -> str:
    return "".join(f if isinstance(f, str) else f.tekst for f in e.fragmenty)


def splaszcz_tabele(elementy: list[Element]) -> list[Element]:
    """Komórki -> akapity „nagłówek kolumny: wartość”; nagłówki bez wartości wzorcowych wchodzą w etykiety."""
    naglowki: dict[tuple[int, int], str] = {}
    rzedy: dict[int, set[int]] = {}
    for e in elementy:
        if e.rodzaj == "komorka":
            a = e.atrybuty
            rzedy.setdefault(a["tabela"], set()).add(a["wiersz"])
            if a["wiersz"] == 0 and all(isinstance(f, str) for f in e.fragmenty):
                naglowki[(a["tabela"], a["kolumna"])] = _tekst(e)
    wynik: list[Element] = []
    for e in elementy:
        if e.rodzaj != "komorka":
            wynik.append(e)
            continue
        a = e.atrybuty
        wielowierszowa = len(rzedy[a["tabela"]]) > 1
        etykieta = naglowki.get((a["tabela"], a["kolumna"]))
        if wielowierszowa and a["wiersz"] == 0 and etykieta is not None:
            continue
        pre = [f"{etykieta}: "] if wielowierszowa and etykieta else []
        wynik.append(_akapit(pre + list(e.fragmenty)))
    return wynik


def przytnij(d: Dokument, utrudnienia: set[str]) -> Dokument:
    """Nowy `Dokument` bez elementów, których `utrudnienia` nie obejmują (deterministycznie, `d` bez zmian).

    Brak `komentarze`/`zmiany`/`przypisy` -> elementy usunięte; brak `pola` -> akapit „etykieta: wartość”;
    brak `tabele` -> komórki jako akapity; brak `papier_firmowy` -> wartości nagłówka i stopki mają miejsce „tresc”;
    brak `metadane` -> autor neutralny, pozostałe metadane z danymi usunięte (nagłówki e-maila przechodzą do treści).
    """
    n = Dokument.from_dict(d.to_dict())
    elementy: list[Element] = []
    for e in n.elementy:
        if e.rodzaj == "komentarz" and "komentarze" not in utrudnienia:
            continue
        if e.rodzaj == "zmiany" and "zmiany" not in utrudnienia:
            continue
        if e.rodzaj == "przypis" and "przypisy" not in utrudnienia:
            continue
        if e.rodzaj == "pole" and "pola" not in utrudnienia:
            etykieta = e.atrybuty.get("etykieta")
            elementy.append(_akapit(([f"{etykieta}: "] if etykieta else []) + list(e.fragmenty)))
            continue
        if e.rodzaj in ("naglowek", "stopka") and "papier_firmowy" not in utrudnienia:
            elementy.append(Element(e.rodzaj, [_na_tresc(f) for f in e.fragmenty], e.atrybuty))
            continue
        elementy.append(e)
    if "tabele" not in utrudnienia:
        elementy = splaszcz_tabele(elementy)
    n.elementy = elementy
    if "metadane" not in utrudnienia:
        meta: dict[str, str | Wartosc] = {}
        for k, v in n.metadane.items():
            if not isinstance(v, Wartosc):
                meta[k] = v
            elif k == "author":
                meta[k] = NEUTRALNY_AUTOR.get(n.jezyk, "User")
            elif n.typ == "email" and k in _NAGLOWKI_EMAIL:
                meta[k] = dataclasses.replace(v, miejsce="tresc")
        n.metadane = meta
    return n


def przytnij_pdf(d: Dokument, utrudnienia: set[str]) -> Dokument:
    """`przytnij` dla formatu PDF: waliduje zbiór (tylko `UTRUDNIENIA_PDF` i pomijane) i usuwa `zmiany`.

    PDF nie ma zmian śledzonych, więc `zmiany` nie wchodzi do `UTRUDNIENIA_PDF`, a `przytnij` bez tego utrudnienia
    usuwa elementy `zmiany` (także tekst usunięty) – dokument i linearyzacja poziomu 1 nie zawierają ich wcale.
    """
    nieznane = set(utrudnienia) - UTRUDNIENIA_PDF - UTRUDNIENIA_POMINIETE
    if nieznane:
        raise ValueError(f"nieznane utrudnienia PDF: {sorted(nieznane)}")
    return przytnij(d, set(utrudnienia))


# ----------------------------------------------------------------------------- pozostałe formaty (zadanie 7)
#: XLSX: `arkusz_ukryty` (część danych na ukrytym arkuszu), `komentarze` (komentarze komórek), `naglowek_wydruku`
#: (nagłówek/stopka wydruku), `metadane` (docProps), `nazwy_arkuszy` (nazwa arkusza z nazwiskiem/firmą). Tabele są
#: zawsze arkuszem (komórki), nie ma więc `tabele`; XLSX nie ma przypisów ani zmian śledzonych ani pól formularza.
UTRUDNIENIA_XLSX: frozenset[str] = frozenset({
    "arkusz_ukryty", "komentarze", "naglowek_wydruku", "metadane", "nazwy_arkuszy",
})
#: PPTX: `logo` (slajd tytułowy z logo; nagłówek/stopka jako elementy slajdów), `tabele` (slajd z tabelą),
#: `notatki` (notatki prelegenta), `komentarze` (komentarze PPTX), `metadane` (docProps).
UTRUDNIENIA_PPTX: frozenset[str] = frozenset({"logo", "tabele", "notatki", "komentarze", "metadane"})
#: EML i MSG: `html` (druga część text/html), `zalacznik` (DOCX jako załącznik), `metadane` (dodatkowe nagłówki
#: X-… z metadanymi poza From/To/Cc/Subject). Nagłówki From/To/Cc/Subject i stopka (podpis) są zawsze; komentarze,
#: zmiany, przypisy, pola i tabele nie istnieją w wiadomości (usuwane albo spłaszczane do tekstu).
UTRUDNIENIA_EML: frozenset[str] = frozenset({"html", "zalacznik", "metadane"})
UTRUDNIENIA_MSG: frozenset[str] = UTRUDNIENIA_EML
#: DOC: te same utrudnienia co DOCX (konwersja LibreOffice'em; co konwersja gubi, `renderuj_doc` usuwa z gold).
UTRUDNIENIA_DOC: frozenset[str] = UTRUDNIENIA_DOCX

#: Per format: (dozwolone utrudnienia, mapa utrudnienie formatu -> flaga `przytnij`, flagi `przytnij` wymuszone).
#: Utrudnienia bez wpisu w mapie (np. `arkusz_ukryty`, `html`) nie zmieniają drzewa – to wyłącznie forma pliku.
#: Mapy: XLSX `naglowek_wydruku`->`papier_firmowy`, tabele wymuszone (komórki arkusza); PPTX `logo`->`papier_firmowy`,
#: `notatki`->`przypisy`; EML/MSG: papier firmowy wymuszony (nagłówek i stopka zachowują miejsce „naglowek”/„stopka”),
#: metadane wymuszone (nagłówki From/To/Cc zostają wartościami „metadane”), a gdy brak `metadane` – autor neutralny
#: i pozostałe metadane z danymi usunięte (jak w `przytnij`); komentarze, zmiany, przypisy – usuwane, pola i tabele –
#: spłaszczane do tekstu.
_FORMATY: dict[str, tuple[frozenset[str], dict[str, str], frozenset[str]]] = {
    "docx": (UTRUDNIENIA_DOCX, {u: u for u in UTRUDNIENIA_DOCX}, frozenset()),
    "doc": (UTRUDNIENIA_DOC, {u: u for u in UTRUDNIENIA_DOC}, frozenset()),
    "pdf": (UTRUDNIENIA_PDF, {u: u for u in UTRUDNIENIA_PDF}, frozenset()),
    "xlsx": (UTRUDNIENIA_XLSX, {"komentarze": "komentarze", "naglowek_wydruku": "papier_firmowy",
                                "metadane": "metadane"}, frozenset({"tabele"})),
    "pptx": (UTRUDNIENIA_PPTX, {"logo": "papier_firmowy", "tabele": "tabele", "notatki": "przypisy",
                                "komentarze": "komentarze", "metadane": "metadane"}, frozenset()),
    "eml": (UTRUDNIENIA_EML, {}, frozenset({"papier_firmowy", "metadane"})),
    "msg": (UTRUDNIENIA_MSG, {}, frozenset({"papier_firmowy", "metadane"})),
    # warstwa trudna (H4b, `formaty_rtf_odt`): RTF i ODT z konwersji DOCX LibreOffice'em – utrudnienia jak w DOCX
    "rtf": (UTRUDNIENIA_DOCX, {u: u for u in UTRUDNIENIA_DOCX}, frozenset()),
    "odt": (UTRUDNIENIA_DOCX, {u: u for u in UTRUDNIENIA_DOCX}, frozenset()),
}
FORMATY: frozenset[str] = frozenset(_FORMATY)
#: Metadane, które w e-mailu są nagłówkami (zostają, gdy brak `metadane`).
NAGLOWKI_POCZTY: tuple[str, ...] = ("from", "to", "cc", "subject")


def przytnij_dla(format: str, d: Dokument, utrudnienia: set[str]) -> Dokument:
    """`przytnij` właściwe formatowi pliku: waliduje `utrudnienia` i tłumaczy je na flagi `przytnij` (zob. `_FORMATY`).

    Wynik trafia do renderera `format` i do linearyzacji poziomu 1 – plik i tekst pochodzą z tego samego `Dokumentu`.
    """
    if format not in _FORMATY:
        raise ValueError(f"nieznany format: {format!r}")
    dozwolone, mapa, wymuszone = _FORMATY[format]
    nieznane = set(utrudnienia) - dozwolone - UTRUDNIENIA_POMINIETE
    if nieznane:
        raise ValueError(f"nieznane utrudnienia {format.upper()}: {sorted(nieznane)}")
    flagi = {mapa[u] for u in utrudnienia if u in mapa} | wymuszone
    n = przytnij(d, flagi)
    if format in ("eml", "msg") and "metadane" not in utrudnienia:
        meta: dict[str, str | Wartosc] = {}
        for k, v in n.metadane.items():
            if k in NAGLOWKI_POCZTY or not isinstance(v, Wartosc):
                meta[k] = v
            elif k == "author":
                meta[k] = NEUTRALNY_AUTOR.get(n.jezyk, "User")
        n.metadane = meta
    return n
