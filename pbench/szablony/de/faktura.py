"""Rechnung einer Rechtsanwaltskanzlei an ein Unternehmen: Pflichtangaben nach § 14 UStG (Steuernummer, USt-IdNr.,
Leistungszeitpunkt), Leistungsempfänger, Positionen in Tabellen, Netto + 19 % Umsatzsteuer = Brutto (Summen aus
`Kontekst`), Zahlungsbedingungen, Hinweise."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="de", typ="faktura",
    role={"verkaeufer": "kancelaria", "kaeufer": "firma", "aussteller": "osoba", "empfaenger": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{verkaeufer.nazwa}",
               "{verkaeufer.adres} | Steuernummer {verkaeufer.steuernr} | USt-IdNr. {verkaeufer.vat}"),
        sekcja("title", "akapit",
               "RECHNUNG Nr. R-{ctx.udzialy1}",
               "Rechnungsdatum: {ctx.dok}",
               "Leistungszeitpunkt: {ctx.dok_sprzedaz}"),
        sekcja("parties", "komorka",
               "Rechnungsaussteller | Rechnungsempfänger\n"
               "{verkaeufer.nazwa} | {kaeufer.nazwa}\n"
               "{verkaeufer.adres} | {kaeufer.adres}\n"
               "USt-IdNr. {verkaeufer.vat} | USt-IdNr. {kaeufer.vat}\n"
               "Tel. {verkaeufer.telefon} | Tel. {kaeufer.telefon}"),
        sekcja("lines", "komorka",
               "Pos. | Leistung | Menge | Einzelpreis netto | Gesamt netto | USt-Satz\n"
               "1 | Pauschale für laufende Rechtsberatung | 1 | {ctx.kf1} | {ctx.kf1} | 19 %\n"
               "2 | Prüfung eines Gewerberaummietvertrags | 1 | {ctx.kf2} | {ctx.kf2} | 19 %\n"
               "3 | Teilnahme an einer Besprechung mit der Behörde | 1 | {ctx.kf3} | {ctx.kf3} | 19 %",
               "Pos. | Leistung | Einheit | Menge | Gesamt netto | USt-Satz\n"
               "1 | Beratung nach Vertrag vom {ctx.umowa_dawna} | pauschal | 1 | {ctx.kf1} | 19 %\n"
               "2 | Entwurf und Verhandlung von Dokumenten | pauschal | 1 | {ctx.kf2} | 19 %\n"
               "3 | Teilnahme an Gesellschafterversammlungen | pauschal | 1 | {ctx.kf3} | 19 %",
               min=1, max=1),
        sekcja("totals", "komorka",
               "Nettobetrag | Umsatzsteuer 19 % | Rechnungsbetrag\n{ctx.netto} | {ctx.vat} | {ctx.brutto}"),
        sekcja("payment", "akapit",
               "Zahlbar bis zum {ctx.dok_termin_fv} ohne Abzug durch Überweisung auf das Konto "
               "{verkaeufer.rachunek} unter Angabe der Rechnungsnummer.",
               "Rückfragen zu dieser Rechnung richten Sie bitte an {verkaeufer.email}, Tel. {verkaeufer.telefon}."),
        sekcja("notes", "akapit",
               "Die Rechnung erfüllt die Anforderungen des § 14 Abs. 4 UStG; die Leistung ist im Inland "
               "steuerbar und steuerpflichtig.",
               "Bei Zahlungsverzug schulden Sie Verzugszinsen in Höhe von neun Prozentpunkten über dem "
               "Basiszinssatz (§ 288 Abs. 2 BGB) sowie die Verzugspauschale von 40 Euro nach § 288 Abs. 5 BGB.",
               "Die Aufbewahrungsfrist für diese Rechnung beträgt acht Jahre (§ 14b UStG, § 147 AO).",
               "Diese Rechnung wurde elektronisch im Format XRechnung/ZUGFeRD erstellt und ist ohne Unterschrift gültig.",
               min=3, max=4),
        sekcja("issued", "akapit",
               "Die Rechnung wurde per E-Mail an {empfaenger.pelne} als zur Entgegennahme von Buchhaltungsunterlagen "
               "berechtigte Person des Empfängers gesendet.",
               "Erstellt und geprüft durch {aussteller.pelne}."),
        sekcja("signature", "podpis", "{aussteller.pelne}"),
        sekcja("footer", "stopka",
               "{verkaeufer.nazwa} | {verkaeufer.adres} | USt-IdNr. {verkaeufer.vat} | Tel. {verkaeufer.telefon}"),
    ],
    metadane={"author": "{aussteller.pelne}", "subject": "Rechnung für Rechtsberatung"},
)
