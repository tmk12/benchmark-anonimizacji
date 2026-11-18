"""Lebenslauf einer Rechtsanwältin oder eines Rechtsanwalts (Berufseinsteiger, Deutschland): persönliche Daten, Profil,
Berufserfahrung, Ausbildung, Sprachen, Referenzen und Einwilligung nach DSGVO. Daten aus `Kontekst`: Erstes Staatsexamen
< frühere Stelle < aktuelle Stelle."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="de", typ="cv",
    role={"kandidat": "osoba", "arbeitgeber1": "firma", "arbeitgeber2": "firma", "vorgesetzter": "osoba",
          "referenz1": "osoba", "referenz2": "osoba", "seite": "sprawa"},
    sekcje=[
        sekcja("header", "naglowek",
               "LEBENSLAUF",
               "{kandidat.pelne}"),
        sekcja("contact", "akapit",
               "Geboren am {kandidat.data_ur}",
               "Staatsangehörigkeit: deutsch",
               "Anschrift: {kandidat.adres}",
               "Telefon: {kandidat.telefon} | E-Mail: {kandidat.email}",
               "Berufliches Profil: {seite.url}",
               min=4, max=5),
        sekcja("summary", "akapit",
               "{kandidat.rodzaj:Rechtsanwalt|Rechtsanwältin} mit Erfahrung im Handels- und Gesellschaftsrecht, im "
               "Vertragsrecht und in der Streitbeilegung, teamorientiert und mandantennah.",
               "Besonderes Interesse am Gesellschaftsrecht, am Datenschutzrecht und am Zivilprozessrecht.",
               "Zugelassen bei der Rechtsanwaltskammer und vertraut mit dem besonderen elektronischen "
               "Anwaltspostfach (beA) sowie mit gängiger Kanzleisoftware.",
               min=2, max=3),
        sekcja("experience_title", "akapit", "BERUFSERFAHRUNG"),
        sekcja("experience", "akapit",
               "{ctx.cv_od1} – heute: {kandidat.rodzaj:Rechtsanwalt|Rechtsanwältin} bei {arbeitgeber1.nazwa}, "
               "{arbeitgeber1.adres}. Beratung mittelständischer Unternehmen in Handels- und Arbeitsrecht, "
               "Vertragsgestaltung und Vorbereitung von Gesellschafterversammlungen.",
               "Fachliche Aufsicht: {vorgesetzter.pelne}.",
               "{ctx.cv_od2} – {ctx.cv_do2}: Wissenschaftliche Mitarbeit bei {arbeitgeber2.nazwa}, Unterstützung der "
               "Prozessabteilung bei Klageschriften, Erwiderungen und Beweisanträgen.",
               min=3, max=3),
        sekcja("education_title", "akapit", "AUSBILDUNG"),
        sekcja("education", "akapit",
               "Erstes juristisches Staatsexamen, bestanden am {ctx.cv_studia}. Schwerpunktbereich: Unternehmens- und "
               "Gesellschaftsrecht.",
               "Juristischer Vorbereitungsdienst (Referendariat) mit Stationen bei Gericht, Staatsanwaltschaft und in "
               "einer Rechtsanwaltskanzlei; Zweites juristisches Staatsexamen.",
               "Fortbildungen im Datenschutzrecht (DSGVO, BDSG) und im Insolvenzrecht.",
               min=2, max=3),
        sekcja("skills", "akapit",
               "Sprachen: Deutsch (Muttersprache), Englisch (verhandlungssicher), Französisch (Grundkenntnisse).",
               "EDV: Microsoft Office, beA, juristische Datenbanken, qualifizierte elektronische Signatur.",
               "Stärken: juristisches Schreiben, Verhandlungsführung, Zeitmanagement, Teamarbeit.",
               min=2, max=3),
        sekcja("referees", "akapit",
               "Referenzen: {referenz1.pelne}, Tel. {referenz1.telefon}; {referenz2.pelne}, E-Mail {referenz2.email}."),
        sekcja("interests", "akapit",
               "Interessen: Wandern, Schach, ehrenamtliche Mitarbeit in einer kostenlosen Rechtsberatung.",
               "Verfügbarkeit: sofort, Vollzeit.",
               min=1, max=2),
        sekcja("consent", "akapit",
               "Ich willige in die Verarbeitung meiner personenbezogenen Daten zum Zweck des Bewerbungsverfahrens "
               "nach Art. 6 Abs. 1 Buchst. a DSGVO und § 26 BDSG ein. Die Einwilligung kann ich jederzeit mit "
               "Wirkung für die Zukunft widerrufen."),
        sekcja("signature", "podpis", "{kandidat.pelne}"),
        sekcja("footer", "stopka",
               "{kandidat.pelne} | {kandidat.email} | Tel. {kandidat.telefon}"),
    ],
    metadane={"author": "{kandidat.pelne}", "subject": "Lebenslauf"},
)
