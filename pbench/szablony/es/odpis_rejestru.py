"""Nota simple informativa del Registro Mercantil de una sociedad limitada: datos de identificación, fechas, capital
social (kapital2 = suma de dos socios × 50 €), tabla de administradores con fecha de nacimiento y DNI/NIE, socios.
Daty z `Kontekst`: constitución <= última inscripción <= fecha de la nota.

Uwaga: DNI/NIE i data urodzenia administratorów są tu celowo (gęstość danych benchmarku); prawdziwe notas simples
mercantiles często je pomijają (pełne dane zawiera dopiero certificación). Administratorzy są pełnoletni w dniu
najwcześniejszej daty kontekstu (`Szablon.dorosli`)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="es", typ="odpis_rejestru", dorosli=True,
    role={"sociedad": "spolka", "administrador1": "osoba", "administrador2": "osoba", "administrador3": "osoba",
          "secretario": "osoba", "socio1": "osoba", "socio2": "osoba", "auditor": "osoba", "solicitante": "osoba"},
    sekcje=[
        sekcja("titles", "naglowek",
               "REGISTRO MERCANTIL – NOTA SIMPLE INFORMATIVA",
               "{sociedad.nazwa}"),
        sekcja("identity", "komorka",
               "Dato | Información\n"
               "Denominación social | {sociedad.nazwa}\n"
               "CIF | {sociedad.cif}\n"
               "Domicilio social | {sociedad.adres}\n"
               "Registro | {sociedad.registro}\n"
               "Hoja registral | {sociedad.company_no}\n"
               "Estado | Vigente"),
        sekcja("dates", "komorka",
               "Hecho | Fecha\n"
               "Constitución de la sociedad | {ctx.kr_rejestracja}\n"
               "Última inscripción | {ctx.kr_wpis}\n"
               "Capital social | {ctx.kapital2}"),
        sekcja("organs_title", "akapit",
               "Órgano de administración (extracto del Registro)",
               "Cargos vigentes y sus titulares"),
        sekcja("organs", "komorka",
               "N.º | Apellidos | Nombre | Fecha de nacimiento | Cargo | DNI/NIE\n"
               "1 | {administrador1.nazwisko} | {administrador1.imie} | {administrador1.data_ur} | Administrador "
               "solidario | {administrador1.dni_nie}\n"
               "2 | {administrador2.nazwisko} | {administrador2.imie} | {administrador2.data_ur} | Administrador "
               "solidario | {administrador2.dni_nie}\n"
               "3 | {administrador3.nazwisko} | {administrador3.imie} | {administrador3.data_ur} | Administrador "
               "solidario | {administrador3.dni_nie}",
               "Cargo | Nombre | Fecha de nacimiento | DNI/NIE | Domicilio\n"
               "Administrador | {administrador1.pelne} | {administrador1.data_ur} | {administrador1.dni_nie} | "
               "{administrador1.adres}\n"
               "Administrador | {administrador2.pelne} | {administrador2.data_ur} | {administrador2.dni_nie} | "
               "{administrador2.adres}\n"
               "Secretario no consejero | {secretario.pelne} | {secretario.data_ur} | {secretario.dni_nie} | "
               "{secretario.adres}",
               min=1, max=1),
        sekcja("holders", "komorka",
               "Socios | Nombre | Participaciones | Observaciones\n"
               "1 | {socio1.pelne} | {ctx.udzialy1} | Titular de participaciones numeradas correlativamente\n"
               "2 | {socio2.pelne} | {ctx.udzialy2} | Titular de participaciones numeradas correlativamente",
               min=0, max=1),
        sekcja("oversight", "akapit",
               "Auditor de cuentas nombrado: {auditor.pelne}. La sociedad no se encuentra en liquidación ni "
               "se ha declarado concurso de acreedores.",
               "Objeto social: actividades de asesoramiento y consultoría empresarial (CNAE 7022) y servicios "
               "relacionados.",
               "Ejercicio social: coincide con el año natural. La duración de la sociedad es indefinida.",
               min=2, max=3),
        sekcja("certification", "akapit",
               "Esta nota simple tiene valor meramente informativo y no acredita, en perjuicio de tercero, el "
               "contenido de los asientos del Registro (artículo 77 del Reglamento del Registro Mercantil). Solo "
               "la certificación del Registrador da fe del contenido de los libros.",
               "La información registral se expide a solicitud de {solicitante.pelne}, que declara un interés "
               "legítimo en la consulta."),
        sekcja("footer", "stopka",
               "Nota simple expedida por el {sociedad.registro} | Hoja {sociedad.company_no} | Fecha de la "
               "nota: {ctx.dok} | Página 1 de 2"),
    ],
    metadane={"subject": "Nota simple del Registro Mercantil", "entity": "{sociedad.nazwa}"},
)
