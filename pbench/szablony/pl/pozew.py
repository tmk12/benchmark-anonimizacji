"""Pozew o zapłatę z tytułu umowy pożyczki wniesiony do sądu cywilnego przez pełnomocnika z kancelarii."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="pl", typ="pozew", warianty=("rejonowy", "okregowy"),
    role={"kancelaria": "kancelaria", "mec": "osoba", "powod": "osoba", "pozwany": "osoba", "swiadek": "osoba",
          "swiadek2": "osoba", "sad": "sad", "poprz": "sprawa"},
    sekcje=[
        sekcja("naglowek", "naglowek",
               "{mec.pelne} – {kancelaria.nazwa}",
               "{kancelaria.adres}, tel. {kancelaria.telefon}"),
        sekcja("miejscowosc", "akapit", "{kancelaria.miasto}, dnia {ctx.pozew}"),
        sekcja("adresat", "akapit",
               "{sad.nazwa}",
               "Wydział Cywilny",
               "{powod.rodzaj:Powód|Powódka}: {powod.pelne}, PESEL {powod.pesel}, adres: {powod.adres}",
               "{pozwany.rodzaj:Pozwany|Pozwana}: {pozwany.pelne}, adres: {pozwany.adres}",
               "Wartość przedmiotu sporu: {ctx.glowna}"),
        sekcja("tytul", "akapit", "POZEW O ZAPŁATĘ"),
        sekcja("zadanie", "akapit",
               "Działając w imieniu {powod.rodzaj:powoda|powódki} {powod.pelne:dop}, na podstawie pełnomocnictwa załączonego do "
               "pozwu, wnoszę o:",
               "1. zasądzenie od {pozwany.rodzaj:pozwanego|pozwanej} {pozwany.pelne:dop} na rzecz {powod.rodzaj:powoda|powódki} {powod.pelne:dop} kwoty "
               "{ctx.glowna} wraz z odsetkami ustawowymi za opóźnienie liczonymi od dnia {ctx.termin_platnosci} do dnia "
               "zapłaty;",
               "2. zasądzenie od {pozwany.rodzaj:pozwanego|pozwanej} {pozwany.pelne:dop} na rzecz {powod.rodzaj:powoda|powódki} kosztów procesu, w tym kosztów "
               "zastępstwa procesowego według norm przepisanych oraz opłaty skarbowej od pełnomocnictwa w "
               "wysokości 17 zł;",
               "3. nadanie wyrokowi rygoru natychmiastowej wykonalności w całości."),
        sekcja("uzasadnienie", "akapit",
               "UZASADNIENIE",
               "W dniu {ctx.umowa} strony zawarły w formie pisemnej umowę pożyczki, na mocy której "
               "udzielono {pozwany.rodzaj:pozwanemu|pozwanej} pożyczki w kwocie {ctx.glowna}, z obowiązkiem zwrotu w terminie "
               "określonym w umowie. Środki zostały wypłacone przelewem w dniu zawarcia umowy.",
               "Zwrot pożyczki nie nastąpił w umówionym terminie. Wezwanie do zapłaty zostało "
               "skierowane do {pozwany.rodzaj:pozwanego|pozwanej} {pozwany.pelne:dop} w dniu {ctx.wezwanie} listem poleconym na "
               "adres {pozwany.adres}, z wyznaczeniem terminu siedmiu dni na dobrowolne spełnienie świadczenia. "
               "Wezwanie pozostało bez odpowiedzi.",
               "Roszczenie o zwrot pożyczki wynika z art. 720 § 1 Kodeksu cywilnego, a żądanie odsetek za "
               "opóźnienie z art. 481 § 1 i § 2 k.c. w związku z art. 455 k.c. Termin zwrotu upłynął dnia "
               "{ctx.termin_platnosci}, co od następnego dnia czyni {pozwany.rodzaj:pozwanego dłużnikiem|pozwaną dłużniczką} w opóźnieniu.",
               "W sprawie o sygn. akt {poprz.sygnatura} toczyło się wcześniej postępowanie zabezpieczające, które "
               "zakończyło się prawomocnym postanowieniem o udzieleniu zabezpieczenia roszczenia.",
               min=3, max=4),
        sekcja("wlasciwosc", "akapit",
               W("rejonowy", "Sąd jest właściwy rzeczowo na podstawie art. 16 § 1 pkt 1 Kodeksu postępowania "
                 "cywilnego (wartość przedmiotu sporu nie przekracza 100 000 zł), a właściwość miejscowa wynika z "
                 "art. 27 § 1 k.p.c. (sąd miejsca zamieszkania {pozwany.rodzaj:pozwanego|pozwanej})."),
               W("okregowy", "Sąd jest właściwy rzeczowo na podstawie art. 17 pkt 4 Kodeksu postępowania "
                 "cywilnego (wartość przedmiotu sporu przekracza 100 000 zł), a właściwość miejscowa wynika z "
                 "art. 27 § 1 k.p.c. (sąd miejsca zamieszkania {pozwany.rodzaj:pozwanego|pozwanej}).",),
               "Wartość przedmiotu sporu przekracza próg określony w art. 505^1 pkt 1 k.p.c., jednak strony nie "
               "korzystają z elektronicznego postępowania upominawczego, a {powod.rodzaj:powód|powódka} nie wnosi o rozpoznanie sprawy w "
               "tym trybie."),
        sekcja("dowody", "akapit",
               "Na powyższe okoliczności {powod.rodzaj:powód|powódka} wnosi o przeprowadzenie dowodów:",
               "1. z umowy pożyczki z dnia {ctx.umowa} – na okoliczność zawarcia umowy i jej warunków;",
               "2. z potwierdzenia przelewu – na okoliczność wypłaty pożyczki na rachunek {pozwany.rachunek};",
               "3. z zeznań świadka {swiadek.pelne:dop}, adres: {swiadek.adres} – na okoliczność przebiegu "
               "negocjacji i uznania długu przez {pozwany.rodzaj:pozwanego|pozwanej};",
               "4. z zeznań świadka {swiadek2.pelne:dop}, tel. {swiadek2.telefon} – na okoliczność wezwań do "
               "zapłaty kierowanych do {pozwany.rodzaj:pozwanego|pozwanej} {pozwany.pelne:dop};",
               "5. z przesłuchania stron, w tym {pozwany.rodzaj:pozwanego|pozwanej} {pozwany.pelne:dop}, w charakterze strony.",
               min=3, max=5),
        sekcja("zalaczniki", "akapit",
               "Załączniki:",
               "1. odpis pozwu wraz z załącznikami,",
               "2. pełnomocnictwo wraz z dowodem uiszczenia opłaty skarbowej,",
               "3. dowód uiszczenia opłaty sądowej od pozwu w wysokości {ctx.oplata_pozwu},",
               "4. odpis wezwania do zapłaty wraz z dowodem nadania."),
        sekcja("podpis", "podpis", "{mec.pelne}"),
        sekcja("stopka", "stopka",
               "{kancelaria.nazwa} | {kancelaria.adres} | NIP {kancelaria.nip} | tel. {kancelaria.telefon} | "
               "{kancelaria.email}"),
    ],
    metadane={"author": "{mec.pelne}", "subject": "Pozew o zapłatę"},
)
