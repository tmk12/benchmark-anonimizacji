"""Szablony wyłącznie do testów drzewa dokumentu (prawdziwe szablony powstają w zadaniu 4)."""
from __future__ import annotations

from pbench.budowa import Blok, Sekcja, Szablon


def szablon_pl() -> Szablon:
    """Pełny szablon PL obejmujący wszystkie rodzaje elementów i miejsca."""
    return Szablon(
        jezyk="pl", typ="test",
        role={"klient": "osoba", "pelnomocnik": "osoba", "kancelaria": "kancelaria", "sad": "sad",
              "pacjent": "pacjent", "cytat": "cytat", "sprawa": "sprawa"},
        sekcje=[
            Sekcja("naglowek", "naglowek", [Blok("{kancelaria.nazwa}, {kancelaria.adres}", {"kancelaria"})], 1, 1),
            Sekcja("wstep", "akapit", [
                Blok("Powód {klient.pelne}, PESEL {klient.pesel}, zam. {klient.adres}.", {"klient"}),
                Blok("Pozwany {pelnomocnik.pelne:dop} reprezentuje {kancelaria.nazwa}.", {"pelnomocnik", "kancelaria"}),
                Blok("Sprawa {sad.sygnatura} przed {sad.nazwa}.", {"sad"}),
                Blok("Por. wyrok {cytat.sprawa}, sygn. {cytat.sygnatura}.", {"cytat"}),
                Blok("Pacjent {pacjent.pelne} rozpoznanie {pacjent.diagnoza}, lek {pacjent.lek}.", {"pacjent"}),
            ], 3, 4),
            Sekcja("tabela", "komorka", [
                Blok("Imię | Nazwisko\n{klient.pelne/1} | {klient.pelne/2}", {"klient"}),
            ], 1, 1),
            Sekcja("przypisy", "przypis", [Blok("Kontakt: {klient.email}, tel. {klient.telefon}.", {"klient"})], 1, 1),
            Sekcja("komentarze", "komentarz", [Blok("{pelnomocnik.pelne} | Sprawdzić dane {klient.nazwisko}.",
                                                   {"pelnomocnik", "klient"})], 1, 1),
            Sekcja("zmiany", "zmiany", [Blok("del | {pelnomocnik.pelne} | stary adres {klient.adres}",
                                             {"pelnomocnik", "klient"})], 1, 1),
            Sekcja("pola", "pole", [Blok("Rachunek | {klient.rachunek}", {"klient"})], 1, 1),
            Sekcja("stopka", "stopka", [Blok("{kancelaria.nazwa} | {kancelaria.telefon}", {"kancelaria"})], 1, 1),
            Sekcja("podpis", "podpis", [Blok("{pelnomocnik.pelne}", {"pelnomocnik"})], 1, 1),
        ],
        metadane={"author": "{pelnomocnik.pelne}", "subject": "Pismo"},
    )
