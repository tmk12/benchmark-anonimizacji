"""E-Mail der Kanzlei an die Mandantschaft mit dem Entwurf der Klageerwiderung und der Bitte um Unterlagen (Von/An/Cc
als Metadaten), Anrede nach Geschlecht, Signatur mit Telefon und Haftungshinweis. Verfahren beim Amtsgericht oder
Landgericht (Aktenzeichen passend zur Instanz). Fristen: `odp_termin` < `rozprawa`."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="de", typ="email", warianty=("de_amtsgericht", "de_landgericht"),
    role={"kanzlei": "kancelaria", "absender": "osoba", "mandant": "osoba", "kollege": "osoba", "gegner": "osoba",
          "zeuge": "osoba", "gericht": "sad", "sache": "sprawa", "portal": "sprawa"},
    sekcje=[
        sekcja("greeting", "akapit",
               "Sehr {mandant.rodzaj:geehrter Herr|geehrte Frau} {mandant.nazwisko},"),
        sekcja("intro", "akapit",
               "Im Anschluss an unser Telefonat sende ich Ihnen den Entwurf der Klageerwiderung in dem Verfahren "
               "{sache.sygnatura}, das {gegner.pelne} gegen Sie angestrengt hat.",
               "Ich bestätige, dass das {gericht.nazwa} den Termin zur mündlichen Verhandlung auf den "
               "{ctx.rozprawa} bestimmt hat. Bitte teilen Sie mir mit, ob Sie an diesem Tag verfügbar sind.",
               "Vielen Dank für die übersandten Unterlagen. Nach erster Durchsicht ist der Sachverhalt gut "
               "dokumentiert, es fehlen jedoch noch einzelne Belege.",
               min=3, max=3),
        sekcja("draft", "akapit",
               "Der Entwurf liegt als Word-Datei mit Änderungsmodus bei. Bitte senden Sie mir Ihre Anmerkungen bis "
               "zum {ctx.odp_termin}, denn an diesem Tag läuft die Frist zur Erwiderung ab; eine Verlängerung ist nur "
               "bei triftigem Grund möglich."),
        sekcja("body", "akapit",
               "Wir benötigen von Ihnen: die Bestätigung Ihrer ladungsfähigen Anschrift ({mandant.adres}), den Beleg "
               "über den Vorschuss und Kopien des Schriftverkehrs der letzten zwei Jahre.",
               "Den Kostenvorschuss in Höhe von {ctx.zaliczka_kosztow} überweisen Sie bitte spätestens am Tag vor der "
               "Verhandlung auf das Konto der Kanzlei {kanzlei.rachunek}.",
               "Unterlagen laden Sie bitte in unser Mandantenportal hoch: {portal.url}. Senden Sie besonders "
               "sensible Dokumente nicht per einfacher E-Mail.",
               "{zeuge.rodzaj:Der benannte Zeuge|Die benannte Zeugin}, {zeuge.pelne}, wurde informiert, dass das "
               "Gericht {zeuge.rodzaj:ihn|sie} laden kann; bei Änderung der Nummer ({zeuge.telefon}) bitte kurz "
               "melden.",
               "Strategisch schlage ich vor, der Klage entgegenzutreten und hilfsweise eine Ratenzahlung "
               "anzubieten, soweit das Gericht dies zulässt.",
               min=3, max=5),
        sekcja("closing", "akapit",
               "Bei Fragen erreichen Sie mich unter {absender.telefon} oder per E-Mail unter {absender.email}.",
               "Zur Information setze ich {kollege.pelne} in Kopie; {kollege.rodzaj:er|sie} vertritt mich während meiner Abwesenheit.",
               "Mit freundlichen Grüßen",
               min=3, max=3),
        sekcja("signature", "stopka",
               "{absender.pelne} | {absender.rodzaj:Rechtsanwalt|Rechtsanwältin} | {kanzlei.nazwa} | {kanzlei.adres} | "
               "Tel. {kanzlei.telefon}"),
        sekcja("disclaimer", "stopka",
               "Diese E-Mail ist vertraulich und kann berufsrechtlich geschützte Informationen enthalten. Wenn "
               "Sie nicht der vorgesehene Empfänger sind, informieren Sie bitte den Absender und löschen Sie die "
               "Nachricht. {kanzlei.nazwa} verarbeitet Ihre Daten nach der DSGVO.",
               "Informationen zum Datenschutz nach Art. 13 DSGVO finden Sie auf unserer Internetseite; "
               "Auskunfts-, Berichtigungs- und Löschungsrechte können Sie schriftlich bei der Kanzlei geltend machen.",
               min=1, max=2),
    ],
    metadane={"from": "{absender.email}", "to": "{mandant.email}", "cc": "{kollege.email}",
              "subject": "Entwurf der Klageerwiderung – bitte prüfen und Anmerkungen senden"},
)
