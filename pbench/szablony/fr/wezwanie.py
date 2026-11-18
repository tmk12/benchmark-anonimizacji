"""Mise en demeure de payer (lettre recommandée avec demande d'avis de réception) adressée par un avocat, pour le compte
d'une SARL créancière (représentée par son gérant), à un particulier: principal, intérêts au taux légal, frais, délai de
paiement, suites. Daty i kwoty z `Kontekst` (prestation < exigibilité < mise en demeure < fin du délai)."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja
from ._formy import civ, g

SZABLON = Szablon(
    jezyk="fr", typ="wezwanie",
    role={"cabinet": "kancelaria", "avocat": "osoba", "creancier": "spolka", "representant": "osoba",
          "debiteur": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{cabinet.nazwa}",
               "{cabinet.adres} | Tél. {cabinet.telefon} | {cabinet.email}",
               "SIREN {cabinet.siren} | TVA intracommunautaire {cabinet.vat}"),
        sekcja("date", "akapit",
               "{cabinet.miasto}, le {ctx.wezwanie}",
               "Lettre recommandée avec demande d'avis de réception",
               "N/Réf. : AV-{ctx.udzialy1}"),
        sekcja("addressee", "akapit",
               civ("debiteur") + " {debiteur.pelne}",
               "{debiteur.adres}"),
        sekcja("subject", "akapit",
               "Objet : Mise en demeure de payer",
               "Créance : société {creancier.nazwa}"),
        sekcja("salutation", "akapit", civ("debiteur") + ","),
        sekcja("basis", "akapit",
               "Je suis le conseil de la société {creancier.nazwa}, {creancier.adres} (SIREN {creancier.siren}, TVA "
               "{creancier.vat}), représentée par " + g("representant", "son gérant", "sa gérante") + ", "
               + civ("representant") + " {representant.pelne}.",
               "Ma cliente vous a facturé le {ctx.umowa} des prestations dont le montant est devenu exigible le "
               "{ctx.termin_platnosci}. Malgré un rappel amiable, aucun paiement n'est intervenu.",
               "Restent dus : le principal de {ctx.glowna}, les intérêts de retard au taux légal arrêtés à ce jour pour "
               "{ctx.odsetki} et les frais de recouvrement de {ctx.koszty_wind}. La créance s'élève ainsi à "
               "{ctx.razem_wez}.",
               "À défaut de paiement à l'échéance, vous êtes en situation de retard ; la présente vaut mise en demeure "
               "au sens de l'article 1344 du Code civil."),
        sekcja("payment", "akapit",
               "Je vous mets en demeure de régler la somme totale de {ctx.razem_wez} au plus tard le "
               "{ctx.termin_wezwania}, par virement sur le compte de ma cliente {creancier.rachunek}, en rappelant ma "
               "référence."),
        sekcja("schedule", "akapit",
               "Si vous ne pouvez pas régler en une fois, ma cliente est disposée à accepter un échéancier, à condition "
               "que le premier versement soit au moins de {ctx.ugoda_rata} et intervienne avant cette date.",
               min=0, max=1),
        sekcja("consequences", "akapit",
               "À défaut de règlement dans ce délai, ma cliente saisira sans autre avis la juridiction compétente, "
               "notamment par une procédure d'injonction de payer ou par assignation, ce qui entraînera pour vous des "
               "frais de justice supplémentaires.",
               "Je vous rappelle que les intérêts continueront de courir au taux légal jusqu'au paiement complet.",
               "Vos données personnelles sont traitées dans le cadre de cette procédure de recouvrement, sur le "
               "fondement de l'intérêt légitime de ma cliente (article 6, paragraphe 1, point f du RGPD).",
               min=2, max=3),
        sekcja("contact", "akapit",
               "Pour toute question, vous pouvez contacter Maître {avocat.pelne} au {avocat.telefon} ou à l'adresse "
               "{avocat.email}."),
        sekcja("close", "akapit",
               "Je vous prie d'agréer, " + civ("debiteur") + ", l'expression de mes salutations distinguées."),
        sekcja("signature", "podpis", "{avocat.pelne}"),
        sekcja("footer", "stopka",
               "{cabinet.nazwa} | {cabinet.adres} | SIREN {cabinet.siren} | TVA intracommunautaire {cabinet.vat} | "
               "Tél. {cabinet.telefon} | {cabinet.email}"),
    ],
    metadane={"author": "{avocat.pelne}", "subject": "Mise en demeure de payer"},
)
