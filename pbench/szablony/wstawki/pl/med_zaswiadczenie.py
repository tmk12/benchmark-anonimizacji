"""Zaświadczenie lekarskie dla pacjenta z Ukrainy (do przedłożenia pracodawcy): cyrylica i transliteracja."""
from __future__ import annotations

from ....budowa import Szablon
from ..._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="pl", typ="med_zaswiadczenie", znacz_encje=True, warianty=("cw", "tr"),
    role={"placowka": "placowka", "pacjent": "osoba_ua", "lekarz": "lekarz", "pracodawca": "firma"},
    sekcje=[
        sekcja("naglowek", "naglowek",
               "{placowka.nazwa}",
               "Poradnia Podstawowej Opieki Zdrowotnej | {placowka.adres} | tel. {placowka.telefon}"),
        sekcja("miejscowosc", "akapit", "{placowka.miasto}, dnia {ctx.dok}"),
        sekcja("tytul", "akapit", "ZAŚWIADCZENIE LEKARSKIE"),
        sekcja("tresc", "akapit",
               "Zaświadczam, że {pacjent.pelne_im:t_s1} ({pacjent.pelne_im:t_s2}), data urodzenia "
               "{pacjent.data_ur}, adres zamieszkania: {pacjent.adres:t_s1}, numer РНОКПП {pacjent.rnokpp}, "
               "paszport zagraniczny {pacjent.paszport}, pozostaje pod opieką naszej poradni.",
               "W dniu {ctx.przyjecie} {pacjent.pelne_im:t_s1} {pacjent.rodzaj:zgłosił|zgłosiła} się z objawami "
               "ostrego zakażenia górnych dróg oddechowych. Rozpoznanie: J06.9. Zalecono leczenie "
               "objawowe i pozostanie w domu przez 7 dni.",
               W("tr", "Imię i nazwisko pacjenta wg dokumentu tożsamości: {pacjent.pelne_im:t_s3}; w dokumentacji "
                       "występuje także zapis {pacjent.pelne_im:t_s4}.")),
        sekcja("zdolnosc", "akapit",
               "Zaświadczenie wydano na wniosek {pacjent.pelne_im:t_s1+dop} w celu przedłożenia pracodawcy: "
               "{pracodawca.nazwa}, {pracodawca.adres}.",
               "Zaświadczenie nie jest zwolnieniem lekarskim w rozumieniu przepisów o świadczeniach pieniężnych "
               "z ubezpieczenia społecznego w razie choroby i macierzyństwa."),
        sekcja("lekarz", "akapit",
               "Lekarz wystawiający: {lekarz.pelne}, nr PWZ {lekarz.pwz}",
               "Miejsce pieczęci lekarza i placówki"),
        sekcja("podpis", "podpis", "{lekarz.pelne}"),
        sekcja("stopka", "stopka", "{placowka.nazwa} | {placowka.adres} | NIP {placowka.nip} | {placowka.email}"),
    ],
    metadane={"author": "{lekarz.pelne}", "subject": "Zaświadczenie lekarskie"},
)
