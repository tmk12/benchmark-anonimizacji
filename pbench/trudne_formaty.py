"""Warstwa trudnych przypadków, zadanie H4b – nowe formaty plików RTF i ODT (`formaty_rtf_odt`, spec §11 pkt 6).

Dokument to zwykły dokument tekstowy trzonu (szablon: umowa, pismo, faktura…) w formacie RTF albo ODT – DOCX przekonwertowany
LibreOffice'em (`pbench.render.rtf`, `pbench.render.odt`, wzorzec DOC: gold sprawdzony odczytem zwrotnym, co konwersja zgubiła –
usunięte z ostrzeżeniem). Żeby plik miał wszystkie miejsca formatu (ODT: tekst, nagłówek/stopka, komentarz, tabela, metadane
`meta.xml`), utrudnienia `papier_firmowy`, `tabele`, `komentarze` i `metadane` są wymuszone (`korpus.WYMUSZONE_UTRUDNIENIA`), a
dokument bez komentarza albo bez tabeli dostaje je tu: komentarz recenzenta z telefonem i tabelę osób kontaktowych (osoby
dodatku nie dzielą słów imienia i nazwiska z resztą dokumentu – `trudne_poczta.FabrykaH4b`). Wartości dodatku mają identyfikatory `h.<rola>.<pole>#n`.
"""
from __future__ import annotations

import random

from . import przypadki as P
from .budowa import Wynik, zbuduj_z_kontekstem
from .dane import Generator
from .dane.wspolne import BazowyGenerator
from .model import Element
from .szablony import SZABLONY_TRUDNE as SZABLONY       # wariant warstwy trudnej (J1, S5)
from .trudne_poczta import FabrykaH4b
from .trudne_ukryta import TYPY_FORMATU, Fabryka

#: Formaty plików przypadku (kolejność: udziały w planie – `trudne.UDZIALY_DODATKOWE`).
FORMATY = ("rtf", "odt")
UWAGA = {"pl": "proszę potwierdzić dane z klientem pod numerem", "en": "please confirm the details with the client on",
         "es": "confirme los datos con el cliente en el", "de": "bitte die Angaben mit dem Mandanten klären unter",
         "fr": "merci de confirmer les données avec le client au"}
KONTAKTY = {"pl": ("Osoba do kontaktu", "Telefon"), "en": ("Contact person", "Phone"), "es": ("Persona de contacto", "Teléfono"),
            "de": ("Ansprechpartner", "Telefon"), "fr": ("Personne de contact", "Téléphone")}


def _dopisz_komentarz(f: Fabryka, elementy: list[Element]) -> None:
    o = f.osoba()
    komentarz = Element("komentarz", [f.pelne("komentarz", o, "komentarz"), f": {UWAGA[f.jezyk]} ",
                                      f.telefon("komentarz", o, "komentarz"), "."], {"autor_fragment": 0})
    elementy.append(komentarz)


def _dopisz_tabele(f: Fabryka, elementy: list[Element]) -> None:
    """Tabela „osoba do kontaktu | telefon” (nagłówek + dwa wiersze) przed podpisem (albo na końcu treści)."""
    nr = 1 + max((e.atrybuty["tabela"] for e in elementy if e.rodzaj == "komorka"), default=-1)
    komorki = [Element("komorka", [t], {"tabela": nr, "wiersz": 0, "kolumna": k}) for k, t in enumerate(KONTAKTY[f.jezyk])]
    for w in (1, 2):
        o = f.osoba()
        komorki += [Element("komorka", [f.pelne("kontakt", o, "tabela")], {"tabela": nr, "wiersz": w, "kolumna": 0}),
                    Element("komorka", [f.telefon("kontakt", o, "tabela")], {"tabela": nr, "wiersz": w, "kolumna": 1})]
    miejsce = next((i for i, e in enumerate(elementy) if e.rodzaj == "podpis"), None)
    if miejsce is None:
        miejsce = max((i for i, e in enumerate(elementy) if e.rodzaj in ("akapit", "komorka")), default=-1) + 1
    elementy[miejsce:miejsce] = komorki


def _rtf_odt(jezyk: str, typ: str, seed: int, fmt: str) -> tuple[Wynik, BazowyGenerator, dict]:
    gen = Generator(jezyk, seed)
    wynik = zbuduj_z_kontekstem(SZABLONY[(jezyk, typ)], gen, random.Random(f"pbench-h4b-ro:{seed}"))
    d = wynik.dokument
    f = FabrykaH4b(gen, wynik.kontekst, wynik)
    if not any(e.rodzaj == "komentarz" for e in d.elementy):
        _dopisz_komentarz(f, d.elementy)
    if not any(e.rodzaj == "komorka" for e in d.elementy):
        _dopisz_tabele(f, d.elementy)
    return wynik, gen, {}


#: Generator przypadku `formaty_rtf_odt`: {(język, typ tekstowy): funkcja `(język, typ, ziarno, format)`}.
GENERATORY: dict[str, dict] = {P.FORMATY_RTF_ODT: {k: _rtf_odt for k in sorted(SZABLONY) if k[1] in TYPY_FORMATU["pdf"]}}
