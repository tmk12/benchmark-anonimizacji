"""Informe clínico de alta hospitalaria (Servicio de Cardiología): datos del paciente (DNI/NIE, afiliación a la Seguridad
Social), diagnósticos CIE-10, evolución, tratamiento al alta, recomendaciones y seguimiento. Fechas de `Kontekst`:
ingreso < alta < revisión; baja laboral hasta `zwolnienie_do`."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="es", typ="med_wypis", profil="cardiologia",
    role={"hospital": "placowka", "paciente": "pacjent", "medico": "lekarz", "jefe": "lekarz", "familiar": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{hospital.nazwa}",
               "{hospital.adres} | CIF {hospital.cif} | tel. {hospital.telefon}"),
        sekcja("title", "akapit",
               "INFORME CLÍNICO DE ALTA HOSPITALARIA – SERVICIO DE CARDIOLOGÍA"),
        sekcja("patient", "akapit",
               "Paciente: {paciente.pelne}, {paciente.rodzaj:nacido|nacida} el {paciente.data_ur}",
               "DNI/NIE: {paciente.dni_nie} | N.º de afiliación a la Seguridad Social: {paciente.nuss}",
               "Domicilio: {paciente.adres}, tel. {paciente.telefon}",
               "Ingreso: {ctx.przyjecie}. Alta: {ctx.wypis}. Tipo de ingreso: urgente.",
               min=4, max=4),
        sekcja("diagnoses", "akapit",
               "Diagnóstico principal (CIE-10): {paciente.diagnoza}",
               "Diagnósticos secundarios: {paciente.diagnoza2}; {paciente.diagnoza3}"),
        sekcja("history", "akapit",
               "Motivo de ingreso y exploración: ingresó por disnea progresiva de "
               "esfuerzo, dolor torácico y edemas en los tobillos. A la exploración presentaba taquicardia, "
               "crepitantes bibasales, tensión arterial de 165/95 mmHg y saturación de oxígeno del 93 % con aire "
               "ambiente.",
               "Pruebas complementarias: hemograma, PCR, creatinina, iones, troponina de alta sensibilidad, NT-proBNP, "
               "sistemático de orina, electrocardiograma, radiografía de tórax y ecocardiograma transtorácico. "
               "Los resultados detallados constan en la historia clínica.",
               "Evolución: se trató con oxigenoterapia, diuréticos del asa por vía intravenosa, anticoagulación "
               "profiláctica y tratamiento antihipertensivo. La evolución fue favorable, los edemas remitieron y "
               "la tensión arterial se estabilizó.",
               "No se registraron complicaciones ni eventos adversos durante el ingreso. Se realizaron "
               "interconsultas con Endocrinología y con Nefrología.",
               min=3, max=4),
        sekcja("discharge", "akapit",
               "Recomendaciones al alta: dieta baja en sal, restricción de líquidos a 1,5 litros al día, pesarse "
               "cada mañana, evitar esfuerzos intensos durante dos semanas y abandono completo del tabaco.",
               "Tratamiento al alta: {paciente.lek}, según la pauta habitual; {paciente.lek2} una vez al día por "
               "la mañana; {paciente.lek3} según indique el Servicio de Cardiología.",
               "Seguimiento: consulta de Cardiología el {ctx.kontrola}, con analítica previa (hemograma, "
               "creatinina y potasio). Se ruega aportar este informe a la cita.",
               "Se emite parte de incapacidad temporal, que cubre la ausencia laboral hasta el {ctx.zwolnienie_do}.",
               min=4, max=4),
        sekcja("information", "akapit",
               "Se informó sobre la enfermedad y el tratamiento previsto el día del alta; con consentimiento, "
               "podrá facilitarse información a {familiar.pelne} (tel. {familiar.telefon}).",
               "Este informe contiene datos de salud, categoría especial de datos conforme al artículo 9 del "
               "Reglamento (UE) 2016/679 y a la Ley 41/2002, básica reguladora de la autonomía del paciente.",
               "Se indicó acudir a Urgencias o llamar al 112 si aparecen dolor torácico, desmayo o empeoramiento de "
               "la dificultad respiratoria.",
               min=2, max=3),
        sekcja("clinicians", "akapit",
               "Médico responsable: {medico.rodzaj:Dr.|Dra.} {medico.pelne}, n.º de colegiado {medico.colegiado}",
               "Jefe de Servicio de Cardiología: {jefe.rodzaj:Dr.|Dra.} {jefe.pelne}, n.º de colegiado "
               "{jefe.colegiado}"),
        sekcja("signatures", "podpis", "{medico.pelne}", "{jefe.pelne}"),
        sekcja("footer", "stopka", "{hospital.nazwa} | {hospital.adres} | tel. {hospital.telefon} | {hospital.email}"),
    ],
    metadane={"author": "{medico.pelne}", "subject": "Informe de alta hospitalaria"},
)
