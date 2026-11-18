"""Correo electrónico del despacho a un cliente con el borrador de contestación a la demanda y solicitud de documentos
(encabezados De/Para/CC en los metadatos); procedimiento ante un Juzgado de Primera Instancia, firma con teléfono y aviso
legal. Plazos: `odp_termin` < `rozprawa`."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="es", typ="email", warianty=("es_primera",),
    role={"despacho": "kancelaria", "remitente": "osoba", "cliente": "osoba", "colega": "osoba",
          "contraparte": "osoba", "testigo": "osoba", "juzgado": "sad", "asunto": "sprawa", "portal": "sprawa"},
    sekcje=[
        sekcja("greeting", "akapit",
               "{cliente.rodzaj:Estimado|Estimada} {cliente.rodzaj:Sr.|Sra.} {cliente.nazwisko}:"),
        sekcja("intro", "akapit",
               "Tras nuestra conversación telefónica, le adjunto el borrador de contestación a la demanda "
               "interpuesta por {contraparte.pelne} contra usted en los autos {asunto.sygnatura}.",
               "Le confirmo que el {juzgado.nazwa} ha señalado la vista para el {ctx.rozprawa}. Le ruego que me "
               "confirme su disponibilidad para asistir.",
               "Gracias por enviarnos la documentación. En una primera revisión el caso está bien documentado, "
               "aunque faltan todavía algunos justificantes.",
               min=3, max=3),
        sekcja("draft", "akapit",
               "El borrador se adjunta en formato Word con los cambios marcados. Le ruego que me envíe sus "
               "comentarios antes del {ctx.odp_termin}, ya que el plazo para presentar el escrito vence "
               "en esa fecha y no admite prórroga salvo causa justificada."),
        sekcja("body", "akapit",
               "Necesitamos que nos facilite: la confirmación de su domicilio a efectos de notificaciones "
               "({cliente.adres}), el justificante del ingreso de la provisión de fondos y copia de la "
               "correspondencia mantenida durante los dos últimos años.",
               "La provisión de fondos para gastos del procedimiento, por importe de {ctx.zaliczka_kosztow}, debe "
               "ingresarse en nuestra cuenta {despacho.rachunek} a más tardar el día antes de la vista.",
               "Puede subir los documentos a nuestro portal seguro: {portal.url}. Le ruego que no nos envíe por "
               "correo ordinario documentos con datos especialmente sensibles.",
               "{testigo.rodzaj:El testigo propuesto|La testigo propuesta}, {testigo.pelne}, ha sido {testigo.rodzaj:avisado|avisada} de que el Juzgado podrá citarle; si cambia "
               "su teléfono ({testigo.telefon}), le agradeceré que nos lo comunique.",
               "En cuanto a la estrategia, propongo oponernos a la demanda y, subsidiariamente, solicitar un "
               "pago aplazado, conforme a lo que permita el Código Civil.",
               min=3, max=5),
        sekcja("closing", "akapit",
               "Si tiene cualquier duda, puede llamarme al {remitente.telefon} o escribirme a {remitente.email}.",
               "Pongo en copia a {colega.rodzaj:mi compañero|mi compañera} {colega.pelne} para que pueda seguir el expediente durante mi "
               "ausencia.",
               "Reciba un cordial saludo,",
               min=3, max=3),
        sekcja("signature", "stopka",
               "{remitente.pelne} | {remitente.rodzaj:Abogado|Abogada} | {despacho.nazwa} | {despacho.adres} | tel. {despacho.telefon}"),
        sekcja("disclaimer", "stopka",
               "Este mensaje es confidencial y puede contener información amparada por el secreto profesional. Si "
               "no es usted el destinatario, le rogamos que lo comunique al remitente y lo elimine. {despacho.nazwa} "
               "es responsable del tratamiento de sus datos conforme al Reglamento (UE) 2016/679.",
               "Puede ejercer sus derechos de acceso, rectificación y supresión escribiendo al despacho; la "
               "información sobre protección de datos está disponible en nuestra página web.",
               min=1, max=2),
    ],
    metadane={"from": "{remitente.email}", "to": "{cliente.email}", "cc": "{colega.email}",
              "subject": "Borrador de contestación a la demanda: por favor, revise y envíe comentarios"},
)
