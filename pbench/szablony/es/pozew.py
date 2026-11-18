"""Demanda de juicio ordinario (reclamación de cantidad por un préstamo) ante el Juzgado de Primera Instancia de la
provincia del documento; hechos (PRIMERO…QUINTO), fundamentos de derecho (I…VI), suplico y otrosí.
Daty i kwoty z `Kontekst` (wariant „es_primera”: roszczenie > 6 000 €); sąd I instancji, bez numeru sprawy (demanda
jeszcze go nie ma), sprawa poboczna w roli `previo`."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="es", typ="pozew", warianty=("es_primera",),
    role={"despacho": "kancelaria", "abogado": "osoba", "procurador": "osoba", "actor": "osoba",
          "demandado": "osoba", "testigo1": "osoba", "testigo2": "osoba", "juzgado": "sad", "previo": "sprawa"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{abogado.pelne} – {despacho.nazwa}",
               "{despacho.adres} | tel. {despacho.telefon} | {despacho.email}"),
        sekcja("court", "akapit",
               "AL {juzgado.nazwa:upper}",
               "DEMANDA DE JUICIO ORDINARIO – RECLAMACIÓN DE CANTIDAD"),
        sekcja("parties", "akapit",
               "{procurador.rodzaj:Don|Doña} {procurador.pelne}, {procurador.rodzaj:Procurador|Procuradora} de los "
               "Tribunales, en nombre y representación de {actor.rodzaj:Don|Doña} {actor.pelne}, con DNI/NIE "
               "{actor.dni_nie} y domicilio en {actor.adres}, según acredito mediante escritura de poder que "
               "acompaño, bajo la dirección letrada de {abogado.rodzaj:Don|Doña} {abogado.pelne}, ante el Juzgado "
               "comparezco y, como mejor proceda en Derecho, DIGO:"),
        sekcja("claim", "akapit",
               "Que por medio del presente escrito formulo DEMANDA DE JUICIO ORDINARIO contra "
               "{demandado.rodzaj:Don|Doña} {demandado.pelne}, con DNI/NIE {demandado.dni_nie} y domicilio en "
               "{demandado.adres}, en reclamación de la cantidad de {ctx.glowna}, más los intereses legales, "
               "con base en los siguientes"),
        sekcja("facts_title", "akapit", "HECHOS"),
        sekcja("facts", "akapit",
               "PRIMERO.- Con fecha {ctx.umowa} mi mandante entregó en préstamo "
               "{demandado.rodzaj:al demandado|a la demandada} la cantidad de {ctx.glowna}, mediante transferencia a "
               "la cuenta {demandado.rachunek}, de la que es titular, con obligación "
               "de devolverla en el plazo pactado.",
               "SEGUNDO.- El préstamo venció el día {ctx.termin_platnosci} sin que {demandado.rodzaj:el "
               "demandado|la demandada} haya devuelto cantidad alguna, pese a los reiterados recordatorios "
               "verbales y escritos de mi mandante.",
               "TERCERO.- Con fecha {ctx.wezwanie} se remitió {demandado.rodzaj:al demandado|a la demandada} un "
               "burofax con acuse de recibo y certificación de contenido, al domicilio indicado, concediéndole plazo "
               "hasta el {ctx.termin_wezwania} para el pago. El requerimiento no fue atendido.",
               "CUARTO.- {demandado.rodzaj:El demandado|La demandada} reconoció la deuda ante {testigo1.pelne} y, "
               "con posterioridad, en una conversación telefónica presenciada por {testigo2.pelne} (tel. "
               "{testigo2.telefon}), en la que prometió abonarla, sin llegar a hacerlo.",
               "QUINTO.- Con anterioridad se intentó la solución extrajudicial de la controversia y se tramitó "
               "{previo.sygnatura}, que concluyó sin pronunciamiento sobre el fondo."),
        sekcja("law_title", "akapit", "FUNDAMENTOS DE DERECHO"),
        sekcja("law", "akapit",
               "I. Jurisdicción y competencia.- Corresponde el conocimiento de este asunto a los Juzgados de Primera "
               "Instancia, en virtud de los artículos 45 y 85 de la Ley Orgánica del Poder Judicial, y es "
               "territorialmente competente este Juzgado conforme al artículo 50 de la Ley de Enjuiciamiento Civil, "
               "por ser el del domicilio {demandado.rodzaj:del demandado|de la demandada}.",
               "II. Capacidad y legitimación.- Ambas partes tienen capacidad para ser parte y capacidad procesal "
               "(artículos 6 y 7 de la Ley de Enjuiciamiento Civil), y la legitimación resulta de su condición de "
               "prestamista y prestatario.",
               "III. Procedimiento.- Procede el juicio ordinario por razón de la cuantía, que excede de seis mil "
               "euros (artículo 249.2 de la Ley de Enjuiciamiento Civil), fijada en {ctx.glowna}.",
               "IV. Postulación.- {actor.rodzaj:El actor|La actora} comparece {actor.rodzaj:representado|representada} por "
               "Procurador y {actor.rodzaj:asistido|asistida} por Letrado, conforme a los artículos 23 y 31 de la Ley de Enjuiciamiento Civil.",
               "V. Fondo del asunto.- Son de aplicación los artículos 1.740 y siguientes y 1.100 del Código Civil "
               "sobre el contrato de préstamo y la mora del deudor, así como el artículo 1.108 del mismo cuerpo "
               "legal en cuanto a los intereses.",
               "VI. Costas.- Procede su imposición {demandado.rodzaj:al demandado|a la demandada}, por aplicación del criterio del vencimiento "
               "del artículo 394 de la Ley de Enjuiciamiento Civil."),
        sekcja("prayer", "akapit",
               "SUPLICO AL JUZGADO que, habiendo por presentado este escrito con los documentos que lo acompañan, "
               "se sirva admitirlo, tener por formulada demanda de juicio ordinario contra {demandado.pelne} y, "
               "previos los trámites legales, dictar sentencia por la que se condene {demandado.rodzaj:al "
               "demandado|a la demandada}:",
               "a) al pago de la cantidad de {ctx.glowna} en concepto de principal;",
               "b) al pago de los intereses legales devengados desde el {ctx.termin_platnosci} y de los del artículo "
               "576 de la Ley de Enjuiciamiento Civil desde la fecha de la sentencia;",
               "c) al pago de las costas del procedimiento."),
        sekcja("otrosi", "akapit",
               "OTROSÍ DIGO: que mi mandante propone como medios de prueba los documentos acompañados, el "
               "interrogatorio {demandado.rodzaj:del demandado|de la demandada} y la testifical de {testigo1.pelne} y de {testigo2.pelne}, "
               "por lo que SUPLICO AL JUZGADO que los admita.",
               "OTROSÍ DIGO: que se interesa que las notificaciones se practiquen por medios telemáticos "
               "(LexNET), de conformidad con la normativa sobre comunicaciones electrónicas con la Administración "
               "de Justicia.",
               "Es justicia que pido en {despacho.miasto}, a {ctx.pozew}.",
               min=3, max=3),
        sekcja("signature", "podpis", "{abogado.pelne}", "{procurador.pelne}"),
        sekcja("footer", "stopka",
               "{despacho.nazwa} | {despacho.adres} | CIF {despacho.cif} | tel. {despacho.telefon} | "
               "{despacho.email}"),
    ],
    metadane={"author": "{abogado.pelne}", "subject": "Demanda de juicio ordinario"},
)
