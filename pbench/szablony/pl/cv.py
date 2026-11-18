"""Życiorys zawodowy (CV) młodego prawnika: dane kontaktowe, doświadczenie, wykształcenie, referencje, klauzula RODO."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="pl", typ="cv",
    role={"kandydat": "osoba", "pracodawca1": "firma", "pracodawca2": "firma", "promotor": "osoba",
          "przelozony": "osoba", "referent": "osoba", "profil": "sprawa", "portfolio": "sprawa"},
    sekcje=[
        sekcja("naglowek", "naglowek",
               "{kandydat.pelne}",
               "Aplikant radcowski | prawo spółek i ochrona danych osobowych"),
        sekcja("kontakt", "akapit",
               "Adres: {kandydat.adres}",
               "Telefon: {kandydat.telefon} | E-mail: {kandydat.email}",
               "Data urodzenia: {kandydat.data_ur}",
               "Profil zawodowy: {profil.url} | Konto w serwisie kodu: {kandydat.login}",
               min=3, max=4),
        sekcja("podsumowanie", "akapit",
               "PROFIL",
               "Prawnik z trzyletnim doświadczeniem w obsłudze spółek kapitałowych, transakcji M&A i projektów "
               "związanych z ochroną danych osobowych. Samodzielnie prowadzę sprawy z zakresu prawa handlowego, "
               "przygotowuję opinie i umowy w języku polskim i angielskim.",
               "Szukam stanowiska w zespole prowadzącym sprawy transgraniczne, z możliwością rozwoju w kierunku "
               "prawa nowych technologii."),
        sekcja("doswiadczenie", "akapit",
               "DOŚWIADCZENIE ZAWODOWE",
               "od {ctx.cv_od1} do dziś – Młodszy prawnik, {pracodawca1.nazwa}, {pracodawca1.adres}. Obsługa "
               "prawna klientów korporacyjnych, due diligence, sporządzanie umów handlowych, udział w "
               "negocjacjach. Bezpośredni przełożony: {przelozony.pelne}.",
               "od {ctx.cv_od2} do {ctx.cv_do2} – Praktykant, a następnie asystent prawny, {pracodawca2.nazwa}. "
               "Wsparcie zespołu postępowań spornych: analiza akt, przygotowywanie projektów pism procesowych, "
               "rejestr terminów. Praca w zespole kierowanym przez {przelozony.pelne:bier}.",
               "Staż w dziale zgodności z regulacjami: opracowanie rejestru czynności przetwarzania i "
               "procedury zgłaszania naruszeń ochrony danych (art. 33 RODO)."),
        sekcja("wyksztalcenie", "akapit",
               "WYKSZTAŁCENIE",
               "Jednolite studia magisterskie na kierunku prawo, Wydział Prawa i Administracji, ukończone w "
               "{ctx.cv_studia}. Praca magisterska z prawa spółek, napisana pod kierunkiem {promotor.pelne:dop}.",
               "Studia podyplomowe: prawo ochrony danych osobowych i cyberbezpieczeństwo. Certyfikat "
               "ukończenia kursu inspektora ochrony danych."),
        sekcja("umiejetnosci", "akapit",
               "UMIEJĘTNOŚCI I JĘZYKI",
               "Języki: angielski (C1, certyfikat CAE), niemiecki (B1). Systemy: LEX, Legalis, pakiet Office, "
               "podstawy pracy z narzędziami do zarządzania dokumentami.",
               "Kursy: negocjacje, legal design, prawo własności intelektualnej w sektorze IT.",
               "Portfolio publikacji i opinii (wybrane): {portfolio.url}",
               min=2, max=4),
        sekcja("referencje", "akapit",
               "REFERENCJE",
               "Referencje udzielone przez {przelozony.pelne:bier} dostępne na życzenie; kontakt do osoby "
               "polecającej: {referent.pelne}, tel. {referent.telefon}, e-mail {referent.email}.",
               min=1, max=2),
        sekcja("zainteresowania", "akapit",
               "Zainteresowania: żeglarstwo, szachy, wolontariat w poradni prawnej.",
               "Prawo jazdy kategorii B, gotowość do podróży służbowych."),
        sekcja("rodo", "akapit",
               "Wyrażam zgodę na przetwarzanie moich danych osobowych zawartych w ofercie pracy dla potrzeb "
               "niezbędnych do realizacji procesu rekrutacji zgodnie z ustawą z dnia 10 maja 2018 r. o ochronie "
               "danych osobowych oraz rozporządzeniem (UE) 2016/679."),
        sekcja("podpis", "podpis", "{kandydat.pelne}"),
        sekcja("stopka", "stopka", "CV – {kandydat.pelne} | {kandydat.email}"),
    ],
    metadane={"author": "{kandydat.pelne}", "subject": "Życiorys zawodowy"},
)
