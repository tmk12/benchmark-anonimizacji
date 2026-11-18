"""Karta wypisowa ze szpitala: NHS discharge summary (Wielka Brytania, numer NHS, GMC) albo hospital discharge summary
(USA, NPI, HIPAA); dane pacjenta, rozpoznania ICD-10, przebieg, leki, zalecenia. Daty z `Kontekst`."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="en", typ="med_wypis", warianty=("gb", "us"),
    profil="cardiology",
    role={"hospital": "placowka", "patient": "pacjent", "physician": "lekarz", "consultant": "lekarz",
          "relative": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{hospital.nazwa}",
               W("gb", "{hospital.adres} | tel. {hospital.telefon}"),
               W("us", "{hospital.adres} | EIN {hospital.ein} | tel. {hospital.telefon}")),
        sekcja("title", "akapit",
               W("gb", "DISCHARGE SUMMARY – CARDIOLOGY WARD"),
               W("us", "HOSPITAL DISCHARGE SUMMARY – CARDIOLOGY SERVICE")),
        sekcja("patient", "akapit",
               "Patient: {patient.pelne}, date of birth {patient.data_ur}",
               W("gb", "NHS number: {patient.nhs} | National Insurance number: {patient.nino}"),
               W("us", "Social Security No.: {patient.ssn}"),
               "Home address: {patient.adres}, tel. {patient.telefon}",
               "Admitted: {ctx.przyjecie}. Discharged: {ctx.wypis}. Admission type: emergency.",
               min=4, max=5),
        sekcja("diagnoses", "akapit",
               W("gb", "Primary diagnosis (ICD-10): {patient.diagnoza}"),
               W("us", "Principal diagnosis (ICD-10-CM): {patient.diagnoza}"),
               "Secondary diagnoses: {patient.diagnoza2}; {patient.diagnoza3}"),
        sekcja("history", "akapit",
               "Presenting complaint and examination: admitted with progressive breathlessness on exertion, chest "
               "pain and ankle swelling. On examination there was tachycardia, bibasal crackles, blood pressure "
               "165/95 mmHg and oxygen saturation of 93% on room air.",
               W("gb", "Investigations: full blood count, CRP, creatinine, electrolytes, high-sensitivity troponin, "
                 "NT-proBNP, urinalysis, ECG, chest X-ray and transthoracic echocardiogram. Detailed results are in "
                 "the clinical record."),
               W("us", "Studies: CBC with differential, CRP, basic metabolic panel, high-sensitivity troponin, "
                 "BNP, urinalysis, EKG, chest X-ray and transthoracic echocardiogram. Detailed results are in the "
                 "medical record."),
               W("gb", "Hospital course: treated with supplemental oxygen, intravenous loop diuretics, prophylactic "
                 "anticoagulation and antihypertensive therapy. The patient improved clinically, the oedema "
                 "resolved and blood pressure stabilised."),
               W("us", "Hospital course: treated with supplemental oxygen, intravenous loop diuretics, prophylactic "
                 "anticoagulation and antihypertensive therapy. The patient improved clinically, the edema "
                 "resolved and blood pressure stabilized."),
               "There were no complications or adverse events during the admission. Diabetes and cardiology "
               "consultations were completed.",
               min=3, max=4),
        sekcja("discharge", "akapit",
               W("gb", "Advice on discharge: low-sodium diet, fluid restriction to 1.5 litres a day, daily morning "
                 "weights, no strenuous exertion for two weeks and complete cessation of smoking."),
               W("us", "Discharge instructions: low-sodium diet, fluid restriction to 1.5 liters a day, daily morning "
                 "weights, no strenuous exertion for two weeks and complete cessation of smoking."),
               W("gb", "Medicines on discharge (TTO): {patient.lek} as established at clinic; {patient.lek2} once "
                 "daily in the morning; {patient.lek3} as directed by the cardiology team."),
               W("us", "Discharge medications: {patient.lek} per outpatient regimen; {patient.lek2} once daily in the "
                 "morning; {patient.lek3} as directed by cardiology."),
               W("gb", "Follow-up: cardiology outpatient clinic on {ctx.kontrola}, with blood tests (full blood "
                 "count, creatinine, potassium). Please bring this summary to the appointment."),
               W("us", "Follow-up: cardiology clinic visit on {ctx.kontrola}, with labs (CBC, basic metabolic "
                 "panel, potassium). Please bring this summary to the appointment."),
               W("gb", "A fit note covering absence from work until {ctx.zwolnienie_do} has been issued."),
               W("us", "A work excuse covering absence until {ctx.zwolnienie_do} has been provided."),
               min=4, max=5),
        sekcja("information", "akapit",
               "Information about the condition and the planned treatment was given to the patient on the day of "
               "discharge; with the patient's consent information may be shared with {relative.pelne} "
               "(tel. {relative.telefon}).",
               W("gb", "This summary has been sent to the patient's GP. It contains health data, which is special "
                 "category data under Article 9 of the UK GDPR."),
               W("us", "This summary contains protected health information subject to the Health Insurance "
                 "Portability and Accountability Act (HIPAA) Privacy Rule."),
               W("gb", "The patient was advised to attend the emergency department or call 999 if chest pain, "
                 "fainting or worsening breathlessness occurs."),
               W("us", "The patient was advised to go to the emergency department or call 911 if chest pain, "
                 "fainting or worsening shortness of breath occurs."),
               min=2, max=3),
        sekcja("clinicians", "akapit",
               W("gb", "Responsible doctor: {physician.pelne}, GMC number {physician.gmc}"),
               W("us", "Attending physician: {physician.pelne}, NPI {physician.npi}"),
               W("gb", "Consultant cardiologist: {consultant.pelne}, GMC number {consultant.gmc}"),
               W("us", "Cardiology service chief: {consultant.pelne}, NPI {consultant.npi}")),
        sekcja("signatures", "podpis", "{physician.pelne}", "{consultant.pelne}"),
        sekcja("footer", "stopka", "{hospital.nazwa} | {hospital.adres} | tel. {hospital.telefon} | {hospital.email}"),
    ],
    metadane={"author": "{physician.pelne}", "subject": "Discharge summary"},
)
