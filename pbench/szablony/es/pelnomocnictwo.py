"""Escritura de poder general para pleitos otorgada ante notario: comparecencia, identificación, otorgamiento a favor de
abogado y procurador, facultades, advertencias legales; fecha `ctx.dok`."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="es", typ="pelnomocnictwo", dorosli=True,
    role={"notario": "osoba", "poderdante": "osoba", "apoderado1": "osoba", "apoderado2": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "NOTARÍA DE {notario.pelne:upper}",
               "{notario.adres} | tel. {notario.telefon} | {notario.email}"),
        sekcja("title", "akapit",
               "ESCRITURA DE PODER GENERAL PARA PLEITOS",
               "NÚMERO {ctx.udzialy2} DE MI PROTOCOLO",
               "En {notario.miasto}, a {ctx.dok}."),
        sekcja("notary", "akapit",
               "Ante mí, {notario.rodzaj:Don|Doña} {notario.pelne}, {notario.rodzaj:Notario|Notaria} del Ilustre "
               "Colegio Notarial, con residencia en {notario.miasto},"),
        sekcja("appears", "akapit",
               "COMPARECE: {poderdante.rodzaj:Don|Doña} {poderdante.pelne}, mayor de edad, con domicilio en "
               "{poderdante.adres}, y con documento de identidad número {poderdante.dni_nie}.",
               "{poderdante.rodzaj:Identifico al compareciente|Identifico a la compareciente} por su documento "
               "nacional de identidad, cuyos datos aparecen en el encabezamiento.",
               "Interviene en su propio nombre y derecho. Tiene, a mi juicio, según interviene, la capacidad legal "
               "necesaria para otorgar la presente escritura de poder.",
               min=3, max=3),
        sekcja("grants", "akapit",
               "OTORGA: Que confiere poder general para pleitos, tan amplio y bastante como en Derecho se "
               "requiera, a favor {apoderado1.rodzaj:del Letrado Don|de la Letrada Doña} {apoderado1.pelne} y "
               "{apoderado2.rodzaj:del Procurador de los Tribunales Don|de la Procuradora de los Tribunales Doña} "
               "{apoderado2.pelne}, para que, conjunta o indistintamente, representen y defiendan al poderdante "
               "ante toda clase de juzgados y tribunales."),
        sekcja("powers", "akapit",
               "Facultades: presentar y contestar demandas, reconvenciones y recursos; solicitar medidas "
               "cautelares; proponer y practicar pruebas; transigir, desistir y allanarse cuando exista facultad "
               "expresa; y cobrar cantidades que correspondan al poderdante conforme a los artículos 24 y 25 de la "
               "Ley de Enjuiciamiento Civil.",
               "Asimismo podrán sustituir este poder, total o parcialmente, a favor de otros Procuradores de los "
               "Tribunales y otorgar poderes de representación a letrados.",
               "Se faculta a los apoderados para pedir y obtener copias, testimonios y certificaciones, y para "
               "recibir notificaciones y requerimientos de cualquier clase.",
               "Los apoderados podrán solicitar la provisión de fondos que estimen necesaria, que el poderdante "
               "satisfará en la cuenta que se le indique, siendo la cantidad inicial prevista {ctx.zaliczka_kosztow}.",
               min=3, max=4),
        sekcja("revocation", "akapit",
               "El presente poder tendrá vigencia indefinida y solo podrá ser revocado mediante comunicación "
               "fehaciente a los apoderados y a los órganos judiciales ante los que estuvieren personados.",
               "Los apoderados aceptan el poder y declaran no hallarse incursos en incompatibilidad alguna."),
        sekcja("legal_notices", "akapit",
               "Advierto a la parte compareciente de que los datos personales contenidos en esta escritura serán "
               "tratados por el Notario conforme al Reglamento (UE) 2016/679 y a la Ley Orgánica 3/2018, con la "
               "finalidad de cumplir la función pública notarial.",
               "Leída por mí, {notario.rodzaj:el Notario|la Notaria}, esta escritura {poderdante.rodzaj:al "
               "compareciente, que la encuentra conforme, la aprueba|a la compareciente, que la encuentra conforme, "
               "la aprueba} y firma conmigo. Doy fe de todo lo consignado en el presente instrumento público.",
               "Se expiden copias autorizadas a solicitud del interesado, quedando matriz en el protocolo.",
               min=3, max=3),
        sekcja("signature", "podpis", "{poderdante.pelne}", "{notario.pelne}"),
        sekcja("footer", "stopka",
               "Notaría de {notario.pelne} | {notario.adres} | tel. {notario.telefon} | {notario.email}"),
    ],
    metadane={"author": "{notario.pelne}", "subject": "Escritura de poder general para pleitos"},
)
