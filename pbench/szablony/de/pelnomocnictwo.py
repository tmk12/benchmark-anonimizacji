"""Prozessvollmacht (§§ 80 ff. ZPO) einer Privatperson für zwei Rechtsanwälte einer Kanzlei in einem Zahlungsrechtsstreit:
Vollmachtgeber, Bevollmächtigte, Umfang der Vollmacht, Vertretung, Hinweise (Datenschutz, Kosten), Ort, Datum und
Unterschrift. Datum `ctx.dok`; alle Personen sind volljährig (`dorosli`)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="de", typ="pelnomocnictwo", dorosli=True,
    role={"kanzlei": "kancelaria", "vollmachtgeber": "osoba", "anwalt1": "osoba", "anwalt2": "osoba",
          "gegner": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{kanzlei.nazwa}",
               "{kanzlei.adres} | Tel. {kanzlei.telefon} | {kanzlei.email}"),
        sekcja("title", "akapit",
               "PROZESSVOLLMACHT",
               "Unser Zeichen: RA-{ctx.udzialy2}"),
        sekcja("principal", "akapit",
               "Hiermit erteile ich, {vollmachtgeber.pelne}, geboren am {vollmachtgeber.data_ur}, wohnhaft "
               "{vollmachtgeber.adres}, E-Mail {vollmachtgeber.email},",
               "{anwalt1.rodzaj:Herrn Rechtsanwalt|Frau Rechtsanwältin} {anwalt1.pelne} und "
               "{anwalt2.rodzaj:Herrn Rechtsanwalt|Frau Rechtsanwältin} {anwalt2.pelne}, {kanzlei.nazwa}, "
               "{kanzlei.adres},",
               "in Sachen {vollmachtgeber.pelne} ./. {gegner.pelne}, {gegner.adres}, wegen Forderung aus Darlehen "
               "(Hauptforderung {ctx.glowna}),",
               "Prozessvollmacht zur Vertretung in dieser Angelegenheit.",
               min=4, max=4),
        sekcja("scope", "akapit",
               "Die Vollmacht umfasst insbesondere die Befugnis, den Rechtsstreit in allen Instanzen zu führen, Klagen, "
               "Widerklagen und Anträge zu erheben und zurückzunehmen sowie Rechtsmittel einzulegen, zurückzunehmen "
               "oder auf sie zu verzichten (§ 81 ZPO).",
               "Sie berechtigt zum Abschluss von Vergleichen, zur Anerkennung von Ansprüchen und zum Verzicht auf "
               "Ansprüche, soweit dies prozessual zulässig ist (§ 83 ZPO).",
               "Die Bevollmächtigten sind befugt, Zustellungen entgegenzunehmen, Kostenerstattungsansprüche "
               "geltend zu machen und Geld, Wertsachen und Urkunden, insbesondere den Streitgegenstand und die "
               "von der Gegenseite zu erstattenden Kosten, in Empfang zu nehmen.",
               "Die Bevollmächtigten dürfen Untervollmacht erteilen und Vertretungen durch andere Rechtsanwälte "
               "der Kanzlei veranlassen.",
               min=3, max=4),
        sekcja("extent", "akapit",
               "Die Vollmacht erstreckt sich auch auf Neben- und Folgeverfahren, wie Arrest, einstweilige "
               "Verfügung, Zwangsvollstreckung, Kostenfestsetzung und Streitverkündung.",
               "Sie gilt bis zu meinem schriftlichen Widerruf. Das Erlöschen der Vollmacht durch Tod oder "
               "Geschäftsunfähigkeit {vollmachtgeber.rodzaj:des Vollmachtgebers|der Vollmachtgeberin} ist ausgeschlossen, soweit gesetzlich zulässig."),
        sekcja("notices", "akapit",
               "Hinweis nach § 49b Abs. 5 BRAO: Die Gebühren der Rechtsanwälte richten sich nach dem "
               "Gegenstandswert und dem Rechtsanwaltsvergütungsgesetz (RVG).",
               "Ich bin darüber informiert, dass meine personenbezogenen Daten zur Mandatsbearbeitung "
               "nach Art. 6 Abs. 1 Buchst. b DSGVO verarbeitet werden.",
               "Eine Rechtsschutzversicherung besteht nach meinen Angaben nicht; eine Deckungsanfrage ist "
               "daher nicht erforderlich.",
               min=3, max=3),
        sekcja("place_date", "akapit",
               "{vollmachtgeber.miasto}, den {ctx.dok}",
               "(Ort, Datum)"),
        sekcja("signature", "podpis", "{vollmachtgeber.pelne}"),
        sekcja("footer", "stopka",
               "{kanzlei.nazwa} | {kanzlei.adres} | Tel. {kanzlei.telefon} | {kanzlei.email}"),
    ],
    metadane={"author": "{anwalt1.pelne}", "subject": "Prozessvollmacht"},
)
