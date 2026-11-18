"""Contrato de arrendamiento de vivienda entre dos particulares (arrendador – arrendatario) conforme a la Ley de
Arrendamientos Urbanos, con fianza de una mensualidad, inventario de lecturas y datos de contacto."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="es", typ="umowa_najmu", dorosli=True,
    role={"arrendador": "osoba", "arrendatario": "osoba", "vivienda": "osoba", "testigo": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "CONTRATO DE ARRENDAMIENTO DE VIVIENDA",
               "Arrendador: {arrendador.pelne} | Arrendatario: {arrendatario.pelne}"),
        sekcja("opening", "akapit",
               "En {arrendador.miasto}, a {ctx.dok}, se celebra el presente contrato entre:"),
        sekcja("parties", "akapit",
               "De una parte, {arrendador.rodzaj:don|doña} {arrendador.pelne}, con DNI/NIE {arrendador.dni_nie}, "
               "mayor de edad, con domicilio en {arrendador.adres}, tel. {arrendador.telefon}, correo electrónico "
               "{arrendador.email}, en adelante el ARRENDADOR.",
               "De otra parte, {arrendatario.rodzaj:don|doña} {arrendatario.pelne}, con DNI/NIE "
               "{arrendatario.dni_nie}, mayor de edad, con domicilio actual en {arrendatario.adres}, tel. "
               "{arrendatario.telefon}, correo electrónico {arrendatario.email}, en adelante el ARRENDATARIO."),
        sekcja("objeto", "akapit",
               "PRIMERA.- Objeto",
               "El ARRENDADOR da en arrendamiento al ARRENDATARIO la vivienda sita en {vivienda.adres}, con trastero y "
               "plaza de garaje, habitada hasta el {ctx.umowa_dawna} por {vivienda.rodzaj:don|doña} {vivienda.pelne}.",
               "La vivienda se destina exclusivamente a residencia habitual del ARRENDATARIO y de las personas que "
               "este comunique por escrito; queda prohibido el subarriendo sin autorización escrita."),
        sekcja("duracion", "akapit",
               "SEGUNDA.- Duración",
               "El contrato comienza el {ctx.od_dnia} y finaliza el {ctx.dok_pozniej}, sin perjuicio de las prórrogas "
               "legales previstas en el artículo 9 de la Ley de Arrendamientos Urbanos.",
               "El ARRENDATARIO podrá desistir del contrato una vez transcurridos seis meses, con un preaviso de treinta días."),
        sekcja("renta", "akapit",
               "TERCERA.- Renta y fianza",
               "La renta mensual es de {ctx.zaliczka_kosztow}, pagadera por adelantado dentro de los cinco primeros días "
               "de cada mes mediante transferencia a la cuenta del ARRENDADOR {arrendador.rachunek}.",
               "El ARRENDATARIO entrega una fianza de {ctx.zaliczka_kosztow} (una mensualidad), que el ARRENDADOR "
               "depositará en el organismo autonómico competente y devolverá en el plazo de un mes desde la entrega de "
               "las llaves, previa comprobación del estado de la vivienda.",
               "Los suministros (electricidad, agua, gas e internet) serán a cargo del ARRENDATARIO según consumo."),
        sekcja("obligaciones", "akapit",
               "CUARTA.- Obligaciones",
               "El ARRENDATARIO conservará la vivienda en buen estado y comunicará sin demora cualquier desperfecto; "
               "las pequeñas reparaciones por el desgaste del uso ordinario serán de su cuenta.",
               "El ARRENDADOR podrá acceder a la vivienda para inspeccionarla, con aviso previo de dos días y en "
               "presencia del ARRENDATARIO.",
               "La entrega de llaves y la lectura de contadores se harán el {ctx.od_dnia}; asistirá por el ARRENDADOR "
               "{testigo.pelne} (tel. {testigo.telefon}).",
               min=2, max=3),
        sekcja("tabla", "komorka",
               "Concepto | Lectura en la entrega | Observaciones\n"
               "Contador de electricidad | 04 213 kWh | leído ante ambas partes\n"
               "Contador de agua | 118 m3 | sin observaciones\n"
               "Llaves | 3 juegos | entregadas a {arrendatario.pelne}",
               "Concepto | Plazo | Responsable\n"
               "Pago de la renta | cinco primeros días del mes | {arrendatario.pelne}\n"
               "Devolución de la fianza | un mes desde la entrega de llaves | {arrendador.pelne}\n"
               "Entrega de la vivienda | {ctx.od_dnia} | {testigo.pelne}",
               min=1, max=1),
        sekcja("finales", "akapit",
               "QUINTA.- Disposiciones finales",
               "Cualquier modificación de este contrato deberá constar por escrito y firmada por ambas partes.",
               "Las notificaciones se dirigirán a los domicilios indicados o por correo electrónico a "
               "{arrendador.email} y {arrendatario.email}.",
               "Las partes se someten a los juzgados y tribunales del lugar donde radica la vivienda. El contrato se "
               "firma en dos ejemplares, uno para cada parte."),
        sekcja("firma_etiqueta", "akapit", "El ARRENDADOR:                                                  El ARRENDATARIO:"),
        sekcja("firma", "podpis", "{arrendador.pelne}", "{arrendatario.pelne}"),
        sekcja("pie", "stopka", "Contrato de arrendamiento – {arrendador.pelne} / {arrendatario.pelne} | Vivienda: {vivienda.adres}"),
        sekcja("nota", "przypis",
               "Se adjunta el certificado de eficiencia energética de la vivienda, entregado al ARRENDATARIO el {ctx.dok}."),
    ],
    metadane={"author": "{arrendador.pelne}", "title": "Contrato de arrendamiento de vivienda"},
)
