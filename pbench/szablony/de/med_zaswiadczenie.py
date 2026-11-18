"""Ärztliche Bescheinigung einer internistischen Praxis zur Vorlage beim Amtsgericht oder Landgericht (Terminsverlegung
wegen Verhandlungsunfähigkeit): Diagnosen nach ICD-10-GM, Ruhe von `zas_od` bis `zas_do`, Termin `rozprawa`, Hinweis auf
die elektronische Arbeitsunfähigkeitsbescheinigung. Daten: zas_od < zas_wystaw < rozprawa < zas_do; Aktenzeichen passend zur
Instanz. Arzt mit Lebenslanger Arztnummer (LANR) als NR_ID."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="de", typ="med_zaswiadczenie", warianty=("de_amtsgericht", "de_landgericht"), profil="innere",
    role={"praxis": "placowka", "patient": "pacjent", "arzt": "lekarz", "gericht": "sad"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{praxis.nazwa}",
               "Ambulanz für Innere Medizin",
               "{praxis.adres} | Tel. {praxis.telefon} | USt-IdNr. {praxis.vat}"),
        sekcja("place", "akapit", "{praxis.miasto}, den {ctx.zas_wystaw}"),
        sekcja("title", "akapit",
               "ÄRZTLICHE BESCHEINIGUNG",
               "zur Vorlage bei Gericht"),
        sekcja("body", "akapit",
               "Hiermit bescheinige ich, Dr. med. {arzt.pelne} (LANR {arzt.lanr}), dass sich "
               "{patient.rodzaj:Herr|Frau} {patient.pelne}, geboren am {patient.data_ur}, wohnhaft {patient.adres}, "
               "Versichertennummer {patient.kvnr}, in meiner Behandlung befindet.",
               "Bei {patient.rodzaj:dem Patienten|der Patientin} bestehen {patient.diagnoza} sowie als Vorerkrankung "
               "{patient.diagnoza2}.",
               "Seit dem {ctx.zas_od} besteht eine Verschlechterung der Grunderkrankung; hinzu kommt "
               "{patient.diagnoza3}. Ärztlich angeordnet sind Bettruhe und Schonung vom {ctx.zas_od} bis zum "
               "{ctx.zas_do}.",
               min=3, max=3),
        sekcja("capacity", "akapit",
               "Aus ärztlicher Sicht ist {patient.rodzaj:der Patient|die Patientin} in dieser Zeit nicht verhandlungsfähig; "
               "die Anreise zum Gericht ist {patient.rodzaj:ihm|ihr} nicht zuzumuten. Das betrifft den Termin am "
               "{ctx.rozprawa} vor dem {gericht.nazwa} im Verfahren {gericht.sygnatura}.",
               "Die aktuelle Medikation lautet: {patient.lek}, {patient.lek2} und {patient.lek3}.",
               min=2, max=2),
        sekcja("notice", "akapit",
               "Diese Bescheinigung beruht auf der Untersuchung vom {ctx.zas_wystaw} und den Daten der Patientenakte; "
               "sie wird auf Wunsch {patient.rodzaj:des Patienten|der Patientin} zur Vorlage bei Gericht ausgestellt.",
               "Die enthaltenen Gesundheitsdaten unterliegen der ärztlichen Schweigepflicht (§ 203 StGB) und dem "
               "Schutz des Art. 9 DSGVO.",
               "Die Bescheinigung ersetzt nicht die elektronische Arbeitsunfähigkeitsbescheinigung (eAU), die den "
               "Krankenkassen und Arbeitgebern gesondert übermittelt wird.",
               min=2, max=3),
        sekcja("doctor", "akapit",
               "{arzt.rodzaj:Facharzt|Fachärztin} für Innere Medizin: Dr. med. {arzt.pelne}, Tel. {arzt.telefon}."),
        sekcja("signature", "podpis", "{arzt.pelne}"),
        sekcja("footer", "stopka",
               "{praxis.nazwa} | {praxis.adres} | Tel. {praxis.telefon} | {praxis.email}"),
    ],
    metadane={"author": "{arzt.pelne}", "subject": "Ärztliche Bescheinigung"},
)
