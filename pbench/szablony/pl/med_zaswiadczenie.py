"""Zaświadczenie lekarskie o stanie zdrowia wystawione do przedłożenia w sądzie (usprawiedliwienie nieobecności)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="pl", typ="med_zaswiadczenie",
    profil="interna", warianty=("rejonowy", "okregowy"),
    role={"placowka": "placowka", "pacjent": "pacjent", "lekarz": "lekarz",
          "sprawa": "sprawa", "sad": "sad"},
    sekcje=[
        sekcja("naglowek", "naglowek",
               "{placowka.nazwa}",
               "Poradnia Specjalistyczna | {placowka.adres} | tel. {placowka.telefon}"),
        sekcja("miejscowosc", "akapit", "{placowka.miasto}, dnia {ctx.zas_wystaw}"),
        sekcja("tytul", "akapit", "ZAŚWIADCZENIE LEKARSKIE"),
        sekcja("tresc", "akapit",
               "Zaświadczam, że {pacjent.pelne}, PESEL {pacjent.pesel}, data urodzenia {pacjent.data_ur}, "
               "adres zamieszkania: {pacjent.adres}, pozostaje pod opieką naszej poradni.",
               "Rozpoznanie: {pacjent.diagnoza}. Choroby współistniejące: {pacjent.diagnoza2}.",
               "W dniu {ctx.zas_od} w stanie zdrowia {pacjent.pelne:dop} stwierdzono zaostrzenie choroby "
               "podstawowej wymagające leczenia farmakologicznego, między innymi: {pacjent.lek} oraz "
               "{pacjent.lek2}. Zalecono ograniczenie aktywności od dnia {ctx.zas_od} do dnia {ctx.zas_do}."),
        sekcja("zdolnosc", "akapit",
               "Ze względu na stan zdrowia {pacjent.rodzaj:wymieniony pacjent jest niezdolny|wymieniona pacjentka jest niezdolna} do uczestniczenia w czynnościach "
               "wymagających dłuższej podróży oraz pozostawania w pozycji siedzącej powyżej dwóch godzin; "
               "dotyczy to także rozprawy wyznaczonej na dzień {ctx.rozprawa}.",
               "Zaświadczenie wydano na wniosek {pacjent.pelne:dop} w celu przedłożenia sądowi w sprawie o "
               "sygn. akt {sprawa.sygnatura} jako usprawiedliwienie nieobecności; sąd prowadzący sprawę: "
               "{sad.nazwa}.",
               "Zalecono kontrolę lekarską po upływie wskazanego okresu, a w razie nasilenia objawów – "
               "niezwłoczny kontakt z lekarzem rodzinnym albo zgłoszenie się do szpitalnego oddziału ratunkowego."),
        sekcja("pouczenie", "akapit",
               "Zaświadczenie wystawiono na podstawie badania przeprowadzonego w dniu {ctx.zas_wystaw} oraz "
               "dokumentacji medycznej prowadzonej w poradni. Zgodnie z art. 233 § 1a Kodeksu karnego, "
               "kto jako lekarz wystawia zaświadczenie niezgodne z prawdą, podlega karze pozbawienia wolności.",
               "Zaświadczenie nie jest zwolnieniem lekarskim w rozumieniu przepisów o świadczeniach pieniężnych "
               "z ubezpieczenia społecznego w razie choroby i macierzyństwa.",
               "Dokument zawiera dane dotyczące zdrowia i został wydany do rąk własnych {pacjent.rodzaj:pacjenta|pacjentki} lub "
               "osoby upoważnionej."),
        sekcja("lekarz", "akapit",
               "Lekarz wystawiający: {lekarz.pelne}, nr PWZ {lekarz.pwz}, specjalista chorób wewnętrznych",
               "Miejsce pieczęci lekarza i placówki"),
        sekcja("podpis", "podpis", "{lekarz.pelne}"),
        sekcja("stopka", "stopka", "{placowka.nazwa} | {placowka.adres} | NIP {placowka.nip} | {placowka.email}"),
    ],
    metadane={"author": "{lekarz.pelne}", "subject": "Zaświadczenie lekarskie"},
)
