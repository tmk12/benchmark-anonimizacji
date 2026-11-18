"""Umowa sprzedaży używanego samochodu osobowego między osobami fizycznymi (sprzedający – kupujący): dane stron
z numerami PESEL i dowodów, numer rejestracyjny pojazdu, cena z zaliczką i rachunkiem, stan licznika w tabeli.
Numer VIN nie jest kategorią generatora – dokument go nie zawiera."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="pl", typ="umowa_sprzedazy_auta", dorosli=True,
    role={"sprzedajacy": "osoba", "kupujacy": "osoba", "pojazd": "sprawa", "swiadek": "osoba"},
    sekcje=[
        sekcja("naglowek", "naglowek",
               "UMOWA SPRZEDAŻY POJAZDU",
               "Sprzedający: {sprzedajacy.pelne} | Kupujący: {kupujacy.pelne}"),
        sekcja("tytul", "akapit",
               "zawarta w dniu {ctx.dok} w miejscowości {sprzedajacy.miasto} pomiędzy:"),
        sekcja("strony", "akapit",
               "{sprzedajacy.pelne}, PESEL {sprzedajacy.pesel}, dowód osobisty {sprzedajacy.dowod}, "
               "{sprzedajacy.rodzaj:zamieszkałym|zamieszkałą} pod adresem: {sprzedajacy.adres}, tel. "
               "{sprzedajacy.telefon}, zwanym dalej „Sprzedającym”,",
               "a",
               "{kupujacy.pelne}, PESEL {kupujacy.pesel}, dowód osobisty {kupujacy.dowod}, "
               "{kupujacy.rodzaj:zamieszkałym|zamieszkałą} pod adresem: {kupujacy.adres}, tel. {kupujacy.telefon}, "
               "e-mail: {kupujacy.email}, zwanym dalej „Kupującym”."),
        sekcja("przedmiot", "akapit",
               "§ 1. Przedmiot sprzedaży",
               "1. Sprzedający oświadcza, że jest wyłącznym właścicielem używanego samochodu osobowego o numerze "
               "rejestracyjnym {pojazd.tablica}, zwanego dalej „Pojazdem”, i że Pojazd nie jest przedmiotem zastawu, "
               "zabezpieczenia ani postępowania egzekucyjnego.",
               "2. Sprzedający sprzedaje Pojazd Kupującemu, a Kupujący go kupuje wraz z dowodem rejestracyjnym, kartą "
               "pojazdu, dwoma kompletami kluczyków i kompletem opon zimowych.",
               "3. Sprzedający oświadcza, że zgłosił zbycie Pojazdu do ubezpieczyciela, a polisa OC Pojazdu "
               "obowiązuje do dnia {ctx.dok_pozniej}."),
        sekcja("cena", "akapit",
               "§ 2. Cena i płatność",
               "1. Strony ustalają cenę sprzedaży Pojazdu na kwotę {ctx.szkoda}.",
               "2. Kupujący wpłacił zaliczkę w wysokości {ctx.zaliczka_ub} przy podpisaniu umowy, a pozostałą część "
               "ceny zapłaci przelewem na rachunek Sprzedającego nr {sprzedajacy.rachunek} do dnia {ctx.dok_termin}.",
               "3. Kupujący pokrywa koszty przerejestrowania Pojazdu oraz podatek od czynności cywilnoprawnych, "
               "który zapłaci w terminie 14 dni od zawarcia umowy."),
        sekcja("stan", "komorka",
               "Element | Stan | Uwagi\n"
               "Przebieg | 187 450 km | zgodny ze wskazaniem licznika\n"
               "Przegląd techniczny | ważny do {ctx.dok_pozniej} | zaświadczenie dołączone\n"
               "Szkody | brak | pojazd bezwypadkowy w ocenie {sprzedajacy.pelne:dop}",
               "Element | Dokument | Przekazano\n"
               "Dowód rejestracyjny | seria i numer wg dokumentu | {kupujacy.pelne}\n"
               "Kluczyki | 2 kpl. | {kupujacy.pelne}\n"
               "Faktury za serwis | 9 szt. | {swiadek.pelne}",
               min=1, max=1),
        sekcja("wydanie", "akapit",
               "§ 3. Wydanie Pojazdu i rękojmia",
               "1. Wydanie Pojazdu nastąpi w dniu {ctx.dok_sprzedaz} pod adresem Sprzedającego; przy wydaniu obecny "
               "będzie {swiadek.pelne} (tel. {swiadek.telefon}) jako świadek stanu Pojazdu.",
               "2. Kupujący oświadcza, że zapoznał się ze stanem technicznym Pojazdu, odbył jazdę próbną i nie "
               "wnosi zastrzeżeń. Odpowiedzialność z tytułu rękojmi za wady fizyczne zostaje wyłączona w zakresie "
               "dopuszczonym przepisami.",
               "3. Z chwilą wydania na Kupującego przechodzą korzyści i ciężary związane z Pojazdem oraz "
               "ryzyko jego przypadkowej utraty."),
        sekcja("koncowe", "akapit",
               "§ 4. Postanowienia końcowe",
               "1. Zmiany umowy wymagają formy pisemnej pod rygorem nieważności.",
               "2. W sprawach nieuregulowanych stosuje się przepisy Kodeksu cywilnego o sprzedaży (art. 535 i nast.).",
               "3. Umowę sporządzono w dwóch jednobrzmiących egzemplarzach, po jednym dla każdej ze Stron; "
               "kontakt: {sprzedajacy.email}, {kupujacy.telefon}."),
        sekcja("podpisy_opis", "akapit", "Sprzedający:                                                  Kupujący:"),
        sekcja("podpisy", "podpis", "{sprzedajacy.pelne}", "{kupujacy.pelne}"),
        sekcja("stopka", "stopka",
               "Umowa sprzedaży pojazdu {pojazd.tablica} | {sprzedajacy.pelne} / {kupujacy.pelne}"),
        sekcja("uwaga", "przypis",
               "Kupujący jest zobowiązany zgłosić nabycie Pojazdu w wydziale komunikacji w terminie 30 dni od dnia "
               "zawarcia umowy, a Sprzedający – zawiadomić o zbyciu ubezpieczyciela."),
    ],
    metadane={"author": "{sprzedajacy.pelne}", "title": "Umowa sprzedaży pojazdu"},
)
