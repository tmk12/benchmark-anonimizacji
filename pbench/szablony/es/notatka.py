"""Nota interna del despacho al socio sobre un siniestro de tráfico: hechos, daños, asesoramiento al cliente, próximos
pasos. Fecha de la nota `ctx.przed_rozprawa`, plazos `notatka_termin` < `rozprawa`; procedimiento ante un Juzgado de
Primera Instancia (wariant „es_primera”, numeracja punktów bez luk przez `{#}`)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="es", typ="notatka", warianty=("es_primera",),
    role={"despacho": "kancelaria", "autor": "osoba", "cliente": "osoba", "contraparte": "osoba", "testigo": "osoba",
          "aseguradora": "firma", "juzgado": "sad"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{despacho.nazwa}",
               "{despacho.adres} | tel. {despacho.telefon}"),
        sekcja("heading", "akapit",
               "NOTA INTERNA – CONFIDENCIAL",
               "De: {autor.pelne}",
               "Fecha: {ctx.przed_rozprawa}",
               "Asunto: reclamación por accidente de circulación – cliente {cliente.pelne}"),
        sekcja("client", "akapit",
               "Cliente: {cliente.pelne}, con DNI/NIE {cliente.dni_nie}, domicilio en {cliente.adres}, tel. "
               "{cliente.telefon}, correo electrónico {cliente.email}.",
               "Parte contraria: {contraparte.pelne}, {contraparte.rodzaj:conductor|conductora} del otro vehículo, {contraparte.rodzaj:domiciliado|domiciliada} en "
               "{contraparte.adres}; su aseguradora es {aseguradora.nazwa} (CIF {aseguradora.cif}).",
               "Procedimiento: autos {juzgado.sygnatura} ante el {juzgado.nazwa}.",
               min=3, max=3),
        sekcja("facts", "akapit",
               "{#}. Hechos. {cliente.rodzaj:El cliente|La cliente} circulaba por una vía urbana cuando el "
               "vehículo conducido por {contraparte.pelne} invadió su carril y colisionó contra el lateral "
               "izquierdo. No hubo lesionados. Se levantó atestado de la Policía Local.",
               "{#}. Daños. Según el presupuesto del taller, el daño de su vehículo asciende a "
               "{ctx.szkoda}. La aseguradora {aseguradora.nazwa} ha abonado un anticipo de {ctx.zaliczka_ub} y "
               "admite la responsabilidad del asegurado, pero discute la cuantía de la reparación.",
               "{#}. Prueba. {testigo.pelne} presenció la colisión y está {testigo.rodzaj:dispuesto|dispuesta} a declarar; su teléfono es "
               "{testigo.telefon}. Disponemos además de fotografías del lugar y del parte amistoso de accidente.",
               "{#}. Fundamento. La responsabilidad se funda en el artículo 1.902 del Código Civil y en el Texto "
               "Refundido de la Ley sobre responsabilidad civil y seguro en la circulación de vehículos a motor.",
               min=4, max=4),
        sekcja("advice", "akapit",
               "{#}. Asesoramiento. He informado {cliente.rodzaj:al cliente|a la cliente} de que, antes del "
               "{ctx.notatka_termin}, debemos remitir a la aseguradora el escrito de reclamación previsto en la "
               "normativa del seguro de automóviles.",
               "{#}. Vista. El juicio está señalado ante el {juzgado.nazwa} para el {ctx.rozprawa}. "
               "{cliente.rodzaj:El cliente|La cliente} deberá acudir personalmente.",
               "{#}. Costas. Se ha advertido de que, en caso de estimación parcial, cada parte abonará las costas "
               "causadas a su instancia y las comunes por mitad (artículo 394.2 de la Ley de Enjuiciamiento Civil).",
               "{#}. Alternativa. Es recomendable explorar una transacción extrajudicial con la aseguradora antes "
               "de la vista, dado el riesgo y el coste del proceso.",
               min=3, max=4),
        sekcja("documents", "akapit",
               "Documentación pendiente: factura definitiva del taller, informe pericial de valoración y "
               "justificante del pago de la franquicia.",
               "Se ha solicitado a la Policía Local copia del atestado; no será necesario acudir al Consorcio de "
               "Compensación de Seguros al estar identificada la aseguradora del vehículo contrario.",
               "Todos los documentos se custodian en el expediente electrónico del despacho, con acceso restringido.",
               min=2, max=3),
        sekcja("actions", "akapit",
               "Próximos pasos: preparar la proposición de prueba y citar a los testigos.",
               "Llamada de seguimiento a {cliente.pelne} prevista para el {ctx.notatka_termin}.",
               min=2, max=2),
        sekcja("signature", "podpis", "{autor.pelne}"),
        sekcja("footer", "stopka",
               "{despacho.nazwa} | {despacho.adres} | CIF {despacho.cif} | tel. {despacho.telefon} | "
               "{despacho.email}"),
    ],
    metadane={"author": "{autor.pelne}", "subject": "Nota interna sobre reclamación de accidente",
              "case": "{juzgado.sygnatura}"},
)
