"""Lettre de liaison à la sortie d'hospitalisation (service de cardiologie d'une clinique) adressée au médecin traitant:
identité du patient (NIR), diagnostics selon la CIM-10, motif et évolution, traitement de sortie, suites à donner (contrôle,
arrêt de travail), mentions (secret médical, personne de confiance), médecins signataires avec leur numéro RPPS. Daty z
`Kontekst`: admission < sortie < contrôle; arrêt de travail jusqu'à `zwolnienie_do`. Narracja dotyczy niewydolności serca."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja
from ._formy import civ, g

SZABLON = Szablon(
    jezyk="fr", typ="med_wypis", profil="cardiologie",
    role={"clinique": "placowka", "patient": "pacjent", "cardiologue": "lekarz", "chef": "lekarz",
          "proche": "osoba", "traitant": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{clinique.nazwa}",
               "{clinique.adres} | Tél. {clinique.telefon} | SIRET {clinique.siret}"),
        sekcja("title", "akapit",
               "LETTRE DE LIAISON À LA SORTIE – SERVICE DE CARDIOLOGIE",
               g("traitant", "Cher confrère", "Chère consœur") + ","),
        sekcja("patient", "akapit",
               "Nous vous écrivons au sujet de " + civ("patient") + " {patient.pelne}, " + g("patient", "né", "née")
               + " le {patient.data_ur}, demeurant {patient.adres}.",
               "Numéro de sécurité sociale (NIR) : {patient.nir} | Téléphone : {patient.telefon}",
               "Hospitalisation du {ctx.przyjecie} au {ctx.wypis}, admission en urgence.",
               min=3, max=3),
        sekcja("diagnoses", "akapit",
               "Diagnostic principal (CIM-10) : {patient.diagnoza}",
               "Diagnostics associés : {patient.diagnoza2} ; {patient.diagnoza3}"),
        sekcja("history", "akapit",
               "Motif d'hospitalisation : dyspnée d'effort croissante, douleurs thoraciques et œdèmes des membres "
               "inférieurs. À l'examen d'entrée : tachycardie, crépitants aux deux bases, tension artérielle à 165/95 mmHg "
               "et saturation en oxygène à 93 % en air ambiant.",
               "Examens complémentaires : bilan biologique (numération, CRP, créatinine, ionogramme, troponine "
               "ultrasensible, NT-proBNP), électrocardiogramme, radiographie thoracique et échocardiographie "
               "transthoracique. Les comptes rendus détaillés figurent dans le dossier.",
               "Évolution : sous oxygénothérapie, diurétiques par voie intraveineuse, prévention thromboembolique et "
               "traitement antihypertenseur, l'état clinique s'est amélioré rapidement, les œdèmes ont régressé et la "
               "tension s'est stabilisée.",
               "Aucune complication ni événement indésirable n'est survenu pendant l'hospitalisation. Aucun avis "
               "spécialisé complémentaire n'a été nécessaire.",
               min=4, max=4),
        sekcja("discharge", "akapit",
               "Conseils de sortie : régime pauvre en sel, restriction hydrique à 1,5 litre par jour, pesée quotidienne le "
               "matin, pas d'effort physique important pendant les deux prochaines semaines, arrêt complet du tabac.",
               "Traitement de sortie (posologies indiquées pour chaque médicament) : {patient.lek} ; {patient.lek2} ; "
               "{patient.lek3}. Les adaptations de doses seront faites en consultation de cardiologie.",
               "Suites à donner : consultation de contrôle en cardiologie le {ctx.kontrola}, avec un bilan biologique "
               "préalable (numération, créatinine, kaliémie). Merci de remettre cette lettre "
               + g("patient", "au patient", "à la patiente") + " pour le rendez-vous.",
               "Arrêt de travail : un arrêt de travail a été délivré jusqu'au {ctx.zwolnienie_do}.",
               min=4, max=4),
        sekcja("information", "akapit",
               g("patient", "Le patient", "La patiente") + " a été " + g("patient", "informé", "informée") + " de sa "
               "maladie et de son traitement le jour de la sortie ; avec son accord, des informations peuvent être "
               "communiquées à " + civ("proche") + " {proche.pelne}, personne de confiance (tél. {proche.telefon}).",
               "Cette lettre contient des données de santé couvertes par le secret médical (article L. 1110-4 du Code de "
               "la santé publique) et protégées par le RGPD.",
               "En cas de douleur thoracique, de malaise ou d'essoufflement croissant, appeler le 15 (SAMU) ou le 112.",
               min=2, max=3),
        sekcja("clinicians", "akapit",
               "Confraternellement,",
               "Docteur {cardiologue.pelne}, cardiologue, RPPS {cardiologue.rpps}",
               g("chef", "Professeur", "Professeure") + " {chef.pelne}, " + g("chef", "chef de service", "cheffe de service")
               + ", RPPS {chef.rpps}"),
        sekcja("signatures", "podpis", "{cardiologue.pelne}", "{chef.pelne}"),
        sekcja("footer", "stopka", "{clinique.nazwa} | {clinique.adres} | Tél. {clinique.telefon} | {clinique.email}"),
    ],
    metadane={"author": "{cardiologue.pelne}", "subject": "Lettre de liaison – sortie d'hospitalisation"},
)
