"""Lohnliste eines Unternehmens (Tabellenkalkulation): Kopf, Abrechnungszeitraum, Tabelle mit über 200 Beschäftigten
(Steuer-ID, Sozialversicherungsnummer, IBAN), Zusammenfassung und Hinweise.

Jede Zeile hat eine eigene Person (`p000`…), weil Lücken derselben Rolle nur einen Wert haben; Gehälter und Summen
stammen aus `Kontekst` (`ctx.brutto_<i>`, `ctx.suma_<n>`), sodass die Zusammenfassung zur Tabelle passt."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

WIERSZE = 212
_FUNKTIONEN = ("Sachbearbeitung", "Buchhaltung", "Teamleitung", "Junior-Techniker", "Assistenz der Geschäftsführung",
               "Fahrer", "Lagermitarbeiter", "Bürokraft", "Senior-Techniker", "Fachkraft für Arbeitssicherheit",
               "Berater", "Systemadministration")

_ROLE_WIERSZY = {f"p{i:03d}": "osoba" for i in range(WIERSZE)}


def _tabela() -> str:
    wiersze = ["Lfd. Nr. | Vorname | Nachname | Steuer-ID | SV-Nummer | Funktion | Bruttogehalt | IBAN"]
    for i in range(WIERSZE):
        p = f"p{i:03d}"
        wiersze.append(f"{i + 1} | {{{p}.pelne/1}} | {{{p}.pelne/2}} | {{{p}.steuer_id}} | {{{p}.svnr}} | "
                       f"{_FUNKTIONEN[i % len(_FUNKTIONEN)]} | {{ctx.brutto_{i}}} | {{{p}.rachunek}}")
    return "\n".join(wiersze)


SZABLON = Szablon(
    jezyk="de", typ="lista_plac",
    role={"firma": "firma", "ersteller": "osoba", "freigeber": "osoba", "personal": "osoba"} | _ROLE_WIERSZY,
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{firma.nazwa}",
               "{firma.adres} | Steuernummer {firma.steuernr} | Betriebsnummer {ctx.udzialy1}"),
        sekcja("title", "akapit",
               "LOHN- UND GEHALTSLISTE",
               "Auszahlungstag: {ctx.dok_termin}",
               "Arbeitgeber: {firma.nazwa}"),
        sekcja("table", "komorka", _tabela()),
        sekcja("summary", "komorka",
               "Position | Betrag\n"
               "Bruttolohnsumme | {ctx.suma_212}\n"
               "Sozialversicherung (Arbeitnehmeranteil) | {ctx.zus_212}\n"
               "Lohnsteuer (einbehalten) | {ctx.pit_212}"),
        sekcja("notes", "akapit",
               "Die Lohnsteuer wird nach § 41a EStG monatlich beziehungsweise vierteljährlich an das Finanzamt "
               "angemeldet und abgeführt.",
               "Die Beiträge zur Sozialversicherung werden spätestens am drittletzten Bankarbeitstag des Monats "
               "an die Einzugsstellen gezahlt (§ 23 SGB IV).",
               "Entgeltfortzahlung im Krankheitsfall, Zuschüsse zum Mutterschaftsgeld und tarifliche Zuschläge sind in den einzelnen Entgeltabrechnungen aufgeführt.",
               "Diese Liste enthält personenbezogene Daten nach Art. 9 und 88 DSGVO in Verbindung mit § 26 BDSG und "
               "ist nach § 41 EStG sechs Jahre aufzubewahren.",
               min=3, max=4),
        sekcja("prepared", "akapit",
               "Erstellt von: {ersteller.pelne}, Lohnbuchhaltung, Tel. {ersteller.telefon}",
               "Geprüft von: {personal.pelne}",
               "Zur Zahlung freigegeben: {freigeber.pelne}"),
        sekcja("signatures", "podpis", "{ersteller.pelne}", "{freigeber.pelne}"),
        sekcja("footer", "stopka",
               "{firma.nazwa} | {firma.adres} | Tel. {firma.telefon} | {firma.email}"),
    ],
    metadane={"author": "{ersteller.pelne}", "subject": "Lohn- und Gehaltsliste"},
)
