"""Notatka służbowa prawnika z rozmowy z klientem po wypadku komunikacyjnym: attendance note (Wielka Brytania) albo
memo to file (USA); ustalenia, terminy, zadania. Daty i szkoda z `Kontekst`."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="en", typ="notatka", warianty=("gb", "us"),
    role={"firm": "kancelaria", "author": "osoba", "client": "osoba", "opponent": "osoba", "witness": "osoba",
          "insurer": "firma", "matter": "sprawa", "vehicle": "sprawa", "court": "sad"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{firm.nazwa}",
               "{firm.adres} | tel. {firm.telefon}"),
        sekcja("heading", "akapit",
               W("gb", "ATTENDANCE NOTE – PRIVILEGED AND CONFIDENTIAL"),
               W("us", "MEMORANDUM TO FILE – ATTORNEY-CLIENT PRIVILEGED / ATTORNEY WORK PRODUCT"),
               "Date: {ctx.dok}",
               "Prepared by: {author.pelne}, {firm.nazwa}",
               W("gb", "Matter reference: {matter.sygnatura}"),
               W("us", "File no.: {matter.sygnatura}")),
        sekcja("client", "akapit",
               "Client details: {client.pelne}, born {client.data_ur}, of {client.adres}, tel. {client.telefon}, "
               "email {client.email}.",
               W("gb", "{client.rodzaj:Mr|Ms} {client.nazwisko} prefers to be contacted by email between 8 am and "
                 "4 pm."),
               W("us", "{client.rodzaj:Mr.|Ms.} {client.nazwisko} prefers to be contacted by email between 8 a.m. "
                 "and 4 p.m."),
               W("gb", "Identity checked: National Insurance number {client.nino}. Source of funds confirmed."),
               W("us", "Identity checked against driver's license; Social Security No. {client.ssn} supplied for the "
                 "insurer's claim form."),
               "{client.rodzaj:He|She} will provide online portal access details in person; they are not to be "
               "written on the file. Portal login: {client.login}.",
               min=4, max=5),
        sekcja("facts", "akapit",
               "1. Facts. The collision occurred at a junction when the other driver failed to give way. The "
               "opposing vehicle, registration {vehicle.tablica}, was driven by {opponent.pelne} of "
               "{opponent.adres}.",
               "2. Loss. According to the garage's estimate the damage to the client's vehicle is {ctx.szkoda}. The "
               "other driver's insurer, {insurer.nazwa}, has paid an interim sum of {ctx.zaliczka_ub} but admits "
               "liability only in part.",
               "3. Witnesses. {witness.pelne} (tel. {witness.telefon}) saw the collision. The client says "
               "{witness.rodzaj:he|she} is willing to give a statement, which is yet to be confirmed.",
               W("gb", "4. The client has legal expenses insurance under the household policy; the insurer's consent "
                 "to costs must be obtained before proceedings are issued."),
               W("us", "4. The client's automobile policy includes medical payments coverage; the carrier's "
                 "subrogation claim should be noted before any settlement is signed."),
               min=3, max=5),
        sekcja("advice", "akapit",
               W("gb", "5. Advice. I explained that the claim is for damage to the vehicle and for personal injury "
                 "under the Pre-Action Protocol for Personal Injury Claims, and that the limitation period is three "
                 "years from the date of the accident under section 11 of the Limitation Act 1980."),
               W("us", "5. Advice. I explained that the claim sounds in negligence, that the statute of limitations "
                 "for personal injury varies by state, typically two to three years from the date of the accident, "
                 "and that comparative fault may reduce any recovery."),
               "6. I advised that a letter of claim to the insurer should be sent before {ctx.notatka_termin}, "
               "failing which we should consider issuing proceedings.",
               "7. Next hearing: the case is listed before the {court.nazwa} on {ctx.rozprawa}. The client's "
               "attendance is mandatory.",
               min=3, max=3),
        sekcja("documents", "akapit",
               "Documents requested from the client by the end of the week: vehicle registration document, the "
               "other driver's insurance details, photographs from the scene, the repair estimate and the police "
               "report. Originals remain with the client.",
               "Time recorded: one hour and twenty minutes. The note was dictated at the end of the meeting and "
               "reviewed by {author.pelne}.",
               min=1, max=2),
        sekcja("actions", "akapit",
               W("gb", "Actions: draft the claim letter to {insurer.nazwa} (author); open the file and diarise dates "
                 "(secretary); client to deliver the documents."),
               W("us", "Actions: draft the claim letter to {insurer.nazwa} (author); open the file and calendar "
                 "deadlines (paralegal); client to deliver the documents."),
               "Follow-up call with {client.nazwisko} scheduled for {ctx.notatka_termin}."),
        sekcja("signature", "podpis", "{author.pelne}"),
        sekcja("footer", "stopka",
               W("gb", "{firm.nazwa} | {firm.adres} | Company No. {firm.company_no} | VAT No. {firm.vat} | "
                 "tel. {firm.telefon}"),
               W("us", "{firm.nazwa} | {firm.adres} | EIN {firm.ein} | tel. {firm.telefon} | {firm.email}")),
    ],
    metadane={"author": "{author.pelne}", "subject": "Attendance note / memo to file"},
)
