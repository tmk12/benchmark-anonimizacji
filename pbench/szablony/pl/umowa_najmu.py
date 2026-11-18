"""Umowa najmu lokalu mieszkalnego zawarta między osobami fizycznymi (wynajmujący – najemca), z kaucją, protokołem
zdawczo-odbiorczym i danymi kontaktowymi. Lokal jest identyfikowany adresem (adres dotychczasowego najemcy to adres
lokalu); kaucja równa jednomiesięcznemu czynszowi."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="pl", typ="umowa_najmu", dorosli=True,
    role={"wynajmujacy": "osoba", "najemca": "osoba", "lokal": "osoba", "swiadek": "osoba"},
    sekcje=[
        sekcja("naglowek", "naglowek",
               "UMOWA NAJMU LOKALU MIESZKALNEGO",
               "Egzemplarz {wynajmujacy.rodzaj:Wynajmującego|Wynajmującej} – {wynajmujacy.pelne}"),
        sekcja("tytul", "akapit",
               "zawarta w dniu {ctx.dok} w miejscowości {wynajmujacy.miasto} pomiędzy:"),
        sekcja("strony", "akapit",
               "{wynajmujacy.pelne}, PESEL {wynajmujacy.pesel}, legitymującym się dowodem osobistym "
               "{wynajmujacy.dowod}, {wynajmujacy.rodzaj:zamieszkałym|zamieszkałą} pod adresem: {wynajmujacy.adres}, "
               "tel. {wynajmujacy.telefon}, e-mail: {wynajmujacy.email}, zwanym dalej „Wynajmującym”,",
               "a",
               "{najemca.pelne}, PESEL {najemca.pesel}, legitymującym się dowodem osobistym {najemca.dowod}, "
               "{najemca.rodzaj:zamieszkałym|zamieszkałą} pod adresem: {najemca.adres}, tel. {najemca.telefon}, "
               "e-mail: {najemca.email}, zwanym dalej „Najemcą”,",
               "zwanymi dalej łącznie „Stronami”, o następującej treści:"),
        sekcja("przedmiot", "akapit",
               "§ 1. Przedmiot najmu",
               "1. Wynajmujący oświadcza, że jest właścicielem lokalu mieszkalnego położonego pod adresem {lokal.adres}, "
               "wraz z piwnicą i miejscem postojowym, zwanego dalej „Lokalem”, który do dnia {ctx.umowa_dawna} "
               "zajmował {lokal.pelne}.",
               "2. Wynajmujący oddaje Najemcy Lokal do używania wyłącznie na cele mieszkalne, a Najemca przyjmuje "
               "Lokal w najem na warunkach określonych w umowie.",
               "3. Lokal zostanie wydany w dniu {ctx.od_dnia} na podstawie protokołu zdawczo-odbiorczego, w którym "
               "spisze się stan liczników oraz wyposażenia; w odbiorze uczestniczy {swiadek.pelne} jako osoba "
               "zaufana Wynajmującego (tel. {swiadek.telefon})."),
        sekcja("czynsz", "akapit",
               "§ 2. Czynsz i kaucja",
               "1. Najemca płaci Wynajmującemu miesięczny czynsz najmu w wysokości {ctx.zaliczka_kosztow}, płatny "
               "z góry do dziesiątego dnia każdego miesiąca przelewem na rachunek Wynajmującego nr "
               "{wynajmujacy.rachunek}.",
               "2. Opłaty za media (energia elektryczna, woda, ogrzewanie, internet) Najemca ponosi według zużycia "
               "bezpośrednio na rzecz dostawców; opłaty administracyjne wspólnoty pokrywa Wynajmujący.",
               "3. Przy wydaniu Lokalu Najemca wpłaca kaucję zabezpieczającą w wysokości {ctx.zaliczka_kosztow} "
               "(równowartość miesięcznego czynszu), którą Wynajmujący zwróci w terminie 14 dni od zwrotu Lokalu, "
               "po potrąceniu ewentualnych należności z tytułu zniszczeń i zaległości."),
        sekcja("czas", "akapit",
               "§ 3. Czas trwania najmu",
               "1. Umowa zostaje zawarta na czas oznaczony od dnia {ctx.od_dnia} do dnia {ctx.dok_pozniej}.",
               "2. Każda ze Stron może wypowiedzieć umowę z zachowaniem miesięcznego okresu wypowiedzenia na koniec "
               "miesiąca kalendarzowego, jeżeli Najemca zalega z czynszem za co najmniej dwa pełne okresy "
               "płatności lub używa Lokalu w sposób sprzeczny z umową."),
        sekcja("prawa", "akapit",
               "§ 4. Prawa i obowiązki",
               "1. Najemca utrzymuje Lokal w stanie niepogorszonym, dokonuje na swój koszt drobnych napraw "
               "bieżących i nie może podnajmować Lokalu ani zmieniać jego przeznaczenia bez pisemnej zgody "
               "Wynajmującego.",
               "2. Wynajmujący ma prawo wejść do Lokalu w obecności Najemcy po uprzednim powiadomieniu go z "
               "co najmniej dwudniowym wyprzedzeniem, a w razie awarii – niezwłocznie.",
               "3. Najemca zamieszkuje w Lokalu wraz z osobami, o których poinformuje Wynajmującego na piśmie; "
               "zameldowanie Najemcy w Lokalu wymaga odrębnej zgody Wynajmującego.",
               min=2, max=3),
        sekcja("zasady", "komorka",
               "Pozycja | Stan przy wydaniu | Uwagi\n"
               "Licznik energii elektrycznej | 04 213 kWh | odczyt w obecności Stron\n"
               "Licznik wody zimnej | 118 m3 | bez uwag\n"
               "Klucze | 3 kpl. | przekazane {najemca.pelne}",
               "Pozycja | Termin | Odpowiedzialny\n"
               "Zapłata czynszu | do 10. dnia miesiąca | {najemca.pelne}\n"
               "Zwrot kaucji | 14 dni od zwrotu Lokalu | {wynajmujacy.pelne}\n"
               "Odbiór Lokalu | {ctx.od_dnia} | {swiadek.pelne}",
               min=1, max=1),
        sekcja("koncowe", "akapit",
               "§ 5. Postanowienia końcowe",
               "1. Wszelkie zmiany umowy wymagają formy pisemnej pod rygorem nieważności.",
               "2. Korespondencję Strony doręczają na adresy wskazane w komparycji, a zmianę adresu zgłaszają "
               "niezwłocznie drugiej Stronie; do kontaktów bieżących służą numery {wynajmujacy.telefon} oraz "
               "{najemca.telefon}.",
               "3. W sprawach nieuregulowanych umową stosuje się przepisy Kodeksu cywilnego (art. 659 i nast.) "
               "oraz ustawy z dnia 21 czerwca 2001 r. o ochronie praw lokatorów, mieszkaniowym zasobie gminy "
               "i o zmianie Kodeksu cywilnego.",
               "4. Umowę sporządzono w dwóch jednobrzmiących egzemplarzach, po jednym dla każdej ze Stron."),
        sekcja("podpisy_opis", "akapit", "Wynajmujący:                                                  Najemca:"),
        sekcja("podpisy", "podpis", "{wynajmujacy.pelne}", "{najemca.pelne}"),
        sekcja("stopka", "stopka",
               "Umowa najmu – {wynajmujacy.pelne} / {najemca.pelne} | lokal: {lokal.adres}"),
        sekcja("uwaga", "przypis",
               "Najem okazjonalny nie został zastrzeżony; do umowy dołączono kopię aktu własności lokalu "
               "i oświadczenie {wynajmujacy.pelne:dop} o braku obciążeń uniemożliwiających wydanie Lokalu."),
    ],
    metadane={"author": "{wynajmujacy.pelne}", "title": "Umowa najmu lokalu mieszkalnego"},
)
