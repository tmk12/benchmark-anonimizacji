"""Faktura VAT za usługi prawne: dane stron i pozycje w tabelach, podsumowanie, uwagi o rozliczeniu."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="pl", typ="faktura",
    role={"sprzedawca": "firma", "nabywca": "firma", "wystawiajacy": "osoba", "odbierajacy": "osoba",
          },
    sekcje=[
        sekcja("naglowek", "naglowek",
               "{sprzedawca.nazwa}",
               "{sprzedawca.adres} | NIP {sprzedawca.nip}"),
        sekcja("tytul", "akapit",
               "FAKTURA VAT",
               "Data wystawienia: {ctx.dok}",
               "Data sprzedaży: {ctx.dok_sprzedaz}"),
        sekcja("strony", "komorka",
               "Sprzedawca | Nabywca\n"
               "{sprzedawca.nazwa} | {nabywca.nazwa}\n"
               "{sprzedawca.adres} | {nabywca.adres}\n"
               "NIP: {sprzedawca.nip} | NIP: {nabywca.nip}\n"
               "REGON: {sprzedawca.regon} | REGON: {nabywca.regon}"),
        sekcja("pozycje", "komorka",
               "Lp. | Nazwa towaru lub usługi | Ilość | Cena netto | Wartość netto | VAT\n"
               "1 | Stała obsługa prawna za miesiąc rozliczeniowy | 1 | {ctx.kf1} | {ctx.kf1} | 23%\n"
               "2 | Opinia prawna w sprawie umowy najmu | 1 | {ctx.kf2} | {ctx.kf2} | 23%\n"
               "3 | Reprezentacja przed organem administracji | 1 | {ctx.kf3} | {ctx.kf3} | 23%",
               "Lp. | Nazwa usługi | Jedn. | Ilość | Wartość netto | Stawka VAT\n"
               "1 | Czynności doradcze wg umowy z dnia {ctx.umowa_dawna} | ryczałt | 1 | {ctx.kf1} | 23%\n"
               "2 | Przygotowanie i negocjacja dokumentacji | ryczałt | 1 | {ctx.kf2} | 23%\n"
               "3 | Udział w posiedzeniach organów spółki | ryczałt | 1 | {ctx.kf3} | 23%",
               min=1, max=1),
        sekcja("podsumowanie", "komorka",
               "Razem netto | Podatek VAT 23% | Razem do zapłaty (brutto)\n"
               "{ctx.netto} | {ctx.vat} | {ctx.brutto}"),
        sekcja("platnosc", "akapit",
               "Termin płatności: {ctx.dok_termin_fv}. Sposób zapłaty: przelew na rachunek {sprzedawca.rachunek}.",
               "Adres e-mail do przesyłania potwierdzeń płatności: {sprzedawca.email}, tel. {sprzedawca.telefon}."),
        sekcja("uwagi", "akapit",
               "Faktura wystawiona zgodnie z art. 106b ustawy z dnia 11 marca 2004 r. o podatku od towarów i "
               "usług. Zastosowano mechanizm podzielonej płatności, jeżeli wartość brutto przekracza 15 000 zł "
               "i usługa została wymieniona w załączniku nr 15 do ustawy.",
               "W przypadku opóźnienia w płatności naliczane będą odsetki ustawowe za opóźnienie w transakcjach "
               "handlowych oraz rekompensata za koszty odzyskiwania należności w wysokości 40 euro "
               "(art. 10 ust. 1 ustawy o przeciwdziałaniu nadmiernym opóźnieniom w transakcjach handlowych).",
               "Faktura jest wystawiona w formie elektronicznej i nie wymaga podpisu odbiorcy "
               "(art. 106n ustawy o VAT)."),
        sekcja("wystawil", "akapit",
               "Fakturę przekazano w formie elektronicznej {odbierajacy.pelne:cel} – osobie upoważnionej do "
               "odbioru dokumentów rozliczeniowych nabywcy.",
               "Fakturę wystawił i sprawdził pod względem rachunkowym {wystawiajacy.pelne}."),
        sekcja("podpis", "podpis", "{wystawiajacy.pelne}"),
        sekcja("stopka", "stopka",
               "{sprzedawca.nazwa} | {sprzedawca.adres} | NIP {sprzedawca.nip} | KRS {sprzedawca.krs} | tel. "
               "{sprzedawca.telefon}"),
    ],
    metadane={"author": "{wystawiajacy.pelne}", "subject": "Faktura VAT"},
)
