"""Dienstleistungsvertrag mit einem Auftragnehmer aus der Ukraine: Name, Anschrift und Kennungen kyrillisch und transliteriert."""
from __future__ import annotations

from ....budowa import Szablon
from ..._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="de", typ="umowa", dorosli=True, znacz_encje=True, warianty=("cw", "tr"),
    role={"auftraggeber": "firma", "vertreter": "osoba", "auftragnehmer": "osoba_ua", "ansprechpartner": "osoba"},
    sekcje=[
        sekcja("naglowek", "naglowek",
               "{auftraggeber.nazwa}",
               "{auftraggeber.adres}"),
        sekcja("titel", "akapit",
               "DIENSTLEISTUNGSVERTRAG",
               "abgeschlossen am {ctx.dok} zwischen"),
        sekcja("parteien", "akapit",
               "{auftraggeber.nazwa}, {auftraggeber.adres}, vertreten durch {vertreter.pelne}, Geschäftsführung "
               "(nachfolgend „Auftraggeber“),",
               "und",
               "{auftragnehmer.pelne_im:t_s1} ({auftragnehmer.pelne_im:t_s2}), geboren am {auftragnehmer.data_ur}, "
               "{auftragnehmer.rodzaj:ukrainischer Staatsangehöriger|ukrainische Staatsangehörige}, wohnhaft in "
               "{auftragnehmer.adres:t_s1} ({auftragnehmer.adres:t_s2}), steuerliche Identifikationsnummer der "
               "Ukraine (РНОКПП) {auftragnehmer.rnokpp}, Reisepass Nr. {auftragnehmer.paszport} (nachfolgend "
               "„Auftragnehmer“)."),
        sekcja("gegenstand", "akapit",
               "§ 1 Vertragsgegenstand",
               "(1) Der Auftragnehmer übernimmt für den Auftraggeber Übersetzungs- und Dolmetscherleistungen "
               "(Ukrainisch–Deutsch) sowie die Betreuung ukrainischer Geschäftspartner.",
               "(2) Der Auftragnehmer erbringt die Leistungen weisungsfrei; fachlicher Ansprechpartner beim "
               "Auftraggeber ist {ansprechpartner.pelne}."),
        sekcja("verguetung", "akapit",
               "§ 2 Vergütung",
               "(1) Der Auftragnehmer erhält eine monatliche Vergütung von {ctx.um_wyn}, zahlbar innerhalb von "
               "14 Tagen nach Rechnungseingang.",
               "(2) Die Zahlung erfolgt auf das Konto des Auftragnehmers, IBAN {auftragnehmer.rachunek}.",
               "(3) Erreichbarkeit des Auftragnehmers: Tel. {auftragnehmer.telefon}, E-Mail "
               "{auftragnehmer.email}."),
        sekcja("angaben", "akapit",
               "§ 3 Personenbezogene Angaben",
               "(1) Der Auftraggeber verarbeitet die personenbezogenen Daten, einschließlich der Nummer "
               "{auftragnehmer.rnokpp}, ausschließlich zur Durchführung dieses Vertrags gemäß Art. 6 Abs. 1 "
               "Buchst. b DSGVO.",
               W("tr", "(2) Der Auftragnehmer bestätigt, dass seine Angaben mit dem Ausweisdokument übereinstimmen und "
                       "dass sein Name in den Unterlagen des Auftraggebers auch als {auftragnehmer.pelne_im:t_s2}, "
                       "{auftragnehmer.pelne_im:t_s3} oder {auftragnehmer.pelne_im:t_s4} geführt werden kann; alle "
                       "Schreibweisen betreffen dieselbe Person.")),
        sekcja("laufzeit", "akapit",
               "§ 4 Laufzeit",
               "Der Vertrag beginnt am {ctx.od_dnia} und läuft auf unbestimmte Zeit. Er kann von beiden Seiten mit "
               "einer Frist von 30 Tagen zum Monatsende schriftlich gekündigt werden."),
        sekcja("unterschrift_text", "akapit", "Unterschrift des Auftragnehmers:"),
        sekcja("unterschrift", "podpis", "{auftragnehmer.pelne_im:t_s1}"),
        sekcja("fusszeile", "stopka", "{auftraggeber.nazwa} | {auftraggeber.adres} | {auftraggeber.email}"),
    ],
    metadane={"author": "{vertreter.pelne}", "subject": "Dienstleistungsvertrag"},
)
