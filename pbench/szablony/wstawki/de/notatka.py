"""Aktenvermerk über ein Mandantengespräch mit einer Mandantin/einem Mandanten aus der Ukraine (mit Dolmetscher)."""
from __future__ import annotations

from ....budowa import Szablon
from ..._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="de", typ="notatka", dorosli=True, znacz_encje=True, warianty=("cw", "tr"),
    role={"kanzlei": "kancelaria", "bearbeiter": "osoba", "mandant": "osoba_ua", "dolmetscher": "osoba",
          "gegner": "osoba"},
    sekcje=[
        sekcja("kopf", "naglowek",
               "{kanzlei.nazwa}",
               "AKTENVERMERK – VERTRAULICH (anwaltliche Verschwiegenheit)"),
        sekcja("angaben", "akapit",
               "Datum: {ctx.przed_rozprawa}",
               "Bearbeiter: {bearbeiter.pelne}",
               "Mandant: {mandant.pelne_im:t_s1} ({mandant.pelne_im:t_s2})"),
        sekcja("gespraech", "akapit",
               "Telefonische Besprechung mit {mandant.rodzaj:dem Mandanten|der Mandantin} unter Hinzuziehung "
               "{dolmetscher.rodzaj:des Dolmetschers|der Dolmetscherin} {dolmetscher.pelne}. {mandant.rodzaj:Der Mandant|Die Mandantin} bestätigte die "
               "folgenden Kontaktdaten: Anschrift {mandant.adres:t_s1} ({mandant.adres:t_s2}); Telefon "
               "{mandant.telefon}; E-Mail {mandant.email}.",
               W("tr", "Der Name wird in den vorliegenden Unterlagen unterschiedlich geschrieben: "
                       "{mandant.pelne_im:t_s2}, {mandant.pelne_im:t_s3} und {mandant.pelne_im:t_s4}. "
                       "{mandant.rodzaj:Der Mandant|Die Mandantin} bestätigte, dass alle Schreibweisen dieselbe "
                       "Person bezeichnen; für gerichtliche Schriftsätze gilt die Schreibweise des Reisepasses "
                       "(Nr. {mandant.paszport})."),
               "Identifikation: steuerliche Identifikationsnummer der Ukraine (РНОКПП) {mandant.rnokpp}; "
               "Ausweisnummer {mandant.dowod}; Geburtsdatum {mandant.data_ur}."),
        sekcja("sachverhalt", "akapit",
               "Sachverhalt: Der Streit mit {gegner.pelne} betrifft eine verspätete Lieferung von Waren, die im "
               "Frühjahr bestellt wurden. Bestellbestätigung und E-Mail-Verkehr liegen vor; Kopien werden bis Ende "
               "der Woche übersandt.",
               "Rechtlicher Hinweis: {mandant.rodzaj:Der Mandant|Die Mandantin} soll sich nicht unmittelbar an "
               "{gegner.pelne} wenden. Die Kanzlei richtet ein Anwaltsschreiben an die Gegenseite und notiert den "
               "Fristablauf zum {ctx.notatka_termin}.",
               "Kosten: Über die Vergütung nach dem RVG wurde belehrt; ein Vorschuss in Höhe von "
               "{ctx.zaliczka_kosztow} wird vor Klageerhebung angefordert.",
               min=2, max=3),
        sekcja("aufgaben", "akapit",
               "Aufgaben: (1) Anwaltsschreiben entwerfen; (2) beglaubigte Übersetzung der ukrainischen Vertrags"
               "unterlagen veranlassen; (3) Mandantenstammdaten mit der Schreibweise {mandant.pelne_im:t_s1} "
               "aktualisieren.",
               "Wiedervorlage nach Ablauf der Antwortfrist."),
        sekcja("unterschrift", "podpis", "{bearbeiter.pelne}"),
        sekcja("fusszeile", "stopka", "{kanzlei.nazwa} | {kanzlei.adres} | {kanzlei.email}"),
    ],
    metadane={"author": "{bearbeiter.pelne}", "subject": "Aktenvermerk"},
)
