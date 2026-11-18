"""Mandat et pouvoir spécial donnés par un particulier à deux avocats d'un cabinet pour une procédure de recouvrement
(« Bon pour pouvoir »): mandant, mandataires, étendue du pouvoir (y compris transiger), mentions d'information, lieu et
date. Date `ctx.dok`; wszystkie osoby pełnoletnie (`dorosli`)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja
from ._formy import civ, g

SZABLON = Szablon(
    jezyk="fr", typ="pelnomocnictwo", dorosli=True,
    role={"cabinet": "kancelaria", "mandant": "osoba", "avocat1": "osoba", "avocat2": "osoba",
          "adversaire": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{cabinet.nazwa}",
               "{cabinet.adres} | Tél. {cabinet.telefon} | {cabinet.email}"),
        sekcja("title", "akapit",
               "MANDAT ET POUVOIR SPÉCIAL",
               "Réf. : AV-{ctx.udzialy2}"),
        sekcja("principal", "akapit",
               g("mandant", "Je soussigné", "Je soussignée") + ", {mandant.pelne}, " + g("mandant", "né", "née")
               + " le {mandant.data_ur}, demeurant {mandant.adres}, courriel {mandant.email},",
               "donne mandat et pouvoir spécial à Maître {avocat1.pelne} et à Maître {avocat2.pelne}, avocats associés "
               "de la {cabinet.nazwa}, {cabinet.adres},",
               "à l'effet de me représenter dans l'affaire " + civ("mandant") + " {mandant.pelne} contre " + civ("adversaire")
               + " {adversaire.pelne}, demeurant {adversaire.adres}, relative au recouvrement d'une créance (principal : "
               "{ctx.glowna}),",
               "et d'accomplir à cette fin tous les actes de procédure utiles.",
               min=4, max=4),
        sekcja("scope", "akapit",
               "Ce pouvoir comprend celui d'introduire et de poursuivre toute instance devant les juridictions civiles, "
               "d'interjeter appel, de se désister de l'instance ou de l'appel et d'exercer toute voie d'exécution.",
               "Il autorise mes mandataires à transiger en mon nom et pour mon compte, à accepter toute réduction de ma "
               "créance et à signer tout protocole d'accord.",
               "Les mandataires peuvent recevoir toute somme versée par la partie adverse, notamment au titre des dépens "
               "et des frais irrépétibles, et en donner quittance.",
               "Ils peuvent se substituer tout autre avocat du cabinet pour l'exécution du présent mandat.",
               min=3, max=4),
        sekcja("extent", "akapit",
               "Ce pouvoir s'étend aux procédures accessoires : référé, mesures conservatoires, procédures d'exécution et "
               "taxation des dépens.",
               "Il est valable jusqu'à sa révocation écrite de ma part."),
        sekcja("notices", "akapit",
               "Les honoraires du cabinet sont fixés par une convention écrite distincte, conclue avec l'avocat chargé du "
               "dossier.",
               "Mes données personnelles sont traitées par le cabinet pour la gestion du dossier, sur le fondement de "
               "l'exécution du contrat (article 6, paragraphe 1, point b du RGPD).",
               "J'ai été " + g("mandant", "informé", "informée") + " que le cabinet est tenu au secret professionnel et "
               "aux obligations de vigilance prévues en matière de lutte contre le blanchiment.",
               min=3, max=3),
        sekcja("place_date", "akapit",
               "Fait à {mandant.miasto}, le {ctx.dok}",
               "Bon pour pouvoir"),
        sekcja("signature", "podpis", "{mandant.pelne}"),
        sekcja("footer", "stopka",
               "{cabinet.nazwa} | {cabinet.adres} | Tél. {cabinet.telefon} | {cabinet.email}"),
    ],
    metadane={"author": "{avocat1.pelne}", "subject": "Mandat et pouvoir spécial"},
)
