"""Relación de nóminas de una empresa (hoja de cálculo): encabezado, período, tabla con más de 200 trabajadores
(DNI/NIE, número de afiliación a la Seguridad Social, IBAN), resumen y notas.

Cada fila tiene su propia persona (`p000`…), porque los huecos de un mismo rol tienen un único valor; salarios y
sumas vienen de `Kontekst` (`ctx.brutto_<i>`, `ctx.suma_<n>`), de modo que el resumen cuadra con la tabla."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

WIERSZE = 212
_PUESTOS = ("Administrativo", "Contable", "Jefe de equipo", "Técnico júnior", "Asistente de dirección", "Conductor",
            "Mozo de almacén", "Auxiliar", "Técnico sénior", "Responsable de prevención", "Consultor",
            "Administrador de sistemas")

_ROLE_WIERSZY = {f"p{i:03d}": "osoba" for i in range(WIERSZE)}


def _tabela() -> str:
    wiersze = ["N.º | Nombre | Apellidos | DNI/NIE | N.º afiliación SS | Puesto | Salario bruto | IBAN"]
    for i in range(WIERSZE):
        p = f"p{i:03d}"
        wiersze.append(f"{i + 1} | {{{p}.pelne/1}} | {{{p}.pelne/2}} | {{{p}.dni_nie}} | {{{p}.nuss}} | "
                       f"{_PUESTOS[i % len(_PUESTOS)]} | {{ctx.brutto_{i}}} | {{{p}.rachunek}}")
    return "\n".join(wiersze)


SZABLON = Szablon(
    jezyk="es", typ="lista_plac",
    role={"empresa": "firma", "elaborado": "osoba", "aprobado": "osoba", "rrhh": "osoba"} | _ROLE_WIERSZY,
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{empresa.nazwa}",
               "{empresa.adres} | CIF {empresa.cif} | Código de cuenta de cotización {ctx.udzialy1}"),
        sekcja("title", "akapit",
               "RELACIÓN MENSUAL DE NÓMINAS",
               "Fecha de pago: {ctx.dok_termin}",
               "Empresa: {empresa.nazwa}"),
        sekcja("table", "komorka", _tabela()),
        sekcja("summary", "komorka",
               "Concepto | Importe\n"
               "Total salario bruto | {ctx.suma_212}\n"
               "Cotizaciones a la Seguridad Social del período | {ctx.zus_212}\n"
               "Retenciones a cuenta del IRPF | {ctx.pit_212}"),
        sekcja("notes", "akapit",
               "Las retenciones se han calculado conforme al Reglamento del Impuesto sobre la Renta de las "
               "Personas Físicas y se ingresan trimestralmente mediante el modelo 111.",
               "Las cotizaciones se liquidan a través del Sistema RED de la Seguridad Social, dentro del mes "
               "siguiente al devengo.",
               "Las prestaciones por incapacidad temporal, nacimiento y cuidado de menor, y los pluses de "
               "convenio figuran en las nóminas individuales.",
               "Esta relación contiene datos personales tratados conforme al Reglamento (UE) 2016/679 y debe "
               "conservarse durante al menos cuatro años, plazo de prescripción de las obligaciones tributarias.",
               min=3, max=4),
        sekcja("prepared", "akapit",
               "Elaborado por: {elaborado.pelne}, Nóminas, tel. {elaborado.telefon}",
               "Revisado por: {rrhh.pelne}",
               "Aprobado para el pago: {aprobado.pelne}"),
        sekcja("signatures", "podpis", "{elaborado.pelne}", "{aprobado.pelne}"),
        sekcja("footer", "stopka",
               "{empresa.nazwa} | {empresa.adres} | tel. {empresa.telefon} | {empresa.email}"),
    ],
    metadane={"author": "{elaborado.pelne}", "subject": "Relación de nóminas"},
)
