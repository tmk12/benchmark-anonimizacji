"""Urteil in einem Zivilrechtsstreit auf Rückzahlung eines Darlehens („IM NAMEN DES VOLKES“) mit Rubrum, Tenor,
Tatbestand und Entscheidungsgründen; Zitate von BGH-Entscheidungen (Klartext, nicht Gold).

Vier Varianten: „de_amtsgericht“ (Einzelrichter, Streitwert bis 5 000 €), „de_landgericht“ (Zivilkammer mit drei Richtern,
über 5 000 €), „de_einzelrichter“ (Landgericht, Einzelrichter) und „de_berufung“ (Landgericht als Berufungsgericht gegen
ein Urteil des Amtsgerichts; Aktenzeichen und Gericht der Vorinstanz in `ctx.sygn_pierwsza` und `ctx.sad_pierwsza`).
Nummerierung (1., 2., … und I., II., …) in jeder Variante fest und lückenlos. Daten, Beträge, Aktenzeichen-Jahr und
Kostenquoten aus `Kontekst`."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

_ERSTE = ("de_amtsgericht", "de_landgericht", "de_einzelrichter")


def erste(tekst: str) -> tuple[W, ...]:
    """Block für alle Varianten der ersten Instanz (nicht für die Berufung)."""
    return tuple(W(v, tekst) for v in _ERSTE)


SZABLON = Szablon(
    jezyk="de", typ="wyrok", przedmiot="darlehen", warianty=("de_amtsgericht", "de_landgericht", "de_einzelrichter", "de_berufung"),
    role={"sad": "sad", "richter1": "osoba", "richter2": "osoba", "richter3": "osoba", "klaeger": "osoba",
          "beklagter": "osoba", "anwalt_kl": "osoba", "anwalt_bekl": "osoba", "zeuge1": "osoba", "zeuge2": "osoba",
          "gutachter": "osoba", "zitat1": "cytat", "zitat2": "cytat", "zitat3": "cytat"},
    sekcje=[
        sekcja("caption", "naglowek",
               "{sad.nazwa}",
               "Aktenzeichen: {sad.sygnatura}",
               W("de_berufung", "Vorinstanz: {ctx.sad_pierwsza}, Aktenzeichen {ctx.sygn_pierwsza}"),
               "Verkündet am {ctx.wyrok_koncowy}",
               "IM NAMEN DES VOLKES",
               "URTEIL"),
        sekcja("parties", "akapit",
               "In dem Rechtsstreit",
               *erste("{klaeger.rodzaj:des Herrn|der Frau} {klaeger.pelne}, {klaeger.adres}"),
               W("de_berufung", "{klaeger.rodzaj:des Herrn|der Frau} {klaeger.pelne}, {klaeger.adres}"),
               *erste("{klaeger.rodzaj:– Kläger –|– Klägerin –}"),
               W("de_berufung", "{klaeger.rodzaj:– Kläger und Berufungsbeklagter –|– Klägerin und Berufungsbeklagte –}"),
               "Prozessbevollmächtigte: {anwalt_kl.rodzaj:Rechtsanwalt|Rechtsanwältin} {anwalt_kl.pelne}",
               "gegen",
               "{beklagter.rodzaj:Herrn|Frau} {beklagter.pelne}, {beklagter.adres}",
               *erste("{beklagter.rodzaj:– Beklagter –|– Beklagte –}"),
               W("de_berufung", "{beklagter.rodzaj:– Beklagter und Berufungskläger –|– Beklagte und Berufungsklägerin –}"),
               "Prozessbevollmächtigte: {anwalt_bekl.rodzaj:Rechtsanwalt|Rechtsanwältin} {anwalt_bekl.pelne}"),
        sekcja("panel", "akapit",
               W("de_amtsgericht", "hat das {sad.nazwa} durch {richter1.rodzaj:den Richter|die Richterin} am "
                 "Amtsgericht {richter1.pelne} auf Grund der mündlichen Verhandlung vom {ctx.rozprawa_koncowa} für "
                 "Recht erkannt:"),
               W("de_landgericht", "hat das {sad.nazwa} – Zivilkammer – durch {richter1.rodzaj:den Vorsitzenden "
                 "Richter|die Vorsitzende Richterin} am Landgericht {richter1.pelne}, {richter2.rodzaj:den "
                 "Richter|die Richterin} am Landgericht {richter2.pelne} und {richter3.rodzaj:den Richter|die "
                 "Richterin} am Landgericht {richter3.pelne} auf Grund der mündlichen Verhandlung vom "
                 "{ctx.rozprawa_koncowa} für Recht erkannt:"),
               W("de_einzelrichter", "hat das {sad.nazwa} durch {richter1.rodzaj:den Richter|die Richterin} am "
                 "Landgericht {richter1.pelne} als Einzelrichter auf Grund der mündlichen Verhandlung vom "
                 "{ctx.rozprawa_koncowa} für Recht erkannt:"),
               W("de_berufung", "hat das {sad.nazwa} – Berufungskammer – durch {richter1.rodzaj:den Vorsitzenden "
                 "Richter|die Vorsitzende Richterin} am Landgericht {richter1.pelne}, {richter2.rodzaj:den "
                 "Richter|die Richterin} am Landgericht {richter2.pelne} und {richter3.rodzaj:den Richter|die "
                 "Richterin} am Landgericht {richter3.pelne} auf Grund der mündlichen Verhandlung vom "
                 "{ctx.rozprawa_koncowa} für Recht erkannt:")),
        sekcja("tenor", "akapit",
               *erste("1. {beklagter.rodzaj:Der Beklagte wird|Die Beklagte wird} verurteilt, an {klaeger.rodzaj:den "
                      "Kläger|die Klägerin} {ctx.zasadzona} nebst Zinsen in Höhe von fünf Prozentpunkten über dem "
                      "Basiszinssatz seit dem {ctx.termin_wezwania} zu zahlen."),
               *erste("2. Im Übrigen wird die Klage abgewiesen."),
               *erste("3. Von den Kosten des Rechtsstreits tragen {klaeger.rodzaj:der Kläger|die Klägerin} "
                      "{ctx.kosten_kl} % und {beklagter.rodzaj:der Beklagte|die Beklagte} {ctx.kosten_bekl} %."),
               *erste("4. Das Urteil ist vorläufig vollstreckbar. Die Parteien dürfen die Vollstreckung der jeweils "
                      "anderen Partei durch Sicherheitsleistung in Höhe von 110 % des aufgrund des Urteils "
                      "vollstreckbaren Betrages abwenden, wenn nicht die andere Partei vor der Vollstreckung "
                      "Sicherheit in Höhe von 110 % des jeweils zu vollstreckenden Betrages leistet."),
               *erste("Der Streitwert wird auf {ctx.glowna} festgesetzt."),
               W("de_berufung", "1. Die Berufung {beklagter.rodzaj:des Beklagten|der Beklagten} gegen das Urteil des "
                 "Amtsgerichts vom {ctx.wyrok} – {ctx.sygn_pierwsza} – wird zurückgewiesen."),
               W("de_berufung", "2. {beklagter.rodzaj:Der Beklagte hat|Die Beklagte hat} die Kosten des "
                 "Berufungsverfahrens zu tragen."),
               W("de_berufung", "3. Dieses und das angefochtene Urteil sind vorläufig vollstreckbar. "
                 "{beklagter.rodzaj:Der Beklagte darf|Die Beklagte darf} die Vollstreckung durch Sicherheitsleistung in "
                 "Höhe von 110 % des aufgrund des Urteils vollstreckbaren Betrages abwenden, wenn nicht "
                 "{klaeger.rodzaj:der Kläger|die Klägerin} vor der Vollstreckung Sicherheit in Höhe von 110 % des "
                 "jeweils zu vollstreckenden Betrages leistet."),
               W("de_berufung", "4. Die Revision wird nicht zugelassen."),
               W("de_berufung", "Der Streitwert des Berufungsverfahrens wird auf {ctx.zasadzona} festgesetzt.")),
        sekcja("tatbestand_titel", "akapit", "Tatbestand"),
        sekcja("tatbestand", "akapit",
               *erste("Die Parteien streiten um die Rückzahlung eines Darlehens."),
               *erste("{klaeger.rodzaj:Der Kläger|Die Klägerin} gewährte {beklagter.rodzaj:dem Beklagten|der "
                      "Beklagten} am {ctx.umowa} ein Darlehen über {ctx.glowna}, das bis zum {ctx.termin_platnosci} "
                      "zurückzuzahlen war. Zahlungen erfolgten nicht in voller Höhe."),
               *erste("Mit Schreiben vom {ctx.wezwanie} forderte {klaeger.rodzaj:der Kläger|die Klägerin} "
                      "{beklagter.rodzaj:den Beklagten|die Beklagte} zur Zahlung bis zum {ctx.termin_wezwania} auf."),
               *erste("{klaeger.rodzaj:Der Kläger beantragt|Die Klägerin beantragt}, {beklagter.rodzaj:den "
                      "Beklagten|die Beklagte} zu verurteilen, {ctx.glowna} nebst Zinsen an {klaeger.rodzaj:ihn|sie} zu "
                      "zahlen."),
               *erste("{beklagter.rodzaj:Der Beklagte beantragt|Die Beklagte beantragt}, die Klage abzuweisen. "
                      "{beklagter.rodzaj:Er|Sie} wendet ein, einen Teil der Darlehenssumme bereits zurückgezahlt zu "
                      "haben."),
               *erste("Das Gericht hat Beweis erhoben durch Vernehmung {zeuge1.rodzaj:des Zeugen|der Zeugin} "
                      "{zeuge1.pelne} und {zeuge2.rodzaj:des Zeugen|der Zeugin} {zeuge2.pelne} sowie durch Einholung eines Gutachtens {gutachter.rodzaj:des Sachverständigen|der "
                      "Sachverständigen} {gutachter.pelne}. Wegen des Ergebnisses wird auf die Sitzungsniederschrift "
                      "vom {ctx.rozprawa_koncowa} Bezug genommen."),
               *erste("Wegen der weiteren Einzelheiten wird auf die gewechselten Schriftsätze nebst Anlagen "
                      "Bezug genommen."),
               W("de_berufung", "Die Parteien streiten in der Berufungsinstanz um die Verurteilung zur Rückzahlung eines "
                 "Darlehens."),
               W("de_berufung", "Das Amtsgericht hat {beklagter.rodzaj:den Beklagten|die Beklagte} mit Urteil vom "
                 "{ctx.wyrok} verurteilt, an {klaeger.rodzaj:den Kläger|die Klägerin} {ctx.zasadzona} nebst Zinsen zu "
                 "zahlen, und die Klage im Übrigen abgewiesen."),
               W("de_berufung", "Gegen dieses Urteil hat {beklagter.rodzaj:der Beklagte|die Beklagte} am {ctx.apelacja} "
                 "Berufung eingelegt und diese begründet. {beklagter.rodzaj:Er|Sie} rügt eine fehlerhafte "
                 "Beweiswürdigung."),
               W("de_berufung", "{beklagter.rodzaj:Der Beklagte beantragt|Die Beklagte beantragt}, das Urteil des "
                 "Amtsgerichts abzuändern und die Klage insgesamt abzuweisen. {klaeger.rodzaj:Der Kläger "
                 "beantragt|Die Klägerin beantragt}, die Berufung zurückzuweisen."),
               W("de_berufung", "Die Kammer hat am {ctx.rozprawa_apel} mündlich verhandelt. Wegen der weiteren "
                 "Einzelheiten wird auf die Feststellungen im angefochtenen Urteil und die Schriftsätze der Parteien "
                 "verwiesen.")),
        sekcja("gruende_titel", "akapit", "Entscheidungsgründe"),
        sekcja("gruende", "akapit",
               W("de_amtsgericht", "I. Die zulässige Klage ist teilweise begründet. Das Amtsgericht ist nach §§ 23 "
                 "Nr. 1, 71 GVG sachlich und nach § 13 ZPO örtlich zuständig."),
               W("de_landgericht", "I. Die zulässige Klage ist teilweise begründet. Das Landgericht ist nach §§ 23 "
                 "Nr. 1, 71 Abs. 1 GVG sachlich und nach § 13 ZPO örtlich zuständig."),
               W("de_einzelrichter", "I. Die zulässige Klage ist teilweise begründet. Das Landgericht ist nach §§ 23 "
                 "Nr. 1, 71 Abs. 1 GVG sachlich und nach § 13 ZPO örtlich zuständig; der Einzelrichter entscheidet "
                 "nach § 348 Abs. 1 ZPO."),
               *erste("II. 1. {klaeger.rodzaj:Der Kläger|Die Klägerin} hat gegen {beklagter.rodzaj:den "
                      "Beklagten|die Beklagte} einen Anspruch auf Rückzahlung des Darlehens in Höhe von "
                      "{ctx.zasadzona} aus § 488 Abs. 1 Satz 2 BGB. Die Darlehensgewährung am {ctx.umowa} steht nach der "
                      "Beweisaufnahme fest."),
               *erste("2. Nach der Aussage {zeuge1.rodzaj:des Zeugen|der Zeugin} {zeuge1.pelne}, die das Gericht für "
                      "glaubhaft hält, und dem Gutachten {gutachter.rodzaj:des Sachverständigen|der "
                      "Sachverständigen} {gutachter.pelne} hat {beklagter.rodzaj:der Beklagte|die Beklagte} "
                      "Teilzahlungen geleistet, die von der Hauptforderung abzuziehen sind."),
               *erste("3. Nach der Rechtsprechung trägt der Darlehensgeber die Beweislast für die Auszahlung und die "
                      "Rückzahlungsabrede ({zitat1.sygnatura}), der Darlehensnehmer die für die Rückzahlung "
                      "({zitat2.sygnatura}; {zitat3.sygnatura})."),
               *erste("4. Der Zinsanspruch folgt aus §§ 286 Abs. 1, 288 Abs. 1 BGB. Verzug trat mit Ablauf der Frist am "
                      "{ctx.termin_wezwania} ein; die Zinsen sind daher seit diesem Tag zu zahlen. Soweit {klaeger.rodzaj:der Kläger|die Klägerin} mehr verlangt, ist die Klage unbegründet."),
               *erste("III. Die Kostenentscheidung beruht auf § 92 Abs. 1 Satz 1 ZPO, die Entscheidung zur "
                      "vorläufigen Vollstreckbarkeit auf §§ 709, 711 ZPO."),
               W("de_amtsgericht", "IV. Rechtsbehelfsbelehrung: Gegen dieses Urteil kann Berufung eingelegt werden, wenn "
                 "der Wert des Beschwerdegegenstandes 600 Euro übersteigt. Die Berufung ist innerhalb eines Monats "
                 "nach Zustellung des Urteils beim zuständigen Landgericht einzulegen (§§ 511, 517 ZPO)."),
               W("de_berufung", "I. Die Berufung ist zulässig, insbesondere form- und fristgerecht eingelegt "
                 "(§§ 511, 517, 519, 520 ZPO). In der Sache bleibt sie ohne Erfolg."),
               W("de_berufung", "II. 1. Das Amtsgericht hat der Klage zu Recht teilweise stattgegeben. Der Anspruch auf "
                 "Rückzahlung des Darlehens folgt aus § 488 Abs. 1 Satz 2 BGB."),
               W("de_berufung", "2. Die Beweiswürdigung des Amtsgerichts ist nicht zu beanstanden (§ 529 Abs. 1 Nr. 1 "
                 "ZPO). Konkrete Anhaltspunkte für Zweifel an den Feststellungen, wie sie {beklagter.rodzaj:der "
                 "Beklagte|die Beklagte} geltend macht, bestehen nicht. Die Aussage {zeuge1.rodzaj:des Zeugen|der "
                 "Zeugin} {zeuge1.pelne} hat das Amtsgericht nachvollziehbar gewürdigt."),
               W("de_berufung", "3. Nach der Rechtsprechung des Bundesgerichtshofs ist das Berufungsgericht an die "
                 "Tatsachenfeststellungen der ersten Instanz gebunden, soweit keine Zweifel bestehen "
                 "({zitat1.sygnatura}; {zitat2.sygnatura}). Eine erneute Beweisaufnahme ist nur geboten, wenn das "
                 "Berufungsgericht die Beweiswürdigung abweichend vornehmen will ({zitat3.sygnatura})."),
               W("de_berufung", "III. Die Kostenentscheidung beruht auf § 97 Abs. 1 ZPO, die Entscheidung zur "
                 "vorläufigen Vollstreckbarkeit auf §§ 708 Nr. 10, 711 ZPO."),
               W("de_berufung", "IV. Die Revision war nicht zuzulassen, weil die Rechtssache keine grundsätzliche "
                 "Bedeutung hat und weder die Fortbildung des Rechts noch die Sicherung einer einheitlichen "
                 "Rechtsprechung eine Entscheidung des Revisionsgerichts erfordern (§ 543 Abs. 2 ZPO).")),
        sekcja("signatures", "podpis",
               W("de_amtsgericht", "{richter1.pelne}"), W("de_einzelrichter", "{richter1.pelne}"),
               W("de_landgericht", "{richter1.pelne}"), W("de_landgericht", "{richter2.pelne}"),
               W("de_landgericht", "{richter3.pelne}"),
               W("de_berufung", "{richter1.pelne}"), W("de_berufung", "{richter2.pelne}"),
               W("de_berufung", "{richter3.pelne}")),
        sekcja("footer", "stopka", "{sad.nazwa} | {sad.sygnatura} | Seite 1"),
    ],
    metadane={"subject": "Urteil in einem Rechtsstreit auf Rückzahlung eines Darlehens", "case": "{sad.sygnatura}"},
)
