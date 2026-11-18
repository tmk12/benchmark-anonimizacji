"""Procès-verbal de l'assemblée générale ordinaire annuelle d'une SARL: convocation, feuille de présence (tableau),
quorum (toutes les parts sociales représentées), comptes, résolutions (nomination d'un gérant, affectation du résultat,
modification des statuts), clôture. Capital en parts sociales de `ctx.nominal` (10 €); les points sont numérotés par
`{#}` sans lacunes. Uczestnicy pełnoletni (`dorosli`); spółka jest SARL, więc organem jest gérant, a nie président."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja
from ._formy import civ, g

SZABLON = Szablon(
    jezyk="fr", typ="protokol", dorosli=True,
    role={"societe": "spolka", "president": "osoba", "secretaire": "osoba", "associe1": "osoba", "associe2": "osoba",
          "associe3": "osoba", "gerant": "osoba", "nouveau": "osoba", "expert": "osoba"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{societe.nazwa}",
               "{societe.adres} | {societe.rcs} {societe.siren} | TVA intracommunautaire {societe.vat}"),
        sekcja("title", "akapit",
               "PROCÈS-VERBAL DE L'ASSEMBLÉE GÉNÉRALE ORDINAIRE ANNUELLE DE LA SOCIÉTÉ {societe.nazwa:upper}",
               "Lieu et date : {societe.miasto}, siège social, {societe.adres}, le {ctx.dok}"),
        sekcja("open", "akapit",
               "Point n° {#} – Ouverture. " + civ("president") + " {president.pelne}, "
               + g("president", "président", "présidente") + " de séance, ouvre l'assemblée. " + civ("secretaire")
               + " {secretaire.pelne} est " + g("secretaire", "désigné", "désignée") + " secrétaire de séance.",
               "Point n° {#} – Convocation. " + g("president", "Le président de séance", "La présidente de séance")
               + " constate que les associés ont été convoqués par lettre recommandée avec demande d'avis de réception, "
               "accompagnée de l'ordre du jour et des comptes de l'exercice, au moins quinze jours avant la date de la "
               "réunion.",
               "Point n° {#} – Gérance. " + civ("gerant") + " {gerant.pelne}, " + g("gerant", "gérant", "gérante")
               + " de la société, assiste à la réunion et répond aux questions des associés.",
               min=3, max=3),
        sekcja("attendance_label", "akapit", "Associés présents ou représentés :"),
        sekcja("attendance", "komorka",
               "N° | Associé | Parts sociales | Valeur nominale par part | Montant des parts | Voix\n"
               "1 | {associe1.pelne} | {ctx.udzialy1} | {ctx.nominal} | {ctx.wartosc1} | {ctx.udzialy1}\n"
               "2 | {associe2.pelne} | {ctx.udzialy2} | {ctx.nominal} | {ctx.wartosc2} | {ctx.udzialy2}\n"
               "3 | {associe3.pelne} | {ctx.udzialy3} | {ctx.nominal} | {ctx.wartosc3} | {ctx.udzialy3}\n"
               "Total | Ensemble des associés | {ctx.udzialy_suma3} | {ctx.nominal} | {ctx.kapital3} | {ctx.udzialy_suma3}"),
        sekcja("quorum", "akapit",
               "Point n° {#} – Quorum. Les associés présents ou représentés détiennent la totalité des "
               "{ctx.udzialy_suma3} parts sociales ; l'assemblée peut valablement délibérer.",
               "Point n° {#} – Capital social. Le capital de la société est de {ctx.kapital3}, divisé en "
               "{ctx.udzialy_suma3} parts sociales de {ctx.nominal} chacune, entièrement libérées ; chaque part donne "
               "droit à une voix.",
               min=2, max=2),
        sekcja("accounts", "akapit",
               "Point n° {#} – Comptes annuels. Les comptes de l'exercice écoulé ont été arrêtés par la gérance ; "
               + civ("expert") + " {expert.pelne}, " + g("expert", "expert-comptable", "experte-comptable") + ", en "
               "présente la synthèse et indique qu'ils donnent une image fidèle du patrimoine et du résultat de la "
               "société.",
               "Point n° {#} – Rapport de gestion. " + civ("gerant") + " {gerant.pelne} présente le rapport de gestion et "
               "les perspectives de l'exercice en cours.",
               min=2, max=2),
        sekcja("resolutions", "akapit",
               "Point n° {#} – Première résolution : approbation des comptes. L'assemblée approuve les comptes annuels de "
               "l'exercice écoulé et donne quitus à la gérance de sa mission. Cette résolution est adoptée à "
               "l'unanimité.",
               "Point n° {#} – Deuxième résolution : nomination d'un gérant. " + civ("nouveau") + " {nouveau.pelne}, "
               "demeurant {nouveau.adres}, est " + g("nouveau", "nommé gérant", "nommée gérante") + " à compter de ce "
               "jour, pour une durée indéterminée. Vote : {ctx.glosy_za2} voix pour, {ctx.glosy_przeciw2} voix contre.",
               "Point n° {#} – Troisième résolution : affectation du résultat. L'assemblée décide de distribuer aux "
               "associés un dividende global de {ctx.dywidenda}, au prorata de leurs parts sociales, mis en paiement dans "
               "un délai de trois mois.",
               "Point n° {#} – Quatrième résolution : conventions réglementées. L'assemblée prend acte qu'aucune "
               "convention réglementée nouvelle n'a été conclue au cours de l'exercice ; les comptes approuvés seront déposés "
               "au greffe du {societe.registro}.",
               min=4, max=4),
        sekcja("close", "akapit",
               "Point n° {#} – Clôture. L'ordre du jour étant épuisé, "
               + g("president", "le président de séance", "la présidente de séance") + " lève la séance.",
               "La prochaine assemblée générale ordinaire annuelle statuera sur les comptes de l'exercice en cours, dans les "
               "six mois suivant sa clôture.",
               "Le présent procès-verbal est signé par " + g("president", "le président de séance", "la présidente de séance")
               + " et " + g("secretaire", "le secrétaire", "la secrétaire") + ", puis conservé dans le registre des "
               "décisions des associés de la société.",
               min=3, max=3),
        sekcja("sign_label", "akapit", "Signatures :"),
        sekcja("signatures", "podpis", "{president.pelne}", "{secretaire.pelne}"),
        sekcja("footer", "stopka",
               "{societe.nazwa} | {societe.adres} | Tél. {societe.telefon} | {societe.email}"),
    ],
    metadane={"author": "{secretaire.pelne}", "subject": "Procès-verbal d'assemblée générale ordinaire annuelle"},
)
