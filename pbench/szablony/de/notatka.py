"""Interner Aktenvermerk der Kanzlei an den Sozius zu einem Verkehrsunfall: Beteiligte, Sachverhalt, Schaden,
Beratung des Mandanten, nächste Schritte. Vermerkdatum `ctx.przed_rozprawa`, Frist `notatka_termin` < `rozprawa`;
Verfahren beim Amtsgericht (Schaden bis 5 000 €) oder Landgericht, Aktenzeichen passend zur Instanz; Punkte mit `{#}`."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="de", typ="notatka", warianty=("de_amtsgericht", "de_landgericht"),
    role={"kanzlei": "kancelaria", "bearbeiter": "osoba", "mandant": "osoba", "gegner": "osoba", "zeuge": "osoba",
          "versicherung": "firma", "gericht": "sad"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{kanzlei.nazwa}",
               "{kanzlei.adres} | Tel. {kanzlei.telefon}"),
        sekcja("heading", "akapit",
               "AKTENVERMERK – INTERN – VERTRAULICH",
               "Von: {bearbeiter.pelne}",
               "Datum: {ctx.przed_rozprawa}",
               "Betreff: Schadensersatz nach Verkehrsunfall – {mandant.rodzaj:Mandant|Mandantin} {mandant.pelne}"),
        sekcja("parties", "akapit",
               "{mandant.rodzaj:Mandant|Mandantin}: {mandant.pelne}, {mandant.adres}, Tel. {mandant.telefon}, E-Mail {mandant.email}.",
               "Unfallgegner: {gegner.pelne}, {gegner.rodzaj:Fahrer|Fahrerin} des anderen Fahrzeugs, wohnhaft "
               "{gegner.adres}; Haftpflichtversicherer ist die {versicherung.nazwa} (USt-IdNr. {versicherung.vat}).",
               "Verfahren: {gericht.sygnatura} beim {gericht.nazwa}.",
               min=3, max=3),
        sekcja("facts", "akapit",
               "{#}. Sachverhalt. {mandant.rodzaj:Der Mandant|Die Mandantin} fuhr innerorts, als das Fahrzeug von "
               "{gegner.pelne} die Spur wechselte und die linke Seite des Fahrzeugs {mandant.rodzaj:des "
               "Mandanten|der Mandantin} streifte. Personen wurden nicht verletzt. Die Polizei hat den Unfall "
               "aufgenommen.",
               "{#}. Schaden. Nach dem Kostenvoranschlag der Werkstatt beläuft sich der Sachschaden auf {ctx.szkoda}. "
               "Die {versicherung.nazwa} hat einen Vorschuss von {ctx.zaliczka_ub} gezahlt, erkennt die Haftung dem "
               "Grunde nach an, bestreitet aber die Höhe der Reparaturkosten.",
               "{#}. Beweismittel. {zeuge.rodzaj:Der Zeuge|Die Zeugin} {zeuge.pelne} hat den Unfall beobachtet und ist "
               "zur Aussage bereit; erreichbar unter {zeuge.telefon}. Lichtbilder der Unfallstelle und die "
               "Unfallmitteilung liegen vor.",
               "{#}. Anspruchsgrundlage. Der Anspruch folgt aus § 7 Abs. 1 StVG und § 115 Abs. 1 VVG gegen den "
               "Haftpflichtversicherer, daneben aus § 823 Abs. 1 BGB gegen {gegner.rodzaj:den Fahrer|die Fahrerin}.",
               min=4, max=4),
        sekcja("advice", "akapit",
               "{#}. Beratung. Ich habe {mandant.rodzaj:den Mandanten|die Mandantin} darauf hingewiesen, dass wir bis "
               "zum {ctx.notatka_termin} die Reparaturrechnung und das Gutachten nachreichen müssen.",
               "{#}. Termin. Die mündliche Verhandlung ist für den {ctx.rozprawa} anberaumt. {mandant.rodzaj:Der "
               "Mandant|Die Mandantin} muss persönlich erscheinen (§ 141 ZPO).",
               "{#}. Kosten. Bei teilweisem Obsiegen werden die Kosten nach § 92 ZPO verhältnismäßig geteilt. Das "
               "Kostenrisiko ist mit {mandant.rodzaj:dem Mandanten|der Mandantin} besprochen.",
               "{#}. Vergleich. Ein außergerichtlicher Vergleich mit der Versicherung ist wegen des Prozessrisikos "
               "und der Verfahrensdauer zu empfehlen.",
               min=3, max=4),
        sekcja("documents", "akapit",
               "Ausstehende Unterlagen: Schlussrechnung der Werkstatt, Sachverständigengutachten, Nachweis der "
               "Selbstbeteiligung.",
               "Die Ermittlungsakte der Polizei wurde angefordert; eine Anfrage beim Zentralruf der Autoversicherer "
               "ist nicht erforderlich, da der Haftpflichtversicherer bekannt ist.",
               "Alle Unterlagen liegen in der elektronischen Akte (beA/Kanzleisoftware) mit beschränktem Zugriff.",
               min=2, max=3),
        sekcja("actions", "akapit",
               "Nächste Schritte: Beweisanträge vorbereiten und die Zeugen laden lassen.",
               "Rückruf bei {mandant.pelne} am {ctx.notatka_termin}.",
               min=2, max=2),
        sekcja("signature", "podpis", "{bearbeiter.pelne}"),
        sekcja("footer", "stopka",
               "{kanzlei.nazwa} | {kanzlei.adres} | USt-IdNr. {kanzlei.vat} | Tel. {kanzlei.telefon} | "
               "{kanzlei.email}"),
    ],
    metadane={"author": "{bearbeiter.pelne}", "subject": "Aktenvermerk Verkehrsunfall", "case": "{gericht.sygnatura}"},
)
