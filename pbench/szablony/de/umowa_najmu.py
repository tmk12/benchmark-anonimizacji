"""Mietvertrag über Wohnraum zwischen zwei Privatpersonen (Vermieter – Mieter) mit Kaution (drei Monatsmieten sind
das gesetzliche Maximum; hier eine Monatsmiete), Übergabeprotokoll und Kontaktdaten."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="de", typ="umowa_najmu", dorosli=True,
    role={"vermieter": "osoba", "mieter": "osoba", "wohnung": "osoba", "zeuge": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "WOHNRAUMMIETVERTRAG",
               "Vermieter: {vermieter.pelne} | Mieter: {mieter.pelne}"),
        sekcja("opening", "akapit",
               "Zwischen den Parteien wird am {ctx.dok} in {vermieter.miasto} folgender Mietvertrag geschlossen:"),
        sekcja("parties", "akapit",
               "{vermieter.rodzaj:Herr|Frau} {vermieter.pelne}, Personalausweis-Nr. {vermieter.personalausweis}, "
               "Steuer-ID {vermieter.steuer_id}, wohnhaft {vermieter.adres}, Tel. {vermieter.telefon}, E-Mail "
               "{vermieter.email} – nachstehend „Vermieter“ genannt –",
               "und",
               "{mieter.rodzaj:Herr|Frau} {mieter.pelne}, Personalausweis-Nr. {mieter.personalausweis}, "
               "Steuer-ID {mieter.steuer_id}, bisher wohnhaft {mieter.adres}, Tel. {mieter.telefon}, E-Mail "
               "{mieter.email} – nachstehend „Mieter“ genannt –."),
        sekcja("object", "akapit",
               "§ 1 Mietsache",
               "(1) Der Vermieter vermietet dem Mieter die Wohnung in {wohnung.adres}, samt Kellerabteil und "
               "Stellplatz, die bis zum {ctx.umowa_dawna} von {wohnung.rodzaj:Herrn|Frau} {wohnung.pelne} bewohnt wurde.",
               "(2) Die Wohnung wird ausschließlich zu Wohnzwecken vermietet. Eine Untervermietung oder gewerbliche "
               "Nutzung bedarf der vorherigen schriftlichen Zustimmung des Vermieters.",
               "(3) Die Übergabe erfolgt am {ctx.od_dnia} gegen Übergabeprotokoll; für den Vermieter nimmt "
               "{zeuge.pelne} (Tel. {zeuge.telefon}) an der Übergabe teil."),
        sekcja("miete", "akapit",
               "§ 2 Miete und Kaution",
               "(1) Die monatliche Miete beträgt {ctx.zaliczka_kosztow} und ist monatlich im Voraus, spätestens bis "
               "zum dritten Werktag, auf das Konto des Vermieters {vermieter.rachunek} zu zahlen.",
               "(2) Die Betriebskosten werden nach Verbrauch bzw. Umlageschlüssel abgerechnet; Strom, Internet und "
               "Telefon schließt der Mieter selbst ab.",
               "(3) Der Mieter leistet eine Kaution von {ctx.zaliczka_kosztow} (eine Monatsmiete). Der Vermieter "
               "legt sie getrennt von seinem Vermögen bei einem Kreditinstitut zu dem für Spareinlagen mit "
               "dreimonatiger Kündigungsfrist üblichen Zinssatz an (§ 551 BGB)."),
        sekcja("dauer", "akapit",
               "§ 3 Mietdauer und Kündigung",
               "(1) Das Mietverhältnis beginnt am {ctx.od_dnia} und läuft bis zum {ctx.dok_pozniej}.",
               "(2) Das Recht zur außerordentlichen fristlosen Kündigung nach den §§ 543, 569 BGB bleibt unberührt; "
               "die Kündigung bedarf der Textform."),
        sekcja("pflichten", "akapit",
               "§ 4 Pflichten der Parteien",
               "(1) Der Mieter hält die Wohnung sauber, lüftet sie ausreichend und zeigt Mängel dem Vermieter "
               "unverzüglich an. Kleinreparaturen trägt er bis zu einem Betrag von 100 € je Einzelfall.",
               "(2) Der Vermieter darf die Wohnung nach vorheriger Ankündigung mit mindestens zwei Tagen Vorlauf "
               "in Anwesenheit des Mieters betreten; bei Gefahr im Verzug jederzeit.",
               "(3) Der Mieter meldet sich fristgerecht beim Einwohnermeldeamt an; der Vermieter bestätigt den "
               "Einzug mit der Wohnungsgeberbescheinigung.",
               min=2, max=3),
        sekcja("tabelle", "komorka",
               "Position | Stand bei Übergabe | Bemerkung\n"
               "Stromzähler | 04 213 kWh | in Anwesenheit beider Parteien abgelesen\n"
               "Wasserzähler | 118 m3 | ohne Beanstandung\n"
               "Schlüssel | 3 Stück | übergeben an {mieter.pelne}",
               "Position | Frist | Verantwortlich\n"
               "Mietzahlung | dritter Werktag | {mieter.pelne}\n"
               "Kautionsrückzahlung | nach Rückgabe der Wohnung | {vermieter.pelne}\n"
               "Übergabe | {ctx.od_dnia} | {zeuge.pelne}",
               min=1, max=1),
        sekcja("schluss", "akapit",
               "§ 5 Schlussbestimmungen",
               "(1) Änderungen und Ergänzungen dieses Vertrags bedürfen der Schriftform.",
               "(2) Mitteilungen erfolgen an die oben genannten Anschriften oder per E-Mail an {vermieter.email} "
               "und {mieter.email}.",
               "(3) Ist eine Bestimmung unwirksam, bleibt der Vertrag im Übrigen wirksam (salvatorische Klausel).",
               "(4) Der Vertrag wird in zwei Ausfertigungen errichtet; jede Partei erhält eine."),
        sekcja("sign_label", "akapit", "Vermieter:                                                  Mieter:"),
        sekcja("signature", "podpis", "{vermieter.pelne}", "{mieter.pelne}"),
        sekcja("footer", "stopka", "Mietvertrag – {vermieter.pelne} / {mieter.pelne} | Mietsache: {wohnung.adres}"),
        sekcja("hinweis", "przypis",
               "Dem Mieter wurden der Energieausweis und die Wohnungsgeberbescheinigung am {ctx.dok} ausgehändigt."),
    ],
    metadane={"author": "{vermieter.pelne}", "title": "Wohnraummietvertrag"},
)
