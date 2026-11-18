"""Ärztlicher Entlassungsbrief (Arztbrief) einer Klinik für Kardiologie: Patientendaten (Geburtsdatum, Versichertennummer),
Diagnosen nach ICD-10-GM, Anamnese, Befunde, Verlauf, Medikation bei Entlassung, Procedere und Kontrolltermin. Daten aus
`Kontekst`: Aufnahme < Entlassung < Kontrolle; Arbeitsunfähigkeit bis `zwolnienie_do`. Ärzte: Oberarzt und Chefarzt."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="de", typ="med_wypis", profil="kardiologie",
    role={"klinik": "placowka", "patient": "pacjent", "oberarzt": "lekarz", "chefarzt": "lekarz",
          "angehoeriger": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{klinik.nazwa}",
               "{klinik.adres} | Tel. {klinik.telefon} | USt-IdNr. {klinik.vat}"),
        sekcja("title", "akapit",
               "ARZTBRIEF – ENTLASSUNG AUS DER KLINIK FÜR KARDIOLOGIE",
               "Sehr geehrte Kolleginnen und Kollegen,"),
        sekcja("patient", "akapit",
               "wir berichten über {patient.rodzaj:Herrn|Frau} {patient.pelne}, geboren am {patient.data_ur}, "
               "wohnhaft {patient.adres}.",
               "Krankenversicherung: gesetzlich, Versichertennummer (KVNR) {patient.kvnr} | Telefon "
               "{patient.telefon}",
               "Aufnahme: {ctx.przyjecie}. Entlassung: {ctx.wypis}. Aufnahmeart: notfallmäßig.",
               min=3, max=3),
        sekcja("diagnoses", "akapit",
               "Hauptdiagnose (ICD-10-GM): {patient.diagnoza}",
               "Nebendiagnosen: {patient.diagnoza2}; {patient.diagnoza3}"),
        sekcja("history", "akapit",
               "Anamnese und Aufnahmebefund: Aufnahme wegen zunehmender Belastungsdyspnoe, Thoraxschmerzen und "
               "Beinödemen. Bei der Untersuchung zeigten sich eine Tachykardie, beidseitige basale Rasselgeräusche, ein "
               "Blutdruck von 165/95 mmHg und eine Sauerstoffsättigung von 93 % unter Raumluft.",
               "Diagnostik: Labor einschließlich Blutbild, CRP, Kreatinin, Elektrolyten, hochsensitivem Troponin und "
               "NT-proBNP, Urinstatus, EKG, Röntgen-Thorax und transthorakale Echokardiographie. Die ausführlichen "
               "Befunde liegen der Krankenakte bei.",
               "Verlauf: Unter Sauerstoffgabe, intravenöser Schleifendiuretika-Therapie, Thromboseprophylaxe und "
               "antihypertensiver Medikation besserte sich der Zustand rasch, die Ödeme bildeten sich zurück und der "
               "Blutdruck stabilisierte sich.",
               "Komplikationen oder unerwünschte Ereignisse traten während des stationären Aufenthaltes nicht auf. "
               "Eine konsiliarische Mitbetreuung war nicht erforderlich.",
               min=4, max=4),
        sekcja("discharge", "akapit",
               "Empfehlungen: salzarme Kost, Trinkmengenbeschränkung auf 1,5 Liter täglich, tägliche Gewichtskontrolle "
               "am Morgen, in den nächsten zwei Wochen keine schweren körperlichen Belastungen, vollständiger "
               "Nikotinverzicht.",
               "Medikation bei Entlassung: {patient.lek} 1-0-0; {patient.lek2} 1-0-0; {patient.lek3} 1-0-0. Dosisanpassungen "
               "erfolgen in der kardiologischen Ambulanz.",
               "Procedere: Wiedervorstellung in der kardiologischen Ambulanz am {ctx.kontrola} mit Labor vorab "
               "(Blutbild, Kreatinin, Kalium). Der Brief ist zum Termin mitzubringen.",
               "Arbeitsunfähigkeit: Eine Arbeitsunfähigkeitsbescheinigung wurde bis zum {ctx.zwolnienie_do} "
               "ausgestellt.",
               min=4, max=4),
        sekcja("information", "akapit",
               "{patient.rodzaj:Der Patient|Die Patientin} wurde am Entlassungstag über Erkrankung und Therapie "
               "aufgeklärt; mit Einwilligung darf Auskunft an {angehoeriger.pelne} (Tel. {angehoeriger.telefon}) "
               "erteilt werden.",
               "Dieser Brief enthält Gesundheitsdaten im Sinne des Art. 9 DSGVO und unterliegt der ärztlichen "
               "Schweigepflicht (§ 203 StGB).",
               "Bei Brustschmerzen, Ohnmacht oder zunehmender Atemnot soll der Rettungsdienst unter der 112 "
               "gerufen werden.",
               min=2, max=3),
        sekcja("clinicians", "akapit",
               "Mit freundlichen kollegialen Grüßen",
               "{oberarzt.rodzaj:Oberarzt|Oberärztin} Dr. med. {oberarzt.pelne}",
               "{chefarzt.rodzaj:Chefarzt|Chefärztin} der Klinik für Kardiologie, Prof. Dr. med. {chefarzt.pelne}"),
        sekcja("signatures", "podpis", "{oberarzt.pelne}", "{chefarzt.pelne}"),
        sekcja("footer", "stopka", "{klinik.nazwa} | {klinik.adres} | Tel. {klinik.telefon} | {klinik.email}"),
    ],
    metadane={"author": "{oberarzt.pelne}", "subject": "Arztbrief – Entlassung"},
)
