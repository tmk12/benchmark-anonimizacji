"""Note interne d'un avocat collaborateur à l'associé pour préparer l'audience de plaidoirie dans un dossier de recouvrement
d'un prêt entre particuliers: parties, faits, preuves, calendrier, frais, transaction, pièces manquantes. Date de la note
`ctx.przed_rozprawa`, échéance des conclusions `notatka_termin` < `rozprawa`; tribunal judiciaire, numéro RG cohérent
avec la juridiction; points numérotés par `{#}`."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja
from ._formy import g

SZABLON = Szablon(
    jezyk="fr", typ="notatka", warianty=("fr_tj_unique", "fr_tj_collegiale"),
    role={"cabinet": "kancelaria", "redacteur": "osoba", "associe": "osoba", "client": "osoba", "adversaire": "osoba",
          "temoin": "osoba", "sad": "sad"},
    sekcje=[
        sekcja("letterhead", "naglowek",
               "{cabinet.nazwa}",
               "{cabinet.adres} | Tél. {cabinet.telefon}"),
        sekcja("heading", "akapit",
               "NOTE INTERNE – CONFIDENTIEL – SECRET PROFESSIONNEL",
               "De : {redacteur.pelne}",
               "À : {associe.pelne}",
               "Date : {ctx.przed_rozprawa}",
               "Objet : dossier " + g("client", "M.", "Mme") + " {client.pelne} contre "
               + g("adversaire", "M.", "Mme") + " {adversaire.pelne} – préparation de l'audience de plaidoirie"),
        sekcja("parties", "akapit",
               g("client", "Client", "Cliente") + " : {client.pelne}, " + g("client", "demandeur", "demanderesse")
               + " à l'instance, demeurant {client.adres}, tél. {client.telefon}, courriel {client.email}.",
               "Partie adverse : {adversaire.pelne}, " + g("adversaire", "défendeur", "défenderesse")
               + ", demeurant {adversaire.adres}.",
               "Juridiction : {sad.nazwa}, affaire {sad.sygnatura}.",
               min=3, max=3),
        sekcja("facts", "akapit",
               "Point n° {#} – Faits. " + g("client", "Le client", "La cliente") + " a consenti le {ctx.umowa} un prêt "
               "de {ctx.glowna} à la partie adverse, remboursable au plus tard le {ctx.termin_platnosci} ; seuls des "
               "remboursements partiels ont été effectués.",
               "Point n° {#} – Preuves. La reconnaissance de dette signée figure au dossier, ainsi que le relevé de "
               "compte attestant le virement. {temoin.rodzaj:Monsieur|Madame} {temoin.pelne} a entendu la partie adverse "
               "reconnaître sa dette et est " + g("temoin", "prêt", "prête") + " à attester (tél. {temoin.telefon}).",
               "Point n° {#} – Mise en demeure. Une mise en demeure a été adressée par lettre recommandée le "
               "{ctx.wezwanie} ; le délai expirait le {ctx.termin_wezwania}.",
               "Point n° {#} – Fondement. L'action repose sur les articles 1103 et 1902 du Code civil ; les intérêts "
               "courent à compter de la mise en demeure (article 1231-6 du même code).",
               min=4, max=4),
        sekcja("advice", "akapit",
               "Point n° {#} – Calendrier. Nos conclusions doivent être déposées au plus tard le {ctx.notatka_termin} ; "
               "l'audience de plaidoirie est fixée au {ctx.rozprawa}.",
               "Point n° {#} – Présence. " + g("client", "Le client", "La cliente") + " n'a pas l'obligation de "
               "comparaître, mais sa présence est recommandée pour répondre aux questions du tribunal.",
               "Point n° {#} – Frais. Nous demandons {ctx.koszty_zast} au titre de l'article 700 du Code de procédure "
               "civile ; le risque de ne pas l'obtenir intégralement a été expliqué à "
               + g("client", "notre client", "notre cliente") + ".",
               "Point n° {#} – Transaction. Un accord avec la partie adverse reste envisageable si elle règle au moins "
               "{ctx.ugoda_rata} immédiatement.",
               min=3, max=4),
        sekcja("documents", "akapit",
               "Pièces manquantes : relevé de compte complet des douze mois suivant le prêt, échanges de courriels et de "
               "messages avec la partie adverse.",
               "Les échanges avec le greffe et avec les confrères passent par le RPVA (réseau privé virtuel des avocats).",
               "Les actes sont signifiés par commissaire de justice ; le dossier est conservé dans le logiciel du cabinet, "
               "avec un accès restreint.",
               min=2, max=3),
        sekcja("actions", "akapit",
               "Prochaines étapes : finaliser les conclusions, préparer le bordereau de pièces et convoquer le témoin.",
               "Rappeler " + g("client", "M.", "Mme") + " {client.pelne} le {ctx.notatka_termin}.",
               min=2, max=2),
        sekcja("signature", "podpis", "{redacteur.pelne}"),
        sekcja("footer", "stopka",
               "{cabinet.nazwa} | {cabinet.adres} | SIREN {cabinet.siren} | TVA intracommunautaire {cabinet.vat} | "
               "Tél. {cabinet.telefon} | {cabinet.email}"),
    ],
    metadane={"author": "{redacteur.pelne}", "subject": "Note interne – préparation d'audience", "case": "{sad.sygnatura}"},
)
