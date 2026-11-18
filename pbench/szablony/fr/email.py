"""Courriel d'un avocat à son client (le défendeur): projet de conclusions en défense à relire, date d'audience, pièces,
provision (De/À/Cc en métadonnées), formule de politesse selon le genre, signature avec téléphone et mention de
confidentialité. Procédure devant le tribunal judiciaire (numéro RG cohérent). Échéances: `odp_termin` < `rozprawa`."""
from __future__ import annotations

from ...budowa import Szablon
from .._pomoc import sekcja
from ._formy import civ, g

SZABLON = Szablon(
    jezyk="fr", typ="email", warianty=("fr_tj_unique", "fr_tj_collegiale"),
    role={"cabinet": "kancelaria", "expediteur": "osoba", "client": "osoba", "confrere": "osoba",
          "adversaire": "osoba", "temoin": "osoba", "sad": "sad", "affaire": "sprawa", "portail": "sprawa"},
    sekcje=[
        sekcja("greeting", "akapit",
               g("client", "Cher Monsieur", "Chère Madame") + " {client.nazwisko},"),
        sekcja("intro", "akapit",
               "Comme convenu lors de notre entretien téléphonique, je vous adresse le projet de conclusions en défense "
               "dans l'affaire {affaire.sygnatura}, dans laquelle " + civ("adversaire") + " {adversaire.pelne} vous "
               "oppose une demande en remboursement.",
               "Je vous confirme que le {sad.nazwa} a fixé l'audience de plaidoirie au {ctx.rozprawa}. Merci de me dire "
               "si vous serez disponible ce jour-là.",
               "Je vous remercie pour les pièces transmises. Après un premier examen, les faits sont bien documentés, "
               "mais certaines pièces manquent encore.",
               min=3, max=3),
        sekcja("draft", "akapit",
               "Le projet est joint au format Word avec suivi des modifications. Merci de me transmettre vos observations "
               "avant le {ctx.odp_termin}, date limite pour le dépôt de nos conclusions ; un report n'est possible que "
               "pour un motif sérieux."),
        sekcja("body", "akapit",
               "J'ai besoin de votre part : la confirmation de votre adresse ({client.adres}), le justificatif du "
               "virement et la copie des échanges des deux dernières années.",
               "Je vous remercie de verser une provision de {ctx.zaliczka_kosztow} sur le compte du cabinet "
               "{cabinet.rachunek} avant l'audience.",
               "Vous pouvez déposer les pièces sur notre espace client sécurisé : {portail.url}. Merci de ne pas "
               "envoyer les documents sensibles par courriel simple.",
               civ("temoin") + " {temoin.pelne}, dont l'attestation figure au dossier, a été "
               + g("temoin", "prévenu", "prévenue") + " que le tribunal pourrait l'entendre ; si son numéro "
               "({temoin.telefon}) change, merci de me le signaler.",
               "Sur le plan stratégique, je vous propose de contester le montant réclamé et de proposer à titre "
               "subsidiaire un échéancier, si le tribunal l'accepte.",
               min=3, max=5),
        sekcja("closing", "akapit",
               "Je reste à votre disposition au {expediteur.telefon} ou à l'adresse {expediteur.email}.",
               "Je mets en copie " + g("confrere", "mon confrère", "ma consœur") + " Maître {confrere.pelne}, qui me "
               "remplacera en cas d'absence.",
               "Je vous prie d'agréer, " + civ("client") + ", l'expression de mes salutations distinguées.",
               min=3, max=3),
        sekcja("signature", "stopka",
               "{expediteur.pelne} | " + g("expediteur", "Avocat", "Avocate") + " | {cabinet.nazwa} | {cabinet.adres} | "
               "Tél. {cabinet.telefon}"),
        sekcja("disclaimer", "stopka",
               "Ce message est confidentiel et peut contenir des informations couvertes par le secret professionnel. Si "
               "vous n'en êtes pas le destinataire, merci d'en informer l'expéditeur et de supprimer le message.",
               "Vos données personnelles sont traitées par le cabinet {cabinet.nazwa} pour la gestion de votre dossier, "
               "conformément au RGPD ; vous disposez d'un droit d'accès et de rectification en écrivant au cabinet.",
               min=1, max=2),
    ],
    metadane={"from": "{expediteur.email}", "to": "{client.email}", "cc": "{confrere.email}",
              "subject": "Projet de conclusions en défense – merci de relire et de nous transmettre vos observations"},
)
