"""Umowa zlecenia (tłumaczenia) z wykonawcą z Ukrainy: imię i nazwisko, adres i identyfikatory w cyrylicy i transliteracji."""
from __future__ import annotations

from ....budowa import Szablon
from ..._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="pl", typ="umowa", dorosli=True, znacz_encje=True, warianty=("cw", "tr"),
    role={"zleceniodawca": "firma", "reprezentant": "osoba", "wykonawca": "osoba_ua", "opiekun": "osoba"},
    sekcje=[
        sekcja("naglowek", "naglowek",
               "{zleceniodawca.nazwa}",
               "{zleceniodawca.adres} | NIP {zleceniodawca.nip} | KRS {zleceniodawca.krs}"),
        sekcja("tytul", "akapit",
               "UMOWA ZLECENIA",
               "zawarta w dniu {ctx.dok} pomiędzy:"),
        sekcja("strony", "akapit",
               "{zleceniodawca.nazwa} z siedzibą: {zleceniodawca.adres}, NIP {zleceniodawca.nip}, REGON "
               "{zleceniodawca.regon}, reprezentowaną przez {reprezentant.pelne:bier} – Prezesa Zarządu, zwaną "
               "dalej „Zleceniodawcą”,",
               "a",
               "{wykonawca.pelne_im:t_s1} ({wykonawca.pelne_im:t_s2}), {wykonawca.rodzaj:obywatelem|obywatelką} "
               "Ukrainy, ur. {wykonawca.data_ur}, {wykonawca.rodzaj:zamieszkałym|zamieszkałą}: "
               "{wykonawca.adres:t_s1} ({wykonawca.adres:t_s2}), {wykonawca.rodzaj:posiadającym|posiadającą} numer "
               "identyfikacji podatkowej РНОКПП {wykonawca.rnokpp} oraz paszport zagraniczny nr "
               "{wykonawca.paszport}, zwanym dalej „Zleceniobiorcą”,",
               "o następującej treści:"),
        sekcja("przedmiot", "akapit",
               "§ 1. Przedmiot umowy",
               "1. Zleceniobiorca zobowiązuje się do wykonywania na rzecz Zleceniodawcy tłumaczeń dokumentów "
               "handlowych z języka ukraińskiego na język polski i odwrotnie oraz do udziału w rozmowach z "
               "kontrahentami z Ukrainy.",
               "2. Zleceniobiorca wykonuje zlecenie osobiście; zastępstwo wymaga pisemnej zgody Zleceniodawcy. "
               "Osobą odpowiedzialną za nadzór nad wykonaniem zlecenia po stronie Zleceniodawcy jest "
               "{opiekun.pelne}."),
        sekcja("wynagrodzenie", "akapit",
               "§ 2. Wynagrodzenie",
               "1. Za wykonanie zlecenia Zleceniobiorca otrzyma miesięczne wynagrodzenie w wysokości {ctx.um_wyn} "
               "brutto, płatne w terminie 14 dni od dnia przedłożenia rachunku.",
               "2. Wynagrodzenie będzie przekazywane przelewem na rachunek Zleceniobiorcy IBAN "
               "{wykonawca.rachunek}.",
               "3. Dane kontaktowe Zleceniobiorcy: tel. {wykonawca.telefon}, e-mail {wykonawca.email}."),
        sekcja("oswiadczenia", "akapit",
               "§ 3. Oświadczenia",
               "1. Zleceniobiorca, jako {wykonawca.rodzaj:obywatel|obywatelka} Ukrainy, przedłoży Zleceniodawcy "
               "dokument potwierdzający legalność pobytu i wykonywania pracy na terytorium Rzeczypospolitej "
               "Polskiej oraz zgłosi się do ubezpieczeń społecznych na zasadach ogólnych.",
               W("tr", "2. Zleceniobiorca oświadcza, że jego dane identyfikacyjne są zgodne z dokumentem tożsamości, "
                       "a imię i nazwisko mogą występować w dokumentach także w zapisach: {wykonawca.pelne_im:t_s2}, "
                       "{wykonawca.pelne_im:t_s3} oraz {wykonawca.pelne_im:t_s4}; wszystkie dotyczą tej samej osoby.")),
        sekcja("rodo", "akapit",
               "§ 4. Dane osobowe. Zleceniodawca przetwarza dane osobowe Zleceniobiorcy w celu zawarcia i "
               "wykonania umowy, zgodnie z art. 6 ust. 1 lit. b rozporządzenia (UE) 2016/679 (RODO). Dane, w tym "
               "numer РНОКПП {wykonawca.rnokpp}, będą przechowywane przez okres przedawnienia roszczeń."),
        sekcja("podpis_opis", "akapit", "Podpis Zleceniobiorcy:"),
        sekcja("podpis", "podpis", "{wykonawca.pelne_im:t_s1}"),
        sekcja("stopka", "stopka", "{zleceniodawca.nazwa}, {zleceniodawca.adres} | {zleceniodawca.email}"),
    ],
    metadane={"author": "{reprezentant.pelne}", "subject": "Umowa zlecenia"},
)
