"""Zaświadczenie lekarskie: fit note (Statement of Fitness for Work, Wielka Brytania) albo doctor's note (USA) do sądu,
usprawiedliwiające nieobecność na rozprawie; rozpoznanie ICD-10, leki, lekarz z numerem GMC/NPI. Daty z `Kontekst`."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="en", typ="med_zaswiadczenie", warianty=("gb", "us"),
    profil="internal",
    role={"clinic": "placowka", "patient": "pacjent", "doctor": "lekarz", "matter": "sprawa", "court": "sad"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{clinic.nazwa}",
               W("gb", "Outpatient department | {clinic.adres} | tel. {clinic.telefon}"),
               W("us", "Internal Medicine Clinic | {clinic.adres} | tel. {clinic.telefon}")),
        sekcja("place", "akapit", "{clinic.miasto}, {ctx.zas_wystaw}"),
        sekcja("title", "akapit",
               W("gb", "STATEMENT OF FITNESS FOR WORK (FIT NOTE) AND MEDICAL CERTIFICATE"),
               W("us", "PHYSICIAN'S STATEMENT – MEDICAL EXCUSE FROM COURT APPEARANCE")),
        sekcja("body", "akapit",
               W("gb", "I certify that I have assessed {patient.pelne}, born {patient.data_ur}, NHS number "
                 "{patient.nhs}, of {patient.adres}, who is under the care of this clinic."),
               W("us", "This is to certify that {patient.pelne}, date of birth {patient.data_ur}, of "
                 "{patient.adres}, is a patient under the care of this clinic."),
               "Diagnosis: {patient.diagnoza}. Co-existing conditions: {patient.diagnoza2}.",
               "On {ctx.zas_od} {patient.pelne}'s health deteriorated, with an exacerbation of the underlying "
               "condition requiring drug treatment, including {patient.lek} and {patient.lek2}. Reduced activity "
               "is advised from {ctx.zas_od} to {ctx.zas_do}.",
               min=3, max=3),
        sekcja("capacity", "akapit",
               W("gb", "In my opinion {patient.rodzaj:he|she} is not fit for work and is unable to travel or sit for "
                 "more than two hours; this also applies to the hearing listed for {ctx.rozprawa}."),
               W("us", "In my medical opinion {patient.rodzaj:he|she} is unable to travel or sit for more than two "
                 "hours and cannot attend the hearing scheduled for {ctx.rozprawa}."),
               "This certificate is issued at {patient.rodzaj:his|her} request for submission to the court in the "
               "matter {matter.sygnatura} as an excuse for non-attendance; the court dealing with the case is the "
               "{court.nazwa}.",
               "{patient.rodzaj:He|She} should have a clinical review when the period ends, and should contact a "
               "family doctor or attend the emergency department if symptoms worsen.",
               min=3, max=3),
        sekcja("notice", "akapit",
               "This certificate is based on an examination carried out on {ctx.zas_wystaw} and on the clinic's "
               "medical records.",
               W("gb", "A fit note is not a certificate of incapacity for the purposes of Statutory Sick Pay unless "
                 "the employer accepts it; knowingly giving a false certificate may be a criminal offence."),
               W("us", "This note is not a disability determination. Knowingly issuing a false medical certificate "
                 "may constitute fraud under state law."),
               W("gb", "The document contains health data and has been handed to the patient or an authorised "
                 "person."),
               W("us", "The document contains health information and has been handed to the patient or an "
                 "authorized person."),
               min=3, max=4),
        sekcja("doctor", "akapit",
               W("gb", "Certifying doctor: {doctor.pelne}, GMC number {doctor.gmc}, general practitioner"),
               W("us", "Treating physician: {doctor.pelne}, NPI {doctor.npi}, board-certified internist"),
               "Stamp of the doctor and the clinic"),
        sekcja("signature", "podpis", "{doctor.pelne}"),
        sekcja("footer", "stopka",
               W("gb", "{clinic.nazwa} | {clinic.adres} | tel. {clinic.telefon} | {clinic.email}"),
               W("us", "{clinic.nazwa} | {clinic.adres} | EIN {clinic.ein} | {clinic.email}")),
    ],
    metadane={"author": "{doctor.pelne}", "subject": "Medical certificate"},
)
