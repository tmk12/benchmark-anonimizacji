"""Contrat de vente d'un véhicule d'occasion entre deux particuliers : numéro de sécurité sociale, immatriculation,
prix avec acompte et solde, tableau d'état. Le générateur ne produit pas de numéro VIN : le document n'en contient pas."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="fr", typ="umowa_sprzedazy_auta", dorosli=True,
    role={"vendeur": "osoba", "acheteur": "osoba", "vehicule": "sprawa", "temoin": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "CONTRAT DE VENTE D'UN VÉHICULE D'OCCASION",
               "Vendeur : {vendeur.pelne} | Acheteur : {acheteur.pelne}"),
        sekcja("opening", "akapit", "Entre les soussignés, à {vendeur.miasto}, le {ctx.dok} :"),
        sekcja("parties", "akapit",
               "{vendeur.pelne}, {vendeur.rodzaj:né|née} le {vendeur.data_ur}, numéro de sécurité sociale "
               "{vendeur.nir}, demeurant {vendeur.adres}, tél. {vendeur.telefon}, ci-après « le vendeur »,",
               "et",
               "{acheteur.pelne}, {acheteur.rodzaj:né|née} le {acheteur.data_ur}, demeurant {acheteur.adres}, tél. "
               "{acheteur.telefon}, courriel {acheteur.email}, ci-après « l'acheteur »."),
        sekcja("objet", "akapit",
               "Article 1 – Objet",
               "Le vendeur vend à l'acheteur le véhicule particulier d'occasion immatriculé {vehicule.tablica}, avec "
               "son certificat d'immatriculation, deux clés et son carnet d'entretien.",
               "Le vendeur déclare être le seul propriétaire du véhicule, qu'il n'est ni gagé ni saisi et qu'il n'a "
               "subi aucun sinistre grave non déclaré.",
               "L'assurance du véhicule court jusqu'au {ctx.dok_pozniej} ; le vendeur informe son assureur de la vente."),
        sekcja("prix", "akapit",
               "Article 2 – Prix et paiement",
               "Le prix de vente est fixé à {ctx.szkoda}.",
               "L'acheteur a versé à la signature un acompte de {ctx.zaliczka_ub} et paiera le solde par virement sur le "
               "compte du vendeur {vendeur.rachunek} au plus tard le {ctx.dok_termin}.",
               "Les frais de changement de titulaire du certificat d'immatriculation sont à la charge de l'acheteur."),
        sekcja("tableau", "komorka",
               "Élément | État | Observations\n"
               "Kilométrage | 187 450 km | selon le compteur\n"
               "Contrôle technique | valable jusqu'au {ctx.dok_pozniej} | rapport joint\n"
               "Sinistres | aucun | déclaration de {vendeur.pelne}",
               "Élément | Document | Remis à\n"
               "Certificat d'immatriculation | original | {acheteur.pelne}\n"
               "Clés | 2 jeux | {acheteur.pelne}\n"
               "Factures d'entretien | 9 | {temoin.pelne}",
               min=1, max=1),
        sekcja("remise", "akapit",
               "Article 3 – Remise du véhicule et garantie",
               "Le véhicule est remis le {ctx.dok_sprzedaz} au domicile du vendeur, en présence de {temoin.pelne} "
               "(tél. {temoin.telefon}) comme témoin de son état.",
               "L'acheteur a examiné et essayé le véhicule et l'achète dans son état actuel ; la garantie légale des "
               "vices cachés demeure applicable. Les risques sont transférés à la remise.",
               "Pour tout litige, les parties se rapprochent du tribunal compétent du domicile du défendeur."),
        sekcja("finales", "akapit",
               "Article 4 – Dispositions finales",
               "Toute modification doit être écrite et signée par les deux parties.",
               "Contact en cas de difficulté : {vendeur.email} et {acheteur.telefon}.",
               "Le contrat est établi en deux exemplaires, remis un à chaque partie."),
        sekcja("signature_etiquette", "akapit", "Le vendeur :                                                  L'acheteur :"),
        sekcja("signature", "podpis", "{vendeur.pelne}", "{acheteur.pelne}"),
        sekcja("pied", "stopka", "Vente du véhicule {vehicule.tablica} | {vendeur.pelne} / {acheteur.pelne}"),
        sekcja("note", "przypis",
               "L'acheteur effectue la demande de changement de titulaire dans un délai d'un mois ; le vendeur déclare "
               "la cession sur le site de l'administration."),
    ],
    metadane={"author": "{vendeur.pelne}", "title": "Contrat de vente de véhicule d'occasion"},
)
