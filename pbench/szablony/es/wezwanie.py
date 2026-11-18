"""Requerimiento de pago por burofax: el despacho de abogados, en nombre de la sociedad acreedora, reclama a una
persona física una factura impagada (principal, intereses de demora, gastos de gestión); plazo, medios de pago,
consecuencias. Daty i kwoty z `Kontekst` (umowa < termin_platnosci < wezwanie < termin_wezwania)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="es", typ="wezwanie",
    role={"despacho": "kancelaria", "abogado": "osoba", "acreedor": "firma", "representante": "osoba",
          "deudor": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{despacho.nazwa}",
               "{despacho.adres} | CIF {despacho.cif} | tel. {despacho.telefon}"),
        sekcja("date", "akapit",
               "{despacho.miasto}, a {ctx.wezwanie}",
               "BUROFAX CON ACUSE DE RECIBO Y CERTIFICACIÓN DE CONTENIDO",
               "Ref.: REQ/{ctx.udzialy1}"),
        sekcja("addressee", "akapit",
               "A la atención de {deudor.rodzaj:Don|Doña} {deudor.pelne}",
               "{deudor.adres}",
               "DNI/NIE {deudor.dni_nie}"),
        sekcja("salutation", "akapit",
               "Muy {deudor.rodzaj:señor mío|señora mía}:"),
        sekcja("heading", "akapit",
               "REQUERIMIENTO FEHACIENTE DE PAGO"),
        sekcja("basis", "akapit",
               "Actuamos en nombre y representación de {acreedor.nazwa}, con CIF {acreedor.cif} y domicilio en "
               "{acreedor.adres}, representada por {representante.rodzaj:Don|Doña} {representante.pelne}, "
               "{representante.rodzaj:en calidad de apoderado|en calidad de apoderada}.",
               "Nuestra representada le prestó servicios y los facturó con fecha "
               "{ctx.umowa}. El importe venció el {ctx.termin_platnosci} y no ha sido satisfecho pese a los "
               "recordatorios enviados.",
               "Las cantidades pendientes son las siguientes: principal, {ctx.glowna}; intereses de demora "
               "devengados hasta la fecha de este escrito, {ctx.odsetki}; y gastos de gestión de cobro, "
               "{ctx.koszty_wind}. El importe total reclamado asciende a {ctx.razem_wez}.",
               "Le recordamos que la Ley 3/2004, de medidas de lucha contra la morosidad en las operaciones "
               "comerciales, fija un plazo máximo de pago de treinta días y devenga intereses de demora desde el "
               "día siguiente al vencimiento."),
        sekcja("payment", "akapit",
               "Le requerimos para que abone la cantidad indicada en el plazo máximo que vence el "
               "{ctx.termin_wezwania}, mediante transferencia a la cuenta de nuestra representada "
               "{acreedor.rachunek}, indicando como concepto el número de referencia de este requerimiento.",
               "Si lo prefiere, nuestra representada estudiará un fraccionamiento del pago, siempre que el primer "
               "plazo no sea inferior a {ctx.ugoda_rata} y se abone dentro del plazo señalado.",
               min=1, max=2),
        sekcja("consequences", "akapit",
               "De no atender este requerimiento, nuestra representada ejercitará las acciones judiciales "
               "oportunas, incluido el procedimiento monitorio (artículo 812 de la Ley de Enjuiciamiento Civil) o "
               "el juicio ordinario, con reclamación de las costas y de los intereses que correspondan.",
               "Asimismo, la deuda cierta, vencida y exigible podrá ser comunicada a sistemas de información "
               "crediticia en los términos del artículo 20 de la Ley Orgánica 3/2018, de Protección de Datos "
               "Personales y garantía de los derechos digitales, previa advertencia en este mismo escrito.",
               "Este requerimiento interrumpe la prescripción de la acción conforme al artículo 1.973 del Código "
               "Civil.",
               min=2, max=3),
        sekcja("contact", "akapit",
               "Para cualquier aclaración puede ponerse en contacto con {abogado.rodzaj:el abogado|la abogada} {abogado.pelne} en el teléfono "
               "{abogado.telefon} o en {abogado.email}."),
        sekcja("close", "akapit",
               "Sin otro particular, le saluda atentamente,"),
        sekcja("signature", "podpis", "{abogado.pelne}"),
        sekcja("footer", "stopka",
               "{despacho.nazwa} | {despacho.adres} | CIF {despacho.cif} | tel. {despacho.telefon} | "
               "{despacho.email}"),
    ],
    metadane={"author": "{abogado.pelne}", "subject": "Requerimiento de pago"},
)
