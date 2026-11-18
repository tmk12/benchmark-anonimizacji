"""Contrat de bail d'habitation meublée entre deux particuliers (bailleur – locataire) selon la loi du 6 juillet 1989,
avec dépôt de garantie d'un mois de loyer, état des lieux et coordonnées."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="fr", typ="umowa_najmu", dorosli=True,
    role={"bailleur": "osoba", "locataire": "osoba", "logement": "osoba", "temoin": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "CONTRAT DE LOCATION D'UN LOGEMENT À USAGE D'HABITATION",
               "Bailleur : {bailleur.pelne} | Locataire : {locataire.pelne}"),
        sekcja("opening", "akapit", "Entre les soussignés, à {bailleur.miasto}, le {ctx.dok} :"),
        sekcja("parties", "akapit",
               "{bailleur.pelne}, {bailleur.rodzaj:né|née} le {bailleur.data_ur}, numéro de sécurité sociale "
               "{bailleur.nir}, demeurant {bailleur.adres}, tél. {bailleur.telefon}, courriel {bailleur.email}, ci-après "
               "« le bailleur »,",
               "et",
               "{locataire.pelne}, {locataire.rodzaj:né|née} le {locataire.data_ur}, numéro de sécurité sociale "
               "{locataire.nir}, demeurant actuellement {locataire.adres}, tél. {locataire.telefon}, courriel "
               "{locataire.email}, ci-après « le locataire »."),
        sekcja("objet", "akapit",
               "Article 1 – Objet",
               "Le bailleur loue au locataire le logement situé {logement.adres}, avec cave et place de parking, "
               "occupé jusqu'au {ctx.umowa_dawna} par {logement.pelne}.",
               "Le logement est destiné à la résidence principale du locataire et des personnes qu'il déclare par "
               "écrit au bailleur ; toute sous-location est interdite sans l'accord écrit du bailleur."),
        sekcja("duree", "akapit",
               "Article 2 – Durée",
               "Le bail du logement meublé est conclu pour un an à compter du {ctx.od_dnia}, soit jusqu'au {ctx.dok_pozniej}, et "
               "se renouvelle par tacite reconduction.",
               "Le locataire peut donner congé à tout moment avec un préavis d'un mois ; le bailleur peut donner congé "
               "avec un préavis de trois mois avant l'échéance, dans les cas prévus par l'article 25-8 de la loi du 6 juillet 1989."),
        sekcja("loyer", "akapit",
               "Article 3 – Loyer et dépôt de garantie",
               "Le loyer mensuel est fixé à {ctx.zaliczka_kosztow}, payable d'avance avant le cinq de chaque mois par "
               "virement sur le compte du bailleur {bailleur.rachunek}.",
               "Le locataire verse un dépôt de garantie de {ctx.zaliczka_kosztow} (un mois de loyer hors charges), "
               "restitué dans un délai d'un mois à compter de la remise des clés si l'état des lieux de sortie est "
               "conforme à celui d'entrée.",
               "Les consommations d'eau, d'électricité, de chauffage et d'internet sont à la charge du locataire."),
        sekcja("obligations", "akapit",
               "Article 4 – Obligations des parties",
               "Le locataire use paisiblement des lieux, répond des dégradations et assure les réparations locatives "
               "courantes ; il informe sans délai le bailleur de tout désordre.",
               "Le bailleur ne peut pénétrer dans le logement qu'avec l'accord du locataire et après un préavis de "
               "deux jours, sauf urgence.",
               "L'état des lieux d'entrée et la remise des clés ont lieu le {ctx.od_dnia} ; {temoin.pelne} (tél. "
               "{temoin.telefon}) y assiste pour le bailleur.",
               min=2, max=3),
        sekcja("tableau", "komorka",
               "Poste | Relevé à l'entrée | Observations\n"
               "Compteur d'électricité | 04 213 kWh | relevé en présence des parties\n"
               "Compteur d'eau | 118 m3 | sans remarque\n"
               "Clés | 3 jeux | remises à {locataire.pelne}",
               "Poste | Échéance | Responsable\n"
               "Paiement du loyer | avant le cinq du mois | {locataire.pelne}\n"
               "Restitution du dépôt | un mois après la remise des clés | {bailleur.pelne}\n"
               "État des lieux d'entrée | {ctx.od_dnia} | {temoin.pelne}",
               min=1, max=1),
        sekcja("finales", "akapit",
               "Article 5 – Dispositions finales",
               "Toute modification du présent contrat doit faire l'objet d'un avenant écrit et signé par les deux parties.",
               "Les notifications sont adressées aux adresses ci-dessus ou par courriel à {bailleur.email} et "
               "{locataire.email}.",
               "Le contrat est établi en deux exemplaires originaux, remis un à chaque partie."),
        sekcja("signature_etiquette", "akapit", "Le bailleur :                                                  Le locataire :"),
        sekcja("signature", "podpis", "{bailleur.pelne}", "{locataire.pelne}"),
        sekcja("pied", "stopka", "Bail d'habitation – {bailleur.pelne} / {locataire.pelne} | Logement : {logement.adres}"),
        sekcja("note", "przypis",
               "Sont annexés au bail le diagnostic de performance énergétique et la notice d'information, remis au "
               "locataire le {ctx.dok}."),
    ],
    metadane={"author": "{bailleur.pelne}", "title": "Contrat de location d'habitation"},
)
