"""Klageschrift einer Privatperson gegen eine Privatperson auf Zahlung des Restkaufpreises für ein verkauftes
Fahrzeug vor dem Amtsgericht (Streitwert bis 5 000 €, kein Anwaltszwang): der Kläger handelt selbst."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="de", typ="pozew_zaplata_osoby", warianty=("de_amtsgericht",), dorosli=True,
    role={"klaeger": "osoba", "beklagter": "osoba", "zeuge1": "osoba", "zeuge2": "osoba", "fahrzeug": "sprawa",
          "gericht": "sad"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{klaeger.pelne}",
               "{klaeger.adres} | Tel. {klaeger.telefon} | {klaeger.email}"),
        sekcja("court", "akapit",
               "An das",
               "{gericht.nazwa}",
               "– Zivilabteilung –",
               "{klaeger.miasto}, den {ctx.pozew}"),
        sekcja("title", "akapit", "KLAGE"),
        sekcja("rubrum", "akapit",
               "{klaeger.rodzaj:des Herrn|der Frau} {klaeger.pelne}, {klaeger.adres}, Steuer-ID {klaeger.steuer_id}",
               "{klaeger.rodzaj:– Kläger –|– Klägerin –}",
               "gegen",
               "{beklagter.rodzaj:Herrn|Frau} {beklagter.pelne}, {beklagter.adres}",
               "{beklagter.rodzaj:– Beklagter –|– Beklagte –}",
               "wegen Zahlung eines Restkaufpreises",
               "Streitwert: {ctx.glowna}"),
        sekcja("antrag", "akapit",
               "Ich erhebe Klage und werde beantragen:",
               "1. {beklagter.rodzaj:Der Beklagte wird|Die Beklagte wird} verurteilt, an {klaeger.rodzaj:den "
               "Kläger|die Klägerin} {ctx.glowna} nebst Zinsen in Höhe von fünf Prozentpunkten über dem "
               "Basiszinssatz seit dem {ctx.termin_wezwania} zu zahlen.",
               "2. {beklagter.rodzaj:Der Beklagte hat|Die Beklagte hat} die Kosten des Rechtsstreits zu tragen, "
               "darunter die Gerichtsgebühr von {ctx.oplata_pozwu}.",
               "3. Ich stimme einer Entscheidung im schriftlichen Verfahren zu."),
        sekcja("begruendung", "akapit",
               "BEGRÜNDUNG",
               "{klaeger.rodzaj:Der Kläger verkaufte|Die Klägerin verkaufte} {beklagter.rodzaj:dem Beklagten|der "
               "Beklagten} am {ctx.umowa} den Personenkraftwagen mit dem amtlichen Kennzeichen {fahrzeug.tablica} "
               "und übergab ihn am selben Tag.",
               "{beklagter.rodzaj:Der Beklagte zahlte|Die Beklagte zahlte} nur einen Teil des Kaufpreises. Der "
               "Restbetrag von {ctx.glowna} war bis zum {ctx.termin_platnosci} auf das Konto {klaeger.rachunek} zu "
               "überweisen und ist nicht eingegangen.",
               "Mit Schreiben vom {ctx.wezwanie} forderte {klaeger.rodzaj:der Kläger|die Klägerin} "
               "{beklagter.rodzaj:den Beklagten|die Beklagte} an der Anschrift {beklagter.adres} unter Fristsetzung bis "
               "zum {ctx.termin_wezwania} zur Zahlung auf. Eine Reaktion blieb aus.",
               "Der Anspruch folgt aus § 433 Abs. 2 BGB, der Zinsanspruch aus den §§ 286, 288 BGB.",
               min=3, max=4),
        sekcja("zustaendigkeit", "akapit",
               "Das Amtsgericht ist sachlich nach den §§ 23, 71 GVG und örtlich nach den §§ 12, 13 ZPO zuständig, da "
               "{beklagter.rodzaj:der Beklagte|die Beklagte} im Gerichtsbezirk wohnt. Ein Anwaltszwang besteht nicht."),
        sekcja("beweis", "akapit",
               "Beweis:",
               "1. Kaufvertrag vom {ctx.umowa} – für Preis und Fälligkeit,",
               "2. Kontoauszug des Kontos {klaeger.rachunek} – für das Ausbleiben der Zahlung,",
               "3. Zeugnis {zeuge1.rodzaj:des Herrn|der Frau} {zeuge1.pelne}, {zeuge1.adres} – für die Übergabe des "
               "Fahrzeugs,",
               "4. Zeugnis {zeuge2.rodzaj:des Herrn|der Frau} {zeuge2.pelne}, Tel. {zeuge2.telefon} – für das "
               "Schuldanerkenntnis {beklagter.rodzaj:des Beklagten|der Beklagten}.",
               min=3, max=4),
        sekcja("anlagen", "akapit",
               "Anlagen:",
               "1. Abschrift der Klage nebst Anlagen,",
               "2. Nachweis über die Zahlung der Gerichtsgebühr von {ctx.oplata_pozwu},",
               "3. Mahnschreiben nebst Zugangsnachweis."),
        sekcja("signature", "podpis", "{klaeger.pelne}"),
        sekcja("footer", "stopka", "{klaeger.pelne} | {klaeger.adres} | Tel. {klaeger.telefon} | {klaeger.email}"),
        sekcja("hinweis", "przypis",
               "Die Gerichtsgebühr wurde vom Konto {klaeger.rachunek} eingezahlt; {klaeger.rodzaj:der Kläger|die Klägerin} "
               "handelt ohne anwaltliche Vertretung."),
    ],
    metadane={"author": "{klaeger.pelne}", "subject": "Klage auf Zahlung des Restkaufpreises"},
)
