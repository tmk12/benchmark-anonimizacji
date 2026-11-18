"""Protokół z nadzwyczajnego zgromadzenia wspólników spółki z o.o. (lista obecności w tabeli, uchwały)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja, z_zamianami

SZABLON = Szablon(
    jezyk="pl", typ="protokol", dorosli=True,
    role={"spolka": "firma", "przewodniczacy": "osoba", "sekretarz": "osoba", "w1": "osoba", "w2": "osoba",
          "w3": "osoba", "prezes": "osoba", "nowy_czlonek": "osoba", "notariusz": "osoba",
          },
    sekcje=[
        sekcja("naglowek", "naglowek",
               "{spolka.nazwa}",
               "{spolka.adres} | KRS {spolka.krs} | NIP {spolka.nip}"),
        sekcja("tytul", "akapit",
               "PROTOKÓŁ Z NADZWYCZAJNEGO ZGROMADZENIA WSPÓLNIKÓW",
               "{spolka.nazwa} z siedzibą: {spolka.adres}",
               "odbytego w dniu {ctx.dok} w siedzibie spółki pod adresem {spolka.adres}"),
        sekcja("otwarcie", "akapit",
               "1. Otwarcie zgromadzenia. Zgromadzenie otwiera i prowadzi do czasu wyboru przewodniczącego "
               "{prezes.pelne}, Prezes Zarządu, który stwierdza, że zgromadzenie zostało zwołane zgodnie z "
               "art. 238 Kodeksu spółek handlowych, a zawiadomienia wysłano wszystkim wspólnikom listami "
               "poleconymi na co najmniej dwa tygodnie przed terminem.",
               "2. Wybór przewodniczącego. Na {przewodniczacy.rodzaj:przewodniczącego|przewodniczącą} zgromadzenia jednogłośnie wybrano "
               "{przewodniczacy.pelne:bier}. Wybór został przyjęty, a {przewodniczacy.rodzaj:przewodniczący|przewodnicząca} stwierdza obecność "
               "wymaganej liczby wspólników.",
               "3. Wybór sekretarza. Na sekretarza powołano {sekretarz.pelne:bier} do sporządzenia protokołu "
               "zgodnie z art. 248 k.s.h."),
        sekcja("lista_tytul", "akapit", "Lista obecności wspólników:"),
        sekcja("lista", "komorka",
               "Lp. | Imię | Nazwisko | Dokument tożsamości | Liczba udziałów | Podpis\n"
               "1 | {w1.pelne/1} | {w1.pelne/2} | {w1.dowod} | {ctx.udzialy1} | \n"
               "2 | {w2.pelne/1} | {w2.pelne/2} | {w2.dowod} | {ctx.udzialy2} | \n"
               "3 | {w3.pelne/1} | {w3.pelne/2} | {w3.dowod} | {ctx.udzialy3} | ",
               "Lp. | Wspólnik | PESEL | Udziały | Głosy\n"
               "1 | {w1.pelne} | {w1.pesel} | {ctx.udzialy1} | {ctx.udzialy1}\n"
               "2 | {w2.pelne} | {w2.pesel} | {ctx.udzialy2} | {ctx.udzialy2}\n"
               "3 | {w3.pelne} | {w3.pesel} | {ctx.udzialy3} | {ctx.udzialy3}",
               min=1, max=1),
        sekcja("kworum", "akapit",
               "{przewodniczacy.rodzaj:Przewodniczący|Przewodnicząca} stwierdza, że na zgromadzeniu reprezentowany jest cały kapitał zakładowy "
               "spółki w wysokości {ctx.kapital3}, wobec czego zgromadzenie jest zdolne do podejmowania "
               "uchwał także bez formalnego zwołania (art. 240 § 1 k.s.h.). Nikt z obecnych nie zgłosił "
               "sprzeciwu co do odbycia zgromadzenia ani co do porządku obrad.",
               "Przyjęto następujący porządek obrad: 1) otwarcie zgromadzenia, 2) wybór przewodniczącego i "
               "sekretarza, 3) stwierdzenie prawidłowości zwołania, 4) podjęcie uchwał, 5) zamknięcie obrad."),
        sekcja("uchwaly", "akapit",
               "Uchwała nr 1 w sprawie udzielenia absolutorium {prezes.pelne:cel} z wykonania obowiązków "
               "Prezesa Zarządu w poprzednim roku obrotowym. Za uchwałą oddano {ctx.udzialy_suma3} głosów, przeciw – 0, "
               "wstrzymujących się – 0.",
               "Uchwała nr 2 w sprawie odwołania {w2.pelne:dop} ze składu Rady Nadzorczej z dniem podjęcia "
               "uchwały. Za uchwałą oddano {ctx.glosy_za2} głosów, przeciw – {ctx.glosy_przeciw2}.",
               "Uchwała nr 3 w sprawie powołania {nowy_czlonek.pelne:dop}, PESEL {nowy_czlonek.pesel}, "
               "adres: {nowy_czlonek.adres}, na członka Rady Nadzorczej na wspólną trzyletnią kadencję. "
               "Za uchwałą oddano {ctx.udzialy_suma3} głosów.",
               "Uchwała nr 4 w sprawie ustalenia wynagrodzenia dla {przewodniczacy.pelne:dop} za pełnienie "
               "funkcji w Radzie Nadzorczej w wysokości {ctx.wyn_mies} brutto miesięcznie.",
               "Uchwała nr 5 w sprawie podziału zysku za rok obrotowy: wspólnikom wypłaci się dywidendę w "
               "łącznej wysokości {ctx.dywidenda}, z terminem wypłaty do dnia {ctx.dok_termin_dl}.",
               "Uchwała nr 6 w sprawie zmiany umowy spółki w zakresie przedmiotu działalności (dodanie "
               "PKD 70.22.Z – pozostałe doradztwo w zakresie prowadzenia działalności gospodarczej). "
               "Uchwała wymaga formy aktu notarialnego (art. 255 k.s.h.).",
               min=4, max=6),
        sekcja("zakonczenie", "akapit",
               "Wobec wyczerpania porządku obrad {przewodniczacy.rodzaj:przewodniczący|przewodnicząca} zamyka zgromadzenie. Do protokołu nie "
               "zgłoszono sprzeciwów ani zdań odrębnych.",
               "Protokół odczytano i podpisano. Kolejne zgromadzenie zwyczajne zaplanowano na dzień "
               "{ctx.dok_pozniej}.",
               "Do protokołu dołączono listę obecności, dowody zawiadomienia wspólników oraz projekty uchwał; "
               "notariusz {notariusz.pelne} sporządza wypis aktu dla potrzeb postępowania rejestrowego."),
        sekcja("podpisy_opis", "akapit", "{przewodniczacy.rodzaj:Przewodniczący|Przewodnicząca} zgromadzenia:                 Sekretarz:"),
        sekcja("podpisy", "podpis", "{przewodniczacy.pelne}", "{sekretarz.pelne}"),
        sekcja("stopka", "stopka",
               "{spolka.nazwa} | {spolka.adres} | tel. {spolka.telefon} | {spolka.email} | REGON {spolka.regon}"),
    ],
    metadane={"author": "{sekretarz.pelne}", "subject": "Protokół zgromadzenia wspólników"},
)

#: Warstwa trudna (H6b-fix1): Prezes Zarządu – kobieta „która stwierdza”; trzon (`SZABLON`) bez zmian.
SZABLON_ZGODNA_PLEC = z_zamianami(SZABLON, {"{prezes.pelne}, Prezes Zarządu, który stwierdza":
                                            "{prezes.pelne}, Prezes Zarządu, {prezes.rodzaj:który|która} stwierdza"})
