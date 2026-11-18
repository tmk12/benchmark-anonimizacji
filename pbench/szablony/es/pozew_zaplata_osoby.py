"""Demanda de juicio ordinario de un particular contra otro particular para reclamar el resto del precio de un
vehículo vendido, ante el Juzgado de Primera Instancia (representación por procurador y dirección letrada)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="es", typ="pozew_zaplata_osoby", warianty=("es_primera",), dorosli=True,
    role={"abogado": "osoba", "procurador": "osoba", "actor": "osoba", "demandado": "osoba", "testigo1": "osoba",
          "testigo2": "osoba", "vehiculo": "sprawa", "juzgado": "sad"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{abogado.pelne} – Abogado",
               "{abogado.adres} | tel. {abogado.telefon} | {abogado.email}"),
        sekcja("court", "akapit",
               "AL {juzgado.nazwa:upper}",
               "DEMANDA DE JUICIO ORDINARIO – RECLAMACIÓN DE CANTIDAD"),
        sekcja("parties", "akapit",
               "{procurador.rodzaj:Don|Doña} {procurador.pelne}, Procurador de los Tribunales, en nombre y "
               "representación de {actor.rodzaj:don|doña} {actor.pelne}, con DNI/NIE {actor.dni_nie} y domicilio en "
               "{actor.adres}, bajo la dirección letrada de {abogado.rodzaj:don|doña} {abogado.pelne}, ante el "
               "Juzgado comparezco y DIGO:"),
        sekcja("claim", "akapit",
               "Que formulo demanda de juicio ordinario contra {demandado.rodzaj:don|doña} {demandado.pelne}, con "
               "DNI/NIE {demandado.dni_nie} y domicilio en {demandado.adres}, en reclamación de {ctx.glowna} más "
               "intereses legales, con base en los siguientes"),
        sekcja("facts_title", "akapit", "HECHOS"),
        sekcja("facts", "akapit",
               "PRIMERO.- El {ctx.umowa} mi mandante vendió {demandado.rodzaj:al demandado|a la demandada} el "
               "turismo con matrícula {vehiculo.tablica} y se lo entregó ese mismo día.",
               "SEGUNDO.- {demandado.rodzaj:El demandado|La demandada} abonó solo parte del precio. El resto, "
               "{ctx.glowna}, debía ingresarse en la cuenta {actor.rachunek} hasta el {ctx.termin_platnosci}, sin que "
               "se haya pagado.",
               "TERCERO.- El {ctx.wezwanie} se remitió burofax a {demandado.adres} concediendo plazo hasta el "
               "{ctx.termin_wezwania}. El requerimiento no fue atendido.",
               "CUARTO.- {demandado.rodzaj:El demandado|La demandada} reconoció la deuda ante {testigo1.pelne} y "
               "después en una llamada presenciada por {testigo2.pelne} (tel. {testigo2.telefon}).",
               min=3, max=4),
        sekcja("law_title", "akapit", "FUNDAMENTOS DE DERECHO"),
        sekcja("law", "akapit",
               "I. Competencia.- Corresponde al Juzgado conforme a los artículos 45 y 52.1.14.º de la Ley de "
               "Enjuiciamiento Civil, por ser el del domicilio {demandado.rodzaj:del demandado|de la demandada}.",
               "II. Fondo.- El artículo 1445 del Código Civil obliga al comprador a pagar el precio; el 1100 y el 1108 "
               "fundan la mora y los intereses.",
               "III. Procedimiento.- Procede el juicio ordinario (artículo 249.2 LEC) por razón de la cuantía.",
               min=2, max=3),
        sekcja("suplico", "akapit",
               "SUPLICO AL JUZGADO que tenga por presentada la demanda y, previos los trámites legales, dicte sentencia "
               "por la que se condene {demandado.rodzaj:al demandado|a la demandada} a pagar {ctx.glowna} más los "
               "intereses legales desde el {ctx.termin_platnosci} y las costas procesales.",
               "OTROSÍ DIGO: que se proponen como prueba el contrato de compraventa del {ctx.umowa}, el extracto de la "
               "cuenta {actor.rachunek} y la declaración de los testigos."),
        sekcja("firma", "podpis", "{abogado.pelne}"),
        sekcja("pie", "stopka", "{abogado.pelne} | {abogado.adres} | tel. {abogado.telefon} | {abogado.email}"),
        sekcja("nota", "przypis",
               "Se acompaña la escritura de poder a favor de "
               "{procurador.pelne}."),
    ],
    metadane={"author": "{abogado.pelne}", "subject": "Demanda de reclamación de cantidad entre particulares"},
)
