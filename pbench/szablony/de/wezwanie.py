"""Zahlungsaufforderung (letzte Mahnung) einer Rechtsanwaltskanzlei im Auftrag einer Gläubigerin (Unternehmen) an eine
Privatperson: Hauptforderung, Verzugszinsen, vorgerichtliche Kosten, Zahlungsfrist, Zahlungsweg, Folgen. Daten und Beträge
aus `Kontekst` (Leistung < Fälligkeit < Mahnung < Fristende)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="de", typ="wezwanie",
    role={"kanzlei": "kancelaria", "anwalt": "osoba", "glaeubigerin": "spolka", "vertreter": "osoba",
          "schuldner": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{kanzlei.nazwa}",
               "{kanzlei.adres} | Tel. {kanzlei.telefon} | {kanzlei.email}",
               "USt-IdNr. {kanzlei.vat}"),
        sekcja("date", "akapit",
               "{kanzlei.miasto}, den {ctx.wezwanie}",
               "Per Einwurf-Einschreiben",
               "Unser Zeichen: RA-{ctx.udzialy1}"),
        sekcja("addressee", "akapit",
               "{schuldner.rodzaj:Herrn|Frau} {schuldner.pelne}",
               "{schuldner.adres}"),
        sekcja("subject", "akapit",
               "Zahlungsaufforderung – letzte Mahnung",
               "Forderung: {glaeubigerin.nazwa}"),
        sekcja("salutation", "akapit",
               "Sehr {schuldner.rodzaj:geehrter Herr|geehrte Frau} {schuldner.nazwisko},"),
        sekcja("basis", "akapit",
               "wir zeigen an, dass uns {glaeubigerin.nazwa}, {glaeubigerin.adres} (USt-IdNr. "
               "{glaeubigerin.vat}), vertreten durch {vertreter.rodzaj:Herrn|Frau} {vertreter.pelne}, mit der "
               "Wahrnehmung ihrer rechtlichen Interessen beauftragt hat.",
               "Unsere Mandantin hat Ihnen am {ctx.umowa} Leistungen berechnet. Der Rechnungsbetrag wurde am "
               "{ctx.termin_platnosci} fällig; eine Zahlung ist trotz Erinnerung nicht erfolgt.",
               "Offen sind: Hauptforderung {ctx.glowna}, Verzugszinsen bis heute {ctx.odsetki} (fünf Prozentpunkte "
               "über dem Basiszinssatz, § 288 Abs. 1 BGB) sowie vorgerichtliche Kosten in Höhe von {ctx.koszty_wind}. "
               "Die Gesamtforderung beträgt damit {ctx.razem_wez}.",
               "Sie befinden sich seit Ablauf der Zahlungsfrist in Verzug (§ 286 BGB); dieses Schreiben dient der "
               "abschließenden Zahlungsaufforderung."),
        sekcja("payment", "akapit",
               "Wir fordern Sie auf, die Gesamtforderung bis zum {ctx.termin_wezwania} auf das Konto unserer "
               "Mandantin {glaeubigerin.rachunek} zu überweisen und im Verwendungszweck unser Zeichen anzugeben.",
               "Sollten Sie die Forderung nicht in einer Summe begleichen können, ist unsere Mandantin zu einer "
               "Ratenzahlung bereit, sofern die erste Rate mindestens {ctx.ugoda_rata} beträgt und innerhalb der "
               "genannten Frist eingeht.",
               min=1, max=2),
        sekcja("consequences", "akapit",
               "Nach fruchtlosem Fristablauf wird unsere Mandantin ohne weitere Ankündigung gerichtliche "
               "Schritte einleiten, etwa durch Beantragung eines Mahnbescheids (§ 688 ZPO) oder durch Klage. "
               "Hierdurch entstehen Ihnen weitere Kosten.",
               "Wir weisen darauf hin, dass der Mahnbescheid die Verjährung hemmt (§ 204 Abs. 1 Nr. 3 BGB).",
               "Eine Meldung an eine Wirtschaftsauskunftei bleibt unter den Voraussetzungen des Art. 6 Abs. 1 "
               "Buchst. f DSGVO vorbehalten.",
               min=2, max=3),
        sekcja("contact", "akapit",
               "Für Rückfragen steht Ihnen {anwalt.rodzaj:Herr Rechtsanwalt|Frau Rechtsanwältin} {anwalt.pelne} unter "
               "Tel. {anwalt.telefon} oder {anwalt.email} zur Verfügung."),
        sekcja("close", "akapit", "Mit freundlichen Grüßen"),
        sekcja("signature", "podpis", "{anwalt.pelne}"),
        sekcja("footer", "stopka",
               "{kanzlei.nazwa} | {kanzlei.adres} | USt-IdNr. {kanzlei.vat} | Tel. {kanzlei.telefon} | "
               "{kanzlei.email}"),
    ],
    metadane={"author": "{anwalt.pelne}", "subject": "Zahlungsaufforderung"},
)
