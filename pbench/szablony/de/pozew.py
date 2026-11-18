"""Klageschrift auf Rückzahlung eines Darlehens an das Amtsgericht (Streitwert bis 5 000 €) oder das Landgericht
(darüber, Anwaltszwang): Rubrum („In dem Rechtsstreit … – Klägerin – gegen … – Beklagter –“), Anträge, Begründung
(Sachverhalt, rechtliche Würdigung), Beweisangebote, Anlagen. Daten und Beträge aus `Kontekst`; Aktenzeichen hat die Sache
noch nicht (Klageeingang), der Streitwert folgt dem Gerichtsstand der Variante."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="de", typ="pozew", warianty=("de_amtsgericht", "de_landgericht"),
    role={"kanzlei": "kancelaria", "anwalt": "osoba", "klaeger": "osoba", "beklagter": "osoba", "zeuge1": "osoba",
          "zeuge2": "osoba", "gericht": "sad"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{kanzlei.nazwa}",
               "{kanzlei.adres} | Tel. {kanzlei.telefon} | {kanzlei.email}",
               "Unser Zeichen: RA-{ctx.udzialy1}"),
        sekcja("court", "akapit",
               "An das",
               "{gericht.nazwa}",
               W("de_amtsgericht", "– Zivilabteilung –"),
               W("de_landgericht", "– Zivilkammer –"),
               "{kanzlei.miasto}, den {ctx.pozew}"),
        sekcja("title", "akapit", "KLAGE"),
        sekcja("rubrum", "akapit",
               "{klaeger.rodzaj:des Herrn|der Frau} {klaeger.pelne}, {klaeger.adres}",
               "{klaeger.rodzaj:– Kläger –|– Klägerin –}",
               "Prozessbevollmächtigte: {anwalt.rodzaj:Rechtsanwalt|Rechtsanwältin} {anwalt.pelne}, {kanzlei.nazwa}, "
               "{kanzlei.adres}",
               "gegen",
               "{beklagter.rodzaj:Herrn|Frau} {beklagter.pelne}, {beklagter.adres}",
               "{beklagter.rodzaj:– Beklagter –|– Beklagte –}",
               "wegen Rückzahlung eines Darlehens",
               "Streitwert: {ctx.glowna}"),
        sekcja("opening", "akapit",
               "Namens und in Vollmacht {klaeger.rodzaj:des Klägers|der Klägerin} erhebe ich Klage und werde beantragen:"),
        sekcja("prayer", "akapit",
               "1. {beklagter.rodzaj:Der Beklagte wird|Die Beklagte wird} verurteilt, an {klaeger.rodzaj:den "
               "Kläger|die Klägerin} {ctx.glowna} nebst Zinsen in Höhe von fünf Prozentpunkten über dem "
               "Basiszinssatz seit dem {ctx.termin_wezwania} sowie vorgerichtliche Rechtsanwaltskosten in Höhe von "
               "{ctx.koszty_wind} zu zahlen.",
               "2. {beklagter.rodzaj:Der Beklagte hat|Die Beklagte hat} die Kosten des Rechtsstreits zu tragen.",
               "3. Das Urteil ist gegebenenfalls gegen Sicherheitsleistung vorläufig vollstreckbar.",
               "4. Für den Fall der Anordnung eines schriftlichen Vorverfahrens und des Vorliegens der Voraussetzungen "
               "der §§ 331 Abs. 3, 307 ZPO wird bereits jetzt der Erlass eines Versäumnis- beziehungsweise "
               "Anerkenntnisurteils beantragt."),
        sekcja("reasons_title", "akapit", "BEGRÜNDUNG", "I. Sachverhalt"),
        sekcja("facts", "akapit",
               "{klaeger.rodzaj:Der Kläger|Die Klägerin} gewährte {beklagter.rodzaj:dem Beklagten|der Beklagten} am "
               "{ctx.umowa} ein Darlehen über {ctx.glowna}. Die Auszahlung erfolgte durch Überweisung auf das Konto "
               "{beklagter.rachunek}.",
               "Das Darlehen war nach der Abrede der Parteien bis zum {ctx.termin_platnosci} zurückzuzahlen. "
               "{beklagter.rodzaj:Der Beklagte|Die Beklagte} hat trotz mehrfacher Erinnerung keine Zahlung geleistet.",
               "Mit Schreiben vom {ctx.wezwanie} forderte {klaeger.rodzaj:der Kläger|die Klägerin} "
               "{beklagter.rodzaj:den Beklagten|die Beklagte} unter Fristsetzung bis zum {ctx.termin_wezwania} zur "
               "Zahlung auf. Die Frist ließ {beklagter.rodzaj:der Beklagte|die Beklagte} ungenutzt verstreichen.",
               "{beklagter.rodzaj:Der Beklagte|Die Beklagte} räumte die Schuld gegenüber {zeuge1.rodzaj:dem "
               "Zeugen|der Zeugin} {zeuge1.pelne} ein und bestätigte sie später in einem Telefonat, das "
               "{zeuge2.rodzaj:der Zeuge|die Zeugin} {zeuge2.pelne} (Tel. {zeuge2.telefon}) mithörte.",
               min=4, max=4),
        sekcja("law_title", "akapit", "II. Rechtliche Würdigung"),
        sekcja("law", "akapit",
               W("de_amtsgericht", "Das angerufene Gericht ist nach §§ 23 Nr. 1, 71 GVG sachlich zuständig, weil der "
                 "Streitwert den Betrag von fünftausend Euro nicht übersteigt. Die örtliche Zuständigkeit folgt aus "
                 "§ 13 ZPO, da {beklagter.rodzaj:der Beklagte|die Beklagte} im Gerichtsbezirk wohnt."),
               W("de_landgericht", "Das angerufene Gericht ist nach §§ 23 Nr. 1, 71 Abs. 1 GVG sachlich zuständig, weil "
                 "der Streitwert fünftausend Euro übersteigt. Die örtliche Zuständigkeit folgt aus § 13 ZPO, da "
                 "{beklagter.rodzaj:der Beklagte|die Beklagte} im Gerichtsbezirk wohnt."),
               W("de_landgericht", "Vor dem Landgericht besteht Anwaltszwang (§ 78 Abs. 1 ZPO); die Klage wird "
                 "daher durch {anwalt.rodzaj:den unterzeichnenden Rechtsanwalt|die unterzeichnende Rechtsanwältin} "
                 "erhoben."),
               "Der Anspruch folgt aus § 488 Abs. 1 Satz 2 BGB. {beklagter.rodzaj:Der Beklagte schuldet|Die Beklagte "
               "schuldet} die Rückzahlung des Darlehens, das am {ctx.termin_platnosci} fällig wurde.",
               "Der Zinsanspruch beruht auf §§ 286, 288 Abs. 1 BGB; {beklagter.rodzaj:der Beklagte|die Beklagte} "
               "befindet sich spätestens seit Ablauf der Zahlungsfrist am {ctx.termin_wezwania} in Verzug.",
               "Die vorgerichtlichen Rechtsanwaltskosten sind als Verzugsschaden nach §§ 280 Abs. 2, 286 BGB zu "
               "ersetzen.",
               "Auf den Gerichtskostenvorschuss (§ 12 GKG) habe ich vorab {ctx.oplata_pozwu} eingezahlt; der "
               "Zahlungsbeleg ist beigefügt.",
               min=6, max=6),
        sekcja("evidence", "akapit",
               "Beweis: Zeugnis {zeuge1.rodzaj:des Herrn|der Frau} {zeuge1.pelne}, {zeuge1.adres}",
               "Zeugnis {zeuge2.rodzaj:des Herrn|der Frau} {zeuge2.pelne}, zu laden über {klaeger.rodzaj:den "
               "Kläger|die Klägerin}",
               "Urkunden: Überweisungsbeleg, Mahnschreiben vom {ctx.wezwanie} mit Zugangsnachweis",
               min=3, max=3),
        sekcja("closing", "akapit",
               "Eine Güteverhandlung (§ 278 Abs. 2 ZPO) halte ich für sinnvoll; {klaeger.rodzaj:der Kläger ist|die "
               "Klägerin ist} zu einem angemessenen Vergleich bereit.",
               "Beglaubigte und einfache Abschrift der Klageschrift sowie die Vollmacht im Original sind beigefügt.",
               "Mit freundlichen Grüßen",
               min=3, max=3),
        sekcja("signature", "podpis", "{anwalt.pelne}"),
        sekcja("footer", "stopka",
               "{kanzlei.nazwa} | {kanzlei.adres} | USt-IdNr. {kanzlei.vat} | Tel. {kanzlei.telefon} | "
               "{kanzlei.email}"),
    ],
    metadane={"author": "{anwalt.pelne}", "subject": "Klage auf Rückzahlung eines Darlehens"},
)
