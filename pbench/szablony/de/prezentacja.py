"""Präsentation der Kanzlei vor dem Beirat einer Mandantin: Ergebnisse der rechtlichen Due Diligence einer
Zielgesellschaft (kurze Folien und Risikotabelle); deutsches Recht (Unternehmenskauf, GmbH-Anteile)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="de", typ="prezentacja",
    role={"kanzlei": "kancelaria", "referent": "osoba", "ansprechpartner": "osoba", "geschaeftsfuehrer": "osoba",
          "zielgesellschaft": "spolka", "mandantin": "firma", "seite": "sprawa"},
    sekcje=[
        sekcja("titles", "naglowek",
               "Rechtliche Due Diligence: {zielgesellschaft.nazwa}",
               "Zusammenfassung der Ergebnisse",
               "Wesentliche Risiken der Transaktion",
               "Maßnahmenplan bis zum Closing",
               "Kontakt und nächste Schritte"),
        sekcja("slide1", "akapit",
               "Es präsentiert {referent.pelne}, {kanzlei.nazwa}",
               "Beirat – {mandantin.nazwa}, {ctx.dok}",
               "Streng vertraulich – nur für den Beirat"),
        sekcja("slide2", "akapit",
               "Zielgesellschaft: {zielgesellschaft.nazwa}, {zielgesellschaft.adres}",
               "{zielgesellschaft.registro}, {zielgesellschaft.hrb} | USt-IdNr. {zielgesellschaft.vat}",
               "Managementgespräche mit {geschaeftsfuehrer.pelne}, {geschaeftsfuehrer.rodzaj:Geschäftsführer|"
               "Geschäftsführerin}",
               "Vorgeschlagener Kaufpreis für die Geschäftsanteile: {ctx.cena}"),
        sekcja("slide3", "akapit",
               "Change-of-Control-Klauseln in den Verträgen mit Schlüsselkunden",
               "Das Verzeichnis der Verarbeitungstätigkeiten (Art. 30 DSGVO) ist veraltet",
               "Drei laufende Rechtsstreitigkeiten mit einem Streitwert von zusammen {ctx.sporow}",
               "Für die eingesetzte Software fehlt eine lückenlose Rechtekette",
               "Keine Rückstände bei Sozialversicherung und Finanzamt festgestellt",
               min=3, max=5),
        sekcja("risks", "komorka",
               "Bereich | Risiko | Empfehlung\n"
               "Arbeitsrecht | Mittel | Vergütungsrichtlinie aktualisieren\n"
               "Datenschutz | Hoch | Verzeichnis und Auftragsverarbeitungsverträge nachziehen\n"
               "Immobilien | Gering | Keine Maßnahmen\n"
               "Geistiges Eigentum | Hoch | Nutzungsrechte der Freelancer einholen"),
        sekcja("slide4", "akapit",
               "Unterzeichnung des Kaufvertrags über die Geschäftsanteile bis zum {ctx.dok_termin_dl}",
               "Aufschiebende Bedingungen: Zustimmung der Gesellschafter und der finanzierenden Bank",
               "Für das Closing ist die Mitwirkung von {geschaeftsfuehrer.pelne} als Geschäftsführung der "
               "Zielgesellschaft erforderlich",
               "Fusionskontrolle: Aufgreifschwellen nach § 35 GWB prüfen",
               min=3, max=4),
        sekcja("slide5", "akapit",
               "Kontakt: {ansprechpartner.pelne}, Tel. {ansprechpartner.telefon}, E-Mail {ansprechpartner.email}",
               "Unsere Seite: {seite.url}",
               "Vielen Dank"),
        sekcja("footer", "stopka", "{kanzlei.nazwa} – vertraulich"),
    ],
    metadane={"author": "{referent.pelne}", "subject": "Rechtliche Due Diligence"},
)
