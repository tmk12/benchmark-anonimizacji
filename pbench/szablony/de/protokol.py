"""Protokoll der ordentlichen Gesellschafterversammlung einer GmbH (GmbHG): Einladung, Anwesenheitsliste als Tabelle,
Beschlussfähigkeit, Jahresabschluss, Beschlüsse (Geschäftsführerbestellung, Gewinnverwendung, Satzungsänderung), Schluss.
Stammkapital aus Geschäftsanteilen zu je `ctx.nominal` (250 €) – mindestens 25 000 € (§ 5 GmbHG); Tagesordnungspunkte mit
`{#}` ohne Lücken. Alle Teilnehmer volljährig (`dorosli`)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="de", typ="protokol", dorosli=True,
    role={"gesellschaft": "spolka", "leiter": "osoba", "schriftfuehrer": "osoba", "gesellschafter1": "osoba",
          "gesellschafter2": "osoba", "gesellschafter3": "osoba", "geschaeftsfuehrer": "osoba", "neu": "osoba",
          "pruefer": "osoba", "berater": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{gesellschaft.nazwa}",
               "{gesellschaft.adres} | {gesellschaft.registro}, {gesellschaft.hrb} | USt-IdNr. {gesellschaft.vat}"),
        sekcja("title", "akapit",
               "PROTOKOLL DER ORDENTLICHEN GESELLSCHAFTERVERSAMMLUNG DER {gesellschaft.nazwa:upper}",
               "Ort und Zeit: {gesellschaft.miasto}, Geschäftsräume der Gesellschaft, {gesellschaft.adres}, am "
               "{ctx.dok}"),
        sekcja("open", "akapit",
               "TOP {#}: Eröffnung. {leiter.rodzaj:Herr|Frau} {leiter.pelne} eröffnet als {leiter.rodzaj:Versammlungsleiter|"
               "Versammlungsleiterin} die Versammlung. Das Protokoll führt {schriftfuehrer.rodzaj:Herr|Frau} "
               "{schriftfuehrer.pelne}.",
               "TOP {#}: Einberufung. {leiter.rodzaj:Der Versammlungsleiter|Die Versammlungsleiterin} stellt fest, dass "
               "die Gesellschafter durch eingeschriebenen Brief unter Mitteilung der Tagesordnung eingeladen wurden "
               "und die Ladungsfrist von einer Woche (§ 51 Abs. 1 GmbHG) gewahrt ist.",
               "TOP {#}: Weitere Teilnehmer. {geschaeftsfuehrer.pelne}, {geschaeftsfuehrer.rodzaj:Geschäftsführer|"
               "Geschäftsführerin} der Gesellschaft, nimmt ohne Stimmrecht teil.",
               min=3, max=3),
        sekcja("attendance_label", "akapit", "Anwesende Gesellschafter:"),
        sekcja("attendance", "komorka",
               "Lfd. Nr. | Gesellschafter | Geschäftsanteile | Nennbetrag | Stimmen\n"
               "1 | {gesellschafter1.pelne} | {ctx.udzialy1} | {ctx.wartosc1} | {ctx.udzialy1}\n"
               "2 | {gesellschafter2.pelne} | {ctx.udzialy2} | {ctx.wartosc2} | {ctx.udzialy2}\n"
               "3 | {gesellschafter3.pelne} | {ctx.udzialy3} | {ctx.wartosc3} | {ctx.udzialy3}\n"
               "Summe | alle Gesellschafter | {ctx.udzialy_suma3} | {ctx.kapital3} | {ctx.udzialy_suma3}"),
        sekcja("quorum", "akapit",
               "TOP {#}: Beschlussfähigkeit. Es sind Gesellschafter mit allen {ctx.udzialy_suma3} Geschäftsanteilen "
               "anwesend; die Versammlung ist damit als Vollversammlung beschlussfähig.",
               "TOP {#}: Stammkapital. Das Stammkapital der Gesellschaft beträgt {ctx.kapital3} und ist in "
               "{ctx.udzialy_suma3} Geschäftsanteile zu je {ctx.nominal} eingeteilt. Je Geschäftsanteil wird eine "
               "Stimme gewährt.",
               min=2, max=2),
        sekcja("accounts", "akapit",
               "TOP {#}: Jahresabschluss. Der Jahresabschluss zum letzten Geschäftsjahr liegt vor; {pruefer.rodzaj:der "
               "Abschlussprüfer|die Abschlussprüferin} {pruefer.pelne} bestätigt im Prüfungsbericht, dass er ein den "
               "tatsächlichen Verhältnissen entsprechendes Bild vermittelt.",
               "TOP {#}: Lagebericht. {geschaeftsfuehrer.pelne} berichtet über den Geschäftsverlauf und die "
               "Aussichten für das laufende Jahr.",
               "TOP {#}: Rechtliche Hinweise. {berater.rodzaj:Der Rechtsberater|Die Rechtsberaterin} der Gesellschaft, {berater.pelne} (Tel. {berater.telefon}), weist auf die für die "
               "anstehenden Beschlüsse erforderlichen Mehrheiten hin.",
               min=2, max=3),
        sekcja("resolutions", "akapit",
               "TOP {#}: Bestellung. Zum weiteren Geschäftsführer wird {neu.pelne}, wohnhaft {neu.adres}, mit Wirkung "
               "ab dem Tag dieser Versammlung bestellt (§ 46 Nr. 5 GmbHG). Abstimmung: {ctx.glosy_za2} Stimmen "
               "dafür, {ctx.glosy_przeciw2} Stimmen dagegen.",
               "TOP {#}: Gewinnverwendung. Vom Bilanzgewinn werden {ctx.dywidenda} an die Gesellschafter im "
               "Verhältnis ihrer Geschäftsanteile ausgeschüttet (§ 29 GmbHG), zahlbar innerhalb des nächsten "
               "Quartals.",
               "TOP {#}: Satzungsänderung. Die Regelung zur Geschäftsführung im Gesellschaftsvertrag wird mit der "
               "nach § 53 Abs. 2 GmbHG erforderlichen Mehrheit von drei Vierteln der abgegebenen Stimmen geändert; "
               "die notarielle Beurkundung ist erforderlich.",
               min=3, max=3),
        sekcja("close", "akapit",
               "TOP {#}: Schluss. Da weitere Punkte nicht zu behandeln sind, {leiter.rodzaj:schließt der "
               "Versammlungsleiter|schließt die Versammlungsleiterin} die Versammlung.",
               "Die nächste ordentliche Gesellschafterversammlung findet am {ctx.dok_pozniej} statt.",
               "Das Protokoll wird von der Versammlungsleitung und der Protokollführung unterzeichnet und in den "
               "Geschäftsunterlagen der Gesellschaft aufbewahrt; Beschlüsse sind nach § 47 GmbHG dokumentiert.",
               min=3, max=3),
        sekcja("sign_label", "akapit", "Versammlungsleitung                      Protokollführung"),
        sekcja("signatures", "podpis", "{leiter.pelne}", "{schriftfuehrer.pelne}"),
        sekcja("footer", "stopka",
               "{gesellschaft.nazwa} | {gesellschaft.adres} | Tel. {gesellschaft.telefon} | {gesellschaft.email}"),
    ],
    metadane={"author": "{schriftfuehrer.pelne}", "subject": "Protokoll der Gesellschafterversammlung"},
)
