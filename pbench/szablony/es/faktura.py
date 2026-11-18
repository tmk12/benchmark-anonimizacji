"""Factura de servicios jurídicos (España): NIF/CIF e IVA al 21 %, datos de las partes y líneas en tablas, totales de
`Kontekst` (base imponible + IVA = total), condiciones de pago y menciones legales."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="es", typ="faktura",
    role={"vendedor": "kancelaria", "comprador": "firma", "emisor": "osoba", "destinatario": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{vendedor.nazwa}",
               "{vendedor.adres} | CIF {vendedor.cif} | NIF-IVA {vendedor.vat}"),
        sekcja("title", "akapit",
               "FACTURA N.º A-{ctx.udzialy1}",
               "Fecha de expedición: {ctx.dok}",
               "Fecha de la operación: {ctx.dok_sprzedaz}"),
        sekcja("parties", "komorka",
               "Emisor | Destinatario\n"
               "{vendedor.nazwa} | {comprador.nazwa}\n"
               "{vendedor.adres} | {comprador.adres}\n"
               "CIF {vendedor.cif} | CIF {comprador.cif}\n"
               "Tel. {vendedor.telefon} | Tel. {comprador.telefon}"),
        sekcja("lines", "komorka",
               "N.º | Concepto | Cantidad | Precio unitario | Base imponible | Tipo de IVA\n"
               "1 | Cuota mensual de asesoramiento jurídico general | 1 | {ctx.kf1} | {ctx.kf1} | 21 %\n"
               "2 | Informe sobre contrato de arrendamiento de local | 1 | {ctx.kf2} | {ctx.kf2} | 21 %\n"
               "3 | Asistencia a reunión con la Administración | 1 | {ctx.kf3} | {ctx.kf3} | 21 %",
               "N.º | Servicio | Unidad | Cantidad | Base imponible | Tipo de IVA\n"
               "1 | Servicios según contrato de fecha {ctx.umowa_dawna} | a tanto alzado | 1 | {ctx.kf1} | 21 %\n"
               "2 | Redacción y negociación de documentos | a tanto alzado | 1 | {ctx.kf2} | 21 %\n"
               "3 | Asistencia a consejos de administración | a tanto alzado | 1 | {ctx.kf3} | 21 %",
               min=1, max=1),
        sekcja("totals", "komorka",
               "Base imponible | IVA 21 % | Total factura\n{ctx.netto} | {ctx.vat} | {ctx.brutto}"),
        sekcja("payment", "akapit",
               "Vencimiento: {ctx.dok_termin_fv}. Forma de pago: transferencia bancaria a la cuenta "
               "{vendedor.rachunek}, indicando el número de factura como concepto.",
               "Consultas sobre esta factura: {vendedor.email}, tel. {vendedor.telefon}."),
        sekcja("notes", "akapit",
               "Factura expedida conforme al Real Decreto 1619/2012, por el que se aprueba el Reglamento por el que "
               "se regulan las obligaciones de facturación.",
               "El impago en plazo devengará los intereses de demora y la indemnización por costes de cobro "
               "previstos en la Ley 3/2004, de medidas de lucha contra la morosidad en las operaciones comerciales.",
               "Operación sujeta a IVA en el territorio de aplicación del impuesto; no procede inversión del "
               "sujeto pasivo.",
               "Esta factura se emite en formato electrónico y es válida sin firma.",
               min=3, max=4),
        sekcja("issued", "akapit",
               "La factura se envió por correo electrónico a {destinatario.pelne}, persona autorizada para recibir "
               "documentos contables en nombre del destinatario.",
               "Elaborada y revisada por {emisor.pelne}."),
        sekcja("signature", "podpis", "{emisor.pelne}"),
        sekcja("footer", "stopka",
               "{vendedor.nazwa} | {vendedor.adres} | CIF {vendedor.cif} | tel. {vendedor.telefon}"),
    ],
    metadane={"author": "{emisor.pelne}", "subject": "Factura por servicios jurídicos"},
)
