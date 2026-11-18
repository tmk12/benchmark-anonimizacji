"""Skierowanie na leczenie szpitalne lub badania specjalistyczne wystawione przez lekarza poradni."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="pl", typ="med_skierowanie",
    profil="interna",
    role={"poradnia": "placowka", "szpital": "placowka", "pacjent": "pacjent",
          "lekarz": "lekarz", "opiekun": "osoba"},
    sekcje=[
        sekcja("naglowek", "naglowek",
               "{poradnia.nazwa}",
               "{poradnia.adres} | tel. {poradnia.telefon} | REGON {poradnia.regon}"),
        sekcja("miejscowosc", "akapit", "{poradnia.miasto}, dnia {ctx.dok}"),
        sekcja("tytul", "akapit",
               "SKIEROWANIE NA LECZENIE SZPITALNE",
               "Pilność: skierowanie w trybie pilnym, termin przyjęcia do {ctx.dok_termin}"),
        sekcja("pacjent", "akapit",
               "Dane {pacjent.rodzaj:pacjenta|pacjentki}: {pacjent.pelne}, PESEL {pacjent.pesel}, data urodzenia {pacjent.data_ur}",
               "Adres: {pacjent.adres}, tel. {pacjent.telefon}",
               "Skierowuję {pacjent.pelne:bier} do szpitala: {szpital.nazwa}, {szpital.adres}, w celu "
               "diagnostyki i leczenia."),
        sekcja("rozpoznanie", "akapit",
               "Rozpoznanie główne (ICD-10): {pacjent.diagnoza}",
               "Rozpoznanie dodatkowe: {pacjent.diagnoza2}",
               "Dotychczasowe leczenie: {pacjent.lek} – bez wystarczającej poprawy; {pacjent.lek2} – z przerwami "
               "z powodu działań niepożądanych.",
               min=3, max=3),
        sekcja("uzasadnienie", "akapit",
               "Uzasadnienie skierowania: w ostatnich tygodniach narastanie dolegliwości mimo leczenia "
               "ambulatoryjnego, konieczność pogłębienia diagnostyki obrazowej i wdrożenia leczenia "
               "w warunkach szpitalnych.",
               "Wyniki badań dodatkowych dołączono do skierowania; {pacjent.rodzaj:pacjent powinien|pacjentka powinna} zabrać aktualny wykaz "
               "przyjmowanych leków oraz dokumentację medyczną z poprzednich hospitalizacji.",
               "Rejestracja do oddziału: {szpital.telefon}, e-mail {szpital.email}; wymagane okazanie dowodu "
               "tożsamości oraz dokumentu potwierdzającego ubezpieczenie.",
               "Skierowanie wystawiono zgodnie z art. 57 ustawy z dnia 27 sierpnia 2004 r. o świadczeniach "
               "opieki zdrowotnej finansowanych ze środków publicznych; skierowanie jest ważne do dnia "
               "wskazanego w terminie przyjęcia.",
               "{pacjent.rodzaj:Pacjent został poinformowany|Pacjentka została poinformowana} o możliwości wyboru świadczeniodawcy w ramach systemu NFZ oraz "
               "o prawie do informacji o stanie zdrowia."),
        sekcja("kontakt", "akapit",
               "Informacje o przebiegu leczenia prosimy przekazywać lekarzowi kierującemu w Poradni "
               "{poradnia.nazwa} oraz osobie wskazanej przez {pacjent.rodzaj:pacjenta|pacjentkę}: {opiekun.pelne:cel}.",
               min=0, max=1),
        sekcja("lekarz", "akapit",
               "Lekarz kierujący: {lekarz.pelne}, nr PWZ {lekarz.pwz}",
               "Miejsce pieczęci imiennej i podpisu"),
        sekcja("podpis", "podpis", "{lekarz.pelne}"),
        sekcja("stopka", "stopka", "{poradnia.nazwa} | {poradnia.adres} | tel. {poradnia.telefon} | {poradnia.email}"),
    ],
    metadane={"author": "{lekarz.pelne}", "subject": "Skierowanie na leczenie szpitalne"},
)
