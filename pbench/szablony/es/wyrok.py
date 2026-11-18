"""Sentencia en un juicio ordinario de reclamación de cantidad (préstamo), con ANTECEDENTES DE HECHO, FUNDAMENTOS DE
DERECHO y FALLO, magistrados y partes, y citas de sentencias del Tribunal Supremo (zwykły tekst, nie gold).

Dwa warianty: „es_primera” – Juzgado de Primera Instancia (jednoosobowo, Magistrado-Juez), „es_apelacion” – Audiencia
Provincial (sección de trzech magistrados, rollo de apelación; sprawa I instancji w `ctx.sygn_pierwsza` i
`ctx.sad_pierwsza`). Ordinales PRIMERO… stałe w obrębie wariantu (każda część ma stały zestaw bloków, więc bez luk).
Daty, kwoty i rok sygnatury z `Kontekst`."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import W, sekcja

SZABLON = Szablon(
    jezyk="es", typ="wyrok", warianty=("es_primera", "es_apelacion"),
    role={"sad": "sad", "juez1": "osoba", "juez2": "osoba", "juez3": "osoba", "actor": "osoba",
          "demandado": "osoba", "procurador1": "osoba", "procurador2": "osoba", "abogado1": "osoba",
          "abogado2": "osoba", "testigo1": "osoba", "testigo2": "osoba", "perito": "osoba", "cita1": "cytat",
          "cita2": "cytat", "cita3": "cytat"},
    sekcje=[
        sekcja("caption", "naglowek",
               "{sad.nazwa:upper}",
               "{sad.sygnatura}",
               W("es_apelacion", "Procedimiento de origen: {ctx.sygn_pierwsza}, {ctx.sad_pierwsza}"),
               "SENTENCIA",
               "En {sad.miasto}, a {ctx.wyrok_koncowy}."),
        sekcja("panel", "akapit",
               W("es_primera", "{juez1.rodzaj:Don|Doña} {juez1.pelne}, {juez1.rodzaj:Magistrado-Juez|Magistrada-Juez} "
                 "del {sad.nazwa}, ha visto los presentes autos de juicio ordinario, seguidos a instancia de "
                 "{actor.pelne}, {actor.rodzaj:representado|representada} por {procurador1.rodzaj:el Procurador "
                 "Don|la Procuradora Doña} {procurador1.pelne} y {actor.rodzaj:asistido|asistida} por "
                 "{abogado1.rodzaj:el Letrado Don|la Letrada Doña} {abogado1.pelne}, contra {demandado.pelne}, "
                 "{demandado.rodzaj:representado|representada} por {procurador2.rodzaj:el Procurador Don|la "
                 "Procuradora Doña} {procurador2.pelne} y {demandado.rodzaj:asistido|asistida} por "
                 "{abogado2.rodzaj:el Letrado Don|la Letrada Doña} {abogado2.pelne}, sobre reclamación de cantidad."),
               W("es_apelacion", "Integrada la Sección por {juez1.rodzaj:Don|Doña} {juez1.pelne} "
                 "({juez1.rodzaj:Presidente|Presidenta}), {juez2.rodzaj:Don|Doña} {juez2.pelne} y "
                 "{juez3.rodzaj:Don|Doña} {juez3.pelne}, ha visto en grado de apelación los autos de juicio "
                 "ordinario seguidos entre {actor.pelne}, {actor.rodzaj:apelado|apelada}, "
                 "{actor.rodzaj:representado|representada} por {procurador1.rodzaj:el Procurador Don|la Procuradora "
                 "Doña} {procurador1.pelne} y {actor.rodzaj:defendido|defendida} por {abogado1.rodzaj:el Letrado "
                 "Don|la Letrada Doña} {abogado1.pelne}, y {demandado.pelne}, apelante, "
                 "{demandado.rodzaj:representado|representada} por {procurador2.rodzaj:el Procurador Don|la "
                 "Procuradora Doña} {procurador2.pelne} y {demandado.rodzaj:defendido|defendida} por "
                 "{abogado2.rodzaj:el Letrado Don|la Letrada Doña} {abogado2.pelne}.")),
        sekcja("antecedentes_titulo", "akapit", "ANTECEDENTES DE HECHO"),
        sekcja("antecedentes", "akapit",
               W("es_primera", "PRIMERO.- Por {procurador1.pelne}, en nombre y representación de {actor.pelne}, se "
                 "presentó el {ctx.pozew} demanda de juicio ordinario contra {demandado.pelne}, en la que, tras "
                 "exponer los hechos y fundamentos de derecho que estimó aplicables, solicitaba que se condenara "
                 "{demandado.rodzaj:al demandado|a la demandada} al pago de {ctx.glowna}, más los intereses "
                 "legales y las costas."),
               W("es_primera", "SEGUNDO.- Admitida a trámite la demanda, se emplazó {demandado.rodzaj:al "
                 "demandado|a la demandada}, que la contestó mediante escrito de fecha {ctx.odp_termin}, oponiéndose "
                 "a la pretensión y alegando el pago parcial de la deuda."),
               W("es_primera", "TERCERO.- Convocadas las partes a la audiencia previa y, después, al acto del "
                 "juicio, este se celebró el {ctx.rozprawa}. Se practicó la prueba admitida: interrogatorio de las "
                 "partes, testifical de {testigo1.pelne} y de {testigo2.pelne}, y pericial de {perito.pelne}."),
               W("es_primera", "CUARTO.- En la tramitación de este procedimiento se han observado las "
                 "prescripciones legales."),
               W("es_apelacion", "PRIMERO.- La sentencia apelada, dictada el {ctx.wyrok} por el {ctx.sad_pierwsza} "
                 "en los autos {ctx.sygn_pierwsza}, estimó parcialmente la demanda de {actor.pelne} y condenó a "
                 "{demandado.pelne} al pago de {ctx.zasadzona}."),
               W("es_apelacion", "SEGUNDO.- Contra dicha sentencia interpuso recurso de apelación "
                 "{demandado.rodzaj:el demandado|la demandada} el {ctx.apelacja}, alegando error en la valoración "
                 "de la prueba. {actor.rodzaj:El actor|La actora} se opuso al recurso."),
               W("es_apelacion", "TERCERO.- Elevadas las actuaciones a esta Audiencia Provincial y formado el "
                 "presente rollo, se señaló para deliberación, votación y fallo el día {ctx.rozprawa_apel}, en que "
                 "ha tenido lugar."),
               W("es_apelacion", "CUARTO.- En la tramitación del recurso se han observado las prescripciones "
                 "legales. Ha sido ponente {juez1.rodzaj:el Ilmo. Sr. Magistrado|la Ilma. Sra. Magistrada} "
                 "{juez1.pelne}.")),
        sekcja("fundamentos_titulo", "akapit", "FUNDAMENTOS DE DERECHO"),
        sekcja("fundamentos", "akapit",
               W("es_primera", "PRIMERO.- Se ejercita en la demanda una acción de reclamación de cantidad derivada "
                 "del contrato de préstamo celebrado entre las partes el {ctx.umowa}, cuyo vencimiento se produjo el "
                 "{ctx.termin_platnosci} sin que se hubiera reintegrado la totalidad de lo prestado. Conforme al "
                 "artículo 1.740 del Código Civil, el prestatario está obligado a devolver al prestamista otro "
                 "tanto de la misma especie y calidad."),
               W("es_primera", "SEGUNDO.- A quien reclama corresponde, según el artículo 217 de la Ley de "
                 "Enjuiciamiento Civil, probar la certeza de los hechos de los que se desprende el efecto jurídico "
                 "pretendido; a quien se opone, la de los hechos extintivos o impeditivos que alegue, como el pago "
                 "o la compensación."),
               W("es_primera", "TERCERO.- De la prueba practicada, y en particular de la declaración de "
                 "{testigo1.pelne} y del informe pericial de {perito.pelne}, resulta acreditada la entrega de la "
                 "cantidad prestada, si bien {demandado.rodzaj:el demandado|la demandada} justificó pagos parciales "
                 "que deben descontarse del principal reclamado."),
               W("es_primera", "CUARTO.- La jurisprudencia del Tribunal Supremo ha declarado que la entrega de la "
                 "cantidad por transferencia bancaria constituye prueba suficiente del préstamo cuando el "
                 "prestatario no justifica otra causa (véanse las sentencias {cita1.sygnatura} y "
                 "{cita2.sygnatura}), y que el reconocimiento de deuda no exige formalidad alguna "
                 "({cita3.sygnatura})."),
               W("es_primera", "QUINTO.- Procede la condena al pago de los intereses legales desde el vencimiento, "
                 "{ctx.termin_platnosci}, conforme al artículo 1.108 del Código Civil, y de los intereses del "
                 "artículo 576 de la Ley de Enjuiciamiento Civil desde la fecha de esta sentencia."),
               W("es_primera", "SEXTO.- Dada la estimación parcial de la demanda, no procede hacer expresa "
                 "imposición de las costas procesales, de conformidad con el artículo 394.2 de la Ley de "
                 "Enjuiciamiento Civil."),
               W("es_apelacion", "PRIMERO.- Se aceptan los fundamentos de derecho de la sentencia apelada en cuanto "
                 "no se opongan a los de esta resolución."),
               W("es_apelacion", "SEGUNDO.- El recurso se funda en un supuesto error en la valoración de la prueba. "
                 "{demandado.rodzaj:El recurrente|La recurrente} sostiene que la entrega del dinero no quedó "
                 "probada. Esta Sala, tras examinar la grabación del juicio y la documental aportada, no aprecia "
                 "error alguno."),
               W("es_apelacion", "TERCERO.- Según la doctrina del Tribunal Supremo (así, {cita1.sygnatura} y "
                 "{cita2.sygnatura}), el tribunal de apelación puede revisar la valoración de la prueba, pero debe "
                 "respetar la del órgano de instancia cuando no sea ilógica, arbitraria o contraria a las reglas de "
                 "la sana crítica ({cita3.sygnatura})."),
               W("es_apelacion", "CUARTO.- El testimonio de {testigo1.pelne}, valorado por el órgano de instancia, "
                 "no queda desvirtuado por ninguna otra prueba, y el informe de {perito.pelne} corrobora la entrega "
                 "de las cantidades."),
               W("es_apelacion", "QUINTO.- La desestimación del recurso determina la imposición de las costas de "
                 "esta alzada a la parte apelante, conforme al artículo 398.1 de la Ley de Enjuiciamiento Civil, "
                 "con el límite de {ctx.koszty_apel}."),
               ),
        sekcja("fallo_titulo", "akapit", "FALLO"),
        sekcja("fallo", "akapit",
               W("es_primera", "Que ESTIMANDO PARCIALMENTE la demanda formulada por {actor.pelne} contra "
                 "{demandado.pelne}, debo condenar y condeno {demandado.rodzaj:al demandado|a la demandada} a "
                 "abonar {actor.rodzaj:al actor|a la actora} la cantidad de {ctx.zasadzona}, más los intereses "
                 "legales devengados desde el {ctx.termin_platnosci}, sin expresa imposición de las costas."),
               W("es_primera", "Notifíquese esta resolución a las partes, haciéndoles saber que contra ella cabe "
                 "recurso de apelación ante la Audiencia Provincial, que deberá interponerse ante este Juzgado en "
                 "el plazo de veinte días desde su notificación (artículo 458 de la Ley de Enjuiciamiento Civil)."),
               W("es_primera", "Así por esta mi sentencia, de la que se llevará certificación a los autos, lo "
                 "pronuncio, mando y firmo."),
               W("es_apelacion", "Que DESESTIMANDO el recurso de apelación interpuesto por {demandado.pelne} "
                 "contra la sentencia dictada el {ctx.wyrok} por el {ctx.sad_pierwsza}, debemos confirmar y "
                 "confirmamos dicha resolución, con imposición a la parte apelante de las costas de esta alzada, "
                 "hasta un máximo de {ctx.koszty_apel}."),
               W("es_apelacion", "Contra esta sentencia podrá interponerse recurso extraordinario por infracción "
                 "procesal y recurso de casación en los supuestos del artículo 477 de la Ley de Enjuiciamiento "
                 "Civil, en el plazo de veinte días desde su notificación."),
               W("es_apelacion", "Así, por esta nuestra sentencia, de la que se unirá certificación al rollo, "
                 "lo pronunciamos, mandamos y firmamos.")),
        sekcja("signatures", "podpis",
               W("es_primera", "{juez1.pelne}"),
               W("es_apelacion", "{juez1.pelne}"), W("es_apelacion", "{juez2.pelne}"),
               W("es_apelacion", "{juez3.pelne}")),
        sekcja("footer", "stopka", "{sad.nazwa} | {sad.sygnatura} | Página 1"),
    ],
    metadane={"subject": "Sentencia en procedimiento de reclamación de cantidad", "case": "{sad.sygnatura}"},
)
