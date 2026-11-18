"""Dienstleistungsvertrag (Rechtsberatung) zwischen einer Rechtsanwaltskanzlei und einer GmbH als Mandantin: Parteien,
Präambel, Paragrafen (Gegenstand, Vergütung nach § 3a RVG mit 19 % Umsatzsteuer, Verschwiegenheit, Datenschutz,
Haftung, Laufzeit, Mitteilungen, Schlussbestimmungen), Unterschriften. Beträge und Daten aus `Kontekst`; Paragrafen fest
nummeriert (keine Lücken). Beide Unterzeichner volljährig (`dorosli`)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="de", typ="umowa", dorosli=True,
    role={"kanzlei": "kancelaria", "mandantin": "spolka", "partner": "osoba", "geschaeftsfuehrer": "osoba",
          "ansprechpartner": "osoba", "vertretung": "osoba", "koordinator": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{kanzlei.nazwa}",
               "{kanzlei.adres} | Tel. {kanzlei.telefon} | {kanzlei.email}",
               "USt-IdNr. {kanzlei.vat} | Steuernummer {kanzlei.steuernr}"),
        sekcja("title", "akapit",
               "DIENSTLEISTUNGSVERTRAG",
               "über laufende Rechtsberatung",
               "{kanzlei.miasto}, den {ctx.dok}"),
        sekcja("between", "akapit", "zwischen"),
        sekcja("parties", "akapit",
               "{kanzlei.nazwa}, {kanzlei.adres}, vertreten durch "
               "{partner.rodzaj:Herrn Rechtsanwalt|Frau Rechtsanwältin} {partner.pelne}, – nachfolgend „Kanzlei“ genannt –",
               "und",
               "{mandantin.nazwa}, {mandantin.adres}, eingetragen im Handelsregister beim {mandantin.registro} unter "
               "{mandantin.hrb}, vertreten durch {geschaeftsfuehrer.rodzaj:den Geschäftsführer Herrn|die "
               "Geschäftsführerin Frau} {geschaeftsfuehrer.pelne}, – nachfolgend „Mandantin“ genannt –"),
        sekcja("preamble", "akapit",
               "Präambel",
               "Die Mandantin benötigt laufende anwaltliche Beratung in gesellschafts-, arbeits- und "
               "datenschutzrechtlichen Fragen. Die Kanzlei ist bereit, diese Beratung zu den nachstehenden "
               "Bedingungen zu erbringen. Dies vorausgeschickt, vereinbaren die Parteien Folgendes:"),
        sekcja("scope", "akapit",
               "§ 1 Gegenstand des Vertrages",
               "(1) Die Kanzlei berät die Mandantin fortlaufend in gesellschafts-, arbeits- und "
               "datenschutzrechtlichen Angelegenheiten, einschließlich der Prüfung und Erstellung von Verträgen, "
               "der Anfertigung schriftlicher Stellungnahmen und der Teilnahme an Verhandlungsterminen (die „Leistungen“).",
               "(2) Nicht umfasst ist die gerichtliche und außergerichtliche Vertretung in Streitverfahren; hierfür "
               "bedarf es eines gesonderten Mandats nebst Vollmacht.",
               "(3) Ansprechpartner der Kanzlei ist {ansprechpartner.rodzaj:Herr Rechtsanwalt|Frau Rechtsanwältin} "
               "{ansprechpartner.pelne}, im Verhinderungsfall {vertretung.rodzaj:Herr Rechtsanwalt|Frau Rechtsanwältin} "
               "{vertretung.pelne}. Ein Wechsel des Ansprechpartners bedarf keiner Vertragsänderung.",
               "(4) Die Mandantin stellt die erforderlichen Informationen und Unterlagen über "
               "{koordinator.pelne} (Tel. {koordinator.telefon}, E-Mail {koordinator.email}) zur Verfügung."),
        sekcja("fees", "akapit",
               "§ 2 Vergütung",
               "(1) Für die Leistungen zahlt die Mandantin der Kanzlei eine monatliche Pauschale von {ctx.um_wyn} "
               "zuzüglich der gesetzlichen Umsatzsteuer in Höhe von derzeit 19 %. Diese Vergütungsvereinbarung "
               "wird in Textform nach § 3a RVG getroffen.",
               "(2) Die Pauschale deckt bis zu zwanzig Arbeitsstunden im Monat ab. Darüber hinausgehende Stunden werden "
               "nach den jeweils gültigen Stundensätzen der Kanzlei abgerechnet, höchstens jedoch bis zu einem "
               "Betrag von {ctx.um_limit} monatlich ohne vorherige schriftliche Zustimmung der Mandantin.",
               "(3) Rechnungen sind innerhalb von vierzehn Tagen nach Zugang ohne Abzug auf das Konto der Kanzlei "
               "{kanzlei.rachunek} zu zahlen. Bei Zahlungsverzug gelten die gesetzlichen Verzugszinsen nach § 288 BGB."),
        sekcja("confidentiality", "akapit",
               "§ 3 Verschwiegenheit",
               "(1) Die Kanzlei ist zur Verschwiegenheit über alles verpflichtet, was ihr in Ausübung des Berufs bekannt "
               "wird (§ 43a Abs. 2 BRAO, § 203 StGB). Diese Pflicht besteht über das Vertragsende hinaus fort.",
               "(2) Die Mandantin behandelt vertrauliche Informationen der Kanzlei, insbesondere Stundensätze und "
               "interne Arbeitsergebnisse, ebenfalls vertraulich."),
        sekcja("data", "akapit",
               "§ 4 Datenschutz",
               "Die Parteien beachten die Datenschutz-Grundverordnung (DSGVO) und das Bundesdatenschutzgesetz (BDSG). "
               "Die Kanzlei verarbeitet personenbezogene Daten als Verantwortliche im Sinne des Art. 4 Nr. 7 DSGVO, "
               "soweit dies zur Mandatsbearbeitung und zur Erfüllung gesetzlicher Pflichten, etwa nach dem "
               "Geldwäschegesetz, erforderlich ist."),
        sekcja("liability", "akapit",
               "§ 5 Haftung",
               "(1) Die Haftung der Kanzlei für fahrlässig verursachte Schäden ist, soweit gesetzlich zulässig, auf "
               "den Betrag von {ctx.um_kara} je Schadensfall begrenzt. Dieser Betrag ist durch die "
               "Berufshaftpflichtversicherung der Kanzlei gedeckt.",
               "(2) Die Haftung für Vorsatz, für die Verletzung des Lebens, des Körpers oder der Gesundheit sowie für "
               "zwingend gesetzlich geregelte Fälle bleibt unberührt."),
        sekcja("term", "akapit",
               "§ 6 Laufzeit und Kündigung",
               "(1) Der Vertrag beginnt am {ctx.od_dnia} und läuft zunächst für zwölf Monate. Er verlängert sich "
               "jeweils um weitere zwölf Monate, wenn er nicht mit einer Frist von drei Monaten zum Laufzeitende "
               "gekündigt wird.",
               "(2) Das Recht zur außerordentlichen Kündigung aus wichtigem Grund (§ 626 BGB) bleibt unberührt. "
               "Kündigungen bedürfen der Textform."),
        sekcja("notices", "akapit",
               "§ 7 Mitteilungen",
               "Mitteilungen im Rahmen dieses Vertrages erfolgen in Textform an die Anschrift der Mandantin "
               "({mandantin.adres}) oder der Kanzlei ({kanzlei.adres}) beziehungsweise an die zuletzt mitgeteilte "
               "E-Mail-Adresse."),
        sekcja("final", "akapit",
               "§ 8 Schlussbestimmungen",
               "(1) Änderungen und Ergänzungen dieses Vertrages bedürfen der Schriftform; dies gilt auch für die "
               "Änderung dieser Klausel.",
               "(2) Sollten einzelne Bestimmungen unwirksam sein oder werden, bleibt die Wirksamkeit der übrigen "
               "Bestimmungen unberührt (salvatorische Klausel).",
               "(3) Es gilt deutsches Recht unter Ausschluss des UN-Kaufrechts. Ausschließlicher Gerichtsstand ist, soweit "
               "gesetzlich zulässig, {kanzlei.miasto}."),
        sekcja("signatures", "podpis", "{partner.pelne}", "{geschaeftsfuehrer.pelne}"),
        sekcja("footer", "stopka",
               "{kanzlei.nazwa} | {kanzlei.adres} | USt-IdNr. {kanzlei.vat} | Tel. {kanzlei.telefon} | "
               "{kanzlei.email}"),
    ],
    metadane={"author": "{partner.pelne}", "subject": "Dienstleistungsvertrag über laufende Rechtsberatung"},
)
