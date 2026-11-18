"""Presentación del despacho al consejo de administración de un cliente: resultados de la auditoría legal (due
diligence) de una sociedad objetivo (breves diapositivas y tabla de riesgos); derecho español."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="es", typ="prezentacja",
    role={"despacho": "kancelaria", "ponente": "osoba", "contacto": "osoba", "ceo": "osoba", "objetivo": "firma",
          "cliente": "firma", "sitio": "sprawa"},
    sekcje=[
        sekcja("titles", "naglowek",
               "Auditoría legal: {objetivo.nazwa}",
               "Resumen de conclusiones",
               "Principales riesgos de la operación",
               "Plan de acción hasta el cierre",
               "Contacto y próximos pasos"),
        sekcja("slide1", "akapit",
               "Presenta {ponente.pelne}, {despacho.nazwa}",
               "Consejo de administración de {cliente.nazwa}, {ctx.dok}",
               "Estrictamente confidencial – solo para el consejo"),
        sekcja("slide2", "akapit",
               "Sociedad objetivo: {objetivo.nazwa}, {objetivo.adres}",
               "CIF {objetivo.cif} | {objetivo.registro}, Hoja {objetivo.company_no}",
               "Entrevistas de gestión con {ceo.pelne}, {ceo.rodzaj:director general|directora general}",
               "Precio propuesto por las participaciones: {ctx.cena}"),
        sekcja("slide3", "akapit",
               "Los contratos con los clientes clave contienen cláusulas de cambio de control",
               "El registro de actividades de tratamiento (art. 30 RGPD) está desactualizado",
               "Tres litigios en curso por un valor total de {ctx.sporow}",
               "Las licencias de software carecen de una cadena de titularidad acreditada",
               "No se han detectado deudas con la Seguridad Social ni con la Hacienda Pública",
               min=3, max=5),
        sekcja("risks", "komorka",
               "Área | Nivel | Recomendación\n"
               "Laboral | Medio | Actualizar la política retributiva\n"
               "Protección de datos | Alto | Adoptar registro y contratos de encargado\n"
               "Inmobiliario | Bajo | Sin acciones\n"
               "Propiedad intelectual | Alto | Obtener cesiones de los colaboradores"),
        sekcja("slide4", "akapit",
               "Firmar el contrato de compraventa de participaciones antes del {ctx.dok_termin_dl}",
               "Condiciones suspensivas: consentimiento de los socios y de la entidad financiadora",
               "El cierre requiere la aprobación de {ceo.pelne} como {ceo.rodzaj:director general|directora general} de la sociedad",
               "Control de concentraciones: comprobar los umbrales de la Ley 15/2007 de Defensa de la Competencia",
               min=3, max=4),
        sekcja("slide5", "akapit",
               "Contacto: {contacto.pelne}, tel. {contacto.telefon}, correo {contacto.email}",
               "Nuestra web: {sitio.url}",
               "Gracias"),
        sekcja("footer", "stopka", "{despacho.nazwa} – confidencial"),
    ],
    metadane={"author": "{ponente.pelne}", "subject": "Auditoría legal (due diligence)"},
)
