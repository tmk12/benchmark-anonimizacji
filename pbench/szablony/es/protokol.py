"""Acta de la Junta General Ordinaria de una sociedad de responsabilidad limitada (Ley de Sociedades de Capital):
convocatoria, lista de asistentes en tabla, quórum, cuentas anuales, acuerdos, cierre. Capital en participaciones
sociales de 50 € (`Kontekst`: kapital3 = suma de participaciones × 50 €)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="es", typ="protokol", dorosli=True,
    role={"sociedad": "spolka", "presidente": "osoba", "secretario": "osoba", "socio1": "osoba", "socio2": "osoba",
          "socio3": "osoba", "gerente": "osoba", "nuevo": "osoba", "auditor": "osoba", "asesor": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{sociedad.nazwa}",
               "{sociedad.adres} | CIF {sociedad.cif} | {sociedad.registro}, Hoja {sociedad.company_no}"),
        sekcja("title", "akapit",
               "ACTA DE LA JUNTA GENERAL ORDINARIA DE SOCIOS DE {sociedad.nazwa}",
               "En {sociedad.miasto}, en el domicilio social, {sociedad.adres}, a {ctx.dok}, se reúnen los socios "
               "de la Sociedad en Junta General Ordinaria."),
        sekcja("open", "akapit",
               "{#}. CONSTITUCIÓN. Preside la reunión {presidente.rodzaj:Don|Doña} {presidente.pelne}, "
               "{presidente.rodzaj:Presidente|Presidenta} de la Junta, y actúa como "
               "{secretario.rodzaj:Secretario|Secretaria} {secretario.rodzaj:Don|Doña} {secretario.pelne}.",
               "{#}. CONVOCATORIA. {presidente.rodzaj:El Presidente|La Presidenta} hace constar que la Junta ha sido convocada por los administradores "
               "mediante comunicación individual y escrita a cada socio, con la antelación mínima de quince días "
               "que exige el artículo 176 de la Ley de Sociedades de Capital.",
               "{#}. ASISTENTES ADICIONALES. {gerente.pelne}, gerente de la Sociedad, asiste con voz pero sin voto.",
               min=3, max=3),
        sekcja("attendance_label", "akapit", "Lista de asistentes:"),
        sekcja("attendance", "komorka",
               "N.º | Socio | NIF | Participaciones | Votos\n"
               "1 | {socio1.pelne} | {socio1.dni_nie} | {ctx.udzialy1} | {ctx.udzialy1}\n"
               "2 | {socio2.pelne} | {socio2.dni_nie} | {ctx.udzialy2} | {ctx.udzialy2}\n"
               "3 | {socio3.pelne} | {socio3.dni_nie} | {ctx.udzialy3} | {ctx.udzialy3}\n"
               "Total | | | {ctx.udzialy_suma3} | {ctx.udzialy_suma3}"),
        sekcja("quorum", "akapit",
               "{#}. QUÓRUM. {presidente.rodzaj:El Presidente|La Presidenta} declara válidamente constituida la Junta, al estar presentes los titulares "
               "de la totalidad de las {ctx.udzialy_suma3} participaciones sociales en que se divide el capital.",
               "{#}. CAPITAL. El capital social es de {ctx.kapital3}, dividido en {ctx.udzialy_suma3} participaciones "
               "sociales iguales, acumulables e indivisibles, de 50 euros de valor nominal cada una, numeradas "
               "correlativamente.",
               min=2, max=2),
        sekcja("accounts", "akapit",
               "{#}. CUENTAS ANUALES. Se someten a la Junta las cuentas anuales del ejercicio anterior, junto con el "
               "informe de {auditor.pelne}, {auditor.rodzaj:auditor|auditora} de la Sociedad, que manifiesta que reflejan la imagen fiel del "
               "patrimonio y de la situación financiera.",
               "{#}. INFORME DE GESTIÓN. {gerente.pelne} presenta el informe sobre la marcha de la Sociedad y las "
               "perspectivas del ejercicio en curso.",
               "{#}. ASESORAMIENTO. {asesor.rodzaj:El asesor jurídico|La asesora jurídica} de la Sociedad, {asesor.pelne} (tel. {asesor.telefon}), "
               "informa de la normativa aplicable a los acuerdos que se someten a votación.",
               min=2, max=3),
        sekcja("resolutions", "akapit",
               "{#}. NOMBRAMIENTO. Se acuerda nombrar {nuevo.rodzaj:administrador|administradora} de la Sociedad a {nuevo.pelne}, con domicilio en "
               "{nuevo.adres}, con efectos desde la fecha de esta Junta. Votos a favor: {ctx.glosy_za2}; en "
               "contra: {ctx.glosy_przeciw2}.",
               "{#}. APLICACIÓN DEL RESULTADO. Se aprueba destinar a dividendos la cantidad de {ctx.dywidenda}, "
               "que se distribuirá entre los socios en proporción a sus participaciones dentro del próximo "
               "trimestre.",
               "{#}. MODIFICACIÓN ESTATUTARIA. Se aprueba modificar el artículo de los estatutos relativo al "
               "órgano de administración, con la mayoría exigida por el artículo 199 de la Ley de Sociedades de "
               "Capital.",
               min=3, max=3),
        sekcja("close", "akapit",
               "{#}. Y no habiendo más asuntos que tratar, se levanta la sesión.",
               "La próxima Junta ordinaria se celebrará el {ctx.dok_pozniej}.",
               "El acta se aprueba al término de la reunión, conforme al artículo 202 de la Ley de Sociedades de "
               "Capital, y será transcrita al libro de actas de la Sociedad, que se conserva en el domicilio "
               "social y podrá ser objeto de elevación a público e inscripción en el Registro Mercantil.",
               min=3, max=3),
        sekcja("sign_label", "akapit", "Vº Bº Presidencia                      Secretaría"),
        sekcja("signatures", "podpis", "{presidente.pelne}", "{secretario.pelne}"),
        sekcja("footer", "stopka",
               "{sociedad.nazwa} | {sociedad.adres} | CIF {sociedad.cif} | tel. {sociedad.telefon} | "
               "{sociedad.email}"),
    ],
    metadane={"author": "{secretario.pelne}", "subject": "Acta de la Junta General Ordinaria"},
)
