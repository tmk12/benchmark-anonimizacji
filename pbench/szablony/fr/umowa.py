"""Contrat de prestation de services (assistance et maintenance informatique) entre deux SARL: parties (représentées par
leur gérant), préambule, articles (objet, durée, prix avec TVA 20 %, confidentialité, données personnelles, responsabilité,
résiliation, notifications, dispositions générales), signatures. Montants et dates de `Kontekst`; articles numérotés en
dur (sans lacunes). Spółka FR jest zawsze SARL, więc reprezentantem jest gérant; obaj podpisujący pełnoletni (`dorosli`)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja
from ._formy import civ, g

SZABLON = Szablon(
    jezyk="fr", typ="umowa", dorosli=True,
    role={"prestataire": "spolka", "client": "spolka", "gerant_p": "osoba", "gerant_c": "osoba",
          "contact": "osoba", "suppleant": "osoba", "referent": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{prestataire.nazwa}",
               "{prestataire.adres} | Tél. {prestataire.telefon} | {prestataire.email}",
               "SIREN {prestataire.siren} | TVA intracommunautaire {prestataire.vat}"),
        sekcja("title", "akapit",
               "CONTRAT DE PRESTATION DE SERVICES",
               "Assistance et maintenance du système d'information",
               "Fait à {prestataire.miasto}, le {ctx.dok}"),
        sekcja("between", "akapit", "ENTRE LES SOUSSIGNÉS :"),
        sekcja("parties", "akapit",
               "La société {prestataire.nazwa}, société à responsabilité limitée au capital de {ctx.kapital2}, dont le "
               "siège social est situé {prestataire.adres}, inscrite au {prestataire.rcs} sous le numéro "
               "{prestataire.siren}, représentée par son gérant, " + civ("gerant_p") + " {gerant_p.pelne}, dûment "
               + g("gerant_p", "habilité", "habilitée") + " aux fins des présentes, ci-après dénommée « le Prestataire »,",
               "ET",
               "La société {client.nazwa}, société à responsabilité limitée au capital de {ctx.kapital3}, dont le siège "
               "social est situé {client.adres}, inscrite au {client.rcs} sous le numéro {client.siren}, représentée par "
               "son gérant, " + civ("gerant_c") + " {gerant_c.pelne}, dûment " + g("gerant_c", "habilité", "habilitée")
               + ", ci-après dénommée « le Client »,",
               "Le Prestataire et le Client sont ci-après désignés ensemble « les Parties » et individuellement « la "
               "Partie »."),
        sekcja("preamble", "akapit",
               "PRÉAMBULE",
               "Le Client exerce une activité de services et dispose d'un parc informatique qu'il souhaite confier à un "
               "prestataire spécialisé pour sa maintenance. Le Prestataire déclare disposer de l'expérience et des moyens "
               "nécessaires. Les Parties sont convenues de ce qui suit :"),
        sekcja("scope", "akapit",
               "Article 1 – Objet du contrat",
               "1.1 Le Prestataire s'engage à fournir au Client des prestations d'assistance, de maintenance corrective "
               "et évolutive de son système d'information, ainsi que la conservation de sauvegardes (les « Prestations »).",
               "1.2 Les Prestations ne comprennent ni la fourniture de matériel ni le développement de nouveaux "
               "logiciels, qui feront l'objet de devis distincts.",
               "1.3 Le référent du Prestataire est " + civ("contact") + " {contact.pelne} ; en cas d'empêchement, "
               + civ("suppleant") + " {suppleant.pelne}. Tout changement de référent est notifié au Client par courriel.",
               "1.4 Le Client désigne " + civ("referent") + " {referent.pelne} (tél. {referent.telefon}, courriel "
               "{referent.email}) comme interlocuteur chargé de transmettre les informations nécessaires."),
        sekcja("term", "akapit",
               "Article 2 – Durée",
               "Le contrat prend effet le {ctx.od_dnia} pour une durée initiale de douze mois. Il se renouvelle ensuite "
               "par tacite reconduction pour des périodes successives de douze mois, sauf dénonciation par l'une des "
               "Parties par lettre recommandée avec demande d'avis de réception adressée trois mois avant l'échéance."),
        sekcja("fees", "akapit",
               "Article 3 – Prix et conditions de paiement",
               "3.1 En contrepartie des Prestations, le Client verse au Prestataire un forfait mensuel de {ctx.um_wyn} "
               "hors taxes, majoré de la TVA au taux en vigueur, soit actuellement 20 %.",
               "3.2 Le forfait couvre jusqu'à vingt heures d'intervention par mois. Les heures supplémentaires sont "
               "facturées au tarif en vigueur du Prestataire, dans la limite de {ctx.um_limit} hors taxes par mois sans "
               "accord écrit préalable du Client.",
               "3.3 Les factures sont payables à trente jours à compter de leur date d'émission, par virement sur le "
               "compte du Prestataire {prestataire.rachunek}. Tout retard de paiement entraîne de plein droit des "
               "pénalités au taux de trois fois le taux d'intérêt légal, ainsi qu'une indemnité forfaitaire de quarante "
               "euros pour frais de recouvrement."),
        sekcja("confidentiality", "akapit",
               "Article 4 – Confidentialité",
               "Chaque Partie s'engage à garder strictement confidentielles les informations de toute nature, "
               "techniques, commerciales ou financières, dont elle a connaissance à l'occasion du contrat, pendant sa "
               "durée et pendant cinq ans après son terme."),
        sekcja("data", "akapit",
               "Article 5 – Protection des données personnelles",
               "Lorsque le Prestataire accède à des données à caractère personnel du Client, il agit en qualité de "
               "sous-traitant au sens du règlement (UE) 2016/679 (RGPD) et de la loi du 6 janvier 1978 relative à "
               "l'informatique, aux fichiers et aux libertés. Un accord de traitement conforme à l'article 28 du RGPD est "
               "annexé au contrat."),
        sekcja("liability", "akapit",
               "Article 6 – Responsabilité",
               "6.1 Le Prestataire est tenu d'une obligation de moyens. Sa responsabilité ne peut être engagée qu'en cas "
               "de faute prouvée et est limitée, tous dommages confondus et par année contractuelle, à la somme de "
               "{ctx.um_kara}.",
               "6.2 Cette limitation ne s'applique ni en cas de faute lourde ou dolosive ni aux dommages corporels."),
        sekcja("termination", "akapit",
               "Article 7 – Résiliation",
               "En cas de manquement grave de l'une des Parties à ses obligations, non réparé dans un délai de trente "
               "jours après une mise en demeure adressée par lettre recommandée avec demande d'avis de réception, l'autre "
               "Partie peut résilier le contrat de plein droit, sans préjudice de tous dommages et intérêts."),
        sekcja("notices", "akapit",
               "Article 8 – Notifications",
               "Toute notification est valablement faite par lettre recommandée avec demande d'avis de réception "
               "adressée au siège de la Partie destinataire ({client.adres} pour le Client, {prestataire.adres} pour le "
               "Prestataire) ou par courriel avec accusé de réception."),
        sekcja("final", "akapit",
               "Article 9 – Dispositions générales",
               "9.1 Toute modification du contrat fait l'objet d'un avenant écrit signé des deux Parties.",
               "9.2 Si l'une des stipulations du contrat est déclarée nulle, les autres stipulations demeurent en vigueur.",
               "9.3 Le contrat est soumis au droit français. À défaut de règlement amiable, tout litige relève de la "
               "compétence exclusive du {prestataire.registro}."),
        sekcja("place_date", "akapit",
               "Fait à {prestataire.miasto}, le {ctx.dok}, en deux exemplaires originaux.",
               "Pour le Prestataire : " + g("gerant_p", "son gérant", "sa gérante"),
               "Pour le Client : " + g("gerant_c", "son gérant", "sa gérante")),
        sekcja("signatures", "podpis", "{gerant_p.pelne}", "{gerant_c.pelne}"),
        sekcja("footer", "stopka",
               "{prestataire.nazwa} | {prestataire.adres} | SIREN {prestataire.siren} | TVA intracommunautaire "
               "{prestataire.vat} | Tél. {prestataire.telefon} | {prestataire.email}"),
    ],
    metadane={"author": "{gerant_p.pelne}", "subject": "Contrat de prestation de services d'assistance et de "
                                                       "maintenance informatique"},
)
