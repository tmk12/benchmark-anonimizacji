"""Notatka służbowa prawnika z rozmowy z klientem (sprawa o szkodę komunikacyjną i roszczenia wobec ubezpieczyciela)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja, z_zamianami

SZABLON = Szablon(
    jezyk="pl", typ="notatka", warianty=("rejonowy", "okregowy"),
    role={"kancelaria": "kancelaria", "autor": "osoba", "klient": "osoba", "przeciwnik": "osoba",
          "swiadek": "osoba", "ubezpieczyciel": "firma", "sprawa": "sprawa", "pojazd": "sprawa",
          "sad": "sad"},
    sekcje=[
        sekcja("naglowek", "naglowek",
               "{kancelaria.nazwa}",
               "NOTATKA SŁUŻBOWA – POUFNE (tajemnica adwokacka / radcowska)"),
        sekcja("dane", "akapit",
               "Data sporządzenia: {ctx.przed_rozprawa}",
               "Sporządził: {autor.pelne}, tel. wewn. {autor.telefon}",
               "Dotyczy: rozmowy z {klient.pelne:narz} w sprawie szkody komunikacyjnej, sygn. akt {sprawa.sygnatura}"),
        sekcja("klient", "akapit",
               "Dane {klient.rodzaj:klienta|klientki}: {klient.pelne}, PESEL {klient.pesel}, adres: {klient.adres}, tel. {klient.telefon}, "
               "e-mail: {klient.email}. {klient.rodzaj:Klient|Klientka} preferuje kontakt mailowy w godzinach 8–16.",
               "Dane do logowania do portalu informacyjnego sądów: login {klient.login}. Hasło {klient.rodzaj:klient|klientka} "
               "przekaże osobiście; nie zapisywać go w aktach."),
        sekcja("stan", "akapit",
               "1. Stan faktyczny. Do zdarzenia doszło na skrzyżowaniu, w wyniku niezachowania pierwszeństwa "
               "przejazdu przez kierującego pojazdem o numerze rejestracyjnym {pojazd.tablica}. Sprawcą "
               "kolizji jest {przeciwnik.pelne}, adres: {przeciwnik.adres}.",
               "2. Szkoda. Według wstępnej kalkulacji warsztatu szkoda w pojeździe {klient.rodzaj:klienta|klientki} wynosi {ctx.szkoda}. "
               "Ubezpieczyciel sprawcy, {ubezpieczyciel.nazwa}, wypłacił dotychczas zaliczkę w kwocie "
               "{ctx.zaliczka_ub}, uznając odpowiedzialność jedynie częściowo.",
               "3. Świadkowie. Zdarzenie obserwował {swiadek.pelne}, tel. {swiadek.telefon}; {klient.rodzaj:klient|klientka} deklaruje "
               "gotowość świadka do złożenia zeznań, wymaga jednak potwierdzenia."),
        sekcja("ustalenia", "akapit",
               "Ustalenia: kancelaria przygotuje reklamację do ubezpieczyciela ({ubezpieczyciel.nazwa}) oraz "
               "wezwanie do zapłaty adresowane do {przeciwnik.pelne:dop}, jeżeli ubezpieczyciel nie zmieni stanowiska do dnia "
               "{ctx.notatka_termin}.",
               "{klient.rodzaj:Klient|Klientka} przekaże do końca tygodnia: dowód rejestracyjny, polisę OC sprawcy, zdjęcia z miejsca "
               "zdarzenia, kosztorys naprawy i dokumenty z Policji. Oryginały pozostają u {klient.rodzaj:klienta|klientki}.",
               "Do rozważenia: powództwo przeciwko ubezpieczycielowi na podstawie art. 822 Kodeksu cywilnego "
               "oraz ustawy z dnia 22 maja 2003 r. o ubezpieczeniach obowiązkowych, Ubezpieczeniowym Funduszu "
               "Gwarancyjnym i Polskim Biurze Ubezpieczycieli Komunikacyjnych. Roszczenie przedawnia się z "
               "upływem trzech lat od dnia, w którym poszkodowany dowiedział się o szkodzie (art. 442^1 k.c.).",
               "Termin najbliższej rozprawy wyznaczono na dzień {ctx.rozprawa}; sprawa toczy się w sądzie: "
               "{sad.nazwa}. Obecność {klient.rodzaj:klienta|klientki} jest obowiązkowa."),
        sekcja("zadania", "akapit",
               "Zadania: sporządzenie reklamacji według wytycznych {autor.pelne:dop}; sekretariat – założenie teczki i wpis terminów "
               "do kalendarza; {klient.rodzaj:klient|klientka} – dostarczenie dokumentów.",
               "Wynagrodzenie kancelarii: stawka godzinowa, zaliczka pobrana przy podpisaniu umowy zlecenia. "
               "Kolejna rozmowa po upływie terminu odpowiedzi ubezpieczyciela."),
        sekcja("przypisy", "przypis",
               "Podstawa prawna czynności: art. 6 Kodeksu cywilnego (ciężar dowodu), art. 361 § 2 k.c. "
               "(zakres odszkodowania).",
               "Notatka podlega przechowywaniu przez okres wymagany przepisami o wykonywaniu zawodu."),
        sekcja("komentarze", "komentarz",
               "{klient.pelne} | Proszę uzupełnić datę kolizji – w mojej dokumentacji jest 3 dni wcześniej.",
               "{autor.pelne} | Sprawdzone z kartą pojazdu; zgodne z numerem {pojazd.tablica}.",
               min=0, max=2),
        sekcja("podpis", "podpis", "{autor.pelne}"),
        sekcja("stopka", "stopka",
               "{kancelaria.nazwa} | {kancelaria.adres} | tel. {kancelaria.telefon} | {kancelaria.email}"),
    ],
    metadane={"author": "{autor.pelne}", "subject": "Notatka z rozmowy z klientem"},
)
#: Wariant warstwy trudnej (`szablony.SZABLONY_TRUDNE`): czasownik podpisu zgodny z płcią autora.
SZABLON_ZGODNA_PLEC = z_zamianami(SZABLON, {"Sporządził: {autor.pelne}": "{autor.rodzaj:Sporządził|Sporządziła}: {autor.pelne}"})
