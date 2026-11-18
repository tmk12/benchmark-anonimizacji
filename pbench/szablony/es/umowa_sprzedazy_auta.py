"""Contrato de compraventa de un vehículo usado entre dos particulares: DNI/NIE, matrícula, precio con señal y saldo,
tabla de estado. El generador no produce número de bastidor (VIN), por lo que el documento no lo contiene."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="es", typ="umowa_sprzedazy_auta", dorosli=True,
    role={"vendedor": "osoba", "comprador": "osoba", "vehiculo": "sprawa", "testigo": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "CONTRATO DE COMPRAVENTA DE VEHÍCULO USADO",
               "Vendedor: {vendedor.pelne} | Comprador: {comprador.pelne}"),
        sekcja("opening", "akapit", "En {vendedor.miasto}, a {ctx.dok}, se celebra el presente contrato entre:"),
        sekcja("parties", "akapit",
               "{vendedor.rodzaj:Don|Doña} {vendedor.pelne}, con DNI/NIE {vendedor.dni_nie}, domicilio en "
               "{vendedor.adres}, tel. {vendedor.telefon}, en adelante el VENDEDOR.",
               "{comprador.rodzaj:Don|Doña} {comprador.pelne}, con DNI/NIE {comprador.dni_nie}, domicilio en "
               "{comprador.adres}, tel. {comprador.telefon}, correo electrónico {comprador.email}, en adelante el COMPRADOR."),
        sekcja("objeto", "akapit",
               "PRIMERA.- Objeto",
               "El VENDEDOR vende al COMPRADOR el turismo usado con matrícula {vehiculo.tablica}, con su permiso de "
               "circulación, ficha técnica, dos llaves y libro de mantenimiento.",
               "El VENDEDOR declara ser propietario único, que el vehículo está libre de cargas, embargos y reserva de "
               "dominio y que no tiene daños graves ocultos.",
               "El seguro obligatorio está en vigor hasta el {ctx.dok_pozniej}; el VENDEDOR comunicará la venta a la aseguradora."),
        sekcja("precio", "akapit",
               "SEGUNDA.- Precio y forma de pago",
               "El precio de la compraventa es de {ctx.szkoda}.",
               "El COMPRADOR ha entregado en este acto una señal de {ctx.zaliczka_ub} y abonará el resto mediante "
               "transferencia a la cuenta del VENDEDOR {vendedor.rachunek} a más tardar el {ctx.dok_termin}.",
               "Los gastos de cambio de titularidad y el impuesto de transmisiones patrimoniales corren por cuenta del COMPRADOR."),
        sekcja("tabla", "komorka",
               "Concepto | Estado | Observaciones\n"
               "Kilometraje | 187 450 km | según el cuentakilómetros\n"
               "ITV | vigente hasta {ctx.dok_pozniej} | informe adjunto\n"
               "Siniestros | ninguno | declaración de {vendedor.pelne}",
               "Concepto | Documento | Entregado a\n"
               "Permiso de circulación | original | {comprador.pelne}\n"
               "Llaves | 2 juegos | {comprador.pelne}\n"
               "Facturas de taller | 9 | {testigo.pelne}",
               min=1, max=1),
        sekcja("entrega", "akapit",
               "TERCERA.- Entrega y garantía",
               "La entrega se realizará el {ctx.dok_sprzedaz} en el domicilio del VENDEDOR; estará presente "
               "{testigo.pelne} (tel. {testigo.telefon}) como testigo del estado del vehículo.",
               "El COMPRADOR ha examinado y probado el vehículo y lo adquiere en el estado en que se encuentra; el "
               "riesgo se transmite con la entrega.",
               "Las partes se someten a los juzgados del domicilio del VENDEDOR."),
        sekcja("finales", "akapit",
               "CUARTA.- Disposiciones finales",
               "Cualquier modificación deberá hacerse por escrito y firmada por ambas partes.",
               "Contacto para cualquier incidencia: {vendedor.email} y {comprador.telefon}.",
               "El contrato se firma en dos ejemplares, uno para cada parte."),
        sekcja("firma_etiqueta", "akapit", "El VENDEDOR:                                                  El COMPRADOR:"),
        sekcja("firma", "podpis", "{vendedor.pelne}", "{comprador.pelne}"),
        sekcja("pie", "stopka", "Compraventa del vehículo {vehiculo.tablica} | {vendedor.pelne} / {comprador.pelne}"),
        sekcja("nota", "przypis",
               "El COMPRADOR solicitará el cambio de titularidad ante la Jefatura Provincial de Tráfico en el plazo de "
               "diez días desde la firma."),
    ],
    metadane={"author": "{vendedor.pelne}", "title": "Contrato de compraventa de vehículo usado"},
)
