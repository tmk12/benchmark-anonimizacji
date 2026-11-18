"""Prezentacja kancelarii dla zarządu klienta: wyniki badania prawnego spółki (krótkie slajdy, tabela ryzyk)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja, z_zamianami

SZABLON = Szablon(
    jezyk="pl", typ="prezentacja",
    role={"kancelaria": "kancelaria", "prelegent": "osoba", "kontakt": "osoba", "prezes": "osoba",
          "cel": "firma", "klient": "firma", "strona": "sprawa"},
    sekcje=[
        sekcja("tytuly", "naglowek",
               "Badanie prawne spółki {cel.nazwa}",
               "Wyniki analizy due diligence",
               "Najważniejsze ryzyka transakcji",
               "Plan działań do zamknięcia transakcji",
               "Kontakt i kolejne kroki"),
        sekcja("slajd1", "akapit",
               "Prelegent: {prelegent.pelne}, {kancelaria.nazwa}",
               "Spotkanie z zarządem {klient.nazwa} w dniu {ctx.dok}",
               "Materiał poufny – wyłącznie dla zarządu"),
        sekcja("slajd2", "akapit",
               "Badana spółka: {cel.nazwa}, siedziba: {cel.adres}",
               "KRS {cel.krs}, NIP {cel.nip}, REGON {cel.regon}",
               "Rozmowy prowadzono z Prezesem Zarządu, {prezes.pelne:narz}",
               "Cena nabycia udziałów: {ctx.cena}"),
        sekcja("slajd3", "akapit",
               "Umowy kluczowych kontrahentów zawierają klauzule zmiany kontroli",
               "Brak aktualnego rejestru czynności przetwarzania danych (art. 30 RODO)",
               "Spory sądowe: trzy postępowania o łącznej wartości {ctx.sporow}",
               "Licencje oprogramowania bez potwierdzenia chain of title",
               "Zaległości w składkach ZUS nie stwierdzono",
               min=3, max=5),
        sekcja("tabela_ryzyk", "komorka",
               "Obszar | Ocena | Rekomendacja\n"
               "Prawo pracy | średnie | Uporządkować regulaminy wynagradzania\n"
               "Ochrona danych | wysokie | Wdrożyć rejestr i umowy powierzenia\n"
               "Nieruchomości | niskie | Brak działań\n"
               "Własność intelektualna | wysokie | Cesje praw autorskich od współpracowników"),
        sekcja("slajd4", "akapit",
               "Podpisanie umowy sprzedaży udziałów: do dnia {ctx.dok_termin_dl}",
               "Warunki zawieszające: zgoda wspólników, zgoda banku finansującego",
               "Zamknięcie transakcji wymaga zgody {prezes.pelne:dop} jako Prezesa Zarządu spółki",
               "Obowiązek zgłoszenia koncentracji do Prezesa UOKiK sprawdzamy według progów z art. 13 ustawy "
               "o ochronie konkurencji i konsumentów"),
        sekcja("slajd5", "akapit",
               "Kontakt: {kontakt.pelne}, tel. {kontakt.telefon}, e-mail {kontakt.email}",
               "Strona kancelarii: {strona.url}",
               "Dziękujemy za uwagę"),
        sekcja("stopka", "stopka", "{kancelaria.nazwa} – materiał poufny"),
    ],
    metadane={"author": "{prelegent.pelne}", "subject": "Badanie prawne spółki"},
)
#: Wariant warstwy trudnej (`szablony.SZABLONY_TRUDNE`): funkcja prezesa zgodna z jego płcią („z Prezes Zarządu, Anną …”).
SZABLON_ZGODNA_PLEC = z_zamianami(SZABLON, {"z Prezesem Zarządu, {prezes.pelne:narz}":
                                            "z {prezes.rodzaj:Prezesem|Prezes} Zarządu, {prezes.pelne:narz}"})
