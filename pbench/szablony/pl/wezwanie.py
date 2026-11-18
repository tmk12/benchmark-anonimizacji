"""Przedsądowe wezwanie do zapłaty kierowane do dłużnika przez pełnomocnika wierzyciela."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="pl", typ="wezwanie",
    role={"kancelaria": "kancelaria", "mec": "osoba", "wierzyciel": "firma", "reprezentant": "osoba",
          "dluznik": "osoba", },
    sekcje=[
        sekcja("naglowek", "naglowek",
               "{kancelaria.nazwa}",
               "{kancelaria.adres} | tel. {kancelaria.telefon}"),
        sekcja("miejscowosc", "akapit", "{kancelaria.miasto}, dnia {ctx.wezwanie}"),
        sekcja("adresat", "akapit",
               "{dluznik.pelne}",
               "{dluznik.adres}",
               "Przesyłka polecona za potwierdzeniem odbioru"),
        sekcja("tytul", "akapit",
               "OSTATECZNE PRZEDSĄDOWE WEZWANIE DO ZAPŁATY"),
        sekcja("podstawa", "akapit",
               "Działając jako pełnomocnik wierzyciela – spółki {wierzyciel.nazwa} z siedzibą: {wierzyciel.adres}, "
               "NIP {wierzyciel.nip}, KRS {wierzyciel.krs}, reprezentowanej przez {reprezentant.pelne:bier}, "
               "wzywam {dluznik.pelne:bier} do zapłaty zaległej należności w terminie do dnia {ctx.termin_wezwania}.",
               "Zadłużenie wynika z faktury VAT wystawionej w dniu {ctx.umowa} za usługi wykonane na rzecz "
               "{dluznik.pelne:dop}, której termin płatności upłynął w dniu {ctx.termin_platnosci} bez wpłaty. Dotychczasowe monity nie "
               "odniosły skutku.",
               "Na kwotę należną składają się: należność główna w wysokości {ctx.glowna}, odsetki za "
               "opóźnienie naliczone na dzień sporządzenia wezwania w wysokości {ctx.odsetki} oraz koszty "
               "dotychczasowej windykacji w kwocie {ctx.koszty_wind}. Łącznie do zapłaty: {ctx.razem_wez}."),
        sekcja("platnosc", "akapit",
               "Wpłaty prosimy dokonać na rachunek bankowy spółki {wierzyciel.nazwa} nr {wierzyciel.rachunek}, "
               "wpisując w tytule przelewu numer faktury oraz nazwisko {dluznik.rodzaj:dłużnika|dłużniczki}.",
               "Odsetki będą naliczane do dnia faktycznej zapłaty w wysokości odsetek ustawowych za opóźnienie "
               "(art. 481 § 2 Kodeksu cywilnego), a w stosunkach z przedsiębiorcami – odsetek za opóźnienie w "
               "transakcjach handlowych na podstawie ustawy z dnia 8 marca 2013 r. o przeciwdziałaniu "
               "nadmiernym opóźnieniom w transakcjach handlowych."),
        sekcja("skutki", "akapit",
               "Po bezskutecznym upływie wyznaczonego terminu sprawa zostanie skierowana do sądu właściwego, "
               "a koszty procesu, w tym koszty zastępstwa procesowego, obciążą {dluznik.rodzaj:dłużnika|dłużniczkę} zgodnie z art. 98 "
               "Kodeksu postępowania cywilnego. Wierzyciel zastrzega możliwość wpisu zobowiązania do rejestru "
               "dłużników zgodnie z ustawą z dnia 9 kwietnia 2010 r. o udostępnianiu informacji gospodarczych.",
               "Wierzyciel dopuszcza zawarcie ugody przewidującej spłatę w ratach, jeżeli {dluznik.pelne} "
               "zgłosi taki zamiar przed upływem terminu. Pierwsza rata nie może być niższa niż "
               "{ctx.ugoda_rata}, a harmonogram wymaga formy pisemnej.",
               "Niniejsze wezwanie stanowi przerwanie biegu przedawnienia roszczenia w rozumieniu art. 123 § 1 "
               "pkt 1 k.c. jedynie w zakresie, w jakim zostanie skutecznie doręczone.",
               min=2, max=3),
        sekcja("kontakt", "akapit",
               "W sprawie rozliczenia należności można kontaktować się z kancelarią pod numerem {mec.telefon} "
               "lub pisać na adres {mec.email}, powołując się na dane {dluznik.rodzaj:dłużnika|dłużniczki}.",
               "Osoba prowadząca sprawę ze strony kancelarii: {mec.pelne}.",
               min=1, max=2),
        sekcja("zalaczniki", "akapit",
               "Załączniki: kopia faktury VAT, zestawienie odsetek, pełnomocnictwo.",
               "Do wiadomości: {reprezentant.pelne:cel} – zarząd wierzyciela."),
        sekcja("podpis", "podpis", "{mec.pelne}"),
        sekcja("stopka", "stopka",
               "{kancelaria.nazwa} | {kancelaria.adres} | NIP {kancelaria.nip} | tel. {kancelaria.telefon} | "
               "{kancelaria.email}"),
    ],
    metadane={"author": "{mec.pelne}", "subject": "Wezwanie do zapłaty"},
)
