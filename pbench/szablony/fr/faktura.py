"""Facture d'honoraires d'un cabinet d'avocats (SELARL) à une entreprise avec les mentions obligatoires: numéro, dates
d'émission et de prestation, identité des parties (SIREN, TVA intracommunautaire), désignation, prix HT, TVA 20 %, total TTC
(sommes de `Kontekst`), conditions de règlement, pénalités de retard et indemnité forfaitaire de recouvrement."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja
from ._formy import g

SZABLON = Szablon(
    jezyk="fr", typ="faktura",
    role={"vendeur": "kancelaria", "acheteur": "firma", "emetteur": "osoba", "destinataire": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{vendeur.nazwa}",
               "{vendeur.adres} | SIREN {vendeur.siren} | TVA intracommunautaire {vendeur.vat}"),
        sekcja("title", "akapit",
               "FACTURE N° F-{ctx.udzialy1}",
               "Date d'émission : {ctx.dok}",
               "Date de la prestation : {ctx.dok_sprzedaz}"),
        sekcja("parties", "komorka",
               "Émetteur | Client\n"
               "{vendeur.nazwa} | {acheteur.nazwa}\n"
               "{vendeur.adres} | {acheteur.adres}\n"
               "SIREN {vendeur.siren} | SIREN {acheteur.siren}\n"
               "TVA intracommunautaire {vendeur.vat} | TVA intracommunautaire {acheteur.vat}\n"
               "Tél. {vendeur.telefon} | Tél. {acheteur.telefon}"),
        sekcja("lines", "komorka",
               "Réf. | Désignation | Quantité | Prix unitaire HT | Total HT | TVA\n"
               "1 | Forfait de conseil juridique récurrent | 1 | {ctx.kf1} | {ctx.kf1} | 20 %\n"
               "2 | Revue d'un bail commercial | 1 | {ctx.kf2} | {ctx.kf2} | 20 %\n"
               "3 | Assistance à une réunion avec l'administration | 1 | {ctx.kf3} | {ctx.kf3} | 20 %",
               "Réf. | Désignation | Unité | Quantité | Total HT | TVA\n"
               "1 | Conseil selon la convention du {ctx.umowa_dawna} | forfait | 1 | {ctx.kf1} | 20 %\n"
               "2 | Rédaction et négociation d'actes | forfait | 1 | {ctx.kf2} | 20 %\n"
               "3 | Assistance à des assemblées d'associés | forfait | 1 | {ctx.kf3} | 20 %",
               min=1, max=1),
        sekcja("totals", "komorka",
               "Total HT | TVA 20 % | Total TTC\n{ctx.netto} | {ctx.vat} | {ctx.brutto}"),
        sekcja("payment", "akapit",
               "Échéance de paiement : {ctx.dok_termin_fv}, par virement sur le compte {vendeur.rachunek} en rappelant "
               "le numéro de facture.",
               "Pour toute question relative à cette facture : {vendeur.email}, tél. {vendeur.telefon}."),
        sekcja("legal", "akapit",
               "Mentions légales : {vendeur.nazwa}, société d'exercice libéral à responsabilité limitée au capital de "
               "{ctx.kapital2}, {vendeur.rcs} {vendeur.siren}, TVA intracommunautaire {vendeur.vat}.",
               "Pas d'escompte pour paiement anticipé. En cas de retard de paiement, des pénalités sont exigibles au taux "
               "de trois fois le taux d'intérêt légal, ainsi qu'une indemnité forfaitaire pour frais de recouvrement de "
               "40 euros."),
        sekcja("notes", "akapit",
               "La prestation est réalisée en France et soumise à la TVA au taux normal de 20 %.",
               "Cette facture est dématérialisée (format Factur-X) et valable sans signature manuscrite.",
               "Les factures sont conservées dix ans par l'émetteur.",
               min=2, max=3),
        sekcja("issued", "akapit",
               "La facture a été envoyée par courriel à {destinataire.pelne}, "
               + g("destinataire", "habilité", "habilitée") + " à recevoir les documents comptables du client.",
               "Établie et vérifiée par {emetteur.pelne}."),
        sekcja("signature", "podpis", "{emetteur.pelne}"),
        sekcja("footer", "stopka",
               "{vendeur.nazwa} | {vendeur.adres} | SIREN {vendeur.siren} | TVA intracommunautaire {vendeur.vat} | "
               "Tél. {vendeur.telefon}"),
    ],
    metadane={"author": "{emetteur.pelne}", "subject": "Facture d'honoraires"},
)
