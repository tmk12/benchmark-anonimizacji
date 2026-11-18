"""Contrato de prestación de servicios jurídicos (despacho de abogados – sociedad cliente): reunidos, cláusulas
(objeto, honorarios con IVA 21 %, confidencialidad, protección de datos, responsabilidad, duración, ley aplicable),
firma. Kwoty i daty z `Kontekst`; cláusulas stałe (numeracja bez luk)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="es", typ="umowa", dorosli=True,
    role={"despacho": "kancelaria", "cliente": "firma", "socio": "osoba", "administrador": "osoba",
          "contacto": "osoba", "coordinador": "osoba", "suplente": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{despacho.nazwa}",
               "{despacho.adres} | CIF {despacho.cif} | tel. {despacho.telefon}",
               "Inscrita en el {despacho.registro}, Hoja {despacho.company_no}"),
        sekcja("title", "akapit",
               "CONTRATO DE PRESTACIÓN DE SERVICIOS JURÍDICOS",
               "En {despacho.miasto}, a {ctx.dok}."),
        sekcja("parties_title", "akapit", "REUNIDOS"),
        sekcja("parties", "akapit",
               "De una parte, {socio.rodzaj:Don|Doña} {socio.pelne}, con DNI/NIE {socio.dni_nie}, que actúa en "
               "nombre y representación de {despacho.nazwa}, con CIF {despacho.cif} y domicilio en "
               "{despacho.adres}, en su condición de {socio.rodzaj:socio|socia} (en adelante, el «Despacho»).",
               "De otra parte, {administrador.rodzaj:Don|Doña} {administrador.pelne}, con DNI/NIE "
               "{administrador.dni_nie}, que actúa en nombre y representación de {cliente.nazwa}, con CIF "
               "{cliente.cif}, domicilio social en {cliente.adres}, inscrita en el {cliente.registro}, Hoja "
               "{cliente.company_no}, en calidad de {administrador.rodzaj:administrador|administradora} (en adelante, el «Cliente»).",
               "Ambas partes se reconocen mutuamente capacidad jurídica suficiente para suscribir el presente "
               "contrato y, a tal efecto,"),
        sekcja("agree_title", "akapit", "ACUERDAN"),
        sekcja("object", "akapit",
               "PRIMERA.- OBJETO. El Despacho prestará al Cliente servicios de asesoramiento jurídico en materia "
               "mercantil, laboral y de protección de datos, incluida la redacción y revisión de contratos, la "
               "emisión de informes escritos y la asistencia a reuniones de negociación (los «Servicios»).",
               "Quedan excluidos del objeto la representación y defensa en procedimientos judiciales y "
               "arbitrales, que requerirán una hoja de encargo independiente.",
               "El Despacho designa como persona de contacto a {contacto.pelne}, {contacto.rodzaj:abogado responsable|abogada responsable} de la cuenta, "
               "y a {suplente.pelne} como {suplente.rodzaj:sustituto|sustituta} en caso de ausencia. El cambio de responsable no requerirá "
               "modificación del contrato.",
               "El Cliente facilitará la información y documentación necesarias a través de {coordinador.pelne} "
               "(teléfono {coordinador.telefon}, correo electrónico {coordinador.email})."),
        sekcja("fees", "akapit",
               "SEGUNDA.- HONORARIOS. Por los Servicios el Cliente abonará al Despacho una cuota mensual fija de "
               "{ctx.um_wyn}, más el IVA al tipo del 21 %.",
               "La cuota cubre hasta veinte horas mensuales de dedicación. Las horas adicionales se facturarán a "
               "las tarifas vigentes del Despacho, sin que el importe adicional pueda superar {ctx.um_limit} al "
               "mes sin la aprobación previa y por escrito del Cliente.",
               "Las facturas se pagarán en el plazo de quince días desde su recepción, mediante transferencia a la "
               "cuenta {despacho.rachunek}, indicando el número de factura como concepto.",
               "El retraso en el pago devengará los intereses de demora previstos en la Ley 3/2004, de medidas de "
               "lucha contra la morosidad en las operaciones comerciales."),
        sekcja("confidentiality", "akapit",
               "TERCERA.- CONFIDENCIALIDAD Y SECRETO PROFESIONAL. Cada parte mantendrá en secreto la información no "
               "pública recibida de la otra y la utilizará únicamente para la ejecución del contrato.",
               "Lo anterior se entiende sin perjuicio del deber de secreto profesional del abogado, que subsistirá "
               "tras la extinción del contrato, conforme al Estatuto General de la Abogacía Española.",
               "Quedan excluidas de esta obligación las informaciones que sean o lleguen a ser públicas sin "
               "incumplimiento, y las que deban revelarse por mandato legal o resolución judicial."),
        sekcja("data", "akapit",
               "CUARTA.- PROTECCIÓN DE DATOS. Las partes cumplirán el Reglamento (UE) 2016/679 y la Ley Orgánica "
               "3/2018, de Protección de Datos Personales y garantía de los derechos digitales. El Despacho "
               "tratará los datos personales como responsable del tratamiento para la prestación de los Servicios "
               "y el cumplimiento de sus obligaciones legales, entre ellas las de prevención del blanqueo de "
               "capitales.",
               "El Despacho mantiene a disposición del Cliente su política de privacidad."),
        sekcja("liability", "akapit",
               "QUINTA.- RESPONSABILIDAD. La responsabilidad total del Despacho derivada de este contrato no "
               "excederá de {ctx.um_kara}, cantidad cubierta por su seguro de responsabilidad civil profesional.",
               "Ninguna de las partes responderá del lucro cesante ni de los daños indirectos, salvo dolo o culpa "
               "grave."),
        sekcja("term", "akapit",
               "SEXTA.- DURACIÓN Y RESOLUCIÓN. El contrato entra en vigor el {ctx.od_dnia} y tendrá una duración "
               "inicial de doce meses, prorrogable tácitamente por períodos iguales.",
               "Cualquiera de las partes podrá resolverlo en cualquier momento con un preaviso escrito de treinta "
               "días, sin perjuicio del derecho del Despacho a percibir los honorarios devengados hasta esa fecha.",
               "A la extinción, el Despacho devolverá al Cliente la documentación original que obre en su poder."),
        sekcja("notices", "akapit",
               "SÉPTIMA.- NOTIFICACIONES. Las comunicaciones se realizarán por escrito, por correo certificado, "
               "burofax o correo electrónico con acuse de recibo, al domicilio del Cliente ({cliente.adres}) y al "
               "del Despacho ({despacho.adres}), o a cualquier otro que se notifique conforme a esta cláusula."),
        sekcja("law", "akapit",
               "OCTAVA.- LEY APLICABLE Y JURISDICCIÓN. El contrato se rige por la legislación española. Para "
               "cualquier controversia, las partes se someten a los Juzgados y Tribunales de {despacho.miasto}, "
               "con renuncia a cualquier otro fuero que pudiera corresponderles.",
               "Y en prueba de conformidad, las partes firman el presente contrato por duplicado y a un solo "
               "efecto, en el lugar y fecha indicados en el encabezamiento."),
        sekcja("signature", "podpis", "{socio.pelne}", "{administrador.pelne}"),
        sekcja("footer", "stopka",
               "{despacho.nazwa} | {despacho.adres} | CIF {despacho.cif} | tel. {despacho.telefon} | "
               "{despacho.email}"),
    ],
    metadane={"author": "{socio.pelne}", "subject": "Contrato de prestación de servicios jurídicos"},
)
