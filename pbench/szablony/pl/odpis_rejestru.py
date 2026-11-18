"""Odpis aktualny z rejestru przedsiębiorców KRS spółki z o.o.: rubryki, tabele organów i wspólników."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="pl", typ="odpis_rejestru", dorosli=True,
    role={"spolka": "firma", "z1": "osoba", "z2": "osoba", "z3": "osoba", "prokurent": "osoba",
          "wsp1": "osoba", "wsp2": "osoba", "rn": "osoba", "sad": "sad", },
    sekcje=[
        sekcja("naglowek", "naglowek",
               "Odpis aktualny z rejestru przedsiębiorców",
               "Numer KRS: {spolka.krs}"),
        sekcja("opis", "akapit",
               "Data sporządzenia odpisu: {ctx.dok}",
               "Rejestr przedsiębiorców Krajowego Rejestru Sądowego prowadzony przez {sad.nazwa}, "
               "Wydział Gospodarczy Krajowego Rejestru Sądowego",
               "Sygnatura akt rejestrowych: {ctx.sygn_rej}",
               "Odpis aktualny zawiera informacje o podmiocie według stanu na dzień sporządzenia."),
        sekcja("rubryka1", "komorka",
               "Rubryka 1 | Dane podmiotu\n"
               "1. Oznaczenie formy prawnej | SPÓŁKA Z OGRANICZONĄ ODPOWIEDZIALNOŚCIĄ\n"
               "2. Numer REGON / NIP | REGON: {spolka.regon}, NIP: {spolka.nip}\n"
               "3. Firma, pod którą spółka działa | {spolka.nazwa}\n"
               "4. Siedziba i adres | {spolka.adres}\n"
               "5. Adres poczty elektronicznej / strona www | {spolka.email}; tel. {spolka.telefon}"),
        sekcja("rubryka2", "komorka",
               "Rubryka 2 | Wzmianki o wpisie\n"
               "1. Data wpisu do rejestru przedsiębiorców | {ctx.kr_rejestracja}\n"
               "2. Data ostatniego wpisu | {ctx.kr_wpis}\n"
               "3. Kapitał zakładowy | {ctx.kapital2}"),
        sekcja("zarzad_tytul", "akapit",
               "Rubryka 1 – Organ uprawniony do reprezentacji podmiotu: ZARZĄD",
               "Sposób reprezentacji: do składania oświadczeń woli w imieniu spółki uprawnieni są dwaj członkowie "
               "zarządu działający łącznie albo jeden członek zarządu łącznie z prokurentem."),
        sekcja("zarzad", "komorka",
               "Lp. | Nazwisko | Imiona | PESEL | Data urodzenia | Funkcja\n"
               "1 | {z1.nazwisko} | {z1.imie} | {z1.pesel} | {z1.data_ur} | PREZES ZARZĄDU\n"
               "2 | {z2.nazwisko} | {z2.imie} | {z2.pesel} | {z2.data_ur} | WICEPREZES ZARZĄDU\n"
               "3 | {z3.nazwisko} | {z3.imie} | {z3.pesel} | {z3.data_ur} | CZŁONEK ZARZĄDU",
               "Lp. | Nazwisko / Nazwa lub firma | Imiona | Numer PESEL / REGON | Funkcja w organie\n"
               "1 | {z1.nazwisko} | {z1.imie} | {z1.pesel} | PREZES ZARZĄDU\n"
               "2 | {z2.nazwisko} | {z2.imie} | {z2.pesel} | CZŁONEK ZARZĄDU\n"
               "Data urodzenia członka zarządu | {z1.data_ur} | {z2.data_ur} |  | ",
               min=1, max=1),
        sekcja("prokura", "komorka",
               "Prokurenci | Nazwisko | Imiona | PESEL | Rodzaj prokury\n"
               "1 | {prokurent.nazwisko} | {prokurent.imie} | {prokurent.pesel} | prokura łączna",
               min=0, max=1),
        sekcja("wspolnicy", "komorka",
               "Wspólnicy | Nazwisko | Imiona | Liczba udziałów | Wartość udziałów\n"
               "1 | {wsp1.nazwisko} | {wsp1.imie} | {ctx.udzialy1} | {ctx.wartosc1}\n"
               "2 | {wsp2.nazwisko} | {wsp2.imie} | {ctx.udzialy2} | {ctx.wartosc2}",
               min=0, max=1),
        sekcja("nadzor", "akapit",
               "Rubryka 2 – Organ nadzoru: RADA NADZORCZA. {rn.rodzaj:Przewodniczący|Przewodnicząca} rady nadzorczej: {rn.pelne}.",
               "Spółka nie jest podmiotem w likwidacji ani w upadłości; nie wszczęto postępowania "
               "restrukturyzacyjnego.",
               min=1, max=2),
        sekcja("dzialalnosc", "akapit",
               "Przedmiot działalności: 69.10.Z – działalność prawnicza; 70.22.Z – pozostałe doradztwo w zakresie "
               "prowadzenia działalności gospodarczej; 62.01.Z – działalność związana z oprogramowaniem.",
               "Czas trwania spółki jest nieoznaczony. Rok obrotowy jest równy rokowi kalendarzowemu; pierwszy "
               "rok obrotowy zakończył się 31 grudnia.",
               "Dane zgłoszone do rejestru podlegają ujawnieniu, a podmiot jest zobowiązany do składania "
               "sprawozdań finansowych w terminie określonym w art. 69 ustawy o rachunkowości."),
        sekcja("stopka", "stopka",
               "Odpis sporządzono na podstawie ustawy z dnia 20 sierpnia 1997 r. o Krajowym Rejestrze Sądowym | "
               "KRS {spolka.krs} | Strona 1 z 2"),
    ],
    metadane={"subject": "Odpis aktualny z KRS", "registry_no": "{spolka.krs}"},
    warianty=("rejonowy",),
)
