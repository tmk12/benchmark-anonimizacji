"""Kaufvertrag über ein gebrauchtes Kraftfahrzeug zwischen zwei Privatpersonen: Personalausweis- und Steuer-Angaben,
amtliches Kennzeichen, Kaufpreis mit Anzahlung, Fahrzeugdaten in einer Tabelle. Eine Fahrgestellnummer gibt es im
Generator nicht – sie kommt im Dokument nicht vor."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="de", typ="umowa_sprzedazy_auta", dorosli=True,
    role={"verkaeufer": "osoba", "kaeufer": "osoba", "fahrzeug": "sprawa", "zeuge": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "KAUFVERTRAG ÜBER EIN GEBRAUCHTES KRAFTFAHRZEUG",
               "Verkäufer: {verkaeufer.pelne} | Käufer: {kaeufer.pelne}"),
        sekcja("opening", "akapit", "Zwischen den Parteien wird am {ctx.dok} in {verkaeufer.miasto} folgender Vertrag geschlossen:"),
        sekcja("parties", "akapit",
               "{verkaeufer.rodzaj:Herr|Frau} {verkaeufer.pelne}, Personalausweis-Nr. {verkaeufer.personalausweis}, "
               "wohnhaft {verkaeufer.adres}, Tel. {verkaeufer.telefon} – nachstehend „Verkäufer“ –",
               "und",
               "{kaeufer.rodzaj:Herr|Frau} {kaeufer.pelne}, Personalausweis-Nr. {kaeufer.personalausweis}, "
               "Steuer-ID {kaeufer.steuer_id}, wohnhaft {kaeufer.adres}, Tel. {kaeufer.telefon}, E-Mail "
               "{kaeufer.email} – nachstehend „Käufer“ –."),
        sekcja("object", "akapit",
               "§ 1 Kaufgegenstand",
               "(1) Der Verkäufer verkauft dem Käufer den gebrauchten Personenkraftwagen mit dem amtlichen Kennzeichen "
               "{fahrzeug.tablica} samt Zulassungsbescheinigung Teil I und II, zwei Schlüsseln und Serviceheft.",
               "(2) Der Verkäufer versichert, dass er alleiniger Eigentümer ist, das Fahrzeug nicht sicherungsübereignet "
               "oder gepfändet ist und es keine nicht offengelegten Unfallschäden gibt.",
               "(3) Die Haftpflichtversicherung des Fahrzeugs läuft bis zum {ctx.dok_pozniej}; der Verkäufer zeigt "
               "den Verkauf dem Versicherer an."),
        sekcja("preis", "akapit",
               "§ 2 Kaufpreis",
               "(1) Der Kaufpreis beträgt {ctx.szkoda}.",
               "(2) Der Käufer hat bei Vertragsschluss eine Anzahlung von {ctx.zaliczka_ub} geleistet; den Restbetrag "
               "überweist er bis zum {ctx.dok_termin} auf das Konto des Verkäufers {verkaeufer.rachunek}.",
               "(3) Die Kosten der Ummeldung und der Kfz-Steuer trägt ab Übergabe der Käufer."),
        sekcja("tabelle", "komorka",
               "Merkmal | Stand | Bemerkung\n"
               "Kilometerstand | 187 450 km | laut Tacho\n"
               "Hauptuntersuchung | gültig bis {ctx.dok_pozniej} | Bericht liegt bei\n"
               "Unfallschäden | keine | Angabe von {verkaeufer.pelne}",
               "Merkmal | Unterlage | Übergeben an\n"
               "Zulassungsbescheinigung | Teil I und II | {kaeufer.pelne}\n"
               "Schlüssel | 2 Stück | {kaeufer.pelne}\n"
               "Rechnungen | 9 Stück | {zeuge.pelne}",
               min=1, max=1),
        sekcja("uebergabe", "akapit",
               "§ 3 Übergabe und Gewährleistung",
               "(1) Das Fahrzeug wird am {ctx.dok_sprzedaz} an der Anschrift des Verkäufers übergeben; "
               "{zeuge.pelne} (Tel. {zeuge.telefon}) ist als Zeuge für den Zustand des Fahrzeugs anwesend.",
               "(2) Der Käufer hat das Fahrzeug besichtigt und Probe gefahren. Der Verkauf erfolgt unter Ausschluss "
               "jeder Sachmängelhaftung, soweit dies gesetzlich zulässig ist; hiervon unberührt bleibt die Haftung "
               "für Vorsatz und arglistig verschwiegene Mängel.",
               "(3) Mit der Übergabe geht die Gefahr des zufälligen Untergangs auf den Käufer über."),
        sekcja("schluss", "akapit",
               "§ 4 Schlussbestimmungen",
               "(1) Änderungen dieses Vertrags bedürfen der Schriftform.",
               "(2) Kontakt für Rückfragen: {verkaeufer.email} und {kaeufer.telefon}.",
               "(3) Der Vertrag wird in zwei Ausfertigungen errichtet; jede Partei erhält eine."),
        sekcja("sign_label", "akapit", "Verkäufer:                                                  Käufer:"),
        sekcja("signature", "podpis", "{verkaeufer.pelne}", "{kaeufer.pelne}"),
        sekcja("footer", "stopka", "Kaufvertrag Kfz {fahrzeug.tablica} | {verkaeufer.pelne} / {kaeufer.pelne}"),
        sekcja("hinweis", "przypis",
               "Der Käufer meldet das Fahrzeug unverzüglich bei der Zulassungsbehörde um; der Verkäufer zeigt die "
               "Veräußerung der Zulassungsbehörde an."),
    ],
    metadane={"author": "{verkaeufer.pelne}", "title": "Kaufvertrag Gebrauchtwagen"},
)
