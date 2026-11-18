"""Pozew o zapłatę wniesiony osobiście przez osobę fizyczną przeciwko osobie fizycznej (niedopłacona reszta ceny
sprzedanego samochodu) do sądu rejonowego; bez pełnomocnika, z danymi powoda, pozwanego i świadków."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="pl", typ="pozew_zaplata_osoby", warianty=("rejonowy",), dorosli=True,
    role={"powod": "osoba", "pozwany": "osoba", "swiadek": "osoba", "swiadek2": "osoba", "pojazd": "sprawa",
          "sad": "sad"},
    sekcje=[
        sekcja("naglowek", "naglowek",
               "{powod.pelne}",
               "{powod.adres}, tel. {powod.telefon}, e-mail: {powod.email}"),
        sekcja("miejscowosc", "akapit", "{powod.miasto}, dnia {ctx.pozew}"),
        sekcja("adresat", "akapit",
               "{sad.nazwa}",
               "Wydział Cywilny",
               "{powod.rodzaj:Powód|Powódka}: {powod.pelne}, PESEL {powod.pesel}, adres: {powod.adres}",
               "{pozwany.rodzaj:Pozwany|Pozwana}: {pozwany.pelne}, PESEL {pozwany.pesel}, adres: {pozwany.adres}",
               "Wartość przedmiotu sporu: {ctx.glowna}"),
        sekcja("tytul", "akapit", "POZEW O ZAPŁATĘ"),
        sekcja("zadanie", "akapit",
               "Wnoszę o:",
               "1. zasądzenie od {pozwany.rodzaj:pozwanego|pozwanej} {pozwany.pelne:dop} na rzecz {powod.rodzaj:powoda|powódki} "
               "kwoty {ctx.glowna} wraz z odsetkami ustawowymi za opóźnienie liczonymi od dnia {ctx.termin_platnosci} "
               "do dnia zapłaty;",
               "2. zasądzenie od {pozwany.rodzaj:pozwanego|pozwanej} na rzecz {powod.rodzaj:powoda|powódki} zwrotu "
               "kosztów procesu, w tym opłaty od pozwu w wysokości {ctx.oplata_pozwu};",
               "3. rozpoznanie sprawy pod nieobecność {powod.rodzaj:powoda|powódki}, jeżeli stawiennictwo okaże się "
               "niemożliwe."),
        sekcja("uzasadnienie", "akapit",
               "UZASADNIENIE",
               "W dniu {ctx.umowa} {powod.rodzaj:powód sprzedał|powódka sprzedała} {pozwany.rodzaj:pozwanemu|pozwanej} "
               "samochód osobowy o numerze rejestracyjnym {pojazd.tablica} za cenę ustaloną w umowie sprzedaży. "
               "Pojazd został wydany {pozwany.rodzaj:pozwanemu|pozwanej} w dniu zawarcia umowy.",
               "{pozwany.rodzaj:Pozwany zapłacił|Pozwana zapłaciła} jedynie część ceny; pozostała kwota {ctx.glowna} "
               "miała zostać przekazana przelewem na rachunek {powod.pelne:dop} nr {powod.rachunek} do dnia "
               "{ctx.termin_platnosci}. Termin upłynął bezskutecznie.",
               "{powod.rodzaj:Powód wezwał|Powódka wezwała} {pozwany.rodzaj:pozwanego|pozwaną} do zapłaty pismem z "
               "dnia {ctx.wezwanie} wysłanym listem poleconym na adres {pozwany.adres}, wyznaczając termin do dnia "
               "{ctx.termin_wezwania}. Wezwanie pozostało bez odpowiedzi.",
               "Podstawę żądania stanowi art. 535 § 1 Kodeksu cywilnego, a odsetki za opóźnienie art. 481 § 1 i 2 k.c. "
               "w związku z art. 455 k.c.",
               min=3, max=4),
        sekcja("wlasciwosc", "akapit",
               "Sąd jest właściwy rzeczowo na podstawie art. 16 § 1 pkt 1 k.p.c., a miejscowo na podstawie art. 27 "
               "§ 1 k.p.c. jako sąd miejsca zamieszkania {pozwany.rodzaj:pozwanego|pozwanej}. {powod.rodzaj:Powód "
               "nie korzysta|Powódka nie korzysta} z pomocy pełnomocnika i działa osobiście."),
        sekcja("dowody", "akapit",
               "Na powyższe okoliczności wnoszę o przeprowadzenie dowodów:",
               "1. z umowy sprzedaży z dnia {ctx.umowa} – na okoliczność ustalenia ceny i terminu jej zapłaty;",
               "2. z wyciągu z rachunku {powod.rachunek} – na okoliczność braku wpłaty brakującej części ceny;",
               "3. z zeznań świadka {swiadek.pelne:dop}, adres: {swiadek.adres} – na okoliczność przebiegu "
               "transakcji i wydania pojazdu;",
               "4. z zeznań świadka {swiadek2.pelne:dop}, tel. {swiadek2.telefon} – na okoliczność uznania długu "
               "przez {pozwany.rodzaj:pozwanego|pozwaną} {pozwany.pelne:dop};",
               "5. z przesłuchania stron.",
               min=3, max=5),
        sekcja("zalaczniki", "akapit",
               "Załączniki:",
               "1. odpis pozwu wraz z załącznikami,",
               "2. dowód uiszczenia opłaty od pozwu w wysokości {ctx.oplata_pozwu},",
               "3. odpis wezwania do zapłaty wraz z potwierdzeniem nadania."),
        sekcja("podpis", "podpis", "{powod.pelne}"),
        sekcja("stopka", "stopka",
               "{powod.pelne} | {powod.adres} | tel. {powod.telefon} | {powod.email}"),
        sekcja("uwaga", "przypis",
               "Powód oświadcza, że nie korzysta ze zwolnienia od kosztów sądowych, a opłatę od pozwu uiścił "
               "przelewem z rachunku {powod.rachunek}."),
    ],
    metadane={"author": "{powod.pelne}", "subject": "Pozew o zapłatę"},
)
