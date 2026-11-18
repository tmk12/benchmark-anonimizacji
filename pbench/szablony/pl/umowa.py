"""Umowa o stałą obsługę prawną (kancelaria – spółka klienta), z klauzulami typowymi dla polskiego obrotu."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="pl", typ="umowa", dorosli=True,
    role={"kancelaria": "kancelaria", "klient": "firma", "partner": "osoba", "prezes": "osoba", "opiekun": "osoba",
          "koordynator": "osoba", "zastepca": "osoba", },
    sekcje=[
        sekcja("naglowek", "naglowek",
               "{kancelaria.nazwa}",
               "{kancelaria.adres} | NIP {kancelaria.nip} | KRS {kancelaria.krs}"),
        sekcja("tytul", "akapit",
               "UMOWA O STAŁĄ OBSŁUGĘ PRAWNĄ",
               "zawarta w dniu {ctx.dok} (miejsce zawarcia: {kancelaria.miasto}) pomiędzy:"),
        sekcja("strony", "akapit",
               "{kancelaria.nazwa} z siedzibą: {kancelaria.adres}, wpisaną do rejestru przedsiębiorców Krajowego "
               "Rejestru Sądowego pod numerem KRS {kancelaria.krs}, NIP {kancelaria.nip}, REGON {kancelaria.regon}, "
               "reprezentowaną przez {partner.pelne:bier} – wspólnika, zwaną dalej „Kancelarią”,",
               "a",
               "{klient.nazwa} z siedzibą: {klient.adres}, wpisaną do rejestru przedsiębiorców Krajowego Rejestru "
               "Sądowego pod numerem KRS {klient.krs}, NIP {klient.nip}, REGON {klient.regon}, reprezentowaną "
               "przez {prezes.pelne:bier} – Prezesa Zarządu, zwaną dalej „Klientem”,",
               "zwanymi dalej łącznie „Stronami”, a każda z osobna „Stroną”, o następującej treści:"),
        sekcja("przedmiot", "akapit",
               "§ 1. Przedmiot umowy",
               "1. Kancelaria zobowiązuje się do świadczenia na rzecz Klienta stałej obsługi prawnej w zakresie "
               "prawa cywilnego i handlowego, prawa pracy oraz ochrony danych osobowych, w szczególności do "
               "sporządzania i opiniowania projektów umów, przygotowywania opinii prawnych oraz udziału w "
               "negocjacjach prowadzonych przez Klienta.",
               "2. Obsługa nie obejmuje zastępstwa procesowego przed sądami powszechnymi, sądami administracyjnymi "
               "i organami administracji publicznej; w takim przypadku Strony ustalą odrębnie zakres "
               "pełnomocnictwa i wynagrodzenie.",
               "3. Opiekunem Klienta ze strony Kancelarii jest {opiekun.pelne}, a w razie jego nieobecności "
               "zastępstwo przejmuje {zastepca.pelne}. Zmiana opiekuna nie wymaga aneksu do umowy.",
               "4. Uwagi do sposobu wykonywania umowy Klient kieruje do {opiekun.pelne:dop}, a w sprawach "
               "spornych do {partner.pelne:dop} jako wspólnika odpowiedzialnego za relację z Klientem."),
        sekcja("wykonanie", "akapit",
               "§ 2. Sposób wykonywania umowy",
               "1. Kancelaria wykonuje umowę z należytą starannością, uwzględniając zawodowy charakter swojej "
               "działalności, w terminach uzgodnionych z Klientem, a w sprawach pilnych – w ciągu dwóch dni "
               "roboczych od otrzymania kompletu dokumentów.",
               "2. Klient przekazuje Kancelarii informacje i dokumenty niezbędne do wykonania zlecenia za "
               "pośrednictwem osoby wskazanej przez Zarząd, którą jest {koordynator.pelne} (tel. "
               "{koordynator.telefon}, e-mail: {koordynator.email}).",
               "3. Opinie prawne i projekty dokumentów są przekazywane w formie elektronicznej, chyba że Klient "
               "zażąda formy pisemnej."),
        sekcja("wynagrodzenie", "akapit",
               "§ 3. Wynagrodzenie",
               "1. Z tytułu obsługi Klient zapłaci Kancelarii miesięczne wynagrodzenie ryczałtowe w wysokości "
               "{ctx.um_wyn} netto, powiększone o podatek od towarów i usług według stawki obowiązującej "
               "w dniu wystawienia faktury.",
               "2. Ryczałt obejmuje do 20 godzin pracy prawników w miesiącu. Czas pracy ponad ten limit rozlicza "
               "się według stawki godzinowej, a łączna wartość czynności ponad limit w danym miesiącu nie może "
               "przekroczyć {ctx.um_limit} bez uprzedniej zgody Klienta.",
               "3. Wynagrodzenie płatne jest z dołu, w terminie 14 dni od doręczenia faktury, przelewem na "
               "rachunek Kancelarii nr {kancelaria.rachunek}."),
        sekcja("czas", "akapit",
               "§ 4. Czas obowiązywania i wypowiedzenie",
               "1. Umowa wchodzi w życie z dniem {ctx.od_dnia} i zostaje zawarta na czas nieokreślony.",
               "2. Każda ze Stron może wypowiedzieć umowę z zachowaniem trzymiesięcznego okresu wypowiedzenia "
               "ze skutkiem na koniec miesiąca kalendarzowego. Wypowiedzenie wymaga formy pisemnej pod "
               "rygorem nieważności."),
        sekcja("dodatkowe", "akapit",
               "§ 5. Poufność. 1. Kancelaria zachowuje w tajemnicy wszelkie informacje uzyskane w związku ze świadczeniem "
               "obsługi, zgodnie z obowiązkami wynikającymi z ustawy z dnia 6 lipca 1982 r. o radcach prawnych "
               "oraz ustawy z dnia 26 maja 1982 r. – Prawo o adwokaturze. Obowiązek ten trwa także po "
               "rozwiązaniu umowy.",
               "2. Za naruszenie obowiązku poufności Strona zapłaci drugiej Stronie karę umowną w wysokości "
               "{ctx.um_kara}, bez uszczerbku dla prawa dochodzenia odszkodowania przewyższającego karę na "
               "zasadach ogólnych (art. 484 § 1 Kodeksu cywilnego).",
               "§ 6. Ochrona danych osobowych. Kancelaria przetwarza dane osobowe powierzone przez Klienta wyłącznie w celu wykonania umowy i "
               "zgodnie z rozporządzeniem Parlamentu Europejskiego i Rady (UE) 2016/679 z dnia 27 kwietnia "
               "2016 r. (RODO). Strony zawrą odrębną umowę powierzenia przetwarzania, o której mowa w art. 28 "
               "RODO, jeżeli przedmiot zlecenia będzie tego wymagał.",
               "§ 7. Odpowiedzialność. Odpowiedzialność Kancelarii jest objęta obowiązkowym ubezpieczeniem odpowiedzialności "
               "cywilnej, a jej wysokość ogranicza się do sumy gwarancyjnej wynikającej z tego ubezpieczenia, "
               "z wyłączeniem szkód wyrządzonych umyślnie. Kancelaria nie odpowiada za skutki decyzji "
               "biznesowych Klienta podjętych wbrew jej pisemnym zastrzeżeniom.",
               ),
        sekcja("koncowe", "akapit",
               "§ 8. Doręczenia",
               "Korespondencję do Klienta doręcza się na adres {klient.adres} lub na adres poczty elektronicznej "
               "{klient.email}, a do Kancelarii – na adres {kancelaria.adres} lub {kancelaria.email}. "
               "Zmiana adresu wymaga pisemnego powiadomienia drugiej Strony.",
               "§ 9. Postanowienia końcowe",
               "1. Zmiany umowy wymagają formy pisemnej pod rygorem nieważności.",
               "2. W sprawach nieuregulowanych umową stosuje się przepisy Kodeksu cywilnego, w tym przepisy o "
               "zleceniu. Spory wynikające z umowy rozstrzyga sąd powszechny właściwy dla siedziby Kancelarii.",
               "3. Umowę sporządzono w dwóch jednobrzmiących egzemplarzach, po jednym dla każdej ze Stron."),
        sekcja("zmiany", "zmiany",
               "ins | {opiekun.pelne} | Dodano zdanie o dwudniowym terminie na opinie w sprawach pilnych.",
               "del | {zastepca.pelne} | Wyłączono wcześniejszy zapis o rozliczaniu czasu pracy w kwartałach.",
               min=0, max=2),
        sekcja("podpisy_opis", "akapit", "Za Kancelarię:                                                  Za Klienta:"),
        sekcja("podpisy", "podpis", "{partner.pelne}", "{prezes.pelne}"),
        sekcja("stopka", "stopka",
               "{kancelaria.nazwa}, {kancelaria.adres} | tel. {kancelaria.telefon} | {kancelaria.email} | "
               "NIP {kancelaria.nip}"),
    ],
    metadane={"author": "{opiekun.pelne}", "title": "Umowa o stałą obsługę prawną"},
)
