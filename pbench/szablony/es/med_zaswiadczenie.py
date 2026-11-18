"""Certificado médico oficial (Medicina Interna) para justificar la imposibilidad de asistir a la vista de un
Juzgado de Primera Instancia: diagnósticos CIE-10, reposo desde `zas_od` hasta `zas_do`, vista en `rozprawa`.
Daty: zas_od < zas_wystaw < rozprawa < zas_do."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="es", typ="med_zaswiadczenie", warianty=("es_primera",), profil="interna",
    role={"clinica": "placowka", "paciente": "pacjent", "medico": "lekarz", "juzgado": "sad"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{clinica.nazwa}",
               "{clinica.adres} | CIF {clinica.cif} | tel. {clinica.telefon}"),
        sekcja("place", "akapit", "{clinica.miasto}, a {ctx.zas_wystaw}"),
        sekcja("title", "akapit",
               "CERTIFICADO MÉDICO OFICIAL",
               "Modelo del Colegio Oficial de Médicos"),
        sekcja("body", "akapit",
               "{medico.rodzaj:Don|Doña} {medico.pelne}, {medico.rodzaj:médico colegiado|médica colegiada} n.º "
               "{medico.colegiado}, CERTIFICA:",
               "Que {paciente.rodzaj:el paciente|la paciente} {paciente.pelne}, {paciente.rodzaj:nacido|nacida} el "
               "{paciente.data_ur}, con DNI/NIE {paciente.dni_nie} y domicilio en {paciente.adres}, es {paciente.rodzaj:seguido|seguida} en "
               "este centro por {paciente.diagnoza}, con antecedentes de {paciente.diagnoza2}.",
               "Que desde el {ctx.zas_od} su estado de salud empeoró, con una descompensación del cuadro de base y de "
               "{paciente.diagnoza3}. Se aconseja reposo domiciliario desde el {ctx.zas_od} hasta el {ctx.zas_do}.",
               min=3, max=3),
        sekcja("capacity", "akapit",
               "En consecuencia, {paciente.rodzaj:el paciente|la paciente} no puede permanecer {paciente.rodzaj:sentado|sentada} más de "
               "dos horas seguidas, y tampoco desplazarse a la sede judicial, lo que afecta a la vista señalada "
               "para el {ctx.rozprawa} ante el {juzgado.nazwa} en los autos {juzgado.sygnatura}.",
               "Se ha pautado el siguiente tratamiento: {paciente.lek}, {paciente.lek2} y {paciente.lek3}.",
               min=2, max=2),
        sekcja("notice", "akapit",
               "Este certificado se basa en la exploración realizada el {ctx.zas_wystaw} y en los datos de la "
               "historia clínica del centro, y se expide a petición de la persona interesada para su presentación "
               "ante el órgano judicial.",
               "Los datos de salud contenidos en este documento están protegidos por el secreto profesional y por "
               "el artículo 9 del Reglamento (UE) 2016/679.",
               "El presente certificado no sustituye al parte de baja ni al de confirmación expedidos por el "
               "servicio público de salud.",
               min=2, max=3),
        sekcja("doctor", "akapit",
               "Médico: {medico.rodzaj:Dr.|Dra.} {medico.pelne}, n.º de colegiado {medico.colegiado}, "
               "tel. {medico.telefon}."),
        sekcja("signature", "podpis", "{medico.pelne}"),
        sekcja("footer", "stopka",
               "{clinica.nazwa} | {clinica.adres} | tel. {clinica.telefon} | {clinica.email}"),
    ],
    metadane={"author": "{medico.pelne}", "subject": "Certificado médico oficial"},
)
