"""Assignation d'un particulier contre un particulier en paiement du solde du prix d'un véhicule vendu, devant le
tribunal judiciaire (représentation par avocat ; huissier de justice pour la signification). Pas de droit de timbre."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja

SZABLON = Szablon(
    jezyk="fr", typ="pozew_zaplata_osoby", warianty=("fr_tj_unique",), dorosli=True,
    role={"avocat": "osoba", "demandeur": "osoba", "defendeur": "osoba", "huissier": "osoba", "temoin1": "osoba",
          "temoin2": "osoba", "vehicule": "sprawa", "sad": "sad"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "Maître {avocat.pelne}, avocat",
               "{avocat.adres} | Tél. {avocat.telefon} | {avocat.email}"),
        sekcja("court", "akapit",
               "{sad.nazwa:upper}",
               "ASSIGNATION EN PAIEMENT",
               "Le {ctx.pozew}"),
        sekcja("requete", "akapit",
               "À LA REQUÊTE DE : {demandeur.pelne}, {demandeur.rodzaj:né|née} le {demandeur.data_ur}, demeurant "
               "{demandeur.adres}, numéro de sécurité sociale {demandeur.nir},",
               "Ayant pour avocat Maître {avocat.pelne}, {avocat.adres}.",
               "J'AI, Maître {huissier.pelne}, commissaire de justice, DONNÉ ASSIGNATION À : {defendeur.pelne}, "
               "{defendeur.rodzaj:né|née} le {defendeur.data_ur}, demeurant {defendeur.adres},",
               "D'AVOIR À COMPARAÎTRE devant le {sad.nazwa}, à l'audience du {ctx.rozprawa}, selon la procédure écrite ordinaire."),
        sekcja("notice", "akapit",
               "Faute de constituer avocat dans un délai de quinze jours, le défendeur s'expose à un jugement rendu "
               "sur les seuls éléments fournis par le demandeur.",
               "Créance : {ctx.glowna}, outre intérêts au taux légal et frais."),
        sekcja("faits_titre", "akapit", "I. FAITS"),
        sekcja("faits", "akapit",
               "Le {ctx.umowa}, {demandeur.pelne} a vendu à {defendeur.pelne} le véhicule immatriculé {vehicule.tablica} "
               "et l'a remis le jour même.",
               "{defendeur.pelne} n'a réglé qu'une partie du prix ; le solde de {ctx.glowna} devait être viré sur le "
               "compte {demandeur.rachunek} avant le {ctx.termin_platnosci} et n'a pas été payé.",
               "Une mise en demeure a été envoyée le {ctx.wezwanie} à {defendeur.adres}, avec délai jusqu'au "
               "{ctx.termin_wezwania}. Elle est restée sans effet.",
               "{defendeur.pelne} a reconnu la dette devant {temoin1.pelne}, puis lors d'un appel entendu par "
               "{temoin2.pelne} (tél. {temoin2.telefon}).",
               min=3, max=4),
        sekcja("droit_titre", "akapit", "II. DISCUSSION"),
        sekcja("droit", "akapit",
               "Aux termes de l'article 1650 du code civil, le principal devoir de l'acheteur est de payer le prix au "
               "jour et au lieu réglés par la vente.",
               "L'article 1231-6 du code civil fait courir les intérêts moratoires à compter de la mise en demeure.",
               "Le tribunal judiciaire de {sad.miasto} est compétent en application de l'article 46 du code de procédure civile.",
               min=2, max=3),
        sekcja("motifs", "akapit",
               "PAR CES MOTIFS, il est demandé au tribunal de condamner {defendeur.pelne} à payer à {demandeur.pelne} "
               "la somme de {ctx.glowna}, outre intérêts au taux légal depuis le {ctx.termin_wezwania}, et la somme de "
               "{ctx.koszty_zast} au titre de l'article 700 du code de procédure civile."),
        sekcja("bordereau", "akapit",
               "Bordereau de pièces :",
               "1. Contrat de vente du {ctx.umowa},",
               "2. Relevé du compte {demandeur.rachunek},",
               "3. Mise en demeure du {ctx.wezwanie} et accusé de réception."),
        sekcja("signature", "podpis", "{avocat.pelne}"),
        sekcja("pied", "stopka", "{avocat.pelne} | {avocat.adres} | Tél. {avocat.telefon} | {avocat.email}"),
        sekcja("note", "przypis",
               "Acte signifié par {huissier.pelne}, commissaire de justice ; le coût de l'acte est avancé par le demandeur."),
    ],
    metadane={"author": "{avocat.pelne}", "subject": "Assignation en paiement entre particuliers"},
)
