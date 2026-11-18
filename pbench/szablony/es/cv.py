"""Currículum vitae de una abogada o un abogado júnior (España): datos personales, perfil, experiencia, formación,
idiomas, referencias y cláusula RGPD. Fechas de `Kontekst`: estudios < empleo anterior < empleo actual."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="es", typ="cv",
    role={"candidato": "osoba", "empleador1": "firma", "empleador2": "firma", "supervisor": "osoba",
          "referencia1": "osoba", "referencia2": "osoba", "sitio": "sprawa"},
    sekcje=[
        sekcja("header", "naglowek",
               "CURRÍCULUM VITAE",
               "{candidato.pelne}"),
        sekcja("contact", "akapit",
               "{candidato.rodzaj:Nacido|Nacida} el {candidato.data_ur}",
               "DNI/NIE: {candidato.dni_nie}",
               "Domicilio: {candidato.adres}",
               "Teléfono: {candidato.telefon} | Correo electrónico: {candidato.email}",
               "Perfil profesional: {sitio.url}",
               min=4, max=5),
        sekcja("summary", "akapit",
               "{candidato.rodzaj:Abogado|Abogada} en ejercicio con experiencia en derecho mercantil, contratación y "
               "resolución de conflictos, {candidato.rodzaj:orientado|orientada} al trabajo en equipo y al cliente.",
               "Interés especial por el derecho de sociedades, la protección de datos y la litigación civil.",
               "{candidato.rodzaj:Colegiado|Colegiada} ejerciente y {candidato.rodzaj:habituado|habituada} al uso de LexNET y de las herramientas de gestión de expedientes.",
               min=2, max=3),
        sekcja("experience_title", "akapit", "EXPERIENCIA PROFESIONAL"),
        sekcja("experience", "akapit",
               "{ctx.cv_od1} – actualidad: {candidato.rodzaj:Abogado|Abogada} júnior, {empleador1.nazwa}, {empleador1.adres}. Asesoramiento "
               "mercantil y laboral a pymes, redacción de contratos y preparación de juntas de socios.",
               "Responsable directo: {supervisor.pelne}.",
               "{ctx.cv_od2} – {ctx.cv_do2}: Pasante en {empleador2.nazwa}, con apoyo al departamento de litigación en "
               "la preparación de demandas, contestaciones y proposición de prueba.",
               min=3, max=3),
        sekcja("education_title", "akapit", "FORMACIÓN"),
        sekcja("education", "akapit",
               "Grado en Derecho, finalizado el {ctx.cv_studia}. Trabajo de fin de grado sobre derecho de "
               "sociedades de capital.",
               "Máster de Acceso a la Abogacía, con prácticas externas en un despacho de la ciudad.",
               "Cursos de especialización en protección de datos (RGPD y LOPDGDD) y en derecho concursal.",
               min=2, max=3),
        sekcja("skills", "akapit",
               "Idiomas: español (lengua materna), inglés (C1), francés (B1).",
               "Informática: paquete Office, LexNET, bases de datos jurídicas, firma electrónica.",
               "Habilidades: redacción jurídica, negociación, gestión del tiempo, trabajo en equipo.",
               min=2, max=3),
        sekcja("referees", "akapit",
               "Referencias: {referencia1.pelne}, tel. {referencia1.telefon}; {referencia2.pelne}, correo "
               "electrónico {referencia2.email}."),
        sekcja("interests", "akapit",
               "Intereses: senderismo, ajedrez, voluntariado en un servicio de orientación jurídica gratuita.",
               "Disponibilidad inmediata e incorporación a jornada completa.",
               min=1, max=2),
        sekcja("consent", "akapit",
               "Consiento el tratamiento de mis datos personales para fines de selección de personal, conforme al "
               "Reglamento (UE) 2016/679 y a la Ley Orgánica 3/2018, y conozco mis derechos de acceso, "
               "rectificación y supresión."),
        sekcja("signature", "podpis", "{candidato.pelne}"),
        sekcja("footer", "stopka",
               "{candidato.pelne} | {candidato.email} | tel. {candidato.telefon}"),
    ],
    metadane={"author": "{candidato.pelne}", "subject": "Currículum vitae"},
)
