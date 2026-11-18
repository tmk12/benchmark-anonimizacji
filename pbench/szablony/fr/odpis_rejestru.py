"""Extrait Kbis (extrait d'immatriculation principale au registre du commerce et des sociétés) d'une SARL: greffe du
tribunal de commerce, SIREN, numéro de gestion, dénomination, forme juridique, capital, siège, dates d'immatriculation et
de dernière mise à jour, gérants avec date et lieu de naissance, nationalité et domicile personnel. Daty z `Kontekst`:
immatriculation <= mise à jour <= délivrance. Un vrai Kbis ne contient ni NIR ni pièce d'identité – la tabela nie ma ID
osób. Lieu de naissance = ville de l'adresse (uproszczenie). Gérants pełnoletni (`dorosli`)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="fr", typ="odpis_rejestru", dorosli=True,
    role={"societe": "spolka", "gerant1": "osoba", "gerant2": "osoba", "gerant3": "osoba"},
    sekcje=[
        sekcja("titles", "naglowek",
               "EXTRAIT D'IMMATRICULATION PRINCIPALE AU REGISTRE DU COMMERCE ET DES SOCIÉTÉS",
               "Greffe du {societe.registro}",
               "{societe.nazwa}"),
        sekcja("identity", "komorka",
               "Rubrique | Mention\n"
               "Numéro d'identification (SIREN) | {societe.siren}\n"
               "Immatriculation au RCS | {societe.siren} {societe.rcs}\n"
               "Numéro de gestion | {ctx.nr_gestion}\n"
               "Dénomination | {societe.nazwa}\n"
               "Forme juridique | Société à responsabilité limitée\n"
               "Siège social | {societe.adres}\n"
               "Établissement principal (SIRET) | {societe.siret}"),
        sekcja("dates", "komorka",
               "Rubrique | Date / montant\n"
               "Date d'immatriculation | {ctx.kr_rejestracja}\n"
               "Date de dernière mise à jour | {ctx.kr_wpis}\n"
               "Capital social | {ctx.kapital2}"),
        sekcja("organs_title", "akapit",
               "Dirigeants",
               "Les dirigeants ci-dessous sont inscrits au registre à la date de délivrance de l'extrait."),
        sekcja("organs", "komorka",
               "N° | Qualité | Nom, prénoms | Date et lieu de naissance | Nationalité | Domicile personnel\n"
               "1 | Gérant | {gerant1.nazwisko:upper} {gerant1.imie} | {gerant1.data_ur} à {gerant1.miasto} | Française | "
               "{gerant1.adres}\n"
               "2 | Gérant | {gerant2.nazwisko:upper} {gerant2.imie} | {gerant2.data_ur} à {gerant2.miasto} | Française | "
               "{gerant2.adres}\n"
               "3 | Gérant | {gerant3.nazwisko:upper} {gerant3.imie} | {gerant3.data_ur} à {gerant3.miasto} | Française | "
               "{gerant3.adres}",
               "Rubrique | Mention\n"
               "Gérant | {gerant1.nazwisko:upper} {gerant1.imie}\n"
               "Date et lieu de naissance | {gerant1.data_ur} à {gerant1.miasto}\n"
               "Domicile personnel | {gerant1.adres}\n"
               "Gérant | {gerant2.nazwisko:upper} {gerant2.imie}\n"
               "Date et lieu de naissance | {gerant2.data_ur} à {gerant2.miasto}\n"
               "Domicile personnel | {gerant2.adres}",
               min=1, max=1),
        sekcja("oversight", "akapit",
               "Activité principale : toutes prestations de services, achat et vente de biens et d'équipements, et toutes "
               "opérations s'y rattachant.",
               "Durée de la personne morale : 99 ans à compter de la date d'immatriculation. Date de clôture de "
               "l'exercice social : 31 décembre.",
               "Observations : néant. À la date de délivrance, aucune procédure collective n'est mentionnée.",
               min=3, max=3),
        sekcja("certification", "akapit",
               "Fin de l'extrait. Ce document est délivré à titre d'information ; son authenticité peut être vérifiée "
               "auprès du greffe au moyen du code figurant sur le document. De nombreuses administrations exigent un extrait "
               "de moins de trois mois.",
               "Extrait délivré le {ctx.dok} par le greffe du {societe.registro}."),
        sekcja("footer", "stopka",
               "Extrait Kbis | {societe.rcs} {societe.siren} | Délivré le {ctx.dok} | Page 1 sur 2"),
    ],
    metadane={"subject": "Extrait Kbis", "entity": "{societe.nazwa}"},
)
