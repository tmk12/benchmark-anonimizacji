"""Karta informacyjna z leczenia szpitalnego (wypis): dane pacjenta, rozpoznania ICD-10, przebieg, zalecenia."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="pl", typ="med_wypis",
    profil="kardiologia",
    role={"szpital": "placowka", "pacjent": "pacjent", "lekarz": "lekarz", "ordynator": "lekarz", "rodzina": "osoba",
          },
    sekcje=[
        sekcja("naglowek", "naglowek",
               "{szpital.nazwa}",
               "{szpital.adres} | REGON {szpital.regon} | tel. {szpital.telefon}"),
        sekcja("tytul", "akapit",
               "KARTA INFORMACYJNA LECZENIA SZPITALNEGO",
               "Oddział Chorób Wewnętrznych i Kardiologii"),
        sekcja("pacjent", "akapit",
               "{pacjent.rodzaj:Pacjent|Pacjentka}: {pacjent.pelne}, PESEL {pacjent.pesel}, data urodzenia {pacjent.data_ur}",
               "Adres zamieszkania: {pacjent.adres}, tel. {pacjent.telefon}",
               "Data przyjęcia: {ctx.przyjecie}. Data wypisu: {ctx.wypis}. Tryb przyjęcia: nagły."),
        sekcja("rozpoznania", "akapit",
               "Rozpoznanie zasadnicze: {pacjent.diagnoza}",
               "Rozpoznania współistniejące: {pacjent.diagnoza2}; {pacjent.diagnoza3}",
               min=2, max=2),
        sekcja("wywiad", "akapit",
               "Wywiad i badanie przy przyjęciu: przyjęto z powodu narastającej duszności wysiłkowej, bólów w "
               "klatce piersiowej i obrzęków kończyn dolnych. W badaniu przedmiotowym stwierdzono tachykardię, "
               "szmery oddechowe pęcherzykowe z trzeszczeniami u podstawy płuc, ciśnienie tętnicze 165/95 "
               "mmHg, saturacja 93% przy oddychaniu powietrzem atmosferycznym.",
               "Badania dodatkowe: morfologia z rozmazem, CRP, kreatynina, jonogram, troponina hs, NT-proBNP, "
               "badanie ogólne moczu, EKG, RTG klatki piersiowej, echokardiografia przezklatkowa. Wyniki "
               "szczegółowe w załączniku do dokumentacji medycznej.",
               "Przebieg leczenia: włączono tlenoterapię bierną, diuretyki pętlowe dożylnie, leki "
               "przeciwkrzepliwe w dawkach profilaktycznych i leczenie hipotensyjne. Stan kliniczny uległ "
               "poprawie, ustąpiły obrzęki, uzyskano stabilizację ciśnienia tętniczego.",
               "W trakcie hospitalizacji nie obserwowano powikłań ani zdarzeń niepożądanych leczenia. Wykonano "
               "konsultacje diabetologiczną i kardiologiczną."),
        sekcja("zalecenia", "akapit",
               "Zalecenia: dieta niskosodowa, ograniczenie płynów do 1,5 l na dobę, kontrola masy ciała "
               "codziennie rano, unikanie wysiłków fizycznych przez dwa tygodnie, całkowity zakaz palenia "
               "tytoniu.",
               "Zalecane leki: {pacjent.lek} – według schematu ustalonego w poradni; {pacjent.lek2} – raz dziennie "
               "rano; {pacjent.lek3} – według zaleceń kardiologa.",
               "Kontrola w poradni kardiologicznej w dniu {ctx.kontrola}, z wynikami badań laboratoryjnych "
               "(morfologia, kreatynina, potas). Dokumentację należy zabrać na wizytę.",
               "Zaświadczenie lekarskie o czasowej niezdolności do pracy (e-ZLA) wystawiono do dnia "
               "{ctx.zwolnienie_do} włącznie.",
               min=4, max=4),
        sekcja("informacje", "akapit",
               "Informację o stanie zdrowia i planowanym leczeniu przekazano {pacjent.pelne:cel} w dniu "
               "wypisu; za zgodą {pacjent.rodzaj:pacjenta|pacjentki} informacje o stanie zdrowia mogą być udzielane {rodzina.pelne:cel}, "
               "tel. {rodzina.telefon}.",
               "Wypis sporządzono zgodnie z rozporządzeniem Ministra Zdrowia w sprawie rodzajów, zakresu i "
               "wzorów dokumentacji medycznej oraz sposobu jej przetwarzania. Dokument zawiera dane dotyczące "
               "zdrowia i podlega szczególnej ochronie na podstawie art. 9 RODO.",
               "{pacjent.rodzaj:Pacjent został pouczony|Pacjentka została pouczona} o objawach, przy których należy bezzwłocznie zgłosić się do szpitalnego "
               "oddziału ratunkowego lub wezwać pogotowie ratunkowe (numer 112 lub 999)."),
        sekcja("lekarze", "akapit",
               "Lekarz prowadzący: {lekarz.pelne}, nr PWZ {lekarz.pwz}",
               "Ordynator oddziału: {ordynator.pelne}, nr PWZ {ordynator.pwz}"),
        sekcja("podpisy", "podpis", "{lekarz.pelne}", "{ordynator.pelne}"),
        sekcja("stopka", "stopka", "{szpital.nazwa} | {szpital.adres} | tel. {szpital.telefon} | {szpital.email}"),
    ],
    metadane={"author": "{lekarz.pelne}", "subject": "Karta informacyjna leczenia szpitalnego"},
)
