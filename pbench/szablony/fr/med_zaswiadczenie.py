"""Certificat médical (arrêt de travail et impossibilité de comparaître) d'une consultation de médecine interne d'une
clinique, à présenter au tribunal judiciaire pour obtenir le renvoi d'une audience: diagnostics selon la CIM-10, repos de
`zas_od` à `zas_do`, audience `rozprawa`, mention de l'avis d'arrêt de travail transmis à la CPAM. Daty: zas_od < zas_wystaw
< rozprawa < zas_do; numéro RG cohérent avec la juridiction. Médecin avec numéro RPPS (NR_ID); patient avec NIR."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja
from ._formy import civ, g

SZABLON = Szablon(
    jezyk="fr", typ="med_zaswiadczenie", warianty=("fr_tj_unique", "fr_tj_collegiale"), profil="medecine_interne",
    role={"etablissement": "placowka", "patient": "pacjent", "medecin": "lekarz", "sad": "sad"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{etablissement.nazwa}",
               "Consultations de médecine interne",
               "{etablissement.adres} | Tél. {etablissement.telefon} | SIRET {etablissement.siret}"),
        sekcja("place", "akapit", "{etablissement.miasto}, le {ctx.zas_wystaw}"),
        sekcja("title", "akapit",
               "CERTIFICAT MÉDICAL",
               "Arrêt de travail et impossibilité de comparaître"),
        sekcja("body", "akapit",
               g("medecin", "Je soussigné", "Je soussignée") + ", Docteur {medecin.pelne} (RPPS {medecin.rpps}), certifie "
               "que " + civ("patient") + " {patient.pelne}, " + g("patient", "né", "née") + " le {patient.data_ur}, "
               "demeurant {patient.adres}, numéro de sécurité sociale {patient.nir}, est "
               + g("patient", "suivi", "suivie") + " dans mon service.",
               "À la demande de " + g("patient", "l'intéressé", "l'intéressée") + " et pour être remis en main propre à "
               "son avocat, le présent certificat précise l'état de santé suivant. Diagnostic principal (CIM-10) : "
               "{patient.diagnoza}. Antécédent : {patient.diagnoza2}.",
               "Depuis le {ctx.zas_od}, l'état de santé s'est dégradé. Diagnostic associé retenu à cette date (CIM-10) : "
               "{patient.diagnoza3}. Un repos strict et un arrêt de travail sont prescrits du {ctx.zas_od} au {ctx.zas_do}.",
               min=3, max=3),
        sekcja("capacity", "akapit",
               "Compte tenu de cet état, " + g("patient", "le patient", "la patiente") + " n'est pas en mesure de se "
               "déplacer ni de participer à une audience pendant cette période, notamment celle du {ctx.rozprawa} devant "
               "le {sad.nazwa} (affaire {sad.sygnatura}).",
               "Traitement habituel " + g("patient", "du patient", "de la patiente") + ", mentionné sans lien établi avec les "
               "diagnostics ci-dessus : {patient.lek} ; {patient.lek2} ; {patient.lek3}.",
               min=2, max=2),
        sekcja("notice", "akapit",
               "Le présent certificat est établi après l'examen du {ctx.zas_wystaw} et au vu du dossier médical ; il est "
               "remis à " + g("patient", "l'intéressé", "l'intéressée") + " à sa demande, pour faire valoir ce que de "
               "droit.",
               "Les informations de santé qu'il contient sont couvertes par le secret médical (article L. 1110-4 du Code "
               "de la santé publique) et par le RGPD.",
               "L'avis d'arrêt de travail a été transmis par voie dématérialisée à la caisse primaire d'assurance "
               "maladie (CPAM) ; l'employeur reçoit le volet qui le concerne, qui ne mentionne pas le diagnostic.",
               min=2, max=3),
        sekcja("doctor", "akapit",
               "Docteur {medecin.pelne}, médecin spécialiste en médecine interne, tél. {medecin.telefon}."),
        sekcja("signature", "podpis", "{medecin.pelne}"),
        sekcja("footer", "stopka",
               "{etablissement.nazwa} | {etablissement.adres} | Tél. {etablissement.telefon} | {etablissement.email}"),
    ],
    metadane={"author": "{medecin.pelne}", "subject": "Certificat médical – arrêt de travail"},
)
