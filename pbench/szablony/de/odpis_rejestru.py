"""Handelsregisterauszug (aktueller Abdruck, Abteilung B) einer GmbH: Registergericht, HRB-Nummer, Firma, Sitz,
Geschäftsanschrift, Stammkapital (mindestens 25 000 € nach § 5 GmbHG, Vielfaches des Nennbetrags 250 €), Tabelle der
Geschäftsführer mit Geburtsdatum und Wohnort, Gesellschafter, Hinweise. Daten aus `Kontekst`: Gründung <= letzte
Eintragung <= Abrufdatum.

Echte Handelsregisterauszüge enthalten Name, Wohnort und Geburtsdatum der Geschäftsführer, aber weder Steuer-ID noch
Ausweisnummer – deshalb stehen hier keine Identifikationsnummern in der Tabelle. Geschäftsführer sind am frühesten Datum
des Kontextes volljährig (`dorosli`)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="de", typ="odpis_rejestru", dorosli=True,
    role={"gesellschaft": "spolka", "gf1": "osoba", "gf2": "osoba", "gf3": "osoba", "prokurist": "osoba",
          "gesellschafter1": "osoba", "gesellschafter2": "osoba", "antragsteller": "osoba"},
    sekcje=[
        sekcja("titles", "naglowek",
               "Handelsregister B beim {gesellschaft.registro}",
               "Aktueller Abdruck – {gesellschaft.nazwa}"),
        sekcja("identity", "komorka",
               "Angabe | Eintragung\n"
               "Nummer der Firma | {gesellschaft.hrb}\n"
               "Firma | {gesellschaft.nazwa}\n"
               "Sitz | {gesellschaft.miasto}\n"
               "Geschäftsanschrift | {gesellschaft.adres}\n"
               "Registergericht | {gesellschaft.registro}\n"
               "Rechtsform | Gesellschaft mit beschränkter Haftung"),
        sekcja("dates", "komorka",
               "Angabe | Datum / Betrag\n"
               "Gesellschaftsvertrag vom | {ctx.kr_rejestracja}\n"
               "Tag der letzten Eintragung | {ctx.kr_wpis}\n"
               "Stammkapital | {ctx.kapital2}"),
        sekcja("organs_title", "akapit",
               "Vertretungsberechtigte Geschäftsführer",
               "Allgemeine Vertretungsregelung: Ist nur ein Geschäftsführer bestellt, vertritt er die Gesellschaft "
               "allein. Sind mehrere Geschäftsführer bestellt, wird die Gesellschaft durch zwei Geschäftsführer "
               "oder durch einen Geschäftsführer gemeinsam mit einem Prokuristen vertreten."),
        sekcja("organs", "komorka",
               "Lfd. Nr. | Name | Vorname | Geburtsdatum | Wohnort | Vertretungsbefugnis\n"
               "1 | {gf1.nazwisko} | {gf1.imie} | {gf1.data_ur} | {gf1.miasto} | einzelvertretungsberechtigt\n"
               "2 | {gf2.nazwisko} | {gf2.imie} | {gf2.data_ur} | {gf2.miasto} | einzelvertretungsberechtigt\n"
               "3 | {gf3.nazwisko} | {gf3.imie} | {gf3.data_ur} | {gf3.miasto} | gemeinsam mit einem weiteren "
               "Geschäftsführer",
               "Funktion | Name | Geburtsdatum | Wohnort\n"
               "Geschäftsführer | {gf1.pelne} | {gf1.data_ur} | {gf1.miasto}\n"
               "Geschäftsführer | {gf2.pelne} | {gf2.data_ur} | {gf2.miasto}\n"
               "Prokurist | {prokurist.pelne} | {prokurist.data_ur} | {prokurist.miasto}",
               min=1, max=1),
        sekcja("holders", "komorka",
               "Gesellschafter | Name | Geschäftsanteile | Bemerkung\n"
               "1 | {gesellschafter1.pelne} | {ctx.udzialy1} | Nennbetrag je Geschäftsanteil {ctx.nominal}\n"
               "2 | {gesellschafter2.pelne} | {ctx.udzialy2} | Nennbetrag je Geschäftsanteil {ctx.nominal}",
               min=0, max=1),
        sekcja("oversight", "akapit",
               "Die Gesellschaft befindet sich nicht in Liquidation; ein Insolvenzverfahren ist nicht eröffnet.",
               "Gegenstand des Unternehmens: Beratung und Dienstleistungen im Bereich der Unternehmensorganisation "
               "sowie damit zusammenhängende Geschäfte.",
               "Geschäftsjahr: Kalenderjahr. Die Gesellschaft ist auf unbestimmte Zeit errichtet.",
               min=3, max=3),
        sekcja("certification", "akapit",
               "Dieser Abdruck dient der Information und ersetzt keine beglaubigte Ausfertigung. Für den Nachweis "
               "der Vertretungsbefugnis wird ein beglaubigter Registerauszug oder eine Notarbescheinigung nach "
               "§ 21 BNotO benötigt.",
               "Der Abruf erfolgte über das gemeinsame Registerportal der Länder auf Antrag von "
               "{antragsteller.pelne}, der ein berechtigtes Interesse an der Einsichtnahme dargelegt hat "
               "(§ 9 HGB)."),
        sekcja("footer", "stopka",
               "Abruf aus dem Handelsregister beim {gesellschaft.registro} | {gesellschaft.hrb} | Abrufdatum: "
               "{ctx.dok} | Seite 1 von 2"),
    ],
    metadane={"subject": "Handelsregisterauszug", "entity": "{gesellschaft.nazwa}"},
)
